# Auteur : Ahmed Ben Arfa
"""Utilisation : python scripts/verifier_texte_pdf.py BANQUE DOCUMENT INDICATEUR N|N1 [BANQUE DOCUMENT ...]
  exemple : python scripts/verifier_texte_pdf.py UIB 2025T3 PNB N1 WIB 2024T1 CHG_OPER N1
Pour chaque cas (banque, document, code d'indicateur, colonnes de l'année N ou N-1) : les valeurs
extraites (trimestre et cumul, donnees/indicateurs_banques_long.csv) figurent-elles dans le texte
de la page du PDF ? Lecture seule. Une valeur « absente du texte » n'est pas forcément fausse (texte
coupé, « 9 6 549 ») : la regarder sur l'image (scripts/rendre_pages.py)."""
import csv, re, sys
from pathlib import Path
import pdfplumber

sys.stdout.reconfigure(encoding="utf-8")
R = Path(__file__).resolve().parent.parent
args = sys.argv[1:]
if not args or len(args) % 4:
    sys.exit(__doc__)
cas = [tuple(args[i:i + 4]) for i in range(0, len(args), 4)]
longc = list(csv.DictReader(open(R / "donnees" / "indicateurs_banques_long.csv", encoding="utf-8-sig"), delimiter=";"))


def motif(v):
    s = f"{abs(v):,.3f}".rstrip("0").rstrip(".") if v != int(v) else f"{int(abs(v)):,}"
    ent, _, dec = s.partition(".")
    m = r"[\s  .]?".join(ent.split(","))
    if dec:
        m += r"[,.]" + dec
    return re.compile(r"(?<![\d])" + m + r"(?![\d])")


textes = {}
for b, doc, ind, cols in cas:
    lignes = [l for l in longc if l["banque"] == b and l["trimestre"] == doc and l["code_indicateur"] == ind
              and l["colonne"] in (f"trim_{cols}", f"cumul_{cols}")]
    if not lignes:
        print(f"{b:5} {doc} {ind:9} {cols} : aucune valeur extraite")
    for l in lignes:
        f = R / "donnees" / "pdf" / b / l["fichier"]
        cle = (f, int(l["page"]))
        if cle not in textes:
            with pdfplumber.open(f) as pdf:
                textes[cle] = pdf.pages[int(l["page"]) - 1].extract_text() or ""
        v = float(l["valeur_source"])
        ok = bool(motif(v).search(textes[cle]))
        print(f"{b:5} {doc} {ind:9} {l['colonne']:9} {v:>16,.3f}  {'trouvé' if ok else 'ABSENT du texte'}  {l['fichier']} p{l['page']}")
