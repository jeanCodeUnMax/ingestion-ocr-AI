"""
Script d'audit du système RAG
Teste la structure, les imports et les fonctionnalités
"""

import sys
import os
import json
import ast
from pathlib import Path
from datetime import datetime

# Configuration
RAG_DIR = Path(__file__).parent
REPORT = {
    "date": datetime.now().isoformat(),
    "structure": {},
    "syntax": {},
    "imports": {},
    "classes": {},
    "functions": {},
    "errors": [],
    "warnings": [],
    "stats": {}
}

print("=" * 60)
print("AUDIT DU SYSTEME RAG - Hephaistos-Kit")
print("=" * 60)
print()

# 1. VERIFICATION DE LA STRUCTURE
print("1. VERIFICATION DE LA STRUCTURE")
print("-" * 40)

expected_files = {
    "__init__.py": "Module principal",
    "config.json": "Configuration",
    "chunker.py": "Découpage documents",
    "tagger.py": "Tagging automatique",
    "router.py": "Routage dual",
    "embedder.py": "Embeddings vectoriels",
    "fusion.py": "Fusion résultats",
    "pipeline.py": "Pipeline principal",
}

expected_dirs = {
    "utils": "Utilitaires",
    "tests": "Tests unitaires"
}

structure_ok = True
for file, desc in expected_files.items():
    path = RAG_DIR / file
    if path.exists():
        size = path.stat().st_size
        REPORT["structure"][file] = {"status": "OK", "size": size, "desc": desc}
        print(f"  ✓ {file} ({size} bytes) - {desc}")
    else:
        REPORT["structure"][file] = {"status": "MANQUANT", "desc": desc}
        REPORT["errors"].append(f"Fichier manquant: {file}")
        print(f"  ✗ {file} MANQUANT - {desc}")
        structure_ok = False

for dir_name, desc in expected_dirs.items():
    path = RAG_DIR / dir_name
    if path.exists() and path.is_dir():
        files = list(path.glob("*.py"))
        REPORT["structure"][dir_name] = {"status": "OK", "files": len(files), "desc": desc}
        print(f"  ✓ {dir_name}/ ({len(files)} fichiers) - {desc}")
    else:
        REPORT["structure"][dir_name] = {"status": "MANQUANT", "desc": desc}
        REPORT["errors"].append(f"Dossier manquant: {dir_name}")
        print(f"  ✗ {dir_name}/ MANQUANT - {desc}")
        structure_ok = False

print()

# 2. VERIFICATION DE LA SYNTAXE
print("2. VERIFICATION DE LA SYNTAXE PYTHON")
print("-" * 40)

python_files = list(RAG_DIR.glob("*.py")) + list(RAG_DIR.glob("*/*.py"))
syntax_ok = True

for py_file in python_files:
    rel_path = py_file.relative_to(RAG_DIR)
    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            code = f.read()
            tree = ast.parse(code)
            
            # Compter les classes et fonctions
            classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            
            REPORT["syntax"][str(rel_path)] = {
                "status": "OK",
                "classes": len(classes),
                "functions": len(functions),
                "lines": len(code.split('\n'))
            }
            print(f"  ✓ {rel_path} - {len(classes)} classes, {len(functions)} fonctions")
    except SyntaxError as e:
        REPORT["syntax"][str(rel_path)] = {"status": "ERREUR", "error": str(e)}
        REPORT["errors"].append(f"Erreur syntaxe {rel_path}: {e}")
        print(f"  ✗ {rel_path} - ERREUR: {e}")
        syntax_ok = False
    except Exception as e:
        REPORT["syntax"][str(rel_path)] = {"status": "ERREUR", "error": str(e)}
        REPORT["errors"].append(f"Erreur {rel_path}: {e}")
        print(f"  ✗ {rel_path} - ERREUR: {e}")
        syntax_ok = False

print()

# 3. VERIFICATION DE LA CONFIGURATION
print("3. VERIFICATION DE LA CONFIGURATION")
print("-" * 40)

config_path = RAG_DIR / "config.json"
config_ok = True

if config_path.exists():
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        required_sections = ["chunking", "tagging", "embedding", "routing", "fusion"]
        for section in required_sections:
            if section in config:
                print(f"  ✓ Section '{section}' présente")
            else:
                print(f"  ✗ Section '{section}' MANQUANTE")
                REPORT["warnings"].append(f"Section config manquante: {section}")
                config_ok = False
        
        REPORT["config"] = {"status": "OK", "sections": list(config.keys())}
    except json.JSONDecodeError as e:
        REPORT["errors"].append(f"JSON invalide dans config.json: {e}")
        print(f"  ✗ JSON invalide: {e}")
        config_ok = False
else:
    REPORT["errors"].append("config.json non trouvé")
    print("  ✗ config.json non trouvé")
    config_ok = False

print()

# 4. ANALYSE DES CLASSES
print("4. ANALYSE DES CLASSES PRINCIPALES")
print("-" * 40)

classes_info = {}

for py_file in [RAG_DIR / f for f in ["chunker.py", "tagger.py", "router.py", "embedder.py", "fusion.py", "pipeline.py"]]:
    if not py_file.exists():
        continue
    
    rel_path = py_file.name
    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            code = f.read()
            tree = ast.parse(code)
        
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        
        for cls in classes:
            methods = [m.name for m in cls.body if isinstance(m, ast.FunctionDef)]
            docstring = ast.get_docstring(cls) or "Pas de docstring"
            
            classes_info[f"{rel_path}:{cls.name}"] = {
                "methods": methods,
                "docstring": docstring[:100] + "..." if len(docstring) > 100 else docstring
            }
            
            print(f"  • {cls.name} ({rel_path})")
            print(f"    Méthodes: {len(methods)}")
            print(f"    Doc: {docstring[:60]}...")
    except Exception as e:
        print(f"  ✗ Erreur analyse {rel_path}: {e}")

REPORT["classes"] = classes_info
print()

# 5. VERIFICATION DES IMPORTS (sans exécution)
print("5. ANALYSE DES DEPENDANCES")
print("-" * 40)

dependencies = {
    "standard": set(),
    "third_party": set(),
    "local": set()
}

for py_file in RAG_DIR.glob("*.py"):
    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name.split('.')[0]
                    if name in ['json', 're', 'os', 'sys', 'pathlib', 'datetime', 'uuid', 'collections', 'typing', 'dataclasses', 'enum', 'asyncio']:
                        dependencies["standard"].add(name)
                    elif name in ['pytest', 'transformers', 'torch', 'requests']:
                        dependencies["third_party"].add(name)
                    else:
                        dependencies["local"].add(name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    name = node.module.split('.')[0]
                    if name in ['json', 're', 'os', 'sys', 'pathlib', 'datetime', 'uuid', 'collections', 'typing', 'dataclasses', 'enum', 'asyncio']:
                        dependencies["standard"].add(name)
                    elif name in ['pytest', 'transformers', 'torch', 'requests']:
                        dependencies["third_party"].add(name)
                    elif name.startswith('.'):
                        dependencies["local"].add(name)
    except:
        pass

print(f"  Bibliothèques standard: {', '.join(sorted(dependencies['standard']))}")
print(f"  Bibliothèques tierces: {', '.join(sorted(dependencies['third_party'])) or 'Aucune'}")
print(f"  Imports locaux: {len(dependencies['local'])}")

REPORT["dependencies"] = {
    "standard": list(dependencies["standard"]),
    "third_party": list(dependencies["third_party"]),
    "local_count": len(dependencies["local"])
}

# Vérifier les bibliothèques tierces requises
missing_deps = []
if "transformers" in dependencies["third_party"]:
    try:
        import transformers
    except ImportError:
        missing_deps.append("transformers")
        REPORT["warnings"].append("transformers non installé (optionnel pour embeddings locaux)")

if missing_deps:
    print(f"  ⚠ Dépendances manquantes: {', '.join(missing_deps)}")

print()

# 6. STATISTIQUES
print("6. STATISTIQUES")
print("-" * 40)

total_lines = 0
total_classes = 0
total_functions = 0

for file_info in REPORT["syntax"].values():
    if isinstance(file_info, dict) and "lines" in file_info:
        total_lines += file_info["lines"]
        total_classes += file_info.get("classes", 0)
        total_functions += file_info.get("functions", 0)

REPORT["stats"] = {
    "total_files": len(REPORT["syntax"]),
    "total_lines": total_lines,
    "total_classes": total_classes,
    "total_functions": total_functions,
    "errors_count": len(REPORT["errors"]),
    "warnings_count": len(REPORT["warnings"])
}

print(f"  Fichiers Python: {REPORT['stats']['total_files']}")
print(f"  Lignes de code: {REPORT['stats']['total_lines']}")
print(f"  Classes: {REPORT['stats']['total_classes']}")
print(f"  Fonctions: {REPORT['stats']['total_functions']}")
print(f"  Erreurs: {REPORT['stats']['errors_count']}")
print(f"  Avertissements: {REPORT['stats']['warnings_count']}")

print()

# 7. RESUME
print("=" * 60)
print("RESUME DE L'AUDIT")
print("=" * 60)

if REPORT["errors"]:
    print("\n❌ ERREURS DETECTEES:")
    for error in REPORT["errors"]:
        print(f"  - {error}")
else:
    print("\n✅ Aucune erreur critique")

if REPORT["warnings"]:
    print("\n⚠️  AVERTISSEMENTS:")
    for warning in REPORT["warnings"]:
        print(f"  - {warning}")

print()

# Score global
score = 100
score -= len(REPORT["errors"]) * 20
score -= len(REPORT["warnings"]) * 5
score = max(0, score)

print(f"SCORE GLOBAL: {score}/100")

if score >= 80:
    print("✅ SYSTÈME RAG OPÉRATIONNEL")
elif score >= 60:
    print("⚠️  SYSTÈME RAG FONCTIONNEL AVEC RÉSERVES")
else:
    print("❌ SYSTÈME RAG NÉCESSITE DES CORRECTIONS")

# Sauvegarder le rapport
report_path = RAG_DIR / "audit_report.json"
with open(report_path, 'w', encoding='utf-8') as f:
    json.dump(REPORT, f, indent=2, ensure_ascii=False)

print(f"\n📄 Rapport sauvegardé: {report_path}")
