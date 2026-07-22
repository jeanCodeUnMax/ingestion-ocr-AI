import { randomUUID } from "node:crypto";
import { stat } from "node:fs/promises";
import type { BatchRecord, PageRecord, ProviderCapabilities } from "../types.js";

export function availableInputTokenBudget(capabilities: ProviderCapabilities): number | undefined {
  if (!capabilities.maxContextTokens) return undefined;
  return Math.max(
    1,
    Math.floor(capabilities.maxContextTokens * capabilities.safetyRatio) -
      capabilities.reservedOutputTokens
  );
}

export async function buildAdaptiveBatches(
  pages: PageRecord[],
  capabilities: ProviderCapabilities,
  now = new Date().toISOString()
): Promise<BatchRecord[]> {
  const visionPages = pages.filter((page) => page.requiresVision);
  const budget = availableInputTokenBudget(capabilities);
  const batches: BatchRecord[] = [];
  let current: PageRecord[] = [];
  let currentTokens = 0;
  let currentBytes = 0;

  async function imageBytes(page: PageRecord): Promise<number> {
    if (!page.imagePath) return 0;
    try {
      return (await stat(page.imagePath)).size;
    } catch {
      return 0;
    }
  }

  function flush(): void {
    if (current.length === 0) return;
    const batchId = `batch_${String(batches.length + 1).padStart(4, "0")}_${randomUUID().slice(0, 6)}`;
    batches.push({
      batchId,
      childBatchIds: [],
      pageIds: current.map((page) => page.pageId),
      estimatedInputTokens: currentTokens,
      estimatedImageBytes: currentBytes,
      status: "planned",
      provider: capabilities.provider,
      model: capabilities.model,
      attempt: 0,
      useFallbackImages: false,
      createdAt: now,
      updatedAt: now,
      errors: []
    });
    for (const page of current) page.batchId = batchId;
    current = [];
    currentTokens = 0;
    currentBytes = 0;
  }

  for (const page of visionPages) {
    const pageBytes = await imageBytes(page);
    const exceedsPageLimit = current.length >= capabilities.maxPagesPerBatch;
    const exceedsTokenBudget = budget !== undefined && current.length > 0 &&
      currentTokens + page.estimatedInputTokens > budget;
    const exceedsPayload = capabilities.maxPayloadBytes !== undefined && current.length > 0 &&
      currentBytes + pageBytes > capabilities.maxPayloadBytes;

    if (exceedsPageLimit || exceedsTokenBudget || exceedsPayload) flush();
    current.push(page);
    currentTokens += page.estimatedInputTokens;
    currentBytes += pageBytes;
  }
  flush();
  return batches;
}

export function splitBatch(
  batch: BatchRecord,
  pagesById: Map<string, PageRecord>,
  now = new Date().toISOString()
): [BatchRecord, BatchRecord] {
  if (batch.pageIds.length < 2) throw new Error("Impossible de scinder un lot d'une seule page.");
  const middle = Math.ceil(batch.pageIds.length / 2);
  const halves = [batch.pageIds.slice(0, middle), batch.pageIds.slice(middle)] as const;

  const makeChild = (ids: string[], suffix: string): BatchRecord => {
    const childId = `${batch.batchId}_${suffix}_${randomUUID().slice(0, 4)}`;
    const records = ids.map((id) => {
      const page = pagesById.get(id);
      if (!page) throw new Error(`Page inconnue: ${id}`);
      page.batchId = childId;
      return page;
    });
    return {
      batchId: childId,
      parentBatchId: batch.batchId,
      childBatchIds: [],
      pageIds: ids,
      estimatedInputTokens: records.reduce((sum, page) => sum + page.estimatedInputTokens, 0),
      estimatedImageBytes: Math.ceil(batch.estimatedImageBytes * (ids.length / batch.pageIds.length)),
      status: "planned",
      provider: batch.provider,
      model: batch.model,
      attempt: 0,
      useFallbackImages: batch.useFallbackImages,
      createdAt: now,
      updatedAt: now,
      errors: []
    };
  };
  return [makeChild([...halves[0]], "a"), makeChild([...halves[1]], "b")];
}
