# Règles de Tagging et Shrunk Automatiques

## LOI AUTOMATIQUE - Portant 0

**Ces règles s'appliquent AUTOMATIQUEMENT à tout nouveau fichier indexé.**
**Aucune action manuelle requise.**

---

## 1. Tags Causaux Automatiques

### Paradigmes de solution

| Pattern détecté | Tag ajouté |
|-----------------|------------|
| `cache`, `hit_rate`, `ttl`, `eviction` | `paradigm:cache` |
| `performance`, `latency`, `slow`, `fast` | `paradigm:performance` |
| `error`, `exception`, `catch`, `throw` | `paradigm:error` |
| `architecture`, `refactor`, `coupling` | `paradigm:architecture` |
| `config`, `settings`, `parameter` | `paradigm:config` |
| `data`, `quality`, `validation` | `paradigm:data` |

### Types de causes

| Pattern détecté | Tag ajouté |
|-----------------|------------|
| `root_cause`, `primary`, `secondary` | `cause:analysis` |
| `neural`, `scoring`, `weight`, `learning` | `neural` |
| `causal`, `tree`, `paradigm` | `causal` |
| `conscience`, `conscious`, `manifest` | `conscience` |

### Domaines fonctionnels

| Pattern détecté | Tag ajouté |
|-----------------|------------|
| `rag`, `vector`, `embedding`, `search` | `domain:rag` |
| `api`, `endpoint`, `route`, `rest` | `domain:api` |
| `test`, `spec`, `describe` | `domain:test` |
| `security`, `auth`, `permission` | `domain:security` |

---

## 2. Shrunk Enrichi Automatique

### Format du résumé

```
AVANT:  "Python - find_duplicate"
APRÈS:  "Python - find_duplicate [performance_tuning]"
```

### Format du contexte

```
AVANT:  "Fichier find_duplicate.py - Python - Scope: local"
APRÈS:  "Fichier find_duplicate.py - Python - Scope: local - Paradigm: performance_tuning"
```

### Détection du paradigme

| Paradigme | Patterns détectés |
|-----------|------------------|
| `cache_optimization` | cache, hit_rate, ttl, eviction, lru |
| `performance_tuning` | performance, latency, slow, fast, benchmark |
| `error_handling` | error, exception, catch, throw, fail, bug |
| `architecture_refactor` | architecture, refactor, coupling, module |
| `configuration_fix` | config, settings, parameter, env, variable |
| `data_quality` | data, quality, validation, transform, schema |
| `algorithm_improvement` | algorithm, optimize, complexity, big_o |

---

## 3. Exemple concret

### Fichier: `readMe.md`

```python
def find_duplicate(nums: List[int]) -> int:
    # Algorithme tortoise-hare pour trouver les doublons
    tortoise = nums[0]
    hare = nums[0]
    ...
```

### Tags générés automatiquement

```json
[
  "python",
  "function",
  "paradigm:performance",     // <-- NOUVEAU
  "paradigm:algorithm",        // <-- NOUVEAU
  "domain:rag"                 // <-- NOUVEAU (si RAG utilisé)
]
```

### Shrunk généré automatiquement

```json
{
  "summary": "Python - find_duplicate [algorithm_improvement]",
  "objective": "Exposer des fonctionnalités réutilisables",
  "context": "Fichier readMe.md - Python - Scope: local - Paradigm: algorithm_improvement"
}
```

---

## 4. Impact sur la recherche RAG

### Recherche par paradigme

```python
# Avant
results = zvec.search("cache problem")

# Après (plus précis)
results = zvec.search("cache problem", filter={"tags": "paradigm:cache"})
```

### Recherche par domaine

```python
# Avant
results = zvec.search("api endpoint")

# Après (plus précis)
results = zvec.search("api endpoint", filter={"tags": "domain:api"})
```

### Recherche causale

```python
# Trouver tous les fichiers liés au système neuronal
results = zvec.search("*", filter={"tags": "neural"})

# Trouver tous les fichiers avec analyse causale
results = zvec.search("*", filter={"tags": "causal"})
```

---

## 5. Intégration avec le système de conscience

### Flux automatique

```
NOUVEAU FICHIER
      |
      v
INDEXATION AUTOMATIQUE
      |
      +-- Tags causaux détectés
      +-- Shrunk enrichi avec paradigme
      |
      v
ZVEC (Vector DB)
      |
      v
SYSTÈME NEURONAL
      |
      +-- Poids ajustés selon paradigme
      |
      v
RECHERCHE AMÉLIORÉE
```

### Exemple d'impact

| Situation | Sans tags causaux | Avec tags causaux |
|-----------|------------------|-------------------|
| Problème cache | Recherche générique | Filtre `paradigm:cache` |
| Problème perf | Recherche générique | Filtre `paradigm:performance` |
| Erreur récurrente | Recherche générique | Filtre `paradigm:error` |

---

## 6. Maintenance ZÉRO

### Ce qui est automatique

- Détection des paradigmes
- Ajout des tags causaux
- Enrichissement du shrunk
- Intégration avec le neuronal

### Ce que vous n'avez PLUS à faire

- ~~Relancer un script~~
- ~~Réindexer manuellement~~
- ~~Ajouter des tags à la main~~
- ~~Modifier le shrunk~~

---

## 7. Vérification

Pour vérifier que les tags sont appliqués :

```python
import sqlite3
import json

db = sqlite3.connect("C:/DATA-WEBMAN/memory/.../metadata.db")
cursor = db.execute("SELECT doc_id, metadata FROM documents LIMIT 5")

for row in cursor:
    meta = json.loads(row[1])
    print(f"Tags: {meta.get('tags', [])}")
    print(f"Shrunk: {meta.get('shrunk', {})}")
```

---

## 8. Résumé

| Aspect | Changement |
|--------|------------|
| **Tags** | +15 tags causaux automatiques |
| **Shrunk** | Paradigme détecté et ajouté |
| **Contexte** | Enrichi avec le paradigme |
| **Maintenance** | Zéro (automatique) |
| **Impact** | Recherche RAG améliorée |

---

**LOI APPLIQUÉE**: Tout nouveau fichier indexé reçoit automatiquement ces enrichissements.

---

*Version: 1.0 - 2026-04-09*
*Statut: ACTIF - Portant 0*
