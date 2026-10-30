# Auteur : Ahmed Ben Arfa
"""Règle les visuels d'une page du rapport Power BI (format PBIR : un fichier visual.json par visuel) après leur
création dans Power BI Desktop : position et taille, noms affichés des champs, titre, réglages simples (étiquettes de
données, axes), remplacement d'une mesure par une autre, interactions entre visuels (page.json). Fichiers JSON
indentés de 2 espaces, fins de ligne CRLF, sans fin de ligne finale, comme Power BI. Relancer ne change rien.

Méthode (étape 7) : l'utilisateur crée chaque visuel avec ses champs (Power BI écrit un fichier correct), enregistre
et ferme le projet ; ce script applique les réglages décrits dans le guide (section 4) ; l'utilisateur rouvre et
vérifie. À lancer seulement quand ce projet est fermé dans Power BI Desktop ; vérifier `git status` avant.

Utilisation : python scripts/ecrire_pbir_visuels.py vue_ensemble
              python scripts/ecrire_pbir_visuels.py nouvelle_page "Classement" "Classement des banques"
(nouvelle page : même fond que la page 1, titre et segment des banques copiés ; l'utilisateur y ajoute les visuels)
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


def nouvelle_page(nom, titre, source="ae07c11e46023397cb08", garder=("00560b6cd900dd5045b6", "434970303466cded6802")):
    """Crée une page à partir de la page source : même taille et même fond, copie des visuels communs (titre, segment
    des banques à logos), texte du titre remplacé ; ajoutée à la fin de pages.json. Rien si une page porte déjà ce nom.
    Les identifiants de la page et des visuels copiés sont neufs (20 caractères hexadécimaux, comme Power BI)."""
    import secrets
    liste = PAGES / "pages.json"
    ordre = lire(liste)
    for page in ordre["pageOrder"]:
        if lire(PAGES / page / "page.json")["displayName"] == nom:
            print(f"page « {nom} » déjà créée : {page}")
            return page
    page = secrets.token_hex(10)
    d = lire(PAGES / source / "page.json")
    d["name"], d["displayName"] = page, nom
    d.pop("visualInteractions", None)
    (PAGES / page / "visuals").mkdir(parents=True)
    ecrire(PAGES / page / "page.json", d)
    for visuel in garder:
        v = lire(PAGES / source / "visuals" / visuel / "visual.json")
        v["name"] = secrets.token_hex(10)
        if v["visual"]["visualType"] == "textbox":
            v["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]["value"] = titre
        (PAGES / page / "visuals" / v["name"]).mkdir()
        ecrire(PAGES / page / "visuals" / v["name"] / "visual.json", v)
    ordre["pageOrder"].append(page)
    ordre["activePageName"] = page  # le projet s'ouvre sur la nouvelle page
    ecrire(liste, ordre)
    print(f"page « {nom} » créée : {page}")
    return page


def retirer_extraction(page):
    """Retire une extraction (drillthrough) posée par erreur sur une page : liaison de page, filtre d'extraction et
    bouton « Retour » ajouté par Power BI ; rien s'il n'y en a pas."""
    p = PAGES / page / "page.json"
    d = lire(p)
    d.pop("pageBinding", None)
    if "filterConfig" in d:
        d["filterConfig"]["filters"] = [f for f in d["filterConfig"]["filters"] if f.get("howCreated") != "Drillthrough"]
        if not d["filterConfig"]["filters"]:
            del d["filterConfig"]
    ecrire(p, d)
    for f in (PAGES / page / "visuals").glob("*/visual.json"):
        v = lire(f)
        lien = v["visual"].get("visualContainerObjects", {}).get("visualLink", [{}])[0].get("properties", {})
        if v["visual"]["visualType"] == "actionButton" and lien.get("type") == texte("Back"):
            f.unlink()
            f.parent.rmdir()


def trier(page, visuel, table, champ, sens="Ascending", genre="Measure"):
    """Tri par défaut du visuel sur une mesure (genre « Measure ») ou une colonne (« Column ») ; sens « Ascending » ou
    « Descending »."""
    p = PAGES / page / "visuals" / visuel / "visual.json"
    d = lire(p)
    d["visual"]["query"]["sortDefinition"] = {"sort": [{
        "field": {genre: {"Expression": {"SourceRef": {"Entity": table}}, "Property": champ}},
        "direction": sens}], "isDefaultSort": True}
    ecrire(p, d)


def couleur_par_mesure(page, visuel, colonnes, mesure):
    """Couleur de police des colonnes d'un tableau = valeur de la mesure (mise en forme conditionnelle « valeur du
    champ » ; forme relevée sur une mise en forme saisie dans Power BI)."""
    p = PAGES / page / "visuals" / visuel / "visual.json"
    d = lire(p)
    d["visual"].setdefault("objects", {})["values"] = [{
        "properties": {"fontColor": {"solid": {"color": {"expr": {
            "Measure": {"Expression": {"SourceRef": {"Entity": "Mesures"}}, "Property": mesure}}}}}},
        "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": colonne}}
        for colonne in colonnes]
    ecrire(p, d)


def copier_visuel(source, visuel, page):
    """Copie un visuel d'une page dans une autre (même position, mêmes réglages, sélection d'un segment comprise) ;
    identifiant neuf tiré des deux identifiants, donc stable : rien si la copie existe déjà. Renvoie l'identifiant."""
    import hashlib
    nom = hashlib.md5((page + visuel).encode()).hexdigest()[:20]
    cible = PAGES / page / "visuals" / nom / "visual.json"
    if not cible.exists():
        v = lire(PAGES / source / "visuals" / visuel / "visual.json")
        v["name"] = nom
        cible.parent.mkdir()
        ecrire(cible, v)
    return nom


def supprimer_visuel(page, visuel):
    """Supprime un visuel de la page ; rien s'il n'existe plus."""
    f = PAGES / page / "visuals" / visuel / "visual.json"
    if f.exists():
        f.unlink()
        f.parent.rmdir()


def ajouter_colonne_role(page, visuel, role, table, colonne):
    """Ajoute une colonne dans une zone (rôle) d'un visuel, par exemple l'axe de lecture « Play » d'un nuage de
    points ; rien si elle y est déjà."""
    p = PAGES / page / "visuals" / visuel / "visual.json"
    d = lire(p)
    projections = d["visual"]["query"]["queryState"].setdefault(role, {"projections": []})["projections"]
    if not any(pr["queryRef"] == f"{table}.{colonne}" for pr in projections):
        projections.append({"field": {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": colonne}},
                            "queryRef": f"{table}.{colonne}", "nativeQueryRef": colonne, "active": True})
    ecrire(p, d)


def classement():
    """Page 2 « Classement » (guide 4.3)."""
    page = "70c29bcb7212072d3d78"
    retirer_extraction(page)
    # le visuel Play Axis démarre sans trimestre choisi et efface sa sélection en fin de lecture (page vide) :
    # remplacé par le segment du trimestre de la page 1 (« Dernier trimestre complet ») et par l'axe de lecture
    # intégré au nuage de points
    supprimer_visuel(page, "b6865abd3591c07d0656")
    segment = copier_visuel("ae07c11e46023397cb08", "fb55d5a1c75e90385c70", page)
    regler(page, segment, (24, 92, 250, 52))
    # cartes de 130 de haut (à 100, le libellé de la carte avec étiquette de référence était coupé, comme en page 1)
    regler(page, "b9106fd5eec51c3d7967", (16, 162, 365, 130), {"Mesures.Trimestre affiche": "Trimestre affiché"})
    regler(page, "997bf12c95589026ae69", (391, 162, 365, 130), {"Mesures.Coef mediane": "Médiane des coefficients"})
    titre_etiquette_reference(page, "997bf12c95589026ae69", "coefficient du secteur")
    # tableau : trié par rang du PNB, coefficient et écart à la médiane colorés par Couleur coef ; logos de 24 pixels
    # de haut (à la taille d'origine, une ligne par logo de 120 pixels : 4 banques visibles), en-têtes courts (sans
    # barre de défilement horizontale)
    tableau = "a65d1a3a157cddcdd761"
    regler(page, tableau, (16, 302, 740, 382),
           {"Dim_Banque.icone": "Logo", "Dim_Banque.code_banque": "Banque", "Mesures.PNB": "PNB (MDT)",
            "Mesures.Part de marche PNB": "Part du PNB", "Mesures.Rang PNB": "Rang PNB",
            "Mesures.Coef exploitation harmonise": "Coefficient", "Mesures.Rang coef": "Rang coef.",
            "Mesures.Ecart coef / mediane": "Écart médiane", "Mesures.Var PNB A/A %": "PNB A/A"},
           titre="Classement des banques au trimestre", objets={"grid": {"imageHeight": litteral("24D")}})
    trier(page, tableau, "Mesures", "Rang PNB")
    couleur_par_mesure(page, tableau, ["Mesures.Coef exploitation harmonise", "Mesures.Ecart coef / mediane"],
                       "Couleur coef")
    # nuage : croissance du PNB sur un an (X) et coefficient (Y), taille = PNB, code de la banque sur chaque point ;
    # axe de lecture sur les trimestres publiés, sans filtre du segment du trimestre (il anime toute la période)
    nuage = "e292731dbd42b887618d"
    ajouter_colonne_role(page, nuage, "Play", "Dim_Date", "Annee_Trimestre")
    regler(page, nuage, (766, 162, 498, 522),
           {"Dim_Banque.code_banque": "Banque", "Mesures.Var PNB A/A %": "PNB sur un an",
            "Mesures.Coef exploitation harmonise": "Coefficient d'exploitation", "Mesures.PNB": "PNB (MDT)",
            "Mesures.Rang PNB": "Rang PNB", "Mesures.Rang coef": "Rang coef.", "Dim_Date.Annee_Trimestre": "Trimestre"},
           titre="Croissance du PNB et coefficient (▶ : les trimestres)",
           objets={"categoryLabels": {"show": litteral("true")}})
    filtre_colonne(page, nuage, "Dim_Date", "Trimestre_Publie", "true", "trimestres_publies")
    interactions(page, [(segment, nuage, "NoFilter")])
    print("Classement : visuels réglés")


def lignes_verticales(page, visuel, lignes):
    """Lignes constantes de l'axe X d'un graphique à axe de dates continu : [(nom, date AAAA-MM-JJ, couleur)], avec
    leur nom affiché au-dessus de la ligne."""
    p = PAGES / page / "visuals" / visuel / "visual.json"
    d = lire(p)
    d["visual"].setdefault("objects", {})["xAxisReferenceLine"] = [{
        "properties": {"show": litteral("true"), "displayName": texte(nom),
                       "value": litteral(f"datetime'{jour}T00:00:00'"),
                       "lineColor": {"solid": {"color": litteral(f"'{couleur}'")}},
                       "style": texte("dashed"), "dataLabelShow": litteral("true"), "dataLabelText": texte("Name"),
                       "dataLabelColor": {"solid": {"color": litteral(f"'{couleur}'")}}},
        "selector": {"id": str(i)}} for i, (nom, jour, couleur) in enumerate(lignes, 1)]
    ecrire(p, d)


def evolution():
    """Page 3 « Évolution 2020–2026 » (guide 4.4)."""
    page = "0c8acf6d4b5f09a619a9"
    retirer_extraction(page)
    # sélecteur d'indicateur (paramètre de champ) à la place du segment du trimestre : liste déroulante, un seul
    # indicateur à la fois, « PNB » au départ
    selecteur = "3891b1531292597b0c66"
    regler(page, selecteur, (24, 92, 250, 52))
    p = PAGES / page / "visuals" / selecteur / "visual.json"
    d = lire(p)
    colonne = {"Column": {"Expression": {"SourceRef": {"Source": "i"}}, "Property": "Indicateur affiché"}}
    d["visual"]["objects"] = {
        "data": [{"properties": {"mode": texte("Dropdown")}}],
        "header": [{"properties": {"text": texte("Indicateur")}}],
        "selection": [{"properties": {"strictSingleSelect": litteral("true")}}],
        "general": [{"properties": {"filter": {"filter": {
            "Version": 2, "From": [{"Name": "i", "Entity": "Indicateur affiché", "Type": 0}],
            "Where": [{"Condition": {"In": {"Expressions": [colonne], "Values": [[{"Literal": {"Value": "'PNB'"}}]]}}}]}}}}]}
    ecrire(p, d)
    # courbes : axe des dates continu (un point par trimestre), trimestres publiés, période Covid en lignes verticales
    courbes = "eb2a6b4104abab1272ea"
    regler(page, courbes, (16, 162, 860, 522),
           {"Dim_Date.Date": "Fin du trimestre", "Dim_Banque.code_banque": "Banque",
            "Mesures.Evenement texte": "Événements", "Mesures.Ruptures texte": "Ruptures de série"},
           titre="Évolution par banque (lignes : début et fin de la période Covid)",
           objets={"categoryAxis": {"axisType": texte("Scalar")}})
    lignes_verticales(page, courbes, [("Début Covid", "2020-03-01", "#C62828"), ("Fin Covid", "2022-01-01", "#2E7D32")])
    filtre_colonne(page, courbes, "Dim_Date", "Trimestre_Publie", "true", "trimestres_publies")
    # tableau des événements : trié par date, description sur plusieurs lignes, sans effet sur les courbes
    tableau = "0b0d0fce4ac5c840b305"
    regler(page, tableau, (886, 162, 378, 522),
           {"Evenements.date": "Date", "Evenements.banque": "Banque", "Evenements.description": "Événement",
            "Evenements.montant_mdt": "MDT"},
           titre="Événements qui expliquent un saut", objets={"values": {"wordWrap": litteral("true")}})
    trier(page, tableau, "Evenements", "date", genre="Column")
    p = PAGES / page / "visuals" / tableau / "visual.json"
    d = lire(p)
    d["visual"]["objects"]["columnWidth"] = [
        {"properties": {"value": litteral(f"{largeur}D")}, "selector": {"metadata": f"Evenements.{colonne}"}}
        for colonne, largeur in [("date", 70), ("banque", 50), ("description", 180), ("montant_mdt", 50)]]
    ecrire(p, d)
    interactions(page, [(tableau, courbes, "NoFilter")])
    print("Évolution : visuels réglés")


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


PAGES_REGLEES = {"vue_ensemble": vue_ensemble, "classement": classement, "evolution": evolution}

if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "nouvelle_page":
        nouvelle_page(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 2 and sys.argv[1] in PAGES_REGLEES:
        PAGES_REGLEES[sys.argv[1]]()
    else:
        sys.exit("utilisation : python scripts/ecrire_pbir_visuels.py " + " | ".join(PAGES_REGLEES)
                 + ' | nouvelle_page "<nom>" "<titre>"')
