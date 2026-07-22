import type {
  AnalysisBundle,
  KentAnalysisResult,
  MaieuticAnalysisResult,
  PseudocodeAnalysisResult,
  SemanticAnalysisResult
} from "../types.js";

function sources(ids: string[]): string {
  return ids.length ? ids.map((id) => `\`${id}\``).join(", ") : "Aucune source";
}

export function semanticMarkdown(results: SemanticAnalysisResult[]): string {
  const out = ["# Analyse sémantique", ""];
  for (const result of results) {
    out.push(`## ${result.title}`, "", result.summary, "", `**Sources :** ${sources(result.source.sourceChunkIds)}`, "");
    if (result.themes.length) {
      out.push("### Thèmes", "", ...result.themes.map((item) => `- **${item.name}** — ${item.explanation}  \n  Sources : ${sources(item.sourceChunkIds)}`), "");
    }
    if (result.concepts.length) {
      out.push("### Concepts", "", ...result.concepts.map((item) => `- **${item.name}** — ${item.definition}  \n  Sources : ${sources(item.sourceChunkIds)}`), "");
    }
    if (result.claims.length) {
      out.push("### Affirmations", "", ...result.claims.map((item) => `- [${item.confidence}] ${item.statement}  \n  Sources : ${sources(item.sourceChunkIds)}`), "");
    }
    if (result.keyFacts.length) {
      out.push("### Faits clés", "", ...result.keyFacts.map((item) => `- ${item.fact}  \n  Sources : ${sources(item.sourceChunkIds)}`), "");
    }
    if (result.uncertainties.length) {
      out.push("### Incertitudes", "", ...result.uncertainties.map((item) => `- ${item.point} — ${item.reason}  \n  Sources : ${sources(item.sourceChunkIds)}`), "");
    }
  }
  return `${out.join("\n").trim()}\n`;
}

export function maieuticMarkdown(results: MaieuticAnalysisResult[]): string {
  const out = ["# Analyse maïeutique", ""];
  for (const result of results) {
    out.push(
      `## ${result.segmentId} — pages ${result.source.pageStart}-${result.source.pageEnd}`,
      "",
      `**Problème central :** ${result.centralProblem}`,
      "",
      `**Finalité recherchée :** ${result.intendedPurpose}`,
      "",
      `**Essence :** ${result.essentialMeaning}`,
      "",
      `**Sources :** ${sources(result.source.sourceChunkIds)}`,
      ""
    );
    out.push("### Présupposés", "", ...result.presuppositions.map((item) => `- ${item.statement}  \n  Sources : ${sources(item.sourceChunkIds)}`), "");
    out.push("### Questions implicites", "", ...result.implicitQuestions.map((item) => `- **${item.question}** — ${item.whyItMatters}  \n  Sources : ${sources(item.sourceChunkIds)}`), "");
    if (result.ambiguities.length) out.push("### Ambiguïtés", "", ...result.ambiguities.map((item) => `- ${item.point} — À préciser : ${item.clarificationNeeded}  \n  Sources : ${sources(item.sourceChunkIds)}`), "");
    if (result.tensions.length) out.push("### Tensions", "", ...result.tensions.map((item) => `- **${item.elementA}** ↔ **${item.elementB}** — ${item.explanation}  \n  Sources : ${sources(item.sourceChunkIds)}`), "");
    if (result.causes.length) out.push("### Causes et effets", "", ...result.causes.map((item) => `- ${item.cause} → ${item.effect}  \n  Sources : ${sources(item.sourceChunkIds)}`), "");
    if (result.consequences.length) out.push("### Conséquences", "", ...result.consequences.map((item) => `- [${item.horizon}] ${item.consequence}  \n  Sources : ${sources(item.sourceChunkIds)}`), "");
    out.push("### Questions essentielles", "", ...result.questionsToAsk.map((item) => `- **${item.question}** — ${item.expectedValue}  \n  Sources : ${sources(item.sourceChunkIds)}`), "");
  }
  return `${out.join("\n").trim()}\n`;
}

export function kentMarkdown(results: KentAnalysisResult[]): string {
  const out = [
    "# Gant de KENT — Gifle de la réalité",
    "",
    "> Grille interne OCR AI System en six questions. Elle sépare les faits, hypothèses, intérêts, conséquences et tests du réel.",
    ""
  ];
  for (const result of results) {
    out.push(`## ${result.segmentId} — pages ${result.source.pageStart}-${result.source.pageEnd}`, "", `**Sources :** ${sources(result.source.sourceChunkIds)}`, "");
    for (const [index, question] of result.questions.entries()) {
      out.push(`### ${index + 1}. ${question.question}`, "", question.answer, "");
      if (question.findings.length) out.push(...question.findings.map((finding) => `- **${finding.classification}** — ${finding.statement}  \n  Sources : ${sources(finding.sourceChunkIds)}`), "");
    }
    out.push(
      "### Verdict",
      "",
      `**${result.verdict.label}** — ${result.verdict.explanation}`,
      "",
      `Confiance : ${(result.verdict.confidence * 100).toFixed(0)} %`,
      "",
      `Sources : ${sources(result.verdict.sourceChunkIds)}`,
      "",
      "### Test minimal de réalité",
      "",
      `**Hypothèse :** ${result.minimalRealityTest.hypothesis}`,
      "",
      "**Protocole :**",
      ...result.minimalRealityTest.protocol.map((step, index) => `${index + 1}. ${step}`),
      "",
      "**Critères de succès :**",
      ...result.minimalRealityTest.successCriteria.map((item) => `- ${item}`),
      "",
      "**Critères d'échec :**",
      ...result.minimalRealityTest.failureCriteria.map((item) => `- ${item}`),
      ""
    );
  }
  return `${out.join("\n").trim()}\n`;
}

export function pseudocodeMarkdown(results: PseudocodeAnalysisResult[]): string {
  const out = ["# Formalisation en pseudocode", ""];
  for (const result of results) {
    out.push(
      `## ${result.name}`,
      "",
      `**Objectif :** ${result.objective}`,
      "",
      `**Sources :** ${sources(result.source.sourceChunkIds)}`,
      "",
      "### Entrées",
      "",
      ...result.inputs.map((item) => `- ${item}`),
      "",
      "### Sorties",
      "",
      ...result.outputs.map((item) => `- ${item}`),
      "",
      "### Préconditions",
      "",
      ...result.preconditions.map((item) => `- ${item}`),
      "",
      "### Invariants",
      "",
      ...result.invariants.map((item) => `- ${item}`),
      "",
      "### Étapes",
      "",
      ...result.steps.map((step) => `${step.order}. ${step.action}${step.condition ? `\n   - Condition : ${step.condition}` : ""}${step.onFailure ? `\n   - En cas d'échec : ${step.onFailure}` : ""}\n   - Sources : ${sources(step.sourceChunkIds)}`),
      "",
      "### Pseudocode",
      "",
      "```text",
      result.pseudocode,
      "```",
      "",
      "### Tests d'acceptation",
      "",
      ...result.acceptanceTests.map((test) => `- **Étant donné** ${test.given}; **quand** ${test.when}; **alors** ${test.then}.  \n  Sources : ${sources(test.sourceChunkIds)}`),
      ""
    );
  }
  return `${out.join("\n").trim()}\n`;
}

export function synthesisMarkdown(bundle: AnalysisBundle): string {
  const value = bundle.synthesis;
  return [
    "# Synthèse documentaire à haute valeur ajoutée",
    "",
    `**Document :** ${bundle.documentId}`,
    "",
    `**Fournisseur :** ${bundle.provider} / ${bundle.model}`,
    "",
    "## Résumé exécutif",
    "",
    value.executiveSummary,
    "",
    "## Thèmes centraux",
    "",
    ...value.coreThemes.map((item) => `- ${item}`),
    "",
    "## Problème central",
    "",
    value.centralProblem,
    "",
    "## Gifle de la réalité",
    "",
    value.realityVerdict,
    "",
    "## Modèle opérationnel",
    "",
    "```text",
    value.operationalModel,
    "```",
    "",
    "## Actions prioritaires",
    "",
    ...value.priorityActions.map((item, index) => `${index + 1}. ${item}`),
    "",
    "## Questions non résolues",
    "",
    ...value.unresolvedQuestions.map((item) => `- ${item}`),
    "",
    `**Sources :** ${sources(value.sourceChunkIds)}`,
    ""
  ].join("\n");
}
