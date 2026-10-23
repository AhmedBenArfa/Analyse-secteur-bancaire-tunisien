<!-- Auteur : Ahmed Ben Arfa -->
# Feuille de route et décisions

État d'avancement du projet et décisions prises, tenus à jour après chaque étape terminée
(chaque requête Power Query, chaque groupe de mesures, chaque décision). La présentation du
projet est dans le [README](../README.md), le détail des règles dans la
[spécification](SPECIFICATION.md).

*Dernière mise à jour : 23/10/2026.*

## État d'avancement

| # | Étape | État |
|---|---|---|
| 1 | Script de collecte et d'extraction des indicateurs trimestriels | Fait |
| 2 | Collecte réelle T4 2019 → T3 2026 et corrections | Fait : 336/336 documents, 12 gabarits de mise en page |
| 3 | Validation sur l'image des PDF | Valeurs de référence relevées à la main (438 sur 41 documents) ; `docs/validation.md` à écrire |
| 4 | Cours boursiers 2019–2026 | Fait : 1 955 séances par banque, 63 opérations sur titres sourcées |
| 4b | États financiers (ROE, ROA) | Fait : 168 arrêtés, 504 valeurs retenues |
| 4c | Écarts du contrôle annuel | Fait : 22 écarts, cause et source de chacun (`docs/ecarts_annuels.csv`) |
| 5 | Requêtes Power Query | **En cours** : `CheminDonnees`, `Fichiers_Donnees`, `Versions`, `Dim_Indicateur` (27 lignes), `Fait_Indicateurs` (7 173 lignes), `Revisions` (14 884 lignes) écrites dans le projet `.pbip` et vérifiées dans Power BI Desktop le 23/10/2026 , `Banques_Actionnariat` (fichier Excel, 15 lignes) et `Dim_Banque` (12 lignes) vérifiées ; `AdresseDepot`, `Evenements` (11 lignes, vérifiée) et `Operations_Titres` (évaluée sans erreur), lues par URL ; cache des données versionné ; `Fait_Cours` (23 460 séances, cours ajustés) vérifiée ; guide : tableau des 38 fonctions M utilisées ; `Variations_Comparables` (10 981 lignes) vérifiée ; `Fait_Etats_Financiers` (504 lignes) vérifiée ; `Revisions_Etats_Financiers` (423 lignes) vérifiée ; `Controle` chargée (336 lignes attendues) ; `Ecarts_Annuels` et `Controle_Annuel` (288 lignes) vérifiées ; `Gabarits`, `Definitions_Charges` (13 lignes) et `Definitions_Capitaux_Propres` (12 lignes) vérifiées |
| 6 | Modèle en étoile et mesures DAX | À faire |
| 7 | Pages du rapport | À faire |
| 8 | README final et captures | README réécrit, section « Ouvrir le rapport » ; captures et lien de publication sur le web à faire |

## En cours

- Étape 5 : dernière transformation, la colonne « segment d'actionnariat » des faits. Vérifiées :
  `Gabarits`, `Definitions_Charges`, `Definitions_Capitaux_Propres`, `Ecarts_Annuels` et `Controle_Annuel` (288 contrôles, écarts
  affichés avec trois décimales) ; la période Covid sera une colonne de la table des dates (étape 6).
  Vérifiées : `Revisions_Etats_Financiers` (423 versions écartées), `Fait_Etats_Financiers` (504 lignes, version retenue, annualisation), `Variations_Comparables` (10 981 lignes : valeur N et
  N-1 du même document, variation recalculée), `Fait_Cours` (23 460 séances ;
  fusion avec `Operations_Titres`, cours ajustés, rendement quotidien, « sans transaction »),
  paramètre `AdresseDepot`,
  `Operations_Titres` et `Evenements` (lues par URL). Vérifiées le 23/10/2026 : `Banques_Actionnariat` (connecteur Excel,
  15 lignes) et `Dim_Banque` (12 banques, fusion avec l'actionnariat en cours) ; part du capital
  affichée avec trois décimales (UBCI 2019 : 50,085 %). BTE : seconde période d'actionnariat à partir
  du 01/07/2024 (date de l'augmentation de capital inconnue, entre le 30/06 et le 31/12/2024) ; test
  de continuité des périodes de 2019 à aujourd'hui pour les 12 banques. Vérifiées le 23/10/2026 dans Power BI Desktop : `Dim_Indicateur`,
  `Fait_Indicateurs` (fusion avec `Dim_Indicateur`, colonne conditionnelle sur les stocks, « non »
  pour les ruptures) et `Revisions` (filtre inverse, écart calculé, colonnes conditionnelles) ; tous
  les contrôles du guide (section 1) conformes.

## Prochaines actions

1. Dernière transformation de l'étape 5 : segment d'actionnariat sur les faits,
   colonnes conditionnelles (période Covid, segment d'actionnariat).
2. Mesures DAX (totaux du secteur seulement quand les 12 banques sont présentes, nombre de banques
   présentes, dernier trimestre complet).
3. `docs/validation.md`, pages du rapport, captures.
4. Publication du rapport terminé sur le web (« Publier sur le web ») et lien en tête du README.

## Trimestres incomplets pour le secteur

Vérifié le 23/10/2026 sur les valeurs retenues (28 trimestres, de 2019T4 à 2026T3) :

- **complets (28/28)** : PNB, produits et charges d'exploitation bancaire, charges opératoires,
  frais de personnel, charges générales (trimestre seul et cumul), crédits, dépôts ;
- **complets (28/28) depuis le 23/10/2026** : intérêts perçus et encourus, commissions en produits
  et encourues, revenus du portefeuille (donc marge d'intérêts et marge sur commissions) ;
- **22/28** : portefeuille-titres, dépôts à vue et d'épargne, emprunts : il manque BTE de 2020T1 à
  2020T4, 2021T1 et 2021T3 (documents publiés en image, détail du bilan non saisi) ;
- capitaux propres trimestriels : 20/28 (BTE), affichés seulement dans la fiche banque ;
- jamais complets, publiés par une partie des banques seulement : dotations aux amortissements,
  dépôts à terme, autres dépôts, portefeuille commercial, autres produits d'exploitation (hors
  indicateurs du rapport).

Le total du secteur d'un indicateur n'est calculé que pour ses trimestres complets.

## Décisions prises

| Date | Sujet | Décision |
|---|---|---|
| 17/10/2026 | Révisions des banques | La valeur retenue est toujours la version révisée quand elle existe (colonne N-1 du document de l'année suivante) ; écart mesuré sur le cumul ; plus de 2 % = révision importante et rupture de série |
| 17/10/2026 | Colonnes de comparaison fausses | Une colonne N-1 fausse dans le document d'une banque n'est jamais retenue (UIB 2023T2 par règle automatique, Wifak 2023T4 par `exclusions_colonnes.csv`) |
| 17/10/2026 | Coefficient d'exploitation | Coefficient harmonisé (frais de personnel + charges générales) / PNB pour toutes les comparaisons ; coefficient publié affiché pour information |
| 17/10/2026 | Documents en image | BH 2019T4 repris du document suivant, sans saisie ; BTE saisi à la main, avec le fichier, la page et la vérification de chaque valeur |
| 18/10/2026 | ROE et ROA | Résultat net avant modifications comptables, pour toutes les banques |
| 18/10/2026 | ilboursa | Comparaison du résultat net purement informative |
| 19/10/2026 | Capitaux propres | Comparaisons entre banques avec les capitaux propres du bilan ; capitaux propres trimestriels dans la fiche banque seulement, avec la définition de chaque banque |
| 19/10/2026 | États financiers manquants | Recherche dans l'ordre : site de la BVMT, liste du CMF, Bulletins Officiels ; même règle des versions que les indicateurs |
| 20/10/2026 | BNA S1 2025 | Le résultat avant modifications comptables prime sur la règle des versions |
| 20/10/2026 | Nombre mal formé (Attijari S1 2026) | Déduit seulement s'il se déduit exactement d'un total du même document |
| 20/10/2026 | Cours 2026 | Bulletins quotidiens de la Bourse pour les cours, volume d'ilboursa ; ajustements calculés dans Power Query à partir de `operations_titres.csv` ; 10 s entre deux requêtes vers la Bourse |
| 21/10/2026 | Ouvertures 2022–2025 | Pas de téléchargement des bulletins quotidiens : ouvertures laissées vides |
| 22/10/2026 | BTE | Saisie des 13 documents publiés en image (indicateurs principaux) |
| 22/10/2026 | Actionnariat | Classement par le contrôle, en 4 catégories (spécification 5.3) |
| 23/10/2026 | Publication | Dépôt public ; adresse e-mail de l'auteur gardée dans l'historique ; audit avant chaque push ; code sous licence MIT |
| 23/10/2026 | Données pour Power BI | CSV finaux versionnés dans `donnees_publiees/`, régénérés par `scripts/publier_donnees.py` |
| 23/10/2026 | Projet Power BI | Enregistré en projet `.pbip` (modèle en texte TMDL, versionné) ; cache des données et réglages du poste non versionnés |
| 23/10/2026 | Valeurs vides de `Fait_Indicateurs` | Vides gardés (jamais zéro) ; `Valeur_Trim` vidé pour les stocks par une colonne conditionnelle après fusion avec `Dim_Indicateur` ; « non » pour les ruptures absentes |
| 23/10/2026 | BTE T4 2021 et T4 2022 | Saisie des composantes du trimestre seul (intérêts, commissions, portefeuille, autres produits) avec les versions révisées des documents suivants ; autres produits de 2023T4 vérifiés sur l'image (0) |
| 23/10/2026 | BTE 2020T1 à 2021T3 | Saisie des composantes (intérêts, commissions, portefeuille, autres produits) de 2020T1–T4, 2021T1 et 2021T3, avec les colonnes N-1 des documents suivants : 216 valeurs ; intérêts, commissions et portefeuille complets pour le secteur à 28/28 trimestres |
| 23/10/2026 | Documentation des transformations | `docs/Guide_PowerBI.pdf` : chaque transformation expliquée, code M de chaque requête et feuille de route en annexe, régénéré après chaque requête ou groupe de mesures |
| 23/10/2026 | Niveaux de confidentialité | Même niveau pour toutes les sources (Professionnel), dossier du projet plutôt que tout le disque, accès anonyme à GitHub |
| 23/10/2026 | Facteur d'ajustement « prix » | Dividende détaché le même jour qu'une attribution retiré de la clôture de la veille avant la parité (BT 10/05/2022 : 0,834 au lieu de 0,796) |
| 23/10/2026 | BTE, actionnariat 2024 | Date de l'augmentation de capital introuvable dans les états financiers : seconde période à partir du 01/07/2024, « date exacte inconnue, entre le 30/06 et le 31/12/2024 » ; périodes continues contrôlées par un test |
| 23/10/2026 | Ouverture du projet par un tiers | Cache des données Power BI versionné (données publiques) : le projet s'ouvre avec ses données sans réglage ; section « Ouvrir le rapport » du README ; publication sur le web à la fin |
| 23/10/2026 | Documentation des fonctions M | Tableau de chaque fonction M utilisée (ce qu'elle fait, requêtes) dans le guide et son PDF, contrôlé par un test |
