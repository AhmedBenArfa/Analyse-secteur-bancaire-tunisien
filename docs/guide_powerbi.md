<!-- Auteur : Ahmed Ben Arfa -->
# Guide Power BI — Analyse du secteur bancaire tunisien

Ce guide explique, étape par étape, chaque requête Power Query et chaque mesure DAX du rapport :
ce qu'elle calcule et pourquoi. Il se lit à côté du projet Power BI (`powerbi/`) et des fichiers
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
   tables, relations, mesures, au format texte TMDL dans `definition\`). Le fichier `.gitignore` qu'il
   ajoute exclut le cache des données (`cache.abf`) et les réglages locaux : seules les définitions
   sont versionnées, jamais les données.

**Où sont les requêtes dans le projet.** Le modèle est stocké en texte (TMDL) dans
`powerbi/SecteurBancaireTunisien.SemanticModel/definition/` :

| Fichier | Contenu |
|---|---|
| `expressions.tmdl` | le paramètre `CheminDonnees` et les requêtes intermédiaires non chargées (`Fichiers_Donnees`, `Versions`) |
| `tables/<Table>.tmdl` | une table chargée : ses colonnes (type, synthèse) et sa requête (partition `m`) |
| `model.tmdl` | options du modèle, ordre des requêtes dans Power Query (`PBI_QueryOrder`), liste des tables |

Le code M de chaque requête est le même que celui du fichier `powerquery/<Requête>.pq`, gardé comme
copie lisible : une modification faite dans Power Query doit être reportée dans le `.pq` (et
inversement). Les requêtes sont écrites directement dans ces fichiers, Power BI Desktop fermé ;
à la réouverture, Power BI les lit et les affiche dans Power Query.

Ne sont pas versionnés (`.gitignore`) : `.pbi/cache.abf` (données importées), `.pbi/localSettings.json`
(réglages et signature de sécurité propres au poste) et l'ancien `SecteurBancaireTunisien.pbix`.

**Vérifier après une réouverture.** Ouvrir `SecteurBancaireTunisien.pbip`, **Accueil › Transformer les
données** : les requêtes apparaissent dans l'ordre de la section 2, les intermédiaires en italique
(chargement désactivé). Revenir au rapport et **Actualiser**. Contrôles sur `Fait_Indicateurs` :
7 137 lignes ; AB 2026T3, PNB : `Valeur_Trim` = 150,021 et `Valeur_Cumul` = 512,448 (valeurs relevées
sur l'image du document, `tests/valeurs_reference.csv`).

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
| 4 | `Fait_Indicateurs` | oui | `Versions` | valeur retenue, trimestre seul et cumul côte à côte |

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

### 2.4 `Fait_Indicateurs` (chargée)

Table de faits des indicateurs trimestriels : une ligne par banque × trimestre × indicateur
(7 137 lignes au 23/10/2026), avec le trimestre seul et le cumul côte à côte.

| Étape | Ce qu'elle fait |
|---|---|
| `Source` | part de `Versions` (référence, pas de nouvelle lecture du fichier) |
| `VersionRetenue` | **filtre sur la version retenue** : `version = source_valeur`, une seule version par banque × trimestre × indicateur × mesure (11 460 lignes) |
| `Colonnes` | garde les clés, la mesure (`trim` / `cumul`), la valeur retenue, la version, le fichier, la page et la rupture de série |
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
dépôts, capitaux propres : la valeur à la date est dans `Valeur_Cumul`). `Fichier_*` et `Page_*`
gardent la source de chaque valeur ; `Rupture_*` (« oui ») et `Detail_Rupture_*` alimentent les
marqueurs et les info-bulles des graphiques.

## 3. Mesures DAX

À écrire après les requêtes (`dax/mesures.dax`).

## 4. Pages du rapport : visuels, champs et mesures

À préparer quand les mesures seront écrites (liste des pages : spécification, section 9).
