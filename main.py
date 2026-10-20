from pawpal_system import Owner, Pet, Scheduler, Task


def show(label: str, tasks: list[Task]) -> None:
    """Print a labelled list of tasks, one per line."""
    print(f"\n{label}")
    if not tasks:
        print("  (none)")
    for t in tasks:
        done = "done" if t.completed else "pending"
        print(f"  {t.preferred_time or '--:--'}  {t.title:<20} {t.pet_name:<6} {done:<8} due {t.due_date}")


def main() -> None:
    owner = Owner(name="Jordan", available_minutes=120, preferences={"day_start": "07:30"})

    mochi = Pet(name="Mochi", species="dog", breed="Corgi", age=4)
    luna = Pet(name="Luna", species="cat", age=2, special_needs="daily thyroid pill")
    owner.add_pet(mochi)
    owner.add_pet(luna)

    mochi.add_task(Task("Morning walk", "exercise", 30, priority=3, preferred_time="07:30"))
    mochi.add_task(Task("Grooming", "grooming", 45, priority=1))
    luna.add_task(Task("Thyroid pill", "health", 5, priority=3, preferred_time="08:15"))
    luna.add_task(Task("Feeding", "food", 10, priority=3, preferred_time="18:00"))
    luna.add_task(Task("Laser pointer play", "enrichment", 20, priority=2, preferred_time="12:30"))

    # Tasks above were added out of time order on purpose.
    mochi.add_task(Task("Evening walk", "exercise", 25, priority=2, preferred_time="17:00"))
    luna.add_task(Task("Brush fur", "grooming", 10, priority=1))
    # Two deliberate clashes: same pet (Mochi) and different pets (Mochi vs Luna).
    mochi.add_task(Task("Vet call", "health", 15, priority=2, preferred_time="17:00"))
    mochi.add_task(Task("Medication", "health", 5, priority=3, preferred_time="12:30"))
    mochi.tasks[0].mark_complete()  # complete "Morning walk"
    luna.tasks[1].mark_complete()  # complete "Feeding"

    scheduler = Scheduler(owner)

    print("=" * 60)
    print("Sorting and filtering demo")
    show("All tasks, in insertion order:", owner.get_all_tasks())
    show("All tasks, sorted by time:", Scheduler.sort_by_time(owner.get_all_tasks()))
    show("Mochi's tasks:", owner.filter_tasks(pet_name="Mochi"))
    show("Pending tasks:", owner.filter_tasks(status=False))
    show("Completed tasks:", owner.filter_tasks(status=True))
    show(
        "Luna's pending tasks, sorted:",
        Scheduler.sort_by_time(owner.filter_tasks(pet_name="Luna", status=False)),
    )
    print()

    conflicts = scheduler.detect_conflicts()
    print(f"Conflict check: {len(conflicts)} warning(s)")
    for warning in conflicts:
        print(f"  {warning}")
    print()

    scheduler.generate_plan()

    print(f"Today's Schedule for {owner.name} ({scheduler.date:%A, %B %d})")
    print("=" * 60)
    for line in scheduler.explain_plan():
        print(line)

    summary = scheduler.get_summary()
    print("-" * 60)
    print(
        f"{summary['tasks_scheduled']} scheduled, {summary['tasks_skipped']} skipped | "
        f"{summary['minutes_scheduled']} of {summary['available_minutes']} min used"
    )


if __name__ == "__main__":
    main()
