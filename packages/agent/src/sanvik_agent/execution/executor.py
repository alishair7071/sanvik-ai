"""Execute an already validated application plan."""

import logging

from sanvik_agent.agent.plan import Plan
from sanvik_agent.execution.plan_validator import UnsupportedPlan, check_plan
from sanvik_agent.execution.windows import (
    open_application,
    type_text,
    verify_application,
    verify_text,
)

logger = logging.getLogger(__name__)



# Run each approved step and stop if an action fails.
def execute_plan(plan: Plan) -> dict:
    executable = check_plan(plan)

    results = []
    window = None

    for step in plan.steps:
        try:
            if step.action == "open_application":
                window = open_application(executable)
            elif step.action == "type_text":
                type_text(window, step.parameters["text"])
            elif step.action == "verify_application":
                verify_application(window)
            elif step.action == "verify_text":
                verify_text(window, step.parameters["text"])
        except Exception:
            logger.exception("Application step failed: %s", step.action)
            results.append({
                "action": step.action,
                "success": False,
                "message": "Action failed or could not be verified",
            })
            return {"completed": False, "steps": results}

        results.append({
            "action": step.action,
            "success": True,
            "message": "Verified" if step.action.startswith("verify_") else "Completed",
        })

    return {"completed": True, "steps": results}
