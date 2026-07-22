import { config } from "../config.js";
import type { AnalysisProvider, AnalysisProviderId } from "../types.js";
import { OpenAiCompatibleAnalysisProvider } from "./openai-compatible.js";
import { RulesAnalysisProvider } from "./rules.js";

export function createAnalysisProvider(id: AnalysisProviderId): AnalysisProvider {
  switch (id) {
    case "rules":
      return new RulesAnalysisProvider();
    case "llama-cpp":
      return new OpenAiCompatibleAnalysisProvider({
        provider: "llama-cpp",
        model: config.llamaCpp.analysisModel,
        baseUrl: config.llamaCpp.baseUrl,
        timeoutMs: config.analysisTimeoutMs,
        maxInputChars: config.analysisMaxCharsPerSegment
      });
    case "mistral":
      if (!config.mistral.apiKey) throw new Error("MISTRAL_API_KEY est obligatoire pour l'analyse Mistral.");
      return new OpenAiCompatibleAnalysisProvider({
        provider: "mistral",
        model: config.mistral.analysisModel,
        baseUrl: config.mistral.baseUrl,
        apiKey: config.mistral.apiKey,
        timeoutMs: config.analysisTimeoutMs,
        maxInputChars: config.analysisMaxCharsPerSegment
      });
  }
}
