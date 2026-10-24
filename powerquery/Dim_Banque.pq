// Auteur : Ahmed Ben Arfa
// Dimension des banques (chargée) : code, nom, ticker de la Bourse (dim_banque.csv), et actionnariat
// actuel (Banques_Actionnariat, depuis le fichier Excel) : actionnaire de référence, part du capital,
// catégorie (public, groupe étranger, mixte, privé sans contrôle étranger), groupe, date de la source.
let
    Fichier = Fichiers_Donnees{[fichier = "dim_banque.csv"]}[contenu],
    Source = Csv.Document(Fichier, [Delimiter = ";", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    EnTetes = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Types = Table.TransformColumnTypes(
        EnTetes, {{"code_banque", type text}, {"nom", type text}, {"ticker_bvmt", type text}}, "en-US"
    ),
    // les colonnes actionnariat et groupe du CSV sont vides : elles viennent du fichier Excel
    SansColonnesVides = Table.RemoveColumns(Types, {"actionnariat", "groupe"}),
    // ligne en cours de chaque banque : celle dont la période n'a pas de fin
    ActionnariatActuel = Table.SelectRows(Banques_Actionnariat, each [date_fin] = null),
    // fusion avec l'actionnariat actuel (une ligne par banque : sinon la fusion dupliquerait la banque)
    Fusion = Table.NestedJoin(
        SansColonnesVides, {"code_banque"}, ActionnariatActuel, {"code_banque"}, "Actionnariat", JoinKind.LeftOuter
    ),
    Developpee = Table.ExpandTableColumn(
        Fusion, "Actionnariat",
        {"actionnaire_reference", "part_capital_pct", "actionnariat", "groupe", "date_reference"},
        {"actionnaire_reference", "part_capital_pct", "actionnariat", "groupe", "date_actionnariat"}
    ),
    // logos des banques (donnees_reference\logos\<code>.png, sources dans le LISEZMOI du dossier), lus avec le
    // connecteur Dossier : chaque image devient une adresse « data:image/png;base64,… » que Power BI affiche
    // dans un segment ou un tableau (catégorie de données « URL d'image »)
    Logos = Table.SelectRows(
        Folder.Files(CheminDonnees & "\donnees_reference\logos"), each Text.Lower([Extension]) = ".png"
    ),
    Icones = Table.AddColumn(
        Logos, "icone", each "data:image/png;base64," & Binary.ToText([Content], BinaryEncoding.Base64), type text
    ),
    CodeLogo = Table.AddColumn(Icones, "code_logo", each Text.BeforeDelimiter([Name], "."), type text),
    // fusion sur le code : une banque sans logo garde une icône vide
    FusionLogos = Table.NestedJoin(
        Developpee, {"code_banque"}, Table.SelectColumns(CodeLogo, {"code_logo", "icone"}), {"code_logo"},
        "Logo", JoinKind.LeftOuter
    ),
    AvecIcone = Table.ExpandTableColumn(FusionLogos, "Logo", {"icone"})
in
    AvecIcone
