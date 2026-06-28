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

export default function Home() {
  return (
    <main style={{ minHeight: "100vh" }}>
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
