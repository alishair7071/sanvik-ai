import pytest

from sanvik_agent.agent.browser_task_state import create_browser_task_state


def test_create_browser_task_state_creates_clean_initial_state() -> None:
    state = create_browser_task_state("  Find Python jobs in Lahore  ")

    assert state == {
        "goal": "Find Python jobs in Lahore",
        "status": "created",
        "max_actions": 10,
        "action_history": [],
    }


@pytest.mark.parametrize("goal", ["", "   ", 42])
def test_create_browser_task_state_rejects_invalid_goal(goal) -> None:
    with pytest.raises(ValueError):
        create_browser_task_state(goal)


@pytest.mark.parametrize("max_actions", [0, -1, 1.5, True])
def test_create_browser_task_state_rejects_invalid_action_limit(max_actions) -> None:
    with pytest.raises(ValueError):
        create_browser_task_state("Open a page", max_actions)