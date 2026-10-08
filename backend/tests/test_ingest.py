import pytest

from app.ingest import ingest
from app.parsing import NoTextError, UnsupportedFileError
from tests.fakes import FakeLLM, FakeStore


def test_ingest_parses_chunks_embeds_and_saves():
    store, llm = FakeStore(), FakeLLM()
    doc = ingest(store, llm, "ws-1", "policy.txt", "Refunds take 30 days.".encode())

    assert doc.status == "ready"
    assert doc.page_count == 1
    assert llm.embedded == ["Refunds take 30 days."]
    [(chunk, embedding)] = store.chunks
    assert chunk.page == 1 and embedding == [0.1, 0.2]


def test_unsupported_or_empty_files_are_rejected_before_saving():
    store, llm = FakeStore(), FakeLLM()
    with pytest.raises(UnsupportedFileError):
        ingest(store, llm, "ws-1", "photo.png", b"...")
    with pytest.raises(NoTextError):
        ingest(store, llm, "ws-1", "empty.txt", b"   ")
    assert store.documents == {}


def test_embedding_failure_marks_document_failed():
    store, llm = FakeStore(), FakeLLM(fail_embedding=True)
    doc = ingest(store, llm, "ws-1", "policy.txt", b"Some text.")
    assert doc.status == "failed"
    assert "quota" in doc.error
    assert store.chunks == []
