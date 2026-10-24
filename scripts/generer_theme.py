# Auteur : Ahmed Ben Arfa
"""Thème et fonds de page du rapport Power BI (étape 7) : couleurs d'un rapport bancaire (bleu marine,
or, sarcelle), fonds de page 16:9 avec bandeau de titre et signature, icônes des banques (pastilles au
code de la banque, sans logo officiel).

Sorties dans powerbi/theme/ :
- secteur_bancaire.json : thème à importer (Affichage › Thèmes › Parcourir les thèmes) ;
- fond_page.png : bandeau de titre en haut, pied de page signé ; fond_page_filtres.png : même fond avec
  une bande claire sous le titre pour les segments (banques, Play Axis) ;
- icones_banques.png : aperçu des pastilles au code de chaque banque, solution de secours si un logo
  officiel (donnees_reference/logos/, colonne icone de Dim_Banque) devait être retiré.

Utilisation : python scripts/generer_theme.py
"""
import json
from pathlib import Path

import fitz
from PIL import Image
from PIL.PngImagePlugin import PngInfo

R = Path(__file__).resolve().parent.parent
SORTIE = R / "powerbi" / "theme"
AUTEUR = "Ahmed Ben Arfa"

MARINE, BLEU, SARCELLE, OR = "#0B2545", "#134074", "#1B998B", "#C9A227"
FOND, CONTOUR, TEXTE, TEXTE_DOUX = "#F4F6FA", "#D9E1EC", "#1F2A3C", "#5B6B82"
BON, NEUTRE, MAUVAIS = "#2E7D32", "#8DA9C4", "#C62828"   # BON et MAUVAIS = mesure Couleur coef
# couleurs assez foncées pour un texte blanc (pastilles) et distinctes sur un graphique à 12 banques
COULEURS = [BLEU, "#B5891C", "#178A7E", "#2F5D8A", "#C0583F", "#5E548E", "#3A7CA5", "#4F7942",
            "#9E3F5C", "#8A6D3B", "#6D597A", "#2E8B9A"]
# une couleur par banque (ordre alphabétique des codes), reprise dans les pastilles et les visuels
COULEURS_BANQUES = dict(zip(["AB", "ATB", "BH", "BIAT", "BNA", "BT", "BTE", "STB", "TJARI", "UBCI", "UIB", "WIB"],
                            COULEURS))


def theme():
    plein = lambda c: {"solid": {"color": c}}
    return {
        "name": "Secteur bancaire tunisien",
        "dataColors": COULEURS,
        "foreground": TEXTE, "foregroundNeutralSecondary": TEXTE_DOUX, "background": "#FFFFFF",
        "backgroundLight": FOND, "tableAccent": BLEU,
        "good": BON, "neutral": NEUTRE, "bad": MAUVAIS,
        "maximum": BLEU, "center": "#DCE6F2", "minimum": "#FFFFFF",
        "textClasses": {
            "callout": {"fontFace": "Segoe UI Semibold", "fontSize": 26, "color": MARINE},
            "title": {"fontFace": "Segoe UI Semibold", "fontSize": 12, "color": MARINE},
            "header": {"fontFace": "Segoe UI Semibold", "fontSize": 11, "color": MARINE},
            "label": {"fontFace": "Segoe UI", "fontSize": 10, "color": TEXTE},
        },
        "visualStyles": {
            "*": {"*": {
                "background": [{"show": True, "color": plein("#FFFFFF"), "transparency": 0}],
                "border": [{"show": True, "color": plein(CONTOUR), "radius": 8}],
                "dropShadow": [{"show": False}],
                "title": [{"show": True, "fontColor": plein(MARINE), "fontSize": 11,
                           "fontFamily": "Segoe UI Semibold", "alignment": "left"}],
                "visualHeader": [{"foreground": plein(TEXTE_DOUX), "border": plein(CONTOUR),
                                  "background": plein("#FFFFFF")}],
            }},
            "page": {"*": {
                "background": [{"color": plein(FOND), "transparency": 0}],
                "outspace": [{"color": plein("#E9EEF5"), "transparency": 0}],
            }},
            "tableEx": {"*": {
                "columnHeaders": [{"fontColor": plein("#FFFFFF"), "backColor": plein(BLEU), "fontFamily": "Segoe UI Semibold"}],
                "values": [{"fontColorPrimary": plein(TEXTE), "backColorPrimary": plein("#FFFFFF"),
                            "fontColorSecondary": plein(TEXTE), "backColorSecondary": plein(FOND)}],
                "grid": [{"gridHorizontalColor": plein(CONTOUR), "gridVerticalColor": plein(CONTOUR)}],
            }},
            "pivotTable": {"*": {
                "columnHeaders": [{"fontColor": plein("#FFFFFF"), "backColor": plein(BLEU), "fontFamily": "Segoe UI Semibold"}],
                "rowHeaders": [{"fontColor": plein(MARINE)}],
            }},
            "card": {"*": {
                "labels": [{"color": plein(MARINE), "fontSize": 26, "fontFamily": "Segoe UI Semibold"}],
                "categoryLabels": [{"color": plein(TEXTE_DOUX), "fontSize": 10}],
            }},
            "slicer": {"*": {
                "header": [{"fontColor": plein(MARINE), "fontFamily": "Segoe UI Semibold"}],
                "items": [{"fontColor": plein(TEXTE)}],
            }},
        },
    }


def melange(c1, c2, part):
    """Couleur pleine c1 recouverte de c2 à part % (le rendu SVG utilisé ignore transparence et dégradés)."""
    a, b = (tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in (c1, c2))
    return "#" + "".join(f"{round(x + (y - x) * part):02X}" for x, y in zip(a, b))


def fond(bande_filtres):
    """Fond 1280 × 720 (format 16:9 de Power BI) en SVG : bandeau marine (dégradé en 64 bandes) avec filet
    or, motif de colonnes (façade de banque) et courbe montante discrets à droite, pied de page signé."""
    degrade = "".join(f'<rect x="{i * 20}" width="21" height="70" fill="{melange(MARINE, BLEU, i / 63)}"/>'
                      for i in range(64))
    motif = melange(BLEU, "#FFFFFF", 0.12)
    colonnes = "".join(
        f'<rect x="{1010 + i * 34}" y="{16 + (5 - i) * 2}" width="14" height="{40 - (5 - i) * 2}" fill="{motif}"/>'
        for i in range(7))
    filtres = (f'<rect x="16" y="86" width="1248" height="64" rx="8" fill="#FFFFFF" stroke="{CONTOUR}"/>'
               if bande_filtres else "")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
<rect width="1280" height="720" fill="{FOND}"/>
{degrade}
<rect y="70" width="1280" height="3" fill="{OR}"/>
<polygon points="1000,14 1124,4 1248,14" fill="{motif}"/>
{colonnes}
<rect x="1000" y="58" width="248" height="4" fill="{motif}"/>
<polyline points="760,58 820,50 870,54 930,38 980,30" fill="none" stroke="{melange(BLEU, OR, 0.6)}" stroke-width="2"/>
{filtres}
<rect y="694" width="1280" height="26" fill="#E9EEF5"/>
<rect y="694" width="1280" height="1" fill="{CONTOUR}"/>
<text x="20" y="711" font-family="Helvetica" font-size="10" fill="{TEXTE_DOUX}">{AUTEUR}  ·  Analyse du secteur bancaire tunisien</text>
<text x="1260" y="711" font-family="Helvetica" font-size="10" fill="{TEXTE_DOUX}" text-anchor="end">Sources : indicateurs trimestriels (CMF, BVMT), états financiers individuels, cours de la Bourse de Tunis</text>
</svg>"""


def pastille(code, couleur, taille=96):
    """Pastille ronde au code de la banque (même dessin que la colonne icone de Dim_Banque)."""
    police = 30 if len(code) <= 3 else (24 if len(code) == 4 else 19)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{taille}" height="{taille}" viewBox="0 0 96 96">'
            f'<circle cx="48" cy="48" r="46" fill="{couleur}"/><circle cx="48" cy="48" r="40" fill="none" '
            f'stroke="{melange(couleur, "#FFFFFF", 0.5)}" stroke-width="2"/><text x="48" y="{48 + police * 0.36:.0f}" '
            f'font-family="Helvetica" font-weight="bold" font-size="{police}" fill="#FFFFFF" text-anchor="middle">'
            f'{code}</text></svg>')


def png(svg, chemin, echelle):
    doc = fitz.open(stream=svg.encode("utf-8"), filetype="svg")
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(echelle, echelle), alpha=False)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    infos = PngInfo()
    infos.add_text("Author", AUTEUR)
    infos.add_text("Title", "Rapport Power BI — Analyse du secteur bancaire tunisien")
    image.save(chemin, pnginfo=infos)
    print(chemin.relative_to(R), f"{pix.width} × {pix.height}")


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    (SORTIE / "secteur_bancaire.json").write_text(json.dumps(theme(), indent=2, ensure_ascii=False) + "\n",
                                                  encoding="utf-8")
    print("powerbi/theme/secteur_bancaire.json")
    png(fond(False), SORTIE / "fond_page.png", 1.5)            # 1920 × 1080
    png(fond(True), SORTIE / "fond_page_filtres.png", 1.5)
    planche = "".join(f'<g transform="translate({20 + i * 106},20)">{pastille(c, coul)}</g>'
                      for i, (c, coul) in enumerate(COULEURS_BANQUES.items()))
    png(f'<svg xmlns="http://www.w3.org/2000/svg" width="1292" height="136" viewBox="0 0 1292 136">'
        f'<rect width="1292" height="136" fill="{FOND}"/>{planche}</svg>', SORTIE / "icones_banques.png", 1)


if __name__ == "__main__":
    main()
