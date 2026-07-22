"""
Consciousness Bridge - Intégration avec IEFASTOS

Ce module fait le pont entre les modules de conscience et
le système IEFASTOS existant (pipeline RAG, mémoire, etc.).

Classes:
    - ConsciousnessBridge: Point d'intégration principal
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

from .reflection import ReflectionEngine, SelfAssessment
from .ethical_guardrails import EthicalGuardrails, ViolationSeverity


@dataclass
class ConsciousnessState:
    """État de conscience courant"""
    awareness_level: float = 0.0
    reflection_active: bool = False
    ethical_mode: str = "strict"
    last_assessment: Optional[Dict[str, Any]] = None
    pending_actions: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "awareness_level": self.awareness_level,
            "reflection_active": self.reflection_active,
            "ethical_mode": self.ethical_mode,
            "last_assessment": self.last_assessment,
            "pending_actions": self.pending_actions,
            "timestamp": self.timestamp
        }


class ConsciousnessBridge:
    """
    Point d'intégration entre conscience et IEFASTOS
    
    Ce bridge permet aux modules de conscience d'interagir
    avec le système existant de manière transparente.
    
    Attributes:
        reflection: Moteur de réflexion
        guardrails: Barrières éthiques
        pipeline: Pipeline RAG (optionnel)
        feedback_loop: Boucle de feedback (optionnel)
        state: État de conscience courant
    
    Example:
        >>> bridge = ConsciousnessBridge(pipeline=pipeline)
        >>> await bridge.initialize()
        >>> action_result = await bridge.execute_with_ethics("search query")
    """
    
    def __init__(
        self,
        pipeline=None,
        feedback_loop=None,
        neuronal_engine=None,
        strict_ethics: bool = True
    ):
        """
        Initialise le bridge de conscience
        
        Args:
            pipeline: Pipeline RAG
            feedback_loop: Boucle de feedback
            neuronal_engine: Moteur neuronal
            strict_ethics: Mode éthique strict
        """
        self.pipeline = pipeline
        self.feedback_loop = feedback_loop
        self.neuronal_engine = neuronal_engine
        
        # Modules de conscience
        self.reflection = ReflectionEngine(metrics_source=pipeline)
        self.guardrails = EthicalGuardrails(strict_mode=strict_ethics)
        
        # État
        self.state = ConsciousnessState(
            ethical_mode="strict" if strict_ethics else "permissive"
        )
        
        # Callbacks pour événements
        self._on_violation_callbacks: List = []
        self._on_assessment_callbacks: List = []
    
    async def initialize(self) -> Dict[str, bool]:
        """
        Initialise tous les composants de conscience
        
        Returns:
            Statut d'initialisation de chaque composant
        """
        results = {
            "reflection": True,
            "guardrails": True,
            "pipeline": self.pipeline is not None,
            "feedback": self.feedback_loop is not None,
            "neuronal": self.neuronal_engine is not None
        }
        
        # Mise à jour de l'état
        self.state.awareness_level = 1.0 if all(results.values()) else 0.5
        
        return results
    
    async def execute_with_ethics(
        self,
        action: str,
        action_func=None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Exécute une action avec validation éthique
        
        Args:
            action: Description de l'action
            action_func: Fonction à exécuter si validée
            context: Contexte additionnel
            
        Returns:
            Résultat de l'exécution
        """
        # 1. Validation éthique
        validation = await self.guardrails.validate_action(action, context)
        
        if not validation["valid"]:
            # Notifier les callbacks de violation
            await self._notify_violation(validation)
            return {
                "status": "blocked",
                "reason": validation["reason"],
                "violations": validation["violations"]
            }
        
        # 2. Exécuter l'action si fournie
        if action_func and callable(action_func):
            try:
                result = await action_func() if asyncio.iscoroutinefunction(action_func) else action_func()
                return {
                    "status": "success",
                    "validation": validation,
                    "result": result
                }
            except Exception as e:
                return {
                    "status": "error",
                    "validation": validation,
                    "error": str(e)
                }
        
        return {
            "status": "validated",
            "validation": validation
        }
    
    async def reflect(self) -> SelfAssessment:
        """
        Déclenche une auto-évaluation
        
        Returns:
            Résultat de l'auto-évaluation
        """
        self.state.reflection_active = True
        assessment = await self.reflection.self_assess()
        self.state.last_assessment = assessment.to_dict()
        self.state.reflection_active = False
        
        # Notifier les callbacks
        await self._notify_assessment(assessment)
        
        return assessment
    
    async def learn_from_feedback(
        self,
        interaction_id: str,
        rating: float,
        correction: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apprend depuis un feedback utilisateur
        
        Args:
            interaction_id: ID de l'interaction
            rating: Score de satisfaction
            correction: Correction optionnelle
            
        Returns:
            Résultat de l'apprentissage
        """
        if not self.feedback_loop:
            return {"status": "error", "reason": "No feedback loop configured"}
        
        result = await self.feedback_loop.process_feedback(
            interaction_id=interaction_id,
            rating=rating,
            correction=correction
        )
        
        # Déclencher une réflexion si feedback négatif
        if rating < -0.3:
            await self.reflect()
        
        return result
    
    def get_consciousness_report(self) -> Dict[str, Any]:
        """
        Génère un rapport complet de l'état de conscience
        
        Returns:
            Rapport consolidé
        """
        return {
            "state": self.state.to_dict(),
            "ethical_barriers": self.guardrails.get_barriers(),
            "violation_stats": self.guardrails.get_violation_stats(),
            "reflection_history": self.reflection.get_reflection_history(limit=5),
            "neuronal_weights": self.neuronal_engine.get_weights() if self.neuronal_engine else None
        }
    
    async def proactive_check(self) -> List[Dict[str, Any]]:
        """
        Effectue une vérification proactive (auto-déclenchée)
        
        Returns:
            Liste des actions proactives suggérées
        """
        suggestions = []
        
        # Vérifier l'état du système
        assessment = await self.reflect()
        
        # Analyser les lacunes
        for gap in assessment.gaps:
            if "cache" in gap.lower():
                suggestions.append({
                    "type": "optimization",
                    "action": "optimize_cache",
                    "reason": gap
                })
            elif "latency" in gap.lower():
                suggestions.append({
                    "type": "performance",
                    "action": "reduce_latency",
                    "reason": gap
                })
        
        # Vérifier les violations récentes
        violation_stats = self.guardrails.get_violation_stats()
        if violation_stats.get("total", 0) > 5:
            suggestions.append({
                "type": "security",
                "action": "review_ethical_settings",
                "reason": f"Multiple violations detected: {violation_stats['total']}"
            })
        
        return suggestions
    
    # === Callbacks ===
    
    def on_violation(self, callback) -> None:
        """Enregistre un callback pour les violations éthiques"""
        self._on_violation_callbacks.append(callback)
    
    def on_assessment(self, callback) -> None:
        """Enregistre un callback pour les auto-évaluations"""
        self._on_assessment_callbacks.append(callback)
    
    async def _notify_violation(self, validation: Dict[str, Any]) -> None:
        """Notifie les callbacks de violation"""
        for callback in self._on_violation_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(validation)
                else:
                    callback(validation)
            except Exception:
                pass
    
    async def _notify_assessment(self, assessment: SelfAssessment) -> None:
        """Notifie les callbacks d'évaluation"""
        for callback in self._on_assessment_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(assessment)
                else:
                    callback(assessment)
            except Exception:
                pass
    
    def __repr__(self) -> str:
        return (
            f"ConsciousnessBridge("
            f"awareness={self.state.awareness_level}, "
            f"barriers={len(self.guardrails.get_barriers())}, "
            f"violations={len(self.guardrails.violation_history)})"
        )
