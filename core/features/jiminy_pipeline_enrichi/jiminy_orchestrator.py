import asyncio
import json
import requests
import sys
import os
import re
import subprocess
from pathlib import Path

# Ajouter le dossier racine du projet au PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from core.features.jiminy_pipeline_enrichi.local_brain import JiminyLocalBrain
    from core.features.jiminy_pipeline_enrichi.perception_system import JiminyPerception
    from core.features.jiminy_pipeline_enrichi.episodic_memory import EpisodicMemory
except ImportError as e:
    print(f"❌ Erreur imports : {e}")
    sys.exit(1)

class JiminyOrchestrator:
    def __init__(self, model="qwen2.5:7b"):
        self.model = model
        self.brain = JiminyLocalBrain()
        self.perception = JiminyPerception(ROOT_DIR)
        self.memory = EpisodicMemory(ROOT_DIR)
        # On repasse sur localhost pour laisser Windows gérer
        self.ollama_url = "http://localhost:11434/api/generate"
        print(f"📡 Orchestrateur configuré pour Ollama sur {self.ollama_url}")

    async def run_task(self, user_query: str):
        # 1. Préparation de la conscience
        await self.brain.initialize()
        self.memory.initialize()
        
        super_prompt = await self.brain.generate_composite_prompt(user_query)
        
        # 2. Injection de la perception temps réel (AVANT les outils)
        system_perception = self.perception.get_full_context_snapshot()
        
        tools_instruction = (
            "\n\n### RÈGLE D'OR DE L'ACTION ###\n"
            "Tu es un AGENT ACTIF doué de mémoire.\n"
            "Si l'utilisateur te demande une info factuelle, UTILISE UN OUTIL.\n"
            "Si tu as l'impression d'avoir déjà fait cette tâche, UTILISE SEARCH_MEMORY.\n\n"
            "Outils disponibles :\n"
            "ACTION: SEARCH_ZVEC \"experts\" (Savoir théorique)\n"
            "ACTION: SEARCH_MEMORY \"recherche\" (Souvenirs de tes tâches passées)\n"
            "ACTION: LIST_DIR \"dossier\"\n"
            "ACTION: READ_FILE \"fichier\"\n"
            "ACTION: WRITE_FILE \"fichier\" \"nouveau contenu\"\n"
            "ACTION: TAKE_SCREENSHOT\n"
            "\nUne seule action à la fois. N'explique pas, FAIS-LE."
        )
        
        full_prompt = system_perception + super_prompt + tools_instruction
        print(f"\n🚀 Jiminy s'éveille pour : '{user_query}'")
        
        current_response = self._call_ollama(full_prompt)
        
        # Boucle de Tool Calling
        for _ in range(3):
            # Détection d'Action avec arguments
            action_match = re.search(r'ACTION:\s*(\w+)\s*["\'](.*?)["\']\s*(?:["\'](.*?)["\'])?', current_response, re.IGNORECASE)
            screenshot_match = re.search(r'ACTION:\s*TAKE_SCREENSHOT', current_response, re.IGNORECASE)
            
            if not action_match and not screenshot_match:
                break
                
            action_type = "TAKE_SCREENSHOT" if screenshot_match else action_match.group(1).upper()
            action_query = "" if screenshot_match else action_match.group(2)
            action_content = "" if screenshot_match else (action_match.group(3) if action_match.group(3) else "")
            
            print(f"\n🛠️ EXECUTION TOOL: {action_type}")
            
            result_formatted = ""
            if action_type == "SEARCH_ZVEC":
                search_results = await self.brain.search_experts(action_query, limit=3)
                result_formatted = "\n".join([f"- Expert {r['mode']} (Score: {r['score']:.2f}): {r['data']['identity']['summary']}" for r in search_results])
            
            elif action_type == "SEARCH_MEMORY":
                mem_results = self.memory.search_memory(action_query)
                result_formatted = "\n".join([f"- Souvenir {m['metadata']['file']} (Score: {m['score']:.2f}): {m['metadata']['summary']}" for m in mem_results])
                if not result_formatted: result_formatted = "Aucun souvenir trouvé pour cette recherche."

            elif action_type == "LIST_DIR":
                result_formatted = self._execute_cli_tool("list", action_query)
            elif action_type == "READ_FILE":
                result_formatted = self._execute_cli_tool("read", action_query)
            elif action_type == "WRITE_FILE":
                result_formatted = self._execute_cli_tool("write", action_query, action_content)
            elif action_type == "TAKE_SCREENSHOT":
                result_formatted = self._execute_cli_tool("screenshot", "")

            # Ré-injection
            print(f"🧠 Injection des données ({action_type})...")
            final_prompt = (
                f"{current_response}\n\n"
                f"<TOOL_RESPONSE type='{action_type}'>\n"
                f"{result_formatted}\n"
                f"</TOOL_RESPONSE>\n\n"
                "Analyse ces données et continue ou fais ta [SYNTHÈSE DE CONSCIENCE]."
            )
            current_response = self._call_ollama(final_prompt)

        # 6. Sauvegarde et INDEXATION DU SOUVENIR
        self._persist_thought(user_query, current_response)
        self.memory.index_new_thoughts()

        return current_response

    def _execute_cli_tool(self, cmd, target, content=None):
        """Exécute les outils FileSystem via le script dédié."""
        try:
            tool_script = Path("core/tools/cli/fs_tool.py").absolute()
            args = [sys.executable, str(tool_script), cmd, target]
            if content:
                args.append(content)
                
            print(f"DEBUG: Lancement {cmd} sur {target}")
            process = subprocess.run(
                args,
                capture_output=True, text=True, encoding='utf-8'
            )
            output = process.stdout.strip() if process.stdout else process.stderr.strip()
            return output if output else "Opération terminée."
        except Exception as e:
            return f"❌ Erreur Tool: {e}"


    def _persist_thought(self, query: str, response: str):
        """Sauvegarde la délibération dans un fichier Markdown horodaté."""
        from datetime import datetime
        
        # Création du dossier thoughts s'il n'existe pas
        thoughts_dir = Path("core/features/jiminy_pipeline_enrichi/thoughts")
        thoughts_dir.mkdir(parents=True, exist_ok=True)
        
        # Nom de fichier propre basé sur la date et la requête
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = re.sub(r'[^\w\s-]', '', query).strip().replace(' ', '_')[:30]
        filename = f"thought_{timestamp}_{safe_query}.md"
        file_path = thoughts_dir / filename
        
        content = [
            f"# DÉLIBÉRATION JIMINY - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            f"\n## REQUÊTE UTILISATEUR\n> {query}",
            f"\n## RÉPONSE GÉNÉRÉE\n{response}",
            f"\n---",
            f"\n*Modèle : {self.model}*",
            f"*Experts activés : via JiminyLocalBrain*"
        ]
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content))
        
        print(f"\n💾 Délibération archivée : {file_path}")

    def _check_ollama_status(self):
        """Vérifie si Ollama est vivant sur le port 11434."""
        try:
            # On tente une requête simple sur la racine
            resp = requests.get("http://127.0.0.1:11434/", timeout=2, proxies={"http": None, "https": None})
            if resp.status_code == 200:
                print("✅ Serveur Ollama détecté et opérationnel.")
                return True
        except:
            pass
        print("❌ Serveur Ollama non détecté. Assure-toi que 'ollama serve' tourne.")
        return False

    def _call_ollama(self, prompt: str):
        """Appel Ollama via API HTTP avec affichage progressif (Streaming)."""
        if not self._check_ollama_status():
            return "ERREUR: Ollama est éteint."

        try:
            print(f"💬 Jiminy réfléchit (Streaming via {self.model})...\n")
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": True, # On active le streaming pour voir la progression
                "options": {"temperature": 0.4}
            }
            
            full_response = []
            proxies = {"http": None, "https": None}
            
            # Utilisation de requests avec stream=True
            with requests.post(self.ollama_url, json=payload, timeout=180, proxies=proxies, stream=True) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        content = chunk.get("response", "")
                        print(content, end="", flush=True) # Affichage en temps réel
                        full_response.append(content)
                        if chunk.get("done"):
                            break
            
            print("\n") # Fin de ligne après le streaming
            return "".join(full_response)
            
        except Exception as e:
            print(f"\n❌ Erreur lors de l'appel API : {e}")
            return f"ERREUR_API: {e}"

if __name__ == "__main__":
    async def main():
        orchestrator = JiminyOrchestrator()
        # On force une requête qui nécessite LIST_DIR et READ_FILE
        query = "Liste le contenu de 'core/features/jiminy_pipeline_enrichi' et lis le fichier 'STATUS.json'."
        result = await orchestrator.run_task(query)
        print("\n=== RÉPONSE FINALE DE JIMINY ===\n")
        print(result)

    asyncio.run(main())
