# Auteur : Ahmed Ben Arfa
"""Utilisation : python scripts/audit_publication.py
Audit avant chaque push (le dépôt est public), en lecture seule :
  1. aucun fichier suivi ne correspond à une exclusion (.gitignore, .git/info/exclude) : données
     locales et fichiers de travail jamais publiés ;
  2. chaque fichier de tout l'historique git, de l'index et des fichiers nouveaux non ignorés
     (texte, texte et métadonnées des PDF, XML des fichiers xlsx/zip) est cherché pour des noms
     interdits, des secrets (jetons, clés, mots de passe) et des chemins personnels ;
  3. messages, auteurs et committeurs de tous les commits : noms interdits, lignes « Co-Authored-By »,
     liste des adresses e-mail.
Les noms interdits sont lus dans .git/info/noms_interdits (un par ligne, fichier local jamais publié,
pour qu'ils n'apparaissent pas dans ce script). Les e-mails et numéros de téléphone trouvés sont
listés pour examen sans faire échouer l'audit. Code de sortie 1 si un problème bloquant est trouvé.
"""
import collections, io, os, re, subprocess, sys, zipfile
from pathlib import Path
import fitz

RACINE = Path(__file__).resolve().parent.parent
TEMOIN = "Ahmed Ben Arfa"   # en-tête de chaque script : prouve que le contenu est bien lu


def git(*args, entree=None):
    return subprocess.run(["git", "-C", str(RACINE), *args], input=entree, capture_output=True, check=True).stdout


def noms_interdits():
    chemin = Path(git("rev-parse", "--git-common-dir").decode().strip())
    chemin = (chemin if chemin.is_absolute() else RACINE / chemin) / "info" / "noms_interdits"
    if not chemin.exists():
        sys.exit(f"{chemin} manquant : y écrire les noms interdits, un par ligne")
    noms = [l.strip() for l in chemin.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    if not noms:
        sys.exit(f"{chemin} ne contient aucun nom")
    return re.compile("|".join(re.escape(n) for n in noms), re.I)


def motifs():
    perso = [r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"'<>]+", r"AppData[\\/]"]
    perso += [re.escape(os.environ[v]) for v in ("USERNAME", "COMPUTERNAME") if len(os.environ.get(v, "")) > 3]
    bloquants = {
        "nom interdit": noms_interdits(),
        "jeton GitHub": re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"),
        "clé AWS": re.compile(r"AKIA[0-9A-Z]{16}"),
        "clé privée": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        "mot de passe ou clé": re.compile(
            r"(?i)(api[_-]?key|secret|password|passwd|mot de passe|token)\s*[:=]\s*['\"][^'\"]{8,}"),
        "jeton Bearer": re.compile(r"(?i)bearer\s+[a-z0-9._-]{20,}"),
        "chemin personnel": re.compile("|".join(perso), re.I),
    }
    a_examiner = {
        "e-mail": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}"),
        "téléphone tunisien": re.compile(r"\+216[\s\d]{8,}"),
    }
    return bloquants, a_examiner


def textes(data):
    """Texte cherchable d'un fichier : brut ; pour un PDF, texte et métadonnées en plus ; XML d'un zip."""
    if data[:5] == b"%PDF-":
        try:
            d = fitz.open(stream=data, filetype="pdf")
            yield "".join(p.get_text() for p in d) + str(d.metadata)
        except Exception as e:
            yield f"PDF illisible : {e}"
        yield data.decode("latin-1")
    elif data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            yield "".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist())
    else:
        yield data.decode("utf-8", "ignore")


def fichiers():
    """(identifiant, chemins) : historique complet, index, puis fichiers nouveaux non ignorés."""
    blobs = collections.defaultdict(set)
    objets = [l.partition(" ") for l in git("rev-list", "--all", "--objects").decode("utf-8").splitlines()]
    types = git("cat-file", "--batch-check=%(objecttype)", entree="\n".join(o[0] for o in objets).encode()).split()
    for (sha, _, chemin), t in zip(objets, types):
        if t == b"blob" and chemin:
            blobs[sha].add(chemin)
    for l in git("ls-files", "-s").decode("utf-8").splitlines():
        info, chemin = l.split("\t", 1)
        blobs[info.split()[1]].add(chemin)
    for sha, chemins in blobs.items():
        yield chemins, lambda sha=sha: git("cat-file", "blob", sha)
    for chemin in git("ls-files", "-o", "--exclude-standard").decode("utf-8").splitlines():
        yield {chemin + " (nouveau)"}, lambda chemin=chemin: (RACINE / chemin).read_bytes()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    bloquants, a_examiner = motifs()
    problemes = []

    # 1. fichiers suivis qui devraient être exclus
    suivis_exclus = git("ls-files", "-ci", "--exclude-standard").decode("utf-8").split()
    problemes += [f"fichier suivi alors qu'il est exclu : {c}" for c in suivis_exclus]
    print(f"1. Fichiers suivis : {len(git('ls-files').split())}, dont exclus par .gitignore ou "
          f".git/info/exclude : {len(suivis_exclus)}")

    # 2. contenu de chaque fichier, et chemins
    trouve, n, temoin = collections.defaultdict(set), 0, 0
    for chemins, lire in fichiers():
        n += 1
        nom = sorted(chemins)[0]
        for t in [*textes(lire()), "\n".join(chemins)]:
            temoin += TEMOIN in t
            for genre, groupe in (("bloquant", bloquants), ("à examiner", a_examiner)):
                for cle, m in groupe.items():
                    for x in set(m.findall(t)):
                        trouve[(genre, cle, (x if isinstance(x, str) else x[0])[:80])].add(nom)
    print(f"2. Contenus lus : {n} (historique, index, nouveaux fichiers) ; témoin « {TEMOIN} » trouvé "
          f"{temoin} fois")
    if n and not temoin:
        problemes.append("témoin introuvable : la lecture des fichiers ne fonctionne pas")

    # 3. commits
    journal = git("log", "--all", "--format=%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%B%x1e").decode("utf-8")
    commits = [c.strip("\n").split("\x1f") for c in journal.split("\x1e") if c.strip()]
    emails = collections.Counter()
    for sha, an, ae, cn, ce, msg in commits:
        emails[ae] += 1
        if ce != ae:
            emails[ce] += 1
        texte = "\n".join((an, ae, cn, ce, msg))
        for x in set(bloquants["nom interdit"].findall(texte)):
            trouve[("bloquant", "nom interdit (commit)", x)].add(sha[:7])
        if re.search(r"(?im)^co-authored-by:", msg):
            trouve[("bloquant", "Co-Authored-By", "")].add(sha[:7])
    print(f"3. Commits : {len(commits)} ; adresses e-mail des auteurs et committeurs :")
    for e, k in emails.most_common():
        print(f"     {e} ({k})")

    print()
    for (genre, cle, x), noms in sorted(trouve.items()):
        print(f"{genre:10} | {cle:22} | {x!r:50} | {len(noms)} : {', '.join(sorted(noms)[:4])}")
        if genre == "bloquant":
            problemes.append(f"{cle} : {x!r}")
    if problemes:
        print(f"\nAUDIT EN ÉCHEC : {len(problemes)} problème(s)")
        sys.exit(1)
    print("\nAudit réussi : aucun problème bloquant.")


if __name__ == "__main__":
    main()
