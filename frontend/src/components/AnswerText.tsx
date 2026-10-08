"use client";

type Props = {
  text: string;
  citationNumbers: number[];
  activeNumber: number | null;
  /** Omit for a static, non-interactive rendering. */
  onSelect?: (n: number) => void;
  label: (n: number) => string;
};

const markerClass =
  "mx-0.5 inline-flex min-w-6 items-center justify-center rounded px-1 align-[0.15em] text-[0.72rem] font-medium leading-5 transition-colors";

/** Renders an answer, turning [n] markers into buttons that reveal source n. */
export function AnswerText({ text, citationNumbers, activeNumber, onSelect, label }: Props) {
  const parts = text.split(/(\[\d+\])/g);
  return (
    <p dir="auto" className="text-[1.05rem] leading-relaxed">
      {parts.map((part, i) => {
        const match = part.match(/^\[(\d+)\]$/);
        const n = match ? Number(match[1]) : null;
        if (n === null || !citationNumbers.includes(n)) return <span key={i}>{part}</span>;
        const active = n === activeNumber;
        const colors = active ? "bg-accent text-accent-ink" : "bg-marker text-marker-ink";
        if (!onSelect) {
          return (
            <span key={i} className={`${markerClass} ${colors}`}>
              {n}
            </span>
          );
        }
        return (
          <button
            key={i}
            type="button"
            onClick={() => onSelect(n)}
            aria-label={label(n)}
            aria-pressed={active}
            className={`${markerClass} ${colors} hover:bg-accent hover:text-accent-ink`}
          >
            {n}
          </button>
        );
      })}
    </p>
  );
}
