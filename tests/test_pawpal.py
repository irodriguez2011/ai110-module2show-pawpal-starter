"""Tests for PawPal+: tasks, pets, owners and the scheduler.

Layout: shared constants and helpers first, then one test class per behavior.
Every date is fixed (see TODAY below), so results never depend on the real day.
"""

from datetime import date, timedelta

import pytest

import pawpal_system
from pawpal_system import Owner, Pet, Scheduler, Task

# --------------------------------------------------------------------------- #
# Fixed dates: no test reads the real clock.
# --------------------------------------------------------------------------- #
TODAY = date(2026, 10, 19)  # a Monday
MON = date(2026, 10, 12)  # a Monday ...
THU = date(2026, 10, 15)  # ... and the Thursday after it
FROZEN_DAY = date(2027, 1, 31)  # "today" for tests of the real-clock defaults


class _NoClock(date):
    """Stands in for `date` inside pawpal_system and fails if anyone asks for today."""

    @classmethod
    def today(cls):
        raise AssertionError(
            "test read the real clock: pass due_date / plan_date / today explicitly"
        )


@pytest.fixture(autouse=True)
def no_real_clock(monkeypatch):
    """Make any accidental date.today() call inside the backend fail the test."""
    monkeypatch.setattr(pawpal_system, "date", _NoClock)


class _FrozenClock(date):
    """Stands in for `date` inside pawpal_system with a clock stuck on FROZEN_DAY."""

    @classmethod
    def today(cls):
        return FROZEN_DAY


@pytest.fixture
def frozen_clock(monkeypatch):
    """Let the backend ask for today's date, and answer FROZEN_DAY every time."""
    monkeypatch.setattr(pawpal_system, "date", _FrozenClock)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def make_task(*args, **kwargs):
    """Build a Task due on the fixed TODAY unless the test gives a due_date."""
    kwargs.setdefault("due_date", TODAY)
    return Task(*args, **kwargs)


def _owner_with_pets():
    """An owner with 240 minutes and two empty pets: (owner, mochi, luna)."""
    owner = Owner(name="Jordan", available_minutes=240)
    mochi, luna = Pet("Mochi", "dog"), Pet("Luna", "cat")
    owner.add_pet(mochi)
    owner.add_pet(luna)
    return owner, mochi, luna


def _plan(owner, plan_date=TODAY):
    """Generate and return a plan for `plan_date`."""
    scheduler = Scheduler(owner, plan_date=plan_date)
    scheduler.generate_plan()
    return scheduler


class TestSorting:
    """Scheduler.sort_by_time and clock-ordered plans."""

    def test_sort_by_time_puts_untimed_last(self):
        a = make_task("B", "other", 5, 1, preferred_time="09:00")
        b = make_task("A", "other", 5, 1, preferred_time="07:30")
        c = make_task("C", "other", 5, 1)
        assert Scheduler.sort_by_time([a, c, b]) == [b, a, c]

    def test_sort_by_time_orders_hhmm_strings(self):
        tasks = [
            make_task(str(t), "other", 5, 1, preferred_time=t)
            for t in ("18:00", "07:30", "09:05")
        ]
        assert [t.preferred_time for t in Scheduler.sort_by_time(tasks)] == [
            "07:30",
            "09:05",
            "18:00",
        ]

    def test_sort_by_time_empty_and_single(self):
        assert Scheduler.sort_by_time([]) == []
        only = make_task("Walk", "exercise", 5, 1, preferred_time="08:00")
        assert Scheduler.sort_by_time([only]) == [only]

    def test_sort_by_time_handles_midnight_and_end_of_day(self):
        late = make_task("Late", "other", 5, 1, preferred_time="23:59")
        midnight = make_task("Midnight", "other", 5, 1, preferred_time="00:00")
        untimed = make_task("Untimed", "other", 5, 1)
        assert Scheduler.sort_by_time([untimed, late, midnight]) == [
            midnight,
            late,
            untimed,
        ]

    def test_sort_by_time_is_stable_for_ties_and_untimed(self):
        a = make_task("A", "other", 5, 1, preferred_time="09:00")
        b = make_task("B", "other", 5, 1, preferred_time="09:00")
        c, d = make_task("C", "other", 5, 1), make_task("D", "other", 5, 1)
        assert Scheduler.sort_by_time([d, b, c, a]) == [b, a, d, c]

    def test_sort_by_time_does_not_mutate_input(self):
        tasks = [
            make_task("B", "other", 5, 1, preferred_time="10:00"),
            make_task("A", "other", 5, 1, preferred_time="07:00"),
        ]
        original = list(tasks)
        Scheduler.sort_by_time(tasks)
        assert tasks == original

    def test_plan_is_in_clock_order_even_when_priority_differs(self):
        owner, mochi, _ = _owner_with_pets()
        mochi.add_task(make_task("Low early", "other", 10, 1, preferred_time="08:00"))
        mochi.add_task(make_task("High late", "other", 10, 3, preferred_time="09:00"))
        mochi.add_task(make_task("Med untimed", "other", 10, 2))
        starts = [i.start_time for i in _plan(owner).scheduled_items]
        assert starts == sorted(starts)


class TestFiltering:
    """Owner.filter_tasks by pet, status and category."""

    def test_filter_tasks_by_pet_and_status(self):
        owner, mochi, luna = _owner_with_pets()
        walk = make_task("Walk", "exercise", 20, 3)
        feed = make_task("Feed", "food", 5, 3)
        mochi.add_task(walk)
        luna.add_task(feed)
        next_walk = walk.mark_complete(today=TODAY)  # also adds tomorrow's walk to Mochi
        assert owner.filter_tasks(pet_name="Mochi") == [walk, next_walk]
        assert owner.filter_tasks(pet_name="Mochi", status=True) == [walk]
        assert owner.filter_tasks(status=False) == [next_walk, feed]
        assert owner.filter_tasks(pet_name="Luna", status=True) == []


class TestRecurrence:
    """Completing a task creates its next occurrence."""

    def test_mark_complete_changes_task_status(self):
        task = make_task("Morning walk", "exercise", 30, priority=3)
        assert task.completed is False

        task.mark_complete(today=TODAY)

        assert task.completed is True

    def test_completing_daily_task_creates_next_day_task(self):
        _, mochi, _ = _owner_with_pets()
        walk = make_task(
            "Walk", "exercise", 20, 3, frequency="daily", due_date=date(2020, 1, 1)
        )
        mochi.add_task(walk)
        nxt = mochi.complete_task(walk, today=TODAY)
        assert walk.completed and not nxt.completed
        assert nxt.due_date == TODAY + timedelta(days=1)  # today + 1, not old due + 1
        assert nxt in mochi.tasks and nxt.pet_name == "Mochi"

    def test_daily_completion_creates_task_for_following_day(self):
        _, mochi, _ = _owner_with_pets()
        walk = make_task(
            "Walk", "exercise", 20, 3, frequency="daily", preferred_time="07:30"
        )
        mochi.add_task(walk)
        nxt = walk.mark_complete(today=TODAY)
        assert nxt is not walk and nxt.completed is False
        assert nxt.due_date == TODAY + timedelta(days=1)
        assert (
            nxt.title,
            nxt.duration_minutes,
            nxt.priority,
            nxt.preferred_time,
            nxt.frequency,
        ) == (
            "Walk",
            20,
            3,
            "07:30",
            "daily",
        )
        assert nxt.pet is mochi and nxt in mochi.tasks

    def test_completing_weekly_task_moves_a_week(self):
        bath = make_task(
            "Bath", "grooming", 30, 2, frequency="weekly", due_date=date(2026, 10, 19)
        )
        assert bath.next_occurrence(today=date(2026, 10, 19)).due_date == date(2026, 10, 26)

    def test_next_occurrence_crosses_month_boundary(self):
        walk = make_task(
            "Walk", "exercise", 20, 3, frequency="daily", due_date=date(2026, 10, 31)
        )
        assert walk.next_occurrence(today=date(2026, 10, 31)).due_date == date(2026, 11, 1)

    @pytest.mark.parametrize(
        "today, frequency, expected",
        [
            (date(2026, 12, 31), "daily", date(2027, 1, 1)),  # year boundary
            (date(2028, 2, 28), "daily", date(2028, 2, 29)),  # leap day exists
            (date(2027, 2, 28), "daily", date(2027, 3, 1)),  # no leap day
            (date(2026, 12, 28), "weekly", date(2027, 1, 4)),  # weekly across the year
        ],
    )
    def test_next_occurrence_calendar_boundaries(self, today, frequency, expected):
        task = make_task("T", "other", 5, 1, frequency=frequency, due_date=today)
        assert task.next_occurrence(today=today).due_date == expected

    def test_next_occurrence_does_not_complete_or_mutate_original(self):
        task = make_task("T", "other", 5, 1, due_date=TODAY)
        task.next_occurrence(today=TODAY)
        assert task.completed is False and task.due_date == TODAY

    def test_mark_complete_automatically_adds_next_occurrence(self):
        _, mochi, _ = _owner_with_pets()
        walk = make_task("Walk", "exercise", 20, 3, frequency="daily")
        mochi.add_task(walk)
        nxt = walk.mark_complete(today=TODAY)
        assert len(mochi.tasks) == 2 and nxt in mochi.tasks
        assert nxt.due_date == TODAY + timedelta(days=1) and not nxt.completed

    def test_mark_complete_twice_does_not_duplicate(self):
        _, mochi, _ = _owner_with_pets()
        walk = make_task("Walk", "exercise", 20, 3)
        mochi.add_task(walk)
        walk.mark_complete(today=TODAY)
        assert walk.mark_complete(today=TODAY) is None
        assert len(mochi.tasks) == 2

    def test_removed_task_no_longer_spawns_into_pet(self):
        _, mochi, _ = _owner_with_pets()
        walk = make_task("Walk", "exercise", 20, 3)
        mochi.add_task(walk)
        mochi.remove_task(walk)
        walk.mark_complete(today=TODAY)
        assert mochi.tasks == []

    def test_completing_orphan_task_does_not_crash(self):
        task = make_task("Walk", "exercise", 20, 3)
        nxt = task.mark_complete(today=TODAY)
        assert task.completed and nxt.pet is None

    def test_complete_task_rejects_other_pets_task(self):
        _, mochi, luna = _owner_with_pets()
        pill = make_task("Pill", "health", 5, 3)
        luna.add_task(pill)
        with pytest.raises(ValueError):
            mochi.complete_task(pill, today=TODAY)
        assert pill.completed is False

    def test_new_occurrence_is_not_scheduled_until_due(self):
        owner, mochi, _ = _owner_with_pets()
        walk = make_task("Walk", "exercise", 20, 3, due_date=TODAY)
        mochi.add_task(walk)
        walk.mark_complete(today=TODAY)
        # Same day: only the completed original exists, nothing pending is due.
        assert _plan(owner, plan_date=TODAY).scheduled_items == []
        tomorrow = _plan(owner, plan_date=TODAY + timedelta(days=1))
        assert [i.task.title for i in tomorrow.scheduled_items] == ["Walk"]

    def test_overdue_task_appears_once_in_plan(self):
        owner, mochi, _ = _owner_with_pets()
        mochi.add_task(
            make_task("Walk", "exercise", 20, 3, due_date=TODAY - timedelta(days=5))
        )
        assert len(_plan(owner).scheduled_items) == 1

    def test_edit_frequency_changes_next_occurrence(self):
        task = make_task("T", "other", 10, 2, frequency="daily", due_date=TODAY)
        task.edit(frequency="weekly")
        assert task.next_occurrence(today=TODAY).due_date == TODAY + timedelta(weeks=1)


class TestLateAndEarlyCompletion:
    """The next due date stays on the task's own schedule."""

    def test_weekly_task_finished_late_stays_on_its_weekday(self):
        bath = make_task("Bath", "grooming", 30, 2, frequency="weekly", due_date=MON)
        assert MON.weekday() == 0
        nxt = bath.next_occurrence(today=THU)
        assert nxt.due_date == date(2026, 10, 19) and nxt.due_date.weekday() == 0

    def test_weekly_task_finished_many_weeks_late_lands_on_next_future_weekday(self):
        bath = make_task("Bath", "grooming", 30, 2, frequency="weekly", due_date=MON)
        nxt = bath.next_occurrence(today=date(2026, 11, 4))  # a Wednesday, 3+ weeks later
        assert nxt.due_date == date(2026, 11, 9) and nxt.due_date.weekday() == 0

    def test_daily_task_finished_late_comes_back_tomorrow(self):
        walk = make_task("Walk", "exercise", 20, 3, frequency="daily", due_date=MON)
        assert walk.next_occurrence(today=THU).due_date == THU + timedelta(days=1)

    def test_weekly_task_finished_early_keeps_its_original_schedule(self):
        bath = make_task(
            "Bath", "grooming", 30, 2, frequency="weekly", due_date=date(2026, 10, 26)
        )
        nxt = bath.next_occurrence(today=date(2026, 10, 22))  # done 4 days early
        assert nxt.due_date == date(2026, 11, 2)

    def test_weekly_task_finished_on_its_due_day_comes_back_in_a_week(self):
        bath = make_task("Bath", "grooming", 30, 2, frequency="weekly", due_date=MON)
        assert bath.next_occurrence(today=MON).due_date == MON + timedelta(weeks=1)

    def test_next_occurrence_is_never_overdue(self):
        for frequency in ("daily", "weekly"):
            task = make_task(
                "T", "other", 5, 1, frequency=frequency, due_date=date(2020, 1, 1)
            )
            assert task.next_occurrence(today=TODAY).due_date > TODAY


class TestOneOffTasks:
    """frequency='once' tasks never repeat."""

    def test_one_off_task_does_not_repeat_when_completed(self):
        _, mochi, _ = _owner_with_pets()
        pills = make_task("Buy flea medicine", "health", 20, 2, frequency="once")
        mochi.add_task(pills)
        assert pills.mark_complete(today=TODAY) is None
        assert pills.completed and mochi.tasks == [pills]

    def test_one_off_task_stays_until_done_then_leaves_the_plan(self):
        owner, mochi, _ = _owner_with_pets()
        errand = make_task("Vet visit", "health", 30, 3, frequency="once", due_date=TODAY)
        mochi.add_task(errand)
        assert (
            len(_plan(owner, TODAY + timedelta(days=3)).scheduled_items) == 1
        )  # carries over
        errand.mark_complete(today=TODAY)
        assert _plan(owner, TODAY + timedelta(days=3)).scheduled_items == []

    def test_one_off_task_has_no_next_occurrence(self):
        with pytest.raises(ValueError):
            make_task("Vet visit", "health", 30, 3, frequency="once").next_occurrence()

    def test_edit_can_turn_recurring_task_into_one_off(self):
        _, mochi, _ = _owner_with_pets()
        walk = make_task("Walk", "exercise", 20, 3, frequency="daily")
        mochi.add_task(walk)
        walk.edit(frequency="once")
        assert walk.mark_complete(today=TODAY) is None and len(mochi.tasks) == 1


class TestDefaultsUseToday:
    """When no date is given, the backend asks the clock (frozen here for a stable answer)."""

    def test_task_without_due_date_is_due_today(self, frozen_clock):
        assert Task("Walk", "exercise", 20, 3).due_date == FROZEN_DAY

    def test_scheduler_without_plan_date_plans_for_today(self, frozen_clock):
        owner, mochi, _ = _owner_with_pets()
        mochi.add_task(Task("Walk", "exercise", 20, 3))  # due today by default
        scheduler = Scheduler(owner)
        scheduler.generate_plan()
        assert scheduler.date == FROZEN_DAY
        assert [i.task.title for i in scheduler.scheduled_items] == ["Walk"]

    def test_completing_without_a_date_schedules_the_next_day_from_today(
        self, frozen_clock
    ):
        _, mochi, _ = _owner_with_pets()
        walk = Task("Walk", "exercise", 20, 3, frequency="daily")
        mochi.add_task(walk)
        nxt = walk.mark_complete()  # no `today` given: uses the clock
        assert nxt.due_date == date(2027, 2, 1)  # crosses the month end
        assert nxt in mochi.tasks


class TestConflictDetection:
    """Scheduler.detect_conflicts warns about overlapping preferred times."""

    def test_detect_conflicts_across_pets(self):
        owner, mochi, luna = _owner_with_pets()
        mochi.add_task(make_task("Walk", "exercise", 30, 3, preferred_time="08:00"))
        luna.add_task(make_task("Pill", "health", 5, 3, preferred_time="08:15"))
        warnings = Scheduler(owner, plan_date=TODAY).detect_conflicts()
        assert len(warnings) == 1 and "Pill" in warnings[0] and "Walk" in warnings[0]

    def test_detect_conflicts_none_when_back_to_back(self):
        owner, mochi, luna = _owner_with_pets()
        mochi.add_task(make_task("Walk", "exercise", 30, 3, preferred_time="08:00"))
        luna.add_task(make_task("Pill", "health", 5, 3, preferred_time="08:30"))
        assert Scheduler(owner, plan_date=TODAY).detect_conflicts() == []

    def test_detect_conflicts_catches_overlap_with_long_earlier_task(self):
        owner, mochi, luna = _owner_with_pets()
        mochi.add_task(make_task("Long", "exercise", 120, 3, preferred_time="08:00"))
        mochi.add_task(make_task("Short", "other", 10, 3, preferred_time="08:30"))
        luna.add_task(make_task("Late", "other", 10, 3, preferred_time="09:00"))
        assert len(Scheduler(owner, plan_date=TODAY).detect_conflicts()) == 2

    def test_same_time_same_pet_warns_without_crashing(self):
        owner, mochi, _ = _owner_with_pets()
        mochi.add_task(make_task("Walk", "exercise", 20, 3, preferred_time="09:00"))
        mochi.add_task(make_task("Vet call", "health", 15, 2, preferred_time="09:00"))
        warnings = Scheduler(owner, plan_date=TODAY).detect_conflicts()
        assert len(warnings) == 1
        assert "same pet: Mochi" in warnings[0] and "same time" in warnings[0]

    def test_same_time_different_pets_warns(self):
        owner, mochi, luna = _owner_with_pets()
        mochi.add_task(make_task("Walk", "exercise", 20, 3, preferred_time="09:00"))
        luna.add_task(make_task("Pill", "health", 5, 3, preferred_time="09:00"))
        warnings = Scheduler(owner, plan_date=TODAY).detect_conflicts()
        assert len(warnings) == 1 and "different pets" in warnings[0]

    def test_duplicate_times_are_flagged(self):
        owner, mochi, luna = _owner_with_pets()
        mochi.add_task(make_task("Walk", "exercise", 30, 3, preferred_time="08:00"))
        luna.add_task(make_task("Feed", "food", 10, 3, preferred_time="08:00"))
        warnings = Scheduler(owner, plan_date=TODAY).detect_conflicts()
        assert len(warnings) == 1
        assert "same time" in warnings[0] and "08:00" in warnings[0]

    def test_one_minute_overlap_is_flagged(self):
        owner, mochi, _ = _owner_with_pets()
        mochi.add_task(make_task("A", "other", 30, 3, preferred_time="08:00"))
        mochi.add_task(make_task("B", "other", 10, 3, preferred_time="08:29"))
        assert len(Scheduler(owner, plan_date=TODAY).detect_conflicts()) == 1

    def test_three_tasks_at_same_time_give_two_warnings(self):
        owner, mochi, luna = _owner_with_pets()
        for pet, title in ((mochi, "A"), (mochi, "B"), (luna, "C")):
            pet.add_task(make_task(title, "other", 10, 2, preferred_time="09:00"))
        assert len(Scheduler(owner, plan_date=TODAY).detect_conflicts()) == 2

    def test_untimed_completed_and_future_tasks_never_conflict(self):
        owner, mochi, luna = _owner_with_pets()
        mochi.add_task(make_task("Untimed 1", "other", 10, 2))
        mochi.add_task(make_task("Untimed 2", "other", 10, 2))
        done = make_task("Done", "other", 10, 2, preferred_time="09:00")
        mochi.add_task(done)
        done.completed = True
        luna.add_task(
            make_task(
                "Future",
                "other",
                10,
                2,
                preferred_time="09:00",
                due_date=TODAY + timedelta(days=1),
            )
        )
        luna.add_task(
            make_task("Now", "other", 10, 2, preferred_time="09:00", due_date=TODAY)
        )
        assert Scheduler(owner, plan_date=TODAY).detect_conflicts() == []

    def test_detect_conflicts_with_no_tasks_returns_empty_list(self):
        owner, _, _ = _owner_with_pets()
        assert Scheduler(owner, plan_date=TODAY).detect_conflicts() == []
        assert Scheduler(Owner("Empty", 60), plan_date=TODAY).detect_conflicts() == []


class TestPlanGeneration:
    """Scheduler.generate_plan: budget, placement, skips and edge cases."""

    def test_future_task_not_scheduled_today(self):
        owner, mochi, _ = _owner_with_pets()
        today = date(2026, 10, 19)
        mochi.add_task(
            make_task("Later", "other", 10, 3, due_date=today + timedelta(days=1))
        )
        scheduler = Scheduler(owner, plan_date=today)
        scheduler.generate_plan()
        assert scheduler.scheduled_items == []

    def test_generate_plan_twice_does_not_duplicate(self):
        owner, mochi, _ = _owner_with_pets()
        mochi.add_task(make_task("Walk", "exercise", 20, 3))
        scheduler = _plan(owner)
        scheduler.generate_plan()
        assert len(scheduler.scheduled_items) == 1

    def test_empty_owner_and_zero_budget(self):
        assert _plan(Owner("Empty", 60)).scheduled_items == []
        owner = Owner("Busy", 0)
        pet = Pet("Mochi", "dog")
        owner.add_pet(pet)
        pet.add_task(make_task("Walk", "exercise", 10, 3))
        scheduler = _plan(owner)
        assert scheduler.scheduled_items == [] and len(scheduler.skipped_tasks) == 1
        assert scheduler.get_summary()["minutes_remaining"] == 0

    def test_budget_boundary_exact_fit_and_one_over(self):
        owner = Owner("Jordan", 30)
        pet = Pet("Mochi", "dog")
        owner.add_pet(pet)
        pet.add_task(make_task("Exact", "other", 30, 3))
        assert len(_plan(owner).scheduled_items) == 1
        owner.available_minutes = 29
        assert len(_plan(owner).skipped_tasks) == 1

    def test_skipped_big_task_does_not_block_smaller_ones(self):
        owner = Owner("Jordan", 30)
        pet = Pet("Mochi", "dog")
        owner.add_pet(pet)
        pet.add_task(make_task("Big", "other", 60, 3))
        pet.add_task(make_task("Small", "other", 10, 1))
        scheduler = _plan(owner)
        assert [i.task.title for i in scheduler.scheduled_items] == ["Small"]
        assert [i.task.title for i in scheduler.skipped_tasks] == ["Big"]
        assert "Skipped" in scheduler.skipped_tasks[0].reason

    def test_untimed_task_fills_gap_before_fixed_task(self):
        owner, mochi, _ = _owner_with_pets()
        mochi.add_task(make_task("Fixed", "other", 30, 3, preferred_time="09:00"))
        mochi.add_task(make_task("Floating", "other", 30, 2))
        starts = {i.task.title: i.start_time for i in _plan(owner).scheduled_items}
        assert starts == {"Floating": "08:00", "Fixed": "09:00"}

    def test_conflicting_tasks_are_not_double_booked_in_plan(self):
        owner, mochi, luna = _owner_with_pets()
        mochi.add_task(make_task("Walk", "exercise", 30, 3, preferred_time="08:00"))
        luna.add_task(make_task("Feed", "food", 10, 3, preferred_time="08:00"))
        items = _plan(owner).scheduled_items
        assert len(items) == 2
        first, second = items
        assert int(second.start_time[:2]) * 60 + int(second.start_time[3:]) >= (
            int(first.start_time[:2]) * 60
            + int(first.start_time[3:])
            + first.task.duration_minutes
        )
        assert "moved to" in second.reason

    def test_plan_start_times_are_always_valid_clock_times(self):
        """A chain of late tasks must not produce times like '24:30'."""
        owner, mochi, _ = _owner_with_pets()
        mochi.add_task(make_task("A", "other", 60, 3, preferred_time="23:30"))
        mochi.add_task(make_task("B", "other", 10, 3, preferred_time="23:45"))
        for item in _plan(owner).scheduled_items:
            hours = int(item.start_time[:2])
            assert 0 <= hours < 24, f"invalid start time {item.start_time}"

    def test_task_that_would_run_past_midnight_is_skipped_with_reason(self):
        owner, mochi, _ = _owner_with_pets()
        mochi.add_task(
            make_task("A", "other", 30, 3, preferred_time="23:30")
        )  # ends exactly 24:00
        mochi.add_task(
            make_task("B", "other", 10, 3, preferred_time="23:45")
        )  # pushed to 24:00
        scheduler = _plan(owner)
        assert [i.task.title for i in scheduler.scheduled_items] == ["A"]
        assert [i.task.title for i in scheduler.skipped_tasks] == ["B"]
        assert "midnight" in scheduler.skipped_tasks[0].reason

    def test_invalid_day_start_gives_clear_error(self):
        owner, mochi, _ = _owner_with_pets()
        owner.preferences["day_start"] = "8am"
        mochi.add_task(make_task("Walk", "exercise", 20, 3))
        with pytest.raises(ValueError):
            _plan(owner)


class TestTaskValidation:
    """Task rejects invalid fields when it is created."""

    @pytest.mark.parametrize("duration", [0, -5, 1.5, "10", None])
    def test_invalid_duration_rejected(self, duration):
        with pytest.raises(ValueError):
            make_task("T", "other", duration, 1)

    @pytest.mark.parametrize("priority", [0, 4, "high", None])
    def test_invalid_priority_rejected(self, priority):
        with pytest.raises(ValueError):
            make_task("T", "other", 5, priority)

    def test_invalid_frequency_rejected(self):
        with pytest.raises(ValueError):
            make_task("T", "other", 5, 1, frequency="monthly")

    @pytest.mark.parametrize("bad", ["25:00", "12:60", "", "07:30:00", "noon"])
    def test_invalid_preferred_time_rejected(self, bad):
        with pytest.raises(ValueError):
            make_task("T", "other", 5, 1, preferred_time=bad)

    def test_unpadded_time_is_rejected(self):
        with pytest.raises(ValueError):
            make_task("Walk", "exercise", 10, 1, preferred_time="7:30")


class TestTaskEdit:
    """Task.edit validates, rolls back, and protects system-managed fields."""

    def test_edit_rolls_back_when_any_value_is_invalid(self):
        task = make_task("T", "other", 10, 2, preferred_time="08:00")
        with pytest.raises(ValueError):
            task.edit(duration_minutes=20, preferred_time="8:00")
        assert task.duration_minutes == 10 and task.preferred_time == "08:00"

    def test_edit_unknown_field_raises(self):
        with pytest.raises(AttributeError):
            make_task("T", "other", 10, 2).edit(colour="red")

    def test_edit_cannot_set_completed_directly(self):
        _, mochi, _ = _owner_with_pets()
        walk = make_task("Walk", "exercise", 20, 3)
        mochi.add_task(walk)
        with pytest.raises(ValueError, match="mark_complete"):
            walk.edit(completed=True)
        assert walk.completed is False and len(mochi.tasks) == 1

    @pytest.mark.parametrize("field_name", ["pet", "pet_name"])
    def test_edit_cannot_change_ownership_fields(self, field_name):
        _, mochi, _ = _owner_with_pets()
        walk = make_task("Walk", "exercise", 20, 3)
        mochi.add_task(walk)
        with pytest.raises(ValueError):
            walk.edit(**{field_name: None})
        assert walk.pet is mochi and walk.pet_name == "Mochi"

    def test_edit_with_managed_and_valid_fields_changes_nothing(self):
        walk = make_task("Walk", "exercise", 20, 3)
        with pytest.raises(ValueError):
            walk.edit(duration_minutes=45, completed=True)
        assert walk.duration_minutes == 20 and walk.completed is False


class TestPetOwnership:
    """Pets own their tasks: one Task object belongs to one pet."""

    def test_adding_task_increases_pet_task_count(self):
        pet = Pet(name="Mochi", species="dog")
        assert len(pet.tasks) == 0

        pet.add_task(make_task("Morning walk", "exercise", 30, priority=3))
        assert len(pet.tasks) == 1

        pet.add_task(make_task("Feeding", "food", 10, priority=3))
        assert len(pet.tasks) == 2

    def test_adding_same_task_twice_is_ignored(self):
        _, mochi, _ = _owner_with_pets()
        task = make_task("T", "other", 5, 1)
        mochi.add_task(task)
        mochi.add_task(task)
        assert len(mochi.tasks) == 1

    def test_remove_missing_task_or_pet_raises(self):
        owner, mochi, _ = _owner_with_pets()
        with pytest.raises(ValueError):
            mochi.remove_task(make_task("Ghost", "other", 5, 1))
        with pytest.raises(ValueError):
            owner.remove_pet(Pet("Ghost", "cat"))

    def test_same_task_object_cannot_be_added_to_two_pets(self):
        _, mochi, luna = _owner_with_pets()
        walk = make_task("Walk", "exercise", 20, 3)
        mochi.add_task(walk)
        with pytest.raises(ValueError):
            luna.add_task(walk)
        assert luna.tasks == [] and walk.pet is mochi

    def test_constructor_rejects_task_owned_by_another_pet(self):
        _, mochi, _ = _owner_with_pets()
        walk = make_task("Walk", "exercise", 20, 3)
        mochi.add_task(walk)
        with pytest.raises(ValueError):
            Pet("Rex", "dog", tasks=[walk])

    def test_task_can_move_after_remove(self):
        _, mochi, luna = _owner_with_pets()
        walk = make_task("Walk", "exercise", 20, 3)
        mochi.add_task(walk)
        mochi.remove_task(walk)
        luna.add_task(walk)
        assert walk.pet is luna and mochi.tasks == []

    def test_each_pet_can_have_its_own_identical_task(self):
        _, mochi, luna = _owner_with_pets()
        a = make_task("Grooming", "grooming", 30, 2, frequency="weekly")
        b = make_task("Grooming", "grooming", 30, 2, frequency="weekly")
        mochi.add_task(a)
        luna.add_task(b)
        nxt = a.mark_complete(today=TODAY)
        assert nxt in mochi.tasks and nxt not in luna.tasks
        assert b.completed is False and len(luna.tasks) == 1
