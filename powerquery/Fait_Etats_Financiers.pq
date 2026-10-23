// Auteur : Ahmed Ben Arfa
// Table de faits des états financiers (chargée) : résultat net (avant modifications comptables), total de
// l'actif et capitaux propres du bilan des 12 banques, comptes individuels, au 30/06 (2020–2026) et au
// 31/12 (2019–2025) ; une ligne par banque × date × code, valeur retenue (révisée par le document suivant
// quand elle existe). Sert au ROE et au ROA (spécification 7.7).
let
    Fichier = Fichiers_Donnees{[fichier = "etats_financiers_versions.csv"]}[contenu],
    Source = Csv.Document(Fichier, [Delimiter = ";", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    EnTetes = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Types = Table.TransformColumnTypes(
        EnTetes,
        {
            {"banque", type text}, {"date_arrete", type date}, {"type", type text}, {"code", type text},
            {"version", type text}, {"valeur_mdt", type number}, {"fichier", type text}, {"page", Int64.Type},
            {"statut_valeur", type text}, {"valeur_retenue", type number}, {"source_valeur", type text},
            {"statut_revision", type text}, {"ecart_mdt", type number}, {"remarque", type text}
        },
        "en-US"
    ),
    VidesEnNull = Table.ReplaceValue(
        Types, "", null, Replacer.ReplaceValue, {"statut_valeur", "statut_revision", "remarque"}
    ),
    // filtre explicite : seule la version retenue entre dans les faits (même règle que les indicateurs)
    VersionRetenue = Table.SelectRows(VidesEnNull, each [version] = [source_valeur]),
    Colonnes = Table.SelectColumns(
        VersionRetenue,
        {"banque", "date_arrete", "type", "code", "valeur_retenue", "version", "fichier", "page",
         "statut_valeur", "statut_revision", "remarque"}
    ),
    Renommees = Table.RenameColumns(Colonnes, {{"valeur_retenue", "valeur_mdt"}}),
    // colonne conditionnelle : annualisation du résultat net (un semestre × 2, un exercice × 1)
    Annualisation = Table.AddColumn(
        Renommees, "facteur_annualisation", each if [type] = "semestriel" then 2 else 1, Int64.Type
    )
in
    Annualisation
