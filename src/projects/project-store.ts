import { randomUUID } from "node:crypto";
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import type { DeploymentMode, InputKind, PlatformIdentity, ProcessingRecipe, ProjectManifest, SourceOrigin } from "../types.js";
import { atomicWriteJson, atomicWriteText, ensureDir } from "../utils/files.js";

function iso(): string { return new Date().toISOString(); }

export class ProjectStore {
  constructor(private readonly root: string) {}

  async initialize(): Promise<void> { await ensureDir(this.root); }

  projectRoot(projectId: string): string { return path.join(this.root, projectId); }
  private manifestPath(projectId: string): string { return path.join(this.projectRoot(projectId), "project.json"); }

  async create(input: {
    name: string;
    description?: string;
    instruction?: string;
    identity: PlatformIdentity;
    deploymentMode: DeploymentMode;
    defaultRecipe: ProcessingRecipe;
  }): Promise<ProjectManifest> {
    const now = iso();
    const projectId = `prj_${randomUUID()}`;
    const project: ProjectManifest = {
      schemaVersion: "1.0",
      projectId,
      name: input.name.trim() || "Nouveau projet",
      description: input.description?.trim() ?? "",
      instruction: input.instruction?.trim() ?? "",
      deploymentMode: input.deploymentMode,
      ownership: { userId: input.identity.userId, tenantId: input.identity.tenantId },
      defaultRecipe: input.defaultRecipe,
      documents: [],
      createdAt: now,
      updatedAt: now
    };
    await Promise.all([
      ensureDir(this.projectRoot(projectId)),
      ensureDir(path.join(this.projectRoot(projectId), "chat")),
      ensureDir(path.join(this.projectRoot(projectId), "knowledge")),
      ensureDir(path.join(this.projectRoot(projectId), "exports"))
    ]);
    await this.save(project);
    return project;
  }

  async save(project: ProjectManifest): Promise<void> {
    project.updatedAt = iso();
    await atomicWriteJson(this.manifestPath(project.projectId), project);
    await this.rebuildIndex(project);
  }

  private async rebuildIndex(project: ProjectManifest): Promise<void> {
    const root = this.projectRoot(project.projectId);
    const completed = project.documents.filter((document) => document.status === "complete").length;
    const markdown = [
      `# Projet — ${project.name}`,
      "",
      project.description || "Workspace documentaire OCR AI System.",
      "",
      `- Projet ID : \`${project.projectId}\``,
      `- Documents : ${project.documents.length}`,
      `- Documents terminés : ${completed}`,
      `- Profil de traitement : ${project.defaultRecipe.profile}`,
      "",
      "## Instruction globale",
      "",
      project.instruction || "Aucune instruction globale.",
      "",
      "## Documents",
      "",
      ...project.documents.map((document) => `- \`${document.documentId}\` — ${document.filename} — ${document.inputKind} — ${document.status} — origine ${document.sourceOrigin}`),
      "",
      "## Recherche",
      "",
      "Le chat RAG interroge uniquement les documents rattachés à ce projet.",
      ""
    ].join("\n");
    await atomicWriteText(path.join(root, "index.md"), markdown);
    await atomicWriteJson(path.join(root, "knowledge", "project_map.json"), {
      schemaVersion: "1.0",
      projectId: project.projectId,
      name: project.name,
      instruction: project.instruction,
      defaultRecipe: project.defaultRecipe,
      documents: project.documents,
      counts: { total: project.documents.length, completed },
      updatedAt: project.updatedAt
    });
  }

  async get(projectId: string): Promise<ProjectManifest | undefined> {
    try { return JSON.parse(await readFile(this.manifestPath(projectId), "utf8")) as ProjectManifest; }
    catch (error) {
      if ((error as NodeJS.ErrnoException).code === "ENOENT") return undefined;
      throw error;
    }
  }

  async list(): Promise<ProjectManifest[]> {
    await this.initialize();
    const entries = await readdir(this.root, { withFileTypes: true });
    const projects: ProjectManifest[] = [];
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      const project = await this.get(entry.name);
      if (project) projects.push(project);
    }
    return projects.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  }

  async attachDocument(input: {
    projectId: string;
    documentId: string;
    filename: string;
    inputKind: InputKind;
    sourceOrigin: SourceOrigin;
    status?: ProjectManifest["documents"][number]["status"];
  }): Promise<ProjectManifest> {
    const project = await this.get(input.projectId);
    if (!project) throw new Error(`PROJECT_NOT_FOUND:${input.projectId}`);
    const existing = project.documents.find((item) => item.documentId === input.documentId);
    if (existing) {
      existing.status = input.status ?? existing.status;
    } else {
      project.documents.push({
        documentId: input.documentId,
        filename: input.filename,
        inputKind: input.inputKind,
        sourceOrigin: input.sourceOrigin,
        status: input.status ?? "queued",
        createdAt: iso()
      });
    }
    await this.save(project);
    return project;
  }

  async updateDocumentStatus(projectId: string, documentId: string, status: ProjectManifest["documents"][number]["status"]): Promise<void> {
    const project = await this.get(projectId);
    if (!project) return;
    const document = project.documents.find((item) => item.documentId === documentId);
    if (document) document.status = status;
    await this.save(project);
  }
}
