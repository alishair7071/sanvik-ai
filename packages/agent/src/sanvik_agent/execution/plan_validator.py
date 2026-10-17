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

# Notepad closing remains unsupported until save-dialog handling is implemented.
CLOSEABLE_APPLICATIONS = {"file_explorer", "chrome"}



# Report a plan that cannot run with the current capabilities.
class UnsupportedPlan(Exception):
    """The plan contains an unsupported action, parameter, or order."""



# Return the trusted executable for a supported application name.
def get_executable(application_name: str) -> str:
    application = SUPPORTED_APPLICATIONS.get(application_name)

    if application is None:
        raise UnsupportedPlan("Application is not supported")

    return application["executable"]



# Validate an open plan and return its trusted application name.
def check_open_plan(plan: Plan) -> str:
    for step in plan.steps:
        if step.risk_level not in (RiskLevel.READ_ONLY, RiskLevel.REVERSIBLE):
            raise UnsupportedPlan("Opening supports only read-only and reversible steps")

    first_step = plan.steps[0]
    if first_step.parameters.keys() != {"application"}:
        raise UnsupportedPlan("open_application needs only an application name")

    application_name = first_step.parameters["application"]
    if application_name not in SUPPORTED_APPLICATIONS:
        allowed = ", ".join(SUPPORTED_APPLICATIONS)
        raise UnsupportedPlan(f"Application must be one of: {allowed}")

    # Supported task 1: open the application, then verify its window.
    if len(plan.steps) == 2:
        verify_step = plan.steps[1]
        if verify_step.action == "verify_application" and not verify_step.parameters:
            return application_name

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
        return application_name

    raise UnsupportedPlan("Only opening an application or opening and typing text is supported")



# Validate a graceful close plan and return its trusted application name.
def check_close_plan(plan: Plan) -> str:
    if len(plan.steps) != 2:
        raise UnsupportedPlan("Closing needs a close step followed by verification")

    close_step = plan.steps[0]
    verify_step = plan.steps[1]

    parameter_names = close_step.parameters.keys()
    allowed_parameters = (
        parameter_names == {"application"}
        or parameter_names == {"application", "scope"}
    )
    if not allowed_parameters:
        raise UnsupportedPlan("close_application accepts application and optional scope")

    if "scope" in close_step.parameters and close_step.parameters["scope"] != "all":
        raise UnsupportedPlan("The only supported close scope is all")

    application_name = close_step.parameters["application"]
    if application_name not in CLOSEABLE_APPLICATIONS:
        allowed = ", ".join(sorted(CLOSEABLE_APPLICATIONS))
        raise UnsupportedPlan(f"Closing is supported only for: {allowed}")

    if close_step.risk_level != RiskLevel.SENSITIVE:
        raise UnsupportedPlan("close_application must use the SENSITIVE risk level")

    if verify_step.action != "verify_application_closed":
        raise UnsupportedPlan("Closing must finish with verify_application_closed")
    if verify_step.parameters:
        raise UnsupportedPlan("verify_application_closed does not need parameters")
    if verify_step.risk_level != RiskLevel.READ_ONLY:
        raise UnsupportedPlan("Close verification must use the READ_ONLY risk level")

    return application_name



# Check the complete plan before any Windows action runs.
def check_plan(plan: Plan) -> str:
    first_action = plan.steps[0].action

    if first_action == "open_application":
        return check_open_plan(plan)

    if first_action == "close_application":
        return check_close_plan(plan)

    raise UnsupportedPlan("The plan must start by opening or closing an application")
