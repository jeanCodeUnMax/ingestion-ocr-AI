import { readFile } from "node:fs/promises";
import path from "node:path";
import { config } from "../config.js";
import { buildAnalysisEmbeddingChunks } from "../analysis/pipeline.js";
import { createEmbeddingProvider } from "../embeddings/router.js";
import type { AnalysisBundle, DocumentManifest, StoredVectorChunk } from "../types.js";
import { atomicWriteText } from "../utils/files.js";
import type { ManifestStore } from "./manifest-store.js";
import type { WorkspacePaths } from "./workspace.js";
import type { SqliteVectorStore } from "../vector/sqlite-vector-store.js";
import { loadTranscriptionChunks } from "./source-chunks.js";
import { loadKnowledgeEmbeddingChunks } from "../knowledge/enrichment.js";

function iso(): string {
  return new Date().toISOString();
}

export async function indexDocument(input: {
  manifest: DocumentManifest;
  workspace: WorkspacePaths;
  store: ManifestStore;
  vectorStore: SqliteVectorStore;
}): Promise<void> {
  const provider = createEmbeddingProvider(input.manifest.embeddingProvider);
  input.manifest.status = "embedding";
  input.manifest.embedding = {
    provider: input.manifest.embeddingProvider,
    model: provider.capabilities.model,
    status: "processing",
    chunksExpected: 0,
    chunksEmbedded: 0,
    transcriptionChunks: 0,
    analysisChunks: 0,
    vectorStore: config.vectorDbPath,
    errors: []
  };
  await input.store.save(input.manifest, "embedding_started", {
    provider: input.manifest.embeddingProvider,
    model: provider.capabilities.model
  });

  try {
    const transcriptionChunks = await loadTranscriptionChunks(input.manifest, input.workspace);
    let analysisChunks = [] as ReturnType<typeof buildAnalysisEmbeddingChunks>;
    const bundlePath = path.join(input.workspace.analysis, "synthesis.json");
    if (input.manifest.analysis.status === "complete") {
      const bundle = JSON.parse(await readFile(bundlePath, "utf8")) as AnalysisBundle;
      analysisChunks = buildAnalysisEmbeddingChunks(bundle);
    }
    const knowledgeChunks = await loadKnowledgeEmbeddingChunks(input.manifest, input.workspace);
    const chunks = [...transcriptionChunks, ...analysisChunks, ...knowledgeChunks];
    input.manifest.embedding.transcriptionChunks = transcriptionChunks.length;
    input.manifest.embedding.analysisChunks = analysisChunks.length;
    input.manifest.knowledge.indexedChunks = knowledgeChunks.length;
    input.manifest.analysis.indexedChunks = analysisChunks.length;
    input.manifest.embedding.chunksExpected = chunks.length;
    await atomicWriteText(
      path.join(input.workspace.embeddings, "chunks.jsonl"),
      `${chunks.map((chunk) => JSON.stringify({ ...chunk, embeddingStatus: "pending" })).join("\n")}${chunks.length ? "\n" : ""}`
    );
    await input.store.save(input.manifest, "chunks_created", {
      total: chunks.length,
      transcription: transcriptionChunks.length,
      analysis: analysisChunks.length,
      knowledge: knowledgeChunks.length
    });

    input.vectorStore.deleteDocument(input.manifest.documentId);
    const embeddedRows: StoredVectorChunk[] = [];
    const maxBatchSize = Math.max(1, Math.min(config.embeddingBatchSize, provider.capabilities.maxBatchSize));
    for (let offset = 0; offset < chunks.length; offset += maxBatchSize) {
      const batch = chunks.slice(offset, offset + maxBatchSize);
      const vectors = await provider.embed(batch.map((chunk) => chunk.text));
      if (vectors.length !== batch.length) {
        throw new Error(`Nombre de vecteurs invalide : ${vectors.length}/${batch.length}.`);
      }
      const now = iso();
      const stored = batch.map((chunk, index): StoredVectorChunk => {
        const embedding = vectors[index];
        if (!embedding || embedding.length === 0) throw new Error(`Vecteur vide pour ${chunk.chunkId}.`);
        return {
          ...chunk,
          embeddingModel: provider.capabilities.model,
          dimension: embedding.length,
          embedding,
          createdAt: now
        };
      });
      input.vectorStore.upsertMany(stored);
      embeddedRows.push(...stored);
      input.manifest.embedding.chunksEmbedded = embeddedRows.length;
      if (stored[0]) input.manifest.embedding.dimension = stored[0].dimension;
      await input.store.save(input.manifest, "embedding_batch_completed", {
        offset,
        batchSize: stored.length,
        embedded: input.manifest.embedding.chunksEmbedded,
        expected: chunks.length
      });
    }

    input.manifest.embedding.status = "complete";
    input.manifest.embedding.indexedAt = iso();
    await atomicWriteText(
      path.join(input.workspace.embeddings, "embedding_manifest.json"),
      `${JSON.stringify(input.manifest.embedding, null, 2)}\n`
    );
    await atomicWriteText(
      path.join(input.workspace.embeddings, "chunks.embedded.jsonl"),
      `${embeddedRows.map((chunk) => JSON.stringify({
        chunkId: chunk.chunkId,
        documentId: chunk.documentId,
        pageStart: chunk.pageStart,
        pageEnd: chunk.pageEnd,
        contentType: chunk.contentType,
        heading: chunk.heading,
        text: chunk.text,
        sourceHash: chunk.sourceHash,
        sourceChunkIds: chunk.sourceChunkIds,
        embeddingModel: chunk.embeddingModel,
        dimension: chunk.dimension
      })).join("\n")}${embeddedRows.length ? "\n" : ""}`
    );
    await input.store.save(input.manifest, "embedding_completed", {
      chunks: embeddedRows.length,
      dimension: input.manifest.embedding.dimension
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    input.manifest.embedding.status = "failed";
    input.manifest.embedding.errors.push({ at: iso(), code: "EMBEDDING_FAILED", message });
    await input.store.save(input.manifest, "embedding_failed", { message });
    throw error;
  }
}
