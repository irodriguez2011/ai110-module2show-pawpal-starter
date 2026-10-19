from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Task:
    """A single pet care activity (walk, feeding, meds, grooming, enrichment)."""

    title: str
    category: str
    duration_minutes: int
    priority: int  # e.g. 1 = low, 2 = medium, 3 = high
    preferred_time: Optional[str] = None  # e.g. "08:00"
    frequency: str = "daily"  # "daily" or "weekly"
    completed: bool = False

    def mark_complete(self) -> None:
        """Mark this task as done."""
        pass

    def edit(self, **fields) -> None:
        """Update task fields such as duration, priority or preferred_time."""
        pass


@dataclass
class Pet:
    """An animal being cared for. Owns its list of tasks."""

    name: str
    species: str
    breed: str = ""
    age: int = 0
    special_needs: str = ""
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task to this pet."""
        pass

    def remove_task(self, task: Task) -> None:
        """Remove a care task from this pet."""
        pass

    def get_tasks(
        self, status: Optional[bool] = None, category: Optional[str] = None
    ) -> list[Task]:
        """Return tasks, optionally filtered by completion status or category."""
        raise NotImplementedError


@dataclass
class Owner:
    """The person using the app. Holds time constraints and preferences."""

    name: str
    available_minutes: int
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        pass

    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet from this owner."""
        pass

    def get_all_tasks(self) -> list[Task]:
        """Collect tasks across all of this owner's pets."""
        raise NotImplementedError


class Scheduler:
    """Turns an owner's tasks and constraints into a daily plan."""

    def __init__(self, owner: Owner, plan_date: Optional[date] = None) -> None:
        self.owner = owner
        self.date = plan_date or date.today()
        self.scheduled_items: list[Task] = []
        self.skipped_tasks: list[Task] = []

    def generate_plan(self) -> None:
        """Sort tasks by priority and fit them into the owner's available time."""
        pass

    def explain_plan(self) -> list[str]:
        """Return a reason for each task that was scheduled or skipped."""
        raise NotImplementedError

    def get_summary(self) -> dict:
        """Return totals such as time used, time left and task counts."""
        raise NotImplementedError
