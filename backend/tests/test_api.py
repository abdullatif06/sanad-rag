import pytest
from fastapi.testclient import TestClient

from app import api
from app.llm import LLMError
from app.main import create_app
from app.ratelimit import RateLimiter
from app.store import SearchHit
from tests.fakes import FakeLLM, FakeStore


@pytest.fixture
def store():
    return FakeStore()


@pytest.fixture
def llm():
    return FakeLLM()


@pytest.fixture
def client(store, llm):
    # Fresh limits per test so tests don't throttle each other.
    for limiter in (api.demo_limiter, api.upload_limiter, api.ask_limiter):
        limiter.reset()
    app = create_app()
    app.dependency_overrides[api.get_store] = lambda: store
    app.dependency_overrides[api.get_llm] = lambda: llm
    return TestClient(app)


def new_demo(client) -> str:
    response = client.post("/demo/workspaces")
    assert response.status_code == 201
    return response.json()["public_key"]


def upload(client, key, name="policy.txt", content=b"Refunds take 30 days."):
    return client.post(f"/w/{key}/documents", files={"file": (name, content)})


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_demo_upload_list_and_ask(client, store, llm):
    key = new_demo(client)

    response = upload(client, key)
    assert response.status_code == 201
    assert response.json()["status"] == "ready"
    assert [d["filename"] for d in client.get(f"/w/{key}/documents").json()] == ["policy.txt"]

    store.hits = [SearchHit(1, "doc-1", 1, "Refunds take 30 days.", 0.03)]
    llm.replies = ["Refunds take 30 days [1]."]
    response = client.post(f"/w/{key}/ask", json={"question": "Refund window?"})
    assert response.status_code == 200
    body = response.json()
    assert body["found"] is True
    assert body["citations"] == [
        {"number": 1, "document_id": "doc-1", "page": 1, "content": "Refunds take 30 days."}
    ]


def test_unknown_workspace_is_404(client):
    assert client.get("/w/nope/documents").status_code == 404
    assert client.post("/w/nope/ask", json={"question": "hi"}).status_code == 404


def test_upload_errors(client, monkeypatch):
    key = new_demo(client)
    assert upload(client, key, name="photo.png").status_code == 415
    assert upload(client, key, content=b"   ").status_code == 422

    monkeypatch.setattr(api, "MAX_UPLOAD_BYTES", 10)
    assert upload(client, key, content=b"x" * 11).status_code == 413


def test_demo_document_limit(client):
    key = new_demo(client)
    for _ in range(api.DEMO_MAX_DOCUMENTS):
        assert upload(client, key).status_code == 201
    assert upload(client, key).status_code == 409


def test_non_demo_workspace_rejects_uploads(client, store):
    workspace = store.create_workspace("Client", is_demo=False)
    assert upload(client, workspace.public_key).status_code == 403


def test_question_validation(client):
    key = new_demo(client)
    assert client.post(f"/w/{key}/ask", json={"question": ""}).status_code == 422
    assert client.post(f"/w/{key}/ask", json={"question": "x" * 1001}).status_code == 422


def test_gemini_outage_is_503(client, store, llm):
    key = new_demo(client)
    store.hits = [SearchHit(1, "doc-1", 1, "text", 0.1)]

    def boom(*args, **kwargs):
        raise LLMError("down")

    llm.generate = boom
    assert client.post(f"/w/{key}/ask", json={"question": "q?"}).status_code == 503


def test_rate_limit_on_demo_creation(client):
    for _ in range(5):
        new_demo(client)
    assert client.post("/demo/workspaces").status_code == 429


def test_rate_limiter_window_slides():
    now = [0.0]
    limiter = RateLimiter(max_calls=2, per_seconds=10, clock=lambda: now[0])
    assert limiter.allow("ip") and limiter.allow("ip")
    assert not limiter.allow("ip")
    assert limiter.allow("other-ip")
    now[0] = 10.0
    assert limiter.allow("ip")
