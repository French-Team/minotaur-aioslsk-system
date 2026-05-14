"""
Fenêtre principale de l'interface graphique aioslsk.
"""

from __future__ import annotations

import logging

from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QStatusBar,
)

from src.gui.layout.entry import LayoutEntry
from src.gui.theme import DARK_THEME
from src.services.connexion_manager import ConnexionManager

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application aioslsk."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("aioslsk — Interface Soulseek")
        self.setMinimumSize(960, 640)
        self.resize(1100, 720)

        # Applique le thème global
        self.setStyleSheet(DARK_THEME)

        # ── Barre de menu ──
        self._build_menu()

        # ── Layout principal via les zones ──
        self._layout = LayoutEntry()
        self.setCentralWidget(self._layout)

        # ── Barre de statut ──
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        self._status_label = QLabel("Serveur hors ligne")
        status_bar.addWidget(self._status_label)
        self._version_label = QLabel("v0.1.0")
        status_bar.addPermanentWidget(self._version_label)

        # ── Gestionnaire de connexion Soulseek ──
        self._connect_connexion_manager()

    # ── Fermeture propre ────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent) -> None:
        """Arrête le gestionnaire de connexion avant de fermer."""
        logger.info("Fermeture de l'application…")
        self._connexion_manager.shutdown()
        super().closeEvent(event)

    # ──────────────────────────────────────────
    #  Méthodes privées
    # ──────────────────────────────────────────

    def _connect_connexion_manager(self) -> None:
        """Crée et connecte le gestionnaire de connexion Soulseek."""
        self._connexion_manager = ConnexionManager(self)

        # Raccourcis vers les widgets UI
        connexion_header = self._layout.header.connexion_widget
        connexion_page = self._layout.center.connexion_page

        # UI → Manager
        connexion_page.login_requested.connect(self._connexion_manager.login)
        connexion_page.generate_requested.connect(
            self._connexion_manager.generate_account
        )

        # Manager → UI (page de connexion) — déjà géré dans les lambdas navigation ci-dessous
        self._connexion_manager.disconnected.connect(
            connexion_page.set_disconnected
        )
        self._connexion_manager.error_occurred.connect(
            connexion_page.show_error
        )
        self._connexion_manager.generating.connect(
            connexion_page.set_generating
        )

        # Manager → UI (header)
        self._connexion_manager.connected.connect(
            lambda username: connexion_header.set_status(True)
        )
        self._connexion_manager.disconnected.connect(
            lambda: connexion_header.set_status(False)
        )

        # Manager → barre de statut
        self._connexion_manager.status_changed.connect(
            self._status_label.setText
        )

        # Navigation automatique : connexion → accueil, déconnexion → connexion
        center = self._layout.center
        self._connexion_manager.connected.connect(
            lambda username: (
                connexion_page.set_connected(username),
                center.show_home(username),
            )
        )
        self._connexion_manager.disconnected.connect(
            lambda: center.show_connexion()
        )

        # Bouton "Se déconnecter" de la page d'accueil
        center.disconnect_requested.connect(
            self._connexion_manager.disconnect
        )

    def _build_menu(self) -> None:
        """Construit la barre de menus."""
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&Fichier")
        quit_action = QAction("&Quitter", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(QApplication.instance().quit)
        file_menu.addAction(quit_action)

        help_menu = menubar.addMenu("&Aide")
        about_action = QAction("À &propos", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _show_about(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.about(
            self,
            "À propos — aioslsk",
            "<b>aioslsk</b><br><br>"
            "Interface graphique pour le client Soulseek aioslsk.<br><br>"
            "Version 0.1.0<br>"
            "Basé sur PySide6 et aioslsk.",
        )

    # ──────────────────────────────────────────
    #  API publique — accès aux zones
    # ──────────────────────────────────────────

    @property
    def header(self):
        return self._layout.header

    @property
    def left(self):
        return self._layout.left

    @property
    def center(self):
        return self._layout.center

    @property
    def right(self):
        return self._layout.right

    @property
    def footer(self):
        return self._layout.footer
