# Auteur : Ahmed Ben Arfa
"""Ajoute (ou remplace) une requête intermédiaire non chargée dans expressions.tmdl du projet Power BI :
description ///, code M de powerquery/<NOM>.pq indenté de 2 tabulations, lineageTag (gardé si la requête
existe), annotations ; place la requête dans l'ordre de Power Query (PBI_QueryOrder) après APRES.
Fins de ligne CRLF, comme Power BI.

À lancer seulement quand ce projet est fermé dans Power BI Desktop ; vérifier `git status` avant.

Utilisation : python scripts/ecrire_tmdl_expression.py NOM "description" APRES
  exemple : python scripts/ecrire_tmdl_expression.py Gabarits "Requête intermédiaire : gabarits" Controle_Annuel
Un paramètre (valeur avec `meta [IsParameterQuery = true]`) ou une fonction ne passent pas par cet outil :
voir `CheminDonnees` et `Actionnariat_A_La_Date` dans expressions.tmdl pour leur forme.
"""
import re, sys, uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ecrire_tmdl_table import DEF, R, NL


def ecrire_expression(nom, description, apres):
    f = DEF / "expressions.tmdl"
    t = f.read_bytes().decode("utf-8")
    assert t.count("\n") == t.count(NL), "expressions.tmdl n'est plus en CRLF"
    code = (R / "powerquery" / f"{nom}.pq").read_text(encoding="utf-8").rstrip("\n").split("\n")
    assert all(l.strip() for l in code), f"ligne vide dans {nom}.pq (interdite dans le TMDL)"
    ancien = re.search(rf"(///[^\r\n]*\r\n)?expression {nom} =\r\n.*?\r\n\tlineageTag: (\S+)\r\n.*?(?=\r\n///|\r\nexpression |\Z)",
                       t, re.S)
    tag = ancien.group(2) if ancien else str(uuid.uuid4())
    bloc = [f"/// {description}", f"expression {nom} =", *["\t\t" + l for l in code], f"\tlineageTag: {tag}", "",
            "\tannotation PBI_NavigationStepName = Navigation", "", "\tannotation PBI_ResultType = Table", ""]
    if ancien:
        t = t[:ancien.start()] + NL.join(bloc).rstrip(NL) + t[ancien.end():]
    else:
        t = t.rstrip(NL) + NL + NL + NL.join(bloc)
    f.write_bytes(t.encode("utf-8"))
    m = (DEF / "model.tmdl").read_bytes().decode("utf-8")
    ordre = re.search(r"annotation PBI_QueryOrder = \[(.*?)\]", m)
    noms = re.findall(r'"([^"]+)"', ordre.group(1))
    if nom not in noms:
        noms.insert(noms.index(apres) + 1, nom)
        m = m.replace(ordre.group(0), "annotation PBI_QueryOrder = [" + ",".join(f'"{n}"' for n in noms) + "]")
        (DEF / "model.tmdl").write_bytes(m.encode("utf-8"))
    print(nom, "écrite (requête intermédiaire) ; ordre :", noms)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    ecrire_expression(*sys.argv[1:])
