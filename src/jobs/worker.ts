import { rm } from "node:fs/promises";
import type { JobStore } from "./job-store.js";
import type { SqliteVectorStore } from "../vector/sqlite-vector-store.js";
import path from "node:path";
import { processDocumentJob } from "../core/document-processor.js";
import type { BillingLedger } from "../platform/billing.js";
import type { ProjectStore } from "../projects/project-store.js";

export class PersistentJobWorker {
  private timer: NodeJS.Timeout | undefined;
  private running = false;

  constructor(
    private readonly jobs: JobStore,
    private readonly vectors: SqliteVectorStore,
    private readonly intervalMs: number,
    private readonly billing?: BillingLedger,
    private readonly projects?: ProjectStore
  ) {}

  async initialize(): Promise<number> {
    await this.jobs.initialize();
    return this.jobs.recoverInterrupted();
  }

  start(): void {
    if (this.timer) return;
    this.timer = setInterval(() => void this.runOnce(), this.intervalMs);
    this.timer.unref();
    void this.runOnce();
  }

  stop(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = undefined;
  }

  async runOnce(): Promise<boolean> {
    if (this.running) return false;
    this.running = true;
    try {
      const job = await this.jobs.claimNext();
      if (!job) return false;
      try {
        await this.jobs.updateProgress(job.jobId, {
          stage: "document_pipeline",
          percent: Math.max(job.progress.percent, 5),
          message: "Normalisation, OCR, traduction optionnelle, analyses KENT/maïeutiques et indexation en cours."
        });
        const manifest = await processDocumentJob({ job, jobStore: this.jobs, vectorStore: this.vectors });
        if (this.billing) {
          const identity = job.payload.identity;
          const at = new Date().toISOString();
          await this.billing.record({ at, tenantId: identity.tenantId, userId: identity.userId, documentId: manifest.documentId, metric: "page", quantity: manifest.totalPages });
          await this.billing.record({ at, tenantId: identity.tenantId, userId: identity.userId, documentId: manifest.documentId, metric: "ocr_page", quantity: manifest.coverage.visionPagesExpected });
          await this.billing.record({ at, tenantId: identity.tenantId, userId: identity.userId, documentId: manifest.documentId, metric: "analysis_chunk", quantity: manifest.analysis.sourceChunks });
          await this.billing.record({ at, tenantId: identity.tenantId, userId: identity.userId, documentId: manifest.documentId, metric: "embedding_chunk", quantity: manifest.embedding.chunksEmbedded });
        }
        if (job.payload.projectId && this.projects) {
          await this.projects.updateDocumentStatus(job.payload.projectId, manifest.documentId, manifest.status);
        }
        const message = manifest.status === "complete"
          ? "Document intégralement traité, enrichi et indexé."
          : `Pipeline terminé avec le statut document ${manifest.status}. Consulte le manifeste.`;
        await this.jobs.complete(job.jobId, message);
        await rm(job.payload.stagedSourcePath, { force: true });
        if (job.payload.stagedPdfPath && job.payload.stagedPdfPath !== job.payload.stagedSourcePath) {
          await rm(path.dirname(job.payload.stagedPdfPath), { recursive: true, force: true });
        }
      } catch (error) {
        if (job.payload.projectId && this.projects) await this.projects.updateDocumentStatus(job.payload.projectId, job.documentId, "failed");
        await this.jobs.fail(job.jobId, error);
      }
      return true;
    } finally {
      this.running = false;
    }
  }
}
