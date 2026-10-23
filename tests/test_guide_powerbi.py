# Auteur : Ahmed Ben Arfa
"""Le guide Power BI (docs/guide_powerbi.md, section 2.13) explique chaque fonction M employée dans les
requêtes powerquery/*.pq : une fonction ajoutée à une requête sans explication fait échouer ce test."""
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent


def fonctions_utilisees():
    usage = {}
    for p in sorted((RACINE / "powerquery").glob("*.pq")):
        lignes = [l for l in p.read_text(encoding="utf-8").split("\n") if not l.strip().startswith("//")]
        code = re.sub(r'"[^"]*"', '""', "\n".join(lignes))      # rien dans les textes entre guillemets
        code = re.sub(r"//.*", "", code)                          # commentaires en fin de ligne
        for f in re.findall(r"\b([A-Z][A-Za-z]+\.[A-Z][A-Za-z]+)\b", code):
            usage.setdefault(f, set()).add(p.stem)
    return usage


def test_chaque_fonction_m_est_expliquee():
    guide = (RACINE / "docs" / "guide_powerbi.md").read_text(encoding="utf-8")
    section = guide.split("### 2.13", 1)[1].split("\n## ", 1)[0]
    documentees = set(re.findall(r"^\| `([A-Za-z]+\.[A-Za-z]+)` \|", section, re.M))
    utilisees = fonctions_utilisees()
    manquantes = sorted(set(utilisees) - documentees)
    assert not manquantes, f"fonctions M sans explication dans le guide (section 2.13) : {manquantes}"
    assert len(utilisees) >= 30


def fonctions_dax_utilisees():
    usage = {}
    for p in sorted((RACINE / "dax").glob("*.dax")):
        code = re.sub(r"//.*|--.*", "", p.read_text(encoding="utf-8"))   # commentaires
        code = re.sub(r'"[^"]*"', '""', code)                             # textes entre guillemets
        for f in re.findall(r"\b([A-Z][A-Z0-9.]+)\s*\(", code):
            usage.setdefault(f, set()).add(p.stem)
    return usage


def test_chaque_fonction_dax_est_expliquee():
    guide = (RACINE / "docs" / "guide_powerbi.md").read_text(encoding="utf-8")
    section = guide.split("### 3.9", 1)[1].split("\n## ", 1)[0]
    documentees = set()
    for cellule in re.findall(r"^\| ([^|]+) \|", section, re.M):
        documentees |= set(re.findall(r"`([A-Z][A-Z0-9.]+)`", cellule))
    utilisees = fonctions_dax_utilisees()
    manquantes = sorted(set(utilisees) - documentees)
    assert not manquantes, f"fonctions DAX sans explication dans le guide (section 3.9) : {manquantes}"
    assert "CALENDAR" in utilisees
