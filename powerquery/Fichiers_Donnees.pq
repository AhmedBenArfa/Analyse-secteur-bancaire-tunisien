// Requête intermédiaire (non chargée) : les CSV du dossier donnees\, lus avec le connecteur Dossier.
// Les autres requêtes y prennent leur fichier par son nom : un seul endroit dépend du disque.
let
    Source = Folder.Files(CheminDonnees & "\donnees"),
    // seulement les CSV posés directement dans donnees\ (pas les sous-dossiers pdf\, cours\…)
    CsvDuDossier = Table.SelectRows(
        Source,
        each [Extension] = ".csv" and [Folder Path] = CheminDonnees & "\donnees\"
    ),
    Colonnes = Table.SelectColumns(CsvDuDossier, {"Name", "Content", "Date modified"}),
    Renommees = Table.RenameColumns(Colonnes, {{"Name", "fichier"}, {"Content", "contenu"}, {"Date modified", "modifie_le"}})
in
    Renommees
