# Collecte des indicateurs trimestriels des banques cotées (BVMT)

Télécharge les indicateurs d'activité trimestriels des 12 banques cotées
(AB, ATB, Attijari, BH, BIAT, BNA, BT, BTE, STB, UBCI, UIB, Wifak),
de T4 2019 jusqu'au dernier trimestre publié, puis les transforme en CSV pour Power BI.

## Installation

```
python -m pip install -r requirements.txt
```

## Lancement

```
python collecte_banques.py tout
```

Autres commandes utiles :

```
python collecte_banques.py telecharger --banques UIB,BIAT --debut 2024T1 --fin 2026T3
python collecte_banques.py telecharger --sans-bulletins     # plus rapide, sites seulement
python collecte_banques.py extraire                          # relance seulement l'extraction
python collecte_banques.py urls --banques BH --debut 2025T2 --fin 2025T2   # URL testées
```

Le script peut être relancé : les PDF déjà trouvés ne sont pas retéléchargés.
Durée : de quelques minutes à environ une heure si beaucoup de documents
doivent être cherchés dans les Bulletins Officiels (une pause est faite entre les requêtes).

## Où le script cherche

1. Pages société du site de la BVMT
   (`/societes/<banque>/indicateurs-dactivite-trimestriels/<banque>-indicateurs-dactivite-trimestriels-JJ-MM-AAAA.pdf`).
2. Dossier des indicateurs du site du CMF (`indic_2trim26_uib.pdf`, `ind_2eme_trim_2026_biat.pdf`…).
3. Pour les documents encore manquants : la liste des indicateurs publiée par le CMF
   (`https://www.cmf.tn/?page=1&q=indicateurs-d-activit-`). Les liens sont gardés dans
   `donnees/liste_indicateurs_cmf.csv` ; option `--rafraichir-liste-cmf` pour relire la liste
   (par exemple après le 20 du mois qui suit un trimestre), `--sans-liste-cmf` pour sauter l'étape.
   Chaque PDF candidat est vérifié (date d'arrêté et nom de la banque dans le document).
4. En dernier recours, les Bulletins Officiels quotidiens du CMF publiés dans les 45 jours
   après la fin du trimestre : seules les pages de la banque sont gardées.

Chaque PDF est vérifié : il doit citer la date d'arrêté du trimestre visé.

## Fichiers produits (dossier `donnees/`)

| Fichier | Contenu |
|---|---|
| `indicateurs_banques_long.csv` | Valeurs brutes : une ligne par document × indicateur × colonne lue |
| `indicateurs_versions.csv` | Table pour Power BI : une ligne par banque × période × indicateur × mesure (trim / cumul) × version (`initiale` = document du trimestre ; `revisee_T<q>_N+1` = colonne N-1 du document de l'année suivante ; `revisee_31-12_T<q>_N+1` = colonne 31/12/N-1 d'un T1–T3 suivant, provisoire, pour le cumul annuel et les soldes au 31/12 seulement), avec `valeur_retenue`, `source_valeur`, `ecart_vs_retenue`, `statut_revision` (la version révisée est toujours retenue ; écart mesuré sur le cumul : `retraitement_mineur` jusqu'à 2 %, `revision_importante` au-delà ; même statut pour le trimestre et le cumul de la période ; les composantes suivent leur total ; `reclassement` à total stable), `mention_retraitement` (la note du document) et `rupture_serie` / `detail_rupture` (période révisée de plus de 2 % sur le cumul, pour annoter les graphiques) ; règle : `docs/SPECIFICATION.md`, 5.2 |
| `variations_comparables.csv` | Variations sur un an calculées dans un même document : valeur N, valeur N-1 de la même colonne de comparaison, variation en % (source de toutes les croissances du rapport) |
| `controle_annuel.csv` | Somme des 4 trimestres retenus vs cumul T4 retenu : `ok`, `en attente de révision`, `rupture de série`, `ecart` |
| `controle_extraction.csv` | Statut de chaque document : ok, retraitement possible, ecart trimestre/cumul, ecart composantes, saisie manuelle, a verifier, illisible (image), echec, pdf manquant |
| `manifeste_telechargements.csv` | URL et fichier de chaque document |
| `dim_indicateur.csv` | Codes, libellés, catégorie et nature (flux / stock) |
| `dim_banque.csv` | Banques — complétez les colonnes `actionnariat` et `groupe` à la main |
| `pdf/<BANQUE>/` | Les PDF sources |

Fichiers versionnés à la racine (lus par le script ou par Power BI) :

| Fichier | Contenu |
|---|---|
| `gabarits.csv` | Mise en page de chaque banque par période : ordre des colonnes, unité, libellés, contenu des charges opératoires |
| `saisies_manuelles.csv` | Valeurs relevées sur l'image des tableaux publiés en image (BTE 2020–2021), avec fichier, page et vérification |
| `evenements.csv` | Événements à annoter dans Power BI (don au Fonds 1818 en 2020, accord salarial du secteur en 2021, retraitement BH 2024), avec la source PDF et la page |

Colonnes de valeurs (`colonne`) :

- `trim_N` : le trimestre seul ; `trim_N1` : le même trimestre de l'année précédente
- `cumul_N` : cumul depuis le 1er janvier (ou solde à la date pour les stocks) ; `cumul_N1` : idem un an plus tôt
- `exercice_N1` : fin de l'exercice précédent

`valeur_mdt` est en millions de dinars, quelle que soit l'unité du document
(l'unité est déduite de l'ordre de grandeur du PNB), avec 9 décimales pour garder le millime.

## Lecture des tableaux

Les montants sont alignés à droite : le script repère le bord droit de chaque colonne de
chiffres sur la page, rattache chaque morceau de nombre (« 6 », « 479 », « 908 ») à sa colonne,
puis le recolle. Il se fie à la position sur la page, pas à l'ordre du texte du PDF (qui est
parfois inversé). Le nom de chaque colonne (trimestre / cumul, année N / N-1, exercice N-1)
est lu dans l'en-tête du tableau ; si l'en-tête n'est pas lisible, l'ordre habituel est supposé
et le document passe en `a verifier`.

**Gabarits (`gabarits.csv`)** : pour chaque banque et chaque période de mise en page
(premier et dernier trimestre, trimestres concernés), l'ordre des colonnes, l'unité et les
libellés particuliers (`CODE=regex`, séparés par `||`), et le contenu des charges opératoires
publiées (`definition_charges_operatoires` : `sans dotations`, `avec dotations publiees`,
`avec reste non detaille`, `composantes non publiees`). Quand un gabarit existe, il décide ;
la lecture de l'en-tête et l'unité déduite du PNB deviennent des contrôles qui signalent tout
désaccord. Le nom du gabarit appliqué figure dans `controle_extraction.csv` et dans les données.

## Contrôles (`controle_extraction.csv`)

- produits − charges d'exploitation = PNB (à 2 % près) ;
- PNB cumulé présent ; au T1, trimestre = cumul ; aux autres trimestres, trimestre ≤ cumul ;
- ordres de grandeur plausibles (PNB, charges opératoires, crédits, dépôts, capitaux propres,
  coefficient d'exploitation, crédits / dépôts) ;
- `ecart trimestre/cumul` : le trimestre publié diffère de plus de 0,1 % de « cumul du trimestre
  − cumul du trimestre précédent » (document précédent de la même année). Cas constaté au T3 2025
  chez BIAT et UIB : le premier semestre a été retraité après la publication du T2. Règle dans
  Power BI : cumul publié pour l'année et le cumul annuel, trimestre publié pour l'analyse
  trimestrielle (voir `docs/SPECIFICATION.md`, section 5.2) ;
- `ecart composantes` : les charges opératoires publiées ne correspondent pas à leurs composantes
  selon la définition du gabarit (ex. BT 2020T3, BNA 2023T2 : vérifié dans le PDF, c'est la
  banque qui publie des chiffres incohérents ; rien n'est corrigé) ;
- `retraitement possible` : le cumul N-1 d'un document diffère du cumul N publié un an plus tôt
  pour le même trimestre. Ce sont souvent de vrais retraitements de la banque (signalés « chiffres
  retraités » dans le PDF) ; on garde le chiffre de l'année N tel que publié dans le document de l'année N.

## Test de l'extraction

```
python tests/test_extraction.py     # ou : python -m pytest tests
```

Compare l'extraction aux valeurs relevées à la main dans les PDF (`tests/valeurs_reference.csv` :
PNB du trimestre et cumulé, charges opératoires, crédits, dépôts, avec la page). Les PDF ne sont
pas versionnés : il faut les avoir téléchargés avant de lancer le test.

CSV séparés par `;`, décimales avec un **point** : dans Power Query, changez le type
avec « Utilisation des paramètres régionaux » → Anglais (États-Unis).

## États financiers (ROE et ROA)

```
python scripts/etats_financiers.py tout
```

Télécharge les états financiers **individuels** annuels (31/12, 2019 →) et semestriels
(30/06, 2020 →) sur le site de la BVMT, en extrait le résultat net, le total de l'actif et le total
des capitaux propres, puis compare le résultat net annuel à ilboursa.
Option `--bulletins` (avec `telecharger`) : cherche aussi dans les Bulletins Officiels du CMF.

Fichiers produits : `etats_financiers_long.csv`, `controle_etats_financiers.csv`,
`verification_ilboursa.csv`, `manifeste_etats_financiers.csv`, `pdf_etats_financiers/`.

## Limites — à lire avant d'utiliser les chiffres

- L'extraction n'a été vérifiée à la main que sur 12 documents réels de deux banques
  (BIAT et UIB, T1 2025 → T2 2026). Les autres banques et les années plus anciennes ont
  d'autres mises en page : les premiers lancements révéleront des cas à ajouter.
- Le site de la BVMT renvoie des pages vides aux scripts : seuls les liens directs vers les PDF
  fonctionnent. Les noms de fichiers changent d'une période à l'autre.
- Les PDF scannés (images) ne sont pas lisibles : statut `echec`, saisie manuelle nécessaire
  (cas connus : BH 2019T4 ; BTE, 13 documents de 2020 à 2023). Quand le document suivant ne
  reprend pas les chiffres, ils sont saisis dans `saisies_manuelles.csv` (BTE 2020T1 à 2020T4,
  2021T1 et 2021T3), relus sur l'image et contrôlés ; statut `saisie manuelle`. Une valeur
  illisible dans un document lisible peut aussi y être saisie (STB 2026T2, revenus du portefeuille).
  Une mesure qu'aucun document lisible ne donne (BTE : T4 seul 2021 et 2022) est marquée
  « non disponible (image) » dans `indicateurs_versions.csv`, sans valeur (jamais zéro).
  Vérification par une personne : `python scripts/verification_saisie.py preparer BTE 2020T2`,
  remplir la colonne « verification », puis `... reporter BTE 2020T2`.
- Vérifiez à la main toutes les lignes `a verifier` du fichier de contrôle,
  et quelques lignes `ok` au hasard contre les PDF.
- Ces indicateurs sont provisoires et non audités.
