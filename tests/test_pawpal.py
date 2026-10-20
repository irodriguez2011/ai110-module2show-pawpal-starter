from pawpal_system import Pet, Task


def test_mark_complete_changes_task_status():
    task = Task("Morning walk", "exercise", 30, priority=3)
    assert task.completed is False

    task.mark_complete()

    assert task.completed is True


def test_adding_task_increases_pet_task_count():
    pet = Pet(name="Mochi", species="dog")
    assert len(pet.tasks) == 0

    pet.add_task(Task("Morning walk", "exercise", 30, priority=3))
    assert len(pet.tasks) == 1

    pet.add_task(Task("Feeding", "food", 10, priority=3))
    assert len(pet.tasks) == 2


# --- sorting, filtering, recurrence, conflicts ---
from datetime import date, timedelta

from pawpal_system import Owner, Scheduler


def _owner_with_pets():
    owner = Owner(name="Jordan", available_minutes=240)
    mochi, luna = Pet("Mochi", "dog"), Pet("Luna", "cat")
    owner.add_pet(mochi)
    owner.add_pet(luna)
    return owner, mochi, luna


def test_sort_by_time_puts_untimed_last():
    a = Task("B", "other", 5, 1, preferred_time="09:00")
    b = Task("A", "other", 5, 1, preferred_time="07:30")
    c = Task("C", "other", 5, 1)
    assert Scheduler.sort_by_time([a, c, b]) == [b, a, c]


def test_filter_tasks_by_pet_and_status():
    owner, mochi, luna = _owner_with_pets()
    walk = Task("Walk", "exercise", 20, 3)
    feed = Task("Feed", "food", 5, 3)
    mochi.add_task(walk)
    luna.add_task(feed)
    next_walk = walk.mark_complete()  # also adds tomorrow's walk to Mochi
    assert owner.filter_tasks(pet_name="Mochi") == [walk, next_walk]
    assert owner.filter_tasks(pet_name="Mochi", status=True) == [walk]
    assert owner.filter_tasks(status=False) == [next_walk, feed]
    assert owner.filter_tasks(pet_name="Luna", status=True) == []


def test_completing_daily_task_creates_next_day_task():
    _, mochi, _ = _owner_with_pets()
    walk = Task("Walk", "exercise", 20, 3, frequency="daily", due_date=date(2020, 1, 1))
    mochi.add_task(walk)
    nxt = mochi.complete_task(walk)
    assert walk.completed and not nxt.completed
    assert nxt.due_date == date.today() + timedelta(days=1)  # today + 1, not old due + 1
    assert nxt in mochi.tasks and nxt.pet_name == "Mochi"


def test_completing_weekly_task_moves_a_week():
    bath = Task("Bath", "grooming", 30, 2, frequency="weekly")
    assert bath.next_occurrence(today=date(2026, 10, 19)).due_date == date(2026, 10, 26)


def test_next_occurrence_crosses_month_boundary():
    walk = Task("Walk", "exercise", 20, 3, frequency="daily")
    assert walk.next_occurrence(today=date(2026, 10, 31)).due_date == date(2026, 11, 1)


def test_future_task_not_scheduled_today():
    owner, mochi, _ = _owner_with_pets()
    today = date(2026, 10, 19)
    mochi.add_task(Task("Later", "other", 10, 3, due_date=today + timedelta(days=1)))
    scheduler = Scheduler(owner, plan_date=today)
    scheduler.generate_plan()
    assert scheduler.scheduled_items == []


def test_detect_conflicts_across_pets():
    owner, mochi, luna = _owner_with_pets()
    mochi.add_task(Task("Walk", "exercise", 30, 3, preferred_time="08:00"))
    luna.add_task(Task("Pill", "health", 5, 3, preferred_time="08:15"))
    warnings = Scheduler(owner).detect_conflicts()
    assert len(warnings) == 1 and "Pill" in warnings[0] and "Walk" in warnings[0]


def test_detect_conflicts_none_when_back_to_back():
    owner, mochi, luna = _owner_with_pets()
    mochi.add_task(Task("Walk", "exercise", 30, 3, preferred_time="08:00"))
    luna.add_task(Task("Pill", "health", 5, 3, preferred_time="08:30"))
    assert Scheduler(owner).detect_conflicts() == []


def test_detect_conflicts_catches_overlap_with_long_earlier_task():
    owner, mochi, luna = _owner_with_pets()
    mochi.add_task(Task("Long", "exercise", 120, 3, preferred_time="08:00"))
    mochi.add_task(Task("Short", "other", 10, 3, preferred_time="08:30"))
    luna.add_task(Task("Late", "other", 10, 3, preferred_time="09:00"))
    assert len(Scheduler(owner).detect_conflicts()) == 2


def test_unpadded_time_is_rejected():
    import pytest

    with pytest.raises(ValueError):
        Task("Walk", "exercise", 10, 1, preferred_time="7:30")


def test_sort_by_time_orders_hhmm_strings():
    tasks = [Task(str(t), "other", 5, 1, preferred_time=t) for t in ("18:00", "07:30", "09:05")]
    assert [t.preferred_time for t in Scheduler.sort_by_time(tasks)] == ["07:30", "09:05", "18:00"]


def test_mark_complete_automatically_adds_next_occurrence():
    _, mochi, _ = _owner_with_pets()
    walk = Task("Walk", "exercise", 20, 3, frequency="daily")
    mochi.add_task(walk)
    nxt = walk.mark_complete()
    assert len(mochi.tasks) == 2 and nxt in mochi.tasks
    assert nxt.due_date == date.today() + timedelta(days=1) and not nxt.completed


def test_mark_complete_twice_does_not_duplicate():
    _, mochi, _ = _owner_with_pets()
    walk = Task("Walk", "exercise", 20, 3)
    mochi.add_task(walk)
    walk.mark_complete()
    assert walk.mark_complete() is None
    assert len(mochi.tasks) == 2


def test_removed_task_no_longer_spawns_into_pet():
    _, mochi, _ = _owner_with_pets()
    walk = Task("Walk", "exercise", 20, 3)
    mochi.add_task(walk)
    mochi.remove_task(walk)
    walk.mark_complete()
    assert mochi.tasks == []


def test_same_time_same_pet_warns_without_crashing():
    owner, mochi, _ = _owner_with_pets()
    mochi.add_task(Task("Walk", "exercise", 20, 3, preferred_time="09:00"))
    mochi.add_task(Task("Vet call", "health", 15, 2, preferred_time="09:00"))
    warnings = Scheduler(owner).detect_conflicts()
    assert len(warnings) == 1
    assert "same pet: Mochi" in warnings[0] and "same time" in warnings[0]


def test_same_time_different_pets_warns():
    owner, mochi, luna = _owner_with_pets()
    mochi.add_task(Task("Walk", "exercise", 20, 3, preferred_time="09:00"))
    luna.add_task(Task("Pill", "health", 5, 3, preferred_time="09:00"))
    warnings = Scheduler(owner).detect_conflicts()
    assert len(warnings) == 1 and "different pets" in warnings[0]
