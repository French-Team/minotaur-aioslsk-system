"""
Zone Footer — barre de navigation des 12 bots.

Chaque bouton = un bot. Change la page affichée dans la zone centrale.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from src.gui.theme_fragments.colors import COLORS


class _FooterNavButton(QPushButton):
    """Bouton de navigation dans le footer, avec badge optionnel."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("footerNavButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)

        # Badge de comptage (caché par défaut)
        self._badge = QLabel("", self)
        self._badge.setObjectName("footerNavBadge")
        self._badge.setFixedSize(18, 18)
        self._badge.setAlignment(Qt.AlignCenter)
        self._badge.setVisible(False)
        self._badge.setStyleSheet(f"""
            #footerNavBadge {{
                background: {COLORS['DANGER']};
                color: #ffffff;
                font-size: 10px;
                font-weight: 700;
                border-radius: 9px;
            }}
        """)

    def set_badge(self, count: int) -> None:
        """Affiche ou masque le badge avec le nombre donné."""
        if count > 0:
            display = str(count) if count <= 99 else "99+"
            self._badge.setText(display)
            self._badge.setVisible(True)
            # Positionner le badge en haut à droite du bouton
            self._badge.move(self.width() - 22, -4)
        else:
            self._badge.setVisible(False)

    def resizeEvent(self, event: object) -> None:
        """Repositionne le badge lors du redimensionnement."""
        super().resizeEvent(event)  # type: ignore[arg-type]
        if self._badge.isVisible():
            self._badge.move(self.width() - 22, -4)


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

    def set_badge(self, name: str, count: int) -> None:
        """Définit le badge de comptage pour un bouton."""
        btn = self._buttons.get(name)
        if isinstance(btn, _FooterNavButton):
            btn.set_badge(count)

    def button(self, name: str) -> _FooterNavButton | None:
        """Retourne le _FooterNavButton correspondant au nom."""
        return self._buttons.get(name)

    # ── Interne ──────────────────────────────────────────────────

    def _on_button(self, name: str) -> None:
        self.set_active(name)
        self.page_changed.emit(name)
