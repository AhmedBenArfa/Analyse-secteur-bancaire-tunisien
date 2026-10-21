#!/usr/bin/env python3
"""
Cours quotidiens des 12 banques cotées (date, ouverture, plus haut, plus bas, clôture, volume),
de 2019 à aujourd'hui.

Sources :
  - archives annuelles de la BVMT (« Historique des données », une archive zip par année,
    fichiers CSV par séance : ouverture, clôture, plus bas, plus haut, quantité négociée,
    nombre de transactions, capitaux) ;
  - année en cours (pas encore archivée) : à décider (spécification 7.5).
Python ne fait que la lecture : les ajustements (divisions du nominal, attributions gratuites,
dividendes) se calculent dans Power Query à partir de la table des opérations sur titres.

Requêtes par le client commun (collecte_banques.Client) : délai et chemins du robots.txt de chaque
site (BVMT : 10 secondes entre deux requêtes).

Utilisation (depuis le dossier du projet) :
  python scripts/cours_boursiers.py telecharger
  python scripts/cours_boursiers.py extraire --banques BIAT
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path


RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
import collecte_banques as cb  # noqa: E402

DOSSIER_COURS = cb.DOSSIER / "cours"
DOSSIER_ARCHIVES = DOSSIER_COURS / "bvmt"
MANIFESTE = DOSSIER_COURS / "manifeste_cours.csv"
PREMIERE_ANNEE = 2019
URL_ARCHIVE = "https://www.bvmt.com.tn/sites/default/files/historiques/cotations/histo_cotation_{annee}.zip"
URL_BULLETIN = "https://www.bvmt.com.tn/sites/default/files/bulletin/pdf/bull{jour:%Y%m%d}.pdf"
DOSSIER_BULLETINS = DOSSIER_COURS / "bulletins"


def lire_manifeste() -> dict[str, dict]:
    if not MANIFESTE.exists():
        return {}
    with MANIFESTE.open(encoding="utf-8-sig") as f:
        return {r["source"]: r for r in csv.DictReader(f, delimiter=";")}


def ecrire_manifeste(m: dict[str, dict]):
    champs = ["source", "url", "fichier", "statut", "octets", "derniere_modification", "telecharge_le"]
    MANIFESTE.parent.mkdir(parents=True, exist_ok=True)
    with MANIFESTE.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=champs, delimiter=";")
        w.writeheader()
        for k in sorted(m):
            w.writerow({c: m[k].get(c, "") for c in champs})


def telecharger_archives(client: cb.Client, m: dict, derniere_annee: int):
    """Une archive par année ; une archive déjà téléchargée n'est pas redemandée."""
    for annee in range(PREMIERE_ANNEE, derniere_annee + 1):
        cle = f"bvmt_{annee}"
        p = DOSSIER_ARCHIVES / f"histo_cotation_{annee}.zip"
        if m.get(cle, {}).get("statut") == "ok" and p.exists():
            continue
        url = URL_ARCHIVE.format(annee=annee)
        r = client.get(url, timeout=180)
        ok = r is not None and r.status_code == 200 and r.content[:2] == b"PK"
        if ok:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(r.content)
        m[cle] = {"source": cle, "url": url, "fichier": str(p) if ok else "", "statut": "ok" if ok else "absent",
                  "octets": len(r.content) if ok else "",
                  "derniere_modification": r.headers.get("last-modified", "") if r is not None else "",
                  "telecharge_le": dt.date.today().isoformat()}
        ecrire_manifeste(m)
        print(f"  {'OK' if ok else '--'}  {annee}  {url}")


def telecharger_bulletin(client: cb.Client, m: dict, jour: dt.date, refaire_absent: bool = False) -> Path | None:
    """Bulletin officiel quotidien de la cote (PDF) d'une séance ; None si absent (jour sans séance)."""
    cle = f"bulletin_{jour:%Y%m%d}"
    p = DOSSIER_BULLETINS / f"bull{jour:%Y%m%d}.pdf"
    statut = m.get(cle, {}).get("statut")
    if statut == "ok" and p.exists():
        return p
    if statut == "absent" and not refaire_absent:
        return None
    url = URL_BULLETIN.format(jour=jour)
    contenu = client.pdf(url)
    if contenu:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(contenu)
    m[cle] = {"source": cle, "url": url, "fichier": str(p) if contenu else "", "statut": "ok" if contenu else "absent",
              "octets": len(contenu) if contenu else "", "telecharge_le": dt.date.today().isoformat()}
    ecrire_manifeste(m)
    return p if contenu else None


def telecharger_bulletins(client: cb.Client, m: dict, debut: dt.date, fin: dt.date):
    """Bulletins des jours ouvrés de debut à fin (année pas encore archivée). Un jour sans bulletin
    (férié) est noté « absent » ; il n'est redemandé que s'il date de moins de 7 jours."""
    jour, n_ok, n_abs = debut, 0, 0
    while jour <= fin:
        if jour.weekday() < 5:
            p = telecharger_bulletin(client, m, jour, refaire_absent=(dt.date.today() - jour).days < 7)
            n_ok += p is not None
            n_abs += p is None
        jour += dt.timedelta(days=1)
    print(f"  bulletins du {debut} au {fin} : {n_ok} présents, {n_abs} jours sans bulletin")


def cmd_telecharger(args):
    m = lire_manifeste()
    client = cb.Client()
    derniere_archive = dt.date.today().year - 1
    telecharger_archives(client, m, derniere_archive)
    if not args.sans_bulletins:
        telecharger_bulletins(client, m, dt.date(derniere_archive + 1, 1, 1), dt.date.today() - dt.timedelta(days=1))
        telecharger_ilboursa(client, m, cb.choisir_banques(args.banques), dt.date(derniere_archive + 1, 1, 1),
                             dt.date.today() - dt.timedelta(days=1))


# ---------------------------------------------------------------------------
# Lecture des archives
# ---------------------------------------------------------------------------

# Titre coté de chaque banque. De 2019 à 2020 les archives donnent un code court (caractères 6 à 11
# de l'ISIN : 180045 pour TN0001800457), à partir de 2021 l'ISIN. BTE : seules ses actions à
# dividende prioritaire (ADP) sont cotées.
ISIN = {"AB": "TN0003400058", "ATB": "TN0003600350", "TJARI": "TN0001600154", "BH": "TN0001900604",
        "BIAT": "TN0001800457", "BNA": "TN0003100609", "BT": "TN0002200053", "BTE": "TN0001300557",
        "STB": "TN0002600955", "UBCI": "TN0002400505", "UIB": "TN0003900107", "WIB": "TN0007200017"}
SORTIE = cb.DOSSIER / "cours_banques.csv"
CONTROLE = cb.DOSSIER / "controle_cours.csv"
# En-têtes des archives (deux formats : texte à colonnes fixes 2019-2021, CSV « ; » à partir de 2022)
NOMS_COLONNES = {"SEANCE": "seance", "C_GR_RLC": "groupe", "GROUPE": "groupe", "CODE_VAL": "code", "CODE": "code",
                 "LIB_VAL": "valeur", "VALEUR": "valeur", "OUVERTURE": "ouverture", "CLOTURE": "cloture",
                 "PLUS_BAS": "plus_bas", "PLUS_HAUT": "plus_haut", "QUANTITE_NEGOCIEE": "quantite",
                 "NB_TRAN": "nb_transactions", "NB_TRANSACTION": "nb_transactions", "CAPITAUX": "capitaux",
                 "COURS_REF": "cours_reference", "COURS_VEILLE": "cours_veille", "DERNIER_COURS": "dernier_cours",
                 "IND_RES": "reservation"}
# une ouverture répétée sur plus de 30 % des séances d'une année, et hors de [plus bas, plus haut]
# pour plus de la moitié de ses occurrences, est figée (archive 2021, du 04/01 au 27/08, pour les
# 12 banques : BIAT 94,300 sur 161 séances, dont 147 hors bornes). Une valeur souvent répétée mais
# dans les bornes est une vraie ouverture (Wifak 2024 : 8,500 sur 64 séances, 56 dans les bornes)
PART_OUVERTURE_FIGEE = 0.30
# De 2022 à 2025, la colonne OUVERTURE des archives égale la clôture de la veille pour 99,2 à
# 99,7 % des séances (les autres sont des jours d'opération sur titres) : c'est le cours de
# référence, pas un cours d'ouverture (bulletin du 31/12/2025 : AB ouverture 49,480, référence et
# archive 49,460). Au-delà de cette part sur une année, l'ouverture de l'année reste vide.
PART_OUVERTURE_REFERENCE = 0.95
# seuil de contrôle des variations de clôture d'une séance à l'autre (au-delà : opération sur titres
# probable : division du nominal, attribution gratuite, dividende important)
SEUIL_SAUT = 0.0615


def lignes_archive(texte: str):
    """Une ligne de l'archive -> dict (noms de NOMS_COLONNES), valeurs en texte brut."""
    lignes = texte.splitlines()
    if ";" in lignes[0]:
        tetes = [NOMS_COLONNES.get(x.strip(), x.strip()) for x in lignes[0].split(";")]
        for x in lignes[1:]:
            if x.strip():
                yield dict(zip(tetes, (c.strip() for c in x.split(";"))))
        return
    # colonnes fixes : bornes données par la ligne de tirets sous l'en-tête
    bornes = [(m.start(), m.end()) for m in re.finditer(r"-+", lignes[1])]
    tetes = []
    for a, b in bornes:
        mots = lignes[0][a:b].split()
        tetes.append(NOMS_COLONNES.get(mots[0], mots[0]) if mots else "?")
    for x in lignes[2:]:
        if x.strip():
            yield dict(zip(tetes, (x[a:b].strip() for a, b in bornes)))


def nombre(txt: str | None) -> float | None:
    t = (txt or "").strip().replace(",", ".")
    if t in ("", "."):
        return None
    return float(t)


def date_seance(txt: str) -> dt.date:
    j, m, a = txt.strip().split("/")
    a = int(a)
    return dt.date(a + 2000 if a < 100 else a, int(m), int(j))


def lire_archives(codes: list[str]) -> tuple[dict, list[str]]:
    """(banque, date) -> ligne retenue ; et les remarques de lecture. Une séance présente dans deux
    archives (2022 : archives 2022 et 2023) doit y être identique, sinon elle est signalée."""
    cherches = {ISIN[c]: c for c in codes} | {ISIN[c][5:11]: c for c in codes}
    seances: dict[tuple[str, dt.date], dict] = {}
    remarques = []
    for p in sorted(DOSSIER_ARCHIVES.glob("histo_cotation_*.zip")):
        with zipfile.ZipFile(p) as zf:
            for info in zf.infolist():
                texte = zf.read(info).decode("latin-1")
                for r in lignes_archive(texte):
                    banque = cherches.get(r.get("code", ""))
                    if not banque:
                        continue
                    d = date_seance(r["seance"])
                    r["fichier"] = f"{p.name}/{info.filename}"
                    cle = (banque, d)
                    if cle in seances:
                        a, b = seances[cle], r
                        champs = ("ouverture", "cloture", "plus_bas", "plus_haut", "quantite")
                        if any(nombre(a.get(k)) != nombre(b.get(k)) for k in champs):
                            remarques.append(f"{banque} {d} : séance différente dans {a['fichier']} et {b['fichier']}")
                        continue
                    seances[cle] = r
    return seances, remarques


# ---------------------------------------------------------------------------
# Lecture des bulletins quotidiens (cours 2026, dividendes, droits, avis de la Bourse)
# ---------------------------------------------------------------------------

# Ancienne mise en page (jusqu'en 2021) : pas d'ISIN ; ligne « N° nominal dividende date nom
# cours-de-référence ouverture clôture plus-haut plus-bas » (cours absents sans transaction).
# (« . » : tiret court ou long selon les bulletins, « BTE – Banque » le 04/05/2021)
NOMS_BULLETIN = {"AB": r"AMEN BANK", "ATB": r"ATB . Arab Tunisian Bank", "TJARI": r"Attijari bank",
                 "BH": r"BH . (?:BH BANK|Banque de l.Habitat)", "BIAT": r"BIAT . Banque Internationale", "BNA": r"BNA . Banque Nationale",
                 "BT": r"BT . Banque de Tunisie(?! et)", "BTE": r"BTE . Banque de Tunisie et des",
                 "STB": r"STB . Soci", "UBCI": r"UBCI . Union Bancaire", "UIB": r"UIB . Union Internationale",
                 "WIB": r"WIFACK INTERNATIONAL BANK"}
RE_NOMBRE = r"\d{1,3}(?: \d{3})*,\d{3}"
# Nouvelle mise en page : colonnes repérées par leur en-tête, à droite de « Cours de Référence »
COLONNES_BULLETIN = [("reference", r"r[ée]f[ée]rence"), ("ouverture", r"^ouverture$"), ("dernier", r"^dernier$"),
                     ("haut", r"^haut$"), ("bas", r"^bas$"), ("cloture", r"^cl[ôo]ture$")]
# Noms des banques dans les avis de la Bourse et dans les noms des droits (« BIAT DA1/7 291124 »)
MOTS_BANQUE = {"AB": r"AMEN BANK|\bAB\b", "ATB": r"ARAB TUNISIAN BANK|\bATB", "TJARI": r"ATTIJARI|\bTJARI",
               "BH": r"\bBH\b|BH BANK|BQ HABITAT", "BIAT": r"\bBIAT\b", "BNA": r"\bBNA\b|BANQUE NATIONALE AGRICOLE",
               "BT": r"\bBT\b|BANQUE DE TUNISIE(?! ET)|BQ DE TSIE", "BTE": r"\bBTE\b|TUNISIE ET DES EMIRATS",
               "STB": r"\bSTB\b|SOCIETE TUNISIENNE DE BANQUE", "UBCI": r"\bUBCI\b", "UIB": r"\bUIB\b|UNION INTERNATIONALE DE BANQUES",
               "WIB": r"WIFA C?K|WIFACK|WIFAK"}


def nombre_fr(txt: str) -> float:
    return float(txt.replace(" ", "").replace(",", "."))


def lire_bulletin(p: Path) -> dict[str, dict]:
    """Ligne de chaque banque dans le bulletin : cours (reference, ouverture, dernier, haut, bas,
    cloture ; une case vide reste absente), nominal, dernier dividende (montant, date), page."""
    import pdfplumber

    sortie: dict[str, dict] = {}
    with pdfplumber.open(p) as pdf:
        for num, page in enumerate(pdf.pages[:4], start=1):
            mots = page.extract_words()
            if any(w["text"] in ISIN.values() for w in mots):
                sortie.update({b: {**v, "page": num} for b, v in lire_page_nouvelle(mots).items() if b not in sortie})
            else:
                for ligne in (page.extract_text() or "").splitlines():
                    for b, nom in NOMS_BULLETIN.items():
                        # date « 15-05-2019 », ou « 01/07/2021 » (mise en page de transition, 2021)
                        m = re.match(rf"^\d+\s+(\d+)\s+({RE_NOMBRE})\s+(\d\d[-/]\d\d[-/]\d{{4}})\s+{nom}.*?\s({RE_NOMBRE})",
                                     ligne)
                        if m and b not in sortie:
                            j, mo, a = re.split(r"[-/]", m[3])
                            sortie[b] = {"nominal": float(m[1]), "dividende": nombre_fr(m[2]),
                                         "date_dividende": f"{a}-{mo}-{j}", "reference": nombre_fr(m[4]), "page": num}
            if len(sortie) == len(ISIN):
                break
    return sortie


def lire_page_nouvelle(mots: list[dict]) -> dict[str, dict]:
    # repère : « Ouverture » (« Cours de Référence » est parfois écrit sur deux lignes dont les
    # lettres s'entremêlent : bulletin du 09/05/2022) ; la référence est la colonne d'avant
    ouv = [w for w in mots if re.search(COLONNES_BULLETIN[1][1], w["text"], re.I)]
    if not ouv:
        return {}
    ouv = min(ouv, key=lambda w: w["top"])
    centres = {"ouverture": (ouv["x0"] + ouv["x1"]) / 2}
    for nom, rx in COLONNES_BULLETIN[2:]:
        c = [w for w in mots if re.search(rx, w["text"], re.I) and w["x0"] > ouv["x1"] and abs(w["top"] - ouv["top"]) < 25]
        if c:
            w = min(c, key=lambda w: w["top"])
            centres[nom] = (w["x0"] + w["x1"]) / 2
    refs = [w for w in mots if re.search(COLONNES_BULLETIN[0][1], w["text"], re.I)
            and w["x1"] < ouv["x0"] and abs(w["top"] - ouv["top"]) < 25]
    if refs:
        centres["reference"] = (refs[0]["x0"] + refs[0]["x1"]) / 2
    elif "dernier" in centres:
        centres["reference"] = 2 * centres["ouverture"] - centres["dernier"]
    noms = sorted(centres, key=centres.get)
    xs = [centres[n] for n in noms]
    bornes = [(xs[i] + xs[i + 1]) / 2 for i in range(len(xs) - 1)]
    debut = xs[0] - ((xs[1] - xs[0]) / 2 if len(xs) > 1 else 30)
    sortie = {}
    for b, isin in ISIN.items():
        w0 = [w for w in mots if w["text"] == isin]
        if not w0:
            continue
        ligne = sorted((w for w in mots if abs(w["top"] - w0[0]["top"]) < 3), key=lambda w: w["x0"])
        texte = " ".join(w["text"] for w in ligne)
        v: dict = {}
        m = re.search(rf"{isin} \S+ ({RE_NOMBRE})(?: ({RE_NOMBRE}) (\d\d)/(\d\d)/(\d{{4}}))?", texte)
        if m:
            v["nominal"] = nombre_fr(m[1])
            if m[2]:
                v["dividende"], v["date_dividende"] = nombre_fr(m[2]), f"{m[5]}-{m[4]}-{m[3]}"
        # les montants (un nombre peut être coupé en plusieurs mots : « 1 234,500 ») : mots réunis
        # quand ils se touchent, puis rangés par la position de leur fin
        groupes: list[list[dict]] = []
        for w in ligne:
            if w["x0"] < debut or not re.fullmatch(r"[\d ,]+", w["text"]):
                continue
            if groupes and w["x0"] - groupes[-1][-1]["x1"] < 4:
                groupes[-1].append(w)
            else:
                groupes.append([w])
        for g in groupes:
            t = " ".join(w["text"] for w in g)
            if re.fullmatch(RE_NOMBRE, t):
                x = (g[0]["x0"] + g[-1]["x1"]) / 2
                v[noms[sum(x > bb for bb in bornes)]] = nombre_fr(t)
        # réservation (« B » à la baisse, « H » à la hausse) après la clôture : la clôture publiée
        # peut alors sortir des cours échangés (BTE le 04/02/2026 : échangé 3,890, clôture 3,720 B)
        res = [w["text"] for w in ligne if w["text"] in ("B", "H") and w["x0"] > xs[-1]]
        if res:
            v["reservation"] = res[0]
        sortie[b] = v
    return sortie


def droits_du_bulletin(p: Path) -> list[tuple[str, str, int]]:
    """Lignes de droits (« DA a/b JJMMAA », « DS … ») des 12 banques dans les lignes secondaires :
    (banque, nom du droit, page)."""
    import fitz

    sortie = []
    with fitz.open(p) as doc:
        for num, page in enumerate(doc, start=1):
            texte = page.get_text()
            if "SECONDAIRES" not in cb.sans_accents(texte).upper():
                continue
            for ligne in texte.splitlines():
                l = cb.sans_accents(ligne).upper().strip()
                if re.search(r"D[AS]\s?\d+/\d+", l):   # « TJARIDA4/21 300425 » : collé au nom
                    for b, rx in MOTS_BANQUE.items():
                        if re.search(rx, l):
                            sortie.append((b, ligne.strip(), num))
                            break
    return sortie


def avis_du_bulletin(p: Path, banque: str) -> list[tuple[int, str]]:
    """Pages « Décisions et avis de la Bourse » qui parlent d'une opération sur les titres de la
    banque : (page, extrait)."""
    import fitz

    sortie = []
    with fitz.open(p) as doc:
        for num, page in enumerate(doc, start=1):
            t = " ".join(page.get_text().split())
            n = cb.sans_accents(t).upper()
            if "DECISIONS ET AVIS" not in n:
                continue
            for m in re.finditer(MOTS_BANQUE[banque], n):
                autour = n[max(0, m.start() - 300):m.start() + 500]
                if re.search(r"ATTRIBUTION|DIVISION|NOMINAL|AUGMENTATION DE CAPITAL|SOUSCRIPTION|DIVIDENDE", autour):
                    k = max(0, m.start() - 150)
                    sortie.append((num, t[k:k + 450]))
                    break
    return sortie


def lignes_archives(codes: list[str], remarques: list[str]) -> list[dict]:
    """Séances 2019 à la dernière année archivée, règles de l'ouverture appliquées."""
    seances, rem = lire_archives(codes)
    remarques += rem
    figees, references = set(), set()
    par_annee: dict[tuple[str, int], list] = {}
    egales_veille: dict[tuple[str, int], list] = {}
    veille: dict[str, float | None] = {}
    for (b, d) in sorted(seances, key=lambda k: (k[0], k[1])):
        r = seances[(b, d)]
        o, c, bas, haut = (nombre(r.get(k)) for k in ("ouverture", "cloture", "plus_bas", "plus_haut"))
        if (nombre(r.get("quantite")) or 0) > 0:
            hors = None not in (o, bas, haut) and not (bas - 1e-9 <= o <= haut + 1e-9)
            par_annee.setdefault((b, d.year), []).append((r.get("ouverture"), hors))
            if veille.get(b) is not None and o is not None:
                egales_veille.setdefault((b, d.year), []).append(abs(o - veille[b]) < 1e-9)
        veille[b] = c
    for (b, a), egal in egales_veille.items():
        if sum(egal) > PART_OUVERTURE_REFERENCE * len(egal):
            references.add((b, a))
            remarques.append(f"{b} {a} : ouverture = clôture de la veille sur {sum(egal)} séances sur "
                             f"{len(egal)} (cours de référence, ouverture laissée vide)")
    for (b, a), valeurs in par_annee.items():
        v, n = Counter(x for x, _ in valeurs).most_common(1)[0]
        n_hors = sum(h for x, h in valeurs if x == v)
        if n > PART_OUVERTURE_FIGEE * len(valeurs) and n_hors > n / 2:
            figees.add((b, a, v))
            remarques.append(f"{b} {a} : ouverture {v} répétée sur {n} séances sur {len(valeurs)}, "
                             f"{n_hors} hors bornes (figée)")
    sortie = []
    for (b, d), r in seances.items():
        o, c, bas, haut, q = (nombre(r.get(k)) for k in ("ouverture", "cloture", "plus_bas", "plus_haut", "quantite"))
        statut = []
        # un cours à 0 n'est jamais un prix : séance sans transaction en 2020 (tous les cours à 0,
        # clôture comprise), journée sans cotation du 17/12/2025 (tous les titres à 0), transaction
        # sans cours coté (UBCI 17/07/2019 : 10 000 titres pour 242 000 DT, cours à 0)
        o, c, bas, haut = (None if x == 0 else x for x in (o, c, bas, haut))
        if c is None:
            statut.append("clôture absente de l'archive (0)")
        if q and c is None and haut is None:
            statut.append("quantité sans cours dans l'archive")
        if not q:
            # pas de transaction : l'archive met 0 aux cours de la séance et la clôture au cours
            # de référence ; ouverture, haut et bas restent vides
            statut.append("sans transaction")
            o = bas = haut = None
        elif (b, d.year, r.get("ouverture")) in figees:
            statut.append("ouverture figée dans l'archive")
            o = None
        elif (b, d.year) in references:
            statut.append("ouverture de l'archive = cours de référence")
            o = None
        elif None not in (o, bas, haut) and not (bas - 1e-9 <= o <= haut + 1e-9):
            statut.append("ouverture hors [plus bas, plus haut]")
            o = None
        if r.get("reservation") in ("B", "H"):
            statut.append(f"réservation {'à la baisse' if r['reservation'] == 'B' else 'à la hausse'}")
        if q and None not in (c, bas, haut) and not (bas - 1e-9 <= c <= haut + 1e-9):
            statut.append("clôture hors [plus bas, plus haut]")
        sortie.append({"banque": b, "date": d, "ouverture": o, "haut": haut, "bas": bas, "cloture": c,
                       "volume": int(q) if q is not None else None, "nb_transactions": r.get("nb_transactions", ""),
                       "capitaux": nombre(r.get("capitaux")), "statut": statut, "source": "bvmt_archive",
                       "fichier": r["fichier"]})
    return sortie


# ---------------------------------------------------------------------------
# Volumes de l'année en cours : ilboursa (le bulletin de la BVMT ne donne pas les quantités)
# ---------------------------------------------------------------------------

URL_ILBOURSA = "https://www.ilboursa.com/api/general/GetHistos"
DOSSIER_ILBOURSA = DOSSIER_COURS / "ilboursa"


def periodes_trois_mois(debut: dt.date, fin: dt.date) -> list[tuple[dt.date, dt.date]]:
    """L'API d'ilboursa refuse plus de 3 mois par requête : découpage par trimestre civil."""
    sortie, d = [], debut
    while d <= fin:
        mois_suivant = (d.month - 1) // 3 * 3 + 4
        f = (dt.date(d.year + 1, 1, 1) if mois_suivant > 12 else dt.date(d.year, mois_suivant, 1)) - dt.timedelta(days=1)
        sortie.append((d, min(f, fin)))
        d = f + dt.timedelta(days=1)
    return sortie


def telecharger_ilboursa(client: cb.Client, m: dict, codes: list[str], debut: dt.date, fin: dt.date):
    for b in codes:
        ticker = cb.BANQUES[b]["ticker"]
        for d, f in periodes_trois_mois(debut, fin):
            cle = f"ilboursa_{b}_{d:%Y%m%d}"
            p = DOSSIER_ILBOURSA / f"{b}_{d:%Y%m%d}.json"
            if m.get(cle, {}).get("statut") == "ok" and p.exists() and m[cle].get("fin", "") >= f.isoformat():
                continue
            r = client.requete("POST", URL_ILBOURSA, json={"ticker": ticker, "datedeb": d.isoformat(),
                                                             "datefin": f.isoformat(), "xperiod": "0"},
                               headers={"Referer": f"https://www.ilboursa.com/marches/historiques/{ticker}"})
            lst = []
            if r is not None and r.status_code == 200:
                try:
                    lst = r.json().get("lst") or []
                except ValueError:
                    lst = []
            ok = isinstance(lst, list) and len(lst) > 0
            if ok:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(r.content)
            m[cle] = {"source": cle, "url": f"{URL_ILBOURSA} ({ticker} {d} {f})", "fichier": str(p) if ok else "",
                      "statut": "ok" if ok else "absent", "octets": len(r.content) if ok else "",
                      "telecharge_le": dt.date.today().isoformat(), "fin": f.isoformat()}
            ecrire_manifeste(m)
            erreur = "" if ok else (" : " + (r.text[:80] if r is not None else "interdit par le robots.txt"))
            print(f"  {'OK' if ok else '--'}  ilboursa {b} ({ticker}) {d} -> {f}{erreur}")


def volumes_ilboursa(m: dict) -> dict[tuple[str, dt.date], dict]:
    sortie = {}
    for cle, r in m.items():
        if not cle.startswith("ilboursa_") or r.get("statut") != "ok" or not Path(r["fichier"]).exists():
            continue
        b = cle.split("_")[1]
        for x in json.loads(Path(r["fichier"]).read_text(encoding="utf-8")).get("lst") or []:
            j, mo, a = x["Date"].split("/")
            sortie[(b, dt.date(int(a), int(mo), int(j)))] = {**x, "fichier": Path(r["fichier"]).name}
    return sortie


def lignes_bulletins(m: dict, codes: list[str], depuis: dt.date, remarques: list[str]) -> list[dict]:
    """Séances de l'année en cours : cours du bulletin officiel quotidien, volume d'ilboursa (titres)."""
    vol = volumes_ilboursa(m)
    sortie, jours = [], set()
    for cle, r in sorted(m.items()):
        if not cle.startswith("bulletin_") or r.get("statut") != "ok":
            continue
        jour = dt.datetime.strptime(cle[9:], "%Y%m%d").date()
        if jour < depuis or not Path(r["fichier"]).exists():
            continue
        jours.add(jour)
        lus = lire_bulletin(Path(r["fichier"]))
        for b in codes:
            v = lus.get(b)
            if not v:
                remarques.append(f"{b} {jour} : ligne absente du bulletin {Path(r['fichier']).name}")
                continue
            statut = []
            o, haut, bas, c = (v.get(k) for k in ("ouverture", "haut", "bas", "cloture"))
            if c is None:
                remarques.append(f"{b} {jour} : clôture absente du bulletin")
            if haut is None and bas is None:
                statut.append("sans transaction")
                o = None
            elif None not in (o, bas, haut) and not (bas - 1e-9 <= o <= haut + 1e-9):
                statut.append("ouverture hors [plus bas, plus haut]")
                o = None
            if v.get("reservation"):
                statut.append(f"réservation {'à la baisse' if v['reservation'] == 'B' else 'à la hausse'}")
            if None not in (c, bas, haut) and not (bas - 1e-9 <= c <= haut + 1e-9):
                statut.append("clôture hors [plus bas, plus haut]")
            il = vol.get((b, jour))
            volume = None
            if il is not None:
                volume = int(il["Volume"])
                if c is not None and abs(float(il["Close"]) - c) > 1e-9:
                    statut.append(f"clôture ilboursa {il['Close']} ≠ bulletin")
            elif "sans transaction" in statut:
                volume = 0
            else:
                statut.append("volume absent d'ilboursa")
            sortie.append({"banque": b, "date": jour, "ouverture": o, "haut": haut, "bas": bas, "cloture": c,
                           "volume": volume, "nb_transactions": "", "capitaux": None, "statut": statut,
                           "source": "bvmt_bulletin" + ("+ilboursa_volume" if il is not None else ""),
                           "fichier": f"{Path(r['fichier']).name} p.{v.get('page')}"
                                      + (f" ; {il['fichier']}" if il is not None else "")})
    # Après le dernier bulletin disponible (aucun bulletin à l'adresse habituelle depuis le
    # 14/04/2026), séances d'ilboursa : clôture et volume seulement (égaux à la BVMT sur 63 des 64
    # séances comparées) ; ouverture, haut et bas d'ilboursa non repris (définition différente).
    # Avant ce jour, une séance d'ilboursa sans bulletin n'est pas retenue.
    dernier_bulletin = max(jours, default=depuis)
    for (b, jour), il in sorted(vol.items()):
        if b not in codes or jour < depuis or jour in jours:
            continue
        if jour <= dernier_bulletin:
            remarques.append(f"{b} {jour} : séance chez ilboursa sans bulletin BVMT (non retenue)")
            continue
        sortie.append({"banque": b, "date": jour, "ouverture": None, "haut": None, "bas": None,
                       "cloture": float(il["Close"]), "volume": int(il["Volume"]), "nb_transactions": "",
                       "capitaux": None, "statut": ["pas de bulletin BVMT : clôture et volume d'ilboursa"]
                       + (["sans transaction"] if not il["Volume"] else []),
                       "source": "ilboursa", "fichier": il["fichier"]})
    return sortie


def cmd_extraire(args):
    codes = cb.choisir_banques(args.banques)
    m = lire_manifeste()
    remarques: list[str] = []
    lignes = lignes_archives(codes, remarques)
    derniere = max((l["date"] for l in lignes), default=dt.date(PREMIERE_ANNEE - 1, 12, 31))
    lignes += lignes_bulletins(m, codes, dt.date(derniere.year + 1, 1, 1), remarques)
    lignes.sort(key=lambda l: (l["banque"], l["date"]))
    champs = ["ticker", "banque", "isin", "date", "ouverture", "haut", "bas", "cloture", "volume",
              "nb_transactions", "capitaux", "statut", "source", "fichier"]
    sauts = []
    precedent: dict[str, float] = {}
    vide = lambda x: "" if x is None else x
    with SORTIE.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=champs, delimiter=";")
        w.writeheader()
        for l in lignes:
            b, c = l["banque"], l["cloture"]
            veille = precedent.get(b)
            if veille and c and abs(c / veille - 1) > SEUIL_SAUT:
                sauts.append((b, l["date"], veille, c))
                l["statut"].append(f"variation {c / veille - 1:+.1%} : opération sur titres ?")
            precedent[b] = c or veille
            w.writerow({"ticker": cb.BANQUES[b]["ticker"], "banque": b, "isin": ISIN[b], "date": l["date"].isoformat(),
                        "ouverture": vide(l["ouverture"]), "haut": vide(l["haut"]), "bas": vide(l["bas"]),
                        "cloture": vide(c), "volume": vide(l["volume"]), "nb_transactions": l["nb_transactions"],
                        "capitaux": vide(l["capitaux"]), "statut": " | ".join(l["statut"]), "source": l["source"],
                        "fichier": l["fichier"]})
    with CONTROLE.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["banque", "date", "cloture_veille", "cloture", "variation_pct"])
        for b, d, v, c in sauts:
            w.writerow([b, d.isoformat(), v, c, f"{c / v - 1:+.2%}"])
    for b in codes:
        jours = [l["date"] for l in lignes if l["banque"] == b]
        if jours:
            print(f"  {b} : {len(jours)} séances du {min(jours)} au {max(jours)}")
    for x in remarques:
        print("  " + x)
    print(f"\n{len(sauts)} variations de plus de {SEUIL_SAUT:.2%} (contrôle : {CONTROLE})\nCours : {SORTIE}")


# ---------------------------------------------------------------------------
# Opérations sur titres (dividendes, attributions gratuites, divisions du nominal, souscriptions)
# ---------------------------------------------------------------------------

OPERATIONS = RACINE / "operations_titres.csv"
RE_DROIT = re.compile(r"D([AS])\s?(\d+)/(\d+)\s+(\d\d)/?(\d\d)/?(\d\d(?:\d\d)?)\b")


def droits_des_archives(codes: list[str]) -> list[tuple[str, str, str]]:
    """Noms des droits (groupe 32) des banques dans les archives : (banque, nom, fichier)."""
    vus, sortie = set(), []
    for p in sorted(DOSSIER_ARCHIVES.glob("histo_cotation_*.zip")):
        with zipfile.ZipFile(p) as zf:
            for info in zf.infolist():
                for r in lignes_archive(zf.read(info).decode("latin-1")):
                    v = r.get("valeur", "")
                    if r.get("groupe") != "32" or v in vus:
                        continue
                    vus.add(v)
                    l = cb.sans_accents(v).upper()
                    for b in codes:
                        if re.search(MOTS_BANQUE[b], l):
                            sortie.append((b, v, f"{p.name}/{info.filename}"))
                            break
    return sortie


def date_du_droit(nom: str) -> tuple[str, int, int, dt.date] | None:
    """« BIAT DA1/7 291124 » -> (« A », 1, 7, 2024-11-29) ; « DS » = droit de souscription."""
    m = RE_DROIT.search(cb.sans_accents(nom).upper())
    if not m:
        return None
    a = int(m[6]) + (2000 if len(m[6]) == 2 else 0)
    try:
        return m[1], int(m[2]), int(m[3]), dt.date(a, int(m[5]), int(m[4]))
    except ValueError:
        return None


def cmd_operations(args):
    """Repère les opérations (droits des archives et du bulletin le plus récent, dernier dividende des
    bulletins de fin d'année et du plus récent, changement de nominal) et les confirme dans le
    bulletin du jour : cours de référence publié et avis de la Bourse. Écrit operations_titres.csv."""
    codes = cb.choisir_banques(args.banques)
    m = lire_manifeste()
    client = cb.Client()
    cours: dict[str, list[tuple[dt.date, float | None]]] = {}
    with SORTIE.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f, delimiter=";"):
            cours.setdefault(r["banque"], []).append((dt.date.fromisoformat(r["date"]), float(r["cloture"]) if r["cloture"] else None))
    debut = min(d for v in cours.values() for d, _ in v)
    fin = max(d for v in cours.values() for d, _ in v)
    candidats: dict[tuple[str, dt.date], dict] = {}

    def ajouter(b, d, typ, details, detection, **kw):
        c = candidats.setdefault((b, d), {"types": [], "details": [], "detection": []})
        for cle, val in (("types", typ), ("details", details), ("detection", detection)):
            if val not in c[cle]:
                c[cle].append(val)
        c.update(kw)

    # 1. bulletins de la dernière séance de chaque année et du jour le plus récent
    jours = sorted({d for v in cours.values() for d, _ in v})
    fins = sorted({max(d for d in jours if d.year == a) for a in {d.year for d in jours}})
    bulletins = [(j, p) for j in fins if (p := telecharger_bulletin(client, m, j))]
    # plus le bulletin le plus récent disponible (aucun après le 13/04/2026 à l'adresse habituelle)
    dispo = sorted(dt.datetime.strptime(k[9:], "%Y%m%d").date() for k, r in m.items()
                   if k.startswith("bulletin_") and r.get("statut") == "ok")
    if dispo and (not bulletins or dispo[-1] > bulletins[-1][0]):
        bulletins.append((dispo[-1], telecharger_bulletin(client, m, dispo[-1])))
    # 2. droits d'attribution (DA) et de souscription (DS) : date de détachement dans leur nom
    droits = droits_des_archives(codes)
    if bulletins:
        j, p = bulletins[-1]
        droits += [(b, nom, f"{p.name} p.{page}") for b, nom, page in droits_du_bulletin(p) if b in codes]
    for b, nom, source in droits:
        x = date_du_droit(nom)
        if x and debut < x[3] <= fin:
            sorte, a, n, d = x
            if sorte == "A":
                ajouter(b, d, "attribution gratuite", f"{nom.strip()} ({a} pour {n})", f"droit : {source}",
                        parite_attribution=(a, n))
            else:
                ajouter(b, d, "souscription en numéraire", f"{nom.strip()} ({a} pour {n})", f"droit : {source}",
                        parite_souscription=(a, n))
    # 3. dividendes (« dernier dividende ») et nominal, dans les bulletins de fin d'année
    nominaux: dict[str, list[tuple[dt.date, float]]] = {}
    for j, p in bulletins:
        for b, v in lire_bulletin(p).items():
            if b not in codes:
                continue
            if v.get("nominal"):
                nominaux.setdefault(b, []).append((j, v["nominal"]))
            if v.get("date_dividende"):
                d = dt.date.fromisoformat(v["date_dividende"])
                if debut < d <= fin:
                    # date du dividende hors séance (UIB : samedi 01/06/2019) : première séance suivante
                    seance = min((x for x in jours if x >= d), default=d)
                    note = "" if seance == d else f" (date du dividende {d:%d/%m/%Y}, pas de séance)"
                    ajouter(b, seance, "dividende", f"dividende {v['dividende']:.3f} DT{note}",
                            f"dernier dividende : {p.name} p.{v['page']}", dividende=v["dividende"],
                            date_dividende=d)
    # 4. division du nominal : nominal plus petit d'une fin d'année à la suivante ; date = plus forte
    #    baisse de clôture entre les deux (confirmée par l'avis du bulletin du jour)
    for b, liste in nominaux.items():
        for (j0, n0), (j1, n1) in zip(liste, liste[1:]):
            if n1 < n0:
                serie = [x for x in cours[b] if j0 <= x[0] <= j1 and x[1]]
                baisses = {serie[i][0]: serie[i][1] / serie[i - 1][1] for i in range(1, len(serie))}
                d = min(baisses, key=baisses.get)
                ajouter(b, d, "division du nominal", f"nominal {n0:g} -> {n1:g} DT",
                        f"nominal des bulletins du {j0} et du {j1}", nominal=(n0, n1))
    # 5. confirmation dans le bulletin du jour de l'opération
    lignes = []
    for (b, d), c in sorted(candidats.items()):
        avant = [x for x in cours.get(b, []) if x[0] < d and x[1]]
        date_veille, veille = avant[-1] if avant else (None, None)
        p = telecharger_bulletin(client, m, d)
        ref, page_ref, avis = None, "", []
        if p:
            v = lire_bulletin(p).get(b, {})
            ref, page_ref = v.get("reference"), v.get("page", "")
            avis = avis_du_bulletin(p, b)
            if "dividende" in c["types"] and v.get("date_dividende") != c.get("date_dividende", d).isoformat():
                c["details"].append(f"dividende non repris sur la ligne du {d}")
        theo = veille
        if theo is not None:
            # le dividende revient aux actions anciennes : retiré avant la parité (BT 10/05/2022 :
            # (6,190 − 0,280) × 5/6 = 4,925, publié 4,930)
            if "dividende" in c:
                theo = theo - c["dividende"]
            if "parite_attribution" in c:
                a, n = c["parite_attribution"]
                theo = theo * n / (a + n)
            if "nominal" in c:
                theo = theo * c["nominal"][1] / c["nominal"][0]
            if "parite_souscription" in c:
                theo = None   # dépend du prix d'émission (avis) : pas de cours théorique calculé
        lignes.append({"banque": b, "isin": ISIN[b], "date_effet": d.isoformat(), "types": " + ".join(c["types"]),
                       "details": " ; ".join(c["details"]), "dividende": c.get("dividende", ""),
                       "date_veille": date_veille.isoformat() if date_veille else "",
                       "cloture_veille": veille if veille is not None else "",
                       "cours_reference_publie": ref if ref is not None else "",
                       "cours_reference_theorique": round(theo, 3) if theo is not None else "",
                       "ecart_theorique": round(theo - ref, 3) if None not in (theo, ref) else "",
                       "bulletin": p.name if p else "absent", "page_cours": page_ref,
                       "page_avis": ",".join(str(a[0]) for a in avis), "extrait_avis": avis[0][1][:300] if avis else "",
                       "detection": " ; ".join(c["detection"])})
    champs = list(lignes[0]) if lignes else ["banque"]
    with OPERATIONS.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=champs, delimiter=";")
        w.writeheader()
        w.writerows(lignes)
    for l in lignes:
        print(f"  {l['banque']:5} {l['date_effet']} {l['types']:40} veille {l['cloture_veille']!s:8} "
              f"réf. publiée {l['cours_reference_publie']!s:8} théorique {l['cours_reference_theorique']!s:8} "
              f"avis p.{l['page_avis'] or '-'}")
    print(f"\n{len(lignes)} opérations : {OPERATIONS}  ({client.nb} requêtes)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sous = ap.add_subparsers(dest="cmd", required=True)
    p = sous.add_parser("telecharger")
    p.add_argument("--sans-bulletins", action="store_true", help="archives annuelles seulement")
    p.add_argument("--banques", help="codes séparés par des virgules (défaut : toutes), pour ilboursa")
    p.set_defaults(f=cmd_telecharger)
    p = sous.add_parser("extraire")
    p.add_argument("--banques", help="codes séparés par des virgules (défaut : toutes)")
    p.set_defaults(f=cmd_extraire)
    p = sous.add_parser("operations")
    p.add_argument("--banques", help="codes séparés par des virgules (défaut : toutes)")
    p.set_defaults(f=cmd_operations)
    args = ap.parse_args()
    args.f(args)


if __name__ == "__main__":
    main()
