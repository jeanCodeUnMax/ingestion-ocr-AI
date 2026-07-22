#!/usr/bin/env python3
from pathlib import Path
import fitz

output = Path(__file__).resolve().parent.parent / "sample-ocr-ai-system.pdf"
document = fitz.open()
pages = [
    "Maintenance préventive\nLa maintenance préventive réduit les pannes des moteurs et améliore la disponibilité.",
    "Méthode 5S\nTrier, ranger, nettoyer, standardiser et maintenir les bonnes pratiques.",
    "Procédure de contrôle\nÉtape 1 : inspecter. Étape 2 : mesurer. Étape 3 : enregistrer le résultat.",
]
for content in pages:
    page = document.new_page()
    page.insert_textbox(fitz.Rect(72, 72, 520, 760), content, fontsize=14)
document.save(output)
print(output)
