"""Day 2 graph: understand_request -> create_plan."""

import logging

from langgraph.graph import END, START, StateGraph

from sanvik_agent.agent.planning.plan import Plan
from sanvik_agent.agent.state.task import TaskState, initial_state
from sanvik_agent.models.provider import InvalidModelResponse, PlanProvider, PlanningError

logger = logging.getLogger(__name__)


class EmptyTask(PlanningError):
    code = "empty_task"
    public_message = "Task must not be empty"


def build_planning_graph(provider: PlanProvider):
    def understand_request(state: TaskState) -> dict[str, str]:
        task = state["task"].strip()
        if not task:
            raise EmptyTask()
        logger.info("planning_started")
        return {"task": task, "status": "planning"}

    def create_plan(state: TaskState) -> dict[str, Plan | str]:
        plan = provider.create_plan(state["task"])
        if not isinstance(plan, Plan):
            raise InvalidModelResponse()
        logger.info("planning_completed")
        return {"plan": plan, "status": "planned"}

    graph = StateGraph(TaskState)
    graph.add_node("understand_request", understand_request)
    graph.add_node("create_plan", create_plan)
    graph.add_edge(START, "understand_request")
    graph.add_edge("understand_request", "create_plan")
    graph.add_edge("create_plan", END)
    return graph.compile()


def plan_task(task: str, provider: PlanProvider) -> Plan:
    logger.info("task_received")
    try:
        state = build_planning_graph(provider).invoke(initial_state(task))
        plan = state["plan"]
        if not isinstance(plan, Plan):
            raise RuntimeError("Graph finished without a plan")
        return plan
    except Exception:
        logger.info("planning_failed")
        raise
