# Spécification — Analyse du secteur bancaire tunisien (2019–2026)

## 1. Objectif

Construire un rapport Power BI qui compare l'activité, l'efficacité et la structure
des 12 banques cotées à la Bourse de Tunis, trimestre par trimestre, de T4 2019 à T3 2026,
et qui met en regard leur performance opérationnelle et leur performance boursière.

Questions auxquelles le rapport doit répondre :

1. Quelles banques ont le PNB le plus élevé, et lesquelles gagnent des parts de marché ?
2. Quelles banques sont les plus efficaces (coefficient d'exploitation) et comment cela évolue-t-il ?
3. D'où vient le PNB de chaque banque (marge d'intérêts, commissions, portefeuille-titres) ?
4. Comment ont évolué crédits et dépôts, et le ratio crédits / dépôts ?
5. Le secteur se concentre-t-il (indice HHI) ?
6. Quel a été l'effet du Covid (2020–2021) et comment le secteur s'est-il redressé ?
7. La Bourse récompense-t-elle les banques les plus performantes ?

Inspiration : un rapport Power BI publié sur LinkedIn sur les ratios des banques cotées au
30/06/2026, construit à partir des mêmes publications trimestrielles. Ce projet s'en distingue
par les ajouts listés en section 8.

## 2. Périmètre

| Élément | Choix |
|---|---|
| Banques | AB, ATB, Attijari Bank, BH Bank, BIAT, BNA, BT, BTE, STB, UBCI, UIB, Wifak International Bank |
| Période | T4 2019 → T3 2026 (T4 2019 sert seulement de base pour les évolutions sur un an de 2020) |
| Fréquence | Trimestrielle (indicateurs), quotidienne (cours) |
| Unité | Millions de dinars (MDT) |

## 3. Sources de données

| Source | Contenu | Format | Connexion Power BI |
|---|---|---|---|
| BVMT / CMF — indicateurs trimestriels | PNB, charges, crédits, dépôts… | PDF → CSV via `collecte_banques.py` | Dossier (CSV) |
| BVMT ou ilboursa — cours | Cours quotidiens 2019–2026 | CSV via script | Dossier (CSV) |
| Kaggle « Tunisian Stock Market » | Cours 2010 → janvier 2022 (contrôle) | CSV | Web (URL) ou fichier |
| Tables de référence remplies à la main | Banques (actionnariat, groupe), libellés, périodes | Excel | Excel |
| États financiers annuels et semestriels (CMF / BVMT) | Résultat net, total de l'actif, capitaux propres | PDF → CSV (script ou saisie) | Dossier (CSV) |
| Page web ilboursa (contrôle) | Tableau annuel par société (dont le résultat net) | HTML | Web (URL) |

Les trois types de connexion (CSV, Excel, URL) sont utilisés volontairement : c'est un point
à montrer dans le portfolio.

Limites des données :

- Indicateurs **provisoires et non audités** ; certaines sociétés publient en retard.
- Mises en page différentes selon les banques et les années : contrôle obligatoire.
- Pas de résultat net dans les indicateurs trimestriels : le ROE et le ROA viennent des
  états financiers, donc seulement en semestriel et en annuel (voir 7.7).
- Certaines banques retraitent l'année précédente : les deux versions sont conservées
  (initiale, révisée) et la règle de la section 5.2 choisit la valeur d'analyse.
- **Wifak International Bank est une banque islamique** : ses indicateurs ne sont pas des
  intérêts et des crédits mais des **équivalences**, rangées sous les codes communs pour pouvoir
  comparer, à signaler dans le rapport :

  | Libellé Wifak | Code | Équivalent conventionnel |
  |---|---|---|
  | Marges et revenus assimilés | `INT_PERCUS` | Intérêts perçus |
  | Charges encourues et charges assimilées | `INT_ENCOURUS` | Intérêts encourus |
  | Revenus du portefeuille commercial & opérations financières + Revenus du portefeuille d'investissement | `REV_PORTEF` (somme des deux lignes) | Revenus du portefeuille-titres |
  | Encours net des financements à la clientèle | `CREDITS` | Encours des crédits |
  | Tawfir | `DEP_EPARGNE` | Dépôts d'épargne |
  | Comptes Istithmars | `DEP_TERME` | Dépôts à terme (comptes d'investissement) |
  | Dettes de financements et ressources spéciales | `EMPRUNTS` | Emprunts et ressources spéciales |

  La ligne « Pertes sur portefeuille titres commercial et opérations financières » (une charge)
  n'est rattachée à aucun indicateur. Pour Wifak, « marge d'intérêts » se lit donc « marges
  et revenus assimilés − charges encourues », et « crédits / dépôts » « financements / dépôts ».

## 4. Pipeline

```
PDF (BVMT, CMF, bulletins officiels)
   └─ collecte_banques.py ──> donnees/indicateurs_banques_long.csv  (une ligne par valeur lue dans un document)
                              donnees/indicateurs_versions.csv    (une ligne par période et version, valeur retenue)
                              donnees/dim_indicateur.csv, dim_banque.csv
                              donnees/controle_extraction.csv
scripts/cours_boursiers.py ─> donnees/cours_banques.csv
Excel de référence ─────────> referentiel.xlsx
                     │
                Power Query (ETL)
                     │
          Modèle en étoile Power BI ─> mesures DAX ─> rapport
```

## 5. ETL dans Power Query

### 5.1 Requêtes

| Requête | Source | Étapes principales |
|---|---|---|
| `Versions` (intermédiaire, non chargée) | `indicateurs_versions.csv` | types (paramètres régionaux en-US) ; application de `Corrections` sur `valeur_mdt` |
| `Fait_Indicateurs` | référence à `Versions` | filtre `version = source_valeur` (une ligne par banque × trimestre × indicateur × mesure) ; suppression de `valeur_mdt`, `version` ; pivot de `mesure` sur `valeur_retenue` → `Valeur_Trim` et `Valeur_Cumul` ; pivot de `mesure` sur `source_valeur` → `Source_Trim` et `Source_Cumul` |
| `Revisions` | référence à `Versions` | filtre `version <> source_valeur` (versions non retenues : initiales révisées, 31/12 provisoires remplacés par le T4 suivant, 31/12 exclus pour les capitaux propres) ; colonnes `banque`, `date_arrete`, `code_indicateur`, `mesure`, `version`, `valeur_mdt`, `valeur_retenue`, `source_valeur`, `statut_revision` (correction / reclassement / exclue), `note_definition`, `Ecart_MDT = valeur_retenue − valeur_mdt` ; pour la page « qualité des données » |
| `Controle_Annuel` | `controle_annuel.csv` | types ; somme des trimestres vs cumul T4, statut (`ok`, `en attente de révision`, `ecart`) |
| `Dim_Banque` | `dim_banque.csv` + Excel | fusion avec l'onglet Excel (actionnariat, groupe), nettoyage |
| `Dim_Indicateur` | `dim_indicateur.csv` | types, ordre de tri |
| `Fait_Cours` | Dossier de CSV cours | combinaison des fichiers, types, suppression des doublons, colonne `Rendement` (variation du cours d'un jour à l'autre) |
| `Controle` | `controle_extraction.csv` | pour la page « qualité des données » |
| `Corrections` | `corrections_manuelles.csv` | remplacement des valeurs corrigées dans `Fait_Indicateurs` |

### 5.2 Points d'attention

- **Valeur du trimestre seul** : les banques publient le trimestre seul (`trim_N`) et le cumul.
  Recalculer aussi `cumul(T) − cumul(T−1)` (même année, T > 1) et comparer : un écart signale
  une erreur d'extraction ou un retraitement.
- **Versions des chiffres** : une même période est publiée plusieurs fois. Colonne `version` :
  - `initiale` : valeur publiée dans le document du trimestre lui-même (colonnes `trim_N`, `cumul_N`) ;
  - `revisee_T<q>_N+1` : valeur du même trimestre redonnée en comparaison (colonnes `trim_N1`,
    `cumul_N1`) par le document du même trimestre de l'année suivante (ex. `revisee_T2_N+1`) ;
  - `revisee_31-12_T<q>_N+1` : **version révisée provisoire** du 31/12, lue dans la colonne
    « 31/12/N-1 » (`exercice_N1`, chiffres souvent audités) d'un document T1, T2 ou T3 de l'année
    suivante. Elle ne concerne que le **cumul annuel (cumul au T4)** des flux et les **soldes au 31/12**
    des stocks.

  Les banques retraitent parfois leurs chiffres entre les deux. Exemple constaté au T3 2025 :
  BIAT et UIB ont retraité leur premier semestre 2025 après la publication des indicateurs du T2
  (BIAT : alignement sur les états financiers intermédiaires ; UIB : chiffres « retraités pour les
  besoins de comparabilité »), et le trimestre T3 publié est calculé sur le semestre retraité
  (BIAT : PNB T3 publié 407,005 MDT ; cumul 9 mois − cumul S1 initial = 407,628 MDT ;
  cumul 9 mois − cumul S1 révisé = 407,005 MDT).

  **Règle** : la valeur d'analyse (`valeur_retenue`) suit cet ordre de priorité ; `source_valeur`
  donne la version exacte retenue :
  1. trimestres T1 à T3 (trimestre seul et cumul) : `revisee_T<q>_N+1` > `initiale` ;
  2. **cumul annuel (cumul au T4) et soldes au 31/12** : `revisee_T4_N+1` > `revisee_31-12` du
     document le plus récent de l'année suivante (T3 > T2 > T1) > `initiale` ;
  3. **T4 seul** (trimestre isolé) : `revisee_T4_N+1` > `initiale` ; la colonne 31/12/N-1 n'est
     **pas** utilisée (elle ne donne pas le trimestre seul). Le T4 seul reste donc en version
     initiale jusqu'à la publication du document T4 de l'année suivante.

  Les périodes de la dernière année publiée (2026) sont en version initiale. Toutes les versions
  restent dans `indicateurs_versions.csv` pour la traçabilité (colonnes `fichier`, `page`), avec
  `ecart_vs_retenue` = valeur de la version − valeur retenue.

  **Contrôle annuel** (`controle_annuel.csv`, refait à chaque extraction) : somme des 4 trimestres
  retenus comparée au cumul T4 retenu, pour le PNB, les produits, les charges d'exploitation
  bancaire et les charges opératoires. Tolérance : 2 milliers de dinars (arrondi des banques qui
  publient en milliers). Statuts :
  - `ok` ;
  - `en attente de révision` : le cumul retenu est la version provisoire 31/12 alors que le T4 seul
    est encore en version initiale ; l'écart disparaîtra (ou se confirmera) avec le document T4
    de l'année suivante. Ce n'est pas une erreur ;
  - `ecart` : à examiner.

  Vérifié sur 2025 : avec les trimestres retenus, la somme des 4 trimestres égale le cumul T4
  **initial**, exactement pour BIAT, à 1 millier de dinars près pour UIB. Le cumul retenu étant
  aujourd'hui le 31/12 provisoire (document T2 2026), les 8 contrôles BIAT / UIB 2025 sont
  `en attente de révision` (ex. charges opératoires BIAT : 723,988 MDT en initial, 711,102 MDT
  au 31/12 provisoire ; PNB UIB : 522,651 MDT contre 525,528 MDT).

  **Nature de chaque révision** (`statut_revision` dans `indicateurs_versions.csv`, pour chaque
  version non retenue comparée à la retenue ; tolérance d'arrondi : 2 milliers de dinars) :
  - `correction` : le total change au-delà de la tolérance, sans compensation (quel que soit le
    pourcentage ; ex. PNB UIB 2025 +0,55 %, intérêts perçus +2,826 MDT, colonne « chiffres audités ») ;
    → la version révisée est retenue ;
  - `reclassement` : le total est stable (sous la tolérance) mais des composantes bougent en sens
    inverse au-delà de la tolérance (ex. BIAT 2025 : −0,401 MDT d'intérêts, +0,401 de commissions)
    → la composante prend **la même version que son total**, l'écart est signalé ;
  - vide : écart sous la tolérance ;
  - `exclue (capitaux propres, 31/12 provisoire)` : voir ci-dessous.
  Totaux et composantes : produits = intérêts + commissions + revenus du portefeuille ;
  charges d'exploitation = intérêts encourus + commissions encourues ; PNB = produits − charges ;
  charges opératoires = frais de personnel + charges générales + dotations ; dépôts = à vue +
  épargne + à terme + autres ; portefeuille = commercial + investissement.

  **Capitaux propres : règle fixe, toutes banques.** La colonne 31/12 provisoire n'est jamais
  retenue pour `CAP_PROPRES` : sa définition change d'un document à l'autre (BIAT au 31/12/2025 :
  1 982,5 dans le document T4 2025, résultat non inclus ; 2 367,8 dans le T1 2026, « avant
  affectation du résultat » ; 2 123,0 dans le T2 2026, « après affectation »). La série reste
  homogène : « **Capitaux propres hors résultat de la période** », en version initiale ou
  `revisee_T<q>_N+1`. La définition annoncée par les notes du document est conservée à titre
  d'information (`note_definition` : « avant affectation du résultat », « après affectation du
  résultat », « résultat de la période non inclus »). Le ROE et le ROA n'utilisent pas cet
  indicateur mais les capitaux propres des états financiers (7.7).

  **Comparaison des deux révisions du 31/12** : quand le document T4 de l'année suivante existe,
  il devient la source retenue et la version `revisee_31-12_…` reste comme ligne de comparaison ;
  son écart (`ecart_vs_retenue`) apparaît dans la table `Revisions` et est listé à l'extraction.

  Points à connaître :
  - si le document initial manque mais qu'une version révisée existe, la période n'a que la
    version révisée (valeur réellement publiée, rien n'est estimé) ;
  - la version révisée d'un trimestre n'est pas toujours cohérente avec les versions initiales
    des trimestres voisins : en mélangeant versions, la somme des trimestres peut différer du
    cumul ; on ne corrige pas, on signale.
- **Années et cumuls (flux)** : chiffres annuels et depuis le début de l'année = **cumul**
  (`Valeur_Cumul`, valeur retenue ; l'année = cumul au T4), jamais la somme des trimestres.
  **Analyse trimestrielle** (T/T, A/A d'un trimestre) : **trimestre** (`Valeur_Trim`, valeur retenue).
- **Contrôle « écart trimestre/cumul »** : dans `controle_extraction.csv`, statut
  `ecart trimestre/cumul` quand le trimestre initial publié diffère de plus de 0,1 % de
  « cumul initial du trimestre − cumul initial du trimestre précédent » (PNB, produits, charges
  d'exploitation bancaire, charges opératoires). La page « Qualité des données » liste ces cas,
  ainsi que les révisions (`Revisions`, écart révisée − initiale en MDT).
- **Paramètres** : un paramètre Power Query `CheminDonnees` pour que le dossier soit modifiable.
- **Nommage** : étapes renommées en français (« Types modifiés », « Filtre colonnes utiles »…).
- Désactiver le chargement des requêtes intermédiaires.

## 6. Modèle en étoile

Tables de faits :

- `Fait_Indicateurs` : banque, date_arrete, code_indicateur, Valeur_Trim, Valeur_Cumul
  (valeurs retenues, voir 5.2), Source_Trim, Source_Cumul (« initiale », « revisee_T2_N+1 »,
  « revisee_31-12_T2_N+1 »…)
- `Revisions` (page qualité) : banque, date_arrete, code_indicateur, mesure, version, valeur_mdt,
  valeur_retenue, source_valeur, Ecart_MDT
- `Fait_Cours` : ticker, date, cloture, volume, rendement

Dimensions :

- `Dim_Date` (DAX) : une ligne par jour, de 2019-01-01 à 2026-12-31
- `Dim_Banque` : code, nom, ticker, actionnariat (public / privé tunisien / groupe étranger), groupe
- `Dim_Indicateur` : code, libellé, catégorie (activité, résultat, bilan), nature (flux / stock), ordre

Relations (1 → plusieurs, filtre simple) :

- `Dim_Date[Date]` → `Fait_Indicateurs[date_arrete]`, `Revisions[date_arrete]` et `Fait_Cours[date]`
- `Dim_Banque[code_banque]` → `Fait_Indicateurs[banque]` et `Revisions[banque]`
- `Dim_Banque[ticker_bvmt]` → `Fait_Cours[ticker]`
- `Dim_Indicateur[code_indicateur]` → `Fait_Indicateurs[code_indicateur]`

### Table de dates

```dax
Dim_Date =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2019, 1, 1 ), DATE ( 2026, 12, 31 ) ),
    "Annee", YEAR ( [Date] ),
    "Trimestre", "T" & QUARTER ( [Date] ),
    "Annee_Trimestre", YEAR ( [Date] ) & "-T" & QUARTER ( [Date] ),
    "Cle_Trimestre", YEAR ( [Date] ) * 10 + QUARTER ( [Date] ),
    "Fin_Trimestre", [Date] = EOMONTH ( [Date], 0 ) && MOD ( MONTH ( [Date] ), 3 ) = 0,
    "Periode",
        SWITCH (
            TRUE (),
            [Date] < DATE ( 2020, 3, 1 ), "Avant Covid",
            [Date] < DATE ( 2022, 1, 1 ), "Covid",
            "Après Covid"
        )
)
```

À marquer comme table de dates ; trier `Annee_Trimestre` par `Cle_Trimestre`.
Colonne calculée utile : `EstDernierTrimestre` (le dernier trimestre présent dans les faits).

## 7. Mesures DAX

### 7.1 Bases

```dax
-- Valeur_Trim et Valeur_Cumul sont les valeurs retenues : révisée si elle existe, sinon initiale (5.2)
Valeur Trim  = SUM ( Fait_Indicateurs[Valeur_Trim] )
Valeur Cumul = SUM ( Fait_Indicateurs[Valeur_Cumul] )

-- Flux, analyse trimestrielle : trimestre publié (voir 5.2, règle trimestre / cumul)
PNB              = CALCULATE ( [Valeur Trim], Dim_Indicateur[code_indicateur] = "PNB" )
-- Flux, année et depuis le début de l'année : cumul publié au dernier trimestre de la sélection,
-- jamais la somme des trimestres (les retraitements en cours d'année la rendent fausse)
PNB cumul brut   = CALCULATE ( [Valeur Cumul], Dim_Indicateur[code_indicateur] = "PNB" )
PNB depuis debut annee = CALCULATE ( [PNB cumul brut], LASTNONBLANK ( Dim_Date[Date], [PNB cumul brut] ) )
PNB annuel       = CALCULATE ( [PNB cumul brut], Dim_Date[Trimestre] = "T4" )   -- cumul au 31/12
Charges operatoires = CALCULATE ( [Valeur Trim], Dim_Indicateur[code_indicateur] = "CHG_OPER" )
Frais personnel  = CALCULATE ( [Valeur Trim], Dim_Indicateur[code_indicateur] = "FRAIS_PERS" )
Marge interets   =
    CALCULATE ( [Valeur Trim], Dim_Indicateur[code_indicateur] = "INT_PERCUS" )
  - CALCULATE ( [Valeur Trim], Dim_Indicateur[code_indicateur] = "INT_ENCOURUS" )
Marge commissions =
    CALCULATE ( [Valeur Trim], Dim_Indicateur[code_indicateur] = "COMM_PROD" )
  - CALCULATE ( [Valeur Trim], Dim_Indicateur[code_indicateur] = "COMM_CHG" )
Revenus portefeuille = CALCULATE ( [Valeur Trim], Dim_Indicateur[code_indicateur] = "REV_PORTEF" )

-- Stocks : dernière valeur disponible de la période, jamais la somme
Credits brut = CALCULATE ( [Valeur Cumul], Dim_Indicateur[code_indicateur] = "CREDITS" )
Credits      = CALCULATE ( [Credits brut], LASTNONBLANK ( Dim_Date[Date], [Credits brut] ) )
Depots brut  = CALCULATE ( [Valeur Cumul], Dim_Indicateur[code_indicateur] = "DEPOTS" )
Depots       = CALCULATE ( [Depots brut], LASTNONBLANK ( Dim_Date[Date], [Depots brut] ) )
```

Même modèle pour les dépôts à vue, d'épargne, à terme et les emprunts. Capitaux propres :

```dax
-- jamais la colonne 31/12 provisoire (5.2) : définition homogène, résultat de la période exclu
Capitaux propres hors resultat brut = CALCULATE ( [Valeur Cumul], Dim_Indicateur[code_indicateur] = "CAP_PROPRES" )
Capitaux propres hors resultat de la periode =
    CALCULATE ( [Capitaux propres hors resultat brut],
                LASTNONBLANK ( Dim_Date[Date], [Capitaux propres hors resultat brut] ) )
```

### 7.2 Ratios

```dax
Coef exploitation      = DIVIDE ( [Charges operatoires], [PNB] )
Part marge interets    = DIVIDE ( [Marge interets], [PNB] )
Part commissions       = DIVIDE ( [Marge commissions], [PNB] )
Part portefeuille      = DIVIDE ( [Revenus portefeuille], [PNB] )
Frais personnel / PNB  = DIVIDE ( [Frais personnel], [PNB] )
Credits / Depots       = DIVIDE ( [Credits], [Depots] )
Part depots a vue      = DIVIDE ( [Depots a vue], [Depots] )
```

### 7.3 Intelligence temporelle

```dax
PNB T-1    = CALCULATE ( [PNB], DATEADD ( Dim_Date[Date], -1, QUARTER ) )
PNB A-1    = CALCULATE ( [PNB], SAMEPERIODLASTYEAR ( Dim_Date[Date] ) )
Var PNB T/T % = DIVIDE ( [PNB] - [PNB T-1], [PNB T-1] )
Var PNB A/A % = DIVIDE ( [PNB] - [PNB A-1], [PNB A-1] )
PNB cumul annee = [PNB depuis debut annee]   -- cumul publié, pas TOTALYTD des trimestres (voir 5.2)
-- 4 trimestres glissants : somme des trimestres publiés (peut différer légèrement d'un cumul,
-- voir 5.2) ; à afficher comme indicateur de tendance, pas comme chiffre annuel
PNB 4T glissants =
    CALCULATE ( [PNB], DATESINPERIOD ( Dim_Date[Date], MAX ( Dim_Date[Date] ), -12, MONTH ) )
TCAM PNB 2020-2025 =
VAR Debut = CALCULATE ( [PNB annuel], REMOVEFILTERS ( Dim_Date ), Dim_Date[Annee] = 2020 )
VAR Fin   = CALCULATE ( [PNB annuel], REMOVEFILTERS ( Dim_Date ), Dim_Date[Annee] = 2025 )
RETURN IF ( Debut > 0, ( Fin / Debut ) ^ ( 1 / 5 ) - 1 )
Depots A-1 = CALCULATE ( [Depots], SAMEPERIODLASTYEAR ( Dim_Date[Date] ) )
Var Depots A/A % = DIVIDE ( [Depots] - [Depots A-1], [Depots A-1] )
```

### 7.4 Comparaison au secteur

```dax
PNB secteur          = CALCULATE ( [PNB], REMOVEFILTERS ( Dim_Banque ) )
Part de marche PNB   = DIVIDE ( [PNB], [PNB secteur] )
Part de marche depots = DIVIDE ( [Depots], CALCULATE ( [Depots], REMOVEFILTERS ( Dim_Banque ) ) )
HHI PNB              = SUMX ( ALL ( Dim_Banque ), [Part de marche PNB] ^ 2 ) * 10000
Coef secteur         = CALCULATE ( [Coef exploitation], REMOVEFILTERS ( Dim_Banque ) )   -- moyenne pondérée
Coef mediane         = MEDIANX ( ALL ( Dim_Banque ), [Coef exploitation] )
Ecart coef / mediane = [Coef exploitation] - [Coef mediane]
Rang coef            = RANKX ( ALL ( Dim_Banque ), [Coef exploitation],, ASC, DENSE )
Rang PNB             = RANKX ( ALL ( Dim_Banque ), [PNB],, DESC, DENSE )
```

### 7.5 Bourse

```dax
Cours brut      = SUM ( Fait_Cours[cloture] )
Dernier cours   = CALCULATE ( [Cours brut], LASTNONBLANK ( Dim_Date[Date], [Cours brut] ) )
Premier cours   = CALCULATE ( [Cours brut], FIRSTNONBLANK ( Dim_Date[Date], [Cours brut] ) )
Performance periode = DIVIDE ( [Dernier cours], [Premier cours] ) - 1
Volatilite annualisee = STDEV.S ( Fait_Cours[rendement] ) * SQRT ( 252 )
```

### 7.7 Rentabilité : ROE et ROA

**Pourquoi une source de plus.** Le ROE et le ROA ont besoin du **résultat net**, qui n'est pas
dans les indicateurs trimestriels. Il est publié dans les **états financiers** :

- annuels (au 31/12, audités), de 2019 à 2025 ;
- intermédiaires (au 30/06, revue limitée des commissaires aux comptes), de 2020 à 2026.

Le ROE et le ROA sont donc **semestriels et annuels**, pas trimestriels. Il faut le dire
clairement dans le rapport.

**Données à collecter** pour chaque banque et chaque date (30/06 et 31/12) :

| Code | Donnée | Où la trouver |
|---|---|---|
| `RES_NET` | Résultat net de la période (cumul depuis le 1er janvier) | État de résultat |
| `TOTAL_ACTIF` | Total de l'actif | Bilan |
| `CAP_PROPRES_EF` | Capitaux propres **y compris le résultat de la période** | Bilan |

Remarque : les capitaux propres des indicateurs trimestriels sont souvent publiés
« compte non tenu des résultats de la période ». On utilise donc ceux du bilan pour le ROE.

Soit environ 12 banques × 13 dates × 3 valeurs ≈ 470 valeurs, collectées par
`scripts/etats_financiers.py` :

1. Téléchargement des états financiers individuels sur le site de la BVMT
   (`.../etats-financiers/<préfixe>-etats-financiers-annuels-individuels-31-12-AAAA.pdf`,
   `...-semestriels-30-06-AAAA.pdf`), avec en option la recherche dans les Bulletins Officiels du CMF.
   Les comptes consolidés sont écartés.
2. Extraction des lignes « Total actif », « Total capitaux propres » et « Résultat net de
   l'exercice / de la période », en ignorant la colonne des notes.
3. Contrôles : total actif = total capitaux propres et passif ; capitaux propres < total actif ;
   résultat net < capitaux propres.
4. Comparaison du résultat net annuel avec le tableau annuel d'ilboursa (écart > 1 % signalé).

Les valeurs que le script ne trouve pas sont saisies à la main dans
`donnees/corrections_manuelles.csv`, avec le fichier source et la page.

Sortie : `donnees/etats_financiers_long.csv`.

Table de faits `Fait_Etats_Financiers` : banque, date_arrete, type (semestriel / annuel),
code, valeur_mdt, fichier, page (dans Power Query, garder `colonne = "N"` ; la colonne `N1`
sert seulement aux contrôles). Relations : `Dim_Banque` et `Dim_Date` comme les autres faits.

**Définitions retenues :**

- ROE = résultat net annualisé / capitaux propres moyens
- ROA = résultat net annualisé / total de l'actif moyen
- Annualisation : × 2 pour un résultat au 30/06, × 1 au 31/12
- Moyenne = (valeur à l'ouverture de l'exercice + valeur à la date) / 2

**Mesures :**

```dax
Resultat net brut = CALCULATE ( SUM ( Fait_Etats_Financiers[valeur_mdt] ),
                        Fait_Etats_Financiers[code] = "RES_NET" )
Resultat net = CALCULATE ( [Resultat net brut],
                   LASTNONBLANK ( Dim_Date[Date], [Resultat net brut] ) )
Resultat net annualise =
VAR DateRes = CALCULATE ( MAX ( Fait_Etats_Financiers[date_arrete] ),
                  Fait_Etats_Financiers[code] = "RES_NET" )
RETURN [Resultat net] * IF ( MONTH ( DateRes ) = 6, 2, 1 )

Cap propres EF brut = CALCULATE ( SUM ( Fait_Etats_Financiers[valeur_mdt] ),
                          Fait_Etats_Financiers[code] = "CAP_PROPRES_EF" )
Cap propres fin = CALCULATE ( [Cap propres EF brut],
                      LASTNONBLANK ( Dim_Date[Date], [Cap propres EF brut] ) )
Cap propres ouverture =
VAR DateFin = CALCULATE ( MAX ( Fait_Etats_Financiers[date_arrete] ),
                  Fait_Etats_Financiers[code] = "CAP_PROPRES_EF" )
RETURN CALCULATE ( [Cap propres EF brut], REMOVEFILTERS ( Dim_Date ),
           Dim_Date[Date] = DATE ( YEAR ( DateFin ) - 1, 12, 31 ) )
Cap propres moyens = AVERAGEX ( { [Cap propres ouverture], [Cap propres fin] }, [Value] )

ROE = DIVIDE ( [Resultat net annualise], [Cap propres moyens] )
```

Même logique pour le total de l'actif et le ROA :

```dax
ROA = DIVIDE ( [Resultat net annualise], [Total actif moyen] )
```

Visuels : ROE et ROA par banque (barres), évolution semestrielle (courbes), matrice
ROE × coefficient d'exploitation, ROE face à la performance boursière.

Limites : résultat semestriel non audité (revue limitée) ; l'annualisation × 2 ignore la
saisonnalité ; certaines banques publient des comptes consolidés et individuels — on prend
toujours les **comptes individuels** pour rester cohérent avec les indicateurs trimestriels.

### 7.8 Affichage et qualité

```dax
Date derniere donnee = CALCULATE ( MAX ( Fait_Indicateurs[date_arrete] ), REMOVEFILTERS () )
Titre rapport = "Banques cotées — données au " & FORMAT ( [Date derniere donnee], "dd/mm/yyyy" )
Couleur coef  = IF ( [Ecart coef / mediane] <= 0, "#2E7D32", "#C62828" )
Nb documents  = COUNTROWS ( Controle )
Taux extraction ok = DIVIDE ( CALCULATE ( [Nb documents], Controle[statut] = "ok" ), [Nb documents] )
Nb ecarts trim cumul = CALCULATE ( [Nb documents], Controle[statut] = "ecart trimestre/cumul" )
-- versions : part des valeurs affichées qui viennent d'une révision, et révisions significatives
Part cumuls revises =
    DIVIDE ( CALCULATE ( COUNTROWS ( Fait_Indicateurs ),
                         LEFT ( Fait_Indicateurs[Source_Cumul], 7 ) = "revisee" ),
             CALCULATE ( COUNTROWS ( Fait_Indicateurs ), NOT ISBLANK ( Fait_Indicateurs[Source_Cumul] ) ) )
Part 31-12 provisoires =
    DIVIDE ( CALCULATE ( COUNTROWS ( Fait_Indicateurs ),
                         LEFT ( Fait_Indicateurs[Source_Cumul], 14 ) = "revisee_31-12_" ),
             CALCULATE ( COUNTROWS ( Fait_Indicateurs ), NOT ISBLANK ( Fait_Indicateurs[Source_Cumul] ) ) )
Nb revisions = CALCULATE ( COUNTROWS ( Revisions ), ABS ( Revisions[Ecart_MDT] ) > 0.002 )
Nb corrections   = CALCULATE ( COUNTROWS ( Revisions ), Revisions[statut_revision] = "correction" )
Nb reclassements = CALCULATE ( COUNTROWS ( Revisions ), Revisions[statut_revision] = "reclassement" )
Ecart revision MDT = SUM ( Revisions[Ecart_MDT] )
Nb annees en attente = CALCULATE ( COUNTROWS ( Controle_Annuel ), Controle_Annuel[statut] = "en attente de révision" )
Nb ecarts annuels    = CALCULATE ( COUNTROWS ( Controle_Annuel ), Controle_Annuel[statut] = "ecart" )
```

Paramètre de champ « Indicateur affiché » : PNB, Coef exploitation, Crédits / Dépôts,
Part de marché, Var A/A % — pour un seul visuel où l'utilisateur choisit l'indicateur.

## 8. Ajouts par rapport au rapport de référence

1. Historique de 27 trimestres au lieu d'une seule date.
2. Valeurs trimestrielles et cumulées, et contrôle entre les deux.
3. Comparaison à la médiane et à la moyenne pondérée du secteur, rangs.
4. Segmentation par actionnariat (public, privé tunisien, groupe étranger).
5. Matrice de positionnement : croissance du PNB × coefficient d'exploitation.
6. Concentration du secteur (HHI) et parts de marché PNB et dépôts.
7. Périodes Avant Covid / Covid / Après Covid.
8. Volet boursier : performance et volatilité face aux indicateurs.
9. Page « qualité des données » : documents trouvés, extraits, à vérifier.
10. Pipeline reproductible : script Python + Power Query paramétré + sources CSV, Excel et URL.
11. Rentabilité (ROE, ROA) à partir des états financiers, croisée avec l'efficacité et la Bourse.

## 9. Pages du rapport

| Page | Contenu |
|---|---|
| 1. Vue d'ensemble | Cartes (PNB secteur, coef secteur, dépôts, crédits), titre dynamique, part de marché PNB, HHI dans le temps |
| 2. Classement | Tableau des banques avec rangs et mise en forme conditionnelle, matrice croissance × coef |
| 3. Évolution 2020–2026 | Courbes par banque avec sélecteur d'indicateur, bandes de périodes Covid |
| 4. Structure du PNB | Barres empilées marge d'intérêts / commissions / portefeuille par banque |
| 5. Bilan | Crédits, dépôts, crédits / dépôts, structure des dépôts |
| 6. Bourse | Cours, performance, volatilité, performance boursière vs croissance du PNB |
| 7. Fiche banque (extraction) | Tous les indicateurs d'une banque, accessible par clic droit |
| 8. Rentabilité | ROE et ROA semestriels et annuels, matrice ROE × coefficient d'exploitation |
| 9. Qualité des données | Contrôle d'extraction (statuts, dont `ecart trimestre/cumul` et `retraitement possible`, avec l'écart en MDT), sources, limites ; phrase expliquant pourquoi la somme des trimestres peut différer du cumul annuel |

Filtres : segments Année / Trimestre, plage de dates, banque, actionnariat, période ;
info-bulles personnalisées ; signets « trimestre » / « année ».

## 10. Limites à mentionner dans le rapport

- Données provisoires, non auditées, publiées par les banques elles-mêmes.
- Retraitements en cours d'année : la somme des trimestres publiés peut différer du cumul
  annuel publié ; les chiffres annuels viennent toujours du cumul (voir 5.2).
- Définitions des postes parfois différentes d'une banque à l'autre.
- ROE et ROA seulement en semestriel et annuel ; résultats semestriels non audités, annualisés.
- Les valeurs extraites automatiquement ont été contrôlées par échantillon (voir `docs/validation.md`).
