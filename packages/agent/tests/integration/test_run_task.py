import json

from sanvik_agent.agent.plan import Plan
from sanvik_agent.agent import workflow
from sanvik_agent.ipc import runtime


def test_run_graph_plans_then_executes(monkeypatch) -> None:
    plan = Plan.model_validate({
        "goal": "Open Notepad",
        "steps": [{"action": "launch_app", "parameters": {"app": "notepad"},
                   "expected_result": "Notepad opens", "risk_level": "READ_ONLY"}],
    })
    calls = []
    monkeypatch.setattr(workflow, "plan_task", lambda task: calls.append(("plan", task)) or plan)
    monkeypatch.setattr(workflow, "execute_plan", lambda selected: calls.append(("execute", selected)) or {
        "completed": True,
        "steps": [{"action": "launch_app", "success": True, "message": "Verified"}],
    })

    result = workflow.run_task("Open Notepad")
    assert calls == [("plan", "Open Notepad"), ("execute", plan)]
    assert result["execution"]["completed"] is True


def test_run_task_ipc_response_keeps_request_id(monkeypatch) -> None:
    fake_result = {"plan": {"goal": "Open Notepad", "steps": []},
                   "execution": {"completed": True, "steps": []}}
    monkeypatch.setattr(workflow, "run_task", lambda task: fake_result)
    request = json.dumps({"version": 1, "type": "request", "id": "run-1",
                          "payload": {"operation": "run_task", "message": "Open Notepad"}})

    response, stop = runtime.handle_line(request)
    assert response["id"] == "run-1"
    assert response["success"] is True
    assert response["payload"] == fake_result
    assert not stop
