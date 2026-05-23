"""
Point d'entrée du layout — assemble les 5 zones dans une grille 3×3.

Grille principale :
┌─────────────────────────────────────┐
│           Header (col 0-2)          │  ← row 0
├──────┬────────────────────┬──────────┤
│ Left │      Center        │  Right   │  ← row 1
├──────┴────────────────────┴──────────┤
│           Footer (col 0-2)          │  ← row 2
└─────────────────────────────────────┘
"""

from __future__ import annotations

import logging

from PySide6.QtWidgets import QGridLayout, QWidget

logger = logging.getLogger("[ENTRY]")


from src.gui.layout.center import CenterZone
from src.gui.layout.footer import FooterZone
from src.gui.layout.header import HeaderZone
from src.gui.layout.left import LeftZone
from src.gui.layout.right import RightZone


class LayoutEntry(QWidget):
    """Assemblage des 5 zones dans une grille 3×3.

    Colonnes : Left (0) | Center (1) | Right (2)
    Lignes   : Header (0) | Body (1) | Footer (2)
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("layoutEntry")

        # ── Grille principale 3×3 ──
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(0)

        # Header : row 0, col 0-2
        self.header = HeaderZone()
        self._grid.addWidget(self.header, 0, 0, 1, 3)

        # Left : row 1, col 0
        self.left = LeftZone()
        self._grid.addWidget(self.left, 1, 0)

        # Center : row 1, col 1
        self.center = CenterZone()
        self._grid.addWidget(self.center, 1, 1)

        # Right : row 1, col 2
        self.right = RightZone()
        self._grid.addWidget(self.right, 1, 2)

        # ── Connexions ──
        self.left.page_changed.connect(self.center.show_page)
        self.header.page_changed.connect(self.center.show_page)

        # Footer : row 2, col 0-2
        self.footer = FooterZone()
        self.footer.page_changed.connect(self.center.show_page)
        self._grid.addWidget(self.footer, 2, 0, 1, 3)

        # Proportions : left et right fixes, center prend le reste
        self._grid.setColumnStretch(0, 0)  # left — pas d'étirement
        self._grid.setColumnStretch(1, 1)  # center — prend l'espace
        self._grid.setColumnStretch(2, 0)  # right — pas d'étirement

        self._grid.setRowStretch(0, 0)  # header — hauteur fixe
        self._grid.setRowStretch(1, 1)  # body — prend l'espace
        self._grid.setRowStretch(2, 0)  # footer — hauteur fixe
