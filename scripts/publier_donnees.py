# Auteur : Ahmed Ben Arfa
"""Utilisation : python scripts/publier_donnees.py
Régénère le dossier versionné donnees_publiees/ à partir de donnees/ (non versionné) : les CSV
finaux lus par le rapport Power BI, sans aucun PDF ni archive, pour qu'on puisse ouvrir le rapport
après avoir cloné le dépôt.
  - les fichiers sans chemin local sont copiés tels quels (octet pour octet) ;
  - dans les manifestes et le contrôle des états financiers, la colonne `fichier` (chemin absolu
    du PDF sur le poste de collecte) est ramenée au nom du fichier ; ces trois fichiers sont
    réécrits avec le séparateur « ; » et l'encodage UTF-8 avec BOM, comme les autres.
Contrôles avant de terminer (code de sortie 1 sinon) : aucun fichier au-dessus de 50 Mo, aucun
chemin local (lettre de lecteur, dossier utilisateur, nom du poste), chaque fichier décrit dans
donnees_publiees/LISEZMOI.md. Les CSV de donnees_publiees/ absents de la liste sont supprimés.
"""
import csv, os, re, shutil, sys
from pathlib import Path, PureWindowsPath

RACINE = Path(__file__).resolve().parent.parent
SOURCE = RACINE / "donnees"
SORTIE = RACINE / "donnees_publiees"
TAILLE_MAX = 50 * 1024 * 1024

COPIES = [
    "dim_banque.csv", "dim_indicateur.csv",
    "indicateurs_banques_long.csv", "indicateurs_versions.csv", "variations_comparables.csv",
    "controle_extraction.csv", "controle_annuel.csv",
    "etats_financiers_long.csv", "etats_financiers_versions.csv", "verification_ilboursa.csv",
    "cours_banques.csv", "controle_cours.csv",
]
# fichier -> (séparateur d'origine, colonnes contenant un chemin absolu)
NOMS_SEULS = {
    "manifeste_telechargements.csv": (",", ["fichier"]),
    "manifeste_etats_financiers.csv": (",", ["fichier"]),
    "controle_etats_financiers.csv": (";", ["fichier"]),
}


def motif_chemin_local():
    m = [r"(?<![A-Za-z])[A-Za-z]:[\\/]", r"Users[\\/]", r"AppData", re.escape(str(RACINE))]
    m += [re.escape(os.environ[v]) for v in ("USERNAME", "COMPUTERNAME") if len(os.environ.get(v, "")) > 3]
    return re.compile("|".join(m), re.I)


def reecrire(nom, sep, colonnes):
    with open(SOURCE / nom, encoding="utf-8-sig", newline="") as f:
        lignes = list(csv.DictReader(f, delimiter=sep))
    with open(SORTIE / nom, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0]), delimiter=";")
        w.writeheader()
        for l in lignes:
            for c in colonnes:
                l[c] = PureWindowsPath(l[c]).name if l[c] else ""
            w.writerow(l)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    SORTIE.mkdir(exist_ok=True)
    attendus = set(COPIES) | set(NOMS_SEULS)
    manquants = [n for n in sorted(attendus) if not (SOURCE / n).exists()]
    if manquants:
        sys.exit(f"absents de donnees/ (lancer la collecte d'abord) : {', '.join(manquants)}")
    for p in SORTIE.glob("*.csv"):
        if p.name not in attendus:
            p.unlink()
            print("supprimé :", p.name)
    for nom in COPIES:
        shutil.copyfile(SOURCE / nom, SORTIE / nom)
    for nom, (sep, colonnes) in NOMS_SEULS.items():
        reecrire(nom, sep, colonnes)

    chemin, problemes = motif_chemin_local(), []
    lisezmoi = (SORTIE / "LISEZMOI.md").read_text(encoding="utf-8") if (SORTIE / "LISEZMOI.md").exists() else ""
    print(f"{'fichier':34} {'taille':>10} {'lignes':>8}")
    for nom in sorted(attendus):
        p = SORTIE / nom
        texte = p.read_text(encoding="utf-8-sig")
        taille = p.stat().st_size
        print(f"{nom:34} {taille / 1e6:8.2f} Mo {texte.count(chr(10)) - 1:8}")
        if taille > TAILLE_MAX:
            problemes.append(f"{nom} : {taille / 1e6:.1f} Mo (plus de 50 Mo)")
        for i, ligne in enumerate(texte.splitlines(), 1):
            if chemin.search(ligne):
                problemes.append(f"{nom} ligne {i} : chemin local « {chemin.search(ligne).group()} »")
                break
        if f"`{nom}`" not in lisezmoi:
            problemes.append(f"{nom} n'est pas décrit dans LISEZMOI.md")
    if problemes:
        print("\nÉCHEC :\n  " + "\n  ".join(problemes))
        sys.exit(1)
    print(f"\n{len(attendus)} fichiers publiés dans {SORTIE.name}/ : tailles et chemins contrôlés.")


if __name__ == "__main__":
    main()
