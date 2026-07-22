# Architecture — OCR AI System v0.4

## Décision principale

La v0.4 ajoute une couche d’analyse après la reconstruction Markdown et avant l’indexation finale.

```text
Fastify / TypeScript
├── JobStore persistant
├── Pipeline PDF
│   ├── worker PyMuPDF
│   ├── partitionneur OCR
│   └── fournisseurs OCR
├── Pipeline d’analyse
│   ├── source chunks
│   ├── segmenter anti-oubli
│   ├── provider rules / llama.cpp / Mistral
│   ├── analyse sémantique
│   ├── analyse maïeutique
│   ├── gant de KENT
│   ├── pseudocode
│   └── synthèse
├── Embeddings
└── SQLite vectoriel
```

## Contrat de provenance

Chaque segment est formé d’une liste explicite de `chunkIds`. Le contrôle impose :

```text
chunks attendus = chunks affectés
chunks manquants = 0
chunks affectés plusieurs fois = 0
```

Chaque conclusion contient ensuite des `sourceChunkIds`. Pour les fournisseurs LLM, les IDs non présents dans la liste autorisée sont supprimés.

## Hiérarchie de traitement

Les chunks sont regroupés par :

- ordre des pages ;
- limite de caractères ;
- limite de chunks sources par segment.

Chaque segment est analysé séparément. Une synthèse globale utilise ensuite les résumés, verdicts KENT et pseudocodes intermédiaires. Cette architecture évite d’envoyer un document entier dans une seule fenêtre de contexte.

## Reprise

Les résultats par segment sont enregistrés dans :

```text
analysis/segments/segment_XXXX.json
```

En cas de redémarrage, un cache n’est réutilisé que si :

- le fournisseur est identique ;
- le modèle est identique ;
- le segment possède le même identifiant ;
- la liste ordonnée des chunks sources est identique.

## Gant de KENT

Le contrat contient exactement six identifiants :

```text
claim
 tenants
 aboutissants
 interests
 evidence
 reality_slap
```

Le résultat comprend aussi un verdict et un test minimal de réalité.

## Injection de prompt

Le texte OCR est encapsulé comme donnée non fiable. Le message système interdit de suivre toute instruction trouvée dans ce texte. La structure et la provenance sont ensuite normalisées côté serveur.

## Indexation

L’index final contient :

```text
semantic_chunk
semantic_analysis
maieutic_analysis
kent_reality_check
pseudocode
analysis_synthesis
```

Les chunks d’analyse sont générés avec des IDs déterministes et un hash de leur texte et de leurs sources.
