import assert from "node:assert/strict";
import test from "node:test";
import type { EmbeddingChunk } from "../src/types.js";
import { buildAnalysisSegments, verifySegmentCoverage } from "../src/analysis/segmenter.js";

function chunk(index: number): EmbeddingChunk {
  return {
    chunkId: `chunk_${String(index).padStart(4, "0")}`,
    documentId: "doc_test",
    pageStart: index,
    pageEnd: index,
    contentType: "semantic_chunk",
    text: `Contenu de la page ${index}. `.repeat(30),
    sourceHash: `hash_${index}`
  };
}

test("le partitionnement d'analyse couvre 200 chunks sans oubli ni doublon", () => {
  const chunks = Array.from({ length: 200 }, (_, index) => chunk(index + 1));
  const segments = buildAnalysisSegments({ chunks, maxChars: 6000, maxChunks: 7 });
  const coverage = verifySegmentCoverage(chunks, segments);
  assert.equal(coverage.isComplete, true);
  assert.deepEqual(coverage.missingChunkIds, []);
  assert.deepEqual(coverage.duplicateChunkIds, []);
  assert.ok(segments.every((segment) => segment.chunkIds.length <= 7));
  assert.deepEqual(segments.flatMap((segment) => segment.chunkIds), chunks.map((item) => item.chunkId));
});
