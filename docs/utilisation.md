<!-- Auteur : Ahmed Ben Arfa -->
# Mode d'emploi des scripts

Ce document explique comment reproduire les données du projet : téléchargement des PDF publics,
extraction en CSV, contrôles, tests et outils de vérification. La présentation du projet est dans
le [README](../README.md) ; la spécification complète (modèle, mesures, pages du rapport) dans
[`SPECIFICATION.md`](SPECIFICATION.md) ; les requêtes Power Query dans
[`guide_powerbi.md`](guide_powerbi.md).

Toutes les commandes se lancent depuis le dossier du projet. Les PDF et les CSV produits vont dans
`donnees/`, qui n'est pas versionné : il faut lancer la collecte pour les obtenir.

## 1. Installation

```
python -m pip install -r requirements.txt
```

## 2. Indicateurs d'activité trimestriels (`collecte_banques.py`)

```
python collecte_banques.py tout                              # télécharge puis extrait
python collecte_banques.py telecharger --banques UIB,BIAT --debut 2024T1 --fin 2026T3
python collecte_banques.py telecharger --sans-bulletins      # plus rapide, sites seulement
python collecte_banques.py telecharger --debut 2026T4 --fin 2026T4 --rafraichir-liste-cmf
python collecte_banques.py extraire                          # relance seulement l'extraction
python collecte_banques.py urls --banques BH --debut 2025T2 --fin 2025T2   # URL testées
```

Le script peut être relancé : les PDF déjà trouvés ne sont pas retéléchargés
(`donnees/manifeste_telechargements.csv`). Durée : de quelques minutes à environ une heure si
beaucoup de documents doivent être cherchés dans les Bulletins Officiels.

Quand la sortie est redirigée vers un fichier, définir `PYTHONIOENCODING=utf-8` (sinon l'écriture
de certains caractères échoue).

**Politesse envers les serveurs.** Les trois scripts de collecte passent par le même client
(`Client` et `Politesse` dans `collecte_banques.py`) : le `robots.txt` de chaque site est lu, les
chemins interdits ne sont jamais demandés, le délai entre deux requêtes au même site est le plus
grand du `Crawl-delay` et de `PAUSE` (10 secondes pour la BVMT, le CMF et la Bourse de Tunis),
une requête à la fois.

### Où le script cherche

1. Pages société du site de la BVMT
   (`/societes/<banque>/indicateurs-dactivite-trimestriels/<banque>-indicateurs-dactivite-trimestriels-JJ-MM-AAAA.pdf`).
2. Dossier des indicateurs du site du CMF (`indic_2trim26_uib.pdf`, `ind_2eme_trim_2026_biat.pdf`…).
3. Pour les documents encore manquants : la liste des indicateurs publiée par le CMF
   (`https://www.cmf.tn/?page=1&q=indicateurs-d-activit-`). Les liens sont gardés dans
   `donnees/liste_indicateurs_cmf.csv` ; option `--rafraichir-liste-cmf` pour relire la liste
   (par exemple après le 20 du mois qui suit un trimestre), `--sans-liste-cmf` pour sauter l'étape.
4. En dernier recours, les Bulletins Officiels quotidiens du CMF publiés dans les 45 jours
   après la fin du trimestre : seules les pages de la banque sont gardées.

Chaque PDF est vérifié : il doit citer la date d'arrêté du trimestre visé (et, pour un candidat de
la liste du CMF, le nom de la banque).
Un document absent des adresses habituelles et de la liste du CMF prend le statut `non publié` ;
sinon `manquant`. Deux documents ont été retrouvés à la main sur d'autres sites (Attijari 2021T2
sur tunis-stockexchange.com, Wifak 2022T3 sur wifakbank.com) et enregistrés dans le manifeste.

Après un téléchargement : `python scripts/verifier_manifeste.py` (doublons, PDF présents et
lisibles, URL, PDF orphelins).

### Lecture des tableaux

Les montants sont alignés à droite : le script repère le bord droit de chaque colonne de
chiffres sur la page, rattache chaque morceau de nombre (« 6 », « 479 », « 908 ») à sa colonne,
puis le recolle. Il se fie à la position sur la page, pas à l'ordre du texte du PDF (qui est
parfois inversé).

**Gabarits (`gabarits.csv`)** : pour chaque banque et chaque période de mise en page, l'ordre des
colonnes, l'unité, les libellés particuliers (`CODE=regex`, séparés par `||`), le contenu des
charges opératoires publiées (`definition_charges_operatoires`) et celui des capitaux propres
trimestriels (`definition_capitaux_propres`). Le gabarit décide ; la lecture de l'en-tête et
l'unité déduite du PNB deviennent des contrôles qui signalent tout désaccord.

**Documents publiés en image.** Un PDF sans texte prend le statut `illisible (image)` ; ses
chiffres sont repris de la colonne N-1 du document suivant quand elle existe. Sinon ils sont
relevés sur l'image dans `saisies_manuelles.csv` (fichier, page, colonne, valeur publiée, unité,
vérification ; contrôle au chargement : `valeur_mdt` = valeur publiée × unité). Vérification par
une seconde lecture :

```
python scripts/verification_saisie.py preparer BTE 2020T2   # fichier à remplir + images
python scripts/verification_saisie.py reporter BTE 2020T2   # recopie la colonne « verification »
```

### Fichiers produits (dossier `donnees/`)

| Fichier | Contenu |
|---|---|
| `indicateurs_banques_long.csv` | Valeurs brutes : une ligne par document × indicateur × colonne lue |
| `indicateurs_versions.csv` | Une ligne par banque × période × indicateur × mesure (`trim` / `cumul`) × version (`initiale` = document du trimestre ; `revisee_T<q>_N+1` = colonne N-1 du document de l'année suivante ; `revisee_31-12_T<q>_N+1` = colonne 31/12/N-1 d'un T1–T3 suivant, provisoire), avec `valeur_retenue`, `source_valeur`, `ecart_vs_retenue`, `statut_revision`, `mention_retraitement` (note du document), `rupture_serie` / `detail_rupture` ; règle : spécification 5.2 |
| `variations_comparables.csv` | Variations sur un an calculées dans un même document (source de toutes les croissances du rapport) |
| `controle_annuel.csv` | Somme des 4 trimestres retenus contre cumul T4 retenu : `ok`, `en attente de révision`, `rupture de série`, `ecart` |
| `controle_extraction.csv` | Statut de chaque document : `ok`, `retraitement possible`, `ecart trimestre/cumul`, `ecart composantes`, `saisie manuelle`, `a verifier`, `illisible (image)`, `echec`, `pdf manquant` |
| `manifeste_telechargements.csv` | URL et fichier de chaque document |
| `dim_indicateur.csv`, `dim_banque.csv` | Codes, libellés, catégorie et nature (flux / stock) des indicateurs ; codes et noms des banques (l'actionnariat est dans `donnees_reference/banques.xlsx`) |
| `pdf/<BANQUE>/` | Les PDF sources (jamais modifiés) |

Colonnes de valeurs (`colonne`) : `trim_N` (trimestre seul), `cumul_N` (cumul depuis le 1er janvier,
ou solde à la date pour un stock), `trim_N1`, `cumul_N1` (un an plus tôt), `exercice_N1` (fin de
l'exercice précédent). `valeur_mdt` est en millions de dinars, quelle que soit l'unité du document.
CSV séparés par `;`, décimales avec un **point**, UTF-8 avec BOM : dans Power Query, les types se
fixent avec les paramètres régionaux Anglais (États-Unis).

### Contrôles (`controle_extraction.csv`)

- produits − charges d'exploitation = PNB (à 2 % près), dans chaque colonne ;
- au T1, trimestre = cumul ; aux autres trimestres, trimestre ≤ cumul ;
- ordres de grandeur plausibles (PNB, charges opératoires, crédits, dépôts, capitaux propres,
  coefficient d'exploitation, crédits / dépôts) ;
- `ecart trimestre/cumul` : le trimestre publié diffère de plus de 0,1 % de « cumul du trimestre
  − cumul du trimestre précédent » (retraitement de la banque en cours d'année) ;
- `ecart composantes` : les charges opératoires publiées ne correspondent pas à leurs composantes
  selon la définition du gabarit (incohérence de la banque, vérifiée dans le PDF, rien n'est corrigé) ;
- `retraitement possible` : le cumul N-1 d'un document diffère du cumul N publié un an plus tôt.

Une colonne de comparaison (N-1) fausse dans le document de la banque n'est jamais retenue :
automatiquement si produits − charges ≠ PNB, sinon par une ligne de `exclusions_colonnes.csv`
(raison, fichier, page).

## 3. États financiers : ROE et ROA (`scripts/etats_financiers.py`)

```
python scripts/etats_financiers.py tout
python scripts/etats_financiers.py telecharger --banques BIAT,UIB --rafraichir-liste-cmf
python scripts/etats_financiers.py telecharger --bulletins   # + Bulletins Officiels du CMF (lent)
python scripts/etats_financiers.py extraire
python scripts/etats_financiers.py verifier                  # comparaison à ilboursa (informative)
```

`--debut` et `--fin` sont des années (exercices). États financiers **individuels** annuels (31/12,
2019 →) et semestriels (30/06, 2020 →) : site de la BVMT, puis liste des états financiers du CMF,
puis Bulletins Officiels. Valeurs extraites : résultat net (**avant modifications comptables**),
total de l'actif, total des capitaux propres. Même règle des versions que les indicateurs
(`etats_financiers_versions.csv`).

Contrôles : total actif = total passif et capitaux propres, résultat de l'état de résultat =
résultat inscrit au bilan (bloquants) ; recoupement avec les capitaux propres trimestriels selon la
définition de chaque banque (non bloquant). La comparaison avec ilboursa
(`verification_ilboursa.csv`) est purement informative (comptes probablement consolidés).

Fichiers produits : `etats_financiers_long.csv`, `etats_financiers_versions.csv`,
`controle_etats_financiers.csv`, `verification_ilboursa.csv`, `manifeste_etats_financiers.csv`,
`pdf_etats_financiers/`.

## 4. Cours boursiers (`scripts/cours_boursiers.py`)

```
python scripts/cours_boursiers.py telecharger       # archives BVMT + bulletins de l'année + volumes
python scripts/cours_boursiers.py extraire --banques BIAT
python scripts/cours_boursiers.py operations        # écrit operations_titres.csv (versionné)
python scripts/resume_cours.py                      # résumé par banque, en lecture seule
```

Archives annuelles de la BVMT (2019–2025), bulletins quotidiens de la Bourse pour l'année en cours
(cours), volumes d'ilboursa pour 2026. Python ne fait que la lecture : les ajustements
(dividendes, attributions gratuites, division du nominal) se calculent dans Power Query à partir de
`operations_titres.csv`, qui donne pour chaque opération le cours de référence publié par la Bourse.
Sortie : `donnees/cours_banques.csv`.

## 5. Tests

```
python -m pytest tests
```

Comparaison de l'extraction aux valeurs relevées à la main sur l'image des PDF
(`tests/valeurs_reference.csv`, `tests/valeurs_reference_ef.csv`), et tests des règles (versions,
saisies, exclusions, écarts annuels expliqués, lecture des cours, robots.txt). Les tests sur les
vrais documents demandent les PDF de `donnees/` ; ils sont sautés s'ils sont absents.

## 6. Outils de vérification (lecture seule)

| Commande | Usage |
|---|---|
| `python scripts/diagnostic_pdf.py donnees/pdf/BT/BT_2024T2.pdf` | Colonnes détectées, en-tête par colonne, unité annoncée, lignes reconnues ou non |
| `python scripts/essai_banque.py ATB` | Extraction d'une banque seule avec son gabarit, sans rien écrire |
| `python scripts/couche_texte.py BH` | Caractères et images par page : repère les PDF scannés |
| `python scripts/rendre_pages.py donnees/pdf/BTE/BTE_2022T1.pdf 1,2 200` | Image PNG des pages, pour comparer une valeur au document |
| `python scripts/verifier_texte_pdf.py UIB 2025T3 PNB N1` | Les valeurs extraites figurent-elles dans le texte de la page ? |
| `python scripts/bilan_extraction.py` | Bilan par banque ; écrit `docs/revisions_importantes.csv` |
| `python scripts/analyse_ecarts.py [BANQUE]` | Origine de chaque valeur d'un écart du contrôle annuel, document par document (cause à écrire dans `docs/ecarts_annuels.csv`) |
| `python scripts/chercher_actionnariat.py "donnees/pdf_etats_financiers/BTE/*.pdf"` | Pages qui décrivent la structure du capital |
| `python scripts/lire_site.py DOSSIER URL…` | Lecture polie de quelques pages d'un site (robots.txt, 2 s au moins), réponses enregistrées |

**Outils du projet Power BI** (écrivent le modèle TMDL de `powerbi/SecteurBancaireTunisien.SemanticModel/`,
fins de ligne CRLF comme Power BI ; à lancer seulement quand ce projet est fermé dans Power BI Desktop,
sinon un enregistrement dans Power BI efface la modification) :

| Commande | Usage |
|---|---|
| `ecrire_table(nom, description, colonnes, apres)` (`scripts/ecrire_tmdl_table.py`, depuis Python) | Ajoute ou remplace une table chargée : colonnes typées, code M de `powerquery/<nom>.pq`, ordre des requêtes |
| `python scripts/ecrire_tmdl_expression.py NOM "description" APRES` | Ajoute ou remplace une requête intermédiaire non chargée dans `expressions.tmdl` |
| `ecrire_table_calculee(nom, description, colonnes, tri, cachees, table_de_dates)` (même fichier) ; `python scripts/ecrire_tmdl_table.py Dim_Date` | Ajoute ou remplace une table calculée DAX : colonnes typées, code de `dax/<nom>.dax`, colonnes de tri, colonnes masquées, marquage en table de dates |
| `python scripts/generer_theme.py` | Thème du rapport (`powerbi/theme/secteur_bancaire.json`), fonds de page signés 1 920 × 1 080 (`fond_page.png`, `fond_page_filtres.png`) et aperçu des icônes des banques (`icones_banques.png`) |
| `python scripts/ecrire_tmdl_table.py mesures` (`ecrire_mesures()` depuis Python) | Écrit la table `Mesures` depuis `dax/mesures.dax` (dossier, format et description de chaque mesure dans la ligne qui la précède) ; garde l'identifiant des mesures déjà écrites |
| `python scripts/ecrire_tmdl_table.py diagramme` (`ecrire_diagramme(onglets)` depuis Python) | Réécrit la disposition de la vue Modèle (`diagramLayout.json`) : onglet « Toutes les tables » et un onglet par thème (`DIAGRAMME` dans le script) |
| `python scripts/ecrire_tmdl_table.py relations` (`ecrire_relations(liste)` depuis Python) | Réécrit `relationships.tmdl` avec les relations du modèle en étoile (`RELATIONS` dans le script) ; chaque colonne doit exister ; une relation déjà présente garde son identifiant |
| `python scripts/ecrire_tmdl_segment.py` | Ajoute une colonne et remplace le code M d'une table sans toucher au reste du fichier, ajoute une fonction personnalisée ; sans argument, applique le segment d'actionnariat (déjà fait : relancer ne change rien) |

## 7. Fichiers de référence

- `donnees_reference/banques.xlsx` (table Excel `Banques`) : actionnariat des 12 banques, une ligne
  par période, source et page de chaque ligne ; règle de classement dans la spécification 5.3.
  Écrit par `python scripts/ecrire_banques_xlsx.py`, qui n'écrase pas un fichier modifié dans
  Excel sans `--ecraser` (reporter d'abord la modification dans le script, avec sa source).
- `evenements.csv`, `exclusions_colonnes.csv`, `saisies_manuelles.csv`, `gabarits.csv`,
  `operations_titres.csv` : voir le README et la spécification (5.1, 5.2, 7.5).
- `docs/ecarts_annuels.csv` : cause et source de chaque écart du contrôle annuel ; un nouvel écart
  fait échouer `test_ecarts_annuels_expliques` tant qu'il n'y est pas expliqué.

## 8. Données publiées (`donnees_publiees/`)

```
python scripts/publier_donnees.py
```

Régénère le dossier versionné `donnees_publiees/` à partir de `donnees/` : les CSV finaux lus par
Power BI (indicateurs, versions, variations comparables, contrôles, états financiers, cours,
dimensions, manifestes), sans PDF ni archive. La colonne `fichier` des manifestes et du contrôle des
états financiers est ramenée au nom du fichier. La commande refuse un fichier de plus de 50 Mo, un
chemin local ou un fichier non décrit dans `donnees_publiees/LISEZMOI.md`. À relancer après chaque
extraction, avant le commit.

## 9. Documents PDF de `docs/`

```
python scripts/generer_pdf.py          # les trois documents
python scripts/generer_pdf.py guide    # seulement le guide Power BI (quelques secondes)
```

Régénère `docs/Specification_projet.pdf` (rendu de `docs/SPECIFICATION.md`),
`docs/Guide_PowerBI.pdf` (rendu de `docs/guide_powerbi.md` : chaque transformation Power Query et
chaque mesure DAX expliquée, avec en annexe le code M de chaque requête et la feuille de route) et
`docs/Rapport_avancement.pdf` (chiffres recalculés à partir des fichiers du projet, tests relancés :
environ une minute). À relancer après chaque extraction ou modification de la spécification ; le
guide, après chaque requête ou groupe de mesures.
Conversion par Microsoft Edge en mode headless (chemin modifiable par la variable `EDGE`).

## 10. Avant de publier (push)

```
python scripts/audit_publication.py
```

Le dépôt est public. L'audit lit tout l'historique git, l'index et les nouveaux fichiers : aucun
fichier suivi ne doit correspondre à une exclusion (`.gitignore`, `.git/info/exclude`), aucun nom
interdit, secret ou chemin personnel ne doit apparaître (texte, texte et métadonnées des PDF,
contenu des fichiers Excel), ni dans les messages de commit ; les adresses e-mail trouvées sont
listées ; un fichier suivi de plus de 50 Mo fait aussi échouer l'audit. Les noms interdits sont lus dans `.git/info/noms_interdits` (fichier local, un nom par
ligne). Code de sortie 1 en cas de problème.
