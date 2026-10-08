import type { Metadata } from "next";
import { Amiri, Readex_Pro } from "next/font/google";
import { LanguageProvider } from "@/lib/i18n";
import "./globals.css";

const readex = Readex_Pro({
  variable: "--font-readex",
  subsets: ["arabic", "latin"],
  axes: ["HEXP"],
});

const amiri = Amiri({
  variable: "--font-amiri",
  subsets: ["arabic", "latin"],
  weight: ["400", "700"],
});

export const metadata: Metadata = {
  title: "Sanad — answers you can check",
  description:
    "Upload your documents and ask in Arabic or English. Every answer points to the page and sentence it came from.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" dir="ltr" className={`${readex.variable} ${amiri.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <LanguageProvider>{children}</LanguageProvider>
      </body>
    </html>
  );
}
