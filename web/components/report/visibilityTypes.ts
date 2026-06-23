// Types for AI visibility (citation) sampling — the MEASURED layer.

export type Rate = {
  count: number; // successes
  n: number; // sample size
  rate: number; // count / n
  ci: [number, number]; // Wilson 95% interval, 0..1
};

export type PromptResult = {
  prompt: string;
  appeared: boolean; // brand named in the answer
  cited: boolean; // domain cited as a source
  found_not_cited: boolean; // domain surfaced in search but not cited in the answer
  competitors: string[]; // competitor brands named in the answer
  excerpt: string;
  error?: string;
};

export type ShareOfVoiceRow = { name: string; mentions: number; share: number; isTarget: boolean };

export type VisibilityReport = {
  scan_type: "visibility";
  confidence: "measured";
  brand: string;
  domain: string;
  engine: string; // e.g. "Claude (web search)"
  model: string;
  sampled_at: string;
  sample_size: number; // successful prompts
  requested: number; // prompts attempted
  visibility: Rate; // brand appeared
  citation: Rate; // domain cited
  share_of_voice: ShareOfVoiceRow[];
  prompts: PromptResult[];
};
