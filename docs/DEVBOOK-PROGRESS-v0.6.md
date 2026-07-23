# DevBook — progression v0.6

## Epic Projets
- [x] création et modification ;
- [x] workspace parent ;
- [x] index projet ;
- [x] rattachement explicite des documents ;
- [x] isolation du chat ;
- [x] export et import ZIP portable avec restauration complète.

## Epic Ingestion
- [x] fichiers multiples ;
- [x] texte collé ;
- [x] URL HTML ou fichier ;
- [x] protection SSRF ;
- [x] SVG ;
- [x] benchmark audio réel.

## Epic Recettes
- [x] quick ;
- [x] standard ;
- [x] deep ;
- [x] custom ;
- [x] filtrage des artefacts et embeddings.

## Epic Knowledge
- [x] shrink sourcé ;
- [x] faits atomiques ;
- [x] tags ;
- [x] taxonomie ;
- [x] knowledge map ;
- [x] index Markdown ;
- [x] embedding des dérivés.

## Epic Chat
- [x] recherche par projet ;
- [x] citations ;
- [x] mode extractif local ;
- [x] mode llama.cpp ;
- [x] mode Mistral ;
- [x] historique JSONL ;
- [x] évaluation qualitative des réponses LLM et des citations.

## Epic Diagnostics & Benchmarks
- [x] diagnostics de santé avancés des providers avec latence RTT ;
- [x] calcul des métriques OCR (CER et WER) ;
- [x] métriques RAG (Recall@k et MRR).

## Epic Plateforme
- [x] auth préparée ;
- [x] multi-tenant préparé ;
- [x] billing préparé ;
- [x] désactivation par défaut ;
- [ ] tests de charge SaaS ;
- [x] Qdrant / pgvector (interface pluggable & routeur).
- [ ] quotas et abonnements réels.

## 🛑 Bilan pour Reprise (Fin de session 23/07/2026)
1. **Pipeline Python OCR corrigé** : `PYTHON_BIN=.venv/Scripts/python.exe` injecté dans `.env`. La normalisation (jusqu'à 60%) fonctionne !
2. **Erreur restante (Fetch Failed)** : L'application tente de joindre `llama-cpp` sur `127.0.0.1:8080`.
3. **Première action à faire demain** : Mettre `OCR_PROVIDER=none`, `EMBEDDING_PROVIDER=hash` et `ANALYSIS_PROVIDER=rules` dans le `.env` pour simuler le LLM, et uploader un document pour vérifier que ça atteint `complete` (100%).
4. **Tester le Chat RAG** : Vérifier que la recherche vectorielle (Cosine Similarity via SQLite) remonte bien les fragments.
