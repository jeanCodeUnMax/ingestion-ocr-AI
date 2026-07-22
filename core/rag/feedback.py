"""
Feedback Loop Module - Apprentissage continu des retours utilisateur

Ce module implémente la boucle de feedback qui permet au système
de s'améliorer automatiquement en fonction des retours utilisateur.

Classes:
    - FeedbackLoop: Gestionnaire de la boucle de feedback
    - FeedbackEntry: Entrée de feedback
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import json
import sqlite3
from pathlib import Path


class FeedbackType(Enum):
    """Types de feedback"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    CORRECTION = "correction"


@dataclass
class FeedbackEntry:
    """Entrée de feedback utilisateur"""
    interaction_id: str
    rating: float  # -1.0 à 1.0
    feedback_type: FeedbackType
    correction: Optional[str] = None
    context_snapshot: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    processed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "interaction_id": self.interaction_id,
            "rating": self.rating,
            "feedback_type": self.feedback_type.value,
            "correction": self.correction,
            "context_snapshot": self.context_snapshot,
            "created_at": self.created_at,
            "processed": self.processed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeedbackEntry':
        return cls(
            interaction_id=data["interaction_id"],
            rating=data["rating"],
            feedback_type=FeedbackType(data.get("feedback_type", "neutral")),
            correction=data.get("correction"),
            context_snapshot=data.get("context_snapshot"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            processed=data.get("processed", False)
        )


class FeedbackLoop:
    """
    Gestionnaire de la boucle de feedback
    
    Coordonne la collecte, le stockage et le traitement des retours
    utilisateur pour améliorer le système de recherche.
    
    Attributes:
        neuronal_engine: Moteur neuronal à ajuster
        db_path: Chemin vers la DB SQLite
        pending_feedbacks: Feedbacks en attente de traitement
    
    Example:
        >>> loop = FeedbackLoop(neuronal_engine, "feedback.db")
        >>> await loop.process_feedback("doc_123", 0.8, "Très pertinent")
    """
    
    # Seuils de classification
    POSITIVE_THRESHOLD = 0.6
    NEGATIVE_THRESHOLD = -0.3
    
    def __init__(
        self,
        neuronal_engine,
        db_path: Optional[str] = None
    ):
        """
        Initialise la boucle de feedback
        
        Args:
            neuronal_engine: Instance de NeuronalScoringEngine
            db_path: Chemin vers la DB SQLite pour persistance
        """
        self.neuronal_engine = neuronal_engine
        self.db_path = db_path
        self.pending_feedbacks: List[FeedbackEntry] = []
        
        if db_path:
            self._init_db()
    
    async def process_feedback(
        self,
        interaction_id: str,
        rating: float,
        correction: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Traite un feedback utilisateur
        
        Args:
            interaction_id: ID de l'interaction/document
            rating: Score de satisfaction (-1.0 à 1.0)
            correction: Correction texte optionnelle
            context: Contexte de l'interaction (scores, requête, etc.)
            
        Returns:
            Rapport de traitement
        """
        # Classifier le feedback
        feedback_type = self._classify_feedback(rating)
        
        # Créer l'entrée
        entry = FeedbackEntry(
            interaction_id=interaction_id,
            rating=rating,
            feedback_type=feedback_type,
            correction=correction,
            context_snapshot=context
        )
        
        # Traiter selon le type
        if feedback_type == FeedbackType.NEGATIVE:
            result = await self._negative_reinforcement(entry)
        elif feedback_type == FeedbackType.POSITIVE:
            result = await self._positive_reinforcement(entry)
        else:
            result = await self._neutral_processing(entry)
        
        # Ajuster les poids neuronaux
        weight_result = self.neuronal_engine.feedback_loop(
            doc_id=interaction_id,
            satisfaction=rating,
            context=context
        )
        
        # Persister
        if self.db_path:
            self._save_feedback_to_db(entry)
        
        entry.processed = True
        
        return {
            "status": "processed",
            "entry": entry.to_dict(),
            "reinforcement": result,
            "weight_adjustment": weight_result
        }
    
    async def batch_process(
        self,
        feedbacks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Traite un batch de feedbacks
        
        Args:
            feedbacks: Liste de {interaction_id, rating, correction, context}
            
        Returns:
            Rapport consolidé
        """
        results = []
        for fb in feedbacks:
            result = await self.process_feedback(
                interaction_id=fb.get("interaction_id", ""),
                rating=fb.get("rating", 0.0),
                correction=fb.get("correction"),
                context=fb.get("context")
            )
            results.append(result)
        
        # Calculer statistiques
        ratings = [fb.get("rating", 0.0) for fb in feedbacks]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
        
        return {
            "total_processed": len(feedbacks),
            "average_rating": avg_rating,
            "results": results,
            "current_weights": self.neuronal_engine.get_weights()
        }
    
    def _classify_feedback(self, rating: float) -> FeedbackType:
        """Classifie le feedback selon le rating"""
        if rating >= self.POSITIVE_THRESHOLD:
            return FeedbackType.POSITIVE
        elif rating <= self.NEGATIVE_THRESHOLD:
            return FeedbackType.NEGATIVE
        else:
            return FeedbackType.NEUTRAL
    
    async def _positive_reinforcement(
        self,
        entry: FeedbackEntry
    ) -> Dict[str, Any]:
        """
        Renforcement positif - Renforce les patterns qui ont fonctionné
        
        Args:
            entry: Entrée de feedback
            
        Returns:
            Actions de renforcement
        """
        actions = []
        
        # Si on a le contexte avec les scores individuels
        if entry.context_snapshot:
            scores = entry.context_snapshot.get("scores", {})
            
            # Renforcer les sources qui ont contribué positivement
            if scores.get("qdrant", 0) > 0.5:
                actions.append("boost_qdrant_weight")
            if scores.get("zvec", 0) > 0.5:
                actions.append("boost_zvec_weight")
            if scores.get("memory", 0) > 0.3:
                actions.append("boost_memory_weight")
        
        return {
            "type": "positive_reinforcement",
            "actions": actions,
            "message": "Patterns renforcés avec succès"
        }
    
    async def _negative_reinforcement(
        self,
        entry: FeedbackEntry
    ) -> Dict[str, Any]:
        """
        Renforcement négatif - Réduit les patterns qui n'ont pas fonctionné
        
        Args:
            entry: Entrée de feedback
            
        Returns:
            Actions de correction
        """
        actions = []
        
        # Si on a le contexte
        if entry.context_snapshot:
            scores = entry.context_snapshot.get("scores", {})
            
            # Réduire les sources qui ont mal contribué
            if scores.get("qdrant", 0) < 0.3:
                actions.append("reduce_qdrant_weight")
            if scores.get("zvec", 0) < 0.3:
                actions.append("reduce_zvec_weight")
        
        # Si correction texte fournie
        if entry.correction:
            actions.append(f"store_correction: {entry.correction[:100]}")
        
        return {
            "type": "negative_reinforcement",
            "actions": actions,
            "message": "Patterns corrigés"
        }
    
    async def _neutral_processing(
        self,
        entry: FeedbackEntry
    ) -> Dict[str, Any]:
        """Traitement neutre - Stockage sans ajustement majeur"""
        return {
            "type": "neutral",
            "actions": ["store_for_analysis"],
            "message": "Feedback stocké pour analyse ultérieure"
        }
    
    # === Statistiques ===
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de feedback"""
        if not self.db_path:
            return {
                "total": len(self.pending_feedbacks),
                "pending": len(self.pending_feedbacks)
            }
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total
        cursor.execute("SELECT COUNT(*) FROM feedback_logs")
        total = cursor.fetchone()[0]
        
        # Par type
        cursor.execute("""
            SELECT feedback_type, COUNT(*) 
            FROM feedback_logs 
            GROUP BY feedback_type
        """)
        by_type = dict(cursor.fetchall())
        
        # Rating moyen
        cursor.execute("SELECT AVG(rating) FROM feedback_logs")
        avg_rating = cursor.fetchone()[0] or 0.0
        
        # Non traités
        cursor.execute("SELECT COUNT(*) FROM feedback_logs WHERE processed = 0")
        pending = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total": total,
            "by_type": by_type,
            "average_rating": round(avg_rating, 3),
            "pending": pending,
            "current_weights": self.neuronal_engine.get_weights()
        }
    
    # === Persistance SQLite ===
    
    def _init_db(self) -> None:
        """Initialise la table SQLite pour les feedbacks"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interaction_id TEXT NOT NULL,
                rating REAL CHECK(rating BETWEEN -1 AND 1),
                feedback_type TEXT,
                correction TEXT,
                context_snapshot TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT FALSE
            )
        """)
        
        # Index pour recherches rapides
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback_interaction 
            ON feedback_logs(interaction_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback_created 
            ON feedback_logs(created_at)
        """)
        
        conn.commit()
        conn.close()
    
    def _save_feedback_to_db(self, entry: FeedbackEntry) -> None:
        """Sauvegarde un feedback dans SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO feedback_logs 
            (interaction_id, rating, feedback_type, correction, context_snapshot, processed)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            entry.interaction_id,
            entry.rating,
            entry.feedback_type.value,
            entry.correction,
            json.dumps(entry.context_snapshot) if entry.context_snapshot else None,
            entry.processed
        ))
        
        conn.commit()
        conn.close()
    
    def get_recent_feedbacks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Récupère les feedbacks récents
        
        Args:
            limit: Nombre max de feedbacks
            
        Returns:
            Liste des feedbacks
        """
        if not self.db_path:
            return [f.to_dict() for f in self.pending_feedbacks[:limit]]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT interaction_id, rating, feedback_type, correction, created_at, processed
            FROM feedback_logs
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "interaction_id": row[0],
                "rating": row[1],
                "feedback_type": row[2],
                "correction": row[3],
                "created_at": row[4],
                "processed": bool(row[5])
            }
            for row in rows
        ]
    
    def __repr__(self) -> str:
        return (
            f"FeedbackLoop("
            f"pending={len(self.pending_feedbacks)}, "
            f"weights={self.neuronal_engine.get_weights()})"
        )
