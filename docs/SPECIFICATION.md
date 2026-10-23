<!-- Auteur : Ahmed Ben Arfa -->
# Spécification — Analyse du secteur bancaire tunisien (2019–2026)

## 1. Objectif

Construire un rapport Power BI qui compare l'activité, l'efficacité et la structure
des 12 banques cotées à la Bourse de Tunis, trimestre par trimestre, de T4 2019 à T3 2026,
et qui met en regard leur performance opérationnelle et leur performance boursière.

Questions auxquelles le rapport doit répondre :

1. Quelles banques ont le PNB le plus élevé, et lesquelles gagnent des parts de marché ?
2. Quelles banques sont les plus efficaces (coefficient d'exploitation) et comment cela évolue-t-il ?
3. D'où vient le PNB de chaque banque (marge d'intérêts, commissions, portefeuille-titres) ?
4. Comment ont évolué crédits et dépôts, et le ratio crédits / dépôts ?
5. Le secteur se concentre-t-il (indice HHI) ?
6. Quel a été l'effet du Covid (2020–2021) et comment le secteur s'est-il redressé ?
7. La Bourse récompense-t-elle les banques les plus performantes ?

Inspiration : un rapport Power BI publié sur LinkedIn sur les ratios des banques cotées au
30/06/2026, construit à partir des mêmes publications trimestrielles. Ce projet s'en distingue
par les ajouts listés en section 8.

## 2. Périmètre

| Élément | Choix |
|---|---|
| Banques | AB, ATB, Attijari Bank, BH Bank, BIAT, BNA, BT, BTE, STB, UBCI, UIB, Wifak International Bank |
| Période | T4 2019 → T3 2026 (T4 2019 sert seulement de base pour les évolutions sur un an de 2020) |
| Fréquence | Trimestrielle (indicateurs), quotidienne (cours) |
| Unité | Millions de dinars (MDT) |

## 3. Sources de données

| Source | Contenu | Format | Connexion Power BI |
|---|---|---|---|
| BVMT / CMF — indicateurs trimestriels | PNB, charges, crédits, dépôts… | PDF → CSV via `collecte_banques.py` | Dossier (CSV) |
| BVMT ou ilboursa — cours | Cours quotidiens 2019–2026 | CSV via script | Dossier (CSV) |
| Kaggle « Tunisian Stock Market » | Cours 2010 → janvier 2022 (contrôle) | CSV | Web (URL) ou fichier |
| Tables de référence remplies à la main | Banques (actionnariat, groupe), libellés, périodes | Excel | Excel |
| États financiers annuels et semestriels (CMF / BVMT) | Résultat net, total de l'actif, capitaux propres | PDF → CSV (script ou saisie) | Dossier (CSV) |
| Page web ilboursa (contrôle) | Tableau annuel par société (dont le résultat net) | HTML | Web (URL) |

Les trois types de connexion (CSV, Excel, URL) sont utilisés volontairement : c'est un point
à montrer dans le portfolio.

**Politesse envers les serveurs (décision du 20/10/2026).** Les trois scripts passent par le même
client (`Client` et `Politesse` dans `collecte_banques.py`) : le `robots.txt` de chaque site est
lu une fois avec notre User-Agent (groupe `User-agent: *`, jokers `*` et `$`, la règle la plus
longue l'emporte) ; délai entre deux requêtes au même site = max(`Crawl-delay`, `PAUSE` = 0,4 s),
URL interdites jamais demandées. Au 20/10/2026 : **bvmt.com.tn et cmf.tn : 10 s** ; ilboursa.com :
pas de délai demandé (0,4 s), seuls `/forums/post`, `/forums/abus`, `/users/login` et `/docs/*`
interdits. Avant cette date, les collectes utilisaient 0,4 s avec tous les sites.

Limites des données :

- Indicateurs **provisoires et non audités** ; certaines sociétés publient en retard.
- Mises en page différentes selon les banques et les années : contrôle obligatoire.
- Pas de résultat net dans les indicateurs trimestriels : le ROE et le ROA viennent des
  états financiers, donc seulement en semestriel et en annuel (voir 7.7).
- Certaines banques retraitent l'année précédente : les deux versions sont conservées
  (initiale, révisée) et la règle de la section 5.2 choisit la valeur d'analyse.
- **Wifak International Bank est une banque islamique** : ses indicateurs ne sont pas des
  intérêts et des crédits mais des **équivalences**, rangées sous les codes communs pour pouvoir
  comparer, à signaler dans le rapport :

  | Libellé Wifak | Code | Équivalent conventionnel |
  |---|---|---|
  | Marges et revenus assimilés | `INT_PERCUS` | Intérêts perçus |
  | Charges encourues et charges assimilées | `INT_ENCOURUS` | Intérêts encourus |
  | Revenus du portefeuille commercial & opérations financières + Revenus du portefeuille d'investissement | `REV_PORTEF` (somme des deux lignes) | Revenus du portefeuille-titres |
  | Encours net des financements à la clientèle | `CREDITS` | Encours des crédits |
  | Tawfir | `DEP_EPARGNE` | Dépôts d'épargne |
  | Comptes Istithmars | `DEP_TERME` | Dépôts à terme (comptes d'investissement) |
  | Dettes de financements et ressources spéciales | `EMPRUNTS` | Emprunts et ressources spéciales |

  La ligne « Pertes sur portefeuille titres commercial et opérations financières » (une charge)
  n'est rattachée à aucun indicateur. Pour Wifak, « marge d'intérêts » se lit donc « marges
  et revenus assimilés − charges encourues », et « crédits / dépôts » « financements / dépôts ».

## 4. Pipeline

```
PDF (BVMT, CMF, bulletins officiels)
   └─ collecte_banques.py ──> donnees/indicateurs_banques_long.csv  (une ligne par valeur lue dans un document)
                              donnees/indicateurs_versions.csv    (une ligne par période et version, valeur retenue)
                              donnees/dim_indicateur.csv, dim_banque.csv
                              donnees/controle_extraction.csv
scripts/publier_donnees.py ─> donnees_publiees/  (CSV finaux versionnés, lus par Power Query)
scripts/cours_boursiers.py ─> donnees/cours_banques.csv
Fiche émetteur, états financiers, rapports annuels ─> donnees_reference/banques.xlsx (actionnariat, sourcé)
                     │
                Power Query (ETL)
                     │
          Modèle en étoile Power BI ─> mesures DAX ─> rapport
```

## 5. ETL dans Power Query

### 5.1 Requêtes

| Requête | Source | Étapes principales |
|---|---|---|
| `Versions` (intermédiaire, non chargée) | `indicateurs_versions.csv` | types (paramètres régionaux en-US) ; textes vides → `null` (les valeurs saisies à la main, `saisies_manuelles.csv`, sont déjà dans le fichier, avec leur source) |
| `Fait_Indicateurs` | référence à `Versions` | filtre `version = source_valeur` (une ligne par banque × trimestre × indicateur × mesure) ; fusion avec `Dim_Indicateur` (nature) et colonne conditionnelle qui écarte la mesure `trim` des stocks (un solde n'a pas de trimestre seul : copie du solde au T1, mouvement du trimestre chez STB 2019T4 et UBCI 2024–2026 ; 320 lignes) ; « non » au lieu d'une case vide dans `rupture_serie` ; suppression de `valeur_mdt`, `version` ; pivot de `mesure` sur `valeur_retenue` → `Valeur_Trim` et `Valeur_Cumul` ; pivot de `mesure` sur `source_valeur` → `Source_Trim` et `Source_Cumul` ; pivot de `mesure` sur `rupture_serie` → `Rupture_Trim` et `Rupture_Cumul` (« oui » : période révisée de plus de 2 % sur le cumul, marqueur des graphiques) ; de même `Fichier_*`, `Page_*` (source de chaque valeur) et `Detail_Rupture_*` (info-bulle). Réalisation : dépivotage des attributs, nom de colonne attribut + mesure, un seul pivot sans agrégation |
| `Revisions` | référence à `Versions` | filtre `version <> source_valeur` (versions non retenues : initiales révisées, 31/12 provisoires remplacés par le T4 suivant, 31/12 exclus pour les capitaux propres) ; colonnes `banque`, `trimestre`, `date_arrete`, `code_indicateur`, `mesure`, `version`, `valeur_mdt`, `fichier`, `page`, `valeur_retenue`, `source_valeur`, `statut_revision` (retraitement_mineur / revision_importante / reclassement / exclue / illisible (image) / non disponible (image)), `note_definition`, `mention_retraitement`, `Ecart_MDT = valeur_retenue − valeur_mdt` (calculé dans Power Query, `ecart_vs_retenue` du CSV non repris), `Ecart_Pct` ; colonnes conditionnelles `Origine_Version` et `Type_Revision` (statut en clair) ; pour la page « qualité des données » |
| `Controle_Annuel` | `controle_annuel.csv` | types ; somme des trimestres vs cumul T4, statut (`ok`, `en attente de révision`, `rupture de série`, `ecart`) ; `Ecart_MDT` recalculé (somme − cumul), `date_arrete` (31/12), fusion avec `Ecarts_Annuels` sur banque, année et indicateur, colonne conditionnelle `Statut_Clair` |
| `Ecarts_Annuels` (intermédiaire) | `docs/ecarts_annuels.csv` (versionné ; connecteur Fichier, `CheminDonnees`) | cause de chaque `ecart` du contrôle annuel : `categorie` (retraitement de la banque / reclassement / arrondi / erreur d'extraction / erreur dans le document de la banque), `cause`, `fichier`, `page`, `correction` ; fusion avec `Controle_Annuel` sur `banque`, `annee`, `code_indicateur` ; page « qualité des données » |
| `Variations_Comparables` | `variations_comparables.csv` | types ; une ligne par banque × trimestre × indicateur × mesure (`trim` / `cumul`) : `valeur_N`, `valeur_N1` **du même document** ; fusion avec `Dim_Indicateur` et même filtre que `Fait_Indicateurs` (pas de mesure `trim` pour un stock) ; `Variation_Pct` = (N − N-1) / \|N-1\| recalculée dans Power Query (vide si N-1 = 0) ; source de toutes les variations sur un an (7.3) |
| `Banques_Actionnariat` | `donnees_reference/banques.xlsx` (table Excel `Banques`, connecteur Excel) | types ; catégorie contrôlée (une valeur hors des quatre catégories de 5.3 = erreur visible) ; une ligne par banque et par période (`date_debut` – `date_fin`) : l'actionnariat d'une période est celui de la ligne qui la couvre (5.3) |
| `Dim_Banque` | `dim_banque.csv` + `Banques_Actionnariat` | colonnes vides `actionnariat` et `groupe` du CSV retirées ; fusion avec la ligne en cours de `Banques_Actionnariat` (sans `date_fin`) : actionnaire de référence, part du capital, catégorie, groupe, `date_actionnariat` |
| `Dim_Indicateur` | `dim_indicateur.csv` | types ; colonne ajoutée `source` (« indicateurs trimestriels ») ; ajout de 3 lignes écrites dans la requête pour les codes des états financiers (`RES_NET` flux, `TOTAL_ACTIF` et `CAP_PROPRES_EF` stocks, source « états financiers », ordre 25 à 27) ; `libelle` trié par `ordre` dans le modèle |
| `Operations_Titres` (intermédiaire) | `operations_titres.csv` (versionné : lien *raw* GitHub, source URL, paramètre `AdresseDepot` + `RelativePath`) | types ; facteur = `cours_reference_publie / cloture_veille` (une valeur par banque et date d'effet) ; colonne conditionnelle `capital` (vrai sauf dividende seul) ; `facteur_prix` = 1 pour un dividende seul, et dividende retiré de la clôture de la veille quand il est détaché le même jour qu'une attribution (BT 10/05/2022 : 4,930 / (6,190 − 0,280)) ; facteurs cumulés par banque (produit des facteurs des dates postérieures), un pour le prix (opérations sur le capital) et un pour le rendement total (toutes) |
| `Fait_Cours` | `cours_banques.csv` | types (paramètres régionaux en-US), fusion avec `Operations_Titres` sur la banque puis première opération postérieure à la séance (ses facteurs cumulés ; 1 s'il n'y en a pas), colonnes `facteur_prix`, `facteur_rendement`, `cloture_ajustee_prix` et `cloture_ajustee_rendement` = clôture × facteur cumulé, `rendement` (variation de la clôture ajustée de la série « rendement total » d'une séance à l'autre, par banque ; dernière clôture connue quand elle est vide ; vide à la première séance) ; colonne conditionnelle `sans_transaction` (statut contenant « sans transaction », mesure de liquidité 7.5) ; `statut` gardé pour la page qualité |
| `Controle` | `controle_extraction.csv` | types ; colonne calculée `date_arrete` (fin du trimestre, à partir de `trimestre`) ; `nb_alertes` (alertes séparées par « \| ») ; colonne conditionnelle `Categorie_Statut` (conforme, écart signalé non bloquant, saisi à la main, repris du document suivant, alerte bloquante) ; page « qualité des données » |
| `Evenements` | `evenements.csv` (versionné, à la racine ; lien *raw* GitHub, source URL) | types ; une ligne par événement et par banque concernée : `id_evenement`, `date` (fin du trimestre concerné), `banque`, `indicateur`, `description`, `montant_mdt` (montant cité par le document), `fichier`, `page` ; annotations des graphiques (7.3, pages 3 et 9) |
| `Gabarits` (intermédiaire) | `gabarits.csv` (versionné ; connecteur Fichier, `CheminDonnees`, 11 colonnes) | banque, période, définitions des charges opératoires et des capitaux propres |
| `Definitions_Charges` | `Gabarits` | regroupement par `banque` et `definition_charges_operatoires` : `premier_trimestre` (minimum), `dernier_trimestre` (maximum) ; colonne conditionnelle `description` (texte en clair) ; info-bulle du coefficient publié et page « qualité des données » |
| `Definitions_Capitaux_Propres` | `Gabarits` | colonnes `banque`, `definition_capitaux_propres` (une ligne par banque, lignes distinctes) ; colonne conditionnelle avec le libellé en clair ; affichée dans la fiche banque à côté des capitaux propres trimestriels (5.2) |

### 5.2 Points d'attention

- **Valeur du trimestre seul** : les banques publient le trimestre seul (`trim_N`) et le cumul.
  Recalculer aussi `cumul(T) − cumul(T−1)` (même année, T > 1) et comparer : un écart signale
  une erreur d'extraction ou un retraitement.
- **Versions des chiffres** : une même période est publiée plusieurs fois. Colonne `version` :
  - `initiale` : valeur publiée dans le document du trimestre lui-même (colonnes `trim_N`, `cumul_N`) ;
  - `revisee_T<q>_N+1` : valeur du même trimestre redonnée en comparaison (colonnes `trim_N1`,
    `cumul_N1`) par le document du même trimestre de l'année suivante (ex. `revisee_T2_N+1`) ;
  - `revisee_31-12_T<q>_N+1` : **version révisée provisoire** du 31/12, lue dans la colonne
    « 31/12/N-1 » (`exercice_N1`, chiffres souvent audités) d'un document T1, T2 ou T3 de l'année
    suivante. Elle ne concerne que le **cumul annuel (cumul au T4)** des flux et les **soldes au 31/12**
    des stocks.

  Les banques retraitent parfois leurs chiffres entre les deux. Exemple constaté au T3 2025 :
  BIAT et UIB ont retraité leur premier semestre 2025 après la publication des indicateurs du T2
  (BIAT : alignement sur les états financiers intermédiaires ; UIB : chiffres « retraités pour les
  besoins de comparabilité »), et le trimestre T3 publié est calculé sur le semestre retraité
  (BIAT : PNB T3 publié 407,005 MDT ; cumul 9 mois − cumul S1 initial = 407,628 MDT ;
  cumul 9 mois − cumul S1 révisé = 407,005 MDT).

  **Règle** : la valeur d'analyse (`valeur_retenue`) suit cet ordre de priorité ; `source_valeur`
  donne la version exacte retenue :
  1. trimestres T1 à T3 (trimestre seul et cumul) : `revisee_T<q>_N+1` > `initiale` ;
  2. **cumul annuel (cumul au T4) et soldes au 31/12** : `revisee_T4_N+1` > `revisee_31-12` du
     document le plus récent de l'année suivante (T3 > T2 > T1) > `initiale` ;
  3. **T4 seul** (trimestre isolé) : `revisee_T4_N+1` > `initiale` ; la colonne 31/12/N-1 n'est
     **pas** utilisée (elle ne donne pas le trimestre seul). Le T4 seul reste donc en version
     initiale jusqu'à la publication du document T4 de l'année suivante.
  4. **Révisions : la version révisée est toujours retenue** (règle du 17/10/2026, la troisième ;
     voir plus bas pourquoi les deux premières ont été abandonnées). Les niveaux prennent la
     version révisée quand elle existe (priorité des règles 1 à 3), **avec ou sans note de
     retraitement** ; la note est gardée pour information (`mention_retraitement`, première ligne
     des 12 premières pages qui parle de « comparabilité », de « chiffres retraités » ou de
     « retraitement »). La révision est **qualifiée**, pas écartée :

     | Écart révisée − initiale, mesuré sur le **cumul** de la période | Statut (`statut_revision`) | Graphiques |
     |---|---|---|
     | ≤ 2 kDT (arrondi) | vide | — |
     | ≤ 2 % du cumul initial | `retraitement_mineur` | — |
     | > 2 % du cumul initial | `revision_importante` | `rupture_serie` = « oui », `detail_rupture` |

     - L'écart se mesure **sur le cumul** (solde pour un stock) et le statut vaut **pour le
       trimestre et le cumul** de la même période et de la même version : un trimestre seul,
       petit montant, dépasse vite 2 % sans que l'année change (BH, PNB du T4 2023 : −2,8 % sur le
       trimestre, −0,9 % sur l'année → `retraitement_mineur`). Le cumul n'est pas publié pour une
       période : on prend le trimestre.
     - Totaux concernés : PNB, produits d'exploitation bancaire, charges d'exploitation bancaire,
       charges opératoires, crédits, dépôts (même règle pour les indicateurs sans composantes :
       autres produits, portefeuille, emprunts, capitaux propres). Les **composantes** prennent le
       statut de leur total pour la même version ; total stable (sous l'arrondi) mais composante
       qui bouge → `reclassement`.
     - **Rupture de série** : marquée sur la période révisée elle-même (trimestre et cumul), pour
       annoter les graphiques (« PNB 2024 révisé de −8,5 % : 765,9 publié, 701,2 dans le document
       T4 2025 »). Elle ne change aucune valeur.
     - Seuil : constante `SEUIL_MATERIALITE = 0.02` dans le script ; c'est un choix d'analyse,
       pas une norme.
     - Exemples : BH, PNB 2024 = **701,188** MDT retenu (T4 2025, −8,5 % : `revision_importante`) ;
       UIB, PNB 2025 = 525,528 MDT (31/12 du T2 2026, +0,55 % : `retraitement_mineur`) ;
       BT, charges opératoires du T3 2020 = 26,011 MDT (T3 2021) au lieu des 12,076 publiés, chiffre
       incohérent avec ses composantes (voir plus bas, don au Fonds 1818).

     **Pourquoi les règles précédentes ont été abandonnées.** Règle 1 (17/10/2026) : garder la
     version initiale dès qu'un document annonçait un retraitement. Règle 2 (même jour) : la garder
     seulement si l'écart dépassait 2 % et que le document l'annonçait. La liste des 60 cas
     « changement de méthode » de la règle 2 a montré que garder l'initiale créait plus de
     problèmes qu'elle n'en réglait :
     - elle gardait des valeurs fausses : BT, charges opératoires du T3 2020, 12,076 MDT publié
       (le don au Fonds 1818 retiré du seul trimestre), corrigé à 26,011 un an plus tard ;
     - elle dépendait de la rédaction de la banque : la note « chiffres retraités pour les
       besoins de comparabilité » est une formule de routine (sept banques l'écrivent presque
       chaque année) et l'ATB retraite sans jamais l'écrire ;
     - elle mélangeait trimestre et cumul : le seuil appliqué mesure par mesure gardait l'initiale
       pour le trimestre et la révisée pour le cumul d'une même période ;
     - elle n'était plus utile : toutes les croissances viennent de `Variations_Comparables`
       (colonne N contre colonne N-1 d'un même document), qui ne dépend pas du choix des niveaux.

     **Causes communes constatées (charges opératoires 2020 et 2021).**
     - 2020 : le **don au Fonds national de lutte contre le Covid-19 (« Fonds 1818 »)**,
       comptabilisé dans les charges générales du premier semestre 2020 puis sorti des charges
       opératoires dans les chiffres 2020 redonnés en 2021 (et déjà dans le cumul du T4 2020). BT :
       ligne « Don Fds 1818 / Covid19 » de 11 350 kDT au premier semestre 2020 (PDF du T2 2020),
       charges générales du semestre révisées de −11,351 MDT ; BH : « cotisation de la banque pour la
       lutte contre le COVID-19 pour un montant de 11.4 MDT » et une taxe conjoncturelle de 0,8 MD,
       charges générales révisées de −12,426 MDT ; BNA : contribution de 11,4 MD au Fonds, charges
       générales révisées de −16,256 MDT (le reste n'est pas expliqué). Le T3 2020 de la BT
       (12,076 MDT, statut `ecart composantes`) est le trimestre dont on a retiré le don.
     - 2021 : l'**accord salarial APTBEF–FGBEF** (augmentation des salaires, indemnité de départ
       à la retraite portée de six à douze mois de salaire, notes BNA du T3 et du T4 2021, BT du
       T4 2021), comptabilisé en fin d'année et réparti sur le premier semestre 2021 dans les
       chiffres redonnés en 2022 : frais de personnel révisés de +6,680 MDT (BH), +12,766 MDT
       (BNA), +3,645 MDT (BT).
     - Attijari : pas de note sur le Fonds 1818 ; sa révision des charges opératoires 2020
       (+10,8 MDT pour l'année) vient du changement de contenu du T4 2021 (reste non détaillé
       ajouté, colonnes N-1 retraitées, voir `gabarits.csv`). Même cause pour le premier semestre
       2021 (document 2021T2, trouvé le 22/10/2026 sur tunis-stockexchange.com) : charges
       opératoires 114,937 MDT publiées, 143,703 dans le document 2022T2 (+25,0 %).

  **Document absent** (décision du 22/10/2026) : ordre de recherche sites BVMT/CMF → liste des
  indicateurs du CMF (`--rafraichir-liste-cmf` relit seulement les pages de tête, jusqu'à la
  première page déjà connue : la liste va du plus récent au plus ancien) → Bulletins Officiels.
  Statut du manifeste `non publié` quand, dans les 90 jours qui suivent la fin du trimestre, le
  document n'est pas aux adresses habituelles (essayées dans le même lancement) et qu'aucun PDF de
  la liste ne porte dans son nom la banque, l'année et le rang du trimestre (pas encore déposé) ;
  `manquant` (introuvable) sinon : document listé mais qui n'est pas le bon, ou trimestre ancien
  absent des trois sources. La liste seule ne suffit pas : le 22/10/2026, le T3 2026 de AB, ATB,
  BIAT, BTE et UBCI était déjà en ligne au CMF sous son nom habituel mais pas encore dans la
  liste. Dans `controle_extraction.csv` : `non publié` ou `pdf manquant`. Derniers recours, à la
  main (22/10/2026) : le nouveau site de la Bourse (`tunis-stockexchange.com/publications-societes`,
  filtres société et « Indicateurs d'activité trimestriels » : Attijari 2021T2) et le site de la
  banque (`wifakbank.com/indicateurs-activite`, 40 PDF de 2016 à 2025 : Wifak 2022T3). Les 336
  documents attendus sont trouvés ; enregistrés dans le manifeste avec leur adresse (source `site`).

  **Document illisible** : un tableau publié en image (BH 2019T4, page 1 : 252 caractères de
  texte, 2 images) a le statut `illisible (image)` dans `controle_extraction.csv` ; sa version
  initiale figure dans `indicateurs_versions.csv` sans valeur, statut `illisible (image)`, et la
  valeur retenue vient des colonnes N-1 du document de l'année suivante (BH 2020T4, « (*) Chiffres
  retraités » : PNB 2019 = 492,929 MDT, PNB du T4 2019 = 156,644 MDT). Pas de saisie manuelle tant
  que le document suivant donne les chiffres. Seuil de détection : page avec images et moins de
  1 000 caractères de texte. **BTE** : 13 documents dans ce cas (2020T1 à 2023T4, sauf 2022T2,
  2023T1 et 2023T3), **tous saisis à la main** : d'abord ceux que le document suivant ne reprend
  pas (2020T1 à 2020T4, 2021T1 et 2021T3, 17/10/2026 ; T4 seuls 2021T4 et 2022T4, 22/10/2026),
  puis les 5 autres (2021T2, 2022T1, 2022T3, 2023T2, 2023T4, 22/10/2026). Raison de la saisie
  complète : la colonne N-1 d'un document en image peut publier une correction que rien d'autre
  ne donne. BTE 2022T1 publie le T1 2021 « données corrigées » (charges opératoires 8 120 au lieu
  de 10 906, frais de personnel 5 825 au lieu de 8 786) ; sans lui, les frais de personnel du
  T2 2021 de BTE_2022T2 (11 196, soit 9 097 publiés à l'origine + 2 099 de révision, aussi dans le
  S1) semblaient faux. Le site de la BTE (`bte.com.tn`, rubrique « Publications et rapports ») ne
  publie que les rapports annuels et ceux des commissaires aux comptes, pas les indicateurs
  trimestriels (vérifié le 22/10/2026, robots.txt respecté).

  **Saisie manuelle** (`saisies_manuelles.csv`, versionné, à la racine) : seulement pour les
  documents illisibles que le document suivant ne reprend pas, et seulement pour les indicateurs
  du rapport (PNB, produits et charges d'exploitation bancaire, frais de personnel, charges
  générales, charges opératoires, crédits, dépôts), toutes les colonnes du tableau (N, N-1,
  31/12/N-1). Chaque valeur porte `fichier`, `page` et `verification` : « lecture image +
  contrôles de cohérence » (relevé sur l'image du tableau rendue à 200–220 dpi), ou « vérifié par
  Ahmed » quand l'utilisateur l'a contrôlée lui-même (`scripts/verification_saisie.py preparer`
  puis `reporter`). À l'extraction, la saisie remplace le document illisible (statut `saisie
  manuelle` dans `controle_extraction.csv`, colonnes `source` = « saisie manuelle » et
  `verification` dans les données) et passe les contrôles de l'extraction plus un contrôle strict
  (produits − charges = PNB à 2 kDT près dans chaque colonne) ; une alerte la met en
  `a verifier`. **Composantes** (23/10/2026, décision de l'utilisateur) : pour BTE T4 2021 et
  T4 2022, intérêts perçus et encourus, commissions en produits et encourues, revenus du
  portefeuille et autres produits du trimestre seul, colonne N et colonne N-1 du document suivant
  (versions révisées, 2022T4 et 2023T4), plus les autres produits de 2023T4 (0 publié) : 26 valeurs.
  Contrôle strict ajouté : intérêts encourus + commissions encourues = charges d'exploitation ;
  intérêts + commissions + portefeuille au plus égal aux produits pour BTE, qui publie ses gains
  nets sur opérations de change sur une ligne à part sans code (reste vérifié sur l'image : égal
  aux gains de change à 1 kDT près). Puis (23/10/2026, décision de l'utilisateur) les mêmes
  composantes pour 2020T1 à 2020T4, 2021T1 et 2021T3 (toutes les colonnes du tableau) et les colonnes
  N-1 de 2021T2, 2021T4, 2022T1 et 2022T3 (versions révisées) : 216 valeurs, mêmes contrôles (37
  colonnes, reste des produits = gains de change à 1 kDT près, charges exactes). Avec les versions
  retenues, la somme des 4 trimestres égale le cumul annuel en 2020 et 2021 pour chaque composante.
  BTE 2021T2 révise le T2 2020 : commissions encourues 5 515 → 5 kDT, intérêts encourus 8 925 →
  14 468 kDT (reclassement d'environ 5,5 MDT, charges totales presque inchangées). BTE 2020T4 et
  2021T2 ne publient pas de ligne « autres produits » (case vide, non saisie).
  Contrôles faits pendant la saisie BTE (13 documents, 436 valeurs, aucune erreur) :
  produits − charges = PNB, charges opératoires = frais de personnel + charges générales,
  colonne « Variation montant » du PDF = cumul N − cumul N-1, dépôts = somme des quatre
  catégories ; les trimestres 2020T3 sont confirmés par la colonne N-1 du document 2021T3.
  2022T4 : trimestre saisi = cumul annuel saisi − cumul de 9 mois retenu, exactement, pour les six
  flux. 2021T4 : totaux à 0,02 MDT près du cumul annuel − cumul de 9 mois publié au T3 2021, mais
  frais de personnel (+0,58) et charges générales (−0,60) se compensent : reclassement de la
  banque en cours d'année (image relue : 10 607 + 3 615 = 14 222), signalé par le statut
  `ecart trimestre/cumul`. Les colonnes N-1 de ces documents (T4 2020, T4 2021, « données
  corrigées ») deviennent les versions révisées de BTE 2020T4 et 2021T4.
  BTE 2020T2 : 36 valeurs relues indépendamment, `verification` = « vérifié par Ahmed Ben Arfa ».
  Avec les 13 documents saisis, la somme des trimestres BTE retrouve le cumul annuel en 2021 et
  2022 ; 2020 : à 0,019 MDT près sur les charges opératoires (T1 2020 corrigé dans 2021T1 mais
  pas dans le cumul du S1 de 2021T2), statut `rupture de série`.
  **Saisie partielle** d'un document lisible : quand quelques valeurs sont illisibles dans le texte
  du PDF (STB 2026T2 : revenus du portefeuille du trimestre superposés à leur libellé ; l'extraction
  laissait le T2 2026 vide et lisait 893 522 au lieu de 115 893 522 pour le T2 2025), les valeurs
  saisies remplacent ou complètent celles extraites (colonne `source` = « saisie manuelle » sur ces
  lignes), le document garde son statut, et le contrôle strict ajoute : intérêts + commissions +
  revenus du portefeuille = produits dans chaque colonne.

  **Valeur non disponible** : quand un document est illisible et qu'aucun autre ne reprend une
  mesure (jusqu'au 22/10/2026 : BTE, T4 seul de 2021 et de 2022 et autres produits du T4 2023 ;
  plus aucun cas depuis la saisie des documents BTE en image),
  `indicateurs_versions.csv` porte une ligne `statut_revision` = « non disponible (image) »,
  sans valeur ni valeur retenue. Elle apparaît dans `Revisions` (page « qualité des données »),
  jamais dans `Fait_Indicateurs` : la valeur reste vide dans les graphiques, jamais à zéro (aucune
  mesure DAX ne doit remplacer un vide par 0, pas de `+ 0` ni de `COALESCE ( …, 0 )` sur les
  valeurs ; le contrôle annuel saute ces années).

  **Trimestres incomplets pour le secteur** (valeur retenue présente pour chaque banque qui publie
  l'indicateur ; vérifié le 23/10/2026 sur `indicateurs_versions.csv`, 28 trimestres de 2019T4 à
  2026T3) :
  - **complets (28/28)**, trimestre seul et cumul : PNB, produits et charges d'exploitation
    bancaire, charges opératoires, frais de personnel, charges générales ; crédits et dépôts ;
  - **complets (28/28) depuis la saisie des composantes BTE** : intérêts perçus et encourus,
    commissions en produits et encourues, revenus du portefeuille (donc marge d'intérêts et marge
    sur commissions) ;
  - **22/28** : portefeuille-titres et portefeuille d'investissement, dépôts à vue et d'épargne,
    emprunts : il manque **BTE 2020T1 à 2020T4, 2021T1 et 2021T3** (documents en image, détail du
    bilan non saisi) ;
  - capitaux propres trimestriels : 20/28 (BTE, mêmes trimestres plus 2021T4 et 2022T4), fiche
    banque seulement (les comparaisons utilisent les capitaux propres du bilan) ;
  - jamais complets, publiés par une partie des banques seulement : dotations aux amortissements
    (2 banques), dépôts à terme (5), autres dépôts (2) ; portefeuille commercial (BT et BTE
    absents à plusieurs dates) ; autres produits d'exploitation (aucune valeur pour Wifak, BTE
    imprime « - » à plusieurs dates : vérifié pour 2026T2 et 2026T3) : hors indicateurs du rapport.
  Le total du secteur d'un indicateur n'est calculé que pour les trimestres complets de cet
  indicateur (mesure « nombre de banques présentes »).

  Les périodes de la dernière année publiée (2026) sont en version initiale. Toutes les versions
  restent dans `indicateurs_versions.csv` pour la traçabilité (colonnes `fichier`, `page`), avec
  `ecart_vs_retenue` = valeur de la version − valeur retenue.

  **Contrôle annuel** (`controle_annuel.csv`, refait à chaque extraction) : somme des 4 trimestres
  retenus comparée au cumul T4 retenu, pour le PNB, les produits, les charges d'exploitation
  bancaire et les charges opératoires. Tolérance : 2 milliers de dinars (arrondi des banques qui
  publient en milliers). Statuts :
  - `ok` ;
  - `en attente de révision` : le cumul retenu est la version provisoire 31/12 alors que le T4 seul
    est encore en version initiale ; l'écart disparaîtra (ou se confirmera) avec le document T4
    de l'année suivante. Ce n'est pas une erreur ;
  - `rupture de série` : l'année contient une `revision_importante` (règle 4) et la somme des
    trimestres retenus ne retrouve pas le cumul. Signalé, pas corrigé ;
  - `ecart` : examiné (étape 4c) ; la cause de chacun est dans `docs/ecarts_annuels.csv`.

  **Causes des écarts annuels** (étape 4c, 22/10/2026 ; 29 écarts, 22 après la saisie des documents
  BTE en image, de 0,003 à 3,441 MDT). Méthode :
  pour chaque écart, l'origine de chaque trimestre retenu et du cumul retenu, puis, document par
  document de l'année suivante (et de l'année elle-même), « cumul − trimestre − cumul précédent » :
  le document où ce reste n'est pas nul est la source de l'écart ; chaque nombre en cause a été
  retrouvé dans le texte de la page ou sur son image. Résultat :

  | Catégorie | Écarts | Cas |
  |---|---|---|
  | retraitement de la banque | 11 | la banque révise un trimestre passé dans le cumul seulement (ou dans le trimestre seulement) : ATB 2021, BH 2023, BT 2023, BTE 2024, STB 2022, UBCI 2021 (2), UBCI 2024, UIB 2020, Wifak 2023 (2) |
  | erreur dans le document de la banque | 7 | colonnes déjà exclues : Wifak 2022 (4, colonne T4 2022 recopiée du T3), UIB 2022 (3, colonne T2 2022 incohérente) |
  | reclassement | 3 | UIB 2024 : 0,677 MDT entre commissions encourues et charges générales (note (1) de UIB_2025T3), appliqué au trimestre et pas au cumul |
  | arrondi | 1 | Attijari 2021, PNB : 3 kDT (chiffres en milliers) |
  | erreur d'extraction | 0 | — |

  Les 7 écarts BTE de 2020 et 2021 (dont les charges opératoires 2021, +2,765 MDT, d'abord classées
  « erreur dans le document de la banque ») ont disparu avec la saisie des documents BTE en image :
  ils venaient de corrections publiées dans des colonnes N-1 en image (T1 2021 dans BTE 2022T1,
  S1 2020 dans BTE 2021T2).

  Aucune valeur n'est corrigée : ce sont des chiffres publiés par les banques. Un test vérifie que
  chaque `ecart` du contrôle annuel a sa cause dans `docs/ecarts_annuels.csv` et qu'aucune erreur
  d'extraction n'y reste sans correction.

  Vérifié sur 2025 : avec les trimestres retenus, la somme des 4 trimestres égale le cumul T4
  **initial** exactement pour BIAT ; le cumul retenu étant le 31/12 provisoire (document T2 2026),
  les 4 contrôles BIAT 2025 sont `en attente de révision` (ex. charges opératoires : 723,988 MDT en
  initial, 711,102 MDT au 31/12 provisoire). UIB 2025 : de même `en attente de révision` (PNB :
  522,651 MDT initial, 525,528 MDT au 31/12 provisoire, `retraitement_mineur`).

  **Nature de chaque révision** (`statut_revision` dans `indicateurs_versions.csv` ; chaque version
  révisée comparée à l'initiale, règle 4 ; la version initiale remplacée prend la nature de la
  version retenue ; tolérance d'arrondi : 2 milliers de dinars) :
  - `retraitement_mineur` : cumul révisé de 2 % au plus (ex. PNB UIB 2025 +0,55 %) ;
  - `revision_importante` : cumul révisé de plus de 2 % (ex. ATB, PNB 2019 : 252,236 → 239,420,
    −5,1 % ; BH, PNB 2024 −8,5 %) → rupture de série marquée ;
  - `reclassement` : le total est stable (sous la tolérance) mais des composantes bougent
    (ex. BIAT 2025 : −0,401 MDT d'intérêts, +0,401 de commissions) → la composante prend
    **la même version que son total**, l'écart est signalé ;
  - vide : écart sous la tolérance ;
  - `exclue (capitaux propres, 31/12 provisoire)` : voir ci-dessous ;
  - `exclue (colonne incohérente : …)` et `exclue (exclusion écrite : …)` : colonne N-1 non retenue,
    voir ci-dessous ;
  - `illisible (image)` : version initiale d'un document dont le tableau est une image.
  Totaux et composantes : produits = intérêts + commissions + revenus du portefeuille ;
  charges d'exploitation = intérêts encourus + commissions encourues ; PNB = produits − charges ;
  charges opératoires = composantes publiées (voir 7.2, coefficient d'exploitation) ; dépôts = à vue +
  épargne + à terme + autres ; portefeuille = commercial + investissement.

  **Capitaux propres : règle fixe, toutes banques.** La colonne 31/12 provisoire n'est jamais
  retenue pour `CAP_PROPRES` : sa définition change d'un document à l'autre (BIAT au 31/12/2025 :
  1 982,5 dans le document T4 2025, résultat non inclus ; 2 367,8 dans le T1 2026, « avant
  affectation du résultat » ; 2 123,0 dans le T2 2026, « après affectation »). La série reste
  homogène : « **Capitaux propres hors résultat de la période** », en version initiale ou
  `revisee_T<q>_N+1`. La définition annoncée par les notes du document est conservée à titre
  d'information (`note_definition` : « avant affectation du résultat », « après affectation du
  résultat », « résultat de la période non inclus »). Le ROE et le ROA n'utilisent pas cet
  indicateur mais les capitaux propres des états financiers (7.7).

  **Usage dans Power BI (décision du 19/10/2026).** La référence pour **toutes les comparaisons
  entre banques** (classements, parts, totaux du secteur, ROE, ratios rapportés aux capitaux
  propres) est le total des capitaux propres du **bilan** (`CAP_PROPRES_EF`, états financiers,
  30/06 et 31/12, résultat inclus). Les capitaux propres trimestriels (`CAP_PROPRES`) ne servent
  qu'à la **fiche banque** (page 7), affichés avec la définition de la banque. Cette définition
  est dans la colonne `definition_capitaux_propres` de `gabarits.csv` (valeurs permises :
  `DEFINITIONS_CAP_PROPRES` dans `collecte_banques.py`, contrôlées au chargement). Elle a été
  établie par recoupement avec les états financiers à toutes les dates (7.7, point 4) :

  | Définition | Banques | Recoupement |
  |---|---|---|
  | `hors resultat de la periode` | BNA, BH, BT, STB, TJARI, UBCI, UIB, WIB | trimestriel = capitaux propres du bilan − résultat net de la période |
  | `resultat inclus` | ATB, BTE | trimestriel = capitaux propres du bilan |
  | `hors resultat, apres affectation au 31/12` | AB, BIAT | 30/06 : hors résultat ; 31/12 : après affectation du résultat de l'exercice (réserves augmentées, dividendes déduits), non comparable au bilan (écart de −43 à −117 MDT de 2020 à 2024) |

  Dates qui ne suivent pas la définition de leur banque (au 19/10/2026, laissées telles que
  publiées, signalées par le recoupement) : AB et BIAT au 31/12/2019 (résultat inclus) ;
  WIB 30/06/2020 (résultat inclus) ; TJARI 30/06/2021 (valeur reprise de la colonne N-1 du
  T2 2022 : sans le résultat 2020 non encore affecté, écart de 131,712 MDT = résultat 2020) ;
  STB 30/06/2022 et 31/12/2023 (écart = modifications comptables, +11,506 et +18,835) ; écarts non
  expliqués : ATB 31/12/2025 (−35,5) et 30/06/2026 (−4,3), BNA 31/12/2025 (+17,2), BTE 31/12/2019
  (−3,0), 30/06/2022 (−0,7) et 31/12/2025 (+3,2), BIAT 30/06/2025 (−1,3) ; écarts de moins de
  1 MDT aux dates les plus récentes (indicateurs provisoires publiés avant l'audit ou la revue
  limitée).

  **Colonnes N-1 non retenues (décision du 17/10/2026).** Une colonne de comparaison
  (`trim_N1`, `cumul_N1`, `exercice_N1`) fausse dans le document de la banque ne devient jamais
  la valeur retenue, pour aucun indicateur ; ses valeurs restent dans `indicateurs_versions.csv`
  avec le statut `exclue (…)` et la raison, et aucune variation n'est calculée avec elle
  (`variations_comparables.csv`). Deux sources :
  - règle automatique : produits − charges d'exploitation ≠ PNB (écart de plus de 2 %) dans la
    colonne. Seul cas sur les 12 banques au 17/10/2026 : UIB 2023T2, colonne T2 2022 (charges
    d'exploitation 125 105 = cumul du semestre ; UIB_2022T2.pdf publie 63 933) ;
  - exclusion écrite dans `exclusions_colonnes.csv` (versionné : banque, trimestre du document,
    colonne, raison, fichier, page), pour une erreur que les contrôles ne voient pas. Seul cas :
    WIB 2023T4, colonne T4 2022 recopiée du T3 2022 (13 indicateurs identiques à ceux de
    WIB_2023T3_bulletin.pdf, PNB 14 455 ; WIB_2022T4_bulletin.pdf publie 17 536).
  La période garde alors la version suivante dans l'ordre de priorité (ici la version initiale).
  Effet de bord connu : une vraie révision contenue dans la colonne exclue est perdue avec elle
  (UIB, PNB du T2 2022 retraité de +0,170 MDT) ; le contrôle annuel 2022 de l'UIB signale l'écart
  (somme des trimestres ≠ cumul révisé, de 0,04 à 0,17 MDT).

  **Comparaison des deux révisions du 31/12** : quand le document T4 de l'année suivante existe,
  il devient la source retenue et la version `revisee_31-12_…` reste comme ligne de comparaison ;
  son écart (`ecart_vs_retenue`) apparaît dans la table `Revisions` et est listé à l'extraction.

  Points à connaître :
  - si le document initial manque mais qu'une version révisée existe, la période n'a que la
    version révisée (valeur réellement publiée, rien n'est estimé) ;
  - la version révisée d'un trimestre n'est pas toujours cohérente avec les versions initiales
    des trimestres voisins : en mélangeant versions, la somme des trimestres peut différer du
    cumul ; on ne corrige pas, on signale.
- **Années et cumuls (flux)** : chiffres annuels et depuis le début de l'année = **cumul**
  (`Valeur_Cumul`, valeur retenue ; l'année = cumul au T4), jamais la somme des trimestres.
  **Analyse trimestrielle** (niveaux, T/T) : **trimestre** (`Valeur_Trim`, valeur retenue).
- **Variations sur un an** (PNB, charges, crédits, dépôts… ; trimestre, cumul ou solde) :
  calculées **à l'intérieur d'un même document**, colonne N contre colonne N-1
  (`variations_comparables.csv` → `Variations_Comparables`), jamais en rapprochant deux documents.
  Les deux chiffres sont publiés ensemble, dans la même méthode : la variation reste juste quand la
  banque retraite N-1 (BH 2025 : PNB 681,479 contre 701,188 retraité, −2,8 %, comme la colonne
  « Var » du PDF ; avec le 765,932 publié un an plus tôt, on obtiendrait −11,0 %).
- **Contrôle « écart trimestre/cumul »** : dans `controle_extraction.csv`, statut
  `ecart trimestre/cumul` quand le trimestre initial publié diffère de plus de 0,1 % de
  « cumul initial du trimestre − cumul initial du trimestre précédent » (PNB, produits, charges
  d'exploitation bancaire, charges opératoires). La page « Qualité des données » liste ces cas,
  ainsi que les révisions (`Revisions`, écart révisée − initiale en MDT).
- **Paramètres** : un paramètre Power Query `CheminDonnees` pour que le dossier soit modifiable.
- **Nommage** : étapes renommées en français (« Types modifiés », « Filtre colonnes utiles »…).
- Désactiver le chargement des requêtes intermédiaires.

### 5.3 Actionnariat des banques (`donnees_reference/banques.xlsx`)

Fichier versionné, rempli à partir de sources officielles uniquement (22/10/2026) : fiche émetteur de
la Bourse de Tunis (`tunis-stockexchange.com/informations-<banque>`, rubrique 4 « Principaux
actionnaires », date de l'AGO), états financiers annuels (note sur la structure du capital, conventions
avec les parties liées), rapports annuels des banques. Colonnes : `code_banque`, `nom`,
`actionnaire_reference`, `part_capital_pct`, `actionnariat`, `groupe`, `date_reference` (date de la
source), `source`, `page`, `date_debut`, `date_fin` (période, vides quand l'actionnaire de référence n'a pas
changé de 2019 à 2026), `remarque`. Une valeur sans source reste vide et la remarque le dit.

**Règle de classement** (`actionnariat`), fondée sur le **contrôle** de la banque (décision du
22/10/2026) :
- **public** : contrôle par l'État et les entreprises publiques (ensemble plus de 50 % du capital ou
  des droits de vote) ;
- **groupe étranger** : contrôle par un groupe bancaire ou financier étranger (majorité du capital ou
  des droits de vote, ou contrôle écrit dans une source) ;
- **mixte** : contrôle conjoint d'actionnaires publics tunisiens et d'un actionnaire étranger (droits de
  vote partagés, aucun ne contrôlant seul) ;
- **privé sans contrôle étranger** : tous les autres cas, y compris quand un actionnaire étranger est le
  premier actionnaire sans contrôler la banque.

Classement et preuve du contrôle :

| Banque | Actionnariat | Preuve |
|---|---|---|
| BNA | public | actionnaires publics 50,23 % (BNA_EF_2019-12.pdf p. 5, BNA_EF_2025-12_cmf.pdf p. 6) |
| BH | public | État 33,37 % + entreprises publiques 22,26 % = 55,63 % (rapport annuel BH 2025, p. 19) |
| STB | public | État 71,56 % + entreprises publiques 11,85 % (STB_EF_2025-12_cmf.pdf p. 6 ; 2019 : p. 5) |
| ATB | groupe étranger | Arab Bank PLC 64,24 % (rapport annuel 2019 p. 14 ; fiche Bourse 2026) |
| Attijari | groupe étranger | Attijariwafa bank, via Andalucarthage Holding (57,21 %), « détient la majorité des droits de vote et assure le contrôle » (plaquette financière d'avril 2022, p. 1) |
| UIB | groupe étranger | Société Générale 52,34 %, « société mère » (UIB_EF_2020-12.pdf p. 38) |
| UBCI jusqu'au 15/03/2021 | groupe étranger | BNP Paribas 50,085 % (UBCI_EF_2019-12.pdf p. 9) |
| BTE | mixte | État (+ La Poste depuis 2024) et ADIA : 50 % des droits de vote chacun (BTE_EF_2019-12.pdf p. 25, BTE_EF_2024-12.pdf p. 32) |
| AB, BIAT, UBCI depuis le 16/03/2021 | privé sans contrôle étranger | premiers actionnaires tunisiens (COMAR 28,76 %, groupe Mabrouk 38,75 %, groupe Carte 39,86 %) |
| BT | privé sans contrôle étranger | BFCM 35,33 %, « influence notable » seulement (BT_EF_2019-12.pdf p. 65) |
| Wifak | privé sans contrôle étranger | ICD 30 % sans majorité jusqu'en 2021, puis groupe Ben Ayed (39,86 %) |

**Changements d'actionnaire de référence entre 2019 et 2026** (une ligne par période) :
- UBCI : BNP Paribas (50,085 %, groupe étranger) jusqu'à la cession de 39 % au groupe Carte, réalisation
  annoncée le 16/03/2021 (UBCI_EF_2020-12.pdf p. 5) ; ensuite groupe Carte (39,86 %, privé sans contrôle
  étranger) : seul changement de catégorie ;
- Wifak : ICD (30 %) jusqu'au 31/12/2021, puis groupe Ben Ayed (32,9 % « début 2022 », 01/01/2022 retenu,
  39,86 % depuis 2023 ; rapports annuels 2021 p. 13, 2022 p. 16, 2023 p. 22) ; catégorie inchangée ;
- BTE : État tunisien et ADIA à parts égales (38,9 % chacun) jusqu'au 30/06/2024 ; augmentation de capital
  décidée par l'AGE du 30/04/2024 (BTE_EF_2024-06.pdf p. 32), réalisée au second semestre 2024 : ADIA
  40,80 %, État 32,19 %, La Poste tunisienne 8,62 % (BTE_EF_2024-12.pdf p. 32) ; catégorie inchangée
  (mixte). **Date exacte inconnue** (aucune dans les notes des états financiers de 2024 et 2025) : la
  seconde période commence au 01/07/2024 pour que les périodes se suivent (décision du 23/10/2026).
  Indice non confirmé : capitaux propres trimestriels 41,704 MDT au 30/06/2024 et 62,764 MDT au
  30/09/2024 (BTE_2025T2.pdf et BTE_2025T3.pdf p. 1), hausse proche des 18,744 MDT de capital.

Contrôle : `tests/test_actionnariat.py` vérifie que, pour chaque banque, les périodes se suivent sans
trou ni chevauchement du 01/01/2019 à aujourd'hui, et que chaque ligne a une catégorie de la règle,
une source et une page.

Limites : l'actionnariat de BH en 2019 n'a pas été trouvé (seul le rapport 2025 est en ligne) ; la part
d'UIB et l'actionnaire de référence de BIAT en 2019 ne sont pas relevés (contrôle et catégorie confirmés
par d'autres sources, voir la colonne `remarque`).

Dans Power Query, l'actionnariat d'une banque à une date est celui de la ligne dont la période couvre
cette date : fonction personnalisée `Actionnariat_A_La_Date` (périodes, banque, date), appelée par
`Fait_Indicateurs`, `Variations_Comparables` et `Fait_Etats_Financiers` pour remplir leur colonne
`Segment_Actionnariat` ; `Dim_Banque` porte l'actionnariat actuel.

## 6. Modèle en étoile

Tables de faits :

- `Fait_Indicateurs` : banque, date_arrete, code_indicateur, Valeur_Trim, Valeur_Cumul
  (valeurs retenues, voir 5.2), Source_Trim, Source_Cumul (« initiale », « revisee_T2_N+1 »,
  « revisee_31-12_T2_N+1 »…), Rupture_Trim, Rupture_Cumul (« oui » sur une période révisée de plus
  de 2 % sur le cumul)
- `Variations_Comparables` : banque, date_arrete, code_indicateur, mesure (`trim` / `cumul`),
  valeur_N, valeur_N1 (même document), variation_pct, fichier, page, mention_retraitement ; source
  de toutes les variations sur un an
- `Evenements` (annotations) : id_evenement, date, banque, indicateur, description, montant_mdt,
  fichier, page
- `Revisions` (page qualité) : banque, date_arrete, code_indicateur, mesure, version, valeur_mdt,
  valeur_retenue, source_valeur, Ecart_MDT
- `Fait_Cours` : ticker, date, cloture, volume, rendement

Dimensions :

- `Dim_Date` (DAX) : une ligne par jour, de 2019-01-01 à 2026-12-31
- `Dim_Banque` : code, nom, ticker, actionnariat (public / groupe étranger / mixte / privé sans contrôle étranger), groupe
- `Banques_Actionnariat` (depuis `donnees_reference/banques.xlsx`) : une ligne par banque et par période d'actionnaire de référence (`date_debut`, `date_fin`), avec la source et la page
- `Dim_Indicateur` : code, libellé, catégorie (activité, résultat, bilan), nature (flux / stock), ordre

Relations (1 → plusieurs, filtre simple) :

- `Dim_Date[Date]` → `Fait_Indicateurs[date_arrete]`, `Variations_Comparables[date_arrete]`,
  `Revisions[date_arrete]` et `Fait_Cours[date]`
- `Dim_Banque[code_banque]` → `Fait_Indicateurs[banque]`, `Variations_Comparables[banque]` et `Revisions[banque]`
- `Dim_Banque[code_banque]` → `Fait_Cours[banque]` (23/10/2026 : par le code de la banque, présent dans
  `Fait_Cours`, au lieu de `ticker_bvmt` → `ticker` : une même clé partout)
- `Dim_Indicateur[code_indicateur]` → `Fait_Indicateurs[code_indicateur]` et `Variations_Comparables[code_indicateur]`
- `Dim_Date[Date]` → `Evenements[date]`, `Dim_Banque[code_banque]` → `Evenements[banque]`,
  `Dim_Indicateur[code_indicateur]` → `Evenements[indicateur]` (annotations filtrées comme les courbes).
  Un événement peut porter sur un code des états financiers (`RES_NET`, `TOTAL_ACTIF`,
  `CAP_PROPRES_EF` : ex. `MORATOIRE_COVID_UIB` au 30/06/2020, résultat net retraité de
  −41,182 à 17,912 MDT) : ces 3 codes sont ajoutés à `Dim_Indicateur` dans Power Query (ajout de
  lignes, nature `flux` pour le résultat, `stock` pour les deux autres) pour que la relation
  garde l'annotation sur la page « Rentabilité »
- Liste complète écrite dans le modèle (23/10/2026, 28 relations, `relationships.tmdl`) : `Dim_Date` vers
  les dates de `Fait_Indicateurs`, `Variations_Comparables`, `Fait_Etats_Financiers`, `Revisions`,
  `Revisions_Etats_Financiers`, `Controle`, `Controle_Annuel`, `Evenements`, `Fait_Cours` ; `Dim_Banque` vers
  la banque de ces 9 tables, de `Definitions_Charges`, `Definitions_Capitaux_Propres` et
  `Banques_Actionnariat` ; `Dim_Indicateur` vers `Fait_Indicateurs`, `Variations_Comparables`, `Revisions`,
  `Controle_Annuel`, `Evenements`, `Fait_Etats_Financiers[code]`, `Revisions_Etats_Financiers[code]`

### Table de dates

```dax
Dim_Date =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2019, 1, 1 ), DATE ( 2026, 12, 31 ) ),
    "Annee", YEAR ( [Date] ),
    "Trimestre", "T" & QUARTER ( [Date] ),
    "Annee_Trimestre", YEAR ( [Date] ) & "T" & QUARTER ( [Date] ),   -- « 2024T3 », format des faits
    "Cle_Trimestre", YEAR ( [Date] ) * 10 + QUARTER ( [Date] ),
    "Fin_Trimestre", [Date] = EOMONTH ( [Date], 0 ) && MOD ( MONTH ( [Date] ), 3 ) = 0,
    "Periode",
        SWITCH (
            TRUE (),
            [Date] < DATE ( 2020, 3, 1 ), "Avant Covid",
            [Date] < DATE ( 2022, 1, 1 ), "Covid",
            "Après Covid"
        ),
    "Ordre_Periode",
        SWITCH (
            TRUE (),
            [Date] < DATE ( 2020, 3, 1 ), 1,
            [Date] < DATE ( 2022, 1, 1 ), 2,
            3
        )
)
```

À marquer comme table de dates ; trier `Annee_Trimestre` par `Cle_Trimestre` et `Periode` par
`Ordre_Periode` (sinon « Après Covid » viendrait en premier) ; masquer les deux colonnes de tri.
Code du modèle : `dax/Dim_Date.dax` (23/10/2026 : libellé « 2024T3 » au format des faits, au lieu de
« 2024-T3 »). Colonne `Choix_Trimestre` (au lieu de `EstDernierTrimestre`) : « Dernier trimestre complet »
pour le dernier trimestre où les 12 banques ont publié PNB, crédits et dépôts, sinon le libellé du trimestre ;
triée par `Ordre_Choix_Trimestre` (masquée). Sert de filtre par défaut des pages (7.4).
Colonne calculée utile : `EstDernierTrimestre` (le dernier trimestre présent dans les faits).

## 7. Mesures DAX

### 7.1 Bases

```dax
-- Valeur_Trim et Valeur_Cumul sont les valeurs retenues : révisée si elle existe, sinon initiale (5.2)
-- Garde-fou (23/10/2026) : vide si la sélection couvre plusieurs dates d'arrêté (jamais la somme de
-- plusieurs trimestres ni de plusieurs cumuls ou soldes) ; code exact : dax/mesures.dax
Valeur Trim  = IF ( DISTINCTCOUNT ( Fait_Indicateurs[date_arrete] ) = 1, SUM ( Fait_Indicateurs[Valeur_Trim] ) )
Valeur Cumul = IF ( DISTINCTCOUNT ( Fait_Indicateurs[date_arrete] ) = 1, SUM ( Fait_Indicateurs[Valeur_Cumul] ) )

-- Flux, analyse trimestrielle : trimestre publié (voir 5.2, règle trimestre / cumul)
PNB              = CALCULATE ( [Valeur Trim], Dim_Indicateur[code_indicateur] = "PNB" )
-- Flux, année et depuis le début de l'année : cumul publié au dernier trimestre de la sélection,
-- jamais la somme des trimestres (les retraitements en cours d'année la rendent fausse)
PNB cumul brut   = CALCULATE ( [Valeur Cumul], Dim_Indicateur[code_indicateur] = "PNB" )
PNB depuis debut annee = CALCULATE ( [PNB cumul brut], LASTNONBLANK ( Dim_Date[Date], [PNB cumul brut] ) )
PNB annuel       = CALCULATE ( [PNB cumul brut], Dim_Date[Trimestre] = "T4" )   -- cumul au 31/12
Charges operatoires = CALCULATE ( [Valeur Trim], Dim_Indicateur[code_indicateur] = "CHG_OPER" )
Frais personnel  = CALCULATE ( [Valeur Trim], Dim_Indicateur[code_indicateur] = "FRAIS_PERS" )
Charges generales = CALCULATE ( [Valeur Trim], Dim_Indicateur[code_indicateur] = "CHG_GEN" )
-- vide si l'un des deux termes manque (en DAX, vide − x = −x : un vide serait lu comme zéro)
Marge interets   =
    VAR Percus = CALCULATE ( [Valeur Trim], Dim_Indicateur[code_indicateur] = "INT_PERCUS" )
    VAR Encourus = CALCULATE ( [Valeur Trim], Dim_Indicateur[code_indicateur] = "INT_ENCOURUS" )
    RETURN IF ( NOT ISBLANK ( Percus ) && NOT ISBLANK ( Encourus ), Percus - Encourus )
Marge commissions = -- même modèle avec COMM_PROD et COMM_CHG
Revenus portefeuille = CALCULATE ( [Valeur Trim], Dim_Indicateur[code_indicateur] = "REV_PORTEF" )

-- Stocks : dernière valeur disponible de la période, jamais la somme
Credits brut = CALCULATE ( [Valeur Cumul], Dim_Indicateur[code_indicateur] = "CREDITS" )
Credits      = CALCULATE ( [Credits brut], LASTNONBLANK ( Dim_Date[Date], [Credits brut] ) )
Depots brut  = CALCULATE ( [Valeur Cumul], Dim_Indicateur[code_indicateur] = "DEPOTS" )
Depots       = CALCULATE ( [Depots brut], LASTNONBLANK ( Dim_Date[Date], [Depots brut] ) )
```

Même modèle pour les dépôts à vue, d'épargne, à terme et les emprunts (`Depots a vue`, `Depots epargne`,
`Depots terme`, `Emprunts`). Toutes les mesures sont dans la table `Mesures` du modèle (dossiers
d'affichage, format `#,0.000`). Capitaux propres :

```dax
-- jamais la colonne 31/12 provisoire (5.2). FICHE BANQUE SEULEMENT : la définition varie selon la
-- banque (gabarits.csv, definition_capitaux_propres, affichée à côté) ; les comparaisons entre
-- banques utilisent les capitaux propres du bilan (Fait_Etats_Financiers, CAP_PROPRES_EF, 7.7)
Capitaux propres hors resultat brut = CALCULATE ( [Valeur Cumul], Dim_Indicateur[code_indicateur] = "CAP_PROPRES" )
Capitaux propres hors resultat de la periode =
    CALCULATE ( [Capitaux propres hors resultat brut],
                LASTNONBLANK ( Dim_Date[Date], [Capitaux propres hors resultat brut] ) )
```

### 7.2 Ratios

**Deux coefficients d'exploitation.** Les charges opératoires publiées n'ont pas le même contenu
d'une banque à l'autre (colonne `definition_charges_operatoires` de `gabarits.csv`) :

| Valeur | Contenu du total publié | Exemples |
|---|---|---|
| `sans dotations` | frais de personnel + charges générales d'exploitation | BT, BH, BTE, STB, TJARI jusqu'au T3 2021 |
| `avec dotations publiees` | frais de personnel + charges générales + dotations aux amortissements, trois lignes publiées | WIB (« Dotations aux amortissements et aux provisions sur immobilisations »), UIB |
| `avec reste non detaille` | plus que frais de personnel + charges générales ; la différence (dotations ou autres) n'est pas détaillée | BNA, ATB, AB, BIAT, TJARI à partir du T4 2021 (colonnes N-1 retraitées) |
| `composantes non publiees` | seul le total est publié | |

- **Coefficient harmonisé** = (frais de personnel + charges générales d'exploitation) / PNB.
  Même définition pour toutes les banques qui publient ces deux lignes. **Les classements et
  comparaisons entre banques (rang, médiane, secteur, matrices, couleurs) utilisent ce coefficient.**
  Il est calculé banque par banque et trimestre par trimestre, seulement là où les deux
  composantes et le PNB sont publiés ; le PNB du dénominateur est pris sur les mêmes lignes
  (une banque sans composantes ne fausse pas le coefficient du secteur). Il est plus bas que le
  coefficient publié quand le total publié comprend les dotations.
- **Coefficient publié** = charges opératoires publiées / PNB : affiché pour information
  (fiche banque, info-bulle avec la définition), jamais classé.
- L'extraction contrôle le total publié contre ses composantes selon la définition du gabarit
  (tolérance : 1 unité de la source par ligne). Un écart est signalé par le statut
  `ecart composantes` dans `controle_extraction.csv` ; il vient de la banque quand le PDF le
  confirme (BT 2020T3 : charges opératoires du trimestre 12 076 kDT, composantes 15 702 + 7 724 ;
  BNA 2023T2 : 86 209 kDT pour des composantes de 69 096 + 17 219). Aucun chiffre n'est corrigé.

Code exact : `dax/mesures.dax`, groupe 3 (23/10/2026). Le coefficient harmonisé se calcule sur une ligne
par banque (`VALUES ( Dim_Banque[code_banque] )`), le trimestre étant unique (garde-fou de 7.1) ; ajout du
`Coef exploitation harmonise annuel` (cumuls publiés au 31/12, jamais la somme des trimestres) et de
`Banques presentes coef`. `Coef secteur`, `Coef mediane` et `Rang coef` (7.4) sont vides si une des 12 banques
manque ; `Ecart coef / mediane` et `Rang coef` vides hors d'une ligne de banque.

```dax
-- Publié : définition propre à chaque banque (Definitions_Charges), pour information
Coef exploitation publie = DIVIDE ( [Charges operatoires], [PNB] )
-- Harmonisé : (frais de personnel + charges générales) / PNB, sur les lignes banque × trimestre
-- où les deux composantes et le PNB existent ; sert à tous les classements et comparaisons
Coef exploitation harmonise =
VAR Lignes =
    ADDCOLUMNS (
        SUMMARIZE ( Fait_Indicateurs, Fait_Indicateurs[banque], Fait_Indicateurs[date_arrete] ),
        "@Pers", [Frais personnel],
        "@Gen", [Charges generales],
        "@PNB", [PNB]
    )
VAR Completes =
    FILTER ( Lignes, NOT ISBLANK ( [@Pers] ) && NOT ISBLANK ( [@Gen] ) && NOT ISBLANK ( [@PNB] ) )
RETURN
    DIVIDE ( SUMX ( Completes, [@Pers] + [@Gen] ), SUMX ( Completes, [@PNB] ) )
Part marge interets    = DIVIDE ( [Marge interets], [PNB] )
Part commissions       = DIVIDE ( [Marge commissions], [PNB] )
Part portefeuille      = DIVIDE ( [Revenus portefeuille], [PNB] )
Frais personnel / PNB  = DIVIDE ( [Frais personnel], [PNB] )
Credits / Depots       = DIVIDE ( [Credits], [Depots] )
Part depots a vue      = DIVIDE ( [Depots a vue], [Depots] )
```

### 7.3 Intelligence temporelle

**Variations sur un an : toujours `Variations_Comparables`** (colonne N contre colonne N-1 du
même document, 5.2). On n'utilise jamais `SAMEPERIODLASTYEAR` ou `DATEADD` sur `Fait_Indicateurs`
pour une variation annuelle : cela rapprocherait deux documents, de méthodes parfois différentes
(les niveaux retenus de deux années consécutives viennent de deux documents révisés différents ;
BH : seul le T4 2025 donne 2025 et 2024 dans la même méthode, −2,8 % ; avec le PNB 2024 publié
au T4 2024, on obtiendrait −11,0 %). Le secteur se calcule de
même (somme des N contre somme des N-1, banque par banque dans leurs documents respectifs).

```dax
-- Bases (filtrées par Dim_Indicateur, Dim_Banque, Dim_Date)
VC N trim   = CALCULATE ( SUM ( Variations_Comparables[valeur_N] ),  Variations_Comparables[mesure] = "trim" )
VC N1 trim  = CALCULATE ( SUM ( Variations_Comparables[valeur_N1] ), Variations_Comparables[mesure] = "trim" )
VC N cumul  = CALCULATE ( SUM ( Variations_Comparables[valeur_N] ),  Variations_Comparables[mesure] = "cumul" )
VC N1 cumul = CALCULATE ( SUM ( Variations_Comparables[valeur_N1] ), Variations_Comparables[mesure] = "cumul" )
-- trimestre seul, sur un an (flux)
Var A/A trimestre % = DIVIDE ( [VC N trim] - [VC N1 trim], [VC N1 trim] )
-- cumul depuis le début de l'année (flux) ou solde (stocks), au dernier trimestre de la sélection
Var A/A cumul % =
    CALCULATE ( DIVIDE ( [VC N cumul] - [VC N1 cumul], [VC N1 cumul] ),
                LASTNONBLANK ( Dim_Date[Date], [VC N cumul] ) )

Var PNB A/A %          = CALCULATE ( [Var A/A trimestre %], Dim_Indicateur[code_indicateur] = "PNB" )
Var PNB cumul A/A %    = CALCULATE ( [Var A/A cumul %], Dim_Indicateur[code_indicateur] = "PNB" )
Var PNB annuel A/A %   = CALCULATE ( [Var A/A cumul %], Dim_Indicateur[code_indicateur] = "PNB",
                                     Dim_Date[Trimestre] = "T4" )
Var Charges operatoires A/A % = CALCULATE ( [Var A/A cumul %], Dim_Indicateur[code_indicateur] = "CHG_OPER" )
Var Credits A/A %      = CALCULATE ( [Var A/A cumul %], Dim_Indicateur[code_indicateur] = "CREDITS" )
Var Depots A/A %       = CALCULATE ( [Var A/A cumul %], Dim_Indicateur[code_indicateur] = "DEPOTS" )

-- T/T : deux documents successifs (pas d'autre source) ; à lire avec les marqueurs de rupture
PNB T-1    = CALCULATE ( [PNB], DATEADD ( Dim_Date[Date], -1, QUARTER ) )
Var PNB T/T % = DIVIDE ( [PNB] - [PNB T-1], [PNB T-1] )
PNB cumul annee = [PNB depuis debut annee]   -- cumul publié, pas TOTALYTD des trimestres (voir 5.2)
-- 4 trimestres glissants : somme des trimestres publiés (peut différer légèrement d'un cumul,
-- voir 5.2) ; à afficher comme indicateur de tendance, pas comme chiffre annuel
PNB 4T glissants =
    CALCULATE ( [PNB], DATESINPERIOD ( Dim_Date[Date], MAX ( Dim_Date[Date] ), -12, MONTH ) )
-- Croissance annuelle moyenne : enchaînement des 5 variations annuelles comparables (2021 à 2025,
-- chacune dans son document T4), jamais 2025 / 2020 en rapprochant deux documents
TCAM PNB 2020-2025 =
VAR Annees = GENERATESERIES ( 2021, 2025 )
VAR Variations =
    ADDCOLUMNS ( Annees, "@Var",
        VAR A = [Value]
        RETURN CALCULATE ( [Var PNB annuel A/A %], REMOVEFILTERS ( Dim_Date ), Dim_Date[Annee] = A ) )
VAR Completes = COUNTROWS ( FILTER ( Variations, NOT ISBLANK ( [@Var] ) ) )
RETURN IF ( Completes = 5, PRODUCTX ( Variations, 1 + [@Var] ) ^ ( 1 / 5 ) - 1 )

-- Annotation d'événement (evenements.csv) : texte affiché au point de la date, filtré par banque et
-- par indicateur ; plusieurs événements le même trimestre sont séparés par un retour à la ligne
Evenement texte =
    CONCATENATEX ( VALUES ( Evenements[description] ), Evenements[description], UNICHAR ( 10 ) )
Evenement montant MDT = SUM ( Evenements[montant_mdt] )
Nb evenements = COUNTROWS ( Evenements )
-- Marqueur de rupture de série pour les graphiques (période révisée de plus de 2 % sur le cumul)
Rupture PNB =
    IF ( CALCULATE ( COUNTROWS ( Fait_Indicateurs ), Fait_Indicateurs[Rupture_Trim] = "oui",
                     Dim_Indicateur[code_indicateur] = "PNB" ) > 0, [PNB] )
Rupture PNB cumul =
    IF ( CALCULATE ( COUNTROWS ( Fait_Indicateurs ), Fait_Indicateurs[Rupture_Cumul] = "oui",
                     Dim_Indicateur[code_indicateur] = "PNB" ) > 0, [PNB depuis debut annee] )
```

### 7.4 Comparaison au secteur

Code exact : `dax/mesures.dax`, groupe 2 (23/10/2026). Ajouts à ce qui suit : `Nombre de banques`,
`Banques presentes PNB` / `credits` / `depots` / (indicateur choisi), totaux `PNB secteur`, `Credits secteur`,
`Depots secteur` **vides si une banque manque** ; encours du secteur et banques présentes comptés à la
dernière date d'arrêté de la sélection (`Date fin credits`, `Date fin depots`) ; parts de marché des crédits ;
`Rang PNB` vide hors d'une ligne de banque ; `Dernier trimestre complet` (libellé et date, depuis
`Dim_Date[Choix_Trimestre]`). Les mesures du coefficient (secteur, médiane, rang) sont écrites avec les
ratios (7.2).

```dax
PNB secteur          = CALCULATE ( [PNB], REMOVEFILTERS ( Dim_Banque ) )
Part de marche PNB   = DIVIDE ( [PNB], [PNB secteur] )
Part de marche depots = DIVIDE ( [Depots], CALCULATE ( [Depots], REMOVEFILTERS ( Dim_Banque ) ) )
HHI PNB              = SUMX ( ALL ( Dim_Banque ), [Part de marche PNB] ^ 2 ) * 10000
-- comparaisons entre banques : toujours le coefficient harmonisé (7.2)
Coef secteur         = CALCULATE ( [Coef exploitation harmonise], REMOVEFILTERS ( Dim_Banque ) )   -- moyenne pondérée
Coef mediane         = MEDIANX ( ALL ( Dim_Banque ), [Coef exploitation harmonise] )
Ecart coef / mediane = [Coef exploitation harmonise] - [Coef mediane]
Rang coef            =
    IF ( NOT ISBLANK ( [Coef exploitation harmonise] ),
         RANKX ( FILTER ( ALL ( Dim_Banque ), NOT ISBLANK ( [Coef exploitation harmonise] ) ),
                 [Coef exploitation harmonise],, ASC, DENSE ) )
Rang PNB             = RANKX ( ALL ( Dim_Banque ), [PNB],, DESC, DENSE )
```

### 7.5 Bourse

**Sources (étape 4, décisions du 20/10/2026).**

- **2019 à 2025 : archives annuelles de la BVMT** (« Historique des données »,
  `https://www.bvmt.com.tn/sites/default/files/historiques/cotations/histo_cotation_AAAA.zip`),
  source officielle, une ligne par titre et par séance : ouverture, clôture, plus bas, plus haut,
  quantité négociée, nombre de transactions, **capitaux réellement échangés**. Deux formats :
  texte à colonnes fixes (2019 à 2021 ; code court en 2019-2020 = caractères 6 à 11 de l'ISIN,
  décimales à virgule en 2019), CSV « ; » à partir de 2022. L'archive 2023 contient aussi 2022 :
  séances identiques à l'archive 2022.
- **Année en cours (2026, pas encore archivée) : bulletin officiel quotidien de la cote**
  (`bulletin/pdf/bullAAAAMMJJ.pdf`, un par séance) pour les cours (référence, ouverture, dernier
  cours, plus haut, plus bas, clôture, réservation), **volume en titres d'ilboursa** (le bulletin
  ne donne pas les quantités ; API de la page « Historiques », 3 mois par requête ; égal à la BVMT
  sur 63 des 64 séances du T4 2025 de la BIAT). La clôture d'ilboursa est comparée à celle du
  bulletin (statut si elles diffèrent) ; une séance d'ilboursa sans bulletin n'est pas retenue.
  En 2026 : 26 écarts, dont 14 jours de réservation (ilboursa donne le dernier cours échangé) et
  12 autres, surtout le 23/09/2026 pour 7 banques (BNA : bulletin 18,720 vérifié sur l'image,
  ilboursa 19,630) ; le bulletin fait foi. Bulletin du 23/09/2026 vérifié le 22/10/2026 : n° 8928
  du « mercredi 23 septembre 2026 », entre le n° 8927 du 22 et le n° 8929 du 24 ; cours de
  référence du 23 = clôtures du 22 et cours de référence du 24 = clôtures du 23 pour les 12 banques
  (test `test_bulletin_20260923_bien_date`) : pas de bulletin mal nommé ; ilboursa concorde avec
  les bulletins le 22 et le 24, c'est sa donnée du 23 qui diffère. Une séance du bulletin sans volume chez ilboursa garde
  un volume vide (Wifak 23/09/2026).
  Les cours, nombres de transactions et capitaux d'ilboursa ne sont pas utilisés (plus hauts et
  plus bas différents de la BVMT, « Volume MDT » estimé, cours anciens ajustés sans méthode
  publiée). Contrôle sur le bulletin du 31/12/2025 : clôture, plus haut et plus bas identiques à
  l'archive 2025 pour les 12 banques.
- **Depuis le 14/04/2026, les bulletins sont publiés sur un autre domaine de la Bourse** :
  `https://tunis-stockexchange.com/sites/default/files/<mois de mise en ligne>/BullAAAAMMJJ.pdf`
  (« B » majuscule ; le bulletin du 30/06 est dans le dossier « 2026-07 »). Noms irréguliers :
  suffixe « -1 », « _0 » ou « _1 » (fichier remis en ligne : la version la plus récente est
  retenue), et un bulletin sans date dans son nom (04/06/2026 : `2026-06/BO.pdf`, date lue en
  page 1). Les adresses exactes sont lues dans la page « Éditions statistiques » de ce domaine
  (paginée, avec aussi les semaines boursières et les lettres mensuelles). Ce domaine ne demande
  pas de délai dans son robots.txt ; même organisme que bvmt.com.tn, il est interrogé avec 10 s
  (`DELAI_MINIMUM` dans `collecte_banques.py`).
- Un jour de séance dont le bulletin n'est pas encore en ligne (le plus récent) : clôture et
  volume d'ilboursa seulement, ouverture, plus haut et plus bas vides, statut `pas de bulletin
  BVMT : clôture et volume d'ilboursa (dernier cours échangé ; réservation non vérifiable)` : la
  clôture d'ilboursa est le dernier cours échangé et diffère de la clôture officielle un jour de
  réservation (4 cas de janvier à avril 2026 ; 3 autres écarts de 0,01 à 0,09 DT le 28/01/2026,
  signalés `clôture ilboursa ≠ bulletin`).
- BTE : le titre coté est l'action à dividende prioritaire (ADP), seule action BTE cotée.

**Règles de lecture** (`scripts/cours_boursiers.py`, sortie `donnees/cours_banques.csv` :
ticker, banque, isin, date, ouverture, haut, bas, cloture, volume, nb_transactions, capitaux,
statut, source, fichier) :
- séance sans transaction : l'archive met 0 aux cours de la séance et la clôture au cours de
  référence ; ouverture, haut et bas restent vides, statut `sans transaction` ;
- **un cours à 0 n'est jamais un prix** : en 2020, une séance sans transaction a tous ses cours à 0,
  clôture comprise ; le 17/12/2025, tous les titres sont à 0 (journée sans cotation, absente aussi
  chez ilboursa) ; l'UBCI a deux transactions sans cours coté (17/07/2019 : 10 000 titres pour
  242 000 DT ; 10/12/2019 : 15 000 titres). Ces cases restent vides (481 clôtures au 21/10/2026),
  statuts `clôture absente de l'archive (0)` et `quantité sans cours dans l'archive` ; quantité
  et capitaux publiés gardés. Pour les rendements, Power Query reprend la dernière clôture
  connue ;
- **ouverture**, selon l'année (mesuré sur les 12 banques) :
  - 2019, 2020, septembre à décembre 2021, 2026 (bulletins) : vraie ouverture ;
  - janvier à août 2021 : valeur figée (la même sur environ 65 % des séances, presque toujours hors
    de [plus bas, plus haut]) → vide, statut `ouverture figée dans l'archive` (règle : valeur
    répétée sur plus de 30 % des séances de l'année et hors bornes pour plus de la moitié d'entre
    elles ; une valeur souvent répétée mais dans les bornes est une vraie ouverture : Wifak 2024) ;
  - **2022 à 2025 : la colonne « OUVERTURE » de l'archive est le cours de référence** (égale à la
    clôture de la veille sur 99,2 à 99,7 % des séances, les autres étant des jours d'opération ;
    bulletin du 31/12/2025 : AB ouverture 49,480, référence et archive 49,460) → vide, statut
    `ouverture de l'archive = cours de référence` (règle : plus de 95 % des séances de l'année) ;
    les vraies ouvertures sont dans les bulletins quotidiens (environ 1 000 PDF, près de 3 heures
    à 10 s par requête : non téléchargés, à décider) ;
  - autre ouverture hors de [plus bas, plus haut] : vide, statut ;
- **réservation** (« B » à la baisse, « H » à la hausse, colonne du bulletin et `IND_RES` de
  l'archive 2020) : la clôture publiée peut sortir des cours échangés (BTE le 04/02/2026 :
  échangé à 3,890, clôture 3,720 B) ; gardée telle que publiée, statuts `réservation …` et
  `clôture hors [plus bas, plus haut]` ;
- contrôle `donnees/controle_cours.csv` : variation de clôture de plus de 6,15 % d'une séance à
  l'autre (33 au 21/10/2026). 22 sont des opérations de la table ci-dessous ; les 11 autres n'en
  sont pas : hausses, krach du 17/03/2020 (ATB, BNA, STB), titres peu liquides au fixing (BTE,
  UBCI, Wifak), lendemains de séance avec réservation, où la Bourse abaisse le cours de référence
  sans opération (UBCI 30/07/2020 : référence 25,260 après une clôture réservée de 26,040 ;
  STB 01/10/2020 : 3,650 après 3,710).

**Ajustements (opérations sur titres).** Sans ajustement les rendements sont faux : BIAT,
clôture 118,000 le 02/01/2019 et 111,000 le 31/12/2025, soit −5,9 % en brut et **+125,8 %**
ajusté des opérations sur le capital (hors dividendes). Opérations de la BIAT, toutes sourcées
dans le bulletin officiel (« Décisions et avis de la Bourse ») :

| Date d'effet | Opération | Facteur | Cours de référence publié (théorique) | Source |
|---|---|---|---|---|
| 29/06/2020 | attribution gratuite 1 pour 20 | 20/21 | 98,090 (98,095) | bull20200629.pdf p.7 |
| 04/05/2021 | division du nominal 10 → 5 DT | 1/2 | 60,870 (60,870) | bull20210503.pdf p.7 |
| 09/05/2022 | dividende 5,200 DT | (P − D) / P | 64,500 (64,500) | bull20220509.pdf p.1 (colonne « dernier dividende ») |
| 29/11/2024 | attribution gratuite 1 pour 7 | 7/8 | 91,880 (91,875) | bull20241129.pdf p.13 |

**Table des opérations sur titres** (`operations_titres.csv`, versionnée, produite par
`python scripts/cours_boursiers.py operations`) : une ligne par banque et par date d'effet (types
réunis si plusieurs le même jour : BNA 15/04/2019, attribution et souscription), avec le cours
de référence publié ce jour-là par la Bourse et la clôture de la séance précédente.
- Repérage : droits d'attribution (« DA a/b JJMMAA ») et de souscription (« DS ») des lignes
  secondaires (archives, groupe 32, et bulletin le plus récent) ; « dernier dividende » (montant,
  date) des bulletins de la dernière séance de chaque année ; division du nominal (nominal plus
  petit d'une fin d'année à la suivante, date = plus forte baisse entre les deux).
- Confirmation dans le bulletin du jour : cours de référence de la banque (page), avis de la
  Bourse (page et extrait) ; cours de référence théorique calculé avec la parité ou le dividende,
  comme contrôle (pas pour la souscription en numéraire, qui dépend du prix d'émission).
- **Facteur d'ajustement = cours de référence publié / clôture de la veille**, calculé dans
  Power Query : c'est l'ajustement fait par la Bourse elle-même, valable pour tous les types
  d'opération, même réunis. Cours ajusté d'une séance = cours × produit des facteurs des
  opérations postérieures. Deux séries : ajustée des opérations sur le capital (attributions,
  divisions, souscriptions : performance du prix) et ajustée de toutes les opérations, dividendes
  compris (rendement total). Pour la série « prix », un dividende détaché le même jour qu'une
  attribution est retiré de la clôture de la veille avant la parité (BT 10/05/2022 : facteur prix
  4,930 / (6,190 − 0,280) = 0,834 au lieu de 4,930 / 6,190 = 0,796 ; Power Query, 23/10/2026). Une
  opération sans cours de référence publié reste sans facteur et est signalée.
- Règles : une date de dividende hors séance prend la première séance suivante (UIB : samedi
  01/06/2019 → 03/06/2019) ; le dividende revient aux actions anciennes, il est retiré avant la
  parité dans le contrôle théorique (BT 10/05/2022 : (6,190 − 0,280) × 5/6 = 4,925, publié 4,930).
- **Résultat au 21/10/2026 : 63 opérations, toutes avec un cours de référence publié, contrôle
  théorique à 0,005 près** : 56 dividendes (aucun en 2020, année de l'interdiction des dividendes
  par la BCT ; 2026 : AB, BIAT, BNA, BT, STB (premier depuis 2010), Attijari, UBCI, UIB ; ATB
  seulement en 2019 ; BTE et Wifak aucun), 7 attributions gratuites (BNA 15/04/2019 avec
  souscription en numéraire, BIAT 29/06/2020 et 29/11/2024, BT 10/05/2022 avec le dividende, AB
  12/10/2023 et 28/10/2024, Attijari 30/04/2025 ; aucune en 2026), 1 division du nominal (BIAT
  04/05/2021).

```dax
Cours brut      = SUM ( Fait_Cours[cloture] )
Dernier cours   = CALCULATE ( [Cours brut], LASTNONBLANK ( Dim_Date[Date], [Cours brut] ) )
Premier cours   = CALCULATE ( [Cours brut], FIRSTNONBLANK ( Dim_Date[Date], [Cours brut] ) )
Performance periode = DIVIDE ( [Dernier cours], [Premier cours] ) - 1
Volatilite annualisee = STDEV.S ( Fait_Cours[rendement] ) * SQRT ( 252 )

-- Liquidité (décision du 21/10/2026) : affichée à côté de la volatilité, par banque.
-- Fait_Cours[sans_transaction] : colonne conditionnelle de Power Query, vrai si le statut contient
-- « sans transaction » (aucun titre échangé ; la clôture est alors le cours de référence)
Seances = COUNTROWS ( Fait_Cours )
Seances sans transaction = CALCULATE ( [Seances], Fait_Cours[sans_transaction] = TRUE () )
Taux seances sans transaction = DIVIDE ( [Seances sans transaction], [Seances] )
Seuil titre peu liquide = 0.20
Avertissement liquidite =
IF ( [Taux seances sans transaction] > [Seuil titre peu liquide],
     "Titre peu liquide : " & FORMAT ( [Taux seances sans transaction], "0 %" )
         & " des séances sans transaction ; volatilité et performance à lire avec prudence" )
```

Taux de séances sans transaction du 02/01/2019 au 20/10/2026 (`cours_banques.csv`, 1 955 séances
par banque, 21/10/2026) : **UBCI 52,7 %, Wifak 42,6 %, BTE 37,6 %** (groupe de cotation au fixing
ou titre peu échangé) ; puis BH 8,6 %, UIB 4,7 %, ATB 4,2 %, AB 3,5 %, STB 1,5 %, BNA 0,8 %,
Attijari 0,5 %, BT 0,4 %, BIAT 0,1 %. Le seuil de 20 % sépare nettement les trois titres peu liquides des neuf autres.
Pour eux, la volatilité calculée est trompeuse (beaucoup de rendements nuls, puis des sauts au
fixing, parfois au-delà de 6 % : BTE, UBCI, Wifak dans `controle_cours.csv`) : l'avertissement
s'affiche dans le tableau de la page Bourse, à côté de la volatilité, et en info-bulle des
graphiques de performance.

### 7.7 Rentabilité : ROE et ROA

**Pourquoi une source de plus.** Le ROE et le ROA ont besoin du **résultat net**, qui n'est pas
dans les indicateurs trimestriels. Il est publié dans les **états financiers** :

- annuels (au 31/12, audités), de 2019 à 2025 ;
- intermédiaires (au 30/06, revue limitée des commissaires aux comptes), de 2020 à 2026.

Le ROE et le ROA sont donc **semestriels et annuels**, pas trimestriels. Il faut le dire
clairement dans le rapport.

**Données à collecter** pour chaque banque et chaque date (30/06 et 31/12) :

| Code | Donnée | Où la trouver |
|---|---|---|
| `RES_NET` | Résultat net de la période (cumul depuis le 1er janvier) | État de résultat |
| `TOTAL_ACTIF` | Total de l'actif | Bilan |
| `CAP_PROPRES_EF` | Capitaux propres **y compris le résultat de la période** | Bilan |

Remarque : les capitaux propres des indicateurs trimestriels n'ont pas la même définition d'une
banque à l'autre (hors résultat, résultat inclus, après affectation au 31/12 : 5.2). On utilise
donc ceux du bilan pour le ROE et pour **toutes les comparaisons entre banques** ; les capitaux
propres trimestriels restent dans la fiche banque, avec leur définition (décision du 19/10/2026).

**Résultat net retenu : avant modifications comptables (règle générale, toutes banques,
décision du 18/10/2026).** Certaines banques publient sous le résultat net une ligne « Effet des
modifications comptables (net d'impôt) » puis un « Résultat après modification(s) comptable(s) ».
Le ROE et le ROA utilisent le résultat net **avant** modifications comptables (`RES_NET`) :

- l'effet d'une modification comptable concerne des **exercices antérieurs** (application
  rétroactive d'une nouvelle méthode) ; il ne mesure pas la rentabilité de la période ;
- il **passe en résultats reportés**, dans les capitaux propres : le résultat inscrit au bilan
  (ligne « Résultat de l'exercice / de la période » des capitaux propres) est le résultat avant
  modifications, donc cohérent avec `CAP_PROPRES_EF`, dénominateur du ROE ;
- exemple : BNA 2024, effet de −40,975 MDT ; résultat net 254,557 MDT au 31/12/2024 (213,582 après
  modification) et 132,749 MDT au 30/06/2024 (91,774 après) ; le bilan porte 254,557 et 132,749,
  et l'effet figure en résultats reportés (−39,940 au 31/12/2024).

Le résultat après modifications (`RES_NET_APRES_MODIF`) et l'effet (`MODIF_COMPTABLES`) sont
enregistrés pour information (fichier, page), sans servir aux ratios. Le résultat inscrit dans
les capitaux propres du bilan (`RES_BILAN`) sert de contrôle : il doit égaler `RES_NET`.

Soit environ 12 banques × 13 dates × 3 valeurs ≈ 470 valeurs, collectées par
`scripts/etats_financiers.py` :

1. Téléchargement des états financiers individuels, dans cet ordre (les comptes consolidés sont
   toujours écartés) :
   1. site de la BVMT
      (`.../etats-financiers/<préfixe>-etats-financiers-annuels-individuels-31-12-AAAA.pdf`,
      `...-semestriels-30-06-AAAA.pdf`) ;
   2. **liste des états financiers du CMF** (page « Consultation des états financiers des
      sociétés faisant APE », filtrée par société : nom des comptes individuels, pas les
      « GROUPE … ») : chaque entrée donne la date de dépôt, l'exercice, la période et le lien.
      Les noms de fichiers n'y suivent aucun format (`bna_bank_efd311225.pdf`, `efi_2026_bna.pdf`,
      `amenbank_efi_01092029.pdf`) : c'est pourquoi les annuels 2025 et les semestriels 2026
      n'étaient pas trouvés sur la BVMT (seul Attijari publie 2025 sous le format habituel). La
      liste est gardée dans `donnees/liste_etats_financiers_cmf.csv` (relue avec
      `--rafraichir-liste-cmf`). Sont cherchés ici les documents manquants, scannés, et en échec à
      l'extraction (états en image au milieu d'un rapport lisible) ; un PDF déjà enregistré n'est
      jamais remplacé (la version du CMF a le suffixe `_cmf`). Les « états financiers
      provisoires » ne sont pas retenus ;
   3. **Bulletins Officiels du CMF**, seulement pour ce qui reste (`--bulletins`). La fenêtre de
      recherche part de la date de dépôt donnée par la liste du CMF (jusqu'à 30 jours après) ;
      sans elle : 15/07 → 30/09 pour un 30/06, 15/02 → 31/05 de l'année suivante pour un 31/12.
      Le bloc retenu doit contenir une ligne de tableau « Total de l'actif » et ne pas parler de
      comptes consolidés sur ses deux premières pages : le sommaire du bulletin (STB S1 2023,
      bulletin du 02/10/2023) et la fin du rapport sur les comptes consolidés du groupe BH (BH 2019,
      bulletin du 15/06/2020, « 34,91 % du total actif ») étaient pris à tort ; ces deux extraits
      sont rangés dans `donnees/rejetes/`.

   Statuts du manifeste : `ok` ; `illisible (image)` (PDF scanné) ; **`non publié`** (date
   absente de la liste du CMF : pas encore déposée) ; `manquant` (listée au CMF ou attendue, mais
   aucune version trouvée). Les dates ne sont demandées qu'après les délais habituels de
   publication (31/12 + 120 jours, 30/06 + 65 jours).

   Bilan au 19/10/2026 : 168 arrêtés (12 banques × 14 dates), 132 documents pris sur la BVMT et
   35 dans la liste du CMF (dont les 11 annuels 2025 et les 12 semestriels 2026 manquants, et des
   versions lisibles de 4 semestriels scannés à la BVMT) ; aucun « non publié ». Sans version
   lisible nulle part (BVMT, CMF, Bulletin) : **BH 31/12/2019** (états en image dans les trois
   sources) et **STB 30/06/2023** (PDF scanné à la BVMT et au CMF, annexe en image dans le
   bulletin du 02/10/2023) : leurs valeurs viennent de la colonne N-1 du document suivant
   (règle des versions, plus bas).
2. Extraction des lignes « Total actif », « Total capitaux propres » et « Résultat net de
   l'exercice / de la période », en ignorant la colonne des notes (y compris les renvois en
   chiffres romains en fin de libellé, « Total des capitaux propres V »). Les lignes de résultat
   ne sont lues que sur la page de l'**état de résultat** (titre en tête de page), jamais dans les
   notes ni dans le tableau de variation des capitaux propres. Un tiret « - » vaut 0 à sa place.
   Un nombre d'un ou deux chiffres est un renvoi de note, sauf s'il finit sur le bord droit d'une
   colonne de montants de la page (BTE S1 2026 : résultat après modifications = 48 kDT). Un
   renvoi de note collé à un nombre (case deux fois plus large que les autres) est retiré
   (WIB S1 2021 : « TOTAL CAPITAUX PROPRES 3 » + 152 890 148). Un nombre **mal formé dans le
   PDF** n'est complété que s'il **se déduit exactement d'un total du même document, même
   colonne** (décision du 20/10/2026) : total de l'actif = total des capitaux propres et passifs
   (et inversement), à condition que les chiffres imprimés soient le début du nombre déduit.
   Statut de la valeur `déduit (contrôle)` (colonne `statut_valeur`), explication dans
   `remarque`, information non bloquante dans le contrôle. Sinon la case reste vide. Seul cas :
   Attijari S1 2026, total des actifs au 30/06/2025 imprimé « 12 983 60 », déduit = 12 983 608
   (total des capitaux propres et passifs de la colonne ; la somme AC1 à AC7, relevée sur
   l'image, donne aussi 12 983 608). Contre 12 965,741 MDT publié dans le S1 2025 : révision
   de +17,867 (« Chiffres retraités au 30/06/2025 pour les besoins de la comparabilité », note 3.12 « Changement de présentation »),
   `retraitement_mineur`, valeur retenue 12 983,608. Libellés : ligature « Ɵ » (= « ti », BT 2025 « Total des AcƟfs ») et apostrophe
   « ʹ » (BH S1 2020) reconnues.
3. Contrôles bloquants (statut `a verifier`) : total actif = total capitaux propres et passif ;
   capitaux propres < total actif ; résultat net < capitaux propres ; résultat de l'état de
   résultat = résultat du bilan (`RES_BILAN`) ; capitaux propres lus sur la page du total
   capitaux propres et passifs.
4. **Recoupement avec les indicateurs trimestriels** (contrôle non bloquant, colonne
   `recoupement_trimestriel` de `controle_etats_financiers.csv`, tolérance 2 kDT) : capitaux
   propres trimestriels retenus dans `indicateurs_versions.csv` à la même date, comparés selon la
   définition de la banque (`definition_capitaux_propres` de `gabarits.csv`, 5.2) : capitaux
   propres du bilan − résultat net de la période (`hors resultat de la periode`), capitaux
   propres du bilan (`resultat inclus`), statut `non comparable (31/12 après affectation du
   résultat)` pour AB et BIAT au 31/12. Non bloquant parce qu'un écart vient de la série
   trimestrielle, pas des états financiers. Au 19/10/2026 : 131 « ok », 14 « non comparable »,
   17 écarts (liste et causes en 5.2), 4 dates sans valeur trimestrielle (BTE : tableaux en
   image).
5. Comparaison du résultat net annuel avec le tableau annuel d'ilboursa : **purement
   informative**, elle ne change jamais le statut d'un document. ilboursa ne précise pas s'il
   s'agit de comptes individuels ou consolidés, et ses chiffres sont probablement consolidés
   (2023 : BNA 212,0 MDT contre 190,0 en individuel ; BIAT 358,6 contre 331,4).
6. **Règle des versions et reprise depuis le document suivant (décision du 19/10/2026, même
   règle que les indicateurs trimestriels, 5.2 règle 4).** Pour chaque banque, date et valeur
   (`RES_NET`, `TOTAL_ACTIF`, `CAP_PROPRES_EF`) :
   - version `initiale` = colonne N du document de la date ;
   - version `revisee` = colonne N-1 du **document suivant de même type** : annuel N+1 pour un
     31/12, semestriel N+1 pour un 30/06. Vérifié sur les 12 banques : la colonne N-1 lue dans un
     semestriel est toujours le 30/06/N-1, jamais le 31/12/N-1 (210 cas comparables, aucun
     égal au 31/12) ; quand le document a deux colonnes N-1 (« retraité » et « publié », BH
     2020 ; WIB S1 2021), c'est la première, la retraitée ;
   - **valeur retenue : toujours la version révisée quand elle existe**, sinon l'initiale. Une
     date sans document lisible n'a que la révisée (statut `repris du document suivant`) : BH
     31/12/2019 (dans BH 2020 : résultat 141,642, total de l'actif 12 207,576, capitaux propres
     981,089 MDT) et STB 30/06/2023 (dans STB S1 2024 : 40,522 ; 15 098,400 ; 1 192,161 ; ce
     sont des chiffres « retraités pour les besoins de la comparabilité », la version publiée à
     l'origine n'étant lisible nulle part). Sans l'une ni l'autre, la valeur reste vide
     (`non disponible`) ; aucun cas au 19/10/2026 ;
   - nature de la révision (`statut_revision`, écart révisée − initiale, tolérance d'arrondi
     2 kDT) : `retraitement_mineur` (2 % au plus de la valeur initiale), `revision_importante`
     (plus de 2 %), vide (sous la tolérance). Au 19/10/2026 : 23 retraitements mineurs (surtout
     STB et le total de l'actif : ATB, TJARI, UIB) et 8 révisions importantes retenues : UIB 30/06/2020
     (résultat −41,182 → 17,912 et capitaux propres +59,094 : intérêts du moratoire Covid
     réintégrés, événement `MORATOIRE_COVID_UIB` de `evenements.csv`, ligne `RES_NET` au 30/06/2020), WIB 31/12/2020 (résultat −5,376 → −7,816 ; capitaux
     propres −3,540), WIB 31/12/2024 (résultat +0,209), BTE 31/12/2023 et 30/06/2025 (capitaux
     propres −4,202 et −1,360 : modifications comptables), STB 31/12/2021 (résultat −2,787) ;
   - **priorité, résultat net (décision du 20/10/2026) : la règle « avant modifications
     comptables » prime sur la règle des versions.** Une version révisée du résultat net égale au
     résultat **après** modifications comptables du document initial (effet non nul, tolérance
     2 kDT) n'est pas retenue : la valeur retenue reste l'initiale, la révisée est gardée pour
     information (statut `revisee non retenue (modification comptable incluse)`, raison dans la
     colonne `remarque`). Seul cas au 20/10/2026 : **BNA 30/06/2025**, 155,069 MDT retenu ;
     137,318 dans le document S1 2026 (note 3.8, p.10 : retraitement « pro-forma » qui reclasse
     l'effet de −17,751 MDT de la déchéance fiscale des fonds gérés en dotations aux provisions,
     −9,329, et en autres éléments ordinaires, −8,422 ; « résultat net final inchangé à
     137,318 »). Vérifié : la colonne 30/06/2026 de ce document n'a pas d'effet de modification
     comptable (ligne « - », la note 3.8 ne retraite que la colonne comparative). À savoir :
     l'**annuel 2025** de la BNA n'a pas non plus de ligne de modification comptable, et le
     paiement de 17,751 MDT (note p.62) est **dans** son résultat 274,544 ; le S1 2025 retenu
     (155,069, sans cet effet) et l'annuel 2025 ne sont donc pas sur la même base. **Décision du
     20/10/2026 : l'annuel 2025 reste tel que publié (274,544)**, l'écart de base est signalé
     sur la page « Qualité des données » (événement `BNA_DECHEANCE_FISCALE_2025` de
     `evenements.csv`, rappelé dans la colonne `remarque` des versions) ;
   - les dates les plus récentes (31/12/2025, 30/06/2026) n'ont encore que la version initiale.

   Conséquence pour le ROE et le ROA : les capitaux propres et le total de l'actif d'ouverture
   (31/12/N-1) retenus sont ceux que publie le document de l'exercice N dans sa colonne N-1,
   donc dans la même méthode que la valeur de fin de période.

Aucune valeur des états financiers n'est saisie à la main : les deux dates sans document lisible
(BH 31/12/2019, STB 30/06/2023) sont reprises de la colonne N-1 du document suivant (règle des
versions), et un nombre mal formé n'est retenu que s'il se déduit exactement d'un total du même
document (statut `déduit (contrôle)`). Il n'y a pas de fichier de corrections séparé : les seules
valeurs saisies à la main (indicateurs trimestriels) sont dans `saisies_manuelles.csv`.

Sorties : `donnees/etats_financiers_long.csv` (toutes les valeurs lues, colonnes N et N1 ;
`statut_valeur` = `déduit (contrôle)` le cas échéant, avec `remarque`) et
`donnees/etats_financiers_versions.csv` (une ligne par version : `banque`, `date_arrete`,
`type`, `code`, `version`, `valeur_mdt`, `fichier`, `page`, `statut_valeur`, `valeur_retenue`,
`source_valeur`, `statut_revision`, `ecart_mdt`, `remarque`).

Table de faits `Fait_Etats_Financiers` : depuis `etats_financiers_versions.csv`, lignes
`version = source_valeur` (valeur retenue) : banque, date_arrete, type (semestriel / annuel),
code, valeur_mdt, version, fichier, page, statut_valeur, statut_revision, remarque, et la colonne
conditionnelle `facteur_annualisation` (2 pour un semestre, 1 pour un exercice, calculée dans Power
Query). Les autres lignes (versions initiales remplacées, révisée non retenue de BNA au 30/06/2025)
vont dans `Revisions_Etats_Financiers` (page qualité), comme `Revisions` pour les indicateurs : filtre
inverse, `Ecart_MDT` et `Ecart_Pct` calculés dans Power Query, colonne conditionnelle `Type_Revision`.
Relations : `Dim_Banque` et `Dim_Date` comme les autres faits.

**Définitions retenues :**

- ROE = résultat net annualisé / capitaux propres moyens
- ROA = résultat net annualisé / total de l'actif moyen
- Annualisation : × 2 pour un résultat au 30/06, × 1 au 31/12
- Moyenne = (valeur à l'ouverture de l'exercice + valeur à la date) / 2

**Mesures :**

```dax
Resultat net brut = CALCULATE ( SUM ( Fait_Etats_Financiers[valeur_mdt] ),
                        Fait_Etats_Financiers[code] = "RES_NET" )
Resultat net = CALCULATE ( [Resultat net brut],
                   LASTNONBLANK ( Dim_Date[Date], [Resultat net brut] ) )
Resultat net annualise =
VAR DateRes = CALCULATE ( MAX ( Fait_Etats_Financiers[date_arrete] ),
                  Fait_Etats_Financiers[code] = "RES_NET" )
RETURN [Resultat net] * IF ( MONTH ( DateRes ) = 6, 2, 1 )

Cap propres EF brut = CALCULATE ( SUM ( Fait_Etats_Financiers[valeur_mdt] ),
                          Fait_Etats_Financiers[code] = "CAP_PROPRES_EF" )
Cap propres fin = CALCULATE ( [Cap propres EF brut],
                      LASTNONBLANK ( Dim_Date[Date], [Cap propres EF brut] ) )
Cap propres ouverture =
VAR DateFin = CALCULATE ( MAX ( Fait_Etats_Financiers[date_arrete] ),
                  Fait_Etats_Financiers[code] = "CAP_PROPRES_EF" )
RETURN CALCULATE ( [Cap propres EF brut], REMOVEFILTERS ( Dim_Date ),
           Dim_Date[Date] = DATE ( YEAR ( DateFin ) - 1, 12, 31 ) )
Cap propres moyens = AVERAGEX ( { [Cap propres ouverture], [Cap propres fin] }, [Value] )

ROE = DIVIDE ( [Resultat net annualise], [Cap propres moyens] )
```

Même logique pour le total de l'actif et le ROA :

```dax
ROA = DIVIDE ( [Resultat net annualise], [Total actif moyen] )
```

Visuels : ROE et ROA par banque (barres), évolution semestrielle (courbes), matrice
ROE × coefficient d'exploitation, ROE face à la performance boursière.

Limites : résultat semestriel non audité (revue limitée) ; l'annualisation × 2 ignore la
saisonnalité ; certaines banques publient des comptes consolidés et individuels — on prend
toujours les **comptes individuels** pour rester cohérent avec les indicateurs trimestriels.

### 7.8 Affichage et qualité

```dax
Date derniere donnee = CALCULATE ( MAX ( Fait_Indicateurs[date_arrete] ), REMOVEFILTERS () )
Titre rapport = "Banques cotées — données au " & FORMAT ( [Date derniere donnee], "dd/mm/yyyy" )
Couleur coef  = IF ( [Ecart coef / mediane] <= 0, "#2E7D32", "#C62828" )
Nb documents  = COUNTROWS ( Controle )
Taux extraction ok = DIVIDE ( CALCULATE ( [Nb documents], Controle[statut] = "ok" ), [Nb documents] )
Nb ecarts trim cumul = CALCULATE ( [Nb documents], Controle[statut] = "ecart trimestre/cumul" )
Nb ecarts composantes = CALCULATE ( [Nb documents], Controle[statut] = "ecart composantes" )
-- versions : part des valeurs affichées qui viennent d'une révision, et révisions significatives
Part cumuls revises =
    DIVIDE ( CALCULATE ( COUNTROWS ( Fait_Indicateurs ),
                         LEFT ( Fait_Indicateurs[Source_Cumul], 7 ) = "revisee" ),
             CALCULATE ( COUNTROWS ( Fait_Indicateurs ), NOT ISBLANK ( Fait_Indicateurs[Source_Cumul] ) ) )
Part 31-12 provisoires =
    DIVIDE ( CALCULATE ( COUNTROWS ( Fait_Indicateurs ),
                         LEFT ( Fait_Indicateurs[Source_Cumul], 14 ) = "revisee_31-12_" ),
             CALCULATE ( COUNTROWS ( Fait_Indicateurs ), NOT ISBLANK ( Fait_Indicateurs[Source_Cumul] ) ) )
Nb revisions = CALCULATE ( COUNTROWS ( Revisions ), ABS ( Revisions[Ecart_MDT] ) > 0.002 )
-- nature des révisions : portée par la ligne de la version initiale remplacée (règle 4)
Nb revisions importantes =
    CALCULATE ( COUNTROWS ( Revisions ), Revisions[version] = "initiale",
                Revisions[statut_revision] = "revision_importante" )
Nb retraitements mineurs =
    CALCULATE ( COUNTROWS ( Revisions ), Revisions[version] = "initiale",
                Revisions[statut_revision] = "retraitement_mineur" )
Nb reclassements = CALCULATE ( COUNTROWS ( Revisions ), Revisions[statut_revision] = "reclassement" )
Ecart revision MDT = SUM ( Revisions[Ecart_MDT] )
Nb annees en attente = CALCULATE ( COUNTROWS ( Controle_Annuel ), Controle_Annuel[statut] = "en attente de révision" )
Nb ecarts annuels    = CALCULATE ( COUNTROWS ( Controle_Annuel ), Controle_Annuel[statut] = "ecart" )
Nb ruptures annuelles = CALCULATE ( COUNTROWS ( Controle_Annuel ), Controle_Annuel[statut] = "rupture de série" )
-- causes des écarts annuels (table Ecarts_Annuels, une ligne par écart)
Nb ecarts expliques  = COUNTROWS ( Ecarts_Annuels )
Ecart annuel MDT     = SUM ( Ecarts_Annuels[ecart_mdt] )
-- ruptures de série : périodes dont la valeur retenue est une révision importante
Nb ruptures serie =
    CALCULATE ( COUNTROWS ( Fait_Indicateurs ),
                Fait_Indicateurs[Rupture_Trim] = "oui" || Fait_Indicateurs[Rupture_Cumul] = "oui" )
Nb documents illisibles = CALCULATE ( [Nb documents], Controle[statut] = "illisible (image)" )
Nb documents saisis    = CALCULATE ( [Nb documents], Controle[statut] = "saisie manuelle" )
Nb valeurs non disponibles =
    CALCULATE ( COUNTROWS ( Revisions ), Revisions[statut_revision] = "non disponible (image)" )
```

Paramètre de champ « Indicateur affiché » : PNB, Coef exploitation harmonise, Crédits / Dépôts,
Part de marché, Var PNB A/A % (Variations_Comparables) — pour un seul visuel où l'utilisateur choisit l'indicateur.

## 8. Ajouts par rapport au rapport de référence

1. Historique de 27 trimestres au lieu d'une seule date.
2. Valeurs trimestrielles et cumulées, et contrôle entre les deux.
3. Comparaison à la médiane et à la moyenne pondérée du secteur, rangs.
4. Segmentation par actionnariat (public, groupe étranger, mixte, privé sans contrôle étranger), selon le contrôle.
5. Matrice de positionnement : croissance du PNB (variation comparable, 7.3) × coefficient d'exploitation harmonisé.
6. Concentration du secteur (HHI) et parts de marché PNB et dépôts.
7. Périodes Avant Covid / Covid / Après Covid.
8. Volet boursier : performance et volatilité face aux indicateurs.
9. Page « qualité des données » : documents trouvés, extraits, à vérifier.
10. Pipeline reproductible : script Python + Power Query paramétré + sources CSV, Excel et URL.
11. Rentabilité (ROE, ROA) à partir des états financiers, croisée avec l'efficacité et la Bourse.

## 9. Pages du rapport

| Page | Contenu |
|---|---|
| 1. Vue d'ensemble | Cartes (PNB secteur, coef secteur, dépôts, crédits), titre dynamique, part de marché PNB, HHI dans le temps |
| 2. Classement | Tableau des banques avec rangs et mise en forme conditionnelle, matrice croissance × coef |
| 3. Évolution 2020–2026 | Courbes par banque avec sélecteur d'indicateur, bandes de périodes Covid, marqueurs de rupture de série (`Rupture PNB`, info-bulle `detail_rupture`), annotations des événements (`Evenements` : don au Fonds 1818 en 2020, moratoire Covid de l'UIB en 2020, accord salarial APTBEF–FGBEF en 2021, retraitement BH 2024) en info-bulle et en marqueurs ; variations sur un an depuis `Variations_Comparables` |
| 4. Structure du PNB | Barres empilées marge d'intérêts / commissions / portefeuille par banque |
| 5. Bilan | Crédits, dépôts, crédits / dépôts, structure des dépôts |
| 6. Bourse | Cours (ajustés des opérations sur titres), performance, volatilité **avec à côté le taux de séances sans transaction et l'avertissement « titre peu liquide »** (UBCI, Wifak, BTE : plus de 20 %), performance boursière vs croissance du PNB |
| 7. Fiche banque (extraction) | Tous les indicateurs d'une banque, accessible par clic droit ; coefficient publié à côté du coefficient harmonisé, avec la définition des charges opératoires de la banque ; capitaux propres trimestriels avec leur définition (`definition_capitaux_propres`), seul endroit où ils apparaissent (ailleurs : capitaux propres du bilan) |
| 8. Rentabilité | ROE et ROA semestriels et annuels, matrice ROE × coefficient d'exploitation |
| 9. Qualité des données | Contrôle d'extraction (statuts, dont `ecart trimestre/cumul`, `retraitement possible`, `ecart composantes`, `illisible (image)`, avec l'écart en MDT), révisions importantes et ruptures de série (avec la note du document), remarques des états financiers (colonne `remarque` de `etats_financiers_versions.csv` : révisée non retenue, valeur déduite, renvoi aux événements ; ex. BNA : S1 2025 et annuel 2025 pas sur la même base, 17,751 MDT), sources, limites ; phrase expliquant pourquoi la somme des trimestres peut différer du cumul annuel, avec le tableau des écarts annuels et leur cause (`Ecarts_Annuels` : catégorie, cause, fichier, page) |

Filtres : segments Année / Trimestre, plage de dates, banque, actionnariat, période ;
info-bulles personnalisées ; signets « trimestre » / « année ».

## 10. Limites à mentionner dans le rapport

- Données provisoires, non auditées, publiées par les banques elles-mêmes.
- Retraitements en cours d'année : la somme des trimestres publiés peut différer du cumul
  annuel publié ; les chiffres annuels viennent toujours du cumul (voir 5.2).
- Révisions : les niveaux sont toujours les derniers chiffres publiés par la banque pour la
  période (version révisée) ; une révision de plus de 2 % du cumul est signalée par un marqueur
  de rupture dans les graphiques. Le seuil de 2 % est un choix d'analyse, pas une norme. Les
  variations sur un an sont toujours calculées dans un même document. Les banques n'expliquent pas
  toujours ce qui a changé (BH, T4 2025) ; deux causes communes sont connues pour 2020 (don au
  Fonds 1818) et 2021 (accord salarial du secteur), plus une cause propre à l'UIB en 2020
  (intérêts du moratoire Covid non comptés dans les chiffres publiés, réintégrés en 2021 : PNB
  des 9 mois 2020 révisé de +42,7 %).
- Erreurs de la banque dans les colonnes N-1 : deux cas vérifiés sur l'image. UIB 2023T2 :
  charges d'exploitation du T2 2022 égales au cumul du semestre (produits − charges ≠ PNB dans
  cette colonne, document « a verifier ») ; WIB 2023T4 : colonne T4 2022 recopiée du T3 2022
  (cohérente en elle-même, repérée par le contrôle annuel 2022). Ces deux colonnes ne sont pas
  retenues (5.2, colonnes N-1 non retenues) ; la liste des révisions importantes est dans
  `docs/revisions_importantes.csv` (`python scripts/bilan_extraction.py`).
- Un document publié en image (BH 2019T4) n'est connu que par les colonnes N-1 du document de
  l'année suivante.
- Définitions des postes parfois différentes d'une banque à l'autre. Exemple : les charges
  opératoires publiées par la BT et la BH ne comprennent que les frais de personnel et les charges
  générales (pas de dotations aux amortissements) ; la BNA et l'ATB ne détaillent que ces deux postes mais
  leur total comprend un reste non détaillé ; WIB et UIB publient en plus les dotations aux
  amortissements. On garde le total publié, sans le recalculer
  (`gabarits.csv`, colonne `definition_charges_operatoires`) ; les comparaisons entre banques
  utilisent le coefficient d'exploitation harmonisé (frais de personnel + charges générales,
  hors dotations), qui sous-estime le coût total des banques dont les dotations sont importantes.
- ROE et ROA seulement en semestriel et annuel ; résultats semestriels non audités, annualisés.
- Les valeurs extraites automatiquement ont été contrôlées par échantillon (voir `docs/validation.md`).
