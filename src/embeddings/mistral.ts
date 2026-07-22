import type { EmbeddingProvider } from "./base.js";

interface MistralEmbeddingResponse {
  data?: Array<{ embedding?: number[]; index?: number }>;
}

export class MistralEmbeddingProvider implements EmbeddingProvider {
  readonly capabilities;

  constructor(
    private readonly settings: {
      apiKey: string;
      baseUrl: string;
      model: string;
      timeoutMs: number;
    }
  ) {
    this.capabilities = {
      provider: "mistral" as const,
      model: settings.model,
      maxBatchSize: 32
    };
  }

  async health(): Promise<{ ok: boolean; message: string }> {
    if (!this.settings.apiKey) return { ok: false, message: "MISTRAL_API_KEY absente." };
    return { ok: true, message: "Configuration Mistral embeddings présente." };
  }

  async embed(texts: string[]): Promise<number[][]> {
    if (!this.settings.apiKey) throw new Error("MISTRAL_API_KEY absente.");
    const response = await fetch(`${this.settings.baseUrl}/embeddings`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${this.settings.apiKey}`
      },
      body: JSON.stringify({ model: this.settings.model, input: texts }),
      signal: AbortSignal.timeout(this.settings.timeoutMs)
    });
    if (!response.ok) {
      throw new Error(`Mistral embeddings HTTP ${response.status}: ${await response.text()}`);
    }
    const payload = await response.json() as MistralEmbeddingResponse;
    const ordered = [...(payload.data ?? [])].sort((a, b) => (a.index ?? 0) - (b.index ?? 0));
    const vectors = ordered.map((item) => item.embedding).filter((value): value is number[] => Array.isArray(value));
    if (vectors.length !== texts.length) {
      throw new Error(`Mistral a retourné ${vectors.length} vecteurs pour ${texts.length} textes.`);
    }
    return vectors;
  }
}
