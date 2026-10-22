// Auteur : Ahmed Ben Arfa
// Table de faits des indicateurs trimestriels (chargée) : la valeur retenue de chaque indicateur, une
// ligne par banque × trimestre × indicateur, avec le trimestre seul et le cumul côte à côte, et pour
// chacun la version retenue, le fichier, la page et la rupture de série (spécification 5.1 et 5.2).
let
    Source = Versions,
    // filtre explicite : seule la version retenue (révisée quand elle existe) entre dans les faits ;
    // les versions écartées vont dans la requête Revisions (page qualité)
    VersionRetenue = Table.SelectRows(Source, each [version] = [source_valeur]),
    Colonnes = Table.SelectColumns(
        VersionRetenue,
        {"banque", "trimestre", "date_arrete", "code_indicateur", "mesure",
         "valeur_retenue", "source_valeur", "fichier", "page", "rupture_serie", "detail_rupture"}
    ),
    // noms des attributs tels qu'ils seront préfixés après le pivot (Valeur_Trim, Source_Cumul…)
    Renommees = Table.RenameColumns(
        Colonnes,
        {{"valeur_retenue", "Valeur"}, {"source_valeur", "Source"}, {"fichier", "Fichier"},
         {"page", "Page"}, {"rupture_serie", "Rupture"}, {"detail_rupture", "Detail_Rupture"}}
    ),
    // dépivotage : une ligne par attribut ; une case vide (pas de rupture) ne donne pas de ligne
    Depivotees = Table.UnpivotOtherColumns(
        Renommees, {"banque", "trimestre", "date_arrete", "code_indicateur", "mesure"}, "attribut", "contenu"
    ),
    // nom de la future colonne : attribut + mesure (« trim » → Trim, « cumul » → Cumul)
    NomColonne = Table.AddColumn(Depivotees, "colonne", each [attribut] & "_" & Text.Proper([mesure]), type text),
    SansMesure = Table.RemoveColumns(NomColonne, {"mesure", "attribut"}),
    // pivot sans agrégation (une seule valeur par cellule) ; liste fixe : les colonnes existent toujours
    Pivotees = Table.Pivot(
        SansMesure,
        {"Valeur_Trim", "Valeur_Cumul", "Source_Trim", "Source_Cumul", "Fichier_Trim", "Fichier_Cumul",
         "Page_Trim", "Page_Cumul", "Rupture_Trim", "Rupture_Cumul", "Detail_Rupture_Trim", "Detail_Rupture_Cumul"},
        "colonne",
        "contenu"
    ),
    Types = Table.TransformColumnTypes(
        Pivotees,
        {
            {"Valeur_Trim", type number}, {"Valeur_Cumul", type number},
            {"Source_Trim", type text}, {"Source_Cumul", type text},
            {"Fichier_Trim", type text}, {"Fichier_Cumul", type text},
            {"Page_Trim", Int64.Type}, {"Page_Cumul", Int64.Type},
            {"Rupture_Trim", type text}, {"Rupture_Cumul", type text},
            {"Detail_Rupture_Trim", type text}, {"Detail_Rupture_Cumul", type text}
        }
    )
in
    Types
