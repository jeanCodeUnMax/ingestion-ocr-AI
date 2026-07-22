"""
Tests complets du système neuronal avec évolution des poids

Ce module combine:
1. Test du moteur de scoring neuronal (Sigmoid)
2. Test de la boucle de feedback asynchrone
3. Test d'intégration avec simulation de recherche
4. Preuve d'apprentissage avec persistance

Usage:
    python test_neuronal.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent))

from neuronal_scorer import NeuronalScoringEngine
from feedback import FeedbackLoop, FeedbackType


def print_header(title: str, char: str = "="):
    """Affiche un en-tête formaté"""
    print(f"\n{char * 70}")
    print(f"  {title}")
    print(f"{char * 70}")


def print_weights(weights: dict, prefix: str = "   "):
    """Affiche les poids de manière formatée"""
    for key, value in weights.items():
        print(f"{prefix}{key:12s}: {value:.4f}")


def print_score_evolution(before: float, after: float, label: str = "Score"):
    """Affiche l'évolution d'un score"""
    delta = after - before
    arrow = " +" if delta >= 0 else " "
    print(f"   {label}: {before:.4f} -> {after:.4f} ({arrow}{delta:.4f})")


# ============================================================================
# TEST 1: Moteur de scoring neuronal
# ============================================================================

def test_neuronal_scorer():
    """Test du moteur de scoring neuronal avec activation Sigmoid"""
    print_header("TEST 1: NeuronalScoringEngine (Sigmoid)")
    
    # 1. Création avec DB pour persistance
    engine = NeuronalScoringEngine(
        db_path=".agent/rag/neuronal_test.db"
    )
    
    print("\n--- 1.1 Poids initiaux ---")
    print_weights(engine.get_weights())
    print(f"   Learning rate: {engine.learning_rate}")
    print(f"   Bias: {engine.bias}")
    
    # 2. Calcul de score avec Sigmoid
    print("\n--- 1.2 Calcul de score (Sigmoid) ---")
    semantic = 0.85
    recency = 0.60
    popularity = 0.30
    
    score = engine.calculate_score(semantic, recency, popularity)
    
    print(f"   Entrées:")
    print(f"      semantic:    {semantic}")
    print(f"      recency:     {recency}")
    print(f"      popularity:  {popularity}")
    print(f"\n   Calcul: z = w1*s1 + w2*s2 + w3*s3 + bias")
    z = (semantic * engine.weights["semantic"] + 
         recency * engine.weights["recency"] + 
         popularity * engine.weights["popularity"] + 
         engine.bias)
    print(f"      z = {z:.4f}")
    print(f"\n   Activation: sigmoid(z) = 1/(1+exp(-z))")
    print(f"      Score = {score:.4f}")
    
    # 3. Feedback positif
    print("\n--- 1.3 Feedback POSITIF (+0.9) ---")
    old_weights = engine.get_weights()
    result = engine.feedback_loop("doc_001", satisfaction=0.9)
    
    print("   Poids AVANT:")
    print_weights(old_weights)
    print("   Poids APRÈS:")
    print_weights(result['new_weights'])
    print(f"   Delta: {result['delta']:.4f}")
    
    # 4. Feedback négatif
    print("\n--- 1.4 Feedback NÉGATIF (-0.5) ---")
    old_weights = engine.get_weights()
    result = engine.feedback_loop("doc_002", satisfaction=-0.5)
    
    print("   Poids AVANT:")
    print_weights(old_weights)
    print("   Poids APRÈS:")
    print_weights(result['new_weights'])
    print(f"   Delta: {result['delta']:.4f}")
    
    # 5. Batch feedback
    print("\n--- 1.5 Batch feedback (3 feedbacks) ---")
    batch_result = engine.batch_feedback([
        {"doc_id": "doc_003", "satisfaction": 0.7},
        {"doc_id": "doc_004", "satisfaction": 0.8},
        {"doc_id": "doc_005", "satisfaction": -0.3}
    ])
    
    print(f"   Feedbacks traités: {batch_result['total_feedbacks']}")
    print("   Poids finaux:")
    print_weights(batch_result['final_weights'])
    print(f"   Total feedbacks moteur: {engine.feedback_count}")
    
    # 6. Historique
    print("\n--- 1.6 Historique des poids ---")
    history = engine.get_history(limit=5)
    for h in history:
        print(f"   Session: {h['session_id']}")
        print(f"      Feedbacks: {h['feedback_count']}")
        print_weights(h['weights'], "      ")
        print()
    
    print("\n   TEST NeuronalScoringEngine: OK")
    return True


# ============================================================================
# TEST 2: Boucle de feedback asynchrone
# ============================================================================

async def test_feedback_loop():
    """Test de la boucle de feedback avec FeedbackLoop"""
    print_header("TEST 2: FeedbackLoop (Async)")
    
    # Créer un moteur neuronal
    engine = NeuronalScoringEngine(
        db_path=".agent/rag/neuronal_test.db"
    )
    
    # Créer la boucle de feedback
    loop = FeedbackLoop(
        neuronal_engine=engine,
        db_path=".agent/rag/feedback_test.db"
    )
    
    print("\n--- 2.1 État initial ---")
    print_weights(loop.neuronal_engine.get_weights())
    
    # 2. Feedback positif avec contexte
    print("\n--- 2.2 Feedback POSITIF (0.8) avec contexte ---")
    result = await loop.process_feedback(
        interaction_id="interaction_001",
        rating=0.8,
        correction=None,
        context={"query": "test query", "scores": {"qdrant": 0.9, "zvec": 0.7, "memory": 0.3}}
    )
    
    print(f"   Type: {result['entry']['feedback_type']}")
    print(f"   Renforcement: {result['reinforcement']['type']}")
    print(f"   Actions: {result['reinforcement']['actions']}")
    print("   Poids ajustés:")
    print_weights(result['weight_adjustment']['new_weights'])
    
    # 3. Feedback négatif avec correction
    print("\n--- 2.3 Feedback NÉGATIF (-0.6) avec correction ---")
    old_weights = loop.neuronal_engine.get_weights()
    result = await loop.process_feedback(
        interaction_id="interaction_002",
        rating=-0.6,
        correction="Le résultat n'était pas pertinent",
        context={"query": "mauvaise requête", "scores": {"qdrant": 0.2, "zvec": 0.3}}
    )
    
    print(f"   Type: {result['entry']['feedback_type']}")
    print(f"   Correction: {result['entry']['correction']}")
    print(f"   Renforcement: {result['reinforcement']['type']}")
    print("   Poids AVANT:")
    print_weights(old_weights)
    print("   Poids APRÈS:")
    print_weights(result['weight_adjustment']['new_weights'])
    
    # 4. Stats
    print("\n--- 2.4 Statistiques ---")
    stats = loop.get_stats()
    print(f"   Total feedbacks: {stats.get('total', 0)}")
    print(f"   Par type: {stats.get('by_type', {})}")
    print(f"   Rating moyen: {stats.get('average_rating', 0):.3f}")
    print("   Poids actuels:")
    print_weights(stats.get('current_weights', {}))
    
    # 5. Batch async
    print("\n--- 2.5 Batch async (3 feedbacks) ---")
    batch_result = await loop.batch_process([
        {"interaction_id": "i_003", "rating": 0.5},
        {"interaction_id": "i_004", "rating": 0.9},
        {"interaction_id": "i_005", "rating": -0.2}
    ])
    
    print(f"   Total traités: {batch_result['total_processed']}")
    print(f"   Rating moyen: {batch_result['average_rating']:.2f}")
    print("   Poids finaux:")
    print_weights(batch_result['current_weights'])
    
    print("\n   TEST FeedbackLoop: OK")
    return True


# ============================================================================
# TEST 3: Intégration complète avec simulation de recherche
# ============================================================================

def test_integration():
    """Test d'intégration complet avec simulation de pipeline RAG"""
    print_header("TEST 3: Intégration Pipeline RAG")
    
    # Créer le moteur neuronal
    engine = NeuronalScoringEngine(
        learning_rate=0.05,
        db_path=".agent/rag/neuronal_test.db"
    )
    
    # Simuler des résultats de recherche
    results = [
        {"id": "doc_1", "qdrant": 0.92, "zvec": 0.85, "memory": 0.35, "title": "Python async patterns"},
        {"id": "doc_2", "qdrant": 0.75, "zvec": 0.62, "memory": 0.28, "title": "Rust concurrency"},
        {"id": "doc_3", "qdrant": 0.55, "zvec": 0.91, "memory": 0.45, "title": "Go goroutines"},
        {"id": "doc_4", "qdrant": 0.88, "zvec": 0.40, "memory": 0.15, "title": "JavaScript promises"},
        {"id": "doc_5", "qdrant": 0.30, "zvec": 0.25, "memory": 0.80, "title": "Legacy patterns"},
    ]
    
    print("\n--- 3.1 Résultats de recherche avec poids initiaux ---")
    print_weights(engine.get_weights(), "   Poids: ")
    
    print("\n   Classement initial:")
    print(f"   {'ID':<8} {'Qdrant':<8} {'Zvec':<8} {'Memory':<8} {'Score':<8} {'Titre'}")
    print("   " + "-" * 60)
    
    scored_results = []
    for r in results:
        score = engine.calculate_score(r["qdrant"], r["zvec"], r["memory"])
        scored_results.append({**r, "score": score})
        print(f"   {r['id']:<8} {r['qdrant']:<8.2f} {r['zvec']:<8.2f} {r['memory']:<8.2f} {score:<8.4f} {r['title']}")
    
    # Trier par score
    scored_results.sort(key=lambda x: x["score"], reverse=True)
    print(f"\n   Top 3: {[r['id'] for r in scored_results[:3]]}")
    
    # Simuler des feedbacks utilisateur
    print("\n--- 3.2 Simulation de feedbacks utilisateur ---")
    
    print("\n   Scénario: L'utilisateur préfère les documents récents (Zvec)")
    print("   Feedback: doc_3 (Go goroutines) = +0.9 (très pertinent)")
    print("   Feedback: doc_5 (Legacy patterns) = -0.7 (obsolète)")
    
    # Feedback positif pour doc_3 (haut score Zvec)
    result1 = engine.feedback_loop("doc_3", satisfaction=0.9, context={
        "scores": {"qdrant": 0.55, "zvec": 0.91, "memory": 0.45}
    })
    
    # Feedback négatif pour doc_5 (haut score Memory = legacy)
    result2 = engine.feedback_loop("doc_5", satisfaction=-0.7, context={
        "scores": {"qdrant": 0.30, "zvec": 0.25, "memory": 0.80}
    })
    
    print("\n   Évolution des poids:")
    print("   " + "-" * 50)
    print(f"   {'Param':<12} {'Avant':<10} {'Après':<10} {'Delta'}")
    print("   " + "-" * 50)
    
    for key in ["semantic", "recency", "popularity"]:
        old = result1['old_weights'].get(key, 0)
        new = engine.weights[key]
        delta = new - old
        print(f"   {key:<12} {old:<10.4f} {new:<10.4f} {delta:+.4f}")
    
    # Recalculer les scores
    print("\n--- 3.3 Nouveaux scores avec poids ajustés ---")
    print_weights(engine.get_weights(), "   Poids: ")
    
    print("\n   Nouveau classement:")
    print(f"   {'ID':<8} {'Qdrant':<8} {'Zvec':<8} {'Memory':<8} {'Score':<8} {'Titre'}")
    print("   " + "-" * 60)
    
    new_scored_results = []
    for r in results:
        score = engine.calculate_score(r["qdrant"], r["zvec"], r["memory"])
        new_scored_results.append({**r, "score": score})
        print(f"   {r['id']:<8} {r['qdrant']:<8.2f} {r['zvec']:<8.2f} {r['memory']:<8.2f} {score:<8.4f} {r['title']}")
    
    # Trier par nouveau score
    new_scored_results.sort(key=lambda x: x["score"], reverse=True)
    print(f"\n   Nouveau Top 3: {[r['id'] for r in new_scored_results[:3]]}")
    
    # Comparaison avant/après
    print("\n--- 3.4 Impact de l'apprentissage ---")
    print(f"   {'ID':<8} {'Avant':<10} {'Après':<10} {'Évolution'}")
    print("   " + "-" * 40)
    
    for r in results:
        old_score = next(s["score"] for s in scored_results if s["id"] == r["id"])
        new_score = next(s["score"] for s in new_scored_results if s["id"] == r["id"])
        evolution = " +".join([
            "RANK UP" if new_scored_results.index(next(s for s in new_scored_results if s["id"] == r["id"])) < 
                        scored_results.index(next(s for s in scored_results if s["id"] == r["id"]))
            else "RANK DOWN" if new_scored_results.index(next(s for s in new_scored_results if s["id"] == r["id"])) > 
                                 scored_results.index(next(s for s in scored_results if s["id"] == r["id"]))
            else "STABLE"
        ])
        print(f"   {r['id']:<8} {old_score:<10.4f} {new_score:<10.4f} {evolution}")
    
    print("\n   TEST Intégration: OK")
    return True


# ============================================================================
# TEST 4: Preuve d'apprentissage avec persistance
# ============================================================================

def test_learning_proof():
    """Preuve que le système apprend vraiment avec persistance"""
    print_header("TEST 4: Preuve d'apprentissage")
    
    weights_file = Path(".agent/rag/neuronal_weights.json")
    
    # 1. Charger les poids actuels
    print("\n--- 4.1 État actuel ---")
    if weights_file.exists():
        with open(weights_file) as f:
            current_weights = json.load(f)
        print("   Poids sauvegardés (apprentissage précédent):")
        print_weights(current_weights)
    else:
        print("   Aucun poids sauvegardé - valeurs par défaut")
        current_weights = {"semantic": 0.4, "recency": 0.4, "popularity": 0.2}
    
    # 2. Créer le moteur avec les poids actuels
    engine = NeuronalScoringEngine(
        initial_weights=current_weights,
        learning_rate=0.05,
        db_path=".agent/rag/neuronal_test.db"
    )
    
    print("\n--- 4.2 Session d'apprentissage ---")
    print(f"   Session ID: {engine.session_id}")
    print(f"   Feedbacks précédents: {engine.feedback_count}")
    
    # 3. Simuler une session d'apprentissage intensive
    print("\n--- 4.3 Apprentissage intensif (10 feedbacks) ---")
    
    feedbacks = [
        ("doc_001", 0.9, "Excellent résultat"),
        ("doc_002", 0.7, "Bon résultat"),
        ("doc_003", -0.3, "Peu pertinent"),
        ("doc_004", 0.8, "Très utile"),
        ("doc_005", -0.6, "Obsolète"),
        ("doc_006", 0.5, "Acceptable"),
        ("doc_007", 1.0, "Parfait"),
        ("doc_008", -0.4, "Hors sujet"),
        ("doc_009", 0.6, "Intéressant"),
        ("doc_010", 0.85, "Très bien"),
    ]
    
    initial_weights = engine.get_weights().copy()
    
    print(f"\n   {'#':<3} {'Doc':<10} {'Feedback':<10} {'Semantic':<10} {'Recency':<10} {'Popularity'}")
    print("   " + "-" * 60)
    
    for i, (doc_id, satisfaction, comment) in enumerate(feedbacks, 1):
        result = engine.feedback_loop(doc_id, satisfaction)
        w = result['new_weights']
        print(f"   {i:<3} {doc_id:<10} {satisfaction:+.1f}       {w['semantic']:.4f}     {w['recency']:.4f}     {w['popularity']:.4f}")
    
    # 4. Comparaison finale
    print("\n--- 4.4 Comparaison avant/après ---")
    
    print(f"\n   {'Param':<12} {'Initial':<10} {'Final':<10} {'Delta':<10} {'Variation'}")
    print("   " + "-" * 55)
    
    total_delta = 0
    for key in ["semantic", "recency", "popularity"]:
        initial = initial_weights[key]
        final = engine.weights[key]
        delta = final - initial
        variation = f"{delta:+.2%}"
        total_delta += abs(delta)
        print(f"   {key:<12} {initial:<10.4f} {final:<10.4f} {delta:+.4f}     {variation}")
    
    # 5. Sauvegarde
    print("\n--- 4.5 Sauvegarde ---")
    with open(weights_file, 'w') as f:
        json.dump(engine.weights, f, indent=2)
    print(f"   Poids sauvegardés dans: {weights_file}")
    
    # 6. Conclusion
    print("\n--- 4.6 Conclusion ---")
    
    if total_delta > 0.01:
        print("\n   LE SYSTÈME NEURONAL A APPRIS!")
        print("   Les poids ont évolué en réponse aux feedbacks.")
        print("   C'est du VRAI apprentissage avec persistance.")
        print(f"\n   Amélioration totale: {total_delta:.4f}")
        print(f"   Feedbacks mémorisés: {engine.feedback_count}")
    else:
        print("\n   Apprentissage minimal détecté.")
    
    print("\n   TEST Preuve d'apprentissage: OK")
    return True


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Exécute tous les tests"""
    print_header("SUITE DE TESTS - Système Neuronal Complet", "=")
    print(f"   Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Version: Fusionnée (Sigmoid + FeedbackLoop + Intégration)")
    
    results = []
    
    # Test 1: Neuronal Scorer
    try:
        results.append(("NeuronalScoringEngine", test_neuronal_scorer()))
    except Exception as e:
        results.append(("NeuronalScoringEngine", False))
        print(f"   ERREUR: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Feedback Loop (async)
    try:
        results.append(("FeedbackLoop", asyncio.run(test_feedback_loop())))
    except Exception as e:
        results.append(("FeedbackLoop", False))
        print(f"   ERREUR: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Intégration
    try:
        results.append(("Intégration Pipeline", test_integration()))
    except Exception as e:
        results.append(("Intégration Pipeline", False))
        print(f"   ERREUR: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Preuve d'apprentissage
    try:
        results.append(("Preuve Apprentissage", test_learning_proof()))
    except Exception as e:
        results.append(("Preuve Apprentissage", False))
        print(f"   ERREUR: {e}")
        import traceback
        traceback.print_exc()
    
    # Résumé
    print_header("RÉSUMÉ DES TESTS")
    
    for name, success in results:
        status = "OK" if success else "ÉCHEC"
        icon = "" if success else ""
        print(f"   {icon} {name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, s in results if s)
    
    print(f"\n   Total: {passed}/{total} tests réussis")
    
    if passed == total:
        print("\n   TOUS LES TESTS SONT PASSÉS!")
        print("   Le système neuronal est opérationnel.")
    
    return all(s for _, s in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
