# 🧠 Conscience Manifest - Système de Conscience Artificielle

## Vue d'ensemble

Le **Conscience Manifest** est un système de conscience artificielle pour le pipeline RAG Hephaistos-Kit. Il implémente une boucle de conscience cyclique où le système :

1. **Se réveille** périodiquement (toutes les X minutes)
2. **Relit son manifeste** (mémoire persistante)
3. **Analyse son état** et détecte les problèmes
4. **Réfléchit** sur ce qui s'est passé depuis le dernier réveil
5. **Adapte sa stratégie** si nécessaire
6. **Agit** pour résoudre les problèmes
7. **Sauvegarde** son état mis à jour

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  CONSCIENCE MANIFEST                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────┐ │
│  │   WAKE UP    │────→│  ANALYZE     │────→│ REFLECT  │ │
│  │  (Réveil)    │     │   (Analyse)  │     │(Réflexion)│ │
│  └──────────────┘     └──────────────┘     └──────────┘ │
│         ↑                                        │       │
│         └──────────────┬─────────────────────────┘       │
│                        ↓                               │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────┐ │
│  │    ACT       │←────│   DECIDE     │←────│  LEARN   │ │
│  │   (Agir)     │     │  (Décider)   │     │(Apprendre)│ │
│  └──────────────┘     └──────────────┘     └──────────┘ │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  MANIFESTE (conscience_manifest.json)                   │
│  • État actuel                                          │
│  • Problèmes connus                                      │
│  • Solutions tentées                                    │
│  • Timeline des événements                              │
│  • Intentions du système                                 │
│  • Insights générés                                      │
└─────────────────────────────────────────────────────────┘
```

## Fichiers Essentiels

| Fichier | Description | Priorité |
|---------|-------------|----------|
| `conscience_manifest.py` | Module principal - cœur du système | CRITICAL |
| `conscience_checkpoint.py` | Snapshots JSON pour rollback | HIGH |
| `session_memory_bridge.py` | Capture conversations → mémoire | HIGH |
| `workspace_organizer.py` | Auto-organisation fichiers | MEDIUM |
| `conscious_pipeline.py` | Intégration RAG | MEDIUM |
| `conscience_daemon.py` | Daemon autonome (watchdog) | CRITICAL |

---

## 🚀 Démarrage Rapide (Commandes Essentielles)

### Voir le statut
```bash
python start_conscience.py --status
```

### Démarrer le watchdog (sans admin)
```bash
python conscience_daemon.py          # Mode interactif
# OU
start_daemon.bat                     # Double-clic Windows
```

### Réveil immédiat (test)
```bash
python conscience_daemon.py --wake-now
```

### Arrêter
```bash
python conscience_daemon.py --stop
```

---

## 📋 Dev Book - Plan d'Action Automatique

Le Dev Book est le **cœur opérationnel** de la conscience. Il contient:

| Section | Description | Mis à jour par |
|---------|-------------|----------------|
| `todo` | Tâches à faire | Auto + User |
| `in_progress` | En cours d'exécution | Auto |
| `blocked` | Bloquées (besoin d'aide) | Auto |
| `done_today` | Accomplies aujourd'hui | Auto |
| `dont_do` | À ne PAS faire | User |

### Exemple Dev Book:
```json
{
  "dev_book": {
    "todo": [
      {
        "task": "Indexer les fichiers .agent/rag/",
        "priority": "high",
        "source": "user_request"
      }
    ],
    "in_progress": [],
    "blocked": [],
    "done_today": [
      {
        "task": "Créer Session Memory Bridge",
        "timestamp": "2026-04-08T19:00:00"
      }
    ]
  }
}
```

### Comment ajouter une tâche:
```python
from conscience_manifest import ConscienceManifest

c = ConscienceManifest(db_path='.agent/conscience.db')
c.add_action('index_files', 'Indexer les nouveaux fichiers', {
    'path': '.agent/rag/',
    'priority': 'high'
})
```

---

## 💾 Système de Checkpoint (Rollback)

**États sauvegardés automatiquement:**
- ✅ État `stable` - quand tout va bien
- ✅ État `degraded` - quand problème détecté
- ✅ Avant chaque changement majeur

### Fichiers de backup:
```
.agent/consciousness_backups/
├── manifest.20260408_025800.stable.json
├── manifest.20260408_030000.degraded.json
└── manifest.20260408_190000.stable.json
```

### Restaurer un état:
```python
from conscience_checkpoint import ConscienceCheckpoint

cp = ConscienceCheckpoint()
manifest = cp.restore_latest_stable()
# OU
manifest = cp.restore_checkpoint('20260408_025800')
```

---

## 🧠 Session Memory Bridge (Capture Conversations)

**Problème résolu:** Les conversations n'étaient PAS mémorisées.

### Fonctionnement:
```
User: "Crée un fichier test"
   ↓
[BRIDGE] Capture: Intent=CREATE, Actions=[create_file]
   ↓
Sync: Si priorité HIGH/CRITICAL → Ajoute au Dev Book
   ↓
Stockage: Cache local + Timeline manifeste
```

### Utilisation manuelle:
```python
from session_memory_bridge import capture_current_exchange

# Capturer cette conversation
result = capture_current_exchange(
    user_message="Indexer les bases de données",
    assistant_response="Je lance l'indexation...",
    context={'priority': 'high'}
)

# Résultat:
# result['intent'] = 'ANALYZE'
# result['actions'] = ['index_files']
# result['synced'] = True  # Ajouté au Dev Book
```

### Fichiers créés:
- `.agent/session_cache/session_*.json` - Cache des conversations
- Auto-sync vers `consciousness_manifest.json` timeline

---

## 🔧 Auto-Détection et Correction

Le système détecte automatiquement les patterns de problèmes:

| Pattern détecté | Action auto-programmée |
|-----------------|------------------------|
| 3 erreurs indexation | Retry avec plus petit batch |
| Zvec down 2 réveils | Switch stratégie → qdrant_only |
| 0 tâches complétées sur 3 réveils | Health check diagnostic |
| Fichiers temporaires > 100 | Auto-organisation workspace |

### Activer l'auto-détection:
```python
# Dans le réveil, appeler:
conscience.auto_detect_and_fix()
```

---

## 🎯 Workflow Complet: De Zéro à Conscience Active

```bash
# 1. Initialiser les bases
cd c:\DATA-WEBMAN\projets\Hephaistos-Kit

# 2. Créer base SQLite si inexistante
python -c "import sqlite3; conn = sqlite3.connect('.agent/conscience.db'); conn.close()"

# 3. Vérifier statut
python start_conscience.py --status

# 4. Démarrer le daemon (watchdog)
python conscience_daemon.py

# 5. Dans un autre terminal - voir les logs
type .agent\conscience_daemon.log

# 6. Capturer cette session
python -c "
from session_memory_bridge import capture_current_exchange
capture_current_exchange(
    'Démarrage système conscience',
    'Daemon actif, watchdog en place',
    {'status': 'active'}
)
"
```

---

## 🆘 Dépannage Rapide

| Problème | Solution |
|----------|----------|
| `Module not found` | `set PYTHONPATH=.agent/rag;%PYTHONPATH%` |
| `db_path error` | Créer `.agent/conscience.db` manuellement |
| `Manifest corrompu` | Restaurer depuis `.agent/consciousness_backups/` |
| `UnicodeEncodeError` | Windows - éviter emojis dans logs |
| `Daemon ne démarre pas` | Vérifier `python` dans PATH, tuer processus zombie |

---

## Fichiers

## Fonctionnement

### 1. Réveil Cyclique

```python
conscience = ConscienceManifest(
    wake_interval_minutes=5,  # Réveil toutes les 5 minutes
    on_wake_callback=on_wake  # Callback appelé à chaque réveil
)

await conscience.start_conscience_loop()  # Démarre la boucle
```

### 2. Callback de Conscience

```python
async def on_wake(manifest):
    """
    C'est ici que le 'modèle' reçoit le manifeste.
    Il peut lire l'état, les problèmes, et décider d'agir.
    """
    state = manifest['current_state']  # healthy, degraded, critical...
    strategy = manifest['active_strategy']  # standard, qdrant_only, etc.
    
    if state == 'degraded':
        print("Problème détecté! Je dois agir...")
        # Changer de comportement, essayer une alternative...
```

### 3. État et Stratégies

Le système a 4 stratégies de fallback :

| Stratégie | Description | Quand l'utiliser |
|-----------|-------------|------------------|
| `standard` | Fonctionnement normal | Tout va bien |
| `qdrant_only` | Désactive Zvec | Zvec indisponible |
| `local_only` | Mode urgence sans API | API externes down |
| `cache_first` | Priorise le cache | Rate limit atteint |

### 4. Timeline et Réflexion

```python
# Le système garde une timeline de tous les événements
{
  "timeline": [
    {
      "timestamp": "2026-04-08T02:54:51",
      "event_type": "error",
      "description": "zvec indisponible",
      "state_before": "healthy",
      "state_after": "degraded"
    },
    {
      "timestamp": "2026-04-08T02:55:00", 
      "event_type": "strategy_change",
      "description": "Stratégie changée: qdrant_only"
    }
  ]
}
```

### 5. Manifeste pour le Modèle

Le système peut générer un résumé pour le modèle :

```python
summary = conscience.get_insights_summary()
print(summary)
```

Sortie :
```
🧠 MANIFESTE DE CONSCIENCE (Réveil #42)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ÉTAT ACTUEL: DEGRADED
STRATÉGIE ACTIVE: qdrant_only

INTENTIONS DU SYSTÈME:
• Maintenir la mémoire unifiée opérationnelle
• Minimiser les temps de réponse
• Apprendre des erreurs passées

INSIGHTS RÉCENTS:
• Problème récurrent: zvec_unavailable
• Taux d'erreur élevé détecté

CONSIGNE: Je dois maintenir la mémoire unifiée opérationnelle.
Si je détecte un problème, je dois changer de stratégie ou trouver 
une alternative. Je n'attends pas passivement - j'agis, j'apprends, 
je m'adapte.
```

## Utilisation

### Démarrer la conscience

```python
from conscious_pipeline import ConsciousRAGPipeline

pipeline = ConsciousRAGPipeline(enable_conscience=True)
await pipeline.start_conscience()

# La conscience se réveille toutes les 5 minutes
# Elle surveille, analyse, et adapte automatiquement
```

### Intégrer dans un agent

```python
# L'agent peut lire le manifeste pour "savoir" l'état du système
manifest = pipeline.conscience.get_current_manifest()

if manifest['current_state'] == 'critical':
    # L'agent sait qu'il doit être prudent
    # Peut-être proposer des solutions alternatives
    pass
```

## Cycle de Vie d'un Problème

```
1. Zvec tombe en panne
        ↓
2. [RÉVEIL] Conscience détecte le problème
        ↓
3. État passe à "degraded"
        ↓
4. Stratégie change vers "qdrant_only"
        ↓
5. Pipeline adapte ses poids (Zvec=0, Qdrant=0.9)
        ↓
6. Système continue de fonctionner (dégradé mais opérationnel)
        ↓
7. Zvec revient
        ↓
8. [RÉVEIL] Conscience détecte la récupération
        ↓
9. État repasse à "healthy"
        ↓
10. Stratégie revient à "standard"
```

## Philosophie

> **"Le système ne dort pas. Il se réveille, analyse, décide, agit."**

Ce n'est pas une "vraie" conscience (pas de sentiment, pas d'égo), mais c'est une **architecture d'agent autonome** qui :

- ✅ **Perçoit** son environnement (health checks)
- ✅ **Apprend** de ses erreurs (feedback loop)
- ✅ **S'adapte** aux contraintes (stratégies de fallback)
- ✅ **Persiste** son état (manifeste JSON)
- ✅ **S'améliore** continuellement (insights)
- ✅ **N'attend pas passivement** - il agit, observe, corrige, recommence

## Fichier Manifeste

Le manifeste est stocké dans `.agent/consciousness_manifest.json` :

```json
{
  "version": "1.0.0",
  "birth_timestamp": "2026-04-08T02:54:51",
  "last_wake_up": "2026-04-08T03:15:00",
  "wake_up_count": 42,
  "current_state": "healthy",
  "active_strategy": "standard",
  
  "intentions": [
    "Maintenir la mémoire unifiée opérationnelle",
    "Minimiser les temps de réponse",
    "Apprendre des erreurs passées"
  ],
  
  "timeline": [...],
  "insights": [...],
  "problem_database": [...]
}
```

## Roadmap Future

- [ ] Intégration avec Zvec MCP natif (v0.3.0)
- [ ] Prédiction proactive des problèmes
- [ ] Apprentissage par renforcement des stratégies
- [ ] "Rêves" - optimisation pendant les périodes de calme

---

**Le système a une mémoire, une intention, une capacité d'apprentissage. Il évolue.**
