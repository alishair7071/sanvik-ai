"""Outer LangGraph for general chat and task-tool calls."""

import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph

from sanvik_agent.llm.provider import get_chat_model
from sanvik_agent.tools import run_general_browser_task, run_known_workflow


SYSTEM_PROMPT = (
    "You are Sanvik AI, a helpful Windows computer assistant. "
    "Answer general questions directly. "
    "When the user asks you to operate their computer, first rewrite the request "
    "as a clear, self-contained task. The refined request must use the correct tool. Resolve references "
    "such as 'it' from the conversation. Preserve the user's exact intent, text, "
    "paths, and URLs. Do not add actions the user did not request. "
    "If important information is missing or ambiguous, ask the user a short "
    "clarifying question instead of calling a tool. "
    "Use run_known_workflow for supported Windows applications and the tested "
    "YouTube video workflow. Use run_general_browser_task for a general task on a "
    "website that needs browser interaction. Call only one tool per user message. "
    "After receiving a tool result, report success only when it completed "
    "successfully."
)


def call_model(state: MessagesState) -> dict:
    """Let the model answer directly or request one supported tool."""
    model = get_chat_model()
    tools = [run_known_workflow, run_general_browser_task]
    model_with_tools = model.bind_tools(tools)
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}


def choose_next_step(state: MessagesState) -> str:
    """Route a tool request to execution; otherwise finish the conversation."""
    last_message = state["messages"][-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "run_tool"

    return "finish"


def run_tool(state: MessagesState) -> dict:
    """Run one requested tool and return its result to the model."""
    tool_calls = state["messages"][-1].tool_calls

    if len(tool_calls) != 1:
        messages = []

        for tool_call in tool_calls:
            messages.append(ToolMessage(
                content="Only one task tool can run in each message.",
                tool_call_id=tool_call["id"],
            ))

        return {"messages": messages}

    tool_call = tool_calls[0]

    if tool_call["name"] == run_known_workflow.name:
        selected_tool = run_known_workflow
    elif tool_call["name"] == run_general_browser_task.name:
        selected_tool = run_general_browser_task
    else:
        selected_tool = None

    if selected_tool is None:
        result = {"success": False, "error": "Unknown tool requested"}
    else:
        try:
            result = selected_tool.invoke(tool_call["args"])
        except Exception as error:
            result = {"success": False, "error": str(error)}

    tool_message = ToolMessage(
        content=json.dumps(result, ensure_ascii=False),
        tool_call_id=tool_call["id"],
    )
    return {"messages": [tool_message]}


def create_final_answer(state: MessagesState) -> dict:
    """Return a factual reply from the tool result without another model call."""
    tool_message = state["messages"][-1]
    result = json.loads(str(tool_message.content))

    final_result = result.get("final_result")

    if isinstance(final_result, dict):
        message = final_result.get("message")

        if isinstance(message, str) and message.strip():
            return {"messages": [AIMessage(content=message)]}

    execution = result.get("execution")

    if isinstance(execution, dict):
        steps = execution.get("steps")
        completed = execution.get("completed")

        if isinstance(steps, list) and steps:
            last_step = steps[-1]
            message = last_step.get("message")

            if isinstance(message, str) and message.strip():
                return {"messages": [AIMessage(content=message)]}

        if completed is True:
            return {"messages": [AIMessage(content="Task completed successfully.")]}

        return {"messages": [AIMessage(content="The task could not be completed.")]}

    error = result.get("error")

    if isinstance(error, str) and error.strip():
        return {"messages": [AIMessage(content=f"The task could not be completed: {error}")]}

    return {"messages": [AIMessage(content="The task finished without a result.")]}

graph = StateGraph(MessagesState)
graph.add_node("call_model", call_model)
graph.add_node("run_tool", run_tool)
graph.add_node("create_final_answer", create_final_answer)
graph.add_edge(START, "call_model")
graph.add_conditional_edges(
    "call_model",
    choose_next_step,
    {"run_tool": "run_tool", "finish": END},
)
graph.add_edge("run_tool", "create_final_answer")
graph.add_edge("create_final_answer", END)

memory = InMemorySaver()
conversation_graph = graph.compile(checkpointer=memory)


def chat(message: str, conversation_id: str) -> str:
    """Run one conversation turn and return the assistant's final text."""
    message = message.strip()
    conversation_id = conversation_id.strip()

    if not message:
        raise ValueError("Message must not be empty")
    if not conversation_id:
        raise ValueError("Conversation ID must not be empty")

    starting_state = {"messages": [HumanMessage(content=message)]}
    config = {"configurable": {"thread_id": conversation_id}}
    final_state = conversation_graph.invoke(starting_state, config=config)
    assistant_message = final_state["messages"][-1]
    return str(assistant_message.content)
