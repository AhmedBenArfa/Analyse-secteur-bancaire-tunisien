// Auteur : Ahmed Ben Arfa
// Requête intermédiaire (non chargée) : gabarits de mise en page des documents de chaque banque
// (gabarits.csv, versionné à la racine, lu dans le dossier du projet) : période, colonnes, unité, et
// définitions des charges opératoires et des capitaux propres trimestriels de la banque.
// Definitions_Charges et Definitions_Capitaux_Propres en partent.
let
    // 11 colonnes : la remarque (dernière colonne) contient parfois un « ; », le reste est ignoré
    Source = Csv.Document(
        File.Contents(CheminDonnees & "\gabarits.csv"),
        [Delimiter = ";", Columns = 11, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    EnTetes = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Colonnes = Table.SelectColumns(
        EnTetes,
        {"banque", "premier_trimestre", "dernier_trimestre", "definition_charges_operatoires",
         "definition_capitaux_propres"}
    ),
    Types = Table.TransformColumnTypes(
        Colonnes,
        {{"banque", type text}, {"premier_trimestre", type text}, {"dernier_trimestre", type text},
         {"definition_charges_operatoires", type text}, {"definition_capitaux_propres", type text}}
    )
in
    Types
