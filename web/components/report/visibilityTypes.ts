// Types for multi-engine AI visibility (citation) sampling — the MEASURED layer.

export type Rate = {
  count: number; // successes
  n: number; // sample size
  rate: number; // count / n
  ci: [number, number]; // Wilson 95% interval, 0..1
};

export type EngineRate = { engine: string; visibility: Rate; citation: Rate };

export type ShareOfVoiceRow = { name: string; mentions: number; share: number; isTarget: boolean };

export type PromptCell = { engine: string; appeared: boolean; cited: boolean };

export type PromptResult = {
  prompt: string;
  cells: PromptCell[]; // one per engine that answered
  competitors: string[];
  excerpt: string;
};

export type VisibilityReport = {
  scan_type: "visibility";
  confidence: "measured";
  brand: string;
  domain: string;
  engines: string[]; // which engines ran
  sampled_at: string;
  sample_size: number; // total (engine × prompt) samples that succeeded
  requested: number; // prompts × engines attempted
  visibility: Rate; // overall: brand appeared
  citation: Rate; // overall: domain cited
  per_engine: EngineRate[];
  share_of_voice: ShareOfVoiceRow[]; // the headline metric
  prompts: PromptResult[];
};
