/** Compile-time compatibility between the view types and generated wire schemas. */
import type { ApiSchemas } from "./api-schema";
import type * as UI from "./types";

type Assert<T extends true> = T;
type Fits<A, B> = A extends B ? true : false;
// FastAPI serializes fields with defaults; they are optional only on input.
type Payload<T> = T extends readonly (infer Item)[] ? Payload<Item>[]
  : T extends object ? { [K in keyof T]-?: Payload<T[K]> } : T;

export type RequestContracts = [
  Assert<Fits<UI.CampaignCreateRequest, ApiSchemas["CampaignCreateRequest"]>>,
  Assert<Fits<ApiSchemas["CampaignCreateRequest"], UI.CampaignCreateRequest>>,
  Assert<Fits<UI.KnowledgeSourceCreate, ApiSchemas["KnowledgeSourceCreate"]>>,
  Assert<Fits<ApiSchemas["KnowledgeSourceCreate"], UI.KnowledgeSourceCreate>>,
  Assert<Fits<UI.BrandCreateRequest, ApiSchemas["BrandCreateRequest"]>>,
  Assert<Fits<UI.CampaignPolicyUpdate, ApiSchemas["CampaignPolicyUpdate"]>>,
];
export type ResponseContracts = [
  Assert<Fits<Payload<ApiSchemas["CampaignRead"]>, UI.Campaign>>,
  Assert<Fits<Payload<ApiSchemas["BrandRead"]>, UI.Brand>>,
  Assert<Fits<Payload<ApiSchemas["KnowledgeDocumentSummary"]>, UI.KnowledgeDocument>>,
  Assert<Fits<Payload<ApiSchemas["KnowledgeDocumentRead"]>, UI.KnowledgeDocumentDetail>>,
];
