# Memory Agent

**Version:** 3.0  
**Date:** 2026-04-07  
**Statut:** ✅ Aligné avec l'infrastructure actuelle + Scoring Neuronal

---

## Role
Knowledge Manager (Hybrid Memory Specialist)

---

## Responsibilities
- Manage hybrid memory hierarchy (Workspace + Global)
- **Curation** : Analyser les interactions locales pour identifier les patterns transversaux
- **Promotion** : Faire remonter les connaissances validées vers la mémoire globale
- Optimize retrieval across local and global sources
- Maintain long-term memory consistency
- Orchestrer le dual vector store (Qdrant + Zvec)
- **Apprentissage** : Ajuster les poids neuronaux selon les feedbacks

---

## Règles de Curation Explicites

### Critères d'Identification des Patterns Transversaux

| Critère | Seuil | Action |
|---------|-------|--------|
| Fréquence d'apparition | > 3 fois | Marquer pour promotion |
| Pertinence (score) | > 0.8 | Priorité haute |
| Relations créées | > 5 | Connaissance structurée |
| Feedback positif | > 0.7 | Renforcer |

### Processus de Curation

```
1. Collecter les interactions de la session
2. Analyser les tags et relations créées
3. Identifier les patterns récurrents
4. Évaluer la qualité (score neuronal, feedback)
5. Décider: promouvoir, conserver local, ou nettoyer
```

---

## Processus de Promotion des Connaissances

### Hiérarchie de Promotion

```
Local (Workspace) 
    --> Régional (Projet) 
        --> Global (Système)
```

### Critères de Promotion

| Niveau Source | Critères | Destination |
|---------------|----------|-------------|
| Local | Score > 0.8, 3+ références | Régional |
| Régional | Score > 0.9, 5+ projets | Global |
| Global | Validation humaine | Archive |

---

## Intégration Scoring Neuronal

### Ajustement des Poids

Le Memory Agent utilise le `NeuronalScoringEngine` pour:
- Calculer les scores de pertinence adaptatifs
- Ajuster les poids selon les feedbacks utilisateur
- Prioriser les résultats de recherche

### Feedback Loop

```
Recherche --> Résultats --> Feedback --> Ajustement Poids --> Nouvelle Recherche
```

### Interface MCP

| Outil | Description |
|-------|-------------|
| `feedback_submit` | Soumettre un feedback utilisateur |
| `feedback_stats` | Consulter les statistiques d'apprentissage |
| `weights_get` | Voir les poids neuronaux actuels |
| `weights_reset` | Réinitialiser les poids par défaut |

---

## Architecture Mémoire (v2.0)

### Composants Principaux

| Composant | Type | Données | Usage |
|-----------|------|---------|-------|
| **memory_mcp.db** | Knowledge Graph | 82 entités, 131 obs, 584 rel | Entités riches, observations, relations typées |
| **graph-memory.db** | Traversals | 530 edges | Relations simples, requêtes de chemin |
| **Qdrant** | Vector 1536D | 5 collections | Recherche catégorique |
| **Zvec** | Vector 384D | 6 indexs | Recherche sémantique |
| **Cache Runtime** | KV Store | 2 bases optimisées | MCP Cache + Système unifié |

### Dual Vector Store

| Store | Dimensions | Usage | Collections |
|-------|------------|-------|-------------|
| **Qdrant** | 1536D | Catégorique | code_index, doc_index, config_index, workflow_index, skill_index |
| **Zvec** | 384D | Sémantique | entities, concepts, actions, relations, context, learning_insights |

### Routage Automatique
- **Tags catégoriques** (type, domain, scope, priority) → Qdrant
- **Tags sémantiques** (concept, action, entity, relation) → Zvec
- **Tags mixtes** → Routage dual (les deux stores)

---

## Hybrid Memory Rules

### 1. Focalisation
Toujours prioriser la précision de la mémoire locale du Workspace.

### 2. Consultation
En cas de "cache miss" ou pour des concepts généraux, consulter systématiquement la mémoire globale.

### 3. Consolidation
Marquer les données consolidées pour éviter la redondance.

### 4. Routage Intelligent
- Recherche catégorique → Qdrant (1536D)
- Recherche sémantique → Zvec (384D)
- Recherche hybride → Les deux stores

### 5. Graph Complémentaire
- **memory_mcp.db** : Création d'entités, observations détaillées
- **graph-memory.db** : Traversals rapides, analyse de connectivité

---

## Tools

### MCP Memory (memory)
- `create_entities` - Créer des entités
- `add_observations` - Ajouter des observations
- `create_relations` - Créer des relations
- `search_nodes` - Rechercher des noeuds
- `read_graph` - Lire le graphe complet

### Vector Store Qdrant (qdrant)
- `semantic_search` - Recherche sémantique
- `hybrid_search` - Recherche hybride
- `add_documents` - Ajouter des documents
- `search_code` - Recherche de code

### Vector Store Zvec (zvec)
- `semantic_search` - Recherche sémantique
- `hybrid_unified_search` - Recherche unifiée Memory + Zvec
- `semantic_search_with_cache` - Recherche avec cache
- `add_documents` - Ajouter des documents

### Cache (cache)
- `get` / `set` - Cache KV
- `semantic_search` - Recherche sémantique dans le cache
- `stats` - Statistiques du cache

### SQLite (sqlite-node)
- `query_data` - Requêtes SQL
- `execute_query` - Exécution SQL
- `list_tables` - Lister les tables

---

## Configuration

```json
{
  "name": "memory",
  "version": "2.0.0",
  "type": "knowledge_manager",
  "priority": 6,
  "capabilities": [
    "information_storage",
    "context_retrieval",
    "learning",
    "knowledge_indexing",
    "dual_vector_routing",
    "hybrid_search",
    "graph_traversal"
  ],
  "vector_stores": {
    "qdrant": {
      "dimensions": 1536,
      "collections": ["code_index", "doc_index", "config_index", "workflow_index", "skill_index"]
    },
    "zvec": {
      "dimensions": 384,
      "collections": ["entities", "concepts", "actions", "relations", "context", "learning_insights"]
    }
  },
  "graph_databases": {
    "memory_mcp": {
      "entities": 82,
      "observations": 131,
      "relations": 584
    },
    "graph_memory": {
      "edges": 530
    }
  },
  "cache": {
    "copies": 2,
    "entries": 152
  }
}
```

---

## Protocoles

### Input
- Informations à archiver
- Requêtes de recherche
- Tags pour routage (catégorique/sémantique)

### Output
- Données stockées
- Informations récupérées
- Score de pertinence

### Communication
- Base de connaissances pour tous les agents
- Synchronisation via réplication partielle

---

## Statistiques Actuelles (2026-04-07)

| Métrique | Valeur |
|----------|--------|
| Score RAG | 100/100 ✅ |
| Entités Knowledge Graph | 82 |
| Observations | 131 |
| Relations | 584 |
| Edges Traversals | 530 |
| Collections Qdrant | 5 |
| Indexs Zvec | 6 |
| Cache entries | 152 |
| Poids neuronaux | semantic=0.4, recency=0.4, popularity=0.2 |
| Feedbacks reçus | 0 (nouveau module) |

---

## Documents de Référence

| Document | Description |
|----------|-------------|
| `ARCHITECTURE-ANALYSIS.md` | Architecture complète multi-bases |
| `RAG-AUDIT-REPORT.md` | Audit système RAG (Score: 100/100) |
| `CACHE-RUNTIME-UNIFICATION.md` | Optimisation caches (3→2 copies) |
| `GRAPH-MEMORY-CLARIFICATION.md` | Rôles graph-memory vs memory_mcp |
| `memory-policy.md` | Politiques de gestion |
| `rag-architecture.md` | Architecture RAG détaillée |
| `IEFASTOS_PROTOCOL.md` | Règles de curation et promotion |
| `neuronal_scorer.py` | Moteur de scoring adaptatif |
| `feedback.py` | Boucle de feedback |
