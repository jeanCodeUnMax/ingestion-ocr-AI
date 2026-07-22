const base = (process.argv[2] ?? "http://127.0.0.1:8000").replace(/\/$/, "");
async function api(path, options = {}) {
  const response = await fetch(`${base}${path}`, options);
  const value = await response.json();
  if (!response.ok) throw new Error(`${path}: ${JSON.stringify(value)}`);
  return value;
}
const project = await api("/api/projects", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ name: "Smoke v0.6", instruction: "Construire une base de connaissance sourcée.", recipeProfile: "standard" }) });
const document = await api(`/api/projects/${project.projectId}/documents/text`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ filename: "preuve.md", text: "# Maintenance\n\nLa vibration doit être mesurée chaque semaine. Une alarme supérieure à 10 mm/s ne doit jamais être ignorée.", provider: "none", embeddingProvider: "hash", analysisProvider: "rules" }) });
let job;
for (let attempt = 0; attempt < 80; attempt += 1) {
  job = await api(`/api/jobs/${document.jobId}`);
  if (job.status === "completed") break;
  if (job.status === "failed") throw new Error(JSON.stringify(job));
  await new Promise((resolve) => setTimeout(resolve, 250));
}
if (job?.status !== "completed") throw new Error("Timeout job");
const manifest = await api(`/api/documents/${document.documentId}/status`);
if (!manifest.coverage.isComplete || manifest.knowledge.status !== "complete" || manifest.embedding.status !== "complete") throw new Error(JSON.stringify(manifest));
const chat = await api(`/api/projects/${project.projectId}/chat`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ question: "Quelle mesure et quel seuil d'alarme ?", provider: "rules", embeddingProvider: "hash" }) });
if (!chat.citations.length || chat.citations.some((citation) => citation.documentId !== document.documentId)) throw new Error(JSON.stringify(chat));
console.log(JSON.stringify({ projectId: project.projectId, documentId: document.documentId, coverage: manifest.coverage, knowledge: manifest.knowledge, citations: chat.citations.length }, null, 2));
