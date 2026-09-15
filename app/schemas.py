from __future__ import annotations
from enum import StrEnum
from typing import Literal, TypedDict
from pydantic import BaseModel, Field

AnswerStatus = Literal["ok", "no_info", "error"]

class SyncStats(TypedDict):
    added: int
    changed: int
    removed: int

class SourceKind(StrEnum):
    MD = "md"
    DOCX = "docx"
    PDF = "pdf"
    HTML = "html"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) ->  SourceKind:
        cleaned = value.lower().strip()
        try:
            return cls(cleaned)
        except ValueError:
            return cls.UNKNOWN

class ApiError(BaseModel):
    error: str
    message: str
    details: dict[str, str] | None = None

class SourceNode(BaseModel):
    id: str
    source: str
    kind: SourceKind
    score: float | None
    snippet: str
    page_start: int | None = None
    page_end: int | None = None
    title: str | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class AskResponse(BaseModel):
    history_id: int
    question: str
    answer: str
    status: AnswerStatus
    sources: list[SourceNode]
    model: str
    duration_ms: int
    timestamp: str


class HistoryListItem(BaseModel):
    id: int
    timestamp: str
    question_preview: str
    status: AnswerStatus


class HistoryListResponse(BaseModel):
    items: list[HistoryListItem]
    total: int


class HistoryEntry(BaseModel):
    id: int
    timestamp: str
    question: str
    answer: str
    sources: list[SourceNode]
    model: str
    duration_ms: int
    status: AnswerStatus
