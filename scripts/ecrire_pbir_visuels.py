# Auteur : Ahmed Ben Arfa
"""Règle les visuels d'une page du rapport Power BI (format PBIR : un fichier visual.json par visuel) après leur
création dans Power BI Desktop : position et taille, noms affichés des champs, titre, réglages simples (étiquettes de
données, axes), remplacement d'une mesure par une autre, interactions entre visuels (page.json). Fichiers JSON
indentés de 2 espaces, fins de ligne CRLF, sans fin de ligne finale, comme Power BI. Relancer ne change rien.

Méthode (étape 7) : l'utilisateur crée chaque visuel avec ses champs (Power BI écrit un fichier correct), enregistre
et ferme le projet ; ce script applique les réglages décrits dans le guide (section 4) ; l'utilisateur rouvre et
vérifie. À lancer seulement quand ce projet est fermé dans Power BI Desktop ; vérifier `git status` avant.

Utilisation : python scripts/ecrire_pbir_visuels.py vue_ensemble
"""
import json, sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
PAGES = R / "powerbi" / "SecteurBancaireTunisien.Report" / "definition" / "pages"
NL = "\r\n"


def lire(p):
    return json.loads(p.read_bytes().decode("utf-8"))


def ecrire(p, d):
    p.write_bytes(json.dumps(d, indent=2, ensure_ascii=False).replace("\n", NL).encode("utf-8"))


def litteral(v):
    return {"expr": {"Literal": {"Value": v}}}


def texte(s):
    return litteral("'" + s.replace("'", "''") + "'")


def remplacer_champ(page, visuel, table, ancien, nouveau):
    """Remplace un champ (mesure ou colonne de la table) par un autre partout dans le visuel (champ, tri, filtre,
    sélecteurs) ; rien si déjà fait."""
    p = PAGES / page / "visuals" / visuel / "visual.json"
    t = p.read_bytes().decode("utf-8")
    if f'"{table}.{nouveau}"' in t:
        return
    for a, b in [(f'"Property": "{ancien}"', f'"Property": "{nouveau}"'),
                 (f'"{table}.{ancien}"', f'"{table}.{nouveau}"'),
                 (f'"nativeQueryRef": "{ancien}"', f'"nativeQueryRef": "{nouveau}"')]:
        assert a in t, f"{visuel} : {a} introuvable"
        t = t.replace(a, b)
    p.write_bytes(t.encode("utf-8"))


def remplacer_mesure(page, visuel, ancienne, nouvelle):
    remplacer_champ(page, visuel, "Mesures", ancienne, nouvelle)


def titre_etiquette_reference(page, visuel, titre):
    """Titre de l'étiquette de référence d'une carte (cardVisual) : objet referenceLabelTitle, même sélecteur
    (metadata et id) que l'étiquette (referenceLabel) ; nom du réglage relevé sur un titre saisi dans Power BI."""
    p = PAGES / page / "visuals" / visuel / "visual.json"
    d = lire(p)
    objets = d["visual"]["objects"]
    selecteur = objets["referenceLabel"][0]["selector"]
    objets["referenceLabelTitle"] = [{
        "properties": {"titleContentType": texte("custom"), "titleText": texte(titre)},
        "selector": {"metadata": selecteur["metadata"], "id": selecteur["id"]}}]
    ecrire(p, d)


def regler(page, visuel, position, noms=None, titre=None, objets=None):
    """Position (x, y, largeur, hauteur), noms affichés {queryRef: nom}, titre du visuel (son sous-titre automatique
    est masqué), objets {objet: propriétés}."""
    p = PAGES / page / "visuals" / visuel / "visual.json"
    d = lire(p)
    d["position"].update(dict(zip(("x", "y", "width", "height"), position)))
    for role in d["visual"]["query"]["queryState"].values():
        for pr in role["projections"]:
            if noms and pr["queryRef"] in noms:
                pr["displayName"] = noms[pr["queryRef"]]
    if titre is not None:
        conteneur = d["visual"].setdefault("visualContainerObjects", {})
        conteneur["title"] = [{"properties": {"show": litteral("true"), "text": texte(titre)}}]
        conteneur["subTitle"] = [{"properties": {"show": litteral("false")}}]
    for cle, proprietes in (objets or {}).items():
        d["visual"].setdefault("objects", {})[cle] = [{"properties": proprietes}]
    ecrire(p, d)


def filtre_colonne(page, visuel, table, colonne, valeur, nom):
    """Filtre du visuel « colonne = valeur » (littéral, ex. "true") ; les filtres de mesure du visuel sont retirés (sur
    un segment, un filtre de mesure tient compte de la sélection du segment lui-même et masque les autres valeurs)."""
    p = PAGES / page / "visuals" / visuel / "visual.json"
    d = lire(p)
    config = d.setdefault("filterConfig", {"filters": []})
    filtres = [f for f in config["filters"] if "Measure" not in f["field"] and f.get("name") != nom]
    filtres.append({
        "name": nom, "ordinal": len(filtres),
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": colonne}},
        "type": "Categorical",
        "filter": {"Version": 2, "From": [{"Name": "d", "Entity": table, "Type": 0}],
                   "Where": [{"Condition": {"In": {
                       "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": colonne}}],
                       "Values": [[{"Literal": {"Value": valeur}}]]}}}]},
        "howCreated": "User"})
    config["filters"] = filtres
    ecrire(p, d)


def interactions(page, liste):
    """Interactions entre visuels de la page : [(source, cible, type)] ; type NoFilter = aucun effet."""
    p = PAGES / page / "page.json"
    d = lire(p)
    d["visualInteractions"] = [{"source": s, "target": c, "type": t} for s, c, t in liste]
    ecrire(p, d)


def vue_ensemble():
    """Page 1 « Vue d'ensemble » (guide 4.2)."""
    page = "ae07c11e46023397cb08"
    # cartes : valeur en texte mis en forme (la nouvelle carte abrège en milliers), nom affiché, position
    for visuel, mesure in [("bb2acd04ce89e9a8960d", "PNB secteur"), ("4e1fe869218880285ccc", "Credits secteur"),
                           ("86140d4c536a8cbe9777", "Depots secteur")]:
        remplacer_mesure(page, visuel, mesure, mesure + " texte")
    # cartes de 130 de haut (à 110, le libellé au-dessus de la valeur était coupé)
    regler(page, "bb2acd04ce89e9a8960d", (16, 162, 304, 130), {"Mesures.PNB secteur texte": "PNB du trimestre (MDT)"})
    regler(page, "debf00a7b8c4b10106dc", (330, 162, 304, 130), {"Mesures.Coef secteur": "Coefficient d'exploitation"})
    regler(page, "4e1fe869218880285ccc", (644, 162, 304, 130), {"Mesures.Credits secteur texte": "Crédits (MDT)"})
    regler(page, "86140d4c536a8cbe9777", (958, 162, 306, 130), {"Mesures.Depots secteur texte": "Dépôts (MDT)"})
    for visuel, titre in [("bb2acd04ce89e9a8960d", "banques présentes"), ("debf00a7b8c4b10106dc", "médiane des banques"),
                          ("4e1fe869218880285ccc", "sur un an"), ("86140d4c536a8cbe9777", "sur un an")]:
        titre_etiquette_reference(page, visuel, titre)
    regler(page, "85ee3c73c966a8290dd4", (646, 584, 618, 100),
           {"Mesures.Top 3 banques PNB": "Trois premières banques",
            "Mesures.Part 3 premieres banques PNB": "Part du PNB du secteur"})
    # parts de marché : barres triées par part décroissante (réglage de Power BI), étiquettes de données, titre
    regler(page, "fec36675a31e52c8c044", (16, 304, 620, 380),
           {"Mesures.Part de marche PNB": "Part de marché", "Dim_Banque.code_banque": "Banque",
            "Mesures.PNB": "PNB du trimestre (MDT)", "Mesures.Rang PNB": "Rang"},
           titre="Part de marché du PNB", objets={"labels": {"show": litteral("true")}})
    # concentration : date en axe continu (les 28 trimestres tiennent dans la largeur, sans défilement ; un point au
    # dernier jour de chaque trimestre, seules dates où le HHI a une valeur), HHI de 1 000 à 1 300, titre
    remplacer_champ(page, "1c3ebd2e2c48355e47e4", "Dim_Date", "Annee_Trimestre", "Date")
    regler(page, "1c3ebd2e2c48355e47e4", (646, 304, 618, 270),
           {"Dim_Date.Date": "Fin du trimestre", "Mesures.HHI PNB": "Indice HHI",
            "Mesures.Top 3 banques PNB": "Trois premières banques",
            "Mesures.Part 3 premieres banques PNB": "Part des trois premières"},
           titre="Concentration du PNB (indice HHI)",
           objets={"categoryAxis": {"axisType": texte("Scalar")},
                   "valueAxis": {"start": litteral("1000D"), "end": litteral("1300D")}})
    # segment du trimestre : seulement les trimestres publiés (Dim_Date[Trimestre_Publie]), un seul à la fois
    filtre_colonne(page, "fb55d5a1c75e90385c70", "Dim_Date", "Trimestre_Publie", "true", "trimestres_publies")
    p = PAGES / page / "visuals" / "fb55d5a1c75e90385c70" / "visual.json"
    d = lire(p)
    d["visual"]["objects"]["selection"] = [{"properties": {"strictSingleSelect": litteral("true")}}]
    ecrire(p, d)
    # le segment du trimestre ne filtre pas la courbe : toute la période reste visible
    interactions(page, [("fb55d5a1c75e90385c70", "1c3ebd2e2c48355e47e4", "NoFilter")])
    print("Vue d'ensemble : visuels réglés")


PAGES_REGLEES = {"vue_ensemble": vue_ensemble}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in PAGES_REGLEES:
        sys.exit("utilisation : python scripts/ecrire_pbir_visuels.py " + " | ".join(PAGES_REGLEES))
    PAGES_REGLEES[sys.argv[1]]()
