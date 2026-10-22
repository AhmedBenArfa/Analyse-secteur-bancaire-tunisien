"""
Génère les deux documents PDF du dossier docs/ :
  - docs/Specification_projet.pdf : rendu de docs/SPECIFICATION.md ;
  - docs/Rapport_avancement.pdf : état d'avancement, chiffres recalculés à partir des fichiers
    du projet (manifeste, contrôle d'extraction, versions, variations comparables, contrôle
    annuel, gabarits, saisies manuelles, valeurs de référence, événements, révisions importantes).

Conversion : HTML -> PDF par Microsoft Edge en mode headless (chemin modifiable par la variable
d'environnement EDGE), puis numéros de page et métadonnées ajoutés avec PyMuPDF.
Les tests (pytest) sont relancés pour donner leur résultat dans le rapport (environ 1 minute).

Utilisation :
  python scripts/generer_pdf.py
"""
import collections, csv, datetime, html, os, re, subprocess, sys, tempfile
from pathlib import Path
import pandas as pd, mistune, fitz

R = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.gettempdir()) / "rapports_banques_pdf"
TMP.mkdir(exist_ok=True)
EDGE = os.environ.get("EDGE") or next(
    (c for c in [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                 r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"] if Path(c).exists()),
    "msedge")
AUTEUR = "Ahmed Ben Arfa"
DATE = datetime.date.today().strftime("%d/%m/%Y")


def fr(x, d=0):
    s = f"{x:,.{d}f}".replace(",", " ").replace(".", ",")
    return s.replace(" ", "\u202f")


def pct(a, b, d=1):
    return fr(100 * a / b, d) + "\u00a0%"


def e(s):
    return html.escape(str(s))


def table(head, rows, cls=""):
    h = "".join(f"<th>{e(x)}</th>" for x in head)
    b = "".join("<tr>" + "".join(f"<td>{x}</td>" for x in r) + "</tr>" for r in rows)
    return f'<table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>'


def lire_csv(p, n):
    """CSV ';' dont la dernière colonne (texte libre) peut contenir des ';'."""
    with open(p, encoding="utf-8-sig") as f:
        rows = list(csv.reader(f, delimiter=";"))
    h = rows[0]
    return [dict(zip(h, r[: n - 1] + [";".join(r[n - 1 :])])) for r in rows[1:]]


CSS = """
@page { size: A4; margin: 18mm 17mm 20mm 17mm; }
body { font-family: 'Segoe UI', Calibri, Arial, sans-serif; font-size: 9.6pt; line-height: 1.42;
       color: #1d2733; background: #fff; }
h1 { font-size: 21pt; color: #12355b; margin: 0 0 4pt 0; line-height: 1.15; }
h2 { font-size: 13.5pt; color: #12355b; border-bottom: 1.5pt solid #12355b; padding-bottom: 2pt;
     margin: 20pt 0 7pt 0; break-after: avoid; }
h3 { font-size: 11pt; color: #1f5c99; margin: 13pt 0 5pt 0; break-after: avoid; }
h4 { font-size: 10pt; margin: 10pt 0 4pt 0; break-after: avoid; }
p, li { margin: 0 0 5pt 0; }
ul, ol { margin: 0 0 6pt 0; padding-left: 16pt; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0 9pt 0; font-size: 8.4pt;
        break-inside: auto; }
tr { break-inside: avoid; }
th { background: #e6edf5; color: #12355b; text-align: left; font-weight: 600;
     border: 0.6pt solid #b8c7d9; padding: 3pt 4pt; }
td { border: 0.6pt solid #cfd9e5; padding: 2.5pt 4pt; vertical-align: top; }
table.num td:not(:first-child), table.num th:not(:first-child) { text-align: right; }
code { font-family: Consolas, 'Courier New', monospace; font-size: 8.4pt; background: #f1f4f8;
       padding: 0 2pt; border-radius: 2pt; }
pre { background: #f4f6f9; border: 0.6pt solid #d5dde7; border-radius: 3pt; padding: 6pt 8pt;
      font-size: 7.8pt; line-height: 1.3; white-space: pre-wrap; break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 7.8pt; }
.titre { border-bottom: 3pt solid #12355b; padding-bottom: 8pt; margin-bottom: 12pt; }
.soustitre { font-size: 11pt; color: #45566b; }
.meta { font-size: 8.8pt; color: #5b6b7e; margin-top: 4pt; }
.encadre { background: #f2f6fb; border-left: 3pt solid #1f5c99; padding: 6pt 9pt; margin: 6pt 0 10pt 0; }
.alerte { background: #fdf5ec; border-left: 3pt solid #c47a1d; padding: 6pt 9pt; margin: 6pt 0 10pt 0; }
.kpis { display: flex; gap: 6pt; margin: 6pt 0 10pt 0; }
.kpi { flex: 1; border: 0.8pt solid #c9d6e5; border-radius: 4pt; padding: 5pt 7pt; }
.kpi b { display: block; font-size: 15pt; color: #12355b; line-height: 1.1; }
.kpi span { font-size: 7.8pt; color: #5b6b7e; }
.petit { font-size: 8.2pt; color: #5b6b7e; }
"""


def page_html(titre, corps):
    return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>{e(titre)}</title>'
            f"<style>{CSS}</style></head><body>{corps}</body></html>")


def vers_pdf(html_txt, sortie, titre, sujet, pied):
    src = TMP / (Path(sortie).stem + ".html")
    src.write_text(html_txt, encoding="utf-8")
    brut = TMP / (Path(sortie).stem + "_brut.pdf")
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--user-data-dir={TMP / 'profil'}", f"--print-to-pdf={brut}", src.as_uri()],
                   check=True, capture_output=True, timeout=180)
    doc = fitz.open(brut)
    n = doc.page_count
    for i, p in enumerate(doc, 1):
        w, h = p.rect.width, p.rect.height
        p.insert_text((48, h - 26), pied, fontsize=7.5, fontname="helv", color=(0.42, 0.48, 0.55))
        t = f"{i} / {n}"
        p.insert_text((w - 48 - fitz.get_text_length(t, "helv", 7.5), h - 26), t,
                      fontsize=7.5, fontname="helv", color=(0.42, 0.48, 0.55))
    doc.set_metadata({"title": titre, "author": AUTEUR, "subject": sujet, "keywords": "",
                      "creator": "", "producer": "", "creationDate": fitz.get_pdf_now(),
                      "modDate": fitz.get_pdf_now()})
    doc.save(sortie, garbage=4, deflate=True)
    print(sortie, n, "pages")


def resultat_tests():
    """Relance les tests : résumé de pytest et comparaison aux valeurs de référence."""
    p = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"],
                       cwd=R, capture_output=True, text=True, encoding="utf-8", errors="replace")
    fin = re.findall(r"(\d+) (passed|failed|error)", p.stdout.strip().splitlines()[-1])
    trad = {"passed": ("réussi", "réussis"), "failed": ("en échec",) * 2, "error": ("en erreur",) * 2}
    resume = ", ".join(f"{n} test{'s' if int(n) > 1 else ''} {trad[s][int(n) > 1]}"
                       for n, s in fin) or "résultat illisible"
    sys.path.insert(0, str(R / "tests"))
    import test_extraction
    res = test_extraction.comparer()
    nb_ok = sum(r["statut"] == "ok" for r in res)
    return {"pytest": resume, "references": f"{nb_ok}/{len(res)} valeurs conformes"}


# --------------------------------------------------------------------------- spécification
def specification():
    md = (R / "docs/SPECIFICATION.md").read_text(encoding="utf-8")
    titre, reste = md.split("\n", 1)
    rendu = mistune.create_markdown(plugins=["table", "strikethrough"], escape=False)(reste)
    corps = (f'<div class="titre"><h1>{e(titre.lstrip("# ").strip())}</h1>'
             f'<div class="soustitre">Spécification du rapport Power BI — 12 banques cotées à la '
             f'Bourse de Tunis</div><div class="meta">{AUTEUR} · version du {DATE} '
             f'(générée à partir de docs/SPECIFICATION.md)</div></div>{rendu}')
    vers_pdf(page_html("Spécification du projet", corps), R / "docs/Specification_projet.pdf",
             "Spécification — Analyse du secteur bancaire tunisien", "Spécification du projet",
             f"Analyse du secteur bancaire tunisien — Spécification ({DATE})")


# --------------------------------------------------------------------------- rapport
def rapport():
    D = R / "donnees"
    man = pd.read_csv(D / "manifeste_telechargements.csv", dtype=str)
    ctl = pd.read_csv(D / "controle_extraction.csv", sep=";", encoding="utf-8-sig", dtype={"alertes": str})
    ver = pd.read_csv(D / "indicateurs_versions.csv", sep=";", encoding="utf-8-sig", low_memory=False)
    vc = pd.read_csv(D / "variations_comparables.csv", sep=";", encoding="utf-8-sig")
    ca = pd.read_csv(D / "controle_annuel.csv", sep=";", encoding="utf-8-sig")
    lng = pd.read_csv(D / "indicateurs_banques_long.csv", sep=";", encoding="utf-8-sig", low_memory=False)
    dimb = pd.read_csv(D / "dim_banque.csv", sep=";", encoding="utf-8-sig")
    ri = pd.read_csv(R / "docs/revisions_importantes.csv", sep=";", encoding="utf-8-sig")
    ref = lire_csv(R / "tests/valeurs_reference.csv", 10)
    sai = lire_csv(R / "saisies_manuelles.csv", 11)
    gab = lire_csv(R / "gabarits.csv", 10)
    with open(R / "evenements.csv", encoding="utf-8-sig") as f:
        er = list(csv.reader(f, delimiter=";"))
    mauvaises = [i for i, r in enumerate(er, 1) if len(r) != len(er[0])]
    if mauvaises:
        raise ValueError(f"evenements.csv : nombre de champs incorrect aux lignes {mauvaises} "
                         "(« ; » dans une description ?)")
    evt = pd.DataFrame(er[1:], columns=er[0])
    evt["montant_mdt"] = evt.montant_mdt.astype(float)
    tests = resultat_tests()
    exc = lire_csv(R / "exclusions_colonnes.csv", 6)
    listecmf = pd.read_csv(D / "liste_indicateurs_cmf.csv")
    noms = dict(zip(dimb.code_banque, dimb.nom))
    banques = list(dimb.code_banque)

    trims = sorted(man.trimestre.unique())
    nb_att = len(man)
    ok = man[man.statut == "ok"]
    manq = man[man.statut != "ok"]
    src_lib = {"site": "Sites BVMT / CMF (adresse construite)", "liste_cmf": "Liste des indicateurs du CMF",
               "bulletin_officiel": "Bulletins Officiels du CMF"}
    src = ok.source.value_counts()

    st = ctl.statut.value_counts()
    lus = ctl[~ctl.statut.isin(["pdf manquant", "non publié", "illisible (image)"])]
    illis = ctl[ctl.statut == "illisible (image)"]
    saisis = ctl[ctl.statut == "saisie manuelle"]

    o = []
    A = o.append
    A(f'<div class="titre"><h1>Rapport d\'avancement</h1><div class="soustitre">Analyse du secteur '
      f'bancaire tunisien — 12 banques cotées, T4 2019 → T3 2026</div><div class="meta">{AUTEUR} · '
      f'état au {DATE} · chiffres recalculés à partir des fichiers du projet (manifeste, contrôle '
      f'd\'extraction, versions, variations comparables, contrôle annuel, gabarits, saisies, '
      f'valeurs de référence, événements)</div></div>')

    A('<div class="kpis">'
      f'<div class="kpi"><b>{len(ok)} / {nb_att}</b><span>documents trouvés</span></div>'
      f'<div class="kpi"><b>{len(lus)}</b><span>documents lus (dont {len(saisis)} saisis à la main)</span></div>'
      f'<div class="kpi"><b>{fr(len(lng))}</b><span>valeurs lues dans les documents</span></div>'
      f'<div class="kpi"><b>{len(ref)}</b><span>valeurs de référence relevées à la main</span></div>'
      f'<div class="kpi"><b>{len(ri)}</b><span>révisions de plus de 2&nbsp;% (totaux, cumul)</span></div>'
      "</div>")

    # 1. Objectif ---------------------------------------------------------------------------
    A("<h2>1. Objectif et périmètre</h2>")
    A("<p>Le projet construit un rapport Power BI de portfolio qui compare l'activité, l'efficacité "
      "et la structure des 12 banques cotées à la Bourse de Tunis, trimestre par trimestre, à partir "
      "de leurs <b>indicateurs d'activité trimestriels</b> (publiés au CMF et à la BVMT au plus tard "
      "20 jours après la fin de chaque trimestre), complétés plus tard par les cours boursiers et par "
      "les états financiers semestriels et annuels (ROE, ROA). L'idée vient d'un rapport Power BI "
      "publié sur LinkedIn sur les ratios des banques cotées au 30/06/2026, construit à partir des "
      "mêmes publications ; ce projet y ajoute l'historique, les contrôles et la traçabilité.</p>")
    A("<p>Chaîne de traitement : PDF publics → script Python (<code>collecte_banques.py</code>) → "
      "CSV → Power Query → modèle en étoile → mesures DAX → rapport. Chaque valeur garde le fichier "
      "et la page d'où elle vient ; aucune valeur n'est estimée.</p>")
    A(f"<p>Période : {trims[0][:4]} T{trims[0][-1]} → {trims[-1][:4]} T{trims[-1][-1]}, soit "
      f"{len(trims)} trimestres (le T4 2019 sert de base aux évolutions sur un an de 2020) ; "
      f"{len(banques)} banques × {len(trims)} trimestres = {nb_att} documents attendus. "
      "Unité de toutes les données : millions de dinars (MDT).</p>")
    A(table(["Code", "Banque", "Code", "Banque"],
            [[f"<b>{a}</b>", e(noms[a]), f"<b>{b}</b>", e(noms[b])]
             for a, b in zip(banques[:6], banques[6:])]))

    # 2. Collecte ---------------------------------------------------------------------------
    A("<h2>2. Collecte des documents</h2>")
    A("<h3>Sources et ordre de recherche</h3>")
    A(f"<p>Pour chaque banque et chaque trimestre, le script essaie les sources dans cet ordre et "
      "s'arrête au premier document trouvé ; il respecte le robots.txt de chaque site (pause de "
      "10&nbsp;s entre deux requêtes à la BVMT, à tunis-stockexchange.com et au CMF depuis le "
      "20/10/2026, 0,4&nbsp;s avant), sans téléchargements en parallèle, et reprend là où il s'était arrêté "
      "(<code>donnees/manifeste_telechargements.csv</code>).</p><ol>"
      "<li><b>Sites de la BVMT et du CMF</b> : adresses construites à partir des formats de nom "
      "constatés pour chaque banque ;</li>"
      f"<li><b>Liste des indicateurs publiés sur le site du CMF</b> "
      f"(<code>liste_indicateurs_cmf.csv</code>, {fr(len(listecmf))} adresses, jusqu'aux documents de 2011 ; les pages de tête sont relues à chaque "
      "mise à jour) ;</li>"
      "<li><b>Bulletins Officiels du CMF</b> : le bloc de la banque est découpé dans le bulletin du "
      "jour ; il doit contenir « produit net bancaire » (règle ajoutée après un faux positif, "
      "voir plus bas).</li></ol>")
    A(table(["Source", "Documents", "Part"],
            [[e(src_lib[k]), fr(src[k]), pct(src[k], len(ok))] for k in ["site", "liste_cmf", "bulletin_officiel"]]
            + [["<b>Total trouvé</b>", f"<b>{len(ok)}</b>", pct(len(ok), nb_att) + " des attendus"]], "num"))
    bo = ok[ok.source == "bulletin_officiel"].groupby("banque").trimestre.apply(list)
    lc = ok[ok.source == "liste_cmf"]
    A("<p>Les Bulletins Officiels servent surtout pour Wifak International Bank "
      f"({len(bo.get('WIB', []))} documents) et la BH ({len(bo.get('BH', []))}) ; la liste du CMF a "
      "fourni " + ", ".join(f"{b} {t}" for b, t in lc[["banque", "trimestre"]].values) + ".</p>")

    A("<h3>Documents par banque</h3>")
    rows = []
    for b in banques:
        mb = man[man.banque == b]
        s = mb[mb.statut == "ok"].source.value_counts()
        mq = mb[mb.statut != "ok"].trimestre.tolist()
        rows.append([f"<b>{b}</b>", fr(len(mb)), fr((mb.statut == 'ok').sum()), fr(s.get("site", 0)),
                     fr(s.get("liste_cmf", 0)), fr(s.get("bulletin_officiel", 0)), e(", ".join(mq))])
    A(table(["Banque", "Attendus", "Trouvés", "Sites", "Liste CMF", "Bulletins", "Manquants"], rows, "num"))

    A("<h3>Documents manquants et raison</h3>")
    t3 = manq[manq.trimestre == trims[-1]]
    autres = manq[manq.trimestre != trims[-1]]
    der = f"T{trims[-1][-1]} {trims[-1][:4]}"
    if not len(manq):
        A(f"<p><b>Aucun document manquant</b> : les {len(man)} documents attendus sont trouvés. Derniers "
          "retrouvés le 22/10/2026 : Attijari 2021T2 sur tunis-stockexchange.com (nouveau site de la Bourse) "
          "et Wifak 2022T3 sur le site de la banque (rubrique « Indicateurs d'activité »), absents des sites "
          "de la BVMT et du CMF, de la liste du CMF et des Bulletins Officiels.</p>")
    A(f"<p><b>{len(manq)} documents manquants</b> :</p><ul>" if len(manq) else "<ul>")
    for statut, sens in (("non publié", "non publiés : absents de la liste du CMF (aucun PDF de la banque "
                                        "pour ce trimestre), publication attendue au plus tard 20 jours "
                                        "après la fin du trimestre"),
                         ("manquant", "introuvables pour l'instant (sites, liste du CMF, Bulletins Officiels)")):
        x = t3[t3.statut == statut]
        if len(x):
            A(f"<li><b>{len(x)} × {der}</b> (" + ("toutes les banques" if len(x) == len(banques)
              else ", ".join(x.banque)) + f") : {sens}.</li>")
    for b, t in autres[["banque", "trimestre"]].values:
        A(f"<li><b>{b} {t}</b> : introuvable (aucune adresse BVMT/CMF valide, absent de la liste du CMF, "
          "lue jusqu'aux documents de 2011, et des Bulletins Officiels ; sur tunis-stockexchange.com, aucune "
          "publication de la banque entre le 26/04/2022 et le 31/12/2022, vérifié le 22/10/2026). Les colonnes "
          "N-1 du document de l'année suivante donnent les chiffres de comparaison.</li>")
    A("</ul>")
    A("<p><b>Document rejeté</b> : pour AB 2021T1, le premier document retenu (Bulletin Officiel du "
      "14/04/2021) était une note d'opération d'emprunt qui ne faisait qu'annoncer les indicateurs. "
      "Il a été mis de côté dans <code>donnees/rejetes/AB/</code> (avec une copie du manifeste "
      "d'avant), puis remplacé par le PDF de la BVMT. C'est l'origine de la règle « le bloc doit "
      "contenir produit net bancaire » ; aucun autre extrait de bulletin n'est rejeté par cette règle.</p>")

    # 3. Extraction -------------------------------------------------------------------------
    A("<h2>3. Extraction des indicateurs</h2>")
    A("<h3>Gabarits</h3>")
    nb_g = collections.Counter(g["banque"] for g in gab)
    defs = collections.defaultdict(set); unites = collections.defaultdict(set)
    for g in gab:
        defs[g["banque"]].add(g["definition_charges_operatoires"]); unites[g["banque"]].add(g["unite"])
    A(f"<p>Les tableaux changent de mise en page d'une banque à l'autre et, pour certaines, presque "
      f"chaque année. Le fichier versionné <code>gabarits.csv</code> ({len(gab)} lignes) décrit pour "
      "chaque banque et chaque période de mise en page : l'ordre des colonnes, l'unité, les libellés "
      "particuliers et le contenu des charges opératoires publiées. <b>Le gabarit décide</b> ; la "
      "lecture de l'en-tête et l'unité déduite du PNB ne servent plus que de contrôles (alerte en cas "
      "de désaccord). Les colonnes sont repérées par le bord droit des montants.</p>")
    A(table(["Banque", "Lignes de gabarit", "Unité de publication", "Charges opératoires publiées"],
            [[f"<b>{b}</b>", fr(nb_g[b]), e(" puis ".join(sorted(unites[b], key=lambda u: u != 'dinars'))
                                            if b == "BH" else ", ".join(sorted(unites[b]))),
              e(", ".join(sorted(defs[b])))] for b in banques]))
    A("<p class='petit'>BH : dinars jusqu'au T3 2022, milliers de dinars ensuite. Attijari (TJARI) : "
      "charges opératoires sans dotations jusqu'au T3 2021, avec un reste non détaillé à partir du "
      "T4 2021.</p>")
    A("<p>Méthode suivie pour chaque banque : diagnostic d'un document par année "
      "(<code>scripts/diagnostic_pdf.py</code> : bords de colonnes, en-têtes, unité, libellés "
      "reconnus) → lignes de gabarit → deux documents de périodes différentes relevés à la main "
      "sur l'image du PDF → extraction de la banque seule (<code>scripts/essai_banque.py</code>) → "
      "examen des alertes, document par document.</p>")

    A("<h3>Contrôles faits à l'extraction</h3><ul>"
      "<li><b>Produits − charges d'exploitation bancaire = PNB</b>, dans toutes les colonnes "
      "(N et N-1) ;</li>"
      "<li><b>Écart trimestre / cumul</b> : trimestre publié comparé à « cumul du trimestre − cumul "
      "du trimestre précédent » (seuil 0,1&nbsp;%) ;</li>"
      "<li><b>Retraitement possible</b> : la colonne N-1 d'un document diffère de la valeur publiée "
      "un an plus tôt ;</li>"
      "<li><b>Charges opératoires contre leurs composantes</b>, selon la définition du gabarit "
      "(statut <code>ecart composantes</code>) ;</li>"
      "<li><b>Ordres de grandeur</b> (bornes par indicateur, coefficient d'exploitation jusqu'à "
      "200&nbsp;%) et <b>contrôle annuel</b> : somme des 4 trimestres retenus contre cumul T4 retenu "
      "(<code>controle_annuel.csv</code>) ;</li>"
      "<li><b>Colonnes N-1 incohérentes</b> non retenues (section 4).</li></ul>")

    A("<h3>Statut des documents</h3>")
    ordre = ["ok", "retraitement possible", "ecart trimestre/cumul", "ecart composantes", "a verifier",
             "saisie manuelle", "illisible (image)", "non publié", "pdf manquant"]
    sens = {"ok": "aucune alerte", "retraitement possible": "colonne N-1 ≠ valeur publiée un an plus tôt (révision de la banque)",
            "ecart trimestre/cumul": "trimestre ≠ différence des cumuls (révision en cours d'année)",
            "ecart composantes": "total des charges opératoires incohérent avec ses composantes",
            "a verifier": "alerte bloquante à examiner", "saisie manuelle": "tableau en image, valeurs saisies",
            "illisible (image)": "tableau en image, repris par d'autres documents",
            "non publié": "absent de la liste du CMF (trimestre récent)", "pdf manquant": "document non trouvé"}
    A(table(["Statut", "Documents", "Signification"],
            [[f"<code>{s}</code>", fr(st.get(s, 0)), e(sens[s])] for s in ordre]
            + [["<b>Total</b>", f"<b>{st.sum()}</b>", ""]]))
    ct = pd.crosstab(ctl.banque, ctl.statut)
    abr = {"ok": "ok", "retraitement possible": "retrait.", "ecart trimestre/cumul": "trim./cumul",
           "ecart composantes": "compos.", "a verifier": "à vérif.", "saisie manuelle": "saisie",
           "illisible (image)": "image", "non publié": "non publ.", "pdf manquant": "manquant"}
    A(table(["Banque"] + [abr[s] for s in ordre],
            [[f"<b>{b}</b>"] + [fr(ct.loc[b].get(s, 0)) if ct.loc[b].get(s, 0) else "·" for s in ordre]
             for b in banques], "num"))
    A("<p>Les statuts <code>retraitement possible</code> et <code>ecart trimestre/cumul</code> ne "
      "signalent pas des erreurs de lecture : ce sont des révisions publiées par les banques "
      "(vérifiées dans les PDF pour les cas examinés). La STB, par exemple, retraite très souvent "
      f"ses trimestres en cours d'année ({ct.loc['STB'].get('ecart trimestre/cumul', 0)} documents).</p>")

    A("<h3>Valeurs de référence</h3>")
    refb = collections.defaultdict(set)
    for r in ref:
        refb[r["banque"]].add(r["fichier"])
    refi = collections.Counter(r["code_indicateur"] for r in ref)
    A(f"<p><code>tests/valeurs_reference.csv</code> : <b>{len(ref)} valeurs relevées à la main sur "
      f"l'image de {sum(len(s) for s in refb.values())} documents</b> "
      f"(2 par banque, 8 pour BIAT et UIB), comparées à l'extraction par les tests "
      f"(<code>python -m pytest tests</code>). Résultat au {DATE} : <b>{tests['references']}</b> ; "
      f"pytest : <b>{tests['pytest']}</b> (comparaison aux valeurs de référence, document "
      "illisible BH 2019T4, révision BH 2024, BT 2020T3, seuil UIB 2025, variations comparables, "
      "saisies manuelles, colonnes N-1 exclues, somme des trimestres, bilan simulé des états "
      "financiers).</p>")
    A(table(["Indicateur", "Valeurs"], [[f"<code>{k}</code>", fr(n)] for k, n in refi.most_common(8)]
            + [["autres", fr(sum(n for k, n in refi.most_common()[8:]))]], "num"))

    A("<h3>Documents illisibles et saisies manuelles</h3>")
    A(f"<p><b>{len(illis)} documents ont leur tableau publié en image sans être saisis</b> (page avec images et moins "
      "de 1 000 caractères de texte) : "
      + ", ".join(f"{b} {t}" for b, t in illis[["banque", "trimestre"]].values)
      + ". Leurs chiffres sont repris des colonnes N-1 du document de l'année suivante quand il est "
      "lisible : en entier pour BH 2019T4 (document BH 2020T4) et UIB 2022T3. Les 13 documents BTE "
      "en image (2020T1 à 2023T4, sauf 2022T2, 2023T1 et 2023T3) sont tous saisis à la main : leurs "
      "colonnes N-1 publient des corrections que rien d'autre ne donne (T1 2021 corrigé dans BTE "
      "2022T1).</p>")
    nd = ver[ver.statut_revision == "non disponible (image)"].groupby(["banque", "trimestre"]).size()
    if nd.sum():
        A(f"<p><b>Valeurs non disponibles</b> : {int(nd.sum())} lignes « non disponible (image) » dans "
          "<code>indicateurs_versions.csv</code> ("
          + ", ".join(f"{b} {t} : {n}" for (b, t), n in nd.items())
          + ") : aucun document lisible ne les publie. Elles restent vides, jamais à zéro.</p>")
    else:
        A("<p><b>Valeurs non disponibles</b> : aucune ligne « non disponible (image) » dans "
          "<code>indicateurs_versions.csv</code>.</p>")
    sb = collections.Counter((s["banque"], s["trimestre"]) for s in sai)
    sv = collections.Counter(s["verification"] for s in sai)
    bte = {k: n for k, n in sb.items() if k[0] == "BTE"}
    A(f"<p><b>Saisies manuelles</b> (<code>saisies_manuelles.csv</code>, versionné) : "
      f"<b>{len(sai)} valeurs</b>, avec fichier, page et mode de vérification pour chacune.</p><ul>"
      f"<li><b>BTE, {len(bte)} documents, {sum(bte.values())} valeurs</b> ("
      + ", ".join(t for _, t in sorted(bte)) + ") : documents illisibles dont le document de l'année "
      "suivante est lui aussi une image. Saisie décidée avec l'utilisateur, limitée aux indicateurs "
      "du rapport (PNB, produits et charges d'exploitation, frais de personnel, charges générales, "
      "charges opératoires, crédits, dépôts). Contrôles passés sans erreur : produits − charges = "
      "PNB, frais de personnel + charges générales = charges opératoires, colonne « Variation "
      "montant » = N − N-1, dépôts = somme des catégories.</li>"
      f"<li><b>STB 2026T2, {sb[('STB','2026T2')]} valeurs</b> : saisie partielle d'un document "
      "lisible ; les revenus du portefeuille du T2 2026 étaient superposés à leur libellé "
      "(l'extraction lisait 893 522 au lieu de 115 893 522 pour le T2 2025). Contrôle intérêts + "
      "commissions + portefeuille = produits passé.</li></ul>")
    A(table(["Vérification", "Valeurs"], [[e(k), fr(n)] for k, n in sv.most_common()], "num"))
    A("<p class='petit'>« vérifié par Ahmed Ben Arfa » : 36 valeurs de BTE 2020T2 relues "
      "indépendamment par l'auteur à partir des images du tableau.</p>")

    # 4. Règles -----------------------------------------------------------------------------
    A("<h2>4. Règles de données et justification</h2>")
    vfam = ver.version.str.replace(r"_T\d.*", "", regex=True).value_counts()
    ret = ver[ver.version == ver.source_valeur]
    rfam = ret.source_valeur.str.replace(r"_T\d.*", "", regex=True).value_counts()
    A("<h3>Versions initiale et révisée</h3>")
    A("<p>Une même période est publiée plusieurs fois : dans le document du trimestre (version "
      "<code>initiale</code>), puis en comparaison dans le document du même trimestre de l'année "
      "suivante (<code>revisee_T&lt;q&gt;_N+1</code>), et, pour le cumul annuel et les soldes au "
      "31/12, dans la colonne « 31/12/N-1 » des documents T1 à T3 suivants "
      "(<code>revisee_31-12</code>, provisoire). Toutes les versions sont gardées dans "
      f"<code>indicateurs_versions.csv</code> ({fr(len(ver))} lignes) avec fichier et page ; la "
      "valeur d'analyse suit un ordre de priorité fixe (révisée N+1 &gt; 31/12 du document le plus "
      "récent &gt; initiale ; le T4 seul n'utilise jamais la colonne 31/12).</p>")
    A(table(["Version", "Lignes", "dont valeurs retenues"],
            [[f"<code>{k}</code>", fr(vfam.get(k, 0)), fr(rfam.get(k, 0))] for k in ["initiale", "revisee", "revisee_31-12"]]
            + [["<b>Total</b>", fr(len(ver)), fr(len(ret))]], "num"))

    A("<h3>Règle des révisions (troisième version, 17/10/2026)</h3>")
    A("<p><b>Les niveaux prennent toujours la version révisée quand elle existe</b>, avec ou sans "
      "note de retraitement (la note est gardée pour information). La révision est qualifiée sur "
      "le <b>cumul</b> de la période, et le statut s'applique au trimestre et au cumul :</p>")
    A(table(["Écart révisée − initiale (cumul)", "Statut", "Effet"],
            [["≤ 2 milliers de dinars (arrondi)", "vide", "—"],
             ["≤ 2&nbsp;% du cumul initial", "<code>retraitement_mineur</code>", "—"],
             ["&gt; 2&nbsp;% du cumul initial", "<code>revision_importante</code>",
              "<code>rupture_serie</code> = « oui » : marqueur dans les graphiques"],
             ["total stable, composantes qui bougent", "<code>reclassement</code>", "signalé"]]))
    A("<p>Le cumul sert de mesure parce qu'un trimestre seul, petit montant, dépasse vite 2&nbsp;% "
      "sans que l'année change. Le seuil de 2&nbsp;% est un choix d'analyse, pas une norme.</p>")
    bt = ver[(ver.banque == "BT") & (ver.trimestre == "2020T3") & (ver.code_indicateur == "CHG_OPER") & (ver.mesure == "trim")]
    bt_i = bt[bt.version == "initiale"].valeur_mdt.iloc[0]; bt_r = bt[bt.version == bt.source_valeur].valeur_mdt.iloc[0]
    A('<div class="encadre"><b>Pourquoi les deux premières versions ont été abandonnées.</b> '
      "Règle 1 : garder l'initiale dès qu'un document annonçait un retraitement. Règle 2 : la garder "
      "seulement si l'écart dépassait 2&nbsp;% et que le document l'annonçait. La liste des 60 cas "
      "« changement de méthode » de la règle 2 a montré quatre problèmes :<ul>"
      f"<li>elle gardait des valeurs fausses : BT, charges opératoires du T3 2020 publiées à "
      f"{fr(bt_i,3)} MDT (le don au Fonds 1818 retiré de ce seul trimestre), corrigées à "
      f"{fr(bt_r,3)} MDT un an plus tard ;</li>"
      "<li>elle dépendait de la rédaction : « chiffres retraités pour les besoins de comparabilité » "
      "est une formule de routine, et l'ATB retraite sans jamais l'écrire ;</li>"
      "<li>elle mélangeait trimestre et cumul d'une même période (seuil appliqué mesure par mesure) ;</li>"
      "<li>elle n'était plus utile : les croissances viennent de <code>Variations_Comparables</code>, "
      "indépendantes du choix des niveaux.</li></ul></div>")
    sr = ver.statut_revision.fillna("(vide)")
    ini = ver[ver.version == "initiale"]
    A(f"<p>Résultat : {fr((ini.statut_revision=='revision_importante').sum())} valeurs initiales "
      f"remplacées par une révision importante, {fr((ini.statut_revision=='retraitement_mineur').sum())} "
      f"par un retraitement mineur, {fr((sr=='reclassement').sum())} reclassements ; "
      f"{fr((ret.rupture_serie=='oui').sum())} valeurs retenues portent un marqueur de rupture.</p>")

    A("<h3>Colonnes N-1 non retenues</h3>")
    ex_auto = ver[ver.statut_revision.fillna("").str.startswith("exclue (colonne")]
    ex_ecr = ver[ver.statut_revision.fillna("").str.startswith("exclue (exclusion")]
    A(f"<p>Une colonne de comparaison fausse dans le document de la banque ne devient jamais la "
      f"valeur retenue (décision du 17/10/2026). Règle automatique (produits − charges ≠ PNB de plus "
      f"de 2&nbsp;% dans la colonne) : UIB 2023T2, colonne T2 2022 ({len(ex_auto)} lignes ; charges "
      f"d'exploitation égales au cumul du semestre). Exclusion écrite (<code>exclusions_colonnes.csv</code>, "
      f"{len(exc)} cas) : " + "; ".join(f"{x['banque']} {x['trimestre']} {x['colonne']} ({len(ex_ecr)} lignes) — "
                                       f"colonne du T4 2022 recopiée du T3 2022, source {x['fichier']} p.{x['page']}" for x in exc)
      + ".</p>")

    A("<h3>Variations comparables</h3>")
    bh = vc[(vc.banque == "BH") & (vc.trimestre == "2025T4") & (vc.code_indicateur == "PNB") & (vc.mesure == "cumul")].iloc[0]
    bh_pub = ver[(ver.banque == "BH") & (ver.trimestre == "2024T4") & (ver.code_indicateur == "PNB")
                 & (ver.mesure == "cumul") & (ver.version == "initiale")].valeur_mdt.iloc[0]
    A(f"<p>Toutes les variations sur un an sont calculées <b>à l'intérieur d'un même document</b> "
      f"(colonne N contre colonne N-1), jamais en rapprochant deux documents : "
      f"<code>variations_comparables.csv</code>, {fr(len(vc))} lignes "
      f"({fr((vc.mesure=='trim').sum())} trimestres seuls, {fr((vc.mesure=='cumul').sum())} cumuls ou soldes). "
      f"Exemple : BH, PNB 2025 = {fr(bh.valeur_N,3)} MDT contre {fr(bh.valeur_N1,3)} MDT pour 2024 "
      f"retraité dans le même document, soit {fr(100*bh.variation_pct,1)}&nbsp;% ; avec le "
      f"{fr(bh_pub,3)} publié un an plus tôt, on obtiendrait {fr(100*(bh.valeur_N/bh_pub-1),1)}&nbsp;%.</p>")

    A("<h3>Coefficient d'exploitation harmonisé</h3>")
    A("<p>Le contenu des charges opératoires publiées varie (tableau des gabarits ci-dessus : sans "
      "dotations, avec dotations publiées, avec un reste non détaillé). Le <b>coefficient "
      "harmonisé</b> = (frais de personnel + charges générales d'exploitation) / PNB sert à tous les "
      "classements et comparaisons entre banques ; le <b>coefficient publié</b> = charges "
      "opératoires publiées / PNB reste affiché pour information, avec la définition de la banque. "
      "Limite : le coefficient harmonisé sous-estime le coût total des banques dont les dotations "
      "aux amortissements sont importantes.</p>")

    A("<h3>Capitaux propres hors résultat de la période</h3>")
    biat = ver[(ver.banque == "BIAT") & (ver.date_arrete == "2025-12-31") & (ver.code_indicateur == "CAP_PROPRES")]
    bv = {r.fichier: r.valeur_mdt for r in biat.itertuples()}
    A(f"<p>La colonne 31/12 provisoire n'est jamais retenue pour les capitaux propres : sa "
      f"définition change d'un document à l'autre. BIAT au 31/12/2025 : {fr(bv['BIAT_2025T4.pdf'],1)} MDT "
      f"dans le document T4 2025 (résultat non inclus), {fr(bv['BIAT_2026T1.pdf'],1)} dans le T1 2026 "
      f"(« avant affectation du résultat »), {fr(bv['BIAT_2026T2.pdf'],1)} dans le T2 2026 (« après "
      "affectation »). La série reste homogène : « capitaux propres hors résultat de la période » "
      f"({fr((sr=='exclue (capitaux propres, 31/12 provisoire)').sum())} lignes 31/12 exclues). Le ROE "
      "utilisera les capitaux propres du bilan des états financiers, résultat inclus.</p>")

    A("<h3>Équivalences Wifak International Bank (banque islamique)</h3>")
    A("<p>Les indicateurs de Wifak ne sont pas des intérêts et des crédits ; ils sont rangés sous "
      "les codes communs pour permettre la comparaison, et signalés dans le rapport :</p>")
    A(table(["Libellé Wifak", "Code", "Équivalent conventionnel"], [
        ["Marges et revenus assimilés", "<code>INT_PERCUS</code>", "Intérêts perçus"],
        ["Charges encourues et charges assimilées", "<code>INT_ENCOURUS</code>", "Intérêts encourus"],
        ["Revenus du portefeuille commercial et opérations financières + du portefeuille d'investissement",
         "<code>REV_PORTEF</code>", "Revenus du portefeuille-titres"],
        ["Encours net des financements à la clientèle", "<code>CREDITS</code>", "Encours des crédits"],
        ["Tawfir", "<code>DEP_EPARGNE</code>", "Dépôts d'épargne"],
        ["Comptes Istithmars", "<code>DEP_TERME</code>", "Dépôts à terme"],
        ["Dettes de financements et ressources spéciales", "<code>EMPRUNTS</code>", "Emprunts et ressources spéciales"]]))

    # 5. Événements -------------------------------------------------------------------------
    A("<h2>5. Événements identifiés</h2>")
    A("<p>Les révisions importantes ont été examinées dans les PDF ; quatre causes sont "
      f"documentées dans <code>evenements.csv</code> ({len(evt)} lignes, une par banque concernée, "
      "avec le fichier et la page de la source). Elles serviront d'annotations aux graphiques.</p>")
    titres = {"FONDS_1818": "Don au Fonds 1818 (Covid-19), 2020",
              "ACCORD_APTBEF_FGBEF": "Accord salarial APTBEF–FGBEF, 2021",
              "MORATOIRE_COVID_UIB": "Moratoire Covid de l'UIB, 2020",
              "BH_RETRAITEMENT_2024": "Retraitement BH 2024"}
    for k in ["FONDS_1818", "ACCORD_APTBEF_FGBEF", "MORATOIRE_COVID_UIB", "BH_RETRAITEMENT_2024"]:
        d = evt[evt.id_evenement == k]
        A(f"<h4>{e(titres[k])}</h4>")
        A(table(["Banque", "Indicateur", "Montant cité (MDT)", "Description", "Source"],
                [[f"<b>{r.banque}</b>", f"<code>{r.indicateur}</code>",
                  fr(r.montant_mdt, 3), e(r.description), f"{e(r.fichier)} p.{r.page}"] for r in d.itertuples()]))

    # 6. Qualité ----------------------------------------------------------------------------
    A("<h2>6. Qualité des données</h2>")
    A("<h3>Statuts des versions</h3>")
    A(table(["statut_revision", "Lignes"],
            [[f"<code>{e(k[:60] + ('…' if len(k) > 60 else ''))}</code>", fr(n)] for k, n in sr.value_counts().items()], "num"))
    A("<h3>Révisions importantes (plus de 2&nbsp;% sur le cumul, totaux)</h3>")
    A(f"<p><code>docs/revisions_importantes.csv</code> ({len(ri)} révisions, produit par "
      f"<code>scripts/bilan_extraction.py</code>) ; {ri.mention_retraitement.notna().sum()} sont "
      "accompagnées d'une note de retraitement dans le document.</p>")
    yi = ri.periode.str[:4].value_counts().sort_index()
    ii = ri.indicateur.value_counts(); bi = ri.banque.value_counts()
    A('<div style="display:flex;gap:10pt">'
      + "<div style='flex:1'>" + table(["Indicateur", "Nb"], [[f"<code>{k}</code>", fr(n)] for k, n in ii.items()], "num") + "</div>"
      + "<div style='flex:1'>" + table(["Année", "Nb"], [[k, fr(n)] for k, n in yi.items()], "num") + "</div>"
      + "<div style='flex:1.4'>" + table(["Banque", "Nb", "Banque", "Nb"],
            [[a, fr(bi[a]), b, fr(bi[b])] for a, b in zip(bi.index[:6], bi.index[6:])], "num") + "</div></div>")
    top = ri.reindex(ri.ecart_pct.abs().sort_values(ascending=False).index).head(10)
    A("<p>Les dix plus fortes :</p>")
    A(table(["Banque", "Période", "Indicateur", "Publié", "Retenu", "Écart", "Document retenu"],
            [[r.banque, r.periode, f"<code>{r.indicateur}</code>", fr(r.publie_mdt, 3), fr(r.retenu_mdt, 3),
              f"{r.ecart_pct:+.1f}".replace(".", ",") + "&nbsp;%", e(r.fichier_retenu)] for r in top.itertuples()], "num"))
    A("<p>L'année 2020 concentre le plus de révisions (Covid : don au Fonds 1818, moratoire UIB), "
      "puis 2021 (accord salarial).</p>")

    A("<h3>Contrôle annuel</h3>")
    cs = ca.statut.value_counts()
    A(f"<p>Somme des 4 trimestres retenus contre cumul T4 retenu, pour le PNB, les produits, les "
      f"charges d'exploitation bancaire et les charges opératoires ({len(ca)} contrôles) : "
      + ", ".join(f"<code>{k}</code> {n}" for k, n in cs.items())
      + ". « En attente de révision » : le cumul retenu est le 31/12 provisoire alors que le T4 seul "
      "est encore initial (pas une erreur). « Rupture de série » : année avec une révision "
      "importante. Les écarts restants :</p>")
    ec = ca[ca.statut == "ecart"].copy()
    causes = pd.read_csv(R / "docs" / "ecarts_annuels.csv", sep=";", encoding="utf-8-sig")
    ec = ec.merge(causes[["banque", "annee", "code_indicateur", "categorie", "fichier", "page"]],
                  on=["banque", "annee", "code_indicateur"], how="left")
    A(table(["Banque", "Année", "Indicateur", "Somme des trimestres", "Cumul T4", "Écart (MDT)", "Cause", "Source"],
            [[r.banque, r.annee, f"<code>{r.code_indicateur}</code>", fr(r.somme_trimestres, 3), fr(r.cumul_T4, 3),
              f"{r.ecart:+.3f}".replace(".", ","), e(r.categorie if isinstance(r.categorie, str) else "à examiner"),
              e(f"{r.fichier} p.{r.page}" if isinstance(r.fichier, str) else "")] for r in ec.itertuples()], "num"))
    cat = causes.categorie.value_counts()
    A(f"<p>Ces {len(ec)} écarts (de {fr(ec.ecart.abs().min(),3)} à {fr(ec.ecart.abs().max(),3)} MDT) ont été "
      "examinés un par un (étape 4c, 22/10/2026) : "
      + ", ".join(f"{e(k)} {n}" for k, n in cat.items())
      + ". Aucune erreur d'extraction : les chiffres en cause figurent tels quels dans les PDF. Ce sont des "
      "chiffres des banques, gardés tels quels ; la cause détaillée de chacun est dans "
      "<code>docs/ecarts_annuels.csv</code>.</p>")

    A("<h3>Cas à vérifier et incohérences de la banque</h3>")
    av = ctl[ctl.statut.isin(["a verifier", "ecart composantes"])]
    expl = {("UBCI", "2025T3"): "colonne du trimestre : produits − charges ≠ PNB dans le PDF (vérifié sur l'image)",
            ("UIB", "2023T2"): "colonne T2 2022 = cumul du semestre (erreur de la banque, colonne non retenue)",
            ("BT", "2020T3"): "charges opératoires du trimestre 12 076 kDT pour des composantes de 15 702 + 7 724 (don au Fonds 1818 retiré)",
            ("BNA", "2023T2"): "charges opératoires 86 209 kDT pour des composantes de 69 096 + 17 219",
            ("UBCI", "2025T4"): "colonne T4 2024 : charges générales 58 743 &gt; charges opératoires 53 689"}
    A(table(["Banque", "Trimestre", "Statut", "Constat (vérifié dans le PDF)"],
            [[r.banque, r.trimestre, f"<code>{r.statut}</code>", expl.get((r.banque, r.trimestre), "")] for r in av.itertuples()]))
    A("<p>Aucun chiffre n'est corrigé : ces documents gardent leur statut et les valeurs publiées.</p>")

    A("<h3>Limites</h3><ul>"
      "<li>Indicateurs <b>provisoires et non audités</b>, publiés par les banques elles-mêmes.</li>"
      "<li>Retraitements fréquents : la somme des trimestres peut différer du cumul annuel ; les "
      "chiffres annuels viennent toujours du cumul publié.</li>"
      "<li>Les banques n'expliquent pas toujours leurs révisions (BH 2024 : aucun PDF n'explique le "
      "changement).</li>"
      "<li>Définitions des postes différentes d'une banque à l'autre (charges opératoires) ; Wifak "
      "comparée par équivalences.</li>"
      f"<li>{len(illis)} documents en image non saisis ; {int(nd.sum())} valeurs non disponibles ; "
      f"{len(sai)} valeurs saisies à la main, toutes tracées.</li>"
      f"<li>{len(autres)} documents introuvables hors {der} ("
      + ", ".join(f"{b} {t}" for b, t in autres[["banque", "trimestre"]].values) + ").</li>"
      "<li>Pas de résultat net dans les indicateurs trimestriels : ROE et ROA seulement semestriels "
      "et annuels (états financiers, pas encore collectés).</li>"
      "<li>Le contrôle par échantillon (<code>docs/validation.md</code>) reste à écrire ; les "
      f"{len(ref)} valeurs de référence en tiennent lieu pour l'instant.</li></ul>")

    # 7. Prochaines étapes ------------------------------------------------------------------
    A("<h2>7. Prochaines étapes</h2>")
    A(table(["#", "Étape", "État"], [
        ["1–2", "Collecte et extraction des indicateurs (12 gabarits)",
         "Fait jusqu'au " + (lambda t: f"T{t[-1]} {t[:4]}")(sorted(ok.trimestre)[-1])],
        ["3", "Validation manuelle d'un échantillon", f"{len(ref)} valeurs relevées ; <code>docs/validation.md</code> à écrire"],
        ["4b", "États financiers (résultat net, total actif, capitaux propres) pour ROE et ROA",
         "<b>Prochaine étape</b> : script écrit et testé sur un PDF simulé, jamais lancé sur le vrai site"],
        ["2", "T3 2026", "Après le 20/10/2026 : téléchargement, extraction, contrôles, tests"],
        ["4", "Cours boursiers 2019–2026 (BVMT ou ilboursa)", "À faire"],
        ["4c", f"Examiner les {len(ec)} écarts du contrôle annuel", "À faire, avant l'étape Power BI"],
        ["5–6", "Requêtes Power Query, modèle en étoile, mesures DAX", "À faire"],
        ["7", "Pages du rapport Power BI", "À faire"],
        ["8", "README final et captures pour le portfolio", "À faire"]]))
    A("<p>Étape 4b, dans l'ordre : test court sur une banque (BNA, exercice 2024 : adresses, "
      "téléchargement, extraction, comparaison à la main au PDF), corrections, extension banque par "
      "banque avec deux documents relevés à la main, lancement complet, puis comparaison du résultat "
      "net annuel avec ilboursa (écarts de plus de 1&nbsp;% signalés).</p>")

    vers_pdf(page_html("Rapport d'avancement", "".join(o)), R / "docs/Rapport_avancement.pdf",
             "Rapport d'avancement — Analyse du secteur bancaire tunisien", "Rapport d'avancement",
             f"Analyse du secteur bancaire tunisien — Rapport d'avancement ({DATE})")


if __name__ == "__main__":
    specification()
    rapport()
