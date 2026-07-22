import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

class JiminyPerception:
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.perception_dir = workspace_root / "core/features/jiminy_pipeline_enrichi/perception"
        self.perception_dir.mkdir(parents=True, exist_ok=True)

    def capture_terminal_state(self):
        """Capture un résumé de l'état du système et du terminal."""
        try:
            # On récupère les dernières lignes du log si il existe
            log_content = "N/A"
            log_file = self.workspace_root / "jiminy.log"
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    log_content = "".join(f.readlines()[-20:])

            state = {
                "timestamp": datetime.now().isoformat(),
                "cwd": os.getcwd(),
                "last_logs": log_content,
                "active_processes": self._get_active_python_procs()
            }
            return state
        except Exception as e:
            return f"Error capturing terminal: {e}"

    def _get_active_python_procs(self):
        """Liste les processus Python en cours (simplifié pour Windows)."""
        try:
            output = subprocess.check_output('tasklist /FI "IMAGENAME eq python.exe"', shell=True, text=True)
            return output
        except:
            return "Impossible de lister les processus."

    def take_system_snapshot(self):
        """Prend un screenshot et capture les logs système."""
        try:
            import pyautogui
            shot_path = self.perception_dir / f"snap_{datetime.now().strftime('%H%M%S')}.png"
            pyautogui.screenshot(str(shot_path))
            return str(shot_path)
        except ImportError:
            return "pyautogui non installé"
        except Exception as e:
            return f"Erreur screenshot: {e}"

    def get_full_context_snapshot(self):
        """Génère un bloc texte de perception pour le prompt."""
        terminal = self.capture_terminal_state()
        
        snapshot_text = f"""
### PERCEPTION SYSTÈME (TEMPS RÉEL) ###
- Horodatage : {terminal['timestamp']}
- Répertoire : {terminal['cwd']}
- Processus Actifs : 
{terminal['active_processes']}

- Derniers Logs (stdout/stderr) :
{terminal['last_logs']}
---------------------------------------
"""
        return snapshot_text

if __name__ == "__main__":
    p = JiminyPerception(Path("."))
    print(p.get_full_context_snapshot())
