<!-- Auteur : Ahmed Ben Arfa -->
# Données publiées

CSV finaux lus par le rapport Power BI (requête `Fichiers_Donnees`, connecteur Dossier). Ils sont
versionnés pour qu'on puisse ouvrir le rapport après avoir cloné le dépôt, sans relancer la
collecte. Aucun PDF ni archive : les documents d'origine restent sur les sites qui les publient ;
chaque valeur donne le fichier et la page d'où elle vient, et les manifestes donnent l'adresse de
chaque fichier.

Ce dossier est **régénéré** à partir de `donnees/` (dossier de travail non versionné) par :

```
python scripts/publier_donnees.py
```

La commande copie les fichiers tels quels, sauf la colonne `fichier` des deux manifestes et du
contrôle des états financiers (chemin du PDF sur le poste de collecte), ramenée au nom du fichier.
Elle refuse un fichier de plus de 50 Mo ou contenant un chemin local. Ne pas modifier ces CSV à la
main : toute correction se fait dans les scripts ou dans les fichiers de corrections, puis on
régénère.

Format commun : séparateur `;`, décimales avec un point, UTF-8 avec BOM ; montants en millions de
dinars (MDT) ; une case vide = valeur non disponible (jamais zéro). Les données sont
**provisoires et non auditées** (publications des banques, souvent révisées l'année suivante).

## Sources

| Source | Fichiers concernés |
|---|---|
| Indicateurs d'activité trimestriels des 12 banques (PDF) : sites de la BVMT et du CMF, liste des indicateurs du CMF, Bulletins Officiels du CMF ; Attijari 2021T2 sur tunis-stockexchange.com, Wifak 2022T3 sur wifakbank.com | `indicateurs_*`, `variations_comparables.csv`, `controle_extraction.csv`, `controle_annuel.csv`, `manifeste_telechargements.csv` |
| États financiers individuels annuels et semestriels (PDF) : site de la BVMT, liste des états financiers du CMF | `etats_financiers_*`, `controle_etats_financiers.csv`, `manifeste_etats_financiers.csv` |
| Archives de cotation de la BVMT (2019–2025), bulletins quotidiens de la Bourse de Tunis (2026), volumes d'ilboursa (2026) | `cours_banques.csv`, `controle_cours.csv` |
| Résultat net affiché par ilboursa (comparaison informative) | `verification_ilboursa.csv` |

Valeurs relevées à la main sur l'image des documents publiés en image : `saisies_manuelles.csv`
(racine du dépôt), reprises dans les fichiers ci-dessous avec le statut `saisie manuelle`.

## Fichiers

### Dimensions

| Fichier | Contenu |
|---|---|
| `dim_banque.csv` | Une ligne par banque : code, nom, ticker de la Bourse. Les colonnes `actionnariat` et `groupe` sont vides : l'actionnariat sourcé est dans `donnees_reference/banques.xlsx` |
| `dim_indicateur.csv` | Une ligne par code d'indicateur : libellé, catégorie, nature (`flux` : s'additionne ; `stock` : solde à une date, jamais additionné), ordre d'affichage |

### Indicateurs trimestriels

| Fichier | Contenu |
|---|---|
| `indicateurs_banques_long.csv` | Valeurs brutes : une ligne par document × indicateur × colonne lue (`trim_N`, `cumul_N`, `trim_N1`, `cumul_N1`, `exercice_N1`), avec le libellé du document, la valeur et l'unité publiées, la valeur en MDT, le fichier, la page, le gabarit appliqué, la mention de retraitement et la vérification (saisies) |
| `indicateurs_versions.csv` | Table de faits des indicateurs : une ligne par banque × trimestre × indicateur × mesure (`trim` / `cumul`) × version (`initiale` = document du trimestre, `revisee_T<q>_N+1` = colonne N-1 du document de l'année suivante, `revisee_31-12_…` = 31/12 provisoire). La valeur retenue est la ligne où `version = source_valeur` (version révisée quand elle existe). Statut de révision, rupture de série, note du document. Règle : `docs/SPECIFICATION.md`, 5.2 |
| `variations_comparables.csv` | Variations sur un an calculées dans un même document (valeur N, valeur N-1 de la même colonne de comparaison, variation en %) : source de toutes les croissances du rapport |
| `controle_extraction.csv` | Statut de chaque document (`ok`, `retraitement possible`, `ecart trimestre/cumul`, `ecart composantes`, `saisie manuelle`, `a verifier`, `illisible (image)`), nombre de valeurs, alertes, gabarit |
| `controle_annuel.csv` | Somme des 4 trimestres retenus contre cumul annuel retenu, par banque, année et indicateur : `ok`, `en attente de révision`, `rupture de série`, `ecart` (cause de chaque écart : `docs/ecarts_annuels.csv`) |
| `manifeste_telechargements.csv` | Un document par banque et trimestre : statut, source (`site`, `liste_cmf`, `bulletin_officiel`), adresse de téléchargement, nom du fichier, pages gardées (extraits de Bulletins Officiels) |

### États financiers (ROE, ROA)

| Fichier | Contenu |
|---|---|
| `etats_financiers_long.csv` | Valeurs lues dans les états financiers : résultat net (avant et après modifications comptables), total de l'actif, capitaux propres, résultat inscrit au bilan ; colonnes N et N-1 ; libellé, fichier, page, statut de la valeur |
| `etats_financiers_versions.csv` | Table de faits des états financiers : versions initiale et révisée de chaque valeur (31/12 et 30/06), valeur retenue (`version = source_valeur`), statut de révision, remarque (révisée non retenue, valeur déduite, événement) |
| `controle_etats_financiers.csv` | Statut de chaque arrêté, trois valeurs clés, alertes, recoupement avec les capitaux propres trimestriels, modifications comptables |
| `manifeste_etats_financiers.csv` | Un document par banque et arrêté : statut, source, adresse, nom du fichier |
| `verification_ilboursa.csv` | Résultat net annuel extrait contre celui d'ilboursa : comparaison **purement informative** (ilboursa ne précise pas comptes individuels ou consolidés) |

### Cours boursiers

| Fichier | Contenu |
|---|---|
| `cours_banques.csv` | Une ligne par banque et séance (02/01/2019 →) : ouverture, plus haut, plus bas, clôture (non ajustés), volume, nombre de transactions, capitaux, statut (sans transaction, ouverture vide, réservation…), source, fichier. Les ajustements se calculent dans Power Query avec `operations_titres.csv` |
| `controle_cours.csv` | Variations de clôture de plus de 6,15 % d'une séance à l'autre, à expliquer (opérations sur titres, hausses ou baisses réelles) |

## Autres fichiers lus par Power BI, ailleurs dans le dépôt

`donnees_reference/banques.xlsx` (actionnariat), `evenements.csv` et `operations_titres.csv`
(aussi lus par leur lien *raw* GitHub), `gabarits.csv` (définitions des charges opératoires et des
capitaux propres), `docs/ecarts_annuels.csv`, `docs/revisions_importantes.csv`.
