"""Run the browser action selected by the browser decision node."""

from sanvik_agent.agent.browser_task_state import BrowserTaskState
from sanvik_agent.capabilities.browser.browser_action_dispatcher import (
    execute_browser_action,
)
from sanvik_agent.capabilities.browser.observation import BrowserObservationStore
from sanvik_agent.execution.browser import BrowserSession


def run_browser_action(
    state: BrowserTaskState,
    session: BrowserSession,
    store: BrowserObservationStore,
) -> dict:
    """Run one selected browser action and save its result in task state."""
    action_request = state.get("next_action")

    if action_request is None:
        raise ValueError("Browser task has no selected action")

    action_result = execute_browser_action(session, store, action_request)

    action_history = list(state["action_history"])
    action_history.append({
        "request": action_request,
        "result": action_result,
    })

    return {
        "status": "action_completed",
        "latest_action_result": action_result,
        "action_history": action_history,
    }