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
- Certaines banques retraitent l'année précédente : on garde le chiffre de l'année N
  tel que publié dans le document de l'année N.

## 4. Pipeline

```
PDF (BVMT, CMF, bulletins officiels)
   └─ collecte_banques.py ──> donnees/indicateurs_banques_long.csv
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
| `Fait_Indicateurs` | CSV long | types (paramètres régionaux en-US), filtre `colonne` ∈ {trim_N, cumul_N}, pivot de `colonne` → colonnes `Valeur_Trim` et `Valeur_Cumul`, ajout de `Valeur_Trim_Calculee` |
| `Dim_Banque` | `dim_banque.csv` + Excel | fusion avec l'onglet Excel (actionnariat, groupe), nettoyage |
| `Dim_Indicateur` | `dim_indicateur.csv` | types, ordre de tri |
| `Fait_Cours` | Dossier de CSV cours | combinaison des fichiers, types, suppression des doublons, colonne `Rendement` (variation du cours d'un jour à l'autre) |
| `Controle` | `controle_extraction.csv` | pour la page « qualité des données » |
| `Corrections` | `corrections_manuelles.csv` | remplacement des valeurs corrigées dans `Fait_Indicateurs` |

### 5.2 Points d'attention

- **Valeur du trimestre seul** : les banques publient le trimestre seul (`trim_N`) et le cumul.
  Recalculer aussi `cumul(T) − cumul(T−1)` (même année, T > 1) et comparer : un écart signale
  une erreur d'extraction ou un retraitement.
- **Paramètres** : un paramètre Power Query `CheminDonnees` pour que le dossier soit modifiable.
- **Nommage** : étapes renommées en français (« Types modifiés », « Filtre colonnes utiles »…).
- Désactiver le chargement des requêtes intermédiaires.

## 6. Modèle en étoile

Tables de faits :

- `Fait_Indicateurs` : banque, date_arrete, code_indicateur, Valeur_Trim, Valeur_Cumul
- `Fait_Cours` : ticker, date, cloture, volume, rendement

Dimensions :

- `Dim_Date` (DAX) : une ligne par jour, de 2019-01-01 à 2026-12-31
- `Dim_Banque` : code, nom, ticker, actionnariat (public / privé tunisien / groupe étranger), groupe
- `Dim_Indicateur` : code, libellé, catégorie (activité, résultat, bilan), nature (flux / stock), ordre

Relations (1 → plusieurs, filtre simple) :

- `Dim_Date[Date]` → `Fait_Indicateurs[date_arrete]` et `Fait_Cours[date]`
- `Dim_Banque[code_banque]` → `Fait_Indicateurs[banque]`
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
Valeur Trim  = SUM ( Fait_Indicateurs[Valeur_Trim] )
Valeur Cumul = SUM ( Fait_Indicateurs[Valeur_Cumul] )

-- Flux : on additionne les trimestres seuls, donc une année = somme de ses 4 trimestres
PNB              = CALCULATE ( [Valeur Trim], Dim_Indicateur[code_indicateur] = "PNB" )
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

Même modèle pour les dépôts à vue, d'épargne, à terme, les capitaux propres et les emprunts.

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
PNB cumul annee = TOTALYTD ( [PNB], Dim_Date[Date] )
PNB 4T glissants =
    CALCULATE ( [PNB], DATESINPERIOD ( Dim_Date[Date], MAX ( Dim_Date[Date] ), -12, MONTH ) )
TCAM PNB 2020-2025 =
VAR Debut = CALCULATE ( [PNB], REMOVEFILTERS ( Dim_Date ), Dim_Date[Annee] = 2020 )
VAR Fin   = CALCULATE ( [PNB], REMOVEFILTERS ( Dim_Date ), Dim_Date[Annee] = 2025 )
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
| 9. Qualité des données | Contrôle d'extraction, sources, limites |

Filtres : segments Année / Trimestre, plage de dates, banque, actionnariat, période ;
info-bulles personnalisées ; signets « trimestre » / « année ».

## 10. Limites à mentionner dans le rapport

- Données provisoires, non auditées, publiées par les banques elles-mêmes.
- Définitions des postes parfois différentes d'une banque à l'autre.
- ROE et ROA seulement en semestriel et annuel ; résultats semestriels non audités, annualisés.
- Les valeurs extraites automatiquement ont été contrôlées par échantillon (voir `docs/validation.md`).
