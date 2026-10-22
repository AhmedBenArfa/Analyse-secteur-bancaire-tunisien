# Auteur : Ahmed Ben Arfa
"""Utilisation : python scripts/analyse_ecarts.py [BANQUE ...]
Examen des écarts du contrôle annuel (statut « ecart » de donnees/controle_annuel.csv), en lecture
seule : pour chaque écart, origine de chaque trimestre et de chaque cumul retenus (version, fichier),
puis découpage de l'écart document par document (cumul − trimestre − cumul précédent, dans les
documents de l'année N+1, puis dans ceux de l'année N). Sert à trouver la cause d'un nouvel écart
avant de l'écrire dans docs/ecarts_annuels.csv (test test_ecarts_annuels_expliques)."""
import csv, sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
D = Path(__file__).resolve().parent.parent / "donnees"
vers = list(csv.DictReader(open(D / "indicateurs_versions.csv", encoding="utf-8-sig"), delimiter=";"))
ann = list(csv.DictReader(open(D / "controle_annuel.csv", encoding="utf-8-sig"), delimiter=";"))
V = defaultdict(dict)   # (banque, trimestre, ind, mesure) -> version -> (valeur, fichier, page)
RET = {}
for r in vers:
    k = (r["banque"], r["trimestre"], r["code_indicateur"], r["mesure"])
    if r["valeur_mdt"]:
        V[k][r["version"]] = (float(r["valeur_mdt"]), r["fichier"], r["page"])
    if r["statut_revision"] == "retenue":
        RET[k] = (float(r["valeur_retenue"]), r["source_valeur"], r["fichier"])
f = lambda x: f"{x:9.3f}" if isinstance(x, float) else f"{'-':>9}"
filtre = sys.argv[1:]
for e in ann:
    if e["statut"] != "ecart" or (filtre and e["banque"] not in filtre):
        continue
    b, y, ind = e["banque"], int(e["annee"]), e["code_indicateur"]
    print(f"\n=== {b} {y} {ind} : somme {float(e['somme_trimestres']):.3f} cumul {float(e['cumul_T4']):.3f} écart {float(e['ecart']):+.3f}")
    for q in (1, 2, 3, 4):
        t = f"{y}T{q}"
        rt, rc = RET.get((b, t, ind, "trim")), RET.get((b, t, ind, "cumul"))
        print(f"  {t} retenu trim {f(rt[0]) if rt else '-'} ({rt[1] if rt else ''} {rt[2] if rt else ''}) | cumul {f(rc[0]) if rc else '-'} ({rc[1] if rc else ''} {rc[2] if rc else ''})")
    for nom, vt, vc in (("N+1", lambda q: f"revisee_T{q}_N+1", lambda q: f"revisee_T{q}_N+1"),
                        ("N  ", lambda q: "initiale", lambda q: "initiale")):
        prec = 0.0
        ligne = []
        for q in (1, 2, 3, 4):
            t = f"{y}T{q}"
            tr = V[(b, t, ind, "trim")].get(vt(q))
            cu = V[(b, t, ind, "cumul")].get(vc(q))
            if q == 1 and tr is None:
                tr = cu
            if tr is None or cu is None:
                ligne.append(f"T{q}: manque"); prec = None; continue
            gap = None if prec is None else cu[0] - tr[0] - prec
            ligne.append(f"T{q} [{cu[1]} p{cu[2]}] trim {tr[0]:.3f} cumul {cu[0]:.3f} saut {('%+.3f' % gap) if gap is not None else '?'}")
            prec = cu[0]
        print(f"  docs {nom} : " + "\n               ".join(ligne))
