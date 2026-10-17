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
| `Fait_Indicateurs` | référence à `Versions` | filtre `version = source_valeur` (une ligne par banque × trimestre × indicateur × mesure) ; suppression de `valeur_mdt`, `version` ; pivot de `mesure` sur `valeur_retenue` → `Valeur_Trim` et `Valeur_Cumul` ; pivot de `mesure` sur `source_valeur` → `Source_Trim` et `Source_Cumul` ; pivot de `mesure` sur `rupture_serie` → `Rupture_Trim` et `Rupture_Cumul` (« oui » : période révisée de plus de 2 % sur le cumul, marqueur des graphiques) |
| `Revisions` | référence à `Versions` | filtre `version <> source_valeur` (versions non retenues : initiales révisées, 31/12 provisoires remplacés par le T4 suivant, 31/12 exclus pour les capitaux propres) ; colonnes `banque`, `date_arrete`, `code_indicateur`, `mesure`, `version`, `valeur_mdt`, `valeur_retenue`, `source_valeur`, `statut_revision` (retraitement_mineur / revision_importante / reclassement / exclue / illisible (image) / non disponible (image)), `note_definition`, `mention_retraitement`, `Ecart_MDT = valeur_retenue − valeur_mdt` ; pour la page « qualité des données » |
| `Controle_Annuel` | `controle_annuel.csv` | types ; somme des trimestres vs cumul T4, statut (`ok`, `en attente de révision`, `rupture de série`, `ecart`) |
| `Variations_Comparables` | `variations_comparables.csv` | types ; une ligne par banque × trimestre × indicateur × mesure (`trim` / `cumul`) : `valeur_N`, `valeur_N1` **du même document**, `variation_pct` ; source de toutes les variations sur un an (7.3) |
| `Dim_Banque` | `dim_banque.csv` + Excel | fusion avec l'onglet Excel (actionnariat, groupe), nettoyage |
| `Dim_Indicateur` | `dim_indicateur.csv` | types, ordre de tri |
| `Fait_Cours` | Dossier de CSV cours | combinaison des fichiers, types, suppression des doublons, colonne `Rendement` (variation du cours d'un jour à l'autre) |
| `Controle` | `controle_extraction.csv` | pour la page « qualité des données » |
| `Corrections` | `corrections_manuelles.csv` | remplacement des valeurs corrigées dans `Fait_Indicateurs` |
| `Evenements` | `evenements.csv` (versionné, à la racine) | types ; une ligne par événement et par banque concernée : `id_evenement`, `date` (fin du trimestre concerné), `banque`, `indicateur`, `description`, `montant_mdt` (montant cité par le document), `fichier`, `page` ; annotations des graphiques (7.3, pages 3 et 9) |
| `Definitions_Charges` | `gabarits.csv` | colonnes `banque`, `premier_trimestre`, `dernier_trimestre`, `definition_charges_operatoires` (lignes distinctes) ; info-bulle du coefficient publié et page « qualité des données » |

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
  4. **Révisions : la version révisée est toujours retenue** (règle du 17/10/2026, la troisième ;
     voir plus bas pourquoi les deux premières ont été abandonnées). Les niveaux prennent la
     version révisée quand elle existe (priorité des règles 1 à 3), **avec ou sans note de
     retraitement** ; la note est gardée pour information (`mention_retraitement`, première ligne
     des 12 premières pages qui parle de « comparabilité », de « chiffres retraités » ou de
     « retraitement »). La révision est **qualifiée**, pas écartée :

     | Écart révisée − initiale, mesuré sur le **cumul** de la période | Statut (`statut_revision`) | Graphiques |
     |---|---|---|
     | ≤ 2 kDT (arrondi) | vide | — |
     | ≤ 2 % du cumul initial | `retraitement_mineur` | — |
     | > 2 % du cumul initial | `revision_importante` | `rupture_serie` = « oui », `detail_rupture` |

     - L'écart se mesure **sur le cumul** (solde pour un stock) et le statut vaut **pour le
       trimestre et le cumul** de la même période et de la même version : un trimestre seul,
       petit montant, dépasse vite 2 % sans que l'année change (BH, PNB du T4 2023 : −2,8 % sur le
       trimestre, −0,9 % sur l'année → `retraitement_mineur`). Le cumul n'est pas publié pour une
       période : on prend le trimestre.
     - Totaux concernés : PNB, produits d'exploitation bancaire, charges d'exploitation bancaire,
       charges opératoires, crédits, dépôts (même règle pour les indicateurs sans composantes :
       autres produits, portefeuille, emprunts, capitaux propres). Les **composantes** prennent le
       statut de leur total pour la même version ; total stable (sous l'arrondi) mais composante
       qui bouge → `reclassement`.
     - **Rupture de série** : marquée sur la période révisée elle-même (trimestre et cumul), pour
       annoter les graphiques (« PNB 2024 révisé de −8,5 % : 765,9 publié, 701,2 dans le document
       T4 2025 »). Elle ne change aucune valeur.
     - Seuil : constante `SEUIL_MATERIALITE = 0.02` dans le script ; c'est un choix d'analyse,
       pas une norme.
     - Exemples : BH, PNB 2024 = **701,188** MDT retenu (T4 2025, −8,5 % : `revision_importante`) ;
       UIB, PNB 2025 = 525,528 MDT (31/12 du T2 2026, +0,55 % : `retraitement_mineur`) ;
       BT, charges opératoires du T3 2020 = 26,011 MDT (T3 2021) au lieu des 12,076 publiés, chiffre
       incohérent avec ses composantes (voir plus bas, don au Fonds 1818).

     **Pourquoi les règles précédentes ont été abandonnées.** Règle 1 (17/10/2026) : garder la
     version initiale dès qu'un document annonçait un retraitement. Règle 2 (même jour) : la garder
     seulement si l'écart dépassait 2 % et que le document l'annonçait. La liste des 60 cas
     « changement de méthode » de la règle 2 a montré que garder l'initiale créait plus de
     problèmes qu'elle n'en réglait :
     - elle gardait des valeurs fausses : BT, charges opératoires du T3 2020, 12,076 MDT publié
       (le don au Fonds 1818 retiré du seul trimestre), corrigé à 26,011 un an plus tard ;
     - elle dépendait de la rédaction de la banque : la note « chiffres retraités pour les
       besoins de comparabilité » est une formule de routine (sept banques l'écrivent presque
       chaque année) et l'ATB retraite sans jamais l'écrire ;
     - elle mélangeait trimestre et cumul : le seuil appliqué mesure par mesure gardait l'initiale
       pour le trimestre et la révisée pour le cumul d'une même période ;
     - elle n'était plus utile : toutes les croissances viennent de `Variations_Comparables`
       (colonne N contre colonne N-1 d'un même document), qui ne dépend pas du choix des niveaux.

     **Causes communes constatées (charges opératoires 2020 et 2021).**
     - 2020 : le **don au Fonds national de lutte contre le Covid-19 (« Fonds 1818 »)**,
       comptabilisé dans les charges générales du premier semestre 2020 puis sorti des charges
       opératoires dans les chiffres 2020 redonnés en 2021 (et déjà dans le cumul du T4 2020). BT :
       ligne « Don Fds 1818 / Covid19 » de 11 350 kDT au premier semestre 2020 (PDF du T2 2020),
       charges générales du semestre révisées de −11,351 MDT ; BH : « cotisation de la banque pour la
       lutte contre le COVID-19 pour un montant de 11.4 MDT » et une taxe conjoncturelle de 0,8 MD,
       charges générales révisées de −12,426 MDT ; BNA : contribution de 11,4 MD au Fonds, charges
       générales révisées de −16,256 MDT (le reste n'est pas expliqué). Le T3 2020 de la BT
       (12,076 MDT, statut `ecart composantes`) est le trimestre dont on a retiré le don.
     - 2021 : l'**accord salarial APTBEF–FGBEF** (augmentation des salaires, indemnité de départ
       à la retraite portée de six à douze mois de salaire, notes BNA du T3 et du T4 2021, BT du
       T4 2021), comptabilisé en fin d'année et réparti sur le premier semestre 2021 dans les
       chiffres redonnés en 2022 : frais de personnel révisés de +6,680 MDT (BH), +12,766 MDT
       (BNA), +3,645 MDT (BT).
     - Attijari : pas de note sur le Fonds 1818 ; sa révision des charges opératoires 2020
       (+10,8 MDT pour l'année) vient du changement de contenu du T4 2021 (reste non détaillé
       ajouté, colonnes N-1 retraitées, voir `gabarits.csv`). Le premier semestre 2021 manque
       (document 2021T2 non trouvé).

  **Document illisible** : un tableau publié en image (BH 2019T4, page 1 : 252 caractères de
  texte, 2 images) a le statut `illisible (image)` dans `controle_extraction.csv` ; sa version
  initiale figure dans `indicateurs_versions.csv` sans valeur, statut `illisible (image)`, et la
  valeur retenue vient des colonnes N-1 du document de l'année suivante (BH 2020T4, « (*) Chiffres
  retraités » : PNB 2019 = 492,929 MDT, PNB du T4 2019 = 156,644 MDT). Pas de saisie manuelle tant
  que le document suivant donne les chiffres. Seuil de détection : page avec images et moins de
  1 000 caractères de texte. **BTE** : 13 documents dans ce cas (2020T1 à 2023T4, sauf 2022T2,
  2023T1 et 2023T3) ; repris par le document suivant : 2021T2, 2022T1, 2022T3, 2023T2, 2023T4 en
  entier, 2021T4 et 2022T4 pour le cumul annuel et les soldes seulement ; **non repris : 2020T1 à
  2020T4, 2021T1 et 2021T3** (le document de l'année suivante est lui aussi une image) : saisie
  manuelle décidée le 17/10/2026, voir ci-dessous.

  **Saisie manuelle** (`saisies_manuelles.csv`, versionné, à la racine) : seulement pour les
  documents illisibles que le document suivant ne reprend pas, et seulement pour les indicateurs
  du rapport (PNB, produits et charges d'exploitation bancaire, frais de personnel, charges
  générales, charges opératoires, crédits, dépôts), toutes les colonnes du tableau (N, N-1,
  31/12/N-1). Chaque valeur porte `fichier`, `page` et `verification` : « lecture image +
  contrôles de cohérence » (relevé sur l'image du tableau rendue à 200–220 dpi), ou « vérifié par
  Ahmed » quand l'utilisateur l'a contrôlée lui-même (`scripts/verification_saisie.py preparer`
  puis `reporter`). À l'extraction, la saisie remplace le document illisible (statut `saisie
  manuelle` dans `controle_extraction.csv`, colonnes `source` = « saisie manuelle » et
  `verification` dans les données) et passe les contrôles de l'extraction plus un contrôle strict
  (produits − charges = PNB à 2 kDT près dans chaque colonne) ; une alerte la met en
  `a verifier`. Contrôles faits pendant la saisie BTE (6 documents, 208 valeurs, aucune erreur) :
  produits − charges = PNB, charges opératoires = frais de personnel + charges générales,
  colonne « Variation montant » du PDF = cumul N − cumul N-1, dépôts = somme des quatre
  catégories ; les trimestres 2020T3 sont confirmés par la colonne N-1 du document 2021T3.
  BTE 2020T2 : 36 valeurs relues indépendamment, `verification` = « vérifié par Ahmed Ben Arfa ».
  **Saisie partielle** d'un document lisible : quand quelques valeurs sont illisibles dans le texte
  du PDF (STB 2026T2 : revenus du portefeuille du trimestre superposés à leur libellé ; l'extraction
  laissait le T2 2026 vide et lisait 893 522 au lieu de 115 893 522 pour le T2 2025), les valeurs
  saisies remplacent ou complètent celles extraites (colonne `source` = « saisie manuelle » sur ces
  lignes), le document garde son statut, et le contrôle strict ajoute : intérêts + commissions +
  revenus du portefeuille = produits dans chaque colonne.

  **Valeur non disponible** : quand un document est illisible et qu'aucun autre ne reprend une
  mesure (BTE : T4 seul de 2021 et de 2022, le document T4 de l'année suivante étant aussi une
  image), `indicateurs_versions.csv` porte une ligne `statut_revision` = « non disponible (image) »,
  sans valeur ni valeur retenue. Elle apparaît dans `Revisions` (page « qualité des données »),
  jamais dans `Fait_Indicateurs` : la valeur reste vide dans les graphiques, jamais à zéro (aucune
  mesure DAX ne doit remplacer un vide par 0, pas de `+ 0` ni de `COALESCE ( …, 0 )` sur les
  valeurs ; le contrôle annuel saute ces années).

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
  - `rupture de série` : l'année contient une `revision_importante` (règle 4) et la somme des
    trimestres retenus ne retrouve pas le cumul. Signalé, pas corrigé ;
  - `ecart` : à examiner.

  Vérifié sur 2025 : avec les trimestres retenus, la somme des 4 trimestres égale le cumul T4
  **initial** exactement pour BIAT ; le cumul retenu étant le 31/12 provisoire (document T2 2026),
  les 4 contrôles BIAT 2025 sont `en attente de révision` (ex. charges opératoires : 723,988 MDT en
  initial, 711,102 MDT au 31/12 provisoire). UIB 2025 : de même `en attente de révision` (PNB :
  522,651 MDT initial, 525,528 MDT au 31/12 provisoire, `retraitement_mineur`).

  **Nature de chaque révision** (`statut_revision` dans `indicateurs_versions.csv` ; chaque version
  révisée comparée à l'initiale, règle 4 ; la version initiale remplacée prend la nature de la
  version retenue ; tolérance d'arrondi : 2 milliers de dinars) :
  - `retraitement_mineur` : cumul révisé de 2 % au plus (ex. PNB UIB 2025 +0,55 %) ;
  - `revision_importante` : cumul révisé de plus de 2 % (ex. ATB, PNB 2019 : 252,236 → 239,420,
    −5,1 % ; BH, PNB 2024 −8,5 %) → rupture de série marquée ;
  - `reclassement` : le total est stable (sous la tolérance) mais des composantes bougent
    (ex. BIAT 2025 : −0,401 MDT d'intérêts, +0,401 de commissions) → la composante prend
    **la même version que son total**, l'écart est signalé ;
  - vide : écart sous la tolérance ;
  - `exclue (capitaux propres, 31/12 provisoire)` : voir ci-dessous ;
  - `exclue (colonne incohérente : …)` et `exclue (exclusion écrite : …)` : colonne N-1 non retenue,
    voir ci-dessous ;
  - `illisible (image)` : version initiale d'un document dont le tableau est une image.
  Totaux et composantes : produits = intérêts + commissions + revenus du portefeuille ;
  charges d'exploitation = intérêts encourus + commissions encourues ; PNB = produits − charges ;
  charges opératoires = composantes publiées (voir 7.2, coefficient d'exploitation) ; dépôts = à vue +
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

  **Colonnes N-1 non retenues (décision du 17/10/2026).** Une colonne de comparaison
  (`trim_N1`, `cumul_N1`, `exercice_N1`) fausse dans le document de la banque ne devient jamais
  la valeur retenue, pour aucun indicateur ; ses valeurs restent dans `indicateurs_versions.csv`
  avec le statut `exclue (…)` et la raison, et aucune variation n'est calculée avec elle
  (`variations_comparables.csv`). Deux sources :
  - règle automatique : produits − charges d'exploitation ≠ PNB (écart de plus de 2 %) dans la
    colonne. Seul cas sur les 12 banques au 17/10/2026 : UIB 2023T2, colonne T2 2022 (charges
    d'exploitation 125 105 = cumul du semestre ; UIB_2022T2.pdf publie 63 933) ;
  - exclusion écrite dans `exclusions_colonnes.csv` (versionné : banque, trimestre du document,
    colonne, raison, fichier, page), pour une erreur que les contrôles ne voient pas. Seul cas :
    WIB 2023T4, colonne T4 2022 recopiée du T3 2022 (13 indicateurs identiques à ceux de
    WIB_2023T3_bulletin.pdf, PNB 14 455 ; WIB_2022T4_bulletin.pdf publie 17 536).
  La période garde alors la version suivante dans l'ordre de priorité (ici la version initiale).
  Effet de bord connu : une vraie révision contenue dans la colonne exclue est perdue avec elle
  (UIB, PNB du T2 2022 retraité de +0,170 MDT) ; le contrôle annuel 2022 de l'UIB signale l'écart
  (somme des trimestres ≠ cumul révisé, de 0,04 à 0,17 MDT).

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
  **Analyse trimestrielle** (niveaux, T/T) : **trimestre** (`Valeur_Trim`, valeur retenue).
- **Variations sur un an** (PNB, charges, crédits, dépôts… ; trimestre, cumul ou solde) :
  calculées **à l'intérieur d'un même document**, colonne N contre colonne N-1
  (`variations_comparables.csv` → `Variations_Comparables`), jamais en rapprochant deux documents.
  Les deux chiffres sont publiés ensemble, dans la même méthode : la variation reste juste quand la
  banque retraite N-1 (BH 2025 : PNB 681,479 contre 701,188 retraité, −2,8 %, comme la colonne
  « Var » du PDF ; avec le 765,932 publié un an plus tôt, on obtiendrait −11,0 %).
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
  « revisee_31-12_T2_N+1 »…), Rupture_Trim, Rupture_Cumul (« oui » sur une période révisée de plus
  de 2 % sur le cumul)
- `Variations_Comparables` : banque, date_arrete, code_indicateur, mesure (`trim` / `cumul`),
  valeur_N, valeur_N1 (même document), variation_pct, fichier, page, mention_retraitement ; source
  de toutes les variations sur un an
- `Evenements` (annotations) : id_evenement, date, banque, indicateur, description, montant_mdt,
  fichier, page
- `Revisions` (page qualité) : banque, date_arrete, code_indicateur, mesure, version, valeur_mdt,
  valeur_retenue, source_valeur, Ecart_MDT
- `Fait_Cours` : ticker, date, cloture, volume, rendement

Dimensions :

- `Dim_Date` (DAX) : une ligne par jour, de 2019-01-01 à 2026-12-31
- `Dim_Banque` : code, nom, ticker, actionnariat (public / privé tunisien / groupe étranger), groupe
- `Dim_Indicateur` : code, libellé, catégorie (activité, résultat, bilan), nature (flux / stock), ordre

Relations (1 → plusieurs, filtre simple) :

- `Dim_Date[Date]` → `Fait_Indicateurs[date_arrete]`, `Variations_Comparables[date_arrete]`,
  `Revisions[date_arrete]` et `Fait_Cours[date]`
- `Dim_Banque[code_banque]` → `Fait_Indicateurs[banque]`, `Variations_Comparables[banque]` et `Revisions[banque]`
- `Dim_Banque[ticker_bvmt]` → `Fait_Cours[ticker]`
- `Dim_Indicateur[code_indicateur]` → `Fait_Indicateurs[code_indicateur]` et `Variations_Comparables[code_indicateur]`
- `Dim_Date[Date]` → `Evenements[date]`, `Dim_Banque[code_banque]` → `Evenements[banque]`,
  `Dim_Indicateur[code_indicateur]` → `Evenements[indicateur]` (annotations filtrées comme les courbes)

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
Charges generales = CALCULATE ( [Valeur Trim], Dim_Indicateur[code_indicateur] = "CHG_GEN" )
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

**Deux coefficients d'exploitation.** Les charges opératoires publiées n'ont pas le même contenu
d'une banque à l'autre (colonne `definition_charges_operatoires` de `gabarits.csv`) :

| Valeur | Contenu du total publié | Exemples |
|---|---|---|
| `sans dotations` | frais de personnel + charges générales d'exploitation | BT, BH, BTE, STB, TJARI jusqu'au T3 2021 |
| `avec dotations publiees` | frais de personnel + charges générales + dotations aux amortissements, trois lignes publiées | WIB (« Dotations aux amortissements et aux provisions sur immobilisations »), UIB |
| `avec reste non detaille` | plus que frais de personnel + charges générales ; la différence (dotations ou autres) n'est pas détaillée | BNA, ATB, AB, BIAT, TJARI à partir du T4 2021 (colonnes N-1 retraitées) |
| `composantes non publiees` | seul le total est publié | |

- **Coefficient harmonisé** = (frais de personnel + charges générales d'exploitation) / PNB.
  Même définition pour toutes les banques qui publient ces deux lignes. **Les classements et
  comparaisons entre banques (rang, médiane, secteur, matrices, couleurs) utilisent ce coefficient.**
  Il est calculé banque par banque et trimestre par trimestre, seulement là où les deux
  composantes et le PNB sont publiés ; le PNB du dénominateur est pris sur les mêmes lignes
  (une banque sans composantes ne fausse pas le coefficient du secteur). Il est plus bas que le
  coefficient publié quand le total publié comprend les dotations.
- **Coefficient publié** = charges opératoires publiées / PNB : affiché pour information
  (fiche banque, info-bulle avec la définition), jamais classé.
- L'extraction contrôle le total publié contre ses composantes selon la définition du gabarit
  (tolérance : 1 unité de la source par ligne). Un écart est signalé par le statut
  `ecart composantes` dans `controle_extraction.csv` ; il vient de la banque quand le PDF le
  confirme (BT 2020T3 : charges opératoires du trimestre 12 076 kDT, composantes 15 702 + 7 724 ;
  BNA 2023T2 : 86 209 kDT pour des composantes de 69 096 + 17 219). Aucun chiffre n'est corrigé.

```dax
-- Publié : définition propre à chaque banque (Definitions_Charges), pour information
Coef exploitation publie = DIVIDE ( [Charges operatoires], [PNB] )
-- Harmonisé : (frais de personnel + charges générales) / PNB, sur les lignes banque × trimestre
-- où les deux composantes et le PNB existent ; sert à tous les classements et comparaisons
Coef exploitation harmonise =
VAR Lignes =
    ADDCOLUMNS (
        SUMMARIZE ( Fait_Indicateurs, Fait_Indicateurs[banque], Fait_Indicateurs[date_arrete] ),
        "@Pers", [Frais personnel],
        "@Gen", [Charges generales],
        "@PNB", [PNB]
    )
VAR Completes =
    FILTER ( Lignes, NOT ISBLANK ( [@Pers] ) && NOT ISBLANK ( [@Gen] ) && NOT ISBLANK ( [@PNB] ) )
RETURN
    DIVIDE ( SUMX ( Completes, [@Pers] + [@Gen] ), SUMX ( Completes, [@PNB] ) )
Part marge interets    = DIVIDE ( [Marge interets], [PNB] )
Part commissions       = DIVIDE ( [Marge commissions], [PNB] )
Part portefeuille      = DIVIDE ( [Revenus portefeuille], [PNB] )
Frais personnel / PNB  = DIVIDE ( [Frais personnel], [PNB] )
Credits / Depots       = DIVIDE ( [Credits], [Depots] )
Part depots a vue      = DIVIDE ( [Depots a vue], [Depots] )
```

### 7.3 Intelligence temporelle

**Variations sur un an : toujours `Variations_Comparables`** (colonne N contre colonne N-1 du
même document, 5.2). On n'utilise jamais `SAMEPERIODLASTYEAR` ou `DATEADD` sur `Fait_Indicateurs`
pour une variation annuelle : cela rapprocherait deux documents, de méthodes parfois différentes
(les niveaux retenus de deux années consécutives viennent de deux documents révisés différents ;
BH : seul le T4 2025 donne 2025 et 2024 dans la même méthode, −2,8 % ; avec le PNB 2024 publié
au T4 2024, on obtiendrait −11,0 %). Le secteur se calcule de
même (somme des N contre somme des N-1, banque par banque dans leurs documents respectifs).

```dax
-- Bases (filtrées par Dim_Indicateur, Dim_Banque, Dim_Date)
VC N trim   = CALCULATE ( SUM ( Variations_Comparables[valeur_N] ),  Variations_Comparables[mesure] = "trim" )
VC N1 trim  = CALCULATE ( SUM ( Variations_Comparables[valeur_N1] ), Variations_Comparables[mesure] = "trim" )
VC N cumul  = CALCULATE ( SUM ( Variations_Comparables[valeur_N] ),  Variations_Comparables[mesure] = "cumul" )
VC N1 cumul = CALCULATE ( SUM ( Variations_Comparables[valeur_N1] ), Variations_Comparables[mesure] = "cumul" )
-- trimestre seul, sur un an (flux)
Var A/A trimestre % = DIVIDE ( [VC N trim] - [VC N1 trim], [VC N1 trim] )
-- cumul depuis le début de l'année (flux) ou solde (stocks), au dernier trimestre de la sélection
Var A/A cumul % =
    CALCULATE ( DIVIDE ( [VC N cumul] - [VC N1 cumul], [VC N1 cumul] ),
                LASTNONBLANK ( Dim_Date[Date], [VC N cumul] ) )

Var PNB A/A %          = CALCULATE ( [Var A/A trimestre %], Dim_Indicateur[code_indicateur] = "PNB" )
Var PNB cumul A/A %    = CALCULATE ( [Var A/A cumul %], Dim_Indicateur[code_indicateur] = "PNB" )
Var PNB annuel A/A %   = CALCULATE ( [Var A/A cumul %], Dim_Indicateur[code_indicateur] = "PNB",
                                     Dim_Date[Trimestre] = "T4" )
Var Charges operatoires A/A % = CALCULATE ( [Var A/A cumul %], Dim_Indicateur[code_indicateur] = "CHG_OPER" )
Var Credits A/A %      = CALCULATE ( [Var A/A cumul %], Dim_Indicateur[code_indicateur] = "CREDITS" )
Var Depots A/A %       = CALCULATE ( [Var A/A cumul %], Dim_Indicateur[code_indicateur] = "DEPOTS" )

-- T/T : deux documents successifs (pas d'autre source) ; à lire avec les marqueurs de rupture
PNB T-1    = CALCULATE ( [PNB], DATEADD ( Dim_Date[Date], -1, QUARTER ) )
Var PNB T/T % = DIVIDE ( [PNB] - [PNB T-1], [PNB T-1] )
PNB cumul annee = [PNB depuis debut annee]   -- cumul publié, pas TOTALYTD des trimestres (voir 5.2)
-- 4 trimestres glissants : somme des trimestres publiés (peut différer légèrement d'un cumul,
-- voir 5.2) ; à afficher comme indicateur de tendance, pas comme chiffre annuel
PNB 4T glissants =
    CALCULATE ( [PNB], DATESINPERIOD ( Dim_Date[Date], MAX ( Dim_Date[Date] ), -12, MONTH ) )
-- Croissance annuelle moyenne : enchaînement des 5 variations annuelles comparables (2021 à 2025,
-- chacune dans son document T4), jamais 2025 / 2020 en rapprochant deux documents
TCAM PNB 2020-2025 =
VAR Annees = GENERATESERIES ( 2021, 2025 )
VAR Variations =
    ADDCOLUMNS ( Annees, "@Var",
        VAR A = [Value]
        RETURN CALCULATE ( [Var PNB annuel A/A %], REMOVEFILTERS ( Dim_Date ), Dim_Date[Annee] = A ) )
VAR Completes = COUNTROWS ( FILTER ( Variations, NOT ISBLANK ( [@Var] ) ) )
RETURN IF ( Completes = 5, PRODUCTX ( Variations, 1 + [@Var] ) ^ ( 1 / 5 ) - 1 )

-- Annotation d'événement (evenements.csv) : texte affiché au point de la date, filtré par banque et
-- par indicateur ; plusieurs événements le même trimestre sont séparés par un retour à la ligne
Evenement texte =
    CONCATENATEX ( VALUES ( Evenements[description] ), Evenements[description], UNICHAR ( 10 ) )
Evenement montant MDT = SUM ( Evenements[montant_mdt] )
Nb evenements = COUNTROWS ( Evenements )
-- Marqueur de rupture de série pour les graphiques (période révisée de plus de 2 % sur le cumul)
Rupture PNB =
    IF ( CALCULATE ( COUNTROWS ( Fait_Indicateurs ), Fait_Indicateurs[Rupture_Trim] = "oui",
                     Dim_Indicateur[code_indicateur] = "PNB" ) > 0, [PNB] )
Rupture PNB cumul =
    IF ( CALCULATE ( COUNTROWS ( Fait_Indicateurs ), Fait_Indicateurs[Rupture_Cumul] = "oui",
                     Dim_Indicateur[code_indicateur] = "PNB" ) > 0, [PNB depuis debut annee] )
```

### 7.4 Comparaison au secteur

```dax
PNB secteur          = CALCULATE ( [PNB], REMOVEFILTERS ( Dim_Banque ) )
Part de marche PNB   = DIVIDE ( [PNB], [PNB secteur] )
Part de marche depots = DIVIDE ( [Depots], CALCULATE ( [Depots], REMOVEFILTERS ( Dim_Banque ) ) )
HHI PNB              = SUMX ( ALL ( Dim_Banque ), [Part de marche PNB] ^ 2 ) * 10000
-- comparaisons entre banques : toujours le coefficient harmonisé (7.2)
Coef secteur         = CALCULATE ( [Coef exploitation harmonise], REMOVEFILTERS ( Dim_Banque ) )   -- moyenne pondérée
Coef mediane         = MEDIANX ( ALL ( Dim_Banque ), [Coef exploitation harmonise] )
Ecart coef / mediane = [Coef exploitation harmonise] - [Coef mediane]
Rang coef            =
    IF ( NOT ISBLANK ( [Coef exploitation harmonise] ),
         RANKX ( FILTER ( ALL ( Dim_Banque ), NOT ISBLANK ( [Coef exploitation harmonise] ) ),
                 [Coef exploitation harmonise],, ASC, DENSE ) )
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
Nb ecarts composantes = CALCULATE ( [Nb documents], Controle[statut] = "ecart composantes" )
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
-- nature des révisions : portée par la ligne de la version initiale remplacée (règle 4)
Nb revisions importantes =
    CALCULATE ( COUNTROWS ( Revisions ), Revisions[version] = "initiale",
                Revisions[statut_revision] = "revision_importante" )
Nb retraitements mineurs =
    CALCULATE ( COUNTROWS ( Revisions ), Revisions[version] = "initiale",
                Revisions[statut_revision] = "retraitement_mineur" )
Nb reclassements = CALCULATE ( COUNTROWS ( Revisions ), Revisions[statut_revision] = "reclassement" )
Ecart revision MDT = SUM ( Revisions[Ecart_MDT] )
Nb annees en attente = CALCULATE ( COUNTROWS ( Controle_Annuel ), Controle_Annuel[statut] = "en attente de révision" )
Nb ecarts annuels    = CALCULATE ( COUNTROWS ( Controle_Annuel ), Controle_Annuel[statut] = "ecart" )
Nb ruptures annuelles = CALCULATE ( COUNTROWS ( Controle_Annuel ), Controle_Annuel[statut] = "rupture de série" )
-- ruptures de série : périodes dont la valeur retenue est une révision importante
Nb ruptures serie =
    CALCULATE ( COUNTROWS ( Fait_Indicateurs ),
                Fait_Indicateurs[Rupture_Trim] = "oui" || Fait_Indicateurs[Rupture_Cumul] = "oui" )
Nb documents illisibles = CALCULATE ( [Nb documents], Controle[statut] = "illisible (image)" )
Nb documents saisis    = CALCULATE ( [Nb documents], Controle[statut] = "saisie manuelle" )
Nb valeurs non disponibles =
    CALCULATE ( COUNTROWS ( Revisions ), Revisions[statut_revision] = "non disponible (image)" )
```

Paramètre de champ « Indicateur affiché » : PNB, Coef exploitation harmonise, Crédits / Dépôts,
Part de marché, Var PNB A/A % (Variations_Comparables) — pour un seul visuel où l'utilisateur choisit l'indicateur.

## 8. Ajouts par rapport au rapport de référence

1. Historique de 27 trimestres au lieu d'une seule date.
2. Valeurs trimestrielles et cumulées, et contrôle entre les deux.
3. Comparaison à la médiane et à la moyenne pondérée du secteur, rangs.
4. Segmentation par actionnariat (public, privé tunisien, groupe étranger).
5. Matrice de positionnement : croissance du PNB (variation comparable, 7.3) × coefficient d'exploitation harmonisé.
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
| 3. Évolution 2020–2026 | Courbes par banque avec sélecteur d'indicateur, bandes de périodes Covid, marqueurs de rupture de série (`Rupture PNB`, info-bulle `detail_rupture`), annotations des
événements (`Evenements` : don au Fonds 1818 en 2020, moratoire Covid de l'UIB en 2020, accord
salarial APTBEF–FGBEF en 2021, retraitement BH 2024) en info-bulle et en marqueurs ; variations sur un an depuis `Variations_Comparables` |
| 4. Structure du PNB | Barres empilées marge d'intérêts / commissions / portefeuille par banque |
| 5. Bilan | Crédits, dépôts, crédits / dépôts, structure des dépôts |
| 6. Bourse | Cours, performance, volatilité, performance boursière vs croissance du PNB |
| 7. Fiche banque (extraction) | Tous les indicateurs d'une banque, accessible par clic droit ; coefficient publié à côté du coefficient harmonisé, avec la définition des charges opératoires de la banque |
| 8. Rentabilité | ROE et ROA semestriels et annuels, matrice ROE × coefficient d'exploitation |
| 9. Qualité des données | Contrôle d'extraction (statuts, dont `ecart trimestre/cumul`, `retraitement possible`, `ecart composantes`, `illisible (image)`, avec l'écart en MDT), révisions importantes et ruptures de série (avec la note du document), sources, limites ; phrase expliquant pourquoi la somme des trimestres peut différer du cumul annuel |

Filtres : segments Année / Trimestre, plage de dates, banque, actionnariat, période ;
info-bulles personnalisées ; signets « trimestre » / « année ».

## 10. Limites à mentionner dans le rapport

- Données provisoires, non auditées, publiées par les banques elles-mêmes.
- Retraitements en cours d'année : la somme des trimestres publiés peut différer du cumul
  annuel publié ; les chiffres annuels viennent toujours du cumul (voir 5.2).
- Révisions : les niveaux sont toujours les derniers chiffres publiés par la banque pour la
  période (version révisée) ; une révision de plus de 2 % du cumul est signalée par un marqueur
  de rupture dans les graphiques. Le seuil de 2 % est un choix d'analyse, pas une norme. Les
  variations sur un an sont toujours calculées dans un même document. Les banques n'expliquent pas
  toujours ce qui a changé (BH, T4 2025) ; deux causes communes sont connues pour 2020 (don au
  Fonds 1818) et 2021 (accord salarial du secteur), plus une cause propre à l'UIB en 2020
  (intérêts du moratoire Covid non comptés dans les chiffres publiés, réintégrés en 2021 : PNB
  des 9 mois 2020 révisé de +42,7 %).
- Erreurs de la banque dans les colonnes N-1 : deux cas vérifiés sur l'image. UIB 2023T2 :
  charges d'exploitation du T2 2022 égales au cumul du semestre (produits − charges ≠ PNB dans
  cette colonne, document « a verifier ») ; WIB 2023T4 : colonne T4 2022 recopiée du T3 2022
  (cohérente en elle-même, repérée par le contrôle annuel 2022). Ces deux colonnes ne sont pas
  retenues (5.2, colonnes N-1 non retenues) ; la liste des révisions importantes est dans
  `docs/revisions_importantes.csv` (`python scripts/bilan_extraction.py`).
- Un document publié en image (BH 2019T4) n'est connu que par les colonnes N-1 du document de
  l'année suivante.
- Définitions des postes parfois différentes d'une banque à l'autre. Exemple : les charges
  opératoires publiées par la BT et la BH ne comprennent que les frais de personnel et les charges
  générales (pas de dotations aux amortissements) ; la BNA et l'ATB ne détaillent que ces deux postes mais
  leur total comprend un reste non détaillé ; WIB et UIB publient en plus les dotations aux
  amortissements. On garde le total publié, sans le recalculer
  (`gabarits.csv`, colonne `definition_charges_operatoires`) ; les comparaisons entre banques
  utilisent le coefficient d'exploitation harmonisé (frais de personnel + charges générales,
  hors dotations), qui sous-estime le coût total des banques dont les dotations sont importantes.
- ROE et ROA seulement en semestriel et annuel ; résultats semestriels non audités, annualisés.
- Les valeurs extraites automatiquement ont été contrôlées par échantillon (voir `docs/validation.md`).
