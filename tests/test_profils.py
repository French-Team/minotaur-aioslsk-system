"""Tests pour les profils d'optimisation (data/profils/*.json).

Execute ``scripts/validate_profils.py`` dans un sous-processus et verifie
que tous les profils sont valides (cles existantes dans _DEFAULTS,
categories mappees a des pages de config existantes).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PROJECT_ROOT / "scripts" / "validate_profils.py"


def test_profils_sont_valides() -> None:
    """Verifie que tous les profils JSON passent la validation."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    assert result.returncode == 0, (
        f"Validation des profils echouee (code {result.returncode}).\nSortie :\n{result.stdout}"
    )
