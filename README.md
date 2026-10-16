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
3. En dernier recours, les Bulletins Officiels quotidiens du CMF publiés dans les 45 jours
   après la fin du trimestre : seules les pages de la banque sont gardées.

Chaque PDF est vérifié : il doit citer la date d'arrêté du trimestre visé.

## Fichiers produits (dossier `donnees/`)

| Fichier | Contenu |
|---|---|
| `indicateurs_banques_long.csv` | Table de faits : une ligne par banque × trimestre × indicateur × colonne |
| `controle_extraction.csv` | Statut de chaque document : ok, retraitement possible, a verifier, echec, pdf manquant |
| `manifeste_telechargements.csv` | URL et fichier de chaque document |
| `dim_indicateur.csv` | Codes, libellés, catégorie et nature (flux / stock) |
| `dim_banque.csv` | Banques — complétez les colonnes `actionnariat` et `groupe` à la main |
| `pdf/<BANQUE>/` | Les PDF sources |

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

## Contrôles (`controle_extraction.csv`)

- produits − charges d'exploitation = PNB (à 2 % près) ;
- PNB cumulé présent ; au T1, trimestre = cumul ; aux autres trimestres, trimestre ≤ cumul ;
- ordres de grandeur plausibles (PNB, charges opératoires, crédits, dépôts, capitaux propres,
  coefficient d'exploitation, crédits / dépôts) ;
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
- Les PDF scannés (images) ne sont pas lisibles : statut `echec`, saisie manuelle nécessaire.
- Vérifiez à la main toutes les lignes `a verifier` du fichier de contrôle,
  et quelques lignes `ok` au hasard contre les PDF.
- Ces indicateurs sont provisoires et non audités.
