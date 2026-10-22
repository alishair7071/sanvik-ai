"""Read the browser and update one general browser task state."""

from sanvik_agent.agent.browser_task_state import BrowserTaskState
from sanvik_agent.capabilities.browser.observation import (
    BrowserObservationStore,
    observe_browser,
)
from sanvik_agent.execution.browser import BrowserSession


def observe_browser_node(
    state: BrowserTaskState,
    session: BrowserSession,
    store: BrowserObservationStore,
) -> dict:
    """Read the browser and return the state values changed by this node."""
    observation = observe_browser(session, store)

    return {
        "status": "observed",
        "current_observation": observation,
    }