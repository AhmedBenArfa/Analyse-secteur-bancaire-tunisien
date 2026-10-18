"""
Test de scripts/etats_financiers.py sur un bilan simulé (aucun téléchargement) : nombres écrits
morceau par morceau (comme UIB), colonne Notes, comptes N et N-1, état de résultat sur une
deuxième page. Le PDF est créé avec PyMuPDF (fitz) ; le test est sauté s'il n'est pas installé.

Utilisation : python -m pytest tests/test_etats_financiers.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "scripts"))

fitz = pytest.importorskip("fitz")
import etats_financiers as ef  # noqa: E402

TAILLE = 8


def droite(page, x_droit: float, y: float, texte: str):
    """Écrit un nombre aligné à droite, un groupe de milliers à la fois (écart de 1,6 pt)."""
    x = x_droit
    for g in reversed(texte.split(" ")):
        w = fitz.get_text_length(g, fontname="helv", fontsize=TAILLE)
        page.insert_text((x - w, y), g, fontname="helv", fontsize=TAILLE)
        x -= w + 1.6


def tableau(page, titre: str, entetes: tuple[str, str], lignes: list[tuple[str, str, str, str]]):
    page.insert_text((60, 80), titre, fontname="helv", fontsize=10)
    page.insert_text((300, 110), "Notes", fontname="helv", fontsize=TAILLE)
    page.insert_text((390, 110), entetes[0], fontname="helv", fontsize=TAILLE)
    page.insert_text((480, 110), entetes[1], fontname="helv", fontsize=TAILLE)
    y = 140
    for lib, note, n, n1 in lignes:
        page.insert_text((60, y), lib, fontname="helv", fontsize=TAILLE)
        if note:
            droite(page, 325, y, note)
        droite(page, 430, y, n)
        droite(page, 520, y, n1)
        y += 16


def test_bilan_simule(tmp_path):
    chemin = tmp_path / "ef_simule.pdf"
    doc = fitz.open()
    tableau(doc.new_page(width=595, height=842), "BILAN ARRETE AU 31 DECEMBRE 2025 (en milliers de dinars)",
            ("31/12/2025", "31/12/2024"), [
                ("AC1 Caisse et avoirs auprès de la BCT", "4.1", "1 234 567", "987 654"),
                ("AC2 Créances sur la clientèle", "4.2", "15 678 901", "14 321 098"),
                ("Total actif", "", "21 345 678", "19 876 543"),
                ("Total passif", "", "18 345 678", "17 076 543"),
                ("Total capitaux propres", "5", "3 000 000", "2 800 000"),
                ("Total capitaux propres et passifs", "", "21 345 678", "19 876 543")])
    tableau(doc.new_page(width=595, height=842), "ETAT DE RESULTAT", ("Exercice 2025", "Exercice 2024"), [
        ("Produit net bancaire", "6.1", "1 595 080", "1 479 714"),
        ("Charges opératoires", "6.2", "(723 987)", "(664 558)"),
        ("Résultat net de l'exercice", "", "612 345", "543 210")])
    doc.save(chemin)
    doc.close()

    trouves, alertes = ef.extraire_pdf(chemin)
    attendu = {"TOTAL_ACTIF": [21345678, 19876543], "CAP_PROPRES_EF": [3000000, 2800000],
               "TOTAL_PASSIF_CP": [21345678, 19876543], "RES_NET": [612345, 543210]}
    for code, valeurs in attendu.items():
        assert trouves.get(code, ([],))[0][:2] == valeurs, (code, trouves.get(code))
    assert not alertes, alertes


# ---------------------------------------------------------------------------
# Vrais documents (téléchargés par « telecharger ») comparés aux valeurs relevées à la main
# sur l'image des pages (tests/valeurs_reference_ef.csv) ; sauté si les PDF sont absents.

REFERENCE_EF = Path(__file__).resolve().parent / "valeurs_reference_ef.csv"


def test_libelles():
    attendu = {
        "Résultat net de l'exercice": "RES_NET",
        "Résultat net de la période (avant modification comptable)": "RES_NET",   # BNA S1 2024
        "Résultat net de la période (après modification comptable)": "RES_NET_APRES_MODIF",
        "Résultat après modification comptable": "RES_NET_APRES_MODIF",            # BNA 2024
        "Effet des modifications comptables (Net d'impôt)": "MODIF_COMPTABLES",
        "Résultat avant impôt": None,
        "Total des capitaux propres V": "CAP_PROPRES_EF",                         # BIAT, renvoi de note
        "Total des produits d'exploitation bancaire VII-1": None,
        "CP6 - Résultat de l'exercice": "RES_EXERCICE",
        "Résultat de l'exer cice": "RES_EXERCICE",                                 # AB 2023, lettres espacées
        "Résultat Net des modifica tions co mptable s": "RES_NET_APRES_MODIF",
        "Effets des modificat ions comp tables": "MODIF_COMPTABLES",
    }
    for libelle, code in attendu.items():
        assert ef.code_ligne(libelle) == code, (libelle, ef.code_ligne(libelle))


def test_valeurs_reference_ef():
    import csv

    with REFERENCE_EF.open(encoding="utf-8-sig") as f:
        refs = list(csv.DictReader(f, delimiter=";"))
    fichiers = sorted({(r["banque"], r["fichier"]) for r in refs})
    absents = [f for b, f in fichiers if not (ef.DOSSIER_PDF / b / f).exists()]
    if absents:
        pytest.skip(f"PDF non téléchargés : {', '.join(absents)}")
    ecarts = []
    for banque, fichier in fichiers:
        trouves, alertes = ef.extraire_pdf(ef.DOSSIER_PDF / banque / fichier)
        assert not any("introuvable" in a or "≠" in a or "hors de la page" in a for a in alertes), (fichier, alertes)
        for r in (r for r in refs if r["fichier"] == fichier):
            vals, _, page = trouves.get(r["code"], ([], "", None))
            i = 0 if r["colonne"] == "N" else 1
            lu = vals[i] if len(vals) > i else None
            if lu != float(r["valeur_source"]) or str(page) != r["page"]:
                ecarts.append((fichier, r["code"], r["colonne"], r["valeur_source"], r["page"], lu, page))
    assert not ecarts, ecarts
