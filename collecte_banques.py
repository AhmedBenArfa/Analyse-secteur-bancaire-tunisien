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
              "slugs": ["wifak", "wib", "wifak-bank", "el-wifak", "wifak-international-bank"],
              "motif_bo": r"WIFAK\s+INTERNATIONAL\s+BANK|EL\s+WIFAK"},
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
        return [f"indic_{n}trim{yy}_{s2}.pdf", f"ind_{n}trim{yy}_{s2}.pdf",
                f"indic_{n}trim{f.year}_{s2}.pdf", f"ind_{n}eme_trim_{s2}.pdf",
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
        combo_connu: Combo | None = None  # une fois trouvé, on n'essaie plus que ce couple
        # du plus récent au plus ancien : les documents récents existent presque toujours,
        # ce qui permet d'apprendre vite le bon nom de la banque dans les URL
        for t in reversed(liste_t):
            cle = (code, str(t))
            if manifeste.get(cle, {}).get("statut") == "ok" and Path(manifeste[cle]["fichier"]).exists():
                continue
            cands = urls_candidates(code, t, [combo_connu] if combo_connu else combinaisons(code))
            # on teste d'abord les gabarits qui ont déjà fonctionné
            cands.sort(key=lambda c: 0 if any(g in c[0] for g in ordre_prefere) else 1)
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
                    combo_connu = combo_connu or combo
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


def urls_bulletin(d: dt.date) -> list[str]:
    base = "https://www.cmf.tn/sites/default/files/pdfs/publications/bulletin-officiel/"
    return [base + f"bo{d:%y%m%d}.pdf", base + f"bo{d:%d%m%Y}.pdf"]


def debut_avis(txt: str) -> bool:
    """Page qui commence l'avis d'indicateurs trimestriels d'une société."""
    haut = sans_accents(txt[:1500]).upper()
    return "INDICATEURS D" in haut and "PUBLIE" in haut


def telecharger_bulletins(client: Client, manifeste: dict, garder: bool, jours: int = 45):
    """Pour chaque trimestre où il manque des banques, parcourt les Bulletins Officiels publiés
    dans les `jours` suivant la fin du trimestre et extrait les pages de chaque banque manquante."""
    from pypdf import PdfReader, PdfWriter

    manquants: dict[str, set[str]] = {}
    for (code, tri), r in manifeste.items():
        if r["statut"] != "ok":
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
                            if not bon_document(textes[i:fin_bloc], t):
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
    telecharger_sites(client, codes, liste_t, manifeste)
    if not args.sans_bulletins:
        telecharger_bulletins(client, manifeste, garder=args.garder_bulletins)
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
    ("CAP_PROPRES",   "Capitaux propres",                        "Bilan",    "stock"),
]
NATURE = {c: n for c, _, _, n in INDICATEURS}

# Règles de reconnaissance des libellés (ordre important : du plus spécifique au plus général)
REGLES = [
    ("REV_PORTEF",   r"revenus? (du |des )?portefeuille"),
    ("PROD_EXPL",    r"produits d'?\s?exploitation bancaires?"),
    ("CHG_EXPL",     r"charges d'?\s?exploitation bancaires?"),
    ("PNB",          r"produit net bancaire"),
    ("AUTRES_PROD",  r"autres produits d'?\s?exploitation"),
    ("CHG_OPER",     r"charges operatoires"),
    ("FRAIS_PERS",   r"frais (de |du )?personnel"),
    ("CHG_GEN",      r"charges generales"),
    ("DOT_AMORT",    r"dotations? aux amortissements"),
    ("INT_ENCOURUS", r"interets? (et charges assimilees )?encourus|interets? (et charges )?payes"),
    ("COMM_CHG",     r"commissions? encourues|commissions? (en )?charges?"),
    ("COMM_PROD",    r"commissions? (en )?produits?|commissions? percues"),
    ("PORTEF",       r"structure du portefeuille"),
    ("PORTEF_COMM",  r"portefeuille ?(titres?)? ?commercial"),
    ("PORTEF_INV",   r"portefeuille ?(titres?)? ?d'?\s?investissement"),
    ("CREDITS",      r"encours (net )?des credits|credits (a|nets? a) la clientele|encours des engagements"),
    ("DEP_VUE",      r"depots? a vue"),
    ("DEP_EPARGNE",  r"depots? d'?\s?epargne|comptes d'?\s?epargne"),
    ("DEP_TERME",    r"depots? a terme"),
    ("DEP_AUTRES",   r"autres depots"),
    ("DEPOTS",       r"encours (des |de )?depots|depots (de la )?clientele"),
    ("EMPRUNTS",     r"emprunts? et ressources speciales"),
    ("CAP_PROPRES",  r"capitaux propres"),
    ("INT_PERCUS",   r"^interets?( et revenus assimiles)?( percus)?$|^interets? et revenus"),
]
REGLES_C = [(c, re.compile(m)) for c, m in REGLES]
COLONNES = ["trim_N", "trim_N1", "cumul_N", "cumul_N1", "exercice_N1"]

RE_NOMBRE = re.compile(r"^\(?-?\d[\d.,]*\)?$")
RE_TIRET = re.compile(r"^[-–—]+$")
RE_POURCENT = re.compile(r"%$")


def code_libelle(lib: str) -> str | None:
    n = normaliser(lib)
    n = re.sub(r"^(\d+\s*)+", "", n).strip()       # numérotation "1", "3-"
    if not n:
        return None
    for code, rx in REGLES_C:
        if rx.search(n):
            return code
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
    texte: str
    x0: float
    x1: float

    @property
    def centre(self):
        return (self.x0 + self.x1) / 2


@dataclass
class Ligne:
    libelle: str
    nombres: list[Jeton] = field(default_factory=list)   # valeurs (None pour un tiret)
    page: int = 0


def lignes_page(page, num_page: int) -> list[Ligne]:
    mots = page.extract_words(x_tolerance=1.2, y_tolerance=2.5, keep_blank_chars=False)
    mots.sort(key=lambda m: (round(m["top"]), m["x0"]))
    groupes: list[list[dict]] = []
    for m in mots:
        if groupes and abs(groupes[-1][0]["top"] - m["top"]) <= 3:
            groupes[-1].append(m)
        else:
            groupes.append([m])

    sortie = []
    for g in groupes:
        g.sort(key=lambda m: m["x0"])
        libelle, nombres = [], []
        for m in g:
            t = m["text"]
            if RE_POURCENT.search(t):
                continue                       # colonne de variation : ignorée
            if re.fullmatch(r"\(\d\)|\(\*+\)|\*+", t):
                continue                       # renvoi de note : (1), (*)
            if RE_TIRET.match(t) and libelle:
                nombres.append(Jeton("-", m["x0"], m["x1"]))
                continue
            if RE_NOMBRE.match(t) and (libelle or nombres):
                prec = nombres[-1] if nombres else None
                # regroupe les milliers : "6" "479" "908" -> "6 479 908"
                if (prec and prec.texte != "-" and re.fullmatch(r"\d{3}\)?", t)
                        and m["x0"] - prec.x1 < 5.5):
                    prec.texte += " " + t
                    prec.x1 = m["x1"]
                else:
                    nombres.append(Jeton(t, m["x0"], m["x1"]))
                continue
            if nombres:                         # du texte après des nombres : on l'ignore (renvois)
                continue
            libelle.append(t)
        sortie.append(Ligne(" ".join(libelle), nombres, num_page))
    return sortie


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


def extraire_pdf(chemin: Path, t: Trimestre | None = None) -> tuple[list[dict], list[str]]:
    """Renvoie (lignes extraites, alertes) pour un PDF."""
    import pdfplumber

    alertes: list[str] = []
    toutes: list[Ligne] = []
    texte_complet = ""
    with pdfplumber.open(chemin) as pdf:
        for i, page in enumerate(pdf.pages[:4], start=1):
            texte_complet += (page.extract_text() or "") + "\n"
            toutes += lignes_page(page, i)

    # libellés sur deux lignes : on recolle un libellé sans nombre à la ligne suivante
    fusion: list[Ligne] = []
    attente = ""
    for l in toutes:
        if l.libelle and not l.nombres:
            attente = (attente + " " + l.libelle).strip() if code_libelle(l.libelle) is None else l.libelle
            continue
        if l.nombres:
            lib = l.libelle
            if attente and (not lib or code_libelle(lib) is None):
                lib = (attente + " " + lib).strip()
            fusion.append(Ligne(lib, l.nombres, l.page))
        attente = ""

    # reconnaissance des indicateurs, en suivant la section parente (produits / charges)
    trouves: dict[str, Ligne] = {}
    parent = None
    for l in fusion:
        c = code_libelle(l.libelle)
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
        if c == "CAP_PROPRES":
            break

    if "PNB" not in trouves:
        return [], ["PNB introuvable : tableau non reconnu (PDF scanné ou mise en page inhabituelle ?)"]

    # centres des colonnes : la ligne de flux qui a le plus de valeurs sert de référence
    ref = max((trouves[c] for c in trouves if NATURE[c] == "flux" and trouves[c].page == trouves["PNB"].page),
              key=lambda l: len(l.nombres))
    centres = [j.centre for j in ref.nombres][:5]
    if len(centres) < 4:
        alertes.append(f"seulement {len(centres)} colonnes détectées sur la ligne de référence")

    def affecter(l: Ligne) -> dict[str, float | None]:
        res: dict[str, float | None] = {}
        if l.page == ref.page and len(centres) >= 3:
            for j in l.nombres:
                k = min(range(len(centres)), key=lambda i: abs(centres[i] - j.centre))
                if COLONNES[k] not in res:
                    res[COLONNES[k]] = None if j.texte == "-" else valeur(j.texte)
        else:  # autre page : affectation par position
            vals = [None if j.texte == "-" else valeur(j.texte) for j in l.nombres]
            noms = COLONNES if len(vals) >= 4 else ["cumul_N", "cumul_N1", "exercice_N1"]
            res = dict(zip(noms, vals))
        return res

    valeurs = {c: affecter(l) for c, l in trouves.items()}
    facteur, unite = detecter_facteur(texte_complet, valeurs["PNB"].get("cumul_N"))

    # contrôles de cohérence
    def get(c, col):
        return valeurs.get(c, {}).get(col)
    for col in ("cumul_N", "trim_N"):
        p, ch, pnb = get("PROD_EXPL", col), get("CHG_EXPL", col), get("PNB", col)
        if None not in (p, ch, pnb) and pnb:
            ecart = abs((p - ch) - pnb) / abs(pnb)
            if ecart > 0.02:
                alertes.append(f"{col} : produits - charges ≠ PNB (écart {ecart:.1%})")
    if get("PNB", "cumul_N") is None:
        alertes.append("PNB cumulé absent")
    trim, cumul = get("PNB", "trim_N"), get("PNB", "cumul_N")
    if t and None not in (trim, cumul):
        if t.num == 1 and abs(trim - cumul) > 0.01 * abs(cumul):
            alertes.append("T1 : trimestre ≠ cumul, ordre des colonnes à vérifier")
        if t.num > 1 and trim > cumul:
            alertes.append("trimestre > cumul, ordre des colonnes à vérifier")

    lignes = []
    for c, cols in valeurs.items():
        for col, v in cols.items():
            if v is None:
                continue
            lignes.append({"code_indicateur": c, "libelle_source": trouves[c].libelle,
                           "colonne": col, "valeur_source": v, "unite_source": unite,
                           "valeur_mdt": round(v * facteur, 6), "page": trouves[c].page})
    manquants = [c for c in ("PROD_EXPL", "CHG_EXPL", "CHG_OPER", "CREDITS", "DEPOTS") if c not in trouves]
    if manquants:
        alertes.append("non trouvés : " + ", ".join(manquants))
    return lignes, alertes


def cmd_extraire(args):
    manifeste = lire_manifeste()
    if not manifeste:
        sys.exit("Aucun manifeste : lancez d'abord « telecharger ».")
    sortie = DOSSIER / "indicateurs_banques_long.csv"
    controle = DOSSIER / "controle_extraction.csv"
    champs = ["banque", "trimestre", "date_arrete", "annee", "num_trimestre", "code_indicateur",
              "libelle_source", "colonne", "valeur_source", "unite_source", "valeur_mdt",
              "source", "fichier", "page"]
    n_ok = 0
    with sortie.open("w", newline="", encoding="utf-8-sig") as f, \
         controle.open("w", newline="", encoding="utf-8-sig") as fc:
        w = csv.DictWriter(f, fieldnames=champs, delimiter=";")
        wc = csv.writer(fc, delimiter=";")
        wc.writerow(["banque", "trimestre", "statut", "nb_valeurs", "alertes", "fichier"])
        w.writeheader()
        for (code, tri), r in sorted(manifeste.items()):
            if r["statut"] != "ok" or not r["fichier"] or not Path(r["fichier"]).exists():
                wc.writerow([code, tri, "pdf manquant", 0, "", ""])
                continue
            t = Trimestre.depuis_texte(tri)
            try:
                lignes, alertes = extraire_pdf(Path(r["fichier"]), t)
            except Exception as e:  # PDF illisible
                lignes, alertes = [], [f"erreur de lecture : {e}"]
            statut = "ok" if lignes and not alertes else ("a verifier" if lignes else "echec")
            n_ok += statut == "ok"
            wc.writerow([code, tri, statut, len(lignes), " | ".join(alertes), r["fichier"]])
            for l in lignes:
                l.update({"banque": code, "trimestre": tri, "date_arrete": t.fin.isoformat(),
                          "annee": t.annee, "num_trimestre": t.num,
                          "source": r["source"], "fichier": Path(r["fichier"]).name})
                w.writerow(l)
            print(f"  {statut:<11} {code} {tri}  ({len(lignes)} valeurs) {'; '.join(alertes)}")

    ecrire_dimensions()
    print(f"\n{n_ok} documents extraits sans alerte.")
    print(f"Données : {sortie}\nContrôle : {controle}")


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

    p = sous.add_parser("telecharger", help="télécharge les PDF")
    options_periode(p)
    p.add_argument("--sans-bulletins", action="store_true", help="ne pas fouiller les Bulletins Officiels")
    p.add_argument("--garder-bulletins", action="store_true", help="garder les bulletins complets en cache")
    p.set_defaults(f=cmd_telecharger)

    p = sous.add_parser("extraire", help="extrait les tableaux en CSV")
    p.set_defaults(f=cmd_extraire)

    p = sous.add_parser("tout", help="télécharge puis extrait")
    options_periode(p)
    p.add_argument("--sans-bulletins", action="store_true")
    p.add_argument("--garder-bulletins", action="store_true")
    p.set_defaults(f=lambda a: (cmd_telecharger(a), cmd_extraire(a)))

    p = sous.add_parser("urls", help="affiche les URL qui seront testées")
    options_periode(p)
    p.set_defaults(f=cmd_urls)

    args = ap.parse_args()
    args.f(args)


if __name__ == "__main__":
    main()
