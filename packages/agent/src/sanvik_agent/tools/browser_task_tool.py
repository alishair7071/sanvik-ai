"""LangChain tool wrapper for the general browser task graph."""

from langchain_core.tools import tool

from sanvik_agent.agent.browser_task_graph.browser_graph import run_browser_task
from sanvik_agent.capabilities.browser.observation import BrowserObservationStore
from sanvik_agent.execution.browser import BrowserSession


# Keep one browser and its private element references for this Python runtime.
browser_session = BrowserSession()
observation_store = BrowserObservationStore()


@tool
def run_browser_task_tool(task: str) -> dict:
    """Complete one general task in Sanvik's managed browser."""
    return run_browser_task(task, browser_session, observation_store)


def close_browser_session() -> None:
    """Close the managed browser when the local Python runtime stops."""
    browser_session.close()
    observation_store.discard_all()