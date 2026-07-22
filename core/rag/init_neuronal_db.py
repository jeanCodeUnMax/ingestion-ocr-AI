"""
Script d'initialisation des tables SQLite pour le scoring neuronal

Ce script crée les tables nécessaires au fonctionnement du
système de scoring neuronal et de feedback.

Tables créées:
    - neuronal_weights: Stockage des poids adaptatifs
    - feedback_logs: Historique des feedbacks utilisateur

Usage:
    python init_neuronal_db.py [db_path]
    
    Par défaut: .agent/memory-database/neuronal.db
"""

import sqlite3
from pathlib import Path
import argparse


def create_tables(db_path: str) -> dict:
    """
    Crée les tables SQLite pour le scoring neuronal
    
    Args:
        db_path: Chemin vers le fichier SQLite
        
    Returns:
        Statut de création
    """
    # Créer le répertoire parent si nécessaire
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    results = {}
    
    # Table neuronal_weights
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS neuronal_weights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                weight_name TEXT NOT NULL,
                weight_value REAL NOT NULL,
                session_id TEXT,
                feedback_count INTEGER DEFAULT 0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        results["neuronal_weights"] = "created"
    except Exception as e:
        results["neuronal_weights"] = f"error: {e}"
    
    # Table feedback_logs
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interaction_id TEXT NOT NULL,
                rating REAL CHECK(rating BETWEEN -1 AND 1),
                feedback_type TEXT,
                correction TEXT,
                context_snapshot TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT FALSE
            )
        """)
        results["feedback_logs"] = "created"
    except Exception as e:
        results["feedback_logs"] = f"error: {e}"
    
    # Index pour performances
    try:
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback_interaction 
            ON feedback_logs(interaction_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback_created 
            ON feedback_logs(created_at)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_weights_session 
            ON neuronal_weights(session_id)
        """)
        results["indexes"] = "created"
    except Exception as e:
        results["indexes"] = f"error: {e}"
    
    # Insérer les poids par défaut
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO neuronal_weights (weight_name, weight_value, session_id)
            VALUES 
                ('semantic', 0.4, 'default'),
                ('recency', 0.4, 'default'),
                ('popularity', 0.2, 'default')
        """)
        results["default_weights"] = "inserted"
    except Exception as e:
        results["default_weights"] = f"error: {e}"
    
    conn.commit()
    conn.close()
    
    return results


def verify_tables(db_path: str) -> dict:
    """
    Vérifie que les tables existent et contiennent les données attendues
    
    Args:
        db_path: Chemin vers le fichier SQLite
        
    Returns:
        Statut de vérification
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    results = {}
    
    # Vérifier neuronal_weights
    cursor.execute("SELECT COUNT(*) FROM neuronal_weights")
    weights_count = cursor.fetchone()[0]
    results["neuronal_weights_count"] = weights_count
    
    # Vérifier feedback_logs
    cursor.execute("SELECT COUNT(*) FROM feedback_logs")
    feedback_count = cursor.fetchone()[0]
    results["feedback_logs_count"] = feedback_count
    
    # Lister les tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    results["tables"] = tables
    
    conn.close()
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialisation DB Neuronal Scoring")
    parser.add_argument(
        "--db-path",
        default=".agent/memory-database/neuronal.db",
        help="Chemin vers le fichier SQLite"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Vérifier les tables existantes"
    )
    
    args = parser.parse_args()
    
    if args.verify:
        print(f"Vérification de {args.db_path}...")
        results = verify_tables(args.db_path)
        print(f"Résultats: {results}")
    else:
        print(f"Création des tables dans {args.db_path}...")
        results = create_tables(args.db_path)
        print(f"Résultats: {results}")
        
        # Vérifier après création
        print("\nVérification post-création:")
        verify_results = verify_tables(args.db_path)
        print(f"Tables: {verify_results['tables']}")
        print(f"Poids initiaux: {verify_results['neuronal_weights_count']} entrées")
