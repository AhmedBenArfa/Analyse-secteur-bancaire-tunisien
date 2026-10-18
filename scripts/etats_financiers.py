#!/usr/bin/env python3
"""
Collecte des données nécessaires au ROE et au ROA des banques cotées :
résultat net, total de l'actif et total des capitaux propres, tirés des
états financiers INDIVIDUELS publiés sur le site de la BVMT.

  - annuels au 31/12 (2019 -> dernier exercice publié)
  - intermédiaires (semestriels) au 30/06 (2020 -> dernier semestre publié)

Utilisation (depuis le dossier du projet) :
  python scripts/etats_financiers.py tout
  python scripts/etats_financiers.py telecharger --banques BIAT,UIB
  python scripts/etats_financiers.py telecharger --bulletins     # + recherche dans les Bulletins Officiels du CMF
  python scripts/etats_financiers.py extraire
  python scripts/etats_financiers.py verifier                    # compare à ilboursa (informatif)
  python scripts/etats_financiers.py urls --banques TJARI        # URL testées

Les fonctions communes (banques, téléchargement, lecture des tableaux) viennent de collecte_banques.py.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import io
import re
import sys
from dataclasses import dataclass
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
import collecte_banques as cb  # noqa: E402

DOSSIER = cb.DOSSIER
DOSSIER_PDF = DOSSIER / "pdf_etats_financiers"
MANIFESTE = DOSSIER / "manifeste_etats_financiers.csv"
SORTIE = DOSSIER / "etats_financiers_long.csv"
CONTROLE = DOSSIER / "controle_etats_financiers.csv"

SUFFIXES = {
    "annuel": ["annuels-individuels", "annuels", "individuels-annuels", "definitifs-individuels", "definitifs"],
    "semestriel": ["semestriels-individuels", "semestriels", "intermediaires-individuels", "intermediaires",
                   "individuels-semestriels"],
}

CODES = [
    ("RES_NET",        "Résultat net de la période (état de résultat, avant modifications comptables)"),
    ("TOTAL_ACTIF",    "Total de l'actif"),
    ("CAP_PROPRES_EF", "Total des capitaux propres (résultat inclus)"),
    ("TOTAL_PASSIF_CP", "Total passif et capitaux propres (contrôle)"),
]
# Lus quand ils existent, pour information et contrôle (jamais obligatoires) :
CODES_INFO = [
    ("MODIF_COMPTABLES",    "Effet des modifications comptables (net d'impôt)"),
    ("RES_NET_APRES_MODIF", "Résultat net après modifications comptables"),
    ("RES_BILAN",           "Résultat de la période inscrit dans les capitaux propres du bilan (contrôle)"),
]

_PERIODE = r"( de l'exercice| de la periode| du semestre| de l'exercice net)?"
REGLES = [
    ("TOTAL_PASSIF_CP", r"^total (des )?capitaux propres et (du )?passifs?$|^total (du )?passifs? et (des )?capitaux propres$"),
    ("CAP_PROPRES_EF",  r"^total (des )?capitaux propres$"),
    ("TOTAL_ACTIF",     r"^total (de l'|des )?actifs?$|^total bilan actif$"),
    # « Résultat net de la période (avant modification comptable) » (BNA S1 2024) = résultat net
    ("RES_NET",         rf"^resultat net{_PERIODE}( avant (les )?modifications? comptables?)?$"),
    ("RES_NET_APRES_MODIF", rf"^resultat( net)?{_PERIODE} apres (les )?modifications? comptables?$"
                            r"|^resultat net des modifications comptables$"),   # AB : « net des » = après
    ("MODIF_COMPTABLES", r"^effets? (net )?des modifications comptables"),
    # repli : certaines banques écrivent seulement « Résultat de l'exercice » (aussi la ligne du bilan)
    ("RES_EXERCICE",    r"^resultat (de l'exercice|de la periode|du semestre)$"),
]
REGLES_C = [(c, re.compile(r)) for c, r in REGLES]
# mêmes règles sans espaces, pour les libellés aux lettres espacées (AB 2023 :
# « Résultat de l'exer cice », « Effets des modificat ions comp tables »)
REGLES_COMPACTES = [(c, re.compile(r.replace(" ", ""))) for c, r in REGLES]
# lignes lues seulement sur la page de l'état de résultat
CODES_RESULTAT = {"RES_NET", "RES_NET_APRES_MODIF", "MODIF_COMPTABLES", "RES_EXERCICE"}


@dataclass(frozen=True)
class Arrete:
    annee: int
    type: str  # "annuel" ou "semestriel"

    @property
    def date(self) -> dt.date:
        return dt.date(self.annee, 12, 31) if self.type == "annuel" else dt.date(self.annee, 6, 30)

    @property
    def trimestre(self) -> cb.Trimestre:   # pour réutiliser la vérification de date
        return cb.Trimestre(self.annee, 4 if self.type == "annuel" else 2)

    @property
    def cle(self) -> str:
        return f"{self.annee}-{'12' if self.type == 'annuel' else '06'}"

    def __str__(self):
        return f"{self.type} {self.date:%d/%m/%Y}"


PREMIER_SEMESTRIEL = 2020   # le périmètre commence au T4 2019 : premier 30/06 utile = 2020


def arretes(debut: int, fin: int, aujourdhui: dt.date | None = None) -> list[Arrete]:
    """Exercices `debut` à `fin` : annuels 31/12 et semestriels 30/06 (à partir de 2020),
    s'ils doivent déjà être publiés."""
    d = aujourdhui or dt.date.today()
    sortie = []
    for a in range(debut, fin + 1):
        if a >= PREMIER_SEMESTRIEL and dt.date(a, 6, 30) + dt.timedelta(days=65) <= d:
            sortie.append(Arrete(a, "semestriel"))
        if dt.date(a, 12, 31) + dt.timedelta(days=120) <= d:
            sortie.append(Arrete(a, "annuel"))
    return sortie


# ---------------------------------------------------------------------------
# Téléchargement
# ---------------------------------------------------------------------------

def urls_candidates(ar: Arrete, combos: list[cb.Combo]) -> list[tuple[str, cb.Combo]]:
    f = ar.date
    date_tiret = f"{f.day:02d}-{f.month:02d}-{f.year}"
    out = []
    for suffixe in SUFFIXES[ar.type]:
        for d, p in combos:
            out.append((f"https://www.bvmt.com.tn/sites/default/files/societes/{d}/etats-financiers/"
                        f"{p}-etats-financiers-{suffixe}-{date_tiret}.pdf", (d, p)))
    return out


def est_consolide(textes: list[str]) -> bool:
    debut = cb.normaliser(" ".join(t[:700] for t in textes[:2]))
    return "consolide" in debut and "individuel" not in debut


def lire_manifeste() -> dict[tuple[str, str], dict]:
    if not MANIFESTE.exists():
        return {}
    with MANIFESTE.open(encoding="utf-8") as f:
        return {(r["banque"], r["arrete"]): r for r in csv.DictReader(f)}


def ecrire_manifeste(m: dict):
    champs = ["banque", "arrete", "type", "date_arrete", "statut", "source", "url", "fichier", "pages"]
    MANIFESTE.parent.mkdir(parents=True, exist_ok=True)
    with MANIFESTE.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=champs)
        w.writeheader()
        for k in sorted(m):
            w.writerow({c: m[k].get(c, "") for c in champs})


def chemin(code: str, ar: Arrete, suffixe: str = "") -> Path:
    return DOSSIER_PDF / code / f"{code}_EF_{ar.cle}{suffixe}.pdf"


def ligne_manifeste(code, ar, statut, source="", url="", fichier="", pages=""):
    return {"banque": code, "arrete": ar.cle, "type": ar.type, "date_arrete": ar.date.isoformat(),
            "statut": statut, "source": source, "url": url, "fichier": fichier, "pages": pages}


def telecharger_sites(client: cb.Client, codes: list[str], liste: list[Arrete], m: dict):
    for code in codes:
        combos_connus: list[cb.Combo] = []   # essayés en premier, sans exclure les autres
        suffixes_ok: list[str] = []
        for ar in sorted(liste, key=lambda a: a.date, reverse=True):
            cle = (code, ar.cle)
            if m.get(cle, {}).get("statut") == "ok" and Path(m[cle]["fichier"]).exists():
                continue
            combos = combos_connus + [c for c in cb.combinaisons(code) if c not in combos_connus]
            cands = urls_candidates(ar, combos)
            cands.sort(key=lambda c: (0 if any(s in c[0] for s in suffixes_ok) else 1,
                                      0 if c[1] in combos_connus else 1))
            trouve = None
            for url, combo in cands:
                contenu = client.pdf(url)
                if not contenu:
                    continue
                try:
                    textes = cb.texte_pdf(contenu, max_pages=3)
                except Exception:
                    continue
                if est_consolide(textes):
                    print(f"    ignoré (comptes consolidés) : {url}")
                    continue
                if not cb.mentionne_trimestre(textes, ar.trimestre):
                    print(f"    ignoré (autre date) : {url}")
                    continue
                trouve = (url, contenu)
                if combo not in combos_connus:
                    combos_connus.append(combo)
                suffixe = url.split("-etats-financiers-", 1)[1].rsplit("-", 3)[0]
                if suffixe not in suffixes_ok:
                    suffixes_ok.insert(0, suffixe)
                break
            if trouve:
                url, contenu = trouve
                p = chemin(code, ar)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(contenu)
                m[cle] = ligne_manifeste(code, ar, "ok", "site", url, str(p))
                print(f"  OK  {code} {ar}  <- {url}")
            else:
                m[cle] = ligne_manifeste(code, ar, "manquant")
                print(f"  --  {code} {ar}  non trouvé sur le site de la BVMT")
            ecrire_manifeste(m)


def telecharger_bulletins(client: cb.Client, m: dict):
    """Recherche des états financiers manquants dans les Bulletins Officiels du CMF.
    Fenêtres : 15/07 -> 30/09 pour le 30/06 ; 15/02 -> 31/05 de l'année suivante pour le 31/12."""
    from pypdf import PdfReader, PdfWriter

    manquants: dict[str, set[str]] = {}
    for (code, cle), r in m.items():
        if r["statut"] != "ok":
            manquants.setdefault(cle, set()).add(code)
    for cle in sorted(manquants):
        a, mois = int(cle[:4]), cle[5:]
        ar = Arrete(a, "annuel" if mois == "12" else "semestriel")
        restants = set(manquants[cle])
        debut, fin = ((dt.date(a, 7, 15), dt.date(a, 9, 30)) if ar.type == "semestriel"
                      else (dt.date(a + 1, 2, 15), dt.date(a + 1, 5, 31)))
        print(f"\nBulletins officiels pour {ar} : {', '.join(sorted(restants))}")
        jour = debut
        while restants and jour <= fin:
            if jour.weekday() < 5:
                contenu, url_bo = None, ""
                for url_bo in cb.urls_bulletin(jour):
                    contenu = client.pdf(url_bo)
                    if contenu:
                        break
                if contenu:
                    try:
                        lecteur = PdfReader(io.BytesIO(contenu))
                        textes = [(p.extract_text() or "") for p in lecteur.pages]
                    except Exception:
                        textes = []
                    for code in sorted(restants):
                        motif = re.compile(cb.BANQUES[code]["motif_bo"])
                        for i, txt in enumerate(textes):
                            if i == 0:
                                continue
                            haut = cb.sans_accents(txt[:1500]).upper()
                            if not ("ETATS FINANCIERS" in haut and motif.search(haut)) or "CONSOLID" in haut:
                                continue
                            bloc = textes[i:i + 8]
                            if not cb.mentionne_trimestre(bloc[:2], ar.trimestre):
                                continue
                            w = PdfWriter()
                            for k in range(i, min(i + 8, len(textes))):
                                w.add_page(lecteur.pages[k])
                            p = chemin(code, ar, "_bulletin")
                            p.parent.mkdir(parents=True, exist_ok=True)
                            with p.open("wb") as f:
                                w.write(f)
                            m[(code, cle)] = ligne_manifeste(code, ar, "ok", "bulletin_officiel", url_bo, str(p),
                                                             f"{i + 1}-{min(i + 8, len(textes))}")
                            print(f"  OK  {code} {ar}  <- bulletin du {jour:%d/%m/%Y}, page {i + 1}")
                            restants.discard(code)
                            ecrire_manifeste(m)
                            break
            jour += dt.timedelta(days=1)
        for code in restants:
            print(f"  --  {code} {ar}  introuvable (à chercher à la main)")


def cmd_telecharger(args):
    codes = cb.choisir_banques(args.banques)
    liste = arretes(args.debut, args.fin)
    m = lire_manifeste()
    client = cb.Client()
    print(f"{len(codes)} banques × {len(liste)} arrêtés ({liste[0]} -> {liste[-1]})")
    telecharger_sites(client, codes, liste, m)
    if args.bulletins:
        telecharger_bulletins(client, m)
    ok = sum(1 for r in m.values() if r["statut"] == "ok")
    print(f"\nTerminé : {ok}/{len(m)} documents, {client.nb} requêtes. Détail : {MANIFESTE}")


def cmd_urls(args):
    for code in cb.choisir_banques(args.banques):
        for ar in arretes(args.debut, args.fin):
            print(f"# {code} {ar}")
            for u, _ in urls_candidates(ar, cb.combinaisons(code)):
                print(u)


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

RE_NOTE = re.compile(r"^\(?\d{1,2}([.,]\d{1,2}){1,2}\)?$")


def code_ligne(libelle: str) -> str | None:
    n = cb.normaliser(libelle)
    n = re.sub(r"^((pr|ch|ac|pa|cp)\s?\d+\s*|\d+\s*)+", "", n).strip()
    # renvoi de note en chiffres romains en fin de libellé (BIAT : « Total des capitaux propres V »,
    # « Total des produits d'exploitation bancaire VII-1 »)
    n = re.sub(r"(\s+[ivx]{1,5}(\s\d{1,2})*)+$", "", n).strip()
    # « Résultat avant impôt »… : jamais le résultat net ; « avant modification comptable » : oui
    if re.search(r"\bavant\b(?! (les )?modifications? comptables?)", n):
        return None
    for code, rx in REGLES_C:
        if rx.search(n):
            return code
    compact = n.replace(" ", "")
    for code, rx in REGLES_COMPACTES:
        if rx.search(compact):
            return code
    return None


def valeurs_ligne(jetons: list[cb.Jeton]) -> list[float]:
    """Valeurs d'une ligne, sans les renvois de notes (4.1, 5-2, 12...). Un tiret isolé (« néant »)
    vaut 0 et garde sa place : sinon les colonnes suivantes se décalent (BNA 2024, « Effet des
    modifications comptables » : (40 975) - (40 975), la variation devenait la colonne N-1)."""
    textes = [j.texte for j in jetons]
    gros = [t for t in textes if len(re.sub(r"\D", "", t)) >= 4]
    garde = []
    for t in textes:
        if t == "-":
            garde.append(0.0)
            continue
        if RE_NOTE.match(t):
            continue
        if re.fullmatch(r"\d{1,2}", t) and len(gros) >= 2:
            continue
        v = cb.valeur(t)
        if v is not None:
            garde.append(v)
    return garde


def facteur_mdt(total_actif: float | None) -> tuple[float, str]:
    if total_actif is None:
        return 1e-3, "milliers de dinars (supposé)"
    v = abs(total_actif)
    if v >= 1e8:
        return 1e-6, "dinars"
    if v >= 1e5:
        return 1e-3, "milliers de dinars"
    return 1.0, "millions de dinars"


RE_TITRE_RESULTAT = re.compile(r"^etat (de|des) resultats?\b")
# titre d'un autre état ou des notes : fin de l'état de résultat (« Notes » seul, en-tête de
# colonne, n'en est pas un)
RE_AUTRE_ETAT = re.compile(r"^(etats? (de|des) (flux|engagements)|tableau (de|des) (flux|variation)|bilan$"
                           r"|(\d+\s*)?notes (aux|relatives|explicatives|sur)\b)")


def page_etat_resultat(lignes) -> bool:
    """Page qui contient le titre « État de résultat » (outil de diagnostic)."""
    return any(RE_TITRE_RESULTAT.match(cb.normaliser(l.libelle)) for l in lignes)


def extraire_pdf(p: Path, max_pages: int = 30) -> tuple[dict[str, tuple[list[float], str, int]], list[str]]:
    """Totaux du bilan : première occurrence dans le document. Lignes de résultat : seulement dans
    l'état de résultat, de son titre jusqu'au titre de l'état suivant ou des notes, y compris sur
    la page suivante tant que le résultat net n'est pas lu (BNA 2022 : titre p.3, résultat net
    p.4). Jamais dans les notes ni le tableau des capitaux propres (BNA S1 2024 : la ligne
    « Résultat net de l'exercice » p.26 donnait le résultat du S1 2023). Le résultat inscrit
    dans les capitaux propres du bilan (même page que leur total) sert de contrôle (RES_BILAN)."""
    import pdfplumber

    trouves: dict[str, tuple[list[float], str, int]] = {}
    res_bilan: dict[int, tuple[list[float], str, int]] = {}   # page -> ligne de résultat hors état de résultat
    dans_resultat = False
    with pdfplumber.open(p) as pdf:
        for i, page in enumerate(pdf.pages[:max_pages], start=1):
            lignes = cb.lignes_page(page, i)
            dans_resultat = dans_resultat and "RES_NET" not in trouves
            for l in lignes:
                n = cb.normaliser(l.libelle)
                if RE_TITRE_RESULTAT.match(n):
                    dans_resultat = True
                elif RE_AUTRE_ETAT.match(n):
                    dans_resultat = False
                if not l.nombres:
                    continue
                c = code_ligne(l.libelle)
                if not c:
                    continue
                vals = valeurs_ligne(l.nombres)
                if not vals:
                    continue
                if c in CODES_RESULTAT and not dans_resultat:
                    if c in ("RES_NET", "RES_EXERCICE") and i not in res_bilan:
                        res_bilan[i] = (vals, l.libelle, i)
                    continue
                if c not in trouves:
                    trouves[c] = (vals, l.libelle, i)
            if all(c in trouves for c, _ in CODES):
                break

    alertes = []
    repli = "RES_NET" not in trouves and "RES_EXERCICE" in trouves
    if repli:
        # AB : la dernière ligne de l'état de résultat est « Résultat de l'exercice » (sans « net ») ;
        # acceptée sans alerte si elle égale le résultat inscrit au bilan (contrôle plus bas)
        trouves["RES_NET"] = trouves["RES_EXERCICE"]
    trouves.pop("RES_EXERCICE", None)
    page_cp = trouves.get("CAP_PROPRES_EF", (None, None, None))[2]
    page_tp = trouves.get("TOTAL_PASSIF_CP", (None, None, None))[2]
    if page_cp and page_tp and page_cp != page_tp:
        # BIAT S1 2024 avant correction : capitaux propres lus p.10 (note des retraitements),
        # total des capitaux propres et passifs p.2 (bilan)
        alertes.append(f"capitaux propres lus p.{page_cp}, hors de la page du bilan (p.{page_tp})")
    if page_cp in res_bilan:
        trouves["RES_BILAN"] = res_bilan[page_cp]
    rb = trouves.get("RES_BILAN", ([None],))[0][0]
    rn0 = trouves.get("RES_NET", ([None],))[0][0]
    if rb is not None and rn0 is not None and abs(rb - rn0) > 1:
        alertes.append(f"résultat de l'état de résultat ≠ résultat du bilan ({rn0:,.0f} vs {rb:,.0f})")
    if repli and rb is None:
        alertes.append("résultat lu sur la ligne « Résultat de l'exercice », sans résultat au bilan pour "
                       "le confirmer : vérifier")
    for c in ("RES_NET", "TOTAL_ACTIF", "CAP_PROPRES_EF"):
        if c not in trouves:
            alertes.append(f"{c} introuvable")
    ta = trouves.get("TOTAL_ACTIF", ([None],))[0][0]
    tp = trouves.get("TOTAL_PASSIF_CP", ([None],))[0][0]
    cp = trouves.get("CAP_PROPRES_EF", ([None],))[0][0]
    rn = trouves.get("RES_NET", ([None],))[0][0]
    if ta and tp and abs(ta - tp) > 0.01 * abs(ta):
        alertes.append(f"total actif ≠ total passif + capitaux propres ({ta:,.0f} vs {tp:,.0f})")
    if ta and cp and not (0 < cp < ta):
        alertes.append("capitaux propres incohérents avec le total de l'actif")
    if cp and rn and abs(rn) > abs(cp):
        alertes.append("résultat net supérieur aux capitaux propres : ligne mal lue ?")
    return trouves, alertes


TOLERANCE_RECOUPEMENT_MDT = 0.002   # arrondi des banques qui publient en milliers de dinars


def capitaux_propres_trimestriels() -> dict[tuple[str, str], tuple[float, str, str]]:
    """Capitaux propres « hors résultat de la période » retenus dans les indicateurs trimestriels
    (indicateurs_versions.csv) : (banque, date) -> (valeur MDT, fichier, définition annoncée)."""
    src = DOSSIER / "indicateurs_versions.csv"
    if not src.exists():
        return {}
    out = {}
    with src.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if (r["code_indicateur"] == "CAP_PROPRES" and r["mesure"] == "cumul"
                    and r["version"] == r["source_valeur"] and r["valeur_retenue"]):
                out[(r["banque"], r["date_arrete"])] = (float(r["valeur_retenue"]), r["fichier"],
                                                        r["note_definition"])
    return out


def recoupement(trouves: dict, fac: float, cp_trim: tuple | None) -> str:
    """Contrôle non bloquant : capitaux propres du bilan − résultat net de la période = capitaux
    propres « hors résultat » des indicateurs trimestriels. Un écart peut venir de la série
    trimestrielle (BIAT 31/12/2024 : « après affectation du résultat »), d'où le statut non bloquant."""
    if "CAP_PROPRES_EF" not in trouves or "RES_NET" not in trouves:
        return "incomplet"
    if cp_trim is None:
        return "pas de valeur trimestrielle"
    hors_res = (trouves["CAP_PROPRES_EF"][0][0] - trouves["RES_NET"][0][0]) * fac
    ecart = hors_res - cp_trim[0]
    if abs(ecart) <= TOLERANCE_RECOUPEMENT_MDT:
        return "ok"
    return (f"ecart {ecart:+.3f} MDT (EF {hors_res:.3f}, trimestriel {cp_trim[0]:.3f}, {cp_trim[1]}"
            + (f", {cp_trim[2]}" if cp_trim[2] else "") + ")")


def cmd_extraire(args):
    m = lire_manifeste()
    if not m:
        sys.exit("Aucun manifeste : lancez d'abord « telecharger ».")
    champs = ["banque", "date_arrete", "annee", "type", "code", "colonne", "valeur_source", "unite_source",
              "valeur_mdt", "libelle_source", "source", "fichier", "page"]
    n_ok = 0
    cp_trimestriels = capitaux_propres_trimestriels()
    with SORTIE.open("w", newline="", encoding="utf-8-sig") as f, \
         CONTROLE.open("w", newline="", encoding="utf-8-sig") as fc:
        w = csv.DictWriter(f, fieldnames=champs, delimiter=";")
        w.writeheader()
        wc = csv.writer(fc, delimiter=";")
        wc.writerow(["banque", "arrete", "type", "statut", "resultat_net_mdt", "total_actif_mdt",
                     "capitaux_propres_mdt", "alertes", "fichier", "recoupement_trimestriel",
                     "modifications_comptables_mdt", "resultat_apres_modifications_mdt"])
        for (code, cle), r in sorted(m.items()):
            if r["statut"] != "ok" or not Path(r["fichier"]).exists():
                wc.writerow([code, cle, r["type"], "pdf manquant", "", "", "", "", ""])
                continue
            try:
                trouves, alertes = extraire_pdf(Path(r["fichier"]))
            except Exception as e:
                trouves, alertes = {}, [f"erreur de lecture : {e}"]
            ta = trouves.get("TOTAL_ACTIF", ([None],))[0][0]
            fac, unite = facteur_mdt(ta)
            statut = "ok" if trouves and not alertes else ("a verifier" if trouves else "echec")
            n_ok += statut == "ok"
            for c, (vals, lib, page) in trouves.items():
                for col, v in zip(["N", "N1"], vals[:2]):
                    w.writerow({"banque": code, "date_arrete": r["date_arrete"], "annee": r["date_arrete"][:4],
                                "type": r["type"], "code": c, "colonne": col, "valeur_source": v,
                                "unite_source": unite, "valeur_mdt": round(v * fac, 6), "libelle_source": lib,
                                "source": r["source"], "fichier": Path(r["fichier"]).name, "page": page})
            get = lambda c: round(trouves[c][0][0] * fac, 3) if c in trouves else ""
            rec = recoupement(trouves, fac, cp_trimestriels.get((code, r["date_arrete"])))
            wc.writerow([code, cle, r["type"], statut, get("RES_NET"), get("TOTAL_ACTIF"),
                         get("CAP_PROPRES_EF"), " | ".join(alertes), r["fichier"], rec,
                         get("MODIF_COMPTABLES"), get("RES_NET_APRES_MODIF")])
            print(f"  {statut:<11} {code} {cle}  RN={get('RES_NET')}  TA={get('TOTAL_ACTIF')}  "
                  f"CP={get('CAP_PROPRES_EF')}  recoupement : {rec}  {'; '.join(alertes)}")
    print(f"\n{n_ok} documents extraits sans alerte.\nDonnées : {SORTIE}\nContrôle : {CONTROLE}")


# ---------------------------------------------------------------------------
# Comparaison avec ilboursa (résultat net annuel), purement informative : ilboursa ne précise pas
# s'il s'agit de comptes individuels ou consolidés (probablement consolidés : BIAT 2023 358,6 MDT
# contre 331,4 en individuel) ; elle ne change jamais le statut d'un document.
# ---------------------------------------------------------------------------

def cellules(ligne_html: str) -> list[str]:
    brut = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", ligne_html, re.S | re.I)
    return [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in brut]


def resultats_ilboursa(ticker: str, session) -> dict[int, float]:
    """Résultat net annuel (milliers de dinars) depuis la page société d'ilboursa. {} si non reconnu."""
    r = session.get(f"https://www.ilboursa.com/marches/societe/{ticker}", timeout=cb.TIMEOUT)
    if r.status_code != 200:
        return {}
    texte = cb.sans_accents(html.unescape(r.text)).lower()
    if "milliers de dinars" not in texte:
        print(f"    {ticker} : unité non indiquée « en milliers de dinars » sur ilboursa, comparaison ignorée")
        return {}
    annees, res = [], {}
    for tr in re.findall(r"<tr.*?</tr>", r.text, re.S | re.I):
        cells = cellules(tr)
        if not cells:
            continue
        if not annees and sum(bool(re.fullmatch(r"20\d\d", c)) for c in cells) >= 3:
            annees = [int(c) for c in cells if re.fullmatch(r"20\d\d", c)]
        elif annees and cb.normaliser(cells[0]).startswith("resultat net"):
            vals = [cb.valeur(c) for c in cells[1:]]
            res = {a: v for a, v in zip(annees, vals) if v is not None}
            break
    return res


def cmd_verifier(args):
    if not SORTIE.exists():
        sys.exit("Lancez d'abord « extraire ».")
    import requests
    import time

    nos = {}
    with SORTIE.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if r["code"] == "RES_NET" and r["colonne"] == "N" and r["type"] == "annuel":
                nos[(r["banque"], int(r["annee"]))] = float(r["valeur_mdt"])
    s = requests.Session()
    s.headers.update(cb.ENTETES)
    sortie = DOSSIER / "verification_ilboursa.csv"
    with sortie.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["banque", "annee", "resultat_net_extrait_mdt", "resultat_net_ilboursa_mdt", "ecart_pct", "statut"])
        for code in cb.choisir_banques(args.banques):
            time.sleep(cb.PAUSE)
            ref = resultats_ilboursa(cb.BANQUES[code]["ticker"], s)
            if not ref:
                print(f"  {code} : page ilboursa non lue ou format non reconnu")
                continue
            for annee, v in sorted(ref.items()):
                v_mdt = v / 1000          # ilboursa affiche des milliers de dinars
                n = nos.get((code, annee))
                if n is None:
                    w.writerow([code, annee, "", round(v_mdt, 3), "", "absent chez nous"])
                    continue
                ecart = abs(n - v_mdt) / abs(v_mdt) if v_mdt else 0
                statut = "ok" if ecart <= 0.01 else "ecart (informatif)"
                w.writerow([code, annee, round(n, 3), round(v_mdt, 3), f"{ecart:.1%}", statut])
                print(f"  {code} {annee} : extrait {n:,.1f} / ilboursa {v_mdt:,.1f} MDT  {statut}")
    print(f"\nComparaison : {sortie}")


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sous = ap.add_subparsers(dest="cmd", required=True)

    def periode(p):
        p.add_argument("--debut", type=int, default=2019, help="premier exercice (défaut 2019)")
        p.add_argument("--fin", type=int, default=dt.date.today().year)
        p.add_argument("--banques", help="codes séparés par des virgules (défaut : toutes)")

    p = sous.add_parser("telecharger")
    periode(p)
    p.add_argument("--bulletins", action="store_true", help="chercher aussi dans les Bulletins Officiels (lent)")
    p.set_defaults(f=cmd_telecharger)

    p = sous.add_parser("extraire")
    p.set_defaults(f=cmd_extraire)

    p = sous.add_parser("verifier")
    p.add_argument("--banques")
    p.set_defaults(f=cmd_verifier)

    p = sous.add_parser("tout")
    periode(p)
    p.add_argument("--bulletins", action="store_true")
    p.set_defaults(f=lambda a: (cmd_telecharger(a), cmd_extraire(a), cmd_verifier(a)))

    p = sous.add_parser("urls")
    periode(p)
    p.set_defaults(f=cmd_urls)

    args = ap.parse_args()
    args.f(args)


if __name__ == "__main__":
    main()
