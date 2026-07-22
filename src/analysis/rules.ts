import { createHash } from "node:crypto";
import type {
  AnalysisBundle,
  AnalysisProvider,
  AnalyzeSegmentRequest,
  AnalyzeSegmentResult,
  KentAnalysisResult,
  KentQuestionResult,
  MaieuticAnalysisResult,
  PseudocodeAnalysisResult,
  SemanticAnalysisResult
} from "../types.js";

const STOP_WORDS = new Set([
  "alors", "avec", "avoir", "cette", "comme", "dans", "donc", "elle", "elles", "entre", "faire", "leurs",
  "mais", "meme", "même", "nous", "pour", "plus", "sans", "sont", "sous", "tout", "tous", "toute", "toutes",
  "une", "des", "les", "que", "qui", "quoi", "dont", "cela", "ceci", "être", "est", "par", "sur", "aux", "ses",
  "son", "notre", "votre", "leur", "ainsi", "afin", "peut", "peuvent", "doit", "doivent", "document", "page"
]);

function normalizeWord(value: string): string {
  return value.toLocaleLowerCase("fr-FR").replace(/[^\p{L}\p{N}-]/gu, "");
}

function plainText(text: string): string {
  return text
    .replace(/\[\[SOURCE_CHUNK[^\]]+\]\]/g, " ")
    .replace(/```[^]*?```/g, " ")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/Description visuelle\s+Aucun élément visuel substantiel détecté[^.]*\.?/gi, " ")
    .replace(/<!--[^]*?-->/g, " ")
    .replace(/\r/g, "");
}

function sentences(text: string): string[] {
  return plainText(text)
    .split(/(?<=[.!?])\s+|\n+/)
    .map((item) => item.replace(/^[-*]\s*/, "").trim())
    .filter((item) => item.length >= 12)
    .slice(0, 120);
}

function sourceIds(request: AnalyzeSegmentRequest): string[] {
  return [...request.segment.chunkIds];
}

function topKeywords(text: string, limit = 8): string[] {
  const counts = new Map<string, number>();
  for (const raw of plainText(text).match(/[\p{L}\p{N}][\p{L}\p{N}-]{3,}/gu) ?? []) {
    const word = normalizeWord(raw);
    if (!word || STOP_WORDS.has(word) || /^\d+$/.test(word)) continue;
    counts.set(word, (counts.get(word) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, limit)
    .map(([word]) => word);
}

function explicitClaims(items: string[]): string[] {
  const indicators = /\b(doit|permet|garantit|est|sont|vise|objectif|nécessite|entraîne|provoque|réduit|augmente|consiste)\b/i;
  const selected = items.filter((item) => indicators.test(item)).slice(0, 6);
  return selected.length ? selected : items.slice(0, 4);
}

function capitalizedEntities(text: string): string[] {
  const matches = text.match(/\b[A-ZÀ-ÖØ-Þ][\p{L}\d-]+(?:\s+[A-ZÀ-ÖØ-Þ][\p{L}\d-]+){0,3}\b/gu) ?? [];
  return [...new Set(matches.filter((value) => value.length > 2 && !value.startsWith("SOURCE_CHUNK")))].slice(0, 8);
}

function summaryFrom(items: string[], fallback: string): string {
  return items.slice(0, 3).join(" ") || fallback;
}

function firstOr(items: string[], fallback: string): string {
  return items.find(Boolean) ?? fallback;
}

function semantic(request: AnalyzeSegmentRequest): SemanticAnalysisResult {
  const ids = sourceIds(request);
  const items = sentences(request.segment.text);
  const keywords = topKeywords(request.segment.text);
  const claims = explicitClaims(items);
  const entities = capitalizedEntities(request.segment.text);
  return {
    segmentId: request.segment.segmentId,
    source: { sourceChunkIds: ids, pageStart: request.segment.pageStart, pageEnd: request.segment.pageEnd },
    title: keywords.slice(0, 3).join(" · ") || `Pages ${request.segment.pageStart}-${request.segment.pageEnd}`,
    summary: summaryFrom(items, "Le segment ne contient pas assez de texte pour une synthèse fiable."),
    themes: keywords.slice(0, 6).map((name) => ({
      name,
      explanation: `Thème récurrent détecté dans le vocabulaire du segment : ${name}.`,
      sourceChunkIds: ids
    })),
    concepts: keywords.slice(0, 6).map((name) => ({
      name,
      definition: `Concept à définir ou préciser à partir du contexte documentaire : ${name}.`,
      sourceChunkIds: ids
    })),
    entities: entities.map((name) => ({ name, type: "entité nommée", role: "Mentionnée dans le segment.", sourceChunkIds: ids })),
    claims: claims.map((statement) => ({ statement, confidence: "explicit", sourceChunkIds: ids })),
    relations: keywords.slice(1, 5).map((keyword, index) => ({
      from: keywords[0] ?? "sujet central",
      relation: index % 2 === 0 ? "est lié à" : "influence",
      to: keyword,
      sourceChunkIds: ids
    })),
    keyFacts: items.filter((item) => /\b(selon|mesuré|mesure|constaté|données|étude|résultat)\b/i.test(item) || /\b\d+(?:[.,]\d+)?\s*(?:%|euros?|heures?|jours?|mm|cm|kg|fois)\b/i.test(item)).slice(0, 6).map((fact) => ({ fact, sourceChunkIds: ids })),
    uncertainties: items.filter((item) => /\b(peut|pourrait|environ|probable|semble|potentiellement)\b/i.test(item)).slice(0, 5).map((point) => ({
      point,
      reason: "Formulation modale ou approximative détectée.",
      sourceChunkIds: ids
    }))
  };
}

function maieutic(request: AnalyzeSegmentRequest, sem: SemanticAnalysisResult): MaieuticAnalysisResult {
  const ids = sourceIds(request);
  const claims = sem.claims.map((claim) => claim.statement);
  const central = firstOr(claims, sem.summary);
  const causeSentences = sentences(request.segment.text).filter((item) => /\b(car|parce que|cause|origine|raison|afin de|pour)\b/i.test(item));
  const consequenceSentences = sentences(request.segment.text).filter((item) => /\b(donc|entraîne|conséquence|résultat|permet|aboutit|provoque)\b/i.test(item));
  return {
    segmentId: request.segment.segmentId,
    source: sem.source,
    centralProblem: `Quel problème concret cherche à résoudre l'affirmation suivante : « ${central.slice(0, 280)} » ?`,
    intendedPurpose: request.instruction.trim() || "Comprendre, structurer et rendre le contenu exploitable.",
    essentialMeaning: sem.summary,
    presuppositions: [
      { statement: "Les définitions et le contexte employés sont suffisamment partagés par le lecteur.", sourceChunkIds: ids },
      { statement: "Les relations causales présentées ou suggérées sont valides hors du document.", sourceChunkIds: ids }
    ],
    implicitQuestions: [
      { question: "Pourquoi cette proposition est-elle nécessaire maintenant ?", whyItMatters: "Elle révèle l'urgence et le problème initial.", sourceChunkIds: ids },
      { question: "Qu'est-ce qui changerait si cette proposition était fausse ?", whyItMatters: "Elle teste la dépendance du raisonnement à sa thèse centrale.", sourceChunkIds: ids },
      { question: "Quelles conditions doivent être vraies pour que cela fonctionne ?", whyItMatters: "Elle explicite les prérequis cachés.", sourceChunkIds: ids }
    ],
    ambiguities: sem.uncertainties.map((item) => ({
      point: item.point,
      clarificationNeeded: "Préciser la mesure, le périmètre, la source et les conditions d'application.",
      sourceChunkIds: item.sourceChunkIds
    })),
    tensions: claims.length >= 2 ? [{
      elementA: claims[0] ?? "première affirmation",
      elementB: claims[1] ?? "seconde affirmation",
      explanation: "Vérifier si les deux affirmations restent compatibles dans les mêmes conditions.",
      sourceChunkIds: ids
    }] : [],
    causes: causeSentences.slice(0, 5).map((cause) => ({ cause, effect: "Effet à confirmer par une preuve ou une mesure.", sourceChunkIds: ids })),
    consequences: consequenceSentences.slice(0, 6).map((consequence, index) => ({
      consequence,
      horizon: index < 2 ? "short" : index < 4 ? "medium" : "long",
      sourceChunkIds: ids
    })),
    questionsToAsk: [
      { question: "Quelle preuve indépendante confirmerait la thèse centrale ?", expectedValue: "Distinguer croyance, hypothèse et fait.", sourceChunkIds: ids },
      { question: "Quel contre-exemple invaliderait la proposition ?", expectedValue: "Rendre le raisonnement falsifiable.", sourceChunkIds: ids },
      { question: "Quels acteurs, coûts et contraintes sont absents du texte ?", expectedValue: "Faire apparaître les angles morts.", sourceChunkIds: ids }
    ]
  };
}

function kentQuestion(
  id: KentQuestionResult["id"],
  question: string,
  answer: string,
  statements: string[],
  classification: string,
  ids: string[]
): KentQuestionResult {
  return {
    id,
    question,
    answer,
    findings: (statements.length ? statements : [answer]).slice(0, 6).map((statement) => ({ statement, classification, sourceChunkIds: ids }))
  };
}

function kent(request: AnalyzeSegmentRequest, sem: SemanticAnalysisResult, mai: MaieuticAnalysisResult): KentAnalysisResult {
  const ids = sourceIds(request);
  const claims = sem.claims.map((item) => item.statement);
  const facts = sem.keyFacts.map((item) => item.fact);
  const uncertaintyCount = sem.uncertainties.length + mai.ambiguities.length;
  const verdictLabel: KentAnalysisResult["verdict"]["label"] = facts.length >= 3 && uncertaintyCount === 0
    ? "credible"
    : facts.length >= 2
      ? "partially_supported"
      : claims.length > 0
        ? "plausible"
        : "fragile";
  const claim = firstOr(claims, sem.summary);
  const questions: KentAnalysisResult["questions"] = [
    kentQuestion("claim", "Qu'est-ce qui est réellement affirmé ?", claim, claims, "affirmation", ids),
    kentQuestion("tenants", "D'où cela vient-il : causes, prérequis et hypothèses ?", mai.centralProblem, [...mai.presuppositions.map((x) => x.statement), ...mai.causes.map((x) => `${x.cause} → ${x.effect}`)], "tenant", ids),
    kentQuestion("aboutissants", "Où cela mène-t-il : effets directs, indirects et limites ?", firstOr(mai.consequences.map((x) => x.consequence), "Les conséquences ne sont pas suffisamment explicitées."), mai.consequences.map((x) => x.consequence), "aboutissant", ids),
    kentQuestion("interests", "À qui cela profite-t-il, qui paie et qui porte le risque ?", "Le segment ne documente pas toujours les bénéficiaires, payeurs et porteurs de risques : cette cartographie doit être complétée.", [
      "Identifier le bénéficiaire direct de la proposition.",
      "Identifier celui qui finance, exécute ou supporte l'échec.",
      "Identifier celui qui contrôle les données, les ressources ou la décision."
    ], "intérêt_à_vérifier", ids),
    kentQuestion("evidence", "Quelles preuves résistent au réel et quels contre-exemples manquent ?", facts.length ? `${facts.length} élément(s) factuel(s) ont été repérés, mais leur indépendance et leur qualité restent à vérifier.` : "Aucune preuve suffisamment explicite n'a été isolée automatiquement.", [...facts, ...sem.uncertainties.map((x) => x.point)], facts.length ? "preuve_à_auditer" : "preuve_manquante", ids),
    kentQuestion("reality_slap", "Quelle est la gifle de la réalité : est-ce faisable dans les contraintes réelles ?", `Verdict ${verdictLabel} : le document doit être confronté à un test mesurable avant de devenir une certitude opérationnelle.`, [
      "Mesurer le temps, le coût, les compétences, les dépendances et les cas d'échec.",
      "Tester sur un échantillon représentatif plutôt que sur un exemple favorable.",
      "Comparer le résultat obtenu à un critère défini avant l'essai."
    ], "gifle_de_la_réalité", ids)
  ];
  return {
    segmentId: request.segment.segmentId,
    source: sem.source,
    questions,
    verdict: {
      label: verdictLabel,
      explanation: `Le contenu présente ${claims.length} affirmation(s), ${facts.length} fait(s) détecté(s) et ${uncertaintyCount} zone(s) d'incertitude ou d'ambiguïté.`,
      confidence: Math.max(0.25, Math.min(0.9, 0.45 + facts.length * 0.07 - uncertaintyCount * 0.04)),
      sourceChunkIds: ids
    },
    minimalRealityTest: {
      hypothesis: claim,
      protocol: [
        "Définir une mesure de départ et un critère de succès avant l'essai.",
        "Appliquer la proposition sur un échantillon représentatif et journaliser chaque exception.",
        "Comparer le résultat à une référence ou à une méthode existante.",
        "Documenter les coûts, le temps, les erreurs et les effets non prévus."
      ],
      successCriteria: ["Le résultat atteint le seuil défini sans déplacer le problème vers un coût caché.", "Le résultat est reproductible sur plusieurs cas."],
      failureCriteria: ["Le seuil n'est pas atteint.", "Le résultat dépend d'un cas favorable non généralisable.", "Le coût ou le risque annule le bénéfice."],
      sourceChunkIds: ids
    }
  };
}

function pseudocode(request: AnalyzeSegmentRequest, sem: SemanticAnalysisResult): PseudocodeAnalysisResult {
  const ids = sourceIds(request);
  const sourceSentences = sentences(request.segment.text);
  const procedural = sourceSentences.filter((item) => /^\s*(\d+[.)-]|[-*])/.test(item) || /\b(d'abord|ensuite|puis|enfin|étape|inspecter|mesurer|vérifier|créer|analyser|traiter|calculer|extraire|enregistrer)\b/i.test(item));
  const actions = (procedural.length ? procedural : sourceSentences.slice(0, 6)).slice(0, 10);
  const steps = actions.map((action, index) => ({
    order: index + 1,
    action,
    ...( /\b(si|lorsque|quand|condition)\b/i.test(action) ? { condition: "Condition extraite ou à formaliser depuis la phrase source." } : {}),
    onFailure: "Journaliser l'échec, conserver la provenance et appliquer une reprise contrôlée.",
    sourceChunkIds: ids
  }));
  const name = `Processus_${request.segment.segmentId}`;
  const pseudoLines = [
    `PROCÉDURE ${name}(entrée)`,
    "  VALIDER entrée",
    ...steps.map((step) => `  ${step.order}. ${step.action.replace(/\s+/g, " ").slice(0, 220)}`),
    "  VÉRIFIER les critères d'acceptation",
    "  RETOURNER résultat, preuves, erreurs, provenance",
    "FIN PROCÉDURE"
  ];
  return {
    segmentId: request.segment.segmentId,
    source: sem.source,
    name,
    objective: sem.summary,
    inputs: ["Contenu documentaire du segment", "Instruction utilisateur", "Identifiants des chunks sources"],
    outputs: ["Résultat structuré", "Journal des preuves", "Erreurs et informations manquantes"],
    preconditions: ["Les chunks sources sont présents et ordonnés.", "La provenance de chaque élément est conservée."],
    invariants: ["Aucun chunk source n'est supprimé.", "Une inférence n'est jamais étiquetée comme fait explicite."],
    steps,
    exceptions: [
      { condition: "Information manquante ou ambiguë", handling: "Marquer INCONNU et produire une question de clarification.", sourceChunkIds: ids },
      { condition: "Contradiction entre deux passages", handling: "Conserver les deux versions et créer une alerte de contradiction.", sourceChunkIds: ids }
    ],
    acceptanceTests: [
      { given: "Tous les chunks du segment", when: "Le processus est exécuté", then: "Chaque chunk apparaît au moins une fois dans la provenance des résultats.", sourceChunkIds: ids },
      { given: "Une affirmation sans preuve", when: "Le gant de KENT est appliqué", then: "L'affirmation est classée comme hypothèse ou preuve manquante.", sourceChunkIds: ids }
    ],
    pseudocode: pseudoLines.join("\n")
  };
}

export class RulesAnalysisProvider implements AnalysisProvider {
  readonly capabilities = {
    provider: "rules" as const,
    model: "ocr-ai-rules-v1",
    maxInputChars: 50000,
    maxSegmentsPerSynthesis: 200,
    supportsStructuredJson: true
  };

  async analyzeSegment(request: AnalyzeSegmentRequest): Promise<AnalyzeSegmentResult> {
    const sem = semantic(request);
    const mai = maieutic(request, sem);
    return {
      semantic: sem,
      maieutic: mai,
      kent: kent(request, sem, mai),
      pseudocode: pseudocode(request, sem)
    };
  }

  async synthesize(input: {
    documentId: string;
    instruction: string;
    results: AnalyzeSegmentResult[];
    sourceChunkIds: string[];
  }): Promise<AnalysisBundle["synthesis"]> {
    const summaries = input.results.map((result) => result.semantic.summary);
    const themes = [...new Set(input.results.flatMap((result) => result.semantic.themes.map((theme) => theme.name)))].slice(0, 12);
    const questions = [...new Set(input.results.flatMap((result) => result.maieutic.questionsToAsk.map((item) => item.question)))].slice(0, 12);
    const priorities = input.results.flatMap((result) => result.kent.minimalRealityTest.protocol).slice(0, 8);
    const digest = createHash("sha256").update(summaries.join("\n")).digest("hex").slice(0, 8);
    return {
      executiveSummary: summaries.slice(0, 8).join("\n\n") || "Aucune synthèse disponible.",
      coreThemes: themes,
      centralProblem: firstOr(input.results.map((result) => result.maieutic.centralProblem), "Problème central non déterminé."),
      realityVerdict: `Synthèse ${digest} : ${input.results.map((result) => result.kent.verdict.label).join(", ") || "aucun verdict"}. Les conclusions doivent être confrontées aux tests minimaux proposés.`,
      operationalModel: input.results.map((result) => result.pseudocode.pseudocode).slice(0, 6).join("\n\n"),
      priorityActions: priorities.length ? priorities : ["Définir un critère mesurable.", "Tester sur un échantillon représentatif.", "Conserver la provenance et les erreurs."],
      unresolvedQuestions: questions,
      sourceChunkIds: input.sourceChunkIds
    };
  }

  async health(): Promise<{ ok: boolean; detail: string }> {
    return { ok: true, detail: "Moteur déterministe local disponible. Il sert de preuve fonctionnelle, pas de substitut à un LLM expert." };
  }
}
