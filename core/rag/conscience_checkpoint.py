"""
Conscience Checkpoint - Système de backup d'état simplifié

Version légère du "Git de conscience" sans complexité Git.

Fonctionnement:
1. Sauvegarde automatique à chaque réveil stable
2. Rotation des backups (garde les N derniers)
3. Restore rapide en cas de crash
"""
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List


class ConscienceCheckpoint:
    """
    Système de checkpoint simplifié pour la conscience.
    
    Alternative légère à Git pour versioning d'état.
    
    Example:
        >>> checkpoint = ConscienceCheckpoint()
        >>> checkpoint.save_checkpoint(manifest, reason="stable_state")
        >>> 
        >>> # Après crash
        >>> restored = checkpoint.restore_latest_stable()
    """
    
    def __init__(
        self,
        manifest_path: str = ".agent/consciousness_manifest.json",
        backup_dir: str = ".agent/consciousness_backups",
        max_backups: int = 10
    ):
        self.manifest_path = Path(manifest_path)
        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups
        
        # Créer le dossier de backups
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Fichier spécial pour "stable"
        self.stable_path = self.backup_dir / "manifest.stable.json"
    
    def save_checkpoint(self, manifest: dict, reason: str = "auto") -> Path:
        """
        Sauvegarde un checkpoint du manifeste
        
        Args:
            manifest: Le manifeste à sauvegarder
            reason: Raison de la sauvegarde (stable, degraded, etc.)
            
        Returns:
            Chemin du fichier sauvegardé
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"manifest.{timestamp}.{reason}.json"
        backup_path = self.backup_dir / filename
        
        # Sauvegarder
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        # Si c'est un état stable, mettre à jour le stable
        if reason == "stable" or manifest.get("current_state") == "healthy":
            shutil.copy(backup_path, self.stable_path)
        
        # Rotation : garder seulement les N derniers
        self._rotate_backups()
        
        return backup_path
    
    def _rotate_backups(self):
        """Garde seulement les N derniers backups"""
        backups = sorted(
            self.backup_dir.glob("manifest.*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        # Supprimer les vieux (sauf stable)
        for old_backup in backups[self.max_backups:]:
            if old_backup != self.stable_path:
                old_backup.unlink()
    
    def restore_latest_stable(self) -> Optional[dict]:
        """
        Restaure le dernier état stable
        
        Returns:
            Manifeste restauré ou None si pas de stable
        """
        if not self.stable_path.exists():
            print("❌ Pas d'état stable sauvegardé")
            return None
        
        with open(self.stable_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        # Restaurer aussi le manifeste principal
        shutil.copy(self.stable_path, self.manifest_path)
        
        print(f"✅ État stable restauré depuis: {self.stable_path}")
        print(f"   Date: {manifest.get('last_wake_up', 'unknown')}")
        print(f"   État: {manifest.get('current_state', 'unknown')}")
        
        return manifest
    
    def restore_specific(self, checkpoint_name: str) -> Optional[dict]:
        """
        Restaure un checkpoint spécifique
        
        Args:
            checkpoint_name: Nom du fichier checkpoint
            
        Returns:
            Manifeste restauré
        """
        checkpoint_path = self.backup_dir / checkpoint_name
        
        if not checkpoint_path.exists():
            print(f"❌ Checkpoint non trouvé: {checkpoint_name}")
            return None
        
        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        # Restaurer
        shutil.copy(checkpoint_path, self.manifest_path)
        
        print(f"✅ Checkpoint restauré: {checkpoint_name}")
        
        return manifest
    
    def list_checkpoints(self) -> List[dict]:
        """
        Liste tous les checkpoints disponibles
        
        Returns:
            Liste des checkpoints avec métadonnées
        """
        checkpoints = []
        
        for backup_file in sorted(self.backup_dir.glob("manifest.*.json")):
            try:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                
                parts = backup_file.stem.split('.')
                timestamp = parts[1] if len(parts) > 1 else "unknown"
                reason = parts[2] if len(parts) > 2 else "unknown"
                
                checkpoints.append({
                    "filename": backup_file.name,
                    "timestamp": timestamp,
                    "reason": reason,
                    "state": manifest.get("current_state", "unknown"),
                    "wake_count": manifest.get("wake_up_count", 0),
                    "size_kb": backup_file.stat().st_size / 1024
                })
            except Exception as e:
                print(f"⚠️ Erreur lecture {backup_file}: {e}")
        
        return checkpoints
    
    def get_diff(self, checkpoint1: str, checkpoint2: str) -> dict:
        """
        Compare deux checkpoints
        
        Returns:
            Différences entre les deux états
        """
        path1 = self.backup_dir / checkpoint1
        path2 = self.backup_dir / checkpoint2
        
        if not path1.exists() or not path2.exists():
            return {"error": "Checkpoint non trouvé"}
        
        with open(path1, 'r') as f:
            m1 = json.load(f)
        with open(path2, 'r') as f:
            m2 = json.load(f)
        
        return {
            "state_changed": m1.get("current_state") != m2.get("current_state"),
            "strategy_changed": m1.get("active_strategy") != m2.get("active_strategy"),
            "wake_count_diff": m2.get("wake_up_count", 0) - m1.get("wake_up_count", 0),
            "new_problems": len([
                p for p in m2.get("problem_database", [])
                if not any(p2["problem_id"] == p["problem_id"] for p2 in m1.get("problem_database", []))
            ])
        }
    
    def cleanup_old_checkpoints(self, days: int = 7):
        """
        Nettoie les checkpoints vieux de plus de N jours
        
        Args:
            days: Nombre de jours à conserver
        """
        import time
        
        cutoff = time.time() - (days * 24 * 60 * 60)
        removed = 0
        
        for backup_file in self.backup_dir.glob("manifest.*.json"):
            if backup_file.stat().st_mtime < cutoff and backup_file != self.stable_path:
                backup_file.unlink()
                removed += 1
        
        print(f"🗑️  {removed} vieux checkpoints supprimés")


# Intégration avec ConscienceManifest
def integrate_with_manifest():
    """
    Montre comment intégrer les checkpoints avec ConscienceManifest
    """
    print("""
# Dans conscience_manifest.py, ajouter:

from conscience_checkpoint import ConscienceCheckpoint

class ConscienceManifest:
    def __init__(self, ...):
        # ... existing code ...
        self.checkpoint = ConscienceCheckpoint()
    
    async def _wake_up(self):
        # ... existing wake up code ...
        
        # Sauvegarder checkpoint si état stable
        if manifest["current_state"] == "healthy":
            self.checkpoint.save_checkpoint(manifest, reason="stable")
        
        # Sauvegarder aussi si changement majeur
        if state_changed:
            self.checkpoint.save_checkpoint(manifest, reason="state_change")
    
    def recover_from_crash(self):
        '''Restaure après crash'''
        return self.checkpoint.restore_latest_stable()
""")


if __name__ == '__main__':
    # Demo
    print("=" * 60)
    print("  CONSCIENCE CHECKPOINT - Demo")
    print("=" * 60)
    
    checkpoint = ConscienceCheckpoint()
    
    # Simuler un manifeste
    test_manifest = {
        "current_state": "healthy",
        "active_strategy": "standard",
        "wake_up_count": 42,
        "last_wake_up": datetime.now().isoformat()
    }
    
    # Sauvegarder
    print("\n💾 Sauvegarde checkpoint stable...")
    path = checkpoint.save_checkpoint(test_manifest, reason="stable")
    print(f"   Sauvegardé: {path.name}")
    
    # Lister
    print("\n📋 Checkpoints disponibles:")
    for cp in checkpoint.list_checkpoints():
        print(f"   • {cp['filename']}")
        print(f"     État: {cp['state']}, Wake: {cp['wake_count']}")
    
    # Restore
    print("\n🔄 Restore depuis stable...")
    restored = checkpoint.restore_latest_stable()
    if restored:
        print(f"   ✅ Restauré: {restored['current_state']}")
    
    print("\n" + "=" * 60)
    print("Système de checkpoint prêt !")
    print("Prochaine étape: Intégrer dans ConscienceManifest")
