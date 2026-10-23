// Auteur : Ahmed Ben Arfa
// Dimension des indicateurs (chargée) : une ligne par code, avec le libellé, la catégorie, la nature
// (flux : s'additionne ; stock : solde à une date, jamais additionné) et l'ordre d'affichage.
// Les 3 codes des états financiers y sont ajoutés pour que les événements qui les concernent gardent
// leur relation (spécification 5.1 et 6). Fait_Indicateurs y prend la nature par une fusion.
let
    Fichier = Fichiers_Donnees{[fichier = "dim_indicateur.csv"]}[contenu],
    Source = Csv.Document(Fichier, [Delimiter = ";", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    EnTetes = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Types = Table.TransformColumnTypes(
        EnTetes,
        {{"code_indicateur", type text}, {"libelle", type text}, {"categorie", type text},
         {"nature", type text}, {"ordre", Int64.Type}},
        "en-US"
    ),
    // colonne ajoutée : d'où viennent les valeurs de l'indicateur
    SourceIndicateurs = Table.AddColumn(Types, "source", each "indicateurs trimestriels", type text),
    // codes des états financiers (libellés de scripts/etats_financiers.py), à la suite des 24 codes
    EtatsFinanciers = #table(
        type table [code_indicateur = text, libelle = text, categorie = text, nature = text,
                    ordre = Int64.Type, source = text],
        {
            {"RES_NET", "Résultat net (avant modifications comptables)", "Résultat", "flux", 25, "états financiers"},
            {"TOTAL_ACTIF", "Total de l'actif", "Bilan", "stock", 26, "états financiers"},
            {"CAP_PROPRES_EF", "Total des capitaux propres (bilan, résultat inclus)", "Bilan", "stock", 27, "états financiers"}
        }
    ),
    Ajoutees = Table.Combine({SourceIndicateurs, EtatsFinanciers})
in
    Ajoutees
