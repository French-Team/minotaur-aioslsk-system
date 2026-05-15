#!/usr/bin/env python3
"""
Validation script pour les profils d'optimisation.

Verifie que tous les profils JSON dans data/profils/ ont :
1. Des cles valides existant dans _DEFAULTS (src/services/app_config.py)
2. Des categories mappees a des pages de config existantes (_CAT_TO_PAGE)

Usage :
    python scripts/validate_profils.py

Exit codes :
    0 = tout est valide
    1 = warnings (cles manquantes mais inoffensives)
    2 = erreurs (cles invalides / pages manquantes)
"""

from __future__ import annotations

import json
import os
import sys
from glob import glob
from typing import Any

# ── Couleurs terminal ─────────────────────────────────────────────
# Evite les caracteres Unicode qui plantent sur Windows (cp1252)
_RED = "\033[91m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_CYAN = "\033[96m"
_BOLD = "\033[1m"
_RESET = "\033[0m"

# Symboles ASCII-safe
_CHECK = "[OK]"
_CROSS = "[XX]"
_WARN = "[!!]"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

# ── Imports du projet ────────────────────────────────────────────
# isort:skip
from src.services.app_config import _DEFAULTS  # type: ignore[import-untyped]
from src.gui.widgets.bots.bot_optimiseur import BotOptimiseur  # type: ignore[import-untyped]

_CAT_TO_PAGE: dict[str, str] = BotOptimiseur._CAT_TO_PAGE  # type: ignore[attr-defined]


def _type_str(valeur: Any) -> str:
    """Retourne le nom du type Python d'une valeur."""
    t = type(valeur)
    return {
        str: "str",
        int: "int",
        float: "float",
        bool: "bool",
        list: "list",
        dict: "dict",
        type(None): "None",
    }.get(t, t.__name__)


def _types_compatibles(v1: Any, v2: Any) -> bool:
    """Verifie si deux valeurs ont des types compatibles."""
    return type(v1) is type(v2) or (
        isinstance(v1, (int, float)) and isinstance(v2, (int, float))
    )


def _valide_profil(
    chemin: str,
) -> tuple[int, int, list[str], list[str]]:
    """
    Valide un fichier profil JSON.

    Retourne (nb_ok, nb_cles_parcourues, warnings, erreurs).
    """
    warnings: list[str] = []
    erreurs: list[str] = []
    nb_ok = 0
    nb_cles_parcourues = 0

    try:
        with open(chemin, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        erreurs.append(f"Impossible de lire le fichier JSON : {e}")
        return 0, 0, [], erreurs

    # ── Structure obligatoire ──
    if "params" not in data:
        erreurs.append("Cle 'params' manquante dans le fichier JSON")
        return 0, 0, [], erreurs

    if not isinstance(data["params"], dict):
        erreurs.append("'params' doit etre un dictionnaire")
        return 0, 0, [], erreurs

    params = data["params"]

    # ── Verification de chaque categorie ──
    for categorie, sous_cles in params.items():
        # Compter les cles dans cette categorie
        if isinstance(sous_cles, dict):
            nb_cles_parcourues += len(sous_cles)
        else:
            nb_cles_parcourues += 1

        # La categorie est-elle mappee ?
        page = _CAT_TO_PAGE.get(categorie)
        if page is None:
            erreurs.append(
                f"[{categorie}] Categorie inconnue => absente de _CAT_TO_PAGE"
            )
            continue

        if not isinstance(sous_cles, dict):
            erreurs.append(f"[{categorie}] doit etre un dictionnaire de cles")
            continue

        for sous_cle, valeur in sous_cles.items():
            if "." in sous_cle:
                cle = sous_cle  # deja plate (ex: "reseau.port_ecoute")
            else:
                cle = f"{categorie}.{sous_cle}"

            if cle in _DEFAULTS:
                nb_ok += 1
                # Verification de type
                if not _types_compatibles(valeur, _DEFAULTS[cle]):
                    warnings.append(
                        f"[{categorie}] '{cle}' : attendu {_type_str(_DEFAULTS[cle])}, "
                        f"recu {_type_str(valeur)} ({valeur!r})"
                    )
            else:
                warnings.append(
                    f"[{categorie}] '{cle}' = {valeur!r} n'existe PAS dans _DEFAULTS"
                )

    return nb_ok, nb_cles_parcourues, warnings, erreurs


def main() -> int:
    nb_profils = 0
    nb_ok_total = 0
    nb_cles_total = 0
    nb_warnings = 0
    nb_erreurs = 0
    a_des_erreurs = False

    profils_dir = os.path.join(PROJECT_ROOT, "data", "profils")
    fichiers = sorted(glob(os.path.join(profils_dir, "*.json")))

    if not fichiers:
        print(f"{_RED}{_CROSS} Aucun fichier profil trouve dans {profils_dir}{_RESET}")
        return 2

    # ── Entete ────────────────────────────────────────────────────
    print(f"\n{_BOLD}{_CYAN}=== Validation des profils ==={_RESET}\n")
    print(
        f"{_BOLD}References :{_RESET} "
        f"{len(_DEFAULTS)} cles dans _DEFAULTS, "
        f"{len(_CAT_TO_PAGE)} pages dans _CAT_TO_PAGE\n"
    )

    # ── Validation de _CAT_TO_PAGE vs _DEFAULTS ──────────────────
    categories_defaults: set[str] = set()
    for cle in _DEFAULTS:
        cat = cle.split(".")[0]
        categories_defaults.add(cat)

    cats_sans_page = categories_defaults - set(_CAT_TO_PAGE.keys())
    if cats_sans_page:
        print(
            f"{_YELLOW}{_WARN} Categories _DEFAULTS sans page _CAT_TO_PAGE : "
            f"{', '.join(sorted(cats_sans_page))}{_RESET}\n"
        )

    # ── Validation de chaque profil ───────────────────────────────
    for chemin in fichiers:
        nom_fichier = os.path.splitext(os.path.basename(chemin))[0]
        print(f"{_BOLD}-- {nom_fichier} --{_RESET}")

        nb_ok, nb_cles, warns, errs = _valide_profil(chemin)
        nb_ok_total += nb_ok
        nb_cles_total += nb_cles
        nb_warnings += len(warns)
        nb_erreurs += len(errs)

        if errs:
            a_des_erreurs = True
            for e in errs:
                print(f"  {_RED}{_CROSS} {e}{_RESET}")
        if warns:
            for w in warns:
                print(f"  {_YELLOW}{_WARN} {w}{_RESET}")
        if not errs and not warns:
            print(f"  {_GREEN}{_CHECK} {nb_ok}/{nb_cles} cles valides{_RESET}")
        else:
            print(
                f"  {_GREEN}{_CHECK} {nb_ok}/{nb_cles} cles valides{_RESET}"
                f"{_YELLOW}, {len(warns)} avertissements{_RESET}"
                f"{_RED}, {len(errs)} erreurs{_RESET}"
            )
        nb_profils += 1
        print()

    # ── Resume ────────────────────────────────────────────────────
    print(f"{_BOLD}{_CYAN}=== Resume ==={_RESET}")
    print(f"  Profils : {nb_profils}")
    print(f"  Cles valides : {nb_ok_total}/{nb_cles_total}")
    if nb_warnings:
        print(f"  {_YELLOW}Avertissements : {nb_warnings}{_RESET}")
    else:
        print(f"  {_GREEN}Avertissements : 0{_RESET}")
    if nb_erreurs:
        print(f"  {_RED}Erreurs : {nb_erreurs}{_RESET}")
        print(f"\n{_RED}{_CROSS} ECHEC -- corrigez les erreurs ci-dessus.{_RESET}")
        return 2
    else:
        print(f"  {_GREEN}Erreurs : 0{_RESET}")

    if nb_warnings:
        print(
            f"\n{_YELLOW}{_WARN} {nb_warnings} avertissement(s) -- "
            f"cles non reconnues dans _DEFAULTS (peut-etre intentionnel).{_RESET}"
        )
        return 1

    print(f"\n{_GREEN}{_CHECK} Tous les profils sont valides.{_RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
