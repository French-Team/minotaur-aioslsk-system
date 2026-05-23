"""Tests unitaires pour le Crash Reporter — register_crash_hook & _call_hooks."""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── On importe le module en tant que namespace pour pouvoir
#    sauvegarder/restaurer son état global entre les tests ────────
from security import crash_reporter as cr


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_crash_reporter_state() -> None:
    """Sauvegarde et restaure l'état global du module entre chaque test.

    Évite les fuites de hooks entre tests et réinitialise _SAVED.
    """
    saved_hooks = list(cr._CRASH_HOOKS)
    saved_saved = cr._SAVED
    yield
    cr._CRASH_HOOKS.clear()
    cr._CRASH_HOOKS.extend(saved_hooks)
    cr._SAVED = saved_saved


# ── Tests : register_crash_hook ──────────────────────────────────────────────


class TestRegisterCrashHook:
    """Vérifie que register_crash_hook enregistre correctement les hooks."""

    def test_ajoute_un_hook(self) -> None:
        """Un hook enregistré doit apparaître dans _CRASH_HOOKS."""
        initial = len(cr._CRASH_HOOKS)
        cr.register_crash_hook(lambda: None)
        assert len(cr._CRASH_HOOKS) == initial + 1

    def test_multiple_hooks_conserves_ordre(self) -> None:
        """Les hooks sont conservés dans l'ordre d'enregistrement."""
        appel = []

        def h1() -> None:
            appel.append(1)

        def h2() -> None:
            appel.append(2)

        cr.register_crash_hook(h1)
        cr.register_crash_hook(h2)
        cr._call_hooks()
        assert appel == [1, 2]

    def test_hook_est_callable(self) -> None:
        """register_crash_hook accepte n'importe quel callable sans argument."""
        hook = MagicMock()
        cr.register_crash_hook(hook)
        cr._call_hooks()
        hook.assert_called_once_with()


# ── Tests : _call_hooks ──────────────────────────────────────────────────────


class TestCallHooks:
    """Vérifie le comportement de _call_hooks."""

    def test_appelle_tous_les_hooks(self) -> None:
        """Tous les hooks enregistrés sont appelés."""
        h1 = MagicMock()
        h2 = MagicMock()
        cr.register_crash_hook(h1)
        cr.register_crash_hook(h2)
        cr._call_hooks()
        h1.assert_called_once_with()
        h2.assert_called_once_with()

    def test_appelle_hooks_dans_ordre(self) -> None:
        """Les hooks sont appelés dans l'ordre FIFO."""
        trace: list[int] = []

        cr.register_crash_hook(lambda: trace.append(1))
        cr.register_crash_hook(lambda: trace.append(2))
        cr.register_crash_hook(lambda: trace.append(3))
        cr._call_hooks()
        assert trace == [1, 2, 3]

    def test_hook_qui_leve_exception_ne_bloque_pas_les_autres(self) -> None:
        """Un hook qui plante n'empêche pas les hooks suivants de s'exécuter."""
        trace: list[int] = []

        def h1() -> None:
            trace.append(1)
            raise RuntimeError("Hook 1 a planté !")

        def h2() -> None:
            trace.append(2)

        cr.register_crash_hook(h1)
        cr.register_crash_hook(h2)
        # Ne doit pas lever d'exception
        cr._call_hooks()
        assert trace == [1, 2], (
            "h2 doit être appelé même si h1 a levé une exception"
        )

    def test_hook_qui_leve_type_erreur_egalement_ignore(self) -> None:
        """Même TypeError doit être attrapé par _call_hooks."""
        def mauvais_hook() -> None:
            raise TypeError("Mauvais type !")

        bon_hook = MagicMock()
        cr.register_crash_hook(mauvais_hook)
        cr.register_crash_hook(bon_hook)
        cr._call_hooks()
        bon_hook.assert_called_once_with()

    def test_aucun_hook_ne_leve_pas(self) -> None:
        """_call_hooks ne fait rien si aucun hook n'est enregistré."""
        # Ne doit pas lever d'exception
        cr._call_hooks()

    def test_hook_modifie_etat_entre_hooks(self) -> None:
        """Les hooks peuvent modifier un état partagé séquentiellement."""
        etat: dict[str, int] = {"compteur": 0}

        def incremente() -> None:
            etat["compteur"] += 1

        cr.register_crash_hook(incremente)
        cr.register_crash_hook(incremente)
        cr.register_crash_hook(incremente)
        cr._call_hooks()
        assert etat["compteur"] == 3


# ── Tests : intégration dans _excepthook ─────────────────────────────────────


class TestIntegrationExcepthook:
    """Vérifie que _call_hooks est bien appelé depuis _excepthook."""

    def test_hook_appele_depuis_excepthook(self) -> None:
        """_excepthook appelle les hooks avant _halt."""
        hook = MagicMock()

        with (
            patch.object(cr, "_save_tb", return_value=Path("/tmp/test.log")),
            patch.object(cr, "_halt") as mock_halt,
        ):
            cr.register_crash_hook(hook)
            cr._excepthook(RuntimeError, RuntimeError("boom"), None)

        hook.assert_called_once_with()

    def test_hook_appele_avant_halt(self) -> None:
        """Les hooks sont appelés AVANT _halt (ordre d'appel)."""
        trace: list[str] = []

        def mon_hook() -> None:
            trace.append("hook")

        with (
            patch.object(cr, "_save_tb", return_value=Path("/tmp/test.log")),
            patch.object(cr, "_halt", lambda p: trace.append("halt")),
        ):
            cr.register_crash_hook(mon_hook)
            cr._excepthook(RuntimeError, RuntimeError("boom"), None)

        assert trace == ["hook", "halt"]

    def test_plusieurs_hooks_depuis_excepthook(self) -> None:
        """Tous les hooks enregistrés sont appelés depuis _excepthook."""
        hook1 = MagicMock()
        hook2 = MagicMock()

        with (
            patch.object(cr, "_save_tb", return_value=Path("/tmp/test.log")),
            patch.object(cr, "_halt"),
        ):
            cr.register_crash_hook(hook1)
            cr.register_crash_hook(hook2)
            cr._excepthook(RuntimeError, RuntimeError("boom"), None)

        hook1.assert_called_once_with()
        hook2.assert_called_once_with()

    def test_hooks_pas_appeles_si_deja_sauve(self) -> None:
        """Si _SAVED est déjà True, _excepthook n'appelle PAS les hooks."""
        hook = MagicMock()

        with patch.object(cr, "_halt") as mock_halt:
            cr._SAVED = True
            cr._excepthook(RuntimeError, RuntimeError("boom"), None)

        hook.assert_not_called()
        mock_halt.assert_not_called()


# ── Tests : intégration dans _StderrCapture._flush ────────────────────────────


class TestIntegrationStderrFlush:
    """Vérifie que _call_hooks est bien appelé depuis _StderrCapture._flush."""

    def _make_capture(self) -> cr._StderrCapture:
        """Crée un _StderrCapture avec _original mocké (pas de bruit stderr)."""
        capture = cr._StderrCapture()
        capture._original = MagicMock()  # évite d'écrire sur le vrai stderr
        return capture

    def test_hook_appele_depuis_flush(self) -> None:
        """_StderrCapture._flush appelle les hooks avant os._exit."""
        hook = MagicMock()

        with (
            patch.object(cr, "_save_tb", return_value=Path("/tmp/test.log")),
            patch.object(cr.os, "_exit"),
            patch.object(threading, "Timer"),
        ):
            cr._SAVED = False
            capture = self._make_capture()
            capture._buffer = ["Traceback (most recent call last):\n"]
            cr.register_crash_hook(hook)
            capture._flush()

        hook.assert_called_once_with()

    def test_hook_appele_avant_os_exit(self) -> None:
        """Les hooks sont appelés AVANT os._exit(1)."""
        trace: list[str] = []

        def mon_hook() -> None:
            trace.append("hook")

        def fake_exit(code: int) -> None:
            trace.append(f"exit({code})")

        with (
            patch.object(cr, "_save_tb", return_value=Path("/tmp/test.log")),
            patch.object(cr.os, "_exit", fake_exit),
            patch.object(threading, "Timer"),
        ):
            cr._SAVED = False
            capture = self._make_capture()
            capture._buffer = ["Traceback (most recent call last):\n"]
            cr.register_crash_hook(mon_hook)
            capture._flush()

        assert trace == ["hook", "exit(1)"]

    def test_aucun_hook_ne_plante_pas_flush(self) -> None:
        """_flush ne plante pas si aucun hook n'est enregistré."""
        with (
            patch.object(cr, "_save_tb", return_value=Path("/tmp/test.log")),
            patch.object(cr.os, "_exit"),
            patch.object(threading, "Timer"),
        ):
            cr._SAVED = False
            capture = self._make_capture()
            capture._buffer = ["Traceback (most recent call last):\n"]
            # Ne doit pas lever d'exception
            capture._flush()

    def test_hook_plante_pas_os_exit(self) -> None:
        """Même si un hook plante, os._exit(1) est quand même appelé."""
        trace: list[str] = []

        def mauvais_hook() -> None:
            trace.append("hook")
            raise RuntimeError("boom")

        def fake_exit(code: int) -> None:
            trace.append(f"exit({code})")

        with (
            patch.object(cr, "_save_tb", return_value=Path("/tmp/test.log")),
            patch.object(cr.os, "_exit", fake_exit),
            patch.object(threading, "Timer"),
        ):
            cr._SAVED = False
            capture = self._make_capture()
            capture._buffer = ["Traceback (most recent call last):\n"]
            cr.register_crash_hook(mauvais_hook)
            capture._flush()

        assert trace == ["hook", "exit(1)"]

    def test_pas_de_hooks_si_deja_sauve(self) -> None:
        """Si _SAVED est déjà True, _flush retourne sans appeler les hooks."""
        hook = MagicMock()

        with (
            patch.object(threading, "Timer"),
        ):
            cr._SAVED = True
            capture = self._make_capture()
            capture._buffer = ["Traceback (most recent call last):\n"]
            cr.register_crash_hook(hook)
            capture._flush()

        hook.assert_not_called()


# ── Tests : thread-safety (niveau basique) ────────────────────────────────────


class TestThreadSafety:
    """Vérifie le comportement basique de _call_hooks dans un contexte threading."""

    def test_hook_appele_dans_thread_separe(self) -> None:
        """Un hook enregistré est appelé quand _call_hooks est exécuté
        depuis un thread différent."""
        appel = []

        def hook() -> None:
            appel.append(1)

        cr.register_crash_hook(hook)

        def run_in_thread() -> None:
            cr._call_hooks()
            appel.append(2)

        t = threading.Thread(target=run_in_thread)
        t.start()
        t.join()

        assert appel == [1, 2]

    def test_hook_thread_safe_avec_verrou(self) -> None:
        """Plusieurs threads peuvent appeler register_crash_hook
        sans corruption (vérification non bloquante)."""
        hooks_avant = len(cr._CRASH_HOOKS)
        n_threads = 10

        def ajouter_hook() -> None:
            cr.register_crash_hook(lambda: None)

        threads = [threading.Thread(target=ajouter_hook) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(cr._CRASH_HOOKS) == hooks_avant + n_threads
