import { appendFile, readFile } from "node:fs/promises";
import path from "node:path";
import type { DocumentManifest } from "../types.js";
import { atomicWriteJson, ensureDir } from "../utils/files.js";

export class ManifestStore {
  constructor(
    private readonly manifestPath: string,
    private readonly eventLogPath: string
  ) {}

  async save(manifest: DocumentManifest, event?: string, details?: unknown): Promise<void> {
    manifest.updatedAt = new Date().toISOString();
    await atomicWriteJson(this.manifestPath, manifest);
    if (event) {
      await ensureDir(path.dirname(this.eventLogPath));
      await appendFile(
        this.eventLogPath,
        `${JSON.stringify({ at: manifest.updatedAt, event, details })}\n`,
        "utf8"
      );
    }
  }

  async load(): Promise<DocumentManifest> {
    return JSON.parse(await readFile(this.manifestPath, "utf8")) as DocumentManifest;
  }
}
