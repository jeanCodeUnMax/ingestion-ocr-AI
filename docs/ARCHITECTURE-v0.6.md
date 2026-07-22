# Architecture — OCR AI System v0.6

## Isolation par projet

Un `ProjectManifest` contient l’instruction globale, la recette par défaut, le propriétaire et la liste explicite de ses documents. Le chat calcule ses résultats uniquement sur cette liste. La base vectorielle peut être commune physiquement, mais le filtre logique de projet est obligatoire.

## Entrées

```text
upload simple
upload multiple
texte collé
URL HTTP(S)
```

Toutes les entrées deviennent un fichier source puis passent par le normaliseur canonique.

## Recette

Les couches sont activables séparément : sémantique, maïeutique, KENT, pseudocode, synthèse, shrink, faits atomiques, tags et embeddings. Les artefacts désactivés ne sont pas exportés ni indexés.

## Enrichissement

Le moteur produit des dérivés non destructifs :

- `shrink.jsonl` : condensation liée au chunk source ;
- `atomic_facts.jsonl` : fait ou affirmation avec `sourceChunkIds` ;
- `tags.json` et `taxonomy.json` ;
- `knowledge_map.json` ;
- `index.md`.

La transcription originale reste la référence.

## Chat RAG

1. embedding de la question ;
2. recherche uniquement sur les `documentIds` du projet ;
3. reclassement privilégiant faits atomiques, shrink et chunks sources ;
4. déduplication ;
5. réponse extractive ou LLM ;
6. citations document/page/chunk ;
7. journalisation dans `chat/conversations.jsonl`.

## Sécurité

- défense SSRF sur syntaxe URL, DNS, IP et redirections ;
- document traité comme contenu non fiable ;
- vérification d’accès projet/document ;
- auth, multi-tenant et billing feature-gated ;
- manifestes et écritures atomiques.
