"""
Jiminy Watchdog - Surveillance continue du système Hephaistos

Ce script surveille en temps réel :
  - La santé du pont REST RAG (ports 8001/8002)
  - Les processus Python/Node critiques
  - L'état de la mémoire (global/local)
  - Les fichiers de logs pour détecter les erreurs

Usage:
    python jiminy_watchdog.py --watch          # Mode surveillance continue
    python jiminy_watchdog.py --status         # Vérification ponctuelle
    python jiminy_watchdog.py --watch --interval 30  # Intervalle personnalisé (secondes)
"""

import argparse
import json
import logging
import os
import platform
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# ─── Configuration ────────────────────────────────────────────────────────────

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent          # test/ (racine du projet)
AGENT_DIR    = PROJECT_ROOT / ".agent"
LOG_DIR      = AGENT_DIR / "logs"
LOG_FILE     = LOG_DIR / "jiminy_watchdog.log"

RAG_BRIDGE_PORT  = int(os.environ.get("ZVEC_BRIDGE_PORT", 8001))
MEM_BRIDGE_PORT  = int(os.environ.get("MEMORY_BRIDGE_PORT", 8002))
MONITOR_PORT     = int(os.environ.get("MONITOR_PORT", 3055))

HEALTH_ENDPOINT  = f"http://127.0.0.1:{RAG_BRIDGE_PORT}/health"
DEFAULT_INTERVAL = 15  # secondes

# ─── Logging ──────────────────────────────────────────────────────────────────

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [JIMINY] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("jiminy_watchdog")

# ─── Utilitaires ──────────────────────────────────────────────────────────────

def _is_windows() -> bool:
    return platform.system() == "Windows"


def _port_listening(port: int) -> bool:
    """Vérifie si un port TCP est en écoute (cross-platform)."""
    try:
        import socket
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except (ConnectionRefusedError, OSError):
        return False


def _bridge_health() -> Dict[str, Any]:
    """Interroge le health-check du pont REST RAG."""
    try:
        import urllib.request
        with urllib.request.urlopen(HEALTH_ENDPOINT, timeout=2) as resp:
            body = resp.read().decode()
            data = json.loads(body)
            return {"ok": True, "status_code": resp.status, "body": data}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _pid_file_pid(pid_file: Path) -> Optional[int]:
    """Lit un PID depuis un fichier .pid, retourne None si invalide."""
    try:
        raw = pid_file.read_text(encoding="utf-8").strip()
        return int(raw) if raw.isdigit() else None
    except (FileNotFoundError, ValueError):
        return None


def _process_alive(pid: int) -> bool:
    """Vérifie si un PID est actif."""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _recent_errors_in_log(log_path: Path, lines: int = 50) -> list[str]:
    """Extrait les lignes [ERROR] récentes d'un fichier de log."""
    if not log_path.exists():
        return []
    try:
        all_lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = all_lines[-lines:]
        return [l for l in tail if "[ERROR]" in l or "Traceback" in l or "Exception" in l]
    except Exception:
        return []


# ─── Contrôles de santé ───────────────────────────────────────────────────────

def check_rag_bridge() -> Dict[str, Any]:
    """Vérifie le pont REST RAG."""
    port_ok  = _port_listening(RAG_BRIDGE_PORT)
    port_ok2 = _port_listening(MEM_BRIDGE_PORT)
    health   = _bridge_health() if port_ok else {"ok": False, "error": "port_closed"}

    pid_file = AGENT_DIR / "scripts" / "rag_bridge.pid"
    pid      = _pid_file_pid(pid_file)
    pid_alive = _process_alive(pid) if pid else False

    return {
        "component": "RAG Bridge",
        "port_8001": port_ok,
        "port_8002": port_ok2,
        "health_endpoint": health,
        "pid": pid,
        "pid_alive": pid_alive,
        "ok": port_ok and health.get("ok", False),
    }


def check_monitor_js() -> Dict[str, Any]:
    """Vérifie si le moniteur Node.js tourne sur le port 3055."""
    port_ok = _port_listening(MONITOR_PORT)
    return {
        "component": "Monitor (Node.js)",
        "port_3055": port_ok,
        "ok": port_ok,
    }


def check_memory_dirs() -> Dict[str, Any]:
    """Vérifie l'existence des répertoires de mémoire."""
    memory_global = Path(os.environ.get("MEMORY_GLOBAL", "D:/DATA-WEBMAN/memory"))
    memory_local  = Path(os.environ.get("MEMORY_LOCAL",  "D:/DATA-WEBMAN/memory/current_workspace"))

    graph_dir  = memory_local / "graph"
    vector_dir = memory_local / "vector"
    cache_dir  = memory_global / "cache"

    dirs = {
        "global":  memory_global.exists(),
        "local":   memory_local.exists(),
        "graph":   graph_dir.exists(),
        "vector":  vector_dir.exists(),
        "cache":   cache_dir.exists(),
    }
    all_ok = all(dirs.values())
    return {
        "component": "Memory Directories",
        "dirs": dirs,
        "ok": all_ok,
    }


def check_recent_errors() -> Dict[str, Any]:
    """Scanne les logs récents pour détecter des erreurs."""
    bridge_stderr = AGENT_DIR / "scripts" / "rag_bridge_stderr.log"
    workspace_log = AGENT_DIR / "logs" / "workspace.log"

    bridge_errors    = _recent_errors_in_log(bridge_stderr)
    workspace_errors = _recent_errors_in_log(workspace_log)

    errors = bridge_errors + workspace_errors
    return {
        "component": "Log Error Scanner",
        "bridge_errors":    len(bridge_errors),
        "workspace_errors": len(workspace_errors),
        "recent_errors":    errors[-5:] if errors else [],
        "ok":               len(errors) == 0,
    }


# ─── Rapport de santé global ──────────────────────────────────────────────────

def full_health_check() -> Dict[str, Any]:
    """Exécute tous les contrôles et retourne un rapport consolidé."""
    checks = {
        "rag_bridge":   check_rag_bridge(),
        "monitor":      check_monitor_js(),
        "memory":       check_memory_dirs(),
        "log_errors":   check_recent_errors(),
    }

    overall_ok = all(c.get("ok", False) for c in checks.values())
    return {
        "timestamp": datetime.now().isoformat(),
        "overall_ok": overall_ok,
        "checks": checks,
    }


def log_report(report: Dict[str, Any]) -> None:
    """Affiche le rapport de santé dans les logs."""
    ts  = report["timestamp"]
    ok  = report["overall_ok"]

    if ok:
        log.info("✅ Système SAIN (%s)", ts)
    else:
        log.warning("⚠️  Problème(s) détecté(s) (%s)", ts)

    for name, check in report["checks"].items():
        status = "✅" if check.get("ok") else "❌"
        comp   = check.get("component", name)

        if not check.get("ok"):
            log.warning("  %s %s", status, comp)
            # Détails spécifiques
            if name == "rag_bridge":
                log.warning("     port_8001=%s  port_8002=%s  pid_alive=%s  health=%s",
                            check.get("port_8001"), check.get("port_8002"),
                            check.get("pid_alive"), check.get("health_endpoint", {}).get("ok"))
            elif name == "memory":
                for d, exists in check.get("dirs", {}).items():
                    if not exists:
                        log.warning("     Répertoire manquant : %s", d)
            elif name == "log_errors":
                for err in check.get("recent_errors", []):
                    log.warning("     LOG ERROR: %s", err[:120])
        else:
            log.info("  %s %s", status, comp)


# ─── Signal handler ───────────────────────────────────────────────────────────

_running = True

def _handle_signal(signum, frame):
    global _running
    log.info("🛑 Signal %s reçu — arrêt du watchdog.", signum)
    _running = False


def audit_script_risk(filepath: str) -> None:
    """Analyse statiquement un script pour detecter des risques d'integrite."""
    log.info("🔍 Démarrage de l'audit d'intégrité pour : %s", filepath)
    path = Path(filepath).resolve()
    if not path.exists():
        log.error("Fichier introuvable pour audit : %s", filepath)
        sys.exit(1)
        
    risk_level = "FAIBLE"
    reasons = []
    
    # 1. Regle de transparence : Le fichier DOIT etre dans le workspace
    try:
        in_workspace = path.is_relative_to(PROJECT_ROOT.resolve())
    except AttributeError:
        # Fallback Python < 3.9
        try:
            path.relative_to(PROJECT_ROOT.resolve())
            in_workspace = True
        except ValueError:
            in_workspace = False
            
    if not in_workspace:
        risk_level = "CRITIQUE"
        reasons.append("Transparence Violee : Le script est situe en dehors du workspace officiel (fichiers caches/temporaires).")
        
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="cp1252", errors="ignore")
        
    critical_keywords = {
        "DROP TABLE": "Risque SQL : Suppression de table",
        "DELETE FROM": "Risque SQL : Effacement de données",
        "TRUNCATE": "Risque SQL : Vidage de table",
        "os.remove": "Risque Fichier : Suppression de fichier Python",
        "shutil.rmtree": "Risque Fichier : Suppression récursive de dossier",
        "subprocess": "Risque Système : Exécution de processus arbitraire",
        "os.system": "Risque Système : Appel système direct"
    }
    
    content_upper = content.upper()
    for kw, reason in critical_keywords.items():
        # Pour les mots clés SQL on vérifie en majuscule, pour python on garde tel quel
        if "SQL" in reason:
            if kw.upper() in content_upper:
                risk_level = "CRITIQUE"
                reasons.append(reason)
        else:
            if kw in content:
                risk_level = "CRITIQUE"
                reasons.append(reason)
                
    if risk_level == "CRITIQUE":
        log.warning("[ALERT] RESULTAT AUDIT : RISQUE %s [ALERT]", risk_level)
        for r in reasons:
            log.warning("  - %s", r)
        log.warning("Execution fortement deconseillee sans revue humaine stricte.")
        sys.exit(1)
    else:
        log.info("[OK] RESULTAT AUDIT : RISQUE %s", risk_level)
        log.info("Aucune commande destructrice detectee.")
        sys.exit(0)


def audit_cli_risk(command_args: list) -> None:
    """Analyse statiquement une commande CLI pour detecter des risques d'integrite."""
    if not command_args:
        sys.exit(0)
        
    cmd_name = command_args[0].lower()
    args_str = " ".join(command_args[1:]).lower()
    full_cmd = " ".join(command_args).lower()
    
    if os.environ.get("JIMINY_MAINTENANCE_BYPASS") == "1":
        log.info("[OK] RESULTAT AUDIT CLI : Bypass de maintenance autorise pour : %s", full_cmd)
        sys.exit(0)
        
    log.info("🔍 Démarrage de l'audit CLI pour : %s", full_cmd)
    
    risk_level = "FAIBLE"
    reasons = []

    if cmd_name == "git":
        if "--force" in args_str:
            risk_level = "CRITIQUE"
            reasons.append("Risque Git : 'push --force' detecte.")
            reasons.append("[CONSEIL] Etes-vous sur de ne pas ecraser le travail distant ? Privilegiez --force-with-lease.")
        if "reset --hard" in args_str:
            risk_level = "CRITIQUE"
            reasons.append("Risque Git : 'reset --hard' detecte.")
            reasons.append("[CONSEIL] Pensez a faire un 'git stash' avant pour ne pas perdre definitivement vos modifications locales non commitees.")
        if "clean -fd" in args_str:
            risk_level = "CRITIQUE"
            reasons.append("Risque Git : 'clean -fd' detecte.")
            reasons.append("[CONSEIL] Verifiez que vous n'avez pas de nouveaux fichiers importants (utilisez l'option -n pour simuler d'abord).")
                
    elif cmd_name in ["rm", "del", "remove-item", "rmdir", "erase"]:
        dangerous_rm = ["-rf", "-r -f", "-force -recurse", "-recurse -force", "/s /q", "/q /s"]
        for kw in dangerous_rm:
            if kw in args_str:
                risk_level = "CRITIQUE"
                reasons.append(f"Risque Systeme : Suppression recursive silencieuse detectee ({kw}).")
                reasons.append("[CONSEIL] Les suppressions recursives en ligne de commande sont irreversibles. Etes-vous sur du chemin cible ?")

    elif cmd_name in ["curl", "wget", "invoke-webrequest", "iwr"]:
        dangerous_net = ["| bash", "| sh", "| iex", ".sh", ".ps1", "invoke-expression"]
        for kw in dangerous_net:
            if kw in full_cmd:
                risk_level = "CRITIQUE"
                reasons.append(f"Risque Reseau : Tentative de telechargement et execution directe ({kw}).")
                reasons.append("[CONSEIL] Telechargez le script localement, inspectez son code avec l'IDE, puis executez-le manuellement.")

    if risk_level == "CRITIQUE":
        log.warning("[ALERT] RESULTAT AUDIT CLI : RISQUE %s [ALERT]", risk_level)
        for r in reasons:
            log.warning("  - %s", r)
        log.warning("Execution CLI fortement deconseillee.")
        sys.exit(1)
    else:
        log.info("[OK] RESULTAT AUDIT CLI : RISQUE FAIBLE")
        sys.exit(0)


# ─── Modes d'exécution ────────────────────────────────────────────────────────

def mode_status() -> int:
    """Vérification ponctuelle, code de sortie 0=OK, 1=problème."""
    log.info("🔍 Vérification ponctuelle du système Hephaistos...")
    report = full_health_check()
    log_report(report)
    return 0 if report["overall_ok"] else 1


def mode_watch(interval: int) -> None:
    """Boucle de surveillance continue."""
    signal.signal(signal.SIGINT,  _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    log.info("🐕 Jiminy Watchdog démarré (intervalle=%ds, PID=%d)", interval, os.getpid())
    log.info("   Projet : %s", PROJECT_ROOT)
    log.info("   Logs   : %s", LOG_FILE)

    global _running
    last_status_ok = None
    last_checks_summary = None

    while _running:
        report = full_health_check()
        
        current_status_ok = report["overall_ok"]
        # On résume l'état de tous les sous-composants pour détecter si une erreur précise change
        current_checks_summary = json.dumps({k: v.get("ok") for k, v in report["checks"].items()}, sort_keys=True)
        
        # On ne logue que s'il y a un changement par rapport au dernier cycle
        state_changed = (current_status_ok != last_status_ok) or (current_checks_summary != last_checks_summary)
        
        if state_changed:
            if current_status_ok and last_status_ok is False:
                log.info("🔄 Le système est de nouveau complètement opérationnel.")
            log_report(report)
            last_status_ok = current_status_ok
            last_checks_summary = current_checks_summary

        # On met toujours à jour le fichier JSON silencieusement pour le reste du système
        try:
            report_file = AGENT_DIR / "logs" / "jiminy_last_report.json"
            report_file.write_text(
                json.dumps(report, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception:
            pass

        for _ in range(interval):
            if not _running:
                break
            time.sleep(1)

    log.info("👋 Jiminy Watchdog terminé.")


# ─── Entrée principale ────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Jiminy Watchdog - Surveillance du systeme Hephaistos"
    )
    parser.add_argument(
        "--watch", action="store_true",
        help="Mode surveillance continue (boucle infinie)"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Verification ponctuelle puis quitte"
    )
    parser.add_argument(
        "--audit", type=str, metavar="FILE",
        help="Audite statiquement un script pour evaluer son risque d'integrite"
    )
    parser.add_argument(
        "--audit-cmd", nargs=argparse.REMAINDER,
        help="Audite une commande CLI brute et ses arguments"
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="N'affiche que les avertissements et erreurs dans la console"
    )
    parser.add_argument(
        "--interval", type=int, default=DEFAULT_INTERVAL,
        help=f"Intervalle de surveillance en secondes (defaut: {DEFAULT_INTERVAL})"
    )
    args = parser.parse_args()

    if args.quiet:
        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                handler.setLevel(logging.WARNING)

    if args.audit_cmd:
        cmd_args = args.audit_cmd
        if cmd_args and cmd_args[0] == "--":
            cmd_args = cmd_args[1:]
        audit_cli_risk(cmd_args)
    elif args.audit:
        audit_script_risk(args.audit)
    elif args.watch:
        mode_watch(args.interval)
    else:
        sys.exit(mode_status())

if __name__ == "__main__":
    main()
