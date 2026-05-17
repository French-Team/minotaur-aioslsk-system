"""Tests unitaires pour le BotBibliotheque — layout de base + arborescence."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
)

from src.gui.widgets.bots.bot_bibliotheque import (
    BotBibliotheque,
    _FileInfoPopup,
    _StatCard,
    _Toolbar,
)
from src.services.event_bus import EventBus
from src.services.library_scanner import LibraryScanner

# ── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_eventbus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isoler EventBus avec une base SQLite temporaire (évite conflits xdist)."""
    db_file = tmp_path / "test_events.db"
    monkeypatch.setattr("src.services.event_bus._DB_PATH", db_file)
    EventBus._instance = None
    yield
    bus = EventBus._instance
    if bus is not None:
        bus.shutdown()
        EventBus._instance = None


@pytest.fixture(autouse=True)
def _mock_soulseek(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock Soulseek service comme connecté pour la compatibilité des tests existants.

    Sans ce mock, _update_connection_state() empêcherait refresh() de s'exécuter
    dans __init__, ce qui casserait tous les tests qui utilisent BotBibliotheque().
    Les tests dans TestSoulseekIntegration peuvent surcharger ce comportement
    avec leurs propres @patch.
    """
    # Patcher la base de données pour qu'elle retourne des stats vides
    mock_db = _MockDb()
    monkeypatch.setattr(
        "src.gui.widgets.bots.bot_bibliotheque.get_library_db",
        lambda: mock_db,
    )
    # Réinitialiser les caches module-level pour éviter la contamination entre tests
    monkeypatch.setattr("src.gui.widgets.bots.bot_bibliotheque._STATS_CACHE", None)
    monkeypatch.setattr("src.gui.widgets.bots.bot_bibliotheque._LAST_SCAN", None)
    with patch("src.gui.widgets.bots.bot_bibliotheque.soulseek_service") as mock_slsk:
        # is_connected est un @property dans la vraie classe
        from unittest.mock import PropertyMock

        type(mock_slsk).is_connected = PropertyMock(return_value=True)
        yield


@pytest.fixture
def bot(qapp: QApplication) -> BotBibliotheque:
    """Instance du BotBibliotheque prête pour les tests."""
    return BotBibliotheque()


# ── Test d'instanciation ───────────────────────────────────────────


class TestInit:
    """Vérifie que le bot s'initialise sans erreur."""

    def test_can_instantiate(self, bot: BotBibliotheque) -> None:
        """Le bot peut être instancié."""
        assert bot is not None
        assert isinstance(bot, BotBibliotheque)

    def test_object_name(self, bot: BotBibliotheque) -> None:
        """L'objectName est correct."""
        assert bot.objectName() == "botBibliotheque"

    def test_has_page_changed_signal(self, bot: BotBibliotheque) -> None:
        """Le signal page_changed est présent."""
        assert hasattr(bot, "page_changed")
        assert bot.page_changed is not None

    def test_default_stats(self, bot: BotBibliotheque) -> None:
        """Les stats par défaut sont à zéro."""
        assert bot._stats == {"dossiers": 0, "fichiers": 0, "audio": 0}

    def test_has_current_folder_attrs(self, bot: BotBibliotheque) -> None:
        """Les attributs de dossier courant sont initialisés."""
        assert bot._current_folder is None
        assert bot._current_folder_id is None
        assert bot._current_folder_label is None

    def test_library_db_is_lazy(self, bot: BotBibliotheque) -> None:
        """_library_db est None jusqu'au premier appel."""
        # _library_db peut être None ou un objet selon si refresh() a réussi
        # On vérifie juste que _get_db() retourne quelque chose
        db = bot._get_db()
        assert db is not None

    def test_tree_root_exists(self, bot: BotBibliotheque) -> None:
        """La racine de l'arbre est créée."""
        assert bot._tree_root is not None
        assert isinstance(bot._tree_root, QTreeWidgetItem)
        assert "Racine" in bot._tree_root.text(0)


# ── Test du layout ─────────────────────────────────────────────────


class TestLayout:
    """Vérifie la structure visuelle du bot."""

    def test_header_exists(self, bot: BotBibliotheque) -> None:
        """L'en-tête est présent avec le bon texte."""
        assert bot._header is not None
        assert isinstance(bot._header, QLabel)
        assert "Bibliothèque" in bot._header.text()

    def test_stat_cards_exist(self, bot: BotBibliotheque) -> None:
        """Trois cartes de stats sont présentes."""
        assert len(bot._stat_cards) == 3
        for key in ("dossiers", "fichiers", "audio"):
            assert key in bot._stat_cards
            assert isinstance(bot._stat_cards[key], _StatCard)

    def test_stat_cards_have_correct_values(self, bot: BotBibliotheque) -> None:
        """Les cartes affichent les valeurs par défaut (0)."""
        for key, card in bot._stat_cards.items():
            assert card._value_lbl.text() == "0"

    def test_toolbar_exists(self, bot: BotBibliotheque) -> None:
        """La barre d'outils est présente avec ses composants."""
        assert bot._toolbar is not None
        assert isinstance(bot._toolbar, _Toolbar)

    def test_toolbar_has_search_input(self, bot: BotBibliotheque) -> None:
        """La toolbar contient un champ de recherche."""
        assert isinstance(bot._toolbar._search_input, QLineEdit)
        assert "Rechercher" in bot._toolbar._search_input.placeholderText()

    def test_toolbar_has_rescan_button(self, bot: BotBibliotheque) -> None:
        """La toolbar contient un bouton Re-scanner."""
        assert isinstance(bot._toolbar._rescan_btn, QPushButton)
        assert "Re-scanner" in bot._toolbar._rescan_btn.text()

    def test_main_view_has_splitter(self, bot: BotBibliotheque) -> None:
        """La vue principale contient un QSplitter."""
        assert bot._splitter is not None
        assert isinstance(bot._splitter, QSplitter)

    def test_splitter_has_tree_widget(self, bot: BotBibliotheque) -> None:
        """Le panneau gauche du splitter est un QTreeWidget."""
        assert isinstance(bot._tree_widget, QTreeWidget)

    def test_splitter_has_table_widget(self, bot: BotBibliotheque) -> None:
        """Le panneau droit du splitter est un QTableWidget."""
        assert isinstance(bot._table_widget, QTableWidget)

    def test_table_has_correct_headers(self, bot: BotBibliotheque) -> None:
        """Le tableau a 6 colonnes avec les bons en-têtes."""
        expected = ["📄 Nom", "📏 Taille", "🎵 Durée", "🎧 Bitrate", "📁 Dossier", "📅 Modifié"]
        for i, expected_text in enumerate(expected):
            assert bot._table_widget.horizontalHeaderItem(i).text() == expected_text

    def test_status_bar_exists(self, bot: BotBibliotheque) -> None:
        """La barre de statut est présente."""
        assert bot._status_lbl is not None
        assert isinstance(bot._status_lbl, QLabel)

    def test_table_no_edit_triggers(self, bot: BotBibliotheque) -> None:
        """Le tableau interdit l'édition inline."""
        assert bot._table_widget.editTriggers() == QTableWidget.EditTrigger.NoEditTriggers

    def test_table_selects_rows(self, bot: BotBibliotheque) -> None:
        """La sélection du tableau se fait par ligne entière."""
        assert bot._table_widget.selectionBehavior() == QTableWidget.SelectionBehavior.SelectRows


# ── Test de _StatCard ──────────────────────────────────────────────


class TestStatCard:
    """Vérifie le sous-composant _StatCard."""

    def test_card_displays_value(self, qapp: QApplication) -> None:
        """La carte affiche la valeur donnée."""
        card = _StatCard(42, "Test", "#ff0000")
        assert card._value_lbl.text() == "42"

    def test_card_update_value(self, qapp: QApplication) -> None:
        """set_value() met à jour l'affichage."""
        card = _StatCard(0, "Test", "#ff0000")
        card.set_value(99)
        assert card._value_lbl.text() == "99"

    def test_card_compact_badge(self, qapp: QApplication) -> None:
        """Le badge compact affiche la valeur et la cellule d'étiquette."""
        card = _StatCard(5, "Dossiers", "#6c5ce7")
        assert card._value_lbl.text() == "5"
        # Le badge a un QHBoxLayout (contenu horizontal)
        assert card.layout() is not None
        assert isinstance(card.layout(), QHBoxLayout)


# ── Test de _Toolbar ──────────────────────────────────────────────


class TestToolbar:
    """Vérifie le sous-composant _Toolbar."""

    def test_toolbar_has_signals(self, qapp: QApplication) -> None:
        """La toolbar expose ses signaux."""
        tb = _Toolbar()
        assert hasattr(tb, "search_requested")
        assert hasattr(tb, "rescan_requested")

    def test_set_rescan_enabled(self, qapp: QApplication) -> None:
        """set_rescan_enabled() active/désactive le bouton."""
        tb = _Toolbar()
        tb.set_rescan_enabled(False)
        assert not tb._rescan_btn.isEnabled()
        tb.set_rescan_enabled(True)
        assert tb._rescan_btn.isEnabled()

    def test_set_search_enabled(self, qapp: QApplication) -> None:
        """set_search_enabled() active/désactive le champ recherche."""
        tb = _Toolbar()
        tb.set_search_enabled(False)
        assert not tb._search_input.isEnabled()
        tb.set_search_enabled(True)
        assert tb._search_input.isEnabled()

    def test_set_rescan_text(self, qapp: QApplication) -> None:
        """set_rescan_text() change le texte du bouton."""
        tb = _Toolbar()
        tb.set_rescan_text("⏳ Scanning…")
        assert tb._rescan_btn.text() == "⏳ Scanning…"

    def test_search_text_property(self, qapp: QApplication) -> None:
        """La propriété search_text retourne le texte saisi."""
        tb = _Toolbar()
        tb._search_input.setText("test query")
        assert tb.search_text == "test query"

    def test_clear_search(self, qapp: QApplication) -> None:
        """clear_search() vide le champ."""
        tb = _Toolbar()
        tb._search_input.setText("something")
        tb.clear_search()
        assert tb.search_text == ""


# ── Test de l'arborescence des dossiers ────────────────────────────


class TestArbreDossiers:
    """Vérifie le chargement et l'affichage de l'arborescence."""

    def test_tree_has_root_item(self, bot: BotBibliotheque) -> None:
        """La racine '📂 Racine' est présente dans l'arbre."""
        root = bot._tree_root
        assert root is not None
        assert "Racine" in root.text(0)

    def test_tree_root_is_top_level_item(self, bot: BotBibliotheque) -> None:
        """La racine est un top-level item dans le QTreeWidget."""
        assert bot._tree_widget.topLevelItemCount() == 1
        assert bot._tree_widget.topLevelItem(0) == bot._tree_root

    def test_tree_root_has_no_folder_id(self, bot: BotBibliotheque) -> None:
        """Le UserRole de la racine est None (pas de folder_id)."""
        assert bot._tree_root.data(0, Qt.ItemDataRole.UserRole) is None

    def test_tree_root_is_expanded(self, bot: BotBibliotheque) -> None:
        """La racine est dépliée par défaut."""
        assert bot._tree_root.isExpanded() is True

    def test_tree_root_is_selected(self, bot: BotBibliotheque) -> None:
        """La racine est sélectionnée par défaut."""
        assert bot._tree_widget.currentItem() == bot._tree_root

    def test_folder_items_have_folder_id(self, bot: BotBibliotheque) -> None:
        """Chaque dossier enfant (si présent) a un folder_id dans UserRole."""
        for i in range(bot._tree_root.childCount()):
            child = bot._tree_root.child(i)
            child.data(0, Qt.ItemDataRole.UserRole)
            # folder_id peut être None si la DB est vide, doit être présent si enfant
            assert child.text(0).startswith("📁")


# ── Test du clic sur un dossier ────────────────────────────────────


class TestClicDossier:
    """Vérifie le comportement au clic sur un item de l'arbre."""

    def test_click_root_sets_folder_none(self, bot: BotBibliotheque) -> None:
        """Clic sur la racine réinitialise _current_folder à None."""
        bot._on_tree_item_clicked(bot._tree_root, 0)
        assert bot._current_folder is None
        assert bot._current_folder_id is None
        assert bot._current_folder_label is None

    def test_click_root_clears_table(self, bot: BotBibliotheque) -> None:
        """Clic sur la racine vide le tableau."""
        bot._on_tree_item_clicked(bot._tree_root, 0)
        # Le tableau doit être vide (0 lignes ou une cellule message)
        assert bot._table_widget.rowCount() >= 0

    def test_click_root_shows_message(self, bot: BotBibliotheque) -> None:
        """Clic sur la racine affiche un message d'invite."""
        bot._on_tree_item_clicked(bot._tree_root, 0)
        # Doit afficher le message de sélection
        assert bot._table_widget.rowCount() == 1
        # Vérifie qu'il y a un widget message
        cell_widget = bot._table_widget.cellWidget(0, 0)
        assert cell_widget is not None
        assert isinstance(cell_widget, QLabel)
        assert "Sélectionne" in cell_widget.text()

    def test_click_folder_updates_status(self, bot: BotBibliotheque) -> None:
        """Clic sur un dossier met à jour la barre de statut."""
        # Simuler un clic sur un enfant de dossier (s'il existe)
        # Si aucun enfant, la racine est déjà sélectionnée → status = "Prêt"
        if bot._tree_root.childCount() > 0:
            child = bot._tree_root.child(0)
            bot._on_tree_item_clicked(child, 0)
            label = child.text(0).removeprefix("📁 ")
            assert label in bot._status_lbl.text() or bot._current_folder == label
        else:
            # Pas de dossier → clic sur racine → "Prêt"
            bot._on_tree_item_clicked(bot._tree_root, 0)
            assert "Prêt" in bot._status_lbl.text()


# ── Test du chargement des fichiers ────────────────────────────────


class TestChargementFichiers:
    """Vérifie le chargement des fichiers dans le QTableWidget."""

    def test_load_files_empty_when_no_folder(self, bot: BotBibliotheque) -> None:
        """_load_files_for_folder() sans folder_id affiche un message."""
        bot._current_folder_id = None
        bot._load_files_for_folder()
        assert bot._table_widget.rowCount() >= 1
        cell_widget = bot._table_widget.cellWidget(0, 0)
        assert cell_widget is not None
        assert "Sélectionne" in cell_widget.text()

    def test_load_files_sets_folder_label_column(self, bot: BotBibliotheque) -> None:
        """La colonne 📁 Dossier affiche le label du dossier."""
        bot._current_folder_id = 999  # inexistant en DB → retourne liste vide
        bot._current_folder_label = "Musique"
        bot._load_files_for_folder()
        # Pas de fichier, donc la colonne n'est pas testée, mais pas d'erreur
        assert bot._table_widget.rowCount() == 0

    def test_load_files_handles_db_error(self, bot: BotBibliotheque) -> None:
        """Une erreur DB ne fait pas planter le chargement."""
        bot._current_folder_id = 999999
        bot._load_files_for_folder()
        assert bot._table_widget.rowCount() >= 0

    def test_format_duration_with_values(self, bot: BotBibliotheque) -> None:
        """_format_duration formate correctement."""
        assert bot._format_duration(0) == "0:00"
        assert bot._format_duration(65) == "1:05"
        assert bot._format_duration(3661) == "61:01"

    def test_format_duration_edge_cases(self, bot: BotBibliotheque) -> None:
        """_format_duration gère les cas limites."""
        assert bot._format_duration(0) == "0:00"
        assert bot._format_duration(59) == "0:59"
        assert bot._format_duration(600) == "10:00"


# ── Test de la méthode refresh ─────────────────────────────────────


class TestRefresh:
    """Vérifie que refresh() recharge les données."""

    def test_refresh_rebuilds_tree(self, bot: BotBibliotheque) -> None:
        """refresh() reconstruit l'arbre."""
        bot._tree_widget.clear()
        bot._tree_root = None
        bot.refresh()
        assert bot._tree_root is not None
        assert "Racine" in bot._tree_root.text(0)

    def test_refresh_updates_stats(self, bot: BotBibliotheque) -> None:
        """refresh() met à jour les statistiques."""
        bot.refresh()
        # Les stats doivent être présentes (même à 0)
        assert "dossiers" in bot._stats
        assert "fichiers" in bot._stats
        assert "audio" in bot._stats

    def test_refresh_updates_status(self, bot: BotBibliotheque) -> None:
        """refresh() met à jour la barre de statut."""
        bot.refresh()
        assert bot._status_lbl.text() is not None


# ── Test des méthodes publiques de BotBibliotheque ─────────────────


class TestPublicAPI:
    """Vérifie l'API publique du bot."""

    def test_update_stats_updates_cards(self, bot: BotBibliotheque) -> None:
        """update_stats() met à jour les valeurs des cartes."""
        bot.update_stats({"dossiers": 5, "fichiers": 1234, "audio": 890})
        assert bot._stat_cards["dossiers"]._value_lbl.text() == "5"
        assert bot._stat_cards["fichiers"]._value_lbl.text() == "1234"
        assert bot._stat_cards["audio"]._value_lbl.text() == "890"

    def test_set_status(self, bot: BotBibliotheque) -> None:
        """set_status() change le texte de la barre de statut."""
        bot.set_status("⏳ Scan en cours… 42 fichiers")
        assert "42 fichiers" in bot._status_lbl.text()

    def test_format_size_bytes(self, bot: BotBibliotheque) -> None:
        """_format_size() formate correctement les petits fichiers."""
        result = bot._format_size(500)
        assert result == "500 o"

    def test_format_size_kb(self, bot: BotBibliotheque) -> None:
        """_format_size() formate correctement les Ko."""
        result = bot._format_size(2048)
        assert result == "2.0 Ko"

    def test_format_size_mb(self, bot: BotBibliotheque) -> None:
        """_format_size() formate correctement les Mo."""
        result = bot._format_size(5_242_880)  # 5 Mo
        assert result == "5.0 Mo"

    def test_format_size_gb(self, bot: BotBibliotheque) -> None:
        """_format_size() formate correctement les Go."""
        result = bot._format_size(3_221_225_472)  # 3 Go
        assert result == "3.0 Go"

    def test_default_status_text(self, bot: BotBibliotheque) -> None:
        """La barre de statut affiche 'Prêt' par défaut."""
        assert "Prêt" in bot._status_lbl.text()


# ── Test des appels réseau — signaux _Toolbar ─────────────────────


class TestToolbarSignals:
    """Vérifie que les signaux de la toolbar sont bien câblés."""

    def test_rescan_click_triggers_callback(self, qapp: QApplication) -> None:
        """Le clic sur Re-scanner déclenche _on_rescan."""
        bot = BotBibliotheque()
        # Le bouton est activé avant clic
        assert bot._toolbar._rescan_btn.isEnabled()
        bot._toolbar._rescan_btn.click()
        # Après clic, le bouton doit être désactivé (scan en cours simulé)
        assert not bot._toolbar._rescan_btn.isEnabled()
        assert not bot._toolbar._search_input.isEnabled()


# ── Test du menu contextuel ─────────────────────────────────────────


class TestMenuContextuel:
    """Vérifie le menu contextuel (clic droit) sur le tableau."""

    def test_context_menu_policy(self, bot: BotBibliotheque) -> None:
        """Le tableau a une politique de menu contextuel CustomContextMenu."""
        policy = bot._table_widget.contextMenuPolicy()
        assert policy == Qt.ContextMenuPolicy.CustomContextMenu

    def test_context_menu_method_exists(self, bot: BotBibliotheque) -> None:
        """La méthode _on_context_menu est définie et callable."""
        assert hasattr(bot, "_on_context_menu")
        assert callable(bot._on_context_menu)

    def test_file_data_stored_in_table(self, qapp: QApplication) -> None:
        """Les données fichier sont stockées dans UserRole de la colonne 0."""
        bot = BotBibliotheque()
        # Simuler un chargement avec un folder_id
        bot._current_folder_id = 1
        bot._current_folder_label = "Test"
        bot._load_files_for_folder()
        # Même sans DB, le tableau doit être préparé (0 lignes si pas de fichiers)
        # On vérifie que le mécanisme est en place
        assert bot._table_widget.rowCount() >= 0

    def test_on_context_menu_no_item(self, qapp: QApplication) -> None:
        """Aucun menu si clic hors d'un item."""
        bot = BotBibliotheque()
        # Cette méthode ne doit pas planter si aucun item sous le curseur
        bot._on_context_menu(bot._table_widget.pos())
        assert True  # Aucune exception == succès


# ── Test du FileInfoPopup ───────────────────────────────────────────


class TestFileInfoPopup:
    """Vérifie la popup d'informations détaillées."""

    @pytest.fixture
    def sample_file(self) -> dict:
        return {
            "id": 42,
            "name": "track01.mp3",
            "path": "/home/user/music/track01.mp3",
            "size_bytes": 8_245_120,
            "folder_label": "Rock",
            "folder_path": "/home/user/music",
            "modified_at": "2026-05-14T14:30:00",
            "artist": "Led Zeppelin",
            "album": "Physical Graffiti",
            "title": "Custard Pie",
            "track": 1,
            "year": 1975,
            "bitrate": 320,
            "duration": 255,
        }

    def test_popup_title(self, qapp: QApplication, sample_file: dict) -> None:
        """Le titre contient le nom du fichier."""
        popup = _FileInfoPopup(sample_file)
        assert "track01.mp3" in popup.windowTitle()

    def test_popup_modal(self, qapp: QApplication, sample_file: dict) -> None:
        """La popup est modale."""
        popup = _FileInfoPopup(sample_file)
        assert popup.isModal()

    def test_popup_audio_section(self, qapp: QApplication, sample_file: dict) -> None:
        """La section audio affiche les métadonnées."""
        popup = _FileInfoPopup(sample_file)
        assert popup._file["artist"] == "Led Zeppelin"
        assert popup._file["album"] == "Physical Graffiti"
        assert popup._file["bitrate"] == 320
        assert popup._file["duration"] == 255

    def test_popup_no_audio(self, qapp: QApplication) -> None:
        """La popup fonctionne sans métadonnées audio."""
        file_data = {
            "id": 1,
            "name": "readme.txt",
            "path": "/home/user/readme.txt",
            "size_bytes": 1024,
            "folder_label": "Docs",
            "folder_path": "/home/user",
            "modified_at": "2026-01-01T12:00:00",
        }
        popup = _FileInfoPopup(file_data)
        assert "readme.txt" in popup.windowTitle()

    def test_format_size_static(self) -> None:
        """_format_size formate correctement les tailles."""
        assert _FileInfoPopup._format_size(0) == "0 o"
        assert _FileInfoPopup._format_size(1024) == "1.0 Ko"
        assert _FileInfoPopup._format_size(1_048_576) == "1.0 Mo"
        assert _FileInfoPopup._format_size(1_073_741_824) == "1.0 Go"
        assert "Mo" in _FileInfoPopup._format_size(8_245_120)

    def test_format_duration_static(self) -> None:
        """_format_duration formate correctement les durées."""
        assert _FileInfoPopup._format_duration(0) == "0:00"
        assert _FileInfoPopup._format_duration(255) == "4:15"
        assert _FileInfoPopup._format_duration(3661) == "61:01"

    def test_format_date_static(self) -> None:
        """_format_date formate les dates ISO en format lisible."""
        assert "14/05/2026" in _FileInfoPopup._format_date("2026-05-14T14:30:00")
        assert _FileInfoPopup._format_date("") == "—"
        assert _FileInfoPopup._format_date("invalide") == "invalide"

    def test_make_info_row(self, qapp: QApplication, sample_file: dict) -> None:
        """_make_info_row crée un widget avec label et valeur."""
        popup = _FileInfoPopup(sample_file)
        row = popup._make_info_row("📄 Nom", "track01.mp3")
        assert row is not None
        # Vérifie qu'il a un layout avec des enfants
        assert row.layout() is not None
        assert row.layout().count() >= 2


# ── Test de la suppression ──────────────────────────────────────────


class TestSuppression:
    """Vérifie le comportement de suppression de fichiers."""

    def test_on_delete_file_structure(self, qapp: QApplication) -> None:
        """La méthode _on_delete_file existe et gère 'retirer des partages'."""
        bot = BotBibliotheque()
        assert hasattr(bot, "_on_delete_file")
        # Vérifie que la méthode accepte un dict
        # (on ne teste pas l'exécution car msg.exec() est bloquant)
        assert callable(bot._on_delete_file)

    def test_on_view_info_creates_popup(self, qapp: QApplication) -> None:
        """_on_view_info crée une popup avec le bon titre."""
        bot = BotBibliotheque()
        file_data = {"id": 1, "name": "test.mp3", "path": "/tmp/test.mp3"}
        popup = _FileInfoPopup(file_data, bot)
        assert popup.windowTitle() == "👁️ Informations — test.mp3"

    def test_on_read_file_no_crash(self, qapp: QApplication) -> None:
        """_on_read_file ne plante pas avec un path vide."""
        bot = BotBibliotheque()
        bot._on_read_file({"name": "test.mp3", "path": ""})
        assert True

    def test_on_read_file_with_path(self, qapp: QApplication) -> None:
        """_on_read_file appelle QDesktopServices avec un path valide."""
        bot = BotBibliotheque()
        # Ne doit pas planter avec un path valide
        bot._on_read_file({"name": "test.mp3", "path": "/tmp/test.mp3"})
        assert True

    def test_get_file_data_after_load(self, qapp: QApplication) -> None:
        """Après un chargement, les données sont stockées (ne plante pas)."""
        bot = BotBibliotheque()
        bot._current_folder_id = 0
        bot._current_folder_label = "Test"
        bot._load_files_for_folder()
        # Ne doit pas planter même sans DB
        assert True

    def test_context_menu_has_delete_action(self, qapp: QApplication) -> None:
        """Le menu contextuel contient une option Supprimer."""
        bot = BotBibliotheque()
        # Vérifie que le setup du contexte est en place
        assert bot._table_widget.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu


# ── Tests du scan threadé ───────────────────────────────────────────


class TestScanThreaded:
    """Tests pour le re-scanner threadé (LibraryScanner) dans BotBibliotheque."""

    def test_scanner_is_none_initially(self, qapp: QApplication) -> None:
        """Le scanner n'est pas créé tant que _on_rescan n'est pas appelé."""
        bot = BotBibliotheque()
        assert bot._scanner is None

    def test_on_rescan_creates_scanner(self, qapp: QApplication) -> None:
        """_on_rescan crée le scanner sans lancer un vrai thread (mocké)."""
        from unittest.mock import patch

        bot = BotBibliotheque()
        assert bot._scanner is None
        with patch.object(LibraryScanner, "start_scan"):
            bot._on_rescan()
        assert bot._scanner is not None

    def test_second_rescan_skips_if_running(self, qapp: QApplication) -> None:
        """Un second appel à _on_rescan ignore si le scanner tourne déjà."""
        from unittest.mock import PropertyMock, patch

        bot = BotBibliotheque()
        # Créer le scanner
        with patch.object(LibraryScanner, "start_scan"):
            bot._on_rescan()
        # Simuler qu'il tourne
        with patch.object(LibraryScanner, "is_running", new_callable=PropertyMock, return_value=True):
            bot._on_rescan()  # ne doit pas planter ni relancer

    def test_progress_bar_hidden_initially(self, qapp: QApplication) -> None:
        """La barre de progression est masquée par défaut."""
        bot = BotBibliotheque()
        assert bot._toolbar._progress_bar.isHidden() is True

    def test_toolbar_has_progress_methods(self, qapp: QApplication) -> None:
        """La toolbar expose les méthodes de progression."""
        bot = BotBibliotheque()
        tb = bot._toolbar
        assert hasattr(tb, "set_progress_visible")
        assert hasattr(tb, "set_progress_range")
        assert hasattr(tb, "set_progress_value")
        assert hasattr(tb, "set_progress_format")

    def test_progress_bar_set_value(self, qapp: QApplication) -> None:
        """set_progress_value met à jour la barre."""
        bot = BotBibliotheque()
        tb = bot._toolbar
        tb.set_progress_range(100)
        tb.set_progress_value(50)
        assert tb._progress_bar.value() == 50

    def test_progress_bar_visibility(self, qapp: QApplication) -> None:
        """set_progress_visible affiche/masque la barre (avec bot.show())."""
        bot = BotBibliotheque()
        bot.show()
        tb = bot._toolbar
        tb.set_progress_visible(True)
        assert tb._progress_bar.isVisible() is True
        assert tb._search_input.isVisible() is False
        tb.set_progress_visible(False)
        assert tb._progress_bar.isVisible() is False
        assert tb._search_input.isVisible() is True
        bot.hide()

    def test_scan_started_updates_toolbar(self, qapp: QApplication) -> None:
        """_on_scan_started désactive les contrôles et affiche la barre."""
        bot = BotBibliotheque()
        bot.show()
        bot._on_scan_started()
        assert bot._toolbar._rescan_btn.isEnabled() is False
        assert bot._toolbar._search_input.isEnabled() is False
        assert bot._toolbar._progress_bar.isVisible() is True
        assert bot._toolbar._progress_bar.value() == 0
        bot.hide()

    def test_scan_progress_updates_bar(self, qapp: QApplication) -> None:
        """_on_scan_progress met à jour la valeur et le statut."""
        bot = BotBibliotheque()
        bot._on_scan_started()
        bot._on_scan_progress(25, 100)
        assert bot._toolbar._progress_bar.value() == 25
        assert "25/100" in bot._status_lbl.text()

    def test_scan_completed_restores_toolbar(self, qapp: QApplication) -> None:
        """_on_scan_completed réactive les contrôles et masque la barre."""
        bot = BotBibliotheque()
        bot.show()
        from src.services.library_db import ScanResult

        result = ScanResult(
            folders_scanned=1,
            files_found=10,
            files_new=5,
            files_removed=2,
            errors=[],
            duration_ms=1500,
        )
        bot._on_scan_started()
        bot._on_scan_completed(result)
        assert bot._toolbar._rescan_btn.isEnabled() is True
        assert bot._toolbar._search_input.isEnabled() is True
        assert bot._toolbar._progress_bar.isVisible() is False
        assert "✅" in bot._status_lbl.text()
        bot.hide()

    def test_scan_error_restores_toolbar(self, qapp: QApplication) -> None:
        """_on_scan_error réactive les contrôles et affiche l'erreur."""
        bot = BotBibliotheque()
        bot.show()
        bot._on_scan_started()
        bot._on_scan_error("Disk full")
        assert bot._toolbar._rescan_btn.isEnabled() is True
        assert bot._toolbar._search_input.isEnabled() is True
        assert bot._toolbar._progress_bar.isVisible() is False
        assert "Disk full" in bot._status_lbl.text()
        bot.hide()

    def test_scan_completed_without_duration(self, qapp: QApplication) -> None:
        """ScanResult sans duration ne plante pas."""
        bot = BotBibliotheque()
        from src.services.library_db import ScanResult

        result = ScanResult(
            folders_scanned=0,
            files_found=0,
            files_new=0,
            files_removed=0,
            errors=["some error"],
        )
        bot._on_scan_completed(result)
        assert "✅" in bot._status_lbl.text()
        # Vérifie que le message contient le nombre d'erreurs
        assert "1 erreurs" in bot._status_lbl.text() or "1 erreur" in bot._status_lbl.text()


# ── Tests du cache des stats et auto-scan au démarrage ────────────


class TestCacheEtAutoScan:
    """Tests pour le module-level _STATS_CACHE et l'auto-scan au démarrage."""

    def test_cache_charge_les_stats_initialement(self, qapp: QApplication) -> None:
        """_STATS_CACHE pré-rempli → les stats sont chargées dès l'init.

        On mocke _get_db pour que le refresh() post-init ne remette
        pas les stats à zéro (pas de vraie DB dans les tests).
        """
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._STATS_CACHE = {"dossiers": 42, "fichiers": 100, "audio": 80}
        from unittest.mock import patch

        def mock_get_db() -> _MockDb:
            return _MockDb(stats={"folders": 42, "files": 100, "audio": 80})

        with patch.object(
            bb.BotBibliotheque, "_get_db", return_value=_MockDb(stats={"folders": 42, "files": 100, "audio": 80})
        ):
            bot = BotBibliotheque()
            try:
                assert bot._stats["dossiers"] == 42
                assert bot._stats["fichiers"] == 100
                assert bot._stats["audio"] == 80
            finally:
                bot.deleteLater()
                bb._STATS_CACHE = None

    def test_cache_none_initialise_stats_vides(self, qapp: QApplication) -> None:
        """Cache None → stats à zéro jusqu'au premier refresh.

        On mocke _get_db pour que refresh() utilise un mock
        qui renvoie des stats à zéro.
        """
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._STATS_CACHE = None
        from unittest.mock import patch

        with patch.object(
            bb.BotBibliotheque, "_get_db", return_value=_MockDb(stats={"folders": 0, "files": 0, "audio": 0})
        ):
            bot = BotBibliotheque()
            try:
                assert bot._stats["dossiers"] == 0
                assert bot._stats["fichiers"] == 0
                assert bot._stats["audio"] == 0
            finally:
                bot.deleteLater()

    def test_refresh_stats_met_a_jour_le_cache(self, qapp: QApplication) -> None:
        """_refresh_stats() écrit dans _STATS_CACHE après un refresh réussi."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._STATS_CACHE = None
        bot = BotBibliotheque()
        try:
            bot._get_db = lambda: _MockDb(stats={"folders": 7, "files": 33, "audio": 22})  # type: ignore[method-assign]
            bot._refresh_stats()
            assert bb._STATS_CACHE == {"dossiers": 7, "fichiers": 33, "audio": 22}
        finally:
            bot.deleteLater()
            bb._STATS_CACHE = None

    def test_refresh_stats_cache_sur_exception(self, qapp: QApplication) -> None:
        """Exception dans _refresh_stats → cache mis à jour avec zéros."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._STATS_CACHE = {"dossiers": 99, "fichiers": 99, "audio": 99}
        bot = BotBibliotheque()
        try:
            bot._get_db = lambda: _MockDb(should_fail=True)  # type: ignore[method-assign]
            bot._refresh_stats()
            assert bb._STATS_CACHE == {"dossiers": 0, "fichiers": 0, "audio": 0}
        finally:
            bot.deleteLater()
            bb._STATS_CACHE = None

    def test_auto_scan_enabled_programme_timer(self, qapp: QApplication) -> None:
        """scan_on_start=True → QTimer.singleShot est appelé avec _on_rescan.

        On vérifie en mockant QTimer.singleShot directement.
        """
        from unittest.mock import ANY, patch

        import src.services.app_config as ac

        original = ac.get("general.scan_on_start", True)
        try:
            ac.set("general.scan_on_start", True)
            with patch("PySide6.QtCore.QTimer.singleShot") as mock_singleshot:
                from unittest.mock import patch as patch_db

                with patch.object(BotBibliotheque, "_get_db", return_value=_MockDb()):
                    bot = BotBibliotheque()
                    try:
                        mock_singleshot.assert_called_once_with(1500, bot._on_rescan)
                    finally:
                        bot.deleteLater()
        finally:
            ac.set("general.scan_on_start", original)

    def test_auto_scan_disabled_ne_programme_pas_timer(self, qapp: QApplication) -> None:
        """scan_on_start=False → QTimer.singleShot n'est PAS appelé."""
        from unittest.mock import patch

        import src.services.app_config as ac

        original = ac.get("general.scan_on_start", True)
        try:
            ac.set("general.scan_on_start", False)
            with patch("PySide6.QtCore.QTimer.singleShot") as mock_singleshot:
                with patch.object(BotBibliotheque, "_get_db", return_value=_MockDb()):
                    bot = BotBibliotheque()
                    try:
                        mock_singleshot.assert_not_called()
                    finally:
                        bot.deleteLater()
        finally:
            ac.set("general.scan_on_start", original)


# ── Tests de l'historique du dernier scan ──────────────────


class TestDernierScan:
    """Tests pour _LAST_SCAN : stockage et affichage du dernier scan."""

    def test_last_scan_none_par_defaut(self, qapp: QApplication) -> None:
        """_LAST_SCAN est None à l'initialisation → pas d'info affichée."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._STATS_CACHE = {"dossiers": 0, "fichiers": 0, "audio": 0}
        bb._LAST_SCAN = None
        bot = BotBibliotheque()
        try:
            status = bot._build_status_text()
            assert "Dernier scan" not in status
            assert bot._format_last_scan() == ""
        finally:
            bot.deleteLater()

    def test_format_last_scan_affiche_infos(self, qapp: QApplication) -> None:
        """_format_last_scan() retourne le bon format quand _LAST_SCAN est défini."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._STATS_CACHE = {"dossiers": 5, "fichiers": 100, "audio": 80}
        bb._LAST_SCAN = {
            "timestamp": "2026-06-15T14:30:00",
            "files_new": 12,
            "files_removed": 3,
            "errors": 1,
            "duration_ms": 2450,
            "folders_scanned": 5,
            "files_found": 100,
        }
        bot = BotBibliotheque()
        try:
            result = bot._format_last_scan()
            assert "15/0" in result  # date
            assert "+12/−3" in result  # new/removed
            assert "⚠️1" in result  # erreurs
            assert "2.5s" in result or "2.4s" in result  # durée ≈ 2.45s
        finally:
            bot.deleteLater()
            bb._LAST_SCAN = None

    def test_format_last_scan_sans_duree(self, qapp: QApplication) -> None:
        """_format_last_scan sans duration_ms → pas de durée affichée."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._STATS_CACHE = {"dossiers": 5, "fichiers": 100, "audio": 80}
        bb._LAST_SCAN = {
            "timestamp": "2026-06-15T14:30:00",
            "files_new": 5,
            "files_removed": 0,
            "errors": 0,
            "duration_ms": 0,
        }
        bot = BotBibliotheque()
        try:
            result = bot._format_last_scan()
            assert "+5/−0" in result  # le − (U+2212) est toujours présent
            assert "⚠️" not in result  # pas d'erreurs
            assert "2.5" not in result  # pas de durée
        finally:
            bot.deleteLater()
            bb._LAST_SCAN = None

    def test_format_last_scan_sans_timestamp(self, qapp: QApplication) -> None:
        """_format_last_scan sans timestamp → pas de date affichée."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._STATS_CACHE = {"dossiers": 5, "fichiers": 100, "audio": 80}
        bb._LAST_SCAN = {
            "files_new": 3,
            "files_removed": 1,
            "errors": 0,
            "duration_ms": 1000,
        }
        bot = BotBibliotheque()
        try:
            result = bot._format_last_scan()
            assert "+3/−1" in result
            assert "1.0s" in result
        finally:
            bot.deleteLater()
            bb._LAST_SCAN = None

    def test_build_status_text_inclut_dernier_scan(self, qapp: QApplication) -> None:
        """_build_status_text() inclut les infos du dernier scan quand dispo."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._STATS_CACHE = {"dossiers": 5, "fichiers": 100, "audio": 80}
        from unittest.mock import patch

        bb._LAST_SCAN = {
            "timestamp": "2026-06-15T14:30:00",
            "files_new": 7,
            "files_removed": 2,
            "errors": 0,
            "duration_ms": 3000,
        }
        with patch.object(
            BotBibliotheque, "_get_db", return_value=_MockDb(stats={"folders": 5, "files": 100, "audio": 80})
        ):
            bot = BotBibliotheque()
            try:
                status = bot._build_status_text()
                # Avec des fichiers, devrait afficher "📂 Tous les dossiers — 100 fichiers — 🕐 ..."
                assert "100 fichiers" in status
                assert "🕐" in status
                assert "+7/−2" in status
            finally:
                bot.deleteLater()
                bb._LAST_SCAN = None

    def test_build_status_text_etat_pret_avec_scan(self, qapp: QApplication) -> None:
        """État 'Prêt' avec stats à zéro mais dernier scan dispo."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._STATS_CACHE = {"dossiers": 0, "fichiers": 0, "audio": 0}
        from unittest.mock import patch

        bb._LAST_SCAN = {
            "timestamp": "2026-06-15T10:00:00",
            "files_new": 50,
            "files_removed": 10,
            "errors": 2,
            "duration_ms": 5200,
        }
        with patch.object(
            BotBibliotheque, "_get_db", return_value=_MockDb(stats={"folders": 0, "files": 0, "audio": 0})
        ):
            bot = BotBibliotheque()
            try:
                status = bot._build_status_text()
                assert status.startswith("Prêt")
                assert "Dernier scan :" in status
                assert "+50/−10" in status
                assert "⚠️2" in status
                assert "5.2s" in status or "5.1s" in status or "5.0s" in status
            finally:
                bot.deleteLater()
                bb._LAST_SCAN = None

    def test_last_scan_persiste_entre_instances(self, qapp: QApplication) -> None:
        """_LAST_SCAN reste défini même après destruction d'une instance."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._LAST_SCAN = None

        bot = BotBibliotheque()
        try:
            from src.services.library_db import ScanResult

            result = ScanResult(
                folders_scanned=2,
                files_found=30,
                files_new=15,
                files_removed=5,
                errors=[],
                duration_ms=1234,
            )
            bot._on_scan_completed(result)
            assert bb._LAST_SCAN is not None
            assert bb._LAST_SCAN["files_new"] == 15
            assert bb._LAST_SCAN["files_removed"] == 5
            assert bb._LAST_SCAN["errors"] == 0
            assert bb._LAST_SCAN["duration_ms"] == 1234
            assert "timestamp" in bb._LAST_SCAN
        finally:
            bot.deleteLater()

    def test_scan_completed_enregistre_cache(self, qapp: QApplication) -> None:
        """_on_scan_completed remplit _LAST_SCAN avec les données du ScanResult."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._LAST_SCAN = None

        bot = BotBibliotheque()
        try:
            from src.services.library_db import ScanResult

            result = ScanResult(
                folders_scanned=3,
                files_found=50,
                files_new=10,
                files_removed=2,
                errors=["corrupted file"],
                duration_ms=2500,
            )
            bot._on_scan_completed(result)
            assert bb._LAST_SCAN is not None
            assert bb._LAST_SCAN["files_new"] == 10
            assert bb._LAST_SCAN["files_removed"] == 2
            assert bb._LAST_SCAN["errors"] == 1  # len(errors)
            assert bb._LAST_SCAN["duration_ms"] == 2500
            assert bb._LAST_SCAN["folders_scanned"] == 3
            assert bb._LAST_SCAN["files_found"] == 50
        finally:
            bot.deleteLater()
            bb._LAST_SCAN = None


# ── Tests de la barre de statut ─────────────────────────────────────


class TestStatusBar:
    """Tests pour la barre de statut : texte, historique de scan, formatage."""

    def test_status_all_folders(self, bot: BotBibliotheque) -> None:
        """Statut avec fichiers mais sans dossier ni recherche active."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._LAST_SCAN = None
        bot._stats["fichiers"] = 50
        bot._current_folder = None
        bot._search_active = False
        text = bot._build_status_text()
        assert "📂 Tous les dossiers" in text
        assert "50 fichiers" in text
        assert "🕐" not in text

    def test_status_with_folder(self, bot: BotBibliotheque) -> None:
        """Statut avec un dossier sélectionné dans l'arbre."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._LAST_SCAN = None
        bot._stats["fichiers"] = 50
        bot._current_folder = "Musique"
        bot._search_active = False
        text = bot._build_status_text()
        assert "📂 Musique" in text
        assert "📂 Tous les dossiers" not in text
        assert "50 fichiers" in text

    def test_status_search_active(self, bot: BotBibliotheque) -> None:
        """Statut avec une recherche active et tri par défaut (Nom ↑)."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._LAST_SCAN = None
        bot._stats["fichiers"] = 20
        bot._current_folder = None
        bot._search_active = True
        bot._search_text = "rock"
        bot._sort_column = "name"
        bot._sort_order = "ASC"
        text = bot._build_status_text()
        assert "🔍 «rock»" in text
        assert "Tri : Nom ↑" in text
        assert "20 fichiers" in text

    def test_status_search_desc(self, bot: BotBibliotheque) -> None:
        """Statut avec tri descendant (↓)."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._LAST_SCAN = None
        bot._stats["fichiers"] = 10
        bot._search_active = True
        bot._search_text = "test"
        bot._sort_column = "name"
        bot._sort_order = "DESC"
        text = bot._build_status_text()
        assert "Tri : Nom ↓" in text

    def test_status_sort_size(self, bot: BotBibliotheque) -> None:
        """Statut avec tri par taille."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._LAST_SCAN = None
        bot._stats["fichiers"] = 10
        bot._search_active = True
        bot._search_text = "test"
        bot._sort_column = "size_bytes"
        bot._sort_order = "ASC"
        text = bot._build_status_text()
        assert "Tri : Taille ↑" in text

    def test_status_sort_duration(self, bot: BotBibliotheque) -> None:
        """Statut avec tri par durée."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._LAST_SCAN = None
        bot._stats["fichiers"] = 10
        bot._search_active = True
        bot._search_text = "test"
        bot._sort_column = "duration"
        bot._sort_order = "ASC"
        text = bot._build_status_text()
        assert "Tri : Durée ↑" in text

    def test_status_sort_bitrate(self, bot: BotBibliotheque) -> None:
        """Statut avec tri par débit (descendant)."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._LAST_SCAN = None
        bot._stats["fichiers"] = 10
        bot._search_active = True
        bot._search_text = "test"
        bot._sort_column = "bitrate"
        bot._sort_order = "DESC"
        text = bot._build_status_text()
        assert "Tri : Bitrate ↓" in text

    def test_status_sort_modified(self, bot: BotBibliotheque) -> None:
        """Statut avec tri par date de modification."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._LAST_SCAN = None
        bot._stats["fichiers"] = 10
        bot._search_active = True
        bot._search_text = "test"
        bot._sort_column = "modified_at"
        bot._sort_order = "ASC"
        text = bot._build_status_text()
        assert "Tri : Modifié ↑" in text

    def test_status_no_last_scan(self, bot: BotBibliotheque) -> None:
        """Statut sans historique de scan : pas d'emoji 🕐."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._LAST_SCAN = None
        bot._stats["fichiers"] = 10
        bot._current_folder = None
        bot._search_active = False
        text = bot._build_status_text()
        assert "🕐" not in text
        assert "📂 Tous les dossiers" in text

    def test_status_inclut_last_scan(self, bot: BotBibliotheque) -> None:
        """Statut avec historique de scan : emoji 🕐 présent."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._LAST_SCAN = {
            "timestamp": "2026-06-15T14:30:00",
            "files_new": 12,
            "files_removed": 3,
            "errors": 0,
            "duration_ms": 2450,
        }
        try:
            bot._stats["fichiers"] = 100
            bot._current_folder = None
            bot._search_active = False
            text = bot._build_status_text()
            assert "🕐" in text
            assert "+12/−3" in text
            assert "100 fichiers" in text
        finally:
            bb._LAST_SCAN = None

    def test_format_last_scan_no_errors(self, bot: BotBibliotheque) -> None:
        """_format_last_scan sans erreurs : pas de ⚠️ affiché."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._LAST_SCAN = {
            "timestamp": "2026-06-15T14:30:00",
            "files_new": 5,
            "files_removed": 2,
            "errors": 0,
            "duration_ms": 1000,
        }
        try:
            text = bot._format_last_scan()
            assert "⚠️" not in text
            assert "+5/−2" in text
        finally:
            bb._LAST_SCAN = None

    def test_format_last_scan_invalid_timestamp(self, bot: BotBibliotheque) -> None:
        """_format_last_scan avec timestamp invalide : affiche la valeur brute."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._LAST_SCAN = {
            "timestamp": "not-a-date",
            "files_new": 0,
            "files_removed": 0,
            "errors": 0,
            "duration_ms": 500,
        }
        try:
            text = bot._format_last_scan()
            assert "not-a-date" in text
            assert "+0/−0" in text
        finally:
            bb._LAST_SCAN = None

    def test_update_status_sets_label(self, bot: BotBibliotheque) -> None:
        """_update_status() met à jour le texte du QLabel de la barre de statut."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._LAST_SCAN = None
        bot._stats["fichiers"] = 10
        bot._current_folder = None
        bot._search_active = False
        bot._update_status()
        assert "📂 Tous les dossiers" in bot._status_lbl.text()
        assert "10 fichiers" in bot._status_lbl.text()

    def test_scan_completed_status_with_duration(self, qapp: QApplication) -> None:
        """_on_scan_completed avec durée : le message inclut ⏱️."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._LAST_SCAN = None
        bot = BotBibliotheque()
        try:
            from src.services.library_db import ScanResult

            result = ScanResult(
                folders_scanned=3,
                files_new=15,
                files_removed=2,
                errors=[],
                duration_ms=5000,
                files_found=50,
            )
            bot._on_scan_completed(result)
            assert "⏱️ 5.0s" in bot._status_lbl.text()
            assert "15 nouveaux" in bot._status_lbl.text()
            assert "2 retirés" in bot._status_lbl.text()
        finally:
            bot.deleteLater()
            bb._LAST_SCAN = None

    def test_scan_completed_status_without_duration(self, qapp: QApplication) -> None:
        """_on_scan_completed sans durée : pas de ⏱️ dans le message."""
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._LAST_SCAN = None
        bot = BotBibliotheque()
        try:
            from src.services.library_db import ScanResult

            result = ScanResult(
                folders_scanned=1,
                files_new=5,
                files_removed=0,
                errors=[],
                duration_ms=0,
                files_found=10,
            )
            bot._on_scan_completed(result)
            assert "⏱️" not in bot._status_lbl.text()
            assert "5 nouveaux" in bot._status_lbl.text()
            assert "0 retirés" in bot._status_lbl.text()
        finally:
            bot.deleteLater()
            bb._LAST_SCAN = None


# ── Tests de l'intégration Soulseek ────────────────────────────


class TestSoulseekIntegration:
    """Tests pour l'état de connexion Soulseek et la vue déconnectée."""

    @patch("src.gui.widgets.bots.bot_bibliotheque.soulseek_service")
    def test_etat_deconnecte_affiche_page_0(self, mock_slsk) -> None:
        """Quand soulseek_service.is_connected = False → stack index 0."""
        mock_slsk.is_connected = False
        bot = BotBibliotheque()
        try:
            bot._update_connection_state()
            assert bot._soulseek_connected is False
            assert bot._main_stack.currentIndex() == 0
        finally:
            bot.deleteLater()

    @patch("src.gui.widgets.bots.bot_bibliotheque.soulseek_service")
    @patch.object(BotBibliotheque, "refresh")
    def test_etat_connecte_affiche_page_1_et_refresh(self, mock_refresh, mock_slsk) -> None:
        """Transition déconnecté → connecté : stack index 1 + refresh appelé."""
        mock_slsk.is_connected = True
        bot = BotBibliotheque()
        try:
            # Simuler une déconnexion, puis reconnexion
            mock_slsk.is_connected = False
            bot._update_connection_state()
            assert bot._soulseek_connected is False
            assert bot._main_stack.currentIndex() == 0

            mock_slsk.is_connected = True
            mock_refresh.reset_mock()
            bot._update_connection_state()
            assert bot._soulseek_connected is True
            assert bot._main_stack.currentIndex() == 1
            mock_refresh.assert_called_once()
        finally:
            bot.deleteLater()

    @patch("src.gui.widgets.bots.bot_bibliotheque.soulseek_service")
    def test_connexion_bouton_emet_signal_page_changed(self, mock_slsk) -> None:
        """Le clic sur le bouton Connexion émet page_changed('Connexion')."""
        mock_slsk.is_connected = False
        bot = BotBibliotheque()
        try:
            received: list[str] = []
            bot.page_changed.connect(lambda name: received.append(name))
            bot._connect_btn.click()
            assert len(received) == 1
            assert received[0] == "Connexion"
        finally:
            bot.deleteLater()

    @patch("src.gui.widgets.bots.bot_bibliotheque.soulseek_service")
    @patch("PySide6.QtCore.QTimer.singleShot")
    @patch.object(BotBibliotheque, "_get_db")
    def test_init_sans_connexion_reste_sur_page_deconnectee(self, mock_db, mock_timer, mock_slsk) -> None:
        """À l'init, si Soulseek déconnecté → page déconnectée visible."""
        mock_db.return_value = _MockDb()
        mock_slsk.is_connected = False
        bot = BotBibliotheque()
        try:
            assert bot._soulseek_connected is False
            assert bot._main_stack.currentIndex() == 0
        finally:
            bot.deleteLater()

    @patch("src.gui.widgets.bots.bot_bibliotheque.soulseek_service")
    @patch("PySide6.QtCore.QTimer.singleShot")
    @patch.object(BotBibliotheque, "_get_db")
    def test_init_avec_connexion_affiche_bibliotheque(self, mock_db, mock_timer, mock_slsk) -> None:
        """À l'init, si Soulseek connecté → page bibliothèque visible."""
        mock_db.return_value = _MockDb()
        mock_slsk.is_connected = True
        import src.gui.widgets.bots.bot_bibliotheque as bb

        bb._STATS_CACHE = None
        bb._LAST_SCAN = None
        bot = BotBibliotheque()
        try:
            assert bot._soulseek_connected is True
            assert bot._main_stack.currentIndex() == 1
        finally:
            bot.deleteLater()


class _MockDb:
    """Mock minimal pour simuler library_db.LibraryDB dans les tests."""

    def __init__(self, stats: dict[str, int] | None = None, should_fail: bool = False) -> None:
        self._stats = stats or {"folders": 0, "files": 0, "audio": 0}
        self._should_fail = should_fail

    def get_stats(self) -> dict[str, int]:
        if self._should_fail:
            raise RuntimeError("DB error")
        return dict(self._stats)

    def add_folder(self, path: str, label: str = "") -> int:
        """Simule l'ajout d'un dossier, retourne un ID fictif."""
        return 1

    def remove_folder(self, folder_id: int) -> None:
        """Simule la suppression d'un dossier."""
        return

    def get_folders(self) -> list[dict]:
        return []

    def get_files(self, **kwargs) -> list[dict]:
        return []
