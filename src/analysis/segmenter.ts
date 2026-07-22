import type { AnalysisSegment, EmbeddingChunk } from "../types.js";

function estimateTokens(text: string): number {
  return Math.max(1, Math.ceil(text.length / 4));
}

export function buildAnalysisSegments(input: {
  chunks: EmbeddingChunk[];
  maxChars: number;
  maxChunks: number;
}): AnalysisSegment[] {
  const ordered = [...input.chunks].sort((a, b) =>
    a.pageStart - b.pageStart || a.pageEnd - b.pageEnd || a.chunkId.localeCompare(b.chunkId)
  );
  const segments: AnalysisSegment[] = [];
  let current: EmbeddingChunk[] = [];
  let chars = 0;

  const flush = (): void => {
    if (current.length === 0) return;
    const index = segments.length + 1;
    const text = current.map((chunk) => [
      `[[SOURCE_CHUNK ${chunk.chunkId} | pages ${chunk.pageStart}-${chunk.pageEnd}]]`,
      chunk.text
    ].join("\n")).join("\n\n");
    segments.push({
      segmentId: `segment_${String(index).padStart(4, "0")}`,
      chunkIds: current.map((chunk) => chunk.chunkId),
      pageStart: Math.min(...current.map((chunk) => chunk.pageStart)),
      pageEnd: Math.max(...current.map((chunk) => chunk.pageEnd)),
      text,
      estimatedTokens: estimateTokens(text)
    });
    current = [];
    chars = 0;
  };

  for (const chunk of ordered) {
    const addition = chunk.text.length + chunk.chunkId.length + 64;
    const mustFlush = current.length > 0 && (
      current.length >= input.maxChunks || chars + addition > input.maxChars
    );
    if (mustFlush) flush();
    current.push(chunk);
    chars += addition;
  }
  flush();
  return segments;
}

export function verifySegmentCoverage(chunks: EmbeddingChunk[], segments: AnalysisSegment[]): {
  missingChunkIds: string[];
  duplicateChunkIds: string[];
  isComplete: boolean;
} {
  const expected = new Set(chunks.map((chunk) => chunk.chunkId));
  const seen = new Map<string, number>();
  for (const segment of segments) {
    for (const chunkId of segment.chunkIds) seen.set(chunkId, (seen.get(chunkId) ?? 0) + 1);
  }
  const missingChunkIds = [...expected].filter((chunkId) => !seen.has(chunkId));
  const duplicateChunkIds = [...seen.entries()].filter(([, count]) => count > 1).map(([chunkId]) => chunkId);
  return {
    missingChunkIds,
    duplicateChunkIds,
    isComplete: missingChunkIds.length === 0 && duplicateChunkIds.length === 0
  };
}
