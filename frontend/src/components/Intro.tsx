"use client";

import { useRef, useState } from "react";
import { useLanguage } from "@/lib/i18n";
import { AnswerText } from "./AnswerText";
import { SourcePassage } from "./SourcePassage";

const ACCEPT = ".pdf,.docx,.txt,.md";

const SPECIMEN = {
  en: {
    question: "Can I get a refund on a latte?",
    answer: "No. Prepared drinks and food cannot be refunded, but a wrong order will be remade [1].",
    source:
      "Unopened packaged products can be returned within 14 days with a receipt. Prepared drinks and food cannot be refunded, but we will remake any order that is wrong.",
  },
  ar: {
    question: "كم رسوم التوصيل؟",
    answer: "رسوم التوصيل دينار ونصف، والتوصيل مجاني للطلبات التي تزيد عن عشرة دنانير [1].",
    source:
      "نوصل الطلبات داخل عمّان فقط. رسوم التوصيل دينار ونصف، والتوصيل مجاني للطلبات التي تزيد عن عشرة دنانير. مدة التوصيل المتوقعة بين ٣٠ و٤٥ دقيقة.",
  },
};

type Props = {
  busy: string | null;
  error: string | null;
  onFile: (file: File) => void;
  onSample: () => void;
};

export function Intro({ busy, error, onFile, onSample }: Props) {
  const { lang, t } = useLanguage();
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const specimen = SPECIMEN[lang];

  return (
    <main className="mx-auto grid w-full max-w-6xl gap-12 px-4 pt-12 pb-20 sm:px-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] lg:gap-16 lg:pt-20">
      <section>
        <h1 className="display max-w-[14ch] text-[2.5rem] font-medium sm:text-6xl">{t.heroTitle}</h1>
        <p className="mt-6 max-w-[52ch] text-lg text-muted">{t.heroBody}</p>

        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            const file = e.dataTransfer.files[0];
            if (file && !busy) onFile(file);
          }}
          className={`mt-10 rounded-lg border-2 border-dashed p-6 transition-colors sm:p-8 ${
            dragging ? "border-accent bg-surface" : "border-rule"
          }`}
        >
          {busy ? (
            <p role="status" className="text-lg">
              {busy}
            </p>
          ) : (
            <>
              <p className="text-lg font-medium">{t.dropTitle}</p>
              <p className="mt-1 text-sm text-muted">{t.dropHint}</p>
              <div className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-3">
                <button
                  type="button"
                  onClick={() => input.current?.click()}
                  className="rounded-md bg-accent px-5 py-2.5 font-medium text-accent-ink transition-opacity hover:opacity-90"
                >
                  {t.chooseFile}
                </button>
                <button type="button" onClick={onSample} className="text-accent underline underline-offset-4">
                  {t.trySample}
                </button>
              </div>
            </>
          )}
          <input
            ref={input}
            type="file"
            accept={ACCEPT}
            className="sr-only"
            tabIndex={-1}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onFile(file);
              e.target.value = "";
            }}
          />
        </div>
        {error && (
          <p role="alert" className="mt-4 text-danger">
            {error}
          </p>
        )}
        <p className="mt-6 max-w-[60ch] text-sm text-muted">{t.privacyNote}</p>
      </section>

      {/* A specimen of what an answer looks like: the product's whole idea in one glance. */}
      <section aria-hidden="true" className="self-start rounded-lg bg-surface p-6 sm:p-8 lg:mt-4">
        <p dir="auto" className="font-medium">
          {specimen.question}
        </p>
        <div className="mt-3">
          <AnswerText text={specimen.answer} citationNumbers={[1]} activeNumber={1} label={t.showSource} />
        </div>
        <div className="mt-6">
          <SourcePassage number={1} content={specimen.source} answer={specimen.answer} pageLabel={t.page(1)} active />
        </div>
      </section>
    </main>
  );
}
