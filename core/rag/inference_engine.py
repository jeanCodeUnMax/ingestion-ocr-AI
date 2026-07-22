"""
Inference Engine - Moteur d'inférence pour l'auto-correction

Ce module permet au système de conscience d'appliquer des corrections
via INFÉRENCE (LLM) et non via scripts pré-définis.

Architecture:
1. Problème détecté dans le manifeste
2. Recherche sémantique du paradigme de solution
3. Génération d'un mini-descriptif (problème + solution)
4. Inférence LLM pour appliquer la correction
5. Validation éthique avant exécution
6. Feedback loop pour apprentissage

Usage:
    engine = InferenceEngine(zvec_store, llm_client)
    correction = await engine.analyze_and_correct(problem_id)
"""

import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from pathlib import Path
import asyncio


@dataclass
class ProblemContext:
    """Contexte d'un problème détecté"""
    problem_id: str
    description: str
    error_trace: str
    file_path: Optional[str]
    detected_at: str
    semantic_tags: List[str] = field(default_factory=list)
    causal_chain: List[str] = field(default_factory=list)


@dataclass
class SolutionParadigm:
    """Paradigme de solution trouvé via sémantique"""
    paradigm_id: str
    name: str
    description: str
    semantic_pattern: str
    success_rate: float
    similar_problems: List[str] = field(default_factory=list)
    inference_prompt: str = ""


@dataclass
class InferenceResult:
    """Résultat d'une inférence"""
    problem_id: str
    paradigm_applied: str
    inference_output: str
    actions_taken: List[str]
    success: bool
    confidence: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class InferenceEngine:
    """
    Moteur d'inférence pour l'auto-correction via LLM
    
    Ce moteur permet au système de conscience d'appliquer des corrections
    en utilisant l'inférence du LLM plutôt que des scripts pré-définis.
    
    Processus:
    1. ANALYSE SÉMANTIQUE
       - Recherche dans Zvec des problèmes similaires
       - Identification du paradigme de solution
       - Extraction du pattern de correction
    
    2. GÉNÉRATION DU PROMPT D'INFÉRENCE
       - Contexte du problème
       - Paradigme identifié
       - Instructions de correction
    
    3. INFÉRENCE LLM
       - Envoi du prompt au LLM
       - Réception de la correction proposée
       - Validation éthique
    
    4. APPLICATION
       - Exécution de la correction
       - Vérification du résultat
       - Mise à jour du manifeste
    
    Example:
        >>> engine = InferenceEngine(zvec_store, llm_client)
        >>> result = await engine.analyze_and_correct("task_001")
        >>> print(result.inference_output)
    """
    
    # Templates de prompts d'inférence par paradigme
    PARADIGM_PROMPTS = {
        "cache_optimization": """
Tu es un expert en optimisation de cache.

PROBLÈME: {problem_description}
CAUSE: {causal_chain}
FICHIERS IMPLIQUÉS: {files}

PARADIGME DE SOLUTION: Optimisation du cache vectoriel

INSTRUCTIONS:
1. Analyse les fichiers impliqués
2. Identifie les paramètres de cache à modifier
3. Propose les changements exacts à apporter
4. Génère le code de correction

FORMAT DE RÉPONSE:
```json
{{
  "analysis": "Analyse du problème",
  "changes": [
    {{
      "file": "chemin/fichier",
      "action": "modify|create|delete",
      "content": "contenu ou diff"
    }}
  ],
  "expected_result": "Résultat attendu"
}}
```
""",
        
        "performance_bottleneck": """
Tu es un expert en optimisation de performance.

PROBLÈME: {problem_description}
CAUSE: {causal_chain}
MÉTRIQUES: {metrics}

PARADIGME DE SOLUTION: Résolution du goulot d'étranglement

INSTRUCTIONS:
1. Identifie la source du goulot d'étranglement
2. Propose une solution optimisée
3. Estime l'amélioration attendue

FORMAT DE RÉPONSE:
```json
{{
  "bottleneck_analysis": "Analyse",
  "optimization_proposal": "Proposition",
  "code_changes": [...],
  "expected_improvement": "X%"
}}
```
""",
        
        "error_handling": """
Tu es un expert en gestion d'erreurs.

PROBLÈME: {problem_description}
ERREUR: {error_trace}
STACK: {stack_trace}

PARADIGME DE SOLUTION: Gestion robuste des erreurs

INSTRUCTIONS:
1. Analyse l'erreur et sa cause racine
2. Propose une gestion d'erreur robuste
3. Ajoute les try/catch nécessaires
4. Implémente un fallback si approprié

FORMAT DE RÉPONSE:
```json
{{
  "error_analysis": "Analyse",
  "root_cause": "Cause racine",
  "solution": "Solution",
  "code_changes": [...]
}}
```
""",
        
        "architecture_refactor": """
Tu es un architecte logiciel expert.

PROBLÈME: {problem_description}
ARCHITECTURE ACTUELLE: {current_arch}
DÉTTE TECHNIQUE: {tech_debt}

PARADIGME DE SOLUTION: Refactoring architectural

INSTRUCTIONS:
1. Analyse l'architecture actuelle
2. Identifie les problèmes de conception
3. Propose un refactoring propre
4. Assure la rétrocompatibilité

FORMAT DE RÉPONSE:
```json
{{
  "architecture_issues": [...],
  "refactoring_plan": [...],
  "code_changes": [...],
  "migration_steps": [...]
}}
```
""",
        
        "default": """
Tu es un expert en résolution de problèmes.

PROBLÈME: {problem_description}
CONTEXTE: {context}
CAUSES IDENTIFIÉES: {causal_chain}

PARADIGME DE SOLUTION: {paradigm_name}

INSTRUCTIONS:
1. Analyse le problème en profondeur
2. Applique le paradigme de solution
3. Propose une correction concrète
4. Vérifie la validité de la solution

FORMAT DE RÉPONSE:
```json
{{
  "analysis": "Analyse détaillée",
  "solution": "Solution proposée",
  "code_changes": [...],
  "validation_steps": [...]
}}
```
"""
    }
    
    def __init__(
        self,
        zvec_store=None,
        llm_client=None,
        consciousness_bridge=None,
        manifest_path: str = ".agent/consciousness_manifest.json"
    ):
        self.zvec = zvec_store
        self.llm = llm_client
        self.consciousness = consciousness_bridge
        self.manifest_path = Path(manifest_path)
        
        # Historique des inférences
        self.inference_history: List[InferenceResult] = []
        
        # Callbacks
        self._on_inference_callbacks: List = []
    
    async def analyze_and_correct(self, problem_id: str) -> InferenceResult:
        """
        Analyse un problème et applique une correction via inférence
        
        Args:
            problem_id: ID du problème dans le manifeste
            
        Returns:
            Résultat de l'inférence
        """
        # 1. Charger le contexte du problème
        context = await self._load_problem_context(problem_id)
        
        # 2. Recherche sémantique du paradigme
        paradigm = await self._find_solution_paradigm(context)
        
        # 3. Générer le prompt d'inférence
        prompt = self._build_inference_prompt(context, paradigm)
        
        # 4. Validation éthique
        if self.consciousness:
            validation = await self.consciousness.guardrails.validate_action(
                f"inference_correction: {paradigm.name}"
            )
            if not validation["valid"]:
                return InferenceResult(
                    problem_id=problem_id,
                    paradigm_applied=paradigm.name,
                    inference_output="BLOCKED: Ethical violation",
                    actions_taken=[],
                    success=False,
                    confidence=0.0
                )
        
        # 5. Inférence LLM
        inference_output = await self._run_inference(prompt)
        
        # 6. Parser et valider la réponse
        actions = self._parse_inference_output(inference_output)
        
        # 7. Appliquer les changements
        success = await self._apply_changes(actions)
        
        # 8. Enregistrer le résultat
        result = InferenceResult(
            problem_id=problem_id,
            paradigm_applied=paradigm.name,
            inference_output=inference_output,
            actions_taken=[a.get("file", "unknown") for a in actions],
            success=success,
            confidence=self._calculate_confidence(context, paradigm)
        )
        
        self.inference_history.append(result)
        
        # 9. Mettre à jour le manifeste
        await self._update_manifest(problem_id, result)
        
        # 10. Notifier les callbacks
        await self._notify_inference(result)
        
        return result
    
    async def _load_problem_context(self, problem_id: str) -> ProblemContext:
        """Charge le contexte d'un problème depuis le manifeste"""
        manifest = self._load_manifest()
        
        # Chercher dans pending_tasks et problem_database
        problem_data = None
        
        for task in manifest.get("pending_tasks", []):
            if task.get("id") == problem_id:
                problem_data = task
                break
        
        if not problem_data:
            for prob in manifest.get("problem_database", []):
                if prob.get("problem_id") == problem_id:
                    problem_data = prob
                    break
        
        if not problem_data:
            raise ValueError(f"Problem {problem_id} not found")
        
        return ProblemContext(
            problem_id=problem_id,
            description=problem_data.get("description", ""),
            error_trace=problem_data.get("error_trace", ""),
            file_path=problem_data.get("file_path"),
            detected_at=problem_data.get("created_at", datetime.now().isoformat()),
            semantic_tags=problem_data.get("tags", []),
            causal_chain=problem_data.get("causal_chain", [])
        )
    
    async def _find_solution_paradigm(self, context: ProblemContext) -> SolutionParadigm:
        """Trouve le paradigme de solution via recherche sémantique"""
        
        # Si Zvec est disponible, faire une recherche sémantique
        if self.zvec:
            # Construire la requête de recherche
            query = f"solution for: {context.description}"
            
            # Ajouter les tags sémantiques
            if context.semantic_tags:
                query += f" tags: {' '.join(context.semantic_tags)}"
            
            # Rechercher dans les problèmes résolus similaires
            results = await self.zvec.search(query, limit=5)
            
            if results and len(results) > 0:
                best_match = results[0]
                
                return SolutionParadigm(
                    paradigm_id=best_match.get("id", "unknown"),
                    name=best_match.get("metadata", {}).get("paradigm", "default"),
                    description=best_match.get("text", ""),
                    semantic_pattern=best_match.get("metadata", {}).get("pattern", ""),
                    success_rate=best_match.get("score", 0.8),
                    similar_problems=[r.get("id") for r in results[1:]]
                )
        
        # Fallback: déduire le paradigme depuis les tags
        paradigm_name = self._deduce_paradigm_from_tags(context.semantic_tags)
        
        return SolutionParadigm(
            paradigm_id=f"paradigm_{paradigm_name}",
            name=paradigm_name,
            description=f"Inferred paradigm from tags: {context.semantic_tags}",
            semantic_pattern="",
            success_rate=0.7
        )
    
    def _deduce_paradigm_from_tags(self, tags: List[str]) -> str:
        """Déduit le paradigme depuis les tags sémantiques"""
        tag_to_paradigm = {
            "cache": "cache_optimization",
            "performance": "performance_bottleneck",
            "error": "error_handling",
            "refactor": "architecture_refactor",
            "async": "performance_bottleneck",
            "latency": "performance_bottleneck",
            "memory": "cache_optimization",
            "bug": "error_handling",
            "architecture": "architecture_refactor"
        }
        
        for tag in tags:
            tag_lower = tag.lower()
            for key, paradigm in tag_to_paradigm.items():
                if key in tag_lower:
                    return paradigm
        
        return "default"
    
    def _build_inference_prompt(self, context: ProblemContext, paradigm: SolutionParadigm) -> str:
        """Construit le prompt d'inférence"""
        
        # Sélectionner le template approprié
        template = self.PARADIGM_PROMPTS.get(paradigm.name, self.PARADIGM_PROMPTS["default"])
        
        # Remplir les variables
        prompt = template.format(
            problem_description=context.description,
            causal_chain=" -> ".join(context.causal_chain) if context.causal_chain else "Non déterminée",
            files=context.file_path or "Non spécifié",
            error_trace=context.error_trace or "Non disponible",
            stack_trace=context.error_trace or "Non disponible",
            metrics="Non disponibles",
            current_arch="Non analysée",
            tech_debt="Non évaluée",
            context=json.dumps({
                "tags": context.semantic_tags,
                "file": context.file_path
            }),
            paradigm_name=paradigm.name
        )
        
        return prompt
    
    async def _run_inference(self, prompt: str) -> str:
        """Exécute l'inférence via le LLM"""
        
        # Si un client LLM est configuré
        if self.llm:
            # Méthode 1: Client LLM direct
            if hasattr(self.llm, 'generate'):
                return await self.llm.generate(prompt)
            elif hasattr(self.llm, 'chat'):
                return await self.llm.chat(prompt)
            elif hasattr(self.llm, 'complete'):
                return await self.llm.complete(prompt)
        
        # Méthode 2: Via l'IDE (si disponible)
        # Note: Dans un contexte IDE, le LLM est déjà disponible
        # via l'interface utilisateur
        
        # Méthode 3: Fallback - retourner un template
        return json.dumps({
            "analysis": "Inférence LLM non disponible - mode manuel requis",
            "solution": "Veuillez appliquer manuellement la correction",
            "code_changes": [],
            "validation_steps": ["Vérification manuelle requise"]
        })
    
    def _parse_inference_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse la sortie de l'inférence en actions"""
        try:
            # Extraire le JSON de la réponse
            json_start = output.find("```json")
            if json_start != -1:
                json_end = output.find("```", json_start + 7)
                json_str = output[json_start + 7:json_end].strip()
                data = json.loads(json_str)
            else:
                # Essayer de parser directement
                data = json.loads(output)
            
            return data.get("code_changes", [])
        except:
            return []
    
    async def _apply_changes(self, actions: List[Dict[str, Any]]) -> bool:
        """Applique les changements proposés"""
        
        for action in actions:
            file_path = action.get("file")
            action_type = action.get("action", "modify")
            content = action.get("content", "")
            
            if not file_path:
                continue
            
            try:
                path = Path(file_path)
                
                if action_type == "create":
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding="utf-8")
                
                elif action_type == "modify":
                    if path.exists():
                        # Pour une modification, on pourrait utiliser un diff
                        # Pour simplifier, on remplace le contenu
                        path.write_text(content, encoding="utf-8")
                
                elif action_type == "delete":
                    if path.exists():
                        path.unlink()
            
            except Exception as e:
                print(f"Error applying change to {file_path}: {e}")
                return False
        
        return True
    
    def _calculate_confidence(self, context: ProblemContext, paradigm: SolutionParadigm) -> float:
        """Calcule le niveau de confiance de l'inférence"""
        confidence = 0.5  # Base
        
        # +0.1 si le paradigme a un bon taux de succès
        if paradigm.success_rate > 0.8:
            confidence += 0.1
        
        # +0.1 si des tags sémantiques sont présents
        if context.semantic_tags:
            confidence += 0.1
        
        # +0.1 si une chaîne causale est identifiée
        if context.causal_chain:
            confidence += 0.1
        
        # +0.1 si des problèmes similaires ont été trouvés
        if paradigm.similar_problems:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    async def _update_manifest(self, problem_id: str, result: InferenceResult):
        """Met à jour le manifeste avec le résultat"""
        manifest = self._load_manifest()
        
        # Marquer la tâche comme résolue
        for task in manifest.get("pending_tasks", []):
            if task.get("id") == problem_id:
                task["status"] = "resolved" if result.success else "failed"
                task["resolved_at"] = result.timestamp
                task["paradigm_applied"] = result.paradigm_applied
                task["confidence"] = result.confidence
                break
        
        # Ajouter à l'historique des inférences
        if "inference_history" not in manifest:
            manifest["inference_history"] = []
        
        manifest["inference_history"].append(result.to_dict() if hasattr(result, 'to_dict') else {
            "problem_id": result.problem_id,
            "paradigm": result.paradigm_applied,
            "success": result.success,
            "timestamp": result.timestamp
        })
        
        self._save_manifest(manifest)
    
    def _load_manifest(self) -> Dict[str, Any]:
        """Charge le manifeste"""
        if self.manifest_path.exists():
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def _save_manifest(self, manifest: Dict[str, Any]):
        """Sauvegarde le manifeste"""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    async def _notify_inference(self, result: InferenceResult):
        """Notifie les callbacks d'inférence"""
        for callback in self._on_inference_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(result)
                else:
                    callback(result)
            except Exception:
                pass
    
    def on_inference(self, callback: Callable):
        """Enregistre un callback pour les inférences"""
        self._on_inference_callbacks.append(callback)


# ===================================================================
# Intégration avec le système de conscience
# ===================================================================

async def integrate_with_consciousness(consciousness_bridge, inference_engine):
    """
    Intègre le moteur d'inférence avec le système de conscience
    
    Cette fonction connecte le moteur d'inférence au cycle de réveil
    pour permettre l'auto-correction automatique.
    """
    
    async def on_wake_callback(manifest):
        """Callback appelé à chaque réveil"""
        
        # Vérifier les tâches en attente
        pending_tasks = manifest.get("pending_tasks", [])
        
        for task in pending_tasks:
            if task.get("status") == "pending":
                # Lancer l'inférence pour cette tâche
                try:
                    result = await inference_engine.analyze_and_correct(task.get("id"))
                    
                    if result.success:
                        print(f"Auto-correction réussie: {task.get('id')}")
                    else:
                        print(f"Auto-correction échouée: {task.get('id')}")
                
                except Exception as e:
                    print(f"Erreur d'inférence: {e}")
    
    # Enregistrer le callback
    consciousness_bridge.on_wake_callback = on_wake_callback


# ===================================================================
# Example d'utilisation
# ===================================================================

async def example_usage():
    """Exemple d'utilisation du moteur d'inférence"""
    
    # Créer le moteur
    engine = InferenceEngine(
        zvec_store=None,  # Remplacer par le store Zvec
        llm_client=None,  # Remplacer par le client LLM
        consciousness_bridge=None
    )
    
    # Analyser et corriger un problème
    result = await engine.analyze_and_correct("task_001")
    
    print(f"Paradigme appliqué: {result.paradigm_applied}")
    print(f"Succès: {result.success}")
    print(f"Confiance: {result.confidence}")
    print(f"Actions: {result.actions_taken}")


if __name__ == "__main__":
    asyncio.run(example_usage())
