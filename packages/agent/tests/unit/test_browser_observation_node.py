from sanvik_agent.agent.browser_task_graph.browser_observation_node import observe_browser_node
from sanvik_agent.agent.browser_task_state import create_browser_task_state
from sanvik_agent.capabilities.browser.observation import BrowserObservationStore
from test_browser_observation import FakeElement, FakePage, FakeSession


def test_observe_browser_node_returns_observation_state_update() -> None:
    page = FakePage(
        "https://example.com",
        "Example",
        [FakeElement({"tag": "button", "role": "", "name": "Continue"})],
    )
    session = FakeSession(page, [page])
    store = BrowserObservationStore()
    state = create_browser_task_state("Find a job")

    update = observe_browser_node(state, session, store)

    assert update["status"] == "observed"
    assert update["current_observation"]["active_page"] == {
        "url": "https://example.com",
        "title": "Example",
    }
    assert update["current_observation"]["interactive_elements"][0]["name"] == "Continue"