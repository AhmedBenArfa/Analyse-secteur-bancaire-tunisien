"""Utilisation : python scripts/bilan_extraction.py
Bilan de l'extraction des 12 banques, en lecture seule des CSV produits par « extraire » :
statuts des documents, saisies manuelles, valeurs non disponibles, valeurs de référence et
révisions importantes par banque. Écrit la liste des révisions importantes des totaux (version
initiale remplacée par une révision de plus de 2 % sur le cumul) dans docs/revisions_importantes.csv.
"""
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "docs" / "revisions_importantes.csv"
TOTAUX = ["PNB", "PROD_EXPL", "CHG_EXPL", "CHG_OPER", "CREDITS", "DEPOTS"]


def lire(chemin: Path) -> list[dict]:
    with chemin.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ctrl = lire(RACINE / "donnees" / "controle_extraction.csv")
    vers = lire(RACINE / "donnees" / "indicateurs_versions.csv")
    saisies = lire(RACINE / "saisies_manuelles.csv")
    ref = lire(RACINE / "tests" / "valeurs_reference.csv")
    fichier_version = {(v["banque"], v["trimestre"], v["code_indicateur"], v["mesure"], v["version"]): v["fichier"]
                       for v in vers}
    rev = defaultdict(list)
    for v in vers:
        if (v["statut_revision"] == "revision_importante" and v["mesure"] == "cumul" and v["version"] == "initiale"
                and v["code_indicateur"] in TOTAUX):
            rev[v["banque"]].append(v)

    print(f"{'banque':<6} {'PDF':>4} {'lus':>4} {'ok':>3} {'retr.':>5} {'éc.T/C':>6} {'éc.comp':>7} "
          f"{'à vérif.':>8} {'saisis':>6} {'illis.':>6} {'manq.':>5} | saisies docs/val. | non disp. | "
          f"réf. docs/val. | rév. imp.")
    tot = Counter()
    for b in sorted({c["banque"] for c in ctrl}):
        s = Counter(c["statut"] for c in ctrl if c["banque"] == b)
        pdf = sum(n for k, n in s.items() if k not in ("pdf manquant", "non publié"))
        lus = pdf - s["illisible (image)"] - s["echec"]
        sd = len({x["trimestre"] for x in saisies if x["banque"] == b})
        sv = sum(x["banque"] == b for x in saisies)
        nd = sum(v["banque"] == b and v["statut_revision"] == "non disponible (image)" for v in vers)
        rd = len({x["trimestre"] for x in ref if x["banque"] == b})
        rv = sum(x["banque"] == b for x in ref)
        ligne = {"pdf": pdf, "lus": lus, "ok": s["ok"], "retr": s["retraitement possible"],
                 "ectc": s["ecart trimestre/cumul"], "ecc": s["ecart composantes"], "av": s["a verifier"],
                 "sm": s["saisie manuelle"], "ill": s["illisible (image)"], "manq": s["pdf manquant"] + s["non publié"],
                 "sd": sd, "sv": sv, "nd": nd, "rd": rd, "rv": rv, "rev": len(rev[b])}
        tot.update(ligne)
        afficher(b, ligne)
    afficher("Total", tot)
    print("\na verifier :", [(c["banque"], c["trimestre"]) for c in ctrl if c["statut"] == "a verifier"])
    print("pdf manquants :", [(c["banque"], c["trimestre"]) for c in ctrl if c["statut"] == "pdf manquant"])
    print("non publiés :", [(c["banque"], c["trimestre"]) for c in ctrl if c["statut"] == "non publié"])
    exclues = Counter(v["statut_revision"].split(" :")[0] for v in vers if v["statut_revision"].startswith("exclue ("))
    print("versions exclues :", dict(exclues))

    lignes = []
    for b in sorted(rev):
        for v in sorted(rev[b], key=lambda v: (v["trimestre"], TOTAUX.index(v["code_indicateur"]))):
            ini, ret = float(v["valeur_mdt"]), float(v["valeur_retenue"])
            lignes.append({"banque": b, "periode": v["trimestre"], "indicateur": v["code_indicateur"],
                           "publie_mdt": f"{ini:.3f}", "retenu_mdt": f"{ret:.3f}",
                           "ecart_pct": f"{100 * (ret - ini) / abs(ini):+.1f}" if ini else "",
                           "version_retenue": v["source_valeur"], "fichier_publie": v["fichier"],
                           "fichier_retenu": fichier_version.get((b, v["trimestre"], v["code_indicateur"],
                                                                  "cumul", v["source_valeur"]), ""),
                           "mention_retraitement": v["mention_retraitement"]})
    with SORTIE.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0]), delimiter=";")
        w.writeheader()
        w.writerows(lignes)
    print(f"\n{len(lignes)} révisions importantes de totaux (cumul) -> {SORTIE}")
    print("par indicateur :", dict(Counter(l["indicateur"] for l in lignes)))


def afficher(nom: str, l: dict):
    print(f"{nom:<6} {l['pdf']:>4} {l['lus']:>4} {l['ok']:>3} {l['retr']:>5} {l['ectc']:>6} {l['ecc']:>7} "
          f"{l['av']:>8} {l['sm']:>6} {l['ill']:>6} {l['manq']:>5} | {l['sd']:>7} / {l['sv']:<7} | {l['nd']:>9} | "
          f"{l['rd']:>6} / {l['rv']:<5} | {l['rev']:>9}")


if __name__ == "__main__":
    main()
