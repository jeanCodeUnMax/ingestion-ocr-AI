import "dotenv/config";
import path from "node:path";
import type { AnalysisProviderId, AudioProviderId, DeploymentMode, EmbeddingProviderId, FeatureFlags, ProviderId, TranslationProviderId } from "./types.js";


function boolEnv(name: string, fallback: boolean): boolean {
  const value = process.env[name];
  if (value === undefined || value === "") return fallback;
  if (["1", "true", "yes", "on"].includes(value.toLowerCase())) return true;
  if (["0", "false", "no", "off"].includes(value.toLowerCase())) return false;
  throw new Error(`${name} doit être un booléen.`);
}

function deploymentModeEnv(value: string | undefined): DeploymentMode {
  if (value === "personal" || value === "saas" || value === "enterprise") return value;
  throw new Error(`DEPLOYMENT_MODE invalide: ${value ?? "undefined"}`);
}


function audioProviderEnv(value: string | undefined): AudioProviderId {
  if (value === "none" || value === "mistral" || value === "whisper-cpp") return value;
  throw new Error(`AUDIO_TRANSCRIPTION_PROVIDER invalide: ${value ?? "undefined"}`);
}

function translationProviderEnv(value: string | undefined): TranslationProviderId {
  if (value === "none" || value === "llama-cpp" || value === "mistral") return value;
  throw new Error(`TRANSLATION_PROVIDER invalide: ${value ?? "undefined"}`);
}

function intEnv(name: string, fallback: number): number {
  const value = process.env[name];
  if (!value) return fallback;
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error(`${name} doit être un entier positif.`);
  }
  return parsed;
}

function nonNegativeIntEnv(name: string, fallback: number): number {
  const value = process.env[name];
  if (!value) return fallback;
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed < 0) {
    throw new Error(`${name} doit être un entier positif ou nul.`);
  }
  return parsed;
}

function floatEnv(name: string, fallback: number): number {
  const value = process.env[name];
  if (!value) return fallback;
  const parsed = Number.parseFloat(value);
  if (!Number.isFinite(parsed) || parsed <= 0 || parsed > 1) {
    throw new Error(`${name} doit être compris entre 0 et 1.`);
  }
  return parsed;
}

function providerEnv(value: string | undefined): ProviderId {
  if (value === "llama-cpp" || value === "mistral" || value === "none") return value;
  throw new Error(`OCR_PROVIDER invalide: ${value ?? "undefined"}`);
}

function embeddingProviderEnv(value: string | undefined): EmbeddingProviderId {
  if (value === "hash" || value === "llama-cpp" || value === "mistral") return value;
  throw new Error(`EMBEDDING_PROVIDER invalide: ${value ?? "undefined"}`);
}

function analysisProviderEnv(value: string | undefined): AnalysisProviderId {
  if (value === "rules" || value === "llama-cpp" || value === "mistral") return value;
  throw new Error(`ANALYSIS_PROVIDER invalide: ${value ?? "undefined"}`);
}

const runtimeRoot = path.resolve(process.env.RUNTIME_ROOT ?? "./runtime");
const deploymentMode = deploymentModeEnv(process.env.DEPLOYMENT_MODE ?? "personal");
const authTokenSecret = process.env.AUTH_TOKEN_SECRET ?? "change-me-before-enabling-auth";

const featureFlags: FeatureFlags = {
  word: boolEnv("FEATURE_WORD", true),
  excel: boolEnv("FEATURE_EXCEL", true),
  csv: boolEnv("FEATURE_CSV", true),
  json: boolEnv("FEATURE_JSON", true),
  markdown: boolEnv("FEATURE_MARKDOWN", true),
  text: boolEnv("FEATURE_TEXT", true),
  image: boolEnv("FEATURE_IMAGE", true),
  audio: boolEnv("FEATURE_AUDIO", false),
  translation: boolEnv("FEATURE_TRANSLATION", true),
  comparison: boolEnv("FEATURE_COMPARISON", true),
  advancedWorkspace: boolEnv("FEATURE_ADVANCED_WORKSPACE", true),
  auth: boolEnv("FEATURE_AUTH", false),
  billing: boolEnv("FEATURE_BILLING", false),
  multiTenant: boolEnv("FEATURE_MULTI_TENANT", false),
  projects: boolEnv("FEATURE_PROJECTS", true),
  urlIngestion: boolEnv("FEATURE_URL_INGESTION", true),
  chatRag: boolEnv("FEATURE_CHAT_RAG", true),
  knowledgeEnrichment: boolEnv("FEATURE_KNOWLEDGE_ENRICHMENT", true),
  svg: boolEnv("FEATURE_SVG", true)
};

if (featureFlags.auth && authTokenSecret === "change-me-before-enabling-auth") {
  throw new Error("AUTH_TOKEN_SECRET doit être remplacé avant d'activer FEATURE_AUTH.");
}
if (featureFlags.multiTenant && !featureFlags.auth) {
  throw new Error("FEATURE_MULTI_TENANT exige FEATURE_AUTH=true.");
}

export const config = {
  host: process.env.HOST ?? "127.0.0.1",
  deploymentMode,
  featureFlags,
  port: intEnv("PORT", 8000),
  workspaceRoot: path.resolve(process.env.WORKSPACE_ROOT ?? "./workspaces"),
  projectsRoot: path.resolve(process.env.PROJECTS_ROOT ?? "./projects"),
  runtimeRoot,
  jobsRoot: path.join(runtimeRoot, "jobs"),
  uploadsRoot: path.join(runtimeRoot, "uploads"),
  vectorDbPath: path.resolve(process.env.VECTOR_DB_PATH ?? path.join(runtimeRoot, "vector", "vectors.sqlite")),
  maxUploadBytes: intEnv("MAX_UPLOAD_BYTES", 512 * 1024 * 1024),
  maxUrlBytes: intEnv("MAX_URL_BYTES", 64 * 1024 * 1024),
  urlFetchTimeoutMs: intEnv("URL_FETCH_TIMEOUT_MS", 30000),
  defaultRecipeProfile: (process.env.DEFAULT_RECIPE_PROFILE ?? "standard") as "quick" | "standard" | "deep" | "custom",
  pythonBin: process.env.PYTHON_BIN ?? "python",
  pdfWorkerPath: path.resolve("./workers/pdf/analyze_pdf.py"),
  pdfRenderDpi: intEnv("PDF_RENDER_DPI", 160),
  pdfFallbackDpi: intEnv("PDF_FALLBACK_DPI", 110),
  minNativeTextChars: intEnv("MIN_NATIVE_TEXT_CHARS", 40),
  visualAnalysisMode: process.env.VISUAL_ANALYSIS_MODE ?? "auto",
  provider: providerEnv(process.env.OCR_PROVIDER ?? "none"),
  embeddingProvider: embeddingProviderEnv(process.env.EMBEDDING_PROVIDER ?? "hash"),
  analysisProvider: analysisProviderEnv(process.env.ANALYSIS_PROVIDER ?? "rules"),
  translationProvider: translationProviderEnv(process.env.TRANSLATION_PROVIDER ?? "none"),
  maxProcessingAttempts: intEnv("MAX_PROCESSING_ATTEMPTS", 3),
  jobMaxAttempts: intEnv("JOB_MAX_ATTEMPTS", 3),
  jobPollIntervalMs: intEnv("JOB_POLL_INTERVAL_MS", 750),
  chunkMaxChars: intEnv("CHUNK_MAX_CHARS", 1800),
  chunkOverlapChars: nonNegativeIntEnv("CHUNK_OVERLAP_CHARS", 240),
  embeddingBatchSize: intEnv("EMBEDDING_BATCH_SIZE", 16),
  hashEmbeddingDimensions: intEnv("HASH_EMBEDDING_DIMENSIONS", 384),
  analysisMaxCharsPerSegment: intEnv("ANALYSIS_MAX_CHARS_PER_SEGMENT", 12000),
  analysisMaxSourceChunksPerSegment: intEnv("ANALYSIS_MAX_SOURCE_CHUNKS_PER_SEGMENT", 8),
  analysisTimeoutMs: intEnv("ANALYSIS_TIMEOUT_MS", 300000),
  translationMaxCharsPerSegment: intEnv("TRANSLATION_MAX_CHARS_PER_SEGMENT", 9000),
  translationTimeoutMs: intEnv("TRANSLATION_TIMEOUT_MS", 300000),
  comparisonsRoot: path.join(runtimeRoot, "comparisons"),
  authRoot: path.join(runtimeRoot, "auth"),
  authTokenSecret,
  authTokenTtlSeconds: intEnv("AUTH_TOKEN_TTL_SECONDS", 86400),
  authAllowRegistration: boolEnv("AUTH_ALLOW_REGISTRATION", false),
  billingRoot: path.join(runtimeRoot, "billing"),
  audioTranscriptionProvider: audioProviderEnv(process.env.AUDIO_TRANSCRIPTION_PROVIDER ?? "none"),
  llamaCpp: {
    baseUrl: (process.env.LLAMA_CPP_BASE_URL ?? "http://127.0.0.1:8080/v1").replace(/\/$/, ""),
    model: process.env.LLAMA_CPP_MODEL ?? "qwen-ocr",
    embeddingModel: process.env.LLAMA_CPP_EMBEDDING_MODEL ?? process.env.LLAMA_CPP_MODEL ?? "embedding-model",
    contextTokens: intEnv("LLAMA_CPP_CONTEXT_TOKENS", 32768),
    maxPages: intEnv("LLAMA_CPP_MAX_PAGES", 5),
    reservedOutputTokens: intEnv("LLAMA_CPP_RESERVED_OUTPUT_TOKENS", 10000),
    safetyRatio: floatEnv("LLAMA_CPP_SAFETY_RATIO", 0.78),
    timeoutMs: intEnv("LLAMA_CPP_TIMEOUT_MS", 300000),
    analysisModel: process.env.LLAMA_CPP_ANALYSIS_MODEL ?? process.env.LLAMA_CPP_MODEL ?? "analysis-model"
  },
  whisperCpp: {
    baseUrl: (process.env.WHISPER_CPP_BASE_URL ?? "http://127.0.0.1:8081").replace(/\/$/, ""),
    timeoutMs: intEnv("WHISPER_CPP_TIMEOUT_MS", 600000),
    language: process.env.WHISPER_CPP_LANGUAGE ?? "auto"
  },
  mistral: {
    apiKey: process.env.MISTRAL_API_KEY ?? "",
    baseUrl: (process.env.MISTRAL_BASE_URL ?? "https://api.mistral.ai/v1").replace(/\/$/, ""),
    model: process.env.MISTRAL_OCR_MODEL ?? "mistral-ocr-latest",
    embeddingModel: process.env.MISTRAL_EMBEDDING_MODEL ?? "mistral-embed",
    maxPages: intEnv("MISTRAL_MAX_PAGES", 10),
    timeoutMs: intEnv("MISTRAL_TIMEOUT_MS", 300000),
    analysisModel: process.env.MISTRAL_ANALYSIS_MODEL ?? "mistral-small-latest",
    audioModel: process.env.MISTRAL_AUDIO_MODEL ?? "voxtral-mini-latest"
  }
} as const;
