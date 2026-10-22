from sanvik_agent.tools import known_workflow_tool


def test_computer_tool_calls_existing_workflow(monkeypatch) -> None:
    expected_result = {
        "plan": {"goal": "Open Google Chrome", "steps": []},
        "execution": {"completed": True, "steps": []},
    }
    received_tasks = []

    def fake_run_task(task: str) -> dict:
        received_tasks.append(task)
        return expected_result

    monkeypatch.setattr(known_workflow_tool, "run_task", fake_run_task)

    result = known_workflow_tool.run_known_workflow.invoke({"task": "Open Chrome"})

    assert received_tasks == ["Open Chrome"]
    assert result == expected_result
