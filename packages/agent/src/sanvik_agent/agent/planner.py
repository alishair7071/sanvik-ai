"""Turn a task into a validated plan using LangGraph."""

from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from sanvik_agent.agent.plan import Plan
from sanvik_agent.llm.provider import PlanningError, get_chat_model

SYSTEM_PROMPT = (
    "Create a concise computer-operation plan for the user's task. "
    "Return only structured plan data. Do not produce code or claim that actions "
    "have been performed. Each action must be a lowercase snake_case identifier "
    "such as launch_app, type_text, or verify_result; never put prose in action. "
    "Use simple scalar parameters, observable expected results, and honest risk "
    "levels. Include a final verification step."
)


class TaskState(TypedDict):
    task: str
    plan: NotRequired[Plan]


class EmptyTask(PlanningError):
    code = "empty_task"
    public_message = "Task must not be empty"


def create_plan(state: TaskState) -> dict:
    """LangGraph supplies state; this node asks the selected model for a plan."""
    model = get_chat_model()
    messages = [("system", SYSTEM_PROMPT), ("human", state["task"])]
    result = model.with_structured_output(Plan).invoke(messages)

    if isinstance(result, Plan):
        plan_data = result.model_dump(mode="json")
    else:
        plan_data = result

    plan = Plan.model_validate(plan_data)
    return {"plan": plan}


graph = StateGraph(TaskState)
graph.add_node("create_plan", create_plan)
graph.add_edge(START, "create_plan")
graph.add_edge("create_plan", END)
workflow = graph.compile()


def plan_task(task: str) -> Plan:
    task = task.strip()
    if not task:
        raise EmptyTask()

    starting_state = {"task": task}
    final_state = workflow.invoke(starting_state)
    plan = final_state["plan"]
    return plan
