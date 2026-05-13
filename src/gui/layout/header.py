"""
Zone Header — bannière d'informations.

Grille interne : 2 lignes × 5 colonnes (rows 1-2).
Chaque colonne représente une section d'information.

Colonnes :
  0 — Connexions
  1 — Clients actifs / joignables
  2 — Téléchargements en cours
  3 — Barre de progression
  4 — Horloge
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QWidget

from src.gui.widgets.clock import ClockWidget
from src.gui.widgets.clients_actifs import ClientsHeaderWidget
from src.gui.widgets.connexions import ConnexionHeaderWidget
from src.gui.widgets.progression import ProgressionWidget
from src.gui.widgets.telechargements import TelechargementsHeaderWidget


# ── Étiquettes par colonne ─────────────────────────────────────────
_HEADERS = [
    "🔌  Connexions",
    "👥  Clients",
    "⬇  Téléchargements",
    "📊  Progression",
    "🕐  Horloge",
]

_VALUES = [
    "Serveur : —",
    "Actif : —  /  Joignable : —",
    "En cours : —",
    "█ █ █ █ ░ ░ ░ ░ ░ ░",
    "--:--:--",
]


class HeaderZone(QFrame):
    """Bannière d'informations en haut de l'application.

    Grille : ligne 0 = titre, lignes 1-2 = cellules 2×5.
    """

    page_changed = Signal(str)  # émet le nom de la page à afficher

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setObjectName("headerZone")

        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(8, 8, 8, 8)
        self._grid.setSpacing(6)

        # Ligne 0 — titre provisoire
        title = QLabel("INFORMATIONS")
        title.setStyleSheet("color: #6c5ce7; font-size: 14px; font-weight: 700;")
        self._grid.addWidget(title, 0, 0, 1, 5)

        # Lignes 1-2 — grille 2×5
        self._cells: dict[tuple[int, int], QWidget] = {}
        for row, texts in enumerate((_HEADERS, _VALUES), start=1):
            for col, text in enumerate(texts):
                if col in (0, 1, 2, 3, 4):
                    # Colonne 0 (Connexions) — remplacée par ConnexionHeaderWidget
                    # Colonne 1 (Clients) — remplacée par ClientsHeaderWidget
                    # Colonne 2 (Téléchargements) — remplacée par TelechargementsHeaderWidget
                    # Colonne 3 (Progression) — remplacée par ProgressionWidget
                    # Colonne 4 (Horloge) — remplacée par le ClockWidget
                    continue
                label = QLabel(text)
                label.setObjectName(f"headerCell_{row}_{col}")
                if row == 1:
                    # Titre de section
                    label.setStyleSheet(
                        "color: #8a8a9a; font-size: 11px; font-weight: 600;"
                        " padding: 2px 6px;"
                    )
                else:
                    # Valeur / placeholder
                    label.setStyleSheet(
                        "color: #e4e4ec; font-size: 13px; font-weight: 500;"
                        " padding: 2px 6px;"
                    )
                self._grid.addWidget(label, row, col)
                self._cells[(row, col)] = label

        # Connexion — colonne 0, rows 1-2
        self._connexion = ConnexionHeaderWidget()
        self._connexion.clicked.connect(lambda: self.page_changed.emit("connexion"))
        self._grid.addWidget(self._connexion, 1, 0, 2, 1)

        # Clients actifs — colonne 1, rows 1-2
        self._clients = ClientsHeaderWidget()
        self._clients.clicked.connect(lambda: self.page_changed.emit("clients-actifs"))
        self._grid.addWidget(self._clients, 1, 1, 2, 1)

        # Téléchargements — colonne 2, rows 1-2
        self._telechargements = TelechargementsHeaderWidget()
        self._telechargements.clicked.connect(
            lambda: self.page_changed.emit("telechargements")
        )
        self._grid.addWidget(self._telechargements, 1, 2, 2, 1)

        # Progression — colonne 3, rows 1-2
        self._progression = ProgressionWidget()
        self._grid.addWidget(self._progression, 1, 3, 2, 1)

        # Horloge digitale — colonne 4, rows 1-2
        self._clock = ClockWidget()
        self._grid.addWidget(self._clock, 1, 4, 2, 1)

    # ── API publique ─────────────────────────────────────────────

    @property
    def connexion_widget(self) -> ConnexionHeaderWidget:
        """Widget de connexion dans le header."""
        return self._connexion

    @property
    def clients_widget(self) -> ClientsHeaderWidget:
        """Widget clients actifs dans le header."""
        return self._clients

    @property
    def telechargements_widget(self) -> TelechargementsHeaderWidget:
        """Widget téléchargements dans le header."""
        return self._telechargements

    @property
    def progression_widget(self) -> ProgressionWidget:
        """Widget progression dans le header."""
        return self._progression

    @property
    def clock_widget(self) -> ClockWidget:
        """Widget horloge dans le header."""
        return self._clock

    def cell(self, row: int, col: int) -> QWidget:
        """Retourne le widget de la cellule (row, col)."""
        widget = self._cells.get((row, col))
        if widget is None:
            raise IndexError(f"Cellule ({row}, {col}) inexistante dans le header")
        return widget

    def set_cell(self, row: int, col: int, widget: QWidget) -> None:
        """Remplace le contenu de la cellule (row, col) par un widget.

        Supprime l'ancien QLabel et place le nouveau widget.
        """
        old = self._cells.pop((row, col), None)
        if old is not None:
            self._grid.removeWidget(old)
            old.deleteLater()
        self._grid.addWidget(widget, row, col)
        self._cells[(row, col)] = widget
