"""Tests unitaires pour les interrupteurs demarrer()/arreter() des 5 bots.

Vérifie que chaque bot expose correctement :
- _actif = False à l'initialisation
- demarrer() → _actif = True (idempotent)
- arreter() → _actif = False (idempotent)
- Cycle demarrer → arreter fonctionne
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Generator

import pytest
from PySide6.QtWidgets import QFrame
from pytest import MonkeyPatch

from src.gui.widgets.bots.bot_bibliotheque import BotBibliotheque
from src.gui.widgets.bots.bot_optimiseur import BotOptimiseur
from src.gui.widgets.bots.bot_recherche import BotRecherche
from src.gui.widgets.bots.bot_surveillance import BotSurveillance
from src.gui.widgets.bots.bot_telechargement import BotTelechargement
from src.services.event_bus import EventBus


# ═══════════════════════════════════════════════════════════════════════════
#  Classe de base pour les tests d'interrupteur
# ═══════════════════════════════════════════════════════════════════════════


class _MixinInterrupteur:
    """Mixin avec les tests communs pour tous les interrupteurs."""

    def test_initial_actif_false(self, bot: QFrame) -> None:
        """_actif est False après l'instanciation."""
        assert bot._actif is False

    def test_demarrer_active(self, bot: QFrame) -> None:
        """demarrer() passe _actif à True."""
        bot.demarrer()
        assert bot._actif is True

    def test_demarrer_idempotent(self, bot: QFrame) -> None:
        """demarrer() deux fois : _actif reste True."""
        bot.demarrer()
        bot.demarrer()
        assert bot._actif is True

    def test_arreter_desactive(self, bot: QFrame) -> None:
        """arreter() après demarrer() repasse _actif à False."""
        bot.demarrer()
        bot.arreter()
        assert bot._actif is False

    def test_arreter_idempotent(self, bot: QFrame) -> None:
        """arreter() deux fois : _actif reste False."""
        bot.demarrer()
        bot.arreter()
        bot.arreter()
        assert bot._actif is False

    def test_cycle_demarrer_arreter(self, bot: QFrame) -> None:
        """Cycle complet demarrer → arreter → demarrer fonctionne."""
        bot.demarrer()
        bot.arreter()
        bot.demarrer()
        assert bot._actif is True

    def test_demarrer_appelle_on_loop_tick(self, bot: QFrame, monkeypatch: MonkeyPatch) -> None:
        """demarrer() appelle _on_loop_tick() immédiatement (premier tick)."""
        from unittest.mock import MagicMock

        mock_tick = MagicMock()
        monkeypatch.setattr(bot, "_on_loop_tick", mock_tick)
        bot.demarrer()
        mock_tick.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
#  BotRecherche
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.qt_heavy
class TestBotRechercheInterrupteur(_MixinInterrupteur):
    """Interrupteur demarrer/arreter de BotRecherche."""

    @pytest.fixture
    def tmp_history_file(self, tmp_path: Path) -> Path:
        return tmp_path / "data" / "bot_recherche_history.json"

    @pytest.fixture
    def mock_settings(self, monkeypatch: MonkeyPatch, tmp_history_file: Path) -> None:
        import src.services.search_history as sh_module

        monkeypatch.setattr(sh_module, "HISTORY_FILE", tmp_history_file)
        monkeypatch.setattr(
            BotRecherche,
            "_update_connected_state",
            lambda self: None,
        )

    @pytest.fixture
    def bot(self, qapp: Any, mock_settings: None) -> Generator[BotRecherche, None, None]:
        instance = BotRecherche()
        yield instance
        instance.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════
#  BotTelechargement
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.qt_heavy
class TestBotTelechargementInterrupteur(_MixinInterrupteur):
    """Interrupteur demarrer/arreter de BotTelechargement."""

    @pytest.fixture
    def bot(self, qapp: Any) -> Generator[BotTelechargement, None, None]:
        instance = BotTelechargement()
        yield instance
        instance.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════
#  BotSurveillance
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.qt_heavy
class TestBotSurveillanceInterrupteur(_MixinInterrupteur):
    """Interrupteur demarrer/arreter de BotSurveillance."""

    @pytest.fixture(autouse=True)
    def _mock_eventbus(self, mocker) -> None:
        """Évite la connexion au vrai EventBus (qui nécessite une DB SQLite)."""
        mocker.patch.object(EventBus, "_instance", None)
        mocker.patch("src.services.event_bus.EventBus.__init__", return_value=None)
        mocker.patch("src.services.event_bus.EventBus.emit_event")
        mocker.patch("src.services.event_bus.EventBus.pause")
        mocker.patch("src.services.event_bus.EventBus.resume")
        mocker.patch.object(EventBus, "event_emitted", create=True)

    @pytest.fixture
    def bot(self, qapp: Any) -> Generator[BotSurveillance, None, None]:
        instance = BotSurveillance(center_zone=None)
        yield instance
        instance.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════
#  BotBibliotheque
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.qt_heavy
class TestBotBibliothequeInterrupteur(_MixinInterrupteur):
    """Interrupteur demarrer/arreter de BotBibliotheque."""

    @pytest.fixture(autouse=True)
    def _mock_deps(self, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
        """Mock les dépendances lourdes de BotBibliotheque.

        - EventBus isolé avec une base SQLite temporaire
        - Soulseek connecté
        - LibraryScanner safe
        - DB mockée
        - Scan désactivé
        """
        import src.services.app_config as ac

        # EventBus isolé
        db_file = tmp_path / "test_events.db"
        monkeypatch.setattr("src.services.event_bus._DB_PATH", db_file)
        EventBus._instance = None

        # Scan désactivé
        _orig_scan = ac.get("general.scan_on_start", True)
        ac.set("general.scan_on_start", False)

        # LibraryScanner safe (ne crée pas de vrai thread)
        from src.services.library_scanner import LibraryScanner

        def _safe_start_scan(self: LibraryScanner) -> None:
            self.scan_started.emit()

        monkeypatch.setattr(LibraryScanner, "start_scan", _safe_start_scan)

        # DB mockée
        mock_db = _MockDb()
        monkeypatch.setattr(
            "src.gui.widgets.bots.bot_bibliotheque.get_library_db",
            lambda: mock_db,
        )

        # Cache et dernier scan réinitialisés
        monkeypatch.setattr("src.gui.widgets.bots.bot_bibliotheque._STATS_CACHE", None)
        monkeypatch.setattr("src.gui.widgets.bots.bot_bibliotheque._LAST_SCAN", None)

        # Soulseek connecté
        from unittest.mock import patch, PropertyMock

        self._mock_slsk = patch("src.gui.widgets.bots.bot_bibliotheque.soulseek_service")
        mock_slsk = self._mock_slsk.start()
        type(mock_slsk).is_connected = PropertyMock(return_value=True)

        yield

        self._mock_slsk.stop()
        bus = EventBus._instance
        if bus is not None:
            bus.shutdown()
            EventBus._instance = None
        ac.set("general.scan_on_start", _orig_scan)

    @pytest.fixture
    def bot(self, qapp: Any) -> Generator[BotBibliotheque, None, None]:
        instance = BotBibliotheque()
        yield instance
        instance.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════
#  BotOptimiseur
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.qt_heavy
class TestBotOptimiseurInterrupteur(_MixinInterrupteur):
    """Interrupteur demarrer/arreter de BotOptimiseur."""

    @pytest.fixture(autouse=True)
    def _mock_eventbus(self, mocker) -> None:
        """Évite la connexion au vrai EventBus."""
        mocker.patch("src.services.event_bus.EventBus.emit_event")

    @pytest.fixture
    def bot(self, qapp: Any) -> Generator[BotOptimiseur, None, None]:
        instance = BotOptimiseur(center_zone=None)
        yield instance
        instance.deleteLater()


# ═══════════════════════════════════════════════════════════════════════════
#  Mock DB pour BotBibliotheque
# ═══════════════════════════════════════════════════════════════════════════


class _MockDb:
    """Mock minimal pour library_db.LibraryDB."""

    def __init__(self, stats: dict[str, int] | None = None) -> None:
        self._stats = stats or {"folders": 0, "files": 0, "audio": 0}

    def get_stats(self) -> dict[str, int]:
        return dict(self._stats)

    def add_folder(self, path: str, label: str = "") -> int:
        return 1

    def remove_folder(self, folder_id: int) -> None:
        return

    def get_folders(self) -> list[dict]:
        return []

    def get_files(self, **kwargs) -> list[dict]:
        return []
