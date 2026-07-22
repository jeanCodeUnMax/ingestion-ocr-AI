"""
TEST D'INFÉRENCE RÉELLE
Ce script va réellement interroger le LLM et afficher la réponse.
Aucune simulation - on veut la preuve que ça fonctionne.
"""

import subprocess
import sys
import json
from pathlib import Path

def test_inference_via_anthropic_api():
    """
    Méthode 1: Via l'API Anthropic directe
    Nécessite ANTHROPIC_API_KEY dans l'environnement
    """
    print("=" * 60)
    print("MÉTHODE 1: API Anthropic directe")
    print("=" * 60)
    
    try:
        import anthropic
        
        client = anthropic.Anthropic()
        
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": "Réponds en une seule phrase: Quelle est la capitale de la France?"
                }
            ]
        )
        
        response = message.content[0].text
        print(f"RÉPONSE REÇUE: {response}")
        return True, response
        
    except ImportError:
        print("ERREUR: Module 'anthropic' non installé")
        print("Install avec: pip install anthropic")
        return False, None
    except Exception as e:
        print(f"ERREUR: {e}")
        return False, None


def test_inference_via_openai_api():
    """
    Méthode 2: Via l'API OpenAI
    Nécessite OPENAI_API_KEY dans l'environnement
    """
    print("\n" + "=" * 60)
    print("MÉTHODE 2: API OpenAI")
    print("=" * 60)
    
    try:
        import openai
        
        client = openai.OpenAI()
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=100,
            messages=[
                {
                    "role": "user", 
                    "content": "Réponds en une seule phrase: Quelle est la capitale de l'Allemagne?"
                }
            ]
        )
        
        answer = response.choices[0].message.content
        print(f"RÉPONSE REÇUE: {answer}")
        return True, answer
        
    except ImportError:
        print("ERREUR: Module 'openai' non installé")
        print("Install avec: pip install openai")
        return False, None
    except Exception as e:
        print(f"ERREUR: {e}")
        return False, None


def test_inference_via_ollama():
    """
    Méthode 3: Via Ollama (local, gratuit)
    Nécessite Ollama installé et un modèle téléchargé
    """
    print("\n" + "=" * 60)
    print("MÉTHODE 3: Ollama (local)")
    print("=" * 60)
    
    try:
        import requests
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2",
                "prompt": "Réponds en une seule phrase: Quelle est la capitale de l'Italie?",
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get("response", "")
            print(f"RÉPONSE REÇUE: {answer}")
            return True, answer
        else:
            print(f"ERREUR HTTP: {response.status_code}")
            return False, None
            
    except ImportError:
        print("ERREUR: Module 'requests' non installé")
        return False, None
    except requests.exceptions.ConnectionError:
        print("ERREUR: Ollama n'est pas en cours d'exécution")
        print("Démarre avec: ollama serve")
        return False, None
    except Exception as e:
        print(f"ERREUR: {e}")
        return False, None


def test_inference_via_mistral():
    """
    Méthode 4: Via Mistral API
    Nécessite MISTRAL_API_KEY
    """
    print("\n" + "=" * 60)
    print("MÉTHODE 4: Mistral API")
    print("=" * 60)
    
    try:
        import requests
        import os
        
        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            print("ERREUR: MISTRAL_API_KEY non définie")
            return False, None
        
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistral-small-latest",
                "max_tokens": 100,
                "messages": [
                    {
                        "role": "user",
                        "content": "Réponds en une seule phrase: Quelle est la capitale de l'Espagne?"
                    }
                ]
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            print(f"RÉPONSE REÇUE: {answer}")
            return True, answer
        else:
            print(f"ERREUR HTTP: {response.status_code}")
            print(response.text)
            return False, None
            
    except ImportError:
        print("ERREUR: Module 'requests' non installé")
        return False, None
    except Exception as e:
        print(f"ERREUR: {e}")
        return False, None


def test_inference_via_file_bridge():
    """
    Méthode 5: Via fichier pont (pour IDE sans API directe)
    Écrit un prompt dans un fichier surveillé par l'IDE
    """
    print("\n" + "=" * 60)
    print("MÉTHODE 5: Fichier pont (bridge)")
    print("=" * 60)
    
    prompt_file = Path(".agent/inference_prompt.txt")
    response_file = Path(".agent/inference_response.txt")
    
    # Créer le prompt
    prompt = "Réponds en une seule phrase: Quelle est la capitale du Portugal?"
    
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text(prompt, encoding="utf-8")
    
    print(f"Prompt écrit dans: {prompt_file}")
    print(f"Contenu: {prompt}")
    print("\nEn attente de réponse...")
    print("(L'IDE doit surveiller ce fichier et écrire la réponse)")
    
    # Attendre la réponse (max 60 secondes)
    import time
    for i in range(60):
        if response_file.exists():
            response = response_file.read_text(encoding="utf-8")
            print(f"\nRÉPONSE REÇUE: {response}")
            return True, response
        time.sleep(1)
        if i % 10 == 0:
            print(f"  Attente... {i}s/60s")
    
    print("\nTIMEOUT: Pas de réponse reçue après 60 secondes")
    print("L'IDE ne surveille pas le fichier pont")
    return False, None


def test_inference_via_subprocess_claude():
    """
    Méthode 6: Via Claude CLI (si installé)
    """
    print("\n" + "=" * 60)
    print("MÉTHODE 6: Claude CLI")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            ["claude", "-p", "Réponds en une seule phrase: Quelle est la capitale de la Belgique?"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"RÉPONSE REÇUE: {result.stdout.strip()}")
            return True, result.stdout.strip()
        else:
            print(f"ERREUR: {result.stderr}")
            return False, None
            
    except FileNotFoundError:
        print("ERREUR: Claude CLI non installé")
        print("Install avec: npm install -g @anthropic-ai/claude-code")
        return False, None
    except subprocess.TimeoutExpired:
        print("ERREUR: Timeout")
        return False, None
    except Exception as e:
        print(f"ERREUR: {e}")
        return False, None


def main():
    """Test toutes les méthodes d'inférence"""
    
    print("\n" + "=" * 60)
    print("TEST D'INFÉRENCE RÉELLE")
    print("Ce script va tenter d'interroger un LLM de différentes façons")
    print("=" * 60)
    
    results = []
    
    # Tester chaque méthode
    success, response = test_inference_via_anthropic_api()
    results.append(("Anthropic API", success))
    
    success, response = test_inference_via_openai_api()
    results.append(("OpenAI API", success))
    
    success, response = test_inference_via_ollama()
    results.append(("Ollama (local)", success))
    
    success, response = test_inference_via_mistral()
    results.append(("Mistral API", success))
    
    success, response = test_inference_via_subprocess_claude()
    results.append(("Claude CLI", success))
    
    success, response = test_inference_via_file_bridge()
    results.append(("Fichier pont", success))
    
    # Résumé
    print("\n" + "=" * 60)
    print("RÉSUMÉ DES TESTS")
    print("=" * 60)
    
    for method, success in results:
        status = "SUCCÈS" if success else "ÉCHEC"
        print(f"  {method}: {status}")
    
    # Conclusion
    successful = [m for m, s in results if s]
    
    if successful:
        print(f"\nAU MOINS UNE MÉTHODE FONCTIONNE: {successful[0]}")
        print("L'inférence est possible via cette méthode.")
    else:
        print("\nAUCUNE MÉTHODE NE FONCTIONNE")
        print("Pour activer l'inférence, vous devez:")
        print("  1. Installer une clé API (Anthropic, OpenAI, Mistral)")
        print("  2. Ou installer Ollama localement (gratuit)")
        print("  3. Ou installer Claude CLI")
        print("\nSans configuration, l'inférence autonome n'est PAS possible.")
        print("Le système de conscience peut analyser, mais pas corriger seul.")


if __name__ == "__main__":
    main()
