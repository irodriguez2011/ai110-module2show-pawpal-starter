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

## ✨ Features

- **Priority-based planning:** tasks are ordered by priority (high first), then earlier preferred time, then shorter duration, and added until the owner's available minutes run out. This is a greedy approach, so it is fast and predictable but not guaranteed to pack the day perfectly.
- **Time-budget fitting:** a task that doesn't fit is skipped with a reason, and smaller tasks after it are still tried, so one long task doesn't block the rest.
- **Sorting by time:** `Scheduler.sort_by_time()` orders tasks by preferred time with untimed tasks last. It is stable, so ties keep their original order, and it never changes the original list.
- **Filtering:** view tasks by pet, by completion status, by category, or any combination.
- **Conflict warnings:** `Scheduler.detect_conflicts()` finds tasks whose time windows (start to start plus duration) overlap, across pets or within one pet. Each warning says whether the tasks start at the same time or only overlap, and it never raises, so the app can show the warning and keep going. It checks preferred times only.
- **Automatic conflict resolution:** when the plan is built, an overlapping task is moved back to the next free moment, and its "Why" text says it was moved.
- **First-free-slot placement:** tasks without a preferred time go into the earliest gap, starting from the day's start time (08:00 by default, configurable through the owner's `day_start` preference).
- **Midnight guard:** a task that would run past 24:00 is skipped with a reason instead of getting an invalid time.
- **Daily, weekly and one-off recurrence:** completing a daily or weekly task creates the next one on the same pet. The next due date steps from the original due date, so a weekly Monday task stays on Mondays even when finished late, and it is never created already overdue. One-off (`once`) tasks don't repeat, and completing a task twice never creates duplicates.
- **Due-date awareness and carry-over:** a plan includes pending tasks due on or before the plan date, so future tasks wait their turn and unfinished tasks carry over to the next plan.
- **Plan explanations:** every scheduled or skipped task has a plain-language reason, shown in the app and by `explain_plan()`.
- **Input validation:** durations, priorities, frequencies and times (strict zero-padded `HH:MM`) are checked when a task is created. An `edit()` that fails leaves the task unchanged.
- **One Task per pet:** each pet owns its own Task objects, so two pets can both need grooming and complete it independently.

The algorithms are described in more detail under [Smarter Scheduling](#-smarter-scheduling).

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

Output from running the demo script (`python main.py`). One owner with two pets (Mochi and Luna) and nine tasks: it shows the tasks sorted and filtered, the conflict warnings, and the final plan, which moves two overlapping tasks and skips one that doesn't fit. Dates follow the day the script is run.

```
============================================================
Sorting and filtering demo

All tasks, in insertion order:
  07:30  Morning walk         Mochi  done     due 2026-10-19
  --:--  Grooming             Mochi  pending  due 2026-10-19
  17:00  Evening walk         Mochi  pending  due 2026-10-19
  17:00  Vet call             Mochi  pending  due 2026-10-19
  12:30  Medication           Mochi  pending  due 2026-10-19
  07:30  Morning walk         Mochi  pending  due 2026-10-20
  08:15  Thyroid pill         Luna   pending  due 2026-10-19
  18:00  Feeding              Luna   done     due 2026-10-19
  12:30  Laser pointer play   Luna   pending  due 2026-10-19
  --:--  Brush fur            Luna   pending  due 2026-10-19
  18:00  Feeding              Luna   pending  due 2026-10-20

All tasks, sorted by time:
  07:30  Morning walk         Mochi  done     due 2026-10-19
  07:30  Morning walk         Mochi  pending  due 2026-10-20
  08:15  Thyroid pill         Luna   pending  due 2026-10-19
  12:30  Medication           Mochi  pending  due 2026-10-19
  12:30  Laser pointer play   Luna   pending  due 2026-10-19
  17:00  Evening walk         Mochi  pending  due 2026-10-19
  17:00  Vet call             Mochi  pending  due 2026-10-19
  18:00  Feeding              Luna   done     due 2026-10-19
  18:00  Feeding              Luna   pending  due 2026-10-20
  --:--  Grooming             Mochi  pending  due 2026-10-19
  --:--  Brush fur            Luna   pending  due 2026-10-19

Mochi's tasks:
  07:30  Morning walk         Mochi  done     due 2026-10-19
  --:--  Grooming             Mochi  pending  due 2026-10-19
  17:00  Evening walk         Mochi  pending  due 2026-10-19
  17:00  Vet call             Mochi  pending  due 2026-10-19
  12:30  Medication           Mochi  pending  due 2026-10-19
  07:30  Morning walk         Mochi  pending  due 2026-10-20

Pending tasks:
  --:--  Grooming             Mochi  pending  due 2026-10-19
  17:00  Evening walk         Mochi  pending  due 2026-10-19
  17:00  Vet call             Mochi  pending  due 2026-10-19
  12:30  Medication           Mochi  pending  due 2026-10-19
  07:30  Morning walk         Mochi  pending  due 2026-10-20
  08:15  Thyroid pill         Luna   pending  due 2026-10-19
  12:30  Laser pointer play   Luna   pending  due 2026-10-19
  --:--  Brush fur            Luna   pending  due 2026-10-19
  18:00  Feeding              Luna   pending  due 2026-10-20

Completed tasks:
  07:30  Morning walk         Mochi  done     due 2026-10-19
  18:00  Feeding              Luna   done     due 2026-10-19

Luna's pending tasks, sorted:
  08:15  Thyroid pill         Luna   pending  due 2026-10-19
  12:30  Laser pointer play   Luna   pending  due 2026-10-19
  18:00  Feeding              Luna   pending  due 2026-10-20
  --:--  Brush fur            Luna   pending  due 2026-10-19

Conflict check: 2 warning(s)
  WARNING (different pets: Luna and Mochi) - same time: 'Laser pointer play' at 12:30 conflicts with 'Medication' at 12:30 (runs until 12:35).
  WARNING (same pet: Mochi) - same time: 'Vet call' at 17:00 conflicts with 'Evening walk' at 17:00 (runs until 17:25).

Today's Schedule for Jordan (Monday, October 19)
============================================================
07:30 - Brush fur (Luna), 10 min: Low priority; no preferred time, placed in the first free slot.
08:15 - Thyroid pill (Luna), 5 min: High priority; scheduled at its preferred time 08:15.
12:30 - Medication (Mochi), 5 min: High priority; scheduled at its preferred time 12:30.
12:35 - Laser pointer play (Luna), 20 min: Medium priority; preferred time 12:30 overlapped another task, moved to 12:35.
17:00 - Vet call (Mochi), 15 min: Medium priority; scheduled at its preferred time 17:00.
17:15 - Evening walk (Mochi), 25 min: Medium priority; preferred time 17:00 overlapped another task, moved to 17:15.
-- - Grooming (Mochi), 45 min: Skipped: needs 45 min but only 40 of 120 min were left (low priority).
------------------------------------------------------------
6 scheduled, 1 skipped | 80 of 120 min used
```

## 🧪 Testing PawPal+

Run the full suite from the project root:

```bash
python -m pytest
```

The 85 tests in `tests/test_pawpal.py` cover:

- **Sorting:** chronological order, untimed tasks last, stable order for ties, empty and single-item lists, `00:00` and `23:59`, and the input list is never modified.
- **Recurrence:** completing a daily or weekly task creates the next occurrence on the same pet; late and early completion keep a weekly task on its own weekday; month, year and leap-day rollovers; completing twice never duplicates; one-off (`"once"`) tasks do not repeat; overdue tasks carry over and appear once.
- **Conflict detection:** duplicate times across pets and within one pet, one-minute overlaps, back-to-back tasks (no conflict), three-way clashes, and untimed, completed or future tasks being ignored.
- **Scheduling:** time-budget boundaries, skipped tasks with reasons, tasks that would run past midnight, zero budget, empty owners, running `generate_plan` twice, and an invalid `day_start`.
- **Validation and ownership:** bad durations, priorities, frequencies and times are rejected; `edit()` rolls back on error and refuses `completed`, `pet` and `pet_name`; each Task belongs to one pet, so the same object can't be added to two pets.

Test output:

```
============================= test session starts ==============================
platform darwin -- Python 3.14.3, pytest-9.1.1, pluggy-1.7.0
rootdir: .
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1
collected 85 items

tests/test_pawpal.py ................................................... [ 60%]
..................................                                       [100%]

============================== 85 passed in 0.03s ==============================
```

**Confidence Level: ★★★★☆ (4/5).** All 85 tests pass, and they cover the core behaviors (sorting, recurrence, conflicts) plus many failure paths. Writing the edge-case tests found a real bug (tasks pushed past midnight produced a start time of `24:30`), which is now fixed. I'm holding back one star because the Streamlit UI has no automated tests (it was only checked with Streamlit's headless runner) and the tests haven't been measured for coverage.

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
- **`Task.next_occurrence(today=None)`** builds a fresh, pending copy due one step (1 day for `"daily"`, 7 days for `"weekly"`) after the task's own `due_date`, so a weekly Monday task stays on Mondays even if it is finished on Thursday. If that date has already passed, it keeps stepping forward until it is after today, so the new task is never overdue the moment it is created. `"once"` tasks do not repeat.
- **`Pet.complete_task(task)`** checks that the task belongs to the pet, then calls `mark_complete()`. The "Mark done" button in the app uses it.
- Each task has a `due_date`, and **`Scheduler.generate_plan()`** only includes pending tasks that are due on or before the plan date, so a weekly task does not show up every day.

Run `python main.py` to see all four in the terminal.

## 🎬 Demo Walkthrough

### What you can do in the app

Start the app with `.venv/bin/python -m streamlit run app.py`. The page is one scrolling screen:

- **Owner:** set your name and how many minutes you have for pet care today.
- **Pets:** add one or more pets by name and species. Duplicate names are rejected.
- **Tasks:** pick a pet and add a task with a title, duration, priority (low, medium, high), category, an optional preferred time (`HH:MM`) and how often it repeats (once, daily or weekly). Invalid input, such as a bad time, shows a red error and nothing is added.
- **Task list:** every task in a table (pet, duration, priority, preferred time, repeats, due date, status), sorted by time. Filter it by pet and by pending or completed.
- **Mark a task done:** completing a daily or weekly task shows when the next one is due. A one-off task simply disappears from the pending list.
- **Conflict warnings:** if two tasks overlap, yellow warnings explain which ones clash. If tasks have times and none clash, a green message says so.
- **Generate schedule:** builds today's plan with a summary (scheduled, skipped, time used), a table with a "Why" for each task, a table of skipped tasks, and a "Plan explanation" expander.

### Example workflow

1. **Add a pet.** Enter "Mochi" and "dog" and click **Add pet**.
2. **Add tasks.** Add "Morning walk" (20 min, high priority, preferred time `09:00`, repeats daily), then "Vet call" (15 min, medium, preferred time `09:10`, once).
3. **Read the warning.** The task list shows a yellow banner: the two tasks overlap.
4. **Generate the schedule.** The walk stays at 09:00, and the vet call is moved to 09:20 with the reason "preferred time 09:10 overlapped another task, moved to 09:20."
5. **Finish the walk.** Under **Mark a task done**, pick the walk. The app confirms that tomorrow's walk is now due.
6. **Look at the list again.** Today's walk shows as done, and a new pending walk is due tomorrow. The vet call, once done, won't come back.

### Scheduler behaviors on display

- **Sorting by time:** the task list and the plan are in clock order, and tasks without a time go last.
- **Filtering:** by pet, by status, or both.
- **Conflict warnings:** same-time and overlapping tasks are flagged across pets and within one pet.
- **Conflict resolution:** overlapping tasks are moved back to the next free moment, and the plan says so.
- **Priority and time budget:** higher-priority tasks claim the available minutes first, and a task that doesn't fit is skipped with a reason.
- **Recurrence:** completing a task creates its next occurrence, and tasks due in the future wait their turn.

### Sample CLI output

`python main.py` runs the same logic in the terminal. This output was produced by running it on October 19, 2026 (the dates follow the day you run it). It shows two pets, sorting and filtering, two conflict warnings, and a final plan with a moved task and a skipped task:

```
============================================================
Sorting and filtering demo

All tasks, in insertion order:
  07:30  Morning walk         Mochi  done     due 2026-10-19
  --:--  Grooming             Mochi  pending  due 2026-10-19
  17:00  Evening walk         Mochi  pending  due 2026-10-19
  17:00  Vet call             Mochi  pending  due 2026-10-19
  12:30  Medication           Mochi  pending  due 2026-10-19
  07:30  Morning walk         Mochi  pending  due 2026-10-20
  08:15  Thyroid pill         Luna   pending  due 2026-10-19
  18:00  Feeding              Luna   done     due 2026-10-19
  12:30  Laser pointer play   Luna   pending  due 2026-10-19
  --:--  Brush fur            Luna   pending  due 2026-10-19
  18:00  Feeding              Luna   pending  due 2026-10-20

All tasks, sorted by time:
  07:30  Morning walk         Mochi  done     due 2026-10-19
  07:30  Morning walk         Mochi  pending  due 2026-10-20
  08:15  Thyroid pill         Luna   pending  due 2026-10-19
  12:30  Medication           Mochi  pending  due 2026-10-19
  12:30  Laser pointer play   Luna   pending  due 2026-10-19
  17:00  Evening walk         Mochi  pending  due 2026-10-19
  17:00  Vet call             Mochi  pending  due 2026-10-19
  18:00  Feeding              Luna   done     due 2026-10-19
  18:00  Feeding              Luna   pending  due 2026-10-20
  --:--  Grooming             Mochi  pending  due 2026-10-19
  --:--  Brush fur            Luna   pending  due 2026-10-19

Mochi's tasks:
  07:30  Morning walk         Mochi  done     due 2026-10-19
  --:--  Grooming             Mochi  pending  due 2026-10-19
  17:00  Evening walk         Mochi  pending  due 2026-10-19
  17:00  Vet call             Mochi  pending  due 2026-10-19
  12:30  Medication           Mochi  pending  due 2026-10-19
  07:30  Morning walk         Mochi  pending  due 2026-10-20

Pending tasks:
  --:--  Grooming             Mochi  pending  due 2026-10-19
  17:00  Evening walk         Mochi  pending  due 2026-10-19
  17:00  Vet call             Mochi  pending  due 2026-10-19
  12:30  Medication           Mochi  pending  due 2026-10-19
  07:30  Morning walk         Mochi  pending  due 2026-10-20
  08:15  Thyroid pill         Luna   pending  due 2026-10-19
  12:30  Laser pointer play   Luna   pending  due 2026-10-19
  --:--  Brush fur            Luna   pending  due 2026-10-19
  18:00  Feeding              Luna   pending  due 2026-10-20

Completed tasks:
  07:30  Morning walk         Mochi  done     due 2026-10-19
  18:00  Feeding              Luna   done     due 2026-10-19

Luna's pending tasks, sorted:
  08:15  Thyroid pill         Luna   pending  due 2026-10-19
  12:30  Laser pointer play   Luna   pending  due 2026-10-19
  18:00  Feeding              Luna   pending  due 2026-10-20
  --:--  Brush fur            Luna   pending  due 2026-10-19

Conflict check: 2 warning(s)
  WARNING (different pets: Luna and Mochi) - same time: 'Laser pointer play' at 12:30 conflicts with 'Medication' at 12:30 (runs until 12:35).
  WARNING (same pet: Mochi) - same time: 'Vet call' at 17:00 conflicts with 'Evening walk' at 17:00 (runs until 17:25).

Today's Schedule for Jordan (Monday, October 19)
============================================================
07:30 - Brush fur (Luna), 10 min: Low priority; no preferred time, placed in the first free slot.
08:15 - Thyroid pill (Luna), 5 min: High priority; scheduled at its preferred time 08:15.
12:30 - Medication (Mochi), 5 min: High priority; scheduled at its preferred time 12:30.
12:35 - Laser pointer play (Luna), 20 min: Medium priority; preferred time 12:30 overlapped another task, moved to 12:35.
17:00 - Vet call (Mochi), 15 min: Medium priority; scheduled at its preferred time 17:00.
17:15 - Evening walk (Mochi), 25 min: Medium priority; preferred time 17:00 overlapped another task, moved to 17:15.
-- - Grooming (Mochi), 45 min: Skipped: needs 45 min but only 40 of 120 min were left (low priority).
------------------------------------------------------------
6 scheduled, 1 skipped | 80 of 120 min used
```

Reading the output: the "done" rows with a matching "pending" row due the next day are recurrence at work. The two warnings are the conflicts found, and in the plan below them "Laser pointer play" and "Evening walk" are the tasks that were moved back to avoid them. "Grooming" is skipped because only 40 of the 120 minutes were left when its turn came.

---

## 🤝 Credits

Built by Isamar Rodriguez with Claude (Anthropic's AI coding assistant) as a pair-programming partner. Claude helped with the implementation, the edge-case tests, the Streamlit display, and the documentation, and Isamar made the design decisions and reviewed the work. See the AI Collaboration section of [reflection.md](reflection.md) for how the collaboration worked.
