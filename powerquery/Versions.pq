// Auteur : Ahmed Ben Arfa
// Requête intermédiaire (non chargée) : toutes les versions de chaque valeur des indicateurs trimestriels
// (initiale, révisée par le document suivant, 31/12 provisoire), une ligne par banque × trimestre ×
// indicateur × mesure (trim / cumul) × version. Fait_Indicateurs et Revisions en partent.
let
    Fichier = Fichiers_Donnees{[fichier = "indicateurs_versions.csv"]}[contenu],
    Source = Csv.Document(Fichier, [Delimiter = ";", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    EnTetes = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    // le CSV écrit les décimales avec un point : types appliqués avec les paramètres régionaux en-US
    Types = Table.TransformColumnTypes(
        EnTetes,
        {
            {"banque", type text}, {"trimestre", type text}, {"date_arrete", type date},
            {"annee", Int64.Type}, {"num_trimestre", Int64.Type}, {"code_indicateur", type text},
            {"mesure", type text}, {"version", type text}, {"valeur_mdt", type number},
            {"fichier", type text}, {"page", Int64.Type}, {"valeur_retenue", type number},
            {"source_valeur", type text}, {"ecart_vs_retenue", type number},
            {"statut_revision", type text}, {"note_definition", type text},
            {"mention_retraitement", type text}, {"rupture_serie", type text},
            {"detail_rupture", type text}
        },
        "en-US"
    ),
    // cases vides du CSV (valeur non disponible, pas de note) : null, jamais zéro
    VidesEnNull = Table.ReplaceValue(
        Types, "", null, Replacer.ReplaceValue,
        {"statut_revision", "note_definition", "mention_retraitement", "rupture_serie", "detail_rupture"}
    )
in
    VidesEnNull
