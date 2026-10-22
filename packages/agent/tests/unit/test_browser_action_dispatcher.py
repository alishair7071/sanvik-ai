import pytest

from sanvik_agent.capabilities.browser.browser_action_dispatcher import (
    execute_browser_action,
)
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


class FakeElement:
    def __init__(self):
        self.filled_text = None

    def fill(self, text):
        self.filled_text = text


def test_dispatcher_runs_fill_element() -> None:
    page = FakePage()
    element = FakeElement()
    session = FakeSession(page)
    store = BrowserObservationStore()
    observation_id = store.save(page, {"element_1": element})

    result = execute_browser_action(
        session,
        store,
        {
            "action": "fill_element",
            "observation_id": observation_id,
            "element_id": "element_1",
            "text": "Python developer",
        },
    )

    assert result["filled"] is True
    assert element.filled_text == "Python developer"


def test_dispatcher_runs_open_url_and_returns_observation() -> None:
    page = FakePage()
    session = FakeSession(page)
    store = BrowserObservationStore()

    result = execute_browser_action(
        session,
        store,
        {
            "action": "open_url",
            "url": "https://example.com/jobs",
        },
    )

    assert result["action"] == "open_url"
    assert result["observation"]["active_page"]["url"] == "https://example.com/jobs"


@pytest.mark.parametrize(
    "action_request, message",
    [
        ({"action": "delete_everything"}, "not supported"),
        ({"action": "open_url", "url": "https://example.com", "extra": True}, "requires only url"),
        ({"action": "fill_element", "text": "Hello"}, "requires observation_id"),
    ],
)
def test_dispatcher_rejects_unknown_or_incomplete_requests(action_request, message) -> None:
    page = FakePage()
    session = FakeSession(page)
    store = BrowserObservationStore()

    with pytest.raises(ValueError, match=message):
        execute_browser_action(session, store, action_request)