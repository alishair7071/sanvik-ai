"""Validated planning data. A plan is intent, never an executable command."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RiskLevel(StrEnum):
    READ_ONLY = "READ_ONLY"
    REVERSIBLE = "REVERSIBLE"
    SENSITIVE = "SENSITIVE"
    DESTRUCTIVE = "DESTRUCTIVE"


class PlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    parameters: dict[str, str | int | float | bool]
    expected_result: str = Field(min_length=1, max_length=1000)
    risk_level: RiskLevel

    @field_validator("action", "expected_result")
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str = Field(min_length=1, max_length=1000)
    steps: list[PlanStep] = Field(min_length=1, max_length=20)

    @field_validator("goal")
    @classmethod
    def non_blank_goal(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()
