"""
Utilities pour le module RAG

Modules:
    - text_processing: Fonctions de traitement de texte
    - tag_helpers: Helpers pour les tags
    - scoring: Fonctions de scoring
    - env_loader: Chargement des variables d'environnement
"""

from .text_processing import (
    clean_text,
    extract_sentences,
    count_tokens,
    normalize_whitespace,
)
from .tag_helpers import (
    merge_tags,
    filter_tags_by_confidence,
    deduplicate_tags,
)
from .scoring import (
    calculate_hybrid_score,
    normalize_score,
    rank_results,
)
from .env_loader import (
    load_env,
    get_env,
    get_env_int,
    get_env_float,
    get_env_bool,
    merge_config_with_env,
    get_workspace_root,
)

__all__ = [
    "clean_text",
    "extract_sentences",
    "count_tokens",
    "normalize_whitespace",
    "merge_tags",
    "filter_tags_by_confidence",
    "deduplicate_tags",
    "calculate_hybrid_score",
    "normalize_score",
    "rank_results",
    "load_env",
    "get_env",
    "get_env_int",
    "get_env_float",
    "get_env_bool",
    "merge_config_with_env",
    "get_workspace_root",
]
