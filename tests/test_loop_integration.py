from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from src.gui.widgets.bots.bot_accueil import BotAccueil


class TestLoopStarterIntegration:
    @pytest.fixture
    def qapp(self) -> QApplication:
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    @pytest.fixture
    def bot_accueil(self, qapp: QApplication) -> BotAccueil:
        return BotAccueil()

    @pytest.fixture
    def loop_starter_mock(self) -> MagicMock:
        return MagicMock(return_value=True)

    @pytest.fixture
    def loop_stopper_mock(self) -> MagicMock:
        return MagicMock(return_value=True)

    # ── _start_loop tests ────────────────────────────────

    def test_set_loop_starter_injecte_callable(
        self, bot_accueil: BotAccueil, loop_starter_mock: MagicMock
    ) -> None:
        bot_accueil.set_loop_starter(loop_starter_mock)
        # Appeler _start_loop et vérifier que le starter est appelé
        result = bot_accueil._start_loop('Recherche')
        loop_starter_mock.assert_called_once_with('Recherche')
        assert result is True

    def test_start_loop_retourne_false_si_starter_none(self, bot_accueil: BotAccueil) -> None:
        result = bot_accueil._start_loop('Recherche')
        assert result is False

    def test_loop_starter_non_configure_logge_warning(
        self, bot_accueil: BotAccueil, caplog: Any
    ) -> None:
        import logging

        with caplog.at_level(logging.WARNING):
            bot_accueil._start_loop('Recherche')
        assert any('loop_starter non configuré' in msg for msg in caplog.messages)

    def test_do_start_loop_emet_loop_started_on_success(
        self, bot_accueil: BotAccueil, loop_starter_mock: MagicMock
    ) -> None:
        loop_starter_mock.return_value = True
        bot_accueil.set_loop_starter(loop_starter_mock)

        received: list[str] = []
        bot_accueil.loop_started.connect(received.append)

        bot_accueil._do_start_loop('Recherche')
        assert received == ['Recherche']

    def test_do_start_loop_nemet_pas_loop_started_on_failure(
        self, bot_accueil: BotAccueil, loop_starter_mock: MagicMock
    ) -> None:
        loop_starter_mock.return_value = False
        bot_accueil.set_loop_starter(loop_starter_mock)

        received: list[str] = []
        bot_accueil.loop_started.connect(received.append)

        result = bot_accueil._do_start_loop('Inconnu')
        assert result is False
        assert received == []

    # ── _stop_loop tests ────────────────────────────────

    def test_set_loop_stopper_injecte_callable(
        self, bot_accueil: BotAccueil, loop_stopper_mock: MagicMock
    ) -> None:
        bot_accueil.set_loop_stopper(loop_stopper_mock)
        result = bot_accueil._stop_loop('Recherche')
        loop_stopper_mock.assert_called_once_with('Recherche')
        assert result is True

    def test_stop_loop_retourne_false_si_stopper_none(self, bot_accueil: BotAccueil) -> None:
        result = bot_accueil._stop_loop('Recherche')
        assert result is False

    def test_loop_stopper_non_configure_logge_warning(
        self, bot_accueil: BotAccueil, caplog: Any
    ) -> None:
        import logging

        with caplog.at_level(logging.WARNING):
            bot_accueil._stop_loop('Recherche')
        assert any('loop_stopper non configuré' in msg for msg in caplog.messages)


class TestStartLoopActionType:
    @pytest.fixture
    def qapp(self) -> QApplication:
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    @pytest.fixture
    def bot_accueil(self, qapp: QApplication) -> BotAccueil:
        return BotAccueil()

    def test_execute_actions_action_start_loop(self, bot_accueil: BotAccueil) -> None:
        started: list[str] = []
        bot_accueil.loop_started.connect(started.append)

        starter = MagicMock(return_value=True)
        bot_accueil.set_loop_starter(starter)

        bot_accueil._execute_actions([{'type': 'start_loop', 'bot': 'Recherche'}])

        # Le starter doit être appelé
        starter.assert_called_once_with('Recherche')
        # Le signal doit être émis
        assert started == ['Recherche']

    def test_execute_actions_action_start_loop_delay(
        self, bot_accueil: BotAccueil, qapp: QApplication
    ) -> None:
        # start_loop avec delay=500 ms attend avant de démarrer la boucle
        started: list[str] = []
        bot_accueil.loop_started.connect(started.append)

        starter = MagicMock(return_value=True)
        bot_accueil.set_loop_starter(starter)

        bot_accueil._execute_actions([{'type': 'start_loop', 'bot': 'Recherche', 'delay': 500}])

        # Pas encore appelé immédiatement
        assert starter.call_count == 0
        assert started == []

    def test_execute_actions_action_start_loop_unknown_bot(
        self, bot_accueil: BotAccueil
    ) -> None:
        # start_loop avec bot inconnu ne crash pas (starter retourne False)
        started: list[str] = []
        bot_accueil.loop_started.connect(started.append)

        starter = MagicMock(return_value=False)
        bot_accueil.set_loop_starter(starter)

        # Ne doit pas lever d'exception
        bot_accueil._execute_actions([{'type': 'start_loop', 'bot': 'Inconnu'}])

        starter.assert_called_once_with('Inconnu')
        assert started == []  # Pas de signal car starter a retourné False

    def test_execute_actions_action_start_loop_and_navigate(
        self, bot_accueil: BotAccueil, qapp: QApplication
    ) -> None:
        # start_loop_and_navigate démarre la boucle puis navigue
        # On mock le starter pour qu'il retourne True
        starter = MagicMock(return_value=True)
        bot_accueil.set_loop_starter(starter)

        # On vérifie que le starter est appelé avec le bon bot
        bot_accueil._execute_actions(
            [{'type': 'start_loop_and_navigate', 'bot': 'Recherche', 'icon': '🔍'}]
        )

        starter.assert_called_once_with('Recherche')
        # Le starter a été appelé (la navigation est.async via QTimer.singleShot)


class TestStopLoopActionType:
    @pytest.fixture
    def qapp(self) -> QApplication:
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    @pytest.fixture
    def bot_accueil(self, qapp: QApplication) -> BotAccueil:
        return BotAccueil()

    def test_execute_actions_action_stop_loop(self, bot_accueil: BotAccueil) -> None:
        """stop_loop action type appelle le stopper avec le bon bot."""
        stopper = MagicMock(return_value=True)
        bot_accueil.set_loop_stopper(stopper)

        bot_accueil._execute_actions([{'type': 'stop_loop', 'bot': 'Recherche'}])

        stopper.assert_called_once_with('Recherche')

    def test_execute_actions_action_stop_loop_unknown_bot(self, bot_accueil: BotAccueil) -> None:
        """stop_loop avec bot inconnu ne crash pas (stopper retourne False)."""
        stopper = MagicMock(return_value=False)
        bot_accueil.set_loop_stopper(stopper)

        # Ne doit pas lever d'exception
        bot_accueil._execute_actions([{'type': 'stop_loop', 'bot': 'Inconnu'}])

        stopper.assert_called_once_with('Inconnu')

    def test_set_loop_stopper_injecte_callable(self, bot_accueil: BotAccueil) -> None:
        """set_loop_stopper injecte le stopper callable."""
        stopper_mock = MagicMock(return_value=True)
        bot_accueil.set_loop_stopper(stopper_mock)

        result = bot_accueil._stop_loop('Recherche')
        stopper_mock.assert_called_once_with('Recherche')
        assert result is True

    def test_stop_loop_retourne_false_si_stopper_none(self, bot_accueil: BotAccueil) -> None:
        """_stop_loop retourne False si loop_stopper n'est pas configuré."""
        result = bot_accueil._stop_loop('Recherche')
        assert result is False

    def test_stop_loop_retourne_false_si_stopper_none_log(self, bot_accueil: BotAccueil, caplog: Any) -> None:
        """_stop_loop sans stopper configure log un warning."""
        import logging

        with caplog.at_level(logging.WARNING):
            bot_accueil._stop_loop('Recherche')
        assert any('loop_stopper non configuré' in msg for msg in caplog.messages)


class TestStartLoopKNOWLEDGEIntegration:
    @pytest.fixture
    def qapp(self) -> QApplication:
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    @pytest.fixture
    def bot_accueil(self, qapp: QApplication) -> BotAccueil:
        return BotAccueil()

    def test_knowledge_entries_have_start_loop_action(self) -> None:
        from src.gui.widgets.bots.bot_accueil_knowledge import KNOWLEDGE

        bots_avec_navigate = [
            'chercher',
            'telechargement',
            'clients-actifs',
            'surveillance',
            'wishlist',
            'planificateur',
            'bibliotheque',
            'assistant',
        ]

        for entry_id in bots_avec_navigate:
            entry = KNOWLEDGE.get(entry_id, {})
            actions = entry.get('actions', [])
            # Vérifier qu'il y a au moins une action qui démarre la boucle
            # (start_loop OU start_loop_and_navigate)
            has_start = any(
                a.get('type') in ('start_loop', 'start_loop_and_navigate')
                for a in actions
            )
            has_navigate = any(
                a.get('type') in ('navigate', 'start_loop_and_navigate')
                for a in actions
            )
            assert has_start, f"Entry {entry_id!r} doit avoir une action de démarrage (start_loop ou start_loop_and_navigate)"
            assert has_navigate, f"Entry {entry_id!r} doit avoir une action de navigation (navigate ou start_loop_and_navigate)"

    def test_knowledge_start_loop_bot_names(self) -> None:
        from src.gui.widgets.bots.bot_accueil_knowledge import KNOWLEDGE

        for entry_id, entry in KNOWLEDGE.items():
            for action in entry.get('actions', []):
                if action.get('type') in ('start_loop', 'start_loop_and_navigate'):
                    start_bot = action.get('bot', '')
                    # Vérifier que le bot existe dans navigate aussi (si présente)
                    navigate_actions = [
                        a for a in entry.get('actions', [])
                        if a.get('type') in ('navigate', 'start_loop_and_navigate')
                    ]
                    if navigate_actions:
                        assert start_bot != '', f'start_loop bot ne doit pas être vide dans {entry_id!r}'

    def test_knowledge_start_loop_before_navigate(self) -> None:
        # start_loop doit apparaître AVANT navigate dans la liste des actions
        from src.gui.widgets.bots.bot_accueil_knowledge import KNOWLEDGE

        bots_avec_navigate = [
            'chercher',
            'telechargement',
            'clients-actifs',
            'surveillance',
            'wishlist',
            'planificateur',
            'bibliotheque',
            'assistant',
        ]

        for entry_id in bots_avec_navigate:
            entry = KNOWLEDGE.get(entry_id, {})
            actions = entry.get('actions', [])
            start_loop_idx = None
            navigate_idx = None
            for i, action in enumerate(actions):
                if action.get('type') == 'start_loop' and start_loop_idx is None:
                    start_loop_idx = i
                if action.get('type') in ('navigate', 'start_loop_and_navigate') and navigate_idx is None:
                    navigate_idx = i
            if start_loop_idx is not None and navigate_idx is not None:
                assert start_loop_idx < navigate_idx, (
                    f'start_loop doit apparaître avant navigate dans {entry_id!r}'
                )
            # Si toute l'entrée utilise start_loop_and_navigate (pas de start_loop séparé), c'est OK aussi
            has_combined = any(a.get('type') == 'start_loop_and_navigate' for a in actions)
            if has_combined and start_loop_idx is None:
                pass  # combined action remplace les deux — pas d'ordre à vérifier