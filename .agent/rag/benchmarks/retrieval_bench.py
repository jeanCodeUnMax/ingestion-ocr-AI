"""
Retrieval Benchmark - Mesure de performance du système RAG

Ce module implémente des benchmarks pour évaluer la qualité
du retrieval hybride (Qdrant + Zvec + Memory MCP).

Classes:
    - RetrievalBenchmark: Suite de benchmarks
    - BenchmarkResult: Résultat d'un benchmark
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import time
import json
import asyncio


@dataclass
class BenchmarkResult:
    """Résultat d'un benchmark"""
    name: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metrics: Dict[str, float] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "timestamp": self.timestamp,
            "metrics": self.metrics,
            "details": self.details
        }


class RetrievalBenchmark:
    """
    Suite de benchmarks pour le système RAG
    
    Mesure les métriques clés du retrieval:
    - Precision@K: Proportion de résultats pertinents dans top-K
    - Recall@K: Proportion de documents pertinents retrouvés
    - Latence: Temps de réponse (p50, p95, p99)
    - Résultats moyens: Nombre et qualité des résultats
    
    Example:
        >>> bench = RetrievalBenchmark(pipeline)
        >>> results = await bench.run_benchmark(test_queries)
        >>> print(results.metrics)
    """
    
    def __init__(self, pipeline, ground_truth: Optional[Dict[str, List[str]]] = None):
        """
        Initialise le benchmark
        
        Args:
            pipeline: Instance de RAGPipeline
            ground_truth: Dictionnaire {query: [doc_ids_pertinents]}
        """
        self.pipeline = pipeline
        self.ground_truth = ground_truth or {}
        self.results: List[BenchmarkResult] = []
    
    async def run_benchmark(
        self,
        test_queries: List[str],
        k_values: List[int] = None
    ) -> BenchmarkResult:
        """
        Exécute le benchmark complet
        
        Args:
            test_queries: Liste de requêtes de test
            k_values: Valeurs de K pour precision/recall (défaut: [5, 10, 20])
            
        Returns:
            Résultat consolidé du benchmark
        """
        if k_values is None:
            k_values = [5, 10, 20]
        
        start_time = time.time()
        
        # Collecter les métriques
        metrics = {
            "precision_at_5": 0.0,
            "precision_at_10": 0.0,
            "precision_at_20": 0.0,
            "recall_at_100": 0.0,
            "latency_p50": 0.0,
            "latency_p95": 0.0,
            "latency_p99": 0.0,
            "avg_results_count": 0.0,
            "avg_score": 0.0
        }
        
        latencies = []
        all_scores = []
        all_counts = []
        
        # Exécuter les requêtes
        for query in test_queries:
            query_start = time.time()
            
            # Recherche
            results = await self.pipeline.search(query=query, limit=100)
            
            query_latency = (time.time() - query_start) * 1000  # ms
            latencies.append(query_latency)
            
            # Collecter scores et counts
            if results:
                all_scores.extend([r.score for r in results])
                all_counts.append(len(results))
        
        # Calculer les métriques de latence
        if latencies:
            latencies_sorted = sorted(latencies)
            n = len(latencies_sorted)
            metrics["latency_p50"] = latencies_sorted[int(n * 0.5)]
            metrics["latency_p95"] = latencies_sorted[int(n * 0.95)]
            metrics["latency_p99"] = latencies_sorted[min(int(n * 0.99), n - 1)]
            metrics["avg_results_count"] = sum(all_counts) / len(all_counts) if all_counts else 0
            metrics["avg_score"] = sum(all_scores) / len(all_scores) if all_scores else 0
        
        # Calculer precision/recall si ground truth disponible
        if self.ground_truth:
            precision_5, precision_10, precision_20, recall_100 = await self._calculate_precision_recall(
                test_queries, k_values
            )
            metrics["precision_at_5"] = precision_5
            metrics["precision_at_10"] = precision_10
            metrics["precision_at_20"] = precision_20
            metrics["recall_at_100"] = recall_100
        
        total_time = time.time() - start_time
        
        result = BenchmarkResult(
            name="retrieval_benchmark",
            metrics=metrics,
            details={
                "queries_count": len(test_queries),
                "total_time_seconds": round(total_time, 3),
                "k_values": k_values,
                "has_ground_truth": bool(self.ground_truth)
            }
        )
        
        self.results.append(result)
        return result
    
    async def _calculate_precision_recall(
        self,
        queries: List[str],
        k_values: List[int]
    ) -> tuple:
        """Calcule precision@K et recall@100"""
        precisions = {k: [] for k in k_values}
        recalls = []
        
        for query in queries:
            if query not in self.ground_truth:
                continue
            
            relevant_docs = set(self.ground_truth[query])
            results = await self.pipeline.search(query=query, limit=100)
            retrieved_ids = [r.chunk_id for r in results]
            
            # Precision@K
            for k in k_values:
                top_k = set(retrieved_ids[:k])
                precision = len(top_k & relevant_docs) / k if k > 0 else 0
                precisions[k].append(precision)
            
            # Recall@100
            retrieved_100 = set(retrieved_ids[:100])
            recall = len(retrieved_100 & relevant_docs) / len(relevant_docs) if relevant_docs else 0
            recalls.append(recall)
        
        avg_precision_5 = sum(precisions[5]) / len(precisions[5]) if precisions[5] else 0
        avg_precision_10 = sum(precisions[10]) / len(precisions[10]) if precisions[10] else 0
        avg_precision_20 = sum(precisions[20]) / len(precisions[20]) if precisions[20] else 0
        avg_recall = sum(recalls) / len(recalls) if recalls else 0
        
        return avg_precision_5, avg_precision_10, avg_precision_20, avg_recall
    
    async def run_latency_stress_test(
        self,
        query: str,
        iterations: int = 100
    ) -> BenchmarkResult:
        """
        Test de charge pour mesurer la latence sous stress
        
        Args:
            query: Requête à répéter
            iterations: Nombre d'itérations
            
        Returns:
            Résultat du stress test
        """
        latencies = []
        
        for _ in range(iterations):
            start = time.time()
            await self.pipeline.search(query=query, limit=10)
            latencies.append((time.time() - start) * 1000)
        
        latencies_sorted = sorted(latencies)
        n = len(latencies_sorted)
        
        return BenchmarkResult(
            name="latency_stress_test",
            metrics={
                "iterations": iterations,
                "latency_min_ms": latencies_sorted[0],
                "latency_max_ms": latencies_sorted[-1],
                "latency_avg_ms": sum(latencies) / n,
                "latency_p50_ms": latencies_sorted[int(n * 0.5)],
                "latency_p95_ms": latencies_sorted[int(n * 0.95)],
                "latency_p99_ms": latencies_sorted[min(int(n * 0.99), n - 1)]
            }
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Retourne un résumé de tous les benchmarks"""
        if not self.results:
            return {"status": "no_results"}
        
        latest = self.results[-1]
        return {
            "last_run": latest.timestamp,
            "metrics": latest.metrics,
            "total_runs": len(self.results),
            "recommendations": self._generate_recommendations(latest.metrics)
        }
    
    def _generate_recommendations(self, metrics: Dict[str, float]) -> List[str]:
        """Génère des recommandations basées sur les métriques"""
        recommendations = []
        
        # Latence
        if metrics.get("latency_p95", 0) > 500:
            recommendations.append(
                "Latence P95 > 500ms: Considérer la réduction des collections ou l'optimisation des requêtes"
            )
        
        # Precision
        if metrics.get("precision_at_10", 0) < 0.7:
            recommendations.append(
                "Precision@10 < 0.7: Ajuster les poids de fusion (augmenter Qdrant si catégorique important)"
            )
        
        # Score moyen
        if metrics.get("avg_score", 0) < 0.5:
            recommendations.append(
                "Score moyen < 0.5: Vérifier la qualité des embeddings et les seuils de pertinence"
            )
        
        return recommendations
    
    def export_results(self, filepath: str) -> None:
        """Exporte les résultats en JSON"""
        data = {
            "results": [r.to_dict() for r in self.results],
            "summary": self.get_summary()
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# Requêtes de test par défaut
DEFAULT_TEST_QUERIES = [
    "configuration memory mcp",
    "architecture rag pipeline",
    "conscience artificielle modules",
    "scoring neuronal adaptatif",
    "feedback loop apprentissage",
    "fusion hybride qdrant zvec",
    "routing automatique tags",
    "cache optimisation ttl",
    "embedding dimensions vector",
    "benchmark retrieval precision"
]


async def run_quick_benchmark(pipeline) -> Dict[str, Any]:
    """
    Exécute un benchmark rapide avec les requêtes par défaut
    
    Args:
        pipeline: Instance de RAGPipeline
        
    Returns:
        Résultats du benchmark
    """
    bench = RetrievalBenchmark(pipeline)
    result = await bench.run_benchmark(DEFAULT_TEST_QUERIES)
    return result.to_dict()
