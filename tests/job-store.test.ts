import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { JobStore } from "../src/jobs/job-store.js";

test("un job processing est remis en file après redémarrage", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "ocr-jobs-"));
  const store = new JobStore(root);
  await store.initialize();
  const job = await store.create({
    documentId: "doc1",
    maxAttempts: 3,
    payload: {
      stagedSourcePath: "/tmp/source.pdf",
      stagedPdfPath: "/tmp/source.pdf",
      filename: "source.pdf",
      mimeType: "application/pdf",
      inputKind: "pdf",
      sourceOrigin: "upload",
      recipe: { profile: "standard", semanticAnalysis: true, maieuticAnalysis: true, kentRealityCheck: true, pseudocode: true, synthesis: true, shrink: true, atomicFacts: true, tagsAndTaxonomy: true, embeddings: true, visualDescriptions: true, translation: false },
      instruction: "Transcrire",
      providerId: "none",
      embeddingProviderId: "hash",
      analysisProviderId: "rules",
      translationProviderId: "none",
      identity: { userId: "personal-user", tenantId: "personal-workspace", roles: ["owner"], anonymous: true }
    }
  });
  const claimed = await store.claimNext();
  assert.equal(claimed?.status, "processing");

  const reloaded = new JobStore(root);
  const recovered = await reloaded.recoverInterrupted();
  assert.equal(recovered, 1);
  const after = await reloaded.get(job.jobId);
  assert.equal(after?.status, "queued");
  assert.equal(after?.attempts, 1);
  await rm(root, { recursive: true, force: true });
});
