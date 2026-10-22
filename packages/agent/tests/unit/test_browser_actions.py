import pytest

from sanvik_agent.capabilities.browser.actions import (
    click_element,
    fill_element,
    open_url,
    press_key,
    scroll_page,
    select_option,
    switch_tab,
)
from sanvik_agent.capabilities.browser.observation import BrowserObservationStore


class FakeMouse:
    def __init__(self):
        self.scrolls = []

    def wheel(self, horizontal, vertical):
        self.scrolls.append((horizontal, vertical))


class FakePage:
    def __init__(self, url="https://example.com", title="Example"):
        self.url = url
        self.page_title = title
        self.mouse = FakeMouse()
        self.was_brought_to_front = False

    def title(self):
        return self.page_title

    def locator(self, selector):
        return FakeLocator([])

    def bring_to_front(self):
        self.was_brought_to_front = True


class FakeLocator:
    def __init__(self, elements):
        self.elements = elements

    def count(self):
        return len(self.elements)

    def nth(self, index):
        return self.elements[index]


class FakeContext:
    def __init__(self, pages):
        self.pages = pages


class FakeSession:
    def __init__(self, page, pages=None):
        self.page = page
        self.context = FakeContext(pages or [page])
        self.visited_urls = []

    def start(self):
        return self.page

    def open_page(self, url):
        self.visited_urls.append(url)
        self.page.url = url
        self.page.page_title = "Jobs"
        return self.page


class FakeElement:
    def __init__(self):
        self.click_count = 0
        self.filled_text = None
        self.pressed_key = None
        self.selected_value = None

    def click(self):
        self.click_count += 1

    def fill(self, text):
        self.filled_text = text

    def press(self, key):
        self.pressed_key = key

    def select_option(self, value):
        self.selected_value = value


def test_click_element_uses_a_stored_browser_element() -> None:
    page = FakePage()
    element = FakeElement()
    store = BrowserObservationStore()
    observation_id = store.save(page, {"element_1": element})

    result = click_element(store, observation_id, "element_1")

    assert result == {
        "action": "click_element",
        "element_id": "element_1",
        "clicked": True,
    }
    assert element.click_count == 1

    with pytest.raises(ValueError, match="Browser observation does not exist"):
        store.get_element(observation_id, "element_1")


def test_fill_element_uses_a_stored_browser_element() -> None:
    page = FakePage()
    element = FakeElement()
    store = BrowserObservationStore()
    observation_id = store.save(page, {"element_1": element})

    result = fill_element(store, observation_id, "element_1", "Python developer")

    assert result == {
        "action": "fill_element",
        "element_id": "element_1",
        "filled": True,
        "text_length": 16,
    }
    assert element.filled_text == "Python developer"


def test_fill_element_rejects_non_text_and_very_long_text() -> None:
    page = FakePage()
    element = FakeElement()
    store = BrowserObservationStore()
    observation_id = store.save(page, {"element_1": element})

    with pytest.raises(ValueError, match="must be a string"):
        fill_element(store, observation_id, "element_1", 42)

    with pytest.raises(ValueError, match="at most 10000"):
        fill_element(store, observation_id, "element_1", "a" * 10_001)


def test_press_key_uses_a_supported_key() -> None:
    page = FakePage()
    element = FakeElement()
    store = BrowserObservationStore()
    observation_id = store.save(page, {"element_1": element})

    result = press_key(store, observation_id, "element_1", "Enter")

    assert result == {
        "action": "press_key",
        "element_id": "element_1",
        "key": "Enter",
        "pressed": True,
    }
    assert element.pressed_key == "Enter"


def test_press_key_rejects_an_unknown_key() -> None:
    page = FakePage()
    store = BrowserObservationStore()
    observation_id = store.save(page, {"element_1": FakeElement()})

    with pytest.raises(ValueError, match="Browser key must be one of"):
        press_key(store, observation_id, "element_1", "Control+A")


def test_select_option_uses_a_stored_browser_element() -> None:
    page = FakePage()
    element = FakeElement()
    store = BrowserObservationStore()
    observation_id = store.save(page, {"element_1": element})

    result = select_option(store, observation_id, "element_1", "newest")

    assert result == {
        "action": "select_option",
        "element_id": "element_1",
        "selected": True,
        "value": "newest",
    }
    assert element.selected_value == "newest"


def test_scroll_page_discards_old_page_observations() -> None:
    page = FakePage()
    session = FakeSession(page)
    store = BrowserObservationStore()
    observation_id = store.save(page, {"element_1": FakeElement()})

    result = scroll_page(session, store, "down")

    assert result == {
        "action": "scroll_page",
        "direction": "down",
        "scrolled": True,
    }
    assert page.mouse.scrolls == [(0, 600)]

    with pytest.raises(ValueError, match="Browser observation does not exist"):
        store.get_element(observation_id, "element_1")


def test_switch_tab_returns_a_fresh_observation() -> None:
    first_page = FakePage("https://example.com", "Example")
    second_page = FakePage("https://example.com/jobs", "Jobs")
    session = FakeSession(first_page, [first_page, second_page])
    store = BrowserObservationStore()
    old_observation_id = store.save(first_page, {"element_1": FakeElement()})

    result = switch_tab(session, store, 1)

    assert result["action"] == "switch_tab"
    assert result["observation"]["active_page"] == {
        "url": "https://example.com/jobs",
        "title": "Jobs",
    }
    assert result["observation"]["tabs"][1]["is_active"] is True
    assert second_page.was_brought_to_front is True

    with pytest.raises(ValueError, match="Browser observation does not exist"):
        store.get_element(old_observation_id, "element_1")


def test_open_url_returns_a_fresh_browser_observation() -> None:
    page = FakePage()
    session = FakeSession(page)
    store = BrowserObservationStore()
    old_observation_id = store.save(page, {"element_1": FakeElement()})

    result = open_url(session, store, "https://example.com/jobs")

    assert result == {
        "action": "open_url",
        "observation": {
            "observation_id": "observation_2",
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
            ],
            "interactive_elements": [],
        },
    }
    assert session.visited_urls == ["https://example.com/jobs"]

    with pytest.raises(ValueError, match="Browser observation does not exist"):
        store.get_element(old_observation_id, "element_1")