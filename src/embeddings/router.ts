import { config } from "../config.js";
import type { EmbeddingProviderId } from "../types.js";
import type { EmbeddingProvider } from "./base.js";
import { HashEmbeddingProvider } from "./hash.js";
import { LlamaCppEmbeddingProvider } from "./llama-cpp.js";
import { MistralEmbeddingProvider } from "./mistral.js";

export function createEmbeddingProvider(id: EmbeddingProviderId): EmbeddingProvider {
  switch (id) {
    case "hash":
      return new HashEmbeddingProvider(config.hashEmbeddingDimensions);
    case "llama-cpp":
      return new LlamaCppEmbeddingProvider({
        baseUrl: config.llamaCpp.baseUrl,
        model: config.llamaCpp.embeddingModel,
        timeoutMs: config.llamaCpp.timeoutMs
      });
    case "mistral":
      return new MistralEmbeddingProvider({
        apiKey: config.mistral.apiKey,
        baseUrl: config.mistral.baseUrl,
        model: config.mistral.embeddingModel,
        timeoutMs: config.mistral.timeoutMs
      });
  }
}
