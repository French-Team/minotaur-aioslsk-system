"""
Zone Header — bannière d'informations.

Vide par défaut. N'affiche que la connexion (photo + username)
quand l'utilisateur est connecté.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QWidget

from src.gui.widgets.connexions import ConnexionHeaderWidget


class HeaderZone(QFrame):
    """Bannière d'informations en haut de l'application.

    Masquée par défaut. Affichée uniquement quand l'utilisateur
    est connecté, avec photo + username.
    """

    page_changed = Signal(str)  # émet le nom de la page à afficher

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setObjectName("headerZone")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Connexion — visible seulement quand connecté
        self._connexion = ConnexionHeaderWidget()
        self._connexion.clicked.connect(lambda: self.page_changed.emit("connexion"))
        layout.addWidget(self._connexion)

        # Header masqué par défaut
        self.setVisible(False)

    # ── API publique ─────────────────────────────────────────────

    @property
    def connexion_widget(self) -> ConnexionHeaderWidget:
        """Widget de connexion dans le header."""
        return self._connexion
    