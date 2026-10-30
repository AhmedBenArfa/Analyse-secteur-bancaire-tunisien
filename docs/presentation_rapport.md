<!-- Auteur : Ahmed Ben Arfa -->
# Analyse du secteur bancaire tunisien — présentation du rapport Power BI

## 1. Le projet en bref

Le rapport compare les **12 banques cotées à la Bourse de Tunis** (AB, ATB, Attijari, BH, BIAT, BNA, BT, BTE, STB,
UBCI, UIB, Wifak), **trimestre par trimestre, du T4 2019 au T3 2026**. Il cherche à répondre à sept questions :

1. Quelles banques ont le produit net bancaire (PNB) le plus élevé, et lesquelles gagnent des parts de marché ?
2. Quelles banques sont les plus efficaces (coefficient d'exploitation), et comment cela évolue-t-il ?
3. D'où viennent leurs revenus : marge d'intérêts, commissions, portefeuille-titres ?
4. Comment ont évolué les crédits, les dépôts et la concentration du secteur ?
5. Quelles banques sont les plus rentables (ROE, ROA) ?
6. Quel a été l'effet du Covid, et comment le secteur s'est-il redressé ?
7. La Bourse récompense-t-elle les banques les plus performantes ?

Trois pages sont terminées et vérifiées (section 4) ; elles répondent aux questions 1, 2, 4 (concentration) et 6.
Les six autres pages sont prévues (section 5).

## 2. Les données : publications officielles, tracées et contrôlées

| Source | Contenu | Volume |
|---|---|---|
| Indicateurs d'activité trimestriels (CMF, Bourse de Tunis, sites des banques) | PNB et ses composantes, charges, crédits, dépôts, capitaux propres | 336 documents (12 banques × 28 trimestres), 11 545 valeurs retenues |
| États financiers individuels, annuels et semestriels | résultat net, total de l'actif, capitaux propres (pour le ROE et le ROA) | 168 arrêtés, 504 valeurs |
| Cours de bourse (archives et bulletins de la Bourse de Tunis) | clôtures quotidiennes, ajustées des opérations sur titres | 1 955 séances par banque, 63 opérations sur titres sourcées |

**Chaque valeur garde sa source** (fichier et page du PDF). Rien n'est estimé : une valeur absente reste vide.

**Contrôles et validation.**

- 438 valeurs relevées à la main sur l'image des PDF (41 documents) et 169 pour les états financiers (24 documents),
  comparées automatiquement à l'extraction ; 48 tests automatiques au total.
- Contrôles de cohérence à chaque extraction : produits − charges = PNB, somme des quatre trimestres = cumul
  annuel, PNB = marge d'intérêts + marge sur commissions + revenus du portefeuille.
- 13 documents publiés en image (BTE) saisis à la main avec les mêmes contrôles.
- Les banques révisent souvent leurs chiffres d'un document à l'autre : la règle retenue garde la version révisée,
  signale les révisions de plus de 2 % comme ruptures de série, et calcule les croissances sur un an dans un même
  document (valeur N et valeur N-1 publiées ensemble), pour ne jamais comparer deux bases différentes.
- Les 22 écarts annuels (somme des trimestres différente du cumul) sont tous expliqués, avec leur source.

**Limites** : les indicateurs trimestriels sont provisoires et non audités ; les définitions de certains postes
diffèrent d'une banque à l'autre (d'où un coefficient d'exploitation « harmonisé », défini de la même façon pour
toutes) ; le ROE et le ROA ne sont que semestriels et annuels.

## 3. Chaîne de traitement

**PDF publics → extraction en Python → fichiers CSV publiés → Power Query → modèle en étoile → mesures DAX → pages.**

- **Python ne fait que lire les PDF** (gabarit de mise en page par banque, contrôles, versions initiale et
  révisée). Tout le reste est fait dans Power BI, pour que les transformations restent visibles.
- **Power Query : 22 requêtes**, sur trois types de sources (dossier de fichiers CSV, classeur Excel de
  l'actionnariat, fichier CSV lu par son adresse sur GitHub) ; fusions de requêtes (dont une sur trois colonnes),
  dépivotage, colonnes conditionnelles, types avec paramètres régionaux, requêtes intermédiaires non chargées,
  paramètre de chemin, fonction personnalisée (catégorie d'actionnariat de la banque à la date de chaque valeur).
- **Modèle en étoile** : table des dates (avec la période Covid), dimensions banques et indicateurs, tables de
  faits (indicateurs, variations comparables, états financiers, cours, contrôles) ; 32 relations, dont une inactive
  activée par `USERELATIONSHIP`.
- **154 mesures DAX**, rangées en dossiers (bases, secteur, ratios, croissances, rentabilité, Bourse, qualité), avec
  des règles écrites : totaux du secteur, parts de marché et rangs seulement si les 12 banques sont présentes ;
  chiffres annuels tirés du cumul publié, jamais de la somme des trimestres ; aucun vide remplacé par zéro.
- **Documentation** : chaque requête, chaque mesure et chaque page sont expliquées dans
  `docs/Guide_PowerBI.pdf` ; chaque mesure a été vérifiée dans la vue Requête DAX contre des valeurs calculées à
  part.

## 4. Les pages construites

Toutes les pages partagent la même présentation : thème aux couleurs d'un rapport bancaire, bandeau de titre,
segment du trimestre réglé par défaut sur **« Dernier trimestre complet »** (le dernier trimestre où les 12
banques ont publié, ici le T3 2026, pour que la page reste juste quand de nouvelles publications arrivent) et
segment des banques avec leur logo.

### Page 1 — Vue d'ensemble du secteur

![Page 1 : vue d'ensemble du secteur](captures/page1_vue_ensemble.png)

**Ce que la page montre** : la taille du secteur au dernier trimestre complet, son efficacité et sa concentration.

- Quatre cartes : PNB du trimestre (**1 936,6 MDT**, 12 banques présentes), coefficient d'exploitation du secteur
  (**44,7 %**, médiane des banques 47,0 %), encours de crédits (**86 880 MDT**, +2,1 % sur un an) et de dépôts
  (**112 896 MDT**, +8,2 % sur un an).
- Parts de marché du PNB : la BIAT en tête (**22,4 %**), devant la BNA (15,4 %) et la STB (10,0 %) ; les trois
  premières banques font **47,8 %** du PNB.
- Concentration dans le temps (indice de Herfindahl-Hirschman, de 1 106 à 1 209 sur la période) : marché peu
  concentré, en légère hausse.

**Choix de conception** : les cartes du secteur ne s'affichent que si les 12 banques ont publié (sinon un total
partiel passerait pour le secteur) ; la courbe de concentration ignore le segment du trimestre pour montrer toute
la période.

### Page 2 — Classement des banques

![Page 2 : classement des banques](captures/page2_classement.png)

**Ce que la page montre** : le classement des 12 banques au trimestre choisi, sur la taille, l'efficacité et la
croissance.

- Tableau : PNB, part de marché et rang ; coefficient d'exploitation harmonisé ((frais de personnel + charges
  générales) / PNB) et son rang ; écart à la médiane des banques, en vert si la banque fait mieux que la médiane, en
  rouge sinon ; croissance du PNB sur un an.
- Au T3 2026 : la BIAT est première au PNB, la **BT la plus efficace (coefficient de 30,1 %)**, la BTE la moins
  efficace (82,4 %) ; six banques font mieux que la médiane (47,0 %).
- Nuage de points croissance × efficacité, taille des points = PNB, avec un **axe de lecture** (bouton ▶) qui fait
  défiler les 28 trimestres : on voit par exemple le choc de 2020 (au T2 2020, PNB de l'UIB −78,7 % sur un an,
  effet du moratoire Covid sur les intérêts).

**Choix de conception** : le classement utilise le coefficient harmonisé et non celui publié par chaque banque, dont
le contenu varie (avec ou sans dotations aux amortissements) ; la couleur vient d'une mesure du modèle, la règle
est donc écrite une seule fois.

### Page 3 — Évolution 2020–2026

![Page 3 : évolution 2020–2026](captures/page3_evolution.png)

**Ce que la page montre** : chaque banque trimestre par trimestre, sur l'indicateur choisi dans le sélecteur
(PNB, coefficient d'exploitation, crédits / dépôts, part du PNB, croissance du PNB sur un an), avec la période Covid
marquée par deux lignes verticales (mars 2020 et fin 2021).

- Un **paramètre de champ** change l'indicateur de toutes les courbes sans dupliquer le graphique.
- Les **sauts de série** sont expliqués : les révisions de plus de 2 % (174 sur les cinq indicateurs de la page,
  pour toutes les banques) et les événements datés et sourcés (don au Fonds 1818 en 2020, accord salarial
  APTBEF–FGBEF en 2021, moratoire Covid de l'UIB, retraitement de la BH en 2024) apparaissent dans l'info-bulle de
  chaque point et dans deux tableaux à droite.
- Lecture : au T2 2020, le PNB trimestriel est inférieur à celui du T4 2019 pour 10 banques sur 12 (toutes sauf
  l'ATB et la BT), et c'est le point bas de 2020–2021 pour 8 d'entre elles (BIAT : 264,3 MDT au T4 2019, 224,3 au
  T2 2020) ; puis reprise : la BIAT atteint 433,3 MDT au T3 2026.

**Choix de conception** : axe des dates continu (les 28 trimestres sans défilement) ; courbes droites entre deux
trimestres, sans lissage, pour ne pas dessiner de creux ou de pics qui n'existent pas dans les données.

## 5. Suite du rapport

| Page | Contenu prévu | Question |
|---|---|---|
| 4. Structure du PNB (en construction) | part de la marge d'intérêts, des commissions et du portefeuille, par banque et dans le temps | 3 |
| 5. Bilan | crédits, dépôts, ratio crédits / dépôts, structure des dépôts, parts de marché | 4 |
| 6. Bourse | cours ajustés, performance, volatilité et liquidité du titre ; performance boursière face à la croissance du PNB | 7 |
| 7. Fiche banque | tous les indicateurs d'une banque (clic droit depuis une autre page), définitions propres à la banque, chaîne de contrôle de l'actionnariat | 1 à 5 |
| 8. Rentabilité | ROE et ROA semestriels et annuels, rentabilité face à l'efficacité | 5 |
| 9. Qualité des données | statut de chaque document, révisions, écarts expliqués, sources et limites | — |

Fonctions DAX prévues en plus de celles déjà utilisées : jointures `NATURALINNERJOIN` et `NATURALLEFTOUTERJOIN`
(page 8), hiérarchie parent-enfant `PATH`, `PATHITEM`, `PATHLENGTH`, `PATHCONTAINS` (page 7). Ensuite : publication
du rapport sur le web, captures et page d'accueil du dépôt.

**Dépôt du projet** : https://github.com/AhmedBenArfa/Analyse-secteur-bancaire-tunisien — code, données publiées,
projet Power BI, spécification (`docs/Specification_projet.pdf`), guide de chaque transformation
(`docs/Guide_PowerBI.pdf`) et rapport d'avancement (`docs/Rapport_avancement.pdf`).
