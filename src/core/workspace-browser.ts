import { readdir, readFile, stat } from "node:fs/promises";
import path from "node:path";

export interface WorkspaceNode {
  name: string;
  relativePath: string;
  type: "file" | "directory";
  size?: number;
  children?: WorkspaceNode[];
}

function safeResolve(root: string, relativePath: string): string {
  const resolvedRoot = path.resolve(root);
  const resolved = path.resolve(root, relativePath || ".");
  if (resolved !== resolvedRoot && !resolved.startsWith(`${resolvedRoot}${path.sep}`)) {
    throw new Error("WORKSPACE_PATH_TRAVERSAL");
  }
  return resolved;
}

async function walk(root: string, current: string, depth: number): Promise<WorkspaceNode[]> {
  if (depth < 0) return [];
  const entries = await readdir(current, { withFileTypes: true });
  const nodes: WorkspaceNode[] = [];
  for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
    if (entry.name.startsWith(".")) continue;
    const absolute = path.join(current, entry.name);
    const relativePath = path.relative(root, absolute);
    if (entry.isDirectory()) {
      nodes.push({ name: entry.name, relativePath, type: "directory", children: await walk(root, absolute, depth - 1) });
    } else if (entry.isFile()) {
      const details = await stat(absolute);
      nodes.push({ name: entry.name, relativePath, type: "file", size: details.size });
    }
  }
  return nodes;
}

export async function workspaceTree(root: string, maxDepth = 6): Promise<WorkspaceNode[]> {
  return walk(path.resolve(root), path.resolve(root), maxDepth);
}

export async function readWorkspaceFile(root: string, relativePath: string, maxBytes = 2_000_000): Promise<{ content: string; size: number }> {
  const absolute = safeResolve(root, relativePath);
  const details = await stat(absolute);
  if (!details.isFile()) throw new Error("WORKSPACE_NOT_A_FILE");
  if (details.size > maxBytes) throw new Error("WORKSPACE_FILE_TOO_LARGE");
  return { content: await readFile(absolute, "utf8"), size: details.size };
}
