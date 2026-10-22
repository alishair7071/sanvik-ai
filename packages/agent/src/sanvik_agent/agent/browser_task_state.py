"""State that the future general browser graph will carry between steps."""

from typing import NotRequired, TypedDict


DEFAULT_MAX_BROWSER_ACTIONS = 10


class BrowserTaskState(TypedDict):
    """Keep the browser task goal, observations, actions, and result together."""

    goal: str
    status: str
    max_actions: int
    action_history: list[dict]
    current_observation: NotRequired[dict]
    next_action: NotRequired[dict]
    latest_action_result: NotRequired[dict]
    final_result: NotRequired[dict]


def create_browser_task_state(
    goal: str,
    max_actions: int = DEFAULT_MAX_BROWSER_ACTIONS,
) -> BrowserTaskState:
    """Create the initial state for one general browser task."""
    if not isinstance(goal, str):
        raise ValueError("Browser task goal must be text")

    goal = goal.strip()

    if not goal:
        raise ValueError("Browser task goal must not be empty")

    if isinstance(max_actions, bool) or not isinstance(max_actions, int):
        raise ValueError("Browser action limit must be a whole number")

    if max_actions < 1:
        raise ValueError("Browser action limit must be at least one")

    return {
        "goal": goal,
        "status": "created",
        "max_actions": max_actions,
        "action_history": [],
    }