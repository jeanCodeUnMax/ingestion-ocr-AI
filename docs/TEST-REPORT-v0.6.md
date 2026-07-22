# Rapport de validation — OCR AI System v0.6

## Tests automatisés

```text
22 tests
22 réussis
0 échec
```

Nouveaux contrôles v0.6 :

- profils de recette ;
- isolation des projets ;
- shrink et faits atomiques avec provenance ;
- tags, taxonomie et index ;
- refus des URL privées ;
- conversion HTML ;
- chat RAG limité au projet.

## Smoke test HTTP

Scénario exécuté :

```text
création projet
→ texte collé
→ normalisation
→ analyse rules
→ shrink
→ 2 faits atomiques
→ 11 tags
→ 5 chunks de connaissance
→ embeddings
→ statut complete
→ question RAG avec citations
```

Résultat de couverture :

```json
{
  "pagesDetected": 1,
  "pagesSuccessful": 1,
  "missingPageIds": [],
  "duplicateLeafAssignments": [],
  "isComplete": true
}
```

## Ce qui reste à prouver

- qualité OCR llama.cpp et Mistral ;
- qualité sémantique sur corpus réel ;
- coût et temps par page ;
- charge multi-utilisateur ;
- robustesse de l’extraction HTML sur sites complexes ;
- qualité audio.
