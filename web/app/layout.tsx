import type { Metadata } from "next";
import "./globals.css";

const DESCRIPTION =
  "damask scans your site and separates verified fact from measured estimate — then tells you what to fix, not just what's wrong.";

export const metadata: Metadata = {
  // TODO: set to the real domain once locked — used to build absolute OG/social URLs.
  metadataBase: new URL("https://damask.example"),
  title: {
    default: "damask — know exactly how AI engines see your site",
    template: "%s · damask",
  },
  description: DESCRIPTION,
  openGraph: {
    title: "damask — know exactly how AI engines see your site",
    description: DESCRIPTION,
    type: "website",
    siteName: "damask",
  },
  twitter: {
    card: "summary_large_image",
    title: "damask",
    description: DESCRIPTION,
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
