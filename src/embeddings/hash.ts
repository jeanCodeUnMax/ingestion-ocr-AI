import { createHash } from "node:crypto";
import type { EmbeddingProvider } from "./base.js";

function normalize(vector: number[]): number[] {
  const norm = Math.sqrt(vector.reduce((sum, value) => sum + value * value, 0));
  if (norm === 0) return vector;
  return vector.map((value) => value / norm);
}

function tokenize(text: string): string[] {
  return text
    .toLocaleLowerCase("fr")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .split(/[^a-z0-9_]+/i)
    .filter((token) => token.length > 1);
}

export class HashEmbeddingProvider implements EmbeddingProvider {
  readonly capabilities;

  constructor(private readonly dimensions: number) {
    this.capabilities = {
      provider: "hash" as const,
      model: `hashing-vector-v1-${dimensions}`,
      maxBatchSize: 256,
      dimension: dimensions
    };
  }

  async health(): Promise<{ ok: boolean; message: string }> {
    return { ok: true, message: "Embedding local déterministe disponible." };
  }

  async embed(texts: string[]): Promise<number[][]> {
    return texts.map((text) => {
      const vector = Array.from({ length: this.dimensions }, () => 0);
      const tokens = tokenize(text);
      for (const token of tokens) {
        const digest = createHash("sha256").update(token).digest();
        const index = digest.readUInt32BE(0) % this.dimensions;
        const sign = (digest[4]! & 1) === 0 ? 1 : -1;
        vector[index] = (vector[index] ?? 0) + sign * (1 + Math.log1p(token.length));
      }
      return normalize(vector);
    });
  }
}
