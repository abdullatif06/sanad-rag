"""Upload pipeline: file -> pages -> chunks -> embeddings -> database."""

from app.chunking import chunk_pages
from app.llm import LLMError
from app.parsing import parse
from app.store import Document


def ingest(store, llm, workspace_id: str, filename: str, data: bytes) -> Document:
    """Store a file as searchable chunks.

    Raises UnsupportedFileError / NoTextError before anything is saved.
    Failures after the document row exists (e.g. Gemini quota) mark it 'failed'.
    """
    pages = parse(data, filename)
    chunks = chunk_pages(pages)

    document = store.create_document(workspace_id, filename)
    try:
        embeddings = llm.embed_documents([chunk.text for chunk in chunks])
        store.add_chunks(document, chunks, embeddings)
    except LLMError as e:
        store.mark_document_failed(document.id, str(e))
    except Exception:
        store.mark_document_failed(document.id, "Unexpected error while processing the file")
        raise
    else:
        store.mark_document_ready(document.id, page_count=max(page.number for page in pages))
    return store.get_document(document.id)
