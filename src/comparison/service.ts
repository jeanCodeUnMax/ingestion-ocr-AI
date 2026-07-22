import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { config } from "../config.js";
import type { ComparisonArtifact } from "../types.js";
import { atomicWriteJson, atomicWriteText } from "../utils/files.js";

interface SynthesisShape {
  executiveSummary?: string;
  coreThemes?: string[];
  centralProblem?: string;
  realityVerdict?: string;
  operationalModel?: string;
  priorityActions?: string[];
  unresolvedQuestions?: string[];
}

interface SynthesisFileShape extends SynthesisShape {
  synthesis?: SynthesisShape;
}

function unwrapSynthesis(value: SynthesisFileShape): SynthesisShape {
  return value.synthesis && typeof value.synthesis === "object" ? value.synthesis : value;
}

function normalizeTheme(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, " ");
}

function displayTheme(value: string): string {
  return value.replace(/(^|\s)\p{L}/gu, (letter) => letter.toUpperCase());
}

export async function compareDocuments(documentIds: string[]): Promise<ComparisonArtifact> {
  const uniqueIds = [...new Set(documentIds.filter(Boolean))];
  if (uniqueIds.length < 2) throw new Error("COMPARISON_REQUIRES_TWO_DOCUMENTS");
  const syntheses = new Map<string, SynthesisShape>();
  for (const documentId of uniqueIds) {
    const filePath = path.join(config.workspaceRoot, documentId, "analysis", "synthesis.json");
    try {
      const raw = JSON.parse(await readFile(filePath, "utf8")) as SynthesisFileShape;
      syntheses.set(documentId, unwrapSynthesis(raw));
    } catch {
      throw new Error(`COMPARISON_ANALYSIS_MISSING:${documentId}`);
    }
  }

  const themeSets = new Map<string, Set<string>>();
  for (const [documentId, synthesis] of syntheses) {
    themeSets.set(documentId, new Set((synthesis.coreThemes ?? []).map(normalizeTheme).filter(Boolean)));
  }
  const allThemes = [...new Set([...themeSets.values()].flatMap((set) => [...set]))];
  const commonThemes = allThemes.filter((theme) => [...themeSets.values()].every((set) => set.has(theme))).map(displayTheme);
  const uniqueThemes: Record<string, string[]> = {};
  for (const [documentId, set] of themeSets) {
    uniqueThemes[documentId] = [...set].filter((theme) => [...themeSets.entries()].every(([otherId, other]) => otherId === documentId || !other.has(theme))).map(displayTheme);
  }

  const centralProblems = Object.fromEntries([...syntheses].map(([id, value]) => [id, value.centralProblem ?? "Non disponible"]));
  const realityVerdicts = Object.fromEntries([...syntheses].map(([id, value]) => [id, value.realityVerdict ?? "Non disponible"]));
  const operationalModels = Object.fromEntries([...syntheses].map(([id, value]) => [id, value.operationalModel ?? "Non disponible"]));
  const similarities = commonThemes.length
    ? commonThemes.map((theme) => `Thème commun : ${theme}`)
    : ["Aucun thème strictement commun n'a été détecté dans les synthèses."];
  const differences = uniqueIds.flatMap((id) => uniqueThemes[id]?.map((theme) => `${id} met spécifiquement l'accent sur ${theme}.`) ?? []);
  const recommendations = [
    "Vérifier les différences directement dans les chunks sources avant toute conclusion.",
    "Comparer les verdicts KENT lorsque les documents défendent des affirmations incompatibles.",
    "Produire un benchmark séparé si les documents décrivent des méthodes ou technologies concurrentes."
  ];

  const artifact: ComparisonArtifact = {
    schemaVersion: "1.0",
    comparisonId: `cmp_${randomUUID()}`,
    documentIds: uniqueIds,
    createdAt: new Date().toISOString(),
    commonThemes,
    uniqueThemes,
    centralProblems,
    realityVerdicts,
    operationalModels,
    similarities,
    differences,
    recommendations
  };
  await mkdir(config.comparisonsRoot, { recursive: true });
  await atomicWriteJson(path.join(config.comparisonsRoot, `${artifact.comparisonId}.json`), artifact);
  const markdown = [
    `# Comparaison ${artifact.comparisonId}`,
    "",
    `Documents : ${uniqueIds.join(", ")}`,
    "",
    "## Thèmes communs",
    "",
    ...(commonThemes.length ? commonThemes.map((item) => `- ${item}`) : ["- Aucun thème commun strict."]),
    "",
    "## Différences",
    "",
    ...(differences.length ? differences.map((item) => `- ${item}`) : ["- Aucune différence thématique explicite détectée."]),
    "",
    "## Problèmes centraux",
    "",
    ...Object.entries(centralProblems).map(([id, value]) => `- **${id}** : ${value}`),
    "",
    "## Verdicts de réalité",
    "",
    ...Object.entries(realityVerdicts).map(([id, value]) => `- **${id}** : ${value}`),
    "",
    "## Recommandations",
    "",
    ...recommendations.map((item) => `- ${item}`),
    ""
  ].join("\n");
  await atomicWriteText(path.join(config.comparisonsRoot, `${artifact.comparisonId}.md`), markdown);
  return artifact;
}

export async function readComparison(comparisonId: string): Promise<ComparisonArtifact | undefined> {
  try {
    return JSON.parse(await readFile(path.join(config.comparisonsRoot, `${comparisonId}.json`), "utf8")) as ComparisonArtifact;
  } catch {
    return undefined;
  }
}
