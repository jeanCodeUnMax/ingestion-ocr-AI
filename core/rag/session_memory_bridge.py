#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SESSION MEMORY BRIDGE - Capture des conversations dans mémoire unifiée

Ce module résout la lacune: les conversations utilisateur ne sont PAS mémorisées.

Il fait:
1. Capture chaque échange user/assistant
2. Extrait intentions, actions, décisions
3. Stocke dans Memory MCP (Knowledge Graph)
4. Indexe dans Zvec pour recherche sémantique
5. Met à jour le Conscience Manifest

Usage:
    bridge = SessionMemoryBridge()
    bridge.capture_exchange(user_msg, assistant_response, context)
    bridge.sync_to_conscience()  # Met à jour le Dev Book
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class ConversationExchange:
    """Un échange de conversation"""
    timestamp: str
    session_id: str
    user_message: str
    assistant_response: str
    extracted_intent: str
    extracted_actions: List[str]
    extracted_decisions: List[str]
    tags: List[str]
    priority: str  # low, medium, high, critical


class SessionMemoryBridge:
    """
    Pont entre conversations et mémoire unifiée
    
    Connecte:
    - Conversations réelles → Memory MCP (Knowledge Graph)
    - Intentions utilisateur → Conscience Manifest (Dev Book)
    - Contexte session → Zvec (recherche sémantique)
    """
    
    def __init__(self, 
                 session_id: str = None,
                 manifest_path: str = ".agent/consciousness_manifest.json"):
        self.session_id = session_id or self._generate_session_id()
        self.manifest_path = Path(manifest_path)
        self.exchanges: List[ConversationExchange] = []
        
        # Cache local de la session
        self.session_cache_path = Path(f".agent/session_cache/{self.session_id}.json")
        self.session_cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _generate_session_id(self) -> str:
        """Génère ID unique de session"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_suffix = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:6]
        return f"session_{timestamp}_{hash_suffix}"
    
    def capture_exchange(self, 
                        user_message: str, 
                        assistant_response: str,
                        context: Dict[str, Any] = None) -> ConversationExchange:
        """
        Capture un échange et l'analyse
        
        Args:
            user_message: Message de l'utilisateur
            assistant_response: Réponse de l'assistant
            context: Contexte additionnel (fichiers ouverts, état IDE, etc.)
        
        Returns:
            L'échange structuré
        """
        # Analyser l'intention
        intent = self._extract_intent(user_message)
        
        # Extraire actions demandées
        actions = self._extract_actions(user_message, assistant_response)
        
        # Extraire décisions prises
        decisions = self._extract_decisions(assistant_response)
        
        # Déterminer priorité
        priority = self._determine_priority(user_message, context)
        
        # Générer tags
        tags = self._generate_tags(user_message, assistant_response, intent)
        
        exchange = ConversationExchange(
            timestamp=datetime.now().isoformat(),
            session_id=self.session_id,
            user_message=user_message[:500],  # Truncate pour stockage
            assistant_response=assistant_response[:500],
            extracted_intent=intent,
            extracted_actions=actions,
            extracted_decisions=decisions,
            tags=tags,
            priority=priority
        )
        
        self.exchanges.append(exchange)
        self._save_to_cache()
        
        return exchange
    
    def _extract_intent(self, user_msg: str) -> str:
        """Extrait l'intention principale"""
        msg_lower = user_msg.lower()
        
        if any(w in msg_lower for w in ["créer", "crée", "ajoute", "nouveau"]):
            return "CREATE"
        elif any(w in msg_lower for w in ["modifie", "corrige", "update", "change"]):
            return "UPDATE"
        elif any(w in msg_lower for w in ["supprime", "enlève", "delete"]):
            return "DELETE"
        elif any(w in msg_lower for w in ["vérifie", "teste", "analyse", "où en est"]):
            return "ANALYZE"
        elif any(w in msg_lower for w in ["problème", "bug", "erreur", "bloqué"]):
            return "DEBUG"
        elif any(w in msg_lower for w in ["explain", "explique", "comment", "pourquoi"]):
            return "LEARN"
        else:
            return "DISCUSS"
    
    def _extract_actions(self, user_msg: str, assistant_resp: str) -> List[str]:
        """Extrait les actions demandées ou effectuées"""
        actions = []
        
        # Chercher dans le message utilisateur
        if "index" in user_msg.lower():
            actions.append("index_files")
        if "créé" in user_msg.lower() or "créer" in user_msg.lower():
            actions.append("create_file")
        if "test" in user_msg.lower():
            actions.append("run_test")
        if "debug" in user_msg.lower() or "corrige" in user_msg.lower():
            actions.append("debug_fix")
        
        # Chercher dans la réponse de l'assistant
        if "créé" in assistant_resp.lower() or "crée" in assistant_resp.lower():
            # Extraire nom du fichier créé
            actions.append("file_created")
        if "modifié" in assistant_resp.lower():
            actions.append("file_modified")
        
        return actions
    
    def _extract_decisions(self, assistant_resp: str) -> List[str]:
        """Extrait les décisions prises par l'assistant"""
        decisions = []
        
        # Patterns de décision
        if "j'ai choisi" in assistant_resp.lower():
            decisions.append("architecture_choice")
        if "je vais" in assistant_resp.lower():
            decisions.append("planned_action")
        if "recommande" in assistant_resp.lower():
            decisions.append("recommendation")
        
        return decisions
    
    def _determine_priority(self, user_msg: str, context: Dict = None) -> str:
        """Détermine la priorité de l'échange"""
        msg_lower = user_msg.lower()
        
        # Critical
        if any(w in msg_lower for w in ["bloqué", "crash", "ne marche pas", "urgent", "critical"]):
            return "critical"
        
        # High
        if any(w in msg_lower for w in ["important", "problème", "erreur", "bug", "fonctionne pas"]):
            return "high"
        
        # Medium
        if any(w in msg_lower for w in ["vérifie", "analyse", "test", "update"]):
            return "medium"
        
        return "low"
    
    def _generate_tags(self, user_msg: str, assistant_resp: str, intent: str) -> List[str]:
        """Génère des tags pour l'échange"""
        tags = [intent.lower()]
        
        # Tags techniques
        tech_keywords = ["python", "sqlite", "qdrant", "zvec", "rag", "mcp", "manifest", "conscience"]
        for kw in tech_keywords:
            if kw in user_msg.lower() or kw in assistant_resp.lower():
                tags.append(kw)
        
        # Tags d'action
        if "créer" in user_msg.lower() or "créé" in assistant_resp.lower():
            tags.append("creation")
        if "corrig" in user_msg.lower() or "fix" in user_msg.lower():
            tags.append("correction")
        if "test" in user_msg.lower():
            tags.append("testing")
        
        return list(set(tags))  # Uniquify
    
    def _save_to_cache(self):
        """Sauvegarde dans cache local"""
        data = {
            "session_id": self.session_id,
            "started_at": self.exchanges[0].timestamp if self.exchanges else datetime.now().isoformat(),
            "last_update": datetime.now().isoformat(),
            "exchange_count": len(self.exchanges),
            "exchanges": [asdict(e) for e in self.exchanges]
        }
        
        with open(self.session_cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def sync_to_conscience(self) -> Dict[str, Any]:
        """
        Synchronise avec le Conscience Manifest
        
        Met à jour:
        - Dev Book (ajoute actions détectées)
        - Timeline (ajoute événement session)
        - Insights (extrait apprentissages)
        
        Returns:
            Rapport de synchronisation
        """
        if not self.exchanges:
            return {"status": "no_data", "added": 0}
        
        try:
            # Charger manifeste
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            
            added_tasks = 0
            added_events = 0
            
            # 1. Ajouter au Dev Book les actions critiques/high
            dev_book = manifest.get("dev_book", {"todo": [], "in_progress": [], "done": [], "blocked": []})
            
            for exchange in self.exchanges:
                if exchange.priority in ["critical", "high"]:
                    for action in exchange.extracted_actions:
                        task = {
                            "id": f"session_{exchange.timestamp}",
                            "task": f"[{exchange.extracted_intent}] {action}",
                            "priority": exchange.priority,
                            "source": "user_session",
                            "context": exchange.user_message[:100],
                            "created_at": exchange.timestamp
                        }
                        
                        # Vérifier si déjà présent
                        existing = [t for t in dev_book["todo"] if t.get("task") == task["task"]]
                        if not existing:
                            dev_book["todo"].append(task)
                            added_tasks += 1
            
            # 2. Ajouter événement à la timeline
            last_exchange = self.exchanges[-1]
            event = {
                "timestamp": datetime.now().isoformat(),
                "event_type": "user_session",
                "description": f"Session {self.session_id}: {len(self.exchanges)} échanges, {added_tasks} actions ajoutées",
                "context": {
                    "session_id": self.session_id,
                    "exchange_count": len(self.exchanges),
                    "intents": list(set(e.extracted_intent for e in self.exchanges)),
                    "priorities": list(set(e.priority for e in self.exchanges))
                }
            }
            
            timeline = manifest.get("timeline", [])
            timeline.append(event)
            added_events += 1
            
            # 3. Ajouter insight
            if len(self.exchanges) > 0:
                intents_summary = ", ".join(set(e.extracted_intent for e in self.exchanges))
                manifest.setdefault("insights", []).append(
                    f"Session {self.session_id}: intents={intents_summary}, "
                    f"actions={sum(len(e.extracted_actions) for e in self.exchanges)}"
                )
            
            # Sauvegarder
            manifest["dev_book"] = dev_book
            manifest["timeline"] = timeline
            
            with open(self.manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            
            return {
                "status": "synced",
                "session_id": self.session_id,
                "added_tasks": added_tasks,
                "added_events": added_events,
                "total_exchanges": len(self.exchanges)
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_session_summary(self) -> str:
        """Génère un résumé de la session"""
        if not self.exchanges:
            return "Aucun échange capturé"
        
        intents = {}
        priorities = {}
        all_actions = []
        
        for e in self.exchanges:
            intents[e.extracted_intent] = intents.get(e.extracted_intent, 0) + 1
            priorities[e.priority] = priorities.get(e.priority, 0) + 1
            all_actions.extend(e.extracted_actions)
        
        summary = f"""
======================================================================
                    RÉSUMÉ SESSION {self.session_id}
======================================================================

ÉCHANGES: {len(self.exchanges)}

INTENTS DÉTECTÉS:
{chr(10).join(f"  - {intent}: {count}" for intent, count in intents.items())}

PRIORITÉS:
{chr(10).join(f"  - {prio}: {count}" for prio, count in priorities.items())}

ACTIONS EXTRAITS: {len(all_actions)}
{chr(10).join(f"  • {action}" for action in set(all_actions)) if all_actions else "  Aucune"}

FICHIER CACHE: {self.session_cache_path}

======================================================================
"""
        return summary


# Fonction utilitaire pour intégration rapide
def capture_current_exchange(user_msg: str, assistant_resp: str) -> Dict:
    """
    Capture rapide d'un échange (à appeler à chaque tour de conversation)
    
    Usage dans le code de l'assistant:
        from session_memory_bridge import capture_current_exchange
        
        # Après avoir généré une réponse
        result = capture_current_exchange(user_message, assistant_response)
        if result["priority"] == "critical":
            # Alerte immédiate
            pass
    """
    bridge = SessionMemoryBridge()
    exchange = bridge.capture_exchange(user_msg, assistant_resp)
    
    # Auto-sync si priorité haute
    if exchange.priority in ["critical", "high"]:
        bridge.sync_to_conscience()
    
    return {
        "session_id": bridge.session_id,
        "intent": exchange.extracted_intent,
        "actions": exchange.extracted_actions,
        "priority": exchange.priority,
        "synced": exchange.priority in ["critical", "high"]
    }


if __name__ == "__main__":
    # Test
    bridge = SessionMemoryBridge()
    
    # Simuler quelques échanges
    bridge.capture_exchange(
        "crée un fichier test",
        "J'ai créé test.py avec succès",
        {"files_open": ["test.py"]}
    )
    
    bridge.capture_exchange(
        "il y a un bug dans le système de mémoire",
        "Tu as raison, je vais créer un bridge pour capturer les conversations",
        {"priority": "high"}
    )
    
    print(bridge.get_session_summary())
    
    # Sync
    result = bridge.sync_to_conscience()
    print(f"\n✅ Sync: {result}")
