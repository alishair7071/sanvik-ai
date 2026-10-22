"""Small, controlled browser actions."""

from sanvik_agent.capabilities.browser.observation import (
    BrowserObservationStore,
    observe_browser,
)
from sanvik_agent.execution.browser import BrowserSession


SUPPORTED_KEYS = {
    "Enter",
    "Escape",
    "Tab",
    "ArrowUp",
    "ArrowDown",
    "ArrowLeft",
    "ArrowRight",
    "Backspace",
    "Delete",
    "Space",
}


def click_element(
    store: BrowserObservationStore,
    observation_id: str,
    element_id: str,
) -> dict:
    """Click one element that came from a valid browser observation."""
    element = store.get_element(observation_id, element_id)
    element.click()
    store.discard(observation_id)

    return {
        "action": "click_element",
        "element_id": element_id,
        "clicked": True,
    }


def fill_element(
    store: BrowserObservationStore,
    observation_id: str,
    element_id: str,
    text: str,
) -> dict:
    """Fill one observed input or text area with text."""
    if not isinstance(text, str):
        raise ValueError("Browser text must be a string")

    if len(text) > 10_000:
        raise ValueError("Browser text must contain at most 10000 characters")

    element = store.get_element(observation_id, element_id)
    element.fill(text)
    store.discard(observation_id)

    return {
        "action": "fill_element",
        "element_id": element_id,
        "filled": True,
        "text_length": len(text),
    }


def press_key(
    store: BrowserObservationStore,
    observation_id: str,
    element_id: str,
    key: str,
) -> dict:
    """Press one supported key on an observed browser element."""
    if key not in SUPPORTED_KEYS:
        allowed_keys = ", ".join(sorted(SUPPORTED_KEYS))
        raise ValueError(f"Browser key must be one of: {allowed_keys}")

    element = store.get_element(observation_id, element_id)
    element.press(key)
    store.discard(observation_id)

    return {
        "action": "press_key",
        "element_id": element_id,
        "key": key,
        "pressed": True,
    }


def select_option(
    store: BrowserObservationStore,
    observation_id: str,
    element_id: str,
    value: str,
) -> dict:
    """Select one value in an observed HTML select control."""
    if not isinstance(value, str) or not value:
        raise ValueError("Browser option value must be text")

    if len(value) > 500:
        raise ValueError("Browser option value must contain at most 500 characters")

    element = store.get_element(observation_id, element_id)
    element.select_option(value=value)
    store.discard(observation_id)

    return {
        "action": "select_option",
        "element_id": element_id,
        "selected": True,
        "value": value,
    }


def scroll_page(
    session: BrowserSession,
    store: BrowserObservationStore,
    direction: str,
) -> dict:
    """Scroll the active page one fixed amount up or down."""
    if direction not in {"up", "down"}:
        raise ValueError("Browser scroll direction must be up or down")

    page = session.start()
    scroll_amount = -600 if direction == "up" else 600
    page.mouse.wheel(0, scroll_amount)
    store.discard_for_page(page)

    return {
        "action": "scroll_page",
        "direction": direction,
        "scrolled": True,
    }


def switch_tab(
    session: BrowserSession,
    store: BrowserObservationStore,
    tab_index: int,
) -> dict:
    """Switch to one existing browser tab and return its fresh observation."""
    if not isinstance(tab_index, int) or isinstance(tab_index, bool):
        raise ValueError("Browser tab index must be a number")

    pages = session.context.pages

    if tab_index < 0 or tab_index >= len(pages):
        raise ValueError("Browser tab index does not exist")

    selected_page = pages[tab_index]
    store.discard_all()
    selected_page.bring_to_front()
    session.page = selected_page

    return {
        "action": "switch_tab",
        "observation": observe_browser(session, store),
    }


def open_url(
    session: BrowserSession,
    store: BrowserObservationStore,
    url: str,
) -> dict:
    """Open a complete web address and return a fresh browser observation."""
    current_page = session.start()
    store.discard_for_page(current_page)
    session.open_page(url)

    return {
        "action": "open_url",
        "observation": observe_browser(session, store),
    }