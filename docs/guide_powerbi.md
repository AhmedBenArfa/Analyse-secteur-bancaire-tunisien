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
4. Power BI crée `SecteurBancaireTunisien.pbip`, le dossier `SecteurBancaireTunisien.Report\`
   (pages et visuels) et le dossier `SecteurBancaireTunisien.SemanticModel\` (modèle : requêtes,
   tables, relations, mesures, au format texte TMDL dans `definition\`). Le fichier `.gitignore` qu'il
   ajoute exclut le cache des données (`cache.abf`) et les réglages locaux : seules les définitions
   sont versionnées, jamais les données.

Ajout d'une requête : **Accueil › Transformer les données**, puis dans Power Query **Nouvelle source ›
Requête vide**, **Éditeur avancé**, coller le contenu du fichier `.pq`, renommer la requête exactement
comme le fichier (sans `.pq`). Requête intermédiaire : clic droit › décocher **Activer le chargement**.
Après chaque série d'ajouts : **Fermer et appliquer**, puis enregistrer (Ctrl+S).

## 2. Requêtes Power Query

Ordre de création : chaque requête n'utilise que des requêtes déjà créées.

| # | Requête | Chargée | Source | Rôle |
|---|---|---|---|---|
| 1 | `CheminDonnees` | paramètre | — | dossier du projet sur ce poste |
| 2 | `Fichiers_Donnees` | non | connecteur Dossier | liste des CSV de `donnees\` |
| 3 | `Versions` | non | `indicateurs_versions.csv` | toutes les versions des indicateurs, typées |

### 2.1 `CheminDonnees` (paramètre)

Texte : le dossier du projet (`D:\Projet\Analyse-secteur-bancaire-tunisien`), qui contient `donnees\`
(CSV produits par Python), `donnees_reference\` (fichier Excel des banques) et `docs\`.
**Pourquoi** : un seul endroit à changer si le projet est copié sur un autre poste
(**Accueil › Gérer les paramètres**) ; aucune requête n'écrit de chemin en dur.

### 2.2 `Fichiers_Donnees` (intermédiaire, non chargée)

| Étape | Ce qu'elle fait |
|---|---|
| `Source` | `Folder.Files` : tous les fichiers de `donnees\`, sous-dossiers compris (connecteur Dossier) |
| `CsvDuDossier` | garde les `.csv` posés directement dans `donnees\` (pas les PDF ni les fichiers de `cours\`) |
| `Colonnes` | garde le nom, le contenu binaire et la date de modification |
| `Renommees` | noms en français : `fichier`, `contenu`, `modifie_le` |

**Pourquoi** : les requêtes suivantes prennent leur fichier par son nom dans cette table
(`Fichiers_Donnees{[fichier = "…"]}[contenu]`) ; la date de modification permet de vérifier, sur la
page qualité, que les CSV sont ceux du dernier lancement du script.

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

## 3. Mesures DAX

À écrire après les requêtes (`dax/mesures.dax`).

## 4. Pages du rapport : visuels, champs et mesures

À préparer quand les mesures seront écrites (liste des pages : spécification, section 9).
