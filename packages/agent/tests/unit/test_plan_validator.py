import pytest

from sanvik_agent.agent.plan import Plan
from sanvik_agent.execution.plan_validator import (
    UnsupportedPlan,
    check_plan,
    check_youtube_video_plan,
)


def youtube_video_plan(query="Big Buck Bunny", risk_level="REVERSIBLE") -> Plan:
    return Plan.model_validate({
        "goal": "Play a YouTube video",
        "steps": [
            {
                "action": "play_youtube_video",
                "parameters": {"query": query},
                "expected_result": "The requested video is playing",
                "risk_level": risk_level,
            },
        ],
    })


def test_valid_youtube_video_plan_returns_a_clean_query() -> None:
    plan = youtube_video_plan("  Big Buck Bunny  ")

    query = check_youtube_video_plan(plan)

    assert query == "Big Buck Bunny"


@pytest.mark.parametrize(
    "plan",
    [
        youtube_video_plan("", "REVERSIBLE"),
        youtube_video_plan("x" * 201, "REVERSIBLE"),
        youtube_video_plan("Big Buck Bunny", "READ_ONLY"),
        Plan.model_validate({
            "goal": "Play a YouTube video",
            "steps": [
                {
                    "action": "play_youtube_video",
                    "parameters": {"query": "Big Buck Bunny", "url": "https://example.com"},
                    "expected_result": "The requested video is playing",
                    "risk_level": "REVERSIBLE",
                },
            ],
        }),
        Plan.model_validate({
            "goal": "Play a YouTube video",
            "steps": [
                {
                    "action": "play_youtube_video",
                    "parameters": {},
                    "expected_result": "The requested video is playing",
                    "risk_level": "REVERSIBLE",
                },
            ],
        }),
        Plan.model_validate({
            "goal": "Play a YouTube video",
            "steps": [
                {
                    "action": "play_youtube_video",
                    "parameters": {"query": "Big Buck Bunny"},
                    "expected_result": "The requested video is playing",
                    "risk_level": "REVERSIBLE",
                },
                {
                    "action": "open_application",
                    "parameters": {"application": "notepad"},
                    "expected_result": "Notepad is open",
                    "risk_level": "REVERSIBLE",
                },
            ],
        }),
    ],
)
def test_invalid_youtube_video_plans_are_rejected(plan) -> None:
    with pytest.raises(UnsupportedPlan):
        check_youtube_video_plan(plan)


def test_youtube_video_plan_is_supported_by_the_complete_validator() -> None:
    plan = youtube_video_plan()

    assert check_plan(plan) == "Big Buck Bunny"