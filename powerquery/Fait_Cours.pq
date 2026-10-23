// Auteur : Ahmed Ben Arfa
// Table de faits des cours (chargée) : une ligne par banque et par séance du 02/01/2019 à la dernière
// séance collectée, cours non ajustés de la Bourse, cours ajustés des opérations sur titres
// (Operations_Titres), rendement d'une séance à l'autre et marqueur de séance sans transaction
// (spécification 7.5).
let
    Fichier = Fichiers_Donnees{[fichier = "cours_banques.csv"]}[contenu],
    Source = Csv.Document(Fichier, [Delimiter = ";", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    EnTetes = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Types = Table.TransformColumnTypes(
        EnTetes,
        {
            {"ticker", type text}, {"banque", type text}, {"isin", type text}, {"date", type date},
            {"ouverture", type number}, {"haut", type number}, {"bas", type number}, {"cloture", type number},
            {"volume", Int64.Type}, {"nb_transactions", Int64.Type}, {"capitaux", type number},
            {"statut", type text}, {"source", type text}, {"fichier", type text}
        },
        "en-US"
    ),
    // une case vide du CSV (cours absent, pas de statut) reste vide, jamais zéro
    VidesEnNull = Table.ReplaceValue(Types, "", null, Replacer.ReplaceValue, {"statut"}),
    SansIsin = Table.RemoveColumns(VidesEnNull, {"isin"}),
    // opérations de la banque, gardées en mémoire (lues une fois sur GitHub)
    Operations = Table.Buffer(
        Table.SelectColumns(Operations_Titres, {"banque", "date_effet", "facteur_cumule_prix", "facteur_cumule_rendement"})
    ),
    // fusion avec Operations_Titres sur la banque : chaque séance reçoit les opérations de sa banque
    Fusion = Table.NestedJoin(SansIsin, {"banque"}, Operations, {"banque"}, "operations", JoinKind.LeftOuter),
    // première opération postérieure à la séance (les opérations sont triées par date) : ses facteurs
    // cumulés sont le produit des facteurs de toutes les opérations qui suivent la séance
    Suivante = Table.AddColumn(
        Fusion, "operation_suivante",
        (s) => Table.First(Table.SelectRows(s[operations], (o) => o[date_effet] > s[date]), null)
    ),
    Developpee = Table.ExpandRecordColumn(
        Table.RemoveColumns(Suivante, {"operations"}), "operation_suivante",
        {"facteur_cumule_prix", "facteur_cumule_rendement"}, {"facteur_prix", "facteur_rendement"}
    ),
    // aucune opération après la séance : facteur 1 (cours déjà au niveau d'aujourd'hui)
    FacteurUn = Table.ReplaceValue(Developpee, null, 1, Replacer.ReplaceValue, {"facteur_prix", "facteur_rendement"}),
    // cours ajustés : série « prix » (opérations sur le capital) et série « rendement total » (dividendes compris)
    AjustePrix = Table.AddColumn(
        FacteurUn, "cloture_ajustee_prix", each [cloture] * [facteur_prix], type nullable number
    ),
    AjusteRendement = Table.AddColumn(
        AjustePrix, "cloture_ajustee_rendement", each [cloture] * [facteur_rendement], type nullable number
    ),
    // colonne conditionnelle : séance sans transaction (mesure de liquidité, avertissement « titre peu liquide »)
    SansTransaction = Table.AddColumn(
        AjusteRendement, "sans_transaction",
        each if [statut] <> null and Text.Contains([statut], "sans transaction") then true else false, type logical
    ),
    Triees = Table.Sort(SansTransaction, {{"banque", Order.Ascending}, {"date", Order.Ascending}}),
    // rendement d'une séance à l'autre sur la série « rendement total », banque par banque ; une clôture
    // vide reprend la dernière clôture connue (rendement nul ce jour-là), la première séance n'a pas de rendement
    ParBanque = Table.Group(
        Triees, {"banque"},
        {{"seances", (t) =>
            let
                Connue = Table.FillDown(
                    Table.AddColumn(t, "cloture_connue", each [cloture_ajustee_rendement], type nullable number),
                    {"cloture_connue"}
                ),
                Valeurs = List.Buffer(Connue[cloture_connue]),
                AvecIndex = Table.AddIndexColumn(Connue, "rang", 0, 1, Int64.Type),
                AvecRendement = Table.AddColumn(
                    AvecIndex, "rendement",
                    each if [rang] = 0 or [cloture_connue] = null or Valeurs{[rang] - 1} = null then null
                        else [cloture_connue] / Valeurs{[rang] - 1} - 1,
                    type nullable number
                )
            in
                Table.RemoveColumns(AvecRendement, {"cloture_connue", "rang"}),
          type table}}
    ),
    Seances = Table.Combine(ParBanque[seances]),
    // types rétablis après le regroupement
    TypesFinaux = Table.TransformColumnTypes(
        Seances,
        {
            {"ticker", type text}, {"banque", type text}, {"date", type date},
            {"ouverture", type number}, {"haut", type number}, {"bas", type number}, {"cloture", type number},
            {"volume", Int64.Type}, {"nb_transactions", Int64.Type}, {"capitaux", type number},
            {"statut", type text}, {"source", type text}, {"fichier", type text},
            {"facteur_prix", type number}, {"facteur_rendement", type number},
            {"cloture_ajustee_prix", type number}, {"cloture_ajustee_rendement", type number},
            {"sans_transaction", type logical}, {"rendement", type number}
        }
    )
in
    TypesFinaux
