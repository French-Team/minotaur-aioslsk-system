#!/usr/bin/env python3
"""
Orchestrateur de tests par lots — divise les 1354 tests pytest
en groupes independants avec timeouts courts.

Probleme resolu :
  Au lieu d'un seul ``pytest tests/`` qui attend 5 minutes en cas d'erreur,
  chaque lot est un appel pytest separe avec son propre timeout.
  Si un lot echoue, on le voit immediatement.

Usage :
    python scripts/run_tests_batched.py           # Lance tous les lots
    python scripts/run_tests_batched.py --list    # Affiche les lots
    python scripts/run_tests_batched.py --batch 2 # Lot #2 uniquement
    python scripts/run_tests_batched.py --fast    # Saute les lots qt_heavy + E2E
    python scripts/run_tests_batched.py --cov     # Active la couverture
    python scripts/run_tests_batched.py --continue # Continue meme si un lot echoue
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# ── Couleurs terminal (ASCII-safe pour Windows cp1252) ───────────
_BOLD = "\033[1m"
_RED = "\033[91m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_CYAN = "\033[96m"
_GRAY = "\033[90m"
_RESET = "\033[0m"

_PASS = " [PASS]"
_FAIL = " [FAIL]"
_SKIP = " [SKIP]"
_WARN = " [WARN]"

TEST_DIR = Path("tests")
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent


# ── Definition des lots ──────────────────────────────────────────
# Chaque lot = groupe de fichiers de test independants.
# Le timeout est adapte a la complexite du lot.
# Sans `-o "addopts="`, pytest herite du `-n auto --dist loadscope`
# de pytest.ini, ce qui ajoute 5-15s de overhead xdist par lot.
# On force `-o "addopts="` pour chaque lot, puis on ajoute nos options.


@dataclass
class Batch:
    """Un lot de tests avec ses parametres."""

    id: int
    name: str
    files: list[str]
    timeout: int = 30
    is_heavy: bool = False      # True => qt_heavy, necessite 1 worker dedie
    is_e2e: bool = False        # True => test end-to-end (serveur web)


def _full_paths(files: list[str]) -> list[str]:
    """Convertit les noms de fichiers en chemins absolus."""
    return [str(TEST_DIR / f) for f in files]


BATCHES: list[Batch] = [
    Batch(
        id=1,
        name="infrastructure",
        files=[
            "test_eventbus_routing.py",
            "test_library_db.py",
            "test_search_history.py",
            "test_sql_check_constraints.py",
        ],
        timeout=20,
    ),
    Batch(
        id=2,
        name="services",
        files=[
            "test_error_translator.py",
            "test_connexion_manager.py",
            "test_profils.py",
            "test_profils_unit.py",
        ],
        timeout=20,
    ),
    Batch(
        id=3,
        name="ordonnanceur",
        files=[
            "test_ordonnanceur_service.py",
            "test_ordonnanceur_service_mutagen.py",
            "test_cli_ordonnanceur.py",
            "test_planificateur.py",
        ],
        timeout=20,
    ),
    Batch(
        id=4,
        name="qt-light",
        files=[
            "test_clock.py",
            "test_progression.py",
            "test_telechargements.py",
            "test_theme.py",
        ],
        timeout=20,

    ),
    Batch(
        id=5,
        name="qt-heavy-biblio",
        files=[
            "test_bot_bibliotheque.py",
        ],
        timeout=30,
        is_heavy=True,
    ),
    Batch(
        id=6,
        name="qt-heavy-wishlist",
        files=[
            "test_bot_wishlist.py",
        ],
        timeout=30,
        is_heavy=True,
    ),
    Batch(
        id=7,
        name="qt-heavy-accueil",
        files=[
            "test_bot_accueil.py",
            "test_bot_assistant.py",
            "test_bot_recherche.py",
        ],
        timeout=30,
        is_heavy=True,
    ),
    Batch(
        id=8,
        name="qt-heavy-telechargement",
        files=[
            "test_bot_telechargement.py",
            "test_bot_ordonnanceur_integration.py",
            "test_layout_entry.py",
        ],
        timeout=45,
        is_heavy=True,
    ),
    Batch(
        id=9,
        name="qt-heavy-center",
        files=[
            "test_center_integration.py",
            "test_clients_actifs_integration.py",
            "test_clients_actifs_ui.py",
        ],
        timeout=45,
        is_heavy=True,
    ),
    Batch(
        id=10,
        name="qt-heavy-surveillance",
        files=[
            "test_surveillance_integration.py",
            "test_surveillance_ui.py",
            "test_library_scanner.py",
        ],
        timeout=45,
        is_heavy=True,
    ),
    Batch(
        id=11,
        name="qt-heavy-integration",
        files=[
            "test_integration_planificateur_ordonnanceur.py",
            "test_etape10_polish.py",
        ],
        timeout=30,
        is_heavy=True,
    ),
    Batch(
        id=12,
        name="qt-heavy-window",
        files=[
            "test_main_window.py",
            "test_qss_inspector.py",
        ],
        timeout=30,
        is_heavy=True,
    ),
    Batch(
        id=13,
        name="e2e-web",
        files=[
            "test_e2e_web.py",
        ],
        timeout=45,
        is_e2e=True,
    ),
]


def _build_pytest_cmd(
    batch: Batch,
    use_cov: bool = False,
    cov_append: bool = False,
) -> list[str]:
    """Construit la commande pytest pour un lot.

    - On ecrase ``addopts`` de pytest.ini pour eviter ``-n auto``
      (xdist overhead de 5-15s par lot)
    - On ajoute nos options : timeout, verbosity, no-header
    - Coverage optionnelle avec ``--cov-append``
    """
    files = _full_paths(batch.files)

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *files,
        "-o",
        "addopts=",
        "-q",
        "--no-header",
        "-x",               # stop au premier echec
        "--timeout",
        str(batch.timeout),
    ]

    if use_cov:
        cmd.extend(["--cov=src", "--cov-report=term-missing:skip-covered"])
        if cov_append:
            cmd.append("--cov-append")

    return cmd


# ── Execution ────────────────────────────────────────────────────


def _print_separator(title: str, char: str = "-") -> None:
    """Affiche une ligne de separation avec titre."""
    width = 68
    side = (width - len(title) - 2) // 2
    sep = char * max(side, 2)
    print(f"\n{sep} {_BOLD}{_CYAN}{title}{_RESET} {sep}")


def _run_batch(
    batch: Batch,
    use_cov: bool = False,
    cov_append: bool = False,
) -> tuple[int, float]:
    """Execute un lot de tests et retourne (exit_code, duration_s)."""
    cmd = _build_pytest_cmd(batch, use_cov=use_cov, cov_append=cov_append)

    files_str = ", ".join(batch.files)
    print(
        f"  {_BOLD}Lot {batch.id:02d} : {batch.name}{_RESET} "
        f"{_GRAY}({files_str}){_RESET}"
    )
    print(f"  {'-' * 60}")

    start = time.time()
    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=False,
    )
    duration = time.time() - start

    return result.returncode, duration


@dataclass
class BatchResult:
    batch: Batch
    returncode: int
    duration: float
    skipped: bool = False


def _print_summary(results: list[BatchResult], total_time: float) -> None:
    """Affiche le tableau recapitulatif final."""
    _print_separator(" RESULTATS ", "=")
    print()

    passed = 0
    failed = 0
    skipped = 0

    for r in results:
        if r.skipped:
            icon = _SKIP
            label = "ignore"
            skipped += 1
        elif r.returncode == 0:
            icon = _PASS
            label = f"{_GREEN}PASSE{_RESET}"
            passed += 1
        elif r.returncode == 5:
            icon = _WARN
            label = f"{_YELLOW}0 TEST{_RESET}"
            passed += 1
        else:
            icon = _FAIL
            label = f"{_RED}ECHEC ({r.returncode}){_RESET}"
            failed += 1

        batch_label = f"{_BOLD}{r.batch.name:32s}{_RESET}"
        dur_str = f" {r.duration:.1f}s"
        print(f"  {icon} {batch_label} {label:18s} {dur_str}")

    print()
    total_batches = len(results)
    _print_separator(f" {passed}/{total_batches} lots OK ", "=")
    print(f"  Temps total : {total_time:.1f}s")
    if failed > 0:
        print(f"  {_FAIL} {_RED}{failed} lot(s) en echec{_RESET}")
    if skipped > 0:
        print(f"  {_SKIP} {skipped} lot(s) ignore(s)")


# ── Interface CLI ────────────────────────────────────────────────


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Orchestrateur de tests pytest par lots.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemples :\n"
            "  python scripts/run_tests_batched.py           # Tout\n"
            "  python scripts/run_tests_batched.py --list    # Liste\n"
            "  python scripts/run_tests_batched.py --fast    # Sans qt_heavy ni E2E\n"
            "  python scripts/run_tests_batched.py --batch 3 # Lot 3 seulement\n"
            "  python scripts/run_tests_batched.py --cov     # Avec couverture\n"
        ),
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="show_list",
        help="Affiche les lots disponibles sans les executer",
    )
    parser.add_argument(
        "--batch",
        type=int,
        metavar="N",
        help="Execute uniquement le lot N (1-13)",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Saute les lots qt_heavy (5-12) et E2E (13)",
    )
    parser.add_argument(
        "--cov",
        action="store_true",
        help="Active la couverture avec --cov=src --cov-append",
    )
    parser.add_argument(
        "--continue",
        action="store_true",
        dest="continue_on_fail",
        help="Continue meme si un lot echoue",
    )
    return parser.parse_args(argv)


def _list_batches() -> None:
    """Affiche la liste des lots."""
    _print_separator(" LOTS DISPONIBLES ", "=")
    print()
    print(
        f"  {'ID':>2s}  {'Nom':32s} {'Timeout':>8s}  {'Type':4s}  Fichiers"
    )
    print(f"  {'--':>2s}  {'---':32s} {'-------':>8s}  {'----':4s}  --------")
    for batch in BATCHES:
        qt_flag = "hvy" if batch.is_heavy else ("e2e" if batch.is_e2e else "")
        files_str = ", ".join(batch.files)
        print(
            f"  {batch.id:>2d}  {batch.name:32s} "
            f"{batch.timeout:>3d}s     {qt_flag:4s}  {files_str}"
        )
    print()


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])

    if args.show_list:
        _list_batches()
        return 0

    # Filtrer les lots
    batches = list(BATCHES)

    if args.batch is not None:
        batches = [b for b in batches if b.id == args.batch]
        if not batches:
            print(
                f"{_RED}Erreur : lot {args.batch} introuvable. "
                f"Utilisez --list pour voir les lots.{_RESET}"
            )
            return 1


    if args.fast:
        old_count = len(batches)
        batches = [
            b for b in batches
            if not b.is_heavy and not b.is_e2e
        ]
        skipped = old_count - len(batches)
        if skipped > 0:
            print(        f"  {_SKIP} Mode --fast : {skipped} lot(s) qt_heavy/E2E ignores\n"
            )

    # ── Execution ────────────────────────────────────────────────
    results: list[BatchResult] = []
    start_total = time.time()
    exit_code = 0
    first_failure: int | None = None

    total_estimation = sum(b.timeout for b in batches)
    print(
        f"{_BOLD}Demarrage de {len(batches)} lot(s) de test{_RESET} "
        f"(timeout max total estime : {total_estimation}s)\n"
    )

    try:
        for i, batch in enumerate(batches, 1):
            _print_separator(f" Lot {batch.id:02d} : {batch.name} ")

            returncode, duration = _run_batch(
                batch,
                use_cov=args.cov,
                cov_append=(args.cov and i > 1),
            )

            results.append(BatchResult(
                batch=batch,
                returncode=returncode,
                duration=duration,
            ))

            if returncode != 0 and returncode != 5:
                print(
                    f"\n  {_FAIL} {_RED}Lot {batch.id} en echec "
                    f"(code {returncode}){_RESET}"
                )
                if first_failure is None:
                    first_failure = batch.id
                exit_code = returncode
                if not args.continue_on_fail:
                    print(
                        f"  {_YELLOW}Arret. Corrigez le lot {batch.id} "
                        f"et relancez : --batch {batch.id}{_RESET}"
                    )
                    return exit_code
    finally:
        total_time = time.time() - start_total
        _print_summary(results, total_time)

        if first_failure is not None:
            print(
                f"\n  Pour relancer un lot specifique :\n"
                f"    python scripts/run_tests_batched.py --batch {first_failure}\n"
            )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
