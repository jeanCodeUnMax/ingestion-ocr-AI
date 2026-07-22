import { createReadStream } from "node:fs";
import { access, mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import multipart from "@fastify/multipart";
import Fastify, { type FastifyRequest } from "fastify";
import { config } from "./config.js";
import { createAnalysisProvider } from "./analysis/router.js";
import { compareDocuments, readComparison } from "./comparison/service.js";
import { createEmbeddingProvider } from "./embeddings/router.js";
import { enqueueDocument } from "./core/enqueue.js";
import { normalizeRecipe } from "./core/recipe.js";
import { ProjectStore } from "./projects/project-store.js";
import { fetchPublicDocument, htmlToMarkdown } from "./ingestion/url-fetcher.js";
import { answerProjectQuestion } from "./chat/service.js";
import { detectInputKind, acceptedExtensions } from "./ingestion/detect.js";
import { JobStore } from "./jobs/job-store.js";
import { PersistentJobWorker } from "./jobs/worker.js";
import { BillingLedger } from "./platform/billing.js";
import { identityFromAuthorization, loginUser, personalIdentity, registerUser } from "./platform/auth.js";
import { assertFeature, assertInputKindEnabled, platformStatus } from "./platform/features.js";
import { createProvider } from "./providers/router.js";
import type {
  AnalysisProviderId,
  DocumentManifest,
  EmbeddingProviderId,
  PlatformIdentity,
  ProviderId,
  TranslationProviderId,
  ProcessingRecipe,
  RecipeProfile,
  ProjectManifest
} from "./types.js";
import { safeFilename } from "./utils/files.js";
import { SqliteVectorStore } from "./vector/sqlite-vector-store.js";
import { readWorkspaceFile, workspaceTree } from "./core/workspace-browser.js";

async function readManifest(id: string): Promise<DocumentManifest | undefined> {
  try {
    return JSON.parse(await readFile(path.join(config.workspaceRoot, id, "manifest.json"), "utf8")) as DocumentManifest;
  } catch {
    return undefined;
  }
}

const identities = new WeakMap<object, PlatformIdentity>();
function identityFor(request: FastifyRequest): PlatformIdentity {
  return identities.get(request) ?? personalIdentity();
}

function isPublicApi(url: string): boolean {
  return url === "/api/health" || url === "/api/platform" || url === "/api/auth/login" || url === "/api/auth/register";
}

function canAccess(identity: PlatformIdentity, manifest: DocumentManifest): boolean {
  if (!config.featureFlags.auth) return true;
  if (identity.roles.includes("admin")) return true;
  return config.featureFlags.multiTenant
    ? identity.tenantId === manifest.ownership.tenantId
    : identity.userId === manifest.ownership.userId;
}

async function authorizedManifest(request: FastifyRequest, documentIdValue: string): Promise<DocumentManifest | undefined> {
  const manifest = await readManifest(documentIdValue);
  if (!manifest) return undefined;
  if (!canAccess(identityFor(request), manifest)) throw new Error("DOCUMENT_ACCESS_DENIED");
  return manifest;
}

function canAccessProject(identity: PlatformIdentity, project: ProjectManifest): boolean {
  if (!config.featureFlags.auth) return true;
  if (identity.roles.includes("admin")) return true;
  return config.featureFlags.multiTenant
    ? identity.tenantId === project.ownership.tenantId
    : identity.userId === project.ownership.userId;
}

async function authorizedProject(request: FastifyRequest, projectId: string): Promise<ProjectManifest | undefined> {
  const project = await projects.get(projectId);
  if (!project) return undefined;
  if (!canAccessProject(identityFor(request), project)) throw new Error("PROJECT_ACCESS_DENIED");
  return project;
}

function recipeFromValue(value: unknown, fallback?: ProcessingRecipe): ProcessingRecipe {
  if (!value) return fallback ?? normalizeRecipe(undefined, config.defaultRecipeProfile);
  if (typeof value === "string") {
    try { return normalizeRecipe(JSON.parse(value) as Partial<ProcessingRecipe>, fallback?.profile ?? config.defaultRecipeProfile); }
    catch { throw new Error("PROCESSING_RECIPE_INVALID_JSON"); }
  }
  return normalizeRecipe(value as Partial<ProcessingRecipe>, fallback?.profile ?? config.defaultRecipeProfile);
}

function providerValues(input?: { provider?: string; embeddingProvider?: string; analysisProvider?: string; translationProvider?: string }) {
  const providerId: ProviderId = input?.provider === "llama-cpp" || input?.provider === "mistral" || input?.provider === "none" ? input.provider : config.provider;
  const embeddingProviderId: EmbeddingProviderId = input?.embeddingProvider === "llama-cpp" || input?.embeddingProvider === "mistral" || input?.embeddingProvider === "hash" ? input.embeddingProvider : config.embeddingProvider;
  const analysisProviderId: AnalysisProviderId = input?.analysisProvider === "llama-cpp" || input?.analysisProvider === "mistral" || input?.analysisProvider === "rules" ? input.analysisProvider : config.analysisProvider;
  const translationProviderId: TranslationProviderId = input?.translationProvider === "llama-cpp" || input?.translationProvider === "mistral" || input?.translationProvider === "none" ? input.translationProvider : config.translationProvider;
  return { providerId, embeddingProviderId, analysisProviderId, translationProviderId };
}

async function recordDocumentBilling(identity: PlatformIdentity, documentId: string, inputKind: string, filename: string): Promise<void> {
  await billing.record({
    at: new Date().toISOString(),
    tenantId: identity.tenantId,
    userId: identity.userId,
    documentId,
    metric: "document",
    quantity: 1,
    metadata: { inputKind, filename }
  });
}

function enqueueResponse(result: Awaited<ReturnType<typeof enqueueDocument>>) {
  return {
    jobId: result.job.jobId,
    documentId: result.documentId,
    inputKind: result.inputKind,
    recipe: result.recipe,
    status: result.job.status,
    statusUrl: `/api/jobs/${result.job.jobId}`,
    manifestUrl: `/api/documents/${result.documentId}/manifest`,
    workspaceUrl: `/api/documents/${result.documentId}/workspace`,
    searchUrl: `/api/documents/${result.documentId}/search?q=votre+question`,
    analysisUrl: `/api/documents/${result.documentId}/analysis`
  };
}

const app = Fastify({ logger: true, bodyLimit: config.maxUploadBytes });
await app.register(multipart, {
  limits: { fileSize: config.maxUploadBytes, files: 20, fields: 64 }
});

app.addHook("onRequest", async (request, reply) => {
  if (!request.url.startsWith("/api/") || isPublicApi(request.url.split("?")[0] ?? request.url)) {
    identities.set(request, personalIdentity());
    return;
  }
  if (!config.featureFlags.auth) {
    identities.set(request, personalIdentity());
    return;
  }
  const identity = identityFromAuthorization(request.headers.authorization);
  if (!identity) {
    await reply.code(401).send({ error: "AUTH_REQUIRED" });
    return;
  }
  identities.set(request, identity);
});

const jobs = new JobStore(config.jobsRoot);
const vectors = new SqliteVectorStore(config.vectorDbPath);
const billing = new BillingLedger();
const projects = new ProjectStore(config.projectsRoot);
await Promise.all([vectors.initialize(), projects.initialize()]);
const worker = new PersistentJobWorker(jobs, vectors, config.jobPollIntervalMs, billing, projects);
const recoveredJobs = await worker.initialize();
worker.start();

app.addHook("onClose", async () => {
  worker.stop();
  vectors.close();
});

app.get("/", async (_request, reply) => {
  const html = await readFile(path.resolve("./public/index.html"), "utf8");
  reply.type("text/html; charset=utf-8");
  return html;
});

app.get("/api/platform", async () => ({
  version: "0.6.0",
  ...platformStatus(),
  acceptedExtensions: acceptedExtensions(),
  audioTranscriptionProvider: config.audioTranscriptionProvider,
  billing: billing.status()
}));

app.post("/api/auth/register", async (request, reply) => {
  if (!config.featureFlags.auth) return reply.code(409).send({ error: "AUTH_FEATURE_DISABLED" });
  const body = request.body as { email?: string; password?: string; tenantId?: string };
  try {
    return await registerUser(body.email ?? "", body.password ?? "", body.tenantId);
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : String(error) });
  }
});

app.post("/api/auth/login", async (request, reply) => {
  if (!config.featureFlags.auth) return reply.code(409).send({ error: "AUTH_FEATURE_DISABLED" });
  const body = request.body as { email?: string; password?: string };
  try {
    return await loginUser(body.email ?? "", body.password ?? "");
  } catch (error) {
    return reply.code(401).send({ error: error instanceof Error ? error.message : String(error) });
  }
});

app.get("/api/auth/me", async (request) => identityFor(request));

app.get("/api/billing/status", async () => billing.status());
app.get("/api/billing/usage", async (request, reply) => {
  if (!config.featureFlags.billing) return reply.code(409).send({ error: "BILLING_FEATURE_DISABLED", status: billing.status() });
  const identity = identityFor(request);
  return { tenantId: identity.tenantId, events: await billing.list(identity.tenantId) };
});

app.get("/api/health", async () => {
  const ocrProvider = createProvider(config.provider);
  const embeddingProvider = createEmbeddingProvider(config.embeddingProvider);
  const analysisProvider = createAnalysisProvider(config.analysisProvider);
  return {
    status: "ok",
    version: "0.6.0",
    recoveredJobs,
    deploymentMode: config.deploymentMode,
    features: config.featureFlags,
    configuredOcrProvider: config.provider,
    configuredEmbeddingProvider: config.embeddingProvider,
    configuredAnalysisProvider: config.analysisProvider,
    configuredTranslationProvider: config.translationProvider,
    ocrHealth: await ocrProvider.health(),
    embeddingHealth: await embeddingProvider.health(),
    analysisHealth: await analysisProvider.health(),
    queuedJobs: (await jobs.list("queued")).length,
    processingJobs: (await jobs.list("processing")).length,
    indexedChunks: vectors.count(),
    workspaceRoot: config.workspaceRoot,
    vectorDbPath: config.vectorDbPath
  };
});

app.get("/api/providers", async () => {
  const ocrIds: ProviderId[] = ["none", "llama-cpp", "mistral"];
  const embeddingIds: EmbeddingProviderId[] = ["hash", "llama-cpp", "mistral"];
  const analysisIds: AnalysisProviderId[] = ["rules", "llama-cpp", "mistral"];
  return {
    ocr: await Promise.all(ocrIds.map(async (id) => {
      const provider = createProvider(id);
      return { id, capabilities: provider.capabilities, health: await provider.health() };
    })),
    embeddings: await Promise.all(embeddingIds.map(async (id) => {
      const provider = createEmbeddingProvider(id);
      return { id, capabilities: provider.capabilities, health: await provider.health() };
    })),
    analysis: await Promise.all(analysisIds.map(async (id) => {
      try {
        const provider = createAnalysisProvider(id);
        return { id, capabilities: provider.capabilities, health: await provider.health() };
      } catch (error) {
        return { id, health: { ok: false, detail: error instanceof Error ? error.message : String(error) } };
      }
    })),
    translation: [
      { id: "none", health: { ok: true, detail: "Traduction désactivée." } },
      { id: "llama-cpp", model: config.llamaCpp.analysisModel },
      { id: "mistral", model: config.mistral.analysisModel }
    ]
  };
});

app.post("/api/documents", async (request, reply) => {
  const parts = request.parts();
  let file: Buffer | undefined;
  let filename = "document.pdf";
  let mimeType = "application/octet-stream";
  const fields: Record<string, string> = {};
  for await (const part of parts) {
    if (part.type === "file") {
      file = await part.toBuffer();
      filename = part.filename;
      mimeType = part.mimetype || mimeType;
    } else {
      fields[part.fieldname] = String(part.value ?? "");
    }
  }
  if (!file) return reply.code(400).send({ error: "Fichier manquant." });
  const providers = providerValues(fields);
  try {
    const project = fields.projectId ? await authorizedProject(request, fields.projectId) : undefined;
    if (fields.projectId && !project) return reply.code(404).send({ error: "Projet introuvable." });
    const recipe = recipeFromValue(fields.recipe, project?.defaultRecipe);
    const result = await enqueueDocument({
      jobs,
      projects,
      identity: identityFor(request),
      buffer: file,
      filename,
      mimeType,
      instruction: fields.instruction ?? project?.instruction ?? "",
      ...providers,
      ...(fields.targetLanguage ? { targetLanguage: fields.targetLanguage } : {}),
      ...(fields.projectId ? { projectId: fields.projectId } : {}),
      sourceOrigin: "upload",
      recipe
    });
    await recordDocumentBilling(identityFor(request), result.documentId, result.inputKind, filename);
    void worker.runOnce();
    return reply.code(202).send(enqueueResponse(result));
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return reply.code(message.includes("ACCESS_DENIED") ? 403 : message.includes("NOT_FOUND") ? 404 : message.includes("DISABLED") ? 409 : 400).send({ error: message });
  }
});

app.post("/api/projects", async (request, reply) => {
  try { assertFeature("projects"); } catch { return reply.code(409).send({ error: "FEATURE_DISABLED:projects" }); }
  const body = request.body as { name?: string; description?: string; instruction?: string; recipeProfile?: RecipeProfile; recipe?: Partial<ProcessingRecipe> };
  try {
    const defaultRecipe = normalizeRecipe(body.recipe, body.recipeProfile ?? config.defaultRecipeProfile);
    const project = await projects.create({
      name: body.name ?? "Nouveau projet",
      ...(body.description !== undefined ? { description: body.description } : {}),
      ...(body.instruction !== undefined ? { instruction: body.instruction } : {}),
      identity: identityFor(request),
      deploymentMode: config.deploymentMode,
      defaultRecipe
    });
    return reply.code(201).send(project);
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : String(error) });
  }
});

app.get("/api/projects", async (request, reply) => {
  try { assertFeature("projects"); } catch { return reply.code(409).send({ error: "FEATURE_DISABLED:projects" }); }
  const identity = identityFor(request);
  return (await projects.list()).filter((project) => canAccessProject(identity, project));
});

app.get("/api/projects/:projectId", async (request, reply) => {
  const { projectId } = request.params as { projectId: string };
  try {
    const project = await authorizedProject(request, projectId);
    if (!project) return reply.code(404).send({ error: "Projet introuvable." });
    return project;
  } catch { return reply.code(403).send({ error: "PROJECT_ACCESS_DENIED" }); }
});

app.patch("/api/projects/:projectId", async (request, reply) => {
  const { projectId } = request.params as { projectId: string };
  let project: ProjectManifest | undefined;
  try { project = await authorizedProject(request, projectId); } catch { return reply.code(403).send({ error: "PROJECT_ACCESS_DENIED" }); }
  if (!project) return reply.code(404).send({ error: "Projet introuvable." });
  const body = request.body as { name?: string; description?: string; instruction?: string; recipe?: Partial<ProcessingRecipe>; recipeProfile?: RecipeProfile };
  if (body.name !== undefined) project.name = body.name.trim() || project.name;
  if (body.description !== undefined) project.description = body.description.trim();
  if (body.instruction !== undefined) project.instruction = body.instruction.trim();
  if (body.recipe || body.recipeProfile) project.defaultRecipe = normalizeRecipe(body.recipe, body.recipeProfile ?? project.defaultRecipe.profile);
  await projects.save(project);
  return project;
});

app.post("/api/projects/:projectId/documents", async (request, reply) => {
  const { projectId } = request.params as { projectId: string };
  let project: ProjectManifest | undefined;
  try { project = await authorizedProject(request, projectId); } catch { return reply.code(403).send({ error: "PROJECT_ACCESS_DENIED" }); }
  if (!project) return reply.code(404).send({ error: "Projet introuvable." });
  const files: Array<{ buffer: Buffer; filename: string; mimeType: string }> = [];
  const fields: Record<string, string> = {};
  for await (const part of request.parts()) {
    if (part.type === "file") files.push({ buffer: await part.toBuffer(), filename: part.filename, mimeType: part.mimetype || "application/octet-stream" });
    else fields[part.fieldname] = String(part.value ?? "");
  }
  if (files.length === 0) return reply.code(400).send({ error: "Aucun fichier fourni." });
  const providers = providerValues(fields);
  try {
    const recipe = recipeFromValue(fields.recipe, project.defaultRecipe);
    const created = [];
    for (const file of files) {
      const result = await enqueueDocument({
        jobs, projects, identity: identityFor(request), ...file,
        instruction: fields.instruction ?? project.instruction,
        ...providers,
        ...(fields.targetLanguage ? { targetLanguage: fields.targetLanguage } : {}),
        projectId,
        sourceOrigin: "upload",
        recipe
      });
      await recordDocumentBilling(identityFor(request), result.documentId, result.inputKind, file.filename);
      created.push(enqueueResponse(result));
    }
    void worker.runOnce();
    return reply.code(202).send({ projectId, count: created.length, documents: created });
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : String(error) });
  }
});

app.post("/api/projects/:projectId/documents/text", async (request, reply) => {
  const { projectId } = request.params as { projectId: string };
  let project: ProjectManifest | undefined;
  try { project = await authorizedProject(request, projectId); } catch { return reply.code(403).send({ error: "PROJECT_ACCESS_DENIED" }); }
  if (!project) return reply.code(404).send({ error: "Projet introuvable." });
  const body = request.body as { text?: string; filename?: string; instruction?: string; recipe?: Partial<ProcessingRecipe>; recipeProfile?: RecipeProfile; provider?: string; embeddingProvider?: string; analysisProvider?: string; translationProvider?: string; targetLanguage?: string };
  if (!body.text?.trim()) return reply.code(400).send({ error: "Texte manquant." });
  const providers = providerValues(body);
  try {
    const recipe = normalizeRecipe(body.recipe, body.recipeProfile ?? project.defaultRecipe.profile);
    const filename = body.filename?.trim() || "texte_colle.md";
    const result = await enqueueDocument({
      jobs, projects, identity: identityFor(request), buffer: Buffer.from(body.text, "utf8"), filename,
      mimeType: filename.endsWith(".txt") ? "text/plain" : "text/markdown",
      instruction: body.instruction ?? project.instruction,
      ...providers,
      ...(body.targetLanguage ? { targetLanguage: body.targetLanguage } : {}),
      projectId,
      sourceOrigin: "paste",
      recipe
    });
    await recordDocumentBilling(identityFor(request), result.documentId, result.inputKind, filename);
    void worker.runOnce();
    return reply.code(202).send(enqueueResponse(result));
  } catch (error) { return reply.code(400).send({ error: error instanceof Error ? error.message : String(error) }); }
});

app.post("/api/projects/:projectId/documents/url", async (request, reply) => {
  try { assertFeature("urlIngestion"); } catch { return reply.code(409).send({ error: "FEATURE_DISABLED:urlIngestion" }); }
  const { projectId } = request.params as { projectId: string };
  let project: ProjectManifest | undefined;
  try { project = await authorizedProject(request, projectId); } catch { return reply.code(403).send({ error: "PROJECT_ACCESS_DENIED" }); }
  if (!project) return reply.code(404).send({ error: "Projet introuvable." });
  const body = request.body as { url?: string; instruction?: string; recipe?: Partial<ProcessingRecipe>; recipeProfile?: RecipeProfile; provider?: string; embeddingProvider?: string; analysisProvider?: string; translationProvider?: string; targetLanguage?: string };
  if (!body.url?.trim()) return reply.code(400).send({ error: "URL manquante." });
  try {
    const fetched = await fetchPublicDocument(body.url, { maxBytes: config.maxUrlBytes, timeoutMs: config.urlFetchTimeoutMs });
    const isHtml = fetched.mimeType === "text/html" || fetched.mimeType === "application/xhtml+xml";
    const file = isHtml
      ? { buffer: Buffer.from(htmlToMarkdown(fetched.body.toString("utf8"), fetched.finalUrl), "utf8"), filename: `${path.parse(fetched.filename).name || "page_web"}.md`, mimeType: "text/markdown" }
      : { buffer: fetched.body, filename: fetched.filename, mimeType: fetched.mimeType };
    const providers = providerValues(body);
    const recipe = normalizeRecipe(body.recipe, body.recipeProfile ?? project.defaultRecipe.profile);
    const result = await enqueueDocument({
      jobs, projects, identity: identityFor(request), ...file,
      instruction: body.instruction ?? project.instruction,
      ...providers,
      ...(body.targetLanguage ? { targetLanguage: body.targetLanguage } : {}),
      projectId,
      sourceOrigin: "url",
      sourceUrl: fetched.finalUrl,
      recipe
    });
    await recordDocumentBilling(identityFor(request), result.documentId, result.inputKind, file.filename);
    void worker.runOnce();
    return reply.code(202).send(enqueueResponse(result));
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return reply.code(message.includes("PRIVATE") ? 403 : 400).send({ error: message });
  }
});

app.post("/api/projects/:projectId/chat", async (request, reply) => {
  try { assertFeature("chatRag"); } catch { return reply.code(409).send({ error: "FEATURE_DISABLED:chatRag" }); }
  const { projectId } = request.params as { projectId: string };
  let project: ProjectManifest | undefined;
  try { project = await authorizedProject(request, projectId); } catch { return reply.code(403).send({ error: "PROJECT_ACCESS_DENIED" }); }
  if (!project) return reply.code(404).send({ error: "Projet introuvable." });
  const body = request.body as { question?: string; provider?: AnalysisProviderId; embeddingProvider?: EmbeddingProviderId; limit?: number; conversationId?: string };
  if (!body.question?.trim()) return reply.code(400).send({ error: "Question manquante." });
  try {
    return await answerProjectQuestion({
      project,
      question: body.question.trim(),
      vectorStore: vectors,
      provider: body.provider ?? config.analysisProvider,
      ...(body.embeddingProvider ? { embeddingProviderId: body.embeddingProvider } : {}),
      ...(body.limit !== undefined ? { limit: body.limit } : {}),
      ...(body.conversationId ? { conversationId: body.conversationId } : {}),
      projectsRoot: config.projectsRoot
    });
  } catch (error) { return reply.code(400).send({ error: error instanceof Error ? error.message : String(error) }); }
});

app.get("/api/projects/:projectId/workspace", async (request, reply) => {
  const { projectId } = request.params as { projectId: string };
  try {
    const project = await authorizedProject(request, projectId);
    if (!project) return reply.code(404).send({ error: "Projet introuvable." });
    return { project, tree: await workspaceTree(projects.projectRoot(projectId)) };
  } catch (error) { return reply.code(403).send({ error: error instanceof Error ? error.message : String(error) }); }
});

app.get("/api/jobs", async (request) => {
  const identity = identityFor(request);
  const { status } = request.query as { status?: string };
  const allowed = ["queued", "processing", "completed", "failed", "cancelled"];
  const list = allowed.includes(status ?? "")
    ? await jobs.list(status as Parameters<JobStore["list"]>[0])
    : await jobs.list();
  return config.featureFlags.auth ? list.filter((job) => job.payload.identity.tenantId === identity.tenantId) : list;
});

app.get("/api/jobs/:jobId", async (request, reply) => {
  const { jobId } = request.params as { jobId: string };
  const job = await jobs.get(jobId);
  if (!job) return reply.code(404).send({ error: "Job introuvable." });
  if (config.featureFlags.auth && job.payload.identity.tenantId !== identityFor(request).tenantId) {
    return reply.code(403).send({ error: "JOB_ACCESS_DENIED" });
  }
  const manifest = await readManifest(job.documentId);
  return {
    ...job,
    document: manifest
      ? { status: manifest.status, coverage: manifest.coverage, analysis: manifest.analysis, translation: manifest.translation, embedding: manifest.embedding }
      : undefined
  };
});

app.post("/api/jobs/:jobId/retry", async (request, reply) => {
  const { jobId } = request.params as { jobId: string };
  const existing = await jobs.get(jobId);
  if (!existing) return reply.code(404).send({ error: "Job introuvable." });
  if (config.featureFlags.auth && existing.payload.identity.tenantId !== identityFor(request).tenantId) {
    return reply.code(403).send({ error: "JOB_ACCESS_DENIED" });
  }
  const job = await jobs.retry(jobId);
  void worker.runOnce();
  return job;
});

app.get("/api/documents/:documentId/manifest", async (request, reply) => {
  const { documentId: id } = request.params as { documentId: string };
  try {
    const manifest = await authorizedManifest(request, id);
    if (!manifest) return reply.code(404).send({ error: "Document introuvable." });
  } catch {
    return reply.code(403).send({ error: "DOCUMENT_ACCESS_DENIED" });
  }
  reply.type("application/json");
  return createReadStream(path.join(config.workspaceRoot, id, "manifest.json"));
});

app.get("/api/documents/:documentId/markdown", async (request, reply) => {
  const { documentId: id } = request.params as { documentId: string };
  try {
    const manifest = await authorizedManifest(request, id);
    if (!manifest) return reply.code(404).send({ error: "Document introuvable." });
  } catch { return reply.code(403).send({ error: "DOCUMENT_ACCESS_DENIED" }); }
  const filePath = path.join(config.workspaceRoot, id, "transcription", "full_document.md");
  try { await access(filePath); } catch { return reply.code(404).send({ error: "Markdown introuvable." }); }
  reply.header("content-disposition", `attachment; filename=\"${id}.md\"`);
  reply.type("text/markdown; charset=utf-8");
  return createReadStream(filePath);
});

app.get("/api/documents/:documentId/translation", async (request, reply) => {
  const { documentId: id } = request.params as { documentId: string };
  let manifest: DocumentManifest | undefined;
  try { manifest = await authorizedManifest(request, id); } catch { return reply.code(403).send({ error: "DOCUMENT_ACCESS_DENIED" }); }
  if (!manifest) return reply.code(404).send({ error: "Document introuvable." });
  if (!manifest.translation.artifactPath) return reply.code(404).send({ error: "Traduction indisponible.", translation: manifest.translation });
  reply.type("text/markdown; charset=utf-8");
  return createReadStream(path.join(config.workspaceRoot, id, manifest.translation.artifactPath));
});

app.get("/api/documents/:documentId/status", async (request, reply) => {
  const { documentId: id } = request.params as { documentId: string };
  let manifest: DocumentManifest | undefined;
  try { manifest = await authorizedManifest(request, id); } catch { return reply.code(403).send({ error: "DOCUMENT_ACCESS_DENIED" }); }
  if (!manifest) return reply.code(404).send({ error: "Document introuvable." });
  const relatedJob = (await jobs.list()).find((job) => job.documentId === id);
  return {
    documentId: id,
    status: manifest.status,
    coverage: manifest.coverage,
    analysis: manifest.analysis,
    translation: manifest.translation,
    knowledge: manifest.knowledge,
    embedding: manifest.embedding,
    job: relatedJob ? { jobId: relatedJob.jobId, status: relatedJob.status, progress: relatedJob.progress } : undefined
  };
});

app.get("/api/documents/:documentId/analysis", async (request, reply) => {
  const { documentId: id } = request.params as { documentId: string };
  try {
    const manifest = await authorizedManifest(request, id);
    if (!manifest) return reply.code(404).send({ error: "Document introuvable." });
  } catch { return reply.code(403).send({ error: "DOCUMENT_ACCESS_DENIED" }); }
  const filePath = path.join(config.workspaceRoot, id, "analysis", "synthesis.json");
  try { await access(filePath); } catch { return reply.code(404).send({ error: "Analyse indisponible." }); }
  reply.type("application/json");
  return createReadStream(filePath);
});

app.get("/api/documents/:documentId/analysis/:kind", async (request, reply) => {
  const { documentId: id, kind } = request.params as { documentId: string; kind: string };
  try {
    const manifest = await authorizedManifest(request, id);
    if (!manifest) return reply.code(404).send({ error: "Document introuvable." });
  } catch { return reply.code(403).send({ error: "DOCUMENT_ACCESS_DENIED" }); }
  const format = (request.query as { format?: string }).format === "json" ? "json" : "md";
  const locations: Record<string, string> = {
    semantic: path.join("analysis", "semantic", `semantic.${format}`),
    maieutic: path.join("analysis", "maieutic", `maieutic.${format}`),
    kent: path.join("analysis", "kent_glove", `kent_glove.${format}`),
    pseudocode: path.join("analysis", "pseudocode", `pseudocode.${format}`),
    synthesis: path.join("analysis", `synthesis.${format}`)
  };
  const relative = locations[kind];
  if (!relative) return reply.code(400).send({ error: "Type d'analyse invalide." });
  const filePath = path.join(config.workspaceRoot, id, relative);
  try { await access(filePath); } catch { return reply.code(404).send({ error: "Analyse introuvable." }); }
  reply.type(format === "json" ? "application/json" : "text/markdown; charset=utf-8");
  return createReadStream(filePath);
});

app.get("/api/documents/:documentId/workspace", async (request, reply) => {
  try { assertFeature("advancedWorkspace"); } catch { return reply.code(409).send({ error: "FEATURE_DISABLED:advancedWorkspace" }); }
  const { documentId: id } = request.params as { documentId: string };
  try {
    const manifest = await authorizedManifest(request, id);
    if (!manifest) return reply.code(404).send({ error: "Document introuvable." });
    return { documentId: id, tree: await workspaceTree(path.join(config.workspaceRoot, id)) };
  } catch (error) {
    return reply.code(403).send({ error: error instanceof Error ? error.message : String(error) });
  }
});

app.get("/api/documents/:documentId/workspace/file", async (request, reply) => {
  try { assertFeature("advancedWorkspace"); } catch { return reply.code(409).send({ error: "FEATURE_DISABLED:advancedWorkspace" }); }
  const { documentId: id } = request.params as { documentId: string };
  const { path: relativePath } = request.query as { path?: string };
  if (!relativePath) return reply.code(400).send({ error: "Paramètre path obligatoire." });
  try {
    const manifest = await authorizedManifest(request, id);
    if (!manifest) return reply.code(404).send({ error: "Document introuvable." });
    return await readWorkspaceFile(path.join(config.workspaceRoot, id), relativePath);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return reply.code(message.includes("ACCESS_DENIED") ? 403 : 400).send({ error: message });
  }
});

app.get("/api/documents/:documentId/chunks", async (request, reply) => {
  const { documentId: id } = request.params as { documentId: string };
  try {
    const manifest = await authorizedManifest(request, id);
    if (!manifest) return reply.code(404).send({ error: "Document introuvable." });
  } catch { return reply.code(403).send({ error: "DOCUMENT_ACCESS_DENIED" }); }
  return { documentId: id, count: vectors.count(id), chunks: vectors.listDocumentChunks(id) };
});

app.get("/api/documents/:documentId/search", async (request, reply) => {
  const { documentId: id } = request.params as { documentId: string };
  const { q, limit } = request.query as { q?: string; limit?: string };
  if (!q?.trim()) return reply.code(400).send({ error: "Paramètre q obligatoire." });
  let manifest: DocumentManifest | undefined;
  try { manifest = await authorizedManifest(request, id); } catch { return reply.code(403).send({ error: "DOCUMENT_ACCESS_DENIED" }); }
  if (!manifest) return reply.code(404).send({ error: "Document introuvable." });
  const provider = createEmbeddingProvider(manifest.embeddingProvider);
  const [queryVector] = await provider.embed([q]);
  if (!queryVector) return reply.code(500).send({ error: "Embedding de recherche absent." });
  return {
    query: q,
    documentId: id,
    embeddingModel: provider.capabilities.model,
    results: vectors.search(queryVector, {
      documentId: id,
      embeddingModel: provider.capabilities.model,
      limit: Number.parseInt(limit ?? "8", 10) || 8
    })
  };
});

app.get("/api/search", async (request, reply) => {
  const { q, limit, embeddingProvider } = request.query as { q?: string; limit?: string; embeddingProvider?: EmbeddingProviderId };
  if (!q?.trim()) return reply.code(400).send({ error: "Paramètre q obligatoire." });
  const selected = embeddingProvider ?? config.embeddingProvider;
  const provider = createEmbeddingProvider(selected);
  const [queryVector] = await provider.embed([q]);
  if (!queryVector) return reply.code(500).send({ error: "Embedding de recherche absent." });
  return {
    query: q,
    embeddingProvider: selected,
    embeddingModel: provider.capabilities.model,
    results: vectors.search(queryVector, {
      embeddingModel: provider.capabilities.model,
      limit: Number.parseInt(limit ?? "8", 10) || 8
    })
  };
});

app.post("/api/comparisons", async (request, reply) => {
  try { assertFeature("comparison"); } catch { return reply.code(409).send({ error: "FEATURE_DISABLED:comparison" }); }
  const body = request.body as { documentIds?: string[] };
  const documentIds = body.documentIds ?? [];
  for (const id of documentIds) {
    try {
      const manifest = await authorizedManifest(request, id);
      if (!manifest) return reply.code(404).send({ error: `Document introuvable: ${id}` });
    } catch { return reply.code(403).send({ error: `DOCUMENT_ACCESS_DENIED:${id}` }); }
  }
  try {
    return reply.code(201).send(await compareDocuments(documentIds));
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : String(error) });
  }
});

app.get("/api/comparisons/:comparisonId", async (request, reply) => {
  try { assertFeature("comparison"); } catch { return reply.code(409).send({ error: "FEATURE_DISABLED:comparison" }); }
  const { comparisonId } = request.params as { comparisonId: string };
  const artifact = await readComparison(comparisonId);
  if (!artifact) return reply.code(404).send({ error: "Comparaison introuvable." });
  return artifact;
});

await app.listen({ host: config.host, port: config.port });
