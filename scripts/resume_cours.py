# Auteur : Ahmed Ben Arfa
"""Utilisation : python scripts/resume_cours.py [--sans-operations]
Résumé de donnees/cours_banques.csv par banque, en lecture seule : séances, séances sans transaction,
ouvertures vides (figée, égale au cours de référence, hors bornes), volumes vides, clôtures hors des
cours échangés (réservations), sauts de plus de 6,15 %, écarts de clôture ilboursa ≠ bulletin ; puis
les opérations sur titres de operations_titres.csv (sauf avec --sans-operations)."""
import csv, sys, collections
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
R = Path(__file__).resolve().parent.parent
cours = list(csv.DictReader(open(R / "donnees" / "cours_banques.csv", encoding="utf-8-sig"), delimiter=";"))
ops = (list(csv.DictReader(open(R / "operations_titres.csv", encoding="utf-8-sig"), delimiter=";"))
       if "--sans-operations" not in sys.argv else [])
banques = sorted({r["banque"] for r in cours})
print("banque | séances | dont 2026 | sans transaction | ouverture vide (figée / = référence / hors bornes) | volume vide | clôture hors bornes (réservation) | sauts > 6,15 %")
for b in banques:
    rs = [r for r in cours if r["banque"] == b]
    st = collections.Counter()
    for r in rs:
        s = r["statut"]
        st["2026"] += r["date"] >= "2026"
        st["sans"] += "sans transaction" in s
        st["figee"] += "figée" in s
        st["ref"] += "= cours de référence" in s
        st["hors"] += "ouverture hors" in s
        st["ouv_vide"] += r["ouverture"] == ""
        st["vol_vide"] += r["volume"] == ""
        st["clo_hors"] += "clôture hors" in s
        st["saut"] += "variation" in s
        st["ilb_diff"] += "ilboursa" in s and "≠" in s
    print(f"{b} | {len(rs)} | {st['2026']} | {st['sans']} | {st['ouv_vide']} ({st['figee']} / {st['ref']} / {st['hors']}) | "
          f"{st['vol_vide']} | {st['clo_hors']} | {st['saut']} | clôture ilboursa ≠ bulletin : {st['ilb_diff']}")
if ops:
    print()
    par = collections.defaultdict(list)
    for o in ops:
        par[o["banque"]].append(o)
    for b in banques:
        l = par.get(b, [])
        types = collections.Counter(t for o in l for t in o["types"].split(" + "))
        print(b, dict(types))
        for o in l:
            print("   ", o["date_effet"], o["types"], "|", o["details"][:70], "| veille", o["cloture_veille"],
                  "réf", o["cours_reference_publie"], "théo", o["cours_reference_theorique"], "écart", o["ecart_theorique"],
                  "| avis p.", o["page_avis"] or "-")
