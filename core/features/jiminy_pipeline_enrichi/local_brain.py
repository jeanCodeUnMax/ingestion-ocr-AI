import os
import json
import asyncio
import sys
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional

# Setup path pour les composants RAG
RAG_PATH = Path(".agent/rag")
if str(RAG_PATH) not in sys.path:
    sys.path.insert(0, str(RAG_PATH))

try:
    from embedder import ZvecEmbedder
    from utils.env_loader import merge_config_with_env
except ImportError as e:
    print(f"❌ Erreur imports : {e}")
    sys.exit(1)

class JiminyLocalBrain:
    """
    Moteur de conscience local.
    Zéro dépendance réseau / MCP.
    """
    
    def __init__(self):
        # 1. Charger la config
        config_path = RAG_PATH / "config.json"
        with open(config_path, "r", encoding="utf-8") as f:
            full_config = json.load(f)
        zvec_config = merge_config_with_env(full_config).get("embedding", {}).get("zvec", {})
        
        # On force le modèle Python standard
        zvec_config["model"] = "sentence-transformers/all-MiniLM-L6-v2"
        
        self.embedder = ZvecEmbedder(zvec_config)
        self.experts_dir = Path("core/features/jiminy_pipeline_enrichi/prompts_base")
        self.cache_file = Path("core/features/jiminy_pipeline_enrichi/vector_cache.json")
        
        self.experts_data = {}
        self.expert_vectors = {} # mode -> vector

    async def initialize(self, force_refresh=False):
        """Initialise la RAM avec les vecteurs des experts."""
        print("🧠 Initialisation du Cerveau Local...")
        
        # Reset des listes pour éviter les doublons en cas de ré-initialisation
        self.experts_data = {}
        self.modes = []
        self.texts = []

        # Charger les JSON individuels depuis le dossier DB
        for json_file in self.experts_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Sécurité : On ne charge que si c'est une entité individuelle valide
                    if isinstance(data, dict) and "mode" in data and "essence" in data:
                        mode = data["mode"]
                        self.experts_data[mode] = data
                        
                        # On utilise le 'shrunk' et les 'tags' de l'essence pour l'embedding
                        essence = data.get("essence", {})
                        text_for_embedding = f"{mode} {essence.get('shrunk', '')} {' '.join(essence.get('tags', []))}"
                        self.modes.append(mode)
                        self.texts.append(text_for_embedding)
            except Exception as e:
                print(f"⚠️ Erreur chargement {json_file.name}: {e}")
        
        # Tenter de charger le cache
        if self.cache_file.exists() and not force_refresh:
            with open(self.cache_file, 'r', encoding='utf-8') as c:
                self.expert_vectors = json.load(c)
            print(f"✅ {len(self.expert_vectors)} vecteurs chargés depuis le cache.")
        else:
            print("⏳ Génération des embeddings (première fois uniquement)...")
            for mode, data in self.experts_data.items():
                text = f"{mode} {data.get('essence', {}).get('shrunk', '')} {' '.join(data.get('essence', {}).get('tags', []))}"
                vector = await self.embedder.embed(text)
                self.expert_vectors[mode] = vector
            
            # Sauvegarder le cache
            with open(self.cache_file, 'w', encoding='utf-8') as c:
                json.dump(self.expert_vectors, c)
            print("💾 Cache des vecteurs créé.")

    def _cosine_similarity(self, v1, v2):
        v1 = np.array(v1)
        v2 = np.array(v2)
        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

    async def search_experts(self, query: str, limit=5, threshold=0.25) -> List[Dict]:
        """Recherche sémantique pure RAM."""
        query_vector = await self.embedder.embed(query)
        
        scores = []
        for mode, vector in self.expert_vectors.items():
            sim = self._cosine_similarity(query_vector, vector)
            if sim >= threshold:
                scores.append({"mode": mode, "score": float(sim)})
        
        sorted_scores = sorted(scores, key=lambda x: x["score"], reverse=True)[:limit]
        
        results = []
        for s in sorted_scores:
            expert = self.experts_data[s["mode"]]
            results.append({
                "mode": s["mode"],
                "score": s["score"],
                "data": expert
            })
        
        return results

    async def _deduplicate_items(self, items: List[str], threshold=0.85) -> List[str]:
        """Supprime les doublons sémantiques dans une liste de chaînes."""
        if not items: return []
        
        # On vectorize tous les items
        vectors = []
        for item in items:
            vectors.append(await self.embedder.embed(item))
        
        unique_indices = []
        for i in range(len(items)):
            is_duplicate = False
            for j in unique_indices:
                sim = self._cosine_similarity(vectors[i], vectors[j])
                if sim > threshold:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_indices.append(i)
        
        return [items[i] for i in unique_indices]

    async def generate_composite_prompt(self, query: str) -> str:
        """Produit le super-prompt final avec délibération segmentée pour préserver l'essence des experts."""
        experts = await self.search_experts(query)
        
        if not experts:
            expert = self.experts_data.get("assistant")
            return expert["raw_prompt"] if expert else "Tu es Jiminy Cricket."

        print(f"🔥 Experts activés : {', '.join([f'{e['mode']} ({e['score']:.2f})' for e in experts])}")
        
        expert_blocks = []
        
        for e in experts:
            data = e["data"]
            mode = e["mode"].upper()
            raw = data["raw_prompt"]
            
            # Extraction des composants
            mission = raw.split("MISSION")[1].split("PRINCIPE")[0].strip() if "MISSION" in raw else ""
            principles = raw.split("PRINCIPE")[1].split("CONTEXTE")[0].strip() if "PRINCIPE" in raw else ""
            questions = raw.split("QUESTIONS")[1].split("RÉPONSE")[0].strip() if "QUESTIONS" in raw else ""
            
            # On crée un bloc d'expertise pur et isolé
            expert_blocks.append({
                "mode": mode,
                "mission": mission,
                "principles": principles,
                "questions": questions
            })

        # Construction du prompt avec protocole de délibération
        prompt = [
            "Tu es Jiminy Cricket, une conscience multi-dimensionnelle.",
            f"Ta mission actuelle nécessite la fusion de {len(experts)} experts internes.",
            "\n### PROTOCOLE DE RÉPONSE IMPÉRATIF ###",
            "1. Ne réponds pas de manière globale immédiatement.",
            "2. Tu dois effectuer une DÉLIBÉRATION INTERNE en faisant parler chaque expert successivement.",
            "3. Chaque expert doit utiliser sa propre terminologie, ses propres priorités et sa subtilité spécifique.",
            "4. Utilise le format : [IDENTITÉ : NOM_EXPERT] suivi de son analyse.",
            "5. Termine par une [SYNTHÈSE DE CONSCIENCE] qui arbitre les points de vue.\n",
            "### LES EXPERTS ACTIVÉS ###"
        ]

        for b in expert_blocks:
            prompt.append(f"\n--- EXPERT : {b['mode']} ---")
            prompt.append(f"MISSION : {b['mission']}")
            prompt.append(f"PRINCIPES :\n{b['principles']}")
            prompt.append(f"QUESTIONS À SE POSER :\n{b['questions']}")

        prompt.append(f"\n### TÂCHE À TRAITER ###\n{query}")
        
        return "\n".join(prompt)

if __name__ == "__main__":
    async def test():
        brain = JiminyLocalBrain()
        await brain.initialize()
        prompt = await brain.generate_composite_prompt("J'ai un bug de performance sur ma base de données")
        print("\n=== SUPER PROMPT ===\n")
        print(prompt[:1000] + "...")
        
    asyncio.run(test())
