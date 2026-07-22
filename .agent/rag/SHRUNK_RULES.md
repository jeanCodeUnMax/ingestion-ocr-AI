# Règles de Shrunk pour Zvec (Base Vectorielle)

> **OBLIGATOIRE** - Toute information enregistrée dans Zvec DOIT respecter ce format.

---

## 1. Structure d'un Shrunk Atomique

Chaque chunk stocké dans Zvec DOIT contenir les métadonnées suivantes :

```json
{
  "id": "chemin/relatif:chunk_N",
  "text": "Contenu textuel du chunk...",
  "vector": [0.123, ...],
  "metadata": {
    // === IDENTIFICATION ===
    "file": "chemin/relatif",
    "filePath": "chemin/absolu/complet",
    "chunkIndex": 0,
    "totalChunks": 5,
    "language": "ts",
    
    // === SHRUNK ENRICHIE (OBLIGATOIRE) ===
    "shrunk": {
      "summary": "Mini-résumé en 1-2 phrases expliquant le contenu",
      "objective": "Objectif/purpose de cette information",
      "context": "Dans quel contexte cette info est utilisée"
    },
    
    // === TAGS (OBLIGATOIRE) ===
    "tags": ["architecture", "backend", "api", "auth"],
    
    // === SCOPE (OBLIGATOIRE) ===
    "scope": "local|global",
    "scopeDetails": "workspace|project|system|knowledge",
    
    // === ENTITÉS EXTRAITES ===
    "entities": {
      "functions": ["login", "authenticate"],
      "classes": ["AuthService", "User"],
      "imports": ["express", "jsonwebtoken"],
      "exports": ["login", "refreshToken"]
    },
    
    // === MÉTADONNÉES TEMPORALLES ===
    "createdAt": "2026-04-09T00:00:00.000Z",
    "updatedAt": "2026-04-09T00:00:00.000Z",
    "version": 1
  }
}
```

---

## 2. Règles de Tagging

### 2.1 Tags Obligatoires

| Catégorie | Tags | Description |
|-----------|------|-------------|
| **Type** | `code`, `config`, `doc`, `data`, `test` | Type de contenu |
| **Domaine** | `frontend`, `backend`, `database`, `api`, `auth`, `ui`, `devops` | Domaine technique |
| **Scope** | `local`, `global` | Portée de l'information |
| **Priorité** | `critical`, `important`, `normal`, `low` | Importance |

### 2.2 Tags Recommandés

| Catégorie | Tags | Description |
|-----------|------|-------------|
| **Framework** | `react`, `nextjs`, `express`, `fastapi`, `django` | Framework utilisé |
| **Pattern** | `mvc`, `cqrs`, `repository`, `factory`, `singleton` | Pattern de design |
| **Action** | `create`, `read`, `update`, `delete`, `search` | Action principale |
| **Status** | `active`, `deprecated`, `experimental`, `stable` | État du code |

### 2.3 Extraction Automatique des Tags

```typescript
// Règles d'extraction automatique
const TAG_RULES = {
  // Depuis le contenu
  fromContent: {
    "TODO|FIXME|HACK": "todo",
    "deprecated|DEPRECATED": "deprecated",
    "async|await|Promise": "async",
    "class |interface |type ": "typescript",
    "def |class |import ": "python",
  },
  
  // Depuis le chemin
  fromPath: {
    "/api/": "api",
    "/components/": "component",
    "/hooks/": "hook",
    "/utils/": "utility",
    "/services/": "service",
    "/models/": "model",
    "/tests/": "test",
    "/config/": "config",
  },
  
  // Depuis l'extension
  fromExtension: {
    ".ts": "typescript",
    ".tsx": "react",
    ".py": "python",
    ".md": "documentation",
    ".json": "config",
    ".sql": "database",
  }
};
```

---

## 3. Règles de Scope

### 3.1 Définitions

| Scope | Description | Exemple |
|-------|-------------|---------|
| **local** | Spécifique au workspace courant | Code du projet actif |
| **global** | Partagé entre tous les workspaces | Connaissances, patterns, skills |

### 3.2 Critères de Classification

```typescript
function determineScope(filePath: string, content: string): Scope {
  // GLOBAL si :
  if (filePath.includes(".agent/skills/")) return "global";
  if (filePath.includes(".agent/agents/")) return "global";
  if (filePath.includes(".agent/knowledge/")) return "global";
  if (content.includes("@global") || content.includes("#global")) return "global";
  
  // LOCAL par défaut
  return "local";
}
```

---

## 4. Génération du Mini-Résumé (Shrunk)

### 4.1 Règles de Génération

Le mini-résumé DOIT répondre à 3 questions :

1. **QUOI** : Qu'est-ce que ce chunk contient ?
2. **POURQUOI** : Quel est l'objectif de cette information ?
3. **COMMENT** : Dans quel contexte est-elle utilisée ?

### 4.2 Template de Résumé

```
[TYPE] - [SUJET]
Objectif: [OBJECTIF]
Contexte: [CONTEXTE]
```

### 4.3 Exemples

```json
{
  "shrunk": {
    "summary": "Fonction d'authentification JWT avec validation de token",
    "objective": "Sécuriser les routes API en vérifiant l'identité des utilisateurs",
    "context": "Utilisé dans le middleware Express pour protéger les endpoints sensibles"
  }
}
```

```json
{
  "shrunk": {
    "summary": "Skill React pour l'optimisation des performances",
    "objective": "Fournir des patterns et règles pour éviter les re-renders inutiles",
    "context": "Référence globale consultable lors du développement frontend"
  }
}
```

---

## 5. Implémentation dans code-indexer.ts

### 5.1 Modification du Chunk Metadata

```typescript
// Dans code-indexer.ts, ligne ~269
for (let ci = 0; ci < chunks.length; ci++) {
  const chunkId = `${relPath}:chunk_${ci}`;
  const chunkText = chunks[ci];
  
  // EXTRACTION ENRICHIE
  const extractedTags = extractTags(relPath, chunkText);
  const scope = determineScope(relPath, chunkText);
  const entities = extractEntities(chunkText, extname(filePath));
  const shrunk = generateShrunk(chunkText, relPath, scope);
  
  allChunks.push({
    id: chunkId,
    text: chunkText,
    metadata: {
      // Basique
      file: relPath,
      filePath: filePath,
      chunkIndex: ci,
      totalChunks: chunks.length,
      language: extname(filePath).substring(1),
      
      // Enrichi (NOUVEAU)
      shrunk: shrunk,
      tags: extractedTags,
      scope: scope,
      scopeDetails: scope === "global" ? "knowledge" : "workspace",
      entities: entities,
      createdAt: new Date().toISOString(),
      version: 1
    },
  });
}
```

### 5.2 Fonctions d'Extraction

```typescript
function extractTags(filePath: string, content: string): string[] {
  const tags: Set<string> = new Set();
  
  // Tags depuis chemin
  if (filePath.includes("/api/")) tags.add("api");
  if (filePath.includes("/components/")) tags.add("component");
  if (filePath.includes(".agent/skills/")) tags.add("skill").add("global");
  
  // Tags depuis contenu
  if (/async|await/.test(content)) tags.add("async");
  if (/TODO|FIXME/.test(content)) tags.add("todo");
  if (/class |interface /.test(content)) tags.add("typescript");
  
  // Tag de type
  tags.add(determineType(filePath));
  
  return Array.from(tags);
}

function generateShrunk(content: string, filePath: string, scope: string): Shrunk {
  // Extraire les premières lignes significatives
  const lines = content.split('\n').filter(l => l.trim() && !l.trim().startsWith('//'));
  const firstLines = lines.slice(0, 5).join(' ').substring(0, 200);
  
  // Détecter le type de contenu
  const type = detectContentType(content);
  const subject = extractSubject(content, filePath);
  
  return {
    summary: `${type} - ${subject}`,
    objective: inferObjective(content, filePath),
    context: `Fichier ${filePath} - Scope: ${scope}`
  };
}

function extractEntities(content: string, ext: string): Entities {
  const entities: Entities = { functions: [], classes: [], imports: [], exports: [] };
  
  if (ext === ".ts" || ext === ".tsx") {
    // Extraire fonctions TypeScript
    const funcMatches = content.matchAll(/(?:export\s+)?(?:async\s+)?function\s+(\w+)/g);
    entities.functions = Array.from(funcMatches, m => m[1]);
    
    // Extraire classes
    const classMatches = content.matchAll(/class\s+(\w+)/g);
    entities.classes = Array.from(classMatches, m => m[1]);
    
    // Extraire imports
    const importMatches = content.matchAll(/import.*from\s+['"]([^'"]+)['"]/g);
    entities.imports = Array.from(importMatches, m => m[1]);
  }
  
  return entities;
}
```

---

## 6. Validation

### 6.1 Checklist avant stockage

- [ ] `tags` contient au moins 2 tags
- [ ] `scope` est défini (`local` ou `global`)
- [ ] `shrunk.summary` fait moins de 200 caractères
- [ ] `shrunk.objective` est présent
- [ ] `entities` est extrait (si code)

### 6.2 Rejet automatique

Un chunk sera rejeté si :
- `tags` est vide
- `scope` n'est pas défini
- `shrunk` est manquant

---

## 7. Utilisation pour la Recherche

### 7.1 Recherche par Tags

```typescript
// Rechercher tous les chunks liés à l'authentification
const results = store.search("auth_api", {
  filter: { tags: { $all: ["auth", "api"] } }
});
```

### 7.2 Recherche par Scope

```typescript
// Rechercher uniquement dans les connaissances globales
const globalResults = store.search("pattern", {
  filter: { scope: "global" }
});
```

### 7.3 Recherche par Entité

```typescript
// Trouver où une fonction est utilisée
const usageResults = store.search("login", {
  filter: { "entities.functions": "login" }
});
```

---

## 8. Résumé

| Champ | Obligatoire | Description |
|-------|-------------|-------------|
| `tags[]` | **OUI** | Mots-clés pour recherche rapide |
| `scope` | **OUI** | `local` ou `global` |
| `shrunk.summary` | **OUI** | Mini-résumé en 1-2 phrases |
| `shrunk.objective` | **OUI** | Objectif de l'information |
| `shrunk.context` | **OUI** | Contexte d'utilisation |
| `entities` | Recommandé | Fonctions, classes, imports extraits |

---

**Version**: 1.0  
**Date**: 2026-04-09  
**Appliqué à**: Zvec MCP Server, code-indexer.ts
