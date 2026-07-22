import re
import json

class SemanticCompressor:
    """
    Entité isolée chargée de protéger le modèle Ollama contre la pollution du contexte.
    Transforme les données brutes (logs, erreurs, listes) en 'cristaux sémantiques'.
    """
    def __init__(self, token_budget=500):
        self.token_budget = token_budget

    def digest_tool_output(self, tool_type, raw_output):
        """
        Méthode principale de compression. 
        Selon le type d'outil, applique une stratégie de nettoyage différente.
        """
        if "Traceback" in raw_output or "Error" in raw_output:
            return self._compress_error(raw_output)
        
        if tool_type == "LIST_DIR":
            return self._compress_listing(raw_output)
            
        return self._summarize_generic(raw_output)

    def _compress_error(self, error_text):
        """Extrait uniquement l'essence de l'erreur sans la poubelle technique."""
        # Regex pour trouver le message d'erreur final
        match = re.search(r'(\w+Error:.*)', error_text)
        if match:
            return f"❌ ÉCHEC TECHNIQUE : {match.group(1)}"
        return "❌ ÉCHEC TECHNIQUE : Erreur inconnue (voir logs complets si nécessaire)."

    def _compress_listing(self, listing_text):
        """Réduit un listing de fichiers à sa structure essentielle."""
        lines = listing_text.split('\n')
        if len(lines) > 15:
            return f"📂 STRUCTURE : {len(lines)} fichiers détectés. (Exemples : {', '.join(lines[1:5])}...)"
        return listing_text

    def _summarize_generic(self, text):
        """Résumé basique pour les contenus textuels trop longs."""
        if len(text) > self.token_budget:
            return f"{text[:self.token_budget]}... [DONNÉES TRONQUÉES POUR L'HYGIÈNE DU MODÈLE]"
        return text

if __name__ == "__main__":
    compressor = SemanticCompressor()
    test_err = "Traceback (most recent call last):\n  File 'test.py', line 1\nUnicodeEncodeError: 'charmap' codec can't encode..."
    print(f"TEST COMPRESSION ERREUR : {compressor.digest_tool_output('READ_FILE', test_err)}")
