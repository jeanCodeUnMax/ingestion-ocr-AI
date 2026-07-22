import type {
  OcrBatchRequest,
  OcrBatchResult,
  ProviderCapabilities,
  ProviderId
} from "../types.js";

export interface OcrProvider {
  readonly id: ProviderId;
  readonly capabilities: ProviderCapabilities;
  processBatch(request: OcrBatchRequest): Promise<OcrBatchResult>;
  health(): Promise<{ ok: boolean; detail: string }>;
}
