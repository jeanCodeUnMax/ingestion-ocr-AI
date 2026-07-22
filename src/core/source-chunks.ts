import { readFile } from "node:fs/promises";
import path from "node:path";
import { config } from "../config.js";
import { buildSemanticChunks } from "../embeddings/chunker.js";
import type { DocumentManifest, EmbeddingChunk } from "../types.js";
import type { WorkspacePaths } from "./workspace.js";

export async function loadTranscriptionChunks(
  manifest: DocumentManifest,
  workspace: WorkspacePaths
): Promise<EmbeddingChunk[]> {
  const pageMarkdown: Array<{ page: DocumentManifest["pages"][number]; markdown: string }> = [];
  for (const page of [...manifest.pages].sort((a, b) => a.pageNumber - b.pageNumber)) {
    if (!page.outputMarkdownPath) continue;
    pageMarkdown.push({
      page,
      markdown: await readFile(path.join(workspace.root, page.outputMarkdownPath), "utf8")
    });
  }
  return buildSemanticChunks({
    documentId: manifest.documentId,
    pages: pageMarkdown,
    maxChars: config.chunkMaxChars,
    overlapChars: config.chunkOverlapChars
  });
}
