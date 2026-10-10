"""Check a plan before dispatching its steps to Windows automation."""

import logging

from sanvik_agent.agent.plan import Plan, RiskLevel
from sanvik_agent.execution.notepad import open_notepad, verify_notepad, write_text

logger = logging.getLogger(__name__)


class UnsupportedPlan(Exception):
    """The plan contains an action this V1 executor cannot safely perform."""


def check_plan(plan: Plan) -> None:
    """Reject the whole plan before taking any action."""
    launched = False
    wrote_text = False
    for index, step in enumerate(plan.steps):
        if step.risk_level not in (RiskLevel.READ_ONLY, RiskLevel.REVERSIBLE):
            raise UnsupportedPlan("This plan needs an unsupported risk level")

        if step.action == "launch_app":
            app = step.parameters.get("app")
            if launched or step.parameters.keys() != {"app"}:
                raise UnsupportedPlan("Only one Notepad launch is supported")
            if not isinstance(app, str) or app.lower() not in ("notepad", "notepad.exe"):
                raise UnsupportedPlan("Only Notepad can be opened")
            launched = True
        elif step.action == "type_text":
            text = step.parameters.get("text")
            if not launched or wrote_text or step.parameters.keys() != {"text"}:
                raise UnsupportedPlan("Text must be typed once after opening Notepad")
            if not isinstance(text, str) or not text or len(text) > 10000:
                raise UnsupportedPlan("Text must contain 1 to 10000 characters")
            wrote_text = True
        elif step.action == "verify_result":
            if not launched or index != len(plan.steps) - 1 or step.parameters:
                raise UnsupportedPlan("Only a final Notepad verification is supported")
        else:
            raise UnsupportedPlan(f"Unsupported action: {step.action}")


    if not launched:
        raise UnsupportedPlan("The plan must start by opening Notepad")


def execute_plan(plan: Plan) -> dict:
    check_plan(plan)
    results = []
    window = None
    expected_text = None

    for step in plan.steps:
        try:
            if step.action == "launch_app":
                window = open_notepad()
                verify_notepad(window, None)
            elif step.action == "type_text":
                expected_text = step.parameters["text"]
                write_text(window, expected_text)
            elif step.action == "verify_result":
                verify_notepad(window, expected_text)
        except Exception:
            logger.exception("Notepad step failed: %s", step.action)
            results.append({"action": step.action, "success": False,
                            "message": "Action failed or could not be verified"})
            return {"completed": False, "steps": results}

        results.append({"action": step.action, "success": True,
                        "message": "Verified"})

    return {"completed": True, "steps": results}
