"""
Zone Footer — barre de navigation des 12 bots.

Chaque bouton = un bot. Change la page affichée dans la zone centrale.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPushButton,
    QWidget,
)


class _FooterNavButton(QPushButton):
    """Bouton de navigation dans le footer."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("footerNavButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)


_BOT_NAMES: list[str] = [
    "Accueil",
    "Recherche",
    "Téléchargement",
    "Wishlist",
    "Bibliothèque",
    "Optimiseur",
    "Surveillance",
    "Planificateur",
    "Nettoyage",
    "Statistiques",
    "Assistant",
    "Aide",
]


class FooterZone(QFrame):
    """Barre de navigation en bas de l'application."""

    page_changed = Signal(str)  # émet le nom de la page sélectionnée

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setObjectName("footerZone")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        layout.addStretch(1)

        # Boutons de navigation (centrés)
        self._buttons: dict[str, _FooterNavButton] = {}
        self._active_button: _FooterNavButton | None = None

        for name in _BOT_NAMES:
            btn = _FooterNavButton(name)
            btn.clicked.connect(lambda checked=False, n=name: self._on_button(n))
            layout.addWidget(btn)
            self._buttons[name] = btn

        layout.addStretch(1)  # centrage

        # Footer masqué par défaut — visible seulement quand connecté
        self.setVisible(False)

    # ── API publique ─────────────────────────────────────────────

    @property
    def active_page(self) -> str | None:
        if self._active_button:
            return self._active_button.text()
        return None

    def set_active(self, name: str) -> None:
        """Active le bouton correspondant sans émettre le signal."""
        btn = self._buttons.get(name)
        if btn is not None and btn is not self._active_button:
            if self._active_button:
                self._active_button.setChecked(False)
            btn.setChecked(True)
            self._active_button = btn

    def page_button(self, name: str) -> QPushButton | None:
        return self._buttons.get(name)

    # ── Interne ──────────────────────────────────────────────────

    def _on_button(self, name: str) -> None:
        self.set_active(name)
        self.page_changed.emit(name)
