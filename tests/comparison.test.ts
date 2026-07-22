import assert from "node:assert/strict";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { compareDocuments } from "../src/comparison/service.js";
import { config } from "../src/config.js";

test("la comparaison distingue thèmes communs et spécifiques", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "ocr-v05-compare-"));
  const oldWorkspace = config.workspaceRoot as string;
  const oldComparisons = config.comparisonsRoot as string;
  // Les propriétés sont readonly au typage, mais l'objet runtime reste mutable pour isoler ce test.
  (config as unknown as { workspaceRoot: string; comparisonsRoot: string }).workspaceRoot = path.join(root, "workspaces");
  (config as unknown as { workspaceRoot: string; comparisonsRoot: string }).comparisonsRoot = path.join(root, "comparisons");
  try {
    for (const [id, themes] of [["doc_a", ["maintenance", "sécurité"]], ["doc_b", ["maintenance", "coût"]]] as const) {
      const directory = path.join(config.workspaceRoot, id, "analysis");
      await mkdir(directory, { recursive: true });
      await writeFile(path.join(directory, "synthesis.json"), JSON.stringify({
        coreThemes: themes,
        centralProblem: `Problème ${id}`,
        realityVerdict: `Verdict ${id}`,
        operationalModel: `Modèle ${id}`
      }), "utf8");
    }
    const artifact = await compareDocuments(["doc_a", "doc_b"]);
    assert.deepEqual(artifact.commonThemes, ["Maintenance"]);
    assert.deepEqual(artifact.uniqueThemes.doc_a, ["Sécurité"]);
    assert.deepEqual(artifact.uniqueThemes.doc_b, ["Coût"]);
  } finally {
    (config as unknown as { workspaceRoot: string; comparisonsRoot: string }).workspaceRoot = oldWorkspace;
    (config as unknown as { workspaceRoot: string; comparisonsRoot: string }).comparisonsRoot = oldComparisons;
    await rm(root, { recursive: true, force: true });
  }
});
