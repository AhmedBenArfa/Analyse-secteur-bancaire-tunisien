// Auteur : Ahmed Ben Arfa
// Variations sur un an (chargée) : pour chaque document, la valeur de la période (valeur_N) et celle
// de la même période un an plus tôt publiée dans le MÊME document (valeur_N1), donc dans la même
// méthode ; une ligne par banque × trimestre × indicateur × mesure (trim / cumul). Source de toutes les
// croissances du rapport : jamais deux documents rapprochés (spécification 5.2 et 7.3).
let
    Fichier = Fichiers_Donnees{[fichier = "variations_comparables.csv"]}[contenu],
    Source = Csv.Document(Fichier, [Delimiter = ";", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    EnTetes = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Types = Table.TransformColumnTypes(
        EnTetes,
        {
            {"banque", type text}, {"trimestre", type text}, {"date_arrete", type date}, {"annee", Int64.Type},
            {"num_trimestre", Int64.Type}, {"code_indicateur", type text}, {"mesure", type text},
            {"valeur_N", type number}, {"valeur_N1", type number}, {"variation_pct", type number},
            {"fichier", type text}, {"page", Int64.Type}, {"mention_retraitement", type text}
        },
        "en-US"
    ),
    VidesEnNull = Table.ReplaceValue(Types, "", null, Replacer.ReplaceValue, {"mention_retraitement"}),
    // fusion avec Dim_Indicateur : nature de chaque indicateur (flux ou stock)
    Fusion = Table.NestedJoin(
        VidesEnNull, {"code_indicateur"}, Dim_Indicateur, {"code_indicateur"}, "Dim_Indicateur", JoinKind.LeftOuter
    ),
    Nature = Table.ExpandTableColumn(Fusion, "Dim_Indicateur", {"nature"}),
    // même règle que Fait_Indicateurs : un stock n'a pas de trimestre seul (colonne conditionnelle + filtre)
    Retenir = Table.AddColumn(
        Nature, "retenir", each if [nature] = "stock" and [mesure] = "trim" then false else true, type logical
    ),
    SansTrimDesStocks = Table.SelectRows(Retenir, each [retenir]),
    // variation recalculée ici (la colonne du CSV n'est pas reprise) : (N − N-1) / |N-1|, pour qu'une hausse
    // reste positive quand la valeur N-1 est négative ; vide si N-1 est nul
    VariationPct = Table.AddColumn(
        SansTrimDesStocks, "Variation_Pct",
        each if [valeur_N1] = null or [valeur_N1] = 0 then null
            else ([valeur_N] - [valeur_N1]) / Number.Abs([valeur_N1]),
        type nullable number
    ),
    // colonnes du CSV inutiles dans le modèle (année et rang du trimestre viendront de la table de dates)
    SansColonnes = Table.RemoveColumns(VariationPct, {"variation_pct", "annee", "num_trimestre", "nature", "retenir"})
in
    SansColonnes
