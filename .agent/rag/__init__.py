"""
RAG Module - Retrieval-Augmented Generation pour Hephaistos-Kit

Ce module implémente un système RAG modulaire avec double indexation vectorielle
(Qdrant + Zvec) permettant des recherches hybrides combinant approche catégorielle
et sémantique.

Modules:
    - chunker: Découpage intelligent de documents
    - tagger: Attribution de tags multi-dimensionnels
    - router: Routage dual vers Qdrant/Zvec
    - embedder: Génération des embeddings
    - fusion: Fusion des résultats de recherche
    - pipeline: Orchestration complète
    - neuronal_scorer: Scoring adaptatif avec apprentissage
    - feedback: Boucle de feedback utilisateur

Usage:
    from rag.pipeline import RAGPipeline
    
    pipeline = RAGPipeline()
    await pipeline.index_file("document.md")
    results = await pipeline.search("requete")
    
    # Avec scoring neuronal
    pipeline = RAGPipeline(enable_neuronal=True, db_path="memory.db")
    await pipeline.submit_feedback("doc_123", 0.8)
"""

__version__ = "2.0.0"
__author__ = "Hephaistos-Kit Team"

from .chunker import Chunker, Chunk, ChunkType
from .tagger import Tagger, Tag, TagCategory
from .router import Router, RoutingDecision, StoreTarget
from .fusion import FusionEngine, SearchResult
from .pipeline import RAGPipeline
from .neuronal_scorer import NeuronalScoringEngine, WeightSnapshot
from .feedback import FeedbackLoop, FeedbackEntry, FeedbackType

__all__ = [
    "Chunker",
    "Chunk",
    "ChunkType",
    "Tagger",
    "Tag",
    "TagCategory",
    "Router",
    "RoutingDecision",
    "StoreTarget",
    "FusionEngine",
    "SearchResult",
    "RAGPipeline",
    "NeuronalScoringEngine",
    "WeightSnapshot",
    "FeedbackLoop",
    "FeedbackEntry",
    "FeedbackType",
]
