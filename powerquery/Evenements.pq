// Auteur : Ahmed Ben Arfa
// Événements qui expliquent une rupture de série (chargée) : don au Fonds 1818, accord salarial
// APTBEF–FGBEF, moratoire Covid de l'UIB, retraitement BH 2024, déchéance fiscale BNA 2025 ; une ligne par
// événement et par banque, avec le montant cité, le fichier et la page. Lus sur GitHub (source URL) ;
// annotations des graphiques (spécification 5.1, 7.3, pages 3 et 9).
let
    Source = Csv.Document(
        Web.Contents(AdresseDepot, [RelativePath = "evenements.csv"]),
        [Delimiter = ";", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    EnTetes = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Types = Table.TransformColumnTypes(
        EnTetes,
        {
            {"id_evenement", type text}, {"date", type date}, {"banque", type text}, {"indicateur", type text},
            {"description", type text}, {"montant_mdt", type number}, {"fichier", type text}, {"page", Int64.Type}
        },
        "en-US"
    )
in
    Types
