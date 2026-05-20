#!/usr/bin/env python3
"""
CI — Vérifie que tous les tests utilisant le fixture ``qapp`` (widgets Qt réels)
ont le marqueur ``@pytest.mark.qt_heavy``.

Prévient les oublis : si un test a besoin d'un QApplication pour créer des
widgets, il doit être marqué ``qt_heavy`` pour que pytest-xdist l'exécute
dans le même worker (évite la saturation RAM).

Usage :
    python scripts/check_qt_heavy_markers.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# ── Fichiers connus dont les widgets Qt sont légers (pas de marqueur nécessaire)
# Ces tests créent des widgets simples (QWidget, ClockWidget, etc.) qui ne
# saturent pas la RAM même exécutés en parallèle par les 8 workers xdist.
ALLOWED_LIGHTWEIGHT: set[str] = {
    "test_clock.py",
    "test_progression.py",
    "test_telechargements.py",
    "test_theme.py",  # pas de QApplication du tout
}

# ── Fichier exclu qui utilise uniquement QtCore (QObject, Signal) sans widgets
QT_CORE_ONLY: set[str] = {
    "test_eventbus_routing.py",  # importe QObject + Signal depuis QtCore seulement
}

TESTS_DIR = Path("tests")


def _is_qt_heavy_marker(node: ast.expr) -> bool:
    """Vérifie si un décorateur AST correspond à ``@pytest.mark.qt_heavy``."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "qt_heavy"
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "mark"
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "pytest"
    )


def _has_qapp_parameter(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Vérifie si une fonction de test a un paramètre ``qapp``."""
    return any(arg.arg == "qapp" for arg in node.args.args)


def check_file(filepath: Path) -> list[str]:
    """Analyse un fichier de test et retourne les violations détectées."""
    violations: list[str] = []

    if filepath.name in ALLOWED_LIGHTWEIGHT | QT_CORE_ONLY:
        return violations

    content = filepath.read_text(encoding="utf-8")

    # Vérification rapide : si aucun import QtWidgets, pas besoin du marqueur
    if "from PySide6.QtWidgets" not in content:
        return violations

    try:
        tree = ast.parse(content)
    except SyntaxError:
        # Les fichiers non-Python ne devraient pas arriver ici
        return violations

    # Collecte : quels nœuds de test ont qapp / qt_heavy ?
    nodes_with_qapp: set[str] = set()
    nodes_with_qt_heavy_class: set[str] = set()  # classes marquées → couvre toute la classe
    nodes_with_qt_heavy_func: set[str] = set()  # fonctions marquées individuellement

    # Itérer sur les nœuds racines (tree.body) pour éviter le double-compte
    # des méthodes de classe : ast.walk() visite aussi les enfants des classes,
    # ce qui ferait traiter chaque méthode 2 fois (une fois comme enfant de
    # classe, une fois comme nœud autonome).
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            if any(_is_qt_heavy_marker(d) for d in node.decorator_list):
                nodes_with_qt_heavy_class.add(node.name)
            # Vérifier chaque méthode de la classe
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith(
                    "test_"
                ):
                    if _has_qapp_parameter(item):
                        nodes_with_qapp.add(f"{node.name}.{item.name}")
                    if any(_is_qt_heavy_marker(d) for d in item.decorator_list):
                        nodes_with_qt_heavy_func.add(f"{node.name}.{item.name}")

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
            "test_"
        ):
            # Nœud racine — fonction de test autonome (pas dans une classe)
            if _has_qapp_parameter(node):
                nodes_with_qapp.add(node.name)
            if any(_is_qt_heavy_marker(d) for d in node.decorator_list):
                nodes_with_qt_heavy_func.add(node.name)

    # Vérifier chaque nœud qui utilise qapp
    for test_name in sorted(nodes_with_qapp):
        # Déterminer le nom de la classe (si méthode) pour la couverture classe
        parent_class = test_name.split(".")[0] if "." in test_name else ""
        covered = (
            test_name in nodes_with_qt_heavy_func
            or parent_class in nodes_with_qt_heavy_class
        )
        if not covered:
            violations.append(
                f"  {filepath.name}:{test_name} utilise qapp "
                f"mais n'a pas @pytest.mark.qt_heavy"
            )

    return violations


def main() -> int:
    """Point d'entrée. Retourne 0 si tout va bien, 1 sinon."""
    test_files = sorted(TESTS_DIR.glob("test_*.py"))
    all_violations: list[str] = []

    for filepath in test_files:
        violations = check_file(filepath)
        all_violations.extend(violations)

    if all_violations:
        print("ERREUR: Tests Qt sans marqueur @pytest.mark.qt_heavy :")
        for v in all_violations:
            print(v)
        print()
        print(
            "Ajoute @pytest.mark.qt_heavy sur les tests qui utilisent qapp, "
            "ou ajoute le fichier dans ALLOWED_LIGHTWEIGHT s'il est vraiment leger."
        )
        return 1

    print(f"OK: {len(test_files)} fichiers verifies - aucun oubli de marqueur qt_heavy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
