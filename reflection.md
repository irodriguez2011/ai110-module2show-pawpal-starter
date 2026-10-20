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
3. **Switched Task and Pet to identity comparison (`eq=False`).** Dataclasses compare every field by default, so two identical tasks count as equal. Then `list.remove(task)` could delete the wrong copy, which is likely because the same task is copied to each pet. Default dataclasses are also unhashable, so tasks could not go in sets or dict keys. Comparing by identity keeps every task distinct.

I also added a note to `generate_plan()` to clear its lists before running, so calling it twice (for example, on a Streamlit rerun) does not duplicate entries. I left other issues I found, such as string times, the untyped `preferences` dict, and how `frequency` interacts with `completed`, to deal with when I implement the scheduler.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.

**Answer:** I chose to make the backend the single source of truth for priority levels. The priority names (`low`, `medium`, `high`) used to be defined twice: `PRIORITY_LABELS` in `pawpal_system.py` and `PRIORITY_VALUES` in `app.py`. I changed `app.py` to import `PRIORITY_LABELS` and build its dropdown lookup from it. The tradeoff is that the UI now depends on a backend constant instead of owning its own copy. I accepted that coupling in exchange for removing the risk of the two lists drifting apart. I compared this against four other small cleanups (for example, replacing `any(task is existing ...)` with `task in self.tasks`) and picked this one because it was the only one where the duplication could cause a bug.

- Why is that tradeoff reasonable for this scenario?

**Answer:** The UI already imports `Owner`, `Pet`, `Scheduler` and `Task` from the backend, so one more import does not add a new kind of dependency. Without the change, adding a priority level in the backend would leave the dropdown missing it, and nothing would crash or warn, so the mistake could go unnoticed. With the change, the order (low, medium, high) and the default selection stay the same, and adding a level only needs one edit. The cost is small, and the 18 tests still pass. I only checked the derived dictionary and that `app.py` compiles, and I did not click through the Streamlit UI, so that still needs a manual look.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
