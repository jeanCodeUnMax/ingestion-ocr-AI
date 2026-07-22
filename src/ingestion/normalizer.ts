import { spawn } from "node:child_process";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { config } from "../config.js";
import type { InputKind } from "../types.js";

export interface NormalizedInput {
  schemaVersion: "1.0";
  kind: InputKind;
  sourcePath: string;
  canonicalPdfPath: string;
  canonicalMarkdownPath: string;
  pageCount: number;
  mimeType: string;
}

export async function normalizeInput(input: {
  sourcePath: string;
  kind: InputKind;
  outputDir: string;
}): Promise<NormalizedInput> {
  await mkdir(input.outputDir, { recursive: true });
  const script = path.resolve("./workers/ingestion/normalize_input.py");
  return new Promise((resolve, reject) => {
    const child = spawn(config.pythonBin, [
      script,
      "--input", input.sourcePath,
      "--output-dir", input.outputDir,
      "--kind", input.kind
    ], { stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code !== 0) {
        reject(new Error(`INGESTION_NORMALIZATION_FAILED:${stderr.slice(-2000)}`));
        return;
      }
      try {
        const value = JSON.parse(stdout.trim()) as NormalizedInput;
        resolve(value);
      } catch (error) {
        reject(new Error(`INGESTION_INVALID_RESULT:${error instanceof Error ? error.message : String(error)}`));
      }
    });
  });
}
