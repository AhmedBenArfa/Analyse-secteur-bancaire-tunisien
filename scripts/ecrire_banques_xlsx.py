# Auteur : Ahmed Ben Arfa
"""Utilisation : python scripts/ecrire_banques_xlsx.py [--ecraser]
Écrit donnees_reference/banques.xlsx : actionnariat des 12 banques (actionnaire de référence, part du
capital, classement selon le contrôle, groupe), une ligne par période, avec la source et la page de
chaque ligne (relevées le 22/10/2026 ; règle de classement : docs/SPECIFICATION.md, 5.3).
Le fichier Excel versionné est la référence lue par Power BI. Si le fichier existe et que son contenu
diffère de celui du script (modification faite dans Excel), rien n'est écrit sans --ecraser : reporter
d'abord la modification ici, avec sa source.
"""
import datetime as dt
import sys
from pathlib import Path
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment
from openpyxl.worksheet.table import Table, TableStyleInfo

SORTIE = Path(__file__).resolve().parent.parent / "donnees_reference" / "banques.xlsx"
D = lambda s: dt.date.fromisoformat(s) if s else None
TSE = "https://www.tunis-stockexchange.com/informations-"
R4 = "rubrique 4 « Principaux actionnaires »"
CMF = "liste des états financiers du CMF, "
L = [
 ("AB", "Amen Bank", "Assurances COMAR", 28.76, "privé sans contrôle étranger", "COMAR / PGI Holding", "2026-04-30",
  f"Bourse de Tunis, fiche émetteur (AGO du 30/04/2026) : {TSE}amen-bank", R4, "", "",
  "PGI Holding 20,39 %, Ennakl Automobiles 7,93 %, autres moins de 5 %. 31/12/2019 : COMAR 30,65 %, PGI Holding 22,18 % "
  "(AB_EF_2019-12.pdf p. 50) : même actionnaire de référence. Aucun actionnaire public ou étranger au-dessus de 5 %."),
 ("ATB", "Arab Tunisian Bank", "Arab Bank PLC", 64.24, "groupe étranger", "Arab Bank", "2026-04-28",
  f"Bourse de Tunis, fiche émetteur (AGO du 28/04/2026) : {TSE}atb", R4, "", "",
  "31/12/2019 : Arab Bank PLC 64,24 % (rapport annuel ATB 2019, p. 14, atb.tn) : majorité absolue, inchangée."),
 ("TJARI", "Attijari Bank", "Andalu Carthage Holding", 57.21, "groupe étranger", "Attijariwafa bank", "2026-04-10",
  f"Bourse de Tunis, fiche émetteur (AGO du 10/04/2026) : {TSE}attijari-bank", R4, "", "",
  "Groupe Mzabi 9,94 %, groupe Driss 9,54 %. Plaquette financière Attijari bank d'avril 2022, p. 1 (attijaribank.com.tn) : "
  "« à travers la participation de la société Andalucarthage Holding, le Groupe Attijariwafa bank est l'actionnaire de "
  "référence qui détient la majorité des droits de vote et assure le contrôle de l'institution » (58,98 % au 31/12/2021). "
  "2019 : Attijariwafa bank s'engage à maintenir au moins 55 % du capital (TJARI_EF_2019-12.pdf p. 14)."),
 ("BH", "BH Bank", "État tunisien", 33.37, "public", "État tunisien", "2025-12-31",
  "Rapport annuel BH Bank 2025 (rapport à l'AGO, bhbank.tn, RAPPORT-2025-AGO-BHBANK.pdf)", "19 (page 21 du PDF)", "", "",
  "Tableau « Actionnariat » : État tunisien 33,37 %, entreprises publiques 22,26 % (dont ETAP 16,57 %), entreprises "
  "parapubliques 1,02 %, personnes morales privées 28,70 %, personnes physiques 14,50 %, étrangers 0,10 %. État + "
  "entreprises publiques = 55,63 % : contrôle public. Fiche Bourse (AGO du 30/04/2026) : État 33,37 %, ETAP 16,57 %, groupe "
  "Horchani 23,19 %. BH_EF_2025-12_cmf.pdf p. 48 : « l'État tunisien (principal actionnaire) ». Actionnariat de 2019 non "
  "trouvé (bhbank.tn : rapport 2025 seulement)."),
 ("BIAT", "Banque Internationale Arabe de Tunisie", "Groupe Mabrouk", 38.75, "privé sans contrôle étranger", "Groupe Mabrouk", "2026-04-24",
  f"Bourse de Tunis, fiche émetteur (AGO du 24/04/2026) : {TSE}biat", R4, "", "",
  "Groupe Milad 15,01 %, groupe Tamarziste 9,27 %, groupe Horchani 8,74 %. 31/12/2019 : actionnaires tunisiens 98,8 %, "
  "étrangers 1,2 % (rapport annuel BIAT 2019, p. 51, biat.com.tn) ; l'actionnaire de référence de 2019 n'y est pas nommé."),
 ("BNA", "Banque Nationale Agricole", "État tunisien", 35.26, "public", "État tunisien", "2025-12-31",
  CMF + "BNA_EF_2025-12_cmf.pdf", "6", "", "",
  "Actionnaires publics 50,23 % (État 35,26 %, CNSS 4,26 %, Office des céréales 3,44 %, Office du commerce 2,90 %, ETAP…). "
  "Même total au 31/12/2019 (BNA_EF_2019-12.pdf p. 5). Fiche Bourse (AGO du 30/04/2026) : État 35,26 %."),
 ("BT", "Banque de Tunisie", "Banque Fédérative du Crédit Mutuel (BFCM)", 35.33, "privé sans contrôle étranger", "Crédit Mutuel (BFCM)",
  "2026-04-28", f"Bourse de Tunis, fiche émetteur (AGO du 28/04/2026) : {TSE}bt", R4, "", "",
  "Groupe El Fekih 10 %, groupe Kammoun 9,52 %, autres 45,15 %. BFCM = « entité exerçant une influence notable sur la BT » "
  "(BT_EF_2019-12.pdf p. 65), pas un actionnaire de contrôle : privé sans contrôle étranger."),
 ("BTE", "Banque de Tunisie et des Emirats", "État tunisien et Abou Dhabi Investment Authority (ADIA), à parts égales",
  38.9, "mixte", "État tunisien / ADIA", "2019-12-31", "BVMT, états financiers annuels : BTE_EF_2019-12.pdf", "25", "",
  "2024-06-30",
  "Chacun 38,9 % du capital et 50 % des droits de vote ; ADP 22,2 % sans droit de vote. Inchangé au 30/06/2024 "
  "(BTE_EF_2024-06.pdf p. 24). Contrôle conjoint public / étranger : mixte."),
 ("BTE", "Banque de Tunisie et des Emirats", "Abou Dhabi Investment Authority (ADIA)", 40.80, "mixte",
  "État tunisien / ADIA", "2024-12-31",
  "BVMT, états financiers annuels : BTE_EF_2024-12.pdf", "32", "2024-07-01", "",
  "Augmentation de capital (AGE prévue le 30/04/2024, BTE_EF_2023-12.pdf p. 42 ; décidée par l'AGE du 30/04/2024, "
  "BTE_EF_2024-06.pdf p. 32) : date exacte inconnue, entre le 30/06 et le 31/12/2024 (capital 90 000 → 108 744 kDT, "
  "BTE_EF_2024-12.pdf p. 31 ; aucune date dans les notes de 2024 et 2025) ; début de période fixé au 01/07/2024 pour que "
  "les périodes se suivent. Indice non confirmé : capitaux propres trimestriels 41,704 MDT au 30/06/2024 (BTE_2025T2.pdf "
  "p. 1) et 62,764 MDT au 30/09/2024 (BTE_2025T3.pdf p. 1). État 32,19 % (39 % des droits de vote), La Poste tunisienne 8,62 % (11 %), ADIA 40,80 % (50 %), "
  "ADP 18,39 %. Même structure à la fiche Bourse (AGO du 30/04/2026). Droits de vote : 50 % public (État + La Poste), "
  "50 % ADIA : contrôle conjoint, mixte."),
 ("STB", "Société Tunisienne de Banque", "État tunisien", 71.56, "public", "État tunisien", "2025-12-31",
  CMF + "STB_EF_2025-12_cmf.pdf", "6", "", "",
  "État 71,56 %, entreprises publiques 11,85 %. 31/12/2019 : État 71,54 %, entreprises publiques 11,85 % (STB_EF_2019-12.pdf p. 5)."),
 ("UBCI", "Union Bancaire pour le Commerce et l'Industrie", "BNP Paribas (BNP Paribas IRB Participations)", 50.085,
  "groupe étranger", "BNP Paribas", "2019-12-31", "BVMT, états financiers annuels : UBCI_EF_2019-12.pdf", "9", "", "2021-03-15",
  "Cession de 39 % au groupe Carte annoncée le 28/08/2019 ; réalisation annoncée le 16/03/2021 (UBCI_EF_2020-12.pdf p. 5 et 44) ; "
  "BNP Paribas garde 11,09 %."),
 ("UBCI", "Union Bancaire pour le Commerce et l'Industrie", "Groupe Carte", 39.86, "privé sans contrôle étranger", "Groupe Carte",
  "2026-04-28", f"Bourse de Tunis, fiche émetteur (AGO du 28/04/2026) : {TSE}ubci", R4, "2021-03-16", "",
  "Groupe Tamarziste 12,59 %, BNP Paribas 11,09 %, groupe Sellami 9,52 %. Début : date d'annonce de la réalisation de la cession."),
 ("UIB", "Union Internationale de Banques", "Société Générale", 52.34, "groupe étranger", "Société Générale", "2025-04-30",
  f"Bourse de Tunis, fiche émetteur (AGO du 30/04/2025) : {TSE}uib", R4, "", "",
  "Groupe Sassi 10,71 %, groupe Bouchamaoui 10,62 %, groupe Bouaziz 6,48 %. « Société mère Société Générale » "
  "(UIB_EF_2020-12.pdf p. 38) ; part de 2019 non relevée."),
 ("WIB", "Wifak International Bank", "Islamic Corporation for the Development of the Private Sector (ICD)", 30.00,
  "privé sans contrôle étranger", "ICD", "2019-12-31", "Rapport annuel Wifak Bank 2019 (wifakbank.com/rapports-annuels)", "12", "",
  "2021-12-31",
  "2019 : ICD 30 %, groupe STB 17,16 %, M. Mohamed Hédi Ben Ayed 11,93 %, CDC 10 %, MM. Hamrouni 6,61 % et 6,19 %, Medimix 5 %. "
  "31/12/2021 : ICD 30 %, groupe Ben Ayed 22,82 %, groupe STB 18,43 %, CDC 10 % (rapport annuel 2021, p. 13). Public (groupe "
  "STB + CDC) 27 à 28 % ; ICD, premier actionnaire sans majorité, n'est pas actionnaire de contrôle : privé sans contrôle "
  "étranger."),
 ("WIB", "Wifak International Bank", "Sociétés Mohamed Hédi Ben Ayed", 39.86, "privé sans contrôle étranger", "Groupe Ben Ayed",
  "2026-04-24", f"Bourse de Tunis, fiche émetteur (AGO du 24/04/2026) : {TSE}wifak-international-bank", R4, "2022-01-01", "",
  "Groupe Ben Ayed à 32,9 % « début 2022 » (rapport annuel 2021, p. 13 : date exacte non publiée, 01/01/2022 retenu), 39,5 % "
  "en 2022 (rapport 2022, p. 16), 39,86 % en 2023 (rapport 2023, p. 22). ICD 30 %, CDC 10 %, M. Abdellatif Hamrouni 9,99 %."),
]
COLS = ["code_banque", "nom", "actionnaire_reference", "part_capital_pct", "actionnariat", "groupe", "date_reference",
        "source", "page", "date_debut", "date_fin", "remarque"]
wb = Workbook()
ws = wb.active
ws.title = "Banques"
ws.append(COLS)
for r in L:
    r = list(r)
    r[6], r[9], r[10] = D(r[6]), D(r[9]), D(r[10])
    ws.append(r)
for c in ws[1]:
    c.font = Font(bold=True)
for row in ws.iter_rows(min_row=2):
    for c in row:
        c.alignment = Alignment(vertical="top", wrap_text=c.column in (3, 6, 8, 12))
        if c.column in (7, 10, 11):
            c.number_format = "yyyy-mm-dd"
        if c.column == 4:
            c.number_format = "0.00"
for col, w in zip("ABCDEFGHIJKL", (8, 30, 34, 10, 16, 22, 12, 46, 18, 12, 12, 90)):
    ws.column_dimensions[col].width = w
t = Table(displayName="Banques", ref=f"A1:L{len(L) + 1}")
t.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
ws.add_table(t)
ws.freeze_panes = "B2"
wb.properties.creator = "Ahmed Ben Arfa"
wb.properties.lastModifiedBy = "Ahmed Ben Arfa"
wb.properties.title = "Actionnariat des banques cotées"


def valeurs(feuille):
    """Valeurs des cellules ; une date relue dans le fichier revient en datetime : ramenée à la date."""
    v = lambda x: x.date() if isinstance(x, dt.datetime) else x
    return [[v(c.value) for c in ligne] for ligne in feuille.iter_rows()]


sys.stdout.reconfigure(encoding="utf-8")
if SORTIE.exists() and "--ecraser" not in sys.argv:
    existant = valeurs(load_workbook(SORTIE)["Banques"])
    if existant == valeurs(ws):
        print(f"{SORTIE.name} : contenu identique, rien n'est écrit")
        sys.exit(0)
    diff = [i + 1 for i, (a, b) in enumerate(zip(existant, valeurs(ws))) if a != b]
    sys.exit(f"{SORTIE.name} diffère du script (lignes {diff or 'en plus ou en moins'}) : rien n'est écrit "
             "(--ecraser pour remplacer le fichier)")
wb.save(SORTIE)
print(len(L), "lignes écrites dans", SORTIE)
