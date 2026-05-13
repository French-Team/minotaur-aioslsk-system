"""
Zone Centrale — contenu principal affiché via QStackedWidget.

Affiche la page correspondant à l'élément sélectionné
dans la zone gauche (ou ailleurs).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.gui.widgets.clients_actifs import ClientsActifsPage
from src.gui.widgets.connexions import ConnexionPage
from src.gui.widgets.telechargements import TelechargementsPage


class CenterZone(QFrame):
    """Zone de contenu principal avec pages empilables."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setObjectName("centerZone")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Stacked widget : chaque page = un contenu ──
        self._stack = QStackedWidget()
        self._stack.setObjectName("centerStack")
        layout.addWidget(self._stack)

        # Pages indexées par nom
        self._pages: dict[str, QWidget] = {}

        # Page d'accueil par défaut
        self._build_default_page()

        # Page de connexion
        self._build_connexion_page()

        # Page clients actifs
        self._build_clients_actifs_page()

        # Page téléchargements
        self._build_telechargements_page()

        # Pages de configuration
        for name in ("Général", "Réseau", "Recherche", "Téléchargement"):
            self._build_config_page(name)

        # Pages du footer (menus)
        for name in ("menu_1", "menu_2", "menu_3", "menu_4", "menu_5"):
            self._build_menu_page(name)

    # ── API publique ─────────────────────────────────────────────

    @property
    def stack(self) -> QStackedWidget:
        return self._stack

    @property
    def current_page(self) -> str | None:
        """Retourne le nom de la page affichée ou None."""
        widget = self._stack.currentWidget()
        for name, page in self._pages.items():
            if page is widget:
                return name
        return None

    def show_page(self, name: str) -> None:
        """Affiche la page demandée par son nom."""
        page = self._pages.get(name)
        if page is not None:
            self._stack.setCurrentWidget(page)

    def page(self, name: str) -> QWidget | None:
        """Retourne le widget d'une page par son nom."""
        return self._pages.get(name)

    @property
    def connexion_page(self) -> QWidget | None:
        """Page de connexion Soulseek."""
        return self._pages.get("connexion")

    @property
    def clients_actifs_page(self) -> QWidget | None:
        """Page des clients actifs."""
        return self._pages.get("clients-actifs")

    @property
    def telechargements_page(self) -> QWidget | None:
        """Page des téléchargements."""
        return self._pages.get("telechargements")

    # ── Construction des pages ───────────────────────────────────

    def _build_clients_actifs_page(self) -> None:
        """Page des clients actifs et joignables."""
        page = ClientsActifsPage()
        self._pages["clients-actifs"] = page
        self._stack.addWidget(page)

    def _build_telechargements_page(self) -> None:
        """Page des téléchargements."""
        page = TelechargementsPage()
        self._pages["telechargements"] = page
        self._stack.addWidget(page)

    def _build_connexion_page(self) -> None:
        """Page de connexion Soulseek."""
        page = ConnexionPage()
        self._pages["connexion"] = page
        self._stack.addWidget(page)

    def _build_default_page(self) -> None:
        """Page d'accueil (affichée au démarrage)."""
        page = QWidget()
        page.setObjectName("pageAccueil")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(16, 16, 16, 16)

        label = QLabel("Bienvenue sur aioslsk")
        label.setStyleSheet(
            "color: #5a5a6a; font-size: 18px; font-weight: 600;"
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(label)

        subtitle = QLabel(
            "Sélectionnez une section dans le panneau de gauche\n"
            "pour commencer la configuration."
        )
        subtitle.setStyleSheet(
            "color: #3a3a4a; font-size: 13px;"
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(subtitle)

        lay.addStretch(1)
        self._pages["accueil"] = page
        self._stack.addWidget(page)

    def _build_config_page(self, name: str) -> None:
        """Crée une page de configuration vide (remplie plus tard)."""
        page = QWidget()
        page.setObjectName(f"page{name}")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)

        title = QLabel(name)
        title.setStyleSheet(
            "color: #6c5ce7; font-size: 16px; font-weight: 700;"
        )
        lay.addWidget(title)

        placeholder = QLabel(
            f"Contenu de la section {name}\n"
            "(à venir)"
        )
        placeholder.setStyleSheet("color: #3a3a4a; font-size: 12px;")
        lay.addWidget(placeholder)

        lay.addStretch(1)
        self._pages[name] = page
        self._stack.addWidget(page)

    def _build_menu_page(self, name: str) -> None:
        """Crée une page de menu vide (remplie plus tard)."""
        page = QWidget()
        page.setObjectName(f"page{name}")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)

        title = QLabel(f"Menu : {name}")
        title.setStyleSheet(
            "color: #6c5ce7; font-size: 16px; font-weight: 700;"
        )
        lay.addWidget(title)

        placeholder = QLabel(
            f"Contenu de la page {name}\n"
            "(à venir)"
        )
        placeholder.setStyleSheet("color: #3a3a4a; font-size: 12px;")
        lay.addWidget(placeholder)

        lay.addStretch(1)
        self._pages[name] = page
        self._stack.addWidget(page)
