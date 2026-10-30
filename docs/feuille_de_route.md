<!-- Auteur : Ahmed Ben Arfa -->
# Feuille de route et décisions

État d'avancement du projet et décisions prises, tenus à jour après chaque étape terminée
(chaque requête Power Query, chaque groupe de mesures, chaque décision). La présentation du
projet est dans le [README](../README.md), le détail des règles dans la
[spécification](SPECIFICATION.md).

*Dernière mise à jour : 24/10/2026.*

## État d'avancement

| # | Étape | État |
|---|---|---|
| 1 | Script de collecte et d'extraction des indicateurs trimestriels | Fait |
| 2 | Collecte réelle T4 2019 → T3 2026 et corrections | Fait : 336/336 documents, 12 gabarits de mise en page ; 13 documents publiés en image saisis à la main ; 11 545 valeurs retenues |
| 3 | Validation sur l'image des PDF | Valeurs de référence relevées à la main (438 sur 41 documents) ; `docs/validation.md` à écrire |
| 4 | Cours boursiers 2019–2026 | Fait : 1 955 séances par banque, 63 opérations sur titres sourcées |
| 4b | États financiers (ROE, ROA) | Fait : 168 arrêtés, 504 valeurs retenues |
| 4c | Écarts du contrôle annuel | Fait : 22 écarts, cause et source de chacun (`docs/ecarts_annuels.csv`) |
| 5 | Requêtes Power Query | **Terminée le 23/10/2026** : 22 requêtes, toutes vérifiées dans Power BI Desktop (détail ci-dessous) |
| 6 | Modèle en étoile et mesures DAX | **Terminée le 24/10/2026** : table des dates, 32 relations (dont une inactive), 150 mesures (151 avec la mesure d'affichage de la page 2), colonnes calculées et journal des faits marquants, tout vérifié dans Power BI Desktop (détail ci-dessous) |
| 7 | Pages du rapport | **En cours** : page 1 « Vue d'ensemble » terminée et vérifiée (30/10/2026) ; page 2 « Classement » terminée et vérifiée (30/10/2026) ; prochaine : page 3 « Évolution 2020–2026 » |
| 8 | README final et captures | README réécrit, section « Ouvrir le rapport » ; captures et lien de publication sur le web à faire |

## Étape 5 : requêtes Power Query (terminée)

| Rôle | Requêtes (nombre de lignes) |
|---|---|
| Paramètres | `CheminDonnees` (dossier du projet), `AdresseDepot` (fichiers bruts du dépôt GitHub) |
| Intermédiaires, non chargées | `Fichiers_Donnees`, `Versions`, `Operations_Titres`, `Ecarts_Annuels`, `Gabarits` ; fonction personnalisée `Actionnariat_A_La_Date` |
| Dimensions | `Dim_Indicateur` (27), `Dim_Banque` (12), `Banques_Actionnariat` (15) |
| Faits | `Fait_Indicateurs` (7 173), `Variations_Comparables` (10 981), `Fait_Etats_Financiers` (504), `Fait_Cours` (23 460), `Evenements` (11) |
| Qualité et définitions | `Revisions` (14 884), `Revisions_Etats_Financiers` (423), `Controle` (336), `Controle_Annuel` (288), `Definitions_Charges` (13), `Definitions_Capitaux_Propres` (12) |

Trois types de sources (dossier de CSV, fichier Excel, adresse GitHub) ; dépivotage et pivot, fusions,
types avec paramètres régionaux, colonnes conditionnelles, regroupements, fonction personnalisée
(segment d'actionnariat à la date de chaque valeur). Chaque étape est expliquée dans
[`guide_powerbi.md`](guide_powerbi.md) et dans `Guide_PowerBI.pdf`.

## Étape 6 (terminée) : modèle et mesures DAX

Un groupe à la fois, chacun vérifié dans Power BI Desktop (requête de contrôle `dax/controle_*.dax`) avant le suivant :

1. **Table des dates** (faite le 23/10/2026, `dax/Dim_Date.dax`, vérifiée dans Power BI Desktop ; attendu :
   2 922 jours, 32 fins de trimestre, Avant Covid 425 / Covid 671 / Après Covid 1 826 jours) : du 01/01/2019 au 31/12/2026, année, trimestre, libellé du trimestre trié
   chronologiquement, fin de trimestre, **période Covid** (avant le 01/03/2020, jusqu'au 31/12/2021,
   après) triée par une colonne d'ordre ; libellé du trimestre au format des faits (« 2024T3 ») ;
   marquée comme table de dates.
2. **Relations du modèle en étoile** (28 relations, vérifiées le 23/10/2026 dans « Gérer les relations » ; clés contrôlées :
   aucune banque, aucun code, aucune date des faits absents de leur dimension) (une dimension vers plusieurs lignes, filtre simple) : dates, banques
   et indicateurs vers les tables de faits, de qualité et d'événements.
3. **Mesures DAX par groupes** : bases (26 mesures dans la table `Mesures`, vérifiées le 23/10/2026 avec
   `dax/controle_bases.dax`) ; secteur (17 mesures, vérifiées le 23/10/2026 avec
   `dax/controle_secteur.dax`) ; ratios (16 mesures, vérifiées le 24/10/2026 avec
   `dax/controle_ratios.dax`) ; croissances (22 mesures, vérifiées le 24/10/2026 avec
   `dax/controle_croissances.dax`) ; ROE et ROA (19 mesures, vérifiées le 24/10/2026 avec
   `dax/controle_rentabilite.dax`) ; Bourse (15 mesures, vérifiées le 24/10/2026 avec
   `dax/controle_bourse.dax`) ; qualité des données (27 mesures, vérifiées le 24/10/2026 avec
   `dax/controle_qualite.dax`). Total : 142 mesures dans la table `Mesures`, rangées par dossier (147 avec les compléments du 24/10/2026 :
   `TOPN`, `USERELATIONSHIP`, journal par `UNION`, colonnes calculées par `RELATEDTABLE` et `LOOKUPVALUE`, vérifiés le
   24/10/2026 avec `dax/controle_complements.dax`) ; code et
   explications dans `dax/mesures.dax` et dans le guide (section 3).

## Prochaine étape : étape 7, pages du rapport

Pages construites dans Power BI Desktop à partir des mesures (liste des pages : spécification, section 9),
avec le segment « Dernier trimestre complet » par défaut et le paramètre de champ « Indicateur affiché ».
Présentation commune (demande du 24/10/2026, sans changer les pages ni les visuels prévus) : thème bancaire,
fonds de page signés, segment par banque avec le logo de chaque banque (colonne `icone`, vérifiée dans
Power BI Desktop le 24/10/2026), visuel Play Axis pour faire défiler les
années (guide, section 4.1).
Ensuite : `docs/validation.md` (étape 3), captures et publication sur le web avec le lien en tête du README
(étape 8).

### Règles pour les mesures DAX

- Totaux du secteur, parts de marché, rangs et indice de concentration **seulement quand les 12 banques
  sont présentes** ; sinon vides ou marqués « incomplet », avec le nombre de banques présentes affiché.
- Filtre par défaut sur le **dernier trimestre complet** (12 banques présentes), pas sur le dernier
  trimestre qui contient une donnée.
- **Croissances sur un an** calculées avec `Variations_Comparables` (valeur N et N-1 du même document),
  jamais en rapprochant deux documents.
- **Chiffres annuels** pris dans le cumul de l'année, jamais en additionnant les quatre trimestres.
- Soldes (crédits, dépôts, capitaux propres) pris à la date, jamais additionnés dans le temps.
- **Coefficient d'exploitation harmonisé** (frais de personnel + charges générales) / PNB pour toutes les
  comparaisons ; le coefficient publié reste une information, avec la définition de chaque banque.
- **Aucune valeur absente remplacée par zéro.**
- **ROE et ROA** avec les capitaux propres et le total de l'actif du bilan (états financiers), le résultat
  net avant modifications comptables annualisé, et la moyenne entre l'ouverture de l'exercice et la date ;
  les capitaux propres trimestriels ne servent qu'à la fiche banque.

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
| 23/10/2026 | Étape 5 terminée | Les 22 requêtes Power Query sont vérifiées ; passage à l'étape 6 (table des dates, relations, mesures DAX) |
| 30/10/2026 | Segment du trimestre | Filtré par la colonne `Dim_Date[Trimestre_Publie]` (trimestres où au moins une banque a publié), sélection unique ; un filtre par mesure ne convient pas sur un segment |
| 30/10/2026 | Documentation des pages | Dans le guide (section 4 : méthode, présentation commune, une sous-section par page), et non dans un document séparé : un seul PDF explique tout le rapport |
| 30/10/2026 | Page 2 « Classement » : choix du trimestre | Segment « Dernier trimestre complet » (comme la page 1) et **axe de lecture intégré au nuage de points** pour faire défiler les trimestres ; le visuel Play Axis, essayé d'abord, démarre sans trimestre et vide la page en fin de lecture : retiré ; carte « Trimestre affiché » (mesure `Trimestre affiche`) |
| 30/10/2026 | Construction des pages | Visuels créés dans Power BI Desktop, réglages (positions, noms, titres, axes, interactions) écrits dans les fichiers du rapport par un script ; cartes du PNB, des crédits et des dépôts en mesures de texte mises en forme (la nouvelle carte abrège en milliers) |
| 24/10/2026 | Fonctions DAX complémentaires | `RELATEDTABLE` et `LOOKUPVALUE` en colonnes calculées de `Dim_Banque` (liquidité du titre, définitions), table `Journal_Faits_Marquants` par `UNION` (41 faits datés), relation inactive vers la date d'entrée d'un actionnaire et mesures `USERELATIONSHIP`, mesures `TOPN` (3 premières banques, CR3) ; mesures déjà vérifiées inchangées |
| 24/10/2026 | Logos des banques | Logos officiels téléchargés (sites des banques, sinon fiche de la Bourse ou Wikimedia Commons), réduits en vignettes 240 × 120, versionnés dans `donnees_reference/logos/` avec leur source et la mention de propriété ; colonne `icone` de `Dim_Banque` construite en Power Query (image intégrée, catégorie « URL d'image ») ; pastilles au code en secours |
| 24/10/2026 | Présentation du rapport | Thème bleu marine et or, fonds de page 16:9 signés (`python scripts/generer_theme.py`), pastilles au code de chaque banque pour le segment à images (pas de logo officiel), visuel Play Axis pour faire défiler les années ; pages et visuels de la spécification inchangés |
| 24/10/2026 | Étape 6 terminée | Table des dates, relations et 142 mesures vérifiées ; passage à l'étape 7 (pages du rapport) |
| 24/10/2026 | Qualité des données | « Taux d'extraction » remplacé par la part des documents sans alerte, à côté du nombre d'écarts qui viennent des banques et des documents à vérifier ; paramètre de champ « Indicateur affiché » créé avec les pages du rapport |
| 24/10/2026 | Bourse | Mesures de cours pour une banque à la fois ; performance sur les clôtures ajustées (prix : opérations sur le capital ; rendement total : dividendes compris) au lieu des cours bruts ; avertissement « titre peu liquide » au-dessus de 20 % de séances sans transaction |
| 24/10/2026 | ROE et ROA | Moyenne des capitaux propres et du total de l'actif vide si l'ouverture ou la fin manque (pas de moyenne sur une seule valeur) ; annualisation par la colonne de Power Query ; ratios à la dernière date des états financiers de la sélection ; secteur seulement avec les 12 banques |
| 24/10/2026 | Croissances | Variations sur un an depuis `Variations_Comparables` (même document), sur une ligne par banque, vides si une banque de la sélection manque ; PNB sur 4 trimestres glissants comme tendance seulement ; croissance annuelle moyenne 2020-2025 par enchaînement des 5 variations annuelles |
| 23/10/2026 | Ratios | Coefficient harmonisé calculé banque par banque au trimestre, et en version annuelle depuis les cumuls au 31/12 ; coefficient du secteur, médiane et rang vides si une banque manque ; coefficient publié pour information seulement |
| 23/10/2026 | Secteur et dernier trimestre complet | Totaux, parts de marché, HHI et rangs vides si une banque manque ; encours du secteur comptés à la dernière date de la sélection ; colonne `Dim_Date[Choix_Trimestre]` : « Dernier trimestre complet » (PNB, crédits, dépôts des 12 banques) pour le filtre par défaut des pages |
| 23/10/2026 | Mesures de base | Table `Mesures` dédiée, dossiers d'affichage, format `#,0.000` ; `Valeur Trim` et `Valeur Cumul` vides si la sélection couvre plusieurs dates d'arrêté (jamais de somme de trimestres ni d'encours dans le temps) ; marges vides si un terme manque |
| 23/10/2026 | Relations | 28 relations 1 → plusieurs, filtre simple : dates, banques, indicateurs vers les faits, la qualité et les événements ; `Fait_Cours` relié par le code de la banque (pas le ticker) ; actionnariat et définitions reliés aux banques |
| 23/10/2026 | Table des dates | Code de la spécification, libellé du trimestre « 2024T3 » (format des faits) au lieu de « 2024-T3 », période Covid triée par `Ordre_Periode` ; tables calculées écrites par `scripts/ecrire_tmdl_table.py` (outil existant étendu) ; code DAX dans `dax/`, en annexe du guide en PDF |
