from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import date, datetime
from typing import Optional

PRIORITY_LABELS = {1: "low", 2: "medium", 3: "high"}
FREQUENCIES = ("daily", "weekly")
DEFAULT_DAY_START = "08:00"


def _to_minutes(hhmm: str) -> int:
    """Convert "HH:MM" to minutes since midnight."""
    parsed = datetime.strptime(hhmm, "%H:%M")
    return parsed.hour * 60 + parsed.minute


def _to_hhmm(minutes: int) -> str:
    """Convert minutes since midnight to "HH:MM"."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


@dataclass(eq=False)  # identity comparison: two identical tasks stay distinct
class Task:
    """A single pet care activity (walk, feeding, meds, grooming, enrichment)."""

    title: str
    category: str
    duration_minutes: int
    priority: int  # 1 = low, 2 = medium, 3 = high
    preferred_time: Optional[str] = None  # "HH:MM", e.g. "08:00"
    frequency: str = "daily"  # "daily" or "weekly"
    completed: bool = False
    pet_name: str = ""  # set by Pet.add_task so a plan can say "Walk Rex"

    def __post_init__(self) -> None:
        """Validate the task's fields as soon as it is created."""
        self._validate()

    def _validate(self) -> None:
        """Raise ValueError if duration, priority, frequency or time is invalid."""
        if not isinstance(self.duration_minutes, int) or self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be a positive integer")
        if self.priority not in PRIORITY_LABELS:
            raise ValueError("priority must be 1 (low), 2 (medium) or 3 (high)")
        if self.frequency not in FREQUENCIES:
            raise ValueError(f"frequency must be one of {FREQUENCIES}")
        if self.preferred_time is not None:
            try:
                _to_minutes(self.preferred_time)
            except ValueError:
                raise ValueError("preferred_time must look like 'HH:MM'") from None

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True

    def edit(self, **changes) -> None:
        """Update task fields such as duration, priority or preferred_time.

        Unknown field names raise AttributeError. If the new values are invalid,
        the task is left unchanged and ValueError is raised.
        """
        valid = {f.name for f in fields(self)}
        unknown = set(changes) - valid
        if unknown:
            raise AttributeError(f"Task has no field(s): {sorted(unknown)}")

        old = {name: getattr(self, name) for name in changes}
        for name, value in changes.items():
            setattr(self, name, value)
        try:
            self._validate()
        except ValueError:
            for name, value in old.items():
                setattr(self, name, value)
            raise


@dataclass(eq=False)  # identity comparison: two pets with the same name stay distinct
class Pet:
    """An animal being cared for. Owns its list of tasks."""

    name: str
    species: str
    breed: str = ""
    age: int = 0
    special_needs: str = ""
    tasks: list[Task] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Tag any tasks passed to the constructor with this pet's name."""
        for task in self.tasks:  # tasks passed to the constructor
            task.pet_name = self.name

    def add_task(self, task: Task) -> None:
        """Add a care task to this pet and set task.pet_name."""
        if any(task is existing for existing in self.tasks):
            return
        task.pet_name = self.name
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a care task from this pet. Raises ValueError if it isn't here."""
        self.tasks.remove(task)
        task.pet_name = ""

    def get_tasks(
        self, status: Optional[bool] = None, category: Optional[str] = None
    ) -> list[Task]:
        """Return tasks, optionally filtered by completion status or category.

        status=True returns completed tasks, status=False returns pending ones,
        and None returns both.
        """
        result = self.tasks
        if status is not None:
            result = [t for t in result if t.completed == status]
        if category is not None:
            result = [t for t in result if t.category == category]
        return list(result)


@dataclass
class Owner:
    """The person using the app. Holds time constraints and preferences.

    preferences keys used by the Scheduler:
        "day_start": "HH:MM" time the day's plan begins (default "08:00")
    """

    name: str
    available_minutes: int
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        if any(pet is existing for existing in self.pets):
            return
        self.pets.append(pet)

    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet from this owner. Raises ValueError if it isn't here."""
        self.pets.remove(pet)

    def get_all_tasks(self) -> list[Task]:
        """Collect tasks across all of this owner's pets."""
        return [task for pet in self.pets for task in pet.get_tasks()]


@dataclass
class ScheduledItem:
    """A task placed in (or left out of) the plan, with the reason why."""

    task: Task
    start_time: Optional[str] = None  # None when the task was skipped
    reason: str = ""  # shown by Scheduler.explain_plan()


class Scheduler:
    """Turns an owner's tasks and constraints into a daily plan.

    The Scheduler only talks to the Owner: owner.get_all_tasks() gathers tasks
    from every pet, so it never reaches into a Pet directly.
    """

    def __init__(self, owner: Owner, plan_date: Optional[date] = None) -> None:
        """Create a scheduler for an owner, defaulting the plan date to today."""
        self.owner = owner
        self.date = plan_date or date.today()
        self.scheduled_items: list[ScheduledItem] = []
        self.skipped_tasks: list[ScheduledItem] = []

    def generate_plan(self) -> None:
        """Sort tasks by priority and fit them into the owner's available time.

        1. Take every pending task from the owner's pets.
        2. Pick tasks highest priority first (ties: earlier preferred time, then
           shorter) until available_minutes is used up. A task that doesn't fit
           is skipped and smaller ones are still tried.
        3. Place tasks with a preferred time at that time (pushed back if it
           overlaps another), then slot the rest into the earliest free gap
           from day_start.

        Clears previous results first, so calling it twice is safe.
        """
        self.scheduled_items = []
        self.skipped_tasks = []

        pending = [t for t in self.owner.get_all_tasks() if not t.completed]
        pending.sort(
            key=lambda t: (
                -t.priority,
                _to_minutes(t.preferred_time) if t.preferred_time else 24 * 60,
                t.duration_minutes,
            )
        )

        # Step 1: choose what fits in the time budget.
        budget = self.owner.available_minutes
        chosen: list[Task] = []
        for task in pending:
            if task.duration_minutes <= budget:
                budget -= task.duration_minutes
                chosen.append(task)
            else:
                self.skipped_tasks.append(
                    ScheduledItem(
                        task,
                        reason=(
                            f"Skipped: needs {task.duration_minutes} min but only "
                            f"{budget} of {self.owner.available_minutes} min were left "
                            f"({PRIORITY_LABELS[task.priority]} priority)."
                        ),
                    )
                )

        # Step 2: place the chosen tasks on the clock.
        day_start = _to_minutes(self.owner.preferences.get("day_start", DEFAULT_DAY_START))
        busy: list[tuple[int, int]] = []  # (start, end) in minutes
        placed: list[tuple[int, Task, str]] = []

        fixed = sorted(
            ((_to_minutes(t.preferred_time), t) for t in chosen if t.preferred_time),
            key=lambda pair: pair[0],
        )
        previous_end = 0
        for wanted, task in fixed:
            start = max(wanted, previous_end)
            if start == wanted:
                note = f"scheduled at its preferred time {task.preferred_time}"
            else:
                note = (
                    f"preferred time {task.preferred_time} overlapped another task, "
                    f"moved to {_to_hhmm(start)}"
                )
            previous_end = start + task.duration_minutes
            busy.append((start, previous_end))
            placed.append((start, task, note))

        for task in chosen:
            if task.preferred_time:
                continue
            start = self._earliest_gap(busy, task.duration_minutes, day_start)
            busy.append((start, start + task.duration_minutes))
            busy.sort()
            placed.append((start, task, "no preferred time, placed in the first free slot"))

        placed.sort(key=lambda entry: entry[0])
        self.scheduled_items = [
            ScheduledItem(
                task,
                start_time=_to_hhmm(start),
                reason=f"{PRIORITY_LABELS[task.priority].capitalize()} priority; {note}.",
            )
            for start, task, note in placed
        ]

    @staticmethod
    def _earliest_gap(busy: list[tuple[int, int]], duration: int, day_start: int) -> int:
        """Return the earliest start (in minutes) where `duration` fits."""
        cursor = day_start
        for start, end in sorted(busy):
            if start - cursor >= duration:
                return cursor
            cursor = max(cursor, end)
        return cursor

    def explain_plan(self) -> list[str]:
        """Return a reason for each task that was scheduled or skipped."""
        lines = []
        for item in self.scheduled_items:
            task = item.task
            who = f" ({task.pet_name})" if task.pet_name else ""
            lines.append(
                f"{item.start_time} - {task.title}{who}, "
                f"{task.duration_minutes} min: {item.reason}"
            )
        for item in self.skipped_tasks:
            task = item.task
            who = f" ({task.pet_name})" if task.pet_name else ""
            lines.append(f"-- - {task.title}{who}, {task.duration_minutes} min: {item.reason}")
        return lines

    def get_summary(self) -> dict:
        """Return totals such as time used, time left and task counts."""
        used = sum(i.task.duration_minutes for i in self.scheduled_items)
        available = self.owner.available_minutes
        return {
            "date": self.date,
            "available_minutes": available,
            "minutes_scheduled": used,
            "minutes_remaining": available - used,
            "tasks_scheduled": len(self.scheduled_items),
            "tasks_skipped": len(self.skipped_tasks),
        }
