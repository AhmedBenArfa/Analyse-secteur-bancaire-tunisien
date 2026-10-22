"""Lecture des cours (scripts/cours_boursiers.py) : droits, périodes, bulletins officiels.
Les tests sur les vrais bulletins sont sautés si les PDF ne sont pas téléchargés."""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import cours_boursiers as cbo  # noqa: E402


def test_date_du_droit():
    assert cbo.date_du_droit("BIAT DA1/7 291124") == ("A", 1, 7, dt.date(2024, 11, 29))
    assert cbo.date_du_droit("BT DA 1/5 10052022") == ("A", 1, 5, dt.date(2022, 5, 10))
    assert cbo.date_du_droit("BNA DS 4/5 150419") == ("S", 4, 5, dt.date(2019, 4, 15))
    assert cbo.date_du_droit("TJARIDA4/21 300425") == ("A", 4, 21, dt.date(2025, 4, 30))   # collé au nom
    assert cbo.date_du_droit("BIAT DA32 4/60") is None                                       # sans date
    assert cbo.date_du_droit("Bt Da 3/10 170599")[3] == dt.date(1999, 5, 17)                 # siècle


def test_periodes_trois_mois():
    assert cbo.periodes_trois_mois(dt.date(2026, 1, 1), dt.date(2026, 10, 20)) == [
        (dt.date(2026, 1, 1), dt.date(2026, 3, 31)), (dt.date(2026, 4, 1), dt.date(2026, 6, 30)),
        (dt.date(2026, 7, 1), dt.date(2026, 9, 30)), (dt.date(2026, 10, 1), dt.date(2026, 10, 20))]


def test_archive_colonnes_fixes():
    texte = ("SEANCE      GROUPE CODE   VALEUR               OUVERTURE     CLOTURE\n"
             "---------- ------- ------ ------------------ ----------- -----------\n"
             "02/01/2020      11 180045 BIAT                   113.500     112.510\n")
    r = next(cbo.lignes_archive(texte))
    assert (r["seance"], r["code"], r["valeur"], r["ouverture"], r["cloture"]) == (
        "02/01/2020", "180045", "BIAT", "113.500", "112.510")


# valeurs relevées sur l'image des bulletins (cours de référence, clôture, réservation)
REFERENCES = [
    ("bull20190515.pdf", "BH", {"reference": 12.6, "dividende": 0.6, "date_dividende": "2019-05-15"}),  # « BH - Banque de l'Habitat »
    ("bull20200629.pdf", "BIAT", {"reference": 98.09, "nominal": 10.0}),
    ("bull20210504.pdf", "BIAT", {"reference": 60.87, "nominal": 5.0}),                      # division du nominal
    ("bull20210701.pdf", "BNA", {"reference": 7.12, "date_dividende": "2021-07-01"}),         # date « 01/07/2021 »
    ("bull20220509.pdf", "BIAT", {"reference": 64.5, "ouverture": 66.8, "haut": 66.8, "bas": 64.6, "cloture": 64.6}),
    ("bull20241129.pdf", "BIAT", {"reference": 91.88, "cloture": 94.12}),
    ("bull20251231.pdf", "AB", {"reference": 49.46, "ouverture": 49.48, "dernier": 50.0, "cloture": 50.0}),
    ("bull20260204.pdf", "BTE", {"haut": 3.89, "bas": 3.89, "cloture": 3.72, "reservation": "B"}),
    # tunis-stockexchange.com : « Bull20260923.pdf » ; « 2026-06/BO.pdf » (04/06/2026)
    ("bull20260923.pdf", "BNA", {"reference": 19.75, "ouverture": 19.85, "dernier": 18.72, "haut": 19.85,
                                 "bas": 18.57, "cloture": 18.72, "dividende": 1.15, "date_dividende": "2026-06-15"}),
    ("bull20260923.pdf", "BH", {"cloture": 13.58, "reservation": "B"}),
]


def test_bulletin_20260923_bien_date():
    """ilboursa diffère du bulletin du 23/09/2026 pour 7 banques : le bulletin est bien celui de la
    séance (n° 8928 imprimé entre le 8927 du 22 et le 8929 du 24) et s'enchaîne avec ses voisins :
    référence du jour = clôture de la veille, pour les 12 banques."""
    jours = ("20260922", "20260923", "20260924")
    chemins = [cbo.DOSSIER_BULLETINS / f"bull{j}.pdf" for j in jours]
    if not all(p.exists() for p in chemins):
        pytest.skip("bulletins de septembre 2026 non téléchargés")
    import fitz
    for p, (num, jour) in zip(chemins, [("8927", "mardi 22"), ("8928", "mercredi 23"), ("8929", "jeudi 24")]):
        entete = fitz.open(p)[0].get_text()[:300]
        assert num in entete and f"{jour} septembre 2026" in entete
    veille, jour, lendemain = (cbo.lire_bulletin(p) for p in chemins)
    for b in jour:
        assert jour[b]["reference"] == veille[b]["cloture"]
        assert lendemain[b]["reference"] == jour[b]["cloture"]


@pytest.mark.parametrize("fichier,banque,attendu", REFERENCES)
def test_bulletins(fichier, banque, attendu):
    p = cbo.DOSSIER_BULLETINS / fichier
    if not p.exists():
        pytest.skip(f"{fichier} non téléchargé")
    lu = cbo.lire_bulletin(p)
    assert len(lu) == 12
    assert {k: lu[banque].get(k) for k in attendu} == attendu
