"""Execute an already validated application plan."""

import logging

from sanvik_agent.agent.plan import Plan
from sanvik_agent.execution.plan_validator import (
    UnsupportedPlan,
    check_plan,
    get_executable,
)
from sanvik_agent.execution.windows import (
    close_application,
    find_application_windows,
    open_application,
    type_text,
    verify_application,
    verify_application_closed,
    verify_text,
)

logger = logging.getLogger(__name__)



# Run each approved step and stop if an action fails.
def execute_plan(plan: Plan) -> dict:
    application_name = check_plan(plan)

    results = []
    window = None
    windows_to_verify = []

    for step in plan.steps:
        step_message = "Verified" if step.action.startswith("verify_") else "Completed"

        try:
            if step.action == "open_application":
                executable = get_executable(application_name)
                window = open_application(executable)

            elif step.action == "close_application":
                windows = find_application_windows(application_name)
                close_all = step.parameters.get("scope") == "all"

                if len(windows) == 0:
                    step_message = "Application was already closed"

                elif len(windows) > 1 and not close_all:
                    results.append({
                        "action": step.action,
                        "success": False,
                        "message": (
                            f"Cannot choose safely because {len(windows)} "
                            "application windows are open"
                        ),
                    })
                    return {"completed": False, "steps": results}

                else:
                    if close_all:
                        windows_to_verify = windows
                    else:
                        windows_to_verify = [windows[0]]

                    for selected_window in windows_to_verify:
                        close_application(selected_window)

                    if close_all and len(windows_to_verify) > 1:
                        step_message = f"Closed {len(windows_to_verify)} application windows"

            elif step.action == "type_text":
                type_text(window, step.parameters["text"])

            elif step.action == "verify_application":
                verify_application(window)

            elif step.action == "verify_application_closed":
                for selected_window in windows_to_verify:
                    verify_application_closed(selected_window)

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
            "message": step_message,
        })

    return {"completed": True, "steps": results}
