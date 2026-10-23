// Auteur : Ahmed Ben Arfa
// Dimension des banques (chargée) : code, nom, ticker de la Bourse (dim_banque.csv), et actionnariat
// actuel (Banques_Actionnariat, depuis le fichier Excel) : actionnaire de référence, part du capital,
// catégorie (public, groupe étranger, mixte, privé sans contrôle étranger), groupe, date de la source.
let
    Fichier = Fichiers_Donnees{[fichier = "dim_banque.csv"]}[contenu],
    Source = Csv.Document(Fichier, [Delimiter = ";", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    EnTetes = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Types = Table.TransformColumnTypes(
        EnTetes, {{"code_banque", type text}, {"nom", type text}, {"ticker_bvmt", type text}}, "en-US"
    ),
    // les colonnes actionnariat et groupe du CSV sont vides : elles viennent du fichier Excel
    SansColonnesVides = Table.RemoveColumns(Types, {"actionnariat", "groupe"}),
    // ligne en cours de chaque banque : celle dont la période n'a pas de fin
    ActionnariatActuel = Table.SelectRows(Banques_Actionnariat, each [date_fin] = null),
    // fusion avec l'actionnariat actuel (une ligne par banque : sinon la fusion dupliquerait la banque)
    Fusion = Table.NestedJoin(
        SansColonnesVides, {"code_banque"}, ActionnariatActuel, {"code_banque"}, "Actionnariat", JoinKind.LeftOuter
    ),
    Developpee = Table.ExpandTableColumn(
        Fusion, "Actionnariat",
        {"actionnaire_reference", "part_capital_pct", "actionnariat", "groupe", "date_reference"},
        {"actionnaire_reference", "part_capital_pct", "actionnariat", "groupe", "date_actionnariat"}
    )
in
    Developpee
