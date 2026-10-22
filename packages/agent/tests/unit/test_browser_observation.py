import pytest

from sanvik_agent.capabilities.browser.observation import (
    BrowserObservationStore,
    observe_browser,
)


class FakeElement:
    def __init__(self, details, visible=True):
        self.details = details
        self.visible = visible

    def is_visible(self):
        return self.visible

    def evaluate(self, script):
        return self.details


class FakeLocator:
    def __init__(self, elements):
        self.elements = elements

    def count(self):
        return len(self.elements)

    def nth(self, index):
        return self.elements[index]


class FakePage:
    def __init__(self, url, title, elements):
        self.url = url
        self.page_title = title
        self.elements = elements

    def title(self):
        return self.page_title

    def locator(self, selector):
        assert selector == "a, button, input, textarea, select"
        return FakeLocator(self.elements)


class FakeContext:
    def __init__(self, pages):
        self.pages = pages


class FakeSession:
    def __init__(self, active_page, pages):
        self.active_page = active_page
        self.context = FakeContext(pages)

    def start(self):
        return self.active_page


def test_observe_browser_returns_tabs_and_visible_interactive_elements() -> None:
    active_page = FakePage(
        "https://example.com/jobs",
        "Jobs",
        [
            FakeElement({"tag": "input", "role": "", "name": "Search jobs"}),
            FakeElement({"tag": "button", "role": "", "name": "Search"}),
            FakeElement({"tag": "a", "role": "", "name": "Hidden link"}, visible=False),
        ],
    )
    other_page = FakePage("https://example.com/help", "Help", [])
    session = FakeSession(active_page, [active_page, other_page])
    store = BrowserObservationStore()

    observation = observe_browser(session, store)

    assert observation == {
        "observation_id": "observation_1",
        "active_page": {
            "url": "https://example.com/jobs",
            "title": "Jobs",
        },
        "tabs": [
            {
                "index": 0,
                "url": "https://example.com/jobs",
                "title": "Jobs",
                "is_active": True,
            },
            {
                "index": 1,
                "url": "https://example.com/help",
                "title": "Help",
                "is_active": False,
            },
        ],
        "interactive_elements": [
            {
                "element_id": "element_1",
                "tag": "input",
                "role": "",
                "name": "Search jobs",
            },
            {
                "element_id": "element_2",
                "tag": "button",
                "role": "",
                "name": "Search",
            },
        ],
    }

    assert store.get_element("observation_1", "element_2") is active_page.elements[1]


def test_observation_store_rejects_unknown_or_outdated_references() -> None:
    page = FakePage(
        "https://example.com",
        "Example",
        [FakeElement({"tag": "button", "role": "", "name": "Continue"})],
    )
    store = BrowserObservationStore()
    observation = observe_browser(FakeSession(page, [page]), store)

    with pytest.raises(ValueError, match="does not exist in this browser observation"):
        store.get_element(observation["observation_id"], "element_2")

    page.url = "https://example.com/next"

    with pytest.raises(ValueError, match="page changed"):
        store.get_element(observation["observation_id"], "element_1")