import { Nav } from "@/components/Nav";
import { Hero } from "@/components/Hero";
import { AiEngines } from "@/components/AiEngines";
import { Manifesto } from "@/components/Manifesto";
import { Features } from "@/components/Features";
import { HowItWorks } from "@/components/HowItWorks";
import { McpSpotlight } from "@/components/McpSpotlight";
import { Confidence } from "@/components/Confidence";
import { Pricing } from "@/components/Pricing";
import { Faq } from "@/components/Faq";
import { AgencyCta } from "@/components/AgencyCta";
import { Footer } from "@/components/Footer";

export default function Home() {
  return (
    <main style={{ minHeight: "100vh" }}>
      <Nav />
      <Hero />
      <AiEngines />
      <Manifesto />
      <Features />
      <HowItWorks />
      <McpSpotlight />
      <Confidence />
      <Pricing />
      <Faq />
      <AgencyCta />
      <Footer />
    </main>
  );
}
