import { readFile } from "node:fs/promises";
import path from "node:path";

const baseUrl = (process.argv[2] ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const sourcePath = path.resolve(process.argv[3] ?? "./samples/sample.json");
const bytes = await readFile(sourcePath);
const form = new FormData();
form.set("instruction", "Transcris, analyse, applique le gant de KENT et produis un pseudocode.");
form.set("provider", "none");
form.set("embeddingProvider", "hash");
form.set("analysisProvider", "rules");
form.set("translationProvider", "none");
form.set("file", new Blob([bytes]), path.basename(sourcePath));

const platformResponse = await fetch(`${baseUrl}/api/platform`);
const platform = await platformResponse.json();
if (!platformResponse.ok) throw new Error(JSON.stringify(platform));

const upload = await fetch(`${baseUrl}/api/documents`, { method: "POST", body: form });
const submitted = await upload.json();
if (!upload.ok) throw new Error(JSON.stringify(submitted));
console.log("Job créé", submitted);

let job;
for (let attempt = 0; attempt < 180; attempt += 1) {
  await new Promise((resolve) => setTimeout(resolve, 500));
  const response = await fetch(`${baseUrl}/api/jobs/${submitted.jobId}`);
  job = await response.json();
  console.log(`${job.status} — ${job.progress?.percent ?? 0}% — ${job.progress?.stage ?? ""}`);
  if (job.status === "completed" || job.status === "failed") break;
}
if (!job || job.status !== "completed") throw new Error(`Job non terminé: ${JSON.stringify(job)}`);
if (job.document?.coverage?.pagesSuccessful !== job.document?.coverage?.pagesDetected) {
  throw new Error("Couverture documentaire incomplète.");
}
if (job.document?.analysis?.status !== "complete") throw new Error("Analyse incomplète.");
if (job.document?.embedding?.status !== "complete") throw new Error("Indexation incomplète.");

const workspaceResponse = await fetch(`${baseUrl}/api/documents/${submitted.documentId}/workspace`);
const workspace = await workspaceResponse.json();
if (!workspaceResponse.ok || !Array.isArray(workspace.tree)) throw new Error(JSON.stringify(workspace));

const analysisResponse = await fetch(`${baseUrl}/api/documents/${submitted.documentId}/analysis`);
const analysis = await analysisResponse.json();
const ids = analysis.kent?.[0]?.questions?.map((question) => question.id) ?? [];
const expected = ["claim", "tenants", "aboutissants", "interests", "evidence", "reality_slap"];
if (JSON.stringify(ids) !== JSON.stringify(expected)) throw new Error(`Contrat KENT invalide: ${JSON.stringify(ids)}`);

console.log(JSON.stringify({
  platform: { deploymentMode: platform.deploymentMode, features: platform.features },
  documentId: submitted.documentId,
  inputKind: submitted.inputKind,
  coverage: job.document.coverage,
  analysis: job.document.analysis,
  translation: job.document.translation,
  embedding: job.document.embedding,
  workspaceRootEntries: workspace.tree.map((node) => node.name),
  kentQuestionIds: ids
}, null, 2));
