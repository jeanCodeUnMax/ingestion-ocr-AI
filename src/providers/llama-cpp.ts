import { readFile } from "node:fs/promises";
import path from "node:path";
import { classifyProviderFailure, ProviderError } from "../core/errors.js";
import type {
  OcrBatchRequest,
  OcrBatchResult,
  OcrPageResult,
  ProviderCapabilities
} from "../types.js";
import type { OcrProvider } from "./base.js";

interface LlamaCppOptions {
  baseUrl: string;
  model: string;
  contextTokens: number;
  maxPages: number;
  reservedOutputTokens: number;
  safetyRatio: number;
  timeoutMs: number;
}

const resultSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    pages: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        properties: {
          page_id: { type: "string" },
          markdown: { type: "string" },
          visual_description: { type: "string" },
          confidence: { type: "number" }
        },
        required: ["page_id", "markdown", "visual_description", "confidence"]
      }
    }
  },
  required: ["pages"]
};

function stripCodeFence(value: string): string {
  const trimmed = value.trim();
  if (!trimmed.startsWith("```")) return trimmed;
  return trimmed.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "");
}

function parseContent(content: string): { pages: Array<{ page_id: string; markdown: string; visual_description: string; confidence: number }> } {
  const cleaned = stripCodeFence(content);
  try {
    return JSON.parse(cleaned) as ReturnType<typeof parseContent>;
  } catch {
    const start = cleaned.indexOf("{");
    const end = cleaned.lastIndexOf("}");
    if (start >= 0 && end > start) {
      return JSON.parse(cleaned.slice(start, end + 1)) as ReturnType<typeof parseContent>;
    }
    throw new ProviderError("llama.cpp n'a pas retourné un JSON exploitable.", "INVALID_PROVIDER_JSON", true, false);
  }
}

export class LlamaCppProvider implements OcrProvider {
  readonly id = "llama-cpp" as const;
  readonly capabilities: ProviderCapabilities;

  constructor(private readonly options: LlamaCppOptions) {
    this.capabilities = {
      provider: this.id,
      model: options.model,
      maxPagesPerBatch: options.maxPages,
      maxContextTokens: options.contextTokens,
      reservedOutputTokens: options.reservedOutputTokens,
      safetyRatio: options.safetyRatio,
      supportsMultipleImages: true,
      usesOriginalPdf: false
    };
  }

  async health(): Promise<{ ok: boolean; detail: string }> {
    try {
      const response = await fetch(`${this.options.baseUrl}/models`, {
        signal: AbortSignal.timeout(Math.min(this.options.timeoutMs, 5000))
      });
      return response.ok
        ? { ok: true, detail: `llama-server joignable (${response.status})` }
        : { ok: false, detail: `llama-server HTTP ${response.status}` };
    } catch (error) {
      return { ok: false, detail: error instanceof Error ? error.message : String(error) };
    }
  }

  async processBatch(request: OcrBatchRequest): Promise<OcrBatchResult> {
    const content: Array<Record<string, unknown>> = [
      {
        type: "text",
        text: [
          "Tu es le moteur OCR de OCR AI System.",
          `Document: ${request.documentId}`,
          `Instruction utilisateur: ${request.instruction || "transcription fidèle"}`,
          "Chaque image correspond, dans l'ordre, à l'identifiant de page indiqué ci-dessous.",
          `Pages: ${request.pages.map((p) => p.pageId).join(", ")}`,
          "Retourne exactement un objet JSON conforme au schéma.",
          "Pour chaque page: transcription Markdown fidèle, titres, listes, tableaux, formules, nombres et négations.",
          "Décris aussi les dessins, graphiques et illustrations sans inventer. Utilise [ILLISIBLE] si nécessaire.",
          "Ne résume pas et ne mélange jamais le contenu de deux pages."
        ].join("\n")
      }
    ];

    for (const page of request.pages) {
      const selected = request.useFallbackImages ? page.fallbackImagePath : page.imagePath;
      if (!selected) {
        throw new ProviderError(`Image absente pour ${page.pageId}`, "MISSING_PAGE_IMAGE", false, false);
      }
      const data = await readFile(selected);
      const extension = path.extname(selected).toLowerCase() === ".jpg" ? "jpeg" : "png";
      content.push({
        type: "text",
        text: `PAGE_ID=${page.pageId}`
      });
      content.push({
        type: "image_url",
        image_url: { url: `data:image/${extension};base64,${data.toString("base64")}` }
      });
    }

    const payload = {
      model: this.options.model,
      temperature: 0,
      max_tokens: this.options.reservedOutputTokens,
      messages: [{ role: "user", content }],
      response_format: {
        type: "json_schema",
        json_schema: { name: "ocr_batch", strict: true, schema: resultSchema }
      }
    };

    const response = await fetch(`${this.options.baseUrl}/chat/completions`, {
      method: "POST",
      headers: { "content-type": "application/json", authorization: "Bearer no-key" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(this.options.timeoutMs)
    });
    if (!response.ok) throw classifyProviderFailure(response.status, await response.text());

    const raw = await response.json() as {
      choices?: Array<{ message?: { content?: string } }>;
    };
    const answer = raw.choices?.[0]?.message?.content;
    if (!answer) throw new ProviderError("Réponse llama.cpp vide.", "EMPTY_PROVIDER_RESPONSE", true, false);
    const parsed = parseContent(answer);
    const expected = new Set(request.pages.map((page) => page.pageId));
    const results: OcrPageResult[] = parsed.pages.map((page) => ({
      pageId: page.page_id,
      markdown: page.markdown,
      visualDescription: page.visual_description,
      confidence: page.confidence
    }));
    const returned = new Set(results.map((page) => page.pageId));
    const missing = [...expected].filter((id) => !returned.has(id));
    if (missing.length > 0) {
      throw new ProviderError(`llama.cpp a omis: ${missing.join(", ")}`, "PROVIDER_PAGE_OMISSION", true, true);
    }
    return { provider: this.id, model: this.options.model, pages: results, raw };
  }
}
