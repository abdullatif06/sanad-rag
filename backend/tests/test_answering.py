import pytest

from app.answering import NOT_FOUND_MESSAGES, answer, detect_language
from app.store import SearchHit
from tests.fakes import FakeLLM, FakeStore

HITS = [
    SearchHit(11, "doc-a", 1, "Refunds are accepted within 30 days.", 0.03),
    SearchHit(12, "doc-a", 4, "Shipping takes 5 business days.", 0.02),
    SearchHit(13, "doc-b", 2, "Support is open Sunday to Thursday.", 0.01),
]


@pytest.mark.parametrize(
    ("text", "lang"),
    [
        ("What is the refund policy?", "en"),
        ("ما هي سياسة الاسترجاع؟", "ar"),
        ("ما هي سياسة refund؟", "ar"),
        ("1234 ?", "en"),
    ],
)
def test_detect_language(text, lang):
    assert detect_language(text) == lang


def test_answer_returns_text_and_cited_sources():
    store = FakeStore(hits=HITS)
    llm = FakeLLM(replies=["Refunds are accepted within 30 days [1]. Shipping takes 5 days [2][1]."])

    result = answer(store, llm, "ws-1", "Refund and shipping?")

    assert result.found
    assert result.language == "en"
    assert result.text.startswith("Refunds are accepted")
    assert [(c.number, c.chunk_id, c.page) for c in result.citations] == [(1, 11, 1), (2, 12, 4)]


def test_question_is_normalized_for_keyword_search():
    store = FakeStore(hits=HITS)
    llm = FakeLLM(replies=["x [1]"])
    answer(store, llm, "ws-1", "ما هي سياسة الإسترجاع؟")
    assert llm.queries == ["ما هي سياسة الإسترجاع؟"]  # embedding sees the original
    assert store.searches[0][2] == "ما هي سياسه الاسترجاع؟"  # keyword search sees normalized


def test_prompt_contains_numbered_sources_and_language_rule():
    store = FakeStore(hits=HITS)
    llm = FakeLLM(replies=["الجواب [3]"])
    answer(store, llm, "ws-1", "متى يفتح الدعم؟")

    prompt, system = llm.prompts[0]
    assert "[1] (page 1)" in prompt and "[3] (page 2)" in prompt
    assert "متى يفتح الدعم؟" in prompt
    assert "Arabic" in system


def test_citations_ignore_numbers_outside_the_sources():
    store = FakeStore(hits=HITS)
    llm = FakeLLM(replies=["Answer [2] and [9] and [0]."])
    result = answer(store, llm, "ws-1", "q?")
    assert [c.number for c in result.citations] == [2]


def test_not_found_reply_becomes_localized_message():
    store = FakeStore(hits=HITS)
    llm = FakeLLM(replies=["NOT_FOUND"])
    result = answer(store, llm, "ws-1", "ما هو سعر الذهب؟")
    assert not result.found
    assert result.text == NOT_FOUND_MESSAGES["ar"]
    assert result.citations == []


def test_no_search_hits_skips_the_llm():
    store = FakeStore(hits=[])
    llm = FakeLLM()
    result = answer(store, llm, "ws-1", "Anything?")
    assert not result.found
    assert result.text == NOT_FOUND_MESSAGES["en"]
    assert llm.prompts == []


def test_answer_without_any_citation_is_treated_as_not_found():
    store = FakeStore(hits=HITS)
    llm = FakeLLM(replies=["I think it is probably 30 days."])
    result = answer(store, llm, "ws-1", "Refunds?")
    assert not result.found
