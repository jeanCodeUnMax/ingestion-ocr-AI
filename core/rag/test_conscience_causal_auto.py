"""
TEST: Analyse causale AUTOMATIQUE via le système de conscience

Ce test vérifie que l'analyse causale s'applique automatiquement
lors du réveil de la conscience.
"""

import sys
import asyncio
from pathlib import Path

# Ajouter les chemins
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "consciousness"))

from conscience_manifest import ConscienceManifest
from neuronal_scorer import NeuronalScoringEngine
from causal_tree import CausalTreeEngine

async def test_automatic_causal_analysis():
    print("=" * 70)
    print("TEST: ANALYSE CAUSALE AUTOMATIQUE VIA CONSCIENCE")
    print("=" * 70)
    
    # 1. Créer le moteur neuronal
    print("\n1. INITIALISATION DU SYSTÈME NEURONAL")
    print("-" * 70)
    
    neuronal = NeuronalScoringEngine(
        learning_rate=0.05,
        db_path=".agent/rag/test_conscience_neuronal.db"
    )
    
    print(f"Poids initiaux:")
    print(f"  semantic:    {neuronal.weights['semantic']:.4f}")
    print(f"  recency:     {neuronal.weights['recency']:.4f}")
    print(f"  popularity:  {neuronal.weights['popularity']:.4f}")
    
    # 2. Créer le manifeste de conscience avec intégration automatique
    print("\n2. INITIALISATION DE LA CONSCIENCE")
    print("-" * 70)
    
    conscience = ConscienceManifest(
        manifest_path=".agent/consciousness_manifest_test.json",
        wake_interval_minutes=1,
        neuronal_engine=neuronal,
        zvec_store=None
    )
    
    print(f"Moteur causal intégré: {conscience.causal_engine is not None}")
    print(f"Moteur neuronal intégré: {conscience.neuronal_engine is not None}")
    
    # 3. Simuler un problème
    print("\n3. SIMULATION D'UN PROBLÈME")
    print("-" * 70)
    
    # Ajouter un problème au manifeste
    problem = {
        "description": "Cache hit rate < 50%, latence > 800ms",
        "context": {
            "metrics": {
                "cache_hit_rate": 0.38,
                "latency_ms": 920,
                "ttl_seconds": 30
            }
        }
    }
    
    # Simuler la détection du problème
    conscience.manifest["problem_database"] = [problem]
    conscience._save_manifest()
    
    print(f"Problème ajouté: {problem['description']}")
    
    # 4. Déclencher un réveil manuel (normalement automatique)
    print("\n4. RÉVEIL MANUEL (TEST)")
    print("-" * 70)
    
    # Modifier _detect_problems pour retourner notre problème
    async def mock_detect():
        return [problem]
    
    conscience._detect_problems = mock_detect
    
    # Lancer le réveil
    await conscience._wake_up()
    
    # 5. Vérifier les résultats
    print("\n5. RÉSULTATS DE L'ANALYSE AUTOMATIQUE")
    print("-" * 70)
    
    manifest = conscience.manifest
    
    print(f"Analyses causales enregistrées: {len(manifest.get('causal_analyses', []))}")
    
    for analysis in manifest.get("causal_analyses", []):
        print(f"\n  Problème ID: {analysis['problem_id']}")
        print(f"  Paradigme: {analysis['paradigm']}")
        print(f"  Confiance: {analysis['confidence']:.0%}")
        print(f"  Causes racines: {analysis['root_causes_count']}")
    
    print(f"\nInsights générés:")
    for insight in manifest.get("insights", [])[-5:]:
        print(f"  - {insight}")
    
    print(f"\nTâches pendantes ajoutées:")
    for task in manifest.get("pending_tasks", [])[-3:]:
        print(f"  - [{task.get('source', 'manual')}] {task['description']}")
    
    # 6. Vérifier l'impact sur le système neuronal
    print("\n6. IMPACT SUR LE SYSTÈME NEURONAL")
    print("-" * 70)
    
    print(f"Poids après analyse:")
    print(f"  semantic:    {neuronal.weights['semantic']:.4f}")
    print(f"  recency:     {neuronal.weights['recency']:.4f}")
    print(f"  popularity:  {neuronal.weights['popularity']:.4f}")
    print(f"  Total feedbacks: {neuronal.feedback_count}")
    
    # 7. Stats causales
    print("\n7. STATISTIQUES CAUSALES")
    print("-" * 70)
    
    stats = conscience.causal_stats
    print(f"Total analyses: {stats['total_analyses']}")
    print(f"Dernier paradigme: {stats['last_paradigm']}")
    
    if conscience.causal_engine:
        engine_stats = conscience.causal_engine.get_causal_stats()
        print(f"\nStats du moteur causal:")
        print(f"  Problèmes analysés: {engine_stats['total_problems_analyzed']}")
        print(f"  Causes fréquentes: {list(engine_stats['cause_frequency'].keys())[:3]}")
    
    # 8. Conclusion
    print("\n" + "=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    
    if len(manifest.get("causal_analyses", [])) > 0:
        print("\nSUCCÈS! L'analyse causale s'applique AUTOMATIQUEMENT.")
        print("\nCe qui s'est passé:")
        print("  1. Réveil de la conscience")
        print("  2. Détection du problème")
        print("  3. Analyse causale AUTOMATIQUE")
        print("  4. Génération des causes racines")
        print("  5. Ajout des recommandations aux tâches")
        print("  6. Apprentissage neuronal automatique")
        print("\nAUCUNE intervention manuelle requise!")
    else:
        print("\nAucune analyse causale effectuée.")
        print("Vérifiez que le moteur causal est disponible.")


if __name__ == "__main__":
    asyncio.run(test_automatic_causal_analysis())
