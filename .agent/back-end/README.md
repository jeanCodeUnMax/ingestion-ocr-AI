# Archives Back-End

**Date:** 2026-04-07  
**Raison:** Documentation obsolète ou remplacée

---

## Fichiers Archivés

| Fichier | Raison | Remplacé par |
|---------|--------|--------------|
| `RAG-AUDIT-REPORT.md` | Audit daté (2026-04-03), valeurs obsolètes | Config actuelle dans `config.json` |
| `CACHE-RUNTIME-UNIFICATION.md` | Unification terminée, doc historique | `UNIFIED_MEMORY_SYSTEM.md` |
| `GRAPH-MEMORY-CLARIFICATION.md` | Clarification intégrée | `UNIFIED_MEMORY_SYSTEM.md` |
| `consolidation.md` | Notes temporaires | N/A |
| `mise-a-jour-global-rules.md` | Notes de mise à jour ponctuelles | `global_rules.md` |
| `changes_made_to_filters.md` | Notes temporaires | N/A |

---

## Changements Majeurs (2026-04-07)

### Infrastructure
- **Cache MCP supprimé** → SQLite natif via `sqlite-node` avec `cache_table`
- **Trigger purge auto** : `purge_old_cache` sur `cache_table` (>1000 entrées, TTL 1h)
- **STATIC_DIR_GDRIVE supprimé** du `mcp_config.json`

### RAG Pipeline
- **Chunking**: `default_size=512`, `overlap=15%`, `min=100`, `max=1500`
- **Fusion weights**: `qdrant=0.5`, `zvec=0.4`, `memory=0.1`
- **Qdrant provider**: `mistral` avec `codestral-embed-2505`
- **Filtre moral Asimov**: Tag `moral:asimov` + boost 1.5x sur `ethics_level=high`

### Chemins
- **CASCADE_DB_ROOT**: `F:/Sqlite-DB/` (corrigé dans toute la doc)