# Rapport de validation — OCR AI System v0.4

## Tests automatisés

```text
12 tests
12 réussis
0 échec
```

Couverture testée :

- chunking stable ;
- contrôle de couverture documentaire ;
- détection des doublons ;
- reprise de jobs ;
- partitionnement OCR de 200 pages ;
- découpage selon le contexte ;
- recherche SQLite ;
- partitionnement de 200 chunks d’analyse ;
- six questions KENT dans l’ordre ;
- provenance KENT ;
- résistance du contrat à une instruction injectée ;
- création des cinq familles d’artefacts.

## Test HTTP de bout en bout

Configuration :

```env
OCR_PROVIDER=none
EMBEDDING_PROVIDER=hash
ANALYSIS_PROVIDER=rules
```

Résultat :

```json
{
  "pagesDetected": 3,
  "pagesSuccessful": 3,
  "analysisStatus": "complete",
  "segmentsExpected": 1,
  "segmentsCompleted": 1,
  "transcriptionChunks": 3,
  "analysisChunks": 5,
  "chunksEmbedded": 8,
  "documentStatus": "complete"
}
```

Contrat KENT observé :

```json
[
  "claim",
  "tenants",
  "aboutissants",
  "interests",
  "evidence",
  "reality_slap"
]
```

La recherche vectorielle retourne un chunk `kent_reality_check` pour une requête portant sur la gifle de la réalité.

## Ce qui n’est pas revendiqué

Les providers llama.cpp et Mistral compilent et disposent de contrats HTTP, mais ils n’ont pas été validés dans cet environnement contre un modèle local réel ou une clé Mistral réelle.

## Dépendances

```text
npm audit --omit=dev
0 vulnérabilité connue
```
