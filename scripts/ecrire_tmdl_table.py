# Auteur : Ahmed Ben Arfa
"""Ajoute (ou remplace) une table chargée dans le modèle TMDL du projet Power BI (.pbip) : colonnes typées,
partition m = code de powerquery/<Table>.pq, ordre des requêtes (PBI_QueryOrder) et `ref table` dans
model.tmdl. Fins de ligne CRLF, tabulations, UTF-8 sans BOM, comme Power BI. Une table déjà présente
garde ses lineageTag (colonnes de même nom).

À lancer seulement quand ce projet est fermé dans Power BI Desktop (sinon un enregistrement dans Power
BI efface la modification) ; vérifier `git status` avant. Utilisation, depuis Python :

    import sys; sys.path.insert(0, "scripts")
    from ecrire_tmdl_table import ecrire_table
    ecrire_table("Controle", "description", [("banque", "string"), ("date_arrete", "date")], apres="Revisions")

colonnes : liste (nom, type) avec type parmi string, boolean, date, int64, double, pct (format 0.0 %),
decimal2 (format 0.00#) ; tri : {colonne: colonne de tri} ; apres : requête après laquelle la placer
dans l'ordre de Power Query.

Table calculée DAX (étape 6) : `ecrire_table_calculee(nom, description, colonnes, tri, cachees,
table_de_dates)` ; partition `calculated` = code de dax/<Table>.dax, colonnes dont le nom vient de
l'expression (`sourceColumn: [Nom]`), rien dans PBI_QueryOrder (ce n'est pas une requête) ; cachees :
colonnes masquées ; table_de_dates : colonne clé d'une table marquée comme table de dates. En ligne de
commande, `python scripts/ecrire_tmdl_table.py Dim_Date` écrit la table des dates.
"""
import re, uuid
from pathlib import Path

R = Path(__file__).resolve().parent.parent
DEF = R / "powerbi" / "SecteurBancaireTunisien.SemanticModel" / "definition"
NL = "\r\n"


def lineage_existants(f):
    """lineageTag de la table et de ses colonnes si le fichier existe déjà (gardés à la réécriture)."""
    if not f.exists():
        return str(uuid.uuid4()), {}
    txt = f.read_bytes().decode("utf-8")
    anciens = dict(re.findall(r"\tcolumn (\S+)\r\n(?:\t\t.*\r\n)*?\t\tlineageTag: (\S+)", txt))
    return re.search(r"^\tlineageTag: (\S+)", txt, re.M).group(1), anciens


def ajouter_au_modele(nom, apres=None):
    """`ref table` dans model.tmdl ; avec apres, place aussi la requête dans PBI_QueryOrder."""
    m = (DEF / "model.tmdl").read_bytes().decode("utf-8")
    assert m.count("\n") == m.count(NL), "model.tmdl n'est plus en CRLF"
    ordre = re.search(r"annotation PBI_QueryOrder = \[(.*?)\]", m)
    noms = re.findall(r'"([^"]+)"', ordre.group(1))
    if apres and nom not in noms:
        noms.insert(noms.index(apres) + 1, nom)
        m = m.replace(ordre.group(0), "annotation PBI_QueryOrder = [" + ",".join(f'"{n}"' for n in noms) + "]")
    if f"ref table {nom}{NL}" not in m:
        dernier = re.findall(r"ref table \S+\r\n", m)[-1]
        m = m.replace(dernier, dernier + f"ref table {nom}{NL}", 1)
    (DEF / "model.tmdl").write_bytes(m.encode("utf-8"))
    return noms


def ecrire_table(nom, description, colonnes, apres, tri=None):
    tri = tri or {}
    f = DEF / "tables" / f"{nom}.tmdl"
    table_tag, anciens = lineage_existants(f)
    pq = (R / "powerquery" / f"{nom}.pq").read_text(encoding="utf-8").rstrip("\n").split("\n")
    assert all(l.strip() for l in pq), f"ligne vide dans {nom}.pq (interdite dans le TMDL)"
    t = [f"/// {description}", f"table {nom}", f"\tlineageTag: {table_tag}", ""]
    for col, typ in colonnes:
        t += [f"\tcolumn {col}"]
        t += {"date": ["\t\tdataType: dateTime", "\t\tformatString: Short Date"],
              "int64": ["\t\tdataType: int64", "\t\tformatString: 0"],
              "pct": ["\t\tdataType: double", "\t\tformatString: 0.0 %"],
              "decimal2": ["\t\tdataType: double", "\t\tformatString: 0.00#"]}.get(typ, [f"\t\tdataType: {typ}"])
        t += [f"\t\tlineageTag: {anciens.get(col, uuid.uuid4())}", "\t\tsummarizeBy: none", f"\t\tsourceColumn: {col}"]
        if col in tri:
            t += [f"\t\tsortByColumn: {tri[col]}"]
        t += ["", "\t\tannotation SummarizationSetBy = User"]
        if typ == "double":
            t += ["", '\t\tannotation PBI_FormatHint = {"isGeneralNumber":true}']
        if typ == "date":
            t += ["", "\t\tannotation UnderlyingDateTimeDataType = Date"]
        t += [""]
    t += [f"\tpartition {nom} = m", "\t\tmode: import", "\t\tsource =", *["\t\t\t\t" + l for l in pq], "",
          "\tannotation PBI_NavigationStepName = Navigation", "", "\tannotation PBI_ResultType = Table"]
    f.write_bytes((NL.join(t) + NL).encode("utf-8"))
    print(nom, "écrite ; ordre :", ajouter_au_modele(nom, apres))


def ecrire_table_calculee(nom, description, colonnes, tri=None, cachees=(), table_de_dates=None):
    tri = tri or {}
    f = DEF / "tables" / f"{nom}.tmdl"
    table_tag, anciens = lineage_existants(f)
    dax = (R / "dax" / f"{nom}.dax").read_text(encoding="utf-8").rstrip("\n").split("\n")
    assert all(l.strip() for l in dax), f"ligne vide dans {nom}.dax (interdite dans le TMDL)"
    t = [f"/// {description}", f"table {nom}", f"\tlineageTag: {table_tag}"]
    t += ["\tdataCategory: Time", ""] if table_de_dates else [""]
    for col, typ in colonnes:
        t += [f"\tcolumn {col}", f"\t\tdataType: {'dateTime' if typ == 'date' else typ}"]
        t += ["\t\tisKey"] if col == table_de_dates else []
        t += ["\t\tisHidden"] if col in cachees else []
        t += {"date": ["\t\tformatString: Short Date"], "int64": ["\t\tformatString: 0"]}.get(typ, [])
        t += [f"\t\tlineageTag: {anciens.get(col, uuid.uuid4())}", "\t\tsummarizeBy: none", "\t\tisNameInferred",
              f"\t\tsourceColumn: [{col}]"]
        t += [f"\t\tsortByColumn: {tri[col]}"] if col in tri else []
        t += ["", "\t\tannotation SummarizationSetBy = User"]
        t += ["", "\t\tannotation UnderlyingDateTimeDataType = Date"] if typ == "date" else []
        t += [""]
    t += [f"\tpartition {nom} = calculated", "\t\tmode: import", "\t\tsource =", *["\t\t\t\t" + l for l in dax]]
    f.write_bytes((NL.join(t) + NL).encode("utf-8"))
    ajouter_au_modele(nom)
    print(nom, "écrite (table calculée) :", len(colonnes), "colonnes")


if __name__ == "__main__":
    import sys
    if sys.argv[1:] != ["Dim_Date"]:
        sys.exit("utilisation : python scripts/ecrire_tmdl_table.py Dim_Date (autres tables : depuis Python)")
    ecrire_table_calculee(
        "Dim_Date",
        "Table des dates (DAX) : un jour par ligne du 01/01/2019 au 31/12/2026, trimestre au format des faits, "
        "période Covid ; marquée comme table de dates",
        [("Date", "date"), ("Annee", "int64"), ("Trimestre", "string"), ("Annee_Trimestre", "string"),
         ("Cle_Trimestre", "int64"), ("Fin_Trimestre", "boolean"), ("Periode", "string"), ("Ordre_Periode", "int64")],
        tri={"Annee_Trimestre": "Cle_Trimestre", "Periode": "Ordre_Periode"},
        cachees=["Cle_Trimestre", "Ordre_Periode"], table_de_dates="Date")
