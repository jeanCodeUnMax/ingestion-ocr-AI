"""
Intégration Conscience Manifest dans le Pipeline RAG

Ce module montre comment intégrer la conscience manifeste dans le 
pipeline RAG existant pour un système auto-évolutif.
"""
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

# Import du pipeline existant
from pipeline import RAGPipeline
from conscience_manifest import ConscienceManifest, SystemState


class ConsciousRAGPipeline(RAGPipeline):
    """
    Pipeline RAG avec conscience manifeste intégrée
    
    Ce pipeline étend le RAGPipeline standard avec:
    - Réveils cycliques de conscience
    - Auto-détection de problèmes
    - Changement de stratégie adaptatif
    - Mémoire persistante de l'évolution
    
    Example:
        >>> pipeline = ConsciousRAGPipeline()
        >>> await pipeline.start_conscience()  # Démarre les réveils
        >>> results = await pipeline.search("python")  # Recherche consciente
    """
    
    def __init__(self, config_path: str = None, enable_conscience: bool = True):
        """
        Initialise le pipeline avec conscience
        
        Args:
            config_path: Chemin de la config
            enable_conscience: Activer le système de conscience
        """
        super().__init__(config_path)
        
        self.enable_conscience = enable_conscience
        self.conscience = None
        self.conscience_task = None
        
        if enable_conscience:
            # Créer la conscience manifeste
            self.conscience = ConscienceManifest(
                manifest_path=".agent/consciousness_manifest.json",
                wake_interval_minutes=5,  # Réveil toutes les 5 minutes
                on_wake_callback=self._on_conscience_wake
            )
            
            # Enregistrer les composants à monitorer
            self._register_components()
    
    def _register_components(self):
        """Enregistre les composants du pipeline pour monitoring"""
        # Par défaut, tous les composants sont healthy
        # Le pipeline mettra à jour selon l'état réel
        pass
    
    async def _on_conscience_wake(self, manifest: Dict[str, Any]):
        """
        Callback appelé à chaque réveil de conscience
        
        C'est ici que le "modèle" reçoit le manifeste et peut agir.
        """
        state = manifest.get("current_state", "unknown")
        strategy = manifest.get("active_strategy", "standard")
        
        print(f"\n🧠 [CONSCIENCE] Réveil du pipeline!")
        print(f"   État: {state}")
        print(f"   Stratégie: {strategy}")
        print(f"   Intentions: {manifest.get('intentions', ['évoluer'])[0]}")
        
        # Adapter le comportement selon la stratégie
        if strategy == "qdrant_only":
            print(f"   ⚠️ Fallback activé: Désactivation de Zvec")
            self._disable_zvec_temporarily()
        
        elif strategy == "local_only":
            print(f"   🚨 Mode d'urgence: API externes désactivées")
            self._enable_emergency_mode()
        
        elif strategy == "cache_first":
            print(f"   💾 Mode cache: Priorité SQLite")
            self._prioritize_cache()
        
        # Si problème détecté, demander au modèle de réfléchir
        if state in ["degraded", "critical"]:
            summary = self.conscience.get_insights_summary()
            print(f"\n💡 [SUGGESTION AU MODÈLE]")
            print(summary)
            print(f"\n🤔 Que dois-je faire pour améliorer la situation?")
    
    async def start_conscience(self):
        """Démarre la boucle de conscience"""
        if self.conscience:
            print("🧠 Démarrage de la conscience manifeste...")
            self.conscience_task = asyncio.create_task(
                self.conscience.start_conscience_loop()
            )
    
    def stop_conscience(self):
        """Arrête la boucle de conscience"""
        if self.conscience:
            print("🧠 Arrêt de la conscience...")
            self.conscience.stop_conscience_loop()
    
    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Recherche avec conscience
        
        La conscience peut modifier la stratégie de recherche
        selon l'état du système.
        """
        if not self.enable_conscience or not self.conscience:
            # Mode standard sans conscience
            return await super().search(query, **kwargs)
        
        # Vérifier l'état de conscience avant recherche
        manifest = self.conscience.get_current_manifest()
        state = manifest.get("current_state", "healthy")
        
        # Adapter la recherche selon l'état
        if state == "critical":
            print(f"⚠️ [CONSCIENCE] État critique! Recherche minimale.")
            kwargs["max_results"] = 3  # Limite les résultats
        
        # Effectuer la recherche
        results = await super().search(query, **kwargs)
        
        # Reporter le statut de la recherche à la conscience
        if results.get("success", False):
            # Recherche réussie → système healthy
            self.conscience.report_component_status("search_pipeline", True)
        else:
            # Échec → problème détecté
            self.conscience.report_component_status("search_pipeline", False)
        
        return results
    
    def _disable_zvec_temporarily(self):
        """Désactive temporairement Zvec (fallback)"""
        # Désactiver dans la config de fusion
        if hasattr(self, 'fusion'):
            self.fusion.weights["zvec"] = 0.0
            self.fusion.weights["qdrant"] = 0.9
            self.fusion.weights["memory"] = 0.1
    
    def _enable_emergency_mode(self):
        """Active le mode d'urgence (local seulement)"""
        # Désactiver tous les appels API
        if hasattr(self, 'embedder'):
            self.embedder.config["qdrant"]["enabled"] = False
    
    def _prioritize_cache(self):
        """Priorise le cache SQLite"""
        # Augmenter les poids du cache
        pass  # Implémentation selon cache system
    
    def get_conscience_summary(self) -> str:
        """Retourne un résumé pour le modèle"""
        if not self.conscience:
            return "Conscience non activée"
        
        return self.conscience.get_insights_summary()
    
    async def report_error(self, error_type: str, description: str):
        """
        Reporte une erreur à la conscience
        
        Permet au système d'apprendre de ses erreurs.
        """
        if self.conscience:
            self.conscience.report_component_status(error_type, False)
            print(f"🧠 [CONSCIENCE] Erreur reportée: {error_type}")


# Example d'utilisation
async def demo_conscious_pipeline():
    """Démo du pipeline conscient"""
    print("=" * 70)
    print("  DÉMO - PIPELINE RAG CONSCIENT")
    print("=" * 70)
    
    # Créer le pipeline
    pipeline = ConsciousRAGPipeline(enable_conscience=True)
    
    # Démarrer la conscience
    await pipeline.start_conscience()
    
    print("\n⏱️  La conscience se réveillera toutes les 5 minutes")
    print("   Elle surveille l'état du système et adapte la stratégie")
    
    # Simuler une recherche
    print("\n🔍 Simulation de recherche...")
    # results = await pipeline.search("python tutorial")
    
    # Afficher le résumé de conscience
    print("\n" + pipeline.get_conscience_summary())
    
    # Arrêter après la démo
    await asyncio.sleep(1)
    pipeline.stop_conscience()
    
    print("\n✅ Pipeline conscient démontré!")


if __name__ == '__main__':
    asyncio.run(demo_conscious_pipeline())
