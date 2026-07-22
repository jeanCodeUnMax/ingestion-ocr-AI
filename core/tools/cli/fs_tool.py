import os
import sys
from pathlib import Path

def list_directory(path="."):
    """Liste les fichiers de manière structurée."""
    try:
        root = Path(path)
        result = [f"Contenu de {root.absolute()}:"]
        for item in root.iterdir():
            prefix = "[DIR] " if item.is_dir() else "[FILE]"
            result.append(f"{prefix} {item.name}")
        return "\n".join(result)
    except Exception as e:
        return f"Erreur listing: {e}"

def read_file(path):
    """Lit le contenu d'un fichier."""
    try:
        file_path = Path(path)
        if not file_path.exists():
            return f"❌ Le fichier {path} n'existe pas."
        if file_path.stat().st_size > 100000: # Sécurité : pas de fichiers géants
            return "⚠️ Fichier trop volumineux pour être lu entièrement."
        
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return f"📄 CONTENU DE {path} :\n---\n{content}\n---"
    except Exception as e:
        return f"❌ Erreur lecture: {e}"

def write_file(path, content):
    """Écrit ou écrase un fichier."""
    try:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ Fichier {path} écrit avec succès."
    except Exception as e:
        return f"❌ Erreur écriture: {e}"

def take_screenshot():
    """Prend une capture d'écran et la sauvegarde."""
    try:
        import pyautogui
        from datetime import datetime
        
        shots_dir = Path("core/features/jiminy_pipeline_enrichi/screenshots")
        shots_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screen_{timestamp}.png"
        file_path = shots_dir / filename
        
        pyautogui.screenshot(str(file_path))
        return f"📸 Capture d'écran effectuée : {file_path.absolute()}"
    except ImportError:
        return "❌ Erreur: 'pyautogui' n'est pas installé. Installez-le avec 'pip install pyautogui'."
    except Exception as e:
        return f"❌ Erreur capture: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: fs_tool.py [list|read|write|screenshot] [path] [content]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "list":
        target = sys.argv[2] if len(sys.argv) > 2 else "."
        print(list_directory(target))
    elif cmd == "read":
        target = sys.argv[2] if len(sys.argv) > 2 else "."
        print(read_file(target))
    elif cmd == "write":
        target = sys.argv[2]
        content = sys.argv[3] if len(sys.argv) > 3 else ""
        print(write_file(target, content))
    elif cmd == "screenshot":
        print(take_screenshot())
