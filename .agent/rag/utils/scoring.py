"""
Scoring Utilities

Fonctions utilitaires pour le scoring et le classement.
"""

from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class ScoredItem:
    """Item avec score"""
    item: Any
    score: float


def calculate_hybrid_score(
    qdrant_score: float,
    zvec_score: float,
    memory_boost: float,
    weights: Dict[str, float] = None
) -> float:
    """
    Calcule le score hybride combiné
    
    Args:
        qdrant_score: Score Qdrant (0.0 - 1.0)
        zvec_score: Score Zvec (0.0 - 1.0)
        memory_boost: Boost Memory MCP (0.0 - 0.5)
        weights: Poids personnalisés (optionnel)
        
    Returns:
        Score combiné (0.0 - 1.0)
    """
    if weights is None:
        weights = {"qdrant": 0.4, "zvec": 0.4, "memory": 0.2}
    
    score = (
        weights.get("qdrant", 0.4) * qdrant_score +
        weights.get("zvec", 0.4) * zvec_score +
        weights.get("memory", 0.2) * memory_boost
    )
    
    return min(score, 1.0)


def normalize_score(score: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """
    Normalise un score entre min_val et max_val
    
    Args:
        score: Score à normaliser
        min_val: Valeur minimale
        max_val: Valeur maximale
        
    Returns:
        Score normalisé
    """
    return max(min_val, min(max_val, score))


def rank_results(
    results: List[Dict],
    score_key: str = "score",
    descending: bool = True
) -> List[Dict]:
    """
    Trie les résultats par score
    
    Args:
        results: Liste de résultats
        score_key: Clé du score
        descending: Ordre décroissant
        
    Returns:
        Résultats triés
    """
    return sorted(
        results,
        key=lambda r: r.get(score_key, 0),
        reverse=descending
    )


def deduplicate_by_key(
    results: List[Dict],
    key: str = "id"
) -> List[Dict]:
    """
    Déduplique les résultats par clé
    
    Args:
        results: Liste de résultats
        key: Clé de déduplication
        
    Returns:
        Résultats uniques
    """
    seen = set()
    unique = []
    
    for result in results:
        result_key = result.get(key)
        if result_key and result_key not in seen:
            seen.add(result_key)
            unique.append(result)
    
    return unique


def calculate_relevance_score(
    query_tokens: set,
    content_tokens: set
) -> float:
    """
    Calcule un score de pertinence basé sur les tokens
    
    Args:
        query_tokens: Tokens de la requête
        content_tokens: Tokens du contenu
        
    Returns:
        Score de pertinence (0.0 - 1.0)
    """
    if not query_tokens or not content_tokens:
        return 0.0
    
    intersection = query_tokens & content_tokens
    union = query_tokens | content_tokens
    
    # Jaccard similarity
    jaccard = len(intersection) / len(union) if union else 0
    
    # Coverage (combien de tokens de la requête sont présents)
    coverage = len(intersection) / len(query_tokens) if query_tokens else 0
    
    # Score combiné
    return (jaccard + coverage) / 2


def apply_decay_score(
    score: float,
    age_hours: float,
    decay_rate: float = 0.01
) -> float:
    """
    Applique une décroissance temporelle au score
    
    Args:
        score: Score initial
        age_hours: Âge en heures
        decay_rate: Taux de décroissance
        
    Returns:
        Score avec décroissance
    """
    import math
    
    decay_factor = math.exp(-decay_rate * age_hours)
    return score * decay_factor


def boost_by_metadata(
    score: float,
    metadata: Dict[str, Any],
    boost_rules: Dict[str, Dict[str, float]]
) -> float:
    """
    Applique un boost basé sur les métadonnées
    
    Args:
        score: Score initial
        metadata: Métadonnées de l'item
        boost_rules: Règles de boost {key: {value: boost_factor}}
        
    Returns:
        Score boosté
    """
    boost = 1.0
    
    for key, rules in boost_rules.items():
        value = metadata.get(key)
        if value and value in rules:
            boost *= rules[value]
    
    return min(score * boost, 1.0)
