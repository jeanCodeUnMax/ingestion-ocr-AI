"""
Maximal Marginal Relevance (MMR) - Diversification des résultats

Ce module implémente l'algorithme MMR pour équilibrer 
la pertinence et la diversité des résultats de recherche.

Inspiré de Carbonell & Goldstein (1998) et des implémentations
modernes dans Qdrant 2025.
"""
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass


@dataclass
class MMRResult:
    """Résultat avec score MMR"""
    doc_id: str
    original_score: float
    mmr_score: float
    relevance: float
    diversity_penalty: float
    content: Any


class MaximalMarginalRelevance:
    """
    Sélecteur MMR pour diversifier les résultats
    
    Équilibre entre :
    - Relevance : similarité avec la requête
    - Diversity : distance avec les documents déjà sélectionnés
    
    Formula MMR :
    MMR = argmax [ λ * Relevance(Di) - (1-λ) * max(Similarity(Di, Dj)) ]
                          pour Dj dans selected_docs
    
    Attributes:
        lambda_param: Équilibre relevance/diversity (0.0 à 1.0)
                      1.0 = que relevance
                      0.5 = équilibre (défaut)
                      0.0 = que diversity
    
    Example:
        >>> mmr = MaximalMarginalRelevance(lambda_param=0.5)
        >>> results = mmr.select_diverse_results(
        ...     candidates=search_results,
        ...     query_embedding=query_vec,
        ...     top_k=10
        ... )
    """
    
    def __init__(self, lambda_param: float = 0.5):
        """
        Initialise MMR
        
        Args:
            lambda_param: Poids de relevance vs diversity
                         0.5 = équilibre (recommandé)
        """
        if not 0.0 <= lambda_param <= 1.0:
            raise ValueError("lambda_param doit être entre 0.0 et 1.0")
        
        self.lambda_param = lambda_param
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calcule la similarité cosinus entre deux vecteurs"""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(np.dot(a, b) / (norm_a * norm_b))
    
    def calculate_mmr_scores(
        self,
        candidates: List[Dict[str, Any]],
        query_embedding: np.ndarray,
        selected_ids: List[str]
    ) -> Dict[str, float]:
        """
        Calcule les scores MMR pour tous les candidats
        
        Args:
            candidates: Liste de documents {id, embedding, score, ...}
            query_embedding: Embedding de la requête
            selected_ids: IDs déjà sélectionnés
            
        Returns:
            Dict {doc_id: mmr_score}
        """
        mmr_scores = {}
        
        # Récupérer les embeddings des documents sélectionnés
        selected_embeddings = []
        for doc in candidates:
            if doc.get('id') in selected_ids:
                emb = doc.get('embedding')
                if emb is not None:
                    selected_embeddings.append(np.array(emb))
        
        for doc in candidates:
            doc_id = doc.get('id')
            doc_embedding = doc.get('embedding')
            
            if doc_embedding is None:
                mmr_scores[doc_id] = -float('inf')
                continue
            
            doc_vec = np.array(doc_embedding)
            
            # 1. Relevance : similarité avec la requête
            relevance = self._cosine_similarity(doc_vec, query_embedding)
            
            # 2. Diversity : distance maximale avec les docs sélectionnés
            diversity_penalty = 0.0
            if selected_embeddings:
                similarities = [
                    self._cosine_similarity(doc_vec, sel_emb)
                    for sel_emb in selected_embeddings
                ]
                diversity_penalty = max(similarities)  # Plus similaire = moins diverse
            
            # 3. Score MMR
            mmr_score = (
                self.lambda_param * relevance -
                (1 - self.lambda_param) * diversity_penalty
            )
            
            mmr_scores[doc_id] = mmr_score
        
        return mmr_scores
    
    def select_diverse_results(
        self,
        candidates: List[Dict[str, Any]],
        query_embedding: np.ndarray,
        top_k: int = 10
    ) -> List[MMRResult]:
        """
        Sélectionne top_k résultats diversifiés avec MMR
        
        Args:
            candidates: Liste de documents candidats
            query_embedding: Embedding de la requête
            top_k: Nombre de résultats à retourner
            
        Returns:
            Liste de MMRResult ordonnée par score MMR
        """
        if not candidates:
            return []
        
        # S'assurer que top_k ne dépasse pas le nombre de candidats
        top_k = min(top_k, len(candidates))
        
        selected_ids = []
        selected_results = []
        remaining_candidates = candidates.copy()
        
        for _ in range(top_k):
            if not remaining_candidates:
                break
            
            # Calculer les scores MMR pour les candidats restants
            mmr_scores = self.calculate_mmr_scores(
                remaining_candidates,
                query_embedding,
                selected_ids
            )
            
            # Sélectionner le meilleur
            if not mmr_scores:
                break
                
            best_id = max(mmr_scores, key=mmr_scores.get)
            best_score = mmr_scores[best_id]
            
            # Trouver le document correspondant
            best_doc = next(
                (d for d in remaining_candidates if d.get('id') == best_id),
                None
            )
            
            if best_doc is None:
                break
            
            # Calculer les composantes pour logging
            doc_vec = np.array(best_doc.get('embedding', []))
            relevance = self._cosine_similarity(doc_vec, query_embedding)
            
            diversity_penalty = 0.0
            if selected_ids:
                selected_embeddings = [
                    np.array(r.content.get('embedding')) 
                    for r in selected_results 
                    if r.content.get('embedding') is not None
                ]
                if selected_embeddings:
                    similarities = [
                        self._cosine_similarity(doc_vec, sel_emb)
                        for sel_emb in selected_embeddings
                    ]
                    diversity_penalty = max(similarities)
            
            # Créer le résultat MMR
            mmr_result = MMRResult(
                doc_id=best_id,
                original_score=best_doc.get('score', 0.0),
                mmr_score=best_score,
                relevance=relevance,
                diversity_penalty=diversity_penalty,
                content=best_doc
            )
            
            selected_results.append(mmr_result)
            selected_ids.append(best_id)
            
            # Retirer des candidats
            remaining_candidates = [
                c for c in remaining_candidates 
                if c.get('id') != best_id
            ]
        
        return selected_results
    
    def rerank_results(
        self,
        search_results: List[Any],
        query_embedding: np.ndarray,
        lambda_param: Optional[float] = None
    ) -> List[Any]:
        """
        Méthode pratique pour reranker des résultats existants
        
        Args:
            search_results: Résultats bruts de Qdrant/Zvec
            query_embedding: Embedding de la requête
            lambda_param: Override temporaire du paramètre
            
        Returns:
            Résultats rerankés avec MMR
        """
        if lambda_param is not None:
            old_lambda = self.lambda_param
            self.lambda_param = lambda_param
        
        try:
            # Convertir les résultats au format attendu
            candidates = []
            for result in search_results:
                candidates.append({
                    'id': getattr(result, 'id', str(result)),
                    'embedding': getattr(result, 'embedding', None),
                    'score': getattr(result, 'score', 0.0),
                    'content': result
                })
            
            mmr_results = self.select_diverse_results(
                candidates,
                query_embedding,
                top_k=len(candidates)
            )
            
            # Retourner les résultats dans l'ordre MMR
            return [r.content for r in mmr_results]
            
        finally:
            if lambda_param is not None:
                self.lambda_param = old_lambda


def calculate_diversity_score(results: List[Dict[str, Any]]) -> float:
    """
    Calcule un score de diversité moyen pour un ensemble de résultats
    
    Returns:
        Score entre 0.0 (tous identiques) et 1.0 (tous différents)
    """
    if len(results) < 2:
        return 1.0
    
    embeddings = [r.get('embedding') for r in results if r.get('embedding') is not None]
    if len(embeddings) < 2:
        return 0.0
    
    # Calculer la similarité moyenne entre tous les pairs
    total_sim = 0.0
    count = 0
    
    for i in range(len(embeddings)):
        for j in range(i + 1, len(embeddings)):
            a = np.array(embeddings[i])
            b = np.array(embeddings[j])
            
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a > 0 and norm_b > 0:
                sim = np.dot(a, b) / (norm_a * norm_b)
                total_sim += sim
                count += 1
    
    if count == 0:
        return 0.0
    
    avg_similarity = total_sim / count
    # Diversity = 1 - average_similarity
    return 1.0 - avg_similarity
