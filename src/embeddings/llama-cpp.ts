import type { EmbeddingProvider } from "./base.js";

interface LlamaEmbeddingResponse {
  data?: Array<{ embedding?: number[]; index?: number }>;
}

export class LlamaCppEmbeddingProvider implements EmbeddingProvider {
  readonly capabilities;

  constructor(
    private readonly settings: {
      baseUrl: string;
      model: string;
      timeoutMs: number;
    }
  ) {
    this.capabilities = {
      provider: "llama-cpp" as const,
      model: settings.model,
      maxBatchSize: 32
    };
  }

  async health(): Promise<{ ok: boolean; message: string }> {
    try {
      const response = await fetch(`${this.settings.baseUrl}/models`, {
        signal: AbortSignal.timeout(Math.min(this.settings.timeoutMs, 5000))
      });
      return response.ok
        ? { ok: true, message: "llama-server joignable pour les embeddings." }
        : { ok: false, message: `llama-server HTTP ${response.status}.` };
    } catch (error) {
      return { ok: false, message: error instanceof Error ? error.message : String(error) };
    }
  }

  async embed(texts: string[]): Promise<number[][]> {
    const response = await fetch(`${this.settings.baseUrl}/embeddings`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ model: this.settings.model, input: texts }),
      signal: AbortSignal.timeout(this.settings.timeoutMs)
    });
    if (!response.ok) {
      throw new Error(`llama.cpp embeddings HTTP ${response.status}: ${await response.text()}`);
    }
    const payload = await response.json() as LlamaEmbeddingResponse;
    const ordered = [...(payload.data ?? [])].sort((a, b) => (a.index ?? 0) - (b.index ?? 0));
    const vectors = ordered.map((item) => item.embedding).filter((value): value is number[] => Array.isArray(value));
    if (vectors.length !== texts.length) {
      throw new Error(`llama.cpp a retourné ${vectors.length} vecteurs pour ${texts.length} textes.`);
    }
    return vectors;
  }
}
