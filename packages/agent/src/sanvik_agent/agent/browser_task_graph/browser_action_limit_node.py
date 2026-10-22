"""Stop a browser task that has used all of its allowed actions."""

from sanvik_agent.agent.browser_task_state import BrowserTaskState


def mark_action_limit_reached(state: BrowserTaskState) -> dict:
    """Return a clear failed result when the browser action limit is reached."""
    return {
        "status": "failed",
        "final_result": {
            "success": False,
            "message": (
                f"Stopped after {state['max_actions']} browser actions "
                "without completing the task."
            ),
        },
    }