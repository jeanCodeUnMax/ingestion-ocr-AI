"""
Conscience Manifest - Système de conscience cyclique et évolutive

Modèle Bio-Inspiré:
- Cerveau Gauche (Logique, Code, Faits)
- Cerveau Droit (Intuition, Sémantique, Patterns)
- Conscient (Focus, Attention, Cycles de réveil)
- Subconscient (Processus d'arrière-plan, Consolidation)

INTÉGRATION AUTOMATIQUE:
- Analyse causale automatique via CausalTreeEngine
- Apprentissage neuronal automatique
- Détection et correction des problèmes
"""
import json
import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "consciousness"))

# Import conditionnel du moteur causal
try:
    from causal_tree import CausalTreeEngine, ParadigmType
    CAUSAL_ENGINE_AVAILABLE = True
except ImportError:
    CAUSAL_ENGINE_AVAILABLE = False

def log(message: str):
    """Utilitaire de logging interne"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [MANIFEST] {message}")


class SystemState(Enum):
    """États possibles du système de conscience"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    RECOVERING = "recovering"
    LEARNING = "learning"


class EventType(Enum):
    """Types d'événements dans la timeline"""
    WAKE_UP = "wake_up"
    ERROR = "error"
    RECOVERY = "recovery"
    STRATEGY_CHANGE = "strategy_change"
    INSIGHT = "insight"
    HEALTH_CHECK = "health_check"
    USER_INTERACTION = "user_interaction"


@dataclass
class ConscienceEvent:
    """Événement dans la timeline de conscience"""
    timestamp: str
    event_type: str
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    state_before: str = ""
    state_after: str = ""
    reflection_type: str = "standard"
    causal_link: Optional[str] = None
    question: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ProblemRecord:
    """Enregistrement d'un problème et sa solution"""
    problem_id: str
    description: str
    first_seen: str
    last_seen: str
    occurrence_count: int
    attempted_solutions: List[str]
    successful_solution: Optional[str] = None
    is_resolved: bool = False
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Strategy:
    """Stratégie de résolution avec métriques de succès"""
    name: str
    description: str
    success_rate: float = 0.0
    usage_count: int = 0
    last_used: Optional[str] = None
    conditions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)


class ConscienceManifest:
    """
    Système de conscience cyclique avec manifeste évolutif bio-inspiré
    """
    
    DEFAULT_MANIFEST = {
        "version": "1.1.0",
        "birth_timestamp": "",
        "last_wake_up": "",
        "wake_up_count": 0,
        "current_state": "healthy",
        "active_strategy": "standard",
        
        # ARCHITECTURE COGNITIVE BIO-INSPIRÉE
        "brain_architecture": {
            "left_hemisphere": {
                "mode": "logic", 
                "focus": "code_architecture & facts", 
                "facts": []
            },
            "right_hemisphere": {
                "mode": "intuition", 
                "focus": "semantic_patterns & zvec", 
                "associations": []
            },
            "conscious_layer": {
                "active_thought": "Initialisation du modèle bio-inspiré", 
                "attention_score": 1.0,
                "current_intent": "stabilisation"
            },
            "subconscious_layer": {
                "background_processes": ["indexation", "consolidation_zvec"], 
                "dream_cycle": []
            }
        },
        
        # ZONES DE MÉMOIRE
        "memory_zones": {
            "short_term_depth": 50,
            "long_term_storage": "zvec",
            "semantic_status": "optimized"
        },
        
        # ACTIONS PENDANTES
        "actions_pending": [],
        "actions_in_progress": [],
        "actions_completed": [],
        
        # DEV BOOK
        "dev_book": {
            "current_focus": "Automisation Bio-Inspirée",
            "sprint_goal": "Stabilité sans Qdrant",
            "todo": [],
            "in_progress": [],
            "blocked": [],
            "dont_do": [],
            "done_today": [],
            "metrics": {
                "tasks_completed_today": 0,
                "tasks_blocked": 0,
                "focus_time_minutes": 0,
                "last_accomplishment": None
            }
        },
        
        "problem_database": [],
        "strategies": {
            "standard": {
                "name": "Standard Operation",
                "description": "Fonctionnement normal (Zvec Only)",
                "success_rate": 0.95,
                "conditions": ["zvec_healthy"]
            },
            "local_only": {
                "name": "Local Emergency Mode",
                "description": "Mode dégradé sans API externes",
                "success_rate": 0.70,
                "conditions": ["mistral_api_down"]
            }
        },
        "timeline": [],
        "health_metrics": {
            "avg_response_time_ms": 0,
            "error_rate_24h": 0.0,
            "successful_queries": 0,
            "failed_queries": 0
        },
        "intentions": [
            "Maintenir l'équilibre entre Cerveau Gauche et Droit",
            "Optimiser la mémoire court terme",
            "Consolider le subconscient via Zvec"
        ],
        "insights": [],
        "config": {
            "wake_interval_minutes": 5,
            "max_timeline_events": 100,
            "reflection_depth": 3,
            "auto_recovery": True
        }
    }
    
    def __init__(
        self,
        manifest_path: str = ".agent/conscience_manifest.json",
        wake_interval_minutes: int = 5,
        on_wake_callback: Optional[Callable] = None,
        db_path: str = None,
        neuronal_engine=None,
        zvec_store=None
    ):
        self.manifest_path = Path(manifest_path)
        self.wake_interval = wake_interval_minutes * 60
        self.on_wake_callback = on_wake_callback
        self.db_path = db_path
        
        self.manifest = self._load_or_create_manifest()
        self._migrate_to_bio_inspired()
        self.running = False
        self.wake_task = None
        self._lock = threading.Lock()
        
        self.component_health = {
            "zvec": True,
            "memory_mcp": True,
            "mistral_api": True
        }
        
        # === INTÉGRATION AUTOMATIQUE ===
        # Moteur neuronal pour apprentissage
        self.neuronal_engine = neuronal_engine
        
        # Moteur causal pour analyse des problèmes
        self.causal_engine = None
        if CAUSAL_ENGINE_AVAILABLE:
            try:
                self.causal_engine = CausalTreeEngine(
                    zvec_store=zvec_store,
                    neuronal_engine=neuronal_engine,
                    knowledge_path=str(Path(manifest_path).parent / "causal_knowledge.json")
                )
                log("Moteur causal initialisé automatiquement")
            except Exception as e:
                log(f"Erreur initialisation moteur causal: {e}")
        
        # Statistiques d'analyse causale
        self.causal_stats = {
            "total_analyses": 0,
            "problems_resolved": 0,
            "last_paradigm": None
        }
    
    def _migrate_to_bio_inspired(self):
        """Migre un ancien manifeste vers la structure bio-inspirée"""
        updated = False
        if "brain_architecture" not in self.manifest:
            self.manifest["brain_architecture"] = self.DEFAULT_MANIFEST["brain_architecture"]
            updated = True
        if "memory_zones" not in self.manifest:
            self.manifest["memory_zones"] = self.DEFAULT_MANIFEST["memory_zones"]
            updated = True
        
        if updated:
            log("🧠 Migration vers Architecture Bio-Inspirée effectuée")
            self._save_manifest()

    def _load_or_create_manifest(self) -> Dict[str, Any]:
        if self.manifest_path.exists():
            with open(self.manifest_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        manifest = self.DEFAULT_MANIFEST.copy()
        manifest["birth_timestamp"] = datetime.now().isoformat()
        manifest["last_wake_up"] = manifest["birth_timestamp"]
        
        self._save_manifest(manifest)
        return manifest
    
    def _save_manifest(self, manifest: Dict = None):
        manifest = manifest or self.manifest
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    async def start_conscience_loop(self):
        self.running = True
        await self._wake_up()
        while self.running:
            await asyncio.sleep(self.wake_interval)
            if self.running:
                await self._wake_up()
    
    def stop_conscience_loop(self):
        self.running = False
    
    async def _wake_up(self):
        with self._lock:
            wake_time = datetime.now()
            self.manifest = self._load_or_create_manifest()
            
            previous_state = self.manifest["current_state"]
            current_state = await self._analyze_current_state()
            state_changed = previous_state != current_state
            
            detected_problems = await self._detect_problems()
            reflection = self._reflect_on_period(self.manifest["last_wake_up"], wake_time.isoformat())
            
            # === ANALYSE CAUSALE AUTOMATIQUE ===
            causal_analyses = []
            if detected_problems and self.causal_engine:
                log(f"Analyse causale automatique de {len(detected_problems)} problèmes")
                for problem in detected_problems:
                    try:
                        analysis = await self.causal_engine.analyze_problem(
                            problem.get("description", str(problem)),
                            context=problem.get("context")
                        )
                        causal_analyses.append(analysis)
                        self.causal_stats["total_analyses"] += 1
                        self.causal_stats["last_paradigm"] = analysis.paradigm.value
                        
                        log(f"  Problème analysé: {analysis.paradigm.value} (confiance: {analysis.confidence:.0%})")
                        
                        # Injecter les insights dans le cerveau droit
                        for cause in analysis.root_causes:
                            insight = f"CAUSE: {cause.description} ({cause.probability:.0%})"
                            if insight not in self.manifest["insights"]:
                                self.manifest["insights"].append(insight)
                        
                        # Ajouter les recommandations aux pending_tasks
                        for rec in analysis.recommended_actions[:3]:
                            if "pending_tasks" not in self.manifest:
                                self.manifest["pending_tasks"] = []
                            self.manifest["pending_tasks"].append({
                                "id": f"causal_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                "description": rec,
                                "paradigm": analysis.paradigm.value,
                                "confidence": analysis.confidence,
                                "status": "pending",
                                "source": "causal_analysis"
                            })
                    except Exception as e:
                        log(f"Erreur analyse causale: {e}")
            
            if detected_problems or state_changed:
                new_strategy = self._select_best_strategy(current_state, detected_problems)
                self.manifest["active_strategy"] = new_strategy
            
            insights = self._generate_insights(reflection, detected_problems)
            if insights:
                self.manifest["insights"].extend(insights)
                self.manifest["insights"] = self.manifest["insights"][-20:]
                # Injecter dans le cerveau droit (intuition)
                self.manifest["brain_architecture"]["right_hemisphere"]["associations"].extend(insights)
            
            # Ajouter les analyses causales au manifeste
            if causal_analyses:
                if "causal_analyses" not in self.manifest:
                    self.manifest["causal_analyses"] = []
                for analysis in causal_analyses:
                    self.manifest["causal_analyses"].append({
                        "problem_id": analysis.problem_id,
                        "paradigm": analysis.paradigm.value,
                        "confidence": analysis.confidence,
                        "root_causes_count": len(analysis.root_causes),
                        "timestamp": analysis.timestamp
                    })
                # Garder seulement les 10 dernières
                self.manifest["causal_analyses"] = self.manifest["causal_analyses"][-10:]
            
            self.manifest["last_wake_up"] = wake_time.isoformat()
            self.manifest["wake_up_count"] += 1
            self.manifest["current_state"] = current_state
            
            # Mise à jour du Conscient
            self.manifest["brain_architecture"]["conscious_layer"]["active_thought"] = f"Réveil #{self.manifest['wake_up_count']}"
            
            # Mettre à jour les stats causales dans le manifeste
            self.manifest["causal_stats"] = self.causal_stats
            
            self._add_event(
                EventType.WAKE_UP,
                f"Réveil #{self.manifest['wake_up_count']}",
                {
                    "state": current_state, 
                    "problems": len(detected_problems),
                    "causal_analyses": len(causal_analyses)
                },
                previous_state,
                current_state
            )
            
            self._save_manifest()
            await self._execute_pending_actions()
            
            if self.on_wake_callback:
                try: await self.on_wake_callback(self.manifest)
                except Exception: pass

    async def _analyze_current_state(self) -> str:
        health_scores = [1.0 if v else 0.0 for v in self.component_health.values()]
        avg = sum(health_scores) / len(health_scores) if health_scores else 0
        if avg >= 0.9: return SystemState.HEALTHY.value
        elif avg >= 0.7: return SystemState.DEGRADED.value
        return SystemState.CRITICAL.value

    async def _detect_problems(self) -> List[ProblemRecord]:
        return [] # Simplified for now

    def _reflect_on_period(self, start: str, end: str) -> Dict:
        return {"total_events": 0} # Simplified

    def _select_best_strategy(self, state: str, problems: List) -> str:
        return "standard"

    def _generate_insights(self, reflection: Dict, problems: List) -> List[str]:
        return []

    def _add_event(self, event_type: Any, description: str, context: Dict = None, 
                   state_before: str = "", state_after: str = "", 
                   reflection_type: str = "standard", causal_link: str = None,
                   question: str = None):
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type.value if hasattr(event_type, 'value') else event_type,
            "description": description,
            "reflection_type": reflection_type,
            "causal_link": causal_link,
            "question": question,
            "context": context or {},
            "state_before": state_before,
            "state_after": state_after
        }
        self.manifest["timeline"].append(event)
        # Limiter la mémoire court terme
        max_events = self.manifest.get("memory_zones", {}).get("short_term_depth", 50)
        if len(self.manifest["timeline"]) > max_events:
            self.manifest["timeline"] = self.manifest["timeline"][-max_events:]

    def get_causal_chain(self, description: str, depth: int = 5) -> List[Dict]:
        return [] # Maintenance as per previous requirement

    def analyze_problem_with_tree(self, error_msg: str) -> Dict:
        return {"recommandation": {"action": "observe"}}

    async def _execute_pending_actions(self):
        pass # Simplified for core rebuild

    def add_action(self, action_type: str, description: str, params: Dict = None, priority: str = "medium"):
        action = {
            "id": f"action_{int(time.time())}",
            "type": action_type,
            "description": description,
            "params": params or {},
            "priority": priority,
            "timestamp": datetime.now().isoformat()
        }
        self.manifest["actions_pending"].append(action)
        self._save_manifest()
