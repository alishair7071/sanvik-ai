"""Connect the nodes that run one general browser task."""

from langgraph.graph import END, START, StateGraph

from sanvik_agent.agent.browser_task_graph.browser_action_limit_node import (
    mark_action_limit_reached,
)
from sanvik_agent.agent.browser_task_graph.browser_action_node import (
    run_browser_action,
)
from sanvik_agent.agent.browser_task_graph.browser_decision_node import (
    choose_browser_action,
)
from sanvik_agent.agent.browser_task_graph.browser_observation_node import (
    observe_browser_node,
)
from sanvik_agent.agent.browser_task_state import (
    BrowserTaskState,
    DEFAULT_MAX_BROWSER_ACTIONS,
    create_browser_task_state,
)
from sanvik_agent.capabilities.browser.observation import BrowserObservationStore
from sanvik_agent.execution.browser import BrowserSession


# One browser action can run three graph nodes: observe, decide, and act.
NODES_PER_BROWSER_ACTION = 3
RECURSION_LIMIT_BUFFER = 5


def choose_after_observation(state: BrowserTaskState) -> str:
    """Choose whether the task may ask the model for another action."""
    if len(state["action_history"]) >= state["max_actions"]:
        return "action_limit_reached"

    return "choose_browser_action"


def choose_next_node(state: BrowserTaskState) -> str:
    """Decide whether the browser task has finished or needs one action."""
    if state["status"] == "completed":
        return "finish"

    return "run_browser_action"


def build_browser_task_graph(
    session: BrowserSession,
    store: BrowserObservationStore,
    model=None,
):
    """Build one browser task graph using the supplied browser session and model."""

    def observe_node(state: BrowserTaskState) -> dict:
        return observe_browser_node(state, session, store)

    def decision_node(state: BrowserTaskState) -> dict:
        return choose_browser_action(state, model)

    def action_node(state: BrowserTaskState) -> dict:
        return run_browser_action(state, session, store)

    graph = StateGraph(BrowserTaskState)

    graph.add_node("observe_browser", observe_node)
    graph.add_node("choose_browser_action", decision_node)
    graph.add_node("run_browser_action", action_node)
    graph.add_node("action_limit_reached", mark_action_limit_reached)

    graph.add_edge(START, "observe_browser")
    graph.add_conditional_edges(
        "observe_browser",
        choose_after_observation,
        {
            "action_limit_reached": "action_limit_reached",
            "choose_browser_action": "choose_browser_action",
        },
    )
    graph.add_conditional_edges(
        "choose_browser_action",
        choose_next_node,
        {
            "finish": END,
            "run_browser_action": "run_browser_action",
        },
    )
    graph.add_edge("run_browser_action", "observe_browser")
    graph.add_edge("action_limit_reached", END)

    return graph.compile()


def run_browser_task(
    goal: str,
    session: BrowserSession,
    store: BrowserObservationStore,
    model=None,
    max_actions: int = DEFAULT_MAX_BROWSER_ACTIONS,
) -> BrowserTaskState:
    """Run the graph for one browser goal."""
    graph = build_browser_task_graph(session, store, model)
    starting_state = create_browser_task_state(goal, max_actions)

    # LangGraph counts graph-node transitions separately from browser actions.
    # Give the graph enough transitions to reach Sanvik's action-limit node.
    recursion_limit = (max_actions * NODES_PER_BROWSER_ACTION) + RECURSION_LIMIT_BUFFER
    config = {"recursion_limit": recursion_limit}

    return graph.invoke(starting_state, config=config)