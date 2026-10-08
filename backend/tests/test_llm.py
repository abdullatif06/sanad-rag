import math
import os
from types import SimpleNamespace

import pytest
from google.genai import errors

from app.llm import LLM, LLMError


def server_error(code: int = 503) -> errors.ServerError:
    return errors.ServerError(code, {"error": {"code": code, "message": "busy", "status": "UNAVAILABLE"}})


def client_error(code: int) -> errors.ClientError:
    return errors.ClientError(code, {"error": {"code": code, "message": "nope", "status": "X"}})


class FakeModels:
    """Stands in for client.models; `script` lists results or exceptions per call."""

    def __init__(self, generate_script=(), embed_dim=3):
        self.generate_script = list(generate_script)
        self.embed_dim = embed_dim
        self.generate_calls = []
        self.embed_calls = []

    def generate_content(self, model, contents, config=None):
        self.generate_calls.append(model)
        result = self.generate_script.pop(0)
        if isinstance(result, Exception):
            raise result
        return SimpleNamespace(text=result)

    def embed_content(self, model, contents, config=None):
        self.embed_calls.append((list(contents), config.task_type))
        vectors = [[float(i + 1)] * self.embed_dim for i in range(len(contents))]
        return SimpleNamespace(embeddings=[SimpleNamespace(values=v) for v in vectors])


def make_llm(models: FakeModels) -> tuple[LLM, list[float]]:
    sleeps: list[float] = []
    llm = LLM(
        client=SimpleNamespace(models=models),
        chat_model="main",
        fallback_model="backup",
        max_retries=3,
        sleep=sleeps.append,
    )
    return llm, sleeps


def test_generate_returns_text():
    llm, _ = make_llm(FakeModels(["hello"]))
    assert llm.generate("hi") == "hello"


def test_generate_retries_transient_errors_with_backoff():
    models = FakeModels([server_error(), client_error(429), "ok"])
    llm, sleeps = make_llm(models)
    assert llm.generate("hi") == "ok"
    assert models.generate_calls == ["main", "main", "main"]
    assert sleeps == [1, 2]


def test_generate_falls_back_when_main_model_keeps_failing():
    models = FakeModels([server_error()] * 3 + ["from backup"])
    llm, _ = make_llm(models)
    assert llm.generate("hi") == "from backup"
    assert models.generate_calls == ["main"] * 3 + ["backup"]


def test_generate_does_not_retry_permanent_errors():
    models = FakeModels([client_error(400)])
    llm, sleeps = make_llm(models)
    with pytest.raises(LLMError):
        llm.generate("hi")
    assert models.generate_calls == ["main"]
    assert sleeps == []


def test_generate_raises_when_everything_fails():
    llm, _ = make_llm(FakeModels([server_error()] * 6))
    with pytest.raises(LLMError):
        llm.generate("hi")


def test_embed_documents_batches_and_normalizes():
    models = FakeModels()
    llm, _ = make_llm(models)
    llm.embed_batch_size = 2
    vectors = llm.embed_documents(["a", "b", "c"])
    assert [len(call[0]) for call in models.embed_calls] == [2, 1]
    assert all(call[1] == "RETRIEVAL_DOCUMENT" for call in models.embed_calls)
    assert len(vectors) == 3
    for v in vectors:
        assert math.isclose(math.sqrt(sum(x * x for x in v)), 1.0)


def test_embed_query_uses_query_task_type():
    models = FakeModels()
    llm, _ = make_llm(models)
    vector = llm.embed_query("question?")
    assert models.embed_calls == [(["question?"], "RETRIEVAL_QUERY")]
    assert len(vector) == 3


def test_embed_documents_empty_list_makes_no_calls():
    models = FakeModels()
    llm, _ = make_llm(models)
    assert llm.embed_documents([]) == []
    assert models.embed_calls == []


@pytest.mark.skipif(os.environ.get("RUN_LIVE") != "1", reason="set RUN_LIVE=1 to call real Gemini")
def test_live_gemini_smoke():
    llm = LLM.from_env()
    assert llm.generate("Reply with exactly: ok").strip().lower().startswith("ok")
    [vector] = llm.embed_documents(["سياسة الاسترجاع"])
    assert len(vector) == llm.embed_dim
