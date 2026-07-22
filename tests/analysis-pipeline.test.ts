import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { analyzeDocument, buildAnalysisEmbeddingChunks } from "../src/analysis/pipeline.js";
import { ManifestStore } from "../src/core/manifest-store.js";
import { createWorkspace } from "../src/core/workspace.js";
import type { DocumentManifest } from "../src/types.js";

test("le pipeline v0.4 écrit les cinq familles d'artefacts et des chunks traçables", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "ocr-v04-analysis-"));
  try {
    const workspace = await createWorkspace(root, "doc_analysis");
    const relative = path.join("transcription", "page_0001.md");
    await writeFile(path.join(workspace.root, relative), [
      "# Maintenance préventive",
      "",
      "La maintenance préventive vise à réduire les pannes. Elle impose une inspection hebdomadaire et un relevé des vibrations.",
      "Le coût de l'inspection doit être comparé au coût des arrêts de production."
    ].join("\n"), "utf8");
    const now = new Date().toISOString();
    const manifest: DocumentManifest = {
      schemaVersion: "6.0",
      documentId: "doc_analysis",
      sourceOrigin: "upload",
      recipe: { profile: "standard", semanticAnalysis: true, maieuticAnalysis: true, kentRealityCheck: true, pseudocode: true, synthesis: true, shrink: true, atomicFacts: true, tagsAndTaxonomy: true, embeddings: true, visualDescriptions: true, translation: false },
      originalFilename: "sample.pdf",
      inputKind: "pdf",
      mimeType: "application/pdf",
      originalSourceRelativePath: path.join("source", "original_sample.pdf"),
      sourceRelativePath: path.join("source", "canonical.pdf"),
      deploymentMode: "personal",
      ownership: { userId: "personal-user", tenantId: "personal-workspace" },
      instruction: "Produire une analyse opérationnelle.",
      status: "analysis",
      sourceSha256: "source",
      provider: "none",
      embeddingProvider: "hash",
      analysisProvider: "rules",
      translationProvider: "none",
      createdAt: now,
      updatedAt: now,
      totalPages: 1,
      pages: [{
        pageNumber: 1,
        pageId: "page_0001",
        sourceHash: "page_hash",
        widthPt: 595,
        heightPt: 842,
        nativeTextChars: 180,
        nativeTextPath: path.join(workspace.native, "page_0001.txt"),
        imageCount: 0,
        imageAreaRatio: 0,
        drawingCount: 0,
        estimatedInputTokens: 100,
        requiresVision: false,
        status: "native_success",
        outputMarkdownPath: relative,
        provider: "native",
        model: "PyMuPDF",
        attempts: 0,
        errors: []
      }],
      batches: [],
      coverage: {
        pagesDetected: 1,
        pagesSuccessful: 1,
        pagesFailed: 0,
        pagesPending: 0,
        visionPagesExpected: 0,
        visionPagesAssignedToLeafBatches: 0,
        missingPageIds: [],
        duplicateLeafAssignments: [],
        isComplete: true
      },
      analysis: {
        provider: "rules",
        model: "ocr-ai-rules-v1",
        status: "pending",
        segmentsExpected: 0,
        segmentsCompleted: 0,
        sourceChunks: 0,
        artifacts: {},
        indexedChunks: 0,
        errors: []
      },
      translation: {
        provider: "none",
        model: "none",
        status: "skipped",
        segmentsExpected: 0,
        segmentsCompleted: 0,
        errors: []
      },
      embedding: {
        provider: "hash",
        model: "hash",
        status: "pending",
        chunksExpected: 0,
        chunksEmbedded: 0,
        vectorStore: "test",
        errors: []
      },
      knowledge: { status: "pending", atomicFacts: 0, shrunkChunks: 0, tags: 0, artifacts: {}, indexedChunks: 0, errors: [] }
    };
    const store = new ManifestStore(workspace.manifest, path.join(workspace.logs, "events.jsonl"));
    await store.save(manifest);
    const bundle = await analyzeDocument({ manifest, workspace, store });
    assert.equal(manifest.analysis.status, "complete");
    assert.equal(bundle.kent[0]?.questions.length, 6);
    const artifactFiles = [
      path.join(workspace.semanticAnalysis, "semantic.md"),
      path.join(workspace.conceptualAnalysis, "maieutic.md"),
      path.join(workspace.kentAnalysis, "kent_glove.md"),
      path.join(workspace.pseudocode, "pseudocode.md"),
      path.join(workspace.analysis, "synthesis.md")
    ];
    for (const file of artifactFiles) assert.ok((await readFile(file, "utf8")).length > 50);
    const analysisChunks = buildAnalysisEmbeddingChunks(bundle);
    assert.equal(analysisChunks.length, 5);
    assert.ok(analysisChunks.every((chunk) => (chunk.sourceChunkIds?.length ?? 0) > 0));
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
