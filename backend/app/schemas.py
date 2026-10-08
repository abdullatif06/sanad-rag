"""Request and response shapes for the HTTP API."""

from typing import Any

from pydantic import BaseModel, Field


class DemoWorkspaceResponse(BaseModel):
    public_key: str
    expires_in_hours: int


class DocumentResponse(BaseModel):
    id: str
    filename: str
    status: str
    error: str | None
    page_count: int | None


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class CitationResponse(BaseModel):
    number: int
    document_id: str
    page: int
    content: str


class EvalRunCreated(BaseModel):
    run_id: str
    status: str


class EvalItemResponse(BaseModel):
    question: str
    language: str
    answer: str
    scores: dict[str, Any]


class EvalRunResponse(BaseModel):
    run_id: str
    status: str
    created_at: str
    metrics: dict[str, Any] | None
    items: list[EvalItemResponse]


class AskResponse(BaseModel):
    answer: str
    language: str
    found: bool
    citations: list[CitationResponse]
