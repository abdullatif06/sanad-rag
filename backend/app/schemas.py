"""Request and response shapes for the HTTP API."""

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


class AskResponse(BaseModel):
    answer: str
    language: str
    found: bool
    citations: list[CitationResponse]
