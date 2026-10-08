"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type EvalMetrics, type EvalReport, type EvalScores } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { useLanguage, type Dictionary } from "@/lib/i18n";

const POLL_MS = 4000;
const METRICS = ["correctness", "faithfulness", "citation_accuracy", "retrieval_hit_rate", "refusal_rate"] as const;

export function Report() {
  const { t } = useLanguage();
  const params = useSearchParams();
  const key = params.get("key");
  const runId = params.get("run");
  const [report, setReport] = useState<EvalReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!key || !runId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const load = async () => {
      try {
        const next = await api.getEvaluation(key, runId);
        if (cancelled) return;
        setReport(next);
        setError(null);
        if (next.status === "running") timer = setTimeout(load, POLL_MS);
      } catch (e) {
        if (!cancelled) setError(errorMessage(e, t));
      }
    };
    load();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [key, runId, t]);

  const metrics = report?.status === "done" ? report.metrics : null;
  const answerable = report?.items.filter((i) => i.scores.kind === "answerable").length ?? 0;

  return (
    <main className="mx-auto w-full max-w-3xl px-4 pt-10 pb-20 sm:px-6">
      <Link href="/" className="text-sm text-accent underline underline-offset-4">
        {t.reportBack}
      </Link>
      <h1 className="display mt-6 text-4xl font-medium sm:text-5xl">{t.reportTitle}</h1>

      {error && (
        <p role="alert" className="mt-6 text-danger">
          {error}
        </p>
      )}
      {!error && (!report || report.status === "running") && (
        <p role="status" className="mt-6 text-lg text-muted">
          {t.reportRunning}
        </p>
      )}
      {report?.status === "failed" && (
        <p role="alert" className="mt-6 text-danger">
          {t.reportFailed} {report.metrics?.error}
        </p>
      )}

      {metrics && (
        <>
          <p className="mt-6 max-w-[62ch] text-muted">{t.reportIntro(answerable)}</p>

          <dl className="mt-10 divide-y divide-rule border-y border-rule">
            {METRICS.map((name) => (
              <MetricRow key={name} label={t.metricLabels[name]} help={t.metricHelp[name]} value={metrics[name]} t={t} />
            ))}
          </dl>

          <LanguageSplit metrics={metrics} t={t} />

          {metrics.latency_p50_ms != null && metrics.latency_p95_ms != null && (
            <p className="mt-6 text-sm text-muted">{t.latency(metrics.latency_p50_ms, metrics.latency_p95_ms)}</p>
          )}

          <h2 className="mt-14 text-xl font-medium">{t.questionsHeading}</h2>
          <ol className="mt-6 space-y-6">
            {report!.items.map((item, i) => (
              <li key={i} className="border-s-2 border-rule ps-4">
                <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                  <p dir="auto" className="font-medium">
                    {item.question}
                  </p>
                  <Verdict scores={item.scores} t={t} />
                </div>
                <p dir="auto" className="mt-1 text-muted">
                  {item.answer}
                </p>
                {item.scores.reference_answer && (
                  <p className="mt-1 text-sm text-muted">
                    {t.expected}: <bdi>{item.scores.reference_answer}</bdi>
                  </p>
                )}
              </li>
            ))}
          </ol>
        </>
      )}
    </main>
  );
}

function MetricRow({ label, help, value, t }: { label: string; help: string; value: number | null; t: Dictionary }) {
  const percent = value == null ? null : Math.round(value * 100);
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-6 gap-y-2 py-5">
      <dt>
        <span className="font-medium">{label}</span>
        <span className="mt-0.5 block text-sm text-muted">{help}</span>
      </dt>
      <dd className="text-end text-3xl font-medium tabular-nums">{percent == null ? t.notAvailable : `${percent}%`}</dd>
      <div aria-hidden="true" className="col-span-2 h-1.5 overflow-hidden rounded-full bg-rule">
        <div className="h-full rounded-full bg-accent" style={{ width: `${percent ?? 0}%` }} />
      </div>
    </div>
  );
}

function LanguageSplit({ metrics, t }: { metrics: EvalMetrics; t: Dictionary }) {
  const entries = (["en", "ar"] as const).filter((lang) => metrics.by_language[lang]);
  if (!entries.length) return null;
  return (
    <section className="mt-8">
      <h2 className="text-sm font-medium text-muted">{t.byLanguage}</h2>
      <ul className="mt-2 flex flex-wrap gap-x-8 gap-y-1">
        {entries.map((lang) => {
          const split = metrics.by_language[lang]!;
          const correct = split.correctness == null ? null : Math.round(split.correctness * split.questions);
          return (
            <li key={lang}>
              {t.languageName[lang]}: <span className="font-medium tabular-nums">{correct ?? "–"}</span> / {split.questions}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function Verdict({ scores, t }: { scores: EvalScores; t: Dictionary }) {
  let text: string;
  let good: boolean | null;
  if (scores.kind === "unanswerable") {
    [text, good] = scores.found ? [t.verdictInvented, false] : [t.verdictRefused, true];
  } else if (!scores.found) {
    [text, good] = [t.verdictMissed, false];
  } else if (scores.correct == null) {
    [text, good] = [t.verdictUngraded, null];
  } else {
    [text, good] = scores.correct ? [t.verdictCorrect, true] : [t.verdictWrong, false];
  }
  const color = good == null ? "text-muted" : good ? "text-accent" : "text-danger";
  return <span className={`text-sm font-medium ${color}`}>{text}</span>;
}
