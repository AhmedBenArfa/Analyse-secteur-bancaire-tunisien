"""Utilisation : python scripts/diagnostic_pdf.py donnees/pdf/BT/BT_2024T2.pdf [autres PDF...]
Diagnostic de mise en page d'un PDF d'indicateurs (lecture seule) :
colonnes détectées, texte de l'en-tête par colonne, unité annoncée, lignes reconnues ou non."""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pdfplumber  # noqa: E402
import collecte_banques as cb  # noqa: E402

for chemin in sys.argv[1:]:
    p = Path(chemin)
    tri = p.stem.split("_")[1]
    t = cb.Trimestre.depuis_texte(tri)
    print(f"\n######## {p.name}")
    with pdfplumber.open(p) as pdf:
        n_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages[:3], start=1):
            ap = cb.analyser_page(page, i)
            texte = page.extract_text() or ""
            tab = [l for l in ap.lignes if sum(j.colonne is not None for j in l.nombres) >= 2]
            if not tab:
                continue
            unite = re.findall(r"(?i)(en\s+(?:milliers?\s+de\s+)?dinars|en\s+mille\s+dinars|milliers?\s+de\s+dinars|"
                               r"millions?\s+de\s+dinars|en\s+MD\b|en\s+mDT|en\s+KDT|en\s+DT\b|MTND|\(en[^)]{0,30}\))", texte)
            print(f"page {i}/{n_pages} : {len(ap.bords)} colonnes, bords {[round(b) for b in ap.bords]} ; unité annoncée : {unite[:3]}")
            haut = min(l.top for l in tab)
            # texte d'en-tête par colonne (même découpage que colonnes_entete, sans classement)
            gauche = ap.bords[0] - 1.5 * (ap.bords[1] - ap.bords[0]) if len(ap.bords) > 1 else 0
            textes = [[] for _ in ap.bords]
            for m in sorted(ap.mots, key=lambda m: (round(m["top"]), m["x0"])):
                if haut - 65 <= m["top"] < haut - 1:
                    c = (m["x0"] + m["x1"]) / 2
                    if c < gauche:
                        continue
                    k = next((j for j, b in enumerate(ap.bords) if c <= b + 6), None)
                    if k is not None:
                        textes[k].append(m["text"])
            for k, x in enumerate(textes):
                print(f"   col {k} : {' '.join(x)[:70]!r} -> {cb.type_colonne(' '.join(x), t)}")
            print("   lu par le script :", cb.colonnes_entete(ap, haut, t))
            for l in tab:
                code = cb.code_libelle(l.libelle)
                vals = " | ".join(f"{j.colonne}:{j.texte}" for j in l.nombres)
                print(f"   {code or '?':<12} {l.libelle[:55]:<55} {vals}")
            break
