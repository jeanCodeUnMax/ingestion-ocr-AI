import assert from "node:assert/strict";
import { access, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { detectInputKind } from "../src/ingestion/detect.js";
import { normalizeInput } from "../src/ingestion/normalizer.js";

const projectRoot = process.cwd();

test("la détection couvre les formats structurés principaux", () => {
  assert.equal(detectInputKind("rapport.docx"), "word");
  assert.equal(detectInputKind("mesures.xlsx"), "excel");
  assert.equal(detectInputKind("data.csv"), "csv");
  assert.equal(detectInputKind("config.json"), "json");
  assert.equal(detectInputKind("schema.png"), "image");
});

test("un JSON est normalisé en PDF canonique et Markdown", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "ocr-v05-ingestion-"));
  const previous = process.cwd();
  try {
    process.chdir(projectRoot);
    const source = path.join(root, "input.json");
    await writeFile(source, JSON.stringify({ machine: "pompe", seuil: 42 }), "utf8");
    const output = await normalizeInput({ sourcePath: source, kind: "json", outputDir: path.join(root, "out") });
    await access(output.canonicalPdfPath);
    const markdown = await readFile(output.canonicalMarkdownPath, "utf8");
    assert.match(markdown, /"machine": "pompe"/);
    assert.ok(output.pageCount >= 1);
  } finally {
    process.chdir(previous);
    await rm(root, { recursive: true, force: true });
  }
});
