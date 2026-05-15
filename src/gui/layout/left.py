"""
Zone gauche — panneau de navigation rétractable.

Boutons de navigation : Général, Réseau, Recherche, Téléchargement.
Le panneau complet peut se replier vers la gauche.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Largeurs
_WIDTH_EXPANDED = 200
_WIDTH_COLLAPSED = 20

_SECTIONS = [
    "Général",
    "Partages",
    "Réseau",
    "Recherche",
    "Téléchargement",
    "Utilisateurs",
    "Salons",
    "Debug",
]


class _NavButton(QPushButton):
    """Bouton de navigation latéral."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("navButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)


class _Handle(QFrame):
    """Bouton de repli — toute la hauteur, click détecté."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("leftHandle")
        self.setFixedWidth(20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._arrow = QLabel("◀")
        self._arrow.setObjectName("handleArrow")
        self._arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._arrow)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)

    def set_arrow(self, text: str) -> None:
        self._arrow.setText(text)


_SECTION_TO_PAGE: dict[str, str] = {
    "Général": "Général",
    "Partages": "Partages",
    "Réseau": "Réseau",
    "Recherche": "config-recherche",
    "Téléchargement": "config-telechargement",
    "Utilisateurs": "Utilisateurs",
    "Salons": "Salons",
    "Debug": "Debug",
}


class LeftZone(QFrame):
    """Panneau latéral gauche — navigation + rétractable."""

    page_changed = Signal(str)  # émet le nom de la page sélectionnée

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setObjectName("leftZone")

        self._collapsed = True

        # ── Layout principal horizontal : [contenu | handle] ──
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Zone de contenu ──
        self._content = QWidget(self)
        self._content.setObjectName("leftContent")

        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Contenu : titre + boutons
        inner = QVBoxLayout()
        inner.setContentsMargins(8, 8, 8, 8)
        inner.setSpacing(4)

        # ── Bouton Accueil (visible seulement quand connecté) ──
        self._home_btn = _NavButton("🏠  Accueil")
        self._home_btn.setVisible(False)
        self._home_btn.clicked.connect(
            lambda: self._on_button("accueil")
        )
        inner.addWidget(self._home_btn)

        inner.addSpacing(12)

        title = QLabel("CONFIGURATIONS")
        title.setStyleSheet("color: #6c5ce7; font-size: 12px; font-weight: 700;")
        inner.addWidget(title)

        # Boutons de navigation
        self._buttons: dict[str, _NavButton] = {}
        self._active_button: _NavButton | None = None

        for name in _SECTIONS:
            btn = _NavButton(name)
            btn.clicked.connect(lambda checked=False, n=name: self._on_button(n))
            inner.addWidget(btn)
            self._buttons[name] = btn

        inner.addStretch(1)
        content_layout.addLayout(inner)

        # ── Handle ──
        self._handle = _Handle()
        self._handle.clicked.connect(self._toggle_panel)

        main_layout.addWidget(self._content, 1)
        main_layout.addWidget(self._handle, 0)

        self._apply_state()

    # ── API publique ─────────────────────────────────────────────

    @property
    def is_collapsed(self) -> bool:
        return self._collapsed

    @property
    def active_page(self) -> str | None:
        """Retourne le nom de la page active ou None."""
        if self._active_button:
            return self._active_button.text()
        return None

    @property
    def home_button_visible(self) -> bool:
        """Le bouton Accueil est-il visible ?"""
        return self._home_btn.isVisible()

    @home_button_visible.setter
    def home_button_visible(self, visible: bool) -> None:
        """Affiche ou masque le bouton Accueil."""
        self._home_btn.setVisible(visible)

    def set_active(self, name: str) -> None:
        """Active le bouton correspondant sans émettre le signal."""
        # Gérer le bouton Accueil (pas dans _buttons)
        if name == "accueil":
            if self._active_button:
                self._active_button.setChecked(False)
            self._home_btn.setChecked(True)
            self._active_button = self._home_btn
            return
        btn = self._buttons.get(name)
        if btn is not None and btn is not self._active_button:
            if self._active_button:
                self._active_button.setChecked(False)
            btn.setChecked(True)
            self._active_button = btn

    def page_button(self, name: str) -> _NavButton | None:
        """Retourne le bouton d'une page par son nom."""
        if name == "accueil":
            return self._home_btn
        return self._buttons.get(name)

    def toggle(self) -> None:
        self._toggle_panel()

    def expand(self) -> None:
        if self._collapsed:
            self._toggle_panel()

    def collapse(self) -> None:
        if not self._collapsed:
            self._toggle_panel()

    # ── Mécanisme interne ───────────────────────────────────────

    def _on_button(self, name: str) -> None:
        """Un bouton de navigation a été cliqué."""
        self.set_active(name)
        # Mapper vers le vrai nom de page config (évite les collisions bot/config)
        page_name = _SECTION_TO_PAGE.get(name, name)
        self.page_changed.emit(page_name)

    def _toggle_panel(self) -> None:
        self._collapsed = not self._collapsed
        self._apply_state()

    def _apply_state(self) -> None:
        self._content.setVisible(not self._collapsed)
        self._handle.set_arrow("▶" if self._collapsed else "◀")
        self.setFixedWidth(_WIDTH_COLLAPSED if self._collapsed else _WIDTH_EXPANDED)
