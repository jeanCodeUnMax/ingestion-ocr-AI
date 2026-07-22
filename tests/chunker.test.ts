import assert from "node:assert/strict";
import test from "node:test";
import { buildSemanticChunks } from "../src/embeddings/chunker.js";
import type { PageRecord } from "../src/types.js";

function page(pageNumber: number): PageRecord {
  return {
    pageNumber,
    pageId: `page_${String(pageNumber).padStart(4, "0")}`,
    sourceHash: `hash-${pageNumber}`,
    widthPt: 595,
    heightPt: 842,
    nativeTextChars: 5000,
    nativeTextPath: "native.txt",
    imageCount: 0,
    imageAreaRatio: 0,
    drawingCount: 0,
    estimatedInputTokens: 1000,
    requiresVision: false,
    status: "native_success",
    attempts: 0,
    errors: []
  };
}

test("le chunker conserve la page, le hash et produit des IDs stables", () => {
  const markdown = `# Méthode 5S\n\n${"Ranger et standardiser le poste de travail. ".repeat(80)}`;
  const first = buildSemanticChunks({
    documentId: "doc-test",
    pages: [{ page: page(1), markdown }],
    maxChars: 500,
    overlapChars: 80
  });
  const second = buildSemanticChunks({
    documentId: "doc-test",
    pages: [{ page: page(1), markdown }],
    maxChars: 500,
    overlapChars: 80
  });
  assert.ok(first.length > 1);
  assert.deepEqual(first.map((chunk) => chunk.chunkId), second.map((chunk) => chunk.chunkId));
  assert.ok(first.every((chunk) => chunk.pageStart === 1 && chunk.sourceHash === "hash-1"));
});
