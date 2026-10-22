// Auteur : Ahmed Ben Arfa
// Requête intermédiaire (non chargée) : les CSV du dossier versionné donnees_publiees\, lus avec le
// connecteur Dossier. Les autres requêtes y prennent leur fichier par son nom : un seul endroit dépend
// du disque. Le dossier est régénéré par python scripts/publier_donnees.py (donnees\ reste local).
let
    Source = Folder.Files(CheminDonnees & "\donnees_publiees"),
    // seulement les CSV posés directement dans donnees_publiees\ (pas LISEZMOI.md)
    CsvDuDossier = Table.SelectRows(
        Source,
        each [Extension] = ".csv" and [Folder Path] = CheminDonnees & "\donnees_publiees\"
    ),
    Colonnes = Table.SelectColumns(CsvDuDossier, {"Name", "Content", "Date modified"}),
    Renommees = Table.RenameColumns(Colonnes, {{"Name", "fichier"}, {"Content", "contenu"}, {"Date modified", "modifie_le"}})
in
    Renommees
