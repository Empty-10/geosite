import type { Metadata } from "next";

import { SITE_URL } from "@/lib/site";
import { Nav } from "@/components/Nav";
import { Hero } from "@/components/Hero";
import { AiEngines } from "@/components/AiEngines";
import { Manifesto } from "@/components/Manifesto";
import { Features } from "@/components/Features";
import { HowItWorks } from "@/components/HowItWorks";
import { McpSpotlight } from "@/components/McpSpotlight";
import { WhoItsFor } from "@/components/WhoItsFor";
import { Confidence } from "@/components/Confidence";
import { Pricing } from "@/components/Pricing";
import { Faq } from "@/components/Faq";
import { FinalCta } from "@/components/FinalCta";
import { Footer } from "@/components/Footer";

export const metadata: Metadata = {
  alternates: { canonical: "/" },
};

// Organization + WebSite structured data so AI engines and search can extract a clean entity.
const JSON_LD = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": `${SITE_URL}/#org`,
      name: "Astova",
      url: `${SITE_URL}/`,
      logo: `${SITE_URL}/icon.svg`,
      description:
        "GEO/SEO intelligence that scans your site for AI-search readiness and hands you the fix, not just the finding.",
    },
    {
      "@type": "WebSite",
      "@id": `${SITE_URL}/#website`,
      name: "Astova",
      url: `${SITE_URL}/`,
      publisher: { "@id": `${SITE_URL}/#org` },
    },
  ],
};

export default function Home() {
  return (
    <main style={{ minHeight: "100vh" }}>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD) }} />
      <Nav />
      <Hero />
      <AiEngines />
      <McpSpotlight />
      <Manifesto />
      <Features />
      <HowItWorks />
      <WhoItsFor />
      <Confidence />
      <Pricing />
      <Faq />
      <FinalCta />
      <Footer />
    </main>
  );
}
