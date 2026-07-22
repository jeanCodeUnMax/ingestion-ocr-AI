import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { answerProjectQuestion } from "../src/chat/service.js";
import { ProjectStore } from "../src/projects/project-store.js";
import { recipeForProfile } from "../src/core/recipe.js";
import { SqliteVectorStore } from "../src/vector/sqlite-vector-store.js";
import { createEmbeddingProvider } from "../src/embeddings/router.js";
import type { StoredVectorChunk } from "../src/types.js";

test("le chat RAG ne cite que les documents du projet", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "ocr-chat-"));
  const db = new SqliteVectorStore(path.join(root, "vectors.sqlite"));
  try {
    await db.initialize();
    const projectStore = new ProjectStore(path.join(root, "projects"));
    const project = await projectStore.create({ name: "Maintenance", identity: { userId: "u", tenantId: "t", roles: ["owner"], anonymous: false }, deploymentMode: "personal", defaultRecipe: recipeForProfile("standard") });
    await projectStore.attachDocument({ projectId: project.projectId, documentId: "doc_in", filename: "moteur.md", inputKind: "markdown", sourceOrigin: "paste", status: "complete" });
    const reloaded = await projectStore.get(project.projectId);
    assert.ok(reloaded);
    const provider = createEmbeddingProvider("hash");
    const texts = ["La maintenance préventive réduit les pannes du moteur.", "Les recettes de cuisine utilisent du beurre."];
    const embeddings = await provider.embed(texts);
    const now = new Date().toISOString();
    const rows: StoredVectorChunk[] = texts.map((text, index) => ({
      chunkId: `c${index}`, documentId: index === 0 ? "doc_in" : "doc_out", pageStart: 1, pageEnd: 1,
      contentType: "semantic_chunk", text, sourceHash: `h${index}`, embeddingModel: provider.capabilities.model,
      dimension: embeddings[index]!.length, embedding: embeddings[index]!, createdAt: now
    }));
    db.upsertMany(rows);
    const answer = await answerProjectQuestion({ project: reloaded!, question: "Comment réduire les pannes du moteur ?", vectorStore: db, provider: "rules", projectsRoot: path.join(root, "projects") });
    assert.ok(answer.citations.length > 0);
    assert.ok(answer.citations.every((citation) => citation.documentId === "doc_in"));
    assert.doesNotMatch(answer.answer, /beurre/);
  } finally { db.close(); await rm(root, { recursive: true, force: true }); }
});
