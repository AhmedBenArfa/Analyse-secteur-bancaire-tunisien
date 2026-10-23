// Auteur : Ahmed Ben Arfa
// Fonction (requête non chargée) : catégorie d'actionnariat d'une banque à une date, lue dans les périodes
// de Banques_Actionnariat (la ligne dont la période couvre la date ; spécification 5.3). Appelée par
// Fait_Indicateurs, Variations_Comparables et Fait_Etats_Financiers (colonne Segment_Actionnariat).
// Vide si aucune période ne couvre la date (tests/test_actionnariat.py vérifie qu'il n'y a pas de trou).
(periodes as table, banque as text, jour as date) as nullable text =>
let
    Couvrantes = Table.SelectRows(
        periodes,
        each [code_banque] = banque
            and ([date_debut] = null or [date_debut] <= jour)
            and ([date_fin] = null or [date_fin] >= jour)
    ),
    Segment = if Table.RowCount(Couvrantes) = 1 then Couvrantes{0}[actionnariat] else null
in
    Segment
