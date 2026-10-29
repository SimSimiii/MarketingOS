/** Compile-time compatibility between the view types and generated wire schemas. */
import type { ApiSchemas } from "./api-schema";
import type * as UI from "./types";
import type { EmailAnalysis, EmailAnalysisCapabilities, EmailAnalysisRequest } from "./email-analysis-types";

type Assert<T extends true> = T;
type Fits<A, B> = A extends B ? true : false;
// FastAPI serializes fields with defaults; they are optional only on input.
type Payload<T> = T extends readonly (infer Item)[] ? Payload<Item>[]
  : T extends object ? { [K in keyof T]-?: Payload<T[K]> } : T;

export type RequestContracts = [
  Assert<Fits<UI.KnowledgeCompilationRequest, ApiSchemas["CompilationRequest"]>>,
  Assert<Fits<ApiSchemas["CompilationRequest"], UI.KnowledgeCompilationRequest>>,
  Assert<Fits<UI.MarketScanRequest, ApiSchemas["ScanRequest"]>>,
  Assert<Fits<ApiSchemas["ScanRequest"], UI.MarketScanRequest>>,
  Assert<Fits<UI.MapOptions, ApiSchemas["MapAudienceRequest"]>>,
  Assert<Fits<UI.MarketAudienceJobRequest, ApiSchemas["ResearchAudienceRequest"]>>,
  Assert<Fits<ApiSchemas["ResearchAudienceRequest"], UI.MarketAudienceJobRequest>>,
  Assert<Fits<UI.MarketRelevanceJobRequest, ApiSchemas["RelevanceDossierRequest"]>>,
  Assert<Fits<ApiSchemas["RelevanceDossierRequest"], UI.MarketRelevanceJobRequest>>,
  Assert<Fits<UI.LinkedInSearchRequest, ApiSchemas["SearchRequest"]>>,
  Assert<Fits<UI.LinkedInCriteriaRequest, ApiSchemas["CriteriaRequest"]>>,
  Assert<Fits<UI.LinkedInCriteria, ApiSchemas["TargetingCriteria"]>>,
  Assert<Fits<EmailAnalysisRequest, ApiSchemas["EmailAnalysisRequest"]>>,
  Assert<Fits<UI.CampaignBriefUpdate, ApiSchemas["CampaignBriefUpdate"]>>,
  Assert<Fits<UI.CampaignCreateRequest, ApiSchemas["CampaignCreateRequest"]>>,
  Assert<Fits<ApiSchemas["CampaignCreateRequest"], UI.CampaignCreateRequest>>,
  Assert<Fits<UI.KnowledgeSourceCreate, ApiSchemas["KnowledgeSourceCreate"]>>,
  Assert<Fits<ApiSchemas["KnowledgeSourceCreate"], UI.KnowledgeSourceCreate>>,
  Assert<Fits<UI.BrandCreateRequest, ApiSchemas["BrandCreateRequest"]>>,
  Assert<Fits<UI.CampaignPolicyUpdate, ApiSchemas["CampaignPolicyUpdate"]>>,
];
export type ResponseContracts = [
  Assert<Fits<Payload<ApiSchemas["DefiningNeedFit"]>, NonNullable<UI.RelevanceDossier["defining_need_fit"]>>>,
  Assert<Fits<Payload<ApiSchemas["RivalProfileRead"]>, Omit<UI.RivalProfile, "kind">>>,
  Assert<Fits<Payload<ApiSchemas["CapabilityProfileRead"]>, UI.ProductCapabilityProfile>>,
  Assert<Fits<Payload<ApiSchemas["AudienceResearchRead"]>, UI.AudienceResearch>>,
  Assert<Fits<Payload<ApiSchemas["AxisReadingRead"]>, UI.AxisReading>>,
  Assert<Fits<Payload<ApiSchemas["ClaimRead"]>, UI.Claim>>,
  Assert<Fits<Payload<ApiSchemas["MapAssessment"]>, UI.MappedSegment["assessment"]>>,
  Assert<Fits<Payload<ApiSchemas["ProofCandidateRead"]>, UI.ProofCandidate>>,
  Assert<Fits<Payload<ApiSchemas["EmailAnalysisCapabilities"]>, EmailAnalysisCapabilities>>,
  Assert<Fits<Payload<ApiSchemas["TargetingCriteria"]>, UI.LinkedInCriteria>>,
  // Saved request/result JSON includes historical payloads; API regression tests
  // check their nested fields. Keep the persisted result metadata compatible.
  Assert<Fits<
    Omit<Payload<ApiSchemas["LinkedInRunRead"]>, "request" | "result" | "kind" | "state">,
    Omit<UI.LinkedInRun, "request" | "result" | "kind" | "state">
  >>,
  Assert<Fits<Payload<ApiSchemas["EmailAnalysisRead"]>, EmailAnalysis>>,
  Assert<Fits<Payload<ApiSchemas["CreditBalance"]>, UI.CreditBalance>>,
  Assert<Fits<Payload<ApiSchemas["RunForecast"]>, UI.RunForecast>>,
  Assert<Fits<Payload<ApiSchemas["CampaignExecutionRead"]>, UI.CampaignExecution>>,
  Assert<Fits<Payload<ApiSchemas["CampaignRead"]>, UI.Campaign>>,
  Assert<Fits<Payload<ApiSchemas["BrandRead"]>, UI.Brand>>,
  Assert<Fits<Payload<ApiSchemas["KnowledgeDocumentSummary"]>, UI.KnowledgeDocument>>,
  Assert<Fits<Payload<ApiSchemas["KnowledgeDocumentRead"]>, UI.KnowledgeDocumentDetail>>,
];
