"""Route one validated browser action request to a browser capability."""

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
from sanvik_agent.execution.browser import BrowserSession


def execute_browser_action(
    session: BrowserSession,
    store: BrowserObservationStore,
    request: dict,
) -> dict:
    """Validate one browser action request and run the matching capability."""
    if not isinstance(request, dict):
        raise ValueError("Browser action request must be an object")

    action = request.get("action")

    if action == "open_url":
        if request.keys() != {"action", "url"}:
            raise ValueError("open_url requires only url")
        return open_url(session, store, request["url"])

    if action == "click_element":
        if request.keys() != {"action", "observation_id", "element_id"}:
            raise ValueError("click_element requires observation_id and element_id")
        return click_element(store, request["observation_id"], request["element_id"])

    if action == "fill_element":
        if request.keys() != {"action", "observation_id", "element_id", "text"}:
            raise ValueError("fill_element requires observation_id, element_id, and text")
        return fill_element(
            store,
            request["observation_id"],
            request["element_id"],
            request["text"],
        )

    if action == "press_key":
        if request.keys() != {"action", "observation_id", "element_id", "key"}:
            raise ValueError("press_key requires observation_id, element_id, and key")
        return press_key(
            store,
            request["observation_id"],
            request["element_id"],
            request["key"],
        )

    if action == "select_option":
        if request.keys() != {"action", "observation_id", "element_id", "value"}:
            raise ValueError("select_option requires observation_id, element_id, and value")
        return select_option(
            store,
            request["observation_id"],
            request["element_id"],
            request["value"],
        )

    if action == "scroll_page":
        if request.keys() != {"action", "direction"}:
            raise ValueError("scroll_page requires only direction")
        return scroll_page(session, store, request["direction"])

    if action == "switch_tab":
        if request.keys() != {"action", "tab_index"}:
            raise ValueError("switch_tab requires only tab_index")
        return switch_tab(session, store, request["tab_index"])

    raise ValueError("Browser action is not supported")