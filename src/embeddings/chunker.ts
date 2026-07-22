import { createHash } from "node:crypto";
import type { EmbeddingChunk, PageRecord } from "../types.js";

function cleanMarkdown(text: string): string {
  return text
    .replace(/<!--[^]*?-->/g, "")
    .replace(/\r\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function headingFor(text: string): string | undefined {
  const match = text.match(/^#{1,6}\s+(.+)$/m);
  return match?.[1]?.trim();
}

function splitWithOverlap(text: string, maxChars: number, overlapChars: number): string[] {
  if (text.length <= maxChars) return [text];
  const chunks: string[] = [];
  let start = 0;
  while (start < text.length) {
    let end = Math.min(start + maxChars, text.length);
    if (end < text.length) {
      const paragraphBreak = text.lastIndexOf("\n\n", end);
      const sentenceBreak = Math.max(text.lastIndexOf(". ", end), text.lastIndexOf("\n", end));
      const candidate = Math.max(paragraphBreak, sentenceBreak);
      if (candidate > start + Math.floor(maxChars * 0.55)) end = candidate + 1;
    }
    const value = text.slice(start, end).trim();
    if (value) chunks.push(value);
    if (end >= text.length) break;
    const next = Math.max(start + 1, end - overlapChars);
    start = next;
  }
  return chunks;
}

export function buildSemanticChunks(input: {
  documentId: string;
  pages: Array<{ page: PageRecord; markdown: string }>;
  maxChars: number;
  overlapChars: number;
}): EmbeddingChunk[] {
  const output: EmbeddingChunk[] = [];
  for (const item of [...input.pages].sort((a, b) => a.page.pageNumber - b.page.pageNumber)) {
    const cleaned = cleanMarkdown(item.markdown);
    if (!cleaned) continue;
    const parts = splitWithOverlap(cleaned, input.maxChars, Math.min(input.overlapChars, input.maxChars - 1));
    for (const [index, text] of parts.entries()) {
      const digest = createHash("sha256").update(`${item.page.sourceHash}:${index}:${text}`).digest("hex").slice(0, 16);
      const heading = headingFor(text);
      output.push({
        chunkId: `${input.documentId}_${item.page.pageId}_c${String(index + 1).padStart(3, "0")}_${digest}`,
        documentId: input.documentId,
        pageStart: item.page.pageNumber,
        pageEnd: item.page.pageNumber,
        contentType: "semantic_chunk",
        ...(heading ? { heading } : {}),
        text,
        sourceHash: item.page.sourceHash
      });
    }
  }
  return output;
}
