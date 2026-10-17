from sanvik_agent.tools import computer_task_tool


def test_computer_tool_calls_existing_workflow(monkeypatch) -> None:
    expected_result = {
        "plan": {"goal": "Open Google Chrome", "steps": []},
        "execution": {"completed": True, "steps": []},
    }
    received_tasks = []

    def fake_run_task(task: str) -> dict:
        received_tasks.append(task)
        return expected_result

    monkeypatch.setattr(computer_task_tool, "run_task", fake_run_task)

    result = computer_task_tool.run_computer_task.invoke({"task": "Open Chrome"})

    assert received_tasks == ["Open Chrome"]
    assert result == expected_result
