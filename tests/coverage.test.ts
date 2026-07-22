import assert from "node:assert/strict";
import test from "node:test";
import { computeCoverage } from "../src/core/coverage.js";
import type { DocumentManifest, PageRecord } from "../src/types.js";

function page(number: number, vision: boolean, status: PageRecord["status"]): PageRecord {
  return {
    pageNumber: number,
    pageId: `page_${String(number).padStart(4, "0")}`,
    sourceHash: `h${number}`,
    widthPt: 1,
    heightPt: 1,
    nativeTextChars: 1,
    nativeTextPath: "x",
    imageCount: 0,
    imageAreaRatio: 0,
    drawingCount: 0,
    estimatedInputTokens: 100,
    requiresVision: vision,
    status,
    attempts: 0,
    errors: []
  };
}

test("un document n'est complet que si toutes les pages réussissent", () => {
  const pages = [page(1, false, "native_success"), page(2, true, "vision_success")];
  const manifest = {
    totalPages: 2,
    pages,
    batches: [{
      batchId: "b1", childBatchIds: [], pageIds: [pages[1]!.pageId], estimatedInputTokens: 100,
      estimatedImageBytes: 0, status: "completed" as const, provider: "llama-cpp" as const,
      model: "x", attempt: 1, useFallbackImages: false, createdAt: "", updatedAt: "", errors: []
    }]
  } satisfies Pick<DocumentManifest, "totalPages" | "pages" | "batches">;
  const coverage = computeCoverage(manifest);
  assert.equal(coverage.isComplete, true);
  pages[1]!.status = "failed";
  assert.equal(computeCoverage(manifest).isComplete, false);
});

test("les doublons dans les lots feuilles sont détectés", () => {
  const pages = [page(1, true, "vision_success")];
  const common = {
    childBatchIds: [], pageIds: [pages[0]!.pageId], estimatedInputTokens: 100, estimatedImageBytes: 0,
    status: "completed" as const, provider: "llama-cpp" as const, model: "x", attempt: 1,
    useFallbackImages: false, createdAt: "", updatedAt: "", errors: []
  };
  const coverage = computeCoverage({ totalPages: 1, pages, batches: [
    { ...common, batchId: "b1" }, { ...common, batchId: "b2" }
  ]});
  assert.deepEqual(coverage.duplicateLeafAssignments, [pages[0]!.pageId]);
  assert.equal(coverage.isComplete, false);
});
