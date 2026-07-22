import { createHash } from "node:crypto";
import { access, readFile } from "node:fs/promises";
import path from "node:path";
import { config } from "../config.js";
import { loadTranscriptionChunks } from "../core/source-chunks.js";
import type { ManifestStore } from "../core/manifest-store.js";
import type { WorkspacePaths } from "../core/workspace.js";
import type {
  AnalysisBundle,
  AnalyzeSegmentResult,
  DocumentManifest,
  EmbeddingChunk
} from "../types.js";
import { atomicWriteJson, atomicWriteText } from "../utils/files.js";
import { semanticMarkdown, maieuticMarkdown, kentMarkdown, pseudocodeMarkdown, synthesisMarkdown } from "./markdown.js";
import { createAnalysisProvider } from "./router.js";
import { buildAnalysisSegments, verifySegmentCoverage } from "./segmenter.js";

function iso(): string {
  return new Date().toISOString();
}

async function exists(filePath: string): Promise<boolean> {
  try { await access(filePath); return true; } catch { return false; }
}

interface SegmentCache {
  schemaVersion: "1.0";
  provider: string;
  model: string;
  segmentId: string;
  chunkIds: string[];
  result: AnalyzeSegmentResult;
}

function stableDigest(value: string): string {
  return createHash("sha256").update(value).digest("hex");
}

function artifactPaths(workspace: WorkspacePaths, manifest: DocumentManifest): DocumentManifest["analysis"]["artifacts"] {
  const relative = (absolute: string): string => path.relative(workspace.root, absolute);
  return {
    ...(manifest.recipe.semanticAnalysis ? { semanticJson: relative(path.join(workspace.semanticAnalysis, "semantic.json")), semanticMarkdown: relative(path.join(workspace.semanticAnalysis, "semantic.md")) } : {}),
    ...(manifest.recipe.maieuticAnalysis ? { maieuticJson: relative(path.join(workspace.conceptualAnalysis, "maieutic.json")), maieuticMarkdown: relative(path.join(workspace.conceptualAnalysis, "maieutic.md")) } : {}),
    ...(manifest.recipe.kentRealityCheck ? { kentJson: relative(path.join(workspace.kentAnalysis, "kent_glove.json")), kentMarkdown: relative(path.join(workspace.kentAnalysis, "kent_glove.md")) } : {}),
    ...(manifest.recipe.pseudocode ? { pseudocodeJson: relative(path.join(workspace.pseudocode, "pseudocode.json")), pseudocodeMarkdown: relative(path.join(workspace.pseudocode, "pseudocode.md")) } : {}),
    ...(manifest.recipe.synthesis ? { synthesisJson: relative(path.join(workspace.analysis, "synthesis.json")), synthesisMarkdown: relative(path.join(workspace.analysis, "synthesis.md")) } : {}),
    segmentDirectory: relative(workspace.analysisSegments)
  };
}

export async function analyzeDocument(input: {
  manifest: DocumentManifest;
  workspace: WorkspacePaths;
  store: ManifestStore;
}): Promise<AnalysisBundle> {
  const { manifest, workspace, store } = input;
  const provider = createAnalysisProvider(manifest.analysisProvider);
  const chunks = await loadTranscriptionChunks(manifest, workspace);
  const segments = buildAnalysisSegments({
    chunks,
    maxChars: Math.min(config.analysisMaxCharsPerSegment, provider.capabilities.maxInputChars),
    maxChunks: config.analysisMaxSourceChunksPerSegment
  });
  const coverage = verifySegmentCoverage(chunks, segments);
  if (!coverage.isComplete) {
    throw new Error(`Couverture d'analyse invalide. Manquants=${coverage.missingChunkIds.length}, doublons=${coverage.duplicateChunkIds.length}.`);
  }

  manifest.status = "analysis";
  manifest.analysis = {
    provider: manifest.analysisProvider,
    model: provider.capabilities.model,
    status: "processing",
    segmentsExpected: segments.length,
    segmentsCompleted: 0,
    sourceChunks: chunks.length,
    artifacts: artifactPaths(workspace, manifest),
    indexedChunks: 0,
    errors: []
  };
  await atomicWriteText(
    path.join(workspace.analysis, "source_segments.jsonl"),
    `${segments.map((segment) => JSON.stringify(segment)).join("\n")}${segments.length ? "\n" : ""}`
  );
  await store.save(manifest, "analysis_started", {
    provider: manifest.analysisProvider,
    model: provider.capabilities.model,
    chunks: chunks.length,
    segments: segments.length
  });

  try {
    const results: AnalyzeSegmentResult[] = [];
    for (const segment of segments) {
      const cachePath = path.join(workspace.analysisSegments, `${segment.segmentId}.json`);
      let result: AnalyzeSegmentResult | undefined;
      if (await exists(cachePath)) {
        try {
          const cache = JSON.parse(await readFile(cachePath, "utf8")) as SegmentCache;
          if (
            cache.schemaVersion === "1.0" &&
            cache.provider === manifest.analysisProvider &&
            cache.model === provider.capabilities.model &&
            cache.segmentId === segment.segmentId &&
            stableDigest(cache.chunkIds.join("\n")) === stableDigest(segment.chunkIds.join("\n"))
          ) {
            result = cache.result;
          }
        } catch {
          // Un cache invalide est recalculé.
        }
      }
      if (!result) {
        result = await provider.analyzeSegment({
          documentId: manifest.documentId,
          instruction: manifest.instruction,
          segment
        });
        const cache: SegmentCache = {
          schemaVersion: "1.0",
          provider: manifest.analysisProvider,
          model: provider.capabilities.model,
          segmentId: segment.segmentId,
          chunkIds: segment.chunkIds,
          result
        };
        await atomicWriteJson(cachePath, cache);
      }
      results.push(result);
      manifest.analysis.segmentsCompleted = results.length;
      await store.save(manifest, "analysis_segment_completed", {
        segmentId: segment.segmentId,
        completed: results.length,
        expected: segments.length
      });
    }

    const sourceChunkIds = chunks.map((chunk) => chunk.chunkId);
    const synthesis = manifest.recipe.synthesis
      ? await provider.synthesize({ documentId: manifest.documentId, instruction: manifest.instruction, results, sourceChunkIds })
      : {
          executiveSummary: "Synthèse désactivée par la recette de traitement.",
          coreThemes: [],
          centralProblem: "",
          realityVerdict: "",
          operationalModel: "",
          priorityActions: [],
          unresolvedQuestions: [],
          sourceChunkIds
        };
    const bundle: AnalysisBundle = {
      schemaVersion: "1.0",
      documentId: manifest.documentId,
      provider: manifest.analysisProvider,
      model: provider.capabilities.model,
      generatedAt: iso(),
      sourceChunkIds,
      enabled: { semantic: manifest.recipe.semanticAnalysis, maieutic: manifest.recipe.maieuticAnalysis, kent: manifest.recipe.kentRealityCheck, pseudocode: manifest.recipe.pseudocode, synthesis: manifest.recipe.synthesis },
      semantic: manifest.recipe.semanticAnalysis ? results.map((result) => result.semantic) : [],
      maieutic: manifest.recipe.maieuticAnalysis ? results.map((result) => result.maieutic) : [],
      kent: manifest.recipe.kentRealityCheck ? results.map((result) => result.kent) : [],
      pseudocode: manifest.recipe.pseudocode ? results.map((result) => result.pseudocode) : [],
      synthesis
    };

    const writes: Array<Promise<void>> = [];
    if (manifest.recipe.semanticAnalysis) writes.push(atomicWriteJson(path.join(workspace.semanticAnalysis, "semantic.json"), bundle.semantic), atomicWriteText(path.join(workspace.semanticAnalysis, "semantic.md"), semanticMarkdown(bundle.semantic)));
    if (manifest.recipe.maieuticAnalysis) writes.push(atomicWriteJson(path.join(workspace.conceptualAnalysis, "maieutic.json"), bundle.maieutic), atomicWriteText(path.join(workspace.conceptualAnalysis, "maieutic.md"), maieuticMarkdown(bundle.maieutic)));
    if (manifest.recipe.kentRealityCheck) writes.push(atomicWriteJson(path.join(workspace.kentAnalysis, "kent_glove.json"), bundle.kent), atomicWriteText(path.join(workspace.kentAnalysis, "kent_glove.md"), kentMarkdown(bundle.kent)));
    if (manifest.recipe.pseudocode) writes.push(atomicWriteJson(path.join(workspace.pseudocode, "pseudocode.json"), bundle.pseudocode), atomicWriteText(path.join(workspace.pseudocode, "pseudocode.md"), pseudocodeMarkdown(bundle.pseudocode)));
    // synthesis.json remains the machine-readable bundle used by enrichment and indexing, even if the human synthesis output is disabled.
    writes.push(atomicWriteJson(path.join(workspace.analysis, "synthesis.json"), bundle));
    if (manifest.recipe.synthesis) writes.push(atomicWriteText(path.join(workspace.analysis, "synthesis.md"), synthesisMarkdown(bundle)));
    await Promise.all(writes);

    manifest.analysis.status = "complete";
    manifest.analysis.analyzedAt = iso();
    await store.save(manifest, "analysis_completed", {
      segments: results.length,
      sourceChunks: chunks.length
    });
    return bundle;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    manifest.analysis.status = manifest.analysis.segmentsCompleted > 0 ? "partial_failure" : "failed";
    manifest.analysis.errors.push({ at: iso(), code: "ANALYSIS_FAILED", message });
    await store.save(manifest, "analysis_failed", { message, completed: manifest.analysis.segmentsCompleted });
    throw error;
  }
}

function analysisText(kind: EmbeddingChunk["contentType"], bundle: AnalysisBundle): Array<{ heading: string; text: string; sourceChunkIds: string[]; pageStart: number; pageEnd: number }> {
  switch (kind) {
    case "semantic_analysis":
      return bundle.semantic.map((item) => ({ heading: item.title, text: `${item.summary}\n${item.claims.map((claim) => claim.statement).join("\n")}`, sourceChunkIds: item.source.sourceChunkIds, pageStart: item.source.pageStart, pageEnd: item.source.pageEnd }));
    case "maieutic_analysis":
      return bundle.maieutic.map((item) => ({ heading: `Maïeutique ${item.segmentId}`, text: `${item.centralProblem}\n${item.intendedPurpose}\n${item.essentialMeaning}\n${item.questionsToAsk.map((q) => q.question).join("\n")}`, sourceChunkIds: item.source.sourceChunkIds, pageStart: item.source.pageStart, pageEnd: item.source.pageEnd }));
    case "kent_reality_check":
      return bundle.kent.map((item) => ({ heading: `Gant de KENT ${item.segmentId}`, text: `${item.questions.map((q) => `${q.question}\n${q.answer}`).join("\n")}\nVerdict: ${item.verdict.label} — ${item.verdict.explanation}`, sourceChunkIds: item.source.sourceChunkIds, pageStart: item.source.pageStart, pageEnd: item.source.pageEnd }));
    case "pseudocode":
      return bundle.pseudocode.map((item) => ({ heading: item.name, text: `${item.objective}\n${item.pseudocode}`, sourceChunkIds: item.source.sourceChunkIds, pageStart: item.source.pageStart, pageEnd: item.source.pageEnd }));
    case "analysis_synthesis":
      return [{ heading: "Synthèse globale", text: `${bundle.synthesis.executiveSummary}\n${bundle.synthesis.realityVerdict}\n${bundle.synthesis.operationalModel}`, sourceChunkIds: bundle.sourceChunkIds, pageStart: 1, pageEnd: Math.max(1, ...bundle.semantic.map((item) => item.source.pageEnd)) }];
    default:
      return [];
  }
}

export function buildAnalysisEmbeddingChunks(bundle: AnalysisBundle): EmbeddingChunk[] {
  const enabled = bundle.enabled ?? { semantic: true, maieutic: true, kent: true, pseudocode: true, synthesis: true };
  const kinds: EmbeddingChunk["contentType"][] = [
    ...(enabled.semantic ? ["semantic_analysis" as const] : []),
    ...(enabled.maieutic ? ["maieutic_analysis" as const] : []),
    ...(enabled.kent ? ["kent_reality_check" as const] : []),
    ...(enabled.pseudocode ? ["pseudocode" as const] : []),
    ...(enabled.synthesis ? ["analysis_synthesis" as const] : [])
  ];
  const output: EmbeddingChunk[] = [];
  for (const kind of kinds) {
    for (const [index, item] of analysisText(kind, bundle).entries()) {
      const sourceHash = stableDigest(`${kind}\n${item.text}\n${item.sourceChunkIds.join("\n")}`);
      output.push({
        chunkId: `${bundle.documentId}_${kind}_${String(index + 1).padStart(4, "0")}_${sourceHash.slice(0, 16)}`,
        documentId: bundle.documentId,
        pageStart: item.pageStart,
        pageEnd: item.pageEnd,
        contentType: kind,
        heading: item.heading,
        text: item.text,
        sourceHash,
        sourceChunkIds: item.sourceChunkIds
      });
    }
  }
  return output;
}
