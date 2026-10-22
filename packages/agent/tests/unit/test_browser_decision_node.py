import pytest

from sanvik_agent.agent.browser_task_graph.browser_decision_node import (
    BrowserTaskDecision,
    build_decision_prompt,
    choose_browser_action,
)
from sanvik_agent.agent.browser_task_state import create_browser_task_state


class FakeModel:
    def __init__(self, result):
        self.result = result
        self.output_schema = None
        self.prompt = None

    def with_structured_output(self, output_schema):
        self.output_schema = output_schema
        return self

    def invoke(self, prompt):
        self.prompt = prompt
        return self.result


def create_observed_state():
    state = create_browser_task_state("Search for Python jobs")
    state["current_observation"] = {
        "observation_id": "observation_1",
        "active_page": {"url": "https://example.com", "title": "Example"},
        "tabs": [],
        "interactive_elements": [
            {
                "element_id": "element_1",
                "tag": "input",
                "role": "",
                "name": "Search",
            },
        ],
    }
    return state


def test_choose_browser_action_returns_a_controlled_action_request() -> None:
    model = FakeModel(
        BrowserTaskDecision(
            decision="action",
            action="fill_element",
            parameters={
                "observation_id": "observation_1",
                "element_id": "element_1",
                "text": "Python jobs",
            },
        )
    )

    update = choose_browser_action(create_observed_state(), model)

    assert model.output_schema is BrowserTaskDecision
    assert update == {
        "status": "action_selected",
        "next_action": {
            "action": "fill_element",
            "observation_id": "observation_1",
            "element_id": "element_1",
            "text": "Python jobs",
        },
    }


def test_choose_browser_action_returns_completed_result() -> None:
    model = FakeModel(
        BrowserTaskDecision(
            decision="complete",
            final_message="The search results are open.",
        )
    )

    update = choose_browser_action(create_observed_state(), model)

    assert update == {
        "status": "completed",
        "final_result": {
            "success": True,
            "message": "The search results are open.",
        },
    }


def test_build_decision_prompt_requires_an_observation() -> None:
    state = create_browser_task_state("Search for Python jobs")

    with pytest.raises(ValueError, match="no current observation"):
        build_decision_prompt(state)