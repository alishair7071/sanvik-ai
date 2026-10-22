from sanvik_agent.tools import general_browser_task_tool


def test_run_general_browser_task_uses_the_shared_browser_session(monkeypatch) -> None:
    received = []
    shared_session = object()
    expected = {
        "status": "completed",
        "final_result": {
            "success": True,
            "message": "The jobs page is open.",
        },
    }

    def fake_run_browser_task(task, session, store):
        received.append((task, session, store))
        return expected

    monkeypatch.setattr(
        general_browser_task_tool,
        "get_managed_browser_session",
        lambda: shared_session,
    )
    monkeypatch.setattr(general_browser_task_tool, "run_browser_task", fake_run_browser_task)

    result = general_browser_task_tool.run_general_browser_task.invoke({
        "task": "Open the jobs page",
    })

    assert result == expected
    assert received == [(
        "Open the jobs page",
        shared_session,
        general_browser_task_tool.observation_store,
    )]


def test_close_browser_session_closes_shared_browser_and_clears_observations(monkeypatch) -> None:
    closed = []
    cleared = []
    monkeypatch.setattr(
        general_browser_task_tool,
        "close_managed_browser_session",
        lambda: closed.append(True),
    )
    monkeypatch.setattr(
        general_browser_task_tool.observation_store,
        "discard_all",
        lambda: cleared.append(True),
    )

    general_browser_task_tool.close_browser_session()

    assert closed == [True]
    assert cleared == [True]