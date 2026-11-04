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
    for role in d["visual"].get("query", {}).get("queryState", {}).values():
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
    """Filtre du visuel « colonne = valeur » (littéral, ex. "true", ou liste de littéraux : « colonne dans la liste ») ;
    les filtres de mesure du visuel sont retirés (sur un segment, un filtre de mesure tient compte de la sélection du
    segment lui-même et masque les autres valeurs)."""
    valeurs = valeur if isinstance(valeur, list) else [valeur]
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
                       "Values": [[{"Literal": {"Value": v}}] for v in valeurs]}}}]},
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


def tableau_colonnes(page, visuel, colonnes, largeurs):
    """Colonnes d'un tableau : [(table, colonne)] dans l'ordre, filtres du visuel remis à zéro (ceux des anciennes
    colonnes), largeur de chaque colonne en pixels {(table, colonne): largeur}."""
    p = PAGES / page / "visuals" / visuel / "visual.json"
    d = lire(p)
    d["visual"]["query"]["queryState"] = {"Values": {"projections": [
        {"field": {"Column": {"Expression": {"SourceRef": {"Entity": t}}, "Property": c}},
         "queryRef": f"{t}.{c}", "nativeQueryRef": c} for t, c in colonnes]}}
    d["filterConfig"] = {"filters": []}
    d["visual"].setdefault("objects", {})["columnWidth"] = [
        {"properties": {"value": litteral(f"{l}D")}, "selector": {"metadata": f"{t}.{c}"}}
        for (t, c), l in largeurs.items()]
    ecrire(p, d)


def selection_parametre(parametre, mesure, libelle):
    """Filtre d'un segment de paramètre de champ qui choisit une mesure de la table Mesures : condition sur la colonne
    cachée « <paramètre> Champs » (valeur NAMEOF de la mesure), avec les annotations que Power BI y ajoute (forme
    relevée sur un segment enregistré par Power BI ; une condition sur la colonne affichée laisse le segment sur
    « Tout »)."""
    champs = f"{parametre} Champs"
    valeur = [{"Literal": {"Value": "'''Mesures''[" + mesure + "]'"}}]
    def colonne(propriete, source=None):
        ref = {"Source": source} if source else {"Entity": parametre}
        return {"Column": {"Expression": {"SourceRef": ref}, "Property": propriete}}
    return {"Version": 2, "From": [{"Name": "i", "Entity": parametre, "Type": 0}],
            "Where": [{"Condition": {"In": {"Expressions": [colonne(champs, "i")], "Values": [valeur]}},
                       "Annotations": {"filterExpressionMetadata": {
                           "expressions": [colonne(parametre)],
                           "decomposedIdentities": {"values": [[{"0": valeur}]], "columns": [{"value": colonne(champs)}]},
                           "valueMap": [{"0": libelle}]}}}]}


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
    d["visual"]["objects"] = {
        "data": [{"properties": {"mode": texte("Dropdown")}}],
        "header": [{"properties": {"text": texte("Indicateur")}}],
        "selection": [{"properties": {"strictSingleSelect": litteral("true")}}],
        "general": [{"properties": {"filter": {"filter": selection_parametre("Indicateur affiché", "PNB", "PNB")}}}]}
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
    # tableau des révisions de plus de 2 % (ruptures de série), créé par copie du tableau des événements : toutes les
    # banques en ont, alors que les événements datés ne concernent que BH, BNA, BT et UIB
    tableau = "0b0d0fce4ac5c840b305"
    ruptures = copier_visuel(page, tableau, page)
    tableau_colonnes(page, ruptures,
                     [("Fait_Indicateurs", "trimestre"), ("Fait_Indicateurs", "banque"),
                      ("Fait_Indicateurs", "code_indicateur"), ("Fait_Indicateurs", "Detail_Rupture_Cumul")],
                     {("Fait_Indicateurs", "trimestre"): 70, ("Fait_Indicateurs", "banque"): 64,
                      ("Fait_Indicateurs", "code_indicateur"): 76, ("Fait_Indicateurs", "Detail_Rupture_Cumul"): 112})
    regler(page, ruptures, (886, 162, 378, 300),
           {"Fait_Indicateurs.trimestre": "Trimestre", "Fait_Indicateurs.banque": "Banque",
            "Fait_Indicateurs.code_indicateur": "Indicateur", "Fait_Indicateurs.Detail_Rupture_Cumul": "Révision"},
           titre="Révisions de plus de 2 % (ruptures de série)", objets={"values": {"wordWrap": litteral("true")}})
    trier(page, ruptures, "Fait_Indicateurs", "trimestre", genre="Column")
    filtre_colonne(page, ruptures, "Fait_Indicateurs", "Rupture_Cumul", "'oui'", "ruptures")
    filtre_colonne(page, ruptures, "Fait_Indicateurs", "code_indicateur",
                   ["'PNB'", "'FRAIS_PERS'", "'CHG_GEN'", "'CREDITS'", "'DEPOTS'"], "indicateurs_page")
    # largeurs : leur somme reste sous la largeur utile du tableau (environ 325 pixels, barre de défilement verticale comprise), sans barre de défilement
    # horizontale ; tableau des événements : trié par date, description sur plusieurs lignes ; aucun des deux
    # tableaux ne filtre
    # les courbes
    regler(page, tableau, (886, 472, 378, 212),
           {"Evenements.date": "Date", "Evenements.banque": "Banque", "Evenements.description": "Événement",
            "Evenements.montant_mdt": "MDT"},
           titre="Événements datés", objets={"values": {"wordWrap": litteral("true")}})
    trier(page, tableau, "Evenements", "date", genre="Column")
    p = PAGES / page / "visuals" / tableau / "visual.json"
    d = lire(p)
    d["visual"]["objects"]["columnWidth"] = [
        {"properties": {"value": litteral(f"{largeur}D")}, "selector": {"metadata": f"Evenements.{colonne}"}}
        for colonne, largeur in [("date", 80), ("banque", 64), ("description", 122), ("montant_mdt", 48)]]
    ecrire(p, d)
    interactions(page, [(tableau, courbes, "NoFilter"), (ruptures, courbes, "NoFilter")])
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


def ordonner_role(page, visuel, role, ordre):
    """Ordre des champs d'une zone (rôle) d'un visuel : liste de queryRef ; les champs absents de la liste restent à
    la fin."""
    p = PAGES / page / "visuals" / visuel / "visual.json"
    d = lire(p)
    projections = d["visual"]["query"]["queryState"][role]["projections"]
    rang = {q: i for i, q in enumerate(ordre)}
    projections.sort(key=lambda pr: rang.get(pr["queryRef"], len(ordre)))
    ecrire(p, d)


def structure_pnb():
    """Page 4 « Structure du PNB » (guide 4.5)."""
    page = "d2213f796063e0736cf2"
    retirer_extraction(page)
    composantes = {"Mesures.Marge interets": "Marge d'intérêts", "Mesures.Marge commissions": "Marge sur commissions",
                   "Mesures.Revenus portefeuille": "Revenus du portefeuille",
                   "Mesures.Autres elements PNB": "Autres éléments"}
    parts = {"Mesures.Part marge interets": "Part marge d'intérêts", "Mesures.Part commissions": "Part commissions",
             "Mesures.Part portefeuille": "Part portefeuille"}
    # barres à 100 % par banque, triées par part de la marge d'intérêts (de la plus forte à la plus faible)
    barres = "41af035eeb97d3b486b5"
    regler(page, barres, (16, 162, 560, 522), {"Dim_Banque.code_banque": "Banque", **composantes, **parts},
           titre="Structure du PNB par banque (% du PNB du trimestre)")
    trier(page, barres, "Mesures", "Part marge interets", "Descending")
    # histogramme à 100 % du secteur (banques choisies) dans le temps : trimestres publiés, axe des trimestres
    # catégoriel ; le segment du trimestre ne le filtre pas (toute la période reste visible)
    colonnes = "ef7dc89555b391c0e509"
    # 678 pixels de large : à 618, les 28 trimestres ne tenaient pas (une colonne fait au moins 20 pixels ; barre de
    # défilement, 2026T2 et 2026T3 cachés ; une largeur minimale plus petite, preferredCategoryWidth, est ignorée)
    regler(page, colonnes, (586, 162, 678, 330), {"Dim_Date.Annee_Trimestre": "Trimestre", **composantes, **parts},
           titre="Structure du PNB des banques choisies, 2019T4–2026T3",
           objets={"categoryAxis": {"axisType": texte("Categorical")}})
    # « Autres éléments » en gris : la quatrième couleur du thème est un bleu proche de celle de la marge d'intérêts
    for visuel in (barres, colonnes):
        p = PAGES / page / "visuals" / visuel / "visual.json"
        d = lire(p)
        d["visual"].setdefault("objects", {})["dataPoint"] = [{
            "properties": {"fill": {"solid": {"color": litteral("'#9E9E9E'")}}},
            "selector": {"metadata": "Mesures.Autres elements PNB"}}]
        ecrire(p, d)
    trier(page, colonnes, "Dim_Date", "Annee_Trimestre", genre="Column")
    filtre_colonne(page, colonnes, "Dim_Date", "Trimestre_Publie", "true", "trimestres_publies")
    # carte des trois parts au trimestre choisi, dans l'ordre des barres
    carte = "eae558f868b9ecb0908a"
    ordonner_role(page, carte, "Data", list(parts))
    regler(page, carte, (586, 502, 678, 182),
           {"Mesures.Part marge interets": "Marge d'intérêts", "Mesures.Part commissions": "Commissions",
            "Mesures.Part portefeuille": "Portefeuille"},
           titre="Parts du PNB au trimestre choisi")
    interactions(page, [("495183ff62f9d0795f2d", colonnes, "NoFilter")])
    print("Structure du PNB : visuels réglés")


def ligne_constante(page, visuel, nom, valeur, couleur, objet="y1AxisReferenceLine", libelle=True):
    """Ligne constante de l'axe des valeurs (volet Analyse ; objet y1AxisReferenceLine, relevé sur une ligne saisie
    dans Power BI, valeur en nombre : 1 = 100 % pour une mesure en pourcentage), en pointillé, nom affiché sur la
    ligne (sauf libelle=False)."""
    p = PAGES / page / "visuals" / visuel / "visual.json"
    d = lire(p)
    d["visual"].setdefault("objects", {})[objet] = [{
        "properties": {"show": litteral("true"), "displayName": texte(nom), "value": litteral(f"{valeur}D"),
                       "lineColor": {"solid": {"color": litteral(f"'{couleur}'")}},
                       "style": texte("dashed"), "dataLabelShow": litteral("true" if libelle else "false"),
                       "dataLabelText": texte("Name"),
                       "dataLabelColor": {"solid": {"color": litteral(f"'{couleur}'")}}},
        "selector": {"id": "1"}}]
    ecrire(p, d)


def bilan():
    """Page 5 « Bilan » (guide 4.6)."""
    page = "f829ffbfd733d63d36b1"
    retirer_extraction(page)
    # crédits / dépôts par banque, du plus haut au plus bas, étiquettes, ligne à 100 % (crédits = dépôts)
    ratio = "ba585f6394b10e0b05dc"
    regler(page, ratio, (16, 162, 400, 522),
           {"Dim_Banque.code_banque": "Banque", "Mesures.Credits / Depots": "Crédits / dépôts",
            "Mesures.Credits": "Crédits (MDT)", "Mesures.Depots": "Dépôts (MDT)",
            "Mesures.Part de marche credits": "Part des crédits", "Mesures.Part de marche depots": "Part des dépôts",
            "Mesures.Var Credits A/A %": "Crédits sur un an", "Mesures.Var Depots A/A %": "Dépôts sur un an"},
           titre="Crédits / dépôts par banque (pointillé : 100 %)",
           objets={"labels": {"show": litteral("true"), "labelPosition": texte("InsideEnd"),
                              "color": {"solid": {"color": litteral("'#FFFFFF'")}}}})
    # libellé de la ligne masqué (il chevauchait la première barre) ; étiquettes dans le bout des barres, en blanc,
    # pour que la ligne ne les barre pas
    ligne_constante(page, ratio, "100 % : crédits = dépôts", 1, "#C62828", libelle=False)
    trier(page, ratio, "Mesures", "Credits / Depots", "Descending")
    # structure des dépôts à 100 %, triée par part des dépôts à vue
    structure = "5e468efb1020459e6081"
    regler(page, structure, (426, 162, 400, 522),
           {"Dim_Banque.code_banque": "Banque", "Mesures.Depots a vue": "À vue", "Mesures.Depots epargne": "Épargne",
            "Mesures.Depots terme et autres": "Terme et autres", "Mesures.Part depots a vue": "Part des dépôts à vue"},
           titre="Structure des dépôts par banque")
    trier(page, structure, "Mesures", "Part depots a vue", "Descending")
    # encours dans le temps : axe des dates continu, trimestres publiés, sans filtre du segment du trimestre
    courbes = "d320de5203510898aede"
    regler(page, courbes, (836, 162, 428, 330),
           {"Dim_Date.Date": "Fin du trimestre", "Mesures.Credits": "Crédits", "Mesures.Depots": "Dépôts",
            "Mesures.Credits / Depots": "Crédits / dépôts"},
           titre="Crédits et dépôts des banques choisies (MDT)",
           objets={"categoryAxis": {"axisType": texte("Scalar")}})
    filtre_colonne(page, courbes, "Dim_Date", "Trimestre_Publie", "true", "trimestres_publies")
    carte = "aa7ea3d0e40579d7c29d"
    regler(page, carte, (836, 502, 428, 182),
           {"Mesures.Credits / Depots": "Crédits / dépôts", "Mesures.Part depots a vue": "Part des dépôts à vue"},
           titre="Ratios au trimestre choisi")
    interactions(page, [("f7d3d14bf253529e4ae9", courbes, "NoFilter")])
    print("Bilan : visuels réglés")


def bourse():
    """Page 6 « Bourse » (guide 4.7)."""
    page = "ee963f5881561822580f"
    retirer_extraction(page)
    # segment des années en curseur (style « Entre » : déjà le réglage de Power BI pour une colonne de nombres)
    annees = "c83d471420b0d74864d8"
    regler(page, annees, (24, 92, 250, 52),
           objets={"data": {"mode": texte("Between")}, "header": {"text": texte("Années")}})
    # rendement total en base 100 au début de la période, une courbe par banque, axe des dates continu
    courbes = "d7429c44a33684706703"
    regler(page, courbes, (16, 162, 640, 260),
           {"Dim_Date.Date": "Date", "Mesures.Indice rendement total": "Rendement total (base 100)",
            "Dim_Banque.code_banque": "Banque"},
           titre="Rendement total, dividendes réinvestis (base 100 au début de la période)",
           objets={"categoryAxis": {"axisType": texte("Scalar")}})
    # nuage : deux taux annuels sur la même période (2021–2025), sans effet du segment des années
    nuage = "05c968b036168e9a5109"
    regler(page, nuage, (16, 432, 640, 252),
           {"Dim_Banque.code_banque": "Banque", "Mesures.TCAM PNB 2020-2025": "PNB, par an",
            "Mesures.Rendement annuel moyen": "Bourse, par an", "Mesures.Rendement total": "Rendement total",
            "Mesures.Taux seances sans transaction": "Séances sans transaction"},
           titre="Rendement annuel en Bourse et croissance annuelle du PNB, 2021–2025",
           objets={"categoryLabels": {"show": litteral("true")}})
    filtre_colonne(page, nuage, "Dim_Date", "Annee", [f"{a}L" for a in range(2021, 2026)], "annees_2021_2025")
    # tableau : trié par rendement total, liquidité en rouge au-delà de 20 % de séances sans transaction
    tableau = "468f763ed1797d654128"
    # 598 de large (à 478, valeurs et en-têtes sur deux lignes, défilement) ; pas de ligne de total (une somme de
    # performances de banques différentes n'a pas de sens)
    colonnes = [("Dim_Banque.code_banque", "Banque", 60), ("Mesures.Dernier cours", "Cours (DT)", 76),
                ("Mesures.Performance prix", "Prix", 80), ("Mesures.Rendement total", "Total", 84),
                ("Mesures.Rendement annuel moyen", "Par an", 72), ("Mesures.Volatilite annualisee", "Volatilité", 80),
                ("Mesures.Taux seances sans transaction", "Sans transaction", 92)]
    regler(page, tableau, (666, 162, 598, 522), {q: n for q, n, _ in colonnes}, titre="Performance, risque et liquidité",
           objets={"total": {"totals": litteral("false")}})
    p = PAGES / page / "visuals" / tableau / "visual.json"
    d = lire(p)
    d["visual"].setdefault("objects", {})["columnWidth"] = [
        {"properties": {"value": litteral(f"{l}D")}, "selector": {"metadata": q}} for q, _, l in colonnes]
    ecrire(p, d)
    trier(page, tableau, "Mesures", "Rendement total", "Descending")
    couleur_par_mesure(page, tableau, ["Mesures.Taux seances sans transaction"], "Couleur liquidite")
    interactions(page, [(annees, nuage, "NoFilter")])
    print("Bourse : visuels réglés")


def filtre_mesure(page, visuel, mesure, valeur, nom):
    """Filtre du visuel « mesure = valeur » (littéral, ex. "1L") : un visuel sans ligne qui le remplit reste vide."""
    p = PAGES / page / "visuals" / visuel / "visual.json"
    d = lire(p)
    config = d.setdefault("filterConfig", {"filters": []})
    filtres = [f for f in config["filters"] if f.get("name") != nom
               and f["field"] != {"Measure": {"Expression": {"SourceRef": {"Entity": "Mesures"}}, "Property": mesure}}]
    filtres.append({
        "name": nom,
        "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Mesures"}}, "Property": mesure}},
        "type": "Advanced",
        "filter": {"Version": 2, "From": [{"Name": "m", "Entity": "Mesures", "Type": 0}],
                   "Where": [{"Condition": {"Comparison": {
                       "ComparisonKind": 0,
                       "Left": {"Measure": {"Expression": {"SourceRef": {"Source": "m"}}, "Property": mesure}},
                       "Right": {"Literal": {"Value": valeur}}}}}]},
        "howCreated": "User"})
    config["filters"] = filtres
    ecrire(p, d)


def fiche_banque():
    """Page 7 « Fiche banque » (guide 4.8) : page d'extraction sur Dim_Banque[code_banque] (liaison voulue : pas de
    retirer_extraction ici)."""
    page = "2a6222b60b58c809cb35"
    # bouton « Retour » ajouté par Power BI avec l'extraction : dans la bande blanche, à droite du segment du trimestre
    regler(page, "c7bedd76ad2030a06c82", (290, 98, 48, 44))
    regler(page, "ad14d3be7d6017ddee8b", (16, 162, 1248, 110),
           {"Mesures.Banque affichee": "Banque", "Mesures.Chaine de controle": "Chaîne de contrôle",
            "Mesures.Actionnaire principal": "Actionnaire de référence"})
    regler(page, "12cc8472e5b986c92239", (16, 282, 1248, 120),
           {"Mesures.PNB": "PNB du trimestre (MDT)", "Mesures.Coef exploitation harmonise": "Coefficient harmonisé",
            "Mesures.Coef exploitation publie": "Coefficient publié par la banque",
            "Mesures.Credits / Depots": "Crédits / dépôts"})
    # indicateurs dans l'ordre de Dim_Indicateur (libelle trié par ordre)
    indicateurs = "8e30af2040eae71d00db"
    colonnes = [("Dim_Indicateur.libelle", "Indicateur", 300), ("Mesures.Valeur Trim", "Trimestre", 130),
                ("Mesures.Valeur Cumul", "Cumul ou solde", 140), ("Mesures.Var A/A cumul %", "Sur un an", 130)]
    regler(page, indicateurs, (16, 412, 760, 272), {q: n for q, n, _ in colonnes},
           titre="Indicateurs publiés au trimestre (MDT)", objets={"total": {"totals": litteral("false")}})
    p = PAGES / page / "visuals" / indicateurs / "visual.json"
    d = lire(p)
    d["visual"].setdefault("objects", {})["columnWidth"] = [
        {"properties": {"value": litteral(f"{l}D")}, "selector": {"metadata": q}} for q, _, l in colonnes]
    ecrire(p, d)
    trier(page, indicateurs, "Dim_Indicateur", "libelle", genre="Column")
    # définitions propres à la banque, sur plusieurs lignes
    definitions = "fed06e5570531dded83d"
    regler(page, definitions, (786, 412, 478, 272),
           {"Dim_Banque.Definition_Charges_Operatoires": "Charges opératoires publiées",
            "Dim_Banque.Definition_Capitaux_Propres": "Capitaux propres trimestriels"},
           titre="Ce que la banque publie sous ces noms",
           objets={"values": {"wordWrap": litteral("true")}, "total": {"totals": litteral("false")}})
    p = PAGES / page / "visuals" / definitions / "visual.json"
    d = lire(p)
    d["visual"]["objects"]["columnWidth"] = [
        {"properties": {"value": litteral("215D")}, "selector": {"metadata": q}}
        for q in ("Dim_Banque.Definition_Charges_Operatoires", "Dim_Banque.Definition_Capitaux_Propres")]
    ecrire(p, d)
    # sans banque unique (page ouverte par son onglet), chiffres et tableaux vides plutôt que le total des 12 banques ;
    # la carte d'identité reste visible et dit comment ouvrir la fiche
    for visuel in ("12cc8472e5b986c92239", indicateurs, definitions):
        filtre_mesure(page, visuel, "Banque unique", "1L", "banque_unique")
    print("Fiche banque : visuels réglés")


PAGES_REGLEES = {"vue_ensemble": vue_ensemble, "classement": classement, "evolution": evolution,
                 "structure_pnb": structure_pnb, "bilan": bilan, "bourse": bourse, "fiche_banque": fiche_banque}

if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "nouvelle_page":
        nouvelle_page(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 2 and sys.argv[1] in PAGES_REGLEES:
        PAGES_REGLEES[sys.argv[1]]()
    else:
        sys.exit("utilisation : python scripts/ecrire_pbir_visuels.py " + " | ".join(PAGES_REGLEES)
                 + ' | nouvelle_page "<nom>" "<titre>"')
