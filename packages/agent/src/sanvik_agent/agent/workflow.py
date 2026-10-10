"""LangGraph decides the order; execution code lives in another folder."""

from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from sanvik_agent.agent.plan import Plan
from sanvik_agent.agent.planner import plan_task
from sanvik_agent.execution.executor import execute_plan


class RunState(TypedDict):
    task: str
    plan: NotRequired[Plan]
    execution: NotRequired[dict]


def create_plan_node(state: RunState) -> dict:
    plan = plan_task(state["task"])
    return {"plan": plan}


def execute_plan_node(state: RunState) -> dict:
    execution = execute_plan(state["plan"])
    return {"execution": execution}


graph = StateGraph(RunState)
graph.add_node("create_plan", create_plan_node)
graph.add_node("execute_plan", execute_plan_node)
graph.add_edge(START, "create_plan")
graph.add_edge("create_plan", "execute_plan")
graph.add_edge("execute_plan", END)
workflow = graph.compile()


def run_task(task: str) -> dict:
    if not task.strip():
        raise ValueError("Task must not be empty")
    final_state = workflow.invoke({"task": task.strip()})
    return {
        "plan": final_state["plan"].model_dump(mode="json"),
        "execution": final_state["execution"],
    }
