"""
Benchmarks Module - Tests de performance RAG

Ce package contient les outils de benchmark pour mesurer
la qualité du retrieval et les performances du système.
"""

from .retrieval_bench import RetrievalBenchmark, BenchmarkResult, run_quick_benchmark

__all__ = [
    "RetrievalBenchmark",
    "BenchmarkResult",
    "run_quick_benchmark"
]
