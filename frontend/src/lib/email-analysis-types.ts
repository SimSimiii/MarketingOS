export interface EmailAnalysisRequest {
  subject: string;
  preview_text?: string;
  body: string;
  audience?: string;
  objective?: string;
  merge_fields?: string[];
  cold_read?: boolean;
}

export interface EmailAnalysisCapabilities {
  cold_read_available: boolean;
  reason: string;
  expected_calls: number;
  schema_attempts: number;
}

export interface EmailAnalysis {
  id: string;
  brand_id: string;
  state: string;
  request: EmailAnalysisRequest;
  result: {
    findings: { category: "verification" | "editorial" | "context"; check: string; detail: string; action: string }[];
    knowledge_version: number | null;
    objective: string;
    forecast_calls: number;
    coverage: string[];
    reader: null | {
      reported: boolean;
      understood: boolean | null;
      what_it_sells: string;
      biggest_doubt: string;
      stopped_at: string;
      would_act: boolean | null;
      situation_matches: boolean | null;
      relevance_feedback: string;
      fixes: string[];
      assessment: number | null;
    };
  };
  error: string;
  calls: number;
  input_tokens: number;
  output_tokens: number;
  created_at: string;
  completed_at: string | null;
}
