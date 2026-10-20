# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**
- User can create an owner profile (name, available time, preferences) and add one or more pets.
- User can add, edit, remove and complete care tasks, each with a duration and priority.
- User can generate a daily plan that fits their available time and prioritizes important tasks.
- User can see why each task was scheduled or skipped.


My initial UML has four classes. Ownership runs in a chain: an Owner has one or more Pets, and each Pet has its own Tasks. The Scheduler sits beside that chain and reads from it without owning anything, so the data classes stay simple and the planning logic can be tested on its own.

- **Owner:** holds the person's name, daily available minutes and preferences, plus their list of pets. It adds and removes pets and collects every task across all of them.
- **Pet:** holds profile info (name, species, breed, age, special needs) and owns its list of tasks. It adds, removes and filters tasks.
- **Task:** represents one care activity, with a title, category, duration, priority, optional preferred time, frequency and completed status. It can be marked complete or edited.
- **Scheduler:** takes an Owner and builds the daily plan. It generates a plan that fits the available time by priority, keeps the scheduled and skipped tasks, and explains why each was included or left out.

**b. Design changes**

Yes. After writing the class skeleton I reviewed it for missing relationships and logic problems, and made three changes before implementing any methods.

1. **Added `pet_name` to Task.** A Task originally had no link back to its Pet. `Owner.get_all_tasks()` flattens every pet's tasks into one list, so the Scheduler could not say which pet a task was for, and two "Feed" tasks for different pets looked identical. `Pet.add_task()` now sets `pet_name`, so the plan can read "Walk Rex".
2. **Added a `ScheduledItem` class.** `scheduled_items` and `skipped_tasks` were plain lists of Tasks, with nowhere to store a start time or the reason a task was placed or skipped. `explain_plan()` needs those reasons, so each plan entry now wraps a Task with a `start_time` and a `reason`. Skipped entries use the same class with no start time. The Scheduler now produces ScheduledItems instead of referring to Tasks directly.
3. **Switched Task and Pet to identity comparison (`eq=False`).** Dataclasses compare every field by default, so two identical tasks count as equal. Then `list.remove(task)` could delete the wrong copy, for example when two pets each have an identical "Grooming" task. Default dataclasses are also unhashable, so tasks could not go in sets or dict keys. Comparing by identity keeps every task distinct.

I also added a note to `generate_plan()` to clear its lists before running, so calling it twice (for example, on a Streamlit rerun) does not duplicate entries.

**Changes made after the first implementation.** Testing and using the scheduler exposed more design problems, which I fixed later:

1. **Tasks know their pet and their due date.** `Task` gained a `pet` back-reference and a `due_date`. The back-reference lets `mark_complete()` add the next occurrence to the right pet, and `due_date` lets a plan include only tasks that are due, so a weekly task doesn't show up every day.
2. **One Task object per pet.** Adding the same Task object to two pets would have left it in both lists while claiming to belong to only one, so completing it would recur for only one pet. `Pet.add_task` now raises a `ValueError` for a task owned by another pet. Two pets can both need grooming, but each gets its own Task.
3. **One-off tasks.** Every task used to repeat. I added a `once` frequency, so a task like buying medication is completed once and never copied.
4. **Recurrence stays on its schedule.** The next occurrence now steps from the task's own due date instead of from today, so a weekly Monday task finished on Thursday comes back on Monday.
5. **A midnight guard.** A task pushed back by an overlap could get a start time like `24:30`, so a task that would run past midnight is now skipped with a reason.
6. **`edit()` can't bypass the rules.** It refuses `completed`, `pet` and `pet_name`, so a task can only be completed through `mark_complete()`.

The `how frequency interacts with completed` question I had put off is answered by items 3 and 4. I also updated the UML diagram (`diagrams/uml_final.mmd`) to show these changes.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers these constraints:

- **Time:** the owner's available minutes for the day is a hard limit.
- **Priority:** low, medium or high decides which tasks get the available time first.
- **Preferred time:** an optional `HH:MM` that decides where a task is placed. If two tasks overlap, the later one is moved.
- **Due date:** only pending tasks that are due on or before the plan date are included.
- **Day start and midnight:** the plan begins at the owner's `day_start` (08:00 by default), and nothing may run past 24:00.

I ranked them by what hurts most when it goes wrong. Time came first because the plan has to be realistic. Priority came second, so the important things like medication aren't the ones dropped. Preferred times came third because they are only preferences, and the scheduler can move a task to resolve a clash. A missed medication costs more than a late grooming, which is why priority beats a preferred time.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.

**Answer:** The scheduler is greedy. It sorts tasks by priority (then earlier preferred time, then shorter duration) and adds them until the time runs out. A task that doesn't fit is skipped with a reason, and smaller tasks after it are still tried. The tradeoff is that it can leave time unused. For example, a 60-minute high-priority task can use up a 60-minute day and push out three 20-minute medium-priority tasks, even though a different mix might have fit more tasks. A search for the best possible packing would avoid that.

- Why is that tradeoff reasonable for this scenario?

**Answer:** A pet owner wants the important things done first, and a missed medication is worse than a few unused minutes. The greedy approach is also simple, predictable and easy to explain: every skipped task gets a plain-language reason like "needs 45 min but only 40 were left." A search for the perfect packing would be harder to explain and could choose a surprising plan, such as dropping a high-priority task to fit two lower ones.

**A smaller design tradeoff.** I made the backend the single source of truth for priority levels. The names (`low`, `medium`, `high`) used to be defined twice, in `PRIORITY_LABELS` in `pawpal_system.py` and `PRIORITY_VALUES` in `app.py`. I changed `app.py` to import `PRIORITY_LABELS`, so the UI now depends on a backend constant instead of owning its own copy. I accepted that coupling to remove the risk of the two lists drifting apart. The UI already imports its other classes from the backend, so this adds no new kind of dependency, and the existing tests still passed.

---

## 3. AI Collaboration

**a. How you used AI**

The AI assistant was most useful for four things when building and hardening the scheduler:

- **Reading the real code before answering.** When I asked for edge cases, it read `pawpal_system.py` and the existing tests first. The list it gave was tied to my code, for example that `edit()` could bypass recurrence, not generic scheduler advice.
- **Running things to check its work.** It ran the test suite after every change and drove the Streamlit app with Streamlit's headless test runner to confirm the warnings and metrics appeared. When one of its own new tests failed, it worked out that the test was wrong, not the code.
- **Writing edge-case tests that found a real bug.** A test for a chain of late tasks showed that a plan could contain a start time of `24:30`. That bug is fixed, and the suite grew from 18 tests to 85.
- **Keeping the documents in step with the code.** It updated the README, the UML diagram and the test counts whenever the code changed.

The most helpful prompts asked for a prioritized list ("what are the most important edge cases to test?") and for the reasoning behind a choice ("why yellow and not red?"), because those gave me something to decide on.

*Separate chat sessions:* I started a new chat after each commit, so each session matched one phase of the project (the last one ran across my test commit, so testing and hardening share a phase):

1. **Design:** turning the UML into class skeletons.
2. **Core build:** implementing the classes, the scheduler and the `main.py` demo.
3. **Smarter scheduling:** sorting, filtering, conflict detection and the Streamlit app.
4. **Testing and hardening:** the automated test suite, edge cases, one-off tasks, the one-Task-per-pet rule, the midnight fix, recurrence that stays on its schedule, the app's display, and the README, diagram and reflection.

This helped in three ways. Each commit was a clean checkpoint, so I always knew what the code looked like when a phase started. Each chat stayed on one topic, which made it easier to follow what changed and why. And a fresh session read the finished code with fresh eyes: the last one found problems the earlier phases had missed, such as `edit()` bypassing recurrence and a plan that could produce a `24:30` start time.

**b. Judgment and verification**

Two moments where I did not accept the assistant's framing as-is:

- **One-off tasks.** The assistant said "if the README says so" about tasks needing to recur, but it had not checked, and the README said no such thing. I questioned the claim and decided a real app should support one-time tasks like buying medication. That led to a new `once` frequency, a "Repeats" dropdown in the app, and tests showing a one-off task is not copied when completed.
- **Shared tasks between pets.** The assistant pointed out that adding one Task object to two pets would silently mislead the system, because each task has only one pet. I asked whether two dogs couldn't both need grooming, and I suggested a design where the pet creates the task. After seeing the trade-offs, I chose to reject the shared object. Each pet now needs its own Task, so two dogs can both be groomed and complete it independently.

I checked its work by reading the answer against the code, asking "why" until I understood, and relying on the tests. The suite is the evidence that the code does what I decided, not what the assistant assumed.

---

## 4. Testing and Verification

**a. What you tested**

The suite has 85 pytest tests, written with the AI assistant and organized around the behaviors the scheduler promises:

- **Sorting:** tasks come out in clock order with untimed tasks last, ties keep their original order, the input list is never changed, and the boundary times `00:00` and `23:59` work.
- **Recurrence:** completing a daily or weekly task creates the next one on the same pet, including across month, year and leap-day boundaries. A task finished late or early stays on its own schedule, completing twice never duplicates, and one-off tasks never repeat.
- **Conflict detection:** the same time and overlapping times are flagged across pets and within one pet, back-to-back tasks are not, a one-minute overlap is, and untimed, completed or future tasks are ignored.
- **Scheduling:** the time budget at its exact boundary, tasks skipped with a reason, a big skipped task not blocking smaller ones, an empty owner, a zero budget, and tasks that would run past midnight.
- **Failure paths:** bad durations, priorities, frequencies and times are rejected, `edit()` rolls back when a value is invalid and refuses fields the system manages, and one Task object can't belong to two pets.

These mattered because the scheduler's output looks plausible even when it's wrong. A plan with a start time of `24:30` or a weekly task drifting off its day reads fine at a glance. Writing the failure-path tests also found a real bug, the `24:30` start time, which I then fixed.

**b. Confidence**

Four out of five. All 85 tests pass, and they cover the core behaviors and many failure paths, not just the happy ones. I held back a star for three reasons: the Streamlit app has no automated tests (I only drove it with Streamlit's headless runner), I haven't measured test coverage, and the planner is greedy, so it can leave unused time that a smarter packing would fill.

If I had more time I would test:

- **The UI itself,** with automated app tests for adding pets and tasks, filtering, and marking tasks done.
- **Several days in a row,** simulating a week of plans to check that unfinished tasks carry over and recurring tasks stay on schedule.
- **Overdue tasks that keep losing the time budget,** since priority doesn't increase with age and a low-priority task could be skipped indefinitely.
- **Looser validation holes,** such as a boolean passing as a duration or priority (`True` counts as `1` in Python).
- **Fixed tasks earlier than the day's start time** and a custom `day_start`, which have fewer tests than the default.

## 5. Reflection

**a. What went well**

I can't point to one single feature, but I'm most satisfied with how I worked through understanding the design problems instead of just accepting fixes. Working out why one Task object shared by two pets was a bug, and settling on one Task object per pet, was the clearest example. I also noticed questions the first version never asked: what happens to tasks that never get finished, and what to do with one-off tasks that shouldn't repeat. Answering those made the scheduler behave like something a real pet owner could use.

I'm also satisfied with the range of edge cases I thought through and tested, from midnight overflow to late completions, and that the finished project worked well together: the backend, the tests and the Streamlit app agree with each other.

**b. What you would improve**

If I had another iteration, I would improve four things:

- **Handle overdue tasks better.** Right now an unfinished task simply carries over to the next plan. It isn't flagged as overdue, it doesn't gain priority as it ages, and a low-priority task that keeps losing the time budget could be skipped every day. I would show "overdue by 2 days" in the plan and raise the priority of tasks that keep slipping.
- **Save the data.** Everything lives in memory, so refreshing the Streamlit page starts from an empty list. Saving owners, pets and tasks to a file or a small database would make it usable day to day.
- **Plan more smartly.** The planner is greedy: it takes tasks in priority order until the time runs out, which is fast and predictable but can leave unused time that a better packing would fill. I would also make `detect_conflicts` return structured data instead of strings, so the app doesn't have to trim the text for display.
- **Test the interface.** The backend has 85 tests, but the Streamlit app has none beyond a quick headless run. I would add automated tests for adding pets and tasks, filtering, and marking tasks done.

**c. Key takeaway**

Being the lead architect means the assistant gives me options and I choose the behavior. It could tell me what the code did on a late completion, but only I could decide that a weekly Monday task should stay on Mondays. The same went for yellow versus red conflict warnings and for supporting one-off tasks. I also have to check its claims: it said the README required recurring tasks without reading it, and a confident answer is not a verified one. Tests keep both of us honest, and asking "why" until I understood the design made the system better.
