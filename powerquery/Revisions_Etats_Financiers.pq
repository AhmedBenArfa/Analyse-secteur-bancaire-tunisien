// Auteur : Ahmed Ben Arfa
// Versions écartées des états financiers (chargée) : chaque valeur publiée puis remplacée par la colonne
// N-1 du document suivant de même type (ou révisée non retenue : BNA 30/06/2025), avec l'écart à la valeur
// retenue. Page « qualité des données » (spécification 7.7). Complément exact de Fait_Etats_Financiers :
// même fichier, filtre inverse.
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
    // filtre explicite, inverse de celui de Fait_Etats_Financiers : toutes les versions écartées
    VersionsNonRetenues = Table.SelectRows(VidesEnNull, each [version] <> [source_valeur]),
    Colonnes = Table.SelectColumns(
        VersionsNonRetenues,
        {"banque", "date_arrete", "type", "code", "version", "valeur_mdt", "fichier", "page",
         "valeur_retenue", "source_valeur", "statut_revision", "remarque"}
    ),
    // écart calculé ici (la colonne ecart_mdt du CSV n'est pas reprise) : de combien la valeur retenue
    // s'écarte de cette version
    EcartMDT = Table.AddColumn(Colonnes, "Ecart_MDT", each [valeur_retenue] - [valeur_mdt], type nullable number),
    EcartPct = Table.AddColumn(
        EcartMDT, "Ecart_Pct",
        each if [valeur_mdt] = null or [valeur_mdt] = 0 then null else [Ecart_MDT] / Number.Abs([valeur_mdt]),
        type nullable number
    ),
    // colonne conditionnelle : statut de la révision en clair, pour la page qualité
    TypeRevision = Table.AddColumn(
        EcartPct, "Type_Revision",
        each if [statut_revision] = null then "identique à la valeur retenue (arrondi)"
            else if [statut_revision] = "retraitement_mineur" then "retraitement mineur (2 % au plus)"
            else if [statut_revision] = "revision_importante" then "révision importante (plus de 2 %)"
            else if Text.StartsWith([statut_revision], "revisee non retenue") then "révisée non retenue (modification comptable incluse)"
            else [statut_revision],
        type text
    )
in
    TypeRevision
