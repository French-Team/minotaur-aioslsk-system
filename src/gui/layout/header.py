"""
Zone Header — bannière d'informations.

Vide par défaut. N'affiche que la connexion (photo + username)
quand l'utilisateur est connecté.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("[HEADER]")

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QWidget

from src.utils.log_action import log_action
from src.gui.widgets.connexions import ConnexionHeaderWidget


class HeaderZone(QFrame):
    """Bannière d'informations en haut de l'application.

    Masquée par défaut. Affichée uniquement quand l'utilisateur
    est connecté, avec photo + username.
    """

    page_changed = Signal(str)  # émet le nom de la page à afficher

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # pyrefly: ignore [missing-attribute]
        self.setFrameShape(QFrame.NoFrame)
        self.setObjectName("headerZone")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Connexion — visible seulement quand connecté
        self._connexion = ConnexionHeaderWidget()
        self._connexion.clicked.connect(self._on_connexion_clicked)
        layout.addWidget(self._connexion)

        # Header masqué par défaut
        self.setVisible(False)

    # ── Privé ────────────────────────────────────────────────────

    @log_action("Header : naviguer vers la connexion")
    def _on_connexion_clicked(self) -> None:
        """Navigue vers la page de connexion."""
        self.page_changed.emit("connexion")

    # ── API publique ─────────────────────────────────────────────

    @property
    def connexion_widget(self) -> ConnexionHeaderWidget:
        """Widget de connexion dans le header."""
        return self._connexion
