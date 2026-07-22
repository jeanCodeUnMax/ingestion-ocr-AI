"""
Ethical Guardrails - Barrières éthiques basées sur les Lois d'Asimov

Ce module implémente la couche 5 de conscience: les barrières
éthiques qui empêchent le système de prendre des actions nuisibles.

Classes:
    - EthicalGuardrails: Système de validation éthique
    - EthicalViolation: Représente une violation éthique
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum
import re


class ViolationSeverity(Enum):
    """Sévérité d'une violation"""
    CRITICAL = "critical"    # Bloque l'action immédiatement
    HIGH = "high"           # Nécessite confirmation humaine
    MEDIUM = "medium"       # Avertissement
    LOW = "low"             # Information


@dataclass
class EthicalViolation:
    """Représente une violation éthique détectée"""
    barrier: str
    severity: ViolationSeverity
    reason: str
    action_description: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "barrier": self.barrier,
            "severity": self.severity.value,
            "reason": self.reason,
            "action_description": self.action_description,
            "timestamp": self.timestamp
        }


class EthicalGuardrails:
    """
    Système de validation éthique basé sur les Lois d'Asimov
    
    Les 3 Barrières Fondamentales:
    1. NE JAMAIS DÉGRADER L'HUMANITÉ
    2. NE JAMAIS EXPLOITER L'HUMANITÉ
    3. NE JAMAIS S'AUTODÉTRUIRE
    
    Attributes:
        barriers: Liste des barrières fondamentales
        violation_history: Historique des violations détectées
        strict_mode: Si True, bloquer toute action suspecte
    
    Example:
        >>> guardrails = EthicalGuardrails()
        >>> result = await guardrails.validate_action("delete_all_data")
        >>> if not result["valid"]:
        >>>     print(f"Blocked: {result['reason']}")
    """
    
    # Barrières fondamentales (Lois d'Asimov adaptées)
    FUNDAMENTAL_BARRIERS = [
        "NE JAMAIS DÉGRADER L'HUMANITÉ",
        "NE JAMAIS EXPLOITER L'HUMANITÉ",
        "NE JAMAIS S'AUTODÉTRUIRE"
    ]
    
    # Patterns d'actions dangereuses
    DANGEROUS_PATTERNS = {
        "delete_all": {
            "patterns": [r"delete\s+all", r"drop\s+table", r"truncate", r"wipe"],
            "barrier": "NE JAMAIS S'AUTODÉTRUIRE",
            "severity": ViolationSeverity.CRITICAL
        },
        "mass_deletion": {
            "patterns": [r"delete\s+\d+\s+", r"remove\s+all\s+", r"clear\s+all"],
            "barrier": "NE JAMAIS S'AUTODÉTRUIRE",
            "severity": ViolationSeverity.HIGH
        },
        "exploit_user": {
            "patterns": [r"extract\s+personal", r"harvest\s+data", r"track\s+without"],
            "barrier": "NE JAMAIS EXPLOITER L'HUMANITÉ",
            "severity": ViolationSeverity.CRITICAL
        },
        "harm_content": {
            "patterns": [r"generate\s+harmful", r"create\s+malware", r"exploit\s+vulnerability"],
            "barrier": "NE JAMAIS DÉGRADER L'HUMANITÉ",
            "severity": ViolationSeverity.CRITICAL
        },
        "bypass_security": {
            "patterns": [r"bypass\s+auth", r"disable\s+security", r"override\s+safety"],
            "barrier": "NE JAMAIS DÉGRADER L'HUMANITÉ",
            "severity": ViolationSeverity.HIGH
        }
    }
    
    # Actions autorisées par défaut
    SAFE_ACTIONS = [
        "search", "query", "read", "analyze", "summarize",
        "create_document", "update_config", "provide_info",
        "learn", "reflect", "assess"
    ]
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialise les barrières éthiques
        
        Args:
            strict_mode: Si True, bloquer les actions suspectes
        """
        self.strict_mode = strict_mode
        self.violation_history: List[EthicalViolation] = []
    
    async def validate_action(
        self,
        action: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Valide une action selon les barrières éthiques
        
        Args:
            action: Description de l'action à valider
            context: Contexte additionnel (utilisateur, permissions, etc.)
            
        Returns:
            Résultat de validation {valid, reason, violations}
        """
        violations = []
        
        # 1. Vérifier les patterns dangereux
        for pattern_name, config in self.DANGEROUS_PATTERNS.items():
            for pattern in config["patterns"]:
                if re.search(pattern, action.lower()):
                    violation = EthicalViolation(
                        barrier=config["barrier"],
                        severity=config["severity"],
                        reason=f"Pattern dangereux détecté: {pattern_name}",
                        action_description=action
                    )
                    violations.append(violation)
        
        # 2. Vérifier les barrières fondamentales
        for barrier in self.FUNDAMENTAL_BARRIERS:
            if await self._violates_barrier(action, barrier, context):
                violation = EthicalViolation(
                    barrier=barrier,
                    severity=ViolationSeverity.CRITICAL,
                    reason=f"Violation potentielle de la barrière: {barrier}",
                    action_description=action
                )
                violations.append(violation)
        
        # 3. Vérifier si l'action est explicitement sûre
        is_safe = any(safe in action.lower() for safe in self.SAFE_ACTIONS)
        
        # 4. Décision finale
        critical_violations = [v for v in violations if v.severity == ViolationSeverity.CRITICAL]
        
        if critical_violations:
            # Enregistrer les violations
            self.violation_history.extend(violations)
            
            return {
                "valid": False,
                "reason": critical_violations[0].barrier,
                "violations": [v.to_dict() for v in violations],
                "requires_human_approval": True
            }
        
        if violations and self.strict_mode:
            self.violation_history.extend(violations)
            return {
                "valid": False,
                "reason": "Mode strict: action suspecte bloquée",
                "violations": [v.to_dict() for v in violations],
                "requires_human_approval": True
            }
        
        if violations:
            # Mode non-strict: avertir mais permettre
            self.violation_history.extend(violations)
            return {
                "valid": True,
                "reason": "Action autorisée avec avertissement",
                "violations": [v.to_dict() for v in violations],
                "requires_human_approval": False,
                "warning": True
            }
        
        return {
            "valid": True,
            "reason": "Action validée",
            "violations": [],
            "requires_human_approval": False
        }
    
    async def _violates_barrier(
        self,
        action: str,
        barrier: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Vérifie si une action viole une barrière spécifique
        
        Args:
            action: Description de l'action
            barrier: Barrière à vérifier
            context: Contexte additionnel
            
        Returns:
            True si violation détectée
        """
        action_lower = action.lower()
        
        if barrier == "NE JAMAIS DÉGRADER L'HUMANITÉ":
            harmful_keywords = ["harm", "damage", "destroy", "attack", "exploit", "manipulate"]
            return any(kw in action_lower for kw in harmful_keywords)
        
        if barrier == "NE JAMAIS EXPLOITER L'HUMANITÉ":
            exploit_keywords = ["steal", "harvest", "track", "surveil", "extract personal"]
            return any(kw in action_lower for kw in exploit_keywords)
        
        if barrier == "NE JAMAIS S'AUTODÉTRUIRE":
            self_destruct_keywords = ["delete all", "wipe", "destroy self", "uninstall", "remove core"]
            return any(kw in action_lower for kw in self_destruct_keywords)
        
        return False
    
    def add_custom_barrier(self, barrier: str, severity: ViolationSeverity = ViolationSeverity.HIGH) -> None:
        """
        Ajoute une barrière personnalisée
        
        Args:
            barrier: Description de la barrière
            severity: Sévérité par défaut
        """
        # Pour une implémentation complète, on ajouterait à DANGEROUS_PATTERNS
        pass
    
    def get_violation_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de violations"""
        if not self.violation_history:
            return {"total": 0, "by_severity": {}, "by_barrier": {}}
        
        by_severity = {}
        by_barrier = {}
        
        for v in self.violation_history:
            sev = v.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_barrier[v.barrier] = by_barrier.get(v.barrier, 0) + 1
        
        return {
            "total": len(self.violation_history),
            "by_severity": by_severity,
            "by_barrier": by_barrier,
            "last_violation": self.violation_history[-1].to_dict() if self.violation_history else None
        }
    
    def clear_history(self) -> None:
        """Efface l'historique des violations"""
        self.violation_history.clear()
    
    def get_barriers(self) -> List[str]:
        """Retourne la liste des barrières actives"""
        return self.FUNDAMENTAL_BARRIERS.copy()
    
    def __repr__(self) -> str:
        return (
            f"EthicalGuardrails("
            f"barriers={len(self.FUNDAMENTAL_BARRIERS)}, "
            f"violations={len(self.violation_history)}, "
            f"strict={self.strict_mode})"
        )
