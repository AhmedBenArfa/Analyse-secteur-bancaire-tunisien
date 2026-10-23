// Auteur : Ahmed Ben Arfa
// Actionnariat des banques (chargée) : table Excel « Banques » de donnees_reference\banques.xlsx
// (connecteur Excel), une ligne par banque et par période d'actionnaire de référence (date_debut,
// date_fin vides quand l'actionnaire n'a pas changé de 2019 à 2026), avec la source et la page de
// chaque valeur. Règle de classement par le contrôle : spécification 5.3. Dim_Banque en prend la ligne
// en cours ; la fiche banque affiche l'historique et ses sources.
let
    Classeur = Excel.Workbook(File.Contents(CheminDonnees & "\donnees_reference\banques.xlsx"), true),
    // la table Excel nommée (pas la feuille) : ses limites suivent les lignes ajoutées dans Excel
    Banques = Classeur{[Item = "Banques", Kind = "Table"]}[Data],
    Types = Table.TransformColumnTypes(
        Banques,
        {
            {"code_banque", type text}, {"nom", type text}, {"actionnaire_reference", type text},
            {"part_capital_pct", type number}, {"actionnariat", type text}, {"groupe", type text},
            {"date_reference", type date}, {"source", type text}, {"page", type text},
            {"date_debut", type date}, {"date_fin", type date}, {"remarque", type text}
        }
    ),
    // une catégorie hors de la règle (faute de frappe dans Excel) se verrait ici comme une erreur
    CategorieValide = Table.TransformColumns(
        Types,
        {{"actionnariat", each if List.Contains(
            {"public", "groupe étranger", "mixte", "privé sans contrôle étranger"}, _) then _
            else error "catégorie d'actionnariat inconnue : " & (if _ = null then "(vide)" else _), type text}}
    )
in
    CategorieValide
