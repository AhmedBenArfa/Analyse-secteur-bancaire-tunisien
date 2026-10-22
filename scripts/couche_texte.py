# Auteur : Ahmed Ben Arfa
"""Utilisation : python scripts/couche_texte.py BH
Pour chaque PDF d'une banque : nombre de pages, caractères de texte et images par page
(lecture seule). Un PDF sans texte mais avec une grande image par page est un scan."""
import sys
from pathlib import Path

import pdfplumber

sys.stdout.reconfigure(encoding="utf-8")
racine = Path(__file__).resolve().parent.parent
banque = sys.argv[1]
print(f"{'fichier':<26} {'pages':>5}  caractères par page (images)            verdict")
for p in sorted((racine / "donnees" / "pdf" / banque).glob("*.pdf")):
    with pdfplumber.open(p) as pdf:
        stats = [(len(page.chars), len(page.images)) for page in pdf.pages[:4]]
        n = len(pdf.pages)
    texte = sum(c for c, _ in stats)
    images = sum(i for _, i in stats)
    verdict = "texte" if texte > 500 else ("scan (image sans texte)" if images else "vide ?")
    detail = " ".join(f"{c}({i})" for c, i in stats)
    print(f"{p.name:<26} {n:>5}  {detail:<38} {verdict}")
