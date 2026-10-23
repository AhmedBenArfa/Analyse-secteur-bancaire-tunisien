// Auteur : Ahmed Ben Arfa
// Requête intermédiaire (non chargée) : cause de chacun des écarts du contrôle annuel (somme des 4
// trimestres retenus ≠ cumul annuel retenu), examinés un à un dans les PDF : catégorie (retraitement de
// la banque, erreur dans le document de la banque, reclassement, arrondi, erreur d'extraction), cause,
// fichier et page de la preuve, correction faite. Fichier versionné docs\ecarts_annuels.csv, lu dans le
// dossier du projet. Controle_Annuel en prend la cause par une fusion.
let
    Source = Csv.Document(
        File.Contents(CheminDonnees & "\docs\ecarts_annuels.csv"),
        [Delimiter = ";", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    EnTetes = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Types = Table.TransformColumnTypes(
        EnTetes,
        {
            {"banque", type text}, {"annee", Int64.Type}, {"code_indicateur", type text},
            {"somme_trimestres", type number}, {"cumul_T4", type number}, {"ecart_mdt", type number},
            {"categorie", type text}, {"cause", type text}, {"fichier", type text}, {"page", Int64.Type},
            {"correction", type text}
        },
        "en-US"
    ),
    // seules la clé et l'explication servent à la fusion (les montants sont recalculés dans Controle_Annuel)
    Colonnes = Table.SelectColumns(
        Types, {"banque", "annee", "code_indicateur", "categorie", "cause", "fichier", "page", "correction"}
    )
in
    Colonnes
