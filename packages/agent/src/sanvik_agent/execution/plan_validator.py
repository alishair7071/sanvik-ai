"""Validate whether a complete plan is supported by the current milestone."""

from sanvik_agent.agent.plan import Plan, RiskLevel

# This is the single source of truth for applications Sanvik may open.
SUPPORTED_APPLICATIONS = {
    "notepad": {
        "name": "Notepad",
        "executable": "notepad.exe",
    },
    "file_explorer": {
        "name": "File Explorer",
        "executable": "explorer.exe",
    },
    "chrome": {
        "name": "Google Chrome",
        "executable": "chrome.exe",
    },
}



# Report a plan that cannot run with the current capabilities.
class UnsupportedPlan(Exception):
    """The plan contains an unsupported action, parameter, or order."""



# Return the trusted executable for a supported application name.
def get_executable(application_name: str) -> str:
    application = SUPPORTED_APPLICATIONS.get(application_name)

    if application is None:
        raise UnsupportedPlan("Application is not supported")

    return application["executable"]



# Check the complete plan and return its approved executable.
def check_plan(plan: Plan) -> str:
    for step in plan.steps:
        if step.risk_level not in (RiskLevel.READ_ONLY, RiskLevel.REVERSIBLE):
            raise UnsupportedPlan("Only read-only and reversible steps are supported")

    first_step = plan.steps[0]
    if first_step.action != "open_application":
        raise UnsupportedPlan("The first step must open an application")
    if first_step.parameters.keys() != {"application"}:
        raise UnsupportedPlan("open_application needs only an application name")

    application_name = first_step.parameters["application"]
    if application_name not in SUPPORTED_APPLICATIONS:
        allowed = ", ".join(SUPPORTED_APPLICATIONS)
        raise UnsupportedPlan(f"Application must be one of: {allowed}")

    executable = get_executable(application_name)

    # Supported task 1: open the application, then verify its window.
    if len(plan.steps) == 2:
        verify_step = plan.steps[1]
        if verify_step.action == "verify_application" and not verify_step.parameters:
            return executable

    # Supported task 2: open Notepad, type once, then verify the text.
    if len(plan.steps) == 3:
        if application_name != "notepad":
            raise UnsupportedPlan("Typing text is currently supported only in Notepad")

        type_step = plan.steps[1]
        verify_step = plan.steps[2]

        if type_step.action != "type_text" or type_step.parameters.keys() != {"text"}:
            raise UnsupportedPlan("The second step must type text")

        text = type_step.parameters["text"]
        if not isinstance(text, str) or not text or len(text) > 10000:
            raise UnsupportedPlan("Text must contain 1 to 10000 characters")

        if verify_step.action != "verify_text":
            raise UnsupportedPlan("The final step must verify the typed text")
        if verify_step.parameters != {"text": text}:
            raise UnsupportedPlan("Verification text must match the typed text")
        return executable

    raise UnsupportedPlan("Only opening an application or opening and typing text is supported")
