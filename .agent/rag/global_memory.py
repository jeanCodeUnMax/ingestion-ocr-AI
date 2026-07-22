"""
Global Memory System - Mémoire globale partagée entre projets

Ce module implémente la mémoire globale qui persiste entre les projets,
contrairement à la mémoire locale qui est spécifique à un projet.

Architecture:
- Mémoire LOCALE: Spécifique au projet actuel (dans .agent/)
- Mémoire GLOBALE: Partagée entre tous les projets (dans ~/.agent-global/)

Contenu de la mémoire globale:
- Skills appris
- Patterns de solutions
- Causes racines mémorisées
- Paradigmes de résolution
- Connaissances transversales

Usage:
    global_mem = GlobalMemory()
    global_mem.store("cache_optimization", {"pattern": "ttl_increase", "success_rate": 0.85})
    pattern = global_mem.retrieve("cache_optimization")
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import shutil
import hashlib


@dataclass
class GlobalKnowledge:
    """Une connaissance globale"""
    id: str
    category: str
    pattern: str
    solution: str
    success_rate: float
    projects_used: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used: str = field(default_factory=lambda: datetime.now().isoformat())
    use_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "pattern": self.pattern,
            "solution": self.solution,
            "success_rate": self.success_rate,
            "projects_used": self.projects_used,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "use_count": self.use_count
        }


class GlobalMemory:
    """
    Système de mémoire globale partagée entre projets
    
    La mémoire globale stocke:
    - Les patterns de solutions qui ont fonctionné
    - Les causes racines identifiées
    - Les paradigmes de résolution
    - Les connaissances transversales
    
    Emplacement:
    - Windows: C:/DATA-WEBMAN/memory/global/
    - Variable d'env: MEMORY_DB_ROOT
    
    Structure:
    - global.db (SQLite)
    - knowledge/ (JSON files)
    - patterns/ (Cached patterns)
    
    Example:
        >>> mem = GlobalMemory()
        >>> mem.store_knowledge("cache", "ttl_increase", "Augmenter TTL de 60s à 300s")
        >>> pattern = mem.find_pattern("cache hit rate low")
    """
    
    # Catégories de connaissances globales
    CATEGORIES = [
        "cache_optimization",
        "performance_tuning",
        "error_handling",
        "architecture_pattern",
        "security_fix",
        "data_quality",
        "configuration",
        "algorithm_improvement",
        "testing_pattern",
        "deployment_fix"
    ]
    
    def __init__(self, project_name: str = "default"):
        """
        Initialise la mémoire globale
        
        Args:
            project_name: Nom du projet actuel (pour tracking)
        """
        self.project_name = project_name
        
        # Déterminer le chemin de la mémoire globale
        # Utiliser C:\DATA-WEBMAN\memory comme base (mémoire unifiée)
        import os
        
        # Chemin depuis variable d'environnement ou défaut
        memory_root = os.getenv("MEMORY_DB_ROOT", "C:/DATA-WEBMAN/memory")
        self.global_root = Path(memory_root) / "global"
        self.global_root.mkdir(parents=True, exist_ok=True)
        
        # Sous-dossiers
        self.db_path = self.global_root / "global.db"
        self.knowledge_dir = self.global_root / "knowledge"
        self.patterns_dir = self.global_root / "patterns"
        
        self.knowledge_dir.mkdir(exist_ok=True)
        self.patterns_dir.mkdir(exist_ok=True)
        
        # Initialiser la base de données
        self._init_db()
        
        # Cache en mémoire
        self._cache: Dict[str, GlobalKnowledge] = {}
        self._load_cache()
    
    def _init_db(self):
        """Initialise la base de données SQLite globale"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Table des connaissances
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                pattern TEXT NOT NULL,
                solution TEXT NOT NULL,
                success_rate REAL DEFAULT 0.5,
                projects_used TEXT DEFAULT '[]',
                created_at TEXT,
                last_used TEXT,
                use_count INTEGER DEFAULT 0
            )
        """)
        
        # Index pour recherche rapide
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_category 
            ON knowledge(category)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pattern 
            ON knowledge(pattern)
        """)
        
        # Table des projets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                name TEXT PRIMARY KEY,
                last_sync TEXT,
                knowledge_count INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _load_cache(self):
        """Charge le cache en mémoire"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM knowledge")
        rows = cursor.fetchall()
        
        for row in rows:
            knowledge = GlobalKnowledge(
                id=row[0],
                category=row[1],
                pattern=row[2],
                solution=row[3],
                success_rate=row[4],
                projects_used=json.loads(row[5]) if row[5] else [],
                created_at=row[6],
                last_used=row[7],
                use_count=row[8]
            )
            self._cache[knowledge.id] = knowledge
        
        conn.close()
    
    def store_knowledge(
        self,
        category: str,
        pattern: str,
        solution: str,
        success_rate: float = 0.5
    ) -> str:
        """
        Stocke une nouvelle connaissance globale
        
        Args:
            category: Catégorie (cache, performance, error, etc.)
            pattern: Pattern du problème
            solution: Solution qui a fonctionné
            success_rate: Taux de succès (0.0 - 1.0)
            
        Returns:
            ID de la connaissance
        """
        # Générer un ID unique
        id_hash = hashlib.md5(f"{category}:{pattern}".encode()).hexdigest()[:12]
        knowledge_id = f"{category}_{id_hash}"
        
        # Créer la connaissance
        knowledge = GlobalKnowledge(
            id=knowledge_id,
            category=category,
            pattern=pattern,
            solution=solution,
            success_rate=success_rate,
            projects_used=[self.project_name]
        )
        
        # Vérifier si elle existe déjà
        if knowledge_id in self._cache:
            existing = self._cache[knowledge_id]
            # Mettre à jour
            existing.projects_used.append(self.project_name)
            existing.projects_used = list(set(existing.projects_used))
            existing.use_count += 1
            existing.last_used = datetime.now().isoformat()
            existing.success_rate = (existing.success_rate + success_rate) / 2
            knowledge = existing
        
        # Sauvegarder
        self._save_knowledge(knowledge)
        
        return knowledge_id
    
    def _save_knowledge(self, knowledge: GlobalKnowledge):
        """Sauvegarde une connaissance en base"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO knowledge 
            (id, category, pattern, solution, success_rate, projects_used, created_at, last_used, use_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            knowledge.id,
            knowledge.category,
            knowledge.pattern,
            knowledge.solution,
            knowledge.success_rate,
            json.dumps(knowledge.projects_used),
            knowledge.created_at,
            knowledge.last_used,
            knowledge.use_count
        ))
        
        conn.commit()
        conn.close()
        
        # Mettre à jour le cache
        self._cache[knowledge.id] = knowledge
        
        # Sauvegarder aussi en JSON pour lecture humaine
        json_path = self.knowledge_dir / f"{knowledge.id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(knowledge.to_dict(), f, indent=2, ensure_ascii=False)
    
    def find_pattern(self, query: str, category: Optional[str] = None) -> List[GlobalKnowledge]:
        """
        Trouve des patterns correspondants
        
        Args:
            query: Requête de recherche
            category: Catégorie optionnelle pour filtrer
            
        Returns:
            Liste des connaissances correspondantes
        """
        results = []
        query_lower = query.lower()
        
        for knowledge in self._cache.values():
            # Filtrer par catégorie si spécifié
            if category and knowledge.category != category:
                continue
            
            # Recherche dans le pattern et la solution
            if query_lower in knowledge.pattern.lower() or query_lower in knowledge.solution.lower():
                results.append(knowledge)
        
        # Trier par taux de succès et fréquence d'utilisation
        results.sort(key=lambda k: (k.success_rate, k.use_count), reverse=True)
        
        return results[:10]  # Top 10
    
    def get_best_solution(self, problem_description: str) -> Optional[GlobalKnowledge]:
        """
        Obtient la meilleure solution pour un problème
        
        Args:
            problem_description: Description du problème
            
        Returns:
            Meilleure connaissance correspondante ou None
        """
        results = self.find_pattern(problem_description)
        
        if results:
            # Marquer comme utilisée
            best = results[0]
            best.use_count += 1
            best.last_used = datetime.now().isoformat()
            if self.project_name not in best.projects_used:
                best.projects_used.append(self.project_name)
            self._save_knowledge(best)
            return best
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de la mémoire globale"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Compter par catégorie
        cursor.execute("""
            SELECT category, COUNT(*), AVG(success_rate)
            FROM knowledge
            GROUP BY category
        """)
        
        categories = {}
        for row in cursor.fetchall():
            categories[row[0]] = {
                "count": row[1],
                "avg_success_rate": row[2]
            }
        
        # Total
        cursor.execute("SELECT COUNT(*) FROM knowledge")
        total = cursor.fetchone()[0]
        
        # Projets
        cursor.execute("SELECT COUNT(*) FROM projects")
        projects_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_knowledge": total,
            "categories": categories,
            "projects_count": projects_count,
            "global_root": str(self.global_root)
        }
    
    def export_to_local(self, local_path: Path):
        """
        Exporte les connaissances vers un projet local
        
        Args:
            local_path: Chemin du dossier .agent local
        """
        export_dir = local_path / "knowledge" / "global"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Copier les fichiers JSON
        for json_file in self.knowledge_dir.glob("*.json"):
            shutil.copy(json_file, export_dir / json_file.name)
        
        # Créer un résumé
        summary = {
            "exported_at": datetime.now().isoformat(),
            "source": str(self.global_root),
            "knowledge_count": len(self._cache),
            "categories": list(set(k.category for k in self._cache.values()))
        }
        
        with open(export_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
    
    def import_from_local(self, local_manifest: Dict[str, Any]):
        """
        Importe les connaissances d'un projet local vers la mémoire globale
        
        Args:
            local_manifest: Manifeste local avec causal_analyses
        """
        analyses = local_manifest.get("causal_analyses", [])
        
        for analysis in analyses:
            paradigm = analysis.get("paradigm", "general")
            confidence = analysis.get("confidence", 0.5)
            
            # Créer une connaissance depuis l'analyse
            self.store_knowledge(
                category=paradigm,
                pattern=analysis.get("problem_id", "unknown"),
                solution=f"Paradigm: {paradigm}",
                success_rate=confidence
            )
    
    def sync_with_project(self, project_path: Path):
        """
        Synchronise la mémoire globale avec un projet
        
        Args:
            project_path: Chemin racine du projet
        """
        manifest_path = project_path / ".agent" / "consciousness_manifest.json"
        
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            
            # Importer les analyses causales
            self.import_from_local(manifest)
            
            # Exporter vers le projet
            self.export_to_local(project_path / ".agent")
            
            # Mettre à jour le registre des projets
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO projects (name, last_sync, knowledge_count)
                VALUES (?, ?, ?)
            """, (
                self.project_name,
                datetime.now().isoformat(),
                len(self._cache)
            ))
            
            conn.commit()
            conn.close()


# ===================================================================
# Instance globale
# ===================================================================

_global_memory_instance: Optional[GlobalMemory] = None

def get_global_memory(project_name: str = "default") -> GlobalMemory:
    """
    Obtient l'instance unique de la mémoire globale
    
    Args:
        project_name: Nom du projet
        
    Returns:
        Instance de GlobalMemory
    """
    global _global_memory_instance
    
    if _global_memory_instance is None:
        _global_memory_instance = GlobalMemory(project_name)
    
    return _global_memory_instance


# ===================================================================
# Example d'utilisation
# ===================================================================

if __name__ == "__main__":
    # Créer la mémoire globale
    mem = GlobalMemory(project_name="test-neural")
    
    # Stocker une connaissance
    kid = mem.store_knowledge(
        category="cache_optimization",
        pattern="Cache hit rate < 50%",
        solution="Augmenter TTL de 60s à 300s, max_entries de 1000 à 5000",
        success_rate=0.85
    )
    
    print(f"Connaissance stockée: {kid}")
    
    # Rechercher
    results = mem.find_pattern("cache hit rate")
    print(f"\nRésultats de recherche:")
    for r in results:
        print(f"  - {r.pattern}: {r.solution} ({r.success_rate:.0%})")
    
    # Stats
    stats = mem.get_stats()
    print(f"\nStatistiques:")
    print(f"  Total connaissances: {stats['total_knowledge']}")
    print(f"  Catégories: {list(stats['categories'].keys())}")
    print(f"  Emplacement: {stats['global_root']}")
