import type { EmbeddingProviderCapabilities } from "../types.js";

export interface EmbeddingProvider {
  readonly capabilities: EmbeddingProviderCapabilities;
  health(): Promise<{ ok: boolean; message: string }>;
  embed(texts: string[]): Promise<number[][]>;
}
