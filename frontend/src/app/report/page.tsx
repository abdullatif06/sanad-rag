import type { Metadata } from "next";
import { Suspense } from "react";
import { Header } from "@/components/Header";
import { Report } from "@/components/Report";

export const metadata: Metadata = {
  title: "Accuracy report — Sanad",
};

export default function ReportPage() {
  return (
    <>
      <Header />
      {/* Report reads the URL's search params, which must sit inside Suspense. */}
      <Suspense>
        <Report />
      </Suspense>
    </>
  );
}
