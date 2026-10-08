// Finds the sentence(s) in a cited passage that best support an answer, so the
// UI can mark them like a highlighter on a printed page.

const ARABIC_DIACRITICS = /[ً-ٰٟ]/g;
const ARABIC_INDIC_DIGITS = "٠١٢٣٤٥٦٧٨٩";
const SENTENCE_SPLIT = /(?<=[.!?؟\n])\s+/;
const TOKEN = /[\p{L}\p{N}]+/gu;
const STOPWORDS = new Set([
  "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are", "be", "can", "with", "at", "by",
  "في", "من", "على", "الى", "عن", "او", "و", "ان", "هي", "هو", "مع", "ما", "التي", "الذي",
]);

// Mirrors backend/app/normalize.py, plus Arabic-Indic digits so "٣٠" matches "30".
export function normalize(text: string): string {
  return text
    .replace(ARABIC_DIACRITICS, "")
    .replace(/ـ/g, "")
    .replace(/[أإآٱ]/g, "ا")
    .replace(/ى/g, "ي")
    .replace(/ة/g, "ه")
    .replace(/[٠-٩]/g, (d) => String(ARABIC_INDIC_DIGITS.indexOf(d)))
    .toLowerCase();
}

function tokens(text: string): Set<string> {
  const found = normalize(text).match(TOKEN) ?? [];
  return new Set(found.filter((t) => t.length > 1 && !STOPWORDS.has(t)));
}

export type Segment = { text: string; cited: boolean };

/** Splits `passage` into sentences and flags the one(s) sharing the most words with `answer`. */
export function highlightPassage(passage: string, answer: string): Segment[] {
  const answerTokens = tokens(answer.replace(/\[\d+\]/g, ""));
  const sentences = passage.split(SENTENCE_SPLIT);

  const scores = sentences.map((sentence) => {
    const own = tokens(sentence);
    if (own.size === 0) return 0;
    let overlap = 0;
    own.forEach((t) => answerTokens.has(t) && overlap++);
    return overlap / Math.sqrt(own.size);
  });

  const best = Math.max(0, ...scores);
  // Cross-language answers can share no words with the source: then mark nothing.
  const threshold = best >= 0.6 ? best * 0.75 : Infinity;
  return sentences.map((text, i) => ({ text, cited: scores[i] >= threshold }));
}
