from pawpal_system import Owner, Pet, Scheduler, Task


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

    scheduler = Scheduler(owner)
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
