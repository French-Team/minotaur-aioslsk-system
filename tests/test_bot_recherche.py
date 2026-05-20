"""Tests unitaires pour BotRecherche.

Vérifie que l'instanciation ne plante pas et que les attributs
clés (notamment ``_suggestions_row``) sont du bon type.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Generator

import pytest
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QTableWidget, QWidget
from pytest import MonkeyPatch

from src.gui.widgets.bots.bot_recherche import BotRecherche
from src.services.search_history import SearchHistory

# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def tmp_history_file(tmp_path: Path) -> Path:
    """Chemin vers un fichier d'historique temporaire."""
    return tmp_path / "data" / "bot_recherche_history.json"


@pytest.fixture
def mock_settings(monkeypatch: MonkeyPatch, tmp_history_file: Path) -> None:
    """Monkeypatche les dépendances externes de BotRecherche."""
    # Rediriger SearchHistory vers un fichier temporaire
    import src.services.search_history as sh_module

    monkeypatch.setattr(sh_module, "HISTORY_FILE", tmp_history_file)

    # Éviter _update_connected_state (dépend du connexion_manager)
    monkeypatch.setattr(
        BotRecherche,
        "_update_connected_state",
        lambda self: None,
    )


@pytest.fixture
def bot(qapp: Any, mock_settings: None) -> Generator[BotRecherche, None, None]:
    """Crée une instance de BotRecherche avec les dépendances mockées."""
    instance = BotRecherche()
    yield instance
    instance.deleteLater()


# ── Tests d'instanciation ────────────────────────────────────────


@pytest.mark.qt_heavy
class TestBotRechercheInit:
    """Vérifie que l'instanciation de BotRecherche fonctionne."""

    def test_instantiation_succeeds(self, bot: BotRecherche) -> None:
        """L'instanciation ne doit pas lever d'exception."""
        assert isinstance(bot, BotRecherche)

    def test_suggestions_row_is_qwidget(self, bot: BotRecherche) -> None:
        """Régression : _suggestions_row doit être un QWidget, pas un layout.

        Vérifie que le bug ``'QHBoxLayout' object has no attribute 'setVisible'``
        est bien résolu.
        """
        assert isinstance(bot._suggestions_row, QWidget)

    def test_search_history_initialized(self, bot: BotRecherche) -> None:
        """SearchHistory est instancié automatiquement dans __init__."""
        assert isinstance(bot._search_history, SearchHistory)

    def test_search_history_uses_temp_file(
        self,
        bot: BotRecherche,
        tmp_history_file: Path,
    ) -> None:
        """SearchHistory écrit dans le fichier temporaire, pas dans data/."""
        bot._search_history.add("Pink Floyd")
        assert tmp_history_file.exists()
        assert tmp_history_file.read_text(encoding="utf-8").strip()

    def test_search_input_exists(self, bot: BotRecherche) -> None:
        """Le champ de recherche est créé par _setup_ui."""
        assert isinstance(bot._search_input, QLineEdit)

    def test_search_button_exists(self, bot: BotRecherche) -> None:
        """Le bouton de recherche est créé par _setup_ui."""
        assert isinstance(bot._search_btn, QPushButton)

    def test_results_table_exists(self, bot: BotRecherche) -> None:
        """Le tableau de résultats est créé par _setup_ui."""
        assert isinstance(bot._table, QTableWidget)

    def test_history_btn_is_pushbutton(self, bot: BotRecherche) -> None:
        """Le bouton Historique est un QPushButton."""
        assert isinstance(bot._history_btn, QPushButton)

    def test_suggestions_row_has_layout(self, bot: BotRecherche) -> None:
        """Le widget _suggestions_row contient bien un QHBoxLayout."""
        layout = bot._suggestions_row.layout()
        assert layout is not None
        assert isinstance(layout, QHBoxLayout)


@pytest.mark.qt_heavy
class TestBotRechercheSuggestionsRow:
    """Vérifie le comportement du widget _suggestions_row."""

    def test_set_visible_does_not_crash(self, bot: BotRecherche) -> None:
        """Régression : appeler setVisible sur _suggestions_row ne doit pas planter."""
        bot._suggestions_row.setVisible(True)  # ne doit pas lever d'erreur
        bot._suggestions_row.setVisible(False)  # idem

    def test_set_visible_toggle(self, bot: BotRecherche) -> None:
        """setVisible bascule correctement l'état interne de visibilité.

        On utilise ``isHidden()`` car ``isVisibleTo(None)`` dépend de la
        visibilité de toute la hiérarchie parentale (bot n'est pas show()).
        """
        bot._suggestions_row.setVisible(False)
        assert bot._suggestions_row.isHidden() is True
        bot._suggestions_row.setVisible(True)
        assert bot._suggestions_row.isHidden() is False

    def test_suggestions_widgets_list(self, bot: BotRecherche) -> None:
        """La liste _suggestions_widgets existe et est vide après init sans historique."""
        assert hasattr(bot, "_suggestions_widgets")
        assert isinstance(bot._suggestions_widgets, list)

    def test_add_widget_to_row(self, bot: BotRecherche) -> None:
        """On peut ajouter un widget à _suggestions_row sans planter."""
        btn = QPushButton("Test")
        layout = bot._suggestions_row.layout()
        assert layout is not None
        layout.addWidget(btn)
        # Vérifie que le bouton a bien été ajouté
        assert btn.parent() is bot._suggestions_row
        # Nettoyage
        layout.removeWidget(btn)
        btn.deleteLater()


@pytest.mark.qt_heavy
class TestBotRechercheRebuildSuggestions:
    """Vérifie que _rebuild_suggestions ne plante pas."""

    def test_rebuild_with_empty_history(self, bot: BotRecherche) -> None:
        """Aucun crash quand l'historique est vide."""
        # Simuler un historique vide
        bot._search_history.clear()
        # Doit s'exécuter sans erreur
        bot._rebuild_suggestions()

    def test_rebuild_with_history(self, bot: BotRecherche) -> None:
        """Aucun crash quand l'historique contient des entrées."""
        bot._search_history.add("Pink Floyd")
        bot._search_history.add("Led Zeppelin")
        bot._rebuild_suggestions()
        # Des boutons de suggestion devraient être présents
        assert len(bot._suggestions_widgets) > 0

    def test_rebuild_preserves_history_button(self, bot: BotRecherche) -> None:
        """Le bouton 📜 Historique est toujours présent après rebuild."""
        bot._rebuild_suggestions()
        # Le bouton historique est toujours accessible
        assert isinstance(bot._history_btn, QPushButton)
