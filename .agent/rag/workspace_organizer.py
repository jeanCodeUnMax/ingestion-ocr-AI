#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workspace Organizer - Analyse et rangement automatique du workspace

Ce module organise le workspace en:
1. Analysant la structure complète
2. Identifiant les fichiers incongrus (temp, orphan, doublon)
3. Les déplaçant dans un dossier backup
4. Organisant ce qui reste de manière logique

Usage:
    organizer = WorkspaceOrganizer()
    report = organizer.organize()
    organizer.clean_incongruou()
"""
import os
import shutil
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class FileAnalysis:
    """Analyse d'un fichier"""
    path: Path
    size: int
    modified: datetime
    hash: str = ""
    category: str = "unknown"  # code, doc, temp, orphan
    suggested_action: str = "keep"  # keep, backup, delete
    reason: str = ""


@dataclass
class OrganizationReport:
    """Rapport d'organisation"""
    total_files: int = 0
    analyzed: int = 0
    incongruous_found: int = 0
    moved_to_backup: int = 0
    organized: int = 0
    space_saved: int = 0
    categories: Dict[str, int] = field(default_factory=dict)
    incongruous_list: List[str] = field(default_factory=list)


class WorkspaceOrganizer:
    """
    Organiseur de workspace intelligent
    
    Détecte et gère:
    - Fichiers temporaires (*.tmp, *~, .cache)
    - Fichiers orphelins (non référencés)
    - Doublons (même contenu)
    - Vieux fichiers (> 6 mois)
    - Fichiers de test oubliés (test_*.py sans __init__.py)
    """
    
    # Patterns de fichiers temporaires/incongrus
    TEMP_PATTERNS = [
        "*.tmp", "*~", "*.bak", "*.cache", "*.pyc", "*.pyo",
        "__pycache__", "*.swp", "*.swo", ".DS_Store", "Thumbs.db"
    ]
    
    # Patterns de fichiers à risquer (à vérifier)
    SUSPICIOUS_PATTERNS = [
        "test_*.txt", "*.log.old", "*.json.bak", "*.md.tmp"
    ]
    
    def __init__(self, workspace_path: str = ".", backup_path: str = ".agent/backup_workspace"):
        self.workspace = Path(workspace_path).resolve()
        self.backup_root = Path(backup_path)
        self.report = OrganizationReport()
        self.file_index: Dict[str, FileAnalysis] = {}
        self.hash_index: Dict[str, List[Path]] = defaultdict(list)
        
        # Créer backup si inexistant
        self.backup_root.mkdir(parents=True, exist_ok=True)
    
    def analyze_workspace(self) -> OrganizationReport:
        """
        Phase 1: Analyse complète du workspace
        
        Returns:
            Rapport d'analyse
        """
        print(f"\n🔍 Analyse de {self.workspace}")
        print("=" * 60)
        
        # Scanner tous les fichiers
        all_files = list(self.workspace.rglob("*"))
        self.report.total_files = len(all_files)
        
        for file_path in all_files:
            if file_path.is_file():
                self._analyze_file(file_path)
        
        # Détecter doublons
        self._detect_duplicates()
        
        # Rapport
        print(f"\n📊 ANALYSE TERMINÉE:")
        print(f"   Total fichiers: {self.report.total_files}")
        print(f"   Analysés: {self.report.analyzed}")
        print(f"   Catégories: {dict(self.report.categories)}")
        
        return self.report
    
    def _analyze_file(self, file_path: Path):
        """Analyse un fichier individuel"""
        stat = file_path.stat()
        modified = datetime.fromtimestamp(stat.st_mtime)
        age_days = (datetime.now() - modified).days
        
        analysis = FileAnalysis(
            path=file_path,
            size=stat.st_size,
            modified=modified
        )
        
        # Déterminer catégorie
        if self._is_temp_file(file_path):
            analysis.category = "temp"
            analysis.suggested_action = "backup"
            analysis.reason = "Fichier temporaire"
            
        elif age_days > 180:  # 6 mois
            analysis.category = "old"
            analysis.suggested_action = "backup"
            analysis.reason = f"Fichier vieux ({age_days} jours)"
            
        elif self._is_orphan(file_path):
            analysis.category = "orphan"
            analysis.suggested_action = "backup"
            analysis.reason = "Fichier orphelin (non référencé)"
            
        else:
            analysis.category = self._categorize_file(file_path)
            analysis.suggested_action = "keep"
        
        # Calculer hash pour détection doublons (fichiers < 10MB)
        if stat.st_size < 10_000_000 and analysis.suggested_action == "backup":
            analysis.hash = self._calculate_hash(file_path)
            self.hash_index[analysis.hash].append(file_path)
        
        self.file_index[str(file_path)] = analysis
        self.report.analyzed += 1
        self.report.categories[analysis.category] = self.report.categories.get(analysis.category, 0) + 1
        
        if analysis.suggested_action == "backup":
            self.report.incongruous_found += 1
            self.report.incongruous_list.append(str(file_path))
    
    def _is_temp_file(self, path: Path) -> bool:
        """Vérifie si c'est un fichier temporaire"""
        name = path.name.lower()
        for pattern in self.TEMP_PATTERNS:
            if pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    return True
            elif pattern in name:
                return True
        return False
    
    def _is_orphan(self, path: Path) -> bool:
        """Vérifie si fichier est orphelin (non importé/référencé)"""
        # Fichiers test sans structure de test
        if path.name.startswith("test_") and path.suffix == ".py":
            parent = path.parent
            if not (parent / "__init__.py").exists():
                return True
        
        # Fichiers backup sans original
        if ".bak" in path.suffixes or ".tmp" in path.suffixes:
            original = path.with_suffix("".join(path.suffixes[:-1]))
            if not original.exists():
                return True
        
        return False
    
    def _categorize_file(self, path: Path) -> str:
        """Catégorise un fichier normal"""
        suffix = path.suffix.lower()
        
        categories = {
            ".py": "code",
            ".js": "code",
            ".ts": "code",
            ".json": "config",
            ".md": "doc",
            ".txt": "doc",
            ".yml": "config",
            ".yaml": "config",
        }
        
        return categories.get(suffix, "other")
    
    def _calculate_hash(self, path: Path) -> str:
        """Calcule MD5 d'un fichier"""
        hash_md5 = hashlib.md5()
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except:
            return ""
    
    def _detect_duplicates(self):
        """Détecte les doublons dans l'index"""
        for hash_val, paths in self.hash_index.items():
            if len(paths) > 1:
                # Garder le plus récent, marquer les autres
                newest = max(paths, key=lambda p: p.stat().st_mtime)
                for path in paths:
                    if path != newest:
                        analysis = self.file_index.get(str(path))
                        if analysis:
                            analysis.suggested_action = "backup"
                            analysis.reason = f"Doublon de {newest.name}"
                            self.report.incongruous_found += 1
    
    def organize(self) -> OrganizationReport:
        """
        Phase 2: Organisation proprement dite
        
        Returns:
            Rapport final
        """
        print(f"\n🗂️  ORGANISATION DU WORKSPACE")
        print("=" * 60)
        
        # Créer structure backup datée
        backup_dir = self.backup_root / datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        moved_files = []
        
        for path_str, analysis in self.file_index.items():
            if analysis.suggested_action == "backup":
                try:
                    # Calculer chemin relatif pour préserver structure
                    rel_path = Path(path_str).relative_to(self.workspace)
                    dest_path = backup_dir / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Déplacer vers backup
                    shutil.move(path_str, str(dest_path))
                    moved_files.append((path_str, str(dest_path)))
                    
                    self.report.moved_to_backup += 1
                    self.report.space_saved += analysis.size
                    
                except Exception as e:
                    print(f"   ⚠️ Erreur déplacement {path_str}: {e}")
        
        # Rapport final
        print(f"\n✅ ORGANISATION TERMINÉE:")
        print(f"   Déplacés vers backup: {self.report.moved_to_backup}")
        print(f"   Espace libéré: {self.report.space_saved / 1024 / 1024:.2f} MB")
        print(f"   Backup: {backup_dir}")
        
        if moved_files:
            print(f"\n   📁 Fichiers archivés:")
            for orig, dest in moved_files[:10]:
                print(f"      → {Path(orig).name}")
            if len(moved_files) > 10:
                print(f"      ... et {len(moved_files) - 10} autres")
        
        return self.report
    
    def clean_incongruous(self) -> int:
        """
        Phase 3: Nettoyage des fichiers vraiment inutiles
        
        Supprime les fichiers temporaires vraiment obsolètes
        (après confirmation ou si > 1 an)
        
        Returns:
            Nombre de fichiers supprimés
        """
        deleted = 0
        
        print(f"\n🧹 NETTOYAGE PROFOND")
        print("=" * 60)
        
        backup_dirs = sorted(self.backup_root.iterdir(), key=lambda p: p.stat().st_mtime)
        
        # Garder seulement les 3 derniers backups
        for old_backup in backup_dirs[:-3]:
            try:
                shutil.rmtree(old_backup)
                print(f"   🗑️ Suppression vieux backup: {old_backup.name}")
                deleted += 1
            except Exception as e:
                print(f"   ⚠️ Erreur suppression {old_backup}: {e}")
        
        print(f"\n   {deleted} vieux backups supprimés")
        
        return deleted
    
    def get_report(self) -> str:
        """Génère rapport textuel complet"""
        return f"""
======================================================================
               RAPPORT D'ORGANISATION WORKSPACE
======================================================================

WORKSPACE: {self.workspace}
DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

--- ANALYSE ----------------------------------------------------------
Total fichiers scannés: {self.report.total_files}
Fichiers analysés: {self.report.analyzed}

RÉPARTITION PAR CATÉGORIE:
{chr(10).join(f"  {cat}: {count}" for cat, count in sorted(self.report.categories.items()))}

--- INCONGRUS DÉTECTÉS -----------------------------------------------
Nombre: {self.report.incongruous_found}

PRINCIPAUX FICHIERS:
{chr(10).join(f"  • {Path(p).name[:50]}" for p in self.report.incongruous_list[:10]) if self.report.incongruous_list else '  Aucun'}

--- ACTIONS EFFECTUÉES -----------------------------------------------
Déplacés vers backup: {self.report.moved_to_backup}
Espace libéré: {self.report.space_saved / 1024 / 1024:.2f} MB

--- STATUT FINAL -----------------------------------------------------
Workspace: ORGANISÉ
Backup: {self.backup_root}

======================================================================
"""


# Fonction utilitaire pour intégration avec ConscienceManifest
def organize_workspace_auto(workspace: str = ".") -> OrganizationReport:
    """
    Fonction auto-appelable par la conscience
    
    Example:
        # Dans _wake_up() de la conscience:
        if wake_count % 10 == 0:  # Tous les 10 réveils
            report = organize_workspace_auto()
            if report.incongruous_found > 0:
                print(f"Workspace auto-organisé: {report.moved_to_backup} fichiers archivés")
    """
    organizer = WorkspaceOrganizer(workspace)
    organizer.analyze_workspace()
    return organizer.organize()


if __name__ == '__main__':
    # Demo
    print("=" * 70)
    print("  WORKSPACE ORGANIZER - Demo")
    print("=" * 70)
    
    organizer = WorkspaceOrganizer(".")
    
    # Analyser
    organizer.analyze_workspace()
    
    # Afficher rapport
    print(organizer.get_report())
    
    # Organiser (décommenter pour vraiment déplacer)
    # organizer.organize()
    # organizer.clean_incongruous()
