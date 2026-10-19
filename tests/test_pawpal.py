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
