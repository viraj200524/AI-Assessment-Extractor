import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "VedaAI Assessment Extractor",
  description: "Extract, map, and review handwritten assessments.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
