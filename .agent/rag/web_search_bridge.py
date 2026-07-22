"""
Web Search Bridge - Pont de recherche web pour le système de conscience

Ce module permet au système de conscience d'effectuer des recherches web
de manière autonome via des APIs externes.

APIs supportées:
- Tavily (recommandé pour l'IA)
- Serper (Google Search API)
- Brave Search API
- DuckDuckGo (gratuit, sans API key)

Usage:
    bridge = WebSearchBridge(api_key="tvly-xxx", provider="tavily")
    results = await bridge.search("latest AI news")
    
    # Intégration avec la conscience
    conscious_bridge.register_web_search(bridge)
"""

import aiohttp
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import json


@dataclass
class SearchResult:
    """Résultat d'une recherche web"""
    title: str
    url: str
    snippet: str
    source: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "timestamp": self.timestamp
        }


@dataclass
class WebSearchResponse:
    """Réponse complète d'une recherche web"""
    query: str
    results: List[SearchResult]
    total_results: int
    provider: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "total_results": self.total_results,
            "provider": self.provider,
            "timestamp": self.timestamp
        }


class WebSearchBridge:
    """
    Pont de recherche web pour le système de conscience
    
    Permet au système d'effectuer des recherches web autonomes
    via différentes APIs.
    
    Attributes:
        api_key: Clé API (optionnel pour DuckDuckGo)
        provider: Fournisseur de recherche (tavily, serper, brave, duckduckgo)
        timeout: Timeout des requêtes en secondes
        max_results: Nombre maximum de résultats
    
    Example:
        >>> bridge = WebSearchBridge(api_key="tvly-xxx", provider="tavily")
        >>> results = await bridge.search("Python async patterns")
        >>> print(results.results[0].title)
    """
    
    # Configuration des providers
    PROVIDERS = {
        "tavily": {
            "url": "https://api.tavily.com/search",
            "requires_key": True,
            "method": "POST"
        },
        "serper": {
            "url": "https://google.serper.dev/search",
            "requires_key": True,
            "method": "POST"
        },
        "brave": {
            "url": "https://api.search.brave.com/res/v1/web/search",
            "requires_key": True,
            "method": "GET"
        },
        "duckduckgo": {
            "url": "https://api.duckduckgo.com/",
            "requires_key": False,
            "method": "GET"
        }
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: str = "duckduckgo",
        timeout: int = 30,
        max_results: int = 5
    ):
        self.api_key = api_key
        self.provider = provider
        self.timeout = timeout
        self.max_results = max_results
        
        # Vérifier si le provider nécessite une clé
        config = self.PROVIDERS.get(provider)
        if config and config["requires_key"] and not api_key:
            raise ValueError(f"Provider '{provider}' requires an API key")
        
        # Statistiques
        self.stats = {
            "total_searches": 0,
            "successful_searches": 0,
            "failed_searches": 0,
            "last_search": None
        }
    
    async def search(self, query: str, max_results: Optional[int] = None) -> WebSearchResponse:
        """
        Effectue une recherche web
        
        Args:
            query: Requête de recherche
            max_results: Nombre max de résultats (override)
            
        Returns:
            Réponse de recherche avec résultats
        """
        max_results = max_results or self.max_results
        self.stats["total_searches"] += 1
        self.stats["last_search"] = datetime.now().isoformat()
        
        try:
            if self.provider == "tavily":
                results = await self._search_tavily(query, max_results)
            elif self.provider == "serper":
                results = await self._search_serper(query, max_results)
            elif self.provider == "brave":
                results = await self._search_brave(query, max_results)
            else:
                results = await self._search_duckduckgo(query, max_results)
            
            self.stats["successful_searches"] += 1
            return WebSearchResponse(
                query=query,
                results=results,
                total_results=len(results),
                provider=self.provider
            )
            
        except Exception as e:
            self.stats["failed_searches"] += 1
            raise RuntimeError(f"Search failed: {str(e)}")
    
    async def _search_tavily(self, query: str, max_results: int) -> List[SearchResult]:
        """Recherche via Tavily API"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "api_key": self.api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic"
            }
            
            async with session.post(
                self.PROVIDERS["tavily"]["url"],
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                data = await response.json()
                
                results = []
                for item in data.get("results", []):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("content", ""),
                        source="tavily"
                    ))
                
                return results
    
    async def _search_serper(self, query: str, max_results: int) -> List[SearchResult]:
        """Recherche via Serper (Google) API"""
        async with aiohttp.ClientSession() as session:
            headers = {"X-API-KEY": self.api_key}
            payload = {"q": query, "num": max_results}
            
            async with session.post(
                self.PROVIDERS["serper"]["url"],
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                data = await response.json()
                
                results = []
                for item in data.get("organic", []):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        source="serper"
                    ))
                
                return results
    
    async def _search_brave(self, query: str, max_results: int) -> List[SearchResult]:
        """Recherche via Brave Search API"""
        async with aiohttp.ClientSession() as session:
            headers = {"X-Subscription-Token": self.api_key}
            params = {"q": query, "count": max_results}
            
            async with session.get(
                self.PROVIDERS["brave"]["url"],
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                data = await response.json()
                
                results = []
                for item in data.get("web", {}).get("results", []):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("description", ""),
                        source="brave"
                    ))
                
                return results
    
    async def _search_duckduckgo(self, query: str, max_results: int) -> List[SearchResult]:
        """Recherche via DuckDuckGo (gratuit, pas de clé requise)"""
        async with aiohttp.ClientSession() as session:
            params = {
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1
            }
            
            async with session.get(
                self.PROVIDERS["duckduckgo"]["url"],
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                data = await response.json()
                
                results = []
                
                # Résultat principal
                if data.get("AbstractText"):
                    results.append(SearchResult(
                        title=data.get("Heading", query),
                        url=data.get("AbstractURL", ""),
                        snippet=data.get("AbstractText", ""),
                        source="duckduckgo"
                    ))
                
                # Résultats liés
                for item in data.get("RelatedTopics", [])[:max_results-1]:
                    if isinstance(item, dict) and "Text" in item:
                        results.append(SearchResult(
                            title=item.get("Text", "").split(" - ")[0] if " - " in item.get("Text", "") else item.get("Text", ""),
                            url=item.get("FirstURL", ""),
                            snippet=item.get("Text", ""),
                            source="duckduckgo"
                        ))
                
                return results[:max_results]
    
    async def search_and_save(
        self,
        query: str,
        output_file: str,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Recherche et sauvegarde les résultats dans un fichier
        
        Args:
            query: Requête de recherche
            output_file: Chemin du fichier de sortie
            format: Format de sortie (json, markdown, txt)
            
        Returns:
            Résultats + chemin du fichier
        """
        response = await self.search(query)
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(response.to_dict(), f, indent=2, ensure_ascii=False)
        
        elif format == "markdown":
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"# Recherche: {query}\n\n")
                f.write(f"*Effectué le {response.timestamp} via {response.provider}*\n\n")
                
                for i, result in enumerate(response.results, 1):
                    f.write(f"## {i}. {result.title}\n\n")
                    f.write(f"**URL**: {result.url}\n\n")
                    f.write(f"**Résumé**: {result.snippet}\n\n")
                    f.write("---\n\n")
        
        else:  # txt
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"Recherche: {query}\n")
                f.write(f"Date: {response.timestamp}\n\n")
                
                for i, result in enumerate(response.results, 1):
                    f.write(f"{i}. {result.title}\n")
                    f.write(f"   URL: {result.url}\n")
                    f.write(f"   {result.snippet}\n\n")
        
        return {
            "results": response.to_dict(),
            "saved_to": str(output_path),
            "format": format
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de recherche"""
        return self.stats.copy()


# ===================================================================
# Intégration avec le système de conscience
# ===================================================================

class ConsciousWebSearch:
    """
    Extension du système de conscience pour la recherche web
    
    S'intègre avec ConsciousnessBridge pour permettre
    les recherches web autonomes.
    """
    
    def __init__(self, web_bridge: WebSearchBridge, consciousness_bridge):
        self.web_bridge = web_bridge
        self.consciousness = consciousness_bridge
        
        # Enregistrer les callbacks
        self.consciousness.on_assessment(self._on_assessment)
    
    async def _on_assessment(self, assessment):
        """Callback appelé après chaque auto-évaluation"""
        # Vérifier si une tâche nécessite une recherche web
        pending = self.consciousness.state.pending_actions
        
        for action in pending:
            if action.get("type") == "web_search":
                query = action.get("query", "")
                output = action.get("output_file", "")
                
                try:
                    result = await self.web_bridge.search_and_save(query, output)
                    
                    # Mettre à jour le manifeste
                    self.consciousness.state.last_assessment["web_search_result"] = result
                    
                except Exception as e:
                    # Enregistrer l'échec
                    self.consciousness.state.last_assessment["web_search_error"] = str(e)
    
    async def execute_web_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Exécute une tâche de recherche web
        
        Args:
            task: Tâche avec query, output_file, format
            
        Returns:
            Résultat de la recherche
        """
        # Validation éthique d'abord
        validation = await self.consciousness.guardrails.validate_action(
            f"web_search: {task.get('query', '')}"
        )
        
        if not validation["valid"]:
            return {
                "status": "blocked",
                "reason": validation["reason"]
            }
        
        # Exécuter la recherche
        return await self.web_bridge.search_and_save(
            query=task.get("query", ""),
            output_file=task.get("output_file", "search_results.json"),
            format=task.get("format", "json")
        )


# ===================================================================
# Example d'utilisation
# ===================================================================

async def example_usage():
    """Exemple d'utilisation du WebSearchBridge"""
    
    # Créer le bridge (DuckDuckGo ne nécessite pas de clé)
    bridge = WebSearchBridge(provider="duckduckgo", max_results=5)
    
    # Effectuer une recherche
    results = await bridge.search("Python asyncio best practices 2024")
    
    print(f"Found {results.total_results} results:")
    for r in results.results:
        print(f"  - {r.title}: {r.url}")
    
    # Sauvegarder dans un fichier
    saved = await bridge.search_and_save(
        query="Machine learning frameworks comparison",
        output_file=".agent/knowledge/ml_frameworks.md",
        format="markdown"
    )
    
    print(f"\nSaved to: {saved['saved_to']}")


if __name__ == "__main__":
    asyncio.run(example_usage())
