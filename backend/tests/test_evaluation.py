import json
import random

import pytest

from app.evaluation import (
    UNANSWERABLE_QUESTIONS,
    EvaluationError,
    _percentile,
    compute_metrics,
    generate_test_cases,
    run_evaluation,
)
from app.store import EvalItem, SearchHit, StoredChunk
from tests.fakes import FakeLLM, FakeStore

CHUNKS = [
    StoredChunk(1, 1, "Unopened products can be returned within 14 days."),
    StoredChunk(2, 3, "رسوم التوصيل دينار ونصف."),
]
HITS = [SearchHit(c.id, "doc-1", c.page, c.content, 0.1) for c in CHUNKS]


def ticking_clock(step: float = 0.1):
    now = [0.0]

    def clock():
        now[0] += step
        return now[0]

    return clock


def generation_reply(*entries) -> str:
    return json.dumps(list(entries))


# generate_test_cases ---------------------------------------------------------


def test_generate_alternates_languages_and_maps_sources_to_chunks():
    llm = FakeLLM(
        replies=[
            generation_reply(
                {"source": 1, "language": "en", "question": "Q1?", "answer": "A1"},
                {"source": 2, "language": "ar", "question": "س٢؟", "answer": "ج٢"},
            )
        ]
    )
    cases = generate_test_cases(llm, CHUNKS, 2, random.Random(0))

    prompt, _ = llm.prompts[0]
    assert "languages: English" in prompt and "languages: Arabic" in prompt
    assert [c.language for c in cases] == ["en", "ar"]
    assert {c.expected_chunk_id for c in cases} == {1, 2}


def test_generate_reuses_chunks_when_there_are_fewer_than_questions():
    llm = FakeLLM(replies=[generation_reply({"source": 1, "question": "Q?", "answer": "A"})])
    generate_test_cases(llm, CHUNKS[:1], 3, random.Random(0))
    prompt, _ = llm.prompts[0]
    assert "Write 3 question(s), languages: English, Arabic, English" in prompt


def test_generate_drops_invalid_entries_and_caps_count():
    llm = FakeLLM(
        replies=[
            json.dumps(
                {
                    "questions": [
                        {"source": 9, "question": "out of range", "answer": "x"},
                        {"source": 1, "question": "", "answer": "x"},
                        {"source": "1", "question": "not an int", "answer": "x"},
                        {"source": 1, "question": "Good?", "answer": "Yes", "language": "fr"},
                        {"source": 1, "question": "Extra?", "answer": "Yes"},
                    ]
                }
            )
        ]
    )
    cases = generate_test_cases(llm, CHUNKS[:1], 1, random.Random(0))
    assert [(c.question, c.language) for c in cases] == [("Good?", "en")]


def test_generate_raises_when_nothing_usable():
    with pytest.raises(EvaluationError):
        generate_test_cases(FakeLLM(replies=["[]"]), CHUNKS, 2, random.Random(0))
    with pytest.raises(EvaluationError):
        generate_test_cases(FakeLLM(replies=["not json"]), CHUNKS, 2, random.Random(0))


# run_evaluation --------------------------------------------------------------


def make_run(replies):
    store = FakeStore(hits=HITS, stored_chunks=CHUNKS)
    llm = FakeLLM(replies=replies)
    run = store.create_eval_run("ws-1")
    return store, llm, run


def test_full_run_scores_and_saves_report():
    store, llm, run = make_run(
        [
            generation_reply(
                {"source": 1, "language": "en", "question": "Return window?", "answer": "14 days"},
                {"source": 2, "language": "ar", "question": "كم رسوم التوصيل؟", "answer": "دينار ونصف"},
            ),
            "14 days [1][2].",  # answer to question 1
            "دينار ونصف [1][2].",  # answer to question 2
            "NOT_FOUND",  # unanswerable 1
            "NOT_FOUND",  # unanswerable 2
            json.dumps(
                [{"id": 0, "faithful": True, "correct": True}, {"id": 1, "faithful": True, "correct": False}]
            ),
        ]
    )

    metrics = run_evaluation(store, llm, "ws-1", run.id, num_questions=2, rng=random.Random(0), clock=ticking_clock())

    assert store.get_eval_run(run.id).status == "done"
    assert store.get_eval_run(run.id).metrics == metrics
    assert metrics == {
        "questions": 4,
        "retrieval_hit_rate": 1.0,
        "answer_rate": 1.0,
        "citation_accuracy": 1.0,
        "faithfulness": 1.0,
        "correctness": 0.5,
        "refusal_rate": 1.0,
        "latency_p50_ms": 100,
        "latency_p95_ms": 100,
        "by_language": {"en": {"questions": 1, "correctness": 1.0}, "ar": {"questions": 1, "correctness": 0.0}},
    }
    items = store.list_eval_items(run.id)
    assert [i.question for i in items[2:]] == [q for q, _ in UNANSWERABLE_QUESTIONS]
    assert items[0].scores["reference_answer"] == "14 days"


def test_assistant_inventing_an_answer_to_unanswerable_question_lowers_refusal_rate():
    store, llm, run = make_run(
        [
            generation_reply({"source": 1, "question": "Q?", "answer": "A"}),
            "A [1].",
            "The CEO lives in Amman [1].",  # invented!
            "NOT_FOUND",
            json.dumps([{"id": 0, "faithful": True, "correct": True}]),
        ]
    )
    metrics = run_evaluation(store, llm, "ws-1", run.id, num_questions=1, rng=random.Random(0), clock=ticking_clock())
    assert metrics["refusal_rate"] == 0.5


def test_judge_failure_keeps_the_rest_of_the_report():
    store, llm, run = make_run(
        [
            generation_reply({"source": 1, "question": "Q?", "answer": "A"}),
            "A [1].",
            "NOT_FOUND",
            "NOT_FOUND",
            "judge returned garbage",
        ]
    )
    metrics = run_evaluation(store, llm, "ws-1", run.id, num_questions=1, rng=random.Random(0), clock=ticking_clock())
    assert metrics["faithfulness"] is None
    assert metrics["retrieval_hit_rate"] == 1.0
    assert metrics["refusal_rate"] == 1.0


def test_run_without_documents_fails_cleanly():
    store, llm, run = make_run([])
    store.stored_chunks = []
    assert run_evaluation(store, llm, "ws-1", run.id) is None
    failed = store.get_eval_run(run.id)
    assert failed.status == "failed"
    assert "Upload at least one document" in failed.metrics["error"]


# metrics helpers -------------------------------------------------------------


def item(kind="answerable", language="en", **scores) -> EvalItem:
    return EvalItem("q", language, 1, "a", [], {"kind": kind, "latency_ms": 10, **scores})


def test_metrics_ignore_unknown_values_and_handle_missing_groups():
    items = [
        item(found=False, retrieval_hit=False, cited_expected=None, faithful=None, correct=False),
        item(found=True, retrieval_hit=True, cited_expected=False, faithful=None, correct=None),
    ]
    metrics = compute_metrics(items)
    assert metrics["answer_rate"] == 0.5
    assert metrics["citation_accuracy"] == 0.0
    assert metrics["faithfulness"] is None
    assert metrics["correctness"] == 0.0
    assert metrics["refusal_rate"] is None
    assert "ar" not in metrics["by_language"]


@pytest.mark.parametrize(("values", "p", "expected"), [([], 50, None), ([5], 95, 5), ([1, 2, 3, 4], 50, 2), ([1, 2, 3, 4], 95, 4)])
def test_percentile(values, p, expected):
    assert _percentile(values, p) == expected
