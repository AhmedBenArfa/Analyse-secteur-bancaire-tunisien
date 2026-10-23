// Auteur : Ahmed Ben Arfa
// Contrôle de l'extraction (chargée) : une ligne par document trimestriel (12 banques × 28 trimestres),
// avec son statut, le nombre de valeurs lues, les alertes, le fichier et le gabarit de mise en page.
// Page « qualité des données » (spécification 5.1 et 7.8).
let
    Fichier = Fichiers_Donnees{[fichier = "controle_extraction.csv"]}[contenu],
    Source = Csv.Document(Fichier, [Delimiter = ";", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    EnTetes = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Types = Table.TransformColumnTypes(
        EnTetes,
        {
            {"banque", type text}, {"trimestre", type text}, {"statut", type text}, {"nb_valeurs", Int64.Type},
            {"alertes", type text}, {"fichier", type text}, {"gabarit", type text}
        },
        "en-US"
    ),
    VidesEnNull = Table.ReplaceValue(Types, "", null, Replacer.ReplaceValue, {"alertes", "gabarit"}),
    // date d'arrêté calculée à partir du trimestre (« 2024T3 » → 30/09/2024), pour la relier aux dates
    DateArrete = Table.AddColumn(
        VidesEnNull, "date_arrete",
        each Date.EndOfMonth(#date(Number.From(Text.Start([trimestre], 4)), 3 * Number.From(Text.End([trimestre], 1)), 1)),
        type date
    ),
    // nombre d'alertes : elles sont séparées par « | » dans le fichier
    NbAlertes = Table.AddColumn(
        DateArrete, "nb_alertes",
        each if [alertes] = null then 0 else List.Count(Text.Split([alertes], " | ")),
        Int64.Type
    ),
    // colonne conditionnelle : statut en clair, regroupé pour la page qualité
    CategorieStatut = Table.AddColumn(
        NbAlertes, "Categorie_Statut",
        each if [statut] = "ok" then "conforme"
            else if List.Contains({"retraitement possible", "ecart trimestre/cumul", "ecart composantes"}, [statut])
                then "écart signalé (vient de la banque, non bloquant)"
            else if [statut] = "saisie manuelle" then "tableau en image, saisi à la main"
            else if [statut] = "illisible (image)" then "tableau en image, repris du document suivant"
            else if [statut] = "a verifier" then "alerte bloquante (erreur du document vérifiée)"
            else [statut],
        type text
    )
in
    CategorieStatut
