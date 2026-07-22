"""
Neuronal Scoring Engine - Scoring adaptatif avec apprentissage

Ce module implémente un système de scoring neuronal qui remplace
les poids fixes par des poids adaptatifs apprenant des retours utilisateur.

Classes:
    - NeuronalScoringEngine: Moteur de scoring neuronal
    - WeightPersistence: Gestion de la persistance des poids
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import sqlite3
from pathlib import Path
import numpy as np


@dataclass
class WeightSnapshot:
    """Snapshot des poids à un instant donné"""
    weights: Dict[str, float]
    session_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    feedback_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "weights": self.weights,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "feedback_count": self.feedback_count
        }



class NeuronalScoringEngine:
    """
    Moteur de scoring neuronal adaptatif
    
    Remplace les poids fixes de fusion.py par des poids qui s'ajustent
    automatiquement en fonction des retours utilisateur.
    
    Attributes:
        weights: Poids actuels pour chaque dimension
        learning_rate: Taux d'apprentissage (0.01 - 0.1 recommandé)
        bias: Biais du neurone
        min_weight: Poids minimum (évite poids nuls)
        max_weight: Poids maximum (plafonne les poids)
        session_id: ID de la session courante
        feedback_count: Nombre de feedbacks reçus
    
    Example:
        >>> engine = NeuronalScoringEngine()
        >>> score = engine.calculate_score(0.8, 0.6, 0.3)
        >>> engine.feedback_loop("doc_123", 0.9)  # Feedback positif
    """
    
    # Poids initiaux par défaut (équivalent fusion.py actuel)
    DEFAULT_WEIGHTS = {
        "semantic": 0.4,    # Qdrant score
        "recency": 0.4,     # Zvec score  
        "popularity": 0.2   # Memory boost
    }
    
    def __init__(
        self,
        initial_weights: Optional[Dict[str, float]] = None,
        learning_rate: float = 0.05,
        bias: float = -0.1,
        db_path: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """
        Initialise le moteur neuronal
        
        Args:
            initial_weights: Poids initiaux (optionnel)
            learning_rate: Taux d'apprentissage
            bias: Biais du neurone
            db_path: Chemin vers la DB SQLite pour persistance
            session_id: ID de session (auto-généré si None)
        """
        self.weights = initial_weights or self.DEFAULT_WEIGHTS.copy()
        self.learning_rate = max(0.01, min(0.1, learning_rate))
        self.bias = bias
        self.min_weight = 0.01
        self.max_weight = 1.0
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.feedback_count = 0
        
        # Normaliser les poids initiaux
        self._normalize_weights()
        
        # Persistance
        self.db_path = db_path
        if db_path:
            self._init_db()
            self._load_weights_from_db()
    
    def calculate_score(
        self,
        semantic: float,
        recency: float,
        popularity: float
    ) -> float:
        """
        Calcule le score combiné via activation ReLU
        
        Args:
            semantic: Score sémantique (Qdrant) - 0.0 à 1.0
            recency: Score récence (Zvec) - 0.0 à 1.0
            popularity: Score popularité (Memory) - 0.0 à 1.0
            
        Returns:
            Score combiné - 0.0 à 1.0
        """
        # Calcul linéaire pondéré
        z = (
            semantic * self.weights["semantic"] +
            recency * self.weights["recency"] +
            popularity * self.weights["popularity"] +
            self.bias
        )
        
        # Activation Sigmoid (smooth, bornée [0,1])
        # sigmoid(z) = 1 / (1 + exp(-z))
        score = 1.0 / (1.0 + np.exp(-z))
        return score
    
    def feedback_loop(
        self,
        doc_id: str,
        satisfaction: float,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ajuste les poids selon le feedback utilisateur
        
        Args:
            doc_id: ID du document évalué
            satisfaction: Score de satisfaction (-1.0 à 1.0)
                         -1.0 = très insatisfait
                          0.0 = neutre
                          1.0 = très satisfait
            context: Contexte optionnel (scores individuels, etc.)
            
        Returns:
            Rapport d'ajustement
        """
        old_weights = self.weights.copy()
        
        # Calcul du delta via gradient descent simplifié
        delta = satisfaction * self.learning_rate
        
        # Ajustement des poids
        for key in self.weights:
            new_weight = self.weights[key] + delta
            self.weights[key] = max(self.min_weight, min(self.max_weight, new_weight))
        
        # Renormalisation
        self._normalize_weights()
        
        self.feedback_count += 1
        
        # Persistance
        if self.db_path:
            self._save_weights_to_db()
        
        return {
            "doc_id": doc_id,
            "satisfaction": satisfaction,
            "old_weights": old_weights,
            "new_weights": self.weights.copy(),
            "delta": delta,
            "feedback_count": self.feedback_count
        }
    
    def batch_feedback(
        self,
        feedbacks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Traite un batch de feedbacks
        
        Args:
            feedbacks: Liste de {doc_id, satisfaction, context}
            
        Returns:
            Rapport consolidé
        """
        results = []
        for fb in feedbacks:
            result = self.feedback_loop(
                doc_id=fb.get("doc_id", ""),
                satisfaction=fb.get("satisfaction", 0.0),
                context=fb.get("context")
            )
            results.append(result)
        
        return {
            "total_feedbacks": len(feedbacks),
            "results": results,
            "final_weights": self.weights.copy()
        }
    
    def get_weights(self) -> Dict[str, float]:
        """Retourne les poids actuels"""
        return self.weights.copy()
    
    def set_weights(self, weights: Dict[str, float]) -> None:
        """
        Définit manuellement les poids
        
        Args:
            weights: Nouveaux poids
        """
        self.weights = weights.copy()
        self._normalize_weights()
        if self.db_path:
            self._save_weights_to_db()
    
    def reset_weights(self) -> None:
        """Réinitialise les poids aux valeurs par défaut"""
        self.weights = self.DEFAULT_WEIGHTS.copy()
        self._normalize_weights()
        self.feedback_count = 0
        if self.db_path:
            self._save_weights_to_db()
    
    def get_snapshot(self) -> WeightSnapshot:
        """Retourne un snapshot des poids actuels"""
        return WeightSnapshot(
            weights=self.weights.copy(),
            session_id=self.session_id,
            feedback_count=self.feedback_count
        )
    
    def _normalize_weights(self) -> None:
        """Normalise les poids pour que leur somme = 1.0"""
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}
    
    # === Persistance SQLite ===
    
    def _init_db(self) -> None:
        """Initialise la table SQLite pour les poids"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS neuronal_weights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                weight_name TEXT NOT NULL,
                weight_value REAL NOT NULL,
                session_id TEXT,
                feedback_count INTEGER DEFAULT 0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _save_weights_to_db(self) -> None:
        """Sauvegarde les poids dans SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Supprimer les anciens poids de la session
        cursor.execute(
            "DELETE FROM neuronal_weights WHERE session_id = ?",
            (self.session_id,)
        )
        
        # Insérer les nouveaux poids
        for name, value in self.weights.items():
            cursor.execute("""
                INSERT INTO neuronal_weights 
                (weight_name, weight_value, session_id, feedback_count)
                VALUES (?, ?, ?, ?)
            """, (name, value, self.session_id, self.feedback_count))
        
        conn.commit()
        conn.close()
    
    def _load_weights_from_db(self) -> None:
        """Charge les poids depuis SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Chercher les poids les plus récents
        cursor.execute("""
            SELECT weight_name, weight_value, session_id, feedback_count
            FROM neuronal_weights
            WHERE session_id = (
                SELECT session_id FROM neuronal_weights
                ORDER BY updated_at DESC LIMIT 1
            )
        """)
        
        rows = cursor.fetchall()
        if rows:
            for name, value, sid, count in rows:
                self.weights[name] = value
            # Prendre session_id et count du premier row
            self.session_id = rows[0][2]
            self.feedback_count = rows[0][3]
            self._normalize_weights()
        
        conn.close()
    
    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retourne l'historique des poids
        
        Args:
            limit: Nombre max de snapshots
            
        Returns:
            Liste des snapshots historiques
        """
        if not self.db_path:
            return []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT session_id, feedback_count, updated_at
            FROM neuronal_weights
            GROUP BY session_id
            ORDER BY updated_at DESC
            LIMIT ?
        """, (limit,))
        
        sessions = cursor.fetchall()
        
        history = []
        for session_id, count, timestamp in sessions:
            cursor.execute("""
                SELECT weight_name, weight_value
                FROM neuronal_weights
                WHERE session_id = ?
            """, (session_id,))
            
            weights = {name: value for name, value in cursor.fetchall()}
            history.append({
                "session_id": session_id,
                "weights": weights,
                "feedback_count": count,
                "timestamp": timestamp
            })
        
        conn.close()
        return history
    
    def __repr__(self) -> str:
        return (
            f"NeuronalScoringEngine("
            f"weights={self.weights}, "
            f"lr={self.learning_rate}, "
            f"feedbacks={self.feedback_count})"
        )
