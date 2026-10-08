"use client";

import { useEffect, useRef } from "react";
import { highlightPassage } from "@/lib/highlight";

type Props = {
  number: number;
  content: string;
  answer: string;
  pageLabel: string;
  active?: boolean;
  id?: string;
};

// Markdown heading markers ("## Refunds") read as noise inside a quoted passage.
const stripHeadingMarks = (text: string) => text.replace(/(^|\s)#{1,6}\s+/g, "$1");

/** A cited passage in the document's voice, with the supporting sentence marked. */
export function SourcePassage({ number, content, answer, pageLabel, active, id }: Props) {
  const segments = highlightPassage(stripHeadingMarks(content), answer);
  const quote = useRef<HTMLQuoteElement>(null);

  // Long passages scroll: bring the marked sentence into view inside the box.
  useEffect(() => {
    const box = quote.current;
    const mark = box?.querySelector("mark");
    if (box && mark) box.scrollTop = Math.max(0, mark.offsetTop - 24);
  }, [content, answer]);

  return (
    <figure
      id={id}
      className={`border-s-2 ps-4 transition-colors ${active ? "border-accent" : "border-rule"}`}
    >
      <figcaption className="mb-1 flex items-baseline gap-2 text-sm text-muted">
        <span className={`font-medium ${active ? "text-accent" : "text-ink"}`}>[{number}]</span>
        <span>{pageLabel}</span>
      </figcaption>
      <blockquote ref={quote} dir="auto" className="source-text relative max-h-72 overflow-y-auto whitespace-pre-line">
        {segments.map((segment, i) => (
          <span key={i}>
            {i > 0 && " "}
            {segment.cited ? <mark className="cited">{segment.text}</mark> : segment.text}
          </span>
        ))}
      </blockquote>
    </figure>
  );
}
