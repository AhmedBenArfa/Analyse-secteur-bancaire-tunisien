// Auteur : Ahmed Ben Arfa
// Contrôle annuel (chargée) : pour chaque banque, année (2020–2025) et indicateur de flux, somme des 4
// trimestres retenus comparée au cumul annuel retenu, avec le statut et, pour chaque écart, sa cause
// (Ecarts_Annuels). Page « qualité des données » (spécification 5.1 et 5.2).
let
    Fichier = Fichiers_Donnees{[fichier = "controle_annuel.csv"]}[contenu],
    Source = Csv.Document(Fichier, [Delimiter = ";", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    EnTetes = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Types = Table.TransformColumnTypes(
        EnTetes,
        {
            {"banque", type text}, {"annee", Int64.Type}, {"code_indicateur", type text},
            {"somme_trimestres", type number}, {"cumul_T4", type number}, {"source_cumul", type text},
            {"ecart", type number}, {"statut", type text}
        },
        "en-US"
    ),
    // écart recalculé ici (la colonne du CSV n'est pas reprise) : somme des trimestres − cumul annuel
    Ecart = Table.AddColumn(
        Table.RemoveColumns(Types, {"ecart"}), "Ecart_MDT", each [somme_trimestres] - [cumul_T4], type number
    ),
    // date de l'exercice (31/12), pour la relier aux dates
    DateArrete = Table.AddColumn(Ecart, "date_arrete", each #date([annee], 12, 31), type date),
    // fusion avec Ecarts_Annuels : la cause de chaque écart (vide pour les autres statuts)
    Fusion = Table.NestedJoin(
        DateArrete, {"banque", "annee", "code_indicateur"},
        Ecarts_Annuels, {"banque", "annee", "code_indicateur"}, "Cause", JoinKind.LeftOuter
    ),
    Developpee = Table.ExpandTableColumn(
        Fusion, "Cause", {"categorie", "cause", "fichier", "page", "correction"},
        {"categorie_ecart", "cause_ecart", "fichier_preuve", "page_preuve", "correction"}
    ),
    // colonne conditionnelle : statut en clair pour la page qualité
    StatutClair = Table.AddColumn(
        Developpee, "Statut_Clair",
        each if [statut] = "ok" then "somme des trimestres = cumul annuel"
            else if [statut] = "en attente de révision" then "en attente du document de l'année suivante"
            else if [statut] = "rupture de série" then "changement de méthode en cours d'année"
            else if [statut] = "ecart" and [categorie_ecart] <> null then "écart expliqué : " & [categorie_ecart]
            else if [statut] = "ecart" then "écart sans cause écrite"
            else [statut],
        type text
    )
in
    StatutClair
