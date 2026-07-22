import { randomUUID } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { config } from "../config.js";
import { normalizeRecipe } from "./recipe.js";
import { detectInputKind } from "../ingestion/detect.js";
import type { JobStore } from "../jobs/job-store.js";
import type { ProjectStore } from "../projects/project-store.js";
import { assertFeature, assertInputKindEnabled } from "../platform/features.js";
import type { AnalysisProviderId, EmbeddingProviderId, PlatformIdentity, ProcessingRecipe, ProviderId, RecipeProfile, SourceOrigin, TranslationProviderId } from "../types.js";
import { safeFilename } from "../utils/files.js";

function newDocumentId(): string {
  const timestamp = new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14);
  return `doc_${timestamp}_${randomUUID().slice(0, 8)}`;
}

export async function enqueueDocument(input: {
  jobs: JobStore;
  projects?: ProjectStore;
  identity: PlatformIdentity;
  buffer: Buffer;
  filename: string;
  mimeType: string;
  instruction?: string;
  providerId: ProviderId;
  embeddingProviderId: EmbeddingProviderId;
  analysisProviderId: AnalysisProviderId;
  translationProviderId: TranslationProviderId;
  targetLanguage?: string;
  projectId?: string;
  sourceOrigin: SourceOrigin;
  sourceUrl?: string;
  recipe?: Partial<ProcessingRecipe>;
  recipeProfile?: RecipeProfile;
}) {
  const filename = safeFilename(input.filename);
  const inputKind = detectInputKind(filename, input.mimeType);
  assertInputKindEnabled(inputKind);
  if (input.sourceOrigin === "url") assertFeature("urlIngestion");
  if (input.targetLanguage) assertFeature("translation");
  if (inputKind === "audio" && config.audioTranscriptionProvider === "none") throw new Error("AUDIO_TRANSCRIPTION_PROVIDER_NOT_CONFIGURED");
  if (input.projectId && input.projects) {
    const project = await input.projects.get(input.projectId);
    if (!project) throw new Error(`PROJECT_NOT_FOUND:${input.projectId}`);
  }
  const recipe = normalizeRecipe(input.recipe, input.recipeProfile ?? config.defaultRecipeProfile);
  if (!input.targetLanguage) recipe.translation = false;
  const documentId = newDocumentId();
  await mkdir(config.uploadsRoot, { recursive: true });
  const stagedSourcePath = path.join(config.uploadsRoot, `${documentId}_${filename}`);
  await writeFile(stagedSourcePath, input.buffer);
  const job = await input.jobs.create({
    documentId,
    maxAttempts: config.jobMaxAttempts,
    payload: {
      stagedSourcePath,
      filename,
      mimeType: input.mimeType,
      inputKind,
      ...(input.projectId ? { projectId: input.projectId } : {}),
      sourceOrigin: input.sourceOrigin,
      ...(input.sourceUrl ? { sourceUrl: input.sourceUrl } : {}),
      recipe,
      instruction: input.instruction?.trim() ?? "",
      providerId: input.providerId,
      embeddingProviderId: input.embeddingProviderId,
      analysisProviderId: input.analysisProviderId,
      translationProviderId: input.translationProviderId,
      ...(input.targetLanguage ? { targetLanguage: input.targetLanguage } : {}),
      identity: input.identity
    }
  });
  if (input.projectId && input.projects) {
    await input.projects.attachDocument({ projectId: input.projectId, documentId, filename, inputKind, sourceOrigin: input.sourceOrigin, status: "queued" });
  }
  return { job, documentId, inputKind, recipe };
}
