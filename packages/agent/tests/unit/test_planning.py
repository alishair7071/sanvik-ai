import pytest
from pydantic import ValidationError

from sanvik_agent.agent.graph.planning import EmptyTask, build_planning_graph, plan_task
from sanvik_agent.agent.planning.plan import Plan
from sanvik_agent.agent.state.task import initial_state
from sanvik_agent.models.provider import InvalidModelResponse, ProviderFailure


VALID_PLAN = {
    "goal": "Open Notepad and type Hello",
    "steps": [
        {
            "action": "launch_app",
            "parameters": {"app": "Notepad"},
            "expected_result": "Notepad is open",
            "risk_level": "READ_ONLY",
        },
        {
            "action": "type_text",
            "parameters": {"text": "Hello"},
            "expected_result": "Hello appears in the editor",
            "risk_level": "REVERSIBLE",
        },
    ],
}


class FakeProvider:
    def __init__(self, plan: Plan | None = None, error: Exception | None = None) -> None:
        self.plan = plan
        self.error = error
        self.tasks: list[str] = []

    def create_plan(self, task: str) -> Plan:
        self.tasks.append(task)
        if self.error:
            raise self.error
        assert self.plan is not None
        return self.plan


def test_initial_state() -> None:
    assert initial_state("Open Notepad") == {
        "task": "Open Notepad",
        "plan": None,
        "status": "received",
        "error": None,
    }


def test_valid_plan_parses() -> None:
    plan = Plan.model_validate(VALID_PLAN)
    assert plan.steps[0].action == "launch_app"
    assert plan.steps[1].risk_level == "REVERSIBLE"


@pytest.mark.parametrize(
    "change",
    [
        {"goal": "  "},
        {"steps": []},
        {"steps": [{**VALID_PLAN["steps"][0], "risk_level": "UNKNOWN"}]},
        {"steps": [{**VALID_PLAN["steps"][0], "action": "Open Notepad"}]},
        {"steps": [{**VALID_PLAN["steps"][0], "unexpected": "code"}]},
    ],
)
def test_invalid_plan_rejected(change: dict) -> None:
    with pytest.raises(ValidationError):
        Plan.model_validate({**VALID_PLAN, **change})


def test_graph_runs_with_fake_provider() -> None:
    provider = FakeProvider(Plan.model_validate(VALID_PLAN))
    graph = build_planning_graph(provider)
    result = graph.invoke(initial_state("  Open Notepad and type Hello  "))
    assert result["status"] == "planned"
    assert result["plan"].goal == VALID_PLAN["goal"]
    assert provider.tasks == ["Open Notepad and type Hello"]


def test_empty_task_is_rejected_before_provider_call() -> None:
    provider = FakeProvider(Plan.model_validate(VALID_PLAN))
    with pytest.raises(EmptyTask):
        plan_task("  ", provider)
    assert provider.tasks == []


def test_provider_failure_propagates() -> None:
    with pytest.raises(ProviderFailure):
        plan_task("Open Notepad", FakeProvider(error=ProviderFailure()))


def test_provider_must_return_typed_plan() -> None:
    with pytest.raises(InvalidModelResponse):
        plan_task("Open Notepad", FakeProvider(plan={"goal": "unsafe"}))  # type: ignore[arg-type]
