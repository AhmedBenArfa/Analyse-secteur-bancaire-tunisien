# Auteur : Ahmed Ben Arfa
"""Page « Rentabilité » : les deux tables calculées par jointure (dax/Rentabilite_Efficacite.dax,
NATURALINNERJOIN, et dax/Rentabilite_Trimestres.dax, NATURALLEFTOUTERJOIN) refaites depuis les données publiées
(même calcul que les mesures ROE et ROA, spécification 7.7) : nombre de lignes de chaque jointure et ROE de contrôle
déjà vérifiés dans Power BI (guide 3.7)."""
from pathlib import Path

import pandas as pd

D = Path(__file__).resolve().parent.parent / "donnees_publiees"


def tables():
    ef = pd.read_csv(D / "etats_financiers_versions.csv", sep=";", encoding="utf-8-sig", parse_dates=["date_arrete"])
    ef = ef[ef.version == ef.source_valeur]
    p = ef.pivot_table(index=["banque", "date_arrete"], columns="code", values="valeur_retenue").reset_index()
    p["ouv"] = p.date_arrete.apply(lambda d: pd.Timestamp(d.year - 1, 12, 31))
    o = p[["banque", "date_arrete", "CAP_PROPRES_EF", "TOTAL_ACTIF"]].rename(
        columns={"date_arrete": "ouv", "CAP_PROPRES_EF": "cp_ouv", "TOTAL_ACTIF": "ta_ouv"})
    p = p.merge(o, on=["banque", "ouv"], how="left")
    p["rn"] = p.RES_NET * p.date_arrete.dt.month.map({6: 2, 12: 1})
    p["cp_moy"] = (p.CAP_PROPRES_EF + p.cp_ouv) / 2
    p["ROE"] = p.rn / p.cp_moy
    v = pd.read_csv(D / "indicateurs_versions.csv", sep=";", encoding="utf-8-sig", parse_dates=["date_arrete"])
    v = v[(v.version == v.source_valeur) & (v.mesure == "cumul")
          & v.code_indicateur.isin(["PNB", "FRAIS_PERS", "CHG_GEN"])]
    c = v.pivot_table(index=["banque", "date_arrete"], columns="code_indicateur", values="valeur_retenue").reset_index()
    c["Coef_Cumul"] = (c.FRAIS_PERS + c.CHG_GEN) / c.PNB
    interne = p[["banque", "date_arrete", "ROE", "rn", "cp_moy"]].merge(
        c[["banque", "date_arrete", "Coef_Cumul"]], on=["banque", "date_arrete"], how="inner")
    externe = c[["banque", "date_arrete", "Coef_Cumul"]].merge(
        interne[["banque", "date_arrete", "ROE"]], on=["banque", "date_arrete"], how="left")
    return interne, externe


def test_jointures_rentabilite():
    """Interne : 12 banques × 14 arrêtés = 168 lignes, ROE vide au 31/12/2019 seulement (pas d'ouverture 2018) ;
    externe gauche : 12 banques × 28 trimestres = 336 lignes, ROE seulement aux 30/06 et 31/12. Contrôles : ROE des
    12 banques 11,85 % en 2024 et 12,46 % au S1 2026, BIAT 2024 16,61 % ; BIAT S1 2026 : ROE 22,79 %, coefficient
    cumulé 43,13 %."""
    interne, externe = tables()
    assert len(interne) == 168 and interne.ROE.notna().sum() == 156
    assert set(interne[interne.ROE.isna()].date_arrete.dt.strftime("%Y-%m-%d")) == {"2019-12-31"}
    assert len(externe) == 336
    assert set(externe[externe.ROE.notna()].date_arrete.dt.month) == {6, 12}
    for jour, attendu in (("2024-12-31", 11.85), ("2026-06-30", 12.46)):
        x = interne[interne.date_arrete == jour]
        assert round(x.rn.sum() / x.cp_moy.sum() * 100, 2) == attendu
    biat = interne[interne.banque == "BIAT"].set_index("date_arrete")
    assert round(biat.loc["2024-12-31", "ROE"] * 100, 2) == 16.61
    assert round(biat.loc["2026-06-30", "ROE"] * 100, 2) == 22.79
    assert round(biat.loc["2026-06-30", "Coef_Cumul"] * 100, 2) == 43.13
