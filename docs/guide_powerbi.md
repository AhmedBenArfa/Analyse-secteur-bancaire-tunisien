<!-- Auteur : Ahmed Ben Arfa -->
# Guide Power BI — Analyse du secteur bancaire tunisien

Ce guide explique, étape par étape, chaque requête Power Query et chaque mesure DAX du rapport :
ce qu'elle calcule et pourquoi. Il est aussi publié en PDF, régénéré après chaque requête ou mesure :
`docs/Guide_PowerBI.pdf` (`python scripts/generer_pdf.py guide`), avec en annexe le code M exact de
chaque requête et la feuille de route (décisions). Il se lit à côté du projet Power BI (`powerbi/`) et des fichiers
`powerquery/*.pq` (le texte exact de chaque requête). La spécification complète est dans
`docs/SPECIFICATION.md`.

Principe : Python ne fait que lire les PDF (`collecte_banques.py`, `scripts/`). Tout ce qui peut se
faire dans Power Query s'y fait, pour que la préparation des données reste visible dans le rapport.

## 1. Créer et enregistrer le projet `.pbip`

1. Power BI Desktop : **Fichier › Options et paramètres › Options › Fonctionnalités en préversion**,
   cocher **Enregistrement du projet Power BI (.pbip)** et **Stocker le modèle sémantique au format
   TMDL**, puis redémarrer Power BI Desktop (si ces cases n'existent plus, la fonction est déjà
   activée par défaut).
2. **Fichier › Options › Paramètres régionaux** (fichier actif) : laisser la langue du rapport en
   français ; les requêtes fixent elles-mêmes la culture `en-US` pour lire les nombres à point décimal.
3. Rapport vide : **Fichier › Enregistrer sous**, type **Fichiers de projet Power BI (\*.pbip)**,
   dossier `D:\Projet\Analyse-secteur-bancaire-tunisien\powerbi\`, nom `SecteurBancaireTunisien`.
   Attention : le type par défaut est `.pbix` (un seul fichier binaire, illisible hors de Power BI) ;
   seul le type `.pbip` produit les fichiers texte du modèle que l'on peut lire et versionner.
4. Power BI crée `SecteurBancaireTunisien.pbip`, le dossier `SecteurBancaireTunisien.Report\`
   (pages et visuels) et le dossier `SecteurBancaireTunisien.SemanticModel\` (modèle : requêtes,
   tables, relations, mesures, au format texte TMDL dans `definition\`). Power BI n'a pas créé de
   `.gitignore` dans ce projet : c'est celui de la racine du dépôt qui exclut le cache des données
   (`cache.abf`) et les réglages locaux ; seules les définitions sont versionnées, jamais les données.

**Où sont les requêtes dans le projet.** Le modèle est stocké en texte (TMDL) dans
`powerbi/SecteurBancaireTunisien.SemanticModel/definition/` :

| Fichier | Contenu |
|---|---|
| `expressions.tmdl` | le paramètre `CheminDonnees` et les requêtes intermédiaires non chargées (`Fichiers_Donnees`, `Versions`) |
| `tables/<Table>.tmdl` | une table chargée (`Dim_Indicateur`, `Fait_Indicateurs`…) : ses colonnes (type, synthèse, colonne de tri) et sa requête (partition `m`) |
| `model.tmdl` | options du modèle, ordre des requêtes dans Power Query (`PBI_QueryOrder`), liste des tables |

Le code M de chaque requête est le même que celui du fichier `powerquery/<Requête>.pq`, gardé comme
copie lisible : une modification faite dans Power Query doit être reportée dans le `.pq` (et
inversement). Les requêtes sont écrites directement dans ces fichiers, Power BI Desktop fermé ;
à la réouverture, Power BI les lit et les affiche dans Power Query.

**Niveaux de confidentialité.** À la première actualisation, Power BI demande le niveau de chaque
source (dossier du projet, fichier Excel, adresse GitHub) : choisir le dossier du projet (pas tout le
disque) et le même niveau pour toutes, **Professionnel** (« Organisationnel » dans certaines
versions), sinon les fusions entre sources peuvent être bloquées. Pour l'adresse GitHub, accès
**Anonyme** (dépôt public). Ces réglages sont enregistrés sur le poste, pas dans le projet : une
personne qui clone le dépôt les donne une fois.

**Aperçu annulé.** Power Query ne calcule l'aperçu que d'une requête à la fois : en passant d'une
requête à l'autre, ou pendant un chargement, l'aperçu en cours est annulé (« L'actualisation d'aperçu a
été annulée… aucun impact sur vos données chargées ») ; **Réessayer** ou **Accueil › Actualiser
l'aperçu** le relance. Power BI enregistre alors `PBI_ResultType = Exception` pour cette requête dans le
TMDL (icône « ? » dans Power Query), sans effet sur les données chargées ; c'est fréquent pour
`Banques_Actionnariat` (lecture d'un fichier Excel). Pour le limiter : **Fichier › Options et
paramètres › Options › Fichier actif › Chargement des données**, cocher « Autoriser le téléchargement
des aperçus de données en arrière-plan ».

Ne sont pas versionnés (`.gitignore`) : `.pbi/localSettings.json` (réglages et signature de sécurité
propres au poste) et l'ancien `SecteurBancaireTunisien.pbix`. **Le cache des données
(`.pbi/cache.abf`) est versionné** (décision du 23/10/2026) : le projet s'ouvre avec ses données sans
actualiser, donc sans changer `CheminDonnees` ni répondre aux questions d'accès. Toutes ces données
sont déjà publiques dans le dépôt. Le fichier est compressé : l'audit ne peut pas lire son contenu.
Il est commité seulement après une vérification dans Power BI Desktop suivie d'un enregistrement,
pour que les données publiées correspondent au modèle.

**Vérifier après une réouverture.** Ouvrir `SecteurBancaireTunisien.pbip`, **Accueil › Transformer les
données** : les requêtes apparaissent dans l'ordre de la section 2, les intermédiaires en italique
(chargement désactivé). Revenir au rapport et **Actualiser**. Contrôles (calculés sur les CSV) :

| Table | Contrôle | Attendu |
|---|---|---|
| `Dim_Indicateur` | nombre de lignes | 27 (24 indicateurs trimestriels + 3 des états financiers) |
| `Fait_Indicateurs` | nombre de lignes | 7 173 (7 137 avant la saisie des composantes BTE 2020–2021) |
| `Fait_Indicateurs` | AB 2026T3, PNB | `Valeur_Trim` = 150,021 ; `Valeur_Cumul` = 512,448 (relevés sur l'image, `tests/valeurs_reference.csv`) |
| `Fait_Indicateurs` | AB 2020T1, CREDITS (stock) | `Valeur_Trim`, `Source_Trim`, `Fichier_Trim` vides ; `Valeur_Cumul` = 5 670,677 |
| `Fait_Indicateurs` | BTE 2021T4, INT_PERCUS | `Valeur_Trim` = 22,367, `Source_Trim` = `revisee_T4_N+1`, `Fichier_Trim` = `BTE_2022T4.pdf` (22,069 publié à l'origine) |
| `Fait_Indicateurs` | BTE 2020T2, COMM_CHG | `Valeur_Trim` = 0,005 (5 515 publiés à l'origine, révisés dans BTE 2021T2) |
| `Fait_Indicateurs` | `Rupture_Cumul` | 6 723 « non », 450 « oui », aucune case vide |
| `Revisions` | nombre de lignes | 14 884 (avec `Fait_Indicateurs` : les 26 429 lignes de `indicateurs_versions.csv`) |
| `Revisions` | BH 2024T4, PNB, cumul, version `initiale` | `valeur_mdt` = 765,932 ; `valeur_retenue` = 701,188 ; `Ecart_MDT` = −64,744 ; « révision importante (plus de 2 %) » |
| `Revisions` | `Type_Revision` | 7 639 retraitements mineurs, 5 677 identiques, 1 133 révisions importantes, 241 « 31/12 provisoire écarté », 99 reclassements, 70 documents en image, 25 colonnes fausses |
| `Banques_Actionnariat` | nombre de lignes | 15 (12 banques ; 2 périodes pour BTE, UBCI et Wifak) ; aucune erreur dans `actionnariat` |
| `Dim_Banque` | nombre de lignes | 12 |
| `Dim_Banque` | UBCI | `actionnaire_reference` = Groupe Carte ; `part_capital_pct` = 39,86 ; `actionnariat` = privé sans contrôle étranger |
| `Dim_Banque` | BTE | Abou Dhabi Investment Authority (ADIA) ; 40,80 ; mixte ; `date_actionnariat` = 31/12/2024 |
| `Dim_Banque` | WIB | `ticker_bvmt` = WIFAK ; groupe = Groupe Ben Ayed |
| `Operations_Titres` (Power Query, requête intermédiaire) | nombre de lignes (barre d'état en bas) | 63 |
| `Operations_Titres` | BIAT 04/05/2021 (division du nominal) | `facteur` = 0,5 |
| `Operations_Titres` | BIAT 10/05/2019 | `facteur_cumule_prix` = 0,416667 (produit des 3 opérations sur le capital qui suivent) |
| `Operations_Titres` | BT 10/05/2022 (attribution + dividende) | `facteur` = 0,796446 ; `facteur_prix` = 0,834179 |
| `Evenements` | nombre de lignes | 11 |
| `Evenements` | BH_RETRAITEMENT_2024 | `date` = 31/12/2024 ; `montant_mdt` = −64,744 |
| `Fait_Cours` | nombre de lignes | 23 460 (1 955 séances × 12 banques) |
| `Fait_Cours` | BIAT 02/01/2019 | `cloture` = 118 ; `facteur_prix` = 0,416667 ; `cloture_ajustee_prix` = 49,1667 ; `facteur_rendement` = 0,272016 ; `rendement` vide (première séance) |
| `Fait_Cours` | BIAT 31/12/2025 | `cloture` = 111 ; `facteur_prix` = 1 ; `facteur_rendement` = 0,9625 (dividende de mai 2026) |
| `Fait_Cours` | BT 10/05/2022 (jour de l'attribution) | `cloture` = 5,05 ; `facteur_prix` = 1 ; `facteur_rendement` = 0,795311 |
| `Fait_Cours` | `sans_transaction` = Vrai | 3 074 séances (UBCI 52,7 %, Wifak 42,6 %, BTE 37,6 % de leurs séances) |
| `Variations_Comparables` | nombre de lignes | 10 981 (11 285 du fichier moins 304 lignes « trimestre » de stocks) |
| `Variations_Comparables` | BH 2025T4, PNB | `cumul` : 681,479 contre 701,188, `Variation_Pct` = −2,8 % ; `trim` : 189,758 contre 177,219, +7,1 % |
| `Fait_Etats_Financiers` | nombre de lignes | 504 (12 banques × 14 dates × 3 codes) ; `facteur_annualisation` = 2 sur 252 lignes (semestres), 1 sur 252 (exercices) |
| `Fait_Etats_Financiers` | BNA 30/06/2025, RES_NET | 155,069 ; `version` = initiale ; statut « revisee non retenue (modification comptable incluse) » |
| `Fait_Etats_Financiers` | UIB 30/06/2020, RES_NET | 17,912 (révisée, moratoire Covid ; −41,182 publié à l'origine) |
| `Fait_Etats_Financiers` | BIAT 31/12/2024, CAP_PROPRES_EF | 2 226,391 |
| `Revisions_Etats_Financiers` | nombre de lignes | 423 (avec `Fait_Etats_Financiers` : les 927 lignes du fichier) |
| `Revisions_Etats_Financiers` | UIB 30/06/2020, RES_NET, version `initiale` | −41,182 publié ; 17,912 retenu ; `Ecart_MDT` = 59,094 ; « révision importante (plus de 2 %) » |
| `Revisions_Etats_Financiers` | BNA 30/06/2025, RES_NET, version `revisee` | 137,318 ; 155,069 retenu ; « révisée non retenue (modification comptable incluse) » |
| `Revisions_Etats_Financiers` | `Type_Revision` | 390 identiques, 24 retraitements mineurs, 8 révisions importantes, 1 révisée non retenue |
| `Controle` | nombre de lignes | 336 (12 banques × 28 trimestres) ; somme de `nb_alertes` = 968 |
| `Controle` | `Categorie_Statut` | 91 conformes, 228 écarts signalés, 13 saisis à la main, 2 repris du document suivant, 2 alertes bloquantes (UBCI 2025T3, UIB 2023T2) |
| `Controle` | BTE 2021T4 | `statut` = saisie manuelle ; `date_arrete` = 31/12/2021 ; `nb_alertes` = 7 |
| `Ecarts_Annuels` (Power Query, intermédiaire) | nombre de lignes | 22 |
| `Controle_Annuel` | nombre de lignes | 288 (12 banques × 6 années × 4 indicateurs) |
| `Controle_Annuel` | `Statut_Clair` | 205 « somme des trimestres = cumul annuel », 41 « en attente du document de l'année suivante », 20 « changement de méthode en cours d'année », 22 « écart expliqué : … » (11 retraitements de la banque, 7 erreurs dans le document de la banque, 3 reclassements, 1 arrondi), **0** « écart sans cause écrite » |
| `Controle_Annuel` | ATB 2021, CHG_EXPL | somme 309,5 ; cumul 312,374 ; `Ecart_MDT` = −2,874 ; « écart expliqué : retraitement de la banque » ; preuve ATB_2022T2.pdf p. 1 |
| `Controle_Annuel`, `Revisions`, `Revisions_Etats_Financiers` | `Ecart_MDT` | affiché avec trois décimales (format `#,0.000`) : 0,001 et non 0,000999999… (imprécision de calcul des nombres décimaux, valeur inchangée) |
| `Gabarits` (Power Query, intermédiaire) | nombre de lignes | 46 |
| `Definitions_Charges` | nombre de lignes | 13 (une par banque, deux pour Attijari) |
| `Definitions_Charges` | TJARI | « sans dotations » de 2019T4 à 2021T3 ; « avec reste non detaille » de 2021T4 à 2026T3 |
| `Definitions_Capitaux_Propres` | nombre de lignes | 12 ; « resultat inclus » pour ATB et BTE ; « hors resultat, apres affectation au 31/12 » pour AB et BIAT |
| `Fait_Indicateurs`, `Variations_Comparables`, `Fait_Etats_Financiers` | `Segment_Actionnariat` | jamais vide ; nombres de lignes inchangés (7 173, 10 981, 504) |
| `Fait_Indicateurs` | UBCI 2020T4 / 2021T1 | « groupe étranger » / « privé sans contrôle étranger » (cession du 16/03/2021) |
| `Fait_Indicateurs` | BTE 2024T3 | « mixte » (seconde période, à partir du 01/07/2024) |

Ajout manuel d'une requête (sans passer par les fichiers TMDL) : **Accueil › Transformer les données**,
puis **Nouvelle source › Requête vide**, **Éditeur avancé**, coller le contenu du fichier `.pq`, renommer
la requête exactement comme le fichier (sans `.pq`). Requête intermédiaire : clic droit › décocher
**Activer le chargement**. Puis **Fermer et appliquer** et enregistrer (Ctrl+S).

## 2. Requêtes Power Query

Ordre de création : chaque requête n'utilise que des requêtes déjà créées.

| # | Requête | Chargée | Source | Rôle |
|---|---|---|---|---|
| 1 | `CheminDonnees` | paramètre | — | dossier du projet sur ce poste |
| 1b | `AdresseDepot` | paramètre | — | adresse des fichiers bruts du dépôt GitHub |
| 2 | `Fichiers_Donnees` | non | connecteur Dossier | liste des CSV de `donnees_publiees\` |
| 3 | `Versions` | non | `indicateurs_versions.csv` | toutes les versions des indicateurs, typées |
| 4 | `Dim_Indicateur` | oui | `dim_indicateur.csv` + 3 lignes ajoutées | libellé, catégorie, nature (flux / stock), ordre |
| 5 | `Fait_Indicateurs` | oui | `Versions` + fusion avec `Dim_Indicateur` | valeur retenue, trimestre seul et cumul côte à côte |
| 6 | `Revisions` | oui | `Versions` | versions non retenues et écart à la valeur retenue (page qualité) |
| 7 | `Banques_Actionnariat` | oui | `donnees_referenceanques.xlsx` (connecteur Excel) | actionnariat par période, avec source et page |
| 8 | `Dim_Banque` | oui | `dim_banque.csv` + fusion avec `Banques_Actionnariat` | code, nom, ticker, actionnariat actuel |
| 8b | `Actionnariat_A_La_Date` | fonction | `Banques_Actionnariat` | catégorie d'actionnariat d'une banque à une date (segment des faits) |
| 9 | `Operations_Titres` | non | `operations_titres.csv` sur GitHub (source URL) | facteurs d'ajustement des cours |
| 10 | `Evenements` | oui | `evenements.csv` sur GitHub (source URL) | événements qui expliquent une rupture de série |
| 11 | `Fait_Cours` | oui | `cours_banques.csv` + fusion avec `Operations_Titres` | cours quotidiens, cours ajustés, rendement, séances sans transaction |
| 12 | `Variations_Comparables` | oui | `variations_comparables.csv` + fusion avec `Dim_Indicateur` | valeur N et N-1 du même document, variation sur un an |
| 13 | `Fait_Etats_Financiers` | oui | `etats_financiers_versions.csv` | résultat net, total de l'actif, capitaux propres du bilan (ROE, ROA) |
| 14 | `Revisions_Etats_Financiers` | oui | `etats_financiers_versions.csv` | versions écartées des états financiers (page qualité) |
| 15 | `Controle` | oui | `controle_extraction.csv` | statut d'extraction de chaque document (page qualité) |
| 16 | `Ecarts_Annuels` | non | `docs\ecarts_annuels.csv` (connecteur Fichier) | cause de chaque écart du contrôle annuel |
| 17 | `Controle_Annuel` | oui | `controle_annuel.csv` + fusion avec `Ecarts_Annuels` | somme des trimestres contre cumul annuel, statut et cause |
| 18 | `Gabarits` | non | `gabarits.csv` (connecteur Fichier) | définitions de chaque banque, par mise en page |
| 19 | `Definitions_Charges` | oui | `Gabarits` (regroupement) | contenu des charges opératoires publiées, par période |
| 20 | `Definitions_Capitaux_Propres` | oui | `Gabarits` (lignes distinctes) | contenu des capitaux propres trimestriels publiés |

### 2.1 `CheminDonnees` (paramètre)

Texte : le dossier du projet (`D:\Projet\Analyse-secteur-bancaire-tunisien`), qui contient
`donnees_publiees\` (CSV finaux, versionnés), `donnees_reference\` (fichier Excel des banques) et
`docs\`.
**Pourquoi** : un seul endroit à changer si le projet est copié sur un autre poste
(**Accueil › Gérer les paramètres**) ; aucune requête n'écrit de chemin en dur. Après un clonage du
dépôt, il suffit de donner à `CheminDonnees` le dossier du clone puis d'actualiser : toutes les
données lues sont dans le dépôt.

### 2.2 `Fichiers_Donnees` (intermédiaire, non chargée)

| Étape | Ce qu'elle fait |
|---|---|
| `Source` | `Folder.Files` : tous les fichiers de `donnees_publiees\` (connecteur Dossier) |
| `CsvDuDossier` | garde les `.csv` posés directement dans ce dossier (pas `LISEZMOI.md`) |
| `Colonnes` | garde le nom, le contenu binaire et la date de modification |
| `Renommees` | noms en français : `fichier`, `contenu`, `modifie_le` |

**Pourquoi** : les requêtes suivantes prennent leur fichier par son nom dans cette table
(`Fichiers_Donnees{[fichier = "…"]}[contenu]`) ; la date de modification permet de vérifier, sur la
page qualité, que les CSV sont ceux de la dernière publication.
**Pourquoi `donnees_publiees\` et pas `donnees\`** : `donnees\` est le dossier de travail des scripts
(PDF, archives, caches), non versionné ; `donnees_publiees\` contient seulement les CSV finaux, sans
chemin local, versionnés avec le dépôt. Il est régénéré par `python scripts/publier_donnees.py`
(voir `donnees_publiees/LISEZMOI.md`).

### 2.3 `Versions` (intermédiaire, non chargée)

Une ligne par banque × trimestre × indicateur × mesure (`trim` = trimestre seul, `cumul` = depuis
janvier ou solde) × version (`initiale` = publiée dans le document du trimestre, `revisee_…` = colonne
N-1 du document suivant, `revisee_31-12_…` = 31/12 provisoire). 26 223 lignes au 22/10/2026.

| Étape | Ce qu'elle fait |
|---|---|
| `Fichier` | prend `indicateurs_versions.csv` dans `Fichiers_Donnees` |
| `Source` | lit le CSV : séparateur `;`, encodage UTF-8 (65001, le BOM est reconnu) |
| `EnTetes` | première ligne = noms de colonnes |
| `Types` | types de données **avec les paramètres régionaux `en-US`** : le CSV écrit `29.585` ; lu en français, ce serait 29 585 |
| `VidesEnNull` | une case de texte vide devient `null` (« pas de note », « pas de rupture ») |

**Pourquoi intermédiaire** : ce fichier mélange la valeur retenue et les versions écartées. Deux
requêtes chargées en partent avec un filtre explicite : `Fait_Indicateurs` (version retenue
seulement) et `Revisions` (versions non retenues, page qualité). Une valeur manquante reste `null`,
jamais zéro.

### 2.4 `Dim_Indicateur` (chargée)

Une ligne par code d'indicateur (27 lignes).

| Étape | Ce qu'elle fait |
|---|---|
| `Fichier`, `Source`, `EnTetes` | lit `dim_indicateur.csv` dans `Fichiers_Donnees` |
| `Types` | types de données (paramètres régionaux `en-US`) ; `ordre` en entier |
| `SourceIndicateurs` | **colonne ajoutée** `source` = « indicateurs trimestriels » |
| `EtatsFinanciers` | table de 3 lignes écrite dans la requête : `RES_NET` (flux), `TOTAL_ACTIF` et `CAP_PROPRES_EF` (stocks), source « états financiers » |
| `Ajoutees` | **ajout** des 3 lignes à la suite des 24 codes |

**Pourquoi ajouter les codes des états financiers** : un événement peut porter sur le résultat net
(ex. moratoire Covid de l'UIB au 30/06/2020) ; avec son code dans la dimension, la relation garde
l'annotation sur la page « Rentabilité » (spécification 6). La colonne `libelle` est triée par `ordre`
dans le modèle (ordre d'affichage des indicateurs, pas l'ordre alphabétique).

### 2.5 `Fait_Indicateurs` (chargée)

Table de faits des indicateurs trimestriels : une ligne par banque × trimestre × indicateur
(7 173 lignes au 23/10/2026), avec le trimestre seul et le cumul côte à côte.

| Étape | Ce qu'elle fait |
|---|---|
| `Source` | part de `Versions` (référence, pas de nouvelle lecture du fichier) |
| `VersionRetenue` | **filtre sur la version retenue** : `version = source_valeur`, une seule version par banque × trimestre × indicateur × mesure (11 545 lignes) |
| `Colonnes` | garde les clés, la mesure (`trim` / `cumul`), la valeur retenue, la version, le fichier, la page et la rupture de série |
| `Fusion`, `Nature` | **fusion avec `Dim_Indicateur`** sur `code_indicateur` (jointure externe gauche) : nature de l'indicateur |
| `Retenir`, `SansTrimDesStocks` | **colonne conditionnelle** : faux pour la mesure `trim` d'un stock, puis filtre ; écarte 320 lignes (au T1, copie du solde chez AB, BTE, STB, Attijari, UBCI ; STB 2019T4 et UBCI 2024–2026 : mouvement imprimé dans la colonne du trimestre, qui n'est pas un solde) |
| `RuptureNon` | « non » au lieu d'une case vide dans `rupture_serie` (le détail de la rupture reste vide) |
| `SansColonnesAjoutees` | retire `nature` et `retenir` |
| `Renommees` | noms courts des attributs (`Valeur`, `Source`, `Fichier`, `Page`, `Rupture`, `Detail_Rupture`) |
| `Depivotees` | **dépivotage** : une ligne par attribut ; une case vide (pas de rupture) ne donne pas de ligne |
| `NomColonne` | colonne conditionnelle du nom final : attribut + mesure (`Valeur_Trim`, `Source_Cumul`…) |
| `SansMesure` | retire `mesure` et `attribut`, devenus inutiles |
| `Pivotees` | **pivot** sans agrégation sur cette liste fixe de 12 colonnes (une seule valeur par case : une erreur ici signalerait un doublon dans les versions) |
| `Types` | nombres pour les valeurs, entiers pour les pages, texte pour le reste |
| `Periodes`, `Segment` | **segment d'actionnariat** : périodes de `Banques_Actionnariat` gardées en mémoire, puis colonne `Segment_Actionnariat` = fonction `Actionnariat_A_La_Date` (catégorie de la banque à la date d'arrêté, section 2.12h) |

**Pourquoi un filtre explicite** : la règle des versions (spécification 5.2) se voit dans Power Query :
les niveaux affichés sont toujours la version révisée quand elle existe ; les versions écartées
restent consultables dans la requête `Revisions`.
**Pourquoi trimestre et cumul côte à côte** : les mesures DAX choisissent la colonne (trimestre seul
pour l'analyse trimestrielle, cumul pour l'année et pour les soldes) sans filtre sur une colonne
`mesure`. `Valeur_Cumul` est toujours rempli ; `Valeur_Trim` est vide pour les soldes (crédits,
dépôts, capitaux propres : la valeur à la date est dans `Valeur_Cumul`) et pour un flux dont le
trimestre seul n'est publié nulle part (BTE : autres produits d'exploitation à quelques dates) :
jamais remplacé par zéro. `Fichier_*` et `Page_*`
gardent la source de chaque valeur ; `Rupture_*` (« oui ») et `Detail_Rupture_*` alimentent les
marqueurs et les info-bulles des graphiques.

### 2.6 `Revisions` (chargée)

Toutes les versions qui ne sont pas retenues : une ligne par banque × trimestre × indicateur × mesure ×
version écartée (14 884 lignes au 23/10/2026). Page « qualité des données ».

| Étape | Ce qu'elle fait |
|---|---|
| `Source` | part de `Versions` (référence) |
| `VersionsNonRetenues` | **filtre inverse** de `Fait_Indicateurs` : `version <> source_valeur` ; les deux tables ensemble redonnent toutes les lignes du fichier |
| `Colonnes` | clés, version, valeur publiée (`valeur_mdt`), fichier et page de cette version, valeur et version retenues, statut, note, mention de retraitement |
| `EcartMDT` | **colonne calculée** `Ecart_MDT` = valeur retenue − valeur de cette version (vide si l'une manque, jamais zéro) ; calculée ici plutôt que reprise du CSV |
| `EcartPct` | `Ecart_MDT` rapporté à la valeur de la version (vide si elle est nulle ou absente) |
| `OrigineVersion` | **colonne conditionnelle** : document du trimestre, 31/12 provisoire (document T1 à T3 suivant) ou colonne N-1 du document suivant |
| `TypeRevision` | **colonne conditionnelle** : statut en clair (identique à l'arrondi près, retraitement mineur, révision importante, reclassement, document en image, 31/12 provisoire écarté pour les capitaux propres, colonne fausse écartée) |

**Pourquoi** : chaque valeur affichée dans le rapport est la version retenue ; cette table montre ce que
la banque avait publié avant, et de combien elle a révisé (ex. PNB 2024 de BH : 765,932 publié dans
BH_2024T4, 701,188 retenu, « retraité pour des raisons de comparabilité »). Les 3 lignes sans valeur
retenue sont les capitaux propres BTE au 31/12 provisoire (2021 et 2022), écartés par la règle.

### 2.7 `Banques_Actionnariat` (chargée)

Actionnariat des 12 banques lu dans le fichier Excel `donnees_referenceanques.xlsx` (table Excel
nommée `Banques`, 15 lignes) : une ligne par banque et par période d'actionnaire de référence.

| Étape | Ce qu'elle fait |
|---|---|
| `Classeur` | **connecteur Excel** : `Excel.Workbook` sur le fichier, première ligne = en-têtes |
| `Banques` | prend la **table Excel** `Banques` (pas la feuille) : ses limites suivent les lignes ajoutées dans Excel |
| `Types` | texte, nombre (`part_capital_pct`, en % du capital), dates (`date_reference`, `date_debut`, `date_fin`) |
| `CategorieValide` | une catégorie hors des quatre de la règle (public, groupe étranger, mixte, privé sans contrôle étranger) devient une **erreur visible** à l'actualisation |

**Pourquoi un fichier Excel** : l'actionnariat ne vient pas des PDF d'indicateurs ; il est relevé à la
main dans des sources officielles (fiche émetteur de la Bourse, états financiers, rapports annuels),
avec la source et la page de chaque ligne, dans un fichier qu'on peut relire et corriger dans Excel
(`python scripts/ecrire_banques_xlsx.py` le régénère). Règle de classement par le contrôle :
spécification 5.3. Les périodes (`date_debut`, `date_fin`) servent au segment d'actionnariat des
faits : UBCI change de catégorie le 16/03/2021 (BNP Paribas → groupe Carte) ; Wifak et BTE changent
d'actionnaire de référence sans changer de catégorie. Pour BTE, la date de l'augmentation de capital
du second semestre 2024 n'est pas connue : la seconde période commence au 01/07/2024 (« date exacte
inconnue, entre le 30/06 et le 31/12/2024 »), pour que les périodes se suivent sans trou (contrôlé par
`tests/test_actionnariat.py`).

### 2.8 `Dim_Banque` (chargée)

| Étape | Ce qu'elle fait |
|---|---|
| `Fichier`, `Source`, `EnTetes`, `Types` | lit `dim_banque.csv` (code, nom, ticker de la Bourse) |
| `SansColonnesVides` | retire `actionnariat` et `groupe`, vides dans le CSV |
| `ActionnariatActuel` | filtre de `Banques_Actionnariat` : la ligne sans `date_fin` (une par banque) |
| `Fusion`, `Developpee` | **fusion** sur `code_banque` (jointure externe gauche) : actionnaire de référence, part du capital, catégorie, groupe, date de la source (`date_actionnariat`) |
| `Logos` | connecteur Dossier sur `donnees_reference\logos\` : les fichiers `.png` (un par banque, nommé par son code ; sources dans le `LISEZMOI.md` du dossier) |
| `Icones` | colonne `icone` = `"data:image/png;base64,"` & le contenu du fichier en base 64 (`Binary.ToText`) : l'image elle-même écrite en texte, que Power BI affiche sans aller sur internet |
| `CodeLogo`, `FusionLogos`, `AvecIcone` | code de la banque tiré du nom du fichier (`AB.png` → `AB`), puis **fusion** sur `code_banque` : une banque sans logo garderait une icône vide |

Dans le modèle, `icone` a la **catégorie de données « URL d'image »** (`dataCategory: ImageUrl`) : un tableau ou un
segment à images affiche le logo au lieu du texte. Les logos (12 vignettes de 240 × 120 pixels, fond transparent)
sont la propriété des banques ; ils servent seulement à les identifier (`tests/test_logos.py` : un logo par banque,
assez léger pour une image intégrée, source écrite pour chacun).

**Pourquoi l'actionnariat actuel seulement** : la dimension a une ligne par banque (relation 1 →
plusieurs vers les faits) ; l'historique reste dans `Banques_Actionnariat`.

### 2.9 `AdresseDepot` (paramètre) et lecture par URL

Texte : `https://raw.githubusercontent.com/AhmedBenArfa/Analyse-secteur-bancaire-tunisien/main`,
l'adresse des fichiers bruts (« raw ») du dépôt public. Les fichiers versionnés à la racine
(`operations_titres.csv`, `evenements.csv`) sont lus par `Web.Contents(AdresseDepot,
[RelativePath = "…"])` : l'adresse de base reste fixe, ce qui permet aussi l'actualisation dans le
service Power BI. **Pourquoi une URL** : c'est la troisième source demandée (dossier, Excel, URL) ;
le rapport lit la version publiée de ces fichiers, la même pour tout le monde.

### 2.10 `Operations_Titres` (intermédiaire, non chargée)

63 opérations sur titres (dividendes, attributions gratuites, division du nominal, souscription), une
ligne par banque et par date d'effet, avec le cours de référence publié par la Bourse ce jour-là et la
clôture de la veille (spécification 7.5).

| Étape | Ce qu'elle fait |
|---|---|
| `Source`, `EnTetes`, `Types` | lit le CSV sur GitHub ; types avec les paramètres régionaux `en-US` |
| `Facteur` | **colonne calculée** `facteur` = cours de référence publié / clôture de la veille (vide si l'un manque) : l'ajustement fait par la Bourse elle-même, valable pour tous les types d'opération |
| `Capital` | **colonne conditionnelle** `capital` : vrai pour tout sauf un dividende seul |
| `FacteurPrix` | facteur de la série « prix » : 1 pour un dividende seul ; pour une attribution le même jour qu'un dividende (BT 10/05/2022), le dividende est retiré de la clôture de la veille avant la parité (4,930 / (6,190 − 0,280) = 0,834, proche de la parité 5/6) |
| `EnMemoire` | garde la table en mémoire (`Table.Buffer`) : les cumuls la parcourent pour chaque ligne sans relire le fichier en ligne |
| `CumulPrix`, `CumulRendement` | **facteurs cumulés** par banque : produit des facteurs de cette opération et des suivantes ; série « prix » (opérations sur le capital) et série « rendement total » (dividendes compris) |
| `Triees` | tri par banque et date |

**Comment ils serviront** : dans `Fait_Cours`, une séance prend le facteur cumulé de la première
opération qui la suit ; cours ajusté = clôture × ce facteur. Exemple BIAT : clôture 118,000 le
02/01/2019 et 111,000 le 31/12/2025, soit −5,9 % en brut et +125,8 % ajusté des opérations sur le
capital (attributions de 2020 et 2024, division du nominal de 2021).

### 2.11 `Evenements` (chargée)

11 lignes : une par événement et par banque concernée (don au Fonds 1818, accord salarial
APTBEF–FGBEF, moratoire Covid de l'UIB, retraitement BH 2024, déchéance fiscale BNA 2025), avec la
date (fin du trimestre concerné), l'indicateur, la description, le montant cité par le document, le
fichier et la page. Étapes : lecture du CSV sur GitHub, types (`en-US`). Elles annoteront les
graphiques (marqueurs et info-bulles) une fois les relations créées (étape du modèle).

### 2.12 `Fait_Cours` (chargée)

Une ligne par banque et par séance (23 460 lignes, du 02/01/2019 au 20/10/2026) : cours non ajustés de
la Bourse et cours ajustés des opérations sur titres.

| Étape | Ce qu'elle fait |
|---|---|
| `Fichier`, `Source`, `EnTetes`, `Types` | lit `cours_banques.csv` ; types avec les paramètres régionaux `en-US` (un cours absent reste vide) |
| `VidesEnNull`, `SansIsin` | statut vide → `null` ; retire le code ISIN (la banque et le ticker suffisent) |
| `Operations` | colonnes utiles de `Operations_Titres`, gardées en mémoire (le fichier GitHub est lu une fois) |
| `Fusion` | **fusion** avec `Operations_Titres` sur la banque : chaque séance reçoit les opérations de sa banque |
| `Suivante`, `Developpee` | première opération **postérieure** à la séance ; ses facteurs cumulés (produit des facteurs de toutes les opérations qui suivent la séance) deviennent `facteur_prix` et `facteur_rendement` |
| `FacteurUn` | aucune opération après la séance : facteur 1 |
| `AjustePrix`, `AjusteRendement` | `cloture_ajustee_prix` = clôture × facteur prix (attributions, division du nominal) ; `cloture_ajustee_rendement` = clôture × facteur rendement (dividendes compris) |
| `SansTransaction` | **colonne conditionnelle** : vrai si le statut contient « sans transaction » |
| `Triees`, `ParBanque`, `Seances` | **regroupement par banque** : dans chaque banque, triée par date, une clôture vide reprend la dernière clôture connue, puis `rendement` = clôture ajustée (rendement total) / clôture ajustée de la séance précédente − 1 ; la première séance n'a pas de rendement |
| `TypesFinaux` | types rétablis après le regroupement |

**Pourquoi ajuster** : sans ajustement, une attribution gratuite ou une division du nominal ressemble à
une chute du cours. BIAT : 118,000 le 02/01/2019, 111,000 le 31/12/2025, soit −5,9 % en brut et
+125,8 % ajusté (49,167 → 111,000). **Pourquoi le rendement sur la série « rendement total »** : le jour
du détachement d'un dividende, le cours baisse du montant versé ; ce n'est pas une variation de valeur
pour l'actionnaire, la volatilité ne doit pas la compter. Après ajustement, la plus forte variation
d'une séance à l'autre est de 10,7 % (BTE, 24/12/2020) : aucune opération ne crée de saut.

### 2.12b `Variations_Comparables` (chargée)

Une ligne par banque × trimestre × indicateur × mesure : `valeur_N` (la période) et `valeur_N1` (la même
période un an plus tôt) **lues dans le même document**, donc dans la même méthode (10 981 lignes).

| Étape | Ce qu'elle fait |
|---|---|
| `Fichier`, `Source`, `EnTetes`, `Types` | lit `variations_comparables.csv` ; types `en-US` |
| `VidesEnNull` | mention de retraitement vide → `null` |
| `Fusion`, `Nature` | **fusion avec `Dim_Indicateur`** : nature de l'indicateur |
| `Retenir`, `SansTrimDesStocks` | **colonne conditionnelle** et filtre : même règle que `Fait_Indicateurs`, un stock n'a pas de trimestre seul (304 lignes écartées) |
| `VariationPct` | **colonne calculée** `Variation_Pct` = (N − N-1) / \|N-1\| (vide si N-1 = 0) ; la valeur absolue garde une hausse positive quand N-1 est négatif (commissions encourues de BTE, autres produits) ; calculée ici, la colonne du CSV n'est pas reprise |
| `SansColonnes` | retire la variation du CSV, l'année et le rang du trimestre (ils viendront de la table de dates), `nature` et `retenir` |
| `Periodes`, `Segment` | **segment d'actionnariat** : périodes de `Banques_Actionnariat` gardées en mémoire, puis colonne `Segment_Actionnariat` = fonction `Actionnariat_A_La_Date` (catégorie de la banque à la date d'arrêté, section 2.12h) |

**Pourquoi une table à part** : les niveaux de `Fait_Indicateurs` de deux années viennent de deux
documents révisés différents ; leur rapport mélangerait deux méthodes. BH : PNB 2025 −2,8 % dans le
document du T4 2025 (2024 retraité), −11,0 % si l'on rapprochait le PNB 2025 du PNB 2024 publié un
an plus tôt. Les mesures de croissance (étape DAX) sommeront `valeur_N` et `valeur_N1` puis feront le
rapport, pour une banque comme pour le secteur.

### 2.12c `Fait_Etats_Financiers` (chargée)

Une ligne par banque × date × code (504 lignes) : résultat net avant modifications comptables
(`RES_NET`), total de l'actif (`TOTAL_ACTIF`) et capitaux propres du bilan (`CAP_PROPRES_EF`), comptes
individuels, au 30/06 de 2020 à 2026 et au 31/12 de 2019 à 2025.

| Étape | Ce qu'elle fait |
|---|---|
| `Fichier`, `Source`, `EnTetes`, `Types`, `VidesEnNull` | lit `etats_financiers_versions.csv` ; types `en-US` ; textes vides → `null` |
| `VersionRetenue` | **filtre sur la version retenue** (`version = source_valeur`) : la révisée par le document suivant de même type quand elle existe, sauf exception écrite (BNA 30/06/2025 : résultat avant modifications comptables) |
| `Colonnes`, `Renommees` | garde la valeur retenue (renommée `valeur_mdt`), la version, le fichier, la page, les statuts et la remarque |
| `Annualisation` | **colonne conditionnelle** `facteur_annualisation` : 2 pour un semestre, 1 pour un exercice ; le ROE et le ROA multiplieront le résultat par ce facteur |
| `Periodes`, `Segment` | **segment d'actionnariat** : périodes de `Banques_Actionnariat` gardées en mémoire, puis colonne `Segment_Actionnariat` = fonction `Actionnariat_A_La_Date` (catégorie de la banque à la date d'arrêté, section 2.12h) |

**Pourquoi la version révisée** : le capital et le total de l'actif d'ouverture (31/12/N-1) viennent
alors du document de l'exercice N, dans la même méthode que la valeur de fin de période. Les deux
dates sans document lisible (BH 31/12/2019, STB 30/06/2023) sont reprises de la colonne N-1 du
document suivant (statut « repris du document suivant »).

### 2.12d `Revisions_Etats_Financiers` (chargée)

Les 423 versions écartées des états financiers : la valeur publiée dans le document de la date
(version initiale) quand le document suivant de même type la redonne autrement, et la version révisée
non retenue de BNA au 30/06/2025. Mêmes étapes que `Revisions` : lecture du même fichier que
`Fait_Etats_Financiers`, **filtre inverse** (`version <> source_valeur`), `Ecart_MDT` = valeur
retenue − valeur de la version et `Ecart_Pct` calculés dans Power Query (la colonne du CSV n'est pas
reprise), **colonne conditionnelle** `Type_Revision` (statut en clair). Exemple : résultat net de l'UIB au
30/06/2020, −41,182 MDT publié, 17,912 retenu (+59,094 : intérêts du moratoire Covid réintégrés).

### 2.12e `Controle` (chargée)

Une ligne par document trimestriel (336) : statut de l'extraction, nombre de valeurs lues, alertes,
fichier, gabarit de mise en page.

| Étape | Ce qu'elle fait |
|---|---|
| `Fichier`, `Source`, `EnTetes`, `Types`, `VidesEnNull` | lit `controle_extraction.csv` ; textes vides → `null` |
| `DateArrete` | **colonne calculée** `date_arrete` : fin du trimestre à partir du texte « 2024T3 » (année = 4 premiers caractères, mois = 3 × rang du trimestre, dernier jour du mois) ; servira à la relation avec la table des dates |
| `NbAlertes` | nombre d'alertes du document (elles sont séparées par « \| ») ; 0 sans alerte |
| `CategorieStatut` | **colonne conditionnelle** : conforme (`ok`) ; écart signalé, qui vient de la banque et ne bloque pas (`retraitement possible`, `ecart trimestre/cumul`, `ecart composantes`) ; tableau en image saisi à la main ; tableau en image repris du document suivant ; alerte bloquante (2 erreurs du document de la banque, vérifiées sur l'image) |

**Pourquoi** : la page qualité montre, pour chaque banque et chaque trimestre, comment le chiffre a été
obtenu ; les statuts techniques du script deviennent cinq catégories lisibles.

### 2.12f `Ecarts_Annuels` (intermédiaire) et `Controle_Annuel` (chargée)

`Controle_Annuel` compare, pour chaque banque, année (2020–2025) et indicateur de flux (PNB, produits
et charges d'exploitation, charges opératoires), la somme des 4 trimestres retenus au cumul annuel
retenu (288 lignes). `Ecarts_Annuels` donne la cause de chacun des 22 écarts, trouvée dans les PDF.

| Requête | Étape | Ce qu'elle fait |
|---|---|---|
| `Ecarts_Annuels` | `Source` | lit `docs\ecarts_annuels.csv` dans le dossier du projet (`File.Contents(CheminDonnees & …)`) : fichier versionné, examiné à la main, hors de `donnees_publiees` |
| `Ecarts_Annuels` | `Types`, `Colonnes` | types `en-US` ; garde la clé (banque, année, indicateur) et l'explication (catégorie, cause, fichier, page, correction) |
| `Controle_Annuel` | `Fichier` … `Types` | lit `controle_annuel.csv` |
| `Controle_Annuel` | `Ecart` | **colonne calculée** `Ecart_MDT` = somme des trimestres − cumul annuel (la colonne du CSV n'est pas reprise) |
| `Controle_Annuel` | `DateArrete` | 31/12 de l'année, pour la relation avec les dates |
| `Controle_Annuel` | `Fusion`, `Developpee` | **fusion sur trois colonnes** (banque, année, indicateur) avec `Ecarts_Annuels` : catégorie, cause, fichier et page de la preuve, correction |
| `Controle_Annuel` | `StatutClair` | **colonne conditionnelle** : statut en clair ; un « ecart » sans cause écrite serait affiché « écart sans cause écrite » (aucun aujourd'hui, `test_ecarts_annuels_expliques` le garantit) |

**Pourquoi** : un écart entre la somme des trimestres et l'année n'est jamais corrigé en silence ; la
page qualité montre sa cause et le document qui la prouve (ex. ATB 2021 : T2 retraité dans la colonne
du trimestre mais pas dans le cumul du semestre).

### 2.12g `Gabarits` (intermédiaire), `Definitions_Charges` et `Definitions_Capitaux_Propres` (chargées)

`gabarits.csv` (versionné à la racine) décrit la mise en page des documents de chaque banque ; deux de
ses colonnes disent ce que la banque met dans ses charges opératoires et dans ses capitaux propres
trimestriels.

| Requête | Étape | Ce qu'elle fait |
|---|---|---|
| `Gabarits` | `Source` | lit `gabarits.csv` dans le dossier du projet (`File.Contents`), **11 colonnes** : la remarque, dernière colonne, contient parfois un « ; » |
| `Gabarits` | `Colonnes`, `Types` | garde la banque, la période et les deux définitions |
| `Definitions_Charges` | `Periodes` | **regroupement** par banque et définition : premier et dernier trimestre (`List.Min`, `List.Max`) ; les gabarits découpent l'historique par mise en page, la définition garde sa période entière |
| `Definitions_Charges` | `Description` | **colonne conditionnelle** : la définition en clair (sans dotations ; avec dotations publiées ; avec un reste non détaillé) |
| `Definitions_Capitaux_Propres` | `Colonnes`, `Distinctes` | une ligne par banque (`Table.Distinct`) |
| `Definitions_Capitaux_Propres` | `Description` | **colonne conditionnelle** : hors résultat de la période ; résultat inclus ; hors résultat avec affectation au 31/12 |

**Pourquoi** : le coefficient d'exploitation publié (charges opératoires / PNB) ne se compare pas d'une
banque à l'autre (BT et BH sans dotations, UIB et Wifak avec, les autres avec un reste non détaillé) ;
le rapport classe les banques avec le coefficient harmonisé et affiche la définition de chaque banque
en info-bulle. De même, les capitaux propres trimestriels ne servent qu'à la fiche banque, avec leur
définition ; les comparaisons utilisent ceux du bilan.

### 2.12h Segment d'actionnariat : fonction `Actionnariat_A_La_Date`

L'actionnariat d'une banque peut changer (UBCI : BNP Paribas jusqu'au 15/03/2021, groupe Carte ensuite).
Un trimestre doit donc être classé selon l'actionnariat **à sa date**, pas selon l'actionnariat
d'aujourd'hui (`Dim_Banque`).

`Actionnariat_A_La_Date` est une **fonction personnalisée** (requête non chargée) : elle reçoit la table
des périodes, une banque et une date, garde la ligne de `Banques_Actionnariat` dont la période couvre la
date (début vide ou antérieur, fin vide ou postérieure) et renvoie sa catégorie ; vide si aucune ou
plusieurs lignes la couvrent (`tests/test_actionnariat.py` vérifie que les périodes se suivent sans trou
ni chevauchement). `Fait_Indicateurs`, `Variations_Comparables` et `Fait_Etats_Financiers` l'appellent
pour chaque ligne (étapes `Periodes` et `Segment`) : la table des périodes est gardée en mémoire une
fois par requête, le fichier Excel n'est pas relu à chaque ligne.

**Pourquoi une fonction** : la même règle sert à trois tables de faits ; écrite une fois, elle ne peut pas
diverger d'une table à l'autre. Résultat : au T4 2020, 4 banques sous contrôle étranger (ATB, Attijari,
UBCI, UIB), 3 au T3 2026 ; 3 publiques (BNA, BH, STB) ; 1 mixte (BTE).

### 2.13 Fonctions et mots-clés M utilisés

Chaque fonction du langage M (Power Query) employée dans les requêtes, ce qu'elle fait ici et où elle
sert. Le test `tests/test_guide_powerbi.py` vérifie qu'aucune fonction d'un fichier `powerquery/*.pq`
ne manque à ce tableau.

**Lire les sources**

| Fonction | Ce qu'elle fait | Requêtes |
|---|---|---|
| `Folder.Files` | liste les fichiers d'un dossier (nom, contenu binaire, extension, dossier, dates) : connecteur Dossier | `Fichiers_Donnees`, `Dim_Banque` (logos) |
| `Binary.ToText` | écrit un contenu binaire en texte ; avec `BinaryEncoding.Base64`, en base 64 (image intégrée `data:image/png;base64,…`) | `Dim_Banque` |
| `File.Contents` | lit un fichier du disque en binaire | `Banques_Actionnariat` |
| `Excel.Workbook` | ouvre un classeur Excel et liste ses feuilles et ses tables nommées : connecteur Excel | `Banques_Actionnariat` |
| `Web.Contents` | télécharge une adresse web ; avec `RelativePath`, l'adresse de base reste fixe : source URL | `Operations_Titres`, `Evenements` |
| `Csv.Document` | lit un contenu CSV (séparateur `;`, encodage 65001 = UTF-8) en table de textes | `Versions`, `Dim_Indicateur`, `Dim_Banque`, `Operations_Titres`, `Evenements`, `Fait_Cours` |
| `QuoteStyle.Csv` | option de `Csv.Document` : un texte entre guillemets peut contenir un `;` | mêmes requêtes |
| `Table.PromoteHeaders` | la première ligne devient les noms de colonnes | mêmes requêtes |

**Typer et nettoyer**

| Fonction | Ce qu'elle fait | Requêtes |
|---|---|---|
| `Table.TransformColumnTypes` | donne un type à chaque colonne ; avec la culture `"en-US"`, `29.585` est lu 29,585 (et pas 29 585) | toutes les requêtes qui lisent un fichier |
| `Table.TransformColumns` | applique une fonction à chaque valeur d'une colonne (ici : contrôle de la catégorie d'actionnariat, erreur sinon) | `Banques_Actionnariat` |
| `Table.ReplaceValue` | remplace une valeur dans des colonnes (texte vide → `null`, `null` → « non », `null` → 1) | `Versions`, `Fait_Indicateurs`, `Fait_Cours` |
| `Replacer.ReplaceValue` | option de `Table.ReplaceValue` : remplace la valeur entière (pas un morceau de texte) | mêmes requêtes |
| `Table.SelectColumns` | garde les colonnes nommées, dans cet ordre | `Fichiers_Donnees`, `Fait_Indicateurs`, `Revisions`, `Fait_Cours` |
| `Table.RemoveColumns` | retire des colonnes | `Dim_Banque`, `Fait_Indicateurs`, `Fait_Cours` |
| `Table.RenameColumns` | renomme des colonnes | `Fichiers_Donnees`, `Fait_Indicateurs` |
| `Table.Sort` | trie les lignes | `Operations_Titres`, `Fait_Cours` |
| `Order.Ascending` | option de `Table.Sort` : ordre croissant | mêmes requêtes |

**Filtrer et calculer**

| Fonction | Ce qu'elle fait | Requêtes |
|---|---|---|
| `Table.SelectRows` | garde les lignes qui vérifient une condition (version retenue, versions écartées, ligne en cours, opérations postérieures) | `Fichiers_Donnees`, `Fait_Indicateurs`, `Revisions`, `Dim_Banque`, `Operations_Titres`, `Fait_Cours` |
| `Table.AddColumn` | ajoute une colonne calculée ligne par ligne : colonne conditionnelle (`if … then … else`) ou calcul | `Dim_Indicateur`, `Fait_Indicateurs`, `Revisions`, `Operations_Titres`, `Fait_Cours` |
| `Table.AddIndexColumn` | numérote les lignes (0, 1, 2…) pour retrouver la séance précédente | `Fait_Cours` |
| `Table.FillDown` | recopie vers le bas la dernière valeur non vide (dernière clôture connue) | `Fait_Cours` |
| `Table.First` | première ligne d'une table, ou une valeur par défaut si elle est vide (première opération postérieure) | `Fait_Cours` |
| `Table.RowCount` | nombre de lignes d'une table (une seule période d'actionnariat doit couvrir la date) | `Actionnariat_A_La_Date` |
| `Text.Contains` | le texte contient-il ce mot (« sans transaction ») ? | `Fait_Cours` |
| `Text.StartsWith` | le texte commence-t-il par ce préfixe (« revisee_31-12 », « exclue ») ? | `Revisions` |
| `Text.Proper` | met une majuscule au début du mot (« trim » → « Trim ») | `Fait_Indicateurs` |
| `Number.Abs` | valeur absolue (écart en % rapporté à la valeur absolue) | `Revisions`, `Variations_Comparables`, `Revisions_Etats_Financiers` |
| `Number.From` | convertit un texte en nombre (« 2024 » → 2024) | `Controle` |
| `Text.Start` | premiers caractères d'un texte (« 2024T3 » → « 2024 ») | `Controle` |
| `Text.End` | derniers caractères d'un texte (« 2024T3 » → « 3 ») | `Controle` |
| `Date.EndOfMonth` | dernier jour du mois d'une date (date d'arrêté du trimestre) | `Controle` |
| `Text.Lower` | met un texte en minuscules (extension « .PNG » ou « .png ») | `Dim_Banque` |
| `Text.BeforeDelimiter` | partie d'un texte avant un séparateur (« AB.png » → « AB ») | `Dim_Banque` |
| `Text.Split` | découpe un texte selon un séparateur (alertes séparées par « \| ») | `Controle` |
| `List.Count` | nombre d'éléments d'une liste (nombre d'alertes) | `Controle` |
| `List.Contains` | la liste contient-elle cette valeur (les quatre catégories d'actionnariat) ? | `Banques_Actionnariat` |
| `List.Product` | produit des nombres d'une liste (facteurs d'ajustement cumulés) | `Operations_Titres` |
| `List.Min` | plus petite valeur d'une liste (premier trimestre d'une définition) | `Definitions_Charges` |
| `List.Max` | plus grande valeur d'une liste (dernier trimestre d'une définition) | `Definitions_Charges` |
| `List.RemoveNulls` | retire les valeurs vides d'une liste (un facteur absent n'annule pas le produit) | `Operations_Titres` |

**Combiner et restructurer**

| Fonction | Ce qu'elle fait | Requêtes |
|---|---|---|
| `Table.NestedJoin` | **fusion** de deux requêtes sur une clé : chaque ligne reçoit une table des lignes correspondantes | `Fait_Indicateurs`, `Dim_Banque`, `Fait_Cours` |
| `JoinKind.LeftOuter` | jointure externe gauche : toutes les lignes de la première table sont gardées | mêmes requêtes |
| `Table.ExpandTableColumn` | développe la table de la fusion en colonnes (nature, actionnariat) | `Fait_Indicateurs`, `Dim_Banque` |
| `Table.ExpandRecordColumn` | développe un enregistrement en colonnes (facteurs de l'opération suivante) | `Fait_Cours` |
| `Table.Combine` | **ajoute** des tables les unes sous les autres (codes des états financiers, séances des 12 banques) | `Dim_Indicateur`, `Fait_Cours` |
| `Table.UnpivotOtherColumns` | **dépivotage** : une colonne par attribut devient une ligne par attribut | `Fait_Indicateurs` |
| `Table.Pivot` | **pivot** : une ligne par attribut devient une colonne par attribut | `Fait_Indicateurs` |
| `Table.Group` | **regroupement** : une table par banque, traitée à part (rendement séance par séance) ; une ligne par banque et définition (période des charges opératoires) | `Fait_Cours`, `Definitions_Charges` |
| `Table.Distinct` | garde une seule fois chaque ligne identique (une définition des capitaux propres par banque) | `Definitions_Capitaux_Propres` |
| `Table.Buffer` | garde une table en mémoire : elle n'est pas relue (ni retéléchargée) à chaque utilisation | `Operations_Titres`, `Fait_Cours` |
| `List.Buffer` | même chose pour une liste (clôtures connues d'une banque) | `Fait_Cours` |

**Mots-clés du langage**

| Mot-clé | Ce qu'il fait |
|---|---|
| `let … in` | suite d'étapes nommées ; la requête renvoie l'étape écrite après `in` (chaque nom est une ligne de « Étapes appliquées ») |
| `each [colonne]` | fonction appliquée à chaque ligne ; `[colonne]` est la valeur de la ligne en cours |
| `(op) => …` | fonction avec un paramètre nommé, quand deux lignes sont comparées (une opération et les autres, une séance et les opérations) |
| `(periodes as table, banque as text, jour as date) as nullable text => …` | **fonction personnalisée** enregistrée comme requête : paramètres typés, résultat typé ; appelée ligne par ligne par d'autres requêtes |
| `table{0}[colonne]` | valeur d'une colonne dans la première ligne d'une table |
| `if … then … else` | condition : c'est le code d'une colonne conditionnelle |
| `error "…"` | provoque une erreur visible à l'actualisation (catégorie d'actionnariat inconnue) |
| `#table(type table […], {…})` | table écrite dans la requête (3 codes des états financiers) |
| `#date(année, mois, jour)` | date écrite à partir de nombres (premier jour du dernier mois du trimestre) |
| `meta [IsParameterQuery = true …]` | fait d'une valeur un paramètre (`CheminDonnees`, `AdresseDepot`) |
| `type number`, `type text`, `type date`, `Int64.Type`, `type logical` | types des colonnes : nombre décimal, texte, date, entier, vrai ou faux |
| `null` | valeur absente ; un calcul avec `null` donne `null` (jamais zéro) |

## 3. Modèle et mesures DAX

Le modèle se construit par groupes, chacun vérifié dans Power BI Desktop avant le suivant : table des
dates, relations du modèle en étoile, puis mesures (bases, totaux du secteur, ratios, croissances, ROE et
ROA, Bourse, qualité). Le code DAX est dans `dax/` (copie lisible, identique au code du projet `.pbip`) ;
une table calculée s'écrit dans le TMDL avec `ecrire_table_calculee` de `scripts/ecrire_tmdl_table.py`
(`python scripts/ecrire_tmdl_table.py Dim_Date` pour la table des dates).

### 3.1 `Dim_Date` (table calculée DAX)

Une table de dates sert de filtre commun à toutes les tables qui ont une date (indicateurs, variations,
états financiers, cours, révisions, contrôles, événements) : un segment « 2024T3 » ou « Covid » filtre
alors toutes les pages de la même façon, et les fonctions de temps de DAX (`LASTNONBLANK`, `DATEADD`…)
ont besoin d'une colonne de dates continue, sans jour manquant. Elle est écrite en DAX plutôt qu'en
Power Query parce qu'elle ne lit aucune source : elle se calcule dans le modèle (`dax/Dim_Date.dax`).
Le code part de celui de la spécification (section 6), avec deux changements : le libellé du
trimestre au format des faits et la colonne de tri de la période.

Étapes :

1. **`CALENDAR ( DATE ( 2019, 1, 1 ), DATE ( 2026, 12, 31 ) )`** : une ligne par jour, colonne `Date`.
   Bornes fixes : les données vont du 02/01/2019 (premier cours) au 31/12/2026 au plus ; des bornes
   fixes évitent qu'une date erronée dans un fait étire la table (ce que ferait `CALENDARAUTO`). Les
   trimestres 2019T1 à 2019T3 restent dans la table pour les cours de 2019.
2. **`ADDCOLUMNS`** ajoute à chaque jour :
   - `Annee` (`YEAR`) et `Trimestre` (« T1 » à « T4 », `QUARTER`) : la mesure du chiffre annuel prend
     le cumul au trimestre « T4 » (spécification 7.1) ;
   - `Annee_Trimestre` : « 2024T3 », **au même format que la colonne `trimestre` des faits et des
     documents** (`BIAT_2024T3.pdf`), plutôt que le « 2024-T3 » de la première version de la
     spécification : un même libellé partout ;
   - `Cle_Trimestre` : 20243 (= 2024 × 10 + 3), nombre qui suit l'ordre chronologique ;
     `Annee_Trimestre` est **triée par** cette colonne (un texte se trierait bien ici aussi, mais le
     tri explicite ne dépend pas du format du libellé) ;
   - `Fin_Trimestre` : vrai le dernier jour d'un trimestre (31/03, 30/06, 30/09, 31/12), seuls jours
     où il y a des indicateurs trimestriels et des états financiers ;
   - `Periode` (colonne conditionnelle, `SWITCH ( TRUE (), … )` : la première condition vraie
     l'emporte) : « Avant Covid » avant le 01/03/2020, « Covid » jusqu'au 31/12/2021, « Après Covid »
     ensuite. Pour les indicateurs, datés de la fin du trimestre : 2019T4 avant Covid, 2020T1 à
     2021T4 Covid (8 trimestres), 2022T1 à 2026T3 après Covid (19 trimestres) ;
   - `Ordre_Periode` (1, 2, 3) : `Periode` est triée par cette colonne, sinon l'ordre alphabétique
     mettrait « Après Covid » en premier dans les segments et les axes.
   - `Choix_Trimestre` (ajoutée avec le groupe 2 des mesures, 3.4) : « Dernier trimestre complet » pour
     tous les jours du dernier trimestre où **les 12 banques** ont publié le PNB du trimestre, les crédits
     et les dépôts (valeurs retenues), sinon le libellé « 2024T3 » ; triée par `Ordre_Choix_Trimestre`
     (0 pour le dernier trimestre complet, donc en tête des segments ; `Cle_Trimestre` sinon). Le calcul
     se fait une fois, avant `ADDCOLUMNS` (variables `VAR`) : `FILTER` garde les lignes de
     `Fait_Indicateurs` qui ont une valeur pour ces trois indicateurs, `GROUPBY` les compte par date
     d'arrêté (`COUNTX ( CURRENTGROUP (), 1 )`), une date est complète quand elle a 3 × 12 = 36 valeurs,
     `MAXX` garde la plus récente. Un segment réglé sur « Dernier trimestre complet » reste juste après
     chaque actualisation : quand le T4 2026 sera publié par les 12 banques, il prendra ce libellé tout
     seul, sans toucher au rapport (règle « filtre par défaut sur le dernier trimestre complet », pas sur
     le dernier trimestre qui contient une donnée : au début d'un trimestre, seules quelques banques ont
     publié) ;
   - `Trimestre_Publie` (ajoutée le 30/10/2026 avec la page 1) : vrai pour les trimestres où au moins une banque a
     publié le PNB, les crédits ou les dépôts (mêmes lignes que pour `Choix_Trimestre`, clés des trimestres
     `SELECTCOLUMNS` puis test `IN`). Elle filtre les segments de trimestre : sans elle, ils listeraient aussi 2019T1
     à 2019T3 (avant les données), les trimestres pas encore publiés (2026T4) et la ligne « (Vide) » de la table des
     dates (créée par la relation inactive vers la date d'entrée des actionnaires, dont les premières périodes n'ont
     pas de date). Un filtre par mesure ne convient pas sur un segment : il se calcule avec la sélection du segment
     lui-même et ne laisse que la valeur choisie ;
3. **Réglages du modèle** (dans le TMDL) : table **marquée comme table de dates** sur la colonne `Date`
   (`dataCategory: Time`, `isKey` ; dans Power BI : **Outils de table › Marquer comme table de
   dates**) ; colonnes de tri `Cle_Trimestre` et `Ordre_Periode` **masquées** (elles ne servent qu'au
   tri, comme `Ordre_Choix_Trimestre`) ; synthèse « Ne pas résumer » partout (une année ne s'additionne pas).

Contrôles attendus (vue **Données**, table `Dim_Date`) :

| Contrôle | Attendu |
|---|---|
| Nombre de lignes (bas de la fenêtre) | 2 922 (8 années, dont 2020 et 2024 bissextiles) |
| `Fin_Trimestre` = Vrai (filtre de la colonne) | 32 lignes, du 31/03/2019 au 31/12/2026 |
| `Periode` (filtre de la colonne, ou visuel Table avec le nombre de `Date`) | Avant Covid 425, Covid 671, Après Covid 1 826 |
| Ordre dans un segment `Periode` | Avant Covid, Covid, Après Covid |
| `Annee_Trimestre` | 32 valeurs, de 2019T1 à 2026T4, dans l'ordre chronologique |
| **Outils de table › Marquer comme table de dates** | coché, colonne `Date` |
| Volet **Données** | `Cle_Trimestre` et `Ordre_Periode` absentes (masquées) |

La table ne filtre les faits qu'à travers les relations (3.2).

### 3.2 Relations du modèle en étoile

Un modèle en étoile relie chaque table de faits à des **dimensions** (dates, banques, indicateurs) :
une ligne de la dimension correspond à plusieurs lignes du fait (relation **1 → plusieurs**), et le
filtre ne va que de la dimension vers le fait (**filtre simple**). Un segment de banque, de trimestre
ou d'indicateur filtre alors toutes les tables de la même façon, sans relation entre les faits
eux-mêmes (deux faits ne se filtrent jamais directement : pas de chemin ambigu). Les relations sont
écrites dans `definition/relationships.tmdl` (`python scripts/ecrire_tmdl_table.py relations`) ;
28 relations :

| Dimension (côté 1) | Tables de faits (côté plusieurs) | Nombre |
|---|---|---|
| `Dim_Date[Date]` | `date_arrete` de `Fait_Indicateurs`, `Variations_Comparables`, `Fait_Etats_Financiers`, `Revisions`, `Revisions_Etats_Financiers`, `Controle`, `Controle_Annuel` ; `Evenements[date]` ; `Fait_Cours[date]` | 9 |
| `Dim_Banque[code_banque]` | `banque` des 9 mêmes tables, de `Definitions_Charges` et de `Definitions_Capitaux_Propres` ; `Banques_Actionnariat[code_banque]` | 12 |
| `Dim_Indicateur[code_indicateur]` | `code_indicateur` de `Fait_Indicateurs`, `Variations_Comparables`, `Revisions`, `Controle_Annuel` ; `Evenements[indicateur]` ; `code` de `Fait_Etats_Financiers` et `Revisions_Etats_Financiers` | 7 |

Choix :

- **`Fait_Cours` relié par la banque** (`code_banque` → `banque`) et non par le ticker comme dans la
  première version de la spécification : `Fait_Cours` contient aussi le code de la banque, et une même
  clé partout est plus simple à lire (une dimension n'a de toute façon qu'une relation active vers une
  table).
- **`Banques_Actionnariat` et les définitions** (charges opératoires, capitaux propres) reliées à
  `Dim_Banque` : le segment de banque de la fiche banque les filtre aussi.
- **Codes des états financiers** (`RES_NET`, `TOTAL_ACTIF`, `CAP_PROPRES_EF`) : ajoutés à
  `Dim_Indicateur` dans Power Query (2.4), ce qui permet la relation avec `Fait_Etats_Financiers` et
  garde les événements sur le résultat net (moratoire UIB 2020).
- **Contrôle d'intégrité avant d'écrire** : chaque banque, code et date des faits existe dans sa
  dimension (aucune clé vide ; dates du 02/01/2019 au 20/10/2026). Sinon Power BI ajoute une ligne
  « (vide) » à la dimension, qui regroupe les lignes orphelines.

**Disposition de la vue Modèle** (`diagramLayout.json`, `python scripts/ecrire_tmdl_table.py diagramme`) :
l'onglet « Toutes les tables » range les tables en trois lignes, faits en haut (indicateurs, variations,
états financiers, cours, événements), dimensions au milieu (`Dim_Indicateur`, `Dim_Date`, `Dim_Banque`),
tables de qualité en bas (révisions, contrôles), et à droite les tables propres à chaque banque
(actionnariat, définitions). Quatre onglets par thème montrent chacun une petite étoile lisible :
« Indicateurs trimestriels », « États financiers », « Bourse », « Qualité des données » (une table peut
figurer dans plusieurs onglets ; un onglet ne change que l'affichage, pas le modèle).

Contrôles attendus :

| Contrôle | Attendu |
|---|---|
| Vue **Modèle**, ou **Accueil › Gérer les relations** | 28 relations, toutes actives, cardinalité « plusieurs à un (*:1) », filtre « Unique » |
| Visuel Table : `Dim_Date[Periode]` + nombre de `Fait_Cours[date]` | Avant Covid 3 480, Covid 5 484, Après Covid 14 496 (total 23 460) |
| Même visuel, segment `Dim_Banque[code_banque]` = BIAT | Covid 457 séances |
| Visuel Table : `Dim_Date[Periode]` + nombre de `Evenements[id_evenement]` | Covid 9, Après Covid 2 (pas de ligne Avant Covid) |
| Visuel Table : `Dim_Date[Periode]` + nombre de `Controle[banque]` | Avant Covid 12, Covid 96, Après Covid 228 |
| Visuel Table : `Dim_Indicateur[code_indicateur]` + nombre de `Fait_Etats_Financiers[valeur_mdt]` | `RES_NET`, `TOTAL_ACTIF`, `CAP_PROPRES_EF` : 168 chacun |
| Segment de banque ou de période dans ces visuels | aucune ligne « (vide) » |

### 3.3 Mesures de base (groupe 1, spécification 7.1)

Les mesures sont rangées dans une table **`Mesures`** (en tête du volet Données, icône de calculatrice) :
une table sans données (une colonne masquée, `ROW ( "Colonne_Masquee", 0 )`) qui ne sert qu'à regrouper
les mesures, au lieu de les disperser dans les tables de faits. Chaque mesure a un **dossier d'affichage**
(`1. Bases\Flux du trimestre`…), un **format** (`#,0.000` : millions de dinars à trois décimales,
comme les documents en milliers de dinars) et une **description** (info-bulle dans le volet Données).
Le texte de chaque mesure est dans `dax/mesures.dax` ; `python scripts/ecrire_tmdl_table.py mesures`
l'écrit dans le modèle.

**Deux mesures intermédiaires portent toutes les autres** : `Valeur Trim` (somme de
`Fait_Indicateurs[Valeur_Trim]`, trimestre seul) et `Valeur Cumul` (somme de `Valeur_Cumul` : cumul depuis
janvier pour un flux, solde pour un encours). Les valeurs sont déjà les valeurs retenues (version révisée
quand elle existe, 2.5). Chacune ne renvoie un nombre que si la sélection ne contient **qu'une date
d'arrêté** (`DISTINCTCOUNT ( Fait_Indicateurs[date_arrete] ) = 1`) : un visuel qui couvre une année
entière n'additionne donc jamais quatre trimestres ni quatre cumuls, il reste vide. Ce garde-fou applique
deux règles du projet : un chiffre annuel vient du cumul publié au 31/12 (les révisions en cours d'année
rendent la somme des trimestres fausse), et un encours ne s'additionne pas dans le temps. Plusieurs banques
à une même date s'additionnent bien (somme du secteur, encadrée par le groupe 2).

| Dossier | Mesures | Calcul |
|---|---|---|
| Flux du trimestre | `PNB`, `Charges operatoires`, `Frais personnel`, `Charges generales`, `Revenus portefeuille` | `Valeur Trim` filtrée sur le code de l'indicateur (`CALCULATE`) |
| Flux du trimestre | `Marge interets`, `Marge commissions` | intérêts perçus − encourus, commissions en produits − encourues ; **vide si l'une des deux manque** (en DAX, `vide − x` vaut `−x` : le test `ISBLANK` empêche qu'un vide soit lu comme zéro) |
| Flux cumulés | `PNB depuis debut annee` | cumul publié à la dernière date de la sélection qui a une valeur (`LASTNONBLANK`) |
| Flux cumulés | `PNB annuel` | cumul publié au T4 (31/12) de l'année sélectionnée ; vide pour 2026 (pas encore de T4) |
| Encours | `Credits`, `Depots`, `Depots a vue`, `Depots epargne`, `Depots terme`, `Emprunts` | solde à la dernière date de la sélection qui a une valeur ; dépôts à terme publiés par une partie des banques seulement |
| Fiche banque | `Capitaux propres hors resultat de la periode` | capitaux propres trimestriels, définition propre à chaque banque (`Definitions_Capitaux_Propres`) : jamais dans une comparaison entre banques (capitaux propres du bilan, groupe ROE/ROA) |
| Intermédiaires | `Valeur Trim`, `Valeur Cumul`, `PNB cumul brut` et les `… brut` des encours | valeur à une date, avant le choix de la dernière date |

Comment lire `LASTNONBLANK ( Dim_Date[Date], [Credits brut] )` : parmi les jours de la sélection, garder le
dernier où `Credits brut` n'est pas vide (le 30/09/2024 pour le T3 2024, le 30/09/2026 pour l'année 2026),
puis calculer la mesure à ce seul jour.

**Contrôle** : coller `dax/controle_bases.dax` dans la **vue Requête DAX** (icône « DAX » à gauche), puis
**Exécuter** ; trois résultats. Valeurs attendues (calculées à part depuis `donnees_publiees/`, MDT) :

| Banque | PNB 2024T3 | Marge intérêts | Marge commissions | Frais personnel | PNB depuis début 2024 | Crédits | Dépôts | PNB annuel 2024 |
|---|---|---|---|---|---|---|---|---|
| AB | 126,287 | 45,766 | 30,502 | 42,345 | 421,264 | 7 171,877 | 8 371,009 | 566,487 |
| ATB | 93,205 | 53,355 | 20,903 | 34,407 | 275,494 | 5 399,421 | 6 272,819 | 380,166 |
| BH | 188,447 | 89,940 | 38,689 | 49,212 | 552,339 | 10 687,376 | 9 082,984 | 701,188 |
| BIAT | 367,474 | 169,526 | 70,309 | 85,746 | 1 089,618 | 12 431,844 | 19 724,504 | 1 479,715 |
| BNA | 243,669 | 68,654 | 39,763 | 68,339 | 742,424 | 14 329,840 | 13 079,843 | 976,006 |
| BT | 117,182 | 75,149 | 18,395 | 24,507 | 376,220 | 5 845,271 | 6 163,804 | 509,985 |
| BTE | 17,232 | 6,105 | 6,459 | 9,873 | 49,315 | 950,098 | 1 049,998 | 66,296 |
| STB | 174,182 | 72,269 | 31,165 | 55,592 | 490,165 | 9 969,862 | 11 127,667 | 649,739 |
| TJARI | 177,670 | 96,537 | 34,700 | 58,910 | 526,362 | 7 237,843 | 10 478,881 | 707,895 |
| UBCI | 82,232 | 45,962 | 17,065 | 34,247 | 235,617 | 3 061,387 | 3 707,111 | 320,707 |
| UIB | 133,481 | 80,165 | 36,647 | 46,822 | 399,804 | 6 286,998 | 6 635,941 | 536,335 |
| WIB | 23,461 | 15,771 | 7,118 | 8,548 | 66,224 | 1 107,241 | 1 056,805 | 92,880 |

Troisième résultat : PNB 2024T3 des 12 banques 1 744,522 ; crédits 84 479,057 ; `PNB` et `PNB annuel` sans
filtre vides. Deuxième résultat : la colonne « PNB sur l'annee » vide pour chaque banque (garde-fou). BH
2024 : 701,188 et non 765,932, car la valeur retenue est la version révisée du document 2025T4 (retraitement
« pour des raisons de comparabilité », événement `BH_RETRAITEMENT_2024`).

### 3.4 Secteur : banques présentes, totaux, parts de marché, rangs (groupe 2, spécification 7.4)

Règle du projet : **un total du secteur, une part de marché, un rang ou un indice de concentration n'existe
que si les 12 banques sont présentes** ; sinon la mesure reste vide et le nombre de banques présentes
s'affiche à côté. Un total de 11 banques comparé à un total de 12 ferait croire à une baisse du secteur.

| Dossier | Mesures | Calcul |
|---|---|---|
| Banques présentes | `Nombre de banques` | `COUNTROWS ( ALL ( Dim_Banque ) )` : 12, sans écrire le nombre en dur |
| Banques présentes | `Banques presentes PNB` | banques dont `PNB` n'est pas vide (`FILTER ( ALL ( Dim_Banque ), … )` : le filtre de banque du visuel est ignoré, on compte toujours sur les 12) |
| Banques présentes | `Banques presentes credits`, `Banques presentes depots` | même calcul, **à la dernière date d'arrêté de la sélection** (`Date fin credits`, `Date fin depots`) |
| Banques présentes | `Banques presentes` | pour l'indicateur choisi dans un segment de `Dim_Indicateur` (cumul ou solde) ; vide si aucun ou plusieurs indicateurs sont choisis |
| Totaux | `PNB secteur`, `Credits secteur`, `Depots secteur` | somme des 12 banques (`REMOVEFILTERS ( Dim_Banque )`) si les 12 sont présentes, sinon vide |
| Parts de marché | `Part de marche PNB`, `… credits`, `… depots` | valeur de la banque / total du secteur (`DIVIDE` : vide si le total est vide) |
| Concentration | `HHI PNB` | indice de Herfindahl-Hirschman : somme des carrés des parts × 10 000 ; 833 si les 12 banques étaient égales, 10 000 pour une seule banque ; en dessous de 1 500, marché considéré comme peu concentré (seuil usuel des autorités de la concurrence) |
| Rangs | `Rang PNB` | `RANKX` sur les 12 banques, du plus grand PNB (1) au plus petit ; vide hors d'une ligne de banque ou si une banque manque |
| Dernier trimestre complet | `Dernier trimestre complet`, `Date dernier trimestre complet` | libellé (« 2026T3 ») et date du trimestre marqué dans `Dim_Date[Choix_Trimestre]` |

**Pourquoi les encours se comptent à la dernière date.** Sur une sélection de plusieurs trimestres (l'année
2026, par exemple), chaque banque a son dernier encours ; si une banque n'avait pas encore publié le dernier
trimestre, l'addition mélangerait des dates. Le total du secteur se lit donc à **la dernière date où au moins
une banque a publié** (`MAX ( Fait_Indicateurs[date_arrete] )` sans filtre de banque), et les banques sont
comptées **à cette même date** : au début d'un trimestre (quelques banques publiées), le total reste vide au
lieu d'additionner des banques à des dates différentes.

Ce qui viendra avec les ratios (groupe 3) : coefficient d'exploitation du secteur, médiane et rang du
coefficient (spécification 7.4), qui reposent sur le coefficient harmonisé (7.2).

**Contrôle** : vider la vue Requête DAX (**Ctrl+A**, **Suppr**), coller `dax/controle_secteur.dax`,
**Exécuter** ; trois résultats. Valeurs attendues (calculées à part depuis `donnees_publiees/`) :

Résultat 1, T3 2024, du rang 1 au rang 12 :

| Banque | Part de marché PNB | Rang PNB | Part de marché crédits | Part de marché dépôts |
|---|---|---|---|---|
| BIAT | 21,06 % | 1 | 14,72 % | 20,39 % |
| BNA | 13,97 % | 2 | 16,96 % | 13,52 % |
| BH | 10,80 % | 3 | 12,65 % | 9,39 % |
| TJARI | 10,18 % | 4 | 8,57 % | 10,83 % |
| STB | 9,98 % | 5 | 11,80 % | 11,50 % |
| UIB | 7,65 % | 6 | 7,44 % | 6,86 % |
| AB | 7,24 % | 7 | 8,49 % | 8,65 % |
| BT | 6,72 % | 8 | 6,92 % | 6,37 % |
| ATB | 5,34 % | 9 | 6,39 % | 6,48 % |
| UBCI | 4,71 % | 10 | 3,62 % | 3,83 % |
| WIB | 1,34 % | 11 | 1,31 % | 1,09 % |
| BTE | 0,99 % | 12 | 1,12 % | 1,09 % |

Résultat 2 : banques présentes PNB 2024T3 = 12 ; PNB secteur 1 744,522 ; HHI PNB 1 168,5 (peu concentré) ;
crédits secteur 84 479,057 ; dépôts secteur 96 751,366 ; crédits secteur sur 2026 = 86 880,036 au
30/09/2026 (date fin crédits) ; dernier trimestre complet « 2026T3 », au 30/09/2026 (les 28 trimestres de
2019T4 à 2026T3 sont complets pour ces trois indicateurs).

Résultat 3 (indicateurs publiés par une partie des banques) : `PORTEF` 11 banques en 2020T1 (BTE : document
en image, détail du bilan non saisi), 12 en 2024T3 ; `DEP_TERME` 3 en 2020T1, 4 en 2024T3.

Dans Power BI (vue **Données**, `Dim_Date`) : `Choix_Trimestre` contient « Dernier trimestre complet » pour
les jours du T3 2026 et plus de « 2026T3 » ; dans un segment, « Dernier trimestre complet » vient en premier.

### 3.5 Ratios et comparaison du coefficient (groupe 3, spécification 7.2 et 7.4)

**Deux coefficients d'exploitation.** Les charges opératoires publiées n'ont pas le même contenu d'une
banque à l'autre : BT, BH, BTE, STB les publient sans dotations aux amortissements, WIB et UIB avec les
dotations, BNA, ATB, AB, BIAT avec un reste non détaillé (`Definitions_Charges`). Comparer « charges
opératoires / PNB » entre banques comparerait donc des contenus différents.

- `Coef exploitation harmonise` = (frais de personnel + charges générales d'exploitation) / PNB : même
  définition pour toutes les banques ; **sert à toutes les comparaisons et à tous les classements**. Il se
  calcule sur une table d'une ligne par banque (`ADDCOLUMNS ( VALUES ( Dim_Banque[code_banque] ), … )`) qui
  garde les trois montants, puis ne retient que les banques qui ont les trois (`FILTER`) : une banque sans
  composantes ne fausse pas le coefficient d'un groupe de banques, et le PNB du dénominateur est pris sur les
  mêmes banques que les charges du numérateur. Pour plusieurs banques, c'est une moyenne pondérée par le PNB
  (somme des charges / somme des PNB), pas une moyenne des coefficients.
- `Coef exploitation publie` = charges opératoires publiées / PNB : **pour information** (fiche banque, avec
  la définition de la banque), jamais classé.
- `Coef exploitation harmonise annuel` : même calcul avec les **cumuls publiés au 31/12** (`Frais personnel
  annuel`, `Charges generales annuel`, `PNB annuel`), jamais la somme des quatre trimestres. Le coefficient du
  trimestre reste vide sur une année entière (garde-fou de 3.3).

**Comparaison au secteur** (même règle que 3.4 : vide si une des 12 banques manque) :

| Mesure | Calcul |
|---|---|
| `Banques presentes coef` | banques qui publient frais de personnel, charges générales et PNB |
| `Coef secteur` | coefficient harmonisé des 12 banques ensemble (moyenne pondérée par le PNB) |
| `Coef mediane` | médiane des 12 coefficients (`MEDIANX`) : la banque « du milieu », que les extrêmes (BTE, BT) ne déplacent pas, contrairement à la moyenne |
| `Ecart coef / mediane` | coefficient de la banque − médiane, en points (négatif : plus efficace que la banque médiane) |
| `Rang coef` | `RANKX … ASC` : 1 = coefficient le plus bas, donc la banque la plus efficace |

**Autres ratios** (trimestre, `DIVIDE` : vide si le dénominateur manque) : `Part marge interets`, `Part
commissions`, `Part portefeuille` (structure du PNB), `Frais personnel / PNB`, `Credits / Depots` (plus de
100 % : la banque prête plus qu'elle ne collecte de dépôts, le reste vient des emprunts et des fonds
propres), `Part depots a vue` (ressources peu coûteuses). Les trois parts du PNB ne font pas 100 % : le PNB
comprend aussi les gains de change et d'autres produits.

**Contrôle** : vider la vue Requête DAX (**Ctrl+A**, **Suppr**), coller `dax/controle_ratios.dax`, **Exécuter** ;
trois résultats. Valeurs attendues (calculées à part depuis `donnees_publiees/`) :

Résultat 1, T3 2024, du rang 1 au rang 12 (écart en points) :

| Banque | Coef harmonisé | Rang | Écart / médiane | Coef publié | Part marge intérêts | Part commissions | Part portefeuille | Frais pers. / PNB | Crédits / Dépôts | Part dépôts à vue |
|---|---|---|---|---|---|---|---|---|---|---|
| BT | 29,5 % | 1 | −16,1 | 29,5 % | 64,1 % | 15,7 % | 20,2 % | 20,9 % | 94,8 % | 32,8 % |
| BH | 36,2 % | 2 | −9,4 | 36,2 % | 47,7 % | 20,5 % | 31,7 % | 26,1 % | 117,7 % | 33,1 % |
| BNA | 39,1 % | 3 | −6,5 | 40,7 % | 28,2 % | 16,3 % | 55,5 % | 28,0 % | 109,6 % | 25,9 % |
| BIAT | 41,4 % | 4 | −4,2 | 44,9 % | 46,1 % | 19,1 % | 34,7 % | 23,3 % | 63,0 % | 46,6 % |
| AB | 45,0 % | 5 | −0,6 | 46,8 % | 36,2 % | 24,2 % | 39,6 % | 33,5 % | 85,7 % | 28,4 % |
| TJARI | 45,0 % | 6 | −0,6 | 47,7 % | 54,3 % | 19,5 % | 26,1 % | 33,2 % | 69,1 % | 45,3 % |
| UIB | 46,2 % | 7 | +0,6 | 48,5 % | 60,1 % | 27,5 % | 12,5 % | 35,1 % | 94,7 % | 27,2 % |
| STB | 48,1 % | 8 | +2,5 | 48,1 % | 41,5 % | 17,9 % | 40,6 % | 31,9 % | 89,6 % | 37,4 % |
| WIB | 53,2 % | 9 | +7,6 | 58,2 % | 67,2 % | 30,3 % | 2,4 % | 36,4 % | 104,8 % | 28,9 % |
| ATB | 57,8 % | 10 | +12,2 | 62,2 % | 57,2 % | 22,4 % | 20,3 % | 36,9 % | 86,1 % | 31,1 % |
| UBCI | 65,5 % | 11 | +19,9 | 68,1 % | 55,9 % | 20,8 % | 23,4 % | 41,6 % | 82,6 % | 52,9 % |
| BTE | 79,1 % | 12 | +33,5 | 79,1 % | 35,4 % | 37,5 % | 23,9 % | 57,3 % | 90,5 % | 26,7 % |

AB et TJARI sont à 45,0 % à l'arrondi, mais pas exactement égaux (rangs 5 et 6). Le coefficient publié est
égal au coefficient harmonisé pour les banques qui publient leurs charges opératoires sans dotations (BT, BH,
STB, BTE), plus élevé pour les autres.

Résultat 2 : 12 banques ; coefficient du secteur 43,93 % ; médiane 45,6 % ; coefficient du trimestre sur
l'année 2024 vide ; coefficient annuel 2024 des 12 banques 44,09 %.

Résultat 3, coefficient harmonisé annuel 2024 : AB 38,4 % ; ATB 59,1 % ; BH 37,2 % ; BIAT 41,7 % ; BNA
38,3 % ; BT 30,6 % ; BTE 93,4 % ; STB 50,1 % ; TJARI 45,3 % ; UBCI 65,6 % ; UIB 48,0 % ; WIB 60,7 %.

La vue Requête DAX affiche les pourcentages en décimales (0.295 pour 29,5 %).

### 3.6 Croissances, tendance et annotations (groupe 4, spécification 7.3)

**Une variation sur un an se lit dans un seul document.** Chaque document trimestriel publie l'année N et
l'année N-1 côte à côte, dans la même méthode ; `Variations_Comparables` garde ces deux colonnes (2.12b).
Rapprocher deux documents (`SAMEPERIODLASTYEAR` ou `DATEADD` sur `Fait_Indicateurs`) mélangerait deux
méthodes quand la banque a retraité ses chiffres. Exemple : BH, PNB 2025 contre 2024. Le document du T4 2025
donne −2,8 % (681,479 contre 701,188, 2024 retraité) ; le PNB 2024 publié un an plus tôt (765,932) donnerait
−11,0 %, une baisse qui vient surtout du changement de méthode.

| Dossier | Mesures | Calcul |
|---|---|---|
| Intermédiaires | `VC N trim`, `VC N1 trim`, `VC N cumul`, `VC N1 cumul` | sommes des colonnes N et N-1 de `Variations_Comparables`, une date d'arrêté à la fois (même garde-fou qu'en 3.3) |
| Sur un an | `Var A/A trimestre %`, `Var A/A cumul %` | pour l'indicateur choisi dans un segment ; le cumul est pris à la dernière date de la sélection qui a une valeur |
| Sur un an | `Var PNB A/A %`, `Var PNB cumul A/A %`, `Var PNB annuel A/A %`, `Var Charges operatoires A/A %`, `Var Credits A/A %`, `Var Depots A/A %` | les mêmes, pour un indicateur fixé ; annuel = cumul au 31/12 dans le document du T4 |
| Sur un trimestre | `PNB T-1`, `Var PNB T/T %` | trimestre précédent (`DATEADD … -1, QUARTER`) : deux documents successifs, seule source possible, à lire avec les marqueurs de rupture |
| Tendance | `PNB 4T glissants` | somme des 4 derniers trimestres publiés : tendance, **jamais un chiffre annuel** (le chiffre annuel est `PNB annuel`, le cumul au 31/12) |
| Sur plusieurs années | `TCAM PNB 2020-2025` | croissance annuelle moyenne : produit des 5 variations annuelles comparables 2021 à 2025 (`PRODUCTX`), racine cinquième, moins 1 ; chacune dans son document T4 |
| Annotations | `Evenement texte`, `Evenement montant MDT`, `Nb evenements` | événements de `evenements.csv` (don au Fonds 1818, accord salarial, retraitement BH 2024…) filtrés par banque, indicateur et date : info-bulle des courbes |
| Annotations | `Rupture PNB`, `Rupture PNB cumul` | PNB seulement aux trimestres en rupture de série (période révisée de plus de 2 % sur le cumul) : série de points à superposer à la courbe |

**Plusieurs banques à la fois** (secteur, groupe d'actionnariat) : somme des N contre somme des N-1, calculée
sur une ligne par banque (`ADDCOLUMNS ( VALUES ( Dim_Banque[code_banque] ), … )`), **seulement si toutes les
banques de la sélection ont les deux valeurs** ; pour le secteur, les 12. Le dénominateur est pris en valeur
absolue (`ABS`), comme la colonne `Variation_Pct` : une baisse d'une valeur négative reste une baisse. `PNB 4T
glissants` et `Var PNB T/T %` suivent la même règle (toutes les banques de la sélection à chaque trimestre).

**Contrôle** : vider la vue Requête DAX (**Ctrl+A**, **Suppr**), coller `dax/controle_croissances.dax`,
**Exécuter** ; trois résultats. Valeurs attendues (calculées à part depuis `donnees_publiees/`) :

Résultat 1, secteur (12 banques) :

| Mesure | Attendu |
|---|---|
| Var PNB A/A, T3 2024 (trimestre seul) | +7,14 % |
| Var PNB cumul A/A, 9 mois 2024 | +5,71 % |
| Var crédits A/A, 30/09/2024 | +2,15 % |
| Var dépôts A/A, 30/09/2024 | +9,70 % |
| Var charges opératoires A/A, 9 mois 2024 | +7,70 % |
| Var PNB T/T, T3 2024 contre T2 2024 | +0,16 % |
| PNB 4T glissants au T3 2024 (T4 2023 à T3 2024) | 6 992,476 |
| Var PNB annuel A/A 2025 | +4,34 % |
| Var crédits A/A sur l'année 2026 (au 30/09/2026) | +2,14 % |
| TCAM PNB 2020-2025 | +8,17 % par an (variations annuelles : +10,43 %, +12,11 %, +8,31 %, +5,85 %, +4,34 %) |

Résultat 2 :

| Banque | Var PNB annuel 2025 | Var PNB A/A T4 2025 | Var crédits A/A T3 2024 | Var PNB T/T T3 2024 | PNB 4T glissants T3 2024 | TCAM 2020-2025 |
|---|---|---|---|---|---|---|
| BH | −2,81 % | +7,08 % | +5,25 % | −4,08 % | 751,458 | +8,21 % |
| BIAT | +7,80 % | +2,52 % | +4,43 % | +3,58 % | 1 445,942 | +11,08 % |

Résultat 3 : texte de l'événement `BH_RETRAITEMENT_2024` (« PNB 2024 redonné à 701,188 MDT… ») ; montant
−64,744 ; rupture du PNB de BH au T4 2024 = 177,219 (PNB du trimestre) ; au T3 2024 : vide (pas de rupture) ;
11 événements en tout.

### 3.7 Rentabilité : ROE et ROA (groupe 5, spécification 7.7)

Le résultat net n'est pas dans les indicateurs trimestriels : il vient des **états financiers individuels**
(`Fait_Etats_Financiers`, 2.12c), publiés au 30/06 (semestre, revue limitée) et au 31/12 (exercice, audité).
Le ROE et le ROA sont donc **semestriels et annuels**, jamais trimestriels.

- **ROE** = résultat net annualisé / capitaux propres moyens du bilan ; **ROA** = résultat net annualisé /
  total de l'actif moyen.
- **Résultat net** : avant modifications comptables (décision du 18/10/2026), cumulé depuis le 1er janvier ;
  **annualisé** par la colonne `facteur_annualisation` de Power Query (× 2 au 30/06, × 1 au 31/12 ;
  l'annualisation ignore la saisonnalité).
- **Capitaux propres et total de l'actif** : ceux du **bilan** (résultat inclus), jamais les capitaux propres
  trimestriels (définition propre à chaque banque, fiche banque seulement) ; **moyenne** de l'ouverture de
  l'exercice (31/12/N-1, valeur retenue = colonne N-1 du document de l'exercice N, même méthode que la fin) et
  de la date. Si l'une des deux manque, la moyenne reste vide (la version de la spécification avec
  `AVERAGEX ( { ouverture, fin } )` aurait pris la seule valeur de fin) : le ROE de 2019 est vide, faute
  d'états financiers au 31/12/2018.
- **Date** : la dernière date des états financiers de la sélection (`Date fin EF`) : sur l'année 2024, le
  31/12/2024 (exercice) ; sur le T2 2025, le 30/06/2025 (semestre annualisé) ; sur l'année 2026, le 30/06/2026.
- **Plusieurs banques** : somme des résultats / somme des capitaux propres moyens, banque par banque, vide si
  une banque de la sélection manque (`ROE secteur`, `ROA secteur` : les 12).

| Dossier | Mesures |
|---|---|
| Bilan et résultat | `Date fin EF`, `Resultat net`, `Resultat net annualise`, `Cap propres EF`, `Cap propres moyens`, `Total actif`, `Total actif moyen` |
| Ratios | `ROE`, `ROA`, `ROE secteur`, `ROA secteur` |
| Intermédiaires | `EF valeur` (une date à la fois), `… brut`, `… a la date` (calcul banque par banque à une date) |

**Contrôle** : vider la vue Requête DAX (**Ctrl+A**, **Suppr**), coller `dax/controle_rentabilite.dax`,
**Exécuter** ; trois résultats. Valeurs attendues (calculées à part depuis `donnees_publiees/`) :

Résultat 1 :

| Banque | ROE 2024 | ROA 2024 | ROE S1 2025 (annualisé) | ROA S1 2025 |
|---|---|---|---|---|
| AB | 15,25 % | 2,013 % | 16,55 % | 2,163 % |
| ATB | 1,82 % | 0,128 % | 0,90 % | 0,063 % |
| BH | 5,24 % | 0,503 % | 7,94 % | 0,737 % |
| BIAT | 16,61 % | 1,492 % | 22,10 % | 1,930 % |
| BNA | 12,22 % | 1,186 % | 14,11 % | 1,340 % |
| BT | 13,89 % | 2,304 % | 12,09 % | 1,967 % |
| BTE | −63,66 % | −1,865 % | −30,71 % | −0,685 % |
| STB | 6,64 % | 0,558 % | 3,45 % | 0,296 % |
| TJARI | 21,45 % | 1,947 % | 21,90 % | 1,843 % |
| UBCI | 10,13 % | 1,112 % | 9,96 % | 1,008 % |
| UIB | 8,76 % | 1,077 % | 9,65 % | 1,172 % |
| WIB | 5,48 % | 0,593 % | 2,42 % | 0,240 % |

BTE : pertes de 2020 à 2025 et capitaux propres faibles (41,704 MDT au 30/06/2024 avant l'augmentation de
capital), d'où un ROE très négatif ; c'est la donnée publiée, pas une erreur de calcul.

Résultat 2 : ROE secteur 2024 11,85 %, ROA 1,193 % ; ROE secteur S1 2025 13,13 % ; S1 2026 12,46 % ; dernière
date des états financiers 30/06/2026 ; ROE 2019 vide.

Résultat 3 : BIAT 2024 résultat net 357,754 ; capitaux propres 2 226,391 ; capitaux propres moyens 2 154,256
((2 082,120 + 2 226,391) / 2) ; total de l'actif 24 996,225 ; UIB S1 2020 résultat net 17,912 (révisé : le
semestre publié montrait −41,182, intérêts du moratoire Covid réintégrés ensuite), ROE 5,66 % ; BNA S1 2025
résultat net 155,069 (avant modifications comptables, la version révisée 137,318 n'est pas retenue), annualisé
310,138.

### 3.8 Bourse (groupe 6, spécification 7.5)

**Une banque à la fois.** Additionner les cours de deux banques n'a pas de sens : les mesures de cours, de
performance, de volatilité et l'avertissement de liquidité sont vides sans une banque unique dans le filtre
(`HASONEVALUE ( Dim_Banque[code_banque] )`).

**Performance sur les cours ajustés.** Un cours brut baisse mécaniquement le jour d'une attribution gratuite,
d'une division du nominal ou d'un dividende. BIAT : 118,000 DT le 02/01/2019 et 111,000 DT le 31/12/2025, soit
−5,9 % en brut ; une attribution 1 pour 20 (2020), la division du nominal par 2 (2021) et une attribution 1 pour
7 (2024) ont multiplié le nombre d'actions. Les colonnes ajustées de `Fait_Cours` (2.12, facteurs de la Bourse
elle-même) corrigent ces sauts :

- `Performance prix` = dernière / première clôture **ajustée des opérations sur le capital** − 1 (performance du
  prix, hors dividendes) : BIAT 2019-2025 **+125,8 %** ;
- `Rendement total` = même calcul sur la série **ajustée de toutes les opérations, dividendes compris**
  (dividendes réinvestis) : BIAT 2019-2025 +232,8 % ;
- `Premier cours`, `Dernier cours` (et leurs dates) : clôtures publiées, non ajustées, pour l'affichage. La
  version de la spécification calculait la performance sur ces cours bruts : remplacée par les deux mesures
  ci-dessus.

Une séance sans clôture (481 cas : cours à 0 dans l'archive, journée sans cotation du 17/12/2025) est sautée par
`FIRSTNONBLANK` et `LASTNONBLANK` ; une performance reste vide si le début ou la fin manque (jamais −100 %).

**Risque et liquidité.** `Volatilite annualisee` = écart-type des rendements quotidiens (`STDEVX.S`, série rendement
total) × √252 (nombre habituel de séances par an), au moins 20 rendements. `Taux seances sans transaction` = séances
sans aucun titre échangé / séances ; au-dessus de 20 % (`Seuil titre peu liquide`), `Avertissement liquidite`
affiche « Titre peu liquide : 53 % des séances sans transaction ; volatilité et performance à lire avec
prudence » : beaucoup de rendements nuls puis des sauts, la volatilité et la performance reposent sur peu
d'échanges.

**Contrôle** : vider la vue Requête DAX (**Ctrl+A**, **Suppr**), coller `dax/controle_bourse.dax`, **Exécuter** ;
trois résultats. Valeurs attendues (calculées à part : `cours_banques.csv` et `operations_titres.csv`, mêmes
facteurs que Power Query) :

Résultat 1, année 2025 :

| Banque | Premier cours | Dernier cours | Performance prix | Rendement total | Volatilité | Séances | Sans transaction |
|---|---|---|---|---|---|---|---|
| BIAT | 93,900 | 111,000 | +18,21 % | +25,49 % | 11,32 % | 249 | 1 |
| BT | 5,170 | 6,400 | +23,79 % | +32,47 % | 14,69 % | 249 | 2 |
| UBCI | 20,540 | 33,800 | +64,56 % | +75,53 % | 26,46 % | 249 | 100 |

Résultat 2, du 02/01/2019 au 20/10/2026 (1 955 séances par banque) : UBCI 52,7 %, WIB 42,6 %, BTE 37,6 % (avec
l'avertissement « Titre peu liquide : 53 % / 43 % / 38 % … »), puis BH 8,6 %, UIB 4,7 %, ATB 4,2 %, AB 3,5 %, STB
1,5 %, BNA 0,8 %, TJARI 0,5 %, BT 0,4 %, BIAT 0,1 % (sans avertissement) ; date du dernier cours 20/10/2026.

Résultat 3 : BIAT 2019-2025 performance prix +125,76 %, rendement total +232,85 %, premier cours 118,000, dernier
cours 111,000 ; dernier cours sans banque : vide.

### 3.9 Affichage et qualité des données (groupe 7, spécification 7.8)

Ces mesures alimentent la page « Qualité des données » : elles montrent d'où viennent les chiffres et ce qui a
été corrigé, révisé ou saisi, sans rien cacher.

| Dossier | Mesures | Ce qu'elles comptent |
|---|---|---|
| Affichage | `Date derniere donnee`, `Titre rapport`, `Couleur coef` | date des dernières données (tous filtres ignorés), titre « Banques cotées — données au 30/09/2026 », couleur du coefficient (vert si la banque fait mieux que la médiane, rouge sinon, rien si l'écart est vide) |
| Documents | `Nb documents`, `Part documents sans alerte`, `Nb ecarts signales`, `Nb ecarts trim cumul`, `Nb ecarts composantes`, `Nb documents a verifier`, `Nb documents illisibles`, `Nb documents saisis` | statut de chaque document trimestriel (`Controle`) |
| Révisions | `Part cumuls revises`, `Part 31-12 provisoires`, `Nb revisions`, `Nb revisions importantes`, `Nb retraitements mineurs`, `Nb reclassements`, `Ecart revision MDT`, `Nb ruptures serie`, `Nb valeurs non disponibles` | versions non retenues (`Revisions`) et origine des valeurs affichées (`Fait_Indicateurs[Source_Cumul]`) |
| Contrôle annuel | `Nb annees conformes`, `Nb annees en attente`, `Nb ecarts annuels`, `Nb ecarts expliques`, `Nb ruptures annuelles`, `Ecart annuel MDT` | somme des 4 trimestres contre cumul annuel (`Controle_Annuel`, causes de `docs/ecarts_annuels.csv` fusionnées en 2.12f) |
| États financiers | `Nb revisions importantes EF` | révisions de plus de 2 % des états financiers |

Deux écarts avec la spécification : la part des documents « ok » s'appelle `Part documents sans alerte` (et non
« taux d'extraction ») : 27 % seulement, parce que les autres documents ont surtout des écarts **qui viennent des
banques** (révisions en cours d'année, `Nb ecarts signales` = 228), pas des erreurs de lecture ; les causes des
écarts annuels sont comptées dans `Controle_Annuel` (colonne `categorie_ecart`), la table `Ecarts_Annuels` étant
une requête intermédiaire non chargée. `Couleur coef` ne renvoie rien si l'écart est vide (en DAX, « vide ≤ 0 »
est vrai : sans ce test, une banque sans coefficient serait colorée en vert). Le paramètre de champ « Indicateur
affiché » de la spécification se crée dans Power BI Desktop avec les pages du rapport (étape 7 : **Modélisation ›
Nouveau paramètre › Champs**).

**Contrôle** : vider la vue Requête DAX (**Ctrl+A**, **Suppr**), coller `dax/controle_qualite.dax`, **Exécuter** ;
trois résultats, sans filtre (toutes les données). Valeurs attendues (calculées à part depuis
`donnees_publiees/` et `docs/ecarts_annuels.csv`) :

| Résultat | Attendu |
|---|---|
| 1 | 336 documents ; sans alerte 27,1 % (91) ; écarts signalés 228 (136 retraitements possibles + 89 écarts trimestre/cumul + 3 écarts composantes) ; 89 ; 3 ; à vérifier 2 ; illisibles 2 ; saisis 13 ; « Banques cotées — données au 30/09/2026 » |
| 2 | cumuls révisés 88,3 % (6 331 / 7 173) ; 31/12 provisoires 3,8 % (276) ; révisions de plus de 2 kDT 4 311 ; révisions importantes 813 ; retraitements mineurs 3 992 ; reclassements 99 ; ruptures de série 450 ; valeurs non disponibles : vide ; révisions importantes des états financiers 8 |
| 3 | années conformes 205 ; en attente 41 ; écarts 22 ; écarts expliqués 22 ; ruptures 20 ; somme des écarts −9,953 MDT ; couleur BT T3 2024 « #2E7D32 » (vert, coefficient sous la médiane) ; BTE « #C62828 » (rouge) |

### 3.10 Compléments : colonnes calculées, table par UNION, relation inactive, TOPN (24/10/2026)

Cinq fonctions DAX courantes, chacune là où elle sert le rapport, sans changer les mesures déjà vérifiées.

**Colonnes calculées de `Dim_Banque`** (`dax/colonnes_calculees.dax`, écrites par
`python scripts/ecrire_tmdl_segment.py colonnes`) : une colonne calculée est évaluée une fois par ligne au
chargement ; elle sert de segment, de légende ou de libellé (une mesure ne le peut pas).

| Colonne | Fonction | Calcul |
|---|---|---|
| `Liquidite_Titre` | `RELATEDTABLE` | les séances de la banque dans `Fait_Cours` (la relation `Dim_Banque` → `Fait_Cours` filtre la table liée sur la ligne de la banque) ; « peu liquide » si plus de 20 % sont sans transaction, sinon « liquide » : UBCI, WIB, BTE peu liquides |
| `Definition_Charges_Operatoires` | `LOOKUPVALUE` | la description de `Definitions_Charges` pour la banque et sa période la plus récente (`MAXX` du dernier trimestre ; Attijari a deux périodes) |
| `Definition_Capitaux_Propres` | `LOOKUPVALUE` | la description de `Definitions_Capitaux_Propres` pour la banque (une ligne par banque) |

Une seule de ces colonnes passe par `RELATEDTABLE`. `RELATEDTABLE` fait une **transition de contexte** (la ligne
devient un filtre) ; dans une table sans clé déclarée, deux colonnes de ce genre dépendraient l'une de l'autre
(erreur « dépendance circulaire »). `LOOKUPVALUE` cherche une valeur sans transition de contexte.

**Table calculée par `UNION` : `Journal_Faits_Marquants`** (`dax/Journal_Faits_Marquants.dax`) : une chronologie
unique de 41 faits datés pour la page « Qualité des données », au lieu de trois tableaux séparés. Trois
`SELECTCOLUMNS` donnent la même forme (`date`, `banque`, `indicateur`, `type_fait`, `description`,
`montant_mdt`, `fichier`) à : les 11 événements (`Evenements`) ; les 22 écarts annuels expliqués
(`Controle_Annuel`, statut « ecart », cause en description, somme des trimestres − cumul en montant) ; les 8
révisions importantes des états financiers (`Revisions_Etats_Financiers`, valeur publiée et valeur retenue en
description, écart en montant). `UNION` les met bout à bout (mêmes colonnes, même ordre, mêmes types). La table
est reliée à `Dim_Date`, `Dim_Banque` et `Dim_Indicateur` (3 relations de plus) : les segments de la page la
filtrent ; mesure `Nb faits marquants`.

**Relation inactive et `USERELATIONSHIP`.** `Banques_Actionnariat` a déjà une relation active vers `Dim_Banque`.
Une seconde relation, **inactive** (`isActive: false`), relie `Banques_Actionnariat[date_debut]` (date d'entrée en
fonction d'un nouvel actionnaire de référence) à `Dim_Date[Date]`. Inactive, elle ne filtre rien d'elle-même ;
une mesure l'active pour son seul calcul avec `CALCULATE ( …, USERELATIONSHIP ( Banques_Actionnariat[date_debut],
Dim_Date[Date] ) )` :
- `Changements actionnaire` : nombre de changements dont la date d'effet est dans la période (les premières
  périodes, sans date de début, ne comptent pas) : 3 en tout (UBCI 16/03/2021, Wifak 01/01/2022, BTE
  01/07/2024) ;
- `Changements actionnaire detail` : banque, nouvel actionnaire et date (`CONCATENATEX`).

Le modèle compte désormais **32 relations** : les 28 de 3.2, les 3 du journal et cette relation inactive.

**`TOPN`** (dossier `2. Secteur\Concentration`, vides si une banque manque) :
- `Top 3 banques PNB` : `TOPN ( 3, ALL ( Dim_Banque ), [PNB], DESC )` garde les 3 lignes de banque au plus fort
  PNB du trimestre, `CONCATENATEX` les écrit dans l'ordre : « BIAT, BNA, BH » au T3 2024 ;
- `Part 3 premieres banques PNB` : leur part du PNB des 12 banques (ratio de concentration CR3, souvent lu
  avec le HHI de 3.4) : 45,8 % au T3 2024 (21,06 + 13,97 + 10,80).

**Contrôle** : vider la vue Requête DAX (**Ctrl+A**, **Suppr**), coller `dax/controle_complements.dax`,
**Exécuter** ; trois résultats. Valeurs attendues :

| Résultat | Attendu |
|---|---|
| 1 | 12 banques ; « peu liquide » pour BTE, UBCI, WIB, « liquide » pour les 9 autres ; charges opératoires « total publié = frais de personnel + charges générales d'exploitation » pour BH, BT, BTE, STB, « … dotations aux amortissements, les trois lignes publiées » pour UIB et WIB, « total publié > frais de personnel + charges générales ; … » pour AB, ATB, BIAT, BNA, TJARI, UBCI ; capitaux propres « … y compris le résultat de la période … » pour ATB et BTE, « hors résultat de la période en cours d'année ; au 31/12, après affectation … » pour AB et BIAT, « … sans le résultat de la période en cours … » pour les 8 autres |
| 2 | Écart annuel expliqué 22 ; Événement 11 ; Révision des états financiers 8 |
| 3 | « BIAT, BNA, BH » ; 0.458 ; 3 ; 1 ; vide ; « BTE : Abou Dhabi Investment Authority (ADIA) (01/07/2024) » ; 10 faits en 2020 |

### 3.11 Fonctions DAX utilisées

Chaque fonction DAX employée dans `dax/*.dax`, ce qu'elle fait ici et où elle sert. Le test
`tests/test_guide_powerbi.py` vérifie qu'aucune fonction d'un fichier `dax/*.dax` ne manque à ce
tableau.

| Fonction | Ce qu'elle fait | Code |
|---|---|---|
| `CALENDAR` | table d'une colonne `Date`, un jour par ligne entre deux dates | `Dim_Date` |
| `DATE` | date écrite à partir de l'année, du mois et du jour | `Dim_Date` |
| `ADDCOLUMNS` | ajoute des colonnes calculées à chaque ligne d'une table | `Dim_Date` |
| `YEAR`, `MONTH`, `QUARTER` | année, mois (1 à 12), trimestre (1 à 4) d'une date | `Dim_Date` |
| `EOMONTH` | dernier jour du mois d'une date (décalé de n mois) | `Dim_Date` |
| `MOD` | reste de la division entière (mois multiple de 3 = fin de trimestre) | `Dim_Date` |
| `SWITCH` | renvoie la valeur de la première condition vraie ; avec `TRUE ()`, sert de colonne conditionnelle | `Dim_Date` |
| `TRUE` | valeur vraie | `Dim_Date` |
| `CALCULATE` | calcule une expression dans un filtre modifié (ici : un code d'indicateur, un trimestre, une date) | `mesures` |
| `SUM` | somme d'une colonne dans le filtre courant | `mesures` |
| `DISTINCTCOUNT` | nombre de valeurs distinctes d'une colonne (ici : dates d'arrêté de la sélection) | `mesures` |
| `IF` | renvoie une valeur si la condition est vraie, sinon vide (pas de troisième argument : jamais zéro) | `mesures` |
| `ISBLANK`, `NOT` | vrai si la valeur est vide ; négation | `mesures` |
| `LASTNONBLANK` | dernière valeur d'une colonne (ici : dernier jour) pour laquelle une expression n'est pas vide | `mesures` |
| `VAR` … `RETURN` | mots-clés : valeurs intermédiaires nommées, calculées une fois, puis résultat | `mesures` |
| `SUMMARIZECOLUMNS` | requête : une ligne par valeur des colonnes de regroupement, avec les mesures demandées | `controle_bases` |
| `TREATAS` | applique une liste de valeurs comme filtre sur une colonne (ici : « 2024T3 », 2024) | `controle_bases` |
| `ROW` | table d'une ligne aux colonnes nommées (table `Mesures`, résultats d'une ligne des contrôles) | `mesures`, `controle_bases`, `controle_secteur` |
| `COUNTROWS` | nombre de lignes d'une table (banques du modèle, banques présentes) | `Dim_Date`, `mesures` |
| `ALL` | toute la table, sans aucun filtre (les 12 banques, quel que soit le filtre du visuel) | `mesures` |
| `FILTER` | lignes d'une table qui remplissent une condition | `Dim_Date`, `mesures` |
| `REMOVEFILTERS` | dans `CALCULATE`, retire les filtres d'une table (banque, date) | `mesures` |
| `MAX`, `MAXX` | plus grande valeur d'une colonne ; d'une expression sur chaque ligne d'une table | `Dim_Date`, `mesures` |
| `HASONEVALUE` | vrai si le filtre ne laisse qu'une valeur (une banque, un indicateur) | `mesures` |
| `SELECTEDVALUE` | la valeur d'une colonne si le filtre n'en laisse qu'une, sinon vide | `mesures` |
| `DIVIDE` | division qui renvoie vide (et non une erreur) si le dénominateur est vide ou nul | `mesures` |
| `SUMX` | somme d'une expression calculée sur chaque ligne d'une table (carrés des parts de marché) | `mesures` |
| `RANKX` | rang d'une valeur parmi celles d'une table ; `DESC` : du plus grand au plus petit, `ASC` : du plus petit au plus grand, `DENSE` : pas de rang sauté après des ex aequo | `mesures` |
| `GROUPBY`, `CURRENTGROUP`, `COUNTX` | regroupe des lignes par colonne ; `COUNTX ( CURRENTGROUP (), 1 )` compte les lignes de chaque groupe | `Dim_Date` |
| `IN { … }` | vrai si la valeur est dans la liste | `Dim_Date` |
| `VALUES` | valeurs distinctes d'une colonne dans le filtre courant (les banques de la sélection) | `mesures` |
| `RELATEDTABLE` | lignes d'une table liée, filtrées par la ligne en cours (les séances d'une banque) | `colonnes_calculees` |
| `LOOKUPVALUE` | valeur d'une colonne d'une autre table, trouvée par une ou plusieurs colonnes de recherche | `colonnes_calculees` |
| `USERELATIONSHIP` | dans `CALCULATE`, active une relation inactive pour ce seul calcul | `mesures` |
| `UNION` | met bout à bout des tables de mêmes colonnes | `Journal_Faits_Marquants` |
| `SELECTCOLUMNS` | table aux colonnes choisies et renommées (forme commune avant `UNION`) | `Journal_Faits_Marquants`, `controle_complements` |
| `TOPN` | les n premières lignes d'une table selon une expression (3 banques au plus fort PNB) | `mesures` |
| `MEDIANX` | médiane d'une expression calculée sur chaque ligne d'une table (coefficient des 12 banques) | `mesures` |
| `ABS` | valeur absolue (dénominateur des variations) | `mesures` |
| `DATEADD` | décale les dates du filtre (ici : d'un trimestre en arrière) ; utilisé seulement pour la variation d'un trimestre sur l'autre | `mesures` |
| `EDATE` | même jour n mois plus tôt ou plus tard (12 mois avant la fin de la période glissante) | `mesures` |
| `CALCULATETABLE` | comme `CALCULATE`, pour une table : calcule la table dans un filtre modifié | `mesures` |
| `GENERATESERIES` | table d'une colonne `Value` de nombres consécutifs (années 2021 à 2025) | `mesures` |
| `PRODUCTX` | produit d'une expression sur chaque ligne d'une table (enchaînement des variations annuelles) | `mesures` |
| `CONCATENATEX` | met bout à bout les textes d'une table, avec un séparateur | `mesures` |
| `UNICHAR` | caractère d'après son code (10 = retour à la ligne) | `mesures` |
| `FIRSTNONBLANK` | première valeur d'une colonne (ici : premier jour) pour laquelle une expression n'est pas vide | `mesures` |
| `MIN` | plus petite valeur d'une colonne (date du premier cours) | `mesures` |
| `STDEVX.S` | écart-type (échantillon) d'une expression sur chaque ligne d'une table (rendements quotidiens) | `mesures` |
| `SQRT` | racine carrée (√252 pour annualiser une volatilité quotidienne) | `mesures` |
| `FORMAT` | nombre ou date mis en texte selon un format (« 53 % » dans l'avertissement, « 30/09/2026 » dans le titre) | `mesures` |
| `LEFT` | premiers caractères d'un texte (« revisee » au début de la source d'une valeur) | `mesures` |

## 4. Pages du rapport : visuels, champs et mesures

Les 9 pages de la spécification (section 9) se construisent une à une dans Power BI Desktop ; chaque page
sera décrite ici (visuels, champs, mesures, filtres) avant d'être construite.

### 4.0 Méthode de construction des pages

Chaque page suit les mêmes étapes :

1. **Plan** : la page est décrite ici (visuels, position, champs et leur dossier dans la table `Mesures`, réglages,
   valeurs attendues calculées à part depuis `donnees_publiees/`).
2. **Création des visuels dans Power BI Desktop**, champs seulement (type de visuel et champs dans les zones), sans
   s'occuper du format : Power BI écrit alors des fichiers corrects.
3. **Réglages dans les fichiers du rapport** (format PBIR : un fichier `visual.json` par visuel, projet fermé) par
   `python scripts/ecrire_pbir_visuels.py <page>` : position et taille, noms affichés, titres, axes, étiquettes,
   interactions, filtres. Relancer le script ne change rien ; l'état d'avant est gardé dans l'historique.
4. **Vérification** dans Power BI Desktop (actualisation, capture), contre les valeurs attendues.

Réglages des fichiers du rapport utilisés (noms relevés dans les fichiers écrits par Power BI) :

| Réglage | Propriété du fichier `visual.json` |
|---|---|
| Nom affiché d'un champ | `displayName` du champ (`projections`) |
| Titre du visuel ; sous-titre automatique masqué | `visualContainerObjects.title` (`show`, `text`) ; `visualContainerObjects.subTitle` (`show` faux) |
| Étiquettes de données | `objects.labels.show` |
| Axe des abscisses continu ou catégoriel | `objects.categoryAxis.axisType` : « Scalar » (continu) ou « Categorical » |
| Bornes de l'axe des valeurs | `objects.valueAxis.start`, `end` |
| Carte : étiquette de référence et son titre | `objects.referenceLabel.value` (mesure) ; `objects.referenceLabelTitle` (`titleContentType` « custom », `titleText`) |
| Segment : sélection unique | `objects.selection.strictSingleSelect` |
| Filtre d'un visuel sur une colonne | `filterConfig.filters` (filtre catégoriel, condition `In`) |
| Interaction entre deux visuels | `visualInteractions` de `page.json` (`source`, `target`, `type` « NoFilter » = aucun effet) |

Trois constats faits en construisant la page 1, valables pour les suivantes :

- la nouvelle carte abrège les grands nombres en milliers (« 1,9K ») et cette version de Power BI ne montre pas le
  réglage des unités : les cartes des montants affichent des mesures de texte déjà mises en forme (`… texte`) ;
- un filtre par **mesure** posé sur un segment se calcule avec la sélection du segment lui-même et ne laisse que la
  valeur choisie : un segment se filtre par une **colonne** (`Dim_Date[Trimestre_Publie]`) ;
- un graphique dans le temps doit ignorer le segment du trimestre (interaction « Aucun »), sinon il n'affiche
  qu'un point.

### 4.1 Présentation commune à toutes les pages

**Thème** (`powerbi/theme/secteur_bancaire.json`, produit par `python scripts/generer_theme.py`) : couleurs
d'un rapport bancaire, bleu marine `#0B2545` et `#134074`, or `#C9A227` en filet, fond de page gris très
clair `#F4F6FA`, visuels sur cartes blanches à coins arrondis et contour léger, titres en Segoe UI Semibold
bleu marine, en-têtes de tableaux bleus ; vert `#2E7D32` et rouge `#C62828` pour bon et mauvais (mêmes
couleurs que la mesure `Couleur coef`) ; 12 couleurs de séries assez foncées pour un texte blanc. Import :
**Affichage › Thèmes › Parcourir les thèmes**, choisir le fichier.

**Fonds de page** (1 920 × 1 080, format 16:9, même script) : `fond_page.png` (bandeau bleu marine en haut
avec filet or, motif discret d'une façade à colonnes et d'une courbe montante, pied de page « Ahmed Ben Arfa ·
Analyse du secteur bancaire tunisien » et sources) ; `fond_page_filtres.png` (même fond avec une bande blanche
sous le titre, pour les segments : banques, années). Le titre de la page est une zone de texte blanche posée
sur le bandeau (le fond n'en contient pas, pour servir à toutes les pages). Pose : sélectionner la page (clic
dans le vide), **Format de la page › Arrière-plan du canevas › Image › Parcourir**, ajustement **Ajuster**,
transparence **0 %** ; **Arrière-plan du papier peint** à la même couleur que le fond (`#E9EEF5`).

**Segment par banque avec une icône.** Les **logos officiels** des 12 banques (`donnees_reference/logos/`,
décision du 24/10/2026, sources et mention de propriété dans le `LISEZMOI.md` du dossier) sont dans la colonne
`icone` de `Dim_Banque` (2.8), catégorie « URL d'image ». Ils s'affichent dans un segment cliquable à images
(segment à boutons de Power BI, ou visuel « Chiclet Slicer » d'AppSource s'il faut), choisi avec la première
page. Solution de secours : pastilles au code de chaque banque (aperçu `powerbi/theme/icones_banques.png`).

**Défilement des années : Play Axis.** Le visuel personnalisé **Play Axis (Dynamic Slicer)** (AppSource :
**Visualisations › … › Obtenir d'autres visuels**, rechercher « Play Axis ») ajoute des boutons lecture,
pause, précédent et suivant qui font défiler les valeurs d'un champ (années, ou `Annee_Trimestre`) et filtrent
la page à chaque pas : utile pour les pages Vue d'ensemble, Classement et Évolution. Visuel certifié, il reste
affiché après la publication sur le web.

### 4.2 Page 1 : Vue d'ensemble (terminée le 30/10/2026)

**But** : en un coup d'œil, la taille du secteur au dernier trimestre complet (PNB, crédits, dépôts), son
efficacité (coefficient d'exploitation harmonisé) et sa concentration (part de marché de chaque banque,
indice HHI dans le temps). Chiffres du secteur seulement si les 12 banques sont présentes (3.4).

**Mise en page** (page 1 280 × 720, positions en pixels : x, y, largeur × hauteur ; **Format › Général ›
Propriétés › Taille et position**) :

| Élément | Position | Champs et mesures | Réglages |
|---|---|---|---|
| Fond | page entière | `powerbi/theme/fond_page_filtres.png` | Format de la page › Arrière-plan du canevas › Image, ajustement **Ajuster**, transparence 0 % |
| Titre | 24, 14, 600 × 44 | zone de texte « Vue d'ensemble du secteur » | Segoe UI Semibold 24, blanc, sans arrière-plan |
| Date des données | 640, 22, 360 × 32 | carte (nouvelle) : `Titre rapport` | sans arrière-plan ni contour, valeur Segoe UI 12 blanche, étiquette masquée |
| Segment du trimestre | 24, 92, 250 × 52 | segment : `Dim_Date[Choix_Trimestre]` ; filtre du visuel `Dim_Date[Trimestre_Publie]` = Vrai | style **Liste déroulante**, **sélection unique**, choisir « Dernier trimestre complet » ; en-tête « Trimestre » |
| Segment des banques | 290, 92, 966 × 52 | segment à boutons : `Dim_Banque[code_banque]`, image : `Dim_Banque[icone]` | 12 boutons sur une ligne, image seule, sélection multiple ; sans effet sur les cartes du secteur (elles ignorent le filtre de banque) |
| Carte PNB | 16, 162, 304 × 130 | `PNB secteur` | étiquette « PNB du trimestre (MDT) », 1 décimale ; étiquette de référence : `Banques presentes PNB` « banques présentes » |
| Carte coefficient | 330, 162, 304 × 130 | `Coef secteur` | étiquette « Coefficient d'exploitation harmonisé » ; référence : `Coef mediane` « médiane des banques » |
| Carte crédits | 644, 162, 304 × 130 | `Credits secteur` | étiquette « Encours de crédits (MDT) », 0 décimale ; référence : `Var Credits A/A %` « sur un an » |
| Carte dépôts | 958, 162, 306 × 130 | `Depots secteur` | étiquette « Encours de dépôts (MDT) », 0 décimale ; référence : `Var Depots A/A %` « sur un an » |
| Parts de marché | 16, 304, 620 × 380 | graphique à barres groupées : axe Y `Dim_Banque[code_banque]`, axe X `Part de marche PNB`, info-bulles `PNB`, `Rang PNB` | tri par `Part de marche PNB` décroissant, étiquettes de données « 0,0 % » ; titre « Part de marché du PNB » |
| Concentration | 646, 304, 618 × 270 | graphique en courbes : axe X `Dim_Date[Date]`, axe Y `HHI PNB`, info-bulles `Part 3 premieres banques PNB`, `Top 3 banques PNB` | axe X **continu** (années ; un point au dernier jour de chaque trimestre), axe Y de 1 000 à 1 300 ; titre « Concentration du PNB (indice HHI) » ; **Modifier les interactions** : le segment du trimestre ne filtre **pas** ce graphique (icône « Aucun ») |
| Trois premières banques | 646, 584, 618 × 100 | carte (nouvelle) : `Top 3 banques PNB` et `Part 3 premieres banques PNB` | étiquettes « Trois premières banques » et « Part du PNB du secteur » |

**Construction (30/10/2026).** Les visuels sont créés dans Power BI Desktop avec leurs champs ; les réglages
(positions, noms affichés, titres, étiquettes de données, axes, interaction) sont ensuite écrits dans les fichiers
du rapport par `python scripts/ecrire_pbir_visuels.py vue_ensemble` (format PBIR : un fichier `visual.json` par
visuel), projet fermé. Deux écarts avec le tableau :

- **Cartes du PNB, des crédits et des dépôts** : la nouvelle carte abrège les grands nombres en milliers
  (« 1,9K ») et cette version de Power BI ne montre pas le réglage des unités ; elles affichent donc les mesures
  `PNB secteur texte`, `Credits secteur texte` et `Depots secteur texte` (dossier `2. Secteur\Affichage`), qui
  renvoient le nombre déjà mis en forme (`FORMAT ( valeur, "#,0.0" )`, « 1 936,6 »), vides si le total est vide.
  Le calcul reste celui de `PNB secteur`, `Credits secteur` et `Depots secteur`. `PNB secteur` a gardé une
  décimale (`#,0.0`), réglée dans Power BI et reportée dans `dax/mesures.dax`.
- **Titres des étiquettes de référence** (« banques présentes », « médiane des banques », « sur un an ») : saisis
  une première fois dans Power BI (**Format › Objet visuel › Étiquettes de référence**), ce qui a montré leur réglage
  dans les fichiers (`referenceLabelTitle` : `titleContentType` « custom », `titleText`, même sélecteur que
  l'étiquette) ; l'outil les écrit désormais lui-même.
- **Cartes de 130 pixels de haut** (et non 110) : à 110, le libellé au-dessus de la valeur était coupé ; les
  graphiques sont descendus de 20 pixels. Le sous-titre automatique des graphiques (« Part de marché, PNB du
  trimestre (MDT) et Rang par Banque ») est masqué (`subTitle`).
- **Axe de la courbe de concentration : la date, en axe continu** (et non le libellé « 2024T3 ») : en axe
  catégoriel, les 28 trimestres ne tenaient pas dans la largeur (barre de défilement, 2026T2 et 2026T3 cachés à
  droite). Sur l'axe des dates, le HHI n'a de valeur qu'au dernier jour de chaque trimestre : un point par
  trimestre, l'axe gradué en années, la date exacte dans l'info-bulle. Dans le fichier du visuel, l'axe continu
  s'écrit `axisType` = « Scalar » (la valeur « Continuous » est ignorée : premier essai sans effet). Les trimestres sans indicateurs (2019T1 à
  2019T3, avant le début des données ; 2026T4, pas encore publié) n'ont pas de point.

**Pourquoi ces choix.** Le segment du trimestre est réglé sur « Dernier trimestre complet » et non sur le
dernier trimestre : la page reste juste quand de nouvelles publications arrivent (3.1). Le graphique du HHI
montre toute la période : on retire le filtre du segment du trimestre sur ce seul visuel (interaction
« Aucun »), sinon il n'afficherait qu'un point. Le segment des banques filtre les barres (une banque choisie
reste seule avec sa part) ; les cartes du secteur ne bougent pas, puisque leurs mesures ignorent le filtre de
banque.

**Valeurs attendues au T3 2026** (calculées à part depuis `donnees_publiees/`) : PNB du secteur 1 936,6 MDT
(12 banques présentes) ; coefficient du secteur 44,7 % ; crédits 86 880 MDT ; dépôts 112 896 MDT ; parts du
PNB : BIAT 22,4 %, BNA 15,4 %, STB 10,0 %, Attijari 9,1 %, BH 8,5 %, AB 7,8 %, UIB 7,5 %, BT 6,8 %, ATB 5,0 %,
UBCI 4,9 %, Wifak 1,7 %, BTE 1,0 % ; trois premières banques « BIAT, BNA, STB », 47,8 % du PNB ; HHI 1 209
(entre 1 106 au T2 2021 et 1 209 au T3 2026 sur les 28 trimestres : marché peu concentré, en légère hausse).

**Vérifiée le 30/10/2026** dans Power BI Desktop : toutes ces valeurs, médiane des coefficients 47,0 %, crédits
+2,1 % et dépôts +8,2 % sur un an ; segment limité aux trimestres publiés (« Dernier trimestre complet », 2019T4 à
2026T2) ; courbe sur toute la période sans défilement.

### 4.3 Page 2 : Classement (terminée le 30/10/2026)

**But** : classer les 12 banques sur un trimestre (taille, efficacité, croissance) et voir, d'un trimestre à
l'autre, comment le classement bouge. Le tableau montre, pour chaque banque, son PNB, sa part de marché et son rang,
son coefficient d'exploitation harmonisé et son rang (1 = la plus efficace), l'écart à la médiane des 12 banques
(vert : plus efficace que la médiane, rouge : moins) et la croissance du PNB sur un an. Le nuage de points croise
croissance et efficacité : en bas à droite, les banques qui grandissent vite à faible coût.

**Choix du trimestre et animation** (décision du 30/10/2026, revue le même jour). Premier essai : le visuel
**Play Axis (Dynamic Slicer)** à la place du segment du trimestre. Abandonné après le premier affichage : ce visuel
démarre **sans trimestre choisi** (toutes les mesures du trimestre vides, garde-fou de 3.3), il **efface sa
sélection à la fin de la lecture** (la page redevient vide) et, à 52 pixels de haut, le titre que le thème donne à
chaque visuel cachait ses boutons (code public du visuel, `mprozil/PlayAxis` sur GitHub : `resetAnimation`,
`stopAnimation`). Solution retenue : le **segment du trimestre** de la page 1 (« Dernier trimestre complet » : la page
s'ouvre sur le dernier trimestre complet) pour le tableau et les cartes, et l'**axe de lecture intégré au nuage de
points** de Power BI (zone « Axe de lecture », `Dim_Date[Annee_Trimestre]`, trimestres publiés seulement) : le
bouton ▶ du nuage fait défiler les 28 trimestres (en 2020, le recul du PNB et la hausse des coefficients ; au T2
2020, le PNB de l'UIB recule de 78,7 % sur un an, effet du moratoire Covid). Le segment ne filtre pas le nuage
(interaction « Aucun »), sinon l'animation n'aurait qu'une image. La carte « Trimestre affiché » (mesure
`Trimestre affiche`, `SELECTEDVALUE ( Dim_Date[Annee_Trimestre], "plusieurs trimestres" )`, dossier
`2. Secteur\Affichage`) dit quel trimestre le tableau montre.

**Création de la page** : faite dans les fichiers par `python scripts/ecrire_pbir_visuels.py nouvelle_page
"Classement" "Classement des banques"` (même fond que la page 1, titre et segment des banques à logos copiés).
Visuels créés dans Power BI Desktop avec leurs champs (30/10/2026), puis réglés par `python scripts/ecrire_pbir_visuels.py
classement` : positions, noms affichés, titres, tri du tableau par `Rang PNB`, couleur `Couleur coef` recopiée sur la
colonne de l'écart (forme relevée sur la mise en forme saisie dans Power BI pour le coefficient), barre de lecture
limitée aux trimestres publiés, étiquettes des banques sur le nuage, titre de l'étiquette de référence ; puis Play
Axis retiré, segment du trimestre copié de la page 1 et axe de lecture ajouté au nuage (fonctions `supprimer_visuel`,
`copier_visuel`, `ajouter_colonne_role`). Première capture (30/10/2026) : valeurs justes ; logos à leur taille
d'origine (une ligne de 120 pixels par banque, 4 banques visibles), libellé de la carte de la médiane coupé à 100
pixels, titre du nuage sur deux lignes : corrigés (logos à 24 pixels, cartes à 130, en-têtes et titre raccourcis). Une
extraction (*drillthrough*) sur `code_banque` posée par mégarde sur la page, avec le bouton « Retour » ajouté
automatiquement, a été retirée (`retirer_extraction`) : l'extraction est réservée à la fiche banque (page 7). La
ligne médiane du nuage n'est pas encore ajoutée.

**Mise en page** (positions : x, y, largeur × hauteur) :

| Élément | Position | Champs et mesures (dossier de `Mesures`) | Réglages |
|---|---|---|---|
| Fond, titre, segment des banques | comme la page 1 | copiés de la page 1 | titre « Classement des banques » |
| Segment du trimestre | 24, 92, 250 × 52 | copie du segment de la page 1 : `Dim_Date[Choix_Trimestre]` | « Dernier trimestre complet », sélection unique, filtre `Trimestre_Publie` = Vrai ; ne filtre pas le nuage |
| Trimestre affiché | 16, 162, 365 × 130 | carte (nouvelle) : `Trimestre affiche` (`2. Secteur\Affichage`) | libellé « Trimestre affiché » |
| Médiane des coefficients | 391, 162, 365 × 130 | carte (nouvelle) : `Coef mediane` (`3. Ratios\Comparaison au secteur`) ; étiquette de référence `Coef secteur` | libellé « Médiane des coefficients » ; référence « coefficient du secteur » |
| Classement | 16, 302, 740 × 382 | tableau : `Dim_Banque[icone]`, `Dim_Banque[code_banque]`, `PNB` (`1. Bases\Flux du trimestre`), `Part de marche PNB` (`2. Secteur\Parts de marché`), `Rang PNB` (`2. Secteur\Rangs`), `Coef exploitation harmonise` (`3. Ratios\Coefficient d'exploitation`), `Rang coef`, `Ecart coef / mediane` (`3. Ratios\Comparaison au secteur`), `Var PNB A/A %` (`4. Croissances\Sur un an`) | logos de 24 pixels de haut (`grid.imageHeight`) ; en-têtes courts (« Écart médiane », « PNB A/A ») ; tri par `Rang PNB` croissant ; couleur de police du coefficient et de l'écart = valeur du champ `Couleur coef` ; titre « Classement des banques au trimestre » |
| Croissance et efficacité | 766, 162, 498 × 522 | nuage de points : axe X `Var PNB A/A %`, axe Y `Coef exploitation harmonise`, valeurs `Dim_Banque[code_banque]`, taille `PNB`, axe de lecture `Dim_Date[Annee_Trimestre]`, info-bulles `Rang PNB`, `Rang coef` | étiquettes de catégorie (code de la banque) ; filtre `Trimestre_Publie` = Vrai ; titre « Croissance du PNB et coefficient (▶ : les trimestres) » |

**Pourquoi ces choix.** Le classement utilise le coefficient **harmonisé** (frais de personnel + charges générales,
3.5), seul comparable d'une banque à l'autre. La croissance est celle du **trimestre seul sur un an**, lue dans le
même document que le trimestre (`Variations_Comparables`, 3.6) : c'est la même période que le PNB et le coefficient
du tableau. La couleur vient d'une mesure (`Couleur coef`) plutôt que de règles saisies dans le visuel : la règle
(écart à la médiane ≤ 0 → vert) est écrite une fois, dans le modèle. La taille des points suit le PNB : le poids de
chaque banque dans le secteur reste visible. Le segment des banques filtre le tableau et le nuage ; les rangs et la
médiane restent calculés sur les 12 banques.

**Valeurs attendues au T3 2026** (calculées à part depuis `donnees_publiees/`) :

| Rang PNB | Banque | PNB (MDT) | Part | Coefficient | Rang coef | Écart à la médiane | PNB sur un an | Couleur |
|---|---|---|---|---|---|---|---|---|
| 1 | BIAT | 433,328 | 22,38 % | 39,7 % | 3 | −7,4 | +6,5 % | vert |
| 2 | BNA | 298,334 | 15,41 % | 34,9 % | 2 | −12,1 | +9,8 % | vert |
| 3 | STB | 193,988 | 10,02 % | 46,3 % | 5 | −0,8 | +12,6 % | vert |
| 4 | Attijari | 176,968 | 9,14 % | 52,2 % | 8 | +5,2 | +0,5 % | rouge |
| 5 | BH | 165,030 | 8,52 % | 47,6 % | 7 | +0,6 | −4,9 % | rouge |
| 6 | AB | 150,021 | 7,75 % | 44,7 % | 4 | −2,3 | +11,0 % | vert |
| 7 | UIB | 145,463 | 7,51 % | 46,5 % | 6 | −0,6 | +11,9 % | vert |
| 8 | BT | 131,414 | 6,79 % | 30,1 % | 1 | −16,9 | +7,5 % | vert |
| 9 | ATB | 96,564 | 4,99 % | 62,2 % | 9 | +15,2 | −11,4 % | rouge |
| 10 | UBCI | 94,251 | 4,87 % | 62,6 % | 10 | +15,6 | +11,6 % | rouge |
| 11 | Wifak | 32,113 | 1,66 % | 63,3 % | 11 | +16,3 | +26,5 % | rouge |
| 12 | BTE | 19,089 | 0,99 % | 82,4 % | 12 | +35,4 | +9,5 % | rouge |

Écart à la médiane en points de pourcentage. Ligne de total du tableau : PNB 1 936,564, part 100 %, coefficient
44,7 % (= coefficient du secteur), PNB +6,1 % sur un an, rangs et écart vides. Médiane des coefficients 47,0 %.
Contrôle au **T2 2020** (segment ou axe de lecture du nuage) : BIAT 1re (19,68 %), BT coefficient le plus bas (23,1 %), Wifak 12e,
médiane 45,9 %, secteur 45,7 %, UIB −78,7 % et Wifak +79,3 % sur un an, PNB du secteur −12,8 %.

**Vérifiée le 30/10/2026** dans Power BI Desktop : toutes les valeurs du T3 2026 (rangs, coefficients, couleurs,
croissances, ligne de total à +6,1 %) ; l'axe de lecture du nuage fait défiler les trimestres de 2019T4 à 2026T3 et
s'arrête sur le dernier. Le tableau affiche 8 banques sans défilement (les 4 dernières par la barre verticale).

### 4.4 Page 3 : Évolution 2020–2026 (en construction)

**But** : suivre chaque banque trimestre par trimestre, de 2019T4 à 2026T3, sur l'indicateur choisi, avec la
période Covid repérée et l'explication des sauts de série (révisions de plus de 2 %, événements datés).

**Sélecteur d'indicateur : paramètre de champ « Indicateur affiché »** (créé dans Power BI Desktop :
**Modélisation › Nouveau paramètre › Champs**). Un paramètre de champ est une petite table calculée dont chaque
ligne pointe vers une mesure (`NAMEOF`) ; posé sur l'axe d'un graphique, il remplace la mesure affichée par celle
choisie dans son segment, sans dupliquer le graphique. Cinq mesures, dans cet ordre : `PNB`, `Coef exploitation
harmonise`, `Credits / Depots`, `Part de marche PNB`, `Var PNB A/A %`. Le segment du paramètre prend la place du
segment du trimestre : sur une page qui montre toute la période, choisir un trimestre n'a pas de sens.

**Période Covid** : deux lignes verticales sur l'axe des dates, au 01/03/2020 (début) et au 01/01/2022 (fin), les
bornes de `Dim_Date[Periode]` (3.1). Une bande grise derrière les courbes n'est pas possible ici : avec une courbe
par banque (légende), le graphique n'accepte qu'une mesure, et le graphique combiné (courbes et colonnes) ne sait
pas répartir ses courbes par banque.

**Ruptures de série et événements** : dans l'info-bulle de chaque point, `Ruptures texte` (mesure ajoutée le
30/10/2026, dossier `4. Croissances\Annotations`) liste les révisions de plus de 2 % du point pour le PNB, les frais
de personnel, les charges générales, les crédits et les dépôts (`Fait_Indicateurs[Detail_Rupture_Cumul]`,
`CONCATENATEX`), et `Evenement texte` les événements datés de la banque (`Evenements` : don au Fonds 1818,
moratoire de l'UIB, accord salarial APTBEF–FGBEF, retraitement BH 2024). Le même contenu est lisible sans survol
dans le tableau des événements, à droite, filtré par la banque et le point cliqués. La superposition de marqueurs
`Rupture PNB` sur les courbes, prévue au départ, se heurte à la même limite que la bande (une seule mesure avec une
légende) : l'info-bulle la remplace.

**Création de la page** : `python scripts/ecrire_pbir_visuels.py nouvelle_page "Évolution" "Évolution 2020–2026"`
(fond, titre et segment des banques copiés de la page 1). Visuels et paramètre de champ créés dans Power BI Desktop
(30/10/2026), puis réglés par `python scripts/ecrire_pbir_visuels.py evolution` : positions, titres, noms affichés, axe
continu, lignes de la période Covid (`xAxisReferenceLine`), filtre des trimestres publiés, sélecteur en liste
déroulante à sélection unique sur « PNB », tableau trié par date avec retour à la ligne, interaction tableau →
courbes « Aucun ». Corrections du modèle au même moment : nom du paramètre sans le point final saisi par mégarde
(« Indicateur affiché. »), libellés en français (« Coefficient d'exploitation », « Crédits / dépôts », « Part du
PNB », « PNB sur un an ») ; option **Date/heure automatique** désactivée pour ce fichier : Power BI venait de créer
quatre tables de dates cachées (`LocalDateTable_…`) et trois relations pour les dates de l'actionnariat, inutiles avec
`Dim_Date` et coûteuses en mémoire (**Fichier › Options › Fichier actif › Chargement des données**).

**Mise en page** (positions : x, y, largeur × hauteur) :

| Élément | Position | Champs et mesures (dossier de `Mesures`) | Réglages |
|---|---|---|---|
| Fond, titre, segment des banques | comme la page 1 | copiés de la page 1 | titre « Évolution 2020–2026 » |
| Indicateur affiché | 24, 92, 250 × 52 | segment du paramètre de champ `Indicateur affiché` | liste déroulante, sélection unique, « PNB » par défaut |
| Évolution par banque | 16, 162, 860 × 522 | graphique en courbes : axe X `Dim_Date[Date]`, axe Y `Indicateur affiché`, légende `Dim_Banque[code_banque]`, info-bulles `Evenement texte`, `Ruptures texte` (`4. Croissances\Annotations`) | axe X continu ; lignes verticales Covid au 01/03/2020 et au 01/01/2022 ; filtre `Trimestre_Publie` = Vrai ; titre « Évolution par banque » |
| Événements | 886, 162, 378 × 522 | tableau : `Evenements[date]`, `Evenements[banque]`, `Evenements[description]`, `Evenements[montant_mdt]` | tri par date ; titre « Événements qui expliquent un saut » ; un clic dans le tableau ne filtre pas les courbes (interaction « Aucun ») |

**Pourquoi ces choix.** L'axe des dates est continu, comme pour le HHI de la page 1 : les 28 trimestres tiennent sans
défilement et chaque mesure n'a de valeur qu'au dernier jour d'un trimestre (un point par trimestre). Le segment des
banques sert à alléger le graphique (12 courbes ensemble se lisent mal) : choisir deux ou trois banques. La
croissance affichée vient de `Variations_Comparables` (3.6) : la valeur N-1 est lue dans le même document que la
valeur N, la courbe des variations ne mélange donc jamais deux bases différentes.

**Valeurs attendues** (calculées à part depuis `donnees_publiees/`) :

| Banque | Trimestre | PNB | Coefficient | Crédits / dépôts | Part du PNB | PNB sur un an |
|---|---|---|---|---|---|---|
| BIAT | 2019T4 | 264,279 | 35,9 % | 79,9 % | 18,91 % | +10,9 % |
| BIAT | 2020T2 | 224,319 | 41,8 % | 84,6 % | 19,68 % | −1,3 % |
| BIAT | 2026T3 | 433,328 | 39,7 % | 56,7 % | 22,38 % | +6,5 % |
| UIB | 2020T2 | 87,556 | 52,6 % | 112,3 % | 7,68 % | −78,7 % |
| BH | 2024T4 | 177,219 | 32,9 % | 117,4 % | 9,90 % | +7,6 % |
| BH | 2026T3 | 165,030 | 47,6 % | 98,5 % | 8,52 % | −4,9 % |

BH 2019T4 n'a pas de variation sur un an (document publié en image, colonne N-1 non lue). Info-bulle de BH au
2024T4 : « PNB : 2024T4 révisé de -8.5 % sur le cumul (765.932 publié, 701.188 dans le document 2025T4) » et
l'événement du retraitement BH 2024. 93 points (banque × trimestre) ont au moins une rupture sur ces cinq
indicateurs. Le PNB de l'UIB au T2 2020 (87,556, valeur révisée) et sa variation (−78,7 %, valeurs du document du
T2 2020, avant la réintégration des intérêts du moratoire) ne reposent pas sur la même base : c'est ce que signale
l'événement « moratoire Covid de l'UIB ».
