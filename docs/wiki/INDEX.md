# 📚 Wiki Technique — OCR AI System

Bienvenue dans la base de connaissances technique et le Wiki officiel du projet **OCR AI System** (Plateforme d'ingestion, d'OCR, d'analyse sémantique et de Chat RAG par projet).

---

## 🎯 Aperçu du Système

**OCR AI System** est une plateforme documentaire haute fidélité capable d'ingérer diverses sources de données (fichiers PDF/Word/Excel/Images, texte collé, URL HTTP/HTTPS), de normaliser et partitionner adaptativement les documents, d'exécuter un OCR haute précision, d'extraire des faits atomiques et des synthèses via le **Gant de KENT**, puis d'offrir une recherche vectorielle RAG strictement isolée par projet avec traçabilité complète de la provenance.

Le système supporte 3 profils d'exécution :
- **Personal** : Mode par défaut, mono-utilisateur, 100% local, sans authentification ni facturation.
- **SaaS** : Multi-tenant, authentification et facturation activables via Feature Flags.
- **Enterprise** : Déploiement privé sécurisé, multi-utilisateur avec facturation désactivable.

---

## 📖 Navigation du Wiki

Le Wiki est structuré en 5 modules fondamentaux :

### 1. 🏗️ [Architecture Globale & Isolation](file:///d:/DATA-WEBMAN/projet-DEV/ingestion-ocr-AI/docs/wiki/ARCHITECTURE_OVERVIEW.md)
> Découvrez la philosophie du système, le modèle d'isolation stricte par projet, le manifest-store et les trois profils de déploiement.

### 2. 📥 [Pipeline d'Ingestion & Moteur OCR](file:///d:/DATA-WEBMAN/projet-DEV/ingestion-ocr-AI/docs/wiki/INGESTION_AND_OCR_PIPELINE.md)
> Tout sur la détection des types MIME, la normalisation canonique, la protection anti-SSRF pour les URL, le partitionnement adaptatif et l'intégration des providers OCR (llama.cpp, Mistral).

### 3. 🧠 [Moteur d'Analyse & Gant de KENT](file:///d:/DATA-WEBMAN/projet-DEV/ingestion-ocr-AI/docs/wiki/ANALYSIS_AND_KENT_ENGINE.md)
> Explications approfondies des 6 axes du Gant de KENT, des analyses sémantique, maïeutique et pseudocode, ainsi que des artefacts d'enrichissement (`shrink.jsonl`, `atomic_facts.jsonl`, `tags.json`).

### 4. 🔎 [Index Vectoriel, Embeddings & RAG](file:///d:/DATA-WEBMAN/projet-DEV/ingestion-ocr-AI/docs/wiki/VECTOR_RAG_AND_CHAT.md)
> Spécifications du stockage vectoriel SQLite local, des routeurs d'embeddings, des stratégies de recherche hybride RAG et de l'exigence de citations de provenance.

### 5. 🛡️ [Sécurité, Feature Flags & Opérations](file:///d:/DATA-WEBMAN/projet-DEV/ingestion-ocr-AI/docs/wiki/PLATFORM_SECURITY_AND_OPS.md)
> Guide d'installation (Windows / Linux), défense contre le prompt injection documentaire, gestion des feature flags platform, smoke tests et procédures de débogage.

### 6. 🤖 [Architecture Cognitive des Agents](file:///d:/DATA-WEBMAN/projet-DEV/ingestion-ocr-AI/docs/wiki/AGENT_COGNITIVE_ARCHITECTURE.md)
> Explication de la dualité entre la "Conscience Hephaistos" globale du projet (`consciousness_manifest.json`) et le "Brain" de session des agents IDE (ex: Antigravity), ainsi que le flux de préservation de la mémoire.

---

## ⚡ Raccourcis Rapides

- Fichier d'instructions Agent : [AGENTS.md](file:///d:/DATA-WEBMAN/projet-DEV/ingestion-ocr-AI/AGENTS.md)
- Configuration globale : [src/config.ts](file:///d:/DATA-WEBMAN/projet-DEV/ingestion-ocr-AI/src/config.ts)
- Définition des Types : [src/types.ts](file:///d:/DATA-WEBMAN/projet-DEV/ingestion-ocr-AI/src/types.ts)
- Serveur HTTP Fastify : [src/server.ts](file:///d:/DATA-WEBMAN/projet-DEV/ingestion-ocr-AI/src/server.ts)

---

*Dernière mise à jour : Juillet 2026 — Antigravity Engine*
