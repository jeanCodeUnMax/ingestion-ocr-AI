import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import path from "node:path";
import type { AnalysisBundle, DocumentManifest, EmbeddingChunk } from "../types.js";
import { atomicWriteJson, atomicWriteText } from "../utils/files.js";
import type { ManifestStore } from "../core/manifest-store.js";
import type { WorkspacePaths } from "../core/workspace.js";
import { loadTranscriptionChunks } from "../core/source-chunks.js";

function iso(): string { return new Date().toISOString(); }
function digest(value: string): string { return createHash("sha256").update(value).digest("hex"); }
function normalize(value: string): string { return value.toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, " ").trim(); }
function unique(values: string[]): string[] {
  const seen = new Set<string>();
  return values.filter((value) => { const key = normalize(value); if (!key || seen.has(key)) return false; seen.add(key); return true; });
}

function shrinkText(text: string): string {
  const cleaned = text.replace(/<!--[^>]*-->/g, " ").replace(/\s+/g, " ").trim();
  const sentences = cleaned.split(/(?<=[.!?])\s+/).filter(Boolean);
  const protectedSentences = sentences.filter((sentence) => /\d|\b(ne|n'|pas|jamais|aucun|sans|doit|interdit|exception|condition|si)\b/i.test(sentence));
  const selected = unique([...sentences.slice(0, 3), ...protectedSentences]).slice(0, 7);
  return selected.join(" ").slice(0, 1800) || cleaned.slice(0, 1800);
}

export interface AtomicFact {
  factId: string;
  key: string;
  value: string;
  classification: "explicit_fact" | "claim";
  confidence: "explicit" | "inferred";
  sourceChunkIds: string[];
}

export interface ShrunkChunk {
  shrinkId: string;
  sourceChunkId: string;
  pageStart: number;
  pageEnd: number;
  originalChars: number;
  shrunkChars: number;
  text: string;
  sourceHash: string;
}

export async function enrichKnowledge(input: {
  manifest: DocumentManifest;
  workspace: WorkspacePaths;
  store: ManifestStore;
}): Promise<{ chunks: EmbeddingChunk[] }> {
  const { manifest, workspace, store } = input;
  const recipe = manifest.recipe;
  if (!recipe.shrink && !recipe.atomicFacts && !recipe.tagsAndTaxonomy) {
    manifest.knowledge = { status: "skipped", atomicFacts: 0, shrunkChunks: 0, tags: 0, artifacts: {}, indexedChunks: 0, errors: [] };
    await store.save(manifest, "knowledge_skipped", {});
    return { chunks: [] };
  }

  manifest.knowledge = { status: "processing", atomicFacts: 0, shrunkChunks: 0, tags: 0, artifacts: {}, indexedChunks: 0, errors: [] };
  await store.save(manifest, "knowledge_started", { recipe });
  try {
    const sourceChunks = await loadTranscriptionChunks(manifest, workspace);
    let bundle: AnalysisBundle | undefined;
    try { bundle = JSON.parse(await readFile(path.join(workspace.analysis, "synthesis.json"), "utf8")) as AnalysisBundle; } catch { bundle = undefined; }
    const embeddingChunks: EmbeddingChunk[] = [];

    if (recipe.shrink) {
      const shrunk: ShrunkChunk[] = sourceChunks.map((chunk) => {
        const text = shrinkText(chunk.text);
        return {
          shrinkId: `shrink_${digest(`${chunk.chunkId}\n${text}`).slice(0, 18)}`,
          sourceChunkId: chunk.chunkId,
          pageStart: chunk.pageStart,
          pageEnd: chunk.pageEnd,
          originalChars: chunk.text.length,
          shrunkChars: text.length,
          text,
          sourceHash: chunk.sourceHash
        };
      });
      const jsonl = path.join(workspace.shrink, "shrink.jsonl");
      const markdown = path.join(workspace.shrink, "shrink.md");
      await atomicWriteText(jsonl, `${shrunk.map((item) => JSON.stringify(item)).join("\n")}${shrunk.length ? "\n" : ""}`);
      await atomicWriteText(markdown, shrunk.map((item) => `## ${item.shrinkId}\n\n<!-- source_chunk_id=${item.sourceChunkId} pages=${item.pageStart}-${item.pageEnd} -->\n\n${item.text}\n`).join("\n"));
      manifest.knowledge.shrunkChunks = shrunk.length;
      manifest.knowledge.artifacts.shrinkJsonl = path.relative(workspace.root, jsonl);
      manifest.knowledge.artifacts.shrinkMarkdown = path.relative(workspace.root, markdown);
      embeddingChunks.push(...shrunk.map((item): EmbeddingChunk => ({
        chunkId: `${manifest.documentId}_shrunk_${item.shrinkId}`,
        documentId: manifest.documentId,
        pageStart: item.pageStart,
        pageEnd: item.pageEnd,
        contentType: "shrunk_chunk",
        heading: `Shrink ${item.sourceChunkId}`,
        text: item.text,
        sourceHash: digest(item.text),
        sourceChunkIds: [item.sourceChunkId]
      })));
    }

    if (recipe.atomicFacts && bundle) {
      const candidates = bundle.semantic.flatMap((semantic) => [
        ...semantic.keyFacts.map((item) => ({ value: item.fact, classification: "explicit_fact" as const, confidence: "explicit" as const, sourceChunkIds: item.sourceChunkIds })),
        ...semantic.claims.map((item) => ({ value: item.statement, classification: "claim" as const, confidence: item.confidence, sourceChunkIds: item.sourceChunkIds }))
      ]);
      const seen = new Set<string>();
      const facts: AtomicFact[] = [];
      for (const candidate of candidates) {
        const key = normalize(candidate.value);
        if (!key || seen.has(key)) continue;
        seen.add(key);
        facts.push({
          factId: `fact_${digest(`${candidate.value}\n${candidate.sourceChunkIds.join(",")}`).slice(0, 18)}`,
          key: key.split(" ").slice(0, 8).join("_"),
          value: candidate.value,
          classification: candidate.classification,
          confidence: candidate.confidence,
          sourceChunkIds: candidate.sourceChunkIds
        });
      }
      const filePath = path.join(workspace.shrink, "atomic_facts.jsonl");
      await atomicWriteText(filePath, `${facts.map((item) => JSON.stringify(item)).join("\n")}${facts.length ? "\n" : ""}`);
      manifest.knowledge.atomicFacts = facts.length;
      manifest.knowledge.artifacts.atomicFactsJsonl = path.relative(workspace.root, filePath);
      embeddingChunks.push(...facts.map((fact): EmbeddingChunk => ({
        chunkId: `${manifest.documentId}_atomic_${fact.factId}`,
        documentId: manifest.documentId,
        pageStart: 1,
        pageEnd: Math.max(1, manifest.totalPages),
        contentType: "atomic_fact",
        heading: fact.key,
        text: `${fact.classification}: ${fact.value}`,
        sourceHash: digest(fact.value),
        sourceChunkIds: fact.sourceChunkIds
      })));
    }

    if (recipe.tagsAndTaxonomy) {
      const tags = unique(bundle ? bundle.semantic.flatMap((item) => [
        ...item.themes.map((theme) => theme.name),
        ...item.concepts.map((concept) => concept.name),
        ...item.entities.map((entity) => entity.name)
      ]) : sourceChunks.flatMap((chunk) => chunk.heading ? [chunk.heading] : [])).slice(0, 200);
      const taxonomy = {
        schemaVersion: "1.0",
        documentId: manifest.documentId,
        generatedAt: iso(),
        categories: {
          themes: unique(bundle?.semantic.flatMap((item) => item.themes.map((theme) => theme.name)) ?? []),
          concepts: unique(bundle?.semantic.flatMap((item) => item.concepts.map((concept) => concept.name)) ?? []),
          entities: unique(bundle?.semantic.flatMap((item) => item.entities.map((entity) => entity.name)) ?? [])
        }
      };
      const tagsPath = path.join(workspace.tags, "tags.json");
      const taxonomyPath = path.join(workspace.tags, "taxonomy.json");
      await atomicWriteJson(tagsPath, { schemaVersion: "1.0", documentId: manifest.documentId, tags });
      await atomicWriteJson(taxonomyPath, taxonomy);
      manifest.knowledge.tags = tags.length;
      manifest.knowledge.artifacts.tagsJson = path.relative(workspace.root, tagsPath);
      manifest.knowledge.artifacts.taxonomyJson = path.relative(workspace.root, taxonomyPath);
      if (tags.length) embeddingChunks.push({
        chunkId: `${manifest.documentId}_taxonomy_${digest(tags.join("\n")).slice(0, 18)}`,
        documentId: manifest.documentId,
        pageStart: 1,
        pageEnd: Math.max(1, manifest.totalPages),
        contentType: "tag_taxonomy",
        heading: "Tags et taxonomie",
        text: tags.join(", "),
        sourceHash: digest(tags.join("\n")),
        sourceChunkIds: sourceChunks.map((chunk) => chunk.chunkId)
      });
    }

    const knowledgeMap = {
      schemaVersion: "1.0",
      documentId: manifest.documentId,
      projectId: manifest.projectId ?? null,
      source: { filename: manifest.originalFilename, kind: manifest.inputKind, origin: manifest.sourceOrigin, pages: manifest.totalPages, sha256: manifest.sourceSha256 },
      coverage: manifest.coverage,
      recipe: manifest.recipe,
      artifacts: { transcription: "transcription/full_document.md", analysis: manifest.analysis.artifacts, knowledge: manifest.knowledge.artifacts, embeddings: "embeddings/embedding_manifest.json" },
      counts: { sourceChunks: sourceChunks.length, atomicFacts: manifest.knowledge.atomicFacts, shrunkChunks: manifest.knowledge.shrunkChunks, tags: manifest.knowledge.tags }
    };
    const mapPath = path.join(workspace.root, "knowledge_map.json");
    const indexPath = path.join(workspace.root, "index.md");
    await atomicWriteJson(mapPath, knowledgeMap);
    await atomicWriteText(indexPath, [
      `# Index documentaire — ${manifest.originalFilename}`,
      "",
      `- Document ID : \`${manifest.documentId}\``,
      `- Projet : \`${manifest.projectId ?? "standalone"}\``,
      `- Origine : ${manifest.sourceOrigin}`,
      `- Pages : ${manifest.totalPages}`,
      `- Couverture complète : ${manifest.coverage.isComplete ? "oui" : "non"}`,
      `- Chunks sources : ${sourceChunks.length}`,
      `- Shrinks : ${manifest.knowledge.shrunkChunks}`,
      `- Faits atomiques : ${manifest.knowledge.atomicFacts}`,
      `- Tags : ${manifest.knowledge.tags}`,
      "",
      "## Accès",
      "",
      "- [Transcription](transcription/full_document.md)",
      "- [Synthèse](analysis/synthesis.md)",
      "- [Gant de KENT](analysis/kent_glove/kent_glove.md)",
      "- [Pseudocode](analysis/pseudocode/pseudocode.md)",
      "- [Shrink](shrink/shrink.md)",
      "- [Carte de connaissance](knowledge_map.json)",
      ""
    ].join("\n"));
    manifest.knowledge.artifacts.knowledgeMapJson = path.relative(workspace.root, mapPath);
    manifest.knowledge.artifacts.indexMarkdown = path.relative(workspace.root, indexPath);
    embeddingChunks.push({
      chunkId: `${manifest.documentId}_index_${digest(JSON.stringify(knowledgeMap)).slice(0, 18)}`,
      documentId: manifest.documentId,
      pageStart: 1,
      pageEnd: Math.max(1, manifest.totalPages),
      contentType: "document_index",
      heading: `Index ${manifest.originalFilename}`,
      text: `Document ${manifest.originalFilename}. Origine ${manifest.sourceOrigin}. ${manifest.totalPages} pages. ${manifest.knowledge.tags} tags, ${manifest.knowledge.atomicFacts} faits atomiques, ${manifest.knowledge.shrunkChunks} chunks condensés.`,
      sourceHash: digest(JSON.stringify(knowledgeMap)),
      sourceChunkIds: sourceChunks.map((chunk) => chunk.chunkId)
    });

    manifest.knowledge.status = "complete";
    manifest.knowledge.indexedChunks = embeddingChunks.length;
    await store.save(manifest, "knowledge_completed", { chunks: embeddingChunks.length, facts: manifest.knowledge.atomicFacts, shrinks: manifest.knowledge.shrunkChunks, tags: manifest.knowledge.tags });
    return { chunks: embeddingChunks };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    manifest.knowledge.status = "failed";
    manifest.knowledge.errors.push({ at: iso(), code: "KNOWLEDGE_ENRICHMENT_FAILED", message });
    await store.save(manifest, "knowledge_failed", { message });
    throw error;
  }
}

export async function loadKnowledgeEmbeddingChunks(manifest: DocumentManifest, workspace: WorkspacePaths): Promise<EmbeddingChunk[]> {
  const chunks: EmbeddingChunk[] = [];
  if (manifest.knowledge.status !== "complete") return chunks;
  const shrinkPath = manifest.knowledge.artifacts.shrinkJsonl;
  if (shrinkPath) {
    const lines = (await readFile(path.join(workspace.root, shrinkPath), "utf8")).split(/\r?\n/).filter(Boolean);
    for (const line of lines) {
      const item = JSON.parse(line) as ShrunkChunk;
      chunks.push({ chunkId: `${manifest.documentId}_shrunk_${item.shrinkId}`, documentId: manifest.documentId, pageStart: item.pageStart, pageEnd: item.pageEnd, contentType: "shrunk_chunk", heading: `Shrink ${item.sourceChunkId}`, text: item.text, sourceHash: digest(item.text), sourceChunkIds: [item.sourceChunkId] });
    }
  }
  const factsPath = manifest.knowledge.artifacts.atomicFactsJsonl;
  if (factsPath) {
    const lines = (await readFile(path.join(workspace.root, factsPath), "utf8")).split(/\r?\n/).filter(Boolean);
    for (const line of lines) {
      const fact = JSON.parse(line) as AtomicFact;
      chunks.push({ chunkId: `${manifest.documentId}_atomic_${fact.factId}`, documentId: manifest.documentId, pageStart: 1, pageEnd: Math.max(1, manifest.totalPages), contentType: "atomic_fact", heading: fact.key, text: `${fact.classification}: ${fact.value}`, sourceHash: digest(fact.value), sourceChunkIds: fact.sourceChunkIds });
    }
  }
  const tagsPath = manifest.knowledge.artifacts.tagsJson;
  if (tagsPath) {
    const value = JSON.parse(await readFile(path.join(workspace.root, tagsPath), "utf8")) as { tags: string[] };
    if (value.tags.length) chunks.push({ chunkId: `${manifest.documentId}_taxonomy_${digest(value.tags.join("\n")).slice(0, 18)}`, documentId: manifest.documentId, pageStart: 1, pageEnd: Math.max(1, manifest.totalPages), contentType: "tag_taxonomy", heading: "Tags et taxonomie", text: value.tags.join(", "), sourceHash: digest(value.tags.join("\n")) });
  }
  const mapPath = manifest.knowledge.artifacts.knowledgeMapJson;
  if (mapPath) {
    const mapText = await readFile(path.join(workspace.root, mapPath), "utf8");
    chunks.push({
      chunkId: `${manifest.documentId}_index_${digest(mapText).slice(0, 18)}`,
      documentId: manifest.documentId,
      pageStart: 1,
      pageEnd: Math.max(1, manifest.totalPages),
      contentType: "document_index",
      heading: `Index ${manifest.originalFilename}`,
      text: `Document ${manifest.originalFilename}. Origine ${manifest.sourceOrigin}. ${manifest.totalPages} pages. ${manifest.knowledge.tags} tags, ${manifest.knowledge.atomicFacts} faits atomiques, ${manifest.knowledge.shrunkChunks} chunks condensés.`,
      sourceHash: digest(mapText)
    });
  }
  return chunks;
}
