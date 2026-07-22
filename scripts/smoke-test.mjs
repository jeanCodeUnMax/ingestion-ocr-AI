import { readFile } from "node:fs/promises";
import path from "node:path";

const baseUrl = (process.argv[2] ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const pdfPath = path.resolve(process.argv[3] ?? "./sample-ocr-ai-system.pdf");
const bytes = await readFile(pdfPath);
const form = new FormData();
form.set("instruction", "Transcris, analyse, applique le gant de KENT et produis un pseudocode.");
form.set("provider", "none");
form.set("embeddingProvider", "hash");
form.set("analysisProvider", "rules");
form.set("file", new Blob([bytes], { type: "application/pdf" }), path.basename(pdfPath));

const upload = await fetch(`${baseUrl}/api/documents`, { method: "POST", body: form });
const submitted = await upload.json();
if (!upload.ok) throw new Error(JSON.stringify(submitted));
console.log("Job créé", submitted);

let job;
for (let attempt = 0; attempt < 120; attempt += 1) {
  await new Promise((resolve) => setTimeout(resolve, 500));
  const response = await fetch(`${baseUrl}/api/jobs/${submitted.jobId}`);
  job = await response.json();
  console.log(`${job.status} — ${job.progress?.percent ?? 0}% — ${job.progress?.stage ?? ""}`);
  if (job.status === "completed" || job.status === "failed") break;
}
if (!job || job.status !== "completed") throw new Error(`Job non terminé: ${JSON.stringify(job)}`);
if (job.document?.analysis?.status !== "complete") throw new Error("Analyse v0.4 incomplète.");
if (job.document?.analysis?.segmentsCompleted !== job.document?.analysis?.segmentsExpected) {
  throw new Error("Tous les segments d'analyse n'ont pas été traités.");
}

const analysisResponse = await fetch(`${baseUrl}/api/documents/${submitted.documentId}/analysis`);
const analysis = await analysisResponse.json();
if (!analysisResponse.ok) throw new Error(JSON.stringify(analysis));
const ids = analysis.kent?.[0]?.questions?.map((question) => question.id) ?? [];
const expected = ["claim", "tenants", "aboutissants", "interests", "evidence", "reality_slap"];
if (JSON.stringify(ids) !== JSON.stringify(expected)) throw new Error(`Contrat KENT invalide: ${JSON.stringify(ids)}`);

const query = "gifle de la réalité maintenance";
const search = await fetch(
  `${baseUrl}/api/documents/${submitted.documentId}/search?q=${encodeURIComponent(query)}&limit=5`
);
const result = await search.json();
if (!search.ok) throw new Error(JSON.stringify(result));
if (!result.results?.some((item) => item.contentType === "kent_reality_check")) {
  throw new Error("Le chunk du gant de KENT n'est pas retrouvé dans l'index.");
}
console.log(JSON.stringify({
  documentId: submitted.documentId,
  coverage: job.document.coverage,
  analysis: job.document.analysis,
  embedding: job.document.embedding,
  kentQuestionIds: ids,
  topResults: result.results.map((item) => ({ contentType: item.contentType, pageStart: item.pageStart, score: item.score }))
}, null, 2));
