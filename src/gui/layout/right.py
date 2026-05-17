"""
Zone Droite — panneau latéral droit rétractable.

Affiche les rooms (publiques et privées) dans un QTabWidget.
Le panneau complet peut se replier vers la droite en cliquant
sur le bouton « ▶ » sur le bord gauche.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

# Largeurs
_WIDTH_EXPANDED = 280
_WIDTH_COLLAPSED = 20


class _Handle(QFrame):
    """Bouton de repli — toute la hauteur, click détecté."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("rightHandle")
        self.setFixedWidth(20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._arrow = QLabel("▶")
        self._arrow.setObjectName("handleArrow")
        self._arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._arrow)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)

    def set_arrow(self, text: str) -> None:
        self._arrow.setText(text)


class RightZone(QFrame):
    """Panneau latéral droit — onglets Public / Privé + rétractable."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setObjectName("rightZone")

        self._collapsed = True

        # ── Layout principal horizontal : [handle | contenu] ──
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Handle (bouton de repli sur le bord gauche) ──
        self._handle = _Handle()
        self._handle.clicked.connect(self._toggle_panel)

        # ── Zone de contenu (ce qui se cache) ──
        self._content = QWidget(self)
        self._content.setObjectName("rightContent")

        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(4)

        # ── Titre ──
        title = QLabel("LES ROOMS")
        title.setStyleSheet("color: #6c5ce7; font-size: 12px; font-weight: 700;")
        content_layout.addWidget(title)

        # ── Tabs ──
        self._tabs = QTabWidget()
        self._tabs.setObjectName("roomsTabs")

        # Onglet Public
        self._tab_public = QWidget()
        self._tab_public.setObjectName("tabPublic")
        self._build_tab(self._tab_public, "Salons publics")
        self._tabs.addTab(self._tab_public, "Public")

        # Onglet Privé
        self._tab_prive = QWidget()
        self._tab_prive.setObjectName("tabPrive")
        self._build_tab(self._tab_prive, "Salons privés")
        self._tabs.addTab(self._tab_prive, "Privé")

        content_layout.addWidget(self._tabs, 1)

        # Assemblage
        main_layout.addWidget(self._handle, 0)  # pas d'étirement
        main_layout.addWidget(self._content, 1)  # stretch = prend l'espace

        # ── État初始 ──
        self._apply_state()

    # ── API publique ─────────────────────────────────────────────

    @property
    def is_collapsed(self) -> bool:
        return self._collapsed

    @property
    def tabs(self) -> QTabWidget:
        return self._tabs

    def toggle(self) -> None:
        self._toggle_panel()

    def expand(self) -> None:
        if self._collapsed:
            self._toggle_panel()

    def collapse(self) -> None:
        if not self._collapsed:
            self._toggle_panel()

    # ── Mécanisme interne ────────────────────────────────────────

    def _toggle_panel(self) -> None:
        self._collapsed = not self._collapsed
        self._apply_state()

    def _apply_state(self) -> None:
        self._content.setVisible(not self._collapsed)
        self._handle.set_arrow("◀" if self._collapsed else "▶")
        self.setFixedWidth(_WIDTH_COLLAPSED if self._collapsed else _WIDTH_EXPANDED)

    # ── Construction des tabs ────────────────────────────────────

    @staticmethod
    def _build_tab(tab: QWidget, placeholder: str) -> None:
        """Remplit un onglet avec une grille prête à accueillir du contenu."""
        grid = QGridLayout(tab)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setSpacing(4)

        label = QLabel(placeholder)
        label.setStyleSheet("color: #5a5a6a; font-size: 11px; font-style: italic;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(label, 0, 0)

        grid.setRowStretch(0, 1)
        grid.setColumnStretch(0, 1)
