"""Text normalization for search, so spelling variants still match.

Used on chunks when they are stored and on questions when they are asked.
"""

import re

_ARABIC_DIACRITICS = re.compile(r"[ً-ٰٟ]")
_TATWEEL = "ـ"
_ALEF_VARIANTS = re.compile(r"[أإآٱ]")
_WHITESPACE = re.compile(r"\s+")


def normalize(text: str) -> str:
    text = _ARABIC_DIACRITICS.sub("", text)
    text = text.replace(_TATWEEL, "")
    text = _ALEF_VARIANTS.sub("ا", text)
    text = text.replace("ى", "ي").replace("ة", "ه")
    text = _WHITESPACE.sub(" ", text)
    return text.lower().strip()
