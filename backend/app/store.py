"""Reads and writes Sanad's data in Supabase. No other module touches the database."""

import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client

from app.chunking import Chunk

INSERT_BATCH_SIZE = 200  # keep request bodies small (each row carries a 768-float vector)


class StoreError(RuntimeError):
    pass


@dataclass(frozen=True)
class Workspace:
    id: str
    name: str
    public_key: str
    is_demo: bool


@dataclass(frozen=True)
class Document:
    id: str
    workspace_id: str
    filename: str
    status: str
    error: str | None
    page_count: int | None


@dataclass(frozen=True)
class SearchHit:
    chunk_id: int
    document_id: str
    page: int
    content: str
    score: float


class Store:
    def __init__(self, client: Client):
        self.client = client

    @classmethod
    def from_env(cls) -> "Store":
        load_dotenv(".env")
        url = os.environ.get("SUPABASE_URL", "").strip()
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        if not url or not key:
            raise StoreError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        return cls(create_client(url, key))

    # Workspaces ---------------------------------------------------------------

    def create_workspace(self, name: str, is_demo: bool = False, owner_id: str | None = None) -> Workspace:
        row = self._insert_one("workspaces", {"name": name, "is_demo": is_demo, "owner_id": owner_id})
        return _workspace(row)

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        rows = self.client.table("workspaces").select("*").eq("id", workspace_id).execute().data
        return _workspace(rows[0]) if rows else None

    def get_workspace_by_public_key(self, public_key: str) -> Workspace | None:
        rows = self.client.table("workspaces").select("*").eq("public_key", public_key).execute().data
        return _workspace(rows[0]) if rows else None

    def delete_workspace(self, workspace_id: str) -> None:
        """Deletes the workspace and, via cascade, its documents, chunks and evals."""
        self.client.table("workspaces").delete().eq("id", workspace_id).execute()

    # Documents ----------------------------------------------------------------

    def create_document(self, workspace_id: str, filename: str) -> Document:
        row = self._insert_one("documents", {"workspace_id": workspace_id, "filename": filename})
        return _document(row)

    def get_document(self, document_id: str) -> Document | None:
        rows = self.client.table("documents").select("*").eq("id", document_id).execute().data
        return _document(rows[0]) if rows else None

    def list_documents(self, workspace_id: str) -> list[Document]:
        rows = (
            self.client.table("documents")
            .select("*")
            .eq("workspace_id", workspace_id)
            .order("created_at")
            .execute()
            .data
        )
        return [_document(r) for r in rows]

    def mark_document_ready(self, document_id: str, page_count: int) -> None:
        self._update_document(document_id, {"status": "ready", "page_count": page_count, "error": None})

    def mark_document_failed(self, document_id: str, error: str) -> None:
        self._update_document(document_id, {"status": "failed", "error": error})

    # Chunks -------------------------------------------------------------------

    def add_chunks(
        self,
        document: Document,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> None:
        if len(chunks) != len(embeddings):
            raise StoreError(f"{len(chunks)} chunks but {len(embeddings)} embeddings")
        rows = [
            {
                "document_id": document.id,
                "workspace_id": document.workspace_id,
                "chunk_index": chunk.index,
                "page": chunk.page,
                "content": chunk.text,
                "content_normalized": chunk.normalized,
                "embedding": embedding,
            }
            for chunk, embedding in zip(chunks, embeddings)
        ]
        for start in range(0, len(rows), INSERT_BATCH_SIZE):
            self.client.table("chunks").insert(rows[start : start + INSERT_BATCH_SIZE]).execute()

    def search(
        self,
        workspace_id: str,
        query_embedding: list[float],
        query_text: str,
        match_count: int = 8,
    ) -> list[SearchHit]:
        rows = (
            self.client.rpc(
                "hybrid_search",
                {
                    "p_workspace_id": workspace_id,
                    "p_query_embedding": query_embedding,
                    "p_query_text": query_text,
                    "p_match_count": match_count,
                },
            )
            .execute()
            .data
        )
        return [
            SearchHit(r["id"], r["document_id"], r["page"], r["content"], r["score"])
            for r in rows
        ]

    # Helpers ------------------------------------------------------------------

    def _insert_one(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        rows = self.client.table(table).insert(values).execute().data
        if not rows:
            raise StoreError(f"Insert into {table} returned no row")
        return rows[0]

    def _update_document(self, document_id: str, values: dict[str, Any]) -> None:
        self.client.table("documents").update(values).eq("id", document_id).execute()


def _workspace(row: dict[str, Any]) -> Workspace:
    return Workspace(row["id"], row["name"], row["public_key"], row["is_demo"])


def _document(row: dict[str, Any]) -> Document:
    return Document(
        row["id"], row["workspace_id"], row["filename"], row["status"], row["error"], row["page_count"]
    )
