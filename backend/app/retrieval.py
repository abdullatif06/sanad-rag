"""Find the chunks most relevant to a question."""

from app.normalize import normalize
from app.store import SearchHit

DEFAULT_TOP_K = 8


def retrieve(store, llm, workspace_id: str, question: str, top_k: int = DEFAULT_TOP_K) -> list[SearchHit]:
    # Embeddings understand the original text; keyword search needs the normalized form.
    query_embedding = llm.embed_query(question)
    return store.search(workspace_id, query_embedding, normalize(question), match_count=top_k)
