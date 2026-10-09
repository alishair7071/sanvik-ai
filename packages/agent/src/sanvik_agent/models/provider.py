"""The planner's model boundary and controlled failure categories."""

from typing import Protocol

from sanvik_agent.agent.planning.plan import Plan


class PlanningError(Exception):
    code = "planning_failed"
    public_message = "Planning failed"


class MissingApiKey(PlanningError):
    code = "missing_api_key"
    public_message = "GROQ_API_KEY is not set in the Python runtime environment or packages/agent/.env"


class ProviderTimeout(PlanningError):
    code = "provider_timeout"
    public_message = "Groq did not respond before the timeout"


class ProviderFailure(PlanningError):
    code = "provider_failure"
    public_message = "Groq request failed"


class InvalidModelResponse(PlanningError):
    code = "invalid_model_response"
    public_message = "Groq returned an invalid plan"


class PlanProvider(Protocol):
    def create_plan(self, task: str) -> Plan: ...
