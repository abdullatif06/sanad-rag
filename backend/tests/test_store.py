"""Integration tests against the real Supabase project (they create and delete their own data)."""

import os

import pytest

from app.chunking import Chunk
from app.store import Store, StoreError

pytestmark = pytest.mark.skipif(os.environ.get("RUN_LIVE") != "1", reason="set RUN_LIVE=1 to use real Supabase")

DIM = 768


def vec(*head: float) -> list[float]:
    return list(head) + [0.0] * (DIM - len(head))


@pytest.fixture
def store():
    return Store.from_env()


@pytest.fixture
def workspace(store):
    ws = store.create_workspace("pytest", is_demo=True)
    yield ws
    store.delete_workspace(ws.id)


def test_workspace_round_trip(store, workspace):
    assert store.get_workspace(workspace.id) == workspace
    assert store.get_workspace_by_public_key(workspace.public_key) == workspace
    assert len(workspace.public_key) == 32


def test_document_lifecycle(store, workspace):
    doc = store.create_document(workspace.id, "policy.pdf")
    assert doc.status == "processing"

    store.mark_document_ready(doc.id, page_count=3)
    assert store.get_document(doc.id).status == "ready"
    assert store.get_document(doc.id).page_count == 3

    store.mark_document_failed(doc.id, "boom")
    failed = store.get_document(doc.id)
    assert (failed.status, failed.error) == ("failed", "boom")
    assert [d.id for d in store.list_documents(workspace.id)] == [doc.id]


def test_add_chunks_and_hybrid_search(store, workspace):
    doc = store.create_document(workspace.id, "policy.pdf")
    chunks = [
        Chunk(0, 1, "Refunds within 30 days", "refunds within 30 days"),
        Chunk(1, 2, "سياسة الاسترجاع ثلاثون يوماً", "سياسه الاسترجاع ثلاثون يوما"),
        Chunk(2, 3, "Shipping takes 5 days", "shipping takes 5 days"),
    ]
    store.add_chunks(doc, chunks, [vec(1.0), vec(0.9, 0.1), vec(0.0, 1.0)])

    hits = store.search(workspace.id, vec(0.0, 1.0), "shipping", match_count=2)
    assert hits[0].content == "Shipping takes 5 days"
    assert hits[0].page == 3
    assert len(hits) == 2

    arabic = store.search(workspace.id, vec(1.0), "سياسه الاسترجاع", match_count=1)
    assert arabic[0].page == 2


def test_search_is_isolated_per_workspace(store, workspace):
    other = store.create_workspace("pytest-other", is_demo=True)
    try:
        doc = store.create_document(workspace.id, "a.txt")
        store.add_chunks(doc, [Chunk(0, 1, "secret", "secret")], [vec(1.0)])
        assert store.search(other.id, vec(1.0), "secret") == []
    finally:
        store.delete_workspace(other.id)


def test_deleting_workspace_removes_its_documents(store):
    ws = store.create_workspace("pytest-delete", is_demo=True)
    doc = store.create_document(ws.id, "a.txt")
    store.delete_workspace(ws.id)
    assert store.get_document(doc.id) is None


def test_add_chunks_rejects_mismatched_lengths(store, workspace):
    doc = store.create_document(workspace.id, "a.txt")
    with pytest.raises(StoreError):
        store.add_chunks(doc, [Chunk(0, 1, "x", "x")], [])
