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

1. Collect all pending tasks across every pet.
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

> Fill in once you've implemented scheduling logic.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | | e.g., by priority, duration |
| Filtering | | e.g., skip tasks if time runs out |
| Conflict handling | | e.g., overlapping time slots |
| Recurring tasks | | e.g., daily vs. weekly |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
