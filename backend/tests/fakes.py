"""In-memory stand-ins for Store and LLM, so pipeline tests need no network."""

from dataclasses import dataclass, field, replace

from app.llm import LLMError
from app.store import Document, EvalItem, EvalRun, SearchHit, StoredChunk, Workspace


@dataclass
class FakeLLM:
    replies: list[str] = field(default_factory=list)
    fail_embedding: bool = False
    prompts: list[tuple[str, str | None]] = field(default_factory=list)
    embedded: list[str] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)

    def generate(self, prompt: str, system: str | None = None, temperature: float = 0.2, json_output: bool = False) -> str:
        self.prompts.append((prompt, system))
        reply = self.replies.pop(0)
        return reply(prompt) if callable(reply) else reply

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.fail_embedding:
            raise LLMError("quota exceeded")
        self.embedded.extend(texts)
        return [[0.1, 0.2] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        return [0.3, 0.4]


@dataclass
class FakeStore:
    hits: list[SearchHit] = field(default_factory=list)
    documents: dict[str, Document] = field(default_factory=dict)
    chunks: list = field(default_factory=list)
    searches: list[tuple] = field(default_factory=list)
    workspaces: dict[str, Workspace] = field(default_factory=dict)

    def create_workspace(self, name: str, is_demo: bool = False, owner_id: str | None = None) -> Workspace:
        n = len(self.workspaces) + 1
        workspace = Workspace(f"ws-{n}", name, f"key-{n}", is_demo)
        self.workspaces[workspace.id] = workspace
        return workspace

    def get_workspace_by_public_key(self, public_key: str) -> Workspace | None:
        return next((w for w in self.workspaces.values() if w.public_key == public_key), None)

    def list_documents(self, workspace_id: str) -> list[Document]:
        return [d for d in self.documents.values() if d.workspace_id == workspace_id]

    def create_document(self, workspace_id: str, filename: str) -> Document:
        doc = Document(f"doc-{len(self.documents) + 1}", workspace_id, filename, "processing", None, None)
        self.documents[doc.id] = doc
        return doc

    def get_document(self, document_id: str) -> Document | None:
        return self.documents.get(document_id)

    def mark_document_ready(self, document_id: str, page_count: int) -> None:
        doc = self.documents[document_id]
        self.documents[document_id] = replace(doc, status="ready", page_count=page_count, error=None)

    def mark_document_failed(self, document_id: str, error: str) -> None:
        doc = self.documents[document_id]
        self.documents[document_id] = replace(doc, status="failed", error=error)

    def add_chunks(self, document: Document, chunks, embeddings) -> None:
        self.chunks.extend(zip(chunks, embeddings))

    def search(self, workspace_id, query_embedding, query_text, match_count=8) -> list[SearchHit]:
        self.searches.append((workspace_id, query_embedding, query_text, match_count))
        return self.hits[:match_count]

    # Evaluations
    stored_chunks: list[StoredChunk] = field(default_factory=list)
    eval_runs: dict[str, EvalRun] = field(default_factory=dict)
    eval_items: dict[str, list[EvalItem]] = field(default_factory=dict)

    def list_chunks(self, workspace_id: str, limit: int = 500) -> list[StoredChunk]:
        return self.stored_chunks[:limit]

    def create_eval_run(self, workspace_id: str) -> EvalRun:
        run = EvalRun(f"run-{len(self.eval_runs) + 1}", workspace_id, "running", None, "2026-10-08T00:00:00Z")
        self.eval_runs[run.id] = run
        return run

    def get_eval_run(self, run_id: str) -> EvalRun | None:
        return self.eval_runs.get(run_id)

    def add_eval_items(self, run_id: str, items: list[EvalItem]) -> None:
        self.eval_items.setdefault(run_id, []).extend(items)

    def list_eval_items(self, run_id: str) -> list[EvalItem]:
        return self.eval_items.get(run_id, [])

    def finish_eval_run(self, run_id: str, metrics: dict) -> None:
        self.eval_runs[run_id] = replace(self.eval_runs[run_id], status="done", metrics=metrics)

    def fail_eval_run(self, run_id: str, error: str) -> None:
        self.eval_runs[run_id] = replace(self.eval_runs[run_id], status="failed", metrics={"error": error})
