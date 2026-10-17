"""Outer LangGraph for general chat and computer-task tool calls."""

import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph

from sanvik_agent.llm.provider import get_chat_model
from sanvik_agent.tools import run_computer_task

SYSTEM_PROMPT = (
    "You are Sanvik AI, a helpful Windows computer assistant. "
    "Answer general questions directly. "
    "When the user asks you to operate their computer, first rewrite the request "
    "as a clear, self-contained task for the computer operator. Resolve references "
    "such as 'it' from the conversation. Preserve the user's exact intent, text, "
    "paths, and URLs. Do not add actions the user did not request. "
    "If important information is missing or ambiguous, ask the user a short "
    "clarifying question instead of calling the tool. "
    "When the task is clear, call run_computer_task once and put the refined "
    "request in its task argument. After receiving the tool result, report success "
    "only when its execution completed successfully."
)


def call_model(state: MessagesState) -> dict:
    """Let the model answer directly or request the computer-task tool."""
    model = get_chat_model()
    model_with_tools = model.bind_tools([run_computer_task])
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
    """Execute one requested computer task and return its result to the model."""
    tool_calls = state["messages"][-1].tool_calls

    if len(tool_calls) != 1:
        messages = []

        for tool_call in tool_calls:
            messages.append(ToolMessage(
                content="Only one computer task can run in each message.",
                tool_call_id=tool_call["id"],
            ))

        return {"messages": messages}

    tool_call = tool_calls[0]

    if tool_call["name"] != run_computer_task.name:
        result = {"success": False, "error": "Unknown tool requested"}
    else:
        try:
            result = run_computer_task.invoke(tool_call["args"])
        except Exception as error:
            result = {"success": False, "error": str(error)}

    tool_message = ToolMessage(
        content=json.dumps(result, ensure_ascii=False),
        tool_call_id=tool_call["id"],
    )
    return {"messages": [tool_message]}


def create_final_answer(state: MessagesState) -> dict:
    """Let the model turn the tool result into the final user-facing answer."""
    model = get_chat_model()
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}


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
