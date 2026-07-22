import path from "node:path";
import type { InputKind } from "../types.js";

const extensionMap: Record<string, InputKind> = {
  ".pdf": "pdf",
  ".docx": "word",
  ".xlsx": "excel",
  ".xlsm": "excel",
  ".csv": "csv",
  ".json": "json",
  ".md": "markdown",
  ".markdown": "markdown",
  ".txt": "text",
  ".png": "image",
  ".jpg": "image",
  ".jpeg": "image",
  ".webp": "image",
  ".tif": "image",
  ".tiff": "image",
  ".svg": "svg",
  ".wav": "audio",
  ".mp3": "audio",
  ".m4a": "audio",
  ".ogg": "audio"
};

export function detectInputKind(filename: string, mimeType = ""): InputKind {
  const fromExtension = extensionMap[path.extname(filename).toLowerCase()];
  if (fromExtension) return fromExtension;
  if (mimeType === "application/pdf") return "pdf";
  if (mimeType.startsWith("image/")) return "image";
  if (mimeType.startsWith("audio/")) return "audio";
  if (mimeType.includes("json")) return "json";
  if (mimeType.startsWith("text/")) return "text";
  throw new Error(`FORMAT_UNSUPPORTED:${filename}:${mimeType}`);
}

export function acceptedExtensions(): string[] {
  return Object.keys(extensionMap).sort();
}
