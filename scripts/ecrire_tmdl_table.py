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

Relations et vue Modèle : `ecrire_relations(RELATIONS)` réécrit relationships.tmdl,
`ecrire_diagramme(DIAGRAMME)` réécrit diagramLayout.json (un onglet par thème) ; en ligne de commande,
`python scripts/ecrire_tmdl_table.py relations` ou `diagramme`.
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
    t += [f"\tpartition {nom} = calculated", "\t\tmode: import", "\t\tsource =", *["\t\t\t\t" + l for l in dax], ""]
    f.write_bytes((NL.join(t) + NL).encode("utf-8"))
    ajouter_au_modele(nom)
    print(nom, "écrite (table calculée) :", len(colonnes), "colonnes")


def colonnes_table(table):
    txt = (DEF / "tables" / f"{table}.tmdl").read_bytes().decode("utf-8")
    return set(re.findall(r"^\tcolumn (\S+)", txt, re.M))


def ecrire_relations(relations):
    """Réécrit relationships.tmdl : relations (table du côté plusieurs, colonne, dimension, clé), une
    dimension vers plusieurs lignes, filtre simple (valeurs par défaut du TMDL). Une relation déjà
    présente garde son nom (identifiant) ; chaque colonne doit exister."""
    f = DEF / "relationships.tmdl"
    anciens = {}
    if f.exists():
        txt = f.read_bytes().decode("utf-8")
        for nom, de, vers in re.findall(r"^relationship (\S+)\r\n\tfromColumn: (\S+)\r\n\ttoColumn: (\S+)", txt, re.M):
            anciens[(de, vers)] = nom
    t = []
    for table, col, dim, cle in relations:
        assert col in colonnes_table(table), f"colonne absente : {table}.{col}"
        assert cle in colonnes_table(dim), f"colonne absente : {dim}.{cle}"
        de, vers = f"{table}.{col}", f"{dim}.{cle}"
        t += [f"relationship {anciens.get((de, vers), uuid.uuid4())}", f"\tfromColumn: {de}", f"\ttoColumn: {vers}", ""]
    f.write_bytes((NL.join(t) + NL).encode("utf-8") if t else b"")
    print(len(relations), "relations écrites")


# Relations du modèle en étoile (étape 6, spécification 6)
FAITS_DATES = [("Fait_Indicateurs", "date_arrete"), ("Variations_Comparables", "date_arrete"),
               ("Fait_Etats_Financiers", "date_arrete"), ("Revisions", "date_arrete"),
               ("Revisions_Etats_Financiers", "date_arrete"), ("Controle", "date_arrete"),
               ("Controle_Annuel", "date_arrete"), ("Evenements", "date"), ("Fait_Cours", "date")]
TABLES_BANQUE = [t for t, _ in FAITS_DATES] + ["Definitions_Charges", "Definitions_Capitaux_Propres"]
FAITS_INDICATEURS = [("Fait_Indicateurs", "code_indicateur"), ("Variations_Comparables", "code_indicateur"),
                     ("Revisions", "code_indicateur"), ("Controle_Annuel", "code_indicateur"),
                     ("Evenements", "indicateur"), ("Fait_Etats_Financiers", "code"),
                     ("Revisions_Etats_Financiers", "code")]
RELATIONS = ([(t, c, "Dim_Date", "Date") for t, c in FAITS_DATES]
             + [(t, "banque", "Dim_Banque", "code_banque") for t in TABLES_BANQUE]
             + [("Banques_Actionnariat", "code_banque", "Dim_Banque", "code_banque")]
             + [(t, c, "Dim_Indicateur", "code_indicateur") for t, c in FAITS_INDICATEURS])


def ecrire_diagramme(onglets):
    """Réécrit diagramLayout.json (vue Modèle) : onglets = [(nom, {table: (x, y)})], le premier étant
    « Toutes les tables ». Taille de chaque table : celle que Power BI a enregistrée (300 × 234 sinon).
    JSON indenté de 2 espaces, fins de ligne CRLF, sans fin de ligne finale, comme Power BI."""
    import json
    f = DEF.parent / "diagramLayout.json"
    actuel = json.loads(f.read_bytes().decode("utf-8"))
    tailles = {n["nodeIndex"]: n["size"] for d in actuel["diagrams"] for n in d["nodes"]}
    tags = {p.stem: lineage_existants(p)[0] for p in (DEF / "tables").glob("*.tmdl")}
    diagrammes = []
    for ordinal, (nom, positions) in enumerate(onglets):
        assert set(positions) <= set(tags), f"table inconnue dans l'onglet {nom}"
        noeuds = [{"location": {"x": int(x), "y": int(y)}, "nodeIndex": t, "nodeLineageTag": tags[t],
                   "size": tailles.get(t, {"height": 300, "width": 234}), "zIndex": 0}
                  for t, (x, y) in positions.items()]
        diagrammes.append({"ordinal": ordinal, "scrollPosition": {"x": 0, "y": 0}, "nodes": noeuds, "name": nom,
                           "zoomValue": 80, "pinKeyFieldsToTop": False, "showExtraHeaderInfo": False,
                           "hideKeyFieldsWhenCollapsed": False, "tablesLocked": False})
    assert set(onglets[0][1]) == set(tags), "le premier onglet doit contenir toutes les tables"
    sortie = {"version": actuel["version"], "diagrams": diagrammes,
              "selectedDiagram": onglets[0][0], "defaultDiagram": onglets[0][0]}
    f.write_bytes(json.dumps(sortie, indent=2, ensure_ascii=False).replace("\n", NL).encode("utf-8"))
    print(len(onglets), "onglets écrits :", [n for n, _ in onglets])


# Vue Modèle : faits en haut, dimensions au milieu, qualité en bas ; tables propres aux banques à droite
P = 284   # pas horizontal : largeur d'une table (234) + 50
DIAGRAMME = [
    ("Toutes les tables", {
        "Fait_Indicateurs": (P, 0), "Variations_Comparables": (2 * P, 0), "Fait_Etats_Financiers": (3 * P, 0),
        "Fait_Cours": (4 * P, 0), "Evenements": (5 * P, 0),
        "Dim_Indicateur": (1.5 * P, 420), "Dim_Date": (3 * P, 420), "Dim_Banque": (4.5 * P, 420),
        "Revisions": (P, 820), "Revisions_Etats_Financiers": (2 * P, 820), "Controle": (3 * P, 820),
        "Controle_Annuel": (4 * P, 820),
        "Banques_Actionnariat": (6.5 * P, 220), "Definitions_Charges": (6.5 * P, 560),
        "Definitions_Capitaux_Propres": (6.5 * P, 800)}),
    ("Indicateurs trimestriels", {
        "Fait_Indicateurs": (0, 0), "Variations_Comparables": (P, 0), "Evenements": (2 * P, 0),
        "Dim_Indicateur": (0, 420), "Dim_Date": (P, 420), "Dim_Banque": (2 * P, 420),
        "Definitions_Charges": (3.5 * P, 0), "Definitions_Capitaux_Propres": (3.5 * P, 260),
        "Banques_Actionnariat": (3.5 * P, 460)}),
    ("États financiers", {
        "Fait_Etats_Financiers": (0.5 * P, 0), "Revisions_Etats_Financiers": (1.5 * P, 0),
        "Dim_Indicateur": (0, 420), "Dim_Date": (P, 420), "Dim_Banque": (2 * P, 420)}),
    ("Bourse", {"Fait_Cours": (P, 0), "Dim_Date": (0.5 * P, 420), "Dim_Banque": (1.5 * P, 420)}),
    ("Qualité des données", {
        "Revisions": (0, 0), "Revisions_Etats_Financiers": (P, 0), "Controle": (2 * P, 0),
        "Controle_Annuel": (3 * P, 0),
        "Dim_Indicateur": (0.5 * P, 420), "Dim_Date": (1.5 * P, 420), "Dim_Banque": (2.5 * P, 420)}),
]


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["relations"]:
        ecrire_relations(RELATIONS)
        sys.exit()
    if sys.argv[1:] == ["diagramme"]:
        ecrire_diagramme(DIAGRAMME)
        sys.exit()
    if sys.argv[1:] != ["Dim_Date"]:
        sys.exit("utilisation : python scripts/ecrire_tmdl_table.py Dim_Date | relations | diagramme "
                 "(autres tables : depuis Python)")
    ecrire_table_calculee(
        "Dim_Date",
        "Table des dates (DAX) : un jour par ligne du 01/01/2019 au 31/12/2026, trimestre au format des faits, "
        "période Covid ; marquée comme table de dates",
        [("Date", "date"), ("Annee", "int64"), ("Trimestre", "string"), ("Annee_Trimestre", "string"),
         ("Cle_Trimestre", "int64"), ("Fin_Trimestre", "boolean"), ("Periode", "string"), ("Ordre_Periode", "int64")],
        tri={"Annee_Trimestre": "Cle_Trimestre", "Periode": "Ordre_Periode"},
        cachees=["Cle_Trimestre", "Ordre_Periode"], table_de_dates="Date")
