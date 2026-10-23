// Auteur : Ahmed Ben Arfa
// Requête intermédiaire (non chargée) : opérations sur titres des 12 banques (dividendes, attributions
// gratuites, division du nominal, souscription), lues sur GitHub (source URL), avec le facteur
// d'ajustement publié par la Bourse et les facteurs cumulés qui ajusteront les cours de Fait_Cours
// (spécification 7.5). Cours ajusté d'une séance = cours × produit des facteurs des opérations postérieures.
let
    // Web.Contents avec RelativePath : l'adresse de base reste fixe (actualisation possible en ligne)
    Source = Csv.Document(
        Web.Contents(AdresseDepot, [RelativePath = "operations_titres.csv"]),
        [Delimiter = ";", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    EnTetes = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    // décimales avec un point : types avec les paramètres régionaux en-US
    Types = Table.TransformColumnTypes(
        EnTetes,
        {
            {"banque", type text}, {"isin", type text}, {"date_effet", type date}, {"types", type text},
            {"details", type text}, {"dividende", type number}, {"date_veille", type date},
            {"cloture_veille", type number}, {"cours_reference_publie", type number},
            {"cours_reference_theorique", type number}, {"ecart_theorique", type number},
            {"bulletin", type text}, {"page_cours", Int64.Type}, {"page_avis", Int64.Type},
            {"extrait_avis", type text}, {"detection", type text}
        },
        "en-US"
    ),
    // facteur de la Bourse : cours de référence publié le jour de l'opération / clôture de la veille ;
    // vide si le cours de référence manque (opération signalée, jamais de facteur inventé)
    Facteur = Table.AddColumn(
        Types, "facteur",
        each if [cours_reference_publie] = null or [cloture_veille] = null then null
            else [cours_reference_publie] / [cloture_veille],
        type nullable number
    ),
    // colonne conditionnelle : opération sur le capital (tout sauf un dividende seul)
    Capital = Table.AddColumn(Facteur, "capital", each [types] <> "dividende", type logical),
    // facteur de la série « prix » : 1 pour un dividende seul ; si un dividende est détaché le même jour
    // qu'une attribution (BT 10/05/2022), il est retiré de la clôture de la veille avant la parité
    FacteurPrix = Table.AddColumn(
        Capital, "facteur_prix",
        each if not [capital] then 1
            else if [facteur] = null then null
            else if [dividende] <> null then [cours_reference_publie] / ([cloture_veille] - [dividende])
            else [facteur],
        type nullable number
    ),
    // table gardée en mémoire : les cumuls la parcourent pour chaque ligne sans relire le fichier en ligne
    EnMemoire = Table.Buffer(FacteurPrix),
    // facteurs cumulés : produit des facteurs de la banque pour cette opération et les suivantes ; une
    // séance antérieure à l'opération prend le cumul de la première opération qui la suit
    CumulPrix = Table.AddColumn(
        EnMemoire, "facteur_cumule_prix",
        (op) => List.Product(List.RemoveNulls(Table.SelectRows(
            EnMemoire, (autre) => autre[banque] = op[banque] and autre[date_effet] >= op[date_effet])[facteur_prix])),
        type number
    ),
    CumulRendement = Table.AddColumn(
        CumulPrix, "facteur_cumule_rendement",
        (op) => List.Product(List.RemoveNulls(Table.SelectRows(
            EnMemoire, (autre) => autre[banque] = op[banque] and autre[date_effet] >= op[date_effet])[facteur])),
        type number
    ),
    Triees = Table.Sort(CumulRendement, {{"banque", Order.Ascending}, {"date_effet", Order.Ascending}})
in
    Triees
