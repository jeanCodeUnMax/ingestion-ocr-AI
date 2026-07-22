"""
Tag Helpers Utilities

Fonctions utilitaires pour la gestion des tags.
"""

from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class TagInfo:
    """Information sur un tag"""
    category: str
    key: str
    value: str
    confidence: float


def merge_tags(tags_list: List[List[Dict]]) -> List[Dict]:
    """
    Fusionne plusieurs listes de tags
    
    Args:
        tags_list: Listes de tags à fusionner
        
    Returns:
        Liste fusionnée et dédupliquée
    """
    merged = {}
    
    for tags in tags_list:
        for tag in tags:
            key = f"{tag['category']}:{tag['key']}:{tag['value']}"
            if key not in merged or tag['confidence'] > merged[key]['confidence']:
                merged[key] = tag
    
    return list(merged.values())


def filter_tags_by_confidence(
    tags: List[Dict],
    min_confidence: float = 0.7
) -> List[Dict]:
    """
    Filtre les tags par confiance minimale
    
    Args:
        tags: Liste de tags
        min_confidence: Confiance minimale
        
    Returns:
        Tags filtrés
    """
    return [t for t in tags if t.get('confidence', 0) >= min_confidence]


def deduplicate_tags(tags: List[Dict]) -> List[Dict]:
    """
    Déduplique les tags en gardant le plus haute confiance
    
    Args:
        tags: Liste de tags potentiellement dupliqués
        
    Returns:
        Tags uniques
    """
    unique = {}
    
    for tag in tags:
        key = f"{tag['category']}:{tag['key']}:{tag['value']}"
        if key not in unique or tag['confidence'] > unique[key]['confidence']:
            unique[key] = tag
    
    return list(unique.values())


def tags_to_dict(tags: List[Any]) -> Dict[str, Dict[str, str]]:
    """
    Convertit une liste de tags en dictionnaire structuré
    
    Args:
        tags: Liste de tags
        
    Returns:
        Dictionnaire {category: {key: value}}
    """
    result = {}
    
    for tag in tags:
        if hasattr(tag, 'category'):
            category = tag.category.value if hasattr(tag.category, 'value') else tag.category
            key = tag.key
            value = tag.value
        else:
            category = tag.get('category', '')
            key = tag.get('key', '')
            value = tag.get('value', '')
        
        if category not in result:
            result[category] = {}
        result[category][key] = value
    
    return result


def get_tag_value(tags: List[Dict], category: str, key: str) -> str:
    """
    Récupère la valeur d'un tag spécifique
    
    Args:
        tags: Liste de tags
        category: Catégorie recherchée
        key: Clé recherchée
        
    Returns:
        Valeur du tag ou chaîne vide
    """
    for tag in tags:
        if hasattr(tag, 'category'):
            tag_category = tag.category.value if hasattr(tag.category, 'value') else tag.category
            if tag_category == category and tag.key == key:
                return tag.value
        else:
            if tag.get('category') == category and tag.get('key') == key:
                return tag.get('value', '')
    return ""


def has_tag(tags: List[Dict], category: str, key: str, value: str = None) -> bool:
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
        if hasattr(tag, 'category'):
            tag_category = tag.category.value if hasattr(tag.category, 'value') else tag.category
            if tag_category == category and tag.key == key:
                if value is None or tag.value == value:
                    return True
        else:
            if tag.get('category') == category and tag.get('key') == key:
                if value is None or tag.get('value') == value:
                    return True
    return False
