# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🛠️ Implementation Summary

PawPal+ is a Python backend (`pawpal_system.py`) that turns an owner's pets and care tasks into a daily plan, with a reason for every task it schedules or skips. `main.py` is a command-line demo, and `tests/` holds the pytest suite. A UML class diagram is in `diagrams/`.

### How the classes work together

```
Owner ──has──> Pet ──has──> Task
  ▲
  └── Scheduler ──produces──> ScheduledItem ──wraps──> Task
```

- **Task** is one care activity: title, category, duration, priority (1–3), optional preferred time, frequency and completion status. It validates itself when created and can be edited or marked complete.
- **Pet** holds the pet's details and its own list of tasks. Adding a task tags it with the pet's name, so a plan can say "Walk (Mochi)".
- **Owner** holds the daily time budget (`available_minutes`) and preferences, and manages multiple pets. `get_all_tasks()` returns every pet's tasks in one list.
- **Scheduler** is the brain. It reads tasks only through `owner.get_all_tasks()`, never from a single pet, so one plan covers all pets.
- **ScheduledItem** is one line of the plan: a task, its start time and the reason it was scheduled or skipped.

### How a plan is built

1. Collect all pending tasks across every pet that are due on or before the plan date.
2. Sort by priority (high first), then earlier preferred time, then shorter duration.
3. Fit tasks into the owner's available minutes. A task that doesn't fit is skipped with a reason, and smaller ones are still tried.
4. Place tasks with a preferred time at that time, moving one back if it overlaps another. The rest go in the earliest free gap from the day's start.
5. `explain_plan()` and `get_summary()` report the result.

Run the demo with `python main.py`, and the tests with `pytest`.

## 🖥️ Sample Output

Output from running the demo script (`python main.py`). One owner with two pets (Mochi and Luna) and five tasks, all combined into a single plan:

```
Today's Schedule for Jordan (Sunday, October 18)
============================================================
07:30 - Morning walk (Mochi), 30 min: High priority; scheduled at its preferred time 07:30.
08:15 - Thyroid pill (Luna), 5 min: High priority; scheduled at its preferred time 08:15.
08:20 - Grooming (Mochi), 45 min: Low priority; no preferred time, placed in the first free slot.
12:30 - Laser pointer play (Luna), 20 min: Medium priority; scheduled at its preferred time 12:30.
18:00 - Feeding (Luna), 10 min: High priority; scheduled at its preferred time 18:00.
------------------------------------------------------------
5 scheduled, 0 skipped | 110 of 120 min used
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```

## 📐 Smarter Scheduling

Four features go beyond the basic plan. Each one lives in `pawpal_system.py`, is shown in `main.py`, and is covered by tests in `tests/test_pawpal.py`.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Sorting | `Scheduler.sort_by_time()`, `Scheduler.generate_plan()` | Orders tasks by time, or by priority when building a plan |
| Filtering | `Owner.filter_tasks()`, `Pet.get_tasks()` | By pet name, completion status, and/or category |
| Conflict detection | `Scheduler.detect_conflicts()` | Returns warnings for overlapping preferred times; never raises |
| Recurring tasks | `Task.mark_complete()`, `Task.next_occurrence()`, `Pet.complete_task()` | Completing a daily or weekly task creates the next one automatically |

### Sorting

- **`Scheduler.sort_by_time(tasks)`** returns a new list ordered by `preferred_time`, earliest first. Tasks without a time go last. It sorts the `"HH:MM"` strings directly with a lambda (`key=lambda t: t.preferred_time or "99:99"`), which gives chronological order because `Task` only accepts zero-padded times (`"07:30"`, not `"7:30"`). The sort is stable, so tasks with the same time keep their original order.
- **`Scheduler.generate_plan()`** sorts differently: highest priority first, then earlier preferred time, then shorter duration. That order decides which tasks fit in the owner's available minutes.

### Filtering

- **`Owner.filter_tasks(pet_name=None, status=None, category=None)`** returns tasks across all pets. Any filter left as `None` is ignored, so you can filter by pet, by status (`True` = completed, `False` = pending), by category, or any combination.
- **`Pet.get_tasks(status=None, category=None)`** does the same for a single pet, and `filter_tasks` builds on it.
- In the Streamlit app, the task table has "Show pet" and "Show status" dropdowns, and rows are shown sorted by time.

### Conflict detection

- **`Scheduler.detect_conflicts()`** looks at due tasks that have a preferred time. Each task occupies the window from its preferred time to that time plus its duration. Tasks are sorted by start time, and each is compared with the task that ends latest so far, so a task that overlaps an earlier long task is still caught.
- It works across pets and within one pet. Each warning says whether the clash is between the `same pet` or `different pets`, and whether the tasks start at the `same time` or only `overlap`.
- It returns a list of warning strings (empty if there are none) instead of raising, so the program keeps running. The app shows each one with `st.warning`.
- It only checks preferred times. `generate_plan()` still resolves overlaps by moving the later task back, and says so in its "Why" text.

```
WARNING (different pets: Luna and Mochi) - same time: 'Laser pointer play' at 12:30 conflicts with 'Medication' at 12:30 (runs until 12:35).
WARNING (same pet: Mochi) - same time: 'Vet call' at 17:00 conflicts with 'Evening walk' at 17:00 (runs until 17:25).
```

### Recurring tasks

- **`Task.mark_complete()`** marks the task done and creates its next occurrence. If the task belongs to a pet, the new task is added to that pet automatically. It returns the new task, or `None` if the task was already complete, so completing twice never creates duplicates.
- **`Task.next_occurrence(today=None)`** builds a fresh, pending copy due `today + timedelta(days=1)` for `"daily"` tasks or `today + timedelta(weeks=1)` for `"weekly"` ones. It counts from today, not the old due date, so a task finished late is never overdue the moment it is created.
- **`Pet.complete_task(task)`** checks that the task belongs to the pet, then calls `mark_complete()`. The "Mark done" button in the app uses it.
- Each task has a `due_date`, and **`Scheduler.generate_plan()`** only includes pending tasks that are due on or before the plan date, so a weekly task does not show up every day.

Run `python main.py` to see all four in the terminal.

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
