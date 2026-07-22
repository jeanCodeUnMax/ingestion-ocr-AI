# OCR AI System v0.6

Plateforme documentaire de type chat/RAG organisée par **projets isolés**.

## Fonctionnalités de la v0.6

- projets séparés avec instruction et recette par défaut ;
- import d’un ou plusieurs fichiers ;
- texte collé transformé en document ;
- téléchargement d’une URL HTTP(S) avec protection SSRF ;
- PDF, Word, Excel, CSV, JSON, Markdown, texte, images matricielles et SVG ;
- OCR local via llama.cpp ou API Mistral ;
- découpage adaptatif et manifeste anti-oubli ;
- analyses sémantique, maïeutique, gant de KENT et pseudocode ;
- profils `quick`, `standard`, `deep` et recette personnalisée ;
- shrink non destructif ;
- faits atomiques key/value avec provenance ;
- tags, taxonomie, `index.md` et `knowledge_map.json` ;
- embeddings et index vectoriel SQLite ;
- chat RAG limité aux documents du projet avec citations ;
- authentification, multi-tenant et facturation présents derrière des feature flags, désactivés par défaut.

## Architecture

```text
Projet
├── fichiers multiples
├── texte collé
├── URL sécurisée
└── instruction + recette
        ↓
Normalisation PDF + Markdown canonique
        ↓
Inventaire exhaustif et découpage adaptatif
        ↓
Extraction native / OCR vision
        ↓
Analyses configurables
        ↓
Shrink + faits atomiques + tags + taxonomie
        ↓
Embeddings SQLite
        ↓
Chat RAG sourcé, limité au projet
```

## Installation

Prérequis : Node.js 22.5+, Python 3.11+.

```powershell
cd ocr-ai-system-v0.6
npm install
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
npm run check
npm start
```

Ouvrir `http://127.0.0.1:8000`.

## Preuve locale sans API

```env
DEPLOYMENT_MODE=personal
OCR_PROVIDER=none
EMBEDDING_PROVIDER=hash
ANALYSIS_PROVIDER=rules
TRANSLATION_PROVIDER=none
FEATURE_AUTH=false
FEATURE_BILLING=false
FEATURE_MULTI_TENANT=false
```

Puis :

```powershell
npm start
node scripts/smoke-test-v06.mjs http://127.0.0.1:8000
```

## Profils de traitement

- `quick` : sémantique, synthèse, shrink, tags, embeddings ;
- `standard` : ajoute maïeutique, KENT, pseudocode et faits atomiques ;
- `deep` : profil complet, traduction activable ;
- `custom` : interrupteur indépendant pour chaque couche.

Une recette complète ressemble à :

```json
{
  "profile": "custom",
  "semanticAnalysis": true,
  "maieuticAnalysis": true,
  "kentRealityCheck": true,
  "pseudocode": true,
  "synthesis": true,
  "shrink": true,
  "atomicFacts": true,
  "tagsAndTaxonomy": true,
  "embeddings": true,
  "visualDescriptions": true,
  "translation": false
}
```

## API principale

```text
POST /api/projects
GET  /api/projects
GET  /api/projects/:projectId
PATCH /api/projects/:projectId
POST /api/projects/:projectId/documents
POST /api/projects/:projectId/documents/text
POST /api/projects/:projectId/documents/url
POST /api/projects/:projectId/chat
GET  /api/projects/:projectId/workspace
```

Les anciennes routes `/api/documents` restent disponibles.

## Workspace projet

```text
projects/<projectId>/
├── project.json
├── index.md
├── knowledge/project_map.json
├── chat/conversations.jsonl
└── exports/
```

Chaque document conserve son workspace indépendant :

```text
workspaces/<documentId>/
├── source/
├── transcription/
├── analysis/
├── shrink/
│   ├── shrink.jsonl
│   └── atomic_facts.jsonl
├── tags/
├── embeddings/
├── index.md
├── knowledge_map.json
└── manifest.json
```

## Sécurité URL

Le collecteur refuse :

- `file://`, FTP et protocoles non HTTP(S) ;
- identifiants intégrés dans l’URL ;
- `localhost` et domaines `.local` ;
- IP privées, loopback et link-local ;
- redirections vers une adresse privée ;
- réponse dépassant la taille configurée.

La conversion HTML actuelle est volontairement simple. Une future version pourra intégrer un extracteur de contenu principal plus sophistiqué.

## Déploiements

### Personnel

```env
DEPLOYMENT_MODE=personal
FEATURE_AUTH=false
FEATURE_BILLING=false
FEATURE_MULTI_TENANT=false
```

### SaaS préparé

```env
DEPLOYMENT_MODE=saas
FEATURE_AUTH=true
FEATURE_MULTI_TENANT=true
FEATURE_BILLING=true
AUTH_TOKEN_SECRET=une-cle-longue-et-secrete
```

### Entreprise locale

```env
DEPLOYMENT_MODE=enterprise
FEATURE_AUTH=true
FEATURE_MULTI_TENANT=true
FEATURE_BILLING=false
```

## Limites connues

- l’embedding `hash` et l’analyse `rules` servent de preuve technique, pas de modèle de production ;
- les connecteurs llama.cpp et Mistral doivent être benchmarkés sur la machine cible ;
- SQLite vectoriel convient au mode personnel et aux prototypes ; pgvector ou Qdrant restent à ajouter pour une forte volumétrie ;
- l’audio nécessite Mistral ou whisper.cpp ;
- le chat `rules` est extractif ; un modèle llama.cpp ou Mistral produit une réponse plus naturelle, toujours contrainte par les citations.
