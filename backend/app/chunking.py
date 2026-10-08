"""Split page text into overlapping, sentence-aligned chunks for search.

Chunks never cross page boundaries, so every chunk cites exactly one page.
"""

import re
from dataclasses import dataclass

from app.normalize import normalize
from app.parsing import Page

DEFAULT_MAX_CHARS = 1000
DEFAULT_OVERLAP = 150

# Split after sentence-ending punctuation (English and Arabic) or a line break.
_SENTENCE_END = re.compile(r"(?<=[.!?؟\n])\s+")


@dataclass(frozen=True)
class Chunk:
    index: int
    page: int
    text: str
    normalized: str


def chunk_pages(
    pages: list[Page],
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    if not 0 <= overlap < max_chars:
        raise ValueError("overlap must be >= 0 and smaller than max_chars")

    chunks: list[Chunk] = []
    for page in pages:
        for text in _chunk_text(page.text, max_chars, overlap):
            chunks.append(Chunk(len(chunks), page.number, text, normalize(text)))
    return chunks


def _chunk_text(text: str, max_chars: int, overlap: int) -> list[str]:
    sentences = [
        piece
        for sentence in _SENTENCE_END.split(text.strip())
        if sentence.strip()
        for piece in _split_long(sentence.strip(), max_chars)
    ]

    results: list[str] = []
    current: list[str] = []
    has_new_content = False

    for sentence in sentences:
        if current and _joined_len(current + [sentence]) > max_chars:
            results.append(" ".join(current))
            current = _overlap_tail(current, overlap)
            has_new_content = False
            # Drop overlap sentences until the new sentence fits.
            while current and _joined_len(current + [sentence]) > max_chars:
                current.pop(0)
        current.append(sentence)
        has_new_content = True

    if current and has_new_content:
        results.append(" ".join(current))
    return results


def _split_long(sentence: str, max_chars: int) -> list[str]:
    """Hard-split a sentence longer than max_chars on word boundaries."""
    if len(sentence) <= max_chars:
        return [sentence]

    pieces: list[str] = []
    current = ""
    for word in sentence.split():
        while len(word) > max_chars:  # a single giant "word"
            if current:
                pieces.append(current)
                current = ""
            pieces.append(word[:max_chars])
            word = word[max_chars:]
        candidate = f"{current} {word}" if current else word
        if len(candidate) > max_chars:
            pieces.append(current)
            current = word
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces


def _overlap_tail(sentences: list[str], overlap: int) -> list[str]:
    """Trailing sentences whose combined length fits in `overlap`."""
    tail: list[str] = []
    for sentence in reversed(sentences):
        if _joined_len([sentence] + tail) > overlap:
            break
        tail.insert(0, sentence)
    return tail


def _joined_len(sentences: list[str]) -> int:
    return sum(len(s) for s in sentences) + max(len(sentences) - 1, 0)
