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

Ne sont pas versionnés (`.gitignore`) : `.pbi/cache.abf` (données importées), `.pbi/localSettings.json`
(réglages et signature de sécurité propres au poste) et l'ancien `SecteurBancaireTunisien.pbix`.

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

Ajout manuel d'une requête (sans passer par les fichiers TMDL) : **Accueil › Transformer les données**,
puis **Nouvelle source › Requête vide**, **Éditeur avancé**, coller le contenu du fichier `.pq`, renommer
la requête exactement comme le fichier (sans `.pq`). Requête intermédiaire : clic droit › décocher
**Activer le chargement**. Puis **Fermer et appliquer** et enregistrer (Ctrl+S).

## 2. Requêtes Power Query

Ordre de création : chaque requête n'utilise que des requêtes déjà créées.

| # | Requête | Chargée | Source | Rôle |
|---|---|---|---|---|
| 1 | `CheminDonnees` | paramètre | — | dossier du projet sur ce poste |
| 2 | `Fichiers_Donnees` | non | connecteur Dossier | liste des CSV de `donnees_publiees\` |
| 3 | `Versions` | non | `indicateurs_versions.csv` | toutes les versions des indicateurs, typées |
| 4 | `Dim_Indicateur` | oui | `dim_indicateur.csv` + 3 lignes ajoutées | libellé, catégorie, nature (flux / stock), ordre |
| 5 | `Fait_Indicateurs` | oui | `Versions` + fusion avec `Dim_Indicateur` | valeur retenue, trimestre seul et cumul côte à côte |
| 6 | `Revisions` | oui | `Versions` | versions non retenues et écart à la valeur retenue (page qualité) |

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

## 3. Mesures DAX

À écrire après les requêtes (`dax/mesures.dax`).

## 4. Pages du rapport : visuels, champs et mesures

À préparer quand les mesures seront écrites (liste des pages : spécification, section 9).
