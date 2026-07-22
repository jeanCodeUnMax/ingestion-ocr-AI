import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { HashEmbeddingProvider } from "../src/embeddings/hash.js";
import { SqliteVectorStore } from "../src/vector/sqlite-vector-store.js";

test("la base vectorielle retrouve le chunk sémantiquement le plus proche", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "ocr-vector-"));
  const store = new SqliteVectorStore(path.join(root, "vectors.sqlite"));
  await store.initialize();
  const provider = new HashEmbeddingProvider(128);
  const texts = [
    "La maintenance préventive évite les pannes des moteurs électriques.",
    "Une recette de tarte aux pommes avec de la cannelle.",
    "La méthode 5S organise et standardise le poste de travail."
  ];
  const embeddings = await provider.embed(texts);
  store.upsertMany(texts.map((text, index) => ({
    chunkId: `c${index + 1}`,
    documentId: "doc1",
    pageStart: index + 1,
    pageEnd: index + 1,
    contentType: "semantic_chunk" as const,
    text,
    sourceHash: `h${index + 1}`,
    embeddingModel: provider.capabilities.model,
    dimension: embeddings[index]!.length,
    embedding: embeddings[index]!,
    createdAt: new Date().toISOString()
  })));
  const [query] = await provider.embed(["Comment prévenir les pannes d'un moteur ?"]);
  const results = store.search(query!, { documentId: "doc1", limit: 2 });
  assert.equal(results[0]?.chunkId, "c1");
  assert.equal(store.count("doc1"), 3);
  store.close();
  await rm(root, { recursive: true, force: true });
});
