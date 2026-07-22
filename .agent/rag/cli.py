#!/usr/bin/env python3
"""
Hephaistos CLI - Interface de contrôle du pipeline RAG
"""

import asyncio
import argparse
import sys
import json
from pathlib import Path
from typing import List, Optional

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline import RAGPipeline

async def run_ingest(args):
    pipeline = RAGPipeline()
    print(f"[*] Initialisation de l'ingestion pour: {args.path}")
    
    try:
        path = Path(args.path)
        if path.is_file():
            result = await pipeline.index_document(
                content=path.read_text(encoding="utf-8", errors="ignore"),
                doc_type=args.type or "text",
                source_file=str(path),
                metadata={"source": "cli", "manual": True}
            )
            print(json.dumps(result, indent=2))
        elif path.is_dir():
            result = await pipeline.ingest_workspace(
                root_path=str(path)
            )
            print(f"[+] Ingestion terminee: {result['files_indexed']} fichiers indexes.")
            if result['errors']:
                print(f"[!] {len(result['errors'])} erreurs rencontrees.")
                if result['status'] == "error":
                    print("[!] L'ingestion a echoue completement.")
                    sys.exit(1)
                else:
                    print("[!] L'ingestion a reussi partiellement.")
        else:
            print(f"[!] Chemin non trouve: {args.path}")
            sys.exit(1)
    except Exception as e:
        print(f"[!] Erreur fatale: {e}")
        sys.exit(1)


async def run_search(args):
    pipeline = RAGPipeline()
    print(f"[*] Recherche pour: '{args.query}'")
    # Note: La méthode search du pipeline doit être implémentée ou appelée via fusion
    # Pour l'instant on simule l'appel via embedder manager
    results = await pipeline.embedder.search_dual(
        query=args.query,
        qdrant_collections=["code_index"], # Valeurs par défaut
        zvec_collections=["concepts_index"],
        limit=args.limit
    )
    print(json.dumps(results, indent=2))

def main():
    parser = argparse.ArgumentParser(description="Hephaistos RAG CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commandes disponibles")

    # Ingest
    ingest_parser = subparsers.add_parser("ingest", help="Ingérer un fichier ou un dossier")
    ingest_parser.add_argument("path", help="Chemin du fichier ou dossier")
    ingest_parser.add_argument("--type", help="Type de document (code, text, markdown)")
    
    # Search
    search_parser = subparsers.add_parser("search", help="Rechercher dans l'index")
    search_parser.add_argument("query", help="Requête textuelle")
    search_parser.add_argument("--limit", type=int, default=5, help="Limite de résultats")

    args = parser.parse_args()

    if args.command == "ingest":
        asyncio.run(run_ingest(args))
    elif args.command == "search":
        asyncio.run(run_search(args))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
