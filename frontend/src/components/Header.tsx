"use client";

import Link from "next/link";
import { useLanguage } from "@/lib/i18n";

export function Header() {
  const { t, toggle } = useLanguage();
  return (
    <header className="border-b border-rule">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <Link href="/" className="flex items-baseline gap-3 rounded-sm">
          <span lang="ar" className="font-source text-2xl font-bold leading-none">
            سند
          </span>
          <span className="text-lg font-medium leading-none tracking-tight">Sanad</span>
          <span className="hidden text-sm text-muted sm:inline">{t.brandTagline}</span>
        </Link>
        <button
          type="button"
          onClick={toggle}
          aria-label={t.switchLanguageLabel}
          className="rounded-full border border-rule px-4 py-1.5 text-sm transition-colors hover:border-ink"
        >
          {t.switchLanguage}
        </button>
      </div>
    </header>
  );
}
