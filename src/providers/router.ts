import { config } from "../config.js";
import type { ProviderId } from "../types.js";
import type { OcrProvider } from "./base.js";
import { DisabledProvider } from "./none.js";
import { LlamaCppProvider } from "./llama-cpp.js";
import { MistralOcrProvider } from "./mistral-ocr.js";

export function createProvider(id: ProviderId): OcrProvider {
  switch (id) {
    case "llama-cpp":
      return new LlamaCppProvider(config.llamaCpp);
    case "mistral":
      return new MistralOcrProvider(config.mistral);
    case "none":
      return new DisabledProvider();
    default: {
      const exhaustive: never = id;
      throw new Error(`Fournisseur non géré: ${String(exhaustive)}`);
    }
  }
}
