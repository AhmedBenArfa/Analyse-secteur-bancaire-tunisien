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
| 5 | Requêtes Power Query | **En cours** : `CheminDonnees`, `Fichiers_Donnees`, `Versions`, `Fait_Indicateurs` écrites dans le projet `.pbip` et vérifiées dans Power BI Desktop (7 137 lignes) |
| 6 | Modèle en étoile et mesures DAX | À faire |
| 7 | Pages du rapport | À faire |
| 8 | README final et captures | README réécrit ; captures du rapport à faire |

## En cours

- Étape 5 : requête `Dim_Indicateur`, puis fusion de `Fait_Indicateurs` avec `Dim_Indicateur`
  (nature flux / stock), colonne conditionnelle qui vide `Valeur_Trim` pour les stocks, « non » au
  lieu d'une case vide pour les ruptures de série.

## Prochaines actions

1. Requêtes suivantes, une à la fois, vérifiées dans Power BI Desktop : `Revisions`, `Dim_Banque`
   avec l'actionnariat (`donnees_reference/banques.xlsx`), `Operations_Titres` et `Evenements` par
   leur lien *raw* GitHub, colonnes conditionnelles (période Covid, segment d'actionnariat).
2. Mesures DAX (totaux du secteur seulement quand les 12 banques sont présentes, nombre de banques
   présentes, dernier trimestre complet).
3. `docs/validation.md`, pages du rapport, captures.

## Trimestres incomplets pour le secteur

Vérifié le 23/10/2026 sur les valeurs retenues (28 trimestres, de 2019T4 à 2026T3) :

- **complets (28/28)** : PNB, produits et charges d'exploitation bancaire, charges opératoires,
  frais de personnel, charges générales (trimestre seul et cumul), crédits, dépôts ;
- **22/28** : intérêts perçus et encourus, commissions en produits et encourues, revenus du
  portefeuille (donc marge d'intérêts et marge sur commissions), portefeuille-titres, dépôts à vue
  et d'épargne, emprunts : il manque BTE de 2020T1 à 2020T4, 2021T1 et 2021T3 (documents publiés
  en image, seuls les indicateurs principaux saisis) ;
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
