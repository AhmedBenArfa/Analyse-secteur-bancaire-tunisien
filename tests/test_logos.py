# Auteur : Ahmed Ben Arfa
"""Logos des banques (donnees_reference/logos) : un PNG par banque de dim_banque.csv, assez léger pour une
image intégrée dans une colonne de Power BI, et une source écrite pour chacun dans le LISEZMOI du dossier."""
import base64, csv
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
LOGOS = RACINE / "donnees_reference" / "logos"


def codes_banques():
    with open(RACINE / "donnees_publiees" / "dim_banque.csv", encoding="utf-8-sig") as f:
        return {ligne["code_banque"] for ligne in csv.DictReader(f, delimiter=";")}


def test_un_logo_par_banque():
    assert {p.stem for p in LOGOS.glob("*.png")} == codes_banques()


def test_logos_legers_et_png():
    for p in LOGOS.glob("*.png"):
        contenu = p.read_bytes()
        assert contenu[:8] == b"\x89PNG\r\n\x1a\n", p.name
        # Power BI coupe les textes de plus de 32 766 caractères : l'adresse data:image/png;base64 doit tenir
        assert len("data:image/png;base64," + base64.b64encode(contenu).decode()) < 32766, p.name


def test_source_de_chaque_logo():
    lisezmoi = (LOGOS / "LISEZMOI.md").read_text(encoding="utf-8")
    assert "propriété de leurs banques respectives" in lisezmoi
    for code in codes_banques():
        assert f"\n| {code} |" in lisezmoi, f"source du logo {code} absente du LISEZMOI"
