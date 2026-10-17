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
        # jamais « ecart » : ok ; « en attente de révision » si le cumul retenu est le 31/12 provisoire ;
        # « rupture de série » si l'année contient une révision importante (> 2 % sur le cumul)
        assert r["statut"] in ("ok", "en attente de révision", "rupture de série"), \
            f"{r['banque']} {r['code_indicateur']} : {r}"
        # hors rupture, la somme des trimestres retenus est cohérente avec le cumul T4 du document T4
        if r["statut"] != "rupture de série":
            assert abs(r["somme_trimestres"] - r["cumul_T4_initial"]) <= TOLERANCE_SOMME_MDT, \
                f"{r['banque']} {r['code_indicateur']} : somme {r['somme_trimestres']} ≠ cumul T4 initial {r['cumul_T4_initial']}"


def docs_banque(banque: str, trimestres: list[str]) -> dict:
    """(banque, trimestre) -> (lignes, fichier) pour les PDF demandés (présents dans donnees/pdf)."""
    docs = {}
    for p in sorted((cb.DOSSIER_PDF / banque).glob(f"{banque}_*.pdf")):
        tri = p.stem.split("_")[1]
        if tri in trimestres:
            docs[(banque, tri)] = (p, *cb.extraire_pdf(p, cb.Trimestre.depuis_texte(tri), banque))
    return docs


def versions_de(docs: dict) -> list[dict]:
    illisibles = {cle: p.name for cle, (p, lignes, alertes) in docs.items()
                  if not lignes and any(a.startswith(cb.PREFIXE_ILLISIBLE) for a in alertes)}
    return cb.table_versions({cle: (lignes, p.name) for cle, (p, lignes, _) in docs.items()}, illisibles)


def test_document_illisible_bh_2019t4():
    """BH 2019T4 : tableau en image. Version initiale « illisible (image) », valeurs 2019 reprises
    des colonnes N-1 du document BH 2020T4 (« (*) Chiffres retraités »)."""
    docs = docs_banque("BH", ["2019T4", "2020T4"])
    p, lignes, alertes = docs[("BH", "2019T4")]
    assert not lignes and cb.statut_document(lignes, alertes, [], []) == "illisible (image)", alertes
    v = {(r["code_indicateur"], r["mesure"], r["version"]): r for r in versions_de(docs) if r["trimestre"] == "2019T4"}
    # relevé à la main dans BH_2020T4.pdf, page 1, colonnes « 4 EME TRIMESTRE 2019* » et « AU 31/12/2019* »
    for (ind, mesure), attendu in {("PNB", "trim"): 156.644335, ("PNB", "cumul"): 492.928661,
                                   ("CREDITS", "cumul"): 9647.335031}.items():
        r = v[(ind, mesure, "revisee_T4_N+1")]
        assert r["source_valeur"] == "revisee_T4_N+1" and proche(r["valeur_retenue"], attendu), r
        assert v[(ind, mesure, "initiale")]["statut_revision"] == "illisible (image)"
        assert v[(ind, mesure, "initiale")]["valeur_mdt"] is None


def test_revision_importante_bh_2024():
    """Règle des révisions (spécification 5.2, règle 4) : la version révisée est toujours retenue ;
    l'écart se mesure sur le cumul et le statut vaut pour le trimestre et le cumul.
    BH, PNB 2024 : 765 932 kDT (T4 2024) → 701 188 dans le T4 2025 (−8,5 % sur le cumul) :
    revision_importante, révisée retenue, rupture de série sur le T4 2024 (trimestre et cumul).
    BH, PNB 2023 : 670 872 → 665 046 (−0,9 % sur le cumul) mais T4 2023 seul 206 167 → 200 341
    (−2,8 %) : retraitement_mineur pour les deux mesures, puisque seul le cumul compte."""
    docs = docs_banque("BH", ["2023T4", "2024T4", "2025T1", "2025T2", "2025T3", "2025T4"])
    versions = versions_de(docs)

    def lignes(tri, mesure):
        return {r["version"]: r for r in versions
                if r["trimestre"] == tri and r["code_indicateur"] == "PNB" and r["mesure"] == mesure}

    cumul, trim = lignes("2024T4", "cumul"), lignes("2024T4", "trim")
    assert cumul["revisee_T4_N+1"]["statut_revision"] == "retenue"
    assert proche(cumul["revisee_T4_N+1"]["valeur_retenue"], 701.188)
    assert proche(trim["revisee_T4_N+1"]["valeur_retenue"], 177.219)
    assert cumul["initiale"]["statut_revision"] == trim["initiale"]["statut_revision"] == "revision_importante"
    assert cumul["initiale"]["rupture_serie"] == trim["initiale"]["rupture_serie"] == "oui"
    assert cumul["revisee_31-12_T1_N+1"]["statut_revision"] == "revision_importante"   # 744,228 : −2,8 %
    cumul23, trim23 = lignes("2023T4", "cumul"), lignes("2023T4", "trim")
    assert proche(trim23["revisee_T4_N+1"]["valeur_retenue"], 200.341)
    assert cumul23["initiale"]["statut_revision"] == trim23["initiale"]["statut_revision"] == "retraitement_mineur"
    assert not trim23["initiale"]["rupture_serie"]

def test_valeur_corrigee_bt_2020t3():
    """BT, charges opératoires du T3 2020 : 12 076 kDT publiés (don au Fonds 1818 retiré du seul
    trimestre, incohérent avec frais de personnel 15 702 + charges générales 7 724), 26 011 redonnés
    au T3 2021. La version révisée est retenue ; cumul 77 442 → 79 426 (+2,6 %) : revision_importante."""
    docs = docs_banque("BT", ["2020T3", "2021T3"])
    trim = {r["version"]: r for r in versions_de(docs)
            if r["trimestre"] == "2020T3" and r["code_indicateur"] == "CHG_OPER" and r["mesure"] == "trim"}
    assert proche(trim["initiale"]["valeur_mdt"], 12.076)
    assert trim["revisee_T3_N+1"]["statut_revision"] == "retenue"
    assert proche(trim["revisee_T3_N+1"]["valeur_retenue"], 26.011)
    assert trim["initiale"]["statut_revision"] == "revision_importante"


def test_saisies_manuelles():
    """Chaque document saisi à la main (saisies_manuelles.csv : tableaux en image) remplace
    l'extraction et passe les contrôles de cohérence sans alerte bloquante. BTE 2020T2 : PNB
    du semestre 19 668 kDT, relevé sur l'image de la page 1."""
    saisies = cb.charger_saisies()
    assert saisies, "saisies_manuelles.csv vide ou absent"
    for (banque, tri) in saisies:
        chemin = cb.DOSSIER_PDF / banque / f"{banque}_{tri}.pdf"
        if not chemin.exists():
            continue
        lignes, alertes, origine = cb.extraire_document(banque, tri, chemin)
        statut = cb.statut_document(lignes, alertes, [], [], origine)
        assert statut not in ("a verifier", "echec", "illisible (image)"), f"{banque} {tri} : {alertes}"
        saisies_doc = [l for l in lignes if l.get("origine") == cb.ORIGINE_SAISIE]
        assert len(saisies_doc) == len(saisies[(banque, tri)]), f"{banque} {tri} : saisie non utilisée"
        assert all(l["verification"] for l in saisies_doc)
    lignes, _, _ = cb.extraire_document("BTE", "2020T2", cb.DOSSIER_PDF / "BTE" / "BTE_2020T2.pdf")
    v = {(l["code_indicateur"], l["colonne"]): l for l in lignes}
    assert proche(v[("PNB", "cumul_N")]["valeur_mdt"], 19.668) and proche(v[("CHG_OPER", "trim_N")]["valeur_mdt"], 10.701)
    assert v[("PNB", "cumul_N")]["verification"] == "vérifié par Ahmed ben arfa"
    # saisie partielle d'un document lisible : STB 2026T2, revenus du portefeuille superposés au libellé
    lignes, alertes, origine = cb.extraire_document("STB", "2026T2", cb.DOSSIER_PDF / "STB" / "STB_2026T2.pdf")
    v = {(l["code_indicateur"], l["colonne"]): l["valeur_mdt"] for l in lignes}
    assert origine == "" and not alertes
    assert proche(v[("REV_PORTEF", "trim_N")], 130.764489) and proche(v[("REV_PORTEF", "trim_N1")], 115.893522)


def test_seuil_materialite_uib_2025():
    """UIB, PNB 2025 : 522,651 initial (T4 2025), 525,528 au 31/12 du T2 2026 (+0,55 %, document
    annoté « chiffres retraités pour les besoins de comparabilité ») : sous 2 % → retraitement_mineur,
    version révisée retenue malgré la note."""
    docs = docs_banque("UIB", ["2025T4", "2026T1", "2026T2"])
    pnb = {r["version"]: r for r in versions_de(docs)
           if r["trimestre"] == "2025T4" and r["code_indicateur"] == "PNB" and r["mesure"] == "cumul"}
    assert pnb["revisee_31-12_T2_N+1"]["statut_revision"] == "retenue"
    assert proche(pnb["revisee_31-12_T2_N+1"]["valeur_mdt"], 525.528)
    assert pnb["initiale"]["statut_revision"] == "retraitement_mineur", pnb["initiale"]


def test_variations_comparables():
    """Variation sur un an dans un même document : colonne N contre colonne N-1.
    BH 2025T4 : PNB 681 479 contre 701 188 (2024 retraité), colonne « Var » du PDF : -2,8 %.
    ATB 2024T4 : PNB 391 292 contre 357 317, colonne « Evolution » du PDF : 33 975."""
    docs = {**docs_banque("BH", ["2025T4"]), **docs_banque("ATB", ["2024T4"])}
    var = {(r["banque"], r["code_indicateur"], r["mesure"]): r
           for r in cb.variations_comparables({cle: (lignes, p.name) for cle, (p, lignes, _) in docs.items()})}
    bh = var[("BH", "PNB", "cumul")]
    assert proche(bh["valeur_N"], 681.479) and proche(bh["valeur_N1"], 701.188)
    assert round(bh["variation_pct"] * 100, 1) == -2.8
    atb = var[("ATB", "PNB", "cumul")]
    assert proche(atb["valeur_N"] - atb["valeur_N1"], 33.975)


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
        coherent = (r["statut"] == "rupture de série"
                    or abs(r["somme_trimestres"] - r["cumul_T4_initial"]) <= TOLERANCE_SOMME_MDT)
        sommes_ok &= coherent and r["statut"] != "ecart"
        print(f"  {r['banque']:<5} {r['code_indicateur']:<10} somme {r['somme_trimestres']:>14,.6f} | "
              f"retenu {r['cumul_T4']:>14,.6f} ({r['source_cumul']}) -> {r['statut']} | "
              f"initial {r['cumul_T4_initial']:>14,.6f} écart {r['somme_trimestres'] - r['cumul_T4_initial']:+.6f}")
    sys.exit(0 if all(r["statut"] == "ok" for r in resultats) and sommes_ok else 1)
