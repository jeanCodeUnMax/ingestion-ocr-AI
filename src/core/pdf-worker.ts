import { spawn } from "node:child_process";
import { readFile } from "node:fs/promises";
import type { PdfInventory } from "../types.js";
import { config } from "../config.js";
import type { WorkspacePaths } from "./workspace.js";

export async function runPdfInventory(
  sourcePdfPath: string,
  workspace: WorkspacePaths
): Promise<PdfInventory> {
  const outputPath = `${workspace.inventory}/pdf_inventory.json`;
  const args = [
    config.pdfWorkerPath,
    "--input", sourcePdfPath,
    "--output", outputPath,
    "--pages-dir", workspace.pages,
    "--native-dir", workspace.native,
    "--dpi", String(config.pdfRenderDpi),
    "--fallback-dpi", String(config.pdfFallbackDpi),
    "--min-native-chars", String(config.minNativeTextChars),
    "--visual-mode", config.visualAnalysisMode
  ];

  await new Promise<void>((resolve, reject) => {
    const child = spawn(config.pythonBin, args, { stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => { stdout += String(chunk); });
    child.stderr.on("data", (chunk) => { stderr += String(chunk); });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`PDF worker terminé avec code ${code}. ${stderr || stdout}`));
    });
  });
  return JSON.parse(await readFile(outputPath, "utf8")) as PdfInventory;
}
