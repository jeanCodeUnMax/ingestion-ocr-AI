import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { enrichKnowledge, loadKnowledgeEmbeddingChunks } from "../src/knowledge/enrichment.js";
import { createWorkspace } from "../src/core/workspace.js";
import { ManifestStore } from "../src/core/manifest-store.js";
import type { AnalysisBundle, DocumentManifest } from "../src/types.js";
import { recipeForProfile } from "../src/core/recipe.js";

test("shrink, faits atomiques, tags et index conservent les sources", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "ocr-knowledge-"));
  try {
    const workspace = await createWorkspace(root, "doc_k");
    const pageRelative = path.join("transcription", "page_0001.md");
    await writeFile(path.join(workspace.root, pageRelative), "# Maintenance\n\nLa vibration doit être mesurée chaque semaine. Ne jamais ignorer une alarme supérieure à 10 mm/s.\n", "utf8");
    const now = new Date().toISOString();
    const recipe = recipeForProfile("standard");
    const manifest: DocumentManifest = {
      schemaVersion: "6.0", documentId: "doc_k", projectId: "prj_k", sourceOrigin: "paste", recipe,
      originalFilename: "maintenance.md", inputKind: "markdown", mimeType: "text/markdown",
      originalSourceRelativePath: "source/original.md", sourceRelativePath: "source/canonical.pdf",
      deploymentMode: "personal", ownership: { userId: "u", tenantId: "t" }, instruction: "Analyser",
      status: "analysis", sourceSha256: "source", provider: "none", embeddingProvider: "hash", analysisProvider: "rules", translationProvider: "none",
      createdAt: now, updatedAt: now, totalPages: 1,
      pages: [{ pageNumber: 1, pageId: "page_0001", sourceHash: "p1", widthPt: 1, heightPt: 1, nativeTextChars: 100, nativeTextPath: "native", imageCount: 0, imageAreaRatio: 0, drawingCount: 0, estimatedInputTokens: 100, requiresVision: false, status: "native_success", outputMarkdownPath: pageRelative, attempts: 0, errors: [] }],
      batches: [], coverage: { pagesDetected: 1, pagesSuccessful: 1, pagesFailed: 0, pagesPending: 0, visionPagesExpected: 0, visionPagesAssignedToLeafBatches: 0, missingPageIds: [], duplicateLeafAssignments: [], isComplete: true },
      analysis: { provider: "rules", model: "rules", status: "complete", segmentsExpected: 1, segmentsCompleted: 1, sourceChunks: 1, artifacts: {}, indexedChunks: 0, errors: [] },
      translation: { provider: "none", model: "none", status: "skipped", segmentsExpected: 0, segmentsCompleted: 0, errors: [] },
      embedding: { provider: "hash", model: "hash", status: "pending", chunksExpected: 0, chunksEmbedded: 0, vectorStore: "test", errors: [] },
      knowledge: { status: "pending", atomicFacts: 0, shrunkChunks: 0, tags: 0, artifacts: {}, indexedChunks: 0, errors: [] }
    };
    const sourceIds = ["doc_k_page_0001_c001"];
    const bundle: AnalysisBundle = {
      schemaVersion: "1.0", documentId: "doc_k", provider: "rules", model: "rules", generatedAt: now, sourceChunkIds: sourceIds,
      enabled: { semantic: true, maieutic: true, kent: true, pseudocode: true, synthesis: true },
      semantic: [{ segmentId: "s1", source: { sourceChunkIds: sourceIds, pageStart: 1, pageEnd: 1 }, title: "Maintenance", summary: "Mesure des vibrations.", themes: [{ name: "Maintenance préventive", explanation: "Prévenir les pannes", sourceChunkIds: sourceIds }], concepts: [{ name: "Vibration", definition: "Indicateur mécanique", sourceChunkIds: sourceIds }], entities: [], claims: [{ statement: "La vibration doit être mesurée chaque semaine.", confidence: "explicit", sourceChunkIds: sourceIds }], relations: [], keyFacts: [{ fact: "Une alarme supérieure à 10 mm/s ne doit jamais être ignorée.", sourceChunkIds: sourceIds }], uncertainties: [] }],
      maieutic: [], kent: [], pseudocode: [],
      synthesis: { executiveSummary: "Maintenance", coreThemes: ["Maintenance"], centralProblem: "Pannes", realityVerdict: "Mesurable", operationalModel: "Mesurer", priorityActions: [], unresolvedQuestions: [], sourceChunkIds: sourceIds }
    };
    await writeFile(path.join(workspace.analysis, "synthesis.json"), JSON.stringify(bundle), "utf8");
    const store = new ManifestStore(workspace.manifest, path.join(workspace.logs, "events.jsonl"));
    await store.save(manifest);
    const result = await enrichKnowledge({ manifest, workspace, store });
    assert.equal(manifest.knowledge.status, "complete");
    assert.ok(manifest.knowledge.atomicFacts >= 2);
    assert.ok(manifest.knowledge.shrunkChunks >= 1);
    assert.ok(manifest.knowledge.tags >= 2);
    assert.ok(result.chunks.some((chunk) => chunk.contentType === "document_index"));
    const loaded = await loadKnowledgeEmbeddingChunks(manifest, workspace);
    assert.ok(loaded.some((chunk) => chunk.contentType === "atomic_fact"));
    assert.ok(loaded.some((chunk) => chunk.contentType === "shrunk_chunk"));
    assert.ok(loaded.some((chunk) => chunk.contentType === "document_index"));
    const index = await readFile(path.join(workspace.root, "index.md"), "utf8");
    assert.match(index, /Couverture complète : oui/);
  } finally { await rm(root, { recursive: true, force: true }); }
});
