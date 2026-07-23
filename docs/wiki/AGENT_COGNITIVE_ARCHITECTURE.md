# Architecture Cognitive et Mémoire des Agents

Le projet OCR AI System utilise le système d'orchestration d'agents **Hephaistos**. Il est crucial pour les agents (comme Antigravity, Kilo, ou Cursor) de comprendre la différence entre leur propre "cerveau" (mémoire de session de l'IDE) et le "cerveau global" du projet (Hephaistos).

## 1. La Conscience Hephaistos (Source de vérité du projet)
Hephaistos maintient l'état global du projet dans :
- `.agent/consciousness_manifest.json` : Contient les intentions en cours, les états de santé du système, et le `dev_book.todo` (liste des tâches).
- `docs/DEVBOOK-PROGRESS-v0.6.md` : Le carnet de bord humain lisible.
- **Règle absolue** : Tous les agents doivent lire le `consciousness_manifest.json` au démarrage pour s'aligner sur la mission actuelle. Toute décision ou tâche critique pour le futur doit y être inscrite.

## 2. Le "Brain" d'Antigravity (Mémoire de session IDE)
L'agent Antigravity (Gemini IDE) génère ses propres artefacts (ex: `implementation_plan.md`, `walkthrough.md`, rapports) dans un dossier système caché et local :
`C:\Users\webma\.gemini\antigravity-ide\brain\<conversation-id>\`
- **Volatilité** : Ce "Brain" est attaché à une session (conversation ID). Si l'utilisateur lance une nouvelle conversation ou change d'IDE, ce Brain est perdu/inaccessible.
- **Usage** : Il sert uniquement aux brouillons de session, aux plans d'implémentation temporaires et à l'historique interactif.

## 3. Le Transfert de Connaissance
Puisque le Brain de l'IDE est volatil et isolé, **l'agent ne doit jamais présumer qu'un artefact généré dans son propre Brain sera lu par la prochaine instance**.

Lorsqu'une session se termine ou qu'un point de sauvegarde est atteint, l'agent DOIT transférer les informations vitales du Brain de l'IDE vers le cerveau Hephaistos :
1. Mettre à jour `docs/DEVBOOK-PROGRESS-v0.6.md`.
2. Ajouter les prochaines étapes dans la liste `todo` du `.agent/consciousness_manifest.json`.
3. Optionnellement, créer des fichiers Markdown dans `docs/reports/` si de longs manifestes d'architecture ont été générés.

Le respect de cette dualité garantit que l'IA ne "perd jamais la mémoire" d'un jour à l'autre.
