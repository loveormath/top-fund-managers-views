from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DiscussionMode(StrEnum):
    SINGLE = "single"
    SUMMARY = "summary"
    MEETING = "meeting"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FundRef(BaseModel):
    code: str
    name: str


class ManagerPublic(BaseModel):
    id: str
    name: str
    institution: str
    role: str
    color: str
    avatar: str
    tags: list[str]
    representative_funds: list[FundRef]
    corpus_files: int = 0
    fund_files: int = 0
    profile_excerpt: str = ""
    method_excerpt: str = ""


class Evidence(BaseModel):
    quote: str
    source_file: str
    title: str = ""
    date: str | None = None
    chunk_id: str | None = None
    excerpt: str = ""


class ManagerView(BaseModel):
    manager_id: str
    manager_name: str
    position: str
    direct_evidence: list[Evidence] = Field(default_factory=list)
    method_inference: list[str] = Field(default_factory=list)
    holdings_evidence: list[Evidence] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"
    stage: Literal["analysis", "opening", "response"] = "analysis"


class ThreadCreate(BaseModel):
    mode: DiscussionMode
    manager_ids: list[str]
    title: str | None = None

    @field_validator("manager_ids")
    @classmethod
    def unique_managers(cls, value: list[str]) -> list[str]:
        deduplicated = list(dict.fromkeys(value))
        if not deduplicated:
            raise ValueError("至少选择一位基金经理")
        if len(deduplicated) > 5:
            raise ValueError("最多选择五位基金经理")
        return deduplicated


class RunCreate(BaseModel):
    question: str = Field(min_length=2, max_length=4000)


class SettingsPatch(BaseModel):
    model: str | None = None
    output_language: Literal["zh-CN", "en"] | None = None
    summary_format: Literal["structured", "narrative"] | None = None


class DeepSeekKeyInput(BaseModel):
    api_key: str = Field(min_length=8, max_length=256)


class SettingsPublic(BaseModel):
    deepseek_configured: bool
    deepseek_key_masked: str | None = None
    model: str
    output_language: str
    summary_format: str
    api_available: bool | None = None
    balance_infos: list[dict[str, Any]] = Field(default_factory=list)
    models: list[str] = Field(default_factory=list)
    last_checked_at: str | None = None


class IndexStatus(BaseModel):
    state: Literal["empty", "building", "ready", "degraded", "failed"]
    files: int = 0
    chunks: int = 0
    embedding_model: str
    vector_enabled: bool = False
    last_built_at: str | None = None
    error: str | None = None


class ThreadPublic(BaseModel):
    id: str
    title: str
    mode: DiscussionMode
    manager_ids: list[str]
    status: str
    created_at: str
    updated_at: str
    last_summary: str = ""
    runs: list[dict[str, Any]] = Field(default_factory=list)
    messages: list[dict[str, Any]] = Field(default_factory=list)


class RunPublic(BaseModel):
    id: str
    thread_id: str
    question: str
    status: RunStatus
    created_at: str
    completed_at: str | None = None
    error: str | None = None
    final_report: str = ""


class ApiMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
