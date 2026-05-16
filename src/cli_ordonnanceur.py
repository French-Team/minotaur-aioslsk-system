"""
CLI pour afficher un apercu des operations de l'Ordonnanceur dans la console.

Usage :
    python -m src.cli_ordonnanceur DOSSIER [options]

Exemples :
    python -m src.cli_ordonnanceur ~/Musique
    python -m src.cli_ordonnanceur ~/Musique --ops renommage classement
    python -m src.cli_ordonnanceur ~/Musique --no-resoudre-conflits
    python -m src.cli_ordonnanceur ~/Musique --ops dedoublonner --ops nettoyage
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from src.services.ordonnanceur_service import OrdonnanceurService


# -- Style helpers ----------------------------------------------------------

class Style:
    """Codes ANSI pour le terminal -- desactives si non supporte."""
    _support = sys.stdout.isatty()

    BOLD = f"\033[1m" if _support else ""
    DIM = f"\033[2m" if _support else ""
    GREEN = f"\033[32m" if _support else ""
    YELLOW = f"\033[33m" if _support else ""
    BLUE = f"\033[34m" if _support else ""
    MAGENTA = f"\033[35m" if _support else ""
    CYAN = f"\033[36m" if _support else ""
    RED = f"\033[31m" if _support else ""
    RESET = f"\033[0m" if _support else ""


SEP = "-" * 54
HEADER = "=" * 54


# -- Affichage --------------------------------------------------------------

def _titre(txt: str) -> None:
    """Affiche un titre de section."""
    print()
    print(f"{Style.BOLD}{Style.CYAN}{HEADER}{Style.RESET}")
    print(f"{Style.BOLD}{Style.CYAN}  {txt}{Style.RESET}")
    print(f"{Style.BOLD}{Style.CYAN}{SEP}{Style.RESET}")


def _sous_titre(txt: str, info: str = "") -> None:
    """Affiche un sous-titre avec compteur optionnel."""
    ligne = f"  {Style.BOLD}{txt}{Style.RESET}"
    if info:
        ligne += f"  {Style.DIM}({info}){Style.RESET}"
    print(ligne)
    print(f"  {SEP}")


def _item(txt: str, suffix: str = "") -> None:
    """Affiche une ligne d'item."""
    ligne = f"  {txt}"
    if suffix:
        ligne += f"  {Style.DIM}{suffix}{Style.RESET}"
    print(ligne)


def _ok(msg: str) -> None:
    """Message de succes."""
    print(f"  [{Style.GREEN}OK{Style.RESET}] {Style.DIM}{msg}{Style.RESET}")


def _warning(msg: str) -> None:
    """Message d'avertissement."""
    print(f"  [{Style.YELLOW}!!{Style.RESET}] {Style.DIM}{msg}{Style.RESET}")


def _info(msg: str) -> None:
    """Message d'information."""
    print(f"  [{Style.BLUE}i{Style.RESET}] {Style.DIM}{msg}{Style.RESET}")


def _afficher_renommage(renommage: dict[str, Any]) -> None:
    """Affiche la section renommage."""
    fichiers = renommage.get("fichiers", [])
    total = renommage.get("total", len(fichiers))
    _sous_titre("Renommage", f"{total} fichier{'s' if total != 1 else ''}")

    if not fichiers:
        _info("Aucun fichier a renommer.")
        return

    for i, f in enumerate(fichiers):
        mark = "+--" if i < len(fichiers) - 1 else "\\\\--"
        nom_actuel = f.get("nom_actuel", "?")
        nouveau_nom = f.get("nouveau_nom", "?")
        _item(f"{mark} {Style.DIM}{nom_actuel}{Style.RESET} -> {Style.BOLD}{nouveau_nom}{Style.RESET}")

    conflits_resolus = renommage.get("conflits_resolus", [])
    conflits = renommage.get("conflits", [])
    if conflits_resolus:
        _ok(f"Conflits resolus : {len(conflits_resolus)}")
    if conflits:
        _warning(f"Conflits non resolus : {len(conflits)}")


def _afficher_classement(classement: dict[str, Any]) -> None:
    """Affiche la section classement."""
    fichiers = classement.get("fichiers", [])
    total = classement.get("total", len(fichiers))
    nb_artistes = classement.get("nb_artistes", 0)
    _sous_titre("Classement", f"{total} fichier{'s' if total != 1 else ''}, {nb_artistes} artiste{'s' if nb_artistes != 1 else ''}")

    if not fichiers:
        _info("Aucun fichier a classer.")
        return

    artiste_courant = None
    for i, f in enumerate(fichiers):
        mark = "+--" if i < len(fichiers) - 1 else "\\--"
        artiste = f.get("artiste", "")
        chemin_actuel = f.get("chemin_actuel", "?")
        nouveau_chemin = f.get("nouveau_chemin", "")
        # Afficher le nom d'artiste comme en-tete (une seule fois)
        if artiste and artiste != artiste_courant:
            artiste_courant = artiste
            _item(f"{mark} {Style.MAGENTA}[{artiste}]{Style.RESET}")
            continue
        if artiste:
            _item(f"     {mark} {Style.DIM}{Path(chemin_actuel).name}{Style.RESET} -> {Style.BOLD}{nouveau_chemin}{Style.RESET}")
        else:
            _item(f"{mark} {Style.DIM}{Path(chemin_actuel).name}{Style.RESET} -> {Style.BOLD}{nouveau_chemin}{Style.RESET}")

    conflits_resolus = classement.get("conflits_resolus", [])
    conflits = classement.get("conflits", [])
    if conflits_resolus:
        _ok(f"Conflits resolus : {len(conflits_resolus)}")
    if conflits:
        _warning(f"Conflits non resolus : {len(conflits)}")


def _afficher_deduplication(dedup: dict[str, Any]) -> None:
    """Affiche la section dedoublonnage."""
    groupes = dedup.get("groupes", [])
    total_doublons = dedup.get("total_doublons", 0)
    total_economise = dedup.get("total_lisible", "0 o")
    nb_groupes = dedup.get("nb_groupes", 0)
    _sous_titre("Dedoublonnage", f"{total_doublons} fichier{'s' if total_doublons != 1 else ''} a supprimer ({total_economise} economies)")

    if not groupes:
        _info("Aucun doublon detecte.")
        return

    for i, g in enumerate(groupes):
        mark = "+--" if i < nb_groupes - 1 else "\\\\--"
        garde = g.get("garde")
        supprimables = g.get("supprimables", [])
        garde_nouveau = g.get("garde_nouveau_nom")
        nom_garde = garde_nouveau or (garde.filename if garde else "?")

        _item(f"{mark} Garde : {Style.BOLD}{nom_garde}{Style.RESET}")
        for j, s in enumerate(supprimables):
            sub_mark = "|  +--" if j < len(supprimables) - 1 else "|  \\\\--"
            taille = _taille_lisible(s.size)
            _item(f"   {sub_mark} {Style.RED}{s.filename}{Style.RESET}  ({taille})")

    conflits_resolus = dedup.get("conflits_resolus", [])
    conflits = dedup.get("conflits", [])
    if conflits_resolus:
        resolus = conflits_resolus[0]
        res = resolus.get("resolutions", [])
        renommes = [r for r in res if r.get("nouveau_nom") != r.get("nom_original")]
        if renommes:
            _ok(f"Conflits gardes resolus : {len(renommes)} renommage{'s' if len(renommes) != 1 else ''}")
    if conflits:
        _warning(f"Conflits non resolus : {len(conflits)}")


def _afficher_nettoyage(nettoyage: dict[str, Any]) -> None:
    """Affiche la section nettoyage."""
    fichiers = nettoyage.get("fichiers", [])
    total = nettoyage.get("total", 0)
    total_lisible = nettoyage.get("total_lisible", "0 o")
    _sous_titre("Nettoyage", f"{total} fichier{'s' if total != 1 else ''} ({total_lisible})")

    if not fichiers:
        _info("Aucun fichier temporaire a nettoyer.")
        return

    for i, f in enumerate(fichiers):
        mark = "+--" if i < len(fichiers) - 1 else "\\\\--"
        chemin = f.get("path", "?")
        taille = _taille_lisible(f.get("size", 0))
        _item(f"{mark} {Style.DIM}{Path(str(chemin)).name}{Style.RESET}  ({taille})")


def _taille_lisible(octets: int) -> str:
    """Formate une taille en octets en chaine lisible."""
    if octets < 1024:
        return f"{octets} o"
    elif octets < 1024 ** 2:
        return f"{octets / 1024:.1f} Ko"
    elif octets < 1024 ** 3:
        return f"{octets / 1024 ** 2:.1f} Mo"
    else:
        return f"{octets / 1024 ** 3:.2f} Go"


# -- Fonction principale d'affichage ----------------------------------------

def afficher_apercu_console(
    apercu: dict[str, Any],
    chemin_dossier: str | Path = "",
) -> None:
    """Affiche un apercu complet formate dans la console.

    Args:
        apercu: Dict retourne par OrdonnanceurService.generer_apercu().
        chemin_dossier: Chemin du dossier analyse (affiche en entete).
    """
    _titre("APERCU DES OPERATIONS")
    if chemin_dossier:
        _item(f"Dossier : {Style.BOLD}{chemin_dossier}{Style.RESET}")

    resume = apercu.get("resume", {})
    total_fichiers = resume.get("total_fichiers_confernes", 0)
    total_taille = resume.get("total_taille_lisible", "0 o")

    # Operations dans l'ordre
    for section in ("renommage", "classement", "deduplication", "nettoyage"):
        data = apercu.get(section)
        if data is not None:
            if section == "renommage":
                _afficher_renommage(data)
            elif section == "classement":
                _afficher_classement(data)
            elif section == "deduplication":
                _afficher_deduplication(data)
            elif section == "nettoyage":
                _afficher_nettoyage(data)

    # Resume final
    print()
    print(f"{Style.BOLD}{Style.CYAN}{SEP}{Style.RESET}")
    print(f"{Style.BOLD}{Style.GREEN}  RESUME : {total_fichiers} fichier{'s' if total_fichiers != 1 else ''} concerne{'s' if total_fichiers != 1 else ''}  |  {total_taille} economise{'s' if total_taille != '0 o' else ''}{Style.RESET}")
    print(f"{Style.BOLD}{Style.CYAN}{HEADER}{Style.RESET}")
    print()


# -- CLI --------------------------------------------------------------------

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ordonnanceur-preview",
        description="Affiche un apercu des operations de l'Ordonnanceur (renommage, classement, dedoublonnage, nettoyage).",
        epilog="Exemple : python -m src.cli_ordonnanceur ~/Musique --ops renommage classement",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "dossier",
        type=str,
        help="Chemin du dossier a analyser",
    )

    parser.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Analyser recursivement (defaut: True)",
    )

    parser.add_argument(
        "--ops",
        action="append",
        choices=["renommage", "classement", "dedoublonner", "nettoyage"],
        default=None,
        help="Operation(s) a inclure (peut etre repete, defaut: toutes)",
    )

    parser.add_argument(
        "--template-renommage",
        type=str,
        default=None,
        help="Template de renommage (ex: '{artist} - {title}.{ext}')",
    )

    parser.add_argument(
        "--template-classement",
        type=str,
        default=None,
        help="Template de classement (ex: '{artist}/{album}/{track} {title}.{ext}')",
    )

    parser.add_argument(
        "--racine-classement",
        type=str,
        default="",
        help="Dossier racine pour le classement",
    )

    parser.add_argument(
        "--dossier-temp",
        type=str,
        default="data/tmp",
        help="Dossier temporaire a nettoyer (defaut: data/tmp)",
    )

    parser.add_argument(
        "--age-max",
        type=int,
        default=7,
        help="Age maximum en jours pour le nettoyage (defaut: 7)",
    )

    parser.add_argument(
        "--no-resoudre-conflits",
        action="store_true",
        help="Ne pas resoudre automatiquement les conflits de noms",
    )

    parser.add_argument(
        "--executer",
        action="store_true",
        help="Executer reellement les operations (defaut: simulation seule)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Force le mode simulation (inverse de --executer)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Point d'entree du CLI.

    Args:
        argv: Arguments en ligne de commande (None = sys.argv[1:]).

    Returns:
        Code de sortie (0 = succes).
    """
    args = _parser().parse_args(argv)

    dossier = Path(args.dossier)
    if not dossier.exists():
        print(f"{Style.RED}Erreur : le dossier '{dossier}' n'existe pas.{Style.RESET}", file=sys.stderr)
        return 1
    if not dossier.is_dir():
        print(f"{Style.RED}Erreur : '{dossier}' n'est pas un dossier.{Style.RESET}", file=sys.stderr)
        return 1

    # Determiner les operations selectionnees
    if args.ops is not None:
        selected_ops: set[str] = set(args.ops)
    else:
        selected_ops = {"renommage", "classement", "dedoublonner", "nettoyage"}

    # Options pour generer_apercu
    options: dict[str, Any] = {}
    if args.template_renommage is not None:
        options["template_renommage"] = args.template_renommage
    if args.template_classement is not None:
        options["template_classement"] = args.template_classement
    if args.racine_classement:
        options["racine_classement"] = args.racine_classement
    if args.dossier_temp != "data/tmp":
        options["dossier_temp"] = args.dossier_temp
    if args.age_max != 7:
        options["age_max_jours"] = args.age_max
    if args.no_resoudre_conflits:
        options["resoudre_conflits"] = False

    svc = OrdonnanceurService()

    try:
        analyse = svc.analyser_dossier(dossier, recursive=args.recursive)
    except Exception as e:
        print(f"{Style.RED}Erreur lors de l'analyse : {e}{Style.RESET}", file=sys.stderr)
        return 1

    apercu = svc.generer_apercu(analyse, selected_ops, options=options)
    afficher_apercu_console(apercu, chemin_dossier=dossier)

    # ── Exécution (uniquement si --executer) ──
    if args.executer or args.dry_run:
        simuler = not args.executer or args.dry_run
        resultat = svc.executer_operations(apercu, simuler=simuler)

        if simuler:
            _info("Mode simulation -- Aucun fichier modifie.")
        else:
            _ok("Operations executees avec succes !")

        ops = resultat["operations"]
        if "renommage" in ops:
            r = ops["renommage"]
            _item(f"  Renommage : {r['reussi']}/{r['tente']} fichiers")
        if "classement" in ops:
            c = ops["classement"]
            _item(f"  Classement : {c['reussi']}/{c['tente']} fichiers deplaces")
        if "deduplication" in ops:
            d = ops["deduplication"]
            msg = f"  Dedoublonnage : {d['supprime']} fichiers supprimes"
            if d['renomme_gardes']:
                msg += f", {d['renomme_gardes']} gardes renommes"
            _item(msg)
        if "nettoyage" in ops:
            n = ops["nettoyage"]
            _item(f"  Nettoyage : {n['supprime']}/{n['tente']} fichiers supprimes ({n.get('taille_lisible', '?')} liberes)")

        erreurs = resultat.get("erreurs", [])
        if erreurs:
            _warning(f"{len(erreurs)} erreur(s) rencontree(s) :")
            for err in erreurs[:5]:
                print(f"    - [{err['operation']}] {err['fichier']} : {err['erreur']}")
            if len(erreurs) > 5:
                print(f"    ... et {len(erreurs) - 5} autre(s) erreur(s)")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
