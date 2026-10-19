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

Le robots.txt de la BVMT demande 10 secondes entre deux requêtes (Crawl-delay: 10).

Utilisation (depuis le dossier du projet) :
  python scripts/cours_boursiers.py telecharger
  python scripts/cours_boursiers.py extraire --banques BIAT
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
import time
import zipfile
from collections import Counter
from pathlib import Path

import requests

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
import collecte_banques as cb  # noqa: E402

DOSSIER_COURS = cb.DOSSIER / "cours"
DOSSIER_ARCHIVES = DOSSIER_COURS / "bvmt"
MANIFESTE = DOSSIER_COURS / "manifeste_cours.csv"
PAUSE_BVMT = 10          # secondes : Crawl-delay du robots.txt de la BVMT
PREMIERE_ANNEE = 2019
URL_ARCHIVE = "https://www.bvmt.com.tn/sites/default/files/historiques/cotations/histo_cotation_{annee}.zip"


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


def telecharger_archives(s: requests.Session, m: dict, derniere_annee: int):
    """Une archive par année ; une archive déjà téléchargée n'est pas redemandée."""
    for annee in range(PREMIERE_ANNEE, derniere_annee + 1):
        cle = f"bvmt_{annee}"
        p = DOSSIER_ARCHIVES / f"histo_cotation_{annee}.zip"
        if m.get(cle, {}).get("statut") == "ok" and p.exists():
            continue
        url = URL_ARCHIVE.format(annee=annee)
        time.sleep(PAUSE_BVMT)
        r = s.get(url, timeout=180)
        ok = r.status_code == 200 and r.content[:2] == b"PK"
        if ok:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(r.content)
        m[cle] = {"source": cle, "url": url, "fichier": str(p) if ok else "", "statut": "ok" if ok else "absent",
                  "octets": len(r.content) if ok else "", "derniere_modification": r.headers.get("last-modified", ""),
                  "telecharge_le": dt.date.today().isoformat()}
        ecrire_manifeste(m)
        print(f"  {'OK' if ok else '--'}  {annee}  {url}")


def cmd_telecharger(args):
    m = lire_manifeste()
    s = requests.Session()
    s.headers.update(cb.ENTETES)
    telecharger_archives(s, m, dt.date.today().year - 1)


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
                 "COURS_REF": "cours_reference", "COURS_VEILLE": "cours_veille", "DERNIER_COURS": "dernier_cours"}
# une ouverture répétée sur plus de 30 % des séances d'une année est figée (archive 2021 : la même
# valeur sur environ 65 % des séances, pour les 12 banques, BIAT 94,300 de janvier à août)
PART_OUVERTURE_FIGEE = 0.30
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


def cmd_extraire(args):
    codes = cb.choisir_banques(args.banques)
    seances, remarques = lire_archives(codes)
    # ouvertures figées : valeur répétée sur plus de PART_OUVERTURE_FIGEE des séances de l'année
    figees = set()
    par_annee: dict[tuple[str, int], list] = {}
    for (b, d), r in seances.items():
        if (nombre(r.get("quantite")) or 0) > 0:
            par_annee.setdefault((b, d.year), []).append(r.get("ouverture"))
    for (b, a), valeurs in par_annee.items():
        v, n = Counter(valeurs).most_common(1)[0]
        if n > PART_OUVERTURE_FIGEE * len(valeurs):
            figees.add((b, a, v))
            remarques.append(f"{b} {a} : ouverture {v} répétée sur {n} séances sur {len(valeurs)} (figée)")
    champs = ["ticker", "banque", "isin", "date", "ouverture", "haut", "bas", "cloture", "volume",
              "nb_transactions", "capitaux", "statut", "source", "fichier"]
    sauts = []
    with SORTIE.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=champs, delimiter=";")
        w.writeheader()
        precedent: dict[str, float] = {}
        for (b, d) in sorted(seances, key=lambda k: (k[0], k[1])):
            r = seances[(b, d)]
            o, c, bas, haut, q = (nombre(r.get(k)) for k in ("ouverture", "cloture", "plus_bas", "plus_haut", "quantite"))
            statut = []
            if not q:
                # pas de transaction : l'archive met 0 aux cours de la séance et la clôture au cours
                # de référence ; ouverture, haut et bas restent vides
                statut.append("sans transaction")
                o = bas = haut = None
            elif (b, d.year, r.get("ouverture")) in figees:
                statut.append("ouverture figée dans l'archive")
                o = None
            elif o is not None and bas is not None and haut is not None and not (bas - 1e-9 <= o <= haut + 1e-9):
                statut.append("ouverture hors [plus bas, plus haut]")
                o = None
            veille = precedent.get(b)
            if veille and c and abs(c / veille - 1) > SEUIL_SAUT:
                sauts.append((b, d, veille, c))
                statut.append(f"variation {c / veille - 1:+.1%} : opération sur titres ?")
            precedent[b] = c or veille
            w.writerow({"ticker": cb.BANQUES[b]["ticker"], "banque": b, "isin": ISIN[b], "date": d.isoformat(),
                        "ouverture": o if o is not None else "", "haut": haut if haut is not None else "",
                        "bas": bas if bas is not None else "", "cloture": c if c is not None else "",
                        "volume": int(q) if q is not None else "", "nb_transactions": r.get("nb_transactions", ""),
                        "capitaux": nombre(r.get("capitaux")) if r.get("capitaux") else "",
                        "statut": " | ".join(statut), "source": "bvmt_archive", "fichier": r["fichier"]})
    with CONTROLE.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["banque", "date", "cloture_veille", "cloture", "variation_pct"])
        for b, d, v, c in sauts:
            w.writerow([b, d.isoformat(), v, c, f"{c / v - 1:+.2%}"])
    for b in codes:
        jours = [d for (bb, d) in seances if bb == b]
        if jours:
            print(f"  {b} : {len(jours)} séances du {min(jours)} au {max(jours)}")
    for x in remarques:
        print("  " + x)
    for b, d, v, c in sauts:
        print(f"  saut {b} {d} : {v} -> {c} ({c / v - 1:+.1%})")
    print(f"\nCours : {SORTIE}\nContrôle (variations de plus de {SEUIL_SAUT:.2%}) : {CONTROLE}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sous = ap.add_subparsers(dest="cmd", required=True)
    p = sous.add_parser("telecharger")
    p.set_defaults(f=cmd_telecharger)
    p = sous.add_parser("extraire")
    p.add_argument("--banques", help="codes séparés par des virgules (défaut : toutes)")
    p.set_defaults(f=cmd_extraire)
    args = ap.parse_args()
    args.f(args)


if __name__ == "__main__":
    main()
