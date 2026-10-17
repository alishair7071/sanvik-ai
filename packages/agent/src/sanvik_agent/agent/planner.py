"""Turn a task into a validated plan using LangGraph."""

import sys
from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from sanvik_agent.agent.plan import Plan
from sanvik_agent.execution.plan_validator import (
    CLOSEABLE_APPLICATIONS,
    SUPPORTED_APPLICATIONS,
)
from sanvik_agent.llm.provider import PlanningError, get_chat_model



def build_system_prompt() -> str:
    """Build the prompt from the applications allowed by the validator."""
    supported = ", ".join(
        f"{details['name']} ({application_name})"
        for application_name, details in SUPPORTED_APPLICATIONS.items()
    )
    closeable = ", ".join(sorted(CLOSEABLE_APPLICATIONS))

    return (
        f"Create a plan only for these supported applications: {supported}. "
        "For an open request, start with open_application. Its parameters must "
        "contain only the application key with the exact application name from "
        "the supported list. Finish an open-only request with verify_application "
        "and empty parameters. Only Notepad supports typing. For a Notepad typing "
        "request, use type_text with the exact requested text, then finish with "
        "verify_text using the same text. Open and typing steps may use only "
        "READ_ONLY or REVERSIBLE risk levels. "
        f"Closing is supported only for: {closeable}. For a close request, use "
        "close_application with the application parameter and the SENSITIVE risk "
        "level. If the user explicitly asks to close all windows, also include "
        "the parameter scope with the exact value all. Otherwise do not include "
        "scope. Then use verify_application_closed with empty parameters and the "
        "READ_ONLY risk level. Do not create a close plan for Notepad. "
        "Do not mix opening and closing in one plan. Do not invent other "
        "applications, actions, or parameters."
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
    messages = [("system", build_system_prompt()), ("human", state["task"])]
    result = model.with_structured_output(Plan).invoke(messages)
    print(result, file=sys.stderr)

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
