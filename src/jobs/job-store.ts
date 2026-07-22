import { randomUUID } from "node:crypto";
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import type { JobStatus, PersistentJob, ProcessDocumentJobPayload } from "../types.js";
import { atomicWriteJson, ensureDir } from "../utils/files.js";

function iso(): string {
  return new Date().toISOString();
}

export class JobStore {
  constructor(private readonly root: string) {}

  async initialize(): Promise<void> {
    await ensureDir(this.root);
  }

  private pathFor(jobId: string): string {
    return path.join(this.root, `${jobId}.json`);
  }

  async create(input: {
    documentId: string;
    payload: ProcessDocumentJobPayload;
    maxAttempts: number;
  }): Promise<PersistentJob> {
    const now = iso();
    const job: PersistentJob = {
      schemaVersion: "1.2",
      jobId: `job_${randomUUID()}`,
      documentId: input.documentId,
      type: "process_document",
      status: "queued",
      payload: input.payload,
      attempts: 0,
      maxAttempts: input.maxAttempts,
      createdAt: now,
      updatedAt: now,
      progress: {
        stage: "queued",
        percent: 0,
        message: "Job enregistré dans la file persistante."
      }
    };
    await this.save(job);
    return job;
  }

  async save(job: PersistentJob): Promise<void> {
    job.updatedAt = iso();
    await atomicWriteJson(this.pathFor(job.jobId), job);
  }

  async get(jobId: string): Promise<PersistentJob | undefined> {
    try {
      return JSON.parse(await readFile(this.pathFor(jobId), "utf8")) as PersistentJob;
    } catch (error) {
      const code = (error as NodeJS.ErrnoException).code;
      if (code === "ENOENT") return undefined;
      throw error;
    }
  }

  async list(status?: JobStatus): Promise<PersistentJob[]> {
    await this.initialize();
    const files = (await readdir(this.root)).filter((file) => file.endsWith(".json"));
    const jobs: PersistentJob[] = [];
    for (const file of files) {
      try {
        const job = JSON.parse(await readFile(path.join(this.root, file), "utf8")) as PersistentJob;
        if (!status || job.status === status) jobs.push(job);
      } catch {
        // Un fichier partiellement écrit ne devrait pas exister grâce aux écritures atomiques.
      }
    }
    return jobs.sort((a, b) => a.createdAt.localeCompare(b.createdAt));
  }

  async recoverInterrupted(): Promise<number> {
    const interrupted = await this.list("processing");
    for (const job of interrupted) {
      job.status = job.attempts >= job.maxAttempts ? "failed" : "queued";
      job.progress = job.status === "queued"
        ? { stage: "recovered", percent: Math.max(job.progress.percent, 1), message: "Job repris après redémarrage." }
        : { stage: "failed", percent: job.progress.percent, message: "Nombre maximal de tentatives atteint avant reprise." };
      job.lastError = {
        at: iso(),
        message: "Le processus précédent a été interrompu avant la fin du job."
      };
      await this.save(job);
    }
    return interrupted.length;
  }

  async claimNext(): Promise<PersistentJob | undefined> {
    const queued = await this.list("queued");
    const job = queued[0];
    if (!job) return undefined;
    job.status = "processing";
    job.attempts += 1;
    job.startedAt = iso();
    job.progress = {
      stage: "processing",
      percent: Math.max(job.progress.percent, 2),
      message: `Traitement démarré, tentative ${job.attempts}/${job.maxAttempts}.`
    };
    await this.save(job);
    return job;
  }

  async updateProgress(jobId: string, progress: PersistentJob["progress"]): Promise<void> {
    const job = await this.get(jobId);
    if (!job) throw new Error(`Job introuvable: ${jobId}`);
    job.progress = {
      ...progress,
      percent: Math.max(0, Math.min(100, progress.percent))
    };
    await this.save(job);
  }

  async complete(jobId: string, message = "Document traité et indexé."): Promise<PersistentJob> {
    const job = await this.get(jobId);
    if (!job) throw new Error(`Job introuvable: ${jobId}`);
    job.status = "completed";
    job.finishedAt = iso();
    job.progress = { stage: "completed", percent: 100, message };
    await this.save(job);
    return job;
  }

  async fail(jobId: string, error: unknown): Promise<PersistentJob> {
    const job = await this.get(jobId);
    if (!job) throw new Error(`Job introuvable: ${jobId}`);
    const message = error instanceof Error ? error.message : String(error);
    job.lastError = { at: iso(), message };
    if (job.attempts < job.maxAttempts) {
      job.status = "queued";
      job.progress = {
        stage: "retry_queued",
        percent: job.progress.percent,
        message: `Échec temporaire. Nouvelle tentative planifiée: ${message}`
      };
    } else {
      job.status = "failed";
      job.finishedAt = iso();
      job.progress = { stage: "failed", percent: job.progress.percent, message };
    }
    await this.save(job);
    return job;
  }

  async retry(jobId: string): Promise<PersistentJob> {
    const job = await this.get(jobId);
    if (!job) throw new Error(`Job introuvable: ${jobId}`);
    job.status = "queued";
    job.attempts = 0;
    delete job.finishedAt;
    delete job.lastError;
    job.progress = { stage: "queued", percent: 0, message: "Relance manuelle demandée." };
    await this.save(job);
    return job;
  }
}
