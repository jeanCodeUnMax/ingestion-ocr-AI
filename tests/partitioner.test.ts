import assert from "node:assert/strict";
import test from "node:test";
import { buildAdaptiveBatches, splitBatch } from "../src/core/partitioner.js";
import type { PageRecord, ProviderCapabilities } from "../src/types.js";

function page(number: number, tokens = 2000): PageRecord {
  return {
    pageNumber: number,
    pageId: `page_${String(number).padStart(4, "0")}`,
    sourceHash: `hash-${number}`,
    widthPt: 595,
    heightPt: 842,
    nativeTextChars: 0,
    nativeTextPath: `/tmp/native-${number}.txt`,
    imageCount: 1,
    imageAreaRatio: 1,
    drawingCount: 0,
    estimatedInputTokens: tokens,
    requiresVision: true,
    imagePath: `/missing/page-${number}.png`,
    fallbackImagePath: `/missing/page-${number}.low.png`,
    status: "vision_planned",
    attempts: 0,
    errors: []
  };
}

const capabilities: ProviderCapabilities = {
  provider: "llama-cpp",
  model: "test",
  maxPagesPerBatch: 10,
  maxContextTokens: 20000,
  reservedOutputTokens: 4000,
  safetyRatio: 0.75,
  supportsMultipleImages: true,
  usesOriginalPdf: false
};

test("200 pages sont affectées exactement une fois", async () => {
  const pages = Array.from({ length: 200 }, (_, i) => page(i + 1, 1000));
  const batches = await buildAdaptiveBatches(pages, capabilities);
  const assigned = batches.flatMap((batch) => batch.pageIds);
  assert.equal(assigned.length, 200);
  assert.equal(new Set(assigned).size, 200);
  assert.deepEqual(assigned, pages.map((p) => p.pageId));
});

test("le budget de contexte coupe avant la limite de pages", async () => {
  const pages = [page(1, 6000), page(2, 6000), page(3, 6000)];
  const batches = await buildAdaptiveBatches(pages, capabilities);
  assert.deepEqual(batches.map((batch) => batch.pageIds.length), [1, 1, 1]);
});

test("un lot trop grand est scindé sans perte", () => {
  const pages = [page(1), page(2), page(3), page(4), page(5)];
  const parent = {
    batchId: "batch_parent",
    childBatchIds: [],
    pageIds: pages.map((p) => p.pageId),
    estimatedInputTokens: 10000,
    estimatedImageBytes: 5000,
    status: "processing" as const,
    provider: "llama-cpp" as const,
    model: "test",
    attempt: 1,
    useFallbackImages: false,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    errors: []
  };
  const byId = new Map(pages.map((p) => [p.pageId, p]));
  const [left, right] = splitBatch(parent, byId);
  assert.deepEqual([...left.pageIds, ...right.pageIds], parent.pageIds);
  assert.equal(new Set([...left.pageIds, ...right.pageIds]).size, 5);
});
