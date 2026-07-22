"""
Context Booster - Reranking personnalisé avec signaux contextuels

Booste les résultats de recherche selon :
- Relations Memory MCP (type et force)
- Métadonnées du chunk (tags, catégorie, fraîcheur)
- Historique utilisateur (clics, favoris)
- Contexte de session (requête précédente)
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import json


@dataclass
class UserContext:
    """Contexte utilisateur pour personnalisation"""
    favorited_chunks: set = None
    clicked_chunks: set = None
    recent_queries: list = None
    preferred_categories: set = None
    
    def __post_init__(self):
        if self.favorited_chunks is None:
            self.favorited_chunks = set()
        if self.clicked_chunks is None:
            self.clicked_chunks = set()
        if self.recent_queries is None:
            self.recent_queries = []
        if self.preferred_categories is None:
            self.preferred_categories = set()


@dataclass
class BoostFactors:
    """Facteurs de boost pour un résultat"""
    relation_boost: float = 1.0
    metadata_boost: float = 1.0
    history_boost: float = 1.0
    freshness_boost: float = 1.0
    
    def total(self) -> float:
        """Boost total (multiplicatif)"""
        return (
            self.relation_boost * 
            self.metadata_boost * 
            self.history_boost * 
            self.freshness_boost
        )


class ContextBooster:
    """
    Booster contextuel pour reranking personnalisé
    
    Intègre des signaux business/contextuels aux scores vectoriels
    pour améliorer la pertinence perçue par l'utilisateur.
    
    Example:
        >>> booster = ContextBooster(user_context)
        >>> boosted_results = booster.boost_results(
        ...     results=search_results,
        ...     memory_relations=relations,
        ...     query="python tutorial"
        ... )
    """
    
    # Boosts par type de relation (hiérarchie de confiance)
    RELATION_MULTIPLIERS = {
        "contains": 1.05,
        "stored_in": 1.02,
        "relates_to": 1.15,      # Forte relation sémantique
        "references": 1.10,      # Référence explicite
        "depends_on": 1.12,      # Dépendance forte
        "implements": 1.08,
        "extends": 1.06,
        "proves": 1.20,          # Relation de preuve (haute confiance)
        "uses_qdrant": 1.05,
        "uses_zvec": 1.05,
        "uses_cache": 1.03,
    }
    
    # Boosts par catégorie de tag
    TAG_CATEGORY_BOOST = {
        "critical": 1.25,
        "important": 1.15,
        "high": 1.10,
        "normal": 1.0,
        "low": 0.95,
    }
    
    def __init__(self, user_context: Optional[UserContext] = None):
        """
        Initialise le booster avec contexte utilisateur
        
        Args:
            user_context: Contexte utilisateur (optionnel)
        """
        self.user_context = user_context or UserContext()
    
    def boost_results(
        self,
        results: List[Dict[str, Any]],
        memory_relations: List[Dict[str, Any]],
        query: str
    ) -> List[Dict[str, Any]]:
        """
        Booste les résultats avec signaux contextuels
        
        Args:
            results: Résultats bruts de Qdrant/Zvec
            memory_relations: Relations Memory MCP
            query: Requête originale
            
        Returns:
            Résultats avec scores boostés
        """
        # Indexer les relations par chunk_id
        relation_map = self._index_relations(memory_relations)
        
        boosted = []
        for result in results:
            chunk_id = result.get("id", result.get("chunk_id", ""))
            
            # Calculer les facteurs de boost
            factors = BoostFactors()
            
            # 1. Boost par relations
            factors.relation_boost = self._calculate_relation_boost(
                chunk_id, relation_map
            )
            
            # 2. Boost par métadonnées
            factors.metadata_boost = self._calculate_metadata_boost(result)
            
            # 3. Boost par historique utilisateur
            factors.history_boost = self._calculate_history_boost(chunk_id)
            
            # 4. Boost par fraîcheur
            factors.freshness_boost = self._calculate_freshness_boost(result)
            
            # Appliquer le boost
            original_score = result.get("score", 0.0)
            boosted_score = min(original_score * factors.total(), 1.0)
            
            # Créer le résultat boosté
            boosted_result = result.copy()
            boosted_result["score"] = boosted_score
            boosted_result["original_score"] = original_score
            boosted_result["boost_factors"] = {
                "relation": factors.relation_boost,
                "metadata": factors.metadata_boost,
                "history": factors.history_boost,
                "freshness": factors.freshness_boost,
                "total": factors.total()
            }
            boosted_result["boost_reasons"] = self._explain_boost(
                chunk_id, factors, relation_map
            )
            
            boosted.append(boosted_result)
        
        # Retrier par score boosté
        boosted.sort(key=lambda x: x["score"], reverse=True)
        
        return boosted
    
    def _index_relations(
        self, relations: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Indexe les relations par chunk cible"""
        indexed = {}
        for rel in relations:
            target = rel.get("to", rel.get("target", ""))
            if target:
                if target not in indexed:
                    indexed[target] = []
                indexed[target].append(rel)
        return indexed
    
    def _calculate_relation_boost(
        self, chunk_id: str, relation_map: Dict[str, List[Dict]]
    ) -> float:
        """Calcule le boost basé sur les relations Memory MCP"""
        relations = relation_map.get(chunk_id, [])
        if not relations:
            return 1.0
        
        # Multiplier les boosts des relations (effet cumulatif)
        total_boost = 1.0
        for rel in relations:
            rel_type = rel.get("relationType", "relates_to")
            multiplier = self.RELATION_MULTIPLIERS.get(rel_type, 1.03)
            total_boost *= multiplier
        
        # Plafonner à 1.5 (évite les boosts excessifs)
        return min(total_boost, 1.5)
    
    def _calculate_metadata_boost(self, result: Dict[str, Any]) -> float:
        """Calcule le boost basé sur les métadonnées"""
        metadata = result.get("metadata", result.get("payload", {}))
        boost = 1.0
        
        # Boost par catégorie de tag
        tag_category = metadata.get("tag_category", "normal")
        boost *= self.TAG_CATEGORY_BOOST.get(tag_category, 1.0)
        
        # Boost par niveau éthique (règles Asimov)
        ethics_level = metadata.get("ethics_level", "")
        if ethics_level == "high":
            boost *= 1.15
        elif ethics_level == "critical":
            boost *= 1.25
        
        # Boost si contient exemples ou code
        content = result.get("content", result.get("text", ""))
        if "```" in content or "example" in content.lower():
            boost *= 1.08
        
        return boost
    
    def _calculate_history_boost(self, chunk_id: str) -> float:
        """Calcule le boost basé sur l'historique utilisateur"""
        boost = 1.0
        
        # Boost fort si favori
        if chunk_id in self.user_context.favorited_chunks:
            boost *= 1.30
        
        # Boost modéré si déjà cliqué
        if chunk_id in self.user_context.clicked_chunks:
            boost *= 1.15
        
        return boost
    
    def _calculate_freshness_boost(self, result: Dict[str, Any]) -> float:
        """Calcule le boost basé sur la fraîcheur du document"""
        metadata = result.get("metadata", result.get("payload", {}))
        
        # Récupérer la date de création/modification
        date_str = metadata.get("created_at", metadata.get("modified_at", ""))
        if not date_str:
            return 1.0
        
        try:
            # Parser la date
            if isinstance(date_str, str):
                doc_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                return 1.0
            
            # Calculer l'âge
            age = datetime.now() - doc_date
            
            # Boost dégressif avec l'âge
            if age < timedelta(days=7):      # < 1 semaine
                return 1.15
            elif age < timedelta(days=30):   # < 1 mois
                return 1.08
            elif age < timedelta(days=90):  # < 3 mois
                return 1.04
            else:                            # > 3 mois
                return 1.0
                
        except (ValueError, TypeError):
            return 1.0
    
    def _explain_boost(
        self,
        chunk_id: str,
        factors: BoostFactors,
        relation_map: Dict[str, List[Dict]]
    ) -> List[str]:
        """Génère une explication des boosts appliqués"""
        reasons = []
        
        if factors.relation_boost > 1.05:
            rels = relation_map.get(chunk_id, [])
            rel_types = [r.get("relationType", "relates_to") for r in rels]
            reasons.append(f"Relations: {', '.join(rel_types)}")
        
        if factors.history_boost > 1.1:
            if chunk_id in self.user_context.favorited_chunks:
                reasons.append("⭐ Favori utilisateur")
            elif chunk_id in self.user_context.clicked_chunks:
                reasons.append("👁️ Déjà consulté")
        
        if factors.freshness_boost > 1.05:
            reasons.append("🆕 Contenu récent")
        
        if factors.metadata_boost > 1.1:
            reasons.append("🏷️ Métadonnées prioritaires")
        
        return reasons
    
    def update_user_context(
        self,
        clicked_chunk: Optional[str] = None,
        favorited_chunk: Optional[str] = None,
        query: Optional[str] = None
    ) -> None:
        """
        Met à jour le contexte utilisateur après une interaction
        
        Args:
            clicked_chunk: ID du chunk cliqué
            favorited_chunk: ID du chunk favorisé
            query: Requête effectuée
        """
        if clicked_chunk:
            self.user_context.clicked_chunks.add(clicked_chunk)
        
        if favorited_chunk:
            self.user_context.favorited_chunks.add(favorited_chunk)
        
        if query:
            self.user_context.recent_queries.append({
                "query": query,
                "timestamp": datetime.now().isoformat()
            })
            # Garder seulement les 10 dernières requêtes
            self.user_context.recent_queries = self.user_context.recent_queries[-10:]
    
    def get_boost_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcule des statistiques sur les boosts appliqués"""
        if not results:
            return {}
        
        total_boosts = [r.get("boost_factors", {}).get("total", 1.0) for r in results]
        
        return {
            "avg_boost": sum(total_boosts) / len(total_boosts),
            "max_boost": max(total_boosts),
            "min_boost": min(total_boosts),
            "boosted_count": sum(1 for b in total_boosts if b > 1.01),
            "total_count": len(total_boosts)
        }
