# Auteur : Ahmed Ben Arfa
"""Utilisation : python scripts/chercher_actionnariat.py "donnees/pdf_etats_financiers/BTE/*.pdf"
Extraits des pages qui décrivent la structure du capital (répartition du capital, actionnaire de
référence, société mère…) dans les PDF donnés (motif glob), en lecture seule : sert à trouver la
source et la page d'une ligne de donnees_reference/banques.xlsx (scripts/ecrire_banques_xlsx.py)."""
import glob, re, sys, unicodedata
import fitz

sys.stdout.reconfigure(encoding="utf-8")


def norm(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


if len(sys.argv) < 2:
    sys.exit(__doc__)
MOTS = re.compile(r"(?:structure du capital|repartition du capital|actionnariat|actionnaire de reference|"
                  r"actionnaires? majoritaire|etat tunisien|maison mere|societe mere|detient \d|participation de \d|"
                  r"filiale (?:du|de la|de l)|groupe (?:bnp|attijariwafa|al baraka|qatar|caisse))")
for f in sorted(glob.glob(sys.argv[1])):
    d = fitz.open(f)
    for p in d:
        t = re.sub(r"\s+", " ", norm(p.get_text()))
        for m in MOTS.finditer(t):
            print(f.replace("\\", "/").split("/")[-1], "p.", p.number + 1, "|", t[max(0, m.start() - 150):m.end() + 250])
