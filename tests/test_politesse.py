# Auteur : Ahmed Ben Arfa
"""Lecture du robots.txt (collecte_banques.Politesse), sans réseau : délai et chemins interdits."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import collecte_banques as cb  # noqa: E402

# extraits réels (20/10/2026)
ROBOTS_BVMT = """#
# robots.txt
User-agent: *
Crawl-delay: 10
Allow: /misc/*.css$
Disallow: /misc/
Disallow: /?q=admin/
"""
ROBOTS_ILBOURSA = """﻿#robots.txt pour www.ilboursa.com

User-Agent: *
Disallow: /forums/post
Disallow: /docs/*

https://www.ilboursa.com/sitemap

# Majestic
User-agent: MJ12bot
Disallow: /

User-agent: BLEXBot
User-agent: AwarioRssBot
Disallow: /
"""


def politesse(hote: str, texte: str) -> cb.Politesse:
    p = cb.Politesse(session=None)
    delai, regles = cb.Politesse.lire(texte)
    p.sites[hote] = (max(cb.PAUSE, delai or 0), regles)
    return p


def test_bvmt():
    p = politesse("www.bvmt.com.tn", ROBOTS_BVMT)
    assert p.delai("https://www.bvmt.com.tn/x") == 10
    assert p.autorise("https://www.bvmt.com.tn/sites/default/files/bulletin/pdf/bull20251231.pdf")
    assert not p.autorise("https://www.bvmt.com.tn/misc/drupal.js")
    assert p.autorise("https://www.bvmt.com.tn/misc/style.css")          # Allow plus long
    assert not p.autorise("https://www.bvmt.com.tn/?q=admin/config")


def test_ilboursa():
    p = politesse("www.ilboursa.com", ROBOTS_ILBOURSA)
    assert p.delai("https://www.ilboursa.com/") == cb.PAUSE                # pas de Crawl-delay
    assert p.autorise("https://www.ilboursa.com/api/general/GetHistos")
    assert p.autorise("https://www.ilboursa.com/marches/societe/BIAT")     # « Disallow: / » = autres robots
    assert not p.autorise("https://www.ilboursa.com/docs/rapport.pdf")     # joker
    assert not p.autorise("https://www.ilboursa.com/forums/post?id=3")
