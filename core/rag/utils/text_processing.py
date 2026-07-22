"""
Text Processing Utilities

Fonctions utilitaires pour le traitement de texte.
"""

import re
from typing import List


def clean_text(text: str) -> str:
    """
    Nettoie le texte en supprimant les caractères indésirables
    
    Args:
        text: Texte à nettoyer
        
    Returns:
        Texte nettoyé
    """
    # Supprimer les caractères de contrôle
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    # Normaliser les espaces
    text = normalize_whitespace(text)
    return text.strip()


def extract_sentences(text: str) -> List[str]:
    """
    Extrait les phrases du texte
    
    Args:
        text: Texte à analyser
        
    Returns:
        Liste de phrases
    """
    # Pattern pour séparer les phrases
    pattern = r'(?<=[.!?])\s+(?=[A-Z])'
    sentences = re.split(pattern, text)
    return [s.strip() for s in sentences if s.strip()]


def count_tokens(text: str, method: str = "approx") -> int:
    """
    Compte le nombre de tokens dans le texte
    
    Args:
        text: Texte à analyser
        method: Méthode de comptage ("approx" ou "words")
        
    Returns:
        Nombre estimé de tokens
    """
    if method == "approx":
        # Approximation: 1 token ≈ 4 caractères
        return len(text) // 4
    elif method == "words":
        # Approximation: 1 token ≈ 0.75 mots
        words = len(text.split())
        return int(words / 0.75)
    return len(text) // 4


def normalize_whitespace(text: str) -> str:
    """
    Normalise les espaces dans le texte
    
    Args:
        text: Texte à normaliser
        
    Returns:
        Texte avec espaces normalisés
    """
    # Remplacer les séquences d'espaces par un seul espace
    text = re.sub(r'[ \t]+', ' ', text)
    # Remplacer les séquences de newlines par max 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def extract_code_blocks(text: str) -> List[dict]:
    """
    Extrait les blocs de code d'un texte Markdown
    
    Args:
        text: Texte Markdown
        
    Returns:
        Liste de blocs de code avec langue et contenu
    """
    pattern = r'```(\w*)\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    
    return [
        {"language": lang or "text", "content": content.strip()}
        for lang, content in matches
    ]


def extract_headings(text: str) -> List[dict]:
    """
    Extrait les titres d'un texte Markdown
    
    Args:
        text: Texte Markdown
        
    Returns:
        Liste de titres avec niveau et texte
    """
    pattern = r'^(#{1,6})\s+(.+)$'
    matches = re.findall(pattern, text, re.MULTILINE)
    
    return [
        {"level": len(hashes), "text": heading.strip()}
        for hashes, heading in matches
    ]


def truncate_text(text: str, max_tokens: int = 500) -> str:
    """
    Tronque le texte à un nombre maximum de tokens
    
    Args:
        text: Texte à tronquer
        max_tokens: Nombre maximum de tokens
        
    Returns:
        Texte tronqué
    """
    estimated_chars = max_tokens * 4
    if len(text) <= estimated_chars:
        return text
    
    # Tronquer à la fin d'une phrase
    truncated = text[:estimated_chars]
    last_sentence_end = max(
        truncated.rfind('.'),
        truncated.rfind('!'),
        truncated.rfind('?')
    )
    
    if last_sentence_end > estimated_chars * 0.7:
        return truncated[:last_sentence_end + 1]
    
    return truncated.strip() + "..."
