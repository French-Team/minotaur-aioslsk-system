"""Tests pour le LayoutEntry — grille 3×3 des zones principales."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QWidget

from src.gui.layout.center import CenterZone
from src.gui.layout.entry import LayoutEntry
from src.gui.layout.footer import FooterZone
from src.gui.layout.header import HeaderZone
from src.gui.layout.left import LeftZone
from src.gui.layout.right import RightZone


@pytest.mark.qt_heavy
class TestLayoutEntry:
    """LayoutEntry : assemblage des 5 zones dans une grille 3×3."""

    def test_creer_entry(self, qapp) -> None:
        """Peut créer un LayoutEntry."""
        entry = LayoutEntry()
        assert entry is not None
        assert isinstance(entry, LayoutEntry)

    def test_object_name(self, qapp) -> None:
        """Le widget a le bon objectName."""
        entry = LayoutEntry()
        assert entry.objectName() == "layoutEntry"

    def test_zones_header(self, qapp) -> None:
        """La zone header est un HeaderZone."""
        entry = LayoutEntry()
        assert isinstance(entry.header, HeaderZone)

    def test_zones_left(self, qapp) -> None:
        """La zone left est un LeftZone."""
        entry = LayoutEntry()
        assert isinstance(entry.left, LeftZone)

    def test_zones_center(self, qapp) -> None:
        """La zone center est un CenterZone."""
        entry = LayoutEntry()
        assert isinstance(entry.center, CenterZone)

    def test_zones_right(self, qapp) -> None:
        """La zone right est un RightZone."""
        entry = LayoutEntry()
        assert isinstance(entry.right, RightZone)

    def test_zones_footer(self, qapp) -> None:
        """La zone footer est un FooterZone."""
        entry = LayoutEntry()
        assert isinstance(entry.footer, FooterZone)

    def test_grille_3x3_contient_5_widgets(self, qapp) -> None:
        """La grille contient 5 sous-widgets (header, left, center, right, footer)."""
        entry = LayoutEntry()
        # Le QGridLayout a 5 items
        assert entry._grid.count() == 5

    def test_header_en_haut(self, qapp) -> None:
        """Header est à la position (0, 0) dans la grille."""
        entry = LayoutEntry()
        index = entry._grid.indexOf(entry.header)
        pos = entry._grid.getItemPosition(index)
        assert pos[0] == 0  # row 0

    def test_footer_en_bas(self, qapp) -> None:
        """Footer est à la position (2, 0) dans la grille."""
        entry = LayoutEntry()
        index = entry._grid.indexOf(entry.footer)
        pos = entry._grid.getItemPosition(index)
        assert pos[0] == 2  # row 2

    def test_center_a_colonne_1_etirement(self, qapp) -> None:
        """Center a l'étirement de colonne 1 (prend l'espace)."""
        entry = LayoutEntry()
        assert entry._grid.columnStretch(1) == 1

    def test_signal_left_page_changed_est_connecte(self, qapp) -> None:
        """Le signal page_changed de left peut être émis sans erreur."""
        entry = LayoutEntry()
        emissions: list[str] = []
        entry.left.page_changed.connect(emissions.append)
        entry.left.page_changed.emit("accueil")
        assert len(emissions) == 1
        assert emissions[0] == "accueil"

    def test_parent_optionnel(self, qapp) -> None:
        """Peut créer un LayoutEntry avec un parent."""
        parent = QWidget()
        entry = LayoutEntry(parent)
        assert entry.parent() is parent
