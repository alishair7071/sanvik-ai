"""LangChain tool wrapper for the existing computer-task workflow."""

from langchain_core.tools import tool

from sanvik_agent.agent.workflow import run_task


@tool
def run_computer_task(task: str) -> dict:
    """Run one clear, self-contained task on the user's Windows computer."""
    return run_task(task)
