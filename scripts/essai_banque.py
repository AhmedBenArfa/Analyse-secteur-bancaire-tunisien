"""Utilisation : python scripts/essai_banque.py BT
Extraction d'une banque, en lecture seule (rien n'est écrit dans donnees/) :
statut par document comme dans controle_extraction.csv, contrôles entre documents,
contrôle annuel, et quelques valeurs clés par document."""
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import collecte_banques as cb  # noqa: E402

banque = sys.argv[1]
manifeste = cb.lire_manifeste()
resultats = {}
for (code, tri), r in sorted(manifeste.items()):
    if code != banque or r["statut"] != "ok" or not Path(r["fichier"]).exists():
        continue
    try:
        resultats[(code, tri)] = cb.extraire_pdf(Path(r["fichier"]), cb.Trimestre.depuis_texte(tri), code)
    except Exception as e:
        resultats[(code, tri)] = ([], [f"erreur de lecture : {e}"])
docs = {cle: {(l["code_indicateur"], l["colonne"]): l["valeur_mdt"] for l in lignes}
        for cle, (lignes, _) in resultats.items()}
retr = cb.controle_retraitements(docs)
ecarts = cb.controle_trimestre_cumul(docs)
statuts = Counter()
print(f"{'trim.':<7} {'statut':<22} {'PNB trim':>9} {'PNB cumul':>10} {'Ch.op cumul':>11} {'Crédits':>10} {'Dépôts':>10} {'Cap.pr.':>9}  gabarit / alertes")
for (code, tri), (lignes, alertes) in sorted(resultats.items()):
    e, rt = ecarts.get((code, tri), []), retr.get((code, tri), [])
    statut = cb.statut_document(lignes, alertes, e, rt)
    statuts[statut] += 1
    v = docs[(code, tri)]
    f = lambda c, col: "-" if v.get((c, col)) is None else f"{v[(c, col)]:,.1f}"
    gab = lignes[0]["gabarit"] if lignes else ""
    print(f"{tri:<7} {statut:<22} {f('PNB', 'trim_N'):>9} {f('PNB', 'cumul_N'):>10} {f('CHG_OPER', 'cumul_N'):>11} "
          f"{f('CREDITS', 'cumul_N'):>10} {f('DEPOTS', 'cumul_N'):>10} {f('CAP_PROPRES', 'cumul_N'):>9}  {gab}")
    for a in alertes + e + rt:
        print(f"        - {a}")
manquants = [tri for (code, tri), r in manifeste.items() if code == banque and r["statut"] != "ok"]
print(f"\n{banque} : {dict(statuts)} ; manquants : {manquants}")
illisibles = {cle: Path(manifeste[cle]["fichier"]).name for cle, (lignes, alertes) in resultats.items()
              if not lignes and any(a.startswith(cb.PREFIXE_ILLISIBLE) for a in alertes)}
versions = cb.table_versions({cle: (lignes, Path(manifeste[cle]["fichier"]).name)
                              for cle, (lignes, _) in resultats.items()}, illisibles)
print("Statuts des versions non retenues :",
      dict(Counter(r["statut_revision"] for r in versions if r["statut_revision"] not in ("retenue", ""))))
ruptures = sorted({(r["trimestre"], r["code_indicateur"], r["mesure"], r["detail_rupture"])
                   for r in versions if r["rupture_serie"]})
print(f"Ruptures de série : {len(ruptures)}")
for tri, ind, mesure, detail in ruptures:
    if ind in cb.CODES_RETRAITEMENT:
        print(f"  {tri} {ind:<10} {mesure:<5} {detail}")
ann = cb.controle_somme_annuelle(versions)
print("Contrôle annuel :", dict(Counter(r["statut"] for r in ann)))
for r in ann:
    if r["statut"] != "ok":
        print(f"  {r['annee']} {r['code_indicateur']:<10} somme {r['somme_trimestres']:,.3f} cumul {r['cumul_T4']:,.3f} "
              f"({r['source_cumul']}) écart {r['ecart']:+,.3f} -> {r['statut']}")
