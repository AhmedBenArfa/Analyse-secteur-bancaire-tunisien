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
"""
import re, uuid
from pathlib import Path

R = Path(__file__).resolve().parent.parent
DEF = R / "powerbi" / "SecteurBancaireTunisien.SemanticModel" / "definition"
NL = "\r\n"


def ecrire_table(nom, description, colonnes, apres, tri=None):
    tri = tri or {}
    f = DEF / "tables" / f"{nom}.tmdl"
    anciens = {}
    if f.exists():
        txt = f.read_bytes().decode("utf-8")
        anciens = dict(re.findall(r"\tcolumn (\S+)\r\n(?:\t\t.*\r\n)*?\t\tlineageTag: (\S+)", txt))
        table_tag = re.search(r"^\tlineageTag: (\S+)", txt, re.M).group(1)
    else:
        table_tag = str(uuid.uuid4())
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

    m = (DEF / "model.tmdl").read_bytes().decode("utf-8")
    assert m.count("\n") == m.count(NL), "model.tmdl n'est plus en CRLF"
    ordre = re.search(r"annotation PBI_QueryOrder = \[(.*?)\]", m)
    noms = re.findall(r'"([^"]+)"', ordre.group(1))
    if nom not in noms:
        noms.insert(noms.index(apres) + 1, nom)
        m = m.replace(ordre.group(0), "annotation PBI_QueryOrder = [" + ",".join(f'"{n}"' for n in noms) + "]")
    if f"ref table {nom}{NL}" not in m:
        dernier = re.findall(r"ref table \S+\r\n", m)[-1]
        m = m.replace(dernier, dernier + f"ref table {nom}{NL}", 1)
    (DEF / "model.tmdl").write_bytes(m.encode("utf-8"))
    print(nom, "écrite ; ordre :", noms)
