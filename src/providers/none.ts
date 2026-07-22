import { ProviderError } from "../core/errors.js";
import type { OcrProvider } from "./base.js";

export class DisabledProvider implements OcrProvider {
  readonly id = "none" as const;
  readonly capabilities = {
    provider: "none" as const,
    model: "none",
    maxPagesPerBatch: 1,
    reservedOutputTokens: 0,
    safetyRatio: 1,
    supportsMultipleImages: false,
    usesOriginalPdf: false
  };

  async processBatch(): Promise<never> {
    throw new ProviderError(
      "Aucun fournisseur OCR n'est configuré. Les pages restent dans le workspace pour reprise.",
      "OCR_PROVIDER_DISABLED",
      false,
      false
    );
  }

  async health(): Promise<{ ok: boolean; detail: string }> {
    return { ok: false, detail: "OCR_PROVIDER=none" };
  }
}
