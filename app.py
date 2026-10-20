import streamlit as st

from pawpal_system import FREQUENCIES, PRIORITY_LABELS, Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    "Welcome! PawPal+ helps you keep up with your pets' care. Tell it how much "
    "time you have today, add your pets and their tasks, and it builds a plan "
    "that fits your day, starting with what matters most."
)

with st.expander("How it works", expanded=True):
    st.markdown("""
1. **Set your time** - how many minutes you have for pet care today.
2. **Add your pets** - and give each one the tasks it needs: walks, meals, meds, grooming.
3. **Generate your schedule** - the highest-priority tasks go in first, and you'll
   see why each task was scheduled or left out.

Tasks can repeat daily or weekly, or happen just once. If two tasks overlap,
PawPal+ lets you know and moves the later one to the next free slot.
""")

st.divider()

# Derived from the backend so the UI can't drift from the scheduler's levels.
PRIORITY_NAMES = PRIORITY_LABELS
PRIORITY_VALUES = {name: value for value, name in PRIORITY_LABELS.items()}
CATEGORIES = ["exercise", "food", "health", "grooming", "enrichment", "other"]

PRIORITY_BADGES = {1: "🟢 low", 2: "🟡 medium", 3: "🔴 high"}


def show_conflicts(scheduler: Scheduler) -> None:
    """Show scheduler conflicts as yellow warnings, or a green all-clear.

    A conflict isn't a failure (the planner moves the later task), so it is a
    warning, not an error; red is kept for rejected input.
    """
    conflicts = scheduler.detect_conflicts()
    if not conflicts:
        if any(t.preferred_time for t in owner.get_all_tasks()):
            st.success("No time conflicts between your tasks.")
        return
    count = len(conflicts)
    st.warning(
        f"**{count} scheduling conflict{'s' if count != 1 else ''}** - "
        "overlapping tasks are still planned, but the later one is moved to the "
        "next free slot. Change a preferred time to keep it where you want it.",
        icon="⚠️",
    )
    for message in conflicts:
        st.warning(message.removeprefix("WARNING "), icon="🕒")


# The "vault": create the Owner once per browser session, then reuse it on every rerun.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan", available_minutes=120)
owner = st.session_state.owner

st.subheader("Owner")
col1, col2 = st.columns(2)
with col1:
    owner.name = st.text_input("Owner name", value=owner.name)
with col2:
    owner.available_minutes = int(
        st.number_input(
            "Time available today (minutes)",
            min_value=1,
            max_value=1440,
            value=owner.available_minutes,
        )
    )

st.subheader("Pets")
col1, col2 = st.columns(2)
with col1:
    pet_name = st.text_input("Pet name", value="Mochi")
with col2:
    species = st.selectbox("Species", ["dog", "cat", "other"])

if st.button("Add pet"):
    clean_name = pet_name.strip()
    if not clean_name:
        st.error("Give your pet a name.")
    elif any(p.name.lower() == clean_name.lower() for p in owner.pets):
        st.warning(f"You already have a pet named {clean_name}.")
    else:
        owner.add_pet(Pet(name=clean_name, species=species))

if owner.pets:
    st.write("Your pets: " + ", ".join(f"{p.name} ({p.species})" for p in owner.pets))
else:
    st.info("No pets yet. Add one above.")

st.markdown("### Tasks")
if not owner.pets:
    st.caption("Add a pet first, then you can give it tasks.")
else:
    pet_choice = st.selectbox("Pet", [p.name for p in owner.pets])

    col1, col2, col3 = st.columns(3)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration = st.number_input(
            "Duration (minutes)", min_value=1, max_value=240, value=20
        )
    with col3:
        priority = st.selectbox("Priority", list(PRIORITY_VALUES), index=2)

    col1, col2 = st.columns(2)
    with col1:
        category = st.selectbox("Category", CATEGORIES)
    with col2:
        preferred_time = st.text_input("Preferred time (HH:MM, optional)", value="")
        frequency = st.selectbox("Repeats", FREQUENCIES, index=FREQUENCIES.index("daily"))

    if st.button("Add task"):
        pet = next(p for p in owner.pets if p.name == pet_choice)
        try:
            pet.add_task(
                Task(
                    title=task_title.strip(),
                    category=category,
                    duration_minutes=int(duration),
                    priority=PRIORITY_VALUES[priority],
                    preferred_time=preferred_time.strip() or None,
                    frequency=frequency,
                )
            )
        except ValueError as error:
            st.error(str(error))

all_tasks = owner.get_all_tasks()
if all_tasks:
    st.write("Current tasks:")
    col1, col2 = st.columns(2)
    with col1:
        pet_filter = st.selectbox("Show pet", ["All"] + [p.name for p in owner.pets])
    with col2:
        status_filter = st.selectbox("Show status", ["All", "Pending", "Completed"])
    visible = owner.filter_tasks(
        pet_name=None if pet_filter == "All" else pet_filter,
        status={"All": None, "Pending": False, "Completed": True}[status_filter],
    )
    visible = Scheduler.sort_by_time(visible)
    if visible:
        st.table(
            [
                {
                    "Pet": t.pet_name,
                    "Task": t.title,
                    "Category": t.category,
                    "Duration (min)": t.duration_minutes,
                    "Priority": PRIORITY_BADGES[t.priority],
                    "Preferred time": t.preferred_time or "-",
                    "Repeats": t.frequency,
                    "Due": t.due_date.isoformat(),
                    "Status": "✅ done" if t.completed else "⏳ pending",
                }
                for t in visible
            ]
        )
    else:
        st.info("No tasks match these filters.")

    pending = Scheduler.sort_by_time(owner.filter_tasks(status=False))
    if pending:
        to_complete = st.selectbox(
            "Mark a task done",
            range(len(pending)),
            format_func=lambda i: f"{pending[i].pet_name}: {pending[i].title} ({pending[i].due_date})",
        )
        if st.button("Mark done"):
            task = pending[to_complete]
            pet = next(p for p in owner.pets if p.name == task.pet_name)
            upcoming = pet.complete_task(task)
            if upcoming:
                st.success(f"Done! Next '{task.title}' is due {upcoming.due_date}.")
            st.rerun()

    show_conflicts(Scheduler(owner))
elif owner.pets:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("Fits your tasks into your available time, highest priority first.")

if st.button("Generate schedule"):
    if not all_tasks:
        st.warning("Add at least one task first.")
    else:
        scheduler = Scheduler(owner)
        scheduler.generate_plan()
        summary = scheduler.get_summary()

        if summary["tasks_skipped"] == 0 and summary["tasks_scheduled"]:
            st.success("Everything due today fits in your available time.")
        elif summary["tasks_skipped"]:
            st.warning(
                f"{summary['tasks_skipped']} task(s) didn't fit and stay pending "
                "for the next plan."
            )
        col1, col2, col3 = st.columns(3)
        col1.metric("Scheduled", summary["tasks_scheduled"])
        col2.metric("Skipped", summary["tasks_skipped"])
        col3.metric(
            "Time used",
            f"{summary['minutes_scheduled']} / {summary['available_minutes']} min",
        )
        show_conflicts(scheduler)
        if scheduler.scheduled_items:
            st.table(
                [
                    {
                        "Time": item.start_time,
                        "Task": item.task.title,
                        "Pet": item.task.pet_name,
                        "Duration (min)": item.task.duration_minutes,
                        "Priority": PRIORITY_BADGES[item.task.priority],
                        "Why": item.reason,
                    }
                    for item in scheduler.scheduled_items
                ]
            )
        if scheduler.skipped_tasks:
            st.write("Skipped:")
            st.table(
                [
                    {
                        "Task": item.task.title,
                        "Pet": item.task.pet_name,
                        "Why": item.reason,
                    }
                    for item in scheduler.skipped_tasks
                ]
            )

        with st.expander("Plan explanation"):
            for line in scheduler.explain_plan():
                st.write(f"- {line}")
