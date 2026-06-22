import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "damask — know exactly how AI engines see your site",
  description:
    "damask scans your site and separates verified fact from measured estimate — then tells you what to fix, not just what's wrong.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
