import { Nav } from "@/components/Nav";
import { Hero } from "@/components/Hero";
import { AiEngines } from "@/components/AiEngines";
import { Manifesto } from "@/components/Manifesto";
import { Confidence } from "@/components/Confidence";
import { Features } from "@/components/Features";
import { Pricing } from "@/components/Pricing";
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
      <Confidence />
      <Pricing />
      <AgencyCta />
      <Footer />
    </main>
  );
}
