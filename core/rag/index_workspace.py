#!/usr/bin/env python3
"""Indexation complète du workspace Hephaistos-Kit"""
import os
import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime

# Ajouter le chemin du pipeline (résolu relativement à la racine du projet)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / '.agent' / 'rag'))

# Charger .env
env_path = Path('.env')
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and '=' in line and not line.startswith('#'):
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip().strip('"\'')

from pipeline import RAGPipeline

async def index_workspace():
    print(f"🚀 Début indexation Hephaistos-Kit - {datetime.now().strftime('%H:%M:%S')}")
    
    pipeline = RAGPipeline()
    
    # Indexer le répertoire .agent (priorité haute)
    print("\n📁 Indexation .agent/ (configuration, skills, workflows)...")
    report_agent = await pipeline.index_directory(
        '.agent',
        extensions=['.py', '.js', '.ts', '.json', '.md', '.yaml', '.yml', '.txt'],
        exclude_patterns=[
            'node_modules', '.git', '__pycache__',
            'dist', 'build', '.venv', 'venv',
            'memory-database', 'zvec-data',  # Dossiers data lourds
            '*.min.js', '*.bundle.js'
        ]
    )
    print(f"   ✅ Fichiers: {report_agent['files_processed']} | Chunks: {report_agent['total_chunks']} | Tags: {report_agent['total_tags']}")
    if report_agent['files_failed'] > 0:
        print(f"   ⚠️ Échecs: {report_agent['files_failed']}")
    
    # Indexer la racine (docs principales)
    print("\n📁 Indexation racine (README, docs)...")
    report_root = await pipeline.index_directory(
        '.',
        extensions=['.md', '.txt', '.json'],
        exclude_patterns=[
            'node_modules', '.git', '__pycache__',
            'dist', 'build', '.venv', 'venv',
            '.agent',  # Déjà indexé
            'memory-database'
        ]
    )
    print(f"   ✅ Fichiers: {report_root['files_processed']} | Chunks: {report_root['total_chunks']} | Tags: {report_root['total_tags']}")
    
    # Résumé
    print("\n" + "="*60)
    print("📊 RÉSUMÉ INDEXATION")
    print("="*60)
    total_files = report_agent['files_processed'] + report_root['files_processed']
    total_chunks = report_agent['total_chunks'] + report_root['total_chunks']
    total_tags = report_agent['total_tags'] + report_root['total_tags']
    total_failed = report_agent['files_failed'] + report_root['files_failed']
    
    print(f"   Fichiers traités: {total_files}")
    print(f"   Chunks créés: {total_chunks}")
    print(f"   Tags générés: {total_tags}")
    print(f"   Échecs: {total_failed}")
    
    # Stats finales
    print("\n📊 Stats du pipeline:")
    stats = pipeline.get_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    print(f"\n✅ Indexation terminée - {datetime.now().strftime('%H:%M:%S')}")
    
    return {
        'agent': report_agent,
        'root': report_root,
        'total': {
            'files': total_files,
            'chunks': total_chunks,
            'tags': total_tags,
            'failed': total_failed
        }
    }

if __name__ == '__main__':
    result = asyncio.run(index_workspace())
    
    # Sauvegarder le rapport
    report_path = Path('indexing_report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Rapport sauvegardé: {report_path}")
