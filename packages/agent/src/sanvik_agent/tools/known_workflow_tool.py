"""LangChain tool wrapper for tested, known workflows."""

from langchain_core.tools import tool

from sanvik_agent.agent.workflow import run_task


@tool
def run_known_workflow(task: str) -> dict:
    """Run one clear task through a tested, known workflow."""
    return run_task(task)
