"""Vérification à la main d'un document saisi (saisies_manuelles.csv).

  python scripts/verification_saisie.py preparer BTE 2020T2
      écrit donnees/verification/BTE_2020T2_a_verifier.csv (une ligne par valeur saisie, avec le
      libellé de la ligne et de la colonne du PDF) et les images du tableau (BTE_2020T2_1.png,
      BTE_2020T2_2.png) ; remplir la colonne « verification » des valeurs contrôlées sur l'image.
  python scripts/verification_saisie.py reporter BTE 2020T2
      recopie dans saisies_manuelles.csv la colonne « verification » non vide du fichier rempli ;
      une valeur corrigée dans la colonne « valeur_corrigee » est signalée, jamais recopiée seule.
"""
import csv
import sys
from pathlib import Path

import pdfplumber

RACINE = Path(__file__).resolve().parent.parent
SAISIES = RACINE / "saisies_manuelles.csv"
DOSSIER = RACINE / "donnees" / "verification"
LIGNES_PDF = {"PROD_EXPL": "Produits d'exploitation bancaire", "CHG_EXPL": "Charges d'exploitation bancaire",
              "PNB": "Produit Net Bancaire", "CHG_OPER": "Charges opératoires", "FRAIS_PERS": "Frais de personnel",
              "CHG_GEN": "Charges générales", "CREDITS": "Encours nets de crédits", "DEPOTS": "Encours des dépôts"}
COLONNES_PDF = {"trim_N": "trimestre de l'année", "trim_N1": "même trimestre de l'année précédente",
                "cumul_N": "cumul (ou solde) à la date", "cumul_N1": "cumul (ou solde) un an plus tôt",
                "exercice_N1": "au 31/12 de l'année précédente"}


def lire(chemin: Path) -> tuple[list[str], list[dict]]:
    with chemin.open(encoding="utf-8-sig") as f:
        lecteur = csv.DictReader(f, delimiter=";")
        return list(lecteur.fieldnames), list(lecteur)


def preparer(banque: str, tri: str):
    _, saisies = lire(SAISIES)
    lignes = [r for r in saisies if r["banque"] == banque and r["trimestre"] == tri]
    if not lignes:
        sys.exit(f"Aucune saisie pour {banque} {tri}.")
    DOSSIER.mkdir(parents=True, exist_ok=True)
    sortie = DOSSIER / f"{banque}_{tri}_a_verifier.csv"
    with sortie.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["fichier", "page", "ligne_du_pdf", "colonne_du_pdf", "code_indicateur", "colonne",
                    "valeur_saisie_milliers", "verification", "valeur_corrigee"])
        for r in lignes:
            w.writerow([r["fichier"], r["page"], LIGNES_PDF.get(r["code_indicateur"], r["code_indicateur"]),
                        COLONNES_PDF[r["colonne"]], r["code_indicateur"], r["colonne"],
                        f"{float(r['valeur_source']):,.0f}".replace(",", " "), "", ""])
    pdf_chemin = RACINE / "donnees" / "pdf" / banque / lignes[0]["fichier"]
    with pdfplumber.open(pdf_chemin) as pdf:
        p = pdf.pages[int(lignes[0]["page"]) - 1]
        haut = min((im["top"] for im in p.images), default=150)
        bas = max((im["bottom"] for im in p.images), default=p.height - 40)
        milieu = (haut + bas) / 2
        for i, (a, b) in enumerate([(haut - 5, milieu + 12), (milieu - 12, bas + 5)], start=1):
            p.crop((0, max(0, a), p.width, min(p.height, b))).to_image(resolution=220) \
                .save(DOSSIER / f"{banque}_{tri}_{i}.png")
    print(f"{len(lignes)} valeurs à vérifier : {sortie}\nImages : {DOSSIER / f'{banque}_{tri}_1.png'} et _2.png")


def reporter(banque: str, tri: str):
    _, verifs = lire(DOSSIER / f"{banque}_{tri}_a_verifier.csv")
    marques = {(v["code_indicateur"], v["colonne"]): v for v in verifs if v["verification"].strip()}
    corrigees = [v for v in verifs if v["valeur_corrigee"].strip()]
    champs, saisies = lire(SAISIES)
    n = 0
    for r in saisies:
        v = marques.get((r["code_indicateur"], r["colonne"]))
        if r["banque"] == banque and r["trimestre"] == tri and v:
            r["verification"] = v["verification"].strip()
            n += 1
    with SAISIES.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=champs, delimiter=";")
        w.writeheader()
        w.writerows(saisies)
    print(f"{n} valeur(s) marquée(s) dans {SAISIES.name}.")
    for v in corrigees:
        print(f"  valeur corrigée à reprendre : {v['code_indicateur']} {v['colonne']} saisie {v['valeur_saisie_milliers']}"
              f" → {v['valeur_corrigee']} (non recopiée : à corriger dans saisies_manuelles.csv, puis contrôles)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 4 or sys.argv[1] not in ("preparer", "reporter"):
        sys.exit(__doc__)
    {"preparer": preparer, "reporter": reporter}[sys.argv[1]](sys.argv[2], sys.argv[3])
