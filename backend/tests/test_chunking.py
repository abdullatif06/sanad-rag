import pytest

from app.chunking import Chunk, chunk_pages
from app.normalize import normalize
from app.parsing import Page


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("أحمد إلى آخر", "احمد الي اخر"),  # alef variants, alef maqsura
        ("مَدْرَسَةٌ", "مدرسه"),  # diacritics removed, taa marbuta
        ("كتـــاب", "كتاب"),  # tatweel
        ("Refund  POLICY\n", "refund policy"),  # lowercase, collapse spaces
    ],
)
def test_normalize(raw, expected):
    assert normalize(raw) == expected


def test_short_page_is_one_chunk():
    chunks = chunk_pages([Page(1, "Refunds take 30 days.")])
    assert chunks == [
        Chunk(index=0, page=1, text="Refunds take 30 days.", normalized="refunds take 30 days.")
    ]


def test_chunks_never_cross_pages():
    chunks = chunk_pages([Page(1, "Page one."), Page(4, "Page four.")])
    assert [(c.index, c.page, c.text) for c in chunks] == [(0, 1, "Page one."), (1, 4, "Page four.")]


def test_long_text_respects_max_and_splits_on_sentences():
    sentences = [f"Sentence number {i} is here." for i in range(50)]
    chunks = chunk_pages([Page(1, " ".join(sentences))], max_chars=200, overlap=0)
    assert len(chunks) > 1
    assert all(len(c.text) <= 200 for c in chunks)
    assert all(c.text.endswith(".") for c in chunks)
    # nothing lost
    joined = " ".join(c.text for c in chunks)
    assert all(s in joined for s in sentences)


def test_overlap_repeats_end_of_previous_chunk():
    sentences = [f"Fact {i} matters." for i in range(30)]
    chunks = chunk_pages([Page(1, " ".join(sentences))], max_chars=120, overlap=40)
    assert len(chunks) > 1
    for prev, cur in zip(chunks, chunks[1:]):
        last_sentence_of_prev = prev.text.rsplit(". ", 1)[-1]
        first_sentence_of_cur = cur.text.split(". ", 1)[0] + "."
        assert last_sentence_of_prev in cur.text
        assert first_sentence_of_cur in prev.text


def test_arabic_sentences_split_on_arabic_question_mark():
    text = " ".join(["ما هي سياسة الاسترجاع؟ يمكنك الاسترجاع خلال ثلاثين يوماً."] * 10)
    chunks = chunk_pages([Page(2, text)], max_chars=120, overlap=0)
    assert len(chunks) > 1
    assert all(len(c.text) <= 120 and c.page == 2 for c in chunks)


def test_single_huge_sentence_is_hard_split():
    word_soup = "word " * 500
    chunks = chunk_pages([Page(1, word_soup)], max_chars=100, overlap=0)
    assert all(len(c.text) <= 100 for c in chunks)
    assert sum(c.text.count("word") for c in chunks) == 500


def test_overlap_must_be_smaller_than_max():
    with pytest.raises(ValueError):
        chunk_pages([Page(1, "x")], max_chars=100, overlap=100)
