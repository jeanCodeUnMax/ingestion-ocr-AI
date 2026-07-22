import json
from pathlib import Path
from datetime import datetime
import sentence_transformers
import torch

class EpisodicMemory:
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.cache_path = workspace_root / "core/features/jiminy_pipeline_enrichi/episodic_cache.json"
        self.thoughts_dir = workspace_root / "core/features/jiminy_pipeline_enrichi/thoughts"
        self.model = None
        self.vectors = []
        self.metadata = []

    def initialize(self):
        """Initialise le modèle d'embedding (identique au Brain pour la cohérence)."""
        if self.model is None:
            self.model = sentence_transformers.SentenceTransformer('all-MiniLM-L6-v2')
        self._load_cache()

    def _load_cache(self):
        if self.cache_path.exists():
            with open(self.cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.vectors = torch.tensor(data["vectors"])
                self.metadata = data["metadata"]

    def index_new_thoughts(self):
        """Scanne le dossier thoughts et indexe ce qui ne l'est pas encore."""
        indexed_files = {m["file"] for m in self.metadata}
        new_entries = []
        
        for md_file in self.thoughts_dir.glob("*.md"):
            if md_file.name not in indexed_files:
                print(f"🧠 Indexation du souvenir : {md_file.name}")
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                embedding = self.model.encode(content)
                new_entries.append({
                    "vector": embedding.tolist(),
                    "metadata": {
                        "file": md_file.name,
                        "timestamp": datetime.fromtimestamp(md_file.stat().st_mtime).isoformat(),
                        "summary": content[:200] + "..."
                    }
                })

        if new_entries:
            # Mise à jour des listes locales
            new_vectors = [e["vector"] for e in new_entries]
            new_meta = [e["metadata"] for e in new_entries]
            
            if self.vectors is not None and len(self.vectors) > 0:
                self.vectors = torch.cat([self.vectors, torch.tensor(new_vectors)])
                self.metadata.extend(new_meta)
            else:
                self.vectors = torch.tensor(new_vectors)
                self.metadata = new_meta
                
            # Sauvegarde du cache isolé
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump({"vectors": self.vectors.tolist(), "metadata": self.metadata}, f)
            return len(new_entries)
        return 0

    def search_memory(self, query: str, limit=2):
        """Recherche dans les souvenirs passés."""
        if self.vectors is None or len(self.vectors) == 0:
            return []
            
        query_vec = torch.tensor(self.model.encode(query))
        cos_sim = torch.nn.functional.cosine_similarity(query_vec, self.vectors)
        top_results = torch.topk(cos_sim, min(limit, len(cos_sim)))
        
        results = []
        for score, idx in zip(top_results.values, top_results.indices):
            results.append({
                "score": float(score),
                "metadata": self.metadata[int(idx)]
            })
        return results

if __name__ == "__main__":
    m = EpisodicMemory(Path("."))
    m.initialize()
    count = m.index_new_thoughts()
    print(f"✅ {count} nouveaux souvenirs indexés.")
    res = m.search_memory("erreur encodage")
    print(f"🔍 Résultat recherche : {res}")
