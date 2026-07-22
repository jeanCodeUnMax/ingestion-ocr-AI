import path from "node:path";
import { ensureDir } from "../utils/files.js";

export interface WorkspacePaths {
  root: string;
  request: string;
  source: string;
  inventory: string;
  pages: string;
  batches: string;
  transcription: string;
  native: string;
  analysis: string;
  analysisSegments: string;
  semanticAnalysis: string;
  conceptualAnalysis: string;
  kentAnalysis: string;
  pseudocode: string;
  translation: string;
  comparisons: string;
  perspectives: string;
  shrink: string;
  tags: string;
  embeddings: string;
  exports: string;
  logs: string;
  manifest: string;
}

export async function createWorkspace(root: string, documentId: string): Promise<WorkspacePaths> {
  const workspaceRoot = path.join(root, documentId);
  const analysisRoot = path.join(workspaceRoot, "analysis");
  const paths: WorkspacePaths = {
    root: workspaceRoot,
    request: path.join(workspaceRoot, "request"),
    source: path.join(workspaceRoot, "source"),
    inventory: path.join(workspaceRoot, "inventory"),
    pages: path.join(workspaceRoot, "pages"),
    batches: path.join(workspaceRoot, "batches"),
    transcription: path.join(workspaceRoot, "transcription"),
    native: path.join(workspaceRoot, "transcription", "native"),
    analysis: analysisRoot,
    analysisSegments: path.join(analysisRoot, "segments"),
    semanticAnalysis: path.join(analysisRoot, "semantic"),
    conceptualAnalysis: path.join(analysisRoot, "maieutic"),
    kentAnalysis: path.join(analysisRoot, "kent_glove"),
    pseudocode: path.join(analysisRoot, "pseudocode"),
    translation: path.join(workspaceRoot, "translation"),
    comparisons: path.join(workspaceRoot, "comparisons"),
    perspectives: path.join(workspaceRoot, "perspectives"),
    shrink: path.join(workspaceRoot, "shrink"),
    tags: path.join(workspaceRoot, "tags"),
    embeddings: path.join(workspaceRoot, "embeddings"),
    exports: path.join(workspaceRoot, "exports"),
    logs: path.join(workspaceRoot, "logs"),
    manifest: path.join(workspaceRoot, "manifest.json")
  };
  await Promise.all(Object.values(paths).filter((p) => !path.extname(p)).map(ensureDir));
  return paths;
}
