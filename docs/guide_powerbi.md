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
| 9 | `Operations_Titres` | non | `operations_titres.csv` sur GitHub (source URL) | facteurs d'ajustement des cours |
| 10 | `Evenements` | oui | `evenements.csv` sur GitHub (source URL) | événements qui expliquent une rupture de série |
| 11 | `Fait_Cours` | oui | `cours_banques.csv` + fusion avec `Operations_Titres` | cours quotidiens, cours ajustés, rendement, séances sans transaction |
| 12 | `Variations_Comparables` | oui | `variations_comparables.csv` + fusion avec `Dim_Indicateur` | valeur N et N-1 du même document, variation sur un an |
| 13 | `Fait_Etats_Financiers` | oui | `etats_financiers_versions.csv` | résultat net, total de l'actif, capitaux propres du bilan (ROE, ROA) |

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

**Pourquoi la version révisée** : le capital et le total de l'actif d'ouverture (31/12/N-1) viennent
alors du document de l'exercice N, dans la même méthode que la valeur de fin de période. Les deux
dates sans document lisible (BH 31/12/2019, STB 30/06/2023) sont reprises de la colonne N-1 du
document suivant (statut « repris du document suivant »).

### 2.13 Fonctions et mots-clés M utilisés

Chaque fonction du langage M (Power Query) employée dans les requêtes, ce qu'elle fait ici et où elle
sert. Le test `tests/test_guide_powerbi.py` vérifie qu'aucune fonction d'un fichier `powerquery/*.pq`
ne manque à ce tableau.

**Lire les sources**

| Fonction | Ce qu'elle fait | Requêtes |
|---|---|---|
| `Folder.Files` | liste les fichiers d'un dossier (nom, contenu binaire, extension, dossier, dates) : connecteur Dossier | `Fichiers_Donnees` |
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
| `Text.Contains` | le texte contient-il ce mot (« sans transaction ») ? | `Fait_Cours` |
| `Text.StartsWith` | le texte commence-t-il par ce préfixe (« revisee_31-12 », « exclue ») ? | `Revisions` |
| `Text.Proper` | met une majuscule au début du mot (« trim » → « Trim ») | `Fait_Indicateurs` |
| `Number.Abs` | valeur absolue (écart en % rapporté à la valeur absolue) | `Revisions` |
| `List.Contains` | la liste contient-elle cette valeur (les quatre catégories d'actionnariat) ? | `Banques_Actionnariat` |
| `List.Product` | produit des nombres d'une liste (facteurs d'ajustement cumulés) | `Operations_Titres` |
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
| `Table.Group` | **regroupement** : une table par banque, traitée à part (rendement séance par séance) | `Fait_Cours` |
| `Table.Buffer` | garde une table en mémoire : elle n'est pas relue (ni retéléchargée) à chaque utilisation | `Operations_Titres`, `Fait_Cours` |
| `List.Buffer` | même chose pour une liste (clôtures connues d'une banque) | `Fait_Cours` |

**Mots-clés du langage**

| Mot-clé | Ce qu'il fait |
|---|---|
| `let … in` | suite d'étapes nommées ; la requête renvoie l'étape écrite après `in` (chaque nom est une ligne de « Étapes appliquées ») |
| `each [colonne]` | fonction appliquée à chaque ligne ; `[colonne]` est la valeur de la ligne en cours |
| `(op) => …` | fonction avec un paramètre nommé, quand deux lignes sont comparées (une opération et les autres, une séance et les opérations) |
| `if … then … else` | condition : c'est le code d'une colonne conditionnelle |
| `error "…"` | provoque une erreur visible à l'actualisation (catégorie d'actionnariat inconnue) |
| `#table(type table […], {…})` | table écrite dans la requête (3 codes des états financiers) |
| `meta [IsParameterQuery = true …]` | fait d'une valeur un paramètre (`CheminDonnees`, `AdresseDepot`) |
| `type number`, `type text`, `type date`, `Int64.Type`, `type logical` | types des colonnes : nombre décimal, texte, date, entier, vrai ou faux |
| `null` | valeur absente ; un calcul avec `null` donne `null` (jamais zéro) |

## 3. Mesures DAX

À écrire après les requêtes (`dax/mesures.dax`).

## 4. Pages du rapport : visuels, champs et mesures

À préparer quand les mesures seront écrites (liste des pages : spécification, section 9).
