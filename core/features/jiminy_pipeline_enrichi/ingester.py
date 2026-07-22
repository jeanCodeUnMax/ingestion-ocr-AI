import os
import json
import re
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import sentence_transformers

# Configuration du Schéma Neuronal Avancé (Source de Vérité)
MASTER_SCHEMA = {
    "neuronal_config": {
        "activation": "sigmoid",
        "weights": { "semantic": 0.4, "recency": 0.4, "popularity": 0.2 },
        "bias": -0.1
    },
    "anti_fragile": {
        "version": "V3.2_CLOISONNE",
        "rollback_enabled": True
    }
}

PROMPTS_DIR = Path("core/conscience/prompts")
OUTPUT_DB_DIR = Path("core/features/jiminy_pipeline_enrichi/prompts_base")
STATUS_FILE = Path("core/features/jiminy_pipeline_enrichi/STATUS.json")

class HighPrecisionIngester:
    def __init__(self):
        self.output_data = []
        print("🧠 Chargement du modèle d'embedding (MiniLM-L6)...")
        self.model = sentence_transformers.SentenceTransformer('all-MiniLM-L6-v2')

    def forge_essence(self, mode: str, raw_content: str) -> Dict[str, Any]:
        """
        Forge sémantique de haute précision (Restauration de la Conscience Cloisonnée).
        Récupère la mission, les principes et les questions pour créer une bulle d'expertise.
        """
        # Extraction chirurgicale
        mission = re.search(r"MISSION\n(.*?)(?:\n\n|\nPRINCIPE|$)", raw_content, re.DOTALL)
        principes = re.search(r"PRINCIPE\n(.*?)(?:\n\n|\nQUESTIONS|$)", raw_content, re.DOTALL)
        questions = re.search(r"QUESTIONS.*?\n(.*?)(?:\n\n|\nRÉPONSE|$)", raw_content, re.DOTALL)

        m = mission.group(1).strip() if mission else f"Expertise {mode}"
        p = principes.group(1).strip().split('\n') if principes else []
        q = questions.group(1).strip().split('\n') if questions else []

        # Nettoyage des préfixes inutiles
        p = [line.strip('- ').strip() for line in p if line.strip()]
        q = [line.strip('123456789. ').strip() for line in q if line.strip() and not line.isupper()]

        return {
            "shrunk": f"Bulle d'expertise {mode.upper()} : {m[:100]}...",
            "tags": [f"mode_{mode}", "cloisement_cognitif", "deliberation_imperative", "hephaistos_v3"],
            "summary": f"L'expert {mode} assure la mission : {m}. Il impose un protocole de réponse segmenté [IDENTITÉ : {mode.upper()}].",
            "protocol": {
                "identity_marker": f"[IDENTITÉ : {mode.upper()}]",
                "mission_statement": m,
                "core_principles": p[:6],
                "critical_questions": q[:6]
            }
        }

    async def process_expert(self, file_path: Path):
        mode = file_path.stem.replace("mode_", "")
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()

        essence = self.forge_essence(mode, raw_content)
        
        # Calcul de l'embedding sur le texte enrichi (mode + shrunk + tags)
        text_for_embedding = f"{mode} {essence['shrunk']} {' '.join(essence['tags'])}"
        embedding = self.model.encode(text_for_embedding).tolist()
        
        entry = {
            "mode": mode,
            "neuronal_config": MASTER_SCHEMA["neuronal_config"],
            "essence": essence,
            "anti_fragile": {
                "version": "V3.2_CLOISONNE",
                "timestamp": datetime.now().isoformat(),
                "rollback_id": f"RB_{mode}_GOLDEN_SHAPE"
            },
            "raw_prompt": raw_content,
            "embedding": embedding
        }
        
        # Sauvegarde individuelle
        target_path = OUTPUT_DB_DIR / f"{mode}.json"
        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump(entry, f, indent=2, ensure_ascii=False)
        
        return entry

    async def run_ingestion(self):
        print(f"🚀 Lancement de la Forge Sémantique sur {PROMPTS_DIR}")
        OUTPUT_DB_DIR.mkdir(parents=True, exist_ok=True)
        
        prompt_files = list(PROMPTS_DIR.glob("mode_*.txt"))
        for i, file_path in enumerate(prompt_files, 1):
            print(f"🛠️ [{i}/{len(prompt_files)}] Forging & Embedding {file_path.name}...")
            entry = await self.process_expert(file_path)
            self.output_data.append(entry)

        # Index global pour ZVEC
        with open(OUTPUT_DB_DIR / "all_experts_neuronal.json", 'w', encoding='utf-8') as f:
            json.dump(self.output_data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Forge & Réindexation terminée. {len(self.output_data)} entités vectorisées dans ZVEC.")

if __name__ == "__main__":
    ingester = HighPrecisionIngester()
    asyncio.run(ingester.run_ingestion())

if __name__ == "__main__":
    ingester = HighPrecisionIngester()
    asyncio.run(ingester.run_ingestion())
