from sanvik_agent.tools import browser_task_tool


def test_run_browser_task_tool_runs_the_general_browser_graph(monkeypatch) -> None:
    received = []
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

    monkeypatch.setattr(browser_task_tool, "run_browser_task", fake_run_browser_task)

    result = browser_task_tool.run_browser_task_tool.invoke({
        "task": "Open the jobs page",
    })

    assert result == expected
    assert received == [(
        "Open the jobs page",
        browser_task_tool.browser_session,
        browser_task_tool.observation_store,
    )]


def test_close_browser_session_closes_browser_and_clears_observations(monkeypatch) -> None:
    closed = []
    cleared = []
    monkeypatch.setattr(
        browser_task_tool.browser_session,
        "close",
        lambda: closed.append(True),
    )
    monkeypatch.setattr(
        browser_task_tool.observation_store,
        "discard_all",
        lambda: cleared.append(True),
    )

    browser_task_tool.close_browser_session()

    assert closed == [True]
    assert cleared == [True]