<!-- Auteur : Ahmed Ben Arfa -->
# Note de validation des données

Cette note dit comment on s'est assuré que les chiffres du rapport sont bien ceux que les banques ont publiés, et ce
que cette vérification ne garantit pas. Elle porte sur l'extraction (lecture des PDF par le script Python) ; les
calculs de Power BI (mesures DAX) sont contrôlés à part, mesure par mesure, contre des valeurs calculées
indépendamment (`docs/guide_powerbi.md`, section 3).

Situation au 05/11/2026 : 336 documents d'indicateurs trimestriels (12 banques × 28 trimestres, T4 2019 → T3 2026),
168 arrêtés d'états financiers, 11 545 valeurs retenues.

## 1. Principe

Une valeur de référence est **lue à l'œil sur l'image de la page du PDF** (page rendue en image, et non le texte que
lit le script), avec son unité, puis convertie en millions de dinars. Le test la compare à ce que le script extrait du
même document : même valeur (à l'arrondi de calcul près, écart relatif de 10⁻⁹), même page, même unité. Une seule
différence fait échouer le test. Les références sont dans deux fichiers versionnés :

- `tests/valeurs_reference.csv` (indicateurs trimestriels), test `test_valeurs_reference` de
  `tests/test_extraction.py` ;
- `tests/valeurs_reference_ef.csv` (états financiers), test `test_valeurs_reference_ef` de
  `tests/test_etats_financiers.py`.

Ces tests sont relancés après chaque modification du script : une correction qui améliorerait une banque et en
abîmerait une autre est vue tout de suite.

## 2. Échantillon choisi : indicateurs trimestriels

**438 valeurs sur 41 documents, les 12 banques.** Les documents ont été choisis, et non tirés au hasard : pour chaque
banque, au moins deux documents de périodes différentes, relevés au moment où son gabarit de mise en page a été
écrit (les mises en page changent d'une année à l'autre), puis des documents difficiles (tableau en lettres
espacées, colonnes collées, libellé sur trois lignes, document retrouvé sur le site de la banque…).

| Répartition | Détail |
|---|---|
| Documents par banque | AB 3, ATB 2, BH 2, BIAT 8, BNA 2, BT 2, BTE 3, STB 3, Attijari 3, UBCI 2, UIB 8, Wifak 3 |
| Documents par année | 2019 : 2 ; 2020 : 7 ; 2021 : 4 ; 2022 : 4 ; 2023 : 3 ; 2024 : 5 ; 2025 : 9 ; 2026 : 7 |
| Rang du trimestre | T1 : 7 ; T2 : 19 ; T3 : 7 ; T4 : 8 |
| Indicateurs | PNB 150, charges opératoires 76, crédits 41, dépôts 40, capitaux propres 31, frais de personnel 24, charges générales 24, produits 19, charges 13, autres 20 |
| Colonnes | cumul ou solde de l'année 277, trimestre seul 83, colonnes de l'année précédente 78 |
| Unités | milliers de dinars 317, dinars 121 |

**Résultat : 438 valeurs sur 438 identiques** (même valeur, même page, même unité).

## 3. Échantillon tiré au hasard : indicateurs trimestriels

Pour éviter qu'un échantillon choisi ne laisse de côté un défaut, **10 documents ont été tirés au hasard** le
05/11/2026 parmi les 278 qui n'avaient jamais servi de référence (hors documents publiés en image et saisis à la
main), avec une graine fixe pour que le tirage puisse être refait :

```python
candidats = sorted(fichiers des 336 documents, sans les 41 de référence, les 13 saisis et les 2 illisibles)
tires = random.Random(20261105).sample(candidats, 10)
```

Sur chacun, quatre valeurs ont été lues sur l'image de la page 1 (cumul depuis janvier, ou solde) et comparées à
l'extraction :

| Document | PNB | Charges opératoires | Crédits | Dépôts | Unité | Résultat |
|---|---|---|---|---|---|---|
| ATB 2026T3 | 283 611 | 206 370 | 4 997 117 | 6 759 408 | milliers de dinars | 4/4 |
| BH 2024T1 | 166 214 | 68 272 | 10 452 265 | 8 661 199 | milliers de dinars | 4/4 |
| BIAT 2020T1 | 241 981 243,561 | 103 646 636,572 | 10 541 699 432,488 | 12 305 852 616,119 | dinars | 4/4 |
| BIAT 2022T4 | 1 263 986 090,538 | 496 512 436,305 | 12 278 171 252,892 | 17 166 843 065,666 | dinars | 4/4 |
| BIAT 2023T1 | 357 256 921,467 | 128 420 220,080 | 12 021 949 428,075 | 16 795 923 767,072 | dinars | 4/4 |
| BT 2024T4 | 510 310 | 154 329 | 6 077 377 | 6 695 429 | milliers de dinars | 4/4 |
| STB 2019T4 | 598 686 095 | 219 340 198 | 7 885 183 516 | 7 371 515 898 | dinars | 4/4 |
| UBCI 2020T2 | 106 638 | 83 994 | 2 432 767 | 2 614 461 | milliers de dinars | 4/4 |
| UBCI 2021T4 | 263 221 | 179 650 | 2 568 474 | 3 084 700 | milliers de dinars | 4/4 |
| UBCI 2026T2 | 193 450 | 125 653 | 4 032 070 | 4 271 052 | milliers de dinars | 4/4 |

**Résultat : 40 valeurs sur 40 identiques.** Le hasard a désigné 6 banques sur 12 (trois documents BIAT et trois
UBCI) : ce tirage complète l'échantillon choisi, il ne le remplace pas. Les 40 valeurs ont été ajoutées à
`tests/valeurs_reference.csv` (note « tirage au hasard du 05/11/2026 »), qui compte désormais **478 valeurs sur 51
documents**, toutes conformes.

## 4. États financiers

**169 valeurs sur 24 documents, les 12 banques** (13 comptes annuels au 31/12, 11 semestriels au 30/06) : résultat
net 42, capitaux propres 42, total de l'actif 40, et des lignes de contrôle (total du passif et des capitaux propres,
résultat inscrit au bilan, résultat après modifications comptables, effet des modifications comptables). Les
documents ont été choisis comme pour les indicateurs : un par banque au moment de l'écriture de ses règles, puis les
cas difficiles (colonnes de reprise, nombre mal formé, ligature dans le PDF). **Résultat : 169 valeurs sur 169
identiques.**

## 5. Contrôles de cohérence sur toutes les données

L'échantillon ne voit que les valeurs relevées ; les contrôles suivants portent sur **toutes** les valeurs, à
chaque extraction :

- **Produits − charges = PNB**, dans chaque colonne de chaque document : une colonne de l'année précédente
  incohérente n'est jamais retenue (cas trouvés : UIB 2023T2, colonne du T2 2022 qui contenait le cumul du semestre ;
  Wifak 2023T4, colonne du T4 2022 qui recopiait le T3 2022 ; erreurs des documents des banques, vérifiées sur
  l'image).
- **PNB = marge d'intérêts + marge sur commissions + revenus du portefeuille**, à 0,05 MDT près, sur 1 468
  versions ; seules exceptions, expliquées : la BTE (gains de change publiés sans ligne propre) et la BT au T2 et au
  T3 2026 (pertes sur portefeuille publiées à part).
- **Somme des quatre trimestres = cumul annuel** (288 contrôles, banque × année × indicateur) : 205 conformes, 41
  en attente de la révision de l'année suivante, 20 ruptures de série, **22 écarts, tous expliqués avec leur
  source** (`docs/ecarts_annuels.csv` : 11 retraitements de la banque, 7 erreurs dans le document de la banque,
  3 reclassements, 1 arrondi, **0 erreur d'extraction**).
- **Capitaux propres des états financiers − résultat = capitaux propres trimestriels publiés**, à la même date :
  131 concordent, 17 écarts expliqués (spécification 5.2), 14 non comparables (AB et BIAT au 31/12 : capitaux
  propres après affectation du résultat), 6 impossibles (4 dates BTE sans capitaux propres trimestriels publiés ;
  BH au 31/12/2019 et STB au 30/06/2023, états financiers publiés en image, repris du document suivant).
- **Ordres de grandeur et unité** : l'unité est fixée par le gabarit de chaque banque et contrôlée par l'en-tête du
  document et par l'ordre de grandeur du PNB.

## 6. Valeurs saisies à la main

**682 valeurs** n'ont pas pu être lues par le script : 13 documents BTE dont le tableau est une image, deux valeurs
STB du T2 2026 imprimées sur leur libellé, deux valeurs Wifak du T2 2026 dont les colonnes se touchent. Chacune est
dans `saisies_manuelles.csv` avec le fichier, la page et la façon dont elle a été vérifiée ; toutes passent les
contrôles de la section 5 (produits − charges = PNB, frais + charges générales = charges opératoires, variation
publiée = N − N-1, dépôts = somme de leurs catégories). Le document BTE du T2 2020 a été relu une seconde fois en
entier, indépendamment, par l'auteur (36 valeurs).

## 7. Erreurs trouvées et corrigées par ces vérifications

Les contrôles ont servi : ils ont fait trouver, avant toute utilisation dans le rapport, entre autres :

- Wifak T2 2026 : deux nombres de deux colonnes voisines lus comme un seul (revenus du portefeuille 607,829 MDT au
  lieu de 0,723) ; trouvé par le contrôle des composantes du PNB, corrigé par saisie (section 6) ;
- STB T2 2026 : revenus du portefeuille imprimés sur leur libellé (893 522 lu au lieu de 115 893 522 dinars) ;
- AB T1 2021 : le document retenu était une note d'émission d'emprunt qui ne faisait qu'annoncer les indicateurs ;
  remplacé par le document de la Bourse, et une règle écarte désormais ce genre d'extrait ;
- UBCI T4 2019 : colonnes de 2018 et de 2019 dans l'ordre inverse des autres années (de fausses « corrections » de
  −11,7 % en venaient) ; réglé par le gabarit ;
- unités : plusieurs « erreurs × 1 000 » venaient d'une unité devinée (BTE, UBCI) ; l'unité est désormais fixée par
  le gabarit et seulement contrôlée par le document.

## 8. Ce que cette validation ne garantit pas

- **Un échantillon ne prouve pas l'absence d'erreur** : 478 valeurs relevées sur 11 545 retenues (4 %). Les
  contrôles de la section 5 couvrent tout, mais seulement pour les erreurs qu'ils savent voir (une valeur fausse qui
  respecte toutes les égalités passerait).
- **Une valeur conforme au PDF n'est pas une valeur exacte** : les indicateurs trimestriels sont provisoires et non
  audités, et les banques les révisent souvent (813 révisions de plus de 2 % entre deux documents ; la version
  révisée est retenue). Les comptes semestriels ne sont pas audités (revue limitée).
- **Les relevés sont faits par une seule personne**, sauf le document BTE du T2 2020, relu par une seconde.
- **Les définitions diffèrent d'une banque à l'autre** (contenu des charges opératoires, capitaux propres avec ou
  sans résultat) : les comparaisons du rapport utilisent des définitions communes (coefficient d'exploitation
  harmonisé, capitaux propres du bilan), et les définitions propres à chaque banque sont affichées sur sa fiche.

## 9. Refaire la vérification

```
python -m pytest tests                       # 50 tests, dont les deux comparaisons aux valeurs de référence
python tests/test_extraction.py              # détail des 478 comparaisons, valeur par valeur
python scripts/rendre_pages.py <pdf> <pages> [dpi]   # rendre des pages en image pour relever une valeur
```

Les PDF sources (non versionnés) se retéléchargent avec `python collecte_banques.py telecharger` et
`python scripts/etats_financiers.py telecharger` (mode d'emploi : `docs/utilisation.md`).
