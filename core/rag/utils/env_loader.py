"""
Configuration Environment Loader

Charge les variables d'environnement depuis le fichier .env
et les fusionne avec la configuration JSON.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import json


def load_env(env_path: Optional[str] = None) -> Dict[str, str]:
    """
    Charge les variables d'environnement depuis un fichier .env
    
    Args:
        env_path: Chemin du fichier .env (optionnel)
        
    Returns:
        Dictionnaire des variables chargées
    """
    if env_path is None:
        # Chercher .env à la racine du workspace (4 niveaux au-dessus)
        # .agent/rag/utils -> .agent/rag -> .agent -> workspace_root
        env_path = Path(__file__).parent.parent.parent.parent / ".env"
    else:
        env_path = Path(env_path)
    
    env_vars = {}
    
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                
                # Ignorer les commentaires et lignes vides
                if not line or line.startswith("#"):
                    continue
                
                # Parser la ligne KEY=VALUE
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Enlever les guillemets si présents
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    env_vars[key] = value
                    
                    # Aussi définir dans os.environ
                    os.environ[key] = value
    
    return env_vars


def get_env(key: str, default: Any = None) -> Any:
    """
    Récupère une variable d'environnement
    
    Args:
        key: Nom de la variable
        default: Valeur par défaut
        
    Returns:
        Valeur de la variable ou défaut
    """
    return os.environ.get(key, default)


def get_env_int(key: str, default: int = 0) -> int:
    """
    Récupère une variable d'environnement comme entier
    
    Args:
        key: Nom de la variable
        default: Valeur par défaut
        
    Returns:
        Valeur entière
    """
    value = os.environ.get(key)
    if value is not None:
        try:
            return int(value)
        except ValueError:
            pass
    return default


def get_env_float(key: str, default: float = 0.0) -> float:
    """
    Récupère une variable d'environnement comme float
    
    Args:
        key: Nom de la variable
        default: Valeur par défaut
        
    Returns:
        Valeur float
    """
    value = os.environ.get(key)
    if value is not None:
        try:
            return float(value)
        except ValueError:
            pass
    return default


def get_env_bool(key: str, default: bool = False) -> bool:
    """
    Récupère une variable d'environnement comme booléen
    
    Args:
        key: Nom de la variable
        default: Valeur par défaut
        
    Returns:
        Valeur booléenne
    """
    value = os.environ.get(key)
    if value is not None:
        return value.lower() in ("true", "1", "yes", "on")
    return default


def merge_config_with_env(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fusionne la configuration JSON avec les variables d'environnement
    
    Les variables d'environnement ont priorité sur le JSON.
    
    Args:
        config: Configuration de base
        
    Returns:
        Configuration fusionnée
    """
    # Charger les variables d'environnement
    load_env()
    
    # Chunking
    config.setdefault("chunking", {})["default_size"] = get_env_int("RAG_CHUNK_DEFAULT_SIZE", 300)
    config.setdefault("chunking", {})["overlap_percent"] = get_env_int("RAG_CHUNK_OVERLAP_PERCENT", 10)
    config.setdefault("chunking", {})["min_chunk_size"] = get_env_int("RAG_CHUNK_MIN_SIZE", 50)
    config.setdefault("chunking", {})["max_chunk_size"] = get_env_int("RAG_CHUNK_MAX_SIZE", 1000)
    
    # Chunking types
    config.setdefault("chunking", {}).setdefault("types", {})["atomic"] = {
        "min": get_env_int("RAG_CHUNK_TYPE_ATOMIC_MIN", 50),
        "max": get_env_int("RAG_CHUNK_TYPE_ATOMIC_MAX", 100)
    }
    config.setdefault("chunking", {}).setdefault("types", {})["modular"] = {
        "min": get_env_int("RAG_CHUNK_TYPE_MODULAR_MIN", 200),
        "max": get_env_int("RAG_CHUNK_TYPE_MODULAR_MAX", 500)
    }
    config.setdefault("chunking", {}).setdefault("types", {})["contextual"] = {
        "min": get_env_int("RAG_CHUNK_TYPE_CONTEXTUAL_MIN", 500),
        "max": get_env_int("RAG_CHUNK_TYPE_CONTEXTUAL_MAX", 1000)
    }
    config.setdefault("chunking", {}).setdefault("types", {})["structural"] = {
        "min": get_env_int("RAG_CHUNK_TYPE_STRUCTURAL_MIN", 100),
        "max": get_env_int("RAG_CHUNK_TYPE_STRUCTURAL_MAX", 2000)
    }
    
    # Tagging
    config.setdefault("tagging", {})["auto_detect"] = get_env_bool("RAG_TAG_AUTO_DETECT", True)
    config.setdefault("tagging", {})["min_confidence"] = get_env_float("RAG_TAG_MIN_CONFIDENCE", 0.7)
    config.setdefault("tagging", {})["max_tags_per_chunk"] = get_env_int("RAG_TAG_MAX_PER_CHUNK", 10)
    
    # Embedding - Qdrant
    config.setdefault("embedding", {}).setdefault("qdrant", {})["enabled"] = get_env_bool("RAG_QDRANT_ENABLED", True)
    config.setdefault("embedding", {}).setdefault("qdrant", {})["url"] = get_env("RAG_QDRANT_URL", "http://127.0.0.1:6333")
    config.setdefault("embedding", {}).setdefault("qdrant", {})["provider"] = get_env("RAG_QDRANT_PROVIDER", "mistral")
    config.setdefault("embedding", {}).setdefault("qdrant", {})["model"] = get_env("RAG_QDRANT_MODEL", "codestral-embed-2505")
    config.setdefault("embedding", {}).setdefault("qdrant", {})["dimensions"] = get_env_int("RAG_QDRANT_DIMENSIONS", 1536)

    # Embedding - Zvec
    config.setdefault("embedding", {}).setdefault("zvec", {})["enabled"] = get_env_bool("RAG_ZVEC_ENABLED", True)
    config.setdefault("embedding", {}).setdefault("zvec", {})["url"] = get_env("RAG_ZVEC_URL", "http://127.0.0.1:8001")
    config.setdefault("embedding", {}).setdefault("zvec", {})["provider"] = get_env("RAG_ZVEC_PROVIDER", "local")
    config.setdefault("embedding", {}).setdefault("zvec", {})["model"] = get_env("RAG_ZVEC_MODEL", "Xenova/all-MiniLM-L6-v2")
    config.setdefault("embedding", {}).setdefault("zvec", {})["dimensions"] = get_env_int("RAG_ZVEC_DIMENSIONS", 384)
    # Legacy support for old variable name
    if "RAG_EMBEDDING_MODEL" in os.environ:
        config.setdefault("embedding", {}).setdefault("zvec", {})["model"] = get_env("RAG_EMBEDDING_MODEL")
    
    # Collections Qdrant (avec défauts)
    qdrant_collections = {
        "code": get_env("RAG_QDRANT_COLLECTION_CODE", "code_index"),
        "doc": get_env("RAG_QDRANT_COLLECTION_DOC", "doc_index"),
        "config": get_env("RAG_QDRANT_COLLECTION_CONFIG", "config_index"),
        "workflow": get_env("RAG_QDRANT_COLLECTION_WORKFLOW", "workflow_index"),
        "skill": get_env("RAG_QDRANT_COLLECTION_SKILL", "skill_index"),
    }
    config.setdefault("embedding", {}).setdefault("qdrant", {})["collections"] = qdrant_collections
    
    # Collections Zvec (avec défauts)
    zvec_collections = {
        "concepts": get_env("RAG_ZVEC_COLLECTION_CONCEPTS", "concepts_index"),
        "entities": get_env("RAG_ZVEC_COLLECTION_ENTITIES", "entities_index"),
        "actions": get_env("RAG_ZVEC_COLLECTION_ACTIONS", "actions_index"),
        "relations": get_env("RAG_ZVEC_COLLECTION_RELATIONS", "relations_index"),
        "context": get_env("RAG_ZVEC_COLLECTION_CONTEXT", "context_index"),
    }
    config.setdefault("embedding", {}).setdefault("zvec", {})["collections"] = zvec_collections
    
    # Routing
    config.setdefault("routing", {})["strategy"] = get_env("RAG_ROUTING_STRATEGY", "dual")
    config.setdefault("routing", {})["fallback"] = get_env("RAG_ROUTING_FALLBACK", "both")
    config.setdefault("routing", {})["min_score"] = get_env_float("RAG_ROUTING_MIN_SCORE", 0.5)
    
    # Fusion
    config.setdefault("fusion", {})["weights"] = {
        "qdrant": get_env_float("RAG_FUSION_WEIGHT_QDRANT", 0.4),
        "zvec": get_env_float("RAG_FUSION_WEIGHT_ZVEC", 0.4),
        "memory": get_env_float("RAG_FUSION_WEIGHT_MEMORY", 0.2)
    }
    config.setdefault("fusion", {})["min_results"] = get_env_int("RAG_FUSION_MIN_RESULTS", 5)
    config.setdefault("fusion", {})["max_results"] = get_env_int("RAG_FUSION_MAX_RESULTS", 20)
    
    # Memory MCP
    config.setdefault("memory_mcp", {})["url"] = get_env("RAG_MEMORY_URL", "http://localhost:8002")
    config.setdefault("memory_mcp", {})["entity_type"] = get_env("RAG_MEMORY_ENTITY_TYPE", "chunk")
    
    return config


def get_workspace_root() -> Path:
    """
    Récupère le chemin racine du workspace
    
    Returns:
        Chemin du workspace
    """
    # 1. Variable d'environnement explicite
    if "RAG_WORKSPACE_ROOT" in os.environ and os.environ["RAG_WORKSPACE_ROOT"]:
        return Path(os.environ["RAG_WORKSPACE_ROOT"])
    
    # 2. Détecter automatiquement depuis le module
    # .agent/rag/utils -> .agent/rag -> .agent -> workspace_root
    utils_dir = Path(__file__).parent
    return utils_dir.parent.parent.parent.parent  # Hephaistos-Kit (le vrai workspace)


# Charger automatiquement au démarrage
load_env()
