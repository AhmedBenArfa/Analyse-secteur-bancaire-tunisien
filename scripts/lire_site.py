# Auteur : Ahmed Ben Arfa
"""Utilisation : python scripts/lire_site.py DOSSIER URL [URL ...]
Lecture polie de quelques pages d'un site (recherche d'un document sur le site d'une banque ou de la
Bourse) : client commun de collecte_banques.py (robots.txt lu, chemins interdits respectés, délai du
robots.txt), au moins 2 secondes entre deux requêtes, une requête à la fois. Chaque réponse est
enregistrée dans DOSSIER (.html ou .pdf) pour être lue ensuite sans refaire de requête."""
import re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import collecte_banques as cb

if len(sys.argv) < 3:
    sys.exit(__doc__)
cb.PAUSE = max(cb.PAUSE, 2)
c = cb.Client()
dossier = Path(sys.argv[1])
dossier.mkdir(parents=True, exist_ok=True)
for u in sys.argv[2:]:
    try:
        r = c.get(u, allow_redirects=True)
    except Exception as e:
        print(u, "ERREUR", e)
        continue
    if r is None:   # chemin interdit par le robots.txt
        continue
    print(u, r.status_code, r.headers.get("content-type"), len(r.content), "->", r.url, "| délai", c.politesse.delai(u))
    nom = re.sub(r"[^a-zA-Z0-9]+", "_", u.split("//", 1)[1])[-90:]
    ext = ".pdf" if r.content[:5] == b"%PDF-" else ".html"
    (dossier / f"{nom}{ext}").write_bytes(r.content)
