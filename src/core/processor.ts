import { access, copyFile, readFile } from "node:fs/promises";
import path from "node:path";
import { config } from "../config.js";
import { analyzeDocument } from "../analysis/pipeline.js";
import { translateDocument } from "../translation/pipeline.js";
import { createAnalysisProvider } from "../analysis/router.js";
import { createEmbeddingProvider } from "../embeddings/router.js";
import type { JobStore } from "../jobs/job-store.js";
import type {
  BatchRecord,
  DocumentManifest,
  OcrPageResult,
  PageRecord,
  PersistentJob
} from "../types.js";
import { atomicWriteJson, atomicWriteText, safeFilename, sha256File } from "../utils/files.js";
import type { SqliteVectorStore } from "../vector/sqlite-vector-store.js";
import { createProvider } from "../providers/router.js";
import { computeCoverage } from "./coverage.js";
import { ProviderError } from "./errors.js";
import { indexDocument } from "./indexer.js";
import { enrichKnowledge } from "../knowledge/enrichment.js";
import { ManifestStore } from "./manifest-store.js";
import { buildAdaptiveBatches, splitBatch } from "./partitioner.js";
import { runPdfInventory } from "./pdf-worker.js";
import { createWorkspace, type WorkspacePaths } from "./workspace.js";

function iso(): string {
  return new Date().toISOString();
}

async function exists(filePath: string): Promise<boolean> {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

function emptyCoverage(): DocumentManifest["coverage"] {
  return {
    pagesDetected: 0,
    pagesSuccessful: 0,
    pagesFailed: 0,
    pagesPending: 0,
    visionPagesExpected: 0,
    visionPagesAssignedToLeafBatches: 0,
    missingPageIds: [],
    duplicateLeafAssignments: [],
    isComplete: false
  };
}

function pageMarkdown(page: PageRecord, body: string, visualDescription: string, provider: string): string {
  return [
    `# Page ${page.pageNumber}`,
    "",
    `<!-- page_id=${page.pageId} source_hash=${page.sourceHash} provider=${provider} -->`,
    "",
    body.trim() || "[AUCUN TEXTE EXTRAIT]",
    "",
    "## Description visuelle",
    "",
    visualDescription.trim() || "Aucune description visuelle disponible.",
    ""
  ].join("\n");
}

async function writePageOutput(
  workspaceRoot: string,
  page: PageRecord,
  result: OcrPageResult,
  provider: string
): Promise<void> {
  const relative = path.join("transcription", `${page.pageId}.md`);
  await atomicWriteText(
    path.join(workspaceRoot, relative),
    pageMarkdown(page, result.markdown, result.visualDescription, provider)
  );
  page.outputMarkdownPath = relative;
  if (result.confidence !== undefined) page.confidence = result.confidence;
}

async function finalizeMarkdown(manifest: DocumentManifest, workspaceRoot: string): Promise<void> {
  const ordered = [...manifest.pages].sort((a, b) => a.pageNumber - b.pageNumber);
  const markdown: string[] = [];
  for (const page of ordered) {
    if (!page.outputMarkdownPath) continue;
    markdown.push(await readFile(path.join(workspaceRoot, page.outputMarkdownPath), "utf8"));
  }
  await atomicWriteText(
    path.join(workspaceRoot, "transcription", "full_document.md"),
    markdown.join("\n\n---\n\n")
  );
}

async function prepareNewDocument(input: {
  job: PersistentJob;
  workspace: WorkspacePaths;
  store: ManifestStore;
}): Promise<DocumentManifest> {
  const { job, workspace, store } = input;
  const provider = createProvider(job.payload.providerId);
  const embeddingProvider = createEmbeddingProvider(job.payload.embeddingProviderId);
  const analysisProvider = createAnalysisProvider(job.payload.analysisProviderId);
  if (!job.payload.stagedPdfPath) throw new Error("CANONICAL_PDF_MISSING");
  const sourceFilename = safeFilename(job.payload.filename);
  const originalSourceRelativePath = path.join("source", `original_${sourceFilename}`);
  const sourceRelativePath = path.join("source", "canonical.pdf");
  const originalSourcePath = path.join(workspace.root, originalSourceRelativePath);
  const sourcePath = path.join(workspace.root, sourceRelativePath);
  await copyFile(job.payload.stagedSourcePath, originalSourcePath);
  await copyFile(job.payload.stagedPdfPath, sourcePath);
  if (job.payload.canonicalMarkdownPath && await exists(job.payload.canonicalMarkdownPath)) {
    await copyFile(job.payload.canonicalMarkdownPath, path.join(workspace.source, "canonical_source.md"));
  }
  await atomicWriteText(
    path.join(workspace.request, "user_request.md"),
    job.payload.instruction || "Transcription fidèle."
  );
  await atomicWriteJson(path.join(workspace.request, "processing_config.json"), {
    deployment: { mode: config.deploymentMode, features: config.featureFlags, identity: job.payload.identity },
    project: { projectId: job.payload.projectId ?? null, sourceOrigin: job.payload.sourceOrigin, sourceUrl: job.payload.sourceUrl ?? null },
    recipe: job.payload.recipe,
    input: { kind: job.payload.inputKind, mimeType: job.payload.mimeType, originalFilename: sourceFilename },
    ocr: {
      provider: job.payload.providerId,
      model: provider.capabilities.model,
      capabilities: provider.capabilities
    },
    embeddings: {
      provider: job.payload.embeddingProviderId,
      model: embeddingProvider.capabilities.model,
      capabilities: embeddingProvider.capabilities
    },
    analysis: {
      provider: job.payload.analysisProviderId,
      model: analysisProvider.capabilities.model,
      capabilities: analysisProvider.capabilities,
      kentQuestions: ["claim", "tenants", "aboutissants", "interests", "evidence", "reality_slap"]
    },
    translation: {
      provider: job.payload.translationProviderId,
      targetLanguage: job.payload.targetLanguage ?? null,
      enabled: config.featureFlags.translation
    }
  });

  const now = iso();
  const manifest: DocumentManifest = {
    schemaVersion: "6.0",
    documentId: job.documentId,
    ...(job.payload.projectId ? { projectId: job.payload.projectId } : {}),
    sourceOrigin: job.payload.sourceOrigin,
    ...(job.payload.sourceUrl ? { sourceUrl: job.payload.sourceUrl } : {}),
    recipe: job.payload.recipe,
    originalFilename: sourceFilename,
    inputKind: job.payload.inputKind,
    mimeType: job.payload.mimeType,
    originalSourceRelativePath,
    sourceRelativePath,
    deploymentMode: config.deploymentMode,
    ownership: { userId: job.payload.identity.userId, tenantId: job.payload.identity.tenantId },
    instruction: job.payload.instruction,
    status: "inventory",
    sourceSha256: await sha256File(originalSourcePath),
    provider: job.payload.providerId,
    embeddingProvider: job.payload.embeddingProviderId,
    analysisProvider: job.payload.analysisProviderId,
    translationProvider: job.payload.translationProviderId,
    ...(job.payload.targetLanguage ? { targetLanguage: job.payload.targetLanguage } : {}),
    createdAt: now,
    updatedAt: now,
    totalPages: 0,
    pages: [],
    batches: [],
    coverage: emptyCoverage(),
    analysis: {
      provider: job.payload.analysisProviderId,
      model: analysisProvider.capabilities.model,
      status: "pending",
      segmentsExpected: 0,
      segmentsCompleted: 0,
      sourceChunks: 0,
      artifacts: {},
      indexedChunks: 0,
      errors: []
    },
    translation: {
      provider: job.payload.translationProviderId,
      model: job.payload.translationProviderId === "llama-cpp" ? config.llamaCpp.analysisModel : job.payload.translationProviderId === "mistral" ? config.mistral.analysisModel : "none",
      ...(job.payload.targetLanguage ? { targetLanguage: job.payload.targetLanguage } : {}),
      status: job.payload.targetLanguage && job.payload.translationProviderId !== "none" ? "pending" : "skipped",
      segmentsExpected: 0,
      segmentsCompleted: 0,
      errors: []
    },
    embedding: {
      provider: job.payload.embeddingProviderId,
      model: embeddingProvider.capabilities.model,
      status: "pending",
      chunksExpected: 0,
      chunksEmbedded: 0,
      vectorStore: config.vectorDbPath,
      errors: []
    },
    knowledge: {
      status: "pending",
      atomicFacts: 0,
      shrunkChunks: 0,
      tags: 0,
      artifacts: {},
      indexedChunks: 0,
      errors: []
    }
  };
  await store.save(manifest, "document_created", { jobId: job.jobId });
  return manifest;
}

async function inventoryDocument(input: {
  manifest: DocumentManifest;
  workspace: WorkspacePaths;
  store: ManifestStore;
}): Promise<void> {
  const { manifest, workspace, store } = input;
  if (manifest.pages.length > 0) return;
  const sourcePath = path.join(workspace.root, manifest.sourceRelativePath);
  const provider = createProvider(manifest.provider);
  const inventory = await runPdfInventory(sourcePath, workspace);
  manifest.totalPages = inventory.totalPages;
  manifest.pages = inventory.pages.map((page): PageRecord => ({
    ...page,
    status: page.requiresVision ? "vision_planned" : "pending",
    attempts: 0,
    errors: []
  }));

  for (const page of manifest.pages) {
    if (page.requiresVision) continue;
    const nativeText = await readFile(page.nativeTextPath, "utf8");
    await writePageOutput(
      workspace.root,
      page,
      {
        pageId: page.pageId,
        markdown: nativeText,
        visualDescription: "Aucun élément visuel substantiel détecté par le filtre."
      },
      "native_pdf_text"
    );
    page.status = "native_success";
    page.provider = "native";
    page.model = "PyMuPDF";
  }

  manifest.batches = await buildAdaptiveBatches(manifest.pages, provider.capabilities);
  manifest.status = "processing";
  manifest.coverage = computeCoverage(manifest);
  for (const batch of manifest.batches) {
    await atomicWriteJson(path.join(workspace.batches, `${batch.batchId}.json`), batch);
  }
  await store.save(manifest, "inventory_completed", {
    totalPages: manifest.totalPages,
    nativePages: manifest.pages.filter((page) => !page.requiresVision).length,
    visionPages: manifest.pages.filter((page) => page.requiresVision).length,
    batches: manifest.batches.length
  });
}

function resetInterruptedState(manifest: DocumentManifest, jobAttempt: number): void {
  for (const page of manifest.pages) {
    if (page.status === "vision_processing") page.status = "vision_planned";
  }
  for (const batch of manifest.batches) {
    if (batch.status === "processing") batch.status = "retry_planned";
    if (jobAttempt > 1 && batch.status === "failed") {
      const hasUnfinishedPage = batch.pageIds.some((pageId) => {
        const page = manifest.pages.find((candidate) => candidate.pageId === pageId);
        return page && page.status !== "native_success" && page.status !== "vision_success";
      });
      if (hasUnfinishedPage) {
        batch.status = "retry_planned";
        batch.attempt = 0;
        for (const pageId of batch.pageIds) {
          const page = manifest.pages.find((candidate) => candidate.pageId === pageId);
          if (page?.status === "failed") page.status = "vision_planned";
        }
      }
    }
  }
}

function activeQueue(manifest: DocumentManifest): BatchRecord[] {
  const pagesById = new Map(manifest.pages.map((page) => [page.pageId, page]));
  return manifest.batches.filter((batch) => {
    if (batch.childBatchIds.length > 0 || batch.status === "split" || batch.status === "completed") return false;
    return batch.pageIds.some((pageId) => {
      const page = pagesById.get(pageId);
      return page && page.status !== "native_success" && page.status !== "vision_success";
    });
  });
}

async function processVision(input: {
  manifest: DocumentManifest;
  workspace: WorkspacePaths;
  store: ManifestStore;
}): Promise<void> {
  const { manifest, workspace, store } = input;
  const provider = createProvider(manifest.provider);
  const sourcePath = path.join(workspace.root, manifest.sourceRelativePath);
  const queue = activeQueue(manifest);
  const pagesById = new Map(manifest.pages.map((page) => [page.pageId, page]));

  while (queue.length > 0) {
    const batch = queue.shift();
    if (!batch || batch.status === "split" || batch.status === "completed") continue;
    const batchPages = batch.pageIds
      .map((id) => {
        const page = pagesById.get(id);
        if (!page) throw new Error(`Page introuvable dans le lot: ${id}`);
        return page;
      })
      .filter((page) => page.status !== "native_success" && page.status !== "vision_success");
    if (batchPages.length === 0) {
      batch.status = "completed";
      batch.updatedAt = iso();
      continue;
    }

    batch.status = "processing";
    batch.attempt += 1;
    batch.updatedAt = iso();
    for (const page of batchPages) {
      page.status = "vision_processing";
      page.attempts += 1;
    }
    await store.save(manifest, "batch_started", { batchId: batch.batchId, attempt: batch.attempt });

    try {
      const result = await provider.processBatch({
        documentId: manifest.documentId,
        instruction: manifest.instruction,
        sourcePdfPath: sourcePath,
        pages: batchPages,
        useFallbackImages: batch.useFallbackImages
      });
      const resultByPage = new Map(result.pages.map((page) => [page.pageId, page]));
      for (const page of batchPages) {
        const pageResult = resultByPage.get(page.pageId);
        if (!pageResult) {
          throw new ProviderError(
            `Résultat absent pour ${page.pageId}`,
            "PROVIDER_PAGE_OMISSION",
            true,
            true
          );
        }
        await writePageOutput(workspace.root, page, pageResult, result.provider);
        page.status = "vision_success";
        page.provider = result.provider;
        page.model = result.model;
      }
      batch.status = "completed";
      batch.updatedAt = iso();
      await atomicWriteJson(path.join(workspace.batches, `${batch.batchId}.json`), batch);
      manifest.coverage = computeCoverage(manifest);
      await store.save(manifest, "batch_completed", { batchId: batch.batchId });
    } catch (error) {
      const providerError = error instanceof ProviderError
        ? error
        : new ProviderError(
            error instanceof Error ? error.message : String(error),
            "UNEXPECTED_ERROR",
            true,
            false
          );
      const pageError = {
        at: iso(),
        code: providerError.code,
        message: providerError.message,
        batchId: batch.batchId,
        attempt: batch.attempt
      };
      batch.errors.push(pageError);
      for (const page of batchPages) page.errors.push(pageError);

      if (providerError.requiresSplit && batch.pageIds.length > 1) {
        const [left, right] = splitBatch(batch, pagesById);
        batch.status = "split";
        batch.childBatchIds = [left.batchId, right.batchId];
        batch.updatedAt = iso();
        manifest.batches.push(left, right);
        queue.unshift(right, left);
        await atomicWriteJson(path.join(workspace.batches, `${batch.batchId}.json`), batch);
        await atomicWriteJson(path.join(workspace.batches, `${left.batchId}.json`), left);
        await atomicWriteJson(path.join(workspace.batches, `${right.batchId}.json`), right);
        await store.save(manifest, "batch_split", {
          parent: batch.batchId,
          children: batch.childBatchIds,
          reason: providerError.code
        });
        continue;
      }

      if (batch.pageIds.length === 1 && providerError.requiresSplit && !batch.useFallbackImages) {
        batch.useFallbackImages = true;
        batch.status = "retry_planned";
        batch.updatedAt = iso();
        for (const page of batchPages) page.status = "vision_planned";
        queue.unshift(batch);
        await store.save(manifest, "batch_fallback_image", { batchId: batch.batchId });
        continue;
      }

      if (providerError.retryable && batch.attempt < config.maxProcessingAttempts) {
        batch.status = "retry_planned";
        batch.updatedAt = iso();
        for (const page of batchPages) page.status = "vision_planned";
        queue.push(batch);
        await store.save(manifest, "batch_retry_planned", {
          batchId: batch.batchId,
          attempt: batch.attempt
        });
        continue;
      }

      batch.status = "failed";
      batch.updatedAt = iso();
      for (const page of batchPages) page.status = "failed";
      await atomicWriteJson(path.join(workspace.batches, `${batch.batchId}.json`), batch);
      manifest.coverage = computeCoverage(manifest);
      await store.save(manifest, "batch_failed", { batchId: batch.batchId, code: providerError.code });
    }
  }
}

export async function processPdfJob(input: {
  job: PersistentJob;
  jobStore: JobStore;
  vectorStore: SqliteVectorStore;
}): Promise<DocumentManifest> {
  const { job, jobStore, vectorStore } = input;
  const workspace = await createWorkspace(config.workspaceRoot, job.documentId);
  const store = new ManifestStore(workspace.manifest, path.join(workspace.logs, "events.jsonl"));
  let manifest: DocumentManifest;

  if (await exists(workspace.manifest)) {
    manifest = await store.load();
    if (manifest.schemaVersion !== "6.0") {
      throw new Error(`Manifeste incompatible: ${manifest.schemaVersion}.`);
    }
    resetInterruptedState(manifest, job.attempts);
    await store.save(manifest, "document_resumed", { jobId: job.jobId, jobAttempt: job.attempts });
  } else {
    manifest = await prepareNewDocument({ job, workspace, store });
  }

  if (manifest.status === "complete" && manifest.coverage.isComplete && (manifest.analysis.status === "complete" || manifest.analysis.status === "skipped") && (manifest.translation.status === "skipped" || manifest.translation.status === "complete") && (manifest.knowledge.status === "complete" || manifest.knowledge.status === "skipped") && (manifest.embedding.status === "complete" || manifest.embedding.status === "skipped")) {
    return manifest;
  }

  await jobStore.updateProgress(job.jobId, {
    stage: "inventory",
    percent: 10,
    message: "Inventaire exhaustif des pages et extraction native."
  });
  await inventoryDocument({ manifest, workspace, store });

  await jobStore.updateProgress(job.jobId, {
    stage: "ocr",
    percent: 30,
    message: "OCR adaptatif et reconstruction Markdown."
  });
  manifest.status = "processing";
  await processVision({ manifest, workspace, store });
  manifest.coverage = computeCoverage(manifest);
  await finalizeMarkdown(manifest, workspace.root);
  await store.save(manifest, "markdown_finalized", { coverage: manifest.coverage });

  await jobStore.updateProgress(job.jobId, {
    stage: "translation",
    percent: 48,
    message: "Traduction complète optionnelle avec conservation du Markdown."
  });
  if (manifest.recipe.translation) {
    await translateDocument({ manifest, workspace, store });
  } else {
    manifest.translation.status = "skipped";
    await store.save(manifest, "translation_skipped_by_recipe", {});
  }

  await jobStore.updateProgress(job.jobId, {
    stage: "analysis",
    percent: 60,
    message: "Analyse sémantique, maïeutique, gant de KENT et pseudocode."
  });
  const analysisEnabled = manifest.recipe.semanticAnalysis || manifest.recipe.maieuticAnalysis || manifest.recipe.kentRealityCheck || manifest.recipe.pseudocode || manifest.recipe.synthesis;
  if (analysisEnabled) {
    await analyzeDocument({ manifest, workspace, store });
  } else {
    manifest.analysis.status = "skipped";
    await store.save(manifest, "analysis_skipped_by_recipe", {});
  }

  await jobStore.updateProgress(job.jobId, {
    stage: "knowledge",
    percent: 76,
    message: "Shrink, faits atomiques, tags, taxonomie et index documentaire."
  });
  await enrichKnowledge({ manifest, workspace, store });

  await jobStore.updateProgress(job.jobId, {
    stage: "embedding",
    percent: 84,
    message: "Embeddings des transcriptions et analyses, puis indexation SQLite."
  });
  if (manifest.recipe.embeddings) {
    await indexDocument({ manifest, workspace, store, vectorStore });
  } else {
    manifest.embedding.status = "skipped";
    await store.save(manifest, "embedding_skipped_by_recipe", {});
  }

  manifest.coverage = computeCoverage(manifest);
  manifest.status = manifest.coverage.isComplete && (manifest.analysis.status === "complete" || manifest.analysis.status === "skipped") && (manifest.translation.status === "skipped" || manifest.translation.status === "complete") && (manifest.knowledge.status === "complete" || manifest.knowledge.status === "skipped") && (manifest.embedding.status === "complete" || manifest.embedding.status === "skipped")
    ? "complete"
    : manifest.coverage.pagesSuccessful === 0
      ? "failed"
      : "partial_failure";
  await store.save(manifest, "document_finished", {
    status: manifest.status,
    coverage: manifest.coverage,
    analysis: manifest.analysis,
    translation: manifest.translation,
    embedding: manifest.embedding,
    knowledge: manifest.knowledge
  });
  return manifest;
}
