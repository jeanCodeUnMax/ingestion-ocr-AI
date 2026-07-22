"""
Causal Tree Engine - Arbre de causes pour le système de conscience

Ce module implémente un système de thinking avancé qui construit
des arbres de causes pour identifier les racines des problèmes
et améliorer l'apprentissage neuronal.

Architecture:
1. DÉTECTION: Identifier un problème
2. ANALYSE: Construire l'arbre de causes
3. PARADIGME: Identifier le pattern de solution
4. APPRENTISSAGE: Intégrer dans le système neuronal
5. PRÉDICTION: Anticiper les problèmes futurs

Usage:
    tree = CausalTreeEngine(zvec_store, neuronal_engine)
    analysis = await tree.analyze_problem("Cache hit rate < 50%")
    print(analysis.root_cause)
"""

import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime
from pathlib import Path
from enum import Enum
import math


class CauseType(Enum):
    """Types de causes"""
    ROOT = "root"              # Cause racine
    PRIMARY = "primary"        # Cause primaire
    SECONDARY = "secondary"    # Cause secondaire
    SYMPTOM = "symptom"        # Symptôme visible
    CONTEXTUAL = "contextual"  # Facteur contextuel


class ParadigmType(Enum):
    """Paradigmes de solution"""
    CACHE_OPTIMIZATION = "cache_optimization"
    PERFORMANCE_TUNING = "performance_tuning"
    ERROR_HANDLING = "error_handling"
    ARCHITECTURE_REFACTOR = "architecture_refactor"
    RESOURCE_SCALING = "resource_scaling"
    DATA_QUALITY = "data_quality"
    CONFIGURATION_FIX = "configuration_fix"
    ALGORITHM_IMPROVEMENT = "algorithm_improvement"


@dataclass
class CauseNode:
    """Noeud de cause dans l'arbre"""
    id: str
    description: str
    cause_type: CauseType
    probability: float  # 0.0 - 1.0
    impact: float       # 0.0 - 1.0
    children: List['CauseNode'] = field(default_factory=list)
    parent: Optional['CauseNode'] = None
    evidence: List[str] = field(default_factory=list)
    solution_hint: Optional[str] = None
    
    def add_child(self, child: 'CauseNode'):
        child.parent = self
        self.children.append(child)
    
    def get_depth(self) -> int:
        if not self.children:
            return 1
        return 1 + max(c.get_depth() for c in self.children)
    
    def get_all_causes(self) -> List['CauseNode']:
        causes = [self]
        for child in self.children:
            causes.extend(child.get_all_causes())
        return causes
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "type": self.cause_type.value,
            "probability": self.probability,
            "impact": self.impact,
            "evidence": self.evidence,
            "solution_hint": self.solution_hint,
            "children": [c.to_dict() for c in self.children]
        }


@dataclass
class CausalAnalysis:
    """Résultat d'une analyse causale"""
    problem_id: str
    problem_description: str
    root_causes: List[CauseNode]
    paradigm: ParadigmType
    confidence: float
    recommended_actions: List[str]
    learning_weights: Dict[str, float]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "problem_id": self.problem_id,
            "problem_description": self.problem_description,
            "root_causes": [rc.to_dict() for rc in self.root_causes],
            "paradigm": self.paradigm.value,
            "confidence": self.confidence,
            "recommended_actions": self.recommended_actions,
            "learning_weights": self.learning_weights,
            "timestamp": self.timestamp
        }


class CausalTreeEngine:
    """
    Moteur d'arbre de causes pour le système de conscience
    
    Ce moteur implémente un système de thinking avancé qui:
    1. Analyse les problèmes en profondeur
    2. Construit des arbres de causes hiérarchiques
    3. Identifie les racines (root causes)
    4. Trouve le paradigme de solution
    5. Intègre l'apprentissage dans le système neuronal
    
    Attributes:
        zvec_store: Store vectoriel pour recherche sémantique
        neuronal_engine: Moteur neuronal pour apprentissage
        cause_database: Base de connaissances des causes connues
        paradigm_rules: Règles de détection des paradigmes
    
    Example:
        >>> engine = CausalTreeEngine(zvec, neuronal)
        >>> analysis = await engine.analyze_problem("Latence élevée")
        >>> print(f"Root cause: {analysis.root_causes[0].description}")
    """
    
    # Patterns de causes connues
    CAUSE_PATTERNS = {
        "cache": {
            "keywords": ["cache", "hit rate", "miss", "ttl", "eviction"],
            "root_causes": [
                ("ttl_trop_court", "TTL du cache trop court"),
                ("max_entries_insuffisant", "Nombre max d'entrées insuffisant"),
                ("eviction_policy_inadaptée", "Politique d'éviction inadaptée"),
                ("cache_non_persistant", "Cache non persistant entre sessions")
            ],
            "paradigm": ParadigmType.CACHE_OPTIMIZATION
        },
        "performance": {
            "keywords": ["lent", "latence", "timeout", "performance", "délai"],
            "root_causes": [
                ("requête_non_optimisée", "Requête non optimisée"),
                ("index_manquant", "Index manquant"),
                ("batch_non_utilisé", "Traitement batch non utilisé"),
                ("algorithme_sous_optimal", "Algorithme sous-optimal"),
                ("ressources_insuffisantes", "Ressources insuffisantes")
            ],
            "paradigm": ParadigmType.PERFORMANCE_TUNING
        },
        "error": {
            "keywords": ["erreur", "exception", "crash", "fail", "bug"],
            "root_causes": [
                ("validation_manquante", "Validation des entrées manquante"),
                ("gestion_erreur_incomplete", "Gestion d'erreur incomplète"),
                ("condition_race", "Condition de race"),
                ("ressource_non_libérée", "Ressource non libérée"),
                ("état_invalide", "État invalide non géré")
            ],
            "paradigm": ParadigmType.ERROR_HANDLING
        },
        "architecture": {
            "keywords": ["architecture", "modulaire", "couplage", "dette technique"],
            "root_causes": [
                ("couplage_fort", "Couplage fort entre composants"),
                ("responsabilité_mal_définie", "Responsabilités mal définies"),
                ("abstraction_insuffisante", "Abstraction insuffisante"),
                ("dépendance_circulaire", "Dépendance circulaire")
            ],
            "paradigm": ParadigmType.ARCHITECTURE_REFACTOR
        },
        "data": {
            "keywords": ["données", "qualité", "incohérence", "manquant", "corrompu"],
            "root_causes": [
                ("validation_données_absente", "Validation des données absente"),
                ("source_non_fiable", "Source de données non fiable"),
                ("transformation_erronée", "Transformation erronée"),
                ("synchronisation_défaillante", "Synchronisation défaillante")
            ],
            "paradigm": ParadigmType.DATA_QUALITY
        },
        "config": {
            "keywords": ["config", "paramètre", "settings", "environnement"],
            "root_causes": [
                ("paramètre_incorrect", "Paramètre incorrect"),
                ("environnement_mal_configuré", "Environnement mal configuré"),
                ("valeur_par_défaut_inadaptée", "Valeur par défaut inadaptée"),
                ("config_non_rechargée", "Configuration non rechargée")
            ],
            "paradigm": ParadigmType.CONFIGURATION_FIX
        }
    }
    
    # Règles de propagation des causes
    PROPAGATION_RULES = {
        "cache": ["performance", "error"],
        "performance": ["error", "architecture"],
        "error": ["data", "config"],
        "architecture": ["performance", "config"],
        "data": ["error", "performance"],
        "config": ["error", "performance"]
    }
    
    def __init__(
        self,
        zvec_store=None,
        neuronal_engine=None,
        knowledge_path: str = ".agent/consciousness/causal_knowledge.json"
    ):
        self.zvec = zvec_store
        self.neuronal = neuronal_engine
        self.knowledge_path = Path(knowledge_path)
        
        # Base de connaissances
        self.known_problems: Dict[str, CausalAnalysis] = {}
        self.cause_frequency: Dict[str, int] = {}
        self.paradigm_success_rate: Dict[ParadigmType, float] = {}
        
        # Charger les connaissances existantes
        self._load_knowledge()
    
    def _load_knowledge(self):
        """Charge les connaissances causales existantes"""
        if self.knowledge_path.exists():
            with open(self.knowledge_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # Restaurer les fréquences
                self.cause_frequency = data.get("cause_frequency", {})
                
                # Restaurer les taux de succès
                for p_name, rate in data.get("paradigm_success_rate", {}).items():
                    try:
                        paradigm = ParadigmType(p_name)
                        self.paradigm_success_rate[paradigm] = rate
                    except ValueError:
                        pass
    
    def _save_knowledge(self):
        """Sauvegarde les connaissances causales"""
        self.knowledge_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "cause_frequency": self.cause_frequency,
            "paradigm_success_rate": {
                p.value: rate for p, rate in self.paradigm_success_rate.items()
            },
            "last_updated": datetime.now().isoformat()
        }
        
        with open(self.knowledge_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    async def analyze_problem(
        self,
        problem_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> CausalAnalysis:
        """
        Analyse un problème et construit l'arbre de causes
        
        Args:
            problem_description: Description du problème
            context: Contexte additionnel (métriques, logs, etc.)
            
        Returns:
            Analyse causale complète avec arbre
        """
        problem_id = f"prob_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 1. Identifier le domaine du problème
        domain = self._identify_domain(problem_description)
        
        # 2. Construire l'arbre de causes
        root_causes = await self._build_causal_tree(problem_description, domain, context)
        
        # 3. Identifier le paradigme
        paradigm = self._identify_paradigm(domain, root_causes)
        
        # 4. Calculer la confiance
        confidence = self._calculate_confidence(root_causes, domain)
        
        # 5. Générer les actions recommandées
        recommended_actions = self._generate_recommendations(root_causes, paradigm)
        
        # 6. Calculer les poids d'apprentissage
        learning_weights = self._calculate_learning_weights(root_causes, paradigm)
        
        # 7. Créer l'analyse
        analysis = CausalAnalysis(
            problem_id=problem_id,
            problem_description=problem_description,
            root_causes=root_causes,
            paradigm=paradigm,
            confidence=confidence,
            recommended_actions=recommended_actions,
            learning_weights=learning_weights
        )
        
        # 8. Enregistrer dans la base de connaissances
        self.known_problems[problem_id] = analysis
        
        # 9. Mettre à jour les fréquences
        for root_cause in root_causes:
            cause_id = root_cause.id
            self.cause_frequency[cause_id] = self.cause_frequency.get(cause_id, 0) + 1
        
        # 10. Sauvegarder
        self._save_knowledge()
        
        # 11. Intégrer dans le système neuronal
        if self.neuronal:
            await self._integrate_with_neuronal(analysis)
        
        return analysis
    
    def _identify_domain(self, description: str) -> str:
        """Identifie le domaine du problème"""
        desc_lower = description.lower()
        
        scores = {}
        for domain, pattern in self.CAUSE_PATTERNS.items():
            score = sum(1 for kw in pattern["keywords"] if kw in desc_lower)
            if score > 0:
                scores[domain] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        return "error"  # Domaine par défaut
    
    async def _build_causal_tree(
        self,
        description: str,
        domain: str,
        context: Optional[Dict[str, Any]]
    ) -> List[CauseNode]:
        """Construit l'arbre de causes"""
        
        pattern = self.CAUSE_PATTERNS.get(domain, self.CAUSE_PATTERNS["error"])
        
        root_causes = []
        
        # Pour chaque cause racine potentielle
        for cause_id, cause_desc in pattern["root_causes"]:
            # Calculer la probabilité
            probability = self._estimate_probability(cause_id, description, context)
            
            # Si probabilité significative
            if probability > 0.3:
                # Créer le noeud racine
                root_node = CauseNode(
                    id=cause_id,
                    description=cause_desc,
                    cause_type=CauseType.ROOT,
                    probability=probability,
                    impact=self._estimate_impact(cause_id, domain),
                    evidence=self._gather_evidence(cause_id, description, context),
                    solution_hint=self._get_solution_hint(cause_id, domain)
                )
                
                # Construire les causes secondaires
                secondary_causes = self._build_secondary_causes(root_node, domain)
                for secondary in secondary_causes:
                    root_node.add_child(secondary)
                
                root_causes.append(root_node)
        
        # Trier par impact * probabilité
        root_causes.sort(key=lambda c: c.probability * c.impact, reverse=True)
        
        return root_causes[:3]  # Top 3 causes racines
    
    def _build_secondary_causes(
        self,
        parent: CauseNode,
        domain: str
    ) -> List[CauseNode]:
        """Construit les causes secondaires"""
        
        # Règles de causes secondaires
        SECONDARY_RULES = {
            "ttl_trop_court": [
                ("config_ttl_basse", "Configuration TTL trop basse"),
                ("données_changent_souvent", "Données changent fréquemment")
            ],
            "max_entries_insuffisant": [
                ("mémoire_limitée", "Mémoire limitée"),
                ("volume_données_élevé", "Volume de données élevé")
            ],
            "requête_non_optimisée": [
                ("index_non_utilisé", "Index non utilisé"),
                ("jointure_couteuse", "Jointure coûteuse"),
                ("scan_complet", "Scan complet de table")
            ],
            "validation_manquante": [
                ("hypothèses_implicit", "Hypothèses implicites"),
                ("edge_case_non_géré", "Edge case non géré")
            ]
        }
        
        secondary = []
        
        if parent.id in SECONDARY_RULES:
            for cause_id, cause_desc in SECONDARY_RULES[parent.id]:
                node = CauseNode(
                    id=cause_id,
                    description=cause_desc,
                    cause_type=CauseType.SECONDARY,
                    probability=parent.probability * 0.7,
                    impact=parent.impact * 0.6,
                    parent=parent
                )
                secondary.append(node)
        
        return secondary
    
    def _estimate_probability(
        self,
        cause_id: str,
        description: str,
        context: Optional[Dict[str, Any]]
    ) -> float:
        """Estime la probabilité d'une cause"""
        
        # Probabilité de base
        base_prob = 0.5
        
        # Ajuster selon la fréquence historique
        freq = self.cause_frequency.get(cause_id, 0)
        if freq > 0:
            # Plus une cause est fréquente, plus elle est probable
            base_prob += min(0.3, freq * 0.05)
        
        # Ajuster selon le contexte
        if context:
            metrics = context.get("metrics", {})
            
            # Règles spécifiques
            if cause_id == "ttl_trop_court" and "cache_hit_rate" in metrics:
                if metrics["cache_hit_rate"] < 0.5:
                    base_prob += 0.3
            
            if cause_id == "max_entries_insuffisant" and "cache_size" in metrics:
                if metrics["cache_size"] > 0.9:
                    base_prob += 0.3
            
            if cause_id == "requête_non_optimisée" and "latency_ms" in metrics:
                if metrics["latency_ms"] > 500:
                    base_prob += 0.3
        
        return min(1.0, base_prob)
    
    def _estimate_impact(self, cause_id: str, domain: str) -> float:
        """Estime l'impact d'une cause"""
        
        # Impacts prédéfinis
        IMPACT_SCORES = {
            "ttl_trop_court": 0.8,
            "max_entries_insuffisant": 0.7,
            "requête_non_optimisée": 0.9,
            "validation_manquante": 0.6,
            "couplage_fort": 0.7,
            "paramètre_incorrect": 0.5,
            "algorithme_sous_optimal": 0.8
        }
        
        return IMPACT_SCORES.get(cause_id, 0.5)
    
    def _gather_evidence(
        self,
        cause_id: str,
        description: str,
        context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Rassemble les preuves pour une cause"""
        
        evidence = []
        
        if context:
            metrics = context.get("metrics", {})
            logs = context.get("logs", [])
            
            # Règles d'évidence
            if cause_id == "ttl_trop_court":
                if "cache_hit_rate" in metrics:
                    evidence.append(f"Cache hit rate: {metrics['cache_hit_rate']}")
                if "ttl_seconds" in metrics:
                    evidence.append(f"TTL configuré: {metrics['ttl_seconds']}s")
            
            if cause_id == "requête_non_optimisée":
                if "latency_ms" in metrics:
                    evidence.append(f"Latence: {metrics['latency_ms']}ms")
                if "query_count" in metrics:
                    evidence.append(f"Nombre de requêtes: {metrics['query_count']}")
        
        return evidence
    
    def _get_solution_hint(self, cause_id: str, domain: str) -> str:
        """Obtient un indice de solution pour une cause"""
        
        SOLUTION_HINTS = {
            "ttl_trop_court": "Augmenter le TTL du cache",
            "max_entries_insuffisant": "Augmenter max_entries ou utiliser LRU",
            "requête_non_optimisée": "Ajouter des index ou optimiser la requête",
            "validation_manquante": "Ajouter des validators en entrée",
            "couplage_fort": "Découpler avec des interfaces",
            "paramètre_incorrect": "Vérifier et corriger la configuration",
            "algorithme_sous_optimal": "Utiliser un algorithme plus efficace"
        }
        
        return SOLUTION_HINTS.get(cause_id, "Analyser et corriger")
    
    def _identify_paradigm(
        self,
        domain: str,
        root_causes: List[CauseNode]
    ) -> ParadigmType:
        """Identifie le paradigme de solution"""
        
        pattern = self.CAUSE_PATTERNS.get(domain)
        if pattern:
            return pattern["paradigm"]
        
        return ParadigmType.ERROR_HANDLING
    
    def _calculate_confidence(
        self,
        root_causes: List[CauseNode],
        domain: str
    ) -> float:
        """Calcule la confiance de l'analyse"""
        
        if not root_causes:
            return 0.3
        
        # Moyenne des probabilités
        avg_prob = sum(c.probability for c in root_causes) / len(root_causes)
        
        # Moyenne des impacts
        avg_impact = sum(c.impact for c in root_causes) / len(root_causes)
        
        # Profondeur de l'arbre
        max_depth = max(c.get_depth() for c in root_causes)
        depth_bonus = min(0.2, max_depth * 0.05)
        
        # Fréquence du domaine
        domain_freq = sum(
            self.cause_frequency.get(c.id, 0)
            for c in root_causes
        )
        freq_bonus = min(0.15, domain_freq * 0.02)
        
        confidence = (avg_prob * 0.4 + avg_impact * 0.3 + 0.2 + depth_bonus + freq_bonus)
        
        return min(1.0, confidence)
    
    def _generate_recommendations(
        self,
        root_causes: List[CauseNode],
        paradigm: ParadigmType
    ) -> List[str]:
        """Génère les recommandations d'action"""
        
        recommendations = []
        
        # Recommandations basées sur les causes racines
        for cause in root_causes:
            if cause.solution_hint:
                recommendations.append(f"[{cause.id}] {cause.solution_hint}")
            
            # Recommandations secondaires
            for child in cause.children:
                if child.solution_hint:
                    recommendations.append(f"  - {child.solution_hint}")
        
        # Recommandations basées sur le paradigme
        PARADIGM_ACTIONS = {
            ParadigmType.CACHE_OPTIMIZATION: [
                "Analyser le cache hit rate actuel",
                "Ajuster TTL et max_entries",
                "Considérer une politique LRU"
            ],
            ParadigmType.PERFORMANCE_TUNING: [
                "Profiler les goulots d'étranglement",
                "Optimiser les requêtes critiques",
                "Implémenter le caching"
            ],
            ParadigmType.ERROR_HANDLING: [
                "Ajouter des validations",
                "Implémenter des fallbacks",
                "Logger les erreurs"
            ],
            ParadigmType.ARCHITECTURE_REFACTOR: [
                "Identifier les couplages forts",
                "Définir des interfaces claires",
                "Planifier la refonte"
            ]
        }
        
        if paradigm in PARADIGM_ACTIONS:
            for action in PARADIGM_ACTIONS[paradigm]:
                if action not in recommendations:
                    recommendations.append(action)
        
        return recommendations[:10]  # Max 10 recommandations
    
    def _calculate_learning_weights(
        self,
        root_causes: List[CauseNode],
        paradigm: ParadigmType
    ) -> Dict[str, float]:
        """Calcule les poids d'apprentissage pour le système neuronal"""
        
        weights = {
            "semantic": 0.0,
            "recency": 0.0,
            "popularity": 0.0
        }
        
        # Ajuster selon le paradigme
        PARADIGM_WEIGHTS = {
            ParadigmType.CACHE_OPTIMIZATION: {
                "semantic": 0.1,   # Plus de poids sur la similarité
                "recency": 0.05,   # Récence importante
                "popularity": -0.05  # Popularité moins importante
            },
            ParadigmType.PERFORMANCE_TUNING: {
                "semantic": 0.05,
                "recency": 0.1,    # Récence très importante
                "popularity": 0.0
            },
            ParadigmType.ERROR_HANDLING: {
                "semantic": 0.1,   # Similarité importante pour erreurs similaires
                "recency": 0.0,
                "popularity": 0.05
            },
            ParadigmType.ARCHITECTURE_REFACTOR: {
                "semantic": 0.05,
                "recency": -0.05,  # Architecture stable = moins de récence
                "popularity": 0.1
            }
        }
        
        if paradigm in PARADIGM_WEIGHTS:
            weights = PARADIGM_WEIGHTS[paradigm].copy()
        
        # Ajuster selon la confiance des causes
        for cause in root_causes:
            confidence_factor = cause.probability * cause.impact
            weights["semantic"] += confidence_factor * 0.02
            weights["recency"] += confidence_factor * 0.01
        
        return weights
    
    async def _integrate_with_neuronal(self, analysis: CausalAnalysis):
        """Intègre l'analyse dans le système neuronal"""
        
        if not self.neuronal:
            return
        
        # Convertir l'analyse en feedback pour le système neuronal
        satisfaction = analysis.confidence * 0.5  # 0.0 à 0.5
        
        # Si le paradigme a un bon taux de succès, augmenter la satisfaction
        success_rate = self.paradigm_success_rate.get(analysis.paradigm, 0.5)
        satisfaction += success_rate * 0.3
        
        # Appliquer le feedback
        self.neuronal.feedback_loop(
            doc_id=analysis.problem_id,
            satisfaction=satisfaction,
            context={
                "paradigm": analysis.paradigm.value,
                "root_causes": [c.id for c in analysis.root_causes],
                "weights": analysis.learning_weights
            }
        )
        
        # Ajuster les poids selon les recommandations
        for key, delta in analysis.learning_weights.items():
            if key in self.neuronal.weights:
                new_weight = self.neuronal.weights[key] + delta
                self.neuronal.weights[key] = max(
                    self.neuronal.min_weight,
                    min(self.neuronal.max_weight, new_weight)
                )
        
        # Renormaliser
        self.neuronal._normalize_weights()
    
    def report_solution_success(
        self,
        problem_id: str,
        success: bool
    ):
        """
        Rapporte le succès ou l'échec d'une solution
        
        Args:
            problem_id: ID du problème
            success: True si la solution a fonctionné
        """
        if problem_id not in self.known_problems:
            return
        
        analysis = self.known_problems[problem_id]
        
        # Mettre à jour le taux de succès du paradigme
        current_rate = self.paradigm_success_rate.get(analysis.paradigm, 0.5)
        
        # Moyenne mobile
        new_rate = current_rate * 0.9 + (1.0 if success else 0.0) * 0.1
        self.paradigm_success_rate[analysis.paradigm] = new_rate
        
        # Sauvegarder
        self._save_knowledge()
        
        # Feedback au système neuronal
        if self.neuronal:
            satisfaction = 1.0 if success else -0.5
            self.neuronal.feedback_loop(problem_id, satisfaction)
    
    def get_causal_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques causales"""
        return {
            "total_problems_analyzed": len(self.known_problems),
            "cause_frequency": dict(sorted(
                self.cause_frequency.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]),
            "paradigm_success_rate": {
                p.value: rate for p, rate in self.paradigm_success_rate.items()
            },
            "most_common_paradigms": self._get_most_common_paradigms()
        }
    
    def _get_most_common_paradigms(self) -> List[str]:
        """Obtient les paradigmes les plus courants"""
        paradigm_counts = {}
        
        for analysis in self.known_problems.values():
            p = analysis.paradigm.value
            paradigm_counts[p] = paradigm_counts.get(p, 0) + 1
        
        return sorted(paradigm_counts.keys(), key=lambda x: paradigm_counts[x], reverse=True)[:5]
    
    def visualize_tree(self, analysis: CausalAnalysis) -> str:
        """Génère une représentation textuelle de l'arbre"""
        
        lines = []
        lines.append(f"ARBRE DE CAUSES: {analysis.problem_description}")
        lines.append(f"Paradigme: {analysis.paradigm.value}")
        lines.append(f"Confiance: {analysis.confidence:.2%}")
        lines.append("")
        
        for i, root in enumerate(analysis.root_causes, 1):
            lines.append(f"CAUSE RACINE #{i}: {root.description}")
            lines.append(f"  Probabilité: {root.probability:.2%}")
            lines.append(f"  Impact: {root.impact:.2%}")
            
            if root.evidence:
                lines.append(f"  Preuves:")
                for ev in root.evidence:
                    lines.append(f"    - {ev}")
            
            if root.solution_hint:
                lines.append(f"  Solution: {root.solution_hint}")
            
            if root.children:
                lines.append(f"  Causes secondaires:")
                for child in root.children:
                    lines.append(f"    - {child.description} ({child.probability:.2%})")
            
            lines.append("")
        
        lines.append("RECOMMANDATIONS:")
        for rec in analysis.recommended_actions:
            lines.append(f"  {rec}")
        
        return "\n".join(lines)


# ===================================================================
# Intégration avec le système de conscience
# ===================================================================

async def integrate_causal_tree_with_consciousness(
    consciousness_bridge,
    causal_engine: CausalTreeEngine
):
    """
    Intègre le moteur d'arbre de causes avec le système de conscience
    
    Cette fonction connecte l'analyse causale au cycle de réveil
    pour une analyse automatique des problèmes.
    """
    
    async def on_wake_callback(manifest):
        """Callback appelé à chaque réveil"""
        
        # Analyser les problèmes détectés
        problems = manifest.get("problem_database", [])
        
        for problem in problems:
            if not problem.get("analyzed", False):
                # Lancer l'analyse causale
                analysis = await causal_engine.analyze_problem(
                    problem.get("description", ""),
                    context=problem.get("context")
                )
                
                # Marquer comme analysé
                problem["analyzed"] = True
                problem["causal_analysis"] = analysis.to_dict()
                
                print(f"[CAUSAL] Problème analysé: {analysis.problem_id}")
                print(f"  Causes racines: {len(analysis.root_causes)}")
                print(f"  Paradigme: {analysis.paradigm.value}")
    
    # Enregistrer le callback
    if hasattr(consciousness_bridge, 'on_wake_callback'):
        consciousness_bridge.on_wake_callback = on_wake_callback


# ===================================================================
# Example d'utilisation
# ===================================================================

async def example_usage():
    """Exemple d'utilisation du moteur d'arbre de causes"""
    
    # Créer le moteur
    engine = CausalTreeEngine(
        zvec_store=None,
        neuronal_engine=None
    )
    
    # Analyser un problème
    analysis = await engine.analyze_problem(
        "Cache hit rate < 50%, performances très lentes",
        context={
            "metrics": {
                "cache_hit_rate": 0.42,
                "latency_ms": 850,
                "ttl_seconds": 60
            }
        }
    )
    
    # Afficher l'arbre
    print(engine.visualize_tree(analysis))
    
    # Rapporter le succès
    engine.report_solution_success(analysis.problem_id, success=True)
    
    # Afficher les stats
    print("\nSTATISTIQUES:")
    print(json.dumps(engine.get_causal_stats(), indent=2))


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
