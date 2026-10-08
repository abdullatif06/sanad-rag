"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, type AskResult, type DocumentInfo } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { useLanguage } from "@/lib/i18n";
import { AnswerText } from "./AnswerText";
import { SourcePassage } from "./SourcePassage";

const MAX_DOCUMENTS = 3;

type Message = {
  id: number;
  question: string;
  startedAt: number;
  result?: AskResult;
  error?: string;
};

type Props = {
  publicKey: string;
  documents: DocumentInfo[];
  busy: string | null;
  error: string | null;
  onFile: (file: File) => void;
  onStartOver: () => void;
};

export function Workspace({ publicKey, documents, busy, error, onFile, onStartOver }: Props) {
  const { t } = useLanguage();
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [selected, setSelected] = useState<{ messageId: number; number: number } | null>(null);
  const [evalState, setEvalState] = useState<{ starting: boolean; error: string | null }>({
    starting: false,
    error: null,
  });
  const fileInput = useRef<HTMLInputElement>(null);
  const threadEnd = useRef<HTMLDivElement>(null);
  const nextId = useRef(1);

  const pending = messages.some((m) => !m.result && !m.error);
  const hasReady = documents.some((d) => d.status === "ready");

  // The margin shows sources for the selected answer, or the latest answered one.
  const answered = messages.filter((m) => m.result?.found);
  const focusMessage = messages.find((m) => m.id === selected?.messageId) ?? answered.at(-1);

  useEffect(() => {
    threadEnd.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length]);

  async function ask(text: string) {
    const q = text.trim();
    if (!q || pending) return;
    const id = nextId.current++;
    setQuestion("");
    setMessages((m) => [...m, { id, question: q, startedAt: Date.now() }]);
    try {
      const result = await api.ask(publicKey, q);
      setMessages((m) => m.map((msg) => (msg.id === id ? { ...msg, result } : msg)));
      if (result.citations.length) setSelected({ messageId: id, number: result.citations[0].number });
    } catch (e) {
      setMessages((m) => m.map((msg) => (msg.id === id ? { ...msg, error: errorMessage(e, t) } : msg)));
    }
  }

  function selectCitation(messageId: number, number: number) {
    setSelected({ messageId, number });
    document.getElementById(`source-${messageId}-${number}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  async function checkAccuracy() {
    setEvalState({ starting: true, error: null });
    try {
      const { run_id } = await api.startEvaluation(publicKey);
      router.push(`/report?key=${publicKey}&run=${run_id}`);
    } catch (e) {
      setEvalState({ starting: false, error: errorMessage(e, t) });
    }
  }

  return (
    <main className="mx-auto grid w-full max-w-6xl flex-1 gap-10 px-4 pt-8 pb-10 sm:px-6 lg:grid-cols-[minmax(0,1fr)_24rem]">
      <div className="flex min-w-0 flex-col">
        <DocumentList
          documents={documents}
          busy={busy}
          error={error}
          onAdd={() => fileInput.current?.click()}
          onStartOver={onStartOver}
        />
        <input
          ref={fileInput}
          type="file"
          accept=".pdf,.docx,.txt,.md"
          className="sr-only"
          tabIndex={-1}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onFile(file);
            e.target.value = "";
          }}
        />

        <section aria-label={t.askButton} className="mt-8 flex-1">
          {messages.length === 0 ? (
            <div>
              <p className="max-w-[56ch] text-muted">{t.emptyChat}</p>
              <ul className="mt-4 flex flex-wrap gap-2">
                {t.suggestions.map((s) => (
                  <li key={s}>
                    <button
                      type="button"
                      dir="auto"
                      onClick={() => ask(s)}
                      disabled={!hasReady}
                      className="rounded-full border border-rule px-4 py-1.5 text-sm transition-colors hover:border-ink disabled:opacity-50"
                    >
                      {s}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <ol className="space-y-8">
              {messages.map((m) => (
                <li key={m.id}>
                  <p dir="auto" className="font-medium">
                    {m.question}
                  </p>
                  <div className="mt-2">
                    {m.result ? (
                      <>
                        {!m.result.found && <p className="mb-1 text-sm text-muted">{t.notFound}</p>}
                        <AnswerText
                          text={m.result.answer}
                          citationNumbers={m.result.citations.map((c) => c.number)}
                          activeNumber={selected?.messageId === m.id ? selected.number : null}
                          onSelect={(n) => selectCitation(m.id, n)}
                          label={t.showSource}
                        />
                        {/* On small screens sources sit under their answer instead of in the margin. */}
                        {m.result.citations.length > 0 && (
                          <div className="mt-4 space-y-4 lg:hidden">
                            {m.result.citations.map((c) => (
                              <SourcePassage
                                key={c.number}
                                number={c.number}
                               
                                content={c.content}
                                answer={m.result!.answer}
                                pageLabel={t.page(c.page)}
                                active={selected?.messageId === m.id && selected.number === c.number}
                              />
                            ))}
                          </div>
                        )}
                      </>
                    ) : m.error ? (
                      <p role="alert" className="text-danger">
                        {m.error}
                      </p>
                    ) : (
                      <Pending startedAt={m.startedAt} />
                    )}
                  </div>
                </li>
              ))}
            </ol>
          )}
          <div ref={threadEnd} />
        </section>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            ask(question);
          }}
          className="sticky bottom-0 mt-8 flex gap-2 bg-paper py-4"
        >
          <label htmlFor="question" className="sr-only">
            {t.askPlaceholder}
          </label>
          <input
            id="question"
            dir="auto"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={t.askPlaceholder}
            maxLength={1000}
            disabled={!hasReady}
            className="min-w-0 flex-1 rounded-md border border-rule bg-surface px-4 py-3 placeholder:text-muted focus:border-accent focus:outline-none disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={pending || !question.trim() || !hasReady}
            className="rounded-md bg-accent px-6 font-medium text-accent-ink transition-opacity hover:opacity-90 disabled:opacity-40"
          >
            {t.askButton}
          </button>
        </form>
      </div>

      <aside className="hidden lg:block">
        <div className="sticky top-6 space-y-8">
          <section aria-labelledby="sources-heading">
            <h2 id="sources-heading" className="text-sm font-medium text-muted">
              {t.sources}
            </h2>
            {focusMessage?.result?.citations.length ? (
              <div className="mt-4 max-h-[60vh] space-y-6 overflow-y-auto pe-1">
                {focusMessage.result.citations.map((c) => (
                  <SourcePassage
                    key={c.number}
                    id={`source-${focusMessage.id}-${c.number}`}
                    number={c.number}
                   
                    content={c.content}
                    answer={focusMessage.result!.answer}
                    pageLabel={t.page(c.page)}
                    active={selected?.messageId === focusMessage.id && selected.number === c.number}
                  />
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm text-muted">{t.sourcesEmpty}</p>
            )}
          </section>

          <AccuracyCheck disabled={!hasReady} state={evalState} onStart={checkAccuracy} />
        </div>
      </aside>

      {/* On small screens the margin is hidden, so the check sits below the chat. */}
      <div className="lg:hidden">
        <AccuracyCheck disabled={!hasReady} state={evalState} onStart={checkAccuracy} />
      </div>
    </main>
  );
}

function AccuracyCheck({
  disabled,
  state,
  onStart,
}: {
  disabled: boolean;
  state: { starting: boolean; error: string | null };
  onStart: () => void;
}) {
  const { t } = useLanguage();
  return (
    <section className="border-t border-rule pt-6">
      <button
        type="button"
        onClick={onStart}
        disabled={disabled || state.starting}
        className="rounded-md border border-ink px-5 py-2.5 font-medium transition-colors hover:bg-ink hover:text-paper disabled:opacity-40"
      >
        {state.starting ? t.startingCheck : t.checkAccuracy}
      </button>
      <p className="mt-2 text-sm text-muted">{t.checkAccuracyHint}</p>
      {state.error && (
        <p role="alert" className="mt-2 text-sm text-danger">
          {state.error}
        </p>
      )}
    </section>
  );
}

function DocumentList({
  documents,
  busy,
  error,
  onAdd,
  onStartOver,
}: {
  documents: DocumentInfo[];
  busy: string | null;
  error: string | null;
  onAdd: () => void;
  onStartOver: () => void;
}) {
  const { t } = useLanguage();
  const full = documents.length >= MAX_DOCUMENTS;
  return (
    <section aria-labelledby="documents-heading" className="border-b border-rule pb-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 id="documents-heading" className="text-sm font-medium text-muted">
          {t.documents}
        </h2>
        <button type="button" onClick={onStartOver} className="text-sm text-muted underline underline-offset-4">
          {t.startOver}
        </button>
      </div>
      <ul className="mt-3 space-y-1.5">
        {documents.map((d) => (
          <li key={d.id} className="flex flex-wrap items-baseline gap-x-3">
            <span dir="auto" className="font-medium">
              {d.filename}
            </span>
            <span className={`text-sm ${d.status === "failed" ? "text-danger" : "text-muted"}`}>
              {d.status === "ready" && d.page_count
                ? t.pages(d.page_count)
                : d.status === "failed"
                  ? t.statusFailed
                  : t.statusProcessing}
            </span>
          </li>
        ))}
      </ul>
      <div className="mt-3 flex flex-wrap items-center gap-4 text-sm">
        {busy ? (
          <p role="status">{busy}</p>
        ) : full ? (
          <p className="text-muted">{t.fileLimit}</p>
        ) : (
          <button type="button" onClick={onAdd} className="text-accent underline underline-offset-4">
            {t.addFile}
          </button>
        )}
      </div>
      {error && (
        <p role="alert" className="mt-2 text-sm text-danger">
          {error}
        </p>
      )}
    </section>
  );
}

function Pending({ startedAt }: { startedAt: number }) {
  const { t } = useLanguage();
  const [now, setNow] = useState(startedAt);
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const seconds = Math.max(0, Math.round((now - startedAt) / 1000));
  return (
    <div role="status">
      <p className="text-muted">{t.thinking(seconds)}</p>
      {seconds >= 15 && <p className="mt-1 text-sm text-muted">{t.slowNote}</p>}
    </div>
  );
}
