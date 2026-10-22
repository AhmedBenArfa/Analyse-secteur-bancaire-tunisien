# Auteur : Ahmed Ben Arfa
"""Utilisation : python scripts/rendre_pages.py FICHIER.pdf PAGES [DPI] [DOSSIER]
  exemple : python scripts/rendre_pages.py donnees/pdf/BTE/BTE_2022T1.pdf 1,2 200
Enregistre l'image de chaque page demandée (numéros séparés par des virgules, à partir de 1) en PNG,
pour comparer une valeur extraite au document (règle « vérifier avant d'affirmer »). DPI : 110 par
défaut ; DOSSIER : donnees/verification/ par défaut (non versionné). Le PDF n'est pas modifié."""
import sys
from pathlib import Path
import fitz

if len(sys.argv) < 3:
    sys.exit(__doc__)
pdf = Path(sys.argv[1])
dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 110
dossier = Path(sys.argv[4]) if len(sys.argv) > 4 else Path(__file__).resolve().parent.parent / "donnees" / "verification"
dossier.mkdir(parents=True, exist_ok=True)
d = fitz.open(pdf)
for p in sys.argv[2].split(","):
    sortie = dossier / f"{pdf.stem}_p{p}.png"
    d[int(p) - 1].get_pixmap(dpi=dpi).save(sortie)
    print(sortie)
