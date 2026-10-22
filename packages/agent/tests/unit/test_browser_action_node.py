from sanvik_agent.agent.browser_task_graph.browser_action_node import (
    run_browser_action,
)
from sanvik_agent.agent.browser_task_state import create_browser_task_state
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


def test_run_browser_action_saves_result_in_action_history() -> None:
    page = FakePage()
    session = FakeSession(page)
    store = BrowserObservationStore()
    state = create_browser_task_state("Open the jobs page")
    state["next_action"] = {
        "action": "open_url",
        "url": "https://example.com/jobs",
    }

    update = run_browser_action(state, session, store)

    assert update["status"] == "action_completed"
    assert update["latest_action_result"]["action"] == "open_url"
    assert update["action_history"] == [
        {
            "request": {
                "action": "open_url",
                "url": "https://example.com/jobs",
            },
            "result": update["latest_action_result"],
        },
    ]