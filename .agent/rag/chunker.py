"""
Chunker Module - Découpage intelligent de documents

Ce module implémente un système de chunking intelligent qui découpe les documents
en unités sémantiques cohérentes avec préservation du contexte.

Classes:
    - ChunkType: Types de chunks (atomic, modular, contextual, structural)
    - Chunk: Représente un chunk de document
    - Chunker: Logique de découpage
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import re
import sys
from pathlib import Path

# Support exécution en script direct ou package
try:
    if __package__:
        from .utils.text_processing import count_tokens, clean_text
    else:
        # Résolution via le chemin du fichier pour exécution directe
        import sys
        from pathlib import Path
        current_dir = Path(__file__).resolve().parent
        if str(current_dir) not in sys.path:
            sys.path.insert(0, str(current_dir))
        from utils.text_processing import count_tokens, clean_text
except (ImportError, ValueError):
    # Fallback ultime via le dossier parent
    import sys
    from pathlib import Path
    rag_dir = Path(__file__).resolve().parent
    if str(rag_dir) not in sys.path:
        sys.path.insert(0, str(rag_dir))
    try:
        from utils.text_processing import count_tokens, clean_text
    except ImportError:
        # Si on est au-dessus
        if str(rag_dir.parent) not in sys.path:
            sys.path.insert(0, str(rag_dir.parent))
        from rag.utils.text_processing import count_tokens, clean_text


class ChunkType(Enum):
    """
    Types de chunks supportés
    
    Chaque type a une taille caractéristique adaptée à un usage spécifique.
    """
    ATOMIC = "atomic"          # 50-100 tokens: Entités isolées
    MODULAR = "modular"        # 200-500 tokens: Paragraphes cohérents
    CONTEXTUAL = "contextual"  # 500-1000 tokens: Sections complètes
    STRUCTURAL = "structural"  # Variable: Code/fichiers


@dataclass
class Chunk:
    """
    Représente un chunk de document
    
    Un chunk est une unité sémantique cohérente extraite d'un document,
    avec préservation du contexte et métadonnées.
    
    Attributes:
        id: Identifiant unique UUID v4
        content: Contenu textuel du chunk
        type: Type de chunk (atomic, modular, etc.)
        source_file: Fichier source optionnel
        line_start: Ligne de début dans le source
        line_end: Ligne de fin dans le source
        overlap_previous: Chevauchement avec chunk précédent
        overlap_next: Chevauchement avec chunk suivant
        metadata: Métadonnées additionnelles
        created_at: Timestamp de création
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    type: ChunkType = ChunkType.MODULAR
    source_file: Optional[str] = None
    line_start: int = 0
    line_end: int = 0
    overlap_previous: str = ""
    overlap_next: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le chunk en dictionnaire sérialisable
        
        Returns:
            Dictionnaire représentant le chunk
        """
        return {
            "id": self.id,
            "content": self.content,
            "type": self.type.value,
            "source_file": self.source_file,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "overlap_previous": self.overlap_previous,
            "overlap_next": self.overlap_next,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Chunk':
        """
        Crée un chunk depuis un dictionnaire
        
        Args:
            data: Dictionnaire source
            
        Returns:
            Instance de Chunk
        """
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            content=data.get("content", ""),
            type=ChunkType(data.get("type", "modular")),
            source_file=data.get("source_file"),
            line_start=data.get("line_start", 0),
            line_end=data.get("line_end", 0),
            overlap_previous=data.get("overlap_previous", ""),
            overlap_next=data.get("overlap_next", ""),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow()
        )
    
    def token_count(self) -> int:
        """
        Estime le nombre de tokens dans le chunk
        
        Utilise l'approximation: 1 token ≈ 4 caractères
        
        Returns:
            Nombre estimé de tokens
        """
        return count_tokens(self.content)
    
    def is_valid_size(self, config: Dict) -> bool:
        """
        Vérifie si le chunk respecte les limites de taille configurées
        
        Args:
            config: Configuration du chunking
            
        Returns:
            True si la taille est valide
        """
        type_config = config.get("chunking", {}).get("types", {}).get(self.type.value, {})
        if not type_config:
            return True
        
        token_count = self.token_count()
        return type_config.get("min", 0) <= token_count <= type_config.get("max", float('inf'))
    
    def get_context(self, include_overlap: bool = True) -> str:
        """
        Retourne le contexte complet du chunk
        
        Args:
            include_overlap: Inclure les chevauchements
            
        Returns:
            Contexte complet
        """
        context = ""
        if include_overlap and self.overlap_previous:
            context += f"[...{self.overlap_previous}] "
        context += self.content
        if include_overlap and self.overlap_next:
            context += f" [{self.overlap_next}...]"
        return context


class Chunker:
    """
    Logique de découpage intelligent de documents
    
    Le Chunker analyse la structure des documents et les découpe en
    unités sémantiques cohérentes avec préservation du contexte.
    
    Attributes:
        config: Configuration complète du pipeline RAG
        chunking_config: Configuration spécifique au chunking
    
    Example:
        >>> config = {"chunking": {"default_size": 300, ...}}
        >>> chunker = Chunker(config)
        >>> chunks = chunker.chunk_document("Long texte...", doc_type="text")
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le chunker avec la configuration
        
        Args:
            config: Configuration complète du pipeline RAG
        """
        self.config = config
        self.chunking_config = config.get("chunking", {
            "default_size": 300,
            "overlap_percent": 10,
            "min_chunk_size": 50,
            "max_chunk_size": 1000,
            "types": {
                "atomic": {"min": 50, "max": 100},
                "modular": {"min": 200, "max": 500},
                "contextual": {"min": 500, "max": 1000},
                "structural": {"min": 100, "max": 2000}
            }
        })
    
    def chunk_document(
        self,
        content: str,
        doc_type: str = "text",
        source_file: Optional[str] = None
    ) -> List[Chunk]:
        """
        Découpe un document en chunks intelligents
        
        Args:
            content: Contenu du document
            doc_type: Type de document (text, code, markdown, json)
            source_file: Chemin du fichier source optionnel
            
        Returns:
            Liste de chunks ordonnés
        """
        # Nettoyer le contenu
        content = clean_text(content)
        
        # Analyser la structure
        structure = self._analyze_structure(content, doc_type)
        
        # Identifier les unités sémantiques
        units = self._identify_semantic_units(content, structure, doc_type)
        
        # Créer les chunks avec contexte explicatif
        chunks = []
        for i, unit in enumerate(units):
            chunk_type = self._classify_chunk_type(unit, doc_type)
            
            # Générer l'en-tête explicatif (Mini-contexte)
            file_label = Path(source_file).name if source_file else "Mémoire vive"
            unit_type = unit.get("type", "bloc").upper()
            unit_name = unit.get("name", f"partie {i+1}")
            
            context_header = f"[[ CONTEXTE: {file_label} | UNITÉ: {unit_type} {unit_name} ]]\n"
            enriched_content = context_header + unit["content"]
            
            chunk = Chunk(
                content=enriched_content,
                type=chunk_type,
                source_file=source_file,
                line_start=unit.get("line_start", 0),
                line_end=unit.get("line_end", 0),
                metadata={
                    "doc_type": doc_type,
                    "unit_index": i,
                    "total_units": len(units),
                    "structure_type": unit.get("type", "unknown"),
                    "context_header": context_header.strip()
                }
            )
            
            chunks.append(chunk)
        
        # Ajouter le chevauchement
        chunks = self._add_overlap(chunks)
        
        return chunks
    
    def _analyze_structure(self, content: str, doc_type: str) -> Dict:
        """
        Analyse la structure du document selon son type
        
        Args:
            content: Contenu du document
            doc_type: Type de document
            
        Returns:
            Dictionnaire de structure
        """
        if doc_type == "code":
            return self._analyze_code_structure(content)
        elif doc_type == "markdown":
            return self._analyze_markdown_structure(content)
        elif doc_type == "json":
            return self._analyze_json_structure(content)
        else:
            return self._analyze_text_structure(content)
    
    def _analyze_text_structure(self, content: str) -> Dict:
        """Analyse la structure d'un texte brut"""
        lines = content.split("\n")
        paragraphs = []
        
        current_para = []
        para_start = 0
        
        for i, line in enumerate(lines):
            if line.strip():
                current_para.append(line)
            else:
                if current_para:
                    paragraphs.append({
                        "start": para_start,
                        "end": i - 1,
                        "content": "\n".join(current_para)
                    })
                    current_para = []
                para_start = i + 1
        
        if current_para:
            paragraphs.append({
                "start": para_start,
                "end": len(lines) - 1,
                "content": "\n".join(current_para)
            })
        
        return {
            "paragraphs": paragraphs,
            "total_lines": len(lines)
        }
    
    def _analyze_code_structure(self, content: str) -> Dict:
        """Analyse la structure d'un fichier de code"""
        lines = content.split("\n")
        structure = {
            "functions": [],
            "classes": [],
            "imports": [],
            "total_lines": len(lines)
        }
        
        # Pattern pour détecter les fonctions/classes Python
        func_pattern = r'^\s*def\s+(\w+)\s*\('
        class_pattern = r'^\s*class\s+(\w+)'
        import_pattern = r'^\s*(?:import|from)\s+'
        
        for i, line in enumerate(lines):
            # Détecter les fonctions
            func_match = re.match(func_pattern, line)
            if func_match:
                # Trouver la fin de la fonction (indentation)
                func_start = i
                func_indent = len(line) - len(line.lstrip())
                func_end = i
                
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() and not lines[j].startswith(' ' * (func_indent + 1)):
                        if not lines[j].startswith(' ' * func_indent):
                            break
                    func_end = j
                
                structure["functions"].append({
                    "name": func_match.group(1),
                    "start": func_start,
                    "end": func_end,
                    "content": "\n".join(lines[func_start:func_end + 1])
                })
            
            # Détecter les classes
            class_match = re.match(class_pattern, line)
            if class_match:
                class_start = i
                class_indent = len(line) - len(line.lstrip())
                class_end = i
                
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() and not lines[j].startswith(' ' * (class_indent + 1)):
                        if not lines[j].startswith(' ' * class_indent):
                            break
                    class_end = j
                
                structure["classes"].append({
                    "name": class_match.group(1),
                    "start": class_start,
                    "end": class_end,
                    "content": "\n".join(lines[class_start:class_end + 1])
                })
            
            # Détecter les imports
            if re.match(import_pattern, line):
                structure["imports"].append({
                    "line": i,
                    "content": line.strip()
                })
        
        return structure
    
    def _analyze_markdown_structure(self, content: str) -> Dict:
        """Analyse la structure d'un document Markdown"""
        lines = content.split("\n")
        structure = {
            "headings": [],
            "code_blocks": [],
            "paragraphs": [],
            "total_lines": len(lines)
        }
        
        in_code_block = False
        code_block_start = 0
        code_lang = ""
        
        current_section_start = 0
        current_heading_level = 0
        current_heading_text = ""
        
        for i, line in enumerate(lines):
            # Headings
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2)
                
                structure["headings"].append({
                    "level": level,
                    "text": text,
                    "line": i
                })
                
                current_heading_level = level
                current_heading_text = text
                current_section_start = i
            
            # Code blocks
            if line.startswith("```"):
                if not in_code_block:
                    in_code_block = True
                    code_block_start = i
                    code_lang = line[3:].strip()
                else:
                    structure["code_blocks"].append({
                        "language": code_lang,
                        "start": code_block_start,
                        "end": i,
                        "content": "\n".join(lines[code_block_start:i + 1])
                    })
                    in_code_block = False
        
        return structure
    
    def _analyze_json_structure(self, content: str) -> Dict:
        """Analyse la structure d'un document JSON"""
        try:
            import json
            data = json.loads(content)
            
            structure = {
                "valid": True,
                "type": type(data).__name__,
                "keys": list(data.keys()) if isinstance(data, dict) else [],
                "length": len(data) if isinstance(data, (list, dict)) else None
            }
        except json.JSONDecodeError:
            structure = {
                "valid": False,
                "error": "Invalid JSON"
            }
        
        return structure
    
    def _identify_semantic_units(
        self,
        content: str,
        structure: Dict,
        doc_type: str
    ) -> List[Dict]:
        """
        Identifie les unités sémantiques dans le contenu
        
        Args:
            content: Contenu du document
            structure: Structure analysée
            doc_type: Type de document
            
        Returns:
            Liste d'unités sémantiques
        """
        units = []
        
        if doc_type == "code":
            # Pour le code, utiliser les fonctions/classes comme unités
            for func in structure.get("functions", []):
                units.append({
                    "content": func["content"],
                    "type": "function",
                    "name": func.get("name", "inconnue"),
                    "line_start": func["start"],
                    "line_end": func["end"]
                })
            
            for cls in structure.get("classes", []):
                units.append({
                    "content": cls["content"],
                    "type": "class",
                    "name": cls.get("name", "inconnue"),
                    "line_start": cls["start"],
                    "line_end": cls["end"]
                })
            
            # Ajouter les imports ensemble
            if structure.get("imports"):
                import_content = "\n".join([imp["content"] for imp in structure["imports"]])
                units.insert(0, {
                    "content": import_content,
                    "type": "imports",
                    "line_start": structure["imports"][0]["line"],
                    "line_end": structure["imports"][-1]["line"]
                })
        
        elif doc_type == "markdown":
            # Pour Markdown, utiliser les sections entre headings
            lines = content.split("\n")
            
            # Trouver les sections
            heading_lines = [h["line"] for h in structure.get("headings", [])]
            
            if heading_lines:
                for i, h_line in enumerate(heading_lines):
                    start = h_line
                    end = heading_lines[i + 1] if i + 1 < len(heading_lines) else len(lines)
                    
                    section_content = "\n".join(lines[start:end])
                    if section_content.strip():
                        units.append({
                            "content": section_content,
                            "type": "section",
                            "line_start": start,
                            "line_end": end - 1
                        })
            else:
                # Pas de headings, traiter comme texte
                for para in structure.get("paragraphs", []):
                    units.append({
                        "content": para["content"],
                        "type": "paragraph",
                        "line_start": para["start"],
                        "line_end": para["end"]
                    })
        
        else:
            # Pour texte brut, utiliser les paragraphes
            for para in structure.get("paragraphs", []):
                units.append({
                    "content": para["content"],
                    "type": "paragraph",
                    "line_start": para["start"],
                    "line_end": para["end"]
                })
        
        # Si aucune unité trouvée, découper par taille
        if not units:
            units = self._split_by_size(content)
        
        return units
    
    def _split_by_size(self, content: str) -> List[Dict]:
        """
        Découpe le contenu par taille fixe
        
        Args:
            content: Contenu à découper
            
        Returns:
            Liste d'unités
        """
        default_size = self.chunking_config.get("default_size", 300)
        max_size = self.chunking_config.get("max_chunk_size", 1000)
        
        # Estimer la taille en caractères
        char_size = default_size * 4  # Approximation tokens -> chars
        
        units = []
        lines = content.split("\n")
        
        current_content = []
        current_start = 0
        current_chars = 0
        
        for i, line in enumerate(lines):
            line_chars = len(line) + 1  # +1 pour le newline
            
            if current_chars + line_chars > char_size and current_content:
                # Finaliser le chunk actuel
                units.append({
                    "content": "\n".join(current_content),
                    "type": "size_split",
                    "line_start": current_start,
                    "line_end": i - 1
                })
                
                current_content = []
                current_start = i
                current_chars = 0
            
            current_content.append(line)
            current_chars += line_chars
        
        # Dernier chunk
        if current_content:
            units.append({
                "content": "\n".join(current_content),
                "type": "size_split",
                "line_start": current_start,
                "line_end": len(lines) - 1
            })
        
        return units
    
    def _classify_chunk_type(self, unit: Dict, doc_type: str) -> ChunkType:
        """
        Classifie le type de chunk approprié
        
        Args:
            unit: Unité sémantique
            doc_type: Type de document
            
        Returns:
            Type de chunk
        """
        token_count = count_tokens(unit["content"])
        types_config = self.chunking_config.get("types", {})
        
        # Vérifier chaque type dans l'ordre
        for chunk_type in [ChunkType.ATOMIC, ChunkType.MODULAR, ChunkType.CONTEXTUAL, ChunkType.STRUCTURAL]:
            type_config = types_config.get(chunk_type.value, {})
            min_tokens = type_config.get("min", 0)
            max_tokens = type_config.get("max", float('inf'))
            
            if min_tokens <= token_count <= max_tokens:
                return chunk_type
        
        # Fallback basé sur la taille
        if token_count < 150:
            return ChunkType.ATOMIC
        elif token_count < 400:
            return ChunkType.MODULAR
        elif token_count < 800:
            return ChunkType.CONTEXTUAL
        else:
            return ChunkType.STRUCTURAL
    
    def _add_overlap(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Ajoute le chevauchement entre chunks consécutifs
        
        Args:
            chunks: Liste de chunks
            
        Returns:
            Chunks avec chevauchement ajouté
        """
        overlap_percent = self.chunking_config.get("overlap_percent", 10)
        
        for i in range(len(chunks)):
            if i > 0:
                # Chevauchement avec le précédent
                prev_content = chunks[i - 1].content
                overlap_chars = int(len(prev_content) * overlap_percent / 100)
                chunks[i].overlap_previous = prev_content[-overlap_chars:] if overlap_chars > 0 else ""
            
            if i < len(chunks) - 1:
                # Chevauchement avec le suivant
                next_content = chunks[i + 1].content
                overlap_chars = int(len(next_content) * overlap_percent / 100)
                chunks[i].overlap_next = next_content[:overlap_chars] if overlap_chars > 0 else ""
        
        return chunks
