export type ProviderId = "none" | "llama-cpp" | "mistral";
export type EmbeddingProviderId = "hash" | "llama-cpp" | "mistral";
export type AnalysisProviderId = "rules" | "llama-cpp" | "mistral";
export type TranslationProviderId = "none" | "llama-cpp" | "mistral";
export type AudioProviderId = "none" | "mistral" | "whisper-cpp";
export type DeploymentMode = "personal" | "saas" | "enterprise";
export type InputKind = "pdf" | "word" | "excel" | "csv" | "json" | "markdown" | "text" | "image" | "svg" | "audio";
export type RecipeProfile = "quick" | "standard" | "deep" | "custom";
export type SourceOrigin = "upload" | "paste" | "url";
export type FeatureName =
  | "word"
  | "excel"
  | "csv"
  | "json"
  | "markdown"
  | "text"
  | "image"
  | "audio"
  | "translation"
  | "comparison"
  | "advancedWorkspace"
  | "auth"
  | "billing"
  | "multiTenant"
  | "projects"
  | "urlIngestion"
  | "chatRag"
  | "knowledgeEnrichment"
  | "svg";

export type DocumentStatus =
  | "created"
  | "queued"
  | "inventory"
  | "processing"
  | "analysis"
  | "embedding"
  | "complete"
  | "partial_failure"
  | "failed";

export type PageStatus =
  | "pending"
  | "native_success"
  | "vision_planned"
  | "vision_processing"
  | "vision_success"
  | "failed";

export type BatchStatus =
  | "planned"
  | "processing"
  | "retry_planned"
  | "completed"
  | "split"
  | "failed";

export type EmbeddingStatus = "pending" | "processing" | "complete" | "skipped" | "failed";
export type AnalysisStatus = "pending" | "processing" | "complete" | "skipped" | "partial_failure" | "failed";
export type JobStatus = "queued" | "processing" | "completed" | "failed" | "cancelled";
export type AnalysisKind = "semantic" | "maieutic" | "kent" | "pseudocode" | "synthesis";

export interface PdfInventoryPage {
  pageNumber: number;
  pageId: string;
  sourceHash: string;
  widthPt: number;
  heightPt: number;
  nativeTextChars: number;
  nativeTextPath: string;
  imageCount: number;
  imageAreaRatio: number;
  drawingCount: number;
  estimatedInputTokens: number;
  requiresVision: boolean;
  imagePath?: string;
  fallbackImagePath?: string;
}


export interface PdfInventory {
  schemaVersion: "1.0";
  totalPages: number;
  pages: PdfInventoryPage[];
}

export interface PageError {
  at: string;
  code: string;
  message: string;
  batchId?: string;
  attempt?: number;
}

export interface PageRecord extends PdfInventoryPage {
  status: PageStatus;
  batchId?: string;
  outputMarkdownPath?: string;
  provider?: ProviderId | "native";
  model?: string;
  confidence?: number;
  attempts: number;
  errors: PageError[];
}

export interface BatchRecord {
  batchId: string;
  parentBatchId?: string;
  childBatchIds: string[];
  pageIds: string[];
  estimatedInputTokens: number;
  estimatedImageBytes: number;
  status: BatchStatus;
  provider: ProviderId;
  model: string;
  attempt: number;
  useFallbackImages: boolean;
  createdAt: string;
  updatedAt: string;
  errors: PageError[];
}

export interface CoverageRecord {
  pagesDetected: number;
  pagesSuccessful: number;
  pagesFailed: number;
  pagesPending: number;
  visionPagesExpected: number;
  visionPagesAssignedToLeafBatches: number;
  missingPageIds: string[];
  duplicateLeafAssignments: string[];
  isComplete: boolean;
}

export interface EmbeddingRecord {
  provider: EmbeddingProviderId;
  model: string;
  status: EmbeddingStatus;
  chunksExpected: number;
  chunksEmbedded: number;
  transcriptionChunks?: number;
  analysisChunks?: number;
  dimension?: number;
  vectorStore: string;
  indexedAt?: string;
  errors: PageError[];
}


export type TranslationStatus = "skipped" | "pending" | "processing" | "complete" | "failed";

export interface TranslationRecord {
  provider: TranslationProviderId;
  model: string;
  targetLanguage?: string;
  status: TranslationStatus;
  segmentsExpected: number;
  segmentsCompleted: number;
  artifactPath?: string;
  translatedAt?: string;
  errors: PageError[];
}

export interface PlatformIdentity {
  userId: string;
  tenantId: string;
  email?: string;
  roles: string[];
  anonymous: boolean;
}

export interface FeatureFlags {
  word: boolean;
  excel: boolean;
  csv: boolean;
  json: boolean;
  markdown: boolean;
  text: boolean;
  image: boolean;
  audio: boolean;
  translation: boolean;
  comparison: boolean;
  advancedWorkspace: boolean;
  auth: boolean;
  billing: boolean;
  multiTenant: boolean;
  projects: boolean;
  urlIngestion: boolean;
  chatRag: boolean;
  knowledgeEnrichment: boolean;
  svg: boolean;
}


export interface ProcessingRecipe {
  profile: RecipeProfile;
  semanticAnalysis: boolean;
  maieuticAnalysis: boolean;
  kentRealityCheck: boolean;
  pseudocode: boolean;
  synthesis: boolean;
  shrink: boolean;
  atomicFacts: boolean;
  tagsAndTaxonomy: boolean;
  embeddings: boolean;
  visualDescriptions: boolean;
  translation: boolean;
}

export interface KnowledgeRecord {
  status: "pending" | "processing" | "complete" | "skipped" | "failed";
  atomicFacts: number;
  shrunkChunks: number;
  tags: number;
  artifacts: {
    atomicFactsJsonl?: string;
    shrinkJsonl?: string;
    shrinkMarkdown?: string;
    tagsJson?: string;
    taxonomyJson?: string;
    knowledgeMapJson?: string;
    indexMarkdown?: string;
  };
  indexedChunks: number;
  errors: PageError[];
}

export interface ProjectDocumentReference {
  documentId: string;
  filename: string;
  inputKind: InputKind;
  sourceOrigin: SourceOrigin;
  status: DocumentStatus;
  createdAt: string;
}

export interface ProjectManifest {
  schemaVersion: "1.0";
  projectId: string;
  name: string;
  description: string;
  instruction: string;
  deploymentMode: DeploymentMode;
  ownership: { userId: string; tenantId: string };
  defaultRecipe: ProcessingRecipe;
  documents: ProjectDocumentReference[];
  createdAt: string;
  updatedAt: string;
}

export interface ChatCitation {
  chunkId: string;
  documentId: string;
  pageStart: number;
  pageEnd: number;
  contentType: string;
  quote: string;
  score: number;
}

export interface ChatAnswer {
  conversationId: string;
  messageId: string;
  projectId: string;
  question: string;
  answer: string;
  citations: ChatCitation[];
  createdAt: string;
  provider: AnalysisProviderId;
  model: string;
}

export interface ComparisonArtifact {
  schemaVersion: "1.0";
  comparisonId: string;
  documentIds: string[];
  createdAt: string;
  commonThemes: string[];
  uniqueThemes: Record<string, string[]>;
  centralProblems: Record<string, string>;
  realityVerdicts: Record<string, string>;
  operationalModels: Record<string, string>;
  similarities: string[];
  differences: string[];
  recommendations: string[];
}

export interface AnalysisArtifactPaths {
  semanticJson?: string;
  semanticMarkdown?: string;
  maieuticJson?: string;
  maieuticMarkdown?: string;
  kentJson?: string;
  kentMarkdown?: string;
  pseudocodeJson?: string;
  pseudocodeMarkdown?: string;
  synthesisJson?: string;
  synthesisMarkdown?: string;
  segmentDirectory?: string;
}

export interface AnalysisRecord {
  provider: AnalysisProviderId;
  model: string;
  status: AnalysisStatus;
  segmentsExpected: number;
  segmentsCompleted: number;
  sourceChunks: number;
  artifacts: AnalysisArtifactPaths;
  indexedChunks: number;
  analyzedAt?: string;
  errors: PageError[];
}

export interface DocumentManifest {
  schemaVersion: "6.0";
  documentId: string;
  projectId?: string;
  sourceOrigin: SourceOrigin;
  sourceUrl?: string;
  recipe: ProcessingRecipe;
  originalFilename: string;
  inputKind: InputKind;
  mimeType: string;
  originalSourceRelativePath: string;
  sourceRelativePath: string;
  deploymentMode: DeploymentMode;
  ownership: { userId: string; tenantId: string; };
  instruction: string;
  status: DocumentStatus;
  sourceSha256: string;
  provider: ProviderId;
  embeddingProvider: EmbeddingProviderId;
  analysisProvider: AnalysisProviderId;
  translationProvider: TranslationProviderId;
  targetLanguage?: string;
  createdAt: string;
  updatedAt: string;
  totalPages: number;
  pages: PageRecord[];
  batches: BatchRecord[];
  coverage: CoverageRecord;
  analysis: AnalysisRecord;
  translation: TranslationRecord;
  embedding: EmbeddingRecord;
  knowledge: KnowledgeRecord;
}

export interface ProviderCapabilities {
  provider: ProviderId;
  model: string;
  maxPagesPerBatch: number;
  maxContextTokens?: number;
  reservedOutputTokens: number;
  safetyRatio: number;
  maxPayloadBytes?: number;
  supportsMultipleImages: boolean;
  usesOriginalPdf: boolean;
}

export interface OcrPageResult {
  pageId: string;
  markdown: string;
  visualDescription: string;
  confidence?: number;
  raw?: unknown;
}

export interface OcrBatchRequest {
  documentId: string;
  instruction: string;
  sourcePdfPath: string;
  pages: PageRecord[];
  useFallbackImages: boolean;
}

export interface OcrBatchResult {
  provider: ProviderId;
  model: string;
  pages: OcrPageResult[];
  raw?: unknown;
}

export interface EmbeddingProviderCapabilities {
  provider: EmbeddingProviderId;
  model: string;
  maxBatchSize: number;
  dimension?: number;
}

export type ChunkContentType =
  | "page_transcription"
  | "semantic_chunk"
  | "semantic_analysis"
  | "maieutic_analysis"
  | "kent_reality_check"
  | "pseudocode"
  | "analysis_synthesis"
  | "atomic_fact"
  | "shrunk_chunk"
  | "tag_taxonomy"
  | "document_index";

export interface EmbeddingChunk {
  chunkId: string;
  documentId: string;
  pageStart: number;
  pageEnd: number;
  contentType: ChunkContentType;
  heading?: string;
  text: string;
  sourceHash: string;
  sourceChunkIds?: string[];
}

export interface StoredVectorChunk extends EmbeddingChunk {
  embeddingModel: string;
  dimension: number;
  embedding: number[];
  createdAt: string;
}

export interface VectorSearchResult {
  chunkId: string;
  documentId: string;
  pageStart: number;
  pageEnd: number;
  contentType: string;
  heading?: string;
  text: string;
  score: number;
}

export interface SourceReference {
  sourceChunkIds: string[];
  pageStart: number;
  pageEnd: number;
}

export interface AnalysisSegment {
  segmentId: string;
  chunkIds: string[];
  pageStart: number;
  pageEnd: number;
  text: string;
  estimatedTokens: number;
}

export interface SemanticAnalysisResult {
  segmentId: string;
  source: SourceReference;
  title: string;
  summary: string;
  themes: Array<{ name: string; explanation: string; sourceChunkIds: string[] }>;
  concepts: Array<{ name: string; definition: string; sourceChunkIds: string[] }>;
  entities: Array<{ name: string; type: string; role: string; sourceChunkIds: string[] }>;
  claims: Array<{ statement: string; confidence: "explicit" | "inferred"; sourceChunkIds: string[] }>;
  relations: Array<{ from: string; relation: string; to: string; sourceChunkIds: string[] }>;
  keyFacts: Array<{ fact: string; sourceChunkIds: string[] }>;
  uncertainties: Array<{ point: string; reason: string; sourceChunkIds: string[] }>;
}

export interface MaieuticAnalysisResult {
  segmentId: string;
  source: SourceReference;
  centralProblem: string;
  intendedPurpose: string;
  essentialMeaning: string;
  presuppositions: Array<{ statement: string; sourceChunkIds: string[] }>;
  implicitQuestions: Array<{ question: string; whyItMatters: string; sourceChunkIds: string[] }>;
  ambiguities: Array<{ point: string; clarificationNeeded: string; sourceChunkIds: string[] }>;
  tensions: Array<{ elementA: string; elementB: string; explanation: string; sourceChunkIds: string[] }>;
  causes: Array<{ cause: string; effect: string; sourceChunkIds: string[] }>;
  consequences: Array<{ consequence: string; horizon: "short" | "medium" | "long"; sourceChunkIds: string[] }>;
  questionsToAsk: Array<{ question: string; expectedValue: string; sourceChunkIds: string[] }>;
}

export interface KentQuestionResult {
  id: "claim" | "tenants" | "aboutissants" | "interests" | "evidence" | "reality_slap";
  question: string;
  answer: string;
  findings: Array<{ statement: string; classification: string; sourceChunkIds: string[] }>;
}

export interface KentAnalysisResult {
  segmentId: string;
  source: SourceReference;
  questions: [KentQuestionResult, KentQuestionResult, KentQuestionResult, KentQuestionResult, KentQuestionResult, KentQuestionResult];
  verdict: {
    label: "credible" | "plausible" | "partially_supported" | "fragile" | "unsupported";
    explanation: string;
    confidence: number;
    sourceChunkIds: string[];
  };
  minimalRealityTest: {
    hypothesis: string;
    protocol: string[];
    successCriteria: string[];
    failureCriteria: string[];
    sourceChunkIds: string[];
  };
}

export interface PseudocodeAnalysisResult {
  segmentId: string;
  source: SourceReference;
  name: string;
  objective: string;
  inputs: string[];
  outputs: string[];
  preconditions: string[];
  invariants: string[];
  steps: Array<{
    order: number;
    action: string;
    condition?: string;
    onFailure?: string;
    sourceChunkIds: string[];
  }>;
  exceptions: Array<{ condition: string; handling: string; sourceChunkIds: string[] }>;
  acceptanceTests: Array<{ given: string; when: string; then: string; sourceChunkIds: string[] }>;
  pseudocode: string;
}

export interface AnalysisBundle {
  schemaVersion: "1.0";
  documentId: string;
  provider: AnalysisProviderId;
  model: string;
  generatedAt: string;
  sourceChunkIds: string[];
  enabled?: { semantic: boolean; maieutic: boolean; kent: boolean; pseudocode: boolean; synthesis: boolean };
  semantic: SemanticAnalysisResult[];
  maieutic: MaieuticAnalysisResult[];
  kent: KentAnalysisResult[];
  pseudocode: PseudocodeAnalysisResult[];
  synthesis: {
    executiveSummary: string;
    coreThemes: string[];
    centralProblem: string;
    realityVerdict: string;
    operationalModel: string;
    priorityActions: string[];
    unresolvedQuestions: string[];
    sourceChunkIds: string[];
  };
}

export interface AnalysisProviderCapabilities {
  provider: AnalysisProviderId;
  model: string;
  maxInputChars: number;
  maxSegmentsPerSynthesis: number;
  supportsStructuredJson: boolean;
}

export interface AnalyzeSegmentRequest {
  documentId: string;
  instruction: string;
  segment: AnalysisSegment;
}

export interface AnalyzeSegmentResult {
  semantic: SemanticAnalysisResult;
  maieutic: MaieuticAnalysisResult;
  kent: KentAnalysisResult;
  pseudocode: PseudocodeAnalysisResult;
  raw?: unknown;
}

export interface AnalysisProvider {
  readonly capabilities: AnalysisProviderCapabilities;
  analyzeSegment(request: AnalyzeSegmentRequest): Promise<AnalyzeSegmentResult>;
  synthesize(input: {
    documentId: string;
    instruction: string;
    results: AnalyzeSegmentResult[];
    sourceChunkIds: string[];
  }): Promise<AnalysisBundle["synthesis"]>;
  health(): Promise<{ ok: boolean; detail: string }>;
}

export interface ProcessDocumentJobPayload {
  stagedSourcePath: string;
  stagedPdfPath?: string;
  canonicalMarkdownPath?: string;
  filename: string;
  mimeType: string;
  inputKind: InputKind;
  projectId?: string;
  sourceOrigin: SourceOrigin;
  sourceUrl?: string;
  recipe: ProcessingRecipe;
  instruction: string;
  providerId: ProviderId;
  embeddingProviderId: EmbeddingProviderId;
  analysisProviderId: AnalysisProviderId;
  translationProviderId: TranslationProviderId;
  targetLanguage?: string;
  identity: PlatformIdentity;
}

export interface PersistentJob {
  schemaVersion: "1.2";
  jobId: string;
  documentId: string;
  type: "process_document";
  status: JobStatus;
  payload: ProcessDocumentJobPayload;
  attempts: number;
  maxAttempts: number;
  createdAt: string;
  updatedAt: string;
  startedAt?: string;
  finishedAt?: string;
  progress: {
    stage: string;
    percent: number;
    message: string;
  };
  lastError?: {
    at: string;
    message: string;
  };
}
