import type { Metadata } from "next";
import "./globals.css";
import { SITE_URL } from "@/lib/site";

// Apply the saved theme before paint so there's no dark→light flash on load.
const THEME_SCRIPT = `(function(){try{if(localStorage.getItem('astova-theme')==='light')document.documentElement.setAttribute('data-theme','light');}catch(e){}})();`;

const DESCRIPTION =
  "Astova scans your site and separates verified fact from measured estimate — then tells you what to fix, not just what's wrong.";

export const metadata: Metadata = {
  // Absolute base for OG/social/canonical URLs. Swap by setting NEXT_PUBLIC_SITE_URL when the
  // real domain is locked (see lib/site.ts).
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Astova — know exactly how AI engines see your site",
    template: "%s · Astova",
  },
  description: DESCRIPTION,
  openGraph: {
    title: "Astova — know exactly how AI engines see your site",
    description: DESCRIPTION,
    type: "website",
    siteName: "Astova",
  },
  twitter: {
    card: "summary_large_image",
    title: "Astova",
    description: DESCRIPTION,
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
        {children}
      </body>
    </html>
  );
}
