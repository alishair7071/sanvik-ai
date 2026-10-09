"""Small LangGraph state for Day 2 planning."""

from typing import Literal, TypedDict

from sanvik_agent.agent.planning.plan import Plan


class TaskState(TypedDict):
    task: str
    plan: Plan | None
    status: Literal["received", "planning", "planned"]
    error: str | None


def initial_state(task: str) -> TaskState:
    return {"task": task, "plan": None, "status": "received", "error": None}
