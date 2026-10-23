// Auteur : Ahmed Ben Arfa
// Contenu des charges opératoires publiées par chaque banque, par période (chargée) : sans dotations,
// avec dotations publiées, ou avec un reste non détaillé. Explique pourquoi le coefficient publié n'est
// pas comparable d'une banque à l'autre (info-bulle du coefficient publié, page qualité ; spécification
// 7.2 et 7.4). Les classements utilisent le coefficient harmonisé.
let
    Source = Gabarits,
    // regroupement : les gabarits découpent l'historique par mise en page (et par rang du trimestre) ;
    // une définition garde la période allant de son premier à son dernier trimestre
    Periodes = Table.Group(
        Source, {"banque", "definition_charges_operatoires"},
        {{"premier_trimestre", each List.Min([premier_trimestre]), type text},
         {"dernier_trimestre", each List.Max([dernier_trimestre]), type text}}
    ),
    // colonne conditionnelle : la définition en clair (mêmes textes que le script d'extraction)
    Description = Table.AddColumn(
        Periodes, "description",
        each if [definition_charges_operatoires] = "sans dotations"
                then "total publié = frais de personnel + charges générales d'exploitation"
            else if [definition_charges_operatoires] = "avec dotations publiees"
                then "total publié = frais de personnel + charges générales + dotations aux amortissements, les trois lignes publiées"
            else if [definition_charges_operatoires] = "avec reste non detaille"
                then "total publié > frais de personnel + charges générales ; la différence (dotations ou autres charges) n'est pas détaillée dans le PDF"
            else if [definition_charges_operatoires] = "composantes non publiees"
                then "seul le total est publié ; coefficient harmonisé non calculable"
            else null,
        type text
    ),
    Triees = Table.Sort(Description, {{"banque", Order.Ascending}, {"premier_trimestre", Order.Ascending}})
in
    Triees
