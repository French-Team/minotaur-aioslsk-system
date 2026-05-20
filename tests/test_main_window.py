"""Tests pour MainWindow et ses fonctions QSS modulaires.

Stratégie :
  1. Fonctions QSS (module-level) — testables sans MainWindow
  2. MainWindow — toutes les dépendances externes mockées
"""

from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QLabel, QWidget


# ═══════════════════════════════════════════════════════════════════════════
#  Helper — référence au module pour éviter les copies locales
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def _mw_module():
    import src.gui.main_window as mw
    return mw


# ═══════════════════════════════════════════════════════════════════════════
#  Fonctions QSS — tests indépendants (pas de patches MainWindow)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.qt_heavy
class TestQssWarningHandler:
    """_qss_warning_handler : intercepte les warnings QSS de Qt."""

    @pytest.fixture(autouse=True)
    def _setup(self, _mw_module) -> None:
        _mw_module._qt_qss_warnings.clear()

    def test_capture_parse_warning(self, qapp, _mw_module) -> None:
        """Capture 'Could not parse stylesheet' dans _qt_qss_warnings."""
        _mw_module._qss_warning_handler(
            0, "Could not parse stylesheet: error at line 1"
        )
        assert len(_mw_module._qt_qss_warnings) == 1
        assert "Could not parse stylesheet" in _mw_module._qt_qss_warnings[0]

    def test_ignore_autres_warnings(self, qapp, _mw_module) -> None:
        """Ignore les warnings Qt qui ne sont pas des erreurs QSS."""
        _mw_module._qss_warning_handler(0, "Some other Qt warning")
        assert len(_mw_module._qt_qss_warnings) == 0


@pytest.mark.qt_heavy
class TestPatchSetStyleSheet:
    """_patch_set_style_sheet : monkey-patch de QWidget.setStyleSheet."""

    @pytest.fixture(autouse=True)
    def _reset(self, _mw_module) -> None:
        _mw_module._qss_original_setStyleSheet = None
        _mw_module._qt_qss_warnings.clear()
        _mw_module._qss_call_log.clear()
        yield
        _mw_module._qss_original_setStyleSheet = None

    def test_patch_sauvegarde_original(self, qapp, _mw_module) -> None:
        """Sauvegarde la méthode originale de QWidget."""
        assert _mw_module._qss_original_setStyleSheet is None
        _mw_module._patch_set_style_sheet()
        assert _mw_module._qss_original_setStyleSheet is not None
        assert callable(_mw_module._qss_original_setStyleSheet)

    def test_patch_log_appels(self, qapp, _mw_module) -> None:
        """Les appels à setStyleSheet sont loggés dans _qss_call_log."""
        _mw_module._patch_set_style_sheet()
        _mw_module._qss_call_log.clear()
        label = QLabel()
        label.setObjectName("testLabel")
        label.setStyleSheet("color: red;")
        assert len(_mw_module._qss_call_log) >= 1
        # Vérifier que les entrées sont dans le log (au moins une avec QLabel)
        assert len(_mw_module._qss_call_log) >= 1
        assert any(entry[0] == "QLabel" for entry in _mw_module._qss_call_log)

    def test_patch_appelle_original(self, qapp, _mw_module) -> None:
        """Le patch appelle bien la méthode originale."""
        _mw_module._patch_set_style_sheet()
        label = QLabel()
        label.setStyleSheet("color: red;")
        assert label.styleSheet() == "color: red;"


@pytest.mark.qt_heavy
class TestQssTestAgainstQt:
    """_qss_test_against_qt : teste un stylesheet contre Qt."""

    @pytest.fixture(autouse=True)
    def _reset(self, _mw_module) -> None:
        _mw_module._qss_original_setStyleSheet = None
        _mw_module._qt_qss_warnings.clear()
        yield

    def test_sans_patch_retourne_erreur(self, qapp, _mw_module) -> None:
        """Sans patch préalable, retourne un message d'erreur."""
        result = _mw_module._qss_test_against_qt("color: red;")
        assert isinstance(result, list)
        assert len(result) == 1
        assert "pas encore initialisé" in result[0]

    def test_stylesheet_valide(self, qapp, _mw_module) -> None:
        """Un stylesheet valide retourne [] (ou liste vide)."""
        _mw_module._patch_set_style_sheet()
        result = _mw_module._qss_test_against_qt("color: red;")
        assert isinstance(result, list)

    def test_stylesheet_vide(self, qapp, _mw_module) -> None:
        """Un stylesheet vide retourne une liste."""
        _mw_module._patch_set_style_sheet()
        result = _mw_module._qss_test_against_qt("")
        assert isinstance(result, list)


@pytest.mark.qt_heavy
class TestQssTestRulesRaw:
    """_qss_test_rules_raw : teste des règles QSS combinées."""

    @pytest.fixture(autouse=True)
    def _reset(self, _mw_module) -> None:
        _mw_module._qss_original_setStyleSheet = None
        _mw_module._qt_qss_warnings.clear()
        yield

    def test_sans_patch_retourne_true(self, qapp, _mw_module) -> None:
        """Sans patch préalable, retourne True."""
        result = _mw_module._qss_test_rules_raw(["color: red;"])
        assert result is True

    def test_avec_patch_retourne_bool(self, qapp, _mw_module) -> None:
        """Avec patch, retourne True ou False."""
        _mw_module._patch_set_style_sheet()
        result = _mw_module._qss_test_rules_raw(["color: red;"])
        assert isinstance(result, bool)


@pytest.mark.qt_heavy
class TestQssPinpointError:
    """_qss_pinpoint_error : isolation par recherche binaire."""

    @pytest.fixture(autouse=True)
    def _reset(self, _mw_module) -> None:
        _mw_module._qss_original_setStyleSheet = None
        _mw_module._qt_qss_warnings.clear()
        yield

    def test_sans_patch_retourne_chaine(self, qapp, _mw_module) -> None:
        """Sans patch, retourne le message d'erreur."""
        result = _mw_module._qss_pinpoint_error("color: red;")
        assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════════════════
#  MainWindow — dépendances externes mockées
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.qt_heavy
class TestMainWindow:
    """Tests de MainWindow avec dépendances mockées."""

    @pytest.fixture(autouse=True)
    def _setup_mocks(self, mocker) -> None:
        """Patche toutes les dépendances externes de MainWindow."""
        # Layout mocké avec toutes les zones
        self.mock_header = MagicMock()
        self.mock_header.connexion_widget = MagicMock()
        self.mock_header.connexion_widget.set_username = MagicMock()
        self.mock_header.connexion_widget.set_photo = MagicMock()
        self.mock_header.page_changed = MagicMock()
        self.mock_header.setVisible = MagicMock()

        self.mock_footer = MagicMock()
        self.mock_footer.page_changed = MagicMock()
        self.mock_footer.setVisible = MagicMock()

        self.mock_left = MagicMock()
        self.mock_left.page_changed = MagicMock()

        self.mock_connexion_page = MagicMock()
        self.mock_connexion_page.login_requested = MagicMock()
        self.mock_connexion_page.generate_requested = MagicMock()
        self.mock_connexion_page.disconnect_requested = MagicMock()
        self.mock_connexion_page.set_disconnected = MagicMock()
        self.mock_connexion_page.show_error = MagicMock()
        self.mock_connexion_page.set_generating = MagicMock()
        self.mock_connexion_page.set_connected = MagicMock()
        self.mock_connexion_page.set_auto_login = MagicMock()
        self.mock_connexion_page.prefill = MagicMock()

        self.mock_center = MagicMock()
        self.mock_center.connexion_page = self.mock_connexion_page
        self.mock_center.show_page = MagicMock()
        self.mock_center.show_home = MagicMock()
        self.mock_center.show_connexion = MagicMock()
        self.mock_center.set_connexion_manager = MagicMock()

        self.mock_right = MagicMock()

        self.mock_layout = MagicMock()
        self.mock_layout.header = self.mock_header
        self.mock_layout.left = self.mock_left
        self.mock_layout.center = self.mock_center
        self.mock_layout.right = self.mock_right
        self.mock_layout.footer = self.mock_footer

        self.mock_cm = MagicMock()
        self.mock_cm.connected = MagicMock()
        self.mock_cm.disconnected = MagicMock()
        self.mock_cm.error_occurred = MagicMock()
        self.mock_cm.generating = MagicMock()
        self.mock_cm.status_changed = MagicMock()
        self.mock_cm.login = MagicMock()
        self.mock_cm.generate_account = MagicMock()
        self.mock_cm.disconnect = MagicMock()
        self.mock_cm.auto_login = MagicMock()
        self.mock_cm.shutdown = MagicMock()

        self.mock_toast = MagicMock()
        self.mock_toast.raise_ = MagicMock()
        self.mock_toast.show_toast = MagicMock()

        self.mock_event_bus = MagicMock()
        self.mock_event_bus.event_emitted = MagicMock()

        # Patcher les imports dans main_window
        mocker.patch("src.gui.main_window.QssInspector")
        mocker.patch("src.gui.main_window.LayoutEntry", return_value=self.mock_layout)
        mocker.patch("src.gui.main_window.ConnexionManager", return_value=self.mock_cm)
        mocker.patch("src.gui.main_window.EventBus", return_value=self.mock_event_bus)
        mocker.patch("src.gui.main_window.ToastNotification", return_value=self.mock_toast)
        mocker.patch("src.gui.main_window.cfg_get", return_value="")

        # Patcher les méthodes QMainWindow qui rejettent MagicMock
        mocker.patch("PySide6.QtWidgets.QMainWindow.addDockWidget", return_value=None)
        mocker.patch("PySide6.QtWidgets.QMainWindow.setCentralWidget", return_value=None)

        # Nettoyer l'état global QSS
        import src.gui.main_window as _mw
        _mw._qss_original_setStyleSheet = None
        _mw._qt_qss_warnings.clear()
        _mw._qss_call_log.clear()

        yield

        import src.gui.main_window as _mw2
        _mw2._qss_original_setStyleSheet = None
        _mw2._qss_call_log.clear()

    # ── Création ──────────────────────────────────────────────────────

    def test_creer_fenetre(self, qapp) -> None:
        """Peut créer une MainWindow."""
        from src.gui.main_window import MainWindow

        win = MainWindow()
        assert win is not None
        assert isinstance(win, MainWindow)

    def test_titre_fenetre(self, qapp) -> None:
        """Le titre de la fenêtre est correct."""
        from src.gui.main_window import MainWindow

        win = MainWindow()
        assert win.windowTitle() == "aioslsk — Interface Soulseek"

    def test_taille_minimale(self, qapp) -> None:
        """La taille minimale est définie."""
        from src.gui.main_window import MainWindow

        win = MainWindow()
        assert win.minimumSize().width() >= 960
        assert win.minimumSize().height() >= 640

    def test_status_label_present(self, qapp) -> None:
        """La barre de statut contient un label 'Serveur hors ligne'."""
        from src.gui.main_window import MainWindow

        win = MainWindow()
        status = win.statusBar()
        assert status is not None
        labels = status.findChildren(QLabel)
        assert any(
            "hors ligne" in lbl.text() or "Serveur" in lbl.text()
            for lbl in labels
        )

    def test_version_label_present(self, qapp) -> None:
        """La barre de statut contient un label de version."""
        from src.gui.main_window import MainWindow

        win = MainWindow()
        status = win.statusBar()
        labels = status.findChildren(QLabel)
        assert any("v0" in lbl.text() or "0.1" in lbl.text() for lbl in labels)

    # ── Propriétés ────────────────────────────────────────────────────

    def test_header_property(self, qapp) -> None:
        """La propriété header retourne le header du layout."""
        from src.gui.main_window import MainWindow

        win = MainWindow()
        assert win.header is self.mock_header

    def test_left_property(self, qapp) -> None:
        """La propriété left retourne la left zone."""
        from src.gui.main_window import MainWindow

        win = MainWindow()
        assert win.left is self.mock_left

    def test_center_property(self, qapp) -> None:
        """La propriété center retourne le center zone."""
        from src.gui.main_window import MainWindow

        win = MainWindow()
        assert win.center is self.mock_center

    def test_right_property(self, qapp) -> None:
        """La propriété right retourne le right zone."""
        from src.gui.main_window import MainWindow

        win = MainWindow()
        assert win.right is self.mock_right

    def test_footer_property(self, qapp) -> None:
        """La propriété footer retourne le footer zone."""
        from src.gui.main_window import MainWindow

        win = MainWindow()
        assert win.footer is self.mock_footer

    def test_qss_warnings_property(self, qapp) -> None:
        """qss_warnings retourne une copie de _qt_qss_warnings."""
        from src.gui.main_window import MainWindow, _qt_qss_warnings

        win = MainWindow()
        _qt_qss_warnings.append("test warning")
        warnings = win.qss_warnings
        assert len(warnings) == 1
        assert warnings[0] == "test warning"
        assert warnings is not _qt_qss_warnings

    def test_qss_call_logs_property(self, qapp) -> None:
        """qss_call_logs retourne une copie de _qss_call_log."""
        from src.gui.main_window import MainWindow, _qss_call_log

        win = MainWindow()
        _qss_call_log.append(("Test", "id", "css", "stack"))
        logs = win.qss_call_logs
        _qss_call_log.clear()
        _qss_call_log.append(("PySide6", "test_id", "css", "stack"))
        logs = win.qss_call_logs
        assert len(logs) == 1
        assert logs is not _qss_call_log
        assert logs[0][1] == "test_id"

    # ── Toast ─────────────────────────────────────────────────────────

    def test_on_toast_event_error(self, qapp) -> None:
        """Un événement ERROR affiche une notification toast."""
        from src.gui.main_window import MainWindow

        win = MainWindow()

        class Event:
            severity = "ERROR"
            title = "Erreur test"
            message = "Message de test"

        win._on_toast_event(Event())
        self.mock_toast.show_toast.assert_called_once_with(
            "ERROR", "Erreur test", "Message de test"
        )

    def test_on_toast_event_warn(self, qapp) -> None:
        """Un événement WARN affiche une notification toast."""
        from src.gui.main_window import MainWindow

        win = MainWindow()

        class Event:
            severity = "WARN"
            title = "Attention"
            message = "Message"

        win._on_toast_event(Event())
        self.mock_toast.show_toast.assert_called_once_with(
            "WARN", "Attention", "Message"
        )

    def test_on_toast_event_info_ignore(self, qapp) -> None:
        """Un événement INFO n'affiche pas de toast."""
        from src.gui.main_window import MainWindow

        win = MainWindow()

        class Event:
            severity = "INFO"
            title = "Info"
            message = "Message"

        win._on_toast_event(Event())
        self.mock_toast.show_toast.assert_not_called()

    def test_on_toast_event_sans_severite_ignore(self, qapp) -> None:
        """Un événement sans sévérité n'affiche pas de toast."""
        from src.gui.main_window import MainWindow

        win = MainWindow()

        class Event:
            pass

        win._on_toast_event(Event())
        self.mock_toast.show_toast.assert_not_called()

    def test_on_toast_event_message_vide(self, qapp) -> None:
        """Un événement ERROR sans message n'affiche qu'un titre."""
        from src.gui.main_window import MainWindow

        win = MainWindow()

        class Event:
            severity = "ERROR"
            title = "Erreur seule"
            message = ""

        win._on_toast_event(Event())
        self.mock_toast.show_toast.assert_called_once_with(
            "ERROR", "Erreur seule", ""
        )

    # ── BoucleRooms après connexion ──────────────────────────────────

    def test_lancer_boucle_rooms_apres_connexion(self, qapp) -> None:
        """_lancer_boucle_rooms_apres_connexion appelle add_message puis _do_start_loop('Rooms')."""
        from src.gui.main_window import MainWindow

        mock_accueil = MagicMock()
        mock_accueil.add_message = MagicMock()
        mock_accueil._do_start_loop = MagicMock()
        self.mock_center._bot_accueil = mock_accueil

        win = MainWindow()
        win._lancer_boucle_rooms_apres_connexion()

        # 1. add_message appelé avec le bon message de notification
        mock_accueil.add_message.assert_called_once_with(
            "💬",
            "Je lance la mise à jour des salons et je prépare la liste des clients actifs…",
            None,
        )

        # 2. _do_start_loop appelé avec "Rooms"
        mock_accueil._do_start_loop.assert_called_once_with("Rooms")

        # 3. Ordre correct : add_message AVANT _do_start_loop
        mock_accueil.assert_has_calls([
            call.add_message("💬", "Je lance la mise à jour des salons et je prépare la liste des clients actifs…", None),
            call._do_start_loop("Rooms"),
        ])

    def test_lancer_boucle_rooms_sans_accueil(self, qapp) -> None:
        """Si _bot_accueil est None, _lancer_boucle_rooms_apres_connexion ne fait rien."""
        from src.gui.main_window import MainWindow

        self.mock_center._bot_accueil = None

        win = MainWindow()
        # Ne doit pas planter
        win._lancer_boucle_rooms_apres_connexion()

    def test_lancer_boucle_rooms_sans_do_start_loop(self, qapp) -> None:
        """Si _bot_accueil n'a pas _do_start_loop, add_message n'est pas appelé non plus."""
        from src.gui.main_window import MainWindow

        # spec=["add_message"] → add_message accessible, _do_start_loop non (hasattr=False)
        mock_accueil = MagicMock(spec=["add_message"])
        self.mock_center._bot_accueil = mock_accueil

        win = MainWindow()
        win._lancer_boucle_rooms_apres_connexion()

        # hasattr(mock, "_do_start_loop") → False (pas dans spec)
        # La méthode ne doit donc pas entrer dans le if → add_message jamais appelé
        mock_accueil.add_message.assert_not_called()

    # ── Fermeture ─────────────────────────────────────────────────────

    def test_close_appelle_shutdown(self, qapp) -> None:
        """closeEvent() appelle shutdown() sur le gestionnaire de connexion."""
        from src.gui.main_window import MainWindow

        win = MainWindow()
        event = QCloseEvent()
        win.closeEvent(event)
        self.mock_cm.shutdown.assert_called_once()

    def test_close_appelle_inspector_close(self, qapp) -> None:
        """closeEvent() ferme l'inspecteur QSS."""
        from src.gui.main_window import MainWindow, QssInspector

        win = MainWindow()
        event = QCloseEvent()
        win.closeEvent(event)
        qss = QssInspector.return_value
        qss.close.assert_called_once()

    def test_close_accepte_event(self, qapp) -> None:
        """closeEvent() accepte l'événement (super().closeEvent)."""
        from src.gui.main_window import MainWindow

        win = MainWindow()
        event = QCloseEvent()
        win.closeEvent(event)
        assert event.isAccepted()

    # ── Toggle Inspector ──────────────────────────────────────────────

    def test_toggle_show(self, qapp) -> None:
        """toggle_inspector(True) affiche et rafraîchit l'inspecteur."""
        from src.gui.main_window import MainWindow, QssInspector

        win = MainWindow()
        win._toggle_inspector(True)
        qss = QssInspector.return_value
        qss.refresh.assert_called_once()
        qss.show.assert_called_once()
        qss.raise_.assert_called_once()

    def test_toggle_hide(self, qapp) -> None:
        """toggle_inspector(False) cache l'inspecteur."""
        from src.gui.main_window import MainWindow, QssInspector

        win = MainWindow()
        qss = QssInspector.return_value
        qss.hide.reset_mock()  # hide() est appelé 1× dans __init__
        win._toggle_inspector(False)
        qss.hide.assert_called_once()
        qss.refresh.assert_not_called()
