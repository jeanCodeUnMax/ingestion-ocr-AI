"""
Pipeline Module - Orchestration complète du système RAG

Ce module implémente le pipeline principal qui coordonne tous les
composants RAG: chunking, tagging, routing, embedding et fusion.

Classes:
    - RAGPipeline: Pipeline principal d'indexation et recherche
"""

from typing import List, Dict, Any, Optional, Iterable
from pathlib import Path
import json
import asyncio
import fnmatch
import argparse
import sys

# Support exécution en script direct (python pipeline.py) sans package.
from pathlib import Path
import sys

# Support exécution en script direct ou en tant que package
# On ajoute le dossier courant au sys.path pour aider Pylance et l'exécution directe
base_dir = Path(__file__).resolve().parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

try:
    from chunker import Chunker, Chunk, ChunkType
    from tagger import Tagger, Tag, TagCategory
    from router import Router, RoutingDecision, StoreTarget
    from embedder import EmbedderManager
    from fusion import FusionEngine, SearchResult
    from neuronal_scorer import NeuronalScoringEngine
    from feedback import FeedbackLoop
    from utils.env_loader import merge_config_with_env, get_workspace_root
except ImportError:
    # Fallback pour imports relatifs si lancé en tant que module
    from .chunker import Chunker, Chunk, ChunkType
    from .tagger import Tagger, Tag, TagCategory
    from .router import Router, RoutingDecision, StoreTarget
    from .embedder import EmbedderManager
    from .fusion import FusionEngine, SearchResult
    from .neuronal_scorer import NeuronalScoringEngine
    from .feedback import FeedbackLoop
    from .utils.env_loader import merge_config_with_env, get_workspace_root


class RAGPipeline:
    """
    Pipeline principal RAG
    
    Orchestre le flux complet d'indexation et de recherche:
    1. Chunking: Découpage intelligent du document
    2. Tagging: Attribution de tags multi-dimensionnels
    3. Routing: Détermination des stores cibles
    4. Embedding: Génération et stockage des embeddings
    5. Memory: Stockage des relations dans Memory MCP
    6. Feedback: Apprentissage continu (optionnel)
    
    Attributes:
        config: Configuration complète
        config_path: Chemin du fichier de configuration
        chunker: Module de chunking
        tagger: Module de tagging
        router: Module de routage
        embedder: Gestionnaire d'embeddings
        fusion: Moteur de fusion
        neuronal_engine: Moteur de scoring neuronal (optionnel)
        feedback_loop: Boucle de feedback (optionnel)
    
    Example:
        >>> pipeline = RAGPipeline()
        >>> report = await pipeline.index_file("document.md")
        >>> results = await pipeline.search("requete")
    """
    
    def __init__(self, config_path: str = None, enable_neuronal: bool = False, db_path: str = None):
        """
        Initialise le pipeline RAG
        
        Args:
            config_path: Chemin vers le fichier de configuration.
                        Par défaut: .agent/rag/config.json
            enable_neuronal: Activer le scoring neuronal adaptatif
            db_path: Chemin vers la DB SQLite pour persistance
        """
        # Charger la configuration
        if config_path is None:
            config_path = str(Path(__file__).parent / "config.json")
        
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.db_path = db_path
        
        # Initialiser le moteur neuronal si activé
        self.neuronal_engine = None
        self.feedback_loop = None
        
        if enable_neuronal and db_path:
            self.neuronal_engine = NeuronalScoringEngine(db_path=db_path)
            self.feedback_loop = FeedbackLoop(self.neuronal_engine, db_path=db_path)
        
        # Initialiser les composants
        self.chunker = Chunker(self.config)
        self.tagger = Tagger(self.config)
        self.router = Router(self.config)
        self.embedder = EmbedderManager(self.config)
        self.fusion = FusionEngine(self.config, neuronal_engine=self.neuronal_engine)
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Charge la configuration depuis un fichier JSON
        
        Les variables d'environnement ont priorité sur le JSON.
        
        Args:
            config_path: Chemin du fichier
            
        Returns:
            Configuration fusionnée avec les variables d'environnement
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except FileNotFoundError:
            print(f"Warning: Config non trouvée à {config_path}, utilisation des défauts")
            config = self._default_config()
        except json.JSONDecodeError as e:
            print(f"Warning: Erreur JSON dans config: {e}, utilisation des défauts")
            config = self._default_config()
        
        # Fusionner avec les variables d'environnement
        config = merge_config_with_env(config)
        
        return config
    
    def _default_config(self) -> Dict[str, Any]:
        """
        Retourne une configuration par défaut
        
        Returns:
            Configuration par défaut
        """
        return {
            "chunking": {
                "default_size": 300,
                "overlap_percent": 10,
                "min_chunk_size": 50,
                "max_chunk_size": 1000,
                "types": {
                    "atomic": {"min": 50, "max": 100},
                    "modular": {"min": 200, "max": 500},
                    "contextual": {"min": 500, "max": 1000},
                    "structural": {"min": 100, "max": 2000}
                }
            },
            "tagging": {
                "auto_detect": True,
                "min_confidence": 0.7,
                "max_tags_per_chunk": 10
            },
            "routing": {
                "strategy": "dual",
                "fallback": "both"
            },
            "embedding": {
                "qdrant": {"enabled": True, "dimensions": 1536, "collections": {}},
                "zvec": {"enabled": True, "dimensions": 384, "collections": {}}
            },
            "fusion": {
                "weights": {"qdrant": 0.4, "zvec": 0.4, "memory": 0.2},
                "max_results": 20,
                "min_results": 5,
                "deduplication": True
            }
        }
    
    async def ingest_workspace(
        self,
        root_path: Optional[str] = None,
        include_ext: Iterable[str] = (".md", ".txt", ".py", ".json", ".yaml", ".yml"),
        exclude_globs: Iterable[str] = (
            "**/.git/**",
            "**/.venv/**",
            "**/venv/**",
            "**/__pycache__/**",
            "**/.trae/**",
            "**/.windsurf/**",
        ),
    ) -> Dict[str, Any]:
        """
        Indexe récursivement les fichiers du workspace.

        Chemins strictement relatifs (aucun chemin absolu n'est construit).
        """

        root = Path(root_path) if root_path else get_workspace_root()
        report: Dict[str, Any] = {
            "status": "success",
            "files_indexed": 0,
            "errors": [],
            "details": [],
        }

        def _is_excluded(p: Path) -> bool:
            rel = str(p)
            return any(fnmatch.fnmatch(rel, pattern) for pattern in exclude_globs)

        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in include_ext:
                continue
            if _is_excluded(file_path):
                continue
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(file_path.relative_to(root))
                doc_type = self._guess_doc_type(file_path.suffix.lower())
                res = await self.index_document(
                    content=content,
                    doc_type=doc_type,
                    source_file=rel_path,
                    metadata={"source": "workspace", "relative_path": rel_path},
                )
                report["files_indexed"] += 1
                report["details"].append({"file": rel_path, "chunks": res.get("chunks_created", 0)})
            except Exception as e:
                report["status"] = "error" if report["files_indexed"] == 0 else "partial"
                report["errors"].append(f"{file_path}: {e}")
                print(f"[!] Erreur critique sur {file_path}: {e}")

        return report

    def _guess_doc_type(self, suffix: str) -> str:
        if suffix in {".py", ".js", ".ts", ".tsx", ".jsx"}:
            return "code"
        if suffix in {".md", ".markdown"}:
            return "markdown"
        if suffix in {".json", ".yaml", ".yml"}:
            return "json"
        return "text"

    async def index_document(
        self,
        content: str,
        doc_type: str = "text",
        source_file: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Indexe un document complet
        
        Args:
            content: Contenu du document
            doc_type: Type de document (text, code, markdown, json)
            source_file: Fichier source optionnel
            metadata: Métadonnées additionnelles
            
        Returns:
            Rapport d'indexation
        """
        report = {
            "status": "success",
            "chunks_created": 0,
            "tags_generated": 0,
            "qdrant_stored": 0,
            "zvec_stored": 0,
            "memory_relations": 0,
            "errors": [],
            "chunks": []
        }
        
        try:
            # 1. Chunking
            chunks = self.chunker.chunk_document(
                content=content,
                doc_type=doc_type,
                source_file=source_file
            )
            report["chunks_created"] = len(chunks)
            
            # 2. Traitement de chaque chunk
            for chunk in chunks:
                try:
                    chunk_report = await self._process_chunk(
                        chunk=chunk,
                        metadata=metadata
                    )
                    
                    report["tags_generated"] += chunk_report.get("tags_count", 0)
                    report["qdrant_stored"] += chunk_report.get("qdrant_stored", 0)
                    report["zvec_stored"] += chunk_report.get("zvec_stored", 0)
                    report["memory_relations"] += chunk_report.get("memory_relations", 0)
                    report["chunks"].append(chunk_report)
                    
                except Exception as e:
                    report["errors"].append(f"Chunk {chunk.id}: {str(e)}")
            
        except Exception as e:
            report["status"] = "error"
            report["errors"].append(str(e))
        
        return report
    
    async def _process_chunk(
        self,
        chunk: Chunk,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Traite un chunk individuel
        
        Args:
            chunk: Chunk à traiter
            metadata: Métadonnées additionnelles
            
        Returns:
            Rapport de traitement du chunk
        """
        report = {
            "chunk_id": chunk.id,
            "tags_count": 0,
            "qdrant_stored": 0,
            "zvec_stored": 0,
            "memory_relations": 0,
            "routing": None
        }
        
        # 1. Tagging
        tags = self.tagger.tag_chunk(chunk)
        report["tags_count"] = len(tags)
        
        # ENRICHISSEMENT DU SHRINK: Injection des tags et d'un court résumé dans le vecteur texte
        domain_tag = next((t.value for t in tags if t.key == "domain"), "général")
        semantic_tags = [t.value for t in tags if t.category.value == "semantique"]
        tags_str = ", ".join(semantic_tags) if semantic_tags else "divers"
        
        # Court résumé tiré des premières phrases significatives du shrink
        content_lines = [l.strip() for l in chunk.content.split('\n') if l.strip() and not l.startswith('[[')]
        short_summary = content_lines[0][:100] + "..." if content_lines else "Données techniques"
        
        enrichment_header = f"[[ DOMAINE: {domain_tag} | TAGS: {tags_str} | RÉSUMÉ: {short_summary} ]]\n"
        if "[[ DOMAINE:" not in chunk.content:
            chunk.content = enrichment_header + chunk.content
        
        # 2. Routing
        routing = self.router.route(chunk, tags)
        report["routing"] = routing.to_dict()
        
        # 3. Préparer les métadonnées
        chunk_metadata = {
            **(metadata or {}),
            **chunk.metadata,
            "tags": [t.to_dict() for t in tags],
            "routing": routing.to_dict(),
            "source_file": chunk.source_file,
            "chunk_type": chunk.type.value
        }
        
        # 4. Stockage Qdrant
        if routing.should_index_qdrant():
            for collection in routing.qdrant_collections:
                success = await self.embedder.qdrant.store(
                    collection=collection,
                    chunk_id=chunk.id,
                    content=chunk.content,
                    metadata=chunk_metadata
                )
                if success:
                    report["qdrant_stored"] += 1
        
        # 5. Stockage Zvec
        if routing.should_index_zvec():
            for collection in routing.zvec_collections:
                success = await self.embedder.zvec.store(
                    collection=collection,
                    chunk_id=chunk.id,
                    content=chunk.content,
                    metadata=chunk_metadata
                )
                if success:
                    report["zvec_stored"] += 1
        
        # 6. Memory MCP (relations)
        await self._store_memory_relations(chunk, tags)
        report["memory_relations"] = 1
        
        return report
    
    async def _store_memory_relations(self, chunk: Chunk, tags: List[Tag]) -> None:
        """
        Stocke les relations riches (structurelles et sémantiques) dans Memory MCP
        """
        import httpx
        
        url_base = self.config.get("memory_mcp", {}).get("url", "http://localhost:8002")
        
        try:
            async with httpx.AsyncClient() as client:
                # 1. Préparer l'entité Chunk avec son contexte explicatif
                context_header = chunk.metadata.get("context_header", "Unité sémantique")
                entity_payload = {
                    "entities": [
                        {
                            "name": chunk.id,
                            "entityType": "chunk",
                            "observations": [
                                f"Contexte: {context_header}",
                                f"Fichier source: {chunk.source_file}",
                                f"Lignes: {chunk.line_start}-{chunk.line_end}",
                                f"Contenu partiel: {chunk.content[:500]}..."
                            ]
                        }
                    ]
                }
                
                # 2. Préparer l'entité Fichier Source (Parent)
                if chunk.source_file:
                    file_entity = {
                        "name": chunk.source_file,
                        "entityType": "file",
                        "observations": [f"Fichier indexé dans le workspace: {Path(chunk.source_file).name}"]
                    }
                    entity_payload["entities"].append(file_entity)
                
                await client.post(f"{url_base}/entities", json=entity_payload, timeout=5.0)
                
                # 3. Créer les relations structurelles et sémantiques
                relations = []
                
                # Relation Structurelle: Chunk -> Fichier
                if chunk.source_file:
                    relations.append({
                        "from": chunk.id,
                        "to": chunk.source_file,
                        "relationType": "contained_in"
                    })
                
                # Relations Sémantiques: Chunk -> Tags
                for tag in tags:
                    tag_name = f"{tag.key}:{tag.value}"
                    tag_entity = {
                        "name": tag_name, 
                        "entityType": "tag", 
                        "observations": [f"Catégorie: {tag.category.value}"]
                    }
                    await client.post(f"{url_base}/entities", json={"entities": [tag_entity]}, timeout=2.0)
                    
                    relations.append({
                        "from": chunk.id,
                        "to": tag_name,
                        "relationType": "associated_with"
                    })
                
                if relations:
                    await client.post(f"{url_base}/relations", json={"relations": relations}, timeout=5.0)
                                        
        except Exception as e:
            # On log l'erreur mais on ne bloque pas le pipeline (Memory est souvent optionnel/lent)
            print(f"Note: Erreur stockage Memory MCP (Ignoré): {e}")
    
    async def index_file(self, file_path: str) -> Dict[str, Any]:
        """
        Indexe un fichier
        
        Args:
            file_path: Chemin du fichier
            
        Returns:
            Rapport d'indexation
        """
        path = Path(file_path)
        
        # Vérifier l'existence
        if not path.exists():
            return {
                "status": "error",
                "errors": [f"Fichier non trouvé: {file_path}"]
            }
        
        # Détecter le type
        suffix = path.suffix.lower()
        type_map = {
            ".py": "code",
            ".js": "code",
            ".ts": "code",
            ".jsx": "code",
            ".tsx": "code",
            ".java": "code",
            ".go": "code",
            ".rs": "code",
            ".c": "code",
            ".cpp": "code",
            ".h": "code",
            ".md": "markdown",
            ".markdown": "markdown",
            ".json": "json",
            ".yaml": "config",
            ".yml": "config",
            ".toml": "config",
            ".ini": "config",
            ".env": "config",
            ".txt": "text",
            ".log": "log",
        }
        doc_type = type_map.get(suffix, "text")
        
        # Lire le contenu
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return {
                "status": "error",
                "errors": [f"Erreur lecture: {str(e)}"]
            }
        
        # Indexer
        return await self.index_document(
            content=content,
            doc_type=doc_type,
            source_file=str(path),
            metadata={
                "file_name": path.name,
                "file_extension": suffix,
                "file_size": path.stat().st_size if path.exists() else 0
            }
        )
    
    async def index_directory(
        self,
        dir_path: str,
        extensions: List[str] = None,
        exclude_patterns: List[str] = None
    ) -> Dict[str, Any]:
        """
        Indexe tous les fichiers d'un répertoire
        
        Args:
            dir_path: Chemin du répertoire
            extensions: Extensions à inclure (optionnel)
            exclude_patterns: Patterns à exclure (optionnel)
            
        Returns:
            Rapport d'indexation global
        """
        dir_path = Path(dir_path)
        
        if not dir_path.is_dir():
            return {
                "status": "error",
                "errors": [f"Répertoire non trouvé: {dir_path}"]
            }
        
        # Extensions par défaut
        if extensions is None:
            extensions = [
                ".py", ".js", ".ts", ".jsx", ".tsx",
                ".md", ".json", ".yaml", ".yml",
                ".txt"
            ]
        
        # Patterns d'exclusion par défaut
        if exclude_patterns is None:
            exclude_patterns = [
                "node_modules", ".git", "__pycache__",
                "dist", "build", ".venv", "venv"
            ]
        
        report = {
            "status": "success",
            "files_processed": 0,
            "files_failed": 0,
            "total_chunks": 0,
            "total_tags": 0,
            "errors": [],
            "files": []
        }
        
        # Parcourir les fichiers
        for file_path in dir_path.rglob("*"):
            # Vérifier l'extension
            if file_path.suffix.lower() not in extensions:
                continue
            
            # Vérifier les exclusions
            if any(pattern in str(file_path) for pattern in exclude_patterns):
                continue
            
            # Indexer le fichier
            file_report = await self.index_file(str(file_path))
            
            if file_report.get("status") == "success":
                report["files_processed"] += 1
                report["total_chunks"] += file_report.get("chunks_created", 0)
                report["total_tags"] += file_report.get("tags_generated", 0)
            else:
                report["files_failed"] += 1
            
            report["files"].append({
                "path": str(file_path),
                "status": file_report.get("status"),
                "chunks": file_report.get("chunks_created", 0)
            })
        
        return report
    
    async def search(
        self,
        query: str,
        collections: Optional[List[str]] = None,
        limit: int = 10,
        filters: Optional[Dict] = None
    ) -> List[SearchResult]:
        """
        Recherche hybride
        
        Args:
            query: Requête textuelle
            collections: Collections spécifiques (optionnel)
            limit: Nombre max de résultats
            filters: Filtres de métadonnées (optionnel)
            
        Returns:
            Résultats fusionnés
        """
        qdrant_collections = collections or list(self.embedder.qdrant.collections.values())
        zvec_collections = collections or list(self.embedder.zvec.collections.values())

        results = await self.embedder.search_dual(
            query=query,
            qdrant_collections=qdrant_collections,
            zvec_collections=zvec_collections,
            limit=limit
        )

        memory_relations = await self._get_memory_relations(query)

        fused_results = await self.fusion.fuse(
            qdrant_results=results.get("qdrant", []),
            zvec_results=results.get("zvec", []),
            memory_relations=memory_relations
        )

        return fused_results[:limit]

    async def _get_memory_relations(self, query: str) -> List[Dict]:
        """
        Récupère les relations depuis Memory MCP
        
        Args:
            query: Requête pour la recherche
            
        Returns:
            Liste de relations
        """
        import httpx
        url_base = self.config.get("memory_mcp", {}).get("url", "http://localhost:8002")
        
        try:
            async with httpx.AsyncClient() as client:
                # Recherche par similarité (si supporté par le bridge REST du MCP)
                response = await client.get(f"{url_base}/search?query={query}", timeout=5.0)
                if response.status_code == 200:
                    return response.json().get("results", [])
        except Exception as e:
            print(f"Erreur recherche Memory MCP: {e}")
        
        return []
    
    async def delete(self, chunk_id: str) -> Dict[str, Any]:
        """
        Supprime un chunk de tous les stores
        
        Args:
            chunk_id: ID du chunk
            
        Returns:
            Rapport de suppression
        """
        report = {
            "status": "success",
            "chunk_id": chunk_id,
            "qdrant_deleted": False,
            "zvec_deleted": False,
            "memory_deleted": False
        }
        
        # Supprimer des stores vectoriels
        report["qdrant_deleted"] = await self.embedder.qdrant.delete("all", chunk_id)
        report["zvec_deleted"] = await self.embedder.zvec.delete("all", chunk_id)
        
        # Supprimer de Memory MCP
        await self._delete_memory_entity(chunk_id)
        report["memory_deleted"] = True
        
        return report
    
    async def _delete_memory_entity(self, chunk_id: str) -> None:
        """
        Supprime l'entité de Memory MCP
        
        Args:
            chunk_id: ID du chunk
        """
        import httpx
        url_base = self.config.get("memory_mcp", {}).get("url", "http://localhost:8002")
        
        try:
            async with httpx.AsyncClient() as client:
                # 1. Supprimer l'entité par son nom (chunk_id)
                await client.request("DELETE", f"{url_base}/entities", json={"name": chunk_id}, timeout=5.0)
        except Exception as e:
            print(f"Erreur nettoyage Memory MCP: {e}")
            
        success = True
        return success
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques du pipeline
        
        Returns:
            Statistiques de configuration
        """
        stats = {
            "config_path": self.config_path,
            "chunking": {
                "default_size": self.chunker.chunking_config.get("default_size"),
                "overlap_percent": self.chunker.chunking_config.get("overlap_percent")
            },
            "tagging": {
                "min_confidence": self.tagger.tagging_config.get("min_confidence"),
                "max_tags": self.tagger.tagging_config.get("max_tags_per_chunk")
            },
            "embedding": {
                "qdrant_enabled": self.embedder.qdrant.enabled,
                "qdrant_dimensions": self.embedder.qdrant.dimensions,
                "zvec_enabled": self.embedder.zvec.enabled,
                "zvec_dimensions": self.embedder.zvec.dimensions
            },
            "fusion": {
                "weights": self.fusion.get_weights(),
                "neuronal_mode": self.fusion.neuronal_mode
            }
        }
        
        # Ajouter les stats neuronales si actives
        if self.neuronal_engine:
            stats["neuronal"] = {
                "weights": self.neuronal_engine.get_weights(),
                "feedback_count": self.neuronal_engine.feedback_count
            }
        
        
        # Ajouter les stats feedback si actives
        if self.feedback_loop:
            stats["feedback"] = self.feedback_loop.get_stats()
        
        
        return stats
    
    async def submit_feedback(
        self,
        interaction_id: str,
        rating: float,
        correction: str = None,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Soumet un feedback pour améliorer le système
        
        Args:
            interaction_id: ID de l'interaction
            rating: Score de satisfaction (-1.0 à 1.0)
            correction: Correction optionnelle
            context: Contexte de l'interaction
            
        Returns:
            Résultat du traitement du feedback
        """
        if not self.feedback_loop:
            return {"status": "error", "reason": "Feedback loop not enabled"}
        
        return await self.feedback_loop.process_feedback(
            interaction_id=interaction_id,
            rating=rating,
            correction=correction,
            context=context
        )
    
    def get_neuronal_weights(self) -> Dict[str, float]:
        """
        Retourne les poids neuronaux actuels
        
        Returns:
            Poids ou None si mode neuronal désactivé
        """
        if self.neuronal_engine:
            return self.neuronal_engine.get_weights()
        return None
    
    def reset_neuronal_weights(self) -> None:
        """Réinitialise les poids neuronaux aux valeurs par défaut"""
        if self.neuronal_engine:
            self.neuronal_engine.reset_weights()
    
    async def initialize(self) -> Dict[str, bool]:
        """
        Initialise toutes les collections vectorielles
        
        Returns:
            Résultats d'initialisation
        """
        return await self.embedder.initialize_collections()


# Fonction utilitaire pour créer un pipeline rapidement
def create_pipeline(config_path: str = None) -> RAGPipeline:
    """
    Crée un pipeline RAG
    
    Args:
        config_path: Chemin vers la configuration (optionnel)
        
    Returns:
        Instance de RAGPipeline
    """
    return RAGPipeline(config_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG Pipeline CLI (relative paths only)")
    parser.add_argument("command", choices=["ingest", "search"], help="Action à exécuter")
    parser.add_argument("--query", dest="query", help="Requête de recherche (search)")
    parser.add_argument("--root", dest="root", default=".", help="Racine workspace (ingest)")
    parser.add_argument("--limit", dest="limit", type=int, default=10, help="Limite résultats (search)")
    args = parser.parse_args()

    async def _main():
        pipeline = RAGPipeline()
        if args.command == "ingest":
            report = await pipeline.ingest_workspace(root_path=args.root)
            print(json.dumps(report, ensure_ascii=False, indent=2))
        elif args.command == "search":
            query = args.query or "test"
            import numpy as np
            class NpEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, np.ndarray):
                        return obj.tolist()
                    return super(NpEncoder, self).default(obj)
            
            results = await pipeline.search(query=query, limit=args.limit)
            formatted_results = []
            for r in results:
                # Conversion récursive en dictionnaire simple pour JSON
                if hasattr(r, "to_dict"):
                    res_dict = r.to_dict()
                    # S'assurer que le contenu (qui peut être un objet Chunk) est aussi converti
                    if "content" in res_dict and hasattr(res_dict["content"], "to_dict"):
                        res_dict["content"] = res_dict["content"].to_dict()
                    formatted_results.append(res_dict)
                else:
                    formatted_results.append(str(r))
            
            print(json.dumps(formatted_results, ensure_ascii=False, indent=2, cls=NpEncoder))

    asyncio.run(_main())
