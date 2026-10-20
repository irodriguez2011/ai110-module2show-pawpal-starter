import streamlit as st

from pawpal_system import FREQUENCIES, PRIORITY_LABELS, Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown("""
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
""")

with st.expander("Scenario", expanded=True):
    st.markdown("""
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
""")

with st.expander("What you need to build", expanded=True):
    st.markdown("""
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
""")

st.divider()

# Derived from the backend so the UI can't drift from the scheduler's levels.
PRIORITY_NAMES = PRIORITY_LABELS
PRIORITY_VALUES = {name: value for value, name in PRIORITY_LABELS.items()}
CATEGORIES = ["exercise", "food", "health", "grooming", "enrichment", "other"]

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
                    "Priority": PRIORITY_NAMES[t.priority],
                    "Preferred time": t.preferred_time or "-",
                    "Repeats": t.frequency,
                    "Due": t.due_date.isoformat(),
                    "Done": "yes" if t.completed else "no",
                }
                for t in visible
            ]
        )
    else:
        st.info("No tasks match these filters.")

    pending = owner.filter_tasks(status=False)
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

    for warning in Scheduler(owner).detect_conflicts():
        st.warning(warning)
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

        st.success(
            f"{summary['tasks_scheduled']} scheduled, {summary['tasks_skipped']} skipped "
            f"| {summary['minutes_scheduled']} of {summary['available_minutes']} min used"
        )
        if scheduler.scheduled_items:
            st.table(
                [
                    {
                        "Time": item.start_time,
                        "Task": item.task.title,
                        "Pet": item.task.pet_name,
                        "Duration (min)": item.task.duration_minutes,
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
