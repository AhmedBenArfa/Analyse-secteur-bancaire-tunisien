"""Utilisation : python scripts/verifier_manifeste.py
Vérifie donnees/manifeste_telechargements.csv (lecture seule) : doublons, statuts, PDF présents
et lisibles pour chaque entrée « ok », URL renseignée, PDF orphelins dans donnees/pdf/.
À lancer après chaque téléchargement (par exemple le T3 2026)."""
import csv
import sys
from collections import Counter
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    manifeste = RACINE / "donnees" / "manifeste_telechargements.csv"
    with manifeste.open(encoding="utf-8") as f:
        lignes = list(csv.DictReader(f))
    print(f"lignes de données : {len(lignes)} ; colonnes : {list(lignes[0].keys())}")
    cles = [(r["banque"], r["trimestre"]) for r in lignes]
    print(f"doublons : {len(cles) - len(set(cles))}")
    print("statuts :", dict(Counter(r["statut"] for r in lignes)))
    print("sources :", dict(Counter(r["source"] for r in lignes if r["statut"] == "ok")))
    banques = sorted({b for b, _ in cles})
    trimestres = sorted({t for _, t in cles})
    print(f"{len(banques)} banques × {len(trimestres)} trimestres = {len(banques) * len(trimestres)} attendus")

    problemes = []
    fichiers_manifeste = set()
    for r in lignes:
        if r["statut"] == "ok":
            p = Path(r["fichier"])
            fichiers_manifeste.add(p.resolve())
            if not p.exists():
                problemes.append(f"ok mais PDF absent : {r['banque']} {r['trimestre']} {p}")
            elif p.read_bytes()[:5] != b"%PDF-":
                problemes.append(f"ok mais fichier non PDF : {p}")
            if not r["url"]:
                problemes.append(f"ok sans URL : {r['banque']} {r['trimestre']}")
        elif r["fichier"]:
            problemes.append(f"{r['statut']} avec un fichier : {r['banque']} {r['trimestre']}")
    presents = {p.resolve() for p in (RACINE / "donnees" / "pdf").rglob("*.pdf")}
    orphelins = presents - fichiers_manifeste
    print(f"PDF présents : {len(presents)} ; référencés « ok » : {len(fichiers_manifeste)} ; orphelins : {len(orphelins)}")
    for p in sorted(orphelins):
        print("  orphelin :", p)
    print("problèmes :", len(problemes))
    for p in problemes:
        print("  ", p)


if __name__ == "__main__":
    main()
