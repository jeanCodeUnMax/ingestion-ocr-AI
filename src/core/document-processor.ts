import path from "node:path";
import { config } from "../config.js";
import type { PersistentJob, DocumentManifest } from "../types.js";
import type { JobStore } from "../jobs/job-store.js";
import type { SqliteVectorStore } from "../vector/sqlite-vector-store.js";
import { normalizeInput } from "../ingestion/normalizer.js";
import { transcribeAudio } from "../audio/transcriber.js";
import { atomicWriteText } from "../utils/files.js";
import { processPdfJob } from "./processor.js";

export async function processDocumentJob(input: {
  job: PersistentJob;
  jobStore: JobStore;
  vectorStore: SqliteVectorStore;
}): Promise<DocumentManifest> {
  const { job, jobStore } = input;
  if (!job.payload.stagedPdfPath) {
    await jobStore.updateProgress(job.jobId, {
      stage: "normalization",
      percent: 5,
      message: `Normalisation ${job.payload.inputKind} vers le format canonique PDF + Markdown.`
    });
    const outputDir = path.join(config.uploadsRoot, `${job.documentId}_normalized`);
    let normalizationSource = job.payload.stagedSourcePath;
    let normalizationKind = job.payload.inputKind;
    if (job.payload.inputKind === "audio") {
      const transcript = await transcribeAudio(job.payload.stagedSourcePath, config.audioTranscriptionProvider);
      normalizationSource = path.join(outputDir, "audio_transcript.md");
      await atomicWriteText(normalizationSource, [
        `# Transcription audio — ${job.payload.filename}`,
        "",
        `<!-- provider=${transcript.provider} model=${transcript.model} -->`,
        "",
        transcript.text,
        ""
      ].join("\n"));
      normalizationKind = "markdown";
    }
    const normalized = await normalizeInput({
      sourcePath: normalizationSource,
      kind: normalizationKind,
      outputDir
    });
    job.payload.stagedPdfPath = normalized.canonicalPdfPath;
    job.payload.canonicalMarkdownPath = normalized.canonicalMarkdownPath;
    await jobStore.save(job);
  }
  return processPdfJob(input);
}
