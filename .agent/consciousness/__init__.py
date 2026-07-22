"""
Consciousness Module - Modules de conscience artificielle

Ce package implémente les 8 couches de conscience artificielle
inspirées de SYNTHÈSE_CONSCIENCE_ARTIFICIELLE.md.

Architecture 8 Couches:
    1. Awareness - Perception de l'environnement
    2. Reflection - Auto-questions
    3. CausalTree - Analyse causale
    4. Curiosity - Soif d'apprentissage
    5. EthicalGuardrails - Barrières éthiques (Asimov)
    6. InnerVoice - Auto-questionnement
    7. Intention - Génération d'intentions
    8. Action - Exécution d'actions

Usage:
    >>> from consciousness import ReflectionEngine, EthicalGuardrails
    >>> engine = ReflectionEngine()
    >>> assessment = await engine.self_assess()
"""

from .reflection import ReflectionEngine
from .ethical_guardrails import EthicalGuardrails
from .bridge import ConsciousnessBridge

__all__ = [
    "ReflectionEngine",
    "EthicalGuardrails",
    "ConsciousnessBridge"
]

__version__ = "1.0.0"
