"""HTTP routes. Kept thin: each one validates input and calls a pipeline function.

Workspaces are addressed by their public key. For now only demo workspaces
accept uploads; owner accounts (signed-in uploads) come with the dashboard.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status

from app.answering import answer
from app.ingest import ingest
from app.llm import LLM, LLMError
from app.parsing import NoTextError, UnsupportedFileError
from app.ratelimit import RateLimiter
from app.schemas import (
    AskRequest,
    AskResponse,
    CitationResponse,
    DemoWorkspaceResponse,
    DocumentResponse,
)
from app.store import Document, Store, Workspace

DEMO_TTL_HOURS = 24
DEMO_MAX_DOCUMENTS = 3
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

demo_limiter = RateLimiter(max_calls=5, per_seconds=3600)
upload_limiter = RateLimiter(max_calls=10, per_seconds=3600)
ask_limiter = RateLimiter(max_calls=20, per_seconds=60)

router = APIRouter()


@lru_cache
def get_store() -> Store:
    return Store.from_env()


@lru_cache
def get_llm() -> LLM:
    return LLM.from_env()


StoreDep = Annotated[Store, Depends(get_store)]
LLMDep = Annotated[LLM, Depends(get_llm)]


def get_workspace(public_key: str, store: StoreDep) -> Workspace:
    workspace = store.get_workspace_by_public_key(public_key)
    if workspace is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    return workspace


WorkspaceDep = Annotated[Workspace, Depends(get_workspace)]


def rate_limited(limiter: RateLimiter):
    def check(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        if not limiter.allow(client_ip):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests, slow down")

    return Depends(check)


@router.post(
    "/demo/workspaces",
    response_model=DemoWorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[rate_limited(demo_limiter)],
)
def create_demo_workspace(store: StoreDep) -> DemoWorkspaceResponse:
    workspace = store.create_workspace("Demo", is_demo=True)
    return DemoWorkspaceResponse(public_key=workspace.public_key, expires_in_hours=DEMO_TTL_HOURS)


@router.get("/w/{public_key}/documents", response_model=list[DocumentResponse])
def list_documents(workspace: WorkspaceDep, store: StoreDep) -> list[DocumentResponse]:
    return [_document_response(d) for d in store.list_documents(workspace.id)]


@router.post(
    "/w/{public_key}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[rate_limited(upload_limiter)],
)
def upload_document(file: UploadFile, workspace: WorkspaceDep, store: StoreDep, llm: LLMDep) -> DocumentResponse:
    if not workspace.is_demo:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Uploads to this workspace need an owner account")
    if len(store.list_documents(workspace.id)) >= DEMO_MAX_DOCUMENTS:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Demo workspaces hold at most {DEMO_MAX_DOCUMENTS} files")

    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Files must be 10 MB or smaller")

    try:
        document = ingest(store, llm, workspace.id, file.filename or "upload", data)
    except UnsupportedFileError as e:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(e)) from e
    except NoTextError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
    return _document_response(document)


@router.post(
    "/w/{public_key}/ask",
    response_model=AskResponse,
    dependencies=[rate_limited(ask_limiter)],
)
def ask(body: AskRequest, workspace: WorkspaceDep, store: StoreDep, llm: LLMDep) -> AskResponse:
    try:
        result = answer(store, llm, workspace.id, body.question)
    except LLMError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "The AI service is busy, try again shortly") from e
    return AskResponse(
        answer=result.text,
        language=result.language,
        found=result.found,
        citations=[
            CitationResponse(number=c.number, document_id=c.document_id, page=c.page, content=c.content)
            for c in result.citations
        ],
    )


def _document_response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        status=document.status,
        error=document.error,
        page_count=document.page_count,
    )
