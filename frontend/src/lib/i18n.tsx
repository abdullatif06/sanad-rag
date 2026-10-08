"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

export type Lang = "en" | "ar";

const STORAGE_KEY = "sanad.lang";

const en = {
  brandTagline: "Answers you can check",
  switchLanguage: "عربي",
  switchLanguageLabel: "Switch to Arabic",

  heroTitle: "Answers you can check.",
  heroBody:
    "Upload a policy, a manual or an FAQ. Ask in Arabic or English, and every answer shows the page and sentence it came from.",
  dropTitle: "Drop a file here, or choose one",
  dropHint: "PDF, Word, TXT or Markdown, up to 10 MB",
  chooseFile: "Choose a file",
  trySample: "Try it with a sample café policy",
  privacyNote:
    "Demo files are deleted after 24 hours. This demo uses Gemini's free tier, which Google may use to improve its products, so don't upload private documents.",

  creatingWorkspace: "Preparing your workspace…",
  uploading: (name: string) => `Reading ${name}…`,
  documents: "Your documents",
  addFile: "Add a file",
  fileLimit: "Demo limit reached: 3 files",
  pages: (n: number) => (n === 1 ? "1 page" : `${n} pages`),
  statusProcessing: "Processing",
  statusFailed: "Couldn't process",
  startOver: "Start over",

  askPlaceholder: "Ask a question about your documents",
  askButton: "Ask",
  thinking: (s: number) => `Searching your documents… ${s}s`,
  slowNote: "The free AI tier can take up to a minute.",
  suggestions: ["Can I get a refund on a latte?", "كم رسوم التوصيل؟", "Do you deliver outside Amman?"],
  emptyChat: "Ask anything the documents can answer. Questions they can't answer get an honest “not found”.",
  notFound: "Not in your documents",

  sources: "Sources",
  sourcesEmpty: "Sources for the selected answer appear here, with the supporting sentence marked.",
  page: (n: number) => `Page ${n}`,
  showSource: (n: number) => `Show source ${n}`,

  checkAccuracy: "Check accuracy",
  checkAccuracyHint: "Generates test questions from your files and scores the answers. Takes about two minutes.",
  startingCheck: "Starting…",

  errorNetwork: "Can't reach the Sanad server. Check that the backend is running.",
  errorGeneric: "Something went wrong. Try again.",
  errorBusy: "The AI service is busy. Wait a few seconds and ask again.",
  errorRateLimit: "Too many requests from this network. Wait a minute and try again.",
  errorUnsupported: "That file type isn't supported. Use PDF, Word, TXT or Markdown.",
  errorNoText: "That file has no readable text. Scanned PDFs aren't supported yet.",
  errorTooLarge: "That file is over 10 MB.",
  errorExpired: "This demo workspace has expired. Start a new one.",

  // Report
  reportTitle: "Accuracy report",
  reportRunning: "Writing test questions and answering them. This takes about two minutes.",
  reportFailed: "The accuracy check couldn't finish.",
  reportBack: "Back to your documents",
  reportIntro: (n: number) =>
    `Sanad wrote ${n} test questions from your own documents, half in English and half in Arabic, plus questions your documents can't answer. Then it answered each one and graded the results.`,
  metricLabels: {
    retrieval_hit_rate: "Finds the right passage",
    citation_accuracy: "Cites the right source",
    faithfulness: "Sticks to the documents",
    correctness: "Gives the correct answer",
    refusal_rate: "Says “not found” when it should",
  },
  metricHelp: {
    retrieval_hit_rate: "The passage a question was written from is among the search results.",
    citation_accuracy: "The answer cites the passage the question was written from.",
    faithfulness: "Every claim in the answer is supported by the cited text.",
    correctness: "The answer matches the expected answer.",
    refusal_rate: "Questions with no answer in the documents are declined, not guessed.",
  },
  byLanguage: "Correct answers by question language",
  languageName: { en: "English", ar: "Arabic" },
  latency: (p50: number, p95: number) =>
    `Typical answer time ${(p50 / 1000).toFixed(1)} s, slowest ${(p95 / 1000).toFixed(1)} s.`,
  questionsHeading: "Every test question",
  expected: "Expected",
  verdictCorrect: "Correct",
  verdictWrong: "Wrong",
  verdictRefused: "Declined correctly",
  verdictInvented: "Answered when it shouldn't",
  verdictMissed: "Didn't answer",
  verdictUngraded: "Not graded",
  notAvailable: "n/a",
};

export type Dictionary = typeof en;

const ar: Dictionary = {
  brandTagline: "إجابات يمكنك التحقق منها",
  switchLanguage: "English",
  switchLanguageLabel: "التبديل إلى الإنجليزية",

  heroTitle: "إجابات يمكنك التحقق منها.",
  heroBody:
    "ارفع سياسة أو دليل استخدام أو أسئلة شائعة. اسأل بالعربية أو الإنجليزية، وستعرض كل إجابة الصفحة والجملة التي جاءت منها.",
  dropTitle: "أفلت ملفاً هنا، أو اختر واحداً",
  dropHint: "PDF أو Word أو TXT أو Markdown، حتى ١٠ ميغابايت",
  chooseFile: "اختر ملفاً",
  trySample: "جرّبه على سياسة مقهى نموذجية",
  privacyNote:
    "تُحذف ملفات التجربة بعد ٢٤ ساعة. تستخدم هذه التجربة الباقة المجانية من Gemini، وقد تستخدمها Google لتحسين منتجاتها، فلا ترفع مستندات خاصة.",

  creatingWorkspace: "جارٍ تجهيز مساحة العمل…",
  uploading: (name) => `جارٍ قراءة ${name}…`,
  documents: "مستنداتك",
  addFile: "أضف ملفاً",
  fileLimit: "وصلت إلى حد التجربة: ٣ ملفات",
  pages: (n) => (n === 1 ? "صفحة واحدة" : n === 2 ? "صفحتان" : `${n} صفحات`),
  statusProcessing: "قيد المعالجة",
  statusFailed: "تعذّرت المعالجة",
  startOver: "ابدأ من جديد",

  askPlaceholder: "اسأل سؤالاً عن مستنداتك",
  askButton: "اسأل",
  thinking: (s) => `جارٍ البحث في مستنداتك… ${s} ث`,
  slowNote: "قد تستغرق الباقة المجانية حتى دقيقة.",
  suggestions: ["كم رسوم التوصيل؟", "Can I get a refund on a latte?", "هل يمكن حجز طاولة لأربعة أشخاص؟"],
  emptyChat: "اسأل عن أي شيء تجيب عنه المستندات. الأسئلة التي لا تجيب عنها تحصل على «غير موجود» بصدق.",
  notFound: "غير موجود في مستنداتك",

  sources: "المصادر",
  sourcesEmpty: "تظهر هنا مصادر الإجابة المحددة، مع تمييز الجملة الداعمة.",
  page: (n) => `صفحة ${n}`,
  showSource: (n) => `اعرض المصدر ${n}`,

  checkAccuracy: "افحص الدقة",
  checkAccuracyHint: "يكتب أسئلة اختبار من ملفاتك ويقيّم الإجابات. يستغرق نحو دقيقتين.",
  startingCheck: "جارٍ البدء…",

  errorNetwork: "تعذّر الوصول إلى خادم سند. تأكد من أن الخادم يعمل.",
  errorGeneric: "حدث خطأ. حاول مرة أخرى.",
  errorBusy: "خدمة الذكاء الاصطناعي مشغولة. انتظر بضع ثوانٍ واسأل مجدداً.",
  errorRateLimit: "طلبات كثيرة من هذه الشبكة. انتظر دقيقة ثم حاول مجدداً.",
  errorUnsupported: "نوع الملف غير مدعوم. استخدم PDF أو Word أو TXT أو Markdown.",
  errorNoText: "لا يحتوي الملف على نص قابل للقراءة. ملفات PDF الممسوحة ضوئياً غير مدعومة بعد.",
  errorTooLarge: "حجم الملف أكبر من ١٠ ميغابايت.",
  errorExpired: "انتهت صلاحية مساحة التجربة هذه. ابدأ واحدة جديدة.",

  reportTitle: "تقرير الدقة",
  reportRunning: "جارٍ كتابة أسئلة الاختبار والإجابة عنها. يستغرق ذلك نحو دقيقتين.",
  reportFailed: "تعذّر إكمال فحص الدقة.",
  reportBack: "العودة إلى مستنداتك",
  reportIntro: (n) =>
    `كتب سند ${n} من أسئلة الاختبار من مستنداتك نفسها، نصفها بالإنجليزية ونصفها بالعربية، إضافة إلى أسئلة لا تجيب عنها مستنداتك. ثم أجاب عن كل سؤال وقيّم النتائج.`,
  metricLabels: {
    retrieval_hit_rate: "يجد المقطع الصحيح",
    citation_accuracy: "يستشهد بالمصدر الصحيح",
    faithfulness: "يلتزم بما في المستندات",
    correctness: "يعطي الإجابة الصحيحة",
    refusal_rate: "يقول «غير موجود» عندما يجب",
  },
  metricHelp: {
    retrieval_hit_rate: "المقطع الذي كُتب منه السؤال موجود ضمن نتائج البحث.",
    citation_accuracy: "تستشهد الإجابة بالمقطع الذي كُتب منه السؤال.",
    faithfulness: "كل معلومة في الإجابة مدعومة بالنص المستشهد به.",
    correctness: "الإجابة تطابق الإجابة المتوقعة.",
    refusal_rate: "الأسئلة التي لا جواب لها في المستندات تُرفض ولا تُخمَّن.",
  },
  byLanguage: "الإجابات الصحيحة حسب لغة السؤال",
  languageName: { en: "الإنجليزية", ar: "العربية" },
  latency: (p50, p95) =>
    `زمن الإجابة المعتاد ${(p50 / 1000).toFixed(1)} ث، والأبطأ ${(p95 / 1000).toFixed(1)} ث.`,
  questionsHeading: "كل أسئلة الاختبار",
  expected: "المتوقع",
  verdictCorrect: "صحيحة",
  verdictWrong: "خاطئة",
  verdictRefused: "رُفض بشكل صحيح",
  verdictInvented: "أجاب حين كان يجب أن يرفض",
  verdictMissed: "لم يجب",
  verdictUngraded: "لم تُقيَّم",
  notAvailable: "غير متاح",
};

const dictionaries: Record<Lang, Dictionary> = { en, ar };

type LanguageContextValue = { lang: Lang; t: Dictionary; toggle: () => void };

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>("en");

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      // eslint-disable-next-line react-hooks/set-state-in-effect -- restoring a saved preference after hydration
      if (saved === "ar" || saved === "en") setLang(saved);
    } catch {
      // Storage can be unavailable (private mode); English is fine.
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  }, [lang]);

  const toggle = useCallback(() => {
    setLang((current) => {
      const next = current === "en" ? "ar" : "en";
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch {
        // ignore
      }
      return next;
    });
  }, []);

  return <LanguageContext value={{ lang, t: dictionaries[lang], toggle }}>{children}</LanguageContext>;
}

export function useLanguage(): LanguageContextValue {
  const value = useContext(LanguageContext);
  if (!value) throw new Error("useLanguage must be used inside LanguageProvider");
  return value;
}
