from sanvik_agent.agent.browser_task_graph.browser_decision_node import (
    BrowserTaskDecision,
)
from sanvik_agent.agent.browser_task_graph.browser_graph import run_browser_task
from sanvik_agent.capabilities.browser.observation import BrowserObservationStore


class FakeLocator:
    def count(self):
        return 0


class FakePage:
    def __init__(self):
        self.url = "https://example.com"
        self.page_title = "Example"

    def title(self):
        return self.page_title

    def locator(self, selector):
        return FakeLocator()


class FakeContext:
    def __init__(self, page):
        self.pages = [page]


class FakeSession:
    def __init__(self, page):
        self.page = page
        self.context = FakeContext(page)

    def start(self):
        return self.page

    def open_page(self, url):
        self.page.url = url
        self.page.page_title = "Jobs"
        return self.page


class FakeModel:
    def __init__(self, decisions):
        self.decisions = decisions
        self.prompts = []

    def with_structured_output(self, output_schema):
        assert output_schema is BrowserTaskDecision
        return self

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return self.decisions.pop(0)


def test_browser_graph_observes_acts_and_completes() -> None:
    model = FakeModel([
        BrowserTaskDecision(
            decision="action",
            action="open_url",
            parameters={"url": "https://example.com/jobs"},
        ),
        BrowserTaskDecision(
            decision="complete",
            final_message="The jobs page is open.",
        ),
    ])
    page = FakePage()
    session = FakeSession(page)
    store = BrowserObservationStore()

    final_state = run_browser_task(
        "Open the jobs page",
        session,
        store,
        model,
    )

    assert final_state["status"] == "completed"
    assert final_state["final_result"] == {
        "success": True,
        "message": "The jobs page is open.",
    }
    assert final_state["action_history"][0]["request"] == {
        "action": "open_url",
        "url": "https://example.com/jobs",
    }
    assert len(model.prompts) == 2


def test_browser_graph_stops_when_the_action_limit_is_reached() -> None:
    model = FakeModel([
        BrowserTaskDecision(
            decision="action",
            action="open_url",
            parameters={"url": "https://example.com/jobs"},
        ),
        BrowserTaskDecision(
            decision="action",
            action="scroll_page",
            parameters={"direction": "down"},
        ),
    ])
    page = FakePage()
    session = FakeSession(page)
    store = BrowserObservationStore()

    final_state = run_browser_task(
        "Open the jobs page",
        session,
        store,
        model,
        max_actions=1,
    )

    assert final_state["status"] == "failed"
    assert final_state["final_result"] == {
        "success": False,
        "message": "Stopped after 1 browser actions without completing the task.",
    }
    assert len(final_state["action_history"]) == 1
    assert len(model.prompts) == 1