"""
Tagger Module - Attribution de tags multi-dimensionnels

Ce module implémente un système de tagging automatique qui attribue
des tags catégoriques, sémantiques et contextuels aux chunks.

Classes:
    - TagCategory: Catégories de tags (categorique, semantique, contextuel)
    - Tag: Représente un tag avec confiance
    - Tagger: Logique de tagging automatique
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
import sys
import re
from pathlib import Path

# Support exécution en script direct
try:
    from .chunker import Chunk
except ImportError:
    base_dir = Path(__file__).resolve().parent
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))
    from chunker import Chunk


class TagCategory(Enum):
    """
    Catégories de tags
    
    Chaque catégorie correspond à un type d'indexation différent:
    - CATEGORIQUE: Indexation par type/domaine (Qdrant)
    - SEMANTIQUE: Indexation par concept/action (Zvec)
    - CONTEXTUEL: Métadonnées contextuelles (Memory MCP)
    """
    CATEGORIQUE = "categorique"
    SEMANTIQUE = "semantique"
    CONTEXTUEL = "contextuel"


@dataclass
class Tag:
    """
    Représente un tag attribué à un chunk
    
    Attributes:
        category: Catégorie du tag
        key: Clé du tag (ex: "type", "concept")
        value: Valeur du tag (ex: "code", "authentification")
        confidence: Score de confiance (0.0 - 1.0)
        source: Source du tag (auto, manual, inherited)
    """
    category: TagCategory
    key: str
    value: str
    confidence: float = 1.0
    source: str = "auto"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le tag en dictionnaire
        
        Returns:
            Dictionnaire représentant le tag
        """
        return {
            "category": self.category.value,
            "key": self.key,
            "value": self.value,
            "confidence": self.confidence,
            "source": self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Tag':
        """
        Crée un tag depuis un dictionnaire
        
        Args:
            data: Dictionnaire source
            
        Returns:
            Instance de Tag
        """
        return cls(
            category=TagCategory(data.get("category", "categorique")),
            key=data.get("key", ""),
            value=data.get("value", ""),
            confidence=data.get("confidence", 1.0),
            source=data.get("source", "auto")
        )
    
    def __hash__(self) -> int:
        """Hash pour déduplication"""
        return hash((self.category, self.key, self.value))
    
    def __eq__(self, other) -> bool:
        """Égalité pour déduplication"""
        if not isinstance(other, Tag):
            return False
        return (
            self.category == other.category and
            self.key == other.key and
            self.value == other.value
        )


class Tagger:
    """
    Logique de tagging automatique
    
    Le Tagger analyse le contenu des chunks et leur attribue des tags
    dans les trois catégories: catégorique, sémantique et contextuel.
    
    Attributes:
        config: Configuration complète du pipeline RAG
        tagging_config: Configuration spécifique au tagging
    
    Example:
        >>> config = {"tagging": {"min_confidence": 0.7, ...}}
        >>> tagger = Tagger(config)
        >>> tags = tagger.tag_chunk(chunk)
    """
    
    # Patterns de détection du type de contenu
    TYPE_PATTERNS = {
        "code": [
            r"def\s+\w+\s*\(",
            r"class\s+\w+",
            r"function\s+\w+",
            r"const\s+\w+\s*=",
            r"let\s+\w+\s*=",
            r"var\s+\w+\s*=",
            r"import\s+",
            r"from\s+\w+\s+import",
            r"public\s+\w+",
            r"private\s+\w+",
        ],
        "doc": [
            r"^#\s+\w+",
            r"^///",
            r"^\*\*[\w\s]+\*\*",
            r"^@\w+",
            r"```",
        ],
        "config": [
            r"^\w+:\s*",
            r"^\s*-\s*\w+",
            r'^"[\w_]+"\s*:',
            r"^\s*\w+\s*=",
            r"\.env$",
            r"config\.json$",
        ],
        "data": [
            r"^\[",
            r"^\{",
            r"^\s*\d+\s*,",
            r'"id"\s*:',
        ],
        "log": [
            r"\d{4}-\d{2}-\d{2}",
            r"\[INFO\]",
            r"\[ERROR\]",
            r"\[WARN\]",
            r"\[DEBUG\]",
        ],
    }
    
    # Mots-clés par domaine
    DOMAIN_KEYWORDS = {
        "frontend": [
            "react", "vue", "angular", "svelte", "css", "html", "dom",
            "component", "jsx", "tsx", "style", "render", "state"
        ],
        "backend": [
            "api", "server", "endpoint", "route", "middleware", "request",
            "response", "controller", "service", "repository"
        ],
        "database": [
            "sql", "query", "table", "index", "migration", "orm",
            "schema", "join", "select", "insert", "update", "delete"
        ],
        "devops": [
            "docker", "kubernetes", "ci", "cd", "deploy", "pipeline",
            "container", "pod", "service", "ingress", "helm"
        ],
        "security": [
            "auth", "token", "jwt", "encrypt", "hash", "password",
            "permission", "role", "access", "secure", "ssl", "tls"
        ],
        "testing": [
            "test", "spec", "mock", "stub", "assert", "expect",
            "describe", "it", "before", "after", "fixture"
        ],
        "ai": [
            "model", "embedding", "vector", "llm", "prompt", "token",
            "generation", "inference", "training", "fine-tune"
        ],
    }
    
    # Concepts et leurs mots-clés associés
    CONCEPT_KEYWORDS = {
        "authentification": [
            "login", "password", "token", "jwt", "session", "auth",
            "credential", "signin", "login", "logout", "oauth"
        ],
        "cache": [
            "cache", "redis", "memoize", "ttl", "eviction", "lru",
            "store", "hit", "miss", "invalidate"
        ],
        "api": [
            "endpoint", "route", "request", "response", "rest", "graphql",
            "http", "get", "post", "put", "delete", "patch"
        ],
        "workflow": [
            "step", "transition", "state", "trigger", "automation",
            "pipeline", "flow", "process", "task"
        ],
        "validation": [
            "validate", "check", "verify", "ensure", "assert", "schema",
            "rule", "constraint", "valid", "invalid"
        ],
        "pagination": [
            "page", "limit", "offset", "cursor", "paginate", "next",
            "previous", "per_page"
        ],
        "logging": [
            "log", "logger", "debug", "info", "warn", "error", "trace",
            "level", "format", "output"
        ],
        "configuration": [
            "config", "setting", "env", "variable", "option", "parameter",
            "preference", "default"
        ],
    }
    
    # Verbes d'action
    ACTION_VERBS = {
        "create": ["create", "add", "insert", "new", "generate", "build", "make", "init"],
        "read": ["get", "fetch", "read", "find", "query", "retrieve", "load", "search"],
        "update": ["update", "modify", "edit", "change", "patch", "set", "save", "write"],
        "delete": ["delete", "remove", "destroy", "drop", "clear", "erase", "purge"],
        "validate": ["validate", "check", "verify", "ensure", "assert", "confirm", "test"],
        "process": ["process", "handle", "execute", "run", "perform", "compute", "calculate"],
        "transform": ["transform", "convert", "parse", "format", "encode", "decode", "map"],
        "connect": ["connect", "link", "associate", "bind", "attach", "join", "relate"],
    }
    
    # Entités communes
    ENTITY_PATTERNS = {
        "user": [r"user", r"users?", r"account", r"profile", r"person"],
        "project": [r"project", r"workspace", r"repo", r"repository"],
        "file": [r"file", r"document", r"resource", r"asset"],
        "task": [r"task", r"job", r"process", r"operation"],
        "agent": [r"agent", r"bot", r"assistant", r"ai", r"model"],
        "data": [r"data", r"record", r"entry", r"item", r"object"],
    }
    
    # Mots-clés moraux Asimov
    MORAL_KEYWORDS = {
        "asimov": ["asimov", "asimov's"],
        "loi": ["loi", "law", "règle", "rule"],
        "bien-être": ["bien-être", "bien etre", "welfare", "well-being", "wellbeing"],
        "nuire": ["nuire", "harm", "blesser", "injure", "damage"],
    }
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le tagger avec la configuration
        
        Args:
            config: Configuration complète du pipeline RAG
        """
        self.config = config
        self.tagging_config = config.get("tagging", {
            "auto_detect": True,
            "min_confidence": 0.7,
            "max_tags_per_chunk": 10
        })
    
    def tag_chunk(self, chunk: Chunk) -> List[Tag]:
        """
        Attribue tous les tags à un chunk
        
        Args:
            chunk: Chunk à tagger
            
        Returns:
            Liste de tags filtrés et limités
        """
        tags = []
        
        # 1. Tags catégoriques
        tags.extend(self._detect_categorique(chunk))
        
        # 2. Tags sémantiques
        tags.extend(self._detect_semantique(chunk))
        
        # 3. Tags contextuels
        tags.extend(self._detect_contextuel(chunk))
        
        # 4. Tags moraux Asimov
        tags = self.add_moral_tags(chunk, tags)
        
        # 5. Filtrer par confiance minimale
        min_confidence = self.tagging_config.get("min_confidence", 0.7)
        tags = [t for t in tags if t.confidence >= min_confidence]
        
        # 6. Dédupliquer
        tags = list(dict.fromkeys(tags))
        
        # 7. Limiter le nombre de tags
        max_tags = self.tagging_config.get("max_tags_per_chunk", 10)
        if len(tags) > max_tags:
            tags = sorted(tags, key=lambda t: t.confidence, reverse=True)[:max_tags]
        
        return tags
    
    def _detect_categorique(self, chunk: Chunk) -> List[Tag]:
        """
        Détecte les tags catégoriques
        
        Args:
            chunk: Chunk à analyser
            
        Returns:
            Liste de tags catégoriques
        """
        tags = []
        content_lower = chunk.content.lower()
        
        # Type de contenu
        for type_name, patterns in self.TYPE_PATTERNS.items():
            matches = 0
            for pattern in patterns:
                if re.search(pattern, chunk.content, re.MULTILINE | re.IGNORECASE):
                    matches += 1
            
            if matches > 0:
                confidence = min(matches / len(patterns) * 2, 1.0)
                tags.append(Tag(
                    category=TagCategory.CATEGORIQUE,
                    key="type",
                    value=type_name,
                    confidence=confidence
                ))
                break  # Un seul type
        
        # Domaine
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in content_lower)
            if matches > 0:
                confidence = min(matches / len(keywords) * 2, 1.0)
                tags.append(Tag(
                    category=TagCategory.CATEGORIQUE,
                    key="domain",
                    value=domain,
                    confidence=confidence
                ))
        
        # Scope (basé sur la taille)
        token_count = chunk.token_count()
        if token_count < 100:
            scope = "variable"
        elif token_count < 300:
            scope = "function"
        elif token_count < 700:
            scope = "module"
        else:
            scope = "project"
        
        tags.append(Tag(
            category=TagCategory.CATEGORIQUE,
            key="scope",
            value=scope,
            confidence=0.8
        ))
        
        # Priorité (basée sur les mots-clés)
        critical_keywords = ["critical", "important", "urgent", "security", "auth", "error", "fail"]
        high_keywords = ["warning", "deprecated", "todo", "fixme", "bug"]
        
        if any(kw in content_lower for kw in critical_keywords):
            tags.append(Tag(
                category=TagCategory.CATEGORIQUE,
                key="priority",
                value="critical",
                confidence=0.85
            ))
        elif any(kw in content_lower for kw in high_keywords):
            tags.append(Tag(
                category=TagCategory.CATEGORIQUE,
                key="priority",
                value="high",
                confidence=0.75
            ))
        
        return tags
    
    def _detect_semantique(self, chunk: Chunk) -> List[Tag]:
        """
        Détecte les tags sémantiques
        
        Args:
            chunk: Chunk à analyser
            
        Returns:
            Liste de tags sémantiques
        """
        tags = []
        content_lower = chunk.content.lower()
        
        # Concept
        for concept, keywords in self.CONCEPT_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in content_lower)
            if matches > 0:
                confidence = min(matches / len(keywords) * 1.5, 1.0)
                tags.append(Tag(
                    category=TagCategory.SEMANTIQUE,
                    key="concept",
                    value=concept,
                    confidence=confidence
                ))
        
        # Action
        for action, verbs in self.ACTION_VERBS.items():
            for verb in verbs:
                if re.search(rf'\b{verb}\b', content_lower):
                    tags.append(Tag(
                        category=TagCategory.SEMANTIQUE,
                        key="action",
                        value=action,
                        confidence=0.8
                    ))
                    break
        
        # Entité
        for entity, patterns in self.ENTITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    tags.append(Tag(
                        category=TagCategory.SEMANTIQUE,
                        key="entity",
                        value=entity,
                        confidence=0.75
                    ))
                    break
        
        return tags
    
    def _detect_contextuel(self, chunk: Chunk) -> List[Tag]:
        """
        Détecte les tags contextuels
        
        Args:
            chunk: Chunk à analyser
            
        Returns:
            Liste de tags contextuels
        """
        tags = []
        
        # Temporal (basé sur le type de document)
        doc_type = chunk.metadata.get("doc_type", "text")
        if doc_type == "code":
            temporal = "permanent"
        elif doc_type == "log":
            temporal = "session"
        elif doc_type == "config":
            temporal = "permanent"
        else:
            temporal = "daily"
        
        tags.append(Tag(
            category=TagCategory.CONTEXTUEL,
            key="temporal",
            value=temporal,
            confidence=0.9
        ))
        
        # Source
        tags.append(Tag(
            category=TagCategory.CONTEXTUEL,
            key="source",
            value="agent",
            confidence=1.0
        ))
        
        # Confidence globale (basée sur la qualité du chunk)
        if chunk.is_valid_size(self.config):
            confidence_level = "high"
        else:
            confidence_level = "medium"
        
        tags.append(Tag(
            category=TagCategory.CONTEXTUEL,
            key="confidence",
            value=confidence_level,
            confidence=1.0
        ))
        
        # Access (basé sur le contenu)
        content_lower = chunk.content.lower()
        if any(kw in content_lower for kw in ["private", "secret", "internal", "internal"]):
            access = "private"
        elif any(kw in content_lower for kw in ["public", "api", "export"]):
            access = "public"
        else:
            access = "internal"
        
        tags.append(Tag(
            category=TagCategory.CONTEXTUEL,
            key="access",
            value=access,
            confidence=0.8
        ))
        
        # Richesse contextuelle (Détection de l'en-tête explicatif)
        if "[[" in chunk.content and "CONTEXTE:" in chunk.content:
            tags.append(Tag(
                category=TagCategory.CONTEXTUEL,
                key="quality",
                value="context_rich",
                confidence=1.0
            ))
        
        return tags
    
    def get_tag_value(
        self,
        tags: List[Tag],
        category: TagCategory,
        key: str
    ) -> Optional[str]:
        """
        Récupère la valeur d'un tag spécifique
        
        Args:
            tags: Liste de tags
            category: Catégorie recherchée
            key: Clé recherchée
            
        Returns:
            Valeur du tag ou None
        """
        for tag in tags:
            if tag.category == category and tag.key == key:
                return tag.value
        return None
    
    def has_tag(
        self,
        tags: List[Tag],
        category: TagCategory,
        key: str,
        value: str = None
    ) -> bool:
        """
        Vérifie si un tag existe
        
        Args:
            tags: Liste de tags
            category: Catégorie recherchée
            key: Clé recherchée
            value: Valeur recherchée (optionnel)
            
        Returns:
            True si le tag existe
        """
        for tag in tags:
            if tag.category == category and tag.key == key:
                if value is None or tag.value == value:
                    return True
        return False
    
    def filter_tags_by_category(
        self,
        tags: List[Tag],
        category: TagCategory
    ) -> List[Tag]:
        """
        Filtre les tags par catégorie
        
        Args:
            tags: Liste de tags
            category: Catégorie à filtrer
            
        Returns:
            Tags de la catégorie spécifiée
        """
        return [t for t in tags if t.category == category]
    
    def tags_to_dict(self, tags: List[Tag]) -> Dict[str, Dict[str, str]]:
        """
        Convertit une liste de tags en dictionnaire structuré
        
        Args:
            tags: Liste de tags
            
        Returns:
            Dictionnaire {category: {key: value}}
        """
        result = {}
        
        for tag in tags:
            cat = tag.category.value
            if cat not in result:
                result[cat] = {}
            result[cat][tag.key] = tag.value
        
        return result
    
    def add_moral_tags(self, chunk: Chunk, tags: List[Tag]) -> List[Tag]:
        """
        Ajoute des tags moraux Asimov si le chunk contient des mots-clés éthiques
        
        Détecte les chunks liés aux lois d'Asimov et ajoute le tag 'moral:asimov'
        pour prioriser ces contenus dans le système RAG.
        
        Args:
            chunk: Chunk à analyser
            tags: Liste existante de tags
            
        Returns:
            Liste de tags avec tag moral ajouté si applicable
        """
        content_lower = chunk.content.lower()
        
        # Vérifier la présence de mots-clés moraux
        moral_detected = False
        for category, keywords in self.MORAL_KEYWORDS.items():
            if any(kw in content_lower for kw in keywords):
                moral_detected = True
                break
        
        
        if moral_detected:
            tags.append(Tag(
                category=TagCategory.CONTEXTUEL,
                key="moral",
                value="asimov",
                confidence=1.0,
                source="auto"
            ))
        
        return tags
