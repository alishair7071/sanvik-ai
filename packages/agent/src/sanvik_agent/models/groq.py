"""Groq Responses API adapter. Provider-specific details stay in this module."""

import os
from pathlib import Path

import httpx
from dotenv import dotenv_values

from sanvik_agent.agent.planning.plan import Plan
from sanvik_agent.models.provider import (
    InvalidModelResponse,
    MissingApiKey,
    ProviderFailure,
    ProviderTimeout,
)

GROQ_URL = "https://api.groq.com/openai/v1/responses"
LOCAL_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class GroqProvider:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        if api_key is None:
            api_key = os.environ.get("GROQ_API_KEY")
        if api_key is None:
            api_key = dotenv_values(LOCAL_ENV_FILE).get("GROQ_API_KEY")
        if not api_key or not api_key.strip():
            raise MissingApiKey()
        self.api_key = api_key
        self.model = model or os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        self.client = client

    def create_plan(self, task: str) -> Plan:
        try:
            response = (self.client or httpx).post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=50.0,
                json={
                    "model": self.model,
                    "store": False,
                    "input": [
                        {
                            "role": "system",
                            "content": (
                                "Create a concise computer-operation plan for the user's task. "
                                "Return only structured plan data. Do not produce code or claim "
                                "that actions have been performed. Each action must be a lowercase "
                                "snake_case identifier such as launch_app, type_text, or "
                                "verify_result; never put prose in action. Use "
                                "simple scalar parameters, observable expected results, and "
                                "honest risk levels. Include a final verification step."
                            ),
                        },
                        {"role": "user", "content": task},
                    ],
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "name": "sanvik_plan",
                            "schema": Plan.model_json_schema(),
                            "strict": False,
                        }
                    },
                },
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ProviderTimeout() from exc
        except httpx.HTTPError as exc:
            raise ProviderFailure() from exc

        try:
            body = response.json()
            if body.get("status") != "completed":
                raise ValueError("response did not complete")
            texts = [
                item["text"]
                for output in body["output"]
                if output.get("type") == "message"
                for item in output["content"]
                if item.get("type") == "output_text"
            ]
            if len(texts) != 1:
                raise ValueError("expected one output text")
            return Plan.model_validate_json(texts[0])
        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
            raise InvalidModelResponse() from exc