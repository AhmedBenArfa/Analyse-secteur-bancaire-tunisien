# Auteur : Ahmed Ben Arfa
"""Outils pour modifier une table déjà écrite par Power BI sans toucher au reste de son fichier TMDL :
ajouter une colonne (avant la partition) et remplacer le code M de la partition par celui de
powerquery/<Table>.pq ; ajouter une fonction personnalisée à expressions.tmdl. Fins de ligne CRLF.

Lancé sans argument, applique le segment d'actionnariat (fait le 23/10/2026) : fonction
Actionnariat_A_La_Date et colonne Segment_Actionnariat de Fait_Indicateurs, Variations_Comparables et
Fait_Etats_Financiers ; ce qui existe déjà n'est pas réécrit (relancer ne change rien).

À lancer seulement quand ce projet est fermé dans Power BI Desktop ; vérifier `git status` avant.

Utilisation : python scripts/ecrire_tmdl_segment.py
Depuis Python : ajouter_colonne(table, colonne, "string"), remplacer_partition(table),
ajouter_fonction(nom, description, apres).
"""
import re, sys, uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ecrire_tmdl_table import DEF, R, NL


def code(nom, tabs):
    lignes = (R / "powerquery" / f"{nom}.pq").read_text(encoding="utf-8").rstrip("\n").split("\n")
    assert all(l.strip() for l in lignes), f"ligne vide dans {nom}.pq (interdite dans le TMDL)"
    return ["\t" * tabs + l for l in lignes]


def lire(p):
    t = p.read_bytes().decode("utf-8")
    assert t.count("\n") == t.count(NL), f"{p.name} n'est plus en CRLF"
    return t


def ajouter_fonction(nom, description, apres):
    """Fonction personnalisée (requête non chargée de type Function) à la fin de expressions.tmdl."""
    f = DEF / "expressions.tmdl"
    t = lire(f)
    if f"expression {nom} =" in t:
        print(nom, "existe déjà : rien à faire")
        return
    bloc = [f"/// {description}", f"expression {nom} =", *code(nom, 2), f"\tlineageTag: {uuid.uuid4()}", "",
            "\tannotation PBI_ResultType = Function", ""]
    f.write_bytes((t.rstrip(NL) + NL + NL + NL.join(bloc)).encode("utf-8"))
    m = lire(DEF / "model.tmdl")
    ordre = re.search(r"annotation PBI_QueryOrder = \[(.*?)\]", m)
    noms = re.findall(r'"([^"]+)"', ordre.group(1))
    if nom not in noms:
        noms.insert(noms.index(apres) + 1, nom)
        m = m.replace(ordre.group(0), "annotation PBI_QueryOrder = [" + ",".join(f'"{n}"' for n in noms) + "]")
        (DEF / "model.tmdl").write_bytes(m.encode("utf-8"))
    print(nom, "ajoutée (fonction)")


def ajouter_colonne(table, colonne, type_tmdl="string"):
    """Colonne ajoutée juste avant la partition (le code M doit la produire : voir remplacer_partition)."""
    p = DEF / "tables" / f"{table}.tmdl"
    t = lire(p)
    if f"\tcolumn {colonne}{NL}" in t:
        print(table, colonne, "existe déjà : rien à faire")
        return
    bloc = [f"\tcolumn {colonne}", f"\t\tdataType: {type_tmdl}", f"\t\tlineageTag: {uuid.uuid4()}",
            "\t\tsummarizeBy: none", f"\t\tsourceColumn: {colonne}", "", "\t\tannotation SummarizationSetBy = User", "", ""]
    i = t.index("\tpartition ")
    p.write_bytes((t[:i] + NL.join(bloc) + t[i:]).encode("utf-8"))
    print(table, colonne, "ajoutée")


def remplacer_partition(table):
    """Code M de la partition remplacé par celui de powerquery/<table>.pq (indenté de 4 tabulations)."""
    p = DEF / "tables" / f"{table}.tmdl"
    lignes = lire(p).split(NL)
    k = lignes.index("\t\tsource =")
    j = k + 1
    while lignes[j].startswith("\t\t\t\t"):
        j += 1
    lignes[k + 1:j] = code(table, 4)
    p.write_bytes(NL.join(lignes).encode("utf-8"))
    print(table, "partition remplacée")


if __name__ == "__main__":
    ajouter_fonction("Actionnariat_A_La_Date",
                     "Fonction : catégorie d'actionnariat d'une banque à une date (périodes de Banques_Actionnariat)",
                     "Dim_Banque")
    for table in ["Fait_Indicateurs", "Variations_Comparables", "Fait_Etats_Financiers"]:
        ajouter_colonne(table, "Segment_Actionnariat")
        remplacer_partition(table)
