import { readFile } from "node:fs/promises";
import { classifyProviderFailure, ProviderError } from "../core/errors.js";
import type {
  OcrBatchRequest,
  OcrBatchResult,
  ProviderCapabilities
} from "../types.js";
import type { OcrProvider } from "./base.js";

interface MistralOptions {
  apiKey: string;
  baseUrl: string;
  model: string;
  maxPages: number;
  timeoutMs: number;
}

function ranges(pageNumbersZeroBased: number[]): string {
  const sorted = [...new Set(pageNumbersZeroBased)].sort((a, b) => a - b);
  const parts: string[] = [];
  let start = sorted[0];
  let previous = sorted[0];
  if (start === undefined) return "";
  for (let index = 1; index < sorted.length; index += 1) {
    const current = sorted[index];
    if (current === undefined) continue;
    if (previous !== undefined && current === previous + 1) {
      previous = current;
      continue;
    }
    parts.push(start === previous ? String(start) : `${start}-${previous}`);
    start = current;
    previous = current;
  }
  parts.push(start === previous ? String(start) : `${start}-${previous}`);
  return parts.join(",");
}

export class MistralOcrProvider implements OcrProvider {
  readonly id = "mistral" as const;
  readonly capabilities: ProviderCapabilities;

  constructor(private readonly options: MistralOptions) {
    this.capabilities = {
      provider: this.id,
      model: options.model,
      maxPagesPerBatch: options.maxPages,
      reservedOutputTokens: 0,
      safetyRatio: 1,
      maxPayloadBytes: 512 * 1024 * 1024,
      supportsMultipleImages: true,
      usesOriginalPdf: true
    };
  }

  async health(): Promise<{ ok: boolean; detail: string }> {
    if (!this.options.apiKey) return { ok: false, detail: "MISTRAL_API_KEY absente" };
    return { ok: true, detail: "Clé Mistral configurée" };
  }

  async processBatch(request: OcrBatchRequest): Promise<OcrBatchResult> {
    if (!this.options.apiKey) {
      throw new ProviderError("MISTRAL_API_KEY absente.", "MISSING_MISTRAL_API_KEY", false, false);
    }
    const pdf = await readFile(request.sourcePdfPath);
    const pages = request.pages.map((page) => page.pageNumber - 1);
    const payload = {
      model: this.options.model,
      document: {
        type: "document_url",
        document_url: `data:application/pdf;base64,${pdf.toString("base64")}`
      },
      pages: ranges(pages),
      table_format: "markdown",
      include_blocks: true,
      confidence_scores_granularity: "page"
    };
    const response = await fetch(`${this.options.baseUrl}/ocr`, {
      method: "POST",
      headers: {
        authorization: `Bearer ${this.options.apiKey}`,
        "content-type": "application/json"
      },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(this.options.timeoutMs)
    });
    if (!response.ok) throw classifyProviderFailure(response.status, await response.text());
    const raw = await response.json() as {
      model?: string;
      pages?: Array<{
        index: number;
        markdown?: string;
        images?: unknown[];
        blocks?: unknown[];
        confidence_scores?: { average_page_confidence_score?: number };
      }>;
    };
    const byNumber = new Map(request.pages.map((page) => [page.pageNumber - 1, page]));
    const results = (raw.pages ?? []).map((page) => {
      const record = byNumber.get(page.index);
      if (!record) {
        throw new ProviderError(`Mistral a retourné une page inattendue: ${page.index}`, "UNEXPECTED_PROVIDER_PAGE", false, false);
      }
      const visualDescription = (page.images?.length ?? 0) > 0
        ? `${page.images?.length ?? 0} illustration(s) détectée(s). Description détaillée à produire par une étape vision.`
        : "Aucune illustration distincte signalée par OCR.";
      const result = {
        pageId: record.pageId,
        markdown: page.markdown ?? "[AUCUN TEXTE EXTRAIT]",
        visualDescription,
        raw: { blocks: page.blocks, images: page.images }
      };
      const confidence = page.confidence_scores?.average_page_confidence_score;
      return confidence === undefined ? result : { ...result, confidence };
    });
    const returned = new Set(results.map((page) => page.pageId));
    const missing = request.pages.map((page) => page.pageId).filter((id) => !returned.has(id));
    if (missing.length > 0) {
      throw new ProviderError(`Mistral OCR a omis: ${missing.join(", ")}`, "PROVIDER_PAGE_OMISSION", true, true);
    }
    return { provider: this.id, model: raw.model ?? this.options.model, pages: results, raw };
  }
}
