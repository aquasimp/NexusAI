"""Pydantic schemas for NEXUS AI API request and response contracts."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    ok: bool = True
    state: str
    tick: int
    system_health: float


class SimulateBody(BaseModel):
    scenario: str = Field("random", description="Scenario ID or 'random'")


class ApprovalBody(BaseModel):
    approve: bool
    action_id: str | None = None
    operator: str = "demo-operator"


class EvalBody(BaseModel):
    seeds: int = 4
    clean: int = 8


class LogItem(BaseModel):
    tick: int
    service: str
    level: str
    message: str
    timestamp: float | None = None


class SystemInfoResponse(BaseModel):
    state: str
    tick: int
    tick_seconds: float
    wall_seconds: float
    llm: dict[str, Any]
    ranker: dict[str, Any]
    detector: dict[str, Any]
    knowledge_base: dict[str, Any]
    stages: list[dict[str, str]]
    scenarios: list[dict[str, Any]]
    provenance: dict[str, list[str]]
