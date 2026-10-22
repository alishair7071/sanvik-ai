"""LangChain tool wrapper for the general browser task graph."""

from langchain_core.tools import tool

from sanvik_agent.agent.browser_task_graph.browser_graph import run_browser_task
from sanvik_agent.capabilities.browser.observation import BrowserObservationStore
from sanvik_agent.execution.browser import (
    close_managed_browser_session,
    get_managed_browser_session,
)


# Keep private element references for the latest observations in this Python runtime.
observation_store = BrowserObservationStore()


@tool
def run_general_browser_task(task: str) -> dict:
    """Complete one general task in Sanvik's managed browser."""
    session = get_managed_browser_session()
    return run_browser_task(task, session, observation_store)


def close_browser_session() -> None:
    """Close the managed browser when the local Python runtime stops."""
    close_managed_browser_session()
    observation_store.discard_all()
