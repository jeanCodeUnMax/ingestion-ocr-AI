import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { ProjectStore } from "../src/projects/project-store.js";
import { recipeForProfile } from "../src/core/recipe.js";

test("un projet isole sa liste de documents et sa recette", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "ocr-projects-"));
  try {
    const store = new ProjectStore(root);
    const projectA = await store.create({ name: "Maintenance", identity: { userId: "u1", tenantId: "t1", roles: ["owner"], anonymous: false }, deploymentMode: "personal", defaultRecipe: recipeForProfile("standard") });
    const projectB = await store.create({ name: "Finance", identity: { userId: "u1", tenantId: "t1", roles: ["owner"], anonymous: false }, deploymentMode: "personal", defaultRecipe: recipeForProfile("quick") });
    await store.attachDocument({ projectId: projectA.projectId, documentId: "doc_a", filename: "maintenance.pdf", inputKind: "pdf", sourceOrigin: "upload" });
    const reloadedA = await store.get(projectA.projectId);
    const reloadedB = await store.get(projectB.projectId);
    assert.deepEqual(reloadedA?.documents.map((item) => item.documentId), ["doc_a"]);
    assert.equal(reloadedB?.documents.length, 0);
    assert.equal(reloadedA?.defaultRecipe.kentRealityCheck, true);
    assert.equal(reloadedB?.defaultRecipe.kentRealityCheck, false);
  } finally { await rm(root, { recursive: true, force: true }); }
});
