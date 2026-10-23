// Auteur : Ahmed Ben Arfa
// Versions non retenues des indicateurs trimestriels (chargée) : chaque valeur publiée puis remplacée
// (initiale révisée par le document suivant, 31/12 provisoire remplacé par le T4 de l'année suivante,
// colonne fausse écartée, document en image), avec l'écart à la valeur retenue. Page « qualité des
// données » (spécification 5.1 et 5.2). Complément exact de Fait_Indicateurs : même source, filtre inverse.
let
    Source = Versions,
    // filtre explicite, inverse de celui de Fait_Indicateurs : toutes les versions écartées
    VersionsNonRetenues = Table.SelectRows(Source, each [version] <> [source_valeur]),
    Colonnes = Table.SelectColumns(
        VersionsNonRetenues,
        {"banque", "trimestre", "date_arrete", "code_indicateur", "mesure", "version", "valeur_mdt",
         "fichier", "page", "valeur_retenue", "source_valeur", "statut_revision", "note_definition",
         "mention_retraitement"}
    ),
    // écart calculé ici (la colonne ecart_vs_retenue du CSV n'est pas reprise) : de combien la valeur
    // retenue s'écarte de cette version ; vide si l'une des deux manque (document en image, capitaux
    // propres au 31/12 provisoire sans autre version), jamais zéro
    EcartMDT = Table.AddColumn(Colonnes, "Ecart_MDT", each [valeur_retenue] - [valeur_mdt], type nullable number),
    EcartPct = Table.AddColumn(
        EcartMDT, "Ecart_Pct",
        each if [valeur_mdt] = null or [valeur_mdt] = 0 then null else [Ecart_MDT] / Number.Abs([valeur_mdt]),
        type nullable number
    ),
    // colonne conditionnelle : d'où vient la version écartée
    OrigineVersion = Table.AddColumn(
        EcartPct, "Origine_Version",
        each if [version] = "initiale" then "document du trimestre"
            else if Text.StartsWith([version], "revisee_31-12") then "31/12 provisoire (document T1 à T3 suivant)"
            else if Text.StartsWith([version], "revisee_T") then "colonne N-1 du document suivant"
            else [version],
        type text
    ),
    // colonne conditionnelle : statut de la révision en clair, pour les segments de la page qualité
    TypeRevision = Table.AddColumn(
        OrigineVersion, "Type_Revision",
        each if [statut_revision] = null then "identique à la valeur retenue (arrondi)"
            else if [statut_revision] = "retraitement_mineur" then "retraitement mineur (2 % au plus)"
            else if [statut_revision] = "revision_importante" then "révision importante (plus de 2 %)"
            else if [statut_revision] = "reclassement" then "reclassement (total inchangé)"
            else if [statut_revision] = "illisible (image)" then "document publié en image"
            else if Text.StartsWith([statut_revision], "exclue (capitaux propres") then "31/12 provisoire écarté (capitaux propres)"
            else if Text.StartsWith([statut_revision], "exclue") then "colonne fausse du document, écartée"
            else [statut_revision],
        type text
    )
in
    TypeRevision
