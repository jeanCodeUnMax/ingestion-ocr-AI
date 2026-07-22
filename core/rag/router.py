"""
Router Module - Routage des chunks vers les stores vectoriels

Ce module implémente la logique de routage dual qui détermine
quels chunks doivent être indexés dans Qdrant (catégorique),
Zvec (sémantique) ou les deux.

Classes:
    - StoreTarget: Cibles de stockage (qdrant, zvec, both, none)
    - RoutingDecision: Décision de routage pour un chunk
    - Router: Logique de routage
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# Support exécution en script direct
try:
    from .chunker import Chunk
    from .tagger import Tag, TagCategory
except ImportError:
    base_dir = Path(__file__).resolve().parent
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))
    from chunker import Chunk
    from tagger import Tag, TagCategory


class StoreTarget(Enum):
    """
    Cibles de stockage vectoriel
    
    Détermine dans quel(s) store(s) un chunk sera indexé.
    """
    QDRANT = "qdrant"    # Indexation catégorique uniquement
    ZVEC = "zvec"        # Indexation sémantique uniquement
    BOTH = "both"        # Indexation dans les deux stores
    NONE = "none"        # Pas d'indexation


@dataclass
class RoutingDecision:
    """
    Décision de routage pour un chunk
    
    Attributes:
        chunk_id: ID du chunk
        target: Cible(s) de stockage
        qdrant_collections: Collections Qdrant cibles
        zvec_collections: Collections Zvec cibles
        reason: Raison du routage
        metadata: Métadonnées additionnelles
    """
    chunk_id: str
    target: StoreTarget
    qdrant_collections: List[str] = field(default_factory=list)
    zvec_collections: List[str] = field(default_factory=list)
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit la décision en dictionnaire
        
        Returns:
            Dictionnaire représentant la décision
        """
        return {
            "chunk_id": self.chunk_id,
            "target": self.target.value,
            "qdrant_collections": self.qdrant_collections,
            "zvec_collections": self.zvec_collections,
            "reason": self.reason,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RoutingDecision':
        """
        Crée une décision depuis un dictionnaire
        
        Args:
            data: Dictionnaire source
            
        Returns:
            Instance de RoutingDecision
        """
        return cls(
            chunk_id=data.get("chunk_id", ""),
            target=StoreTarget(data.get("target", "both")),
            qdrant_collections=data.get("qdrant_collections", []),
            zvec_collections=data.get("zvec_collections", []),
            reason=data.get("reason", ""),
            metadata=data.get("metadata", {})
        )
    
    def should_index_qdrant(self) -> bool:
        """
        Vérifie si le chunk doit être indexé dans Qdrant
        
        Returns:
            True si indexation Qdrant requise
        """
        return self.target in [StoreTarget.QDRANT, StoreTarget.BOTH]
    
    def should_index_zvec(self) -> bool:
        """
        Vérifie si le chunk doit être indexé dans Zvec
        
        Returns:
            True si indexation Zvec requise
        """
        return self.target in [StoreTarget.ZVEC, StoreTarget.BOTH]


class Router:
    """
    Logique de routage des chunks
    
    Le Router analyse les tags d'un chunk et détermine le meilleur
    routage vers les stores vectoriels en fonction des règles configurées.
    
    Attributes:
        config: Configuration complète du pipeline RAG
        routing_config: Configuration spécifique au routage
        embedding_config: Configuration des embeddings
    
    Example:
        >>> config = {"routing": {"strategy": "dual", ...}}
        >>> router = Router(config)
        >>> decision = router.route(chunk, tags)
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le router avec la configuration
        
        Args:
            config: Configuration complète du pipeline RAG
        """
        self.config = config
        self.routing_config = config.get("routing", {
            "strategy": "dual",
            "fallback": "both",
            "min_score": 0.5,
            "rules": {}
        })
        self.embedding_config = config.get("embedding", {
            "qdrant": {"collections": {}},
            "zvec": {"collections": {}}
        })
    
    def route(self, chunk: Chunk, tags: List[Tag]) -> RoutingDecision:
        """
        Détermine le routage d'un chunk
        
        Args:
            chunk: Chunk à router
            tags: Tags du chunk
            
        Returns:
            Décision de routage
        """
        # Séparer les tags par catégorie
        categorique_tags = [t for t in tags if t.category == TagCategory.CATEGORIQUE]
        semantique_tags = [t for t in tags if t.category == TagCategory.SEMANTIQUE]
        
        # Déterminer la cible
        target = self._determine_target(categorique_tags, semantique_tags)
        
        # Sélectionner les collections
        qdrant_collections = []
        zvec_collections = []
        
        if target in [StoreTarget.QDRANT, StoreTarget.BOTH]:
            qdrant_collections = self._select_qdrant_collections(categorique_tags, chunk)
        
        if target in [StoreTarget.ZVEC, StoreTarget.BOTH]:
            zvec_collections = self._select_zvec_collections(semantique_tags, chunk)
        
        # Construire la raison
        reason = self._build_reason(target, categorique_tags, semantique_tags)
        
        return RoutingDecision(
            chunk_id=chunk.id,
            target=target,
            qdrant_collections=qdrant_collections,
            zvec_collections=zvec_collections,
            reason=reason,
            metadata={
                "categorique_count": len(categorique_tags),
                "semantique_count": len(semantique_tags)
            }
        )
    
    def _determine_target(
        self,
        categorique_tags: List[Tag],
        semantique_tags: List[Tag]
    ) -> StoreTarget:
        """
        Détermine la cible de stockage
        
        Args:
            categorique_tags: Tags catégoriques
            semantique_tags: Tags sémantiques
            
        Returns:
            Cible de stockage
        """
        has_categorique = len(categorique_tags) > 0
        has_semantique = len(semantique_tags) > 0
        
        # Vérifier les règles explicites par type
        rules = self.routing_config.get("rules", {})
        
        for tag in categorique_tags:
            if tag.key == "type" and tag.value in rules:
                rule = rules[tag.value]
                qdrant_enabled = rule.get("qdrant", True)
                zvec_enabled = rule.get("zvec", True)
                
                if qdrant_enabled and zvec_enabled:
                    return StoreTarget.BOTH
                elif qdrant_enabled:
                    return StoreTarget.QDRANT
                elif zvec_enabled:
                    return StoreTarget.ZVEC
        
        # Vérifier les règles par domaine
        for tag in categorique_tags:
            if tag.key == "domain":
                # Certains domaines sont mieux adaptés à un store
                domain_routing = {
                    "frontend": StoreTarget.BOTH,
                    "backend": StoreTarget.BOTH,
                    "database": StoreTarget.QDRANT,
                    "devops": StoreTarget.QDRANT,
                    "security": StoreTarget.BOTH,
                    "testing": StoreTarget.QDRANT,
                    "ai": StoreTarget.BOTH,
                }
                if tag.value in domain_routing:
                    return domain_routing[tag.value]
        
        # Fallback basé sur la présence de tags
        if has_categorique and has_semantique:
            return StoreTarget.BOTH
        elif has_categorique:
            # Si uniquement catégorique, préférer Qdrant
            return StoreTarget.QDRANT
        elif has_semantique:
            # Si uniquement sémantique, préférer Zvec
            return StoreTarget.ZVEC
        else:
            # Aucun tag, utiliser le fallback configuré
            fallback = self.routing_config.get("fallback", "both")
            if fallback == "qdrant":
                return StoreTarget.QDRANT
            elif fallback == "zvec":
                return StoreTarget.ZVEC
            else:
                return StoreTarget.BOTH
    
    def _select_qdrant_collections(
        self,
        tags: List[Tag],
        chunk: Chunk
    ) -> List[str]:
        """
        Sélectionne les collections Qdrant appropriées
        
        Args:
            tags: Tags catégoriques
            chunk: Chunk à indexer
            
        Returns:
            Liste de collections Qdrant
        """
        collections = []
        qdrant_config = self.embedding_config.get("qdrant", {})
        collection_mapping = qdrant_config.get("collections", {})
        
        # Basé sur le type
        for tag in tags:
            if tag.key == "type" and tag.value in collection_mapping:
                collections.append(collection_mapping[tag.value])
        
        # Basé sur le type de document
        doc_type = chunk.metadata.get("doc_type", "text")
        type_to_collection = {
            "code": collection_mapping.get("code", "code_index"),
            "markdown": collection_mapping.get("doc", "doc_index"),
            "json": collection_mapping.get("config", "config_index"),
            "text": collection_mapping.get("doc", "doc_index"),
        }
        
        if doc_type in type_to_collection:
            collections.append(type_to_collection[doc_type])
        
        # Default si aucune collection trouvée
        if not collections:
            collections.append("doc_index")
        
        return list(set(collections))
    
    def _select_zvec_collections(
        self,
        tags: List[Tag],
        chunk: Chunk
    ) -> List[str]:
        """
        Sélectionne les collections Zvec appropriées
        
        Args:
            tags: Tags sémantiques
            chunk: Chunk à indexer
            
        Returns:
            Liste de collections Zvec
        """
        collections = []
        zvec_config = self.embedding_config.get("zvec", {})
        collection_mapping = zvec_config.get("collections", {})
        
        # Basé sur le concept
        for tag in tags:
            if tag.key == "concept":
                collections.append(collection_mapping.get("concepts", "concepts_index"))
            elif tag.key == "action":
                collections.append(collection_mapping.get("actions", "actions_index"))
            elif tag.key == "entity":
                collections.append(collection_mapping.get("entities", "entities_index"))
        
        # Default si aucune collection trouvée
        if not collections:
            collections.append(collection_mapping.get("concepts", "concepts_index"))
        
        return list(set(collections))
    
    def _build_reason(
        self,
        target: StoreTarget,
        categorique_tags: List[Tag],
        semantique_tags: List[Tag]
    ) -> str:
        """
        Construit la raison du routage
        
        Args:
            target: Cible de stockage
            categorique_tags: Tags catégoriques
            semantique_tags: Tags sémantiques
            
        Returns:
            Description de la raison
        """
        reasons = []
        
        if categorique_tags:
            types = [f"{t.key}={t.value}" for t in categorique_tags[:3]]
            reasons.append(f"Tags catégoriques: {', '.join(types)}")
        
        if semantique_tags:
            concepts = [f"{t.key}={t.value}" for t in semantique_tags[:3]]
            reasons.append(f"Tags sémantiques: {', '.join(concepts)}")
        
        reasons.append(f"Routage: {target.value}")
        
        return " | ".join(reasons)
    
    def get_routing_stats(self, decisions: List[RoutingDecision]) -> Dict[str, Any]:
        """
        Calcule les statistiques de routage
        
        Args:
            decisions: Liste de décisions de routage
            
        Returns:
            Statistiques de routage
        """
        stats = {
            "total": len(decisions),
            "qdrant_only": 0,
            "zvec_only": 0,
            "both": 0,
            "none": 0,
            "qdrant_collections": {},
            "zvec_collections": {},
        }
        
        for decision in decisions:
            if decision.target == StoreTarget.QDRANT:
                stats["qdrant_only"] += 1
            elif decision.target == StoreTarget.ZVEC:
                stats["zvec_only"] += 1
            elif decision.target == StoreTarget.BOTH:
                stats["both"] += 1
            else:
                stats["none"] += 1
            
            # Compter les collections
            for coll in decision.qdrant_collections:
                stats["qdrant_collections"][coll] = stats["qdrant_collections"].get(coll, 0) + 1
            
            for coll in decision.zvec_collections:
                stats["zvec_collections"][coll] = stats["zvec_collections"].get(coll, 0) + 1
        
        return stats
