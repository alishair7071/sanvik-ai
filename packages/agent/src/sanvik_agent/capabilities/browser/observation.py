"""Read the current browser state without changing the browser."""

from sanvik_agent.execution.browser import BrowserSession


# This first observation intentionally includes only common interactive HTML controls.
INTERACTIVE_ELEMENT_SELECTOR = "a, button, input, textarea, select"
MAX_INTERACTIVE_ELEMENTS = 20


class BrowserObservationStore:
    """Keep private Playwright locators for the latest browser observations."""

    def __init__(self):
        self.next_observation_number = 1
        self.observations = {}

    def save(self, page, element_locators: dict) -> str:
        observation_id = f"observation_{self.next_observation_number}"
        self.next_observation_number += 1

        self.observations[observation_id] = {
            "page": page,
            "page_url": page.url,
            "element_locators": element_locators,
        }

        return observation_id

    def get_element(self, observation_id: str, element_id: str):
        observation = self.observations.get(observation_id)

        if observation is None:
            raise ValueError("Browser observation does not exist")

        if observation["page"].url != observation["page_url"]:
            raise ValueError("Browser page changed after the observation")

        element = observation["element_locators"].get(element_id)

        if element is None:
            raise ValueError("Element does not exist in this browser observation")

        return element

    def discard(self, observation_id: str) -> None:
        """Remove an observation after an action may have changed the page."""
        self.observations.pop(observation_id, None)

    def discard_for_page(self, page) -> None:
        """Remove observations created for one browser page."""
        observation_ids = []

        for observation_id, observation in self.observations.items():
            if observation["page"] is page:
                observation_ids.append(observation_id)

        for observation_id in observation_ids:
            self.discard(observation_id)

    def discard_all(self) -> None:
        """Remove every observation when the active browser tab changes."""
        self.observations.clear()


def observe_browser(session: BrowserSession, store: BrowserObservationStore) -> dict:
    """Return a small, read-only description of the current browser state."""
    active_page = session.start()
    elements, element_locators = get_interactive_elements(active_page)
    observation_id = store.save(active_page, element_locators)

    return {
        "observation_id": observation_id,
        "active_page": {
            "url": active_page.url,
            "title": active_page.title(),
        },
        "tabs": get_open_tabs(session, active_page),
        "interactive_elements": elements,
    }


def get_open_tabs(session: BrowserSession, active_page) -> list[dict]:
    """Return the open tabs and identify which tab Sanvik is currently using."""
    tabs = []

    for index, page in enumerate(session.context.pages):
        tabs.append({
            "index": index,
            "url": page.url,
            "title": page.title(),
            "is_active": page is active_page,
        })

    return tabs


def get_interactive_elements(page) -> tuple[list[dict], dict]:
    """Return a limited description of visible links, buttons, and form controls."""
    locator = page.locator(INTERACTIVE_ELEMENT_SELECTOR)
    element_count = min(locator.count(), MAX_INTERACTIVE_ELEMENTS)
    elements = []
    element_locators = {}

    for index in range(element_count):
        element = locator.nth(index)

        if not element.is_visible():
            continue

        details = element.evaluate(
            """element => ({
                tag: element.tagName.toLowerCase(),
                role: element.getAttribute('role') || '',
                name: (
                    element.getAttribute('aria-label') ||
                    element.innerText ||
                    element.value ||
                    element.getAttribute('placeholder') || ''
                ).trim(),
                options: element.tagName === 'SELECT'
                    ? Array.from(element.options).slice(0, 20).map(option => ({
                        value: option.value,
                        label: option.text.trim()
                    }))
                    : []
            })"""
        )
        element_id = f"element_{len(elements) + 1}"
        observed_element = {
            "element_id": element_id,
            "tag": details["tag"],
            "role": details["role"],
            "name": details["name"][:120],
        }

        if details.get("options"):
            observed_element["options"] = details["options"]

        elements.append(observed_element)
        element_locators[element_id] = element

    return elements, element_locators