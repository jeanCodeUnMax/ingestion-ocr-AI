# DevBook — progression v0.4

## Epic A — Analyse sémantique

- [x] segmentation adaptative des chunks ;
- [x] couverture sans oubli ni doublon ;
- [x] thèmes, concepts, entités, affirmations, relations ;
- [x] faits et incertitudes ;
- [x] sorties JSON et Markdown ;
- [x] provenance par `sourceChunkIds`.

## Epic B — Analyse maïeutique

- [x] problème central ;
- [x] finalité ;
- [x] essence ;
- [x] présupposés ;
- [x] questions implicites ;
- [x] ambiguïtés et tensions ;
- [x] causes et conséquences ;
- [x] questions essentielles.

## Epic C — Gant de KENT

- [x] contrat fixe à six questions ;
- [x] tenants et aboutissants ;
- [x] intérêts et porteurs de risques ;
- [x] preuves et contre-exemples ;
- [x] gifle de la réalité ;
- [x] verdict prudent ;
- [x] test minimal mesurable ;
- [x] critères de succès et d’échec.

## Epic D — Pseudocode

- [x] objectif ;
- [x] entrées et sorties ;
- [x] préconditions et invariants ;
- [x] étapes sourcées ;
- [x] exceptions ;
- [x] tests d’acceptation ;
- [x] bloc pseudocode exportable.

## Epic E — Providers

- [x] moteur déterministe `rules` ;
- [x] adaptateur llama.cpp compatible OpenAI ;
- [x] adaptateur Mistral chat ;
- [x] réponse JSON ;
- [x] filtrage des IDs de provenance ;
- [x] défense contre les instructions présentes dans le document ;
- [ ] benchmark réel llama.cpp ;
- [ ] benchmark réel Mistral.

## Epic F — Indexation

- [x] indexation des transcriptions ;
- [x] indexation des cinq familles d’analyse ;
- [x] IDs déterministes ;
- [x] recherche des résultats KENT ;
- [x] compte séparé transcription/analyse dans le manifeste.

## Epic G — Interface et API

- [x] sélection du fournisseur d’analyse ;
- [x] progression des segments ;
- [x] liens synthèse, KENT et pseudocode ;
- [x] routes Markdown et JSON ;
- [x] santé des providers.

## Prochaine branche pressentie

v0.5 :

- perspectives expertes optionnelles ;
- traduction ;
- shrink contrôlé ;
- tags et taxonomie ;
- export ZIP complet ;
- amélioration du workspace visuel.
