// Auteur : Ahmed Ben Arfa
// Contenu des capitaux propres trimestriels publiés par chaque banque (chargée) : hors résultat de la
// période, résultat inclus, ou hors résultat avec affectation au 31/12. Affiché dans la fiche banque à côté
// des capitaux propres trimestriels ; les comparaisons entre banques utilisent les capitaux propres du
// bilan (spécification 5.2 et 7.7, décision du 19/10/2026).
let
    Source = Gabarits,
    Colonnes = Table.SelectColumns(Source, {"banque", "definition_capitaux_propres"}),
    // une ligne par banque (la définition ne change pas d'un gabarit à l'autre)
    Distinctes = Table.Distinct(Colonnes),
    // colonne conditionnelle : la définition en clair (mêmes textes que le script d'extraction)
    Description = Table.AddColumn(
        Distinctes, "description",
        each if [definition_capitaux_propres] = "hors resultat de la periode"
                then "capitaux propres sans le résultat de la période en cours (= capitaux propres du bilan − résultat net de la période)"
            else if [definition_capitaux_propres] = "resultat inclus"
                then "capitaux propres y compris le résultat de la période (= capitaux propres du bilan)"
            else if [definition_capitaux_propres] = "hors resultat, apres affectation au 31/12"
                then "hors résultat de la période en cours d'année ; au 31/12, après affectation du résultat de l'exercice (réserves augmentées, dividendes déduits)"
            else null,
        type text
    ),
    Triees = Table.Sort(Description, {{"banque", Order.Ascending}})
in
    Triees
