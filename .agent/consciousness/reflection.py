"""
Reflection Engine - Auto-évaluation et métacognition

Ce module implémente la couche 2 de conscience: la capacité
de s'auto-questionner et d'évaluer sa propre performance.

Classes:
    - ReflectionEngine: Moteur de réflexion
    - SelfAssessment: Résultat d'auto-évaluation
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class AssessmentCategory(Enum):
    """Catégories d'évaluation"""
    PERFORMANCE = "performance"
    STABILITY = "stability"
    LEARNING = "learning"
    GAPS = "gaps"
    ETHICS = "ethics"


@dataclass
class SelfAssessment:
    """Résultat d'une auto-évaluation"""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    performance: Dict[str, Any] = field(default_factory=dict)
    stability: Dict[str, Any] = field(default_factory=dict)
    learning: Dict[str, Any] = field(default_factory=dict)
    gaps: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "performance": self.performance,
            "stability": self.stability,
            "learning": self.learning,
            "gaps": self.gaps,
            "recommendations": self.recommendations
        }


class ReflectionEngine:
    """
    Moteur de réflexion et auto-évaluation
    
    Permet au système de s'auto-questionner sur:
    - Sa performance actuelle
    - Sa stabilité
    - Son apprentissage
    - Ses lacunes
    
    Attributes:
        questions: Questions d'auto-réflexion
        history: Historique des évaluations
        metrics_source: Source des métriques (pipeline, feedback, etc.)
    
    Example:
        >>> engine = ReflectionEngine(metrics_source=pipeline)
        >>> assessment = await engine.self_assess()
        >>> print(assessment.gaps)
    """
    
    # Questions d'auto-réflexion
    QUESTIONS = [
        "Qu'est-ce que je sais faire?",
        "Qu'est-ce que j'ai appris?",
        "Qu'est-ce qui ne fonctionne pas?",
        "Qu'est-ce que je pourrais améliorer?",
        "Quelles sont mes limites actuelles?",
        "Quels patterns ai-je identifiés?"
    ]
    
    def __init__(self, metrics_source=None):
        """
        Initialise le moteur de réflexion
        
        Args:
            metrics_source: Source de métriques (pipeline, feedback loop, etc.)
        """
        self.metrics_source = metrics_source
        self.history: List[SelfAssessment] = []
    
    async def self_assess(self) -> SelfAssessment:
        """
        Effectue une auto-évaluation complète
        
        Returns:
            Résultat de l'auto-évaluation
        """
        assessment = SelfAssessment(
            performance=await self._assess_performance(),
            stability=await self._assess_stability(),
            learning=await self._assess_learning(),
            gaps=await self._identify_gaps(),
            recommendations=[]
        )
        
        # Générer des recommandations basées sur l'évaluation
        assessment.recommendations = self._generate_recommendations(assessment)
        
        self.history.append(assessment)
        return assessment
    
    async def _assess_performance(self) -> Dict[str, Any]:
        """Évalue la performance du système"""
        if not self.metrics_source:
            return self._default_performance()
        
        try:
            # Récupérer les métriques depuis la source
            stats = self.metrics_source.get_stats() if hasattr(self.metrics_source, 'get_stats') else {}
            
            return {
                "queries_processed": stats.get("queries_count", "N/A"),
                "avg_latency_ms": stats.get("latency_avg_ms", "N/A"),
                "cache_efficiency": stats.get("cache_hit_rate", "N/A"),
                "fusion_weights": stats.get("fusion", {}).get("weights", {})
            }
        except Exception as e:
            return {"error": str(e), "status": "degraded"}
    
    async def _assess_stability(self) -> Dict[str, Any]:
        """Évalue la stabilité du système"""
        return {
            "error_rate": await self._get_error_rate(),
            "uptime_status": "healthy",
            "last_incident": None,
            "recovery_capacity": "high"
        }
    
    async def _assess_learning(self) -> Dict[str, Any]:
        """Évalue l'apprentissage du système"""
        return {
            "feedback_received": await self._get_feedback_count(),
            "weights_adjusted": await self._get_weights_changes(),
            "patterns_identified": await self._get_patterns_count(),
            "knowledge_growth": "positive"
        }
    
    async def _identify_gaps(self) -> List[str]:
        """Identifie les lacunes du système"""
        gaps = []
        
        # Analyser les métriques pour identifier les lacunes
        performance = await self._assess_performance()
        
        if performance.get("cache_efficiency", 1.0) < 0.5:
            gaps.append("Cache efficiency below 50% - optimization needed")
        
        if performance.get("avg_latency_ms", 0) > 500:
            gaps.append("Latency above 500ms - performance bottleneck detected")
        
        # Lacunes structurelles
        gaps.extend([
            "Limited proactive behavior",
            "No autonomous goal setting",
            "Dependency on external feedback"
        ])
        
        return gaps
    
    def _generate_recommendations(self, assessment: SelfAssessment) -> List[str]:
        """Génère des recommandations d'amélioration"""
        recommendations = []
        
        # Basées sur les lacunes
        for gap in assessment.gaps:
            if "cache" in gap.lower():
                recommendations.append("Increase cache TTL and max_entries")
            elif "latency" in gap.lower():
                recommendations.append("Optimize query routing and reduce collection scans")
        
        # Recommandations générales
        if not assessment.learning.get("feedback_received", 0):
            recommendations.append("Implement feedback collection mechanism")
        
        return recommendations
    
    async def _get_error_rate(self) -> float:
        """Récupère le taux d'erreur (placeholder)"""
        return 0.0  # À implémenter avec logs réels
    
    async def _get_feedback_count(self) -> int:
        """Récupère le nombre de feedbacks reçus"""
        if hasattr(self.metrics_source, 'feedback_loop'):
            stats = self.metrics_source.feedback_loop.get_stats() if hasattr(self.metrics_source.feedback_loop, 'get_stats') else {}
            return stats.get("total", 0)
        return 0
    
    async def _get_weights_changes(self) -> int:
        """Récupère le nombre d'ajustements de poids"""
        return 0  # À implémenter
    
    async def _get_patterns_count(self) -> int:
        """Récupère le nombre de patterns identifiés"""
        return 0  # À implémenter
    
    def _default_performance(self) -> Dict[str, Any]:
        """Retourne des métriques par défaut"""
        return {
            "status": "no_metrics_source",
            "queries_processed": "N/A",
            "avg_latency_ms": "N/A"
        }
    
    def ask_question(self, question: str) -> str:
        """
        Pose une question d'auto-réflexion
        
        Args:
            question: Question à poser
            
        Returns:
            Réponse générée
        """
        if question not in self.QUESTIONS:
            return f"Question non reconnue: {question}"
        
        # Réponses basées sur l'état actuel
        responses = {
            "Qu'est-ce que je sais faire?": 
                "Je sais effectuer des recherches hybrides, gérer un système de mémoire distribué, et m'adapter via feedback.",
            "Qu'est-ce que j'ai appris?":
                "J'ai appris à ajuster mes poids de fusion selon les retours utilisateur.",
            "Qu'est-ce qui ne fonctionne pas?":
                "Je manque de comportement proactif et d'autonomie dans la définition d'objectifs.",
            "Qu'est-ce que je pourrais améliorer?":
                "Je pourrais améliorer ma capacité d'auto-évaluation et de génération d'intentions autonomes.",
            "Quelles sont mes limites actuelles?":
                "Mes limites incluent: dépendance aux feedbacks externes, pas de planification à long terme.",
            "Quels patterns ai-je identifiés?":
                "Patterns identifiés: corrélation entre qualité des embeddings et pertinence des résultats."
        }
        
        return responses.get(question, "Question en attente de réponse.")
    
    def get_reflection_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retourne l'historique des réflexions"""
        return [a.to_dict() for a in self.history[-limit:]]
    
    def __repr__(self) -> str:
        return f"ReflectionEngine(reflections={len(self.history)})"
