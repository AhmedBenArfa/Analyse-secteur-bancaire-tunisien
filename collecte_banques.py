#!/usr/bin/env python3
"""
Collecte des indicateurs d'activité trimestriels des banques cotées à la BVMT
(T4 2019 -> dernier trimestre publié) et export en CSV pour Power BI.

Étapes :
  1. telecharger : cherche le PDF de chaque banque et chaque trimestre
       a) sur bvmt.com.tn (pages société),
       b) sur cmf.tn (dossier des indicateurs),
       c) en dernier recours dans les Bulletins Officiels quotidiens du CMF
          (on extrait seulement les pages de la banque).
     Chaque PDF est vérifié : il doit mentionner la date d'arrêté attendue.
  2. extraire : lit les tableaux, standardise les libellés, convertit en MDT,
     contrôle la cohérence (PNB = produits - charges) et écrit les CSV.

Utilisation :
  python collecte_banques.py tout
  python collecte_banques.py telecharger --debut 2019T4 --fin 2026T3 --banques UIB,BIAT
  python collecte_banques.py telecharger --sans-bulletins
  python collecte_banques.py extraire
  python collecte_banques.py urls --banques UIB --debut 2025T1 --fin 2025T1   (affiche les URL testées)
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import re
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DOSSIER = Path(__file__).resolve().parent / "donnees"
DOSSIER_PDF = DOSSIER / "pdf"
DOSSIER_BO = DOSSIER / "bulletins_cache"
MANIFESTE = DOSSIER / "manifeste_telechargements.csv"

PAUSE = 0.4          # secondes entre deux requêtes (politesse envers les serveurs)
TIMEOUT = 30
ENTETES = {"User-Agent": "Mozilla/5.0 (projet etudiant Power BI - collecte indicateurs bancaires)"}

# slugs : noms possibles dans les URL (le script essaie dans l'ordre et retient celui qui marche)
# motif_bo : expression régulière pour repérer la banque dans un Bulletin Officiel du CMF
BANQUES = {
    "AB":    {"nom": "Amen Bank",                               "ticker": "AB",
              "slugs": ["ab", "amen-bank", "amenbank", "amen"],
              "motif_bo": r"AMEN\s*BANK"},
    "ATB":   {"nom": "Arab Tunisian Bank",                      "ticker": "ATB",
              "slugs": ["atb", "arab-tunisian-bank"],
              "motif_bo": r"ARAB\s+TUNISIAN\s+BANK"},
    "TJARI": {"nom": "Attijari Bank",                           "ticker": "TJARI",
              "slugs": ["attijari-bank", "tjari", "attijari", "attijaribank"],
              "prefixes": ["tjari"],   # vu sur la BVMT : societes/attijari-bank/.../tjari-...pdf
              "motif_bo": r"ATTIJARI\s*BANK"},
    "BH":    {"nom": "BH Bank",                                 "ticker": "BH",
              "slugs": ["bh", "bh-bank", "bhbank", "bh_bank"],
              "motif_bo": r"\bBH\s*BANK\b|BANQUE\s+DE\s+L.HABITAT"},
    "BIAT":  {"nom": "Banque Internationale Arabe de Tunisie",  "ticker": "BIAT",
              "slugs": ["biat"],
              "motif_bo": r"BANQUE\s+INTERNATIONALE\s+ARABE\s+DE\s+TUNISIE|\bBIAT\b"},
    "BNA":   {"nom": "Banque Nationale Agricole",               "ticker": "BNA",
              "slugs": ["bna", "bna-bank"],
              "motif_bo": r"BANQUE\s+NATIONALE?\s+AGRICOLE"},
    "BT":    {"nom": "Banque de Tunisie",                       "ticker": "BT",
              "slugs": ["bt", "banque-de-tunisie"],
              "motif_bo": r"BANQUE\s+DE\s+TUNISIE(?!\s+ET\s+DES\s+EMIRATS)"},
    "BTE":   {"nom": "Banque de Tunisie et des Emirats",        "ticker": "BTE",
              "slugs": ["bte", "bte-adp"],
              "motif_bo": r"BANQUE\s+DE\s+TUNISIE\s+ET\s+DES\s+EMIRATS"},
    "STB":   {"nom": "Société Tunisienne de Banque",            "ticker": "STB",
              "slugs": ["stb"],
              "motif_bo": r"SOCIETE\s+TUNISIENNE\s+DE\s+BANQUE"},
    "UBCI":  {"nom": "Union Bancaire pour le Commerce et l'Industrie", "ticker": "UBCI",
              "slugs": ["ubci"],
              "motif_bo": r"UNION\s+BANCAIRE\s+POUR\s+LE\s+COMMERCE|\bUBCI\b"},
    "UIB":   {"nom": "Union Internationale de Banques",         "ticker": "UIB",
              "slugs": ["uib"],
              "motif_bo": r"UNION\s+INTERNATIONALE\s+DE\s+BANQUES"},
    "WIB":   {"nom": "Wifak International Bank",                "ticker": "WIFAK",
              "slugs": ["wifak", "wib", "wifak-bank", "el-wifak", "wifak-international-bank",
                        "el-wifack", "wifack"],
              # ancien nom : « EL WIFACK LEASING » / « BANQUE EL WIFACK » (avec un C)
              "motif_bo": r"WIFA?C?K\s+INTERNATIONAL\s+BANK|EL[\s\-]+WIFA?C?K"},
}

MOIS_FR = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet",
           "aout", "septembre", "octobre", "novembre", "decembre"]


# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------

def sans_accents(txt: str) -> str:
    txt = unicodedata.normalize("NFKD", txt)
    return "".join(c for c in txt if not unicodedata.combining(c))


def normaliser(txt: str) -> str:
    """minuscules, sans accents, apostrophes unifiées, espaces simples"""
    txt = sans_accents(txt).lower()
    txt = txt.replace("’", "'").replace("`", "'")
    txt = re.sub(r"[^a-z0-9' ]+", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


@dataclass(frozen=True)
class Trimestre:
    annee: int
    num: int  # 1..4

    @staticmethod
    def depuis_texte(t: str) -> "Trimestre":
        m = re.fullmatch(r"(\d{4})[Tt]([1-4])", t.strip())
        if not m:
            raise argparse.ArgumentTypeError(f"Format attendu AAAATn, par ex. 2019T4 (reçu : {t})")
        return Trimestre(int(m.group(1)), int(m.group(2)))

    @property
    def fin(self) -> dt.date:
        mois = self.num * 3
        jour = 31 if mois in (3, 12) else 30
        return dt.date(self.annee, mois, jour)

    def suivant(self) -> "Trimestre":
        return Trimestre(self.annee + (self.num == 4), self.num % 4 + 1)

    def __str__(self) -> str:
        return f"{self.annee}T{self.num}"


def trimestres(debut: Trimestre, fin: Trimestre):
    t = debut
    while (t.annee, t.num) <= (fin.annee, fin.num):
        yield t
        t = t.suivant()


def dernier_trimestre_publiable(aujourdhui: dt.date | None = None) -> Trimestre:
    """Dernier trimestre dont la date limite de publication (fin + 20 jours) est passée ou proche."""
    d = aujourdhui or dt.date.today()
    t = Trimestre(2019, 4)
    dernier = t
    while t.fin + dt.timedelta(days=10) <= d:
        dernier = t
        t = t.suivant()
    return dernier


def motifs_date(t: Trimestre) -> list[re.Pattern]:
    """Façons d'écrire la date d'arrêt dans un PDF (31/03/2025, 31.03.2025, 31 mars 2025, 1er trimestre 2025...)."""
    f = t.fin
    jj, mm, aaaa = f"{f.day:02d}", f"{f.month:02d}", str(f.year)
    mois = MOIS_FR[f.month - 1]
    ordinal = {1: r"(1er|1 er|premier|1ere|1 ere)", 2: r"(2eme|2 eme|2e|deuxieme|second)",
               3: r"(3eme|3 eme|3e|troisieme)", 4: r"(4eme|4 eme|4e|quatrieme)"}[t.num]
    return [
        re.compile(rf"{jj}\s*[/.\-]\s*{mm}\s*[/.\-]\s*{aaaa}"),
        re.compile(rf"\b{jj} {mm} {aaaa}\b"),
        re.compile(rf"{f.day}\s*(er)?\s+{mois}\s+{aaaa}"),
        re.compile(rf"fin\s+{mois}\s+{aaaa}"),
        re.compile(rf"{ordinal}\s+trimestre\s+(de\s+l.exercice\s+)?{aaaa}"),
    ]


def texte_pdf(contenu: bytes, max_pages: int | None = None) -> list[str]:
    from pypdf import PdfReader
    lecteur = PdfReader(io.BytesIO(contenu))
    pages = lecteur.pages if max_pages is None else lecteur.pages[:max_pages]
    sortie = []
    for p in pages:
        try:
            sortie.append(p.extract_text() or "")
        except Exception:
            sortie.append("")
    return sortie


def mentionne_trimestre(textes: list[str], t: Trimestre) -> bool:
    txt = normaliser(" ".join(textes))
    brut = sans_accents(" ".join(textes)).lower()
    return any(m.search(txt) or m.search(brut) for m in motifs_date(t))


def bon_document(textes: list[str], t: Trimestre) -> bool:
    """Le document parle du trimestre visé, et pas du même trimestre de l'année suivante
    (qui cite l'année visée comme période de comparaison)."""
    return mentionne_trimestre(textes, t) and not mentionne_trimestre(textes, Trimestre(t.annee + 1, t.num))


# ---------------------------------------------------------------------------
# Téléchargement
# ---------------------------------------------------------------------------

class Client:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update(ENTETES)
        self.nb = 0

    def pdf(self, url: str) -> bytes | None:
        """Renvoie le contenu si l'URL est un vrai PDF, sinon None."""
        time.sleep(PAUSE)
        self.nb += 1
        for essai in range(2):
            try:
                r = self.s.get(url, timeout=TIMEOUT)
            except requests.RequestException:
                time.sleep(2)
                continue
            if r.status_code == 200 and r.content[:5] == b"%PDF-":
                return r.content
            return None
        return None


Combo = tuple[str, str]   # (dossier de la société sur la BVMT, préfixe du nom de fichier)


def combinaisons(code: str) -> list[Combo]:
    """Couples (dossier, préfixe) possibles. Sur la BVMT ils diffèrent parfois :
    Attijari Bank range ses fichiers dans « attijari-bank » sous le préfixe « tjari »."""
    conf = BANQUES[code]
    prefixes = []
    for p in conf.get("prefixes", []) + conf["slugs"] + [conf["ticker"].lower()]:
        if p not in prefixes:
            prefixes.append(p)
    combos = []
    for d in conf["slugs"]:
        for p in ([d] if d in prefixes and not conf.get("prefixes") else []) + prefixes:
            if (d, p) not in combos:
                combos.append((d, p))
    return combos


def urls_candidates(code: str, t: Trimestre, combos: list[Combo]) -> list[tuple[str, Combo]]:
    """Liste de (url, combo) à essayer, du gabarit le plus fiable au moins fiable."""
    f = t.fin
    date_tiret = f"{f.day:02d}-{f.month:02d}-{f.year}"
    yy = f"{f.year % 100:02d}"
    n = t.num

    def noms(s: str) -> list[str]:
        s2 = s.replace("-", "_")
        rangs = ["1er", "1ere", "1eme"] if n == 1 else [f"{n}eme"]
        # vu sur le CMF au T2 2026 : ind_2eme_trim_2026_biat.pdf, ind_2eme_trim_2026_amen_bank.pdf
        recents = [f"ind_{r}_trim_{f.year}_{s2}.pdf" for r in rangs]
        return [f"indic_{n}trim{yy}_{s2}.pdf", f"ind_{n}trim{yy}_{s2}.pdf",
                f"indic_{n}trim{f.year}_{s2}.pdf", *recents, f"ind_{n}eme_trim_{s2}.pdf",
                f"ind_{n}eme_trim{yy}_{s2}.pdf"]

    urls: list[tuple[str, Combo]] = []
    # a) pages société de la BVMT (motif le plus régulier)
    for d, p in combos:
        urls.append((f"https://www.bvmt.com.tn/sites/default/files/societes/{d}/"
                     f"indicateurs-dactivite-trimestriels/{p}-indicateurs-dactivite-trimestriels-{date_tiret}.pdf",
                     (d, p)))
    # b) dossier des indicateurs du CMF (seul le préfixe compte)
    for d, p in combos:
        for nom in noms(p):
            urls.append((f"https://www.cmf.tn/sites/default/files/pdfs/emetteurs/informations/indicateurs/{nom}",
                         (d, p)))
    # c) dossiers mensuels de la BVMT (AAAA-MM du mois de dépôt)
    for decal in (1, 2):
        m = f.month + decal
        a = f.year + (m > 12)
        m = (m - 1) % 12 + 1
        for d, p in combos:
            for nom in noms(p):
                urls.append((f"https://www.bvmt.com.tn/sites/default/files/{a}-{m:02d}/{nom}", (d, p)))
    vu, out = set(), []
    for u, c in urls:
        if u not in vu:
            vu.add(u)
            out.append((u, c))
    return out


def lire_manifeste() -> dict[tuple[str, str], dict]:
    if not MANIFESTE.exists():
        return {}
    with MANIFESTE.open(encoding="utf-8") as f:
        return {(r["banque"], r["trimestre"]): r for r in csv.DictReader(f)}


def ecrire_manifeste(lignes: dict[tuple[str, str], dict]):
    champs = ["banque", "trimestre", "date_arrete", "statut", "source", "url", "fichier", "pages"]
    MANIFESTE.parent.mkdir(parents=True, exist_ok=True)
    with MANIFESTE.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=champs)
        w.writeheader()
        for cle in sorted(lignes):
            w.writerow({k: lignes[cle].get(k, "") for k in champs})


def chemin_pdf(code: str, t: Trimestre, suffixe: str = "") -> Path:
    return DOSSIER_PDF / code / f"{code}_{t}{suffixe}.pdf"


def telecharger_sites(client: Client, codes: list[str], liste_t: list[Trimestre], manifeste: dict):
    for code in codes:
        conf = BANQUES[code]
        ordre_prefere: list[str] = []  # gabarits d'URL qui ont déjà marché pour cette banque
        # noms de la banque dans les URL qui ont déjà marché : essayés en premier, mais les autres
        # restent essayés ensuite (une banque change de nom de fichier d'une année à l'autre :
        # BH publie « bh_bank » en 2026 mais « bh » en 2019)
        combos_connus: list[Combo] = []
        # du plus récent au plus ancien : les documents récents existent presque toujours,
        # ce qui permet d'apprendre vite le bon nom de la banque dans les URL
        for t in reversed(liste_t):
            cle = (code, str(t))
            if manifeste.get(cle, {}).get("statut") == "ok" and Path(manifeste[cle]["fichier"]).exists():
                continue
            combos = combos_connus + [c for c in combinaisons(code) if c not in combos_connus]
            cands = urls_candidates(code, t, combos)
            # on teste d'abord les gabarits d'URL et les noms qui ont déjà fonctionné (tri stable)
            cands.sort(key=lambda c: (0 if any(g in c[0] for g in ordre_prefere) else 1,
                                      0 if c[1] in combos_connus else 1))
            trouve = None
            for url, combo in cands:
                contenu = client.pdf(url)
                if not contenu:
                    continue
                try:
                    textes = texte_pdf(contenu, max_pages=3)
                except Exception:
                    continue
                if bon_document(textes, t):
                    trouve = (url, contenu)
                    if combo not in combos_connus:
                        combos_connus.append(combo)
                    break
                print(f"    ignoré (autre période) : {url}")
            if trouve:
                url, contenu = trouve
                p = chemin_pdf(code, t)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(contenu)
                gabarit = url.rsplit("/", 1)[0].split("/files/", 1)[-1][:40]
                if gabarit not in ordre_prefere:
                    ordre_prefere.insert(0, gabarit)
                manifeste[cle] = {"banque": code, "trimestre": str(t), "date_arrete": t.fin.isoformat(),
                                  "statut": "ok", "source": "site", "url": url, "fichier": str(p), "pages": ""}
                print(f"  OK  {code} {t}  <- {url}")
            else:
                manifeste[cle] = {"banque": code, "trimestre": str(t), "date_arrete": t.fin.isoformat(),
                                  "statut": "manquant", "source": "", "url": "", "fichier": "", "pages": ""}
                print(f"  --  {code} {t}  non trouvé sur les sites")
            ecrire_manifeste(manifeste)


# ---------------------------------------------------------------------------
# Liste des indicateurs publiée par le CMF (avant les Bulletins Officiels)
# ---------------------------------------------------------------------------

URL_LISTE_CMF = "https://www.cmf.tn/?page={page}&q=indicateurs-d-activit-"
LISTE_CMF = DOSSIER / "liste_indicateurs_cmf.csv"
# mots qui désignent une autre société que la banque (filiales d'assurance, leasing…)
MOTS_AUTRES_SOCIETES = {"assurance", "assurances", "leasing", "lease", "sicar", "sicav", "vie", "mag",
                        "capital", "invest", "intermediation", "finance"}


def lire_liste_cmf(client: "Client", max_pages: int, rafraichir: bool) -> list[str]:
    """URL des PDF d'indicateurs listés par le CMF. La liste est gardée dans donnees/ ;
    elle n'est relue sur le site qu'avec `rafraichir` (ou si elle n'existe pas). On s'arrête
    à la première page qui n'apporte aucun lien nouveau."""
    if LISTE_CMF.exists() and not rafraichir:
        with LISTE_CMF.open(encoding="utf-8") as f:
            return [r["url"] for r in csv.DictReader(f)]
    urls: list[str] = []
    for page in range(1, max_pages + 1):
        time.sleep(PAUSE)
        client.nb += 1
        try:
            r = client.s.get(URL_LISTE_CMF.format(page=page), timeout=TIMEOUT)
        except requests.RequestException:
            break
        if r.status_code != 200:
            break
        # le CMF écrit ses liens avec ou sans guillemets : <a href=https://…/ind_2eme_trim_2026_biat.pdf>
        liens = re.findall(r"""href=["']?([^"'\s>]+?\.pdf)""", r.text, re.I)
        nouveaux = []
        for l in liens:
            if "/indicateurs/" not in l:
                continue
            u = requests.compat.urljoin("https://www.cmf.tn/", l.replace(" ", "%20"))
            if u not in urls and u not in nouveaux:
                nouveaux.append(u)
        if not nouveaux:
            break
        urls += nouveaux
        print(f"  liste du CMF, page {page} : {len(nouveaux)} liens")
    LISTE_CMF.parent.mkdir(parents=True, exist_ok=True)
    with LISTE_CMF.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["url"])
        w.writerows([u] for u in urls)
    return urls


def jetons_nom(url: str) -> list[str]:
    nom = requests.utils.unquote(url.rsplit("/", 1)[-1]).lower().removesuffix(".pdf")
    return [j for j in re.split(r"[^a-z0-9]+", nom) if j]


def candidats_liste_cmf(code: str, t: Trimestre, urls: list[str]) -> list[str]:
    """PDF de la liste du CMF qui peuvent être le document (banque, trimestre), du plus
    probable au moins probable. Le contenu est vérifié ensuite (bon_document)."""
    conf = BANQUES[code]
    noms_banque = {tuple(s.replace("-", "_").split("_")) for s in conf["slugs"] + conf.get("prefixes", [])}
    noms_banque.add((conf["ticker"].lower(),))
    yy, aaaa = f"{t.annee % 100:02d}", str(t.annee)
    sortie = []
    for u in urls:
        j = jetons_nom(u)
        if MOTS_AUTRES_SOCIETES & set(j):
            continue
        if not any(tuple(j[i:i + len(n)]) == n for n in noms_banque for i in range(len(j))):
            continue
        nom = "_".join(j)
        annee = re.search(rf"(?<!\d)({aaaa}|{yy})(?!\d)|trim{yy}(?!\d)|trim{aaaa}", nom)
        rang = re.search(rf"(?<![a-z0-9]){t.num}(er|ere|eme|e|t|trim)|(?<!\d){t.num}trim", nom)
        autre_annee = re.search(r"(?<!\d)20\d\d(?!\d)|trim\d\d(?!\d)", nom) and not annee
        if autre_annee:
            continue
        score = (0 if annee else 2) + (0 if rang else 1)
        sortie.append((score, u))
    return [u for _, u in sorted(sortie)]


def telecharger_liste_cmf(client: "Client", manifeste: dict, max_pages: int, rafraichir: bool,
                          perimetre: set[tuple[str, str]] | None = None):
    """Pour chaque document manquant (du périmètre demandé), cherche dans la liste des indicateurs du CMF."""
    manquants = sorted(cle for cle, r in manifeste.items()
                       if r["statut"] != "ok" and (perimetre is None or cle in perimetre))
    if not manquants:
        return
    print(f"\nListe des indicateurs du CMF : {len(manquants)} documents manquants")
    urls = lire_liste_cmf(client, max_pages, rafraichir)
    print(f"  {len(urls)} PDF d'indicateurs dans la liste")
    for code, tri in manquants:
        t = Trimestre.depuis_texte(tri)
        trouve = None
        for url in candidats_liste_cmf(code, t, urls)[:6]:
            contenu = client.pdf(url)
            if not contenu:
                continue
            try:
                textes = texte_pdf(contenu, max_pages=3)
            except Exception:
                continue
            haut = sans_accents(" ".join(textes)[:3000]).upper()
            if bon_document(textes, t) and re.search(BANQUES[code]["motif_bo"], haut):
                trouve = (url, contenu)
                break
        if trouve:
            url, contenu = trouve
            p = chemin_pdf(code, t)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(contenu)
            manifeste[(code, tri)] = {"banque": code, "trimestre": tri, "date_arrete": t.fin.isoformat(),
                                      "statut": "ok", "source": "liste_cmf", "url": url,
                                      "fichier": str(p), "pages": ""}
            ecrire_manifeste(manifeste)
            print(f"  OK  {code} {tri}  <- {url}")


def urls_bulletin(d: dt.date) -> list[str]:
    base = "https://www.cmf.tn/sites/default/files/pdfs/publications/bulletin-officiel/"
    return [base + f"bo{d:%y%m%d}.pdf", base + f"bo{d:%d%m%Y}.pdf"]


def debut_avis(txt: str) -> bool:
    """Page qui commence l'avis d'indicateurs trimestriels d'une société."""
    haut = sans_accents(txt[:1500]).upper()
    return "INDICATEURS D" in haut and "PUBLIE" in haut


def contient_pnb(textes: list[str]) -> bool:
    """Le bloc contient un tableau d'indicateurs (ligne « Produit net bancaire », espaces ignorés :
    Wifak écrit « Bancair e »). Écarte les avis qui annoncent seulement la publication des
    indicateurs (AB, Bulletin du 14/04/2021 : note d'opération d'un emprunt obligataire)."""
    n = re.sub(r"\s+", "", sans_accents(" ".join(textes)).upper())
    return bool(re.search(r"PRODUITS?NETS?BANCAIRES?", n))


def telecharger_bulletins(client: Client, manifeste: dict, garder: bool, jours: int = 45,
                          perimetre: set[tuple[str, str]] | None = None):
    """Pour chaque trimestre où il manque des banques (du périmètre demandé), parcourt les Bulletins
    Officiels publiés dans les `jours` suivant la fin du trimestre et extrait les pages de chaque
    banque manquante."""
    from pypdf import PdfReader, PdfWriter

    manquants: dict[str, set[str]] = {}
    for (code, tri), r in manifeste.items():
        if r["statut"] != "ok" and (perimetre is None or (code, tri) in perimetre):
            manquants.setdefault(tri, set()).add(code)
    if not manquants:
        return

    for tri in sorted(manquants):
        t = Trimestre.depuis_texte(tri)
        restants = set(manquants[tri])
        print(f"\nBulletins officiels pour {tri} : {', '.join(sorted(restants))}")
        jour = t.fin + dt.timedelta(days=1)
        while restants and jour <= t.fin + dt.timedelta(days=jours):
            if jour.weekday() < 5:
                contenu = None
                url_bo = urls_bulletin(jour)[0]
                cache = DOSSIER_BO / f"bo_{jour:%Y%m%d}.pdf"
                if cache.exists():
                    contenu = cache.read_bytes()
                else:
                    for url_bo in urls_bulletin(jour):
                        contenu = client.pdf(url_bo)
                        if contenu:
                            if garder:
                                cache.parent.mkdir(parents=True, exist_ok=True)
                                cache.write_bytes(contenu)
                            break
                if contenu:
                    try:
                        lecteur = PdfReader(io.BytesIO(contenu))
                        textes = [(p.extract_text() or "") for p in lecteur.pages]
                    except Exception:
                        textes, lecteur = [], None
                    for code in sorted(restants):
                        motif = re.compile(BANQUES[code]["motif_bo"])
                        for i, txt in enumerate(textes):
                            if i == 0:          # sommaire du bulletin
                                continue
                            haut = sans_accents(txt[:1500]).upper()
                            if not (debut_avis(txt) and motif.search(haut)):
                                continue
                            # la page de la banque + les suivantes, jusqu'à l'avis d'une autre société
                            fin_bloc = i + 1
                            while fin_bloc < min(i + 3, len(textes)) and not debut_avis(textes[fin_bloc]):
                                fin_bloc += 1
                            if not bon_document(textes[i:fin_bloc], t) or not contient_pnb(textes[i:fin_bloc]):
                                continue
                            w = PdfWriter()
                            for k in range(i, fin_bloc):
                                w.add_page(lecteur.pages[k])
                            p = chemin_pdf(code, t, "_bulletin")
                            p.parent.mkdir(parents=True, exist_ok=True)
                            with p.open("wb") as f:
                                w.write(f)
                            manifeste[(code, tri)] = {
                                "banque": code, "trimestre": tri, "date_arrete": t.fin.isoformat(),
                                "statut": "ok", "source": "bulletin_officiel", "url": url_bo,
                                "fichier": str(p), "pages": f"{i + 1}-{fin_bloc}"}
                            print(f"  OK  {code} {tri}  <- bulletin du {jour:%d/%m/%Y}, page {i + 1}")
                            restants.discard(code)
                            ecrire_manifeste(manifeste)
                            break
            jour += dt.timedelta(days=1)
        for code in restants:
            print(f"  --  {code} {tri}  introuvable (à chercher à la main)")


def cmd_telecharger(args):
    codes = choisir_banques(args.banques)
    liste_t = list(trimestres(args.debut, args.fin))
    manifeste = lire_manifeste()
    client = Client()
    print(f"{len(codes)} banques × {len(liste_t)} trimestres ({args.debut} -> {args.fin})")
    perimetre = {(c, str(t)) for c in codes for t in liste_t}
    if not args.sans_sites:
        telecharger_sites(client, codes, liste_t, manifeste)
    if not args.sans_liste_cmf:
        telecharger_liste_cmf(client, manifeste, args.pages_liste_cmf, args.rafraichir_liste_cmf, perimetre)
    if not args.sans_bulletins:
        telecharger_bulletins(client, manifeste, garder=args.garder_bulletins, perimetre=perimetre)
    ok = sum(1 for r in manifeste.values() if r["statut"] == "ok")
    print(f"\nTerminé : {ok}/{len(manifeste)} documents trouvés, {client.nb} requêtes. Détail : {MANIFESTE}")


def cmd_urls(args):
    for code in choisir_banques(args.banques):
        for t in trimestres(args.debut, args.fin):
            print(f"# {code} {t}")
            for u, _ in urls_candidates(code, t, combinaisons(code)):
                print(u)


# ---------------------------------------------------------------------------
# Extraction des tableaux
# ---------------------------------------------------------------------------

# (code, libellé standard, catégorie, nature) ; nature = flux (cumulable) ou stock (solde)
INDICATEURS = [
    ("PROD_EXPL",     "Produits d'exploitation bancaire",       "Activité", "flux"),
    ("INT_PERCUS",    "Intérêts perçus",                         "Activité", "flux"),
    ("COMM_PROD",     "Commissions en produits",                 "Activité", "flux"),
    ("REV_PORTEF",    "Revenus du portefeuille-titres",          "Activité", "flux"),
    ("CHG_EXPL",      "Charges d'exploitation bancaire",        "Activité", "flux"),
    ("INT_ENCOURUS",  "Intérêts encourus",                       "Activité", "flux"),
    ("COMM_CHG",      "Commissions encourues",                   "Activité", "flux"),
    ("PNB",           "Produit net bancaire",                    "Résultat", "flux"),
    ("AUTRES_PROD",   "Autres produits d'exploitation",          "Résultat", "flux"),
    ("CHG_OPER",      "Charges opératoires",                     "Résultat", "flux"),
    ("FRAIS_PERS",    "Frais de personnel",                      "Résultat", "flux"),
    ("CHG_GEN",       "Charges générales d'exploitation",        "Résultat", "flux"),
    ("DOT_AMORT",     "Dotations aux amortissements",            "Résultat", "flux"),
    ("PORTEF",        "Structure du portefeuille",               "Bilan",    "stock"),
    ("PORTEF_COMM",   "Portefeuille-titres commercial",          "Bilan",    "stock"),
    ("PORTEF_INV",    "Portefeuille-titres d'investissement",    "Bilan",    "stock"),
    ("CREDITS",       "Encours des crédits à la clientèle",      "Bilan",    "stock"),
    ("DEPOTS",        "Encours des dépôts de la clientèle",      "Bilan",    "stock"),
    ("DEP_VUE",       "Dépôts à vue",                            "Bilan",    "stock"),
    ("DEP_EPARGNE",   "Dépôts d'épargne",                        "Bilan",    "stock"),
    ("DEP_TERME",     "Dépôts à terme et assimilés",             "Bilan",    "stock"),
    ("DEP_AUTRES",    "Autres dépôts et avoirs",                 "Bilan",    "stock"),
    ("EMPRUNTS",      "Emprunts et ressources spéciales",        "Bilan",    "stock"),
    ("CAP_PROPRES",   "Capitaux propres hors résultat de la période", "Bilan", "stock"),
]
NATURE = {c: n for c, _, _, n in INDICATEURS}

# Règles de reconnaissance des libellés (ordre important : du plus spécifique au plus général)
REGLES = [
    ("REV_PORTEF",   r"revenus? (du |des )?portefeuille"),
    ("PROD_EXPL",    r"produits d'?\s?exploitation bancaires?"),
    ("CHG_EXPL",     r"charges d'?\s?exploitation bancaires?"),
    ("PNB",          r"produits? nets? bancaires?"),      # BH : « PRODUITS NET BANCAIRE »
    ("AUTRES_PROD",  r"autres produits d'?\s?exploitation"),
    ("CHG_OPER",     r"charges operatoires"),
    ("FRAIS_PERS",   r"frais (de |du )?personnel"),
    ("CHG_GEN",      r"charges generales"),
    ("DOT_AMORT",    r"dotations? aux amortissements"),
    ("INT_ENCOURUS", r"interets? (et charges assimilees )?encourus|interets? (et charges )?payes"
                     r"|^charges encourues( et charges)?"),                   # Wifak (banque islamique)
    ("COMM_CHG",     r"commissions? encourues|commissions? (en )?charges?"),
    ("COMM_PROD",    r"commissions? (en )?produits?|commissions? percues"),
    ("PORTEF",       r"structure du portefeuille"),
    ("PORTEF_COMM",  r"portefeuille ?(titres?)? ?commercial"),
    ("PORTEF_INV",   r"portefeuille ?(titres?)? ?d'?\s?investissement"),
    ("CREDITS",      r"encours (nets? )?(des|de) credits|encours des creances (a|sur) la clientele|credits (a|nets? a) la clientele|encours des engagements"
                     r"|encours (net )?des financements|financements (nets? )?a la clientele"),   # Wifak
    ("DEP_VUE",      r"depots? a vue"),
    ("DEP_EPARGNE",  r"depots? d'?\s?epargne|comptes d'?\s?epargne|^tawfir"),          # Wifak : Tawfir
    ("DEP_TERME",    r"depots? a terme|istithmar"),                                    # Wifak : comptes Istithmars
    ("DEP_AUTRES",   r"autres depots"),
    ("DEPOTS",       r"encours (des |de )?depots?\b|depots (de la )?clientele"),   # TJARI 2026T2 : « DEPOT »
    ("EMPRUNTS",     r"emprunts? et ressources speciales|dettes de financements?( et ressources speciales)?"),
    ("CAP_PROPRES",  r"capitaux propres"),
    ("INT_PERCUS",   r"^interets?( et revenus assimiles)?( percus)?$|^interets? et revenus"
                     r"|^marges? et revenus assimiles"),                              # Wifak
]
REGLES_C = [(c, re.compile(m)) for c, m in REGLES]

# Libellés à ne jamais rattacher à un indicateur, même s'ils contiennent ses mots-clés.
# Wifak : « Pertes sur portefeuille titres commercial et opérations financières » est une charge,
# pas le solde du portefeuille commercial (PORTEF_COMM).
EXCLUSIONS = [re.compile(r"^pertes? sur portefeuille")]

# Indicateurs publiés sur plusieurs lignes à additionner (dans la même section du tableau).
# Wifak : « Revenus du portefeuille commercial & opérations financières » + « Revenus du
# portefeuille d'investissement » = REV_PORTEF.
CODES_A_ADDITIONNER = {"REV_PORTEF"}
COLONNES = ["trim_N", "trim_N1", "cumul_N", "cumul_N1", "exercice_N1"]

RE_FRAGMENT = re.compile(r"^\(?-?\d[\d.,]*\)?$")   # nombre ou morceau de nombre : "1", "56", "686,141"
RE_TIRET = re.compile(r"^[-–—‐]+$")
RE_POURCENT = re.compile(r"%\)?$")             # « 5,2% », « (11,26%) » (TJARI 2021T1)
RE_RENVOI = re.compile(r"^(\(\d\)|\(\*+\)|\*+)$")    # renvoi de note : (1), (*)

# Colonnes par défaut quand l'en-tête du tableau n'est pas lisible (selon le nombre de colonnes)
COLONNES_DEFAUT = {5: COLONNES, 4: ["trim_N", "trim_N1", "cumul_N", "cumul_N1"],
                   3: ["cumul_N", "cumul_N1", "exercice_N1"]}

# Ordres de grandeur plausibles en MDT (au-delà : erreur d'unité ou de colonne probable)
PLAGES_MDT = {"PNB": (5, 5000), "PROD_EXPL": (5, 10000), "CHG_OPER": (2, 3000),
              "CREDITS": (200, 60000), "DEPOTS": (200, 60000), "CAP_PROPRES": (20, 10000)}

# Indicateurs comparés d'un document à celui de l'année précédente (même trimestre)
CODES_RETRAITEMENT = ["PNB", "PROD_EXPL", "CHG_EXPL", "CHG_OPER", "CREDITS", "DEPOTS"]


def code_libelle(lib: str, regles_banque: list[tuple[str, re.Pattern]] = ()) -> str | None:
    """Code de l'indicateur d'un libellé. Les règles propres à la banque (gabarit) passent
    avant les règles générales."""
    n = normaliser(lib)
    n = re.sub(r"^(\d+\s*)+", "", n).strip()       # numérotation "1", "3-"
    n = re.sub(r"^[a-h] (?=\w)", "", n)             # sous-numérotation "a-", "b-" (BNA : « a- Intérêts »)
    if not n or any(rx.search(n) for rx in EXCLUSIONS):
        return None
    for code, rx in list(regles_banque) + REGLES_C:
        if rx.search(n):
            return None if code == "AUCUN" else code      # AUCUN : ligne à ignorer (gabarit)
    return None


# ---------------------------------------------------------------------------
# Gabarits : mise en page de chaque banque par période (gabarits.csv)
# ---------------------------------------------------------------------------

FICHIER_GABARITS = Path(__file__).resolve().parent / "gabarits.csv"
FACTEURS_UNITE = {"dinars": 1e-6, "milliers de dinars": 1e-3, "millions de dinars": 1.0}
# Contenu des charges opératoires publiées (colonne definition_charges_operatoires de gabarits.csv).
# Le coefficient d'exploitation harmonisé n'utilise que frais de personnel + charges générales.
DEFINITIONS_CHG_OPER = {
    "sans dotations": "total publié = frais de personnel + charges générales d'exploitation",
    "avec dotations publiees": "total publié = frais de personnel + charges générales + dotations "
                               "aux amortissements, les trois lignes publiées",
    "avec reste non detaille": "total publié > frais de personnel + charges générales ; la différence "
                               "(dotations ou autres charges) n'est pas détaillée dans le PDF",
    "composantes non publiees": "seul le total est publié ; coefficient harmonisé non calculable",
}


@dataclass
class Gabarit:
    banque: str
    debut: Trimestre
    fin: Trimestre
    trimestres: set[int]                      # numéros de trimestre concernés (T4 souvent différent)
    colonnes: list[str]                       # nom de chaque colonne de chiffres, de gauche à droite
    unite: str                                # clé de FACTEURS_UNITE
    libelles: list[tuple[str, re.Pattern]]    # règles de libellés propres à la banque
    ligne: int                                # numéro de ligne dans gabarits.csv (traçabilité)
    definition_chg_oper: str = ""             # clé de DEFINITIONS_CHG_OPER

    @property
    def nom(self) -> str:
        return f"{self.banque} {self.debut}-{self.fin} T{''.join(str(q) for q in sorted(self.trimestres))}"


def charger_gabarits(chemin: Path = FICHIER_GABARITS) -> list[Gabarit]:
    """Format (séparateur « ; ») : banque ; premier_trimestre ; dernier_trimestre ; trimestres (« 1,2,3 »
    ou « 4 ») ; colonnes (« trim_N|trim_N1|cumul_N|cumul_N1|exercice_N1 », _ignorer pour une colonne
    de variation, « trim_N+cumul_N » pour une colonne qui vaut les deux au T1) ; unite ; libelles (« CODE=regex », séparés par « || », regex sur le libellé
    normalisé : minuscules, sans accents) ; definition_charges_operatoires (clé de
    DEFINITIONS_CHG_OPER) ; documents_verifies ; remarque."""
    if not chemin.exists():
        return []
    sortie = []
    with chemin.open(encoding="utf-8-sig") as f:
        for i, r in enumerate(csv.DictReader(f, delimiter=";"), start=2):
            if not (r.get("banque") or "").strip() or r["banque"].startswith("#"):
                continue
            colonnes = [c.strip() for c in r["colonnes"].split("|")]
            # « trim_N+cumul_N » : une seule colonne qui vaut pour les deux (T1 de TJARI)
            inconnues = [c for c in colonnes for x in c.split("+") if x not in COLONNES + ["_ignorer"]]
            if inconnues or r["unite"] not in FACTEURS_UNITE:
                raise ValueError(f"gabarits.csv ligne {i} : colonnes {inconnues} ou unité « {r['unite']} » inconnues")
            libelles = []
            for regle in filter(None, (x.strip() for x in (r.get("libelles") or "").split("||"))):
                code, motif = regle.split("=", 1)
                if code.strip() not in NATURE and code.strip() != "AUCUN":
                    raise ValueError(f"gabarits.csv ligne {i} : code inconnu {code}")
                libelles.append((code.strip(), re.compile(motif.strip())))
            definition = (r.get("definition_charges_operatoires") or "").strip()
            if definition not in DEFINITIONS_CHG_OPER:
                raise ValueError(f"gabarits.csv ligne {i} : definition_charges_operatoires « {definition} » "
                                 f"inconnue ({', '.join(DEFINITIONS_CHG_OPER)})")
            sortie.append(Gabarit(r["banque"].strip(), Trimestre.depuis_texte(r["premier_trimestre"]),
                                  Trimestre.depuis_texte(r["dernier_trimestre"]),
                                  {int(q) for q in r["trimestres"].split(",")}, colonnes, r["unite"],
                                  libelles, i, definition))
    return sortie


_GABARITS: list[Gabarit] | None = None


def gabarit_pour(banque: str | None, t: Trimestre | None) -> Gabarit | None:
    global _GABARITS
    if banque is None or t is None:
        return None
    if _GABARITS is None:
        _GABARITS = charger_gabarits()
    cles = lambda x: (x.annee, x.num)
    for g in _GABARITS:
        if g.banque == banque and t.num in g.trimestres and cles(g.debut) <= cles(t) <= cles(g.fin):
            return g
    return None


def valeur(txt: str) -> float | None:
    t = txt.strip().replace(" ", "").replace(" ", "")
    negatif = t.startswith("(") and t.endswith(")") or t.startswith("-")
    t = t.strip("()-")
    if not t:
        return None
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", t):       # 1.234.567 -> milliers séparés par des points
        t = t.replace(".", "")
    elif re.fullmatch(r"\d+,\d{1,3}", t):            # 273,2 -> décimale
        t = t.replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(,\d{3})+", t):       # 1,234,567
        t = t.replace(",", "")
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if negatif else v


@dataclass
class Jeton:
    texte: str                 # nombre recollé ("6 479 908") ou "-" pour une case vide
    x0: float
    x1: float
    colonne: int | None = None  # rang de la colonne sur la page (None si aucune colonne détectée)

    @property
    def centre(self):
        return (self.x0 + self.x1) / 2


@dataclass
class Ligne:
    libelle: str
    nombres: list[Jeton] = field(default_factory=list)
    page: int = 0
    top: float = 0.0


@dataclass
class PageAnalysee:
    lignes: list[Ligne]
    bords: list[float]   # bord droit de chaque colonne de chiffres, de gauche à droite
    mots: list[dict]     # mots bruts de la page (pour lire l'en-tête du tableau)


def _est_chiffre(t: str) -> bool:
    return bool(RE_FRAGMENT.match(t))


def _est_case(t: str) -> bool:
    return _est_chiffre(t) or bool(RE_TIRET.match(t))


def _ecart_max(m: dict) -> float:
    """Écart maximal entre deux morceaux d'un même nombre : environ une espace (0,45 × corps), ou
    0,65 × la largeur d'un chiffre pour les polices à chiffres larges (STB 2024T2 : chiffres de
    5,4 pt en gras « Traditional Arabic », espaces de 3,0 pt entre les groupes de milliers)."""
    largeur = (m["x1"] - m["x0"]) / max(1, len(m["text"]))
    return max(2.5, 0.45 * (m["bottom"] - m["top"]), 0.65 * largeur)


def _series(frags: list[dict]) -> list[list[dict]]:
    """Regroupe les morceaux de chiffres proches (séparateur de milliers) en séries."""
    series: list[list[dict]] = []
    for m in frags:
        if series and m["x0"] - series[-1][-1]["x1"] <= _ecart_max(m):
            series[-1].append(m)
        else:
            series.append([m])
    return series


def bords_colonnes(rangees: list[list[dict]]) -> list[float]:
    """Bords droits des colonnes de chiffres (les montants sont alignés à droite).

    On prend la fin de chaque série de chiffres sur les rangées qui en ont au moins deux
    (lignes du tableau), on regroupe les positions proches et on garde celles qui reviennent
    sur assez de rangées. Les tirets (cases vides, souvent centrés) sont ignorés."""
    fins: list[tuple[float, int]] = []
    n_rangees = 0
    for i, frags in enumerate(rangees):
        series = [s for s in _series([m for m in frags if _est_chiffre(m["text"])])]
        if len(series) < 2:
            continue
        n_rangees += 1
        fins += [(s[-1]["x1"], i) for s in series]
    if not fins:
        return []
    fins.sort()
    groupes: list[list[tuple[float, int]]] = [[fins[0]]]
    for f in fins[1:]:
        if f[0] - groupes[-1][-1][0] <= 2.5:
            groupes[-1].append(f)
        else:
            groupes.append([f])
    # 20 % des rangées : sur une page de suite (BNA 2021T3, page 2), les colonnes trimestrielles
    # n'existent que sur les 3 lignes de charges opératoires, les autres étant des encours
    seuil = max(2, 0.2 * n_rangees)
    bords = [max(x for x, _ in g) for g in groupes if len({r for _, r in g}) >= seuil]
    # deux bords à moins de 14 pt : le premier est la fin d'un groupe de milliers ou de chiffres en
    # gras qui s'arrêtent avant les autres (UBCI 2022T2 : totaux à 319, lignes de détail à 331),
    # pas une colonne ; les vraies colonnes sont à plus de 30 pt l'une de l'autre
    propres: list[float] = []
    for b in bords:
        if propres and b - propres[-1] < 14:
            propres[-1] = b
        else:
            propres.append(b)
    return propres


def _jetons_par_colonne(frags: list[dict], bords: list[float]) -> list[Jeton]:
    """Rattache chaque morceau à sa colonne (premier bord droit à sa droite), puis recolle."""
    if not bords:
        sortie = []
        for s in _series(frags):
            txt = " ".join(m["text"] for m in s)
            sortie.append(Jeton("-" if all(RE_TIRET.match(m["text"]) for m in s) else txt,
                                s[0]["x0"], s[-1]["x1"]))
        return sortie
    cases: dict[int, list[dict]] = {}
    # 1) chiffres : on regroupe les morceaux d'un même nombre, on coupe une série qui finit sur
    #    un bord de colonne et continue au-delà, puis chaque nombre va à la colonne dont le bord est
    #    le plus proche de sa fin (les nombres en gras dépassent de quelques points : BT 2026T1)
    ecart_moyen = (bords[-1] - bords[0]) / (len(bords) - 1) if len(bords) > 1 else 50
    for serie in _series([m for m in frags if _est_chiffre(m["text"])]):
        morceaux, courant = [], []
        for i, m in enumerate(serie):
            courant.append(m)
            if i + 1 < len(serie) and any(abs(m["x1"] - b) <= 2.5 for b in bords):
                morceaux.append(courant)
                courant = []
        if courant:
            morceaux.append(courant)
        for morceau in morceaux:
            x1 = morceau[-1]["x1"]
            k = len(bords) if x1 > bords[-1] + 0.4 * ecart_moyen else \
                min(range(len(bords)), key=lambda i: (abs(bords[i] - x1), -i))
            cases.setdefault(k, []).extend(morceau)
    # 2) tirets (case vide, ou signe moins détaché « - 113 ») : premier bord à leur droite
    for m in frags:
        if not _est_chiffre(m["text"]):
            k = next((i for i, b in enumerate(bords) if m["x1"] <= b + 2.5), len(bords))
            cases.setdefault(k, []).append(m)
    sortie = []
    for k in sorted(cases):
        ms = sorted(cases[k], key=lambda m: m["x0"])
        chiffres = [m["text"] for m in ms if _est_chiffre(m["text"])]
        if not chiffres:
            txt = "-"                                        # case vide
        else:
            signe = "-" if RE_TIRET.match(ms[0]["text"]) else ""   # « - 113 » : nombre négatif
            txt = signe + " ".join(chiffres)
        sortie.append(Jeton(txt, ms[0]["x0"], ms[-1]["x1"], k))
    return sortie


def mots_page(page) -> list[dict]:
    """Mots de la page. Certains PDF étirent le texte horizontalement : pdfplumber marque alors
    les caractères « non droits » et les lit comme du texte vertical, un caractère par mot.
    Un caractère dont la matrice n'a ni rotation ni inclinaison est remis droit."""
    from pdfplumber.utils import extract_words

    def droit(c):
        a, b, cc, d = c["matrix"][:4]
        return abs(b) < 1e-6 and abs(cc) < 1e-6 and a > 0 and d > 0

    chars = [dict(c, upright=True) if not c.get("upright", True) and droit(c) else c for c in page.chars]
    mots = extract_words(chars, x_tolerance=1.2, y_tolerance=2.5, keep_blank_chars=False)
    # tirets typographiques (‐ ‑ – − ) ramenés au tiret simple : « ‐416 » est un nombre négatif
    # (BT 2019T4) et « ‐ » seul une case vide (BNA)
    for m in mots:
        m["text"] = m["text"].translate(TIRETS)
    return mots


TIRETS = str.maketrans({"‐": "-", "‑": "-", "‒": "-", "–": "-", "−": "-"})


def analyser_page(page, num_page: int) -> PageAnalysee:
    mots = mots_page(page)
    mots.sort(key=lambda m: (round(m["top"]), m["x0"]))
    groupes: list[list[dict]] = []
    for m in mots:
        if groupes and abs(groupes[-1][0]["top"] - m["top"]) <= 3:
            groupes[-1].append(m)
        else:
            groupes.append([m])

    rangees = []   # (mots du libellé, morceaux de chiffres, haut de la rangée)
    for g in groupes:
        g.sort(key=lambda m: m["x0"])
        hauteurs = sorted(m["bottom"] - m["top"] for m in g)
        h_mediane = hauteurs[len(hauteurs) // 2]
        utiles = []
        for i, m in enumerate(g):
            t = m["text"]
            if RE_POURCENT.search(t) or RE_RENVOI.match(t):
                continue                   # colonne de variation, renvoi de note
            if t.isdigit() and m["bottom"] - m["top"] < 0.75 * h_mediane:
                continue                   # renvoi de note en exposant (TJARI 2020T1 : « encourus¹ »)
            if i + 1 < len(g) and g[i + 1]["text"] == "%":
                continue                   # « 5,2 % » : le nombre d'une variation
            utiles.append(m)
        # les cases de chiffres sont la fin de la rangée ; ce qui précède est le libellé
        debut = len(utiles)
        while debut > 0 and _est_case(utiles[debut - 1]["text"]):
            debut -= 1
        rangees.append(([m["text"] for m in utiles[:debut]], utiles[debut:], g[0]["top"]))

    bords = bords_colonnes([frags for _, frags, _ in rangees])
    lignes = [Ligne(" ".join(lib), _jetons_par_colonne(frags, bords), num_page, top)
              for lib, frags, top in rangees]
    return PageAnalysee(lignes, bords, mots)


def lignes_page(page, num_page: int) -> list[Ligne]:
    return analyser_page(page, num_page).lignes


def type_colonne(entete: str, t: Trimestre) -> str | None:
    """Nature d'une colonne d'après son en-tête (« DEUXIEME TRIMESTRE 2025 »,
    « Du 01/04/2025 Au 30/06/2025 », « DU DEBUT DE L'EXERCICE ... AU 30/06/2024 », « 31/12/2024 »)."""
    n = sans_accents(entete).lower()
    # années sur 4 chiffres, ou sur 2 chiffres dans une date (30/06/26) ou après un mois (juin-26)
    mois = "|".join(MOIS_FR)
    annees = []
    for m in re.finditer(rf"(?<!\d)(20\d\d)(?!\d)|\d{{2}}/\d{{2}}/(\d{{2}})(?!\d)|(?:{mois})\s*-?\s*(\d{{2}})(?!\d)", n):
        a = m.group(1) or m.group(2) or m.group(3)
        annees.append((m.start(), int(a) if len(a) == 4 else 2000 + int(a)))
    # colonne de variation, avec ou sans dates (Wifak : « Variation », « % » ;
    # ATB : « Evolution décembre 19- décembre 18 », en montant)
    # (le titre « Var … » déborde parfois sur la colonne voisine « Au 31/12/2021 » : une date
    # complète l'emporte, TJARI 2022T2)
    if ((re.search(r"\bvariations?\b|\bevolution\b|\becart\b|\bvar\b", n)
         and not re.search(r"\d{2}/\d{2}/\d{2,4}", n)) or n.strip() in ("%", "en %")):
        return "_ignorer"
    if not annees:
        return None
    suffixe = {t.annee: "N", t.annee - 1: "N1"}.get(max(annees)[1])
    if suffixe is None:
        return None
    debut_trim = ["01/01", "01/04", "01/07", "01/10"][t.num - 1]
    if "trimestre" in n or re.search(rf"\bdu\b.*{debut_trim}", n):
        return f"trim_{suffixe}"
    if "debut" in n or "cumul" in n or re.search(r"\bdu\b", n):
        return f"cumul_{suffixe}"
    if ("31/12" in n or "decembre" in n) and suffixe == "N1":
        return "exercice_N1"
    if re.search(r"\d{2}/\d{2}/(20)?\d\d", n) or re.search(rf"(?:{mois})\s*-?\s*\d{{2}}", n):
        return f"cumul_{suffixe}"
    return None


def colonnes_entete(ap: PageAnalysee, haut_tableau: float, t: Trimestre) -> list[str] | None:
    """Lit l'en-tête au-dessus du tableau et renvoie le nom de chaque colonne, ou None."""
    bords = ap.bords
    if len(bords) < 2:
        return None
    gauche = bords[0] - 1.5 * (bords[1] - bords[0])
    # rangées au-dessus du tableau, en remontant jusqu'à une ligne de texte courant
    # (phrase d'introduction : plusieurs mots à gauche ET des mots dans la zone des colonnes ;
    # un libellé seul, à gauche, est simplement ignoré)
    rangees: dict[float, list[dict]] = {}
    for m in ap.mots:
        if haut_tableau - 65 <= m["top"] < haut_tableau - 1:
            cle = next((k for k in rangees if abs(k - m["top"]) <= 3), m["top"])
            rangees.setdefault(cle, []).append(m)
    entete: list[dict] = []
    for cle in sorted(rangees, reverse=True):
        r = rangees[cle]
        a_gauche = sum((m["x0"] + m["x1"]) / 2 < gauche for m in r)
        if a_gauche >= 3 and any((m["x0"] + m["x1"]) / 2 > bords[0] for m in r):
            break
        entete += r
    textes: list[list[str]] = [[] for _ in bords]
    for m in sorted(entete, key=lambda m: (round(m["top"]), m["x0"])):
        c = (m["x0"] + m["x1"]) / 2
        if c < gauche:
            continue
        k = next((i for i, b in enumerate(bords) if c <= b + 6), None)
        if k is not None:
            textes[k].append(m["text"])
    noms = [type_colonne(" ".join(x), t) for x in textes]
    if t.num == 4 and "exercice_N1" in noms and "cumul_N1" not in noms:
        noms[noms.index("exercice_N1")] = "cumul_N1"   # au T4, le 31/12/N-1 est le cumul N-1
    utiles = [x for x in noms if x != "_ignorer"]
    if None in noms or len(set(utiles)) != len(utiles) or not utiles:
        return None
    return noms


def detecter_facteur(texte: str, pnb_cumul: float | None) -> tuple[float, str]:
    """Facteur pour convertir en millions de dinars (MDT), d'après l'ordre de grandeur du PNB."""
    if pnb_cumul:
        v = abs(pnb_cumul)
        if v >= 2e6:
            return 1e-6, "dinars"
        if v >= 2e3:
            return 1e-3, "milliers de dinars"
        return 1.0, "millions de dinars"
    t = sans_accents(texte)
    if re.search(r"(?i)milliers? de dinars|mille dinars|\bmDT\b|\bKDT\b|en\s+1\s?000", t):
        return 1e-3, "milliers de dinars"
    if re.search(r"(?i)millions? de dinars|\bMDT\b|\bMTND\b", t):
        return 1.0, "millions de dinars"
    if re.search(r"(?i)en dinars", t):
        return 1e-6, "dinars"
    return 1e-3, "milliers de dinars (supposé)"


def controles(valeurs: dict[str, dict[str, float | None]], facteur: float, t: Trimestre | None) -> list[str]:
    """Contrôles de cohérence d'un document (valeurs dans l'unité du PDF)."""
    alertes = []

    def get(c, col):
        v = valeurs.get(c, {}).get(col)
        return None if v is None else v * facteur

    for col in ("cumul_N", "trim_N"):
        p, ch, pnb = get("PROD_EXPL", col), get("CHG_EXPL", col), get("PNB", col)
        if None not in (p, ch, pnb) and pnb:
            ecart = abs((p - ch) - pnb) / abs(pnb)
            if ecart > 0.02:
                alertes.append(f"{col} : produits - charges ≠ PNB (écart {ecart:.1%})")
    if get("PNB", "cumul_N") is None:
        alertes.append("PNB cumulé absent")
    if t:
        for c in ("PNB", "PROD_EXPL", "CHG_OPER"):
            trim, cumul = get(c, "trim_N"), get(c, "cumul_N")
            if None in (trim, cumul):
                continue
            if t.num == 1 and abs(trim - cumul) > 0.001 * abs(cumul):
                alertes.append(f"T1 : {c} trimestre ({trim:.3f}) ≠ cumul ({cumul:.3f})")
            if t.num > 1 and trim > cumul:
                alertes.append(f"{c} : trimestre > cumul, ordre des colonnes à vérifier")
    for c, (bas, haut) in PLAGES_MDT.items():
        for col in ("trim_N", "cumul_N"):
            v = get(c, col)
            if v is None or (col == "trim_N" and NATURE[c] == "stock"):
                continue
            mini = bas / 4 if col == "trim_N" else bas
            if not (mini <= v <= haut):
                alertes.append(f"{c} {col} = {v:,.3f} MDT : hors de l'ordre de grandeur plausible "
                               f"({mini:g} à {haut:g} MDT)")
    pnb, chg = get("PNB", "cumul_N"), get("CHG_OPER", "cumul_N")
    if pnb and chg and not (0.15 <= chg / pnb <= 1.5):
        alertes.append(f"coefficient d'exploitation de {chg / pnb:.0%} : invraisemblable")
    cred, dep = get("CREDITS", "cumul_N"), get("DEPOTS", "cumul_N")
    if cred and dep and not (0.3 <= cred / dep <= 3):
        alertes.append(f"crédits / dépôts de {cred / dep:.0%} : invraisemblable")
    return alertes


def controle_retraitements(docs: dict[tuple[str, str], dict[tuple[str, str], float]]) -> dict[tuple[str, str], list[str]]:
    """Compare cumul_N1 d'un document au cumul_N du même trimestre de l'année précédente.
    docs : (banque, trimestre) -> {(code, colonne): valeur_mdt}."""
    alertes: dict[tuple[str, str], list[str]] = {}
    for (code, tri), vals in docs.items():
        t = Trimestre.depuis_texte(tri)
        prec = docs.get((code, str(Trimestre(t.annee - 1, t.num))))
        if not prec:
            continue
        for c in CODES_RETRAITEMENT:
            a, b = vals.get((c, "cumul_N1")), prec.get((c, "cumul_N"))
            if a is None or b is None:
                continue
            if abs(a - b) > max(0.001, 0.0005 * abs(b)):
                alertes.setdefault((code, tri), []).append(
                    f"retraitement possible : {c} {t.annee - 1} = {a:,.3f} ici, "
                    f"{b:,.3f} dans le document de {t.annee - 1}T{t.num} (écart {a - b:+,.3f} MDT)")
    return alertes


def controle_trimestre_cumul(docs: dict[tuple[str, str], dict[tuple[str, str], float]]) -> dict[tuple[str, str], list[str]]:
    """Compare le trimestre publié (trim_N) à cumul_N(T) - cumul_N(T-1), T-1 étant lu dans le
    document du trimestre précédent de la même année. Un écart signale le plus souvent un
    retraitement des trimestres précédents, invisible dans le document du trimestre T."""
    alertes: dict[tuple[str, str], list[str]] = {}
    for (code, tri), vals in docs.items():
        t = Trimestre.depuis_texte(tri)
        if t.num == 1:
            continue
        prec = docs.get((code, str(Trimestre(t.annee, t.num - 1))))
        if not prec:
            continue
        for c in CODES_RETRAITEMENT:
            if NATURE[c] != "flux":
                continue
            publie, cumul, cumul_prec = vals.get((c, "trim_N")), vals.get((c, "cumul_N")), prec.get((c, "cumul_N"))
            if None in (publie, cumul, cumul_prec):
                continue
            calcule = cumul - cumul_prec
            if abs(publie - calcule) > max(0.001, 0.001 * abs(publie)):
                alertes.setdefault((code, tri), []).append(
                    f"écart trimestre/cumul : {c} trimestre publié {publie:,.3f}, cumul {tri} - cumul "
                    f"{t.annee}T{t.num - 1} = {calcule:,.3f} (écart {publie - calcule:+,.3f} MDT)")
    return alertes


# Versions des chiffres d'une même période (colonne `version`, reprise dans `source_valeur`) :
#   initiale                 : document du trimestre lui-même (trim_N, cumul_N) ;
#   revisee_T<q>_N+1         : colonne N-1 (trim_N1, cumul_N1) du document du même trimestre
#                              de l'année suivante ;
#   revisee_31-12_T<q>_N+1   : colonne « 31/12/N-1 » (exercice_N1) d'un document T1, T2 ou T3 de
#                              l'année suivante ; seulement pour le cumul au T4 (flux) et le solde
#                              au 31/12 (stocks), jamais pour le T4 seul. Version provisoire.
# Valeur retenue : revisee_T<q>_N+1 > revisee_31-12 du document le plus récent (T3 > T2 > T1) > initiale.
PREMIERE_PERIODE = Trimestre(2019, 4)
# 2 milliers de dinars : arrondi des banques qui publient en milliers. Le 1e-6 absorbe les erreurs
# de calcul en virgule flottante (0,002 calculé vaut parfois 0,0020000000001).
TOLERANCE_ARRONDI_MDT = 0.002 + 1e-6
# Seuil de matérialité d'une révision (part du cumul initial) : au-delà, révision importante
# (rupture de série marquée pour les graphiques) ; en deçà, retraitement mineur (spécification 5.2).
SEUIL_MATERIALITE = 0.02

# Totaux et leurs composantes (coefficient : +1 ajouté, -1 retranché)
GROUPES = {
    "PROD_EXPL": {"INT_PERCUS": 1, "COMM_PROD": 1, "REV_PORTEF": 1},
    "CHG_EXPL": {"INT_ENCOURUS": 1, "COMM_CHG": 1},
    "PNB": {"PROD_EXPL": 1, "CHG_EXPL": -1},
    "CHG_OPER": {"FRAIS_PERS": 1, "CHG_GEN": 1, "DOT_AMORT": 1},
    "DEPOTS": {"DEP_VUE": 1, "DEP_EPARGNE": 1, "DEP_TERME": 1, "DEP_AUTRES": 1},
    "PORTEF": {"PORTEF_COMM": 1, "PORTEF_INV": 1},
}
PARENT = {comp: total for total, comps in GROUPES.items() for comp in comps if total != "PNB"}


def version_admise(code_indicateur: str, version: str) -> bool:
    """Règle fixe : les capitaux propres ne prennent jamais la colonne 31/12 provisoire
    (sa définition change d'un document à l'autre : avant / après affectation du résultat)."""
    return not (code_indicateur == "CAP_PROPRES" and version.startswith("revisee_31-12_"))


# Mention d'un retraitement ou d'un souci de comparabilité dans un document (notes, renvois,
# commentaires) : « (*) Chiffres retraités », « Les chiffres de 2024 ont été retraités pour des
# raisons de comparabilité ». « Personnel retraité » ou « retraité de l'impact de… » seuls ne
# suffisent pas.
RX_MENTION_RETRAITEMENT = re.compile(
    r"comparabilit|retraitement|chiffres\b[^.\n]{0,60}retrait[ée]|retrait[ée]e?s?\s+pour\s+(des|les)\b", re.I)


def mention_retraitement(texte: str) -> str:
    """Première ligne du document qui annonce un retraitement (vide s'il n'y en a pas)."""
    for ligne in texte.splitlines():
        if RX_MENTION_RETRAITEMENT.search(ligne):
            return re.sub(r"\s+", " ", ligne).strip()[:200]
    return ""


def document_de_version(periode: Trimestre, version: str) -> tuple[int, int]:
    """(année, trimestre) du document qui publie une version : « revisee_T2_N+1 » d'une période de
    l'année N vient du T2 de N+1, « revisee_31-12_T3_N+1 » du T3 de N+1."""
    if version == "initiale":
        return periode.annee, periode.num
    return periode.annee + 1, int(version.split("_")[-2][1])


def priorite_version(version: str) -> int:
    """Plus petit = prioritaire."""
    if version == "initiale":
        return 9
    if version.startswith("revisee_31-12_"):
        return 4 - int(version.split("_")[2][1])     # T3 -> 1, T2 -> 2, T1 -> 3
    return 0                                          # revisee_T<q>_N+1


def table_versions(docs: dict[tuple[str, str], tuple[list[dict], str]],
                   illisibles: dict[tuple[str, str], str] | None = None) -> list[dict]:
    """docs : (banque, trimestre du document) -> (lignes extraites, nom du fichier).
    illisibles : (banque, trimestre) -> fichier des documents dont le tableau est une image ; leur
    version initiale est listée sans valeur, statut « illisible (image) ».
    Renvoie une ligne par banque × période × indicateur × mesure × version, avec la valeur
    retenue, sa source, l'écart de chaque version à la valeur retenue, la nature de la révision
    et les ruptures de série (changement de méthode)."""
    valeurs: dict[tuple[str, str, str, str], dict[str, tuple[float, str, int, str, str]]] = {}
    for (code, tri), (lignes, fichier) in docs.items():
        t = Trimestre.depuis_texte(tri)
        for l in lignes:
            col = l["colonne"]
            if col in ("trim_N", "cumul_N"):
                p, version = t, "initiale"
            elif col in ("trim_N1", "cumul_N1"):
                p, version = Trimestre(t.annee - 1, t.num), f"revisee_T{t.num}_N+1"
            elif col == "exercice_N1" and t.num in (1, 2, 3):
                p, version = Trimestre(t.annee - 1, 4), f"revisee_31-12_T{t.num}_N+1"
            else:
                continue
            if (p.annee, p.num) < (PREMIERE_PERIODE.annee, PREMIERE_PERIODE.num):
                continue
            mesure = "trim" if col.startswith("trim") else "cumul"
            valeurs.setdefault((code, str(p), l["code_indicateur"], mesure), {})[version] = \
                (l["valeur_mdt"], fichier, l["page"], l.get("note", ""), l.get("mention_retraitement", ""))

    # 0) nature de chaque révision (spécification 5.2, règle 4). L'écart à la version initiale est
    #    mesuré sur le CUMUL de la période (solde pour un stock ; trimestre seulement si le cumul
    #    manque) et le statut vaut pour le trimestre et le cumul de la même période et de la même
    #    version. Totaux : > 2 % → revision_importante ; ≤ 2 % → retraitement_mineur ; sous
    #    l'arrondi → vide. Composantes : statut de leur total (total stable mais composante qui bouge
    #    → reclassement). La note de retraitement du document est gardée pour information
    #    (mention_retraitement) : elle ne change ni le statut ni la valeur retenue.
    def ecart_cumul(code, per, ind, version) -> tuple[float, float] | None:
        for m in ("cumul", "trim"):
            vers = valeurs.get((code, per, ind, m), {})
            if "initiale" in vers and version in vers:
                return vers[version][0] - vers["initiale"][0], vers["initiale"][0]
        return None

    def nature_propre(code, per, ind, version) -> str | None:
        e = ecart_cumul(code, per, ind, version)
        if e is None:
            return None
        d, init = e
        if abs(d) <= TOLERANCE_ARRONDI_MDT:
            return ""
        return "revision_importante" if abs(d) > SEUIL_MATERIALITE * abs(init) else "retraitement_mineur"

    revisions: dict[tuple[str, str, str], set[str]] = {}
    for (code, per, ind, _), vers in valeurs.items():
        revisions.setdefault((code, per, ind), set()).update(v for v in vers if v != "initiale")
    natures: dict[tuple[str, str, str, str], str] = {}      # (banque, période, indicateur, version)
    for (code, per, ind), vs in revisions.items():
        parent = PARENT.get(ind)
        for v in vs:
            n = nature_propre(code, per, ind, v)
            if n is None:
                continue
            n_total = nature_propre(code, per, parent, v) if parent else None
            if n_total is not None:
                n = n_total if n_total else ("reclassement" if n else "")
            natures[(code, per, ind, v)] = n

    # 1) version retenue : toujours la plus récente révision admise (priorité), avec ou sans note
    sources: dict[tuple[str, str, str, str], str | None] = {}
    for cle, vers in valeurs.items():
        admises = [v for v in vers if version_admise(cle[2], v)]
        sources[cle] = min(admises, key=priorite_version) if admises else None
    # 2) une composante prend la même version que son total
    for (code, per, ind, mesure), vers in valeurs.items():
        total = PARENT.get(ind)
        src_total = sources.get((code, per, total, mesure)) if total else None
        if src_total and src_total in vers and version_admise(ind, src_total):
            sources[(code, per, ind, mesure)] = src_total

    def statut_revision(code, per, ind, mesure, version) -> str:
        """Pour une version révisée, sa nature ; pour la version initiale remplacée, la nature de
        la version retenue. Sans version initiale : vide."""
        if not version_admise(ind, version):
            return "exclue (capitaux propres, 31/12 provisoire)"
        if version == "initiale":
            return natures.get((code, per, ind, sources.get((code, per, ind, mesure))), "")
        return natures.get((code, per, ind, version), "")

    # 3) rupture de série (annotation des graphiques) : période dont la valeur retenue est une
    #    révision importante (> 2 % sur le cumul), marquée sur la période elle-même, trimestre et cumul
    ruptures: dict[tuple[str, str, str, str], str] = {}
    for (code, per, ind, mesure), source in sources.items():
        if not source or source == "initiale" or natures.get((code, per, ind, source)) != "revision_importante":
            continue
        d, init = ecart_cumul(code, per, ind, source)
        doc = document_de_version(Trimestre.depuis_texte(per), source)
        pct = f"{100 * d / abs(init):+.1f} %" if init else "depuis zéro"
        ruptures[(code, per, ind, mesure)] = (f"{per} révisé de {pct} sur le cumul ({init:,.3f} publié, "
                                             f"{init + d:,.3f} dans le document {doc[0]}T{doc[1]})")

    sortie = []
    for (code, per, ind, mesure), vers in sorted(valeurs.items()):
        source = sources[(code, per, ind, mesure)]
        retenue = vers[source][0] if source else None
        p = Trimestre.depuis_texte(per)
        rupture = ruptures.get((code, per, ind, mesure), "")
        commun = {"banque": code, "trimestre": per, "date_arrete": p.fin.isoformat(),
                  "annee": p.annee, "num_trimestre": p.num, "code_indicateur": ind, "mesure": mesure,
                  "valeur_retenue": retenue, "source_valeur": source or "",
                  "rupture_serie": "oui" if rupture else "", "detail_rupture": rupture}
        if illisibles and (code, per) in illisibles and "initiale" not in vers:
            sortie.append({**commun, "version": "initiale", "valeur_mdt": None,
                           "fichier": illisibles[(code, per)], "page": "", "ecart_vs_retenue": None,
                           "statut_revision": "illisible (image)", "note_definition": "",
                           "mention_retraitement": ""})
        for version in sorted(vers, key=priorite_version):
            v, fichier, page, note, mention = vers[version]
            sortie.append({**commun, "version": version, "valeur_mdt": v, "fichier": fichier, "page": page,
                           "ecart_vs_retenue": None if retenue is None else round(v - retenue, 9),
                           "statut_revision": "retenue" if version == source
                           else statut_revision(code, per, ind, mesure, version),
                           "note_definition": note, "mention_retraitement": mention})
    # 4) document illisible dont une mesure n'est reprise par aucun autre document (BTE : T4 seul de
    #    2021 et de 2022, le document T4 de l'année suivante étant lui aussi une image) : ligne explicite
    #    « non disponible (image) », sans valeur ni valeur retenue (jamais zéro). version ≠ source_valeur :
    #    elle va dans la table Revisions (page qualité), pas dans Fait_Indicateurs.
    for (code, per), fichier in sorted((illisibles or {}).items()):
        p = Trimestre.depuis_texte(per)
        indicateurs = sorted({ind for (c, pe, ind, _) in valeurs if c == code and pe == per})
        for ind in indicateurs:
            for mesure in (("trim", "cumul") if NATURE[ind] == "flux" else ("cumul",)):
                if (code, per, ind, mesure) in valeurs:
                    continue
                sortie.append({"banque": code, "trimestre": per, "date_arrete": p.fin.isoformat(),
                               "annee": p.annee, "num_trimestre": p.num, "code_indicateur": ind,
                               "mesure": mesure, "valeur_retenue": None, "source_valeur": "",
                               "rupture_serie": "", "detail_rupture": "", "version": "initiale",
                               "valeur_mdt": None, "fichier": fichier, "page": "", "ecart_vs_retenue": None,
                               "statut_revision": STATUT_NON_DISPONIBLE, "note_definition": "",
                               "mention_retraitement": ""})
    return sortie


STATUT_NON_DISPONIBLE = "non disponible (image)"


def variations_comparables(docs: dict[tuple[str, str], tuple[list[dict], str]]) -> list[dict]:
    """Variation sur un an calculée à l'intérieur d'un même document : colonne N contre colonne N-1
    (trimestre : trim_N / trim_N1 ; cumul ou solde : cumul_N / cumul_N1). Les deux chiffres sont
    publiés ensemble, sur la même méthode : la variation reste juste quand la banque retraite N-1."""
    sortie = []
    for (code, tri), (lignes, fichier) in sorted(docs.items()):
        t = Trimestre.depuis_texte(tri)
        par_col = {(l["code_indicateur"], l["colonne"]): l for l in lignes}
        for (ind, col), l in sorted(par_col.items()):
            if col not in ("trim_N", "cumul_N"):
                continue
            n1 = par_col.get((ind, col[:-1] + "N1"))
            if n1 is None:
                continue
            vn, vn1 = l["valeur_mdt"], n1["valeur_mdt"]
            sortie.append({"banque": code, "trimestre": tri, "date_arrete": t.fin.isoformat(),
                           "annee": t.annee, "num_trimestre": t.num, "code_indicateur": ind,
                           "mesure": col[:-2], "valeur_N": vn, "valeur_N1": vn1,
                           "variation_pct": round((vn - vn1) / abs(vn1), 9) if vn1 else None,
                           "fichier": fichier, "page": l["page"],
                           "mention_retraitement": l.get("mention_retraitement", "")})
    return sortie


def controle_somme_annuelle(versions: list[dict]) -> list[dict]:
    """Avec les valeurs retenues : somme des 4 trimestres = cumul du T4, pour chaque flux.
    statut : ok ; « en attente de révision » quand le cumul retenu est la version provisoire
    31/12/N-1 (le T4 seul attend le document T4 suivant) ; « rupture de série » quand l'année
    contient un changement de méthode (période retraitée ou rupture marquée) ; « ecart » sinon."""
    retenue: dict[tuple[str, str, str, str], tuple[float, str]] = {}
    ruptures: set[tuple[str, int, str]] = set()     # (banque, année, indicateur) avec rupture de série
    for r in versions:
        if r["valeur_retenue"] is None:      # « non disponible (image) » : pas de valeur, l'année est sautée
            continue
        retenue[(r["banque"], r["trimestre"], r["code_indicateur"], r["mesure"])] = \
            (r["valeur_retenue"], r["source_valeur"])
        if r.get("rupture_serie"):
            ruptures.add((r["banque"], r["annee"], r["code_indicateur"]))
    sortie = []
    for (code, tri, ind, mesure), (cumul, source) in sorted(retenue.items()):
        t = Trimestre.depuis_texte(tri)
        if mesure != "cumul" or t.num != 4 or NATURE[ind] != "flux" or ind not in CODES_RETRAITEMENT:
            continue
        trims = [retenue.get((code, f"{t.annee}T{q}", ind, "trim")) for q in (1, 2, 3, 4)]
        if None in trims:
            continue
        somme = sum(v for v, _ in trims)
        # tolérance : l'arrondi des chiffres publiés en milliers de dinars (1 à 2 milliers)
        if abs(somme - cumul) <= TOLERANCE_ARRONDI_MDT:
            statut = "ok"
        elif source.startswith("revisee_31-12_"):
            statut = "en attente de révision"
        elif (code, t.annee, ind) in ruptures:
            # changement de méthode en cours d'année : trimestres et cumul sur deux méthodes (BH 2025)
            statut = "rupture de série"
        else:
            statut = "ecart"
        sortie.append({"banque": code, "annee": t.annee, "code_indicateur": ind, "somme_trimestres": somme,
                       "cumul_T4": cumul, "source_cumul": source, "ecart": somme - cumul, "statut": statut})
    return sortie


def comparaison_revisions_31_12(versions: list[dict]) -> list[str]:
    """Quand le T4 suivant (revisee_T4_N+1) et une colonne 31/12/N-1 d'un T1–T3 existent tous deux,
    signale les écarts entre eux (ils figurent aussi dans ecart_vs_retenue, table Revisions)."""
    alertes = []
    for r in versions:
        if (r["version"].startswith("revisee_31-12_") and r["source_valeur"] == "revisee_T4_N+1"
                and abs(r["ecart_vs_retenue"]) > TOLERANCE_ARRONDI_MDT):
            alertes.append(f"{r['banque']} {r['annee']} {r['code_indicateur']} : 31/12 du document "
                           f"{r['version'].split('_')[2]} {r['annee'] + 1} = {r['valeur_mdt']:,.3f}, "
                           f"T4 {r['annee'] + 1} (N-1) = {r['valeur_retenue']:,.3f} "
                           f"(écart {r['ecart_vs_retenue']:+,.3f} MDT, {r['statut_revision'] or 'sous la tolérance'})")
    return alertes


def definition_capitaux_propres(texte: str) -> str:
    """Définition des capitaux propres annoncée par les notes du document (information seulement)."""
    n = re.sub(r"\s+", " ", sans_accents(texte).lower().replace("’", "'"))
    trouve = []
    if "avant affectation" in n:
        trouve.append("avant affectation du résultat")
    if "apres affectation" in n:
        trouve.append("après affectation du résultat")
    if re.search(r"non tenu des? resultats?|n'incluent pas (le|les) resultats?|"
                 r"resultats? .{0,120}ne sont pas inclus", n):
        trouve.append("résultat de la période non inclus")
    return " + ".join(trouve)


PREFIXE_COMPOSANTES = "écart composantes : "
PREFIXE_ILLISIBLE = "illisible (image) : "


def statut_document(lignes: list[dict], alertes: list[str], ecarts: list[str], retr: list[str],
                    origine: str = "") -> str:
    """Statut d'un document dans controle_extraction.csv. Un écart entre les charges opératoires
    et leurs composantes vient de la banque (vérifié dans les PDF : BT 2020T3, BNA 2023T2) : il est
    signalé sans bloquer, comme l'écart trimestre/cumul. Un tableau en image (BH 2019T4) est
    « illisible (image) » : ses chiffres ne sont repris que par les colonnes N-1 du document
    de l'année suivante (version révisée)."""
    bloquantes = [a for a in alertes if not a.startswith(PREFIXE_COMPOSANTES)]
    if not lignes:
        return "illisible (image)" if any(a.startswith(PREFIXE_ILLISIBLE) for a in alertes) else "echec"
    if bloquantes:
        return "a verifier"
    if origine == ORIGINE_SAISIE:
        return ORIGINE_SAISIE          # valeurs relevées sur l'image, contrôles de cohérence passés
    if len(bloquantes) < len(alertes):
        return "ecart composantes"
    if ecarts:
        return "ecart trimestre/cumul"
    return "retraitement possible" if retr else "ok"


def controle_definition_chg_oper(valeurs: dict[str, dict[str, float | None]], definition: str) -> list[str]:
    """Charges opératoires publiées comparées à leurs composantes, selon la définition du gabarit.
    Valeurs en unité de la source ; tolérance : 1 unité par ligne additionnée (arrondi de la banque)."""
    if definition not in ("sans dotations", "avec dotations publiees", "avec reste non detaille"):
        return []
    alertes = []
    for col, total in valeurs.get("CHG_OPER", {}).items():
        fp = valeurs.get("FRAIS_PERS", {}).get(col)
        cg = valeurs.get("CHG_GEN", {}).get(col)
        dot = valeurs.get("DOT_AMORT", {}).get(col)
        if total is None:
            continue
        if fp is None or cg is None or (definition == "avec dotations publiees" and dot is None):
            alertes.append(f"{PREFIXE_COMPOSANTES}charges opératoires {col} : composante absente (gabarit : {definition})")
            continue
        reste = total - fp - cg - (dot if definition == "avec dotations publiees" else 0)
        if definition == "avec reste non detaille":
            if reste < -2:
                alertes.append(f"{PREFIXE_COMPOSANTES}charges opératoires {col} < frais de personnel + charges générales "
                               f"(reste {reste:,.0f}, gabarit : {definition})")
        elif abs(reste) > (3 if definition == "avec dotations publiees" else 2):
            alertes.append(f"{PREFIXE_COMPOSANTES}charges opératoires {col} ≠ somme des composantes (écart {reste:,.0f}, "
                           f"gabarit : {definition})")
    return alertes


def _suite_de_nombres(dessus: Ligne, l: Ligne) -> bool:
    """Vrai si la ligne l (sans libellé) ne contient que des groupes de 3 chiffres placés juste
    sous des nombres de la ligne du dessus, dans les mêmes colonnes : fin de nombres renvoyée
    à la ligne dans une case trop étroite."""
    cols_dessus = {j.colonne for j in dessus.nombres if j.texte != "-" and j.colonne is not None}
    return (dessus.page == l.page and 0 < l.top - dessus.top <= 12
            and all(re.fullmatch(r"\d{3}", j.texte) and j.colonne in cols_dessus for j in l.nombres))


def extraire_pdf(chemin: Path, t: Trimestre | None = None,
                 banque: str | None = None) -> tuple[list[dict], list[str]]:
    """Renvoie (lignes extraites, alertes) pour un PDF. Si un gabarit existe pour la banque et le
    trimestre (gabarits.csv), il fixe l'ordre des colonnes, l'unité et les libellés particuliers ;
    la lecture de l'en-tête et la règle d'unité servent alors de contrôles."""
    import pdfplumber

    alertes: list[str] = []
    gab = gabarit_pour(banque, t)
    regles = gab.libelles if gab else []
    toutes: list[Ligne] = []
    pages: dict[int, PageAnalysee] = {}
    texte_complet = ""   # 4 premières pages (tableau) : sert à deviner l'unité
    texte_notes = ""     # toutes les pages : notes (définition des capitaux propres…)
    pages_image: list[int] = []   # pages sans couche texte utile mais avec des images (tableau scanné)
    with pdfplumber.open(chemin) as pdf:
        for i, page in enumerate(pdf.pages[:12], start=1):
            texte = page.extract_text() or ""
            texte_notes += texte + "\n"
            if i <= 4:
                texte_complet += texte + "\n"
                pages[i] = analyser_page(page, i)
                toutes += pages[i].lignes
                if page.images and len(page.chars) < 1000:     # BTE 2020–2023 : ~530 caractères (titre et renvois)
                    pages_image.append(i)

    # libellés sur deux lignes : on recolle un libellé sans nombre à la ligne suivante ;
    # une ligne de chiffres sans libellé prend celui de la ligne juste en dessous s'il en est tout
    # proche (BNA : « 10- Capitaux Propres * », décalé de quelques points vers le bas)
    fusion: list[Ligne] = []
    attente = ""
    consommees: set[int] = set()
    for i, l in enumerate(toutes):
        if i in consommees:
            continue
        if l.libelle and not l.nombres:
            attente = (attente + " " + l.libelle).strip() if code_libelle(l.libelle, regles) is None else l.libelle
            continue
        if l.nombres and not l.libelle and fusion and _suite_de_nombres(fusion[-1], l):
            # nombre trop large pour sa case, renvoyé à la ligne : « 10 575 » puis « 743 » juste
            # en dessous, dans la même colonne (BH 2023T2, encours des crédits)
            par_col = {j.colonne: j for j in fusion[-1].nombres}
            for j in l.nombres:
                par_col[j.colonne].texte += " " + j.texte
            continue
        if l.nombres:
            lib = l.libelle
            if attente and (not lib or code_libelle(lib, regles) is None):
                lib = (attente + " " + lib).strip()
            if (not lib or code_libelle(lib, regles) is None) and i + 1 < len(toutes):
                # fin du libellé juste sous les chiffres (TJARI 2022T2 : « 1) PRODUITS D'EXPLOITATION »,
                # chiffres, « BANCAIRE »)
                s = toutes[i + 1]
                if s.libelle and not s.nombres and s.page == l.page and 0 <= s.top - l.top <= 7:   # AB : 6,1 pt
                    lib = (lib + " " + s.libelle).strip()
                    consommees.add(i + 1)
            fusion.append(Ligne(lib, l.nombres, l.page, l.top))
        attente = ""

    # reconnaissance des indicateurs, en suivant la section parente (produits / charges)
    trouves: dict[str, Ligne] = {}
    supplements: dict[str, list[Ligne]] = {}   # lignes de plus à additionner (CODES_A_ADDITIONNER)
    parent = None
    for l in fusion:
        c = code_libelle(l.libelle, regles)
        if c is None and parent and re.search(r"^[\s\-–•]*\d*\s*-?\s*interets?", normaliser(l.libelle)):
            c = "INT_ENCOURUS" if parent == "CHG_EXPL" else "INT_PERCUS"
        if c is None and parent and re.search(r"commissions?", normaliser(l.libelle)):
            c = "COMM_CHG" if parent == "CHG_EXPL" else "COMM_PROD"
        if c == "INT_PERCUS" and parent == "CHG_EXPL":
            c = "INT_ENCOURUS"
        if c == "COMM_PROD" and parent == "CHG_EXPL":
            c = "COMM_CHG"
        if c in ("PROD_EXPL", "CHG_EXPL"):
            parent = c
        elif c in ("PNB", "CHG_OPER", "CREDITS", "DEPOTS"):
            parent = None
        if c and c not in trouves:
            trouves[c] = l
        elif c in CODES_A_ADDITIONNER and parent == "PROD_EXPL":
            supplements.setdefault(c, []).append(l)
        if c == "CAP_PROPRES":
            break

    alerte_image = (f"{PREFIXE_ILLISIBLE}PNB non lu, page(s) {pages_image} en image sans couche texte "
                    f"(moins de 1 000 caractères)")
    if "PNB" not in trouves:
        if pages_image:
            return [], [alerte_image]
        return [], ["PNB introuvable : tableau non reconnu (PDF scanné ou mise en page inhabituelle ?)"]

    # nom de chaque colonne : d'après l'en-tête du tableau si on sait le lire, sinon ordre habituel
    noms_page: dict[int, list[str] | None] = {}

    def noms_colonnes(num_page: int) -> list[str] | None:
        if num_page not in noms_page:
            ap = pages[num_page]
            lignes_tab = [l for l in fusion if l.page == num_page and
                          sum(j.colonne is not None for j in l.nombres) >= 2]
            lu = None
            if lignes_tab and t:
                lu = colonnes_entete(ap, min(l.top for l in lignes_tab), t)
            if gab:
                # le gabarit décide ; l'en-tête lu n'est qu'un contrôle
                if len(ap.bords) == len(gab.colonnes):
                    noms = gab.colonnes
                    if lu and not (len(lu) == len(gab.colonnes) and
                                   all(a in g.split("+") for a, g in zip(lu, gab.colonnes))):
                        alertes.append(f"page {num_page} : en-tête lu {lu} ≠ gabarit {gab.colonnes}")
                else:
                    noms = lu
                    alertes.append(f"page {num_page} : {len(ap.bords)} colonnes détectées, le gabarit "
                                   f"({gab.nom}) en prévoit {len(gab.colonnes)}")
            else:
                noms = lu
                if noms is None:
                    noms = COLONNES_DEFAUT.get(len(ap.bords))
                    alertes.append(f"page {num_page} : en-tête des colonnes non reconnu, "
                                   f"ordre supposé {noms} ({len(ap.bords)} colonnes)")
            noms_page[num_page] = noms
        return noms_page[num_page]

    def affecter(l: Ligne) -> dict[str, float | None]:
        noms = noms_colonnes(l.page) or []
        res: dict[str, float | None] = {}
        for j in l.nombres:
            if j.colonne is None or j.colonne >= len(noms) or noms[j.colonne] == "_ignorer":
                continue
            for nom in noms[j.colonne].split("+"):      # « trim_N+cumul_N » : les deux
                if nom not in res:
                    res[nom] = None if j.texte == "-" else valeur(j.texte)
        return res

    def additionner(a: dict[str, float | None], b: dict[str, float | None]) -> dict[str, float | None]:
        return {col: (a.get(col) or 0) + (b.get(col) or 0) if None not in (a.get(col), b.get(col))
                else (a.get(col) if b.get(col) is None else b.get(col)) for col in set(a) | set(b)}

    valeurs = {c: affecter(l) for c, l in trouves.items()}
    libelles = {c: l.libelle for c, l in trouves.items()}
    for c, autres in supplements.items():
        for l in autres:
            valeurs[c] = additionner(valeurs[c], affecter(l))
            libelles[c] += " + " + l.libelle
    facteur, unite = detecter_facteur(texte_complet, valeurs["PNB"].get("cumul_N"))
    if gab:
        # le gabarit décide ; l'unité déduite de l'ordre de grandeur du PNB n'est qu'un contrôle
        if facteur != FACTEURS_UNITE[gab.unite]:
            alertes.append(f"unité déduite du PNB ({unite}) ≠ gabarit ({gab.unite})")
        facteur, unite = FACTEURS_UNITE[gab.unite], gab.unite
    alertes += controles(valeurs, facteur, t)
    if gab:
        alertes += controle_definition_chg_oper(valeurs, gab.definition_chg_oper)
    note_cp = definition_capitaux_propres(texte_notes)
    mention = mention_retraitement(texte_notes)

    lignes = []
    for c, cols in valeurs.items():
        for col, v in cols.items():
            if v is None:
                continue
            lignes.append({"code_indicateur": c, "libelle_source": libelles[c],
                           "colonne": col, "valeur_source": v, "unite_source": unite,
                           "valeur_mdt": round(v * facteur, 9),   # 9 décimales : le millime
                           "page": trouves[c].page,
                           "note": note_cp if c == "CAP_PROPRES" else "",
                           "gabarit": gab.nom if gab else "",
                           "mention_retraitement": mention})
    manquants = [c for c in ("PROD_EXPL", "CHG_EXPL", "CHG_OPER", "CREDITS", "DEPOTS") if c not in trouves]
    if manquants:
        alertes.append("non trouvés : " + ", ".join(manquants))
    if pages_image and not any(l["code_indicateur"] == "PNB" for l in lignes):
        # tableau en image (BH 2019T4) : le libellé « PNB » vient du commentaire, sans chiffres
        return [], [alerte_image]
    return lignes, alertes


# ---------------------------------------------------------------------------
# Saisies manuelles (saisies_manuelles.csv) : documents dont le tableau est une image
# ---------------------------------------------------------------------------

FICHIER_SAISIES = Path(__file__).resolve().parent / "saisies_manuelles.csv"
ORIGINE_SAISIE = "saisie manuelle"
_SAISIES: dict[tuple[str, str], list[dict]] | None = None


def charger_saisies(chemin: Path = FICHIER_SAISIES) -> dict[tuple[str, str], list[dict]]:
    """Valeurs relevées à la main sur l'image du tableau, au format des lignes extraites.
    Colonnes : banque ; trimestre ; fichier ; page ; code_indicateur ; colonne ; valeur_source ;
    unite_source ; valeur_mdt ; verification ; note. valeur_mdt est recalculée et doit concorder."""
    if not chemin.exists():
        return {}
    sortie: dict[tuple[str, str], list[dict]] = {}
    with chemin.open(encoding="utf-8-sig") as f:
        for i, r in enumerate(csv.DictReader(f, delimiter=";"), start=2):
            if r["code_indicateur"] not in NATURE or r["colonne"] not in COLONNES \
                    or r["unite_source"] not in FACTEURS_UNITE:
                raise ValueError(f"saisies_manuelles.csv ligne {i} : indicateur, colonne ou unité inconnus")
            v = float(r["valeur_source"])
            mdt = round(v * FACTEURS_UNITE[r["unite_source"]], 9)
            if abs(mdt - float(r["valeur_mdt"])) > 1e-6:
                raise ValueError(f"saisies_manuelles.csv ligne {i} : valeur_mdt ≠ valeur_source × unité")
            sortie.setdefault((r["banque"], r["trimestre"]), []).append({
                "code_indicateur": r["code_indicateur"], "libelle_source": "saisie manuelle (lecture de l'image)",
                "colonne": r["colonne"], "valeur_source": v, "unite_source": r["unite_source"],
                "valeur_mdt": mdt, "page": int(r["page"]), "note": r.get("note", ""), "gabarit": "",
                "mention_retraitement": "", "verification": r["verification"], "origine": ORIGINE_SAISIE})
    return sortie


def controle_saisie(valeurs: dict[str, dict[str, float]], codes_saisis: set[str] | None = None) -> list[str]:
    """Contrôles stricts d'un document contenant des valeurs saisies (unité de la source, 2 unités
    d'arrondi) : produits − charges d'exploitation = PNB dans chaque colonne ; si des composantes des
    produits sont saisies (codes_saisis), intérêts + commissions + revenus du portefeuille = produits
    dans chaque colonne (STB 2026T2). Les autres contrôles sont ceux de l'extraction."""
    alertes = []
    for col, pnb in valeurs.get("PNB", {}).items():
        p, ch = valeurs.get("PROD_EXPL", {}).get(col), valeurs.get("CHG_EXPL", {}).get(col)
        if None not in (p, ch) and abs(p - ch - pnb) > 2:
            alertes.append(f"saisie {col} : produits - charges = {p - ch:,.0f} ≠ PNB {pnb:,.0f}")
    composantes = GROUPES["PROD_EXPL"]
    if codes_saisis and codes_saisis & set(composantes):
        for col, total in valeurs.get("PROD_EXPL", {}).items():
            vals = [valeurs.get(c, {}).get(col) for c in composantes]
            if None not in vals and abs(sum(vals) - total) > 2:
                alertes.append(f"saisie {col} : intérêts + commissions + portefeuille = {sum(vals):,.0f} "
                               f"≠ produits {total:,.0f}")
    return alertes


def extraire_document(code: str, tri: str, chemin: Path) -> tuple[list[dict], list[str], str]:
    """Extraction d'un document, complétée par saisies_manuelles.csv :
    - tableau en image : la saisie remplace l'extraction, passe les mêmes contrôles plus le contrôle
      strict ; origine « saisie manuelle » (statut du document) ;
    - document lisible avec quelques valeurs illisibles (STB 2026T2 : revenus du portefeuille
      superposés à leur libellé) : les valeurs saisies remplacent ou complètent celles extraites,
      le document garde son statut, le contrôle strict s'ajoute ; chaque ligne saisie porte
      origine « saisie manuelle » et sa vérification.
    Renvoie (lignes, alertes, origine du document)."""
    global _SAISIES
    t = Trimestre.depuis_texte(tri)
    lignes, alertes = extraire_pdf(chemin, t, code)
    if _SAISIES is None:
        _SAISIES = charger_saisies()
    saisie = _SAISIES.get((code, tri))
    if not saisie:
        return lignes, alertes, ""
    if lignes:
        unites = {l["unite_source"] for l in lignes} | {s["unite_source"] for s in saisie}
        if len(unites) > 1:
            raise ValueError(f"{code} {tri} : unité de la saisie ≠ unité du document ({unites})")
        modele = lignes[0]
        par_cle = {(l["code_indicateur"], l["colonne"]): i for i, l in enumerate(lignes)}
        for s in saisie:
            nouvelle = dict(s, gabarit=modele["gabarit"], mention_retraitement=modele["mention_retraitement"])
            i = par_cle.get((s["code_indicateur"], s["colonne"]))
            if i is None:
                lignes.append(nouvelle)
            else:
                lignes[i] = nouvelle
        valeurs: dict[str, dict[str, float]] = {}
        for l in lignes:
            valeurs.setdefault(l["code_indicateur"], {})[l["colonne"]] = l["valeur_source"]
        return lignes, alertes + controle_saisie(valeurs, {s["code_indicateur"] for s in saisie}), ""
    if not any(a.startswith(PREFIXE_ILLISIBLE) for a in alertes):
        return lignes, alertes, ""
    valeurs: dict[str, dict[str, float]] = {}
    for l in saisie:
        valeurs.setdefault(l["code_indicateur"], {})[l["colonne"]] = l["valeur_source"]
    alertes = controles(valeurs, FACTEURS_UNITE[saisie[0]["unite_source"]], t) + \
        controle_saisie(valeurs, {s["code_indicateur"] for s in saisie})
    gab = gabarit_pour(code, t)
    if gab:
        alertes += controle_definition_chg_oper(valeurs, gab.definition_chg_oper)
    return [dict(l) for l in saisie], alertes, ORIGINE_SAISIE


def cmd_extraire(args):
    manifeste = lire_manifeste()
    if not manifeste:
        sys.exit("Aucun manifeste : lancez d'abord « telecharger ».")
    sortie = DOSSIER / "indicateurs_banques_long.csv"
    controle = DOSSIER / "controle_extraction.csv"
    champs = ["banque", "trimestre", "date_arrete", "annee", "num_trimestre", "code_indicateur",
              "libelle_source", "colonne", "valeur_source", "unite_source", "valeur_mdt",
              "source", "fichier", "page", "note", "gabarit", "mention_retraitement", "verification"]
    # 1) extraction de chaque document
    resultats: dict[tuple[str, str], tuple[list[dict], list[str]]] = {}
    origines: dict[tuple[str, str], str] = {}
    for (code, tri), r in sorted(manifeste.items()):
        if r["statut"] != "ok" or not r["fichier"] or not Path(r["fichier"]).exists():
            continue
        try:
            lignes, alertes, origines[(code, tri)] = extraire_document(code, tri, Path(r["fichier"]))
            resultats[(code, tri)] = (lignes, alertes)
        except Exception as e:  # PDF illisible
            resultats[(code, tri)] = ([], [f"erreur de lecture : {e}"])

    # 2) comparaisons entre documents : même trimestre de l'année précédente,
    #    et trimestre précédent de la même année (trimestre publié vs différence des cumuls)
    docs = {cle: {(l["code_indicateur"], l["colonne"]): l["valeur_mdt"] for l in lignes}
            for cle, (lignes, _) in resultats.items()}
    retraitements = controle_retraitements(docs)
    ecarts_trim = controle_trimestre_cumul(docs)

    # 3) écriture
    n_ok = 0
    with sortie.open("w", newline="", encoding="utf-8-sig") as f, \
         controle.open("w", newline="", encoding="utf-8-sig") as fc:
        w = csv.DictWriter(f, fieldnames=champs, delimiter=";")
        wc = csv.writer(fc, delimiter=";")
        wc.writerow(["banque", "trimestre", "statut", "nb_valeurs", "alertes", "fichier", "gabarit"])
        w.writeheader()
        for (code, tri), r in sorted(manifeste.items()):
            if (code, tri) not in resultats:
                wc.writerow([code, tri, "pdf manquant", 0, "", ""])
                continue
            t = Trimestre.depuis_texte(tri)
            lignes, alertes = resultats[(code, tri)]
            retr = retraitements.get((code, tri), [])
            ecarts = ecarts_trim.get((code, tri), [])
            statut = statut_document(lignes, alertes, ecarts, retr, origines.get((code, tri), ""))
            n_ok += statut == "ok"
            alertes = alertes + ecarts + retr
            g = gabarit_pour(code, t)
            for l in lignes:
                l.update({"banque": code, "trimestre": tri, "date_arrete": t.fin.isoformat(),
                          "annee": t.annee, "num_trimestre": t.num,
                          "source": l.pop("origine", "") or origines.get((code, tri)) or r["source"],
                          "fichier": Path(r["fichier"]).name,
                          "verification": l.get("verification", "")})
                w.writerow(l)
            print(f"  {statut:<11} {code} {tri}  ({len(lignes)} valeurs) {'; '.join(alertes)}")

    # 4) versions initiale / révisée de chaque période, et valeur retenue pour l'analyse
    docs_fichiers = {cle: (lignes, Path(manifeste[cle]["fichier"]).name) for cle, (lignes, _) in resultats.items()}
    illisibles = {cle: Path(manifeste[cle]["fichier"]).name for cle, (lignes, alertes) in resultats.items()
                  if not lignes and any(a.startswith(PREFIXE_ILLISIBLE) for a in alertes)}
    versions = table_versions(docs_fichiers, illisibles)
    fichier_versions = DOSSIER / "indicateurs_versions.csv"
    champs_v = ["banque", "trimestre", "date_arrete", "annee", "num_trimestre", "code_indicateur",
                "mesure", "version", "valeur_mdt", "fichier", "page", "valeur_retenue", "source_valeur",
                "ecart_vs_retenue", "statut_revision", "note_definition", "mention_retraitement",
                "rupture_serie", "detail_rupture"]
    with fichier_versions.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=champs_v, delimiter=";")
        w.writeheader()
        w.writerows(versions)

    # 5) somme des 4 trimestres retenus = cumul T4 retenu ; comparaison des deux révisions du 31/12
    sommes = controle_somme_annuelle(versions)
    fichier_sommes = DOSSIER / "controle_annuel.csv"
    with fichier_sommes.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["banque", "annee", "code_indicateur", "somme_trimestres",
                                          "cumul_T4", "source_cumul", "ecart", "statut"], delimiter=";")
        w.writeheader()
        w.writerows(sommes)
    compte = {s: sum(r["statut"] == s for r in sommes) for s in ("ok", "en attente de révision", "ecart")}
    print(f"\nSomme des 4 trimestres retenus = cumul T4 : {compte}")
    for r in sommes:
        if r["statut"] == "ecart":
            print(f"  ecart : {r['banque']} {r['annee']} {r['code_indicateur']} somme {r['somme_trimestres']:,.3f} "
                  f"≠ cumul T4 {r['cumul_T4']:,.3f} ({r['source_cumul']}, écart {r['ecart']:+,.3f} MDT)")
    revisions_31_12 = comparaison_revisions_31_12(versions)
    print(f"Révision provisoire 31/12 vs T4 suivant : {len(revisions_31_12)} écart(s)")
    for a in revisions_31_12:
        print("  " + a)

    # 6) variations sur un an à l'intérieur de chaque document (colonne N contre colonne N-1)
    variations = variations_comparables(docs_fichiers)
    fichier_variations = DOSSIER / "variations_comparables.csv"
    with fichier_variations.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(variations[0]) if variations else ["banque"], delimiter=";")
        w.writeheader()
        w.writerows(variations)
    n_imp = len({(r["banque"], r["trimestre"], r["code_indicateur"]) for r in versions
                 if r["version"] == "initiale" and r["statut_revision"] == "revision_importante"})
    print(f"Révisions importantes (> 2 % sur le cumul) : {n_imp} banque × période × indicateur")

    ecrire_dimensions()
    print(f"\n{n_ok} documents extraits sans alerte.")
    print(f"Données : {sortie}\nVersions : {fichier_versions}\nContrôle : {controle}\n"
          f"Contrôle annuel : {fichier_sommes}\nVariations comparables : {fichier_variations}")


def ecrire_dimensions():
    with (DOSSIER / "dim_indicateur.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["code_indicateur", "libelle", "categorie", "nature", "ordre"])
        for i, (c, lib, cat, nat) in enumerate(INDICATEURS, start=1):
            w.writerow([c, lib, cat, nat, i])
    p = DOSSIER / "dim_banque.csv"
    if not p.exists():   # ne pas écraser les colonnes remplies à la main
        with p.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["code_banque", "nom", "ticker_bvmt", "actionnariat", "groupe"])
            for c, conf in BANQUES.items():
                w.writerow([c, conf["nom"], conf["ticker"], "", ""])


# ---------------------------------------------------------------------------

def choisir_banques(txt: str | None) -> list[str]:
    if not txt:
        return list(BANQUES)
    codes = [c.strip().upper() for c in txt.split(",") if c.strip()]
    inconnus = [c for c in codes if c not in BANQUES]
    if inconnus:
        sys.exit(f"Banques inconnues : {inconnus}. Codes possibles : {', '.join(BANQUES)}")
    return codes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sous = ap.add_subparsers(dest="cmd", required=True)

    def options_periode(p):
        p.add_argument("--debut", type=Trimestre.depuis_texte, default=Trimestre(2019, 4))
        p.add_argument("--fin", type=Trimestre.depuis_texte, default=dernier_trimestre_publiable())
        p.add_argument("--banques", help="codes séparés par des virgules (défaut : toutes)")

    def options_recherche(p):
        p.add_argument("--sans-sites", action="store_true",
                       help="ne pas essayer les URL des sites (seulement liste du CMF et bulletins)")
        p.add_argument("--sans-liste-cmf", action="store_true",
                       help="ne pas chercher dans la liste des indicateurs du CMF")
        p.add_argument("--rafraichir-liste-cmf", action="store_true",
                       help="relire la liste du CMF sur le site (sinon : donnees/liste_indicateurs_cmf.csv)")
        p.add_argument("--pages-liste-cmf", type=int, default=150,
                       help="nombre maximal de pages de la liste du CMF à lire (défaut : 150)")
        p.add_argument("--sans-bulletins", action="store_true", help="ne pas fouiller les Bulletins Officiels")
        p.add_argument("--garder-bulletins", action="store_true", help="garder les bulletins complets en cache")

    p = sous.add_parser("telecharger", help="télécharge les PDF")
    options_periode(p)
    options_recherche(p)
    p.set_defaults(f=cmd_telecharger)

    p = sous.add_parser("extraire", help="extrait les tableaux en CSV")
    p.set_defaults(f=cmd_extraire)

    p = sous.add_parser("tout", help="télécharge puis extrait")
    options_periode(p)
    options_recherche(p)
    p.set_defaults(f=lambda a: (cmd_telecharger(a), cmd_extraire(a)))

    p = sous.add_parser("urls", help="affiche les URL qui seront testées")
    options_periode(p)
    p.set_defaults(f=cmd_urls)

    args = ap.parse_args()
    args.f(args)


if __name__ == "__main__":
    main()
