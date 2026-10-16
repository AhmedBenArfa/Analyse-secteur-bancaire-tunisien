"""
Compare l'extraction automatique aux valeurs relevées à la main dans les PDF
(tests/valeurs_reference.csv : banque, trimestre, fichier, page, indicateur, colonne, valeur).

Les PDF ne sont pas versionnés : ils doivent avoir été téléchargés dans donnees/pdf/.

Utilisation :
  python tests/test_extraction.py      (affiche le tableau des écarts, code de sortie 1 si échec)
  python -m pytest tests/              (même contrôle via pytest)
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import collecte_banques as cb  # noqa: E402

REFERENCE = Path(__file__).resolve().parent / "valeurs_reference.csv"
FACTEURS = {"dinars": 1e-6, "milliers de dinars": 1e-3, "millions de dinars": 1.0}
TOLERANCE = 1e-9   # écart relatif admis (arrondis de calcul seulement)
# Somme des trimestres vs cumul : les banques qui publient en milliers de dinars arrondissent
# chaque chiffre, leurs tableaux ne s'additionnent qu'à 1 ou 2 milliers près
# (UIB 2025 : produits 918 583 en somme, 918 582 publié en cumul).
TOLERANCE_SOMME_MDT = 0.002


def proche(a: float, b: float) -> bool:
    return abs(a - b) <= TOLERANCE * max(1.0, abs(b))


def lire_reference() -> list[dict]:
    with REFERENCE.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def comparer() -> list[dict]:
    """Renvoie une ligne de résultat par valeur de référence."""
    references = lire_reference()
    extraits: dict[str, tuple[dict, list[str]]] = {}
    resultats = []
    for ref in references:
        fichier = ref["fichier"]
        chemin = cb.DOSSIER_PDF / ref["banque"] / fichier
        res = {**ref, "extrait_mdt": "", "page_extraite": "", "unite_extraite": "", "statut": ""}
        attendu = float(ref["valeur_mdt"])
        # contrôle de la référence elle-même : valeur_mdt = valeur_source × facteur de l'unité
        if not proche(float(ref["valeur_source"]) * FACTEURS[ref["unite_source"]], attendu):
            res["statut"] = "REFERENCE INCOHERENTE"
            resultats.append(res)
            continue
        if not chemin.exists():
            res["statut"] = "PDF ABSENT"
            resultats.append(res)
            continue
        if fichier not in extraits:
            lignes, alertes = cb.extraire_pdf(chemin, cb.Trimestre.depuis_texte(ref["trimestre"]), ref["banque"])
            extraits[fichier] = ({(l["code_indicateur"], l["colonne"]): l for l in lignes}, alertes)
        lignes, _ = extraits[fichier]
        l = lignes.get((ref["code_indicateur"], ref["colonne"]))
        if l is None:
            res["statut"] = "NON EXTRAIT"
        else:
            res.update(extrait_mdt=l["valeur_mdt"], page_extraite=l["page"], unite_extraite=l["unite_source"])
            ok = (proche(l["valeur_mdt"], attendu) and str(l["page"]) == ref["page"]
                  and l["unite_source"] == ref["unite_source"])
            res["statut"] = "ok" if ok else "ECART"
        resultats.append(res)
    return resultats


def afficher(resultats: list[dict]):
    entete = f"{'banque':<6} {'trim.':<7} {'indicateur':<10} {'colonne':<12} {'PDF (MDT)':>18} {'extrait (MDT)':>18} {'p.':>3}  statut"
    print(entete)
    print("-" * len(entete))
    for r in resultats:
        extrait = f"{r['extrait_mdt']:,.6f}" if r["extrait_mdt"] != "" else "-"
        print(f"{r['banque']:<6} {r['trimestre']:<7} {r['code_indicateur']:<10} {r['colonne']:<12} "
              f"{float(r['valeur_mdt']):>18,.6f} {extrait:>18} {r['page']:>3}  {r['statut']}")
    n_ok = sum(r["statut"] == "ok" for r in resultats)
    print(f"\n{n_ok}/{len(resultats)} valeurs conformes ({n_ok / len(resultats):.0%}), "
          f"{len({r['fichier'] for r in resultats})} documents.")


def sommes_annuelles(banques=("BIAT", "UIB"), annee=2025) -> list[dict]:
    """Somme des 4 trimestres retenus comparée au cumul T4 retenu, et au cumul T4 initial
    (publié dans le document T4 lui-même). Utilise les PDF de l'année et de l'année suivante."""
    docs = {}
    for b in banques:
        for p in sorted((cb.DOSSIER_PDF / b).glob(f"{b}_*.pdf")):
            tri = p.stem.split("_")[1]
            if tri[:4] in (str(annee), str(annee + 1)):
                lignes, _ = cb.extraire_pdf(p, cb.Trimestre.depuis_texte(tri), b)
                docs[(b, tri)] = (lignes, p.name)
    versions = cb.table_versions(docs)
    initiale = {(r["banque"], r["code_indicateur"]): r["valeur_mdt"] for r in versions
                if r["trimestre"] == f"{annee}T4" and r["mesure"] == "cumul" and r["version"] == "initiale"}
    sortie = []
    for r in cb.controle_somme_annuelle(versions):
        if r["banque"] in banques and r["annee"] == annee and r["code_indicateur"] in ("PNB", "PROD_EXPL", "CHG_EXPL", "CHG_OPER"):
            sortie.append({**r, "cumul_T4_initial": initiale.get((r["banque"], r["code_indicateur"]))})
    return sortie


def test_somme_trimestres_revisee():
    lignes = sommes_annuelles()
    assert len(lignes) == 8, f"{len(lignes)} combinaisons banque × indicateur au lieu de 8"
    for r in lignes:
        # jamais « ecart » : ok, ou « en attente de révision » si le cumul retenu est le 31/12 provisoire
        assert r["statut"] in ("ok", "en attente de révision"), f"{r['banque']} {r['code_indicateur']} : {r}"
        # la somme des trimestres retenus est cohérente avec le cumul T4 publié dans le document T4
        assert abs(r["somme_trimestres"] - r["cumul_T4_initial"]) <= TOLERANCE_SOMME_MDT, \
            f"{r['banque']} {r['code_indicateur']} : somme {r['somme_trimestres']} ≠ cumul T4 initial {r['cumul_T4_initial']}"


def test_valeurs_reference():
    resultats = comparer()
    echecs = [r for r in resultats if r["statut"] != "ok"]
    assert not echecs, "\n".join(
        f"{r['banque']} {r['trimestre']} {r['code_indicateur']} {r['colonne']} : {r['statut']} "
        f"(PDF {r['valeur_mdt']}, extrait {r['extrait_mdt']})" for r in echecs)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    resultats = comparer()
    afficher(resultats)
    print("\n2025, valeurs retenues : somme des 4 trimestres, cumul T4 retenu (source), cumul T4 initial")
    sommes_ok = True
    for r in sommes_annuelles():
        coherent = abs(r["somme_trimestres"] - r["cumul_T4_initial"]) <= TOLERANCE_SOMME_MDT
        sommes_ok &= coherent and r["statut"] != "ecart"
        print(f"  {r['banque']:<5} {r['code_indicateur']:<10} somme {r['somme_trimestres']:>14,.6f} | "
              f"retenu {r['cumul_T4']:>14,.6f} ({r['source_cumul']}) -> {r['statut']} | "
              f"initial {r['cumul_T4_initial']:>14,.6f} écart {r['somme_trimestres'] - r['cumul_T4_initial']:+.6f}")
    sys.exit(0 if all(r["statut"] == "ok" for r in resultats) and sommes_ok else 1)
