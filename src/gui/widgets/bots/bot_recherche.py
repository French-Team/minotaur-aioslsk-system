"""
Bot Recherche — interface de recherche Soulseek avec tableau triable.

Barre de recherche + tableau 9 colonnes triables (tri par défaut : bitrate ↓).
Filtre audio mp3/flac/ogg toggleable + modal de filtres avancés.
Limite 200 résultats avec comportement FIFO.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.theme_fragments.colors import COLORS
from src.gui.widgets.bots.bot_recherche_modes import ModesPanel
from src.services.event_bus import EventBus
from src.services.search_history import SearchHistory
from src.utils.log_action import log_action

if TYPE_CHECKING:
    from src.services.clients_actifs_service import ClientsActifsService
    from src.services.connexion_manager import ConnexionManager

logger = logging.getLogger("[RECHERCHE]")

# ── Constantes ─────────────────────────────────────────────────

EXTENSIONS_AUDIO = {"mp3", "flac", "ogg"}
"""Extensions autorisées (sans le point, car extraites du filename)."""

MAX_RESULTS = 200
"""Nombre maximum de lignes affichées simultanément (FIFO)."""

# Attributs FileData
_ATTR_BITRATE = 0
_ATTR_DURATION = 1
_ATTR_VBR = 2
_ATTR_SAMPLE_RATE = 4

# Indices des colonnes du tableau
COL_EXTENSION = 0
COL_FICHIER = 1
COL_TAILLE = 2
COL_BITRATE = 3
COL_DUREE = 4
COL_UTILISATEUR = 5
COL_SLOTS = 6
COL_VITESSE = 7
COL_DL = 8

COLUMNS = [
    "Extension",
    "Fichier",
    "Taille",
    "Bitrate",
    "Durée",
    "Utilisateur",
    "Slots",
    "Vitesse",
    "DL",
]
"""Libellés des colonnes du tableau."""

# ── Helpers de formatage ───────────────────────────────────────


def _format_size(bytes_val: int) -> str:
    if bytes_val >= 1_000_000_000:
        return f"{bytes_val / 1_000_000_000:.1f} Go"
    if bytes_val >= 1_000_000:
        return f"{bytes_val / 1_000_000:.1f} Mo"
    if bytes_val >= 1_000:
        return f"{bytes_val / 1_000:.1f} Ko"
    return f"{bytes_val} o"


def _format_bitrate(bps: int) -> str:
    if bps >= 1000:
        return f"{bps // 1000} kbps"
    return f"{bps} bps"


def _format_duration(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    return f"{m}m{s:02d}s"


def _format_speed(bps: int) -> str:
    if bps >= 1_000_000:
        return f"{bps / 1_000_000:.1f} MB/s"
    if bps >= 1_000:
        return f"{bps / 1_000:.1f} KB/s"
    return f"{bps} B/s"


def _get_attr(attributes: list, key: int) -> int | None:
    for attr in attributes:
        if attr.key == key:
            return attr.value
    return None


def _extraire_extension(filename: str) -> str:
    """Extrait l'extension d'un fichier depuis son chemin complet.

    Utilise le filename (chemin) plutôt que les métadonnées du protocole
    Soulseek, car ``file_data.extension`` est souvent vide même quand
    le fichier a une vraie extension.

    Paramètres
    ----------
    filename : str
        Chemin complet du fichier (ex: ``Music/Artist/Album/track.mp3``).

    Retourne
    -------
    str
        L'extension en minuscules sans le point, ou ``""`` si absente.
    """
    if not filename:
        return ""
    # Normaliser les séparateurs et prendre le basename
    basename = filename.replace("\\", "/").rstrip("/").split("/")[-1]
    if "." in basename:
        return basename.rsplit(".", 1)[-1].lower()
    return ""


def _is_audio(extension: str) -> bool:
    """Vérifie si l'extension est un format audio autorisé."""
    return extension.lower() in EXTENSIONS_AUDIO


# ── Item de tableau avec tri numérique ─────────────────────────


class TableItem(QTableWidgetItem):
    """QTableWidgetItem qui stocke une valeur de tri distincte.

    Le tri standard de QTableWidgetItem est alphabétique.
    TableItem utilise ``Qt.UserRole`` pour conserver la valeur
    numérique, ce qui permet un tri correct (taille, bitrate, etc.).
    """

    def __init__(self, text: str, sort_value: Any = None) -> None:
        super().__init__(text)
        if sort_value is not None:
            # pyrefly: ignore [missing-attribute]
            self.setData(Qt.UserRole, sort_value)

    def __lt__(self, other: QTableWidgetItem) -> bool:
        # pyrefly: ignore [missing-attribute]
        my_val = self.data(Qt.UserRole)
        # pyrefly: ignore [missing-attribute]
        other_val = other.data(Qt.UserRole)
        if my_val is not None and other_val is not None:
            return my_val < other_val
        return super().__lt__(other)


# ═════════════════════════════════════════════════════════════════
#  Modal de filtres avancés
# ═════════════════════════════════════════════════════════════════


class FiltresRechercheModal(QDialog):
    """Modal centrée de filtres avancés pour les résultats."""

    def __init__(
        self,
        filter_state: dict,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Filtres avancés")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setMaximumWidth(500)

        # Résultat : copié depuis filter_state, lira les valeurs après exec()
        self.result_state: dict = dict(filter_state)

        self._setup_ui()
        self._load_state()

    # ── Construction ────────────────────────────────────────────

    def _setup_ui(self) -> None:
        """Construit l'interface de la modal."""
        self.setStyleSheet(
            f"""
            QDialog {{
                background: {COLORS["BG_SURFACE"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 8px;
            }}
            QLabel {{
                color: {COLORS["TEXT_PRIMARY"]};
                font-size: 12px;
            }}
            QGroupBox {{
                color: {COLORS["TEXT_PRIMARY"]};
                font-weight: 600;
                font-size: 12px;
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
            }}
            QSpinBox {{
                background: {COLORS.get("BG_INPUT", "#1a1a2a")};
                color: {COLORS["TEXT_PRIMARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 4px;
                padding: 4px 6px;
            }}
            QSpinBox:focus {{
                border-color: {COLORS["PRIMARY"]};
            }}
            QCheckBox {{
                color: {COLORS["TEXT_PRIMARY"]};
                spacing: 8px;
            }}
            QSlider::groove:horizontal {{
                border: 1px solid {COLORS["BORDER"]};
                height: 6px;
                background: {COLORS.get("BG_INPUT", "#1a1a2a")};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {COLORS["PRIMARY"]};
                border: none;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {COLORS["PRIMARY_HOVER"]};
            }}
            QLineEdit {{
                background: {COLORS.get("BG_INPUT", "#1a1a2a")};
                color: {COLORS["TEXT_PRIMARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS["PRIMARY"]};
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        # ── Titre ──
        header = QLabel("🔍 Filtres avancés")
        header.setStyleSheet(f"color: {COLORS['PRIMARY']}; font-size: 16px; font-weight: 700;")
        layout.addWidget(header)

        # ── Groupe : Qualité ──
        qualite = QGroupBox("Qualité")
        qualite_layout = QFormLayout(qualite)
        qualite_layout.setSpacing(8)
        qualite_layout.setContentsMargins(10, 16, 10, 10)

        # Bitrate min : Slider + SpinBox côte à côte
        bitrate_row = QHBoxLayout()
        # pyrefly: ignore [missing-attribute]
        self._bitrate_slider = QSlider(Qt.Horizontal)
        self._bitrate_slider.setRange(0, 1000)
        self._bitrate_slider.setTickInterval(128)
        # pyrefly: ignore [missing-attribute]
        self._bitrate_slider.setTickPosition(QSlider.TicksBelow)
        self._bitrate_slider.valueChanged.connect(self._on_bitrate_slider)
        bitrate_row.addWidget(self._bitrate_slider, 1)

        self._bitrate_spin = QSpinBox()
        self._bitrate_spin.setRange(0, 1000)
        self._bitrate_spin.setSuffix(" kbps")
        self._bitrate_spin.setSingleStep(32)
        self._bitrate_spin.valueChanged.connect(self._on_bitrate_spin)
        bitrate_row.addWidget(self._bitrate_spin)

        qualite_layout.addRow("Bitrate min :", bitrate_row)

        layout.addWidget(qualite)

        # ── Groupe : Durée ──
        duree = QGroupBox("Durée")
        duree_layout = QFormLayout(duree)
        duree_layout.setSpacing(8)
        duree_layout.setContentsMargins(10, 16, 10, 10)

        self._duration_min = QSpinBox()
        self._duration_min.setRange(0, 3600)
        self._duration_min.setSuffix(" s")
        self._duration_min.setSpecialValueText("Aucun")
        self._duration_min.setSingleStep(15)
        duree_layout.addRow("Min :", self._duration_min)

        self._duration_max = QSpinBox()
        self._duration_max.setRange(0, 7200)
        self._duration_max.setSuffix(" s")
        self._duration_max.setSpecialValueText("Aucun")
        self._duration_max.setSingleStep(30)
        duree_layout.addRow("Max :", self._duration_max)

        layout.addWidget(duree)

        # ── Groupe : Taille ──
        taille = QGroupBox("Taille")
        taille_layout = QFormLayout(taille)
        taille_layout.setSpacing(8)
        taille_layout.setContentsMargins(10, 16, 10, 10)

        self._size_min = QSpinBox()
        self._size_min.setRange(0, 10_000)
        self._size_min.setSpecialValueText("Aucun")
        self._size_min.setSuffix(" Mo")
        self._size_min.setSingleStep(1)
        taille_layout.addRow("Min :", self._size_min)

        self._size_max = QSpinBox()
        self._size_max.setRange(0, 10_000)
        self._size_max.setSpecialValueText("Aucun")
        self._size_max.setSuffix(" Mo")
        self._size_max.setSingleStep(5)
        taille_layout.addRow("Max :", self._size_max)

        layout.addWidget(taille)

        # ── Groupe : Utilisateur ──
        user = QGroupBox("Utilisateur")
        user_layout = QFormLayout(user)
        user_layout.setSpacing(8)
        user_layout.setContentsMargins(10, 16, 10, 10)

        self._username_input = QLineEdit()
        self._username_input.setPlaceholderText("Filtrer par pseudo…")
        user_layout.addRow("Pseudo :", self._username_input)

        self._slots_check = QCheckBox("Slots libres uniquement 🟢")
        user_layout.addRow("", self._slots_check)

        layout.addWidget(user)

        # ── Boutons ──
        layout.addStretch(1)
        # pyrefly: ignore [missing-attribute]
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Apply)
        buttons.accepted.connect(self._on_apply)
        buttons.rejected.connect(self.reject)
        # pyrefly: ignore [missing-attribute]
        buttons.button(QDialogButtonBox.Apply).setStyleSheet(
            f"""
            QPushButton {{
                background: {COLORS["PRIMARY"]};
                color: {COLORS["TEXT_WHITE"]};
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {COLORS["PRIMARY_HOVER"]};
            }}
            """
        )
        # pyrefly: ignore [missing-attribute]
        buttons.button(QDialogButtonBox.Cancel).setStyleSheet(
            f"""
            QPushButton {{
                background: {COLORS["BG_SURFACE2"]};
                color: {COLORS["TEXT_PRIMARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background: {COLORS["BG_HOVER"]};
            }}
            """
        )
        layout.addWidget(buttons)

    # ── Synchronisation slider/spinbox ──────────────────────────

    def _on_bitrate_slider(self, value: int) -> None:
        self._bitrate_spin.blockSignals(True)
        self._bitrate_spin.setValue(value)
        self._bitrate_spin.blockSignals(False)

    def _on_bitrate_spin(self, value: int) -> None:
        self._bitrate_slider.blockSignals(True)
        self._bitrate_slider.setValue(value)
        self._bitrate_slider.blockSignals(False)

    # ── Chargement / sauvegarde ─────────────────────────────────

    def _load_state(self) -> None:
        """Initialise les contrôles depuis l'état actuel."""
        self._bitrate_slider.setValue(self.result_state.get("bitrate_min", 0))
        self._bitrate_spin.setValue(self.result_state.get("bitrate_min", 0))
        self._duration_min.setValue(self.result_state.get("duration_min", 0))
        self._duration_max.setValue(self.result_state.get("duration_max", 0))
        self._size_min.setValue(self.result_state.get("size_min", 0))
        self._size_max.setValue(self.result_state.get("size_max", 0))
        self._username_input.setText(self.result_state.get("username", ""))
        self._slots_check.setChecked(self.result_state.get("slots_libres_only", False))

    def _save_state(self) -> None:
        """Sauvegarde les valeurs des contrôles dans result_state."""
        self.result_state["bitrate_min"] = self._bitrate_spin.value()
        self.result_state["duration_min"] = self._duration_min.value()
        self.result_state["duration_max"] = self._duration_max.value()
        self.result_state["size_min"] = self._size_min.value()
        self.result_state["size_max"] = self._size_max.value()
        self.result_state["username"] = self._username_input.text().strip()
        self.result_state["slots_libres_only"] = self._slots_check.isChecked()

    @log_action("Appliquer les filtres de recherche")
    def _on_apply(self) -> None:
        """Applique les filtres et ferme la modal."""
        self._save_state()
        self.accept()


# ═════════════════════════════════════════════════════════════════
#  Page Recherche
# ═════════════════════════════════════════════════════════════════


class HistoryPopup(QDialog):
    """Fenêtre modale affichant l'historique complet des recherches.

    L'utilisateur peut cliquer sur une entrée pour relancer la
    recherche correspondante.
    """

    clear_requested = Signal()
    """Émis quand l'utilisateur clique sur "Tout effacer"."""

    entries_changed = Signal()
    """Émis quand une entrée est supprimée individuellement."""

    def __init__(
        self,
        entries: list[dict],
        parent: QWidget | None = None,
        history: "SearchHistory | None" = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("📜 Historique des recherches")
        self.setMinimumSize(480, 400)
        self.setModal(True)
        self.selected_entry: dict | None = None
        self._history = history
        self._entries = entries

        self._list_layout: QVBoxLayout | None = None
        self._title_label: QLabel | None = None

        self._setup_ui(entries)

    def _setup_ui(self, entries: list[dict]) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(8)

        # Titre
        self._title_label = QLabel(f"📜 Historique ({len(entries)} recherche(s))")
        self._title_label.setStyleSheet(f"color: {COLORS['PRIMARY']}; font-size: 16px; font-weight: 700;")
        layout.addWidget(self._title_label)

        if not entries:
            empty = QLabel("Aucune recherche pour l'instant.")
            empty.setStyleSheet(f"color: {COLORS['TEXT_SECONDARY']}; font-size: 13px; padding: 20px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(empty, 1)
            self._close_btn(layout)
            return

        # Liste défilable
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        # pyrefly: ignore [missing-attribute]
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"background: transparent; border: none;")

        list_widget = QWidget()
        self._list_layout = QVBoxLayout(list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(4)

        self._build_entry_rows(entries)

        self._list_layout.addStretch(1)
        scroll.setWidget(list_widget)
        layout.addWidget(scroll, 1)

        self._close_btn(layout)

    def _build_entry_rows(self, entries: list[dict]) -> None:
        """Construit les lignes de la liste d'historique (bouton cliquable + ✕)."""
        for entry in entries:
            q = entry["query"]
            type_ = entry.get("type", "global")
            username = entry.get("username")
            count = entry.get("count", 0)
            ts = entry.get("timestamp", "")

            # Icône selon le type
            if type_ == "room":
                icon = "💬"
                extra = f" #{username}"
            elif type_ == "user":
                icon = "👤"
                extra = f" {username}"
            else:
                icon = "🌐"
                extra = ""

            # Texte court
            q_short = q[:42] + "…" if len(q) > 42 else q

            # ── Ligne : bouton principal + X ──
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)

            btn = QPushButton(f"{icon}  {q_short}{extra}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: {COLORS["BG_SURFACE"]};
                    color: {COLORS["TEXT_PRIMARY"]};
                    border: 1px solid {COLORS["BORDER"]};
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 12px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background: rgba(COLORS['PRIMARY'], '15');
                    border-color: {COLORS["PRIMARY"]};
                }}
                """
            )

            if count > 0:
                btn.setText(btn.text() + f"  —  {count} résultat{'s' if count > 1 else ''}")

            if ts:
                date_part = ts[:10] if "T" in ts else ts
                btn.setText(btn.text() + f"  ({date_part})")

            btn.clicked.connect(lambda checked, e=entry: self._on_select(e))
            row_layout.addWidget(btn, 1)

            # Bouton ✕ pour supprimer cette entrée
            x_btn = QPushButton("✕")
            x_btn.setFixedSize(28, 28)
            x_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            x_btn.setToolTip("Supprimer cette entrée")
            x_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: transparent;
                    color: #999999;
                    border: 1px solid transparent;
                    border-radius: 14px;
                    font-size: 11px;
                    font-weight: 700;
                    padding: 0;
                }}
                QPushButton:hover {{
                    color: {COLORS["DANGER_BTN"]};
                    background: {COLORS["DANGER_BG_HOVER"]};
                    border-color: {COLORS["DANGER_BTN"]};
                }}
                """
            )
            x_btn.clicked.connect(lambda checked, e=entry: self._on_remove_entry(e))
            row_layout.addWidget(x_btn)

            # pyrefly: ignore [missing-attribute]
            self._list_layout.addWidget(row)

    @log_action("Supprimer une entrée d'historique")
    def _on_remove_entry(self, entry: dict) -> None:
        """Supprime une entrée de l'historique et rafraîchit la popup."""
        if self._history is None:
            return
        self._history.remove(
            entry["query"],
            entry.get("type", "global"),
            entry.get("username"),
        )
        self._entries = self._history.get_all()
        self.entries_changed.emit()
        self._rebuild_entries_ui()

    def _rebuild_entries_ui(self) -> None:
        """Reconstruit la liste des entrées après une suppression."""
        # Vider la liste existante
        # pyrefly: ignore [missing-attribute]
        while self._list_layout.count():
            # pyrefly: ignore [missing-attribute]
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Mettre à jour le titre
        if self._title_label:
            self._title_label.setText(f"📜 Historique ({len(self._entries)} recherche(s))")

        if not self._entries:
            empty = QLabel("Aucune recherche pour l'instant.")
            empty.setStyleSheet(f"color: {COLORS['TEXT_SECONDARY']}; font-size: 13px; padding: 20px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # pyrefly: ignore [missing-attribute]
            self._list_layout.addWidget(empty)
            # pyrefly: ignore [missing-attribute]
            self._list_layout.addStretch(1)
            return

        self._build_entry_rows(self._entries)
        # pyrefly: ignore [missing-attribute]
        self._list_layout.addStretch(1)

    def _close_btn(self, layout: QVBoxLayout) -> None:
        row = QHBoxLayout()
        row.setSpacing(8)

        # Bouton Tout effacer
        clear_btn = QPushButton("\U0001f5d1 Tout effacer")
        clear_btn.setObjectName("clearHistoryBtn")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(
            f"""
            #clearHistoryBtn {{
                background: transparent;
                color: {COLORS["DANGER_BTN"]};
                border: 1px solid {COLORS["DANGER_BTN"]};
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            #clearHistoryBtn:hover {{
                background: {COLORS["DANGER_BG_HOVER"]};
            }}
            """
        )
        clear_btn.clicked.connect(self._on_clear)
        row.addWidget(clear_btn)

        row.addStretch(1)

        btn = QPushButton("Fermer")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {COLORS["PRIMARY"]};
                color: {COLORS["TEXT_WHITE"]};
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {COLORS["PRIMARY_HOVER"]};
            }}
            """
        )
        btn.clicked.connect(self.reject)

        row.addWidget(btn)
        layout.addLayout(row)

    @log_action("Sélectionner une entrée d'historique")
    def _on_select(self, entry: dict) -> None:
        self.selected_entry = entry
        self.accept()

    @log_action("Tout effacer l'historique")
    def _on_clear(self) -> None:
        """Émet le signal pour vider l'historique et ferme la popup."""
        self.clear_requested.emit()
        self.accept()


# ═════════════════════════════════════════════════════════════════
#  Arbre de navigation par dossiers
# ═════════════════════════════════════════════════════════════════


class DossierTreeWidget(QTreeWidget):
    """Arbre de résultats de recherche groupés par dossier parent.

    Remplace le tableau plat par une vue explorateur avec dossiers
    expandables. Les fichiers individuels sont affichés sous leur
    dossier parent respectif avec les mêmes colonnes.
    """

    COL_NOM = 0
    COL_TAILLE = 1
    COL_BITRATE = 2
    COL_DUREE = 3
    COL_UTILISATEUR = 4
    COL_SLOTS = 5
    COL_VITESSE = 6

    COLUMNS = [
        "📁 Fichier / Dossier",
        "Taille",
        "Bitrate",
        "Durée",
        "Utilisateur",
        "Slots",
        "Vitesse",
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dossierTree")
        self.setColumnCount(len(self.COLUMNS))
        self.setHeaderLabels(self.COLUMNS)
        self.setAlternatingRowColors(True)
        # pyrefly: ignore [missing-attribute]
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        # pyrefly: ignore [missing-attribute]
        # pyrefly: ignore [missing-attribute]
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # pyrefly: ignore [missing-attribute]
        self.setAnimated(True)
        self.setIndentation(20)
        self.setRootIsDecorated(True)
        self.header().setStretchLastSection(False)
        # pyrefly: ignore [missing-attribute]
        self.header().setSectionResizeMode(self.COL_NOM, QHeaderView.Stretch)
        # pyrefly: ignore [missing-attribute]
        self.header().setSectionResizeMode(self.COL_TAILLE, QHeaderView.Fixed)
        self.setColumnWidth(self.COL_TAILLE, 90)
        # pyrefly: ignore [missing-attribute]
        self.header().setSectionResizeMode(self.COL_BITRATE, QHeaderView.Fixed)
        self.setColumnWidth(self.COL_BITRATE, 100)
        # pyrefly: ignore [missing-attribute]
        self.header().setSectionResizeMode(self.COL_DUREE, QHeaderView.Fixed)
        self.setColumnWidth(self.COL_DUREE, 80)
        # pyrefly: ignore [missing-attribute]
        self.header().setSectionResizeMode(self.COL_UTILISATEUR, QHeaderView.Fixed)
        self.setColumnWidth(self.COL_UTILISATEUR, 140)
        # pyrefly: ignore [missing-attribute]
        self.header().setSectionResizeMode(self.COL_SLOTS, QHeaderView.Fixed)
        self.setColumnWidth(self.COL_SLOTS, 50)
        # pyrefly: ignore [missing-attribute]
        self.header().setSectionResizeMode(self.COL_VITESSE, QHeaderView.Fixed)
        self.setColumnWidth(self.COL_VITESSE, 90)

        self.setStyleSheet(
            f"""
            #dossierTree {{
                background: {COLORS["BG_SURFACE"]};
                alternate-background-color: {COLORS.get("BG_SURFACE2", "#2a2a3a")};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                font-size: 12px;
            }}
            #dossierTree::item {{
                padding: 4px 8px;
                color: {COLORS["TEXT_PRIMARY"]};
            }}
            #dossierTree::item:selected {{
                background: rgba(COLORS['ACCENT'], '50');
                color: {COLORS["TEXT_PRIMARY"]};
            }}
            #dossierTree::branch:has-children:!has-siblings:closed,
            #dossierTree::branch:closed:has-children:has-siblings {{
                border-image: none;
            }}
            #dossierTree::branch:open:has-children:!has-siblings,
            #dossierTree::branch:open:has-children:has-siblings {{
                border-image: none;
            }}
            QHeaderView::section {{
                background: {COLORS.get("BG_HEADER", COLORS["BG_SURFACE2"])};
                color: {COLORS["TEXT_PRIMARY"]};
                border: none;
                border-bottom: 1px solid {COLORS["BORDER"]};
                border-right: 1px solid {COLORS["BORDER"]};
                padding: 6px 8px;
                font-weight: 700;
                font-size: 11px;
            }}
            QHeaderView::section:hover {{
                background: {COLORS["BG_HOVER"]};
            }}
            QHeaderView::down-arrow {{
                subcontrol-position: center right;
                padding-right: 4px;
            }}
            QHeaderView::up-arrow {{
                subcontrol-position: center right;
                padding-right: 4px;
            }}
            """
        )

    # ── Construction de l'arbre ─────────────────────────────────

    def build_from_cache(self, cache: list[dict]) -> None:
        """Construit ou reconstruit l'arbre à partir du cache de résultats.

        Paramètres
        ----------
        cache : list[dict]
            Liste des données brutes de chaque résultat (contenant
            ``full_path``, ``filename``, ``filesize``, etc.).
        """
        self.clear()

        if not cache:
            return

        # Construire une structure arborescente : dict imbriqué
        tree: dict[str, object] = {}
        for data in cache:
            full_path = data.get("full_path", "")
            if not full_path:
                continue

            # Découper le chemin en segments
            parts = [p for p in full_path.replace("\\", "/").split("/") if p]
            if not parts:
                continue

            # Parcourir / créer les dossiers
            current = tree
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Dernier segment = fichier
            filename = parts[-1]
            if filename not in current:
                current[filename] = data

        # Remplir le QTreeWidget
        self._add_tree_items(tree, self.invisibleRootItem())

        # Expand le premier niveau
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            item.setExpanded(True)

    def _add_tree_items(self, tree: dict, parent_item: QTreeWidgetItem) -> None:
        """Ajoute récursivement les dossiers/fichiers dans le QTreeWidget.

        Les dossiers sont triés alphabétiquement et apparaissent avant
        les fichiers (dossiers first).

        La distinction dossier/fichier se fait par la présence d'une
        clé ``filename`` dans le dict valeur — si présente, c'est une
        feuille (fichier), sinon c'est un dossier.
        """
        # Séparer dossiers et fichiers pour tri "dossiers first"
        dirs: dict[str, dict] = {}
        files: dict[str, dict] = {}

        for name, value in tree.items():
            if isinstance(value, dict):
                # Un dict qui contient "filename" est une feuille (fichier)
                # Sinon c'est un dossier contenant d'autres entrées
                if "filename" in value:
                    files[name] = value
                else:
                    dirs[name] = value
            else:
                files[name] = value

        # Trier les dossiers par nom
        for dirname in sorted(dirs.keys()):
            sub_tree = dirs[dirname]
            file_count = self._count_files(sub_tree)

            dir_item = QTreeWidgetItem()
            dir_item.setText(self.COL_NOM, f"📁  {dirname}")
            dir_item.setForeground(self.COL_NOM, QColor(COLORS["ACCENT"]))
            font = dir_item.font(self.COL_NOM)
            font.setBold(True)
            dir_item.setFont(self.COL_NOM, font)
            dir_item.setText(
                self.COL_TAILLE,
                f"{file_count} fichier{'s' if file_count > 1 else ''}",
            )
            dir_item.setToolTip(
                self.COL_NOM,
                f"📁 {dirname} — {file_count} fichier{'s' if file_count > 1 else ''}",
            )
            dir_item.setData(self.COL_NOM, Qt.UserRole, {"type": "directory", "path": dirname})

            self._add_tree_items(sub_tree, dir_item)
            parent_item.addChild(dir_item)

        # Trier les fichiers par nom
        for fname in sorted(files.keys()):
            data = files[fname]
            file_item = self._build_file_item(data)
            parent_item.addChild(file_item)

    def _build_file_item(self, data: dict) -> QTreeWidgetItem:
        """Crée un QTreeWidgetItem pour un fichier avec toutes ses colonnes."""
        item = QTreeWidgetItem()

        filename = data.get("filename", "?")
        item.setText(self.COL_NOM, f"📄  {filename}")
        item.setData(self.COL_NOM, Qt.UserRole, {"type": "file", "data": data})

        # Taille
        filesize = data.get("filesize", 0)
        item.setText(self.COL_TAILLE, _format_size(filesize))
        item.setTextAlignment(self.COL_TAILLE, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        item.setData(self.COL_TAILLE, Qt.UserRole, filesize)

        # Bitrate
        bitrate = data.get("bitrate", 0)
        item.setText(self.COL_BITRATE, _format_bitrate(bitrate))
        item.setTextAlignment(self.COL_BITRATE, Qt.AlignmentFlag.AlignCenter)
        item.setData(self.COL_BITRATE, Qt.UserRole, bitrate)

        # Durée
        duration = data.get("duration", 0)
        duree_str = _format_duration(duration) if duration > 0 else "—"
        item.setText(self.COL_DUREE, duree_str)
        item.setTextAlignment(self.COL_DUREE, Qt.AlignmentFlag.AlignCenter)
        item.setData(self.COL_DUREE, Qt.UserRole, duration)

        # Utilisateur
        username = data.get("username", "")
        item.setText(self.COL_UTILISATEUR, username)
        item.setToolTip(self.COL_UTILISATEUR, f"👤 {username}")

        # Slots
        has_free_slots = data.get("has_free_slots", False)
        item.setText(self.COL_SLOTS, "🟢" if has_free_slots else "🔴")
        item.setTextAlignment(self.COL_SLOTS, Qt.AlignmentFlag.AlignCenter)
        item.setToolTip(self.COL_SLOTS, "Slots libres" if has_free_slots else "File d'attente")

        # Vitesse
        avg_speed = data.get("avg_speed", 0)
        speed_str = _format_speed(avg_speed) if avg_speed > 0 else "—"
        item.setText(self.COL_VITESSE, speed_str)
        item.setTextAlignment(self.COL_VITESSE, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        item.setData(self.COL_VITESSE, Qt.UserRole, avg_speed)

        return item

    def _count_files(self, tree: dict) -> int:
        """Compte récursivement le nombre de fichiers dans une branche de l'arbre."""
        count = 0
        for v in tree.values():
            if isinstance(v, dict):
                if "filename" in v:
                    # Feuille : un fichier = 1
                    count += 1
                else:
                    # Nœud interne : récursion dans le sous-dossier
                    count += self._count_files(v)
        return count


class BotRecherche(QFrame):
    """Page de recherche Soulseek avec barre + tableau triable + filtres."""

    page_changed = Signal(str)
    """Émis pour rediriger vers un autre bot (ex: "Téléchargement")."""

    def __init__(
        self,
        connexion_manager: ConnexionManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("botRecherche")
        # pyrefly: ignore [missing-attribute]
        self.setFrameShape(QFrame.NoFrame)

        self._actif = False
        self._connexion_manager = connexion_manager
        self._clients_actifs_service: ClientsActifsService | None = None
        self._searching = False
        self._search_timer: QTimer | None = None
        self._loop_timer: QTimer = QTimer(self)
        self._loop_timer.setInterval(60000)  # 60s entre chaque tick
        self._loop_timer.timeout.connect(self._on_loop_tick)

        self._result_count = 0
        self._total_received = 0
        self._audio_filter_enabled = True
        self._mode_dispo_enabled = False
        self._browse_username: str | None = None
        self._room_name: str | None = None

        # État des filtres avancés
        self._filter_state: dict = {
            "bitrate_min": 0,
            "duration_min": 0,
            "duration_max": 0,
            "size_min": 0,
            "size_max": 0,
            "username": "",
            "slots_libres_only": False,
        }
        self._filtres_compte = 0
        self._filtres_badge: QLabel | None = None
        self._search_history = SearchHistory()
        self._selected_client_username: str | None = None

        # Cache des résultats bruts pour reconstruction table/arbre
        self._result_data: list[dict] = []
        self._folder_view: bool = False

        self._setup_ui()
        self._update_connected_state()

    # ── Interrupteur ─────────────────────────────────────────────

    def demarrer(self) -> None:
        """Active l'interrupteur → démarre la boucle Recherche."""
        if self._actif:
            return
        self._actif = True
        self._loop_timer.start()
        self._on_loop_tick()
        logger.info("BotRecherche démarré (cycle 60s)")

    def arreter(self) -> None:
        """Désactive l'interrupteur → suspend la boucle Recherche."""
        if not self._actif:
            return
        self._actif = False
        self._loop_timer.stop()
        logger.info("BotRecherche arrêté")

    def _on_loop_tick(self) -> None:
        """Tick périodique : vérifie l'état de connexion."""
        if not self._actif:
            return
        self._update_connected_state()
        logger.debug("BotRecherche tick — connexion OK" if (
            self._connexion_manager is not None and self._connexion_manager.is_connected
        ) else "BotRecherche tick — déconnecté")

    # ── Injection des services ─────────────────────────────────

    def setup(self, clients_actifs_service: ClientsActifsService) -> None:
        """Injecte le service clients actifs pour la recherche ciblée."""
        self._clients_actifs_service = clients_actifs_service
        self._update_ares_clients()

        # État initial du système
        self._push_system_status()

        # Mise à jour automatique quand les clients changent
        clients_actifs_service.clients_synchronises.connect(self._on_clients_synchronises)

    # ── Construction de l'interface ─────────────────────────────

    def _setup_ui(self) -> None:
        """Construit l'interface complète."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 8)
        outer.setSpacing(6)

        # ── Titre + boutons de filtre ──
        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        title = QLabel("🔍 Recherche Soulseek")
        title.setStyleSheet(f"color: {COLORS['PRIMARY']}; font-size: 18px; font-weight: 700;")
        title_row.addWidget(title)

        # Badge de filtres actifs (caché si aucun filtre)
        self._filtres_badge = QLabel("")
        self._filtres_badge.setStyleSheet(
            f"""
            color: {COLORS["WARNING"]};
            background: rgba(COLORS['WARNING'], '20');
            border: 1px solid {COLORS["WARNING"]};
            border-radius: 8px;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: 700;
            """
        )
        self._filtres_badge.setVisible(False)
        title_row.addWidget(self._filtres_badge)

        # Bouton Filtres
        self._filtres_btn = QPushButton("🔍 Filtres")
        self._filtres_btn.setObjectName("filtresBtn")
        self._filtres_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._filtres_btn.setStyleSheet(
            f"""
            #filtresBtn {{
                background: transparent;
                color: {COLORS["TEXT_SECONDARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            #filtresBtn:hover {{
                border-color: {COLORS["PRIMARY"]};
                color: {COLORS["PRIMARY"]};
            }}
            """
        )
        self._filtres_btn.clicked.connect(self._open_filtres_modal)
        title_row.addWidget(self._filtres_btn)

        # Toggle audio
        self._audio_filter_btn = QPushButton("🔊 Audio seulement")
        self._audio_filter_btn.setObjectName("audioFilterBtn")
        self._audio_filter_btn.setCheckable(True)
        self._audio_filter_btn.setChecked(True)
        self._audio_filter_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._audio_filter_btn.setStyleSheet(
            f"""
            #audioFilterBtn {{
                background: rgba(COLORS['PRIMARY'], '20');
                color: {COLORS["PRIMARY"]};
                border: 1px solid {COLORS["PRIMARY"]};
                border-radius: 6px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            #audioFilterBtn:checked {{
                background: rgba(COLORS['PRIMARY'], '20');
                border-color: {COLORS["PRIMARY"]};
                color: {COLORS["PRIMARY"]};
            }}
            #audioFilterBtn:!checked {{
                background: transparent;
                border-color: {COLORS["BORDER"]};
                color: {COLORS["TEXT_SECONDARY"]};
            }}
            #audioFilterBtn:hover {{
                border-color: {COLORS["PRIMARY"]};
                color: {COLORS["PRIMARY"]};
            }}
            """
        )
        self._audio_filter_btn.toggled.connect(self._on_audio_filter_toggled)
        title_row.addWidget(self._audio_filter_btn)

        # Toggle Mode dispo (slots libres uniquement)
        self._mode_dispo_btn = QPushButton("🔴 Mode dispo")
        self._mode_dispo_btn.setObjectName("modeDispoBtn")
        self._mode_dispo_btn.setCheckable(True)
        self._mode_dispo_btn.setChecked(False)
        self._mode_dispo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mode_dispo_btn.setStyleSheet(
            f"""
            #modeDispoBtn {{
                background: transparent;
                color: {COLORS["TEXT_SECONDARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            #modeDispoBtn:checked {{
                background: rgba(COLORS['SUCCESS'], '30');
                border-color: {COLORS["SUCCESS"]};
                color: {COLORS["SUCCESS"]};
            }}
            #modeDispoBtn:hover {{
                border-color: {COLORS["SUCCESS"]};
                color: {COLORS["SUCCESS"]};
            }}
            """
        )
        self._mode_dispo_btn.toggled.connect(self._on_mode_dispo_toggled)
        title_row.addWidget(self._mode_dispo_btn)

        # Toggle vue fichiers / dossiers
        self._view_toggle_btn = QPushButton("📁 Vue dossiers")
        self._view_toggle_btn.setObjectName("viewToggleBtn")
        self._view_toggle_btn.setCheckable(True)
        self._view_toggle_btn.setChecked(False)
        self._view_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._view_toggle_btn.setStyleSheet(
            f"""
            #viewToggleBtn {{
                background: transparent;
                color: {COLORS["TEXT_SECONDARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            #viewToggleBtn:checked {{
                background: rgba(COLORS['ACCENT'], '20');
                border-color: {COLORS["ACCENT"]};
                color: {COLORS["ACCENT"]};
            }}
            #viewToggleBtn:hover {{
                border-color: {COLORS["ACCENT"]};
                color: {COLORS["ACCENT"]};
            }}
            """
        )
        self._view_toggle_btn.toggled.connect(self._toggle_view)
        title_row.addWidget(self._view_toggle_btn)

        title_row.addStretch(1)
        outer.addLayout(title_row)

        # ── Bannière mode utilisateur (cachée par défaut) ──
        self._browse_banner = QFrame()
        self._browse_banner.setObjectName("browseBanner")
        self._browse_banner.setStyleSheet(
            f"""
            #browseBanner {{
                background: rgba(COLORS['PRIMARY'], '15');
                border: 1px solid rgba(COLORS['PRIMARY'], '40');
                border-radius: 6px;
                padding: 6px 10px;
            }}
            """
        )
        self._browse_banner.setVisible(False)

        banner_layout = QHBoxLayout(self._browse_banner)
        banner_layout.setContentsMargins(10, 6, 10, 6)
        banner_layout.setSpacing(8)

        self._browse_icon = QLabel("👤")
        self._browse_icon.setStyleSheet(f"font-size: 14px; background: transparent; border: none;")
        banner_layout.addWidget(self._browse_icon)

        self._browse_label = QLabel("")
        self._browse_label.setStyleSheet(
            f"color: {COLORS['PRIMARY']}; font-size: 13px; font-weight: 600; background: transparent; border: none;"
        )
        banner_layout.addWidget(self._browse_label, 1)

        self._browse_back_btn = QPushButton("← Retour à la recherche globale")
        self._browse_back_btn.setObjectName("browseBackBtn")
        self._browse_back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse_back_btn.setStyleSheet(
            f"""
            #browseBackBtn {{
                background: transparent;
                color: {COLORS["TEXT_SECONDARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            #browseBackBtn:hover {{
                border-color: {COLORS["PRIMARY"]};
                color: {COLORS["PRIMARY"]};
            }}
            """
        )
        self._browse_back_btn.clicked.connect(self._exit_browse_mode)
        banner_layout.addWidget(self._browse_back_btn)

        outer.addWidget(self._browse_banner)

        # ── Bannière mode salon (cachée par défaut) ──
        self._room_banner = QFrame()
        self._room_banner.setObjectName("roomBanner")
        self._room_banner.setStyleSheet(
            f"""
            #roomBanner {{
                background: rgba(COLORS['WARNING'], '15');
                border: 1px solid rgba(COLORS['WARNING'], '40');
                border-radius: 6px;
                padding: 6px 10px;
            }}
            """
        )
        self._room_banner.setVisible(False)

        room_banner_layout = QHBoxLayout(self._room_banner)
        room_banner_layout.setContentsMargins(10, 6, 10, 6)
        room_banner_layout.setSpacing(8)

        room_icon = QLabel("💬")
        room_icon.setStyleSheet(f"font-size: 14px; background: transparent; border: none;")
        room_banner_layout.addWidget(room_icon)

        self._room_label = QLabel("")
        self._room_label.setStyleSheet(
            f"color: {COLORS['WARNING']}; font-size: 13px; font-weight: 600; background: transparent; border: none;"
        )
        room_banner_layout.addWidget(self._room_label, 1)

        self._room_back_btn = QPushButton("← Retour à la recherche globale")
        self._room_back_btn.setObjectName("roomBackBtn")
        self._room_back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._room_back_btn.setStyleSheet(
            f"""
            #roomBackBtn {{
                background: transparent;
                color: {COLORS["TEXT_SECONDARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            #roomBackBtn:hover {{
                border-color: {COLORS["WARNING"]};
                color: {COLORS["WARNING"]};
            }}
            """
        )
        self._room_back_btn.clicked.connect(self._exit_room_mode)
        room_banner_layout.addWidget(self._room_back_btn)

        outer.addWidget(self._room_banner)

        # ── Panneau des modes de recherche (remplace la barre de recherche v1) ──
        self._modes_panel = ModesPanel()
        self._modes_panel.search_requested.connect(self._on_search)
        self._modes_panel.search_stopped.connect(self._on_stop)
        self._modes_panel.mode_changed.connect(self._on_mode_changed)
        self._modes_panel.client_ares_selected.connect(self._on_client_ares_changed)
        outer.addWidget(self._modes_panel)

        # ── Barre d'état / compteur ──
        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"color: {COLORS['TEXT_SECONDARY']}; font-size: 12px;")
        outer.addWidget(self._status_label)

        # ── Suggestions d'historique ──
        self._suggestions_row = QWidget()
        self._suggestions_row.setLayout(QHBoxLayout())
        # pyrefly: ignore [missing-attribute]
        self._suggestions_row.layout().setSpacing(6)
        self._suggestions_widgets: list[QPushButton] = []

        self._history_btn = QPushButton("📜 Historique")
        self._history_btn.setObjectName("historyBtn")
        self._history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._history_btn.setStyleSheet(
            f"""
            #historyBtn {{
                background: transparent;
                color: {COLORS["TEXT_SECONDARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 10px;
                padding: 4px 10px;
                font-size: 10px;
                font-weight: 600;
            }}
            #historyBtn:hover {{
                border-color: {COLORS["PRIMARY"]};
                color: {COLORS["PRIMARY"]};
            }}
            """
        )
        self._history_btn.clicked.connect(self._open_history_popup)

        self._rebuild_suggestions()
        outer.addWidget(self._suggestions_row)

        # ── Arbre de navigation par dossiers ──
        self._dossier_tree = DossierTreeWidget()
        # pyrefly: ignore [missing-attribute]
        self._dossier_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._dossier_tree.customContextMenuRequested.connect(self._on_tree_context_menu)

        # ── Stack : page 0 = tableau, page 1 = arbre ──
        self._view_stack = QStackedWidget()

        # ── Tableau de résultats ──
        self._table = QTableWidget()
        self._table.setObjectName("resultTable")
        self._table.setColumnCount(len(COLUMNS))
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.setAlternatingRowColors(True)
        # pyrefly: ignore [missing-attribute]
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        # pyrefly: ignore [missing-attribute]
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        # pyrefly: ignore [missing-attribute]
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)

        self._table.setStyleSheet(
            f"""
            #resultTable {{
                background: {COLORS["BG_SURFACE"]};
                alternate-background-color: {COLORS.get("BG_SURFACE2", "#2a2a3a")};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                gridline-color: transparent;
                font-size: 12px;
            }}
            #resultTable::item {{
                padding: 4px 8px;
                color: {COLORS["TEXT_PRIMARY"]};
            }}
            #resultTable::item:selected {{
                background: rgba(COLORS['PRIMARY'], '50');
                color: {COLORS["TEXT_PRIMARY"]};
            }}
            QHeaderView::section {{
                background: {COLORS.get("BG_HEADER", COLORS["BG_SURFACE2"])};
                color: {COLORS["TEXT_PRIMARY"]};
                border: none;
                border-bottom: 1px solid {COLORS["BORDER"]};
                border-right: 1px solid {COLORS["BORDER"]};
                padding: 6px 8px;
                font-weight: 700;
                font-size: 11px;
            }}
            QHeaderView::section:hover {{
                background: {COLORS["BG_HOVER"]};
            }}
            """
        )

        header = self._table.horizontalHeader()
        header.setStretchLastSection(False)
        # pyrefly: ignore [missing-attribute]
        header.setSectionResizeMode(COL_FICHIER, QHeaderView.Stretch)
        # pyrefly: ignore [missing-attribute]
        header.setSectionResizeMode(COL_EXTENSION, QHeaderView.Fixed)
        # pyrefly: ignore [missing-attribute]
        header.setSectionResizeMode(COL_TAILLE, QHeaderView.Fixed)
        # pyrefly: ignore [missing-attribute]
        header.setSectionResizeMode(COL_BITRATE, QHeaderView.Fixed)
        # pyrefly: ignore [missing-attribute]
        header.setSectionResizeMode(COL_DUREE, QHeaderView.Fixed)
        # pyrefly: ignore [missing-attribute]
        header.setSectionResizeMode(COL_UTILISATEUR, QHeaderView.Fixed)
        # pyrefly: ignore [missing-attribute]
        header.setSectionResizeMode(COL_SLOTS, QHeaderView.Fixed)
        # pyrefly: ignore [missing-attribute]
        header.setSectionResizeMode(COL_VITESSE, QHeaderView.Fixed)
        # pyrefly: ignore [missing-attribute]
        header.setSectionResizeMode(COL_DL, QHeaderView.Fixed)

        self._table.setColumnWidth(COL_EXTENSION, 80)
        self._table.setColumnWidth(COL_TAILLE, 90)
        self._table.setColumnWidth(COL_BITRATE, 100)
        self._table.setColumnWidth(COL_DUREE, 80)
        self._table.setColumnWidth(COL_UTILISATEUR, 140)
        self._table.setColumnWidth(COL_SLOTS, 50)
        self._table.setColumnWidth(COL_VITESSE, 90)
        self._table.setColumnWidth(COL_DL, 40)

        self._table.setSortingEnabled(True)
        # pyrefly: ignore [missing-attribute]
        self._table.sortByColumn(COL_BITRATE, Qt.DescendingOrder)

        # Menu contextuel (clic droit)
        # pyrefly: ignore [missing-attribute]
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)

        # Ajouter table (0) et arbre (1) au stack
        self._view_stack.addWidget(self._table)        # page 0
        self._view_stack.addWidget(self._dossier_tree)  # page 1
        self._view_stack.setCurrentIndex(0)

        outer.addWidget(self._view_stack, 1)

    # ── API publique ────────────────────────────────────────────

    def set_connexion_manager(self, manager: ConnexionManager) -> None:
        """Définit le gestionnaire de connexion et connecte les signaux."""
        self._connexion_manager = manager

        manager.search_result_received.connect(self._on_search_result)
        manager.connected.connect(self._on_connected)
        manager.disconnected.connect(self._on_disconnected)
        manager.error_occurred.connect(self._on_search_error)

        self._update_connected_state()

        # Alimenter le sélecteur de clients Arès dès que disponible
        self._update_ares_clients()

    def _on_mode_changed(self, mode: str) -> None:
        """Le mode de recherche a changé dans le ModesPanel."""
        logger.debug("BotRecherche: mode changé → %s", mode)
        self._clear_results()
        self._status_label.setText("")

    def _on_client_ares_changed(self, username: str) -> None:
        """Un client Arès a été sélectionné dans le ModesPanel."""
        self._selected_client_username = username
        logger.debug("BotRecherche: client Arès sélectionné → %s", username)
        if username:
            self._modes_panel.status_console.push_info(f"🎯 Client ciblé : {username}")
        else:
            self._modes_panel.status_console.push_info("🌐 Recherche globale — tous les clients")

    def _on_clients_synchronises(self, clients: list) -> None:
        """La liste des clients a été mise à jour → rafraîchir le sélecteur + statut."""
        self._update_ares_clients()
        self._push_system_status()

    def _push_system_status(self) -> None:
        """Pousse l'état actuel du système dans la console d'information.

        Vérifie la connexion, les rooms, les clients actifs,
        et affiche un résumé clair pour l'utilisateur.
        """
        console = self._modes_panel.status_console

        # ── Connexion ──
        if self._connexion_manager is None:
            console.push_warning("🔌 En attente du gestionnaire de connexion…")
            return

        if not self._connexion_manager.is_connected:
            console.push_error("🔌 Non connecté à Soulseek — connectez-vous d'abord")
            return

        console.push_success(f"🔌 Connecté à Soulseek ({self._connexion_manager.username})")

        # ── Clients actifs ──
        if self._clients_actifs_service is None:
            console.push_warning("👥 Service clients actifs pas encore initialisé…")
            return

        actifs = self._clients_actifs_service.clients_actifs()
        valides = len(actifs)

        if valides == 0:
            console.push_warning("👥 Aucun client actif détecté — les rooms sont peut-être encore en cours de chargement")
        else:
            console.push_success(f"👥 {valides} client{'s' if valides > 1 else ''} actif{'s' if valides > 1 else ''} détecté{'s' if valides > 1 else ''}")
            client_count = 0
            if self._modes_panel._client_combo is not None:
                client_count = self._modes_panel._client_combo.count() - 1
            console.push_muted(f"   → {client_count} client(s) dans le sélecteur Arès")

    def _update_ares_clients(self) -> None:
        """Met à jour la liste des clients Arès dans le ModesPanel."""
        if self._clients_actifs_service is not None and hasattr(self, "_modes_panel"):
            clients = self._clients_actifs_service.clients_actifs()
            self._modes_panel.update_clients_ares(clients)
            logger.debug("BotRecherche: %d clients Arès envoyés au ModesPanel", len(clients))

    # ── Gestion des modes ────────────────────────────────────────

    def _update_connected_state(self) -> None:
        """Met à jour l'interface selon l'état de connexion."""
        connected = self._connexion_manager is not None and self._connexion_manager.is_connected
        if hasattr(self, "_modes_panel"):
            self._modes_panel.setEnabled(connected)

    # ── Recherche ───────────────────────────────────────────────

    def _on_search(self, query: str | None = None) -> None:
        """Lance une recherche sur Soulseek avec validation d'état préalable.

        Vérifie la connexion, la disponibilité des rooms et des clients
        avant de lancer la recherche. Chaque état est affiché dans la
        console d'information pour que l'utilisateur sache toujours
        où on en est.

        Paramètres
        ----------
        query : str | None
            Texte de recherche. Si None, lit depuis ModesPanel.
        """
        if query is None:
            query = self._modes_panel.query
        if not query or len(query) < 2:
            self._status_label.setText("📝 Minimum 2 caractères pour lancer une recherche")
            return

        console = self._modes_panel.status_console

        # ── Vérification 1 : Connexion ──
        if self._connexion_manager is None:
            console.push_error("🔌 Pas de gestionnaire de connexion — impossible de lancer la recherche")
            self._status_label.setText("❌ Gestionnaire de connexion non initialisé")
            return

        if not self._connexion_manager.is_connected:
            console.push_error(f"🔌 Non connecté à Soulseek — la recherche « {query} » ne peut pas être lancée")
            console.push_warning("💡 Connectez-vous d'abord via la page de connexion")
            self._status_label.setText("❌ Non connecté à Soulseek")
            return

        # ── Vérification 2 : Rooms chargées (si pas déjà fait) ──
        if self._clients_actifs_service is not None:
            actifs = self._clients_actifs_service.clients_actifs()
            if len(actifs) == 0:
                console.push_warning("⏳ Rooms en cours de chargement — aucun client actif pour l'instant")
                console.push_info("💡 La recherche sera lancée quand même, mais les résultats pourraient arriver plus tard")
                # On continue quand même, la recherche peut fonctionner sans clients Arès
            else:
                console.push_success(f"👥 {len(actifs)} client(s) actif(s) disponible(s) — recherche lancée")

        # ── Vérification 3 : Client ciblé existe-t-il ? ──
        if self._selected_client_username and self._clients_actifs_service is not None:
            client_info = self._clients_actifs_service.obtenir_client(self._selected_client_username)
            if client_info is None:
                console.push_warning(f"⚠️ Le client {self._selected_client_username} n'est plus dans la liste active")
                self._selected_client_username = None

        if self._search_timer is not None:
            self._search_timer.stop()

        self._clear_results()
        self._result_count = 0
        self._total_received = 0
        self._searching = True
        self._modes_panel.set_searching(True)

        if self._room_name:
            # Mode salon : recherche dans un salon spécifique
            console.push_info(f"🔍 Recherche de « {query} » dans #{self._room_name}…")
            self._connexion_manager.search_room(self._room_name, query)
            self._search_history.add(query, type_="room", username=self._room_name)
        elif self._browse_username:
            # Mode utilisateur : recherche chez un utilisateur spécifique
            console.push_info(f"🔍 Recherche de « {query} » chez {self._browse_username}…")
            self._connexion_manager.search_user(self._browse_username, query)
            self._search_history.add(query, type_="user", username=self._browse_username)
        elif self._selected_client_username and self._clients_actifs_service is not None:
            # Mode client ciblé : recherche chez le client Arès sélectionné
            console.push_info(f"🔍 Recherche de « {query} » chez {self._selected_client_username}…")
            self._connexion_manager.search_user(self._selected_client_username, query)
            self._search_history.add(query, type_="user", username=self._selected_client_username)
        else:
            # Mode global : dénichage par lots de clients actifs
            # (évite le broadcast réseau qui sature les connexions P2P)
            if self._clients_actifs_service is not None:
                actifs = self._clients_actifs_service.clients_actifs()
                if actifs:
                    usernames = [c.username for c in actifs]
                    nb = len(usernames)
                    lots = (nb - 1) // 5 + 1
                    console.push_info(
                        f"🔍 Dénichage de « {query} » chez {nb} client(s) "
                        f"actifs ({lots} lot(s) de 5)…"
                    )
                    self._connexion_manager.batched_search(query, usernames)
                else:
                    console.push_warning(
                        "⚠️ Aucun client actif disponible pour le dénichage"
                    )
                    console.push_info(
                        "💡 Attendez que les rooms soient chargées "
                        "(le service clients actifs détectera les pairs)"
                    )
                    self._status_label.setText(
                        "⏳ Aucun client actif — attendez le chargement des rooms"
                    )
                    self._reset_search_state()
                    return
            else:
                console.push_error(
                    "❌ Service clients actifs non disponible — dénichage impossible"
                )
                self._status_label.setText(
                    "❌ Service clients actifs non initialisé"
                )
                self._reset_search_state()
                return
            self._search_history.add(query, type_="global")

        self._rebuild_suggestions()
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._on_search_timeout)
        self._search_timer.start(30000)

        EventBus().emit_event(
            severity="INFO",
            category="recherche",
            title="Recherche lancée",
            message=f"Recherche de « {query} » démarrée",
            source="BotRecherche",
        )

    def _on_stop(self) -> None:
        """Arrête la recherche en cours et annule la requête réseau."""
        if self._connexion_manager is not None:
            self._connexion_manager.stop_search()
        self._reset_search_state()
        self._modes_panel.status_console.push_warning(f"⏹ Recherche arrêtée — {self._result_count} résultat(s) affiché(s)")
        self._status_label.setText(f"⏹ Recherche arrêtée — {self._result_count} résultat(s) affiché(s)")

        EventBus().emit_event(
            severity="INFO",
            category="recherche",
            title="Recherche arrêtée",
            message=f"Recherche arrêtée par l'utilisateur — {self._result_count} résultat(s)",
            source="BotRecherche",
        )

    @log_action("Basculer le filtre audio")
    def _on_audio_filter_toggled(self, checked: bool) -> None:
        """Bascule le filtre audio automatique mp3/flac/ogg."""
        self._audio_filter_enabled = checked
        self._audio_filter_btn.setText("🔊 Audio seulement" if checked else "🔊 Tous les fichiers")
        self._apply_filters()

    @log_action("Basculer le mode disponibilité")
    def _on_mode_dispo_toggled(self, checked: bool) -> None:
        """Bascule le mode disponibilité (slots libres uniquement)."""
        self._mode_dispo_enabled = checked
        self._mode_dispo_btn.setText("🟢 Mode dispo" if checked else "🔴 Mode dispo")
        self._apply_filters()

    def _on_search_result(self, evt: object) -> None:
        """Reçoit un lot de résultats de recherche."""
        from aioslsk.events import SearchResultEvent

        if not isinstance(evt, SearchResultEvent):
            return

        result = evt.result
        if not hasattr(result, "shared_items") or not result.shared_items:
            return

        query_text = ""
        try:
            query_text = evt.query.query
        except AttributeError:
            pass

        total_received = len(result.shared_items)
        if total_received > 0:
            logger.info(
                "_on_search_result: reçu %d fichiers (filtre audio=%s) pour « %s » de %s",
                total_received,
                self._audio_filter_enabled,
                query_text or "?",
                result.username,
            )

        self._table.setSortingEnabled(False)
        added = 0

        extensions_vues: set[str] = set()
        for file_data in result.shared_items:
            ext = _extraire_extension(file_data.filename)
            extensions_vues.add(ext if ext else "(sans ext)")

            if self._audio_filter_enabled and not _is_audio(ext):
                continue

            self._add_result_row(
                file_data=file_data,
                username=result.username,
                has_free_slots=result.has_free_slots,
                avg_speed=result.avg_speed,
            )
            added += 1

        if added == 0 and total_received > 0:
            logger.info(
                "_on_search_result: 0 ajouté sur %d reçus — extensions vues : %s",
                total_received,
                sorted(extensions_vues),
            )
            self._modes_panel.status_console.push_warning(
                f"⚠️ {total_received} résultat(s) reçu(s) mais tous filtrés "
                f"(extensions : {', '.join(sorted(extensions_vues)[:8])})"
            )

        # Incrémenter le compteur total reçu (filtrés ou pas)
        self._total_received += total_received

        self._table.setSortingEnabled(True)

        if added > 0:
            self._result_count += added

            self._push_result_counter()

            if self._result_count >= MAX_RESULTS:
                if self._room_name:
                    status = f"⚠️ {MAX_RESULTS} résultats max dans #{self._room_name} — affinez votre recherche"
                elif self._browse_username:
                    status = f"⚠️ {MAX_RESULTS} résultats max chez {self._browse_username} — affinez votre recherche"
                else:
                    status = f"⚠️ {MAX_RESULTS} résultats max — affinez votre recherche"
            else:
                status = f"✅ {self._result_count} résultat{'s' if self._result_count > 1 else ''}"
                if query_text:
                    if self._room_name:
                        status += f" — recherche « {query_text} » dans #{self._room_name}"
                    elif self._browse_username:
                        status += f" — recherche « {query_text} » chez {self._browse_username}"
                    else:
                        status += f" — recherche « {query_text} »"
            self._status_label.setText(status)

            # Premiers résultats → notification console
            if self._result_count <= added:
                source = self._room_name or self._browse_username or self._selected_client_username or ""
                if source:
                    self._modes_panel.status_console.push_success(f"📥 {added} résultat(s) reçu(s) de {source}")
                else:
                    self._modes_panel.status_console.push_success(f"📥 {added} résultat(s) reçu(s)")

        # Mettre à jour le compteur dans l'historique
        if query_text and self._result_count > 0:
            if self._room_name:
                self._search_history.update_count(
                    query_text,
                    type_="room",
                    username=self._room_name,
                    count=self._result_count,
                )
            elif self._browse_username:
                self._search_history.update_count(
                    query_text,
                    type_="user",
                    username=self._browse_username,
                    count=self._result_count,
                )
            else:
                self._search_history.update_count(
                    query_text,
                    type_="global",
                    count=self._result_count,
                )

        if self._searching:
            self._searching = False
            self._modes_panel.set_searching(False)
            self._push_result_counter()
            self._modes_panel.status_console.push_success("✅ Recherche terminée — tous les résultats reçus")
            # Appliquer les filtres sur les nouveaux résultats
            if self._mode_dispo_enabled or any(v for v in self._filter_state.values()):
                self._apply_filters()

    def _on_search_error(self, msg: str) -> None:
        if self._searching:
            self._reset_search_state()
            self._modes_panel.status_console.push_error(f"❌ Erreur : {msg}")
            self._status_label.setText(f"❌ Erreur : {msg}")
            EventBus().emit_event(
                severity="ERROR",
                category="recherche",
                title="Erreur de recherche",
                message=f"Erreur lors de la recherche : {msg}",
                source="BotRecherche",
            )

    def _on_search_timeout(self) -> None:
        if self._searching:
            self._searching = False
            self._modes_panel.set_searching(False)
            self._modes_panel.status_console.push_warning("⏱️ 30s écoulées — la recherche continue en arrière-plan")
            self._modes_panel.status_console.push_info("💡 Les résultats arrivent au fur et à mesure, le tableau se remplit automatiquement")
            self._status_label.setText("⏱️ La recherche continue en arrière-plan…")

    # ── Filtres avancés ─────────────────────────────────────────

    @log_action("Ouvrir les filtres avancés")
    def _open_filtres_modal(self) -> None:
        """Ouvre la modal de filtres avancés."""
        modal = FiltresRechercheModal(
            filter_state=self._filter_state,
            parent=self,
        )
        # pyrefly: ignore [missing-attribute]
        if modal.exec() == QDialog.Accepted:
            self._filter_state = dict(modal.result_state)
            self._apply_filters()

    def _on_connected(self, username: str) -> None:
        self._update_connected_state()
        self._push_system_status()

    def _on_disconnected(self) -> None:
        self._reset_search_state()
        self._update_connected_state()
        self._modes_panel.status_console.push_error("🔌 Déconnecté de Soulseek")

    def _update_filtres_badge(self) -> None:
        """Met à jour le badge du nombre de filtres actifs."""
        count = 0
        if self._filter_state["bitrate_min"] > 0:
            count += 1
        if self._filter_state["duration_min"] > 0:
            count += 1
        if self._filter_state["duration_max"] > 0:
            count += 1
        if self._filter_state["size_min"] > 0:
            count += 1
        if self._filter_state["size_max"] > 0:
            count += 1
        if self._filter_state["username"]:
            count += 1
        if self._filter_state["slots_libres_only"]:
            count += 1

        self._filtres_compte = count
        if count > 0:
            # pyrefly: ignore [missing-attribute]
            self._filtres_badge.setText(f" {count} ")
            # pyrefly: ignore [missing-attribute]
            self._filtres_badge.setVisible(True)
        else:
            # pyrefly: ignore [missing-attribute]
            self._filtres_badge.setVisible(False)

    def _row_matches_filters(self, data: dict) -> bool:
        """Vérifie si une ligne correspond aux filtres actifs."""
        fs = self._filter_state

        # Bitrate min
        if fs["bitrate_min"] > 0 and data["bitrate"] < fs["bitrate_min"]:
            return False

        # Durée min
        if fs["duration_min"] > 0 and data["duration"] < fs["duration_min"]:
            return False

        # Durée max
        if fs["duration_max"] > 0 and data["duration"] > fs["duration_max"]:
            return False

        # Taille min (en Mo)
        if fs["size_min"] > 0 and (data["filesize"] / 1_000_000) < fs["size_min"]:
            return False

        # Taille max (en Mo)
        if fs["size_max"] > 0 and (data["filesize"] / 1_000_000) > fs["size_max"]:
            return False

        # Utilisateur
        if fs["username"] and fs["username"].lower() not in data["username"].lower():
            return False

        # Slots libres uniquement
        if fs["slots_libres_only"] and not data["has_free_slots"]:
            return False

        return True

    def _apply_filters(self) -> None:
        """Applique les filtres masquant/affichent les lignes du tableau.

        Les filtres s'appliquent en masquant les lignes qui ne
        correspondent pas (via setRowHidden). Les données brutes
        sont stockées dans Qt.UserRole+1 sur la colonne Fichier.
        """
        self._update_filtres_badge()

        has_filters = self._filtres_compte > 0 or not self._audio_filter_enabled or self._mode_dispo_enabled

        if not has_filters:
            # Aucun filtre : tout afficher
            for row in range(self._table.rowCount()):
                self._table.setRowHidden(row, False)
            return

        visible_count = 0
        for row in range(self._table.rowCount()):
            item = self._table.item(row, COL_FICHIER)
            if item is None:
                self._table.setRowHidden(row, True)
                continue

            # pyrefly: ignore [missing-attribute]
            data = item.data(Qt.UserRole + 1)
            if data is None:
                self._table.setRowHidden(row, True)
                continue

            matches = True

            # Filtre audio (si désactivé, toutes les extensions passent)
            if self._audio_filter_enabled:
                if not _is_audio(data.get("extension", "")):
                    matches = False

            # Mode dispo : uniquement les slots libres
            if matches and self._mode_dispo_enabled:
                if not data.get("has_free_slots", False):
                    matches = False

            # Filtres avancés
            if matches:
                matches = self._row_matches_filters(data)

            self._table.setRowHidden(row, not matches)
            if matches:
                visible_count += 1

        # Pousser le compteur mis à jour après filtrage
        self._result_count = visible_count
        self._push_result_counter()

        # Mettre à jour le statut pour refléter le filtrage
        total = self._table.rowCount()
        if total > 0:
            if visible_count < total:
                extra = []
                if self._mode_dispo_enabled:
                    extra.append("🟢 dispo")
                if self._filtres_compte > 0:
                    extra.append(f"{self._filtres_compte} filtre{'s' if self._filtres_compte > 1 else ''}")
                suffix = f" — {' + '.join(extra)}" if extra else ""
                self._status_label.setText(f"✅ {visible_count}/{total} résultat{'s' if total > 1 else ''}{suffix}")
            else:
                extra = []
                if self._mode_dispo_enabled:
                    extra.append("🟢 dispo")
                if self._filtres_compte > 0:
                    extra.append(f"{self._filtres_compte} filtre{'s' if self._filtres_compte > 1 else ''}")
                suffix = f" — {' + '.join(extra)}" if extra else ""
                self._status_label.setText(f"✅ {total} résultat{'s' if total > 1 else ''}{suffix}")

    # ── Menu contextuel ──────────────────────────────────────────

    def _get_row_data(self, row: int) -> dict | None:
        """Extrait les données brutes d'une ligne du tableau."""
        item = self._table.item(row, COL_FICHIER)
        if item is None:
            return None
        # pyrefly: ignore [missing-attribute]
        return item.data(Qt.UserRole + 1)

    def _on_context_menu(self, pos) -> None:
        """Affiche le menu contextuel pour une ligne du tableau."""
        row = self._table.rowAt(int(pos.y()))
        if row < 0:
            return

        data = self._get_row_data(row)
        if data is None:
            return

        filename = data.get("filename", "Inconnu")
        username = data.get("username", "Inconnu")

        menu = QMenu(self)
        menu.setStyleSheet(
            f"""
            QMenu {{
                background: {COLORS["BG_SURFACE"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                color: {COLORS["TEXT_PRIMARY"]};
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
            }}
            QMenu::item:selected {{
                background: rgba(COLORS['PRIMARY'], '30');
                color: {COLORS["PRIMARY"]};
            }}
            QMenu::separator {{
                height: 1px;
                background: {COLORS["BORDER"]};
                margin: 4px 8px;
            }}
            """
        )

        # ── ⬇ Télécharger ──
        dl_action = QAction(f"⬇ Télécharger « {filename} »", self)
        dl_action.triggered.connect(lambda: self.page_changed.emit("Téléchargement"))
        menu.addAction(dl_action)

        # ── 👤 Voir les fichiers de l'utilisateur ──
        browse_action = QAction(f"👤 Voir les fichiers de {username}", self)
        browse_action.triggered.connect(lambda: self._on_browse_user(username))
        menu.addAction(browse_action)

        menu.addSeparator()

        # ── 📋 Copier le nom du fichier ──
        copy_action = QAction("📋 Copier le nom du fichier", self)
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(filename))
        menu.addAction(copy_action)

        # ── 🚫 Bloquer l'utilisateur ──
        block_action = QAction(f"🚫 Bloquer {username}", self)
        block_action.triggered.connect(lambda: self._on_block_user(username))
        menu.addAction(block_action)

        # Afficher le menu à la position globale
        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _enter_browse_mode(self, username: str) -> None:
        """Entre en mode navigation utilisateur."""
        # Quitter le mode salon si actif
        if self._room_name:
            self._exit_room_mode()
        self._browse_username = username
        self._browse_label.setText(f"Fichiers de {username}")
        self._browse_banner.setVisible(True)
        self._modes_panel.focus_search()

    @log_action("Quitter le mode navigation utilisateur")
    def _exit_browse_mode(self) -> None:
        """Quitte le mode navigation utilisateur."""
        self._browse_username = None
        self._browse_banner.setVisible(False)
        self._reset_search_state()
        self._clear_results()
        self._status_label.setText("")

    def _enter_room_mode(self, room: str) -> None:
        """Entre en mode recherche dans un salon."""
        # Quitter le mode utilisateur si actif
        if self._browse_username:
            self._exit_browse_mode()
        self._room_name = room
        self._room_label.setText(f"Salon : #{room}")
        self._room_banner.setVisible(True)
        self._modes_panel.focus_search()

    @log_action("Quitter le mode recherche salon")
    def _exit_room_mode(self) -> None:
        """Quitte le mode recherche dans un salon."""
        self._room_name = None
        self._room_banner.setVisible(False)
        self._reset_search_state()
        self._clear_results()
        self._status_label.setText("")

    @log_action("Parcourir les fichiers d'un utilisateur")
    def _on_browse_user(self, username: str) -> None:
        """Lance une recherche des fichiers d'un utilisateur."""
        query = self._modes_panel.query
        if not query:
            self._status_label.setText("📝 Entrez un terme de recherche avant de parcourir un utilisateur")
            return
        if self._connexion_manager is None:
            return

        # Stopper le timer de recherche précédent si actif
        if self._search_timer is not None:
            self._search_timer.stop()

        self._enter_browse_mode(username)
        self._clear_results()
        self._result_count = 0
        self._searching = True
        self._modes_panel.set_searching(True)
        self._status_label.setText(f"🔍 Recherche de « {query} » chez {username}…")
        self._connexion_manager.search_user(username, query)

    @log_action("Bloquer un utilisateur")
    def _on_block_user(self, username: str) -> None:
        """Ajoute un utilisateur à la liste noire."""
        if self._connexion_manager is not None:
            self._connexion_manager.block_user(username)
        self._status_label.setText(f"🚫 Utilisateur {username} bloqué")

    # ── Basculement table / arbre ────────────────────────────────

    @log_action("Basculer la vue table/arbre")
    def _toggle_view(self, checked: bool) -> None:
        """Bascule entre la vue tableau (plate) et la vue arbre (dossiers).

        Paramètres
        ----------
        checked : bool
            True → vue arbre, False → vue tableau.
        """
        self._folder_view = checked
        self._view_toggle_btn.setText("📋 Vue fichiers" if checked else "📁 Vue dossiers")

        if checked:
            # Basculer vers la vue arbre
            self._view_stack.setCurrentIndex(1)
            self._rebuild_tree_view()
            self._modes_panel.status_console.push_info("📁 Passage en vue dossiers — résultats groupés par répertoire")
        else:
            # Basculer vers la vue tableau
            self._view_stack.setCurrentIndex(0)
            self._rebuild_table_view()
            self._modes_panel.status_console.push_info("📋 Passage en vue fichiers — résultats plats")

    def _rebuild_tree_view(self) -> None:
        """Reconstruit la vue arbre à partir du cache de résultats."""
        self._dossier_tree.build_from_cache(self._result_data)

        total = len(self._result_data)
        if total > 0:
            self._status_label.setText(f"✅ {total} résultat{'s' if total > 1 else ''} — Vue dossiers")
        else:
            self._status_label.setText("")

    def _rebuild_table_view(self) -> None:
        """Reconstruit la vue tableau à partir du cache de résultats.

        Vide le tableau et le re-remplit depuis le cache pour
        assurer la cohérence après un basculement.
        """
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        self._table.setSortingEnabled(True)

        if not self._result_data:
            return

        # Re-peupler le tableau depuis le cache
        # Note : on perd les widgets DL (boutons) car QTableWidget
        # ne les sérialise pas — ce n'est pas grave car ils sont
        # désactivés de toute façon.
        self._table.setSortingEnabled(False)
        for data in self._result_data:
            # On ne peut pas reconstruire exactement les mêmes widgets,
            # donc on réutilise _add_result_row... mais ça re-ajouterait
            # au cache. On le fait directement ici.
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setRowHeight(row, 36)

            ext = data.get("extension", "").upper()
            filename = data.get("filename", "?")
            filesize = data.get("filesize", 0)
            bitrate = data.get("bitrate", 0)
            duration = data.get("duration", 0)
            username = data.get("username", "")
            has_free_slots = data.get("has_free_slots", False)
            avg_speed = data.get("avg_speed", 0)

            # Extension
            ext_text = f"[{ext}]" if ext else "[?]"
            ext_item = TableItem(ext_text)
            ext_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, COL_EXTENSION, ext_item)

            # Fichier
            fichier_item = TableItem(filename, filename.lower())
            fichier_item.setData(Qt.UserRole + 1, data)
            self._table.setItem(row, COL_FICHIER, fichier_item)

            # Taille
            size_str = _format_size(filesize)
            size_item = TableItem(size_str, filesize)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, COL_TAILLE, size_item)

            # Bitrate
            bitrate_str = _format_bitrate(bitrate)
            bitrate_item = TableItem(bitrate_str, bitrate)
            bitrate_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, COL_BITRATE, bitrate_item)

            # Durée
            duree_str = _format_duration(duration) if duration > 0 else "—"
            duree_item = TableItem(duree_str, duration)
            duree_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, COL_DUREE, duree_item)

            # Utilisateur
            user_item = TableItem(username, username.lower())
            user_item.setToolTip(f"👤 {username}")
            self._table.setItem(row, COL_UTILISATEUR, user_item)

            # Slots
            slots_text = "🟢" if has_free_slots else "🔴"
            slots_item = TableItem(slots_text)
            slots_item.setToolTip("Slots libres" if has_free_slots else "File d'attente")
            slots_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, COL_SLOTS, slots_item)

            # Vitesse
            speed_str = _format_speed(avg_speed) if avg_speed > 0 else "—"
            speed_item = TableItem(speed_str, avg_speed)
            speed_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, COL_VITESSE, speed_item)

        self._table.setSortingEnabled(True)

        # Appliquer les filtres si actifs
        if self._mode_dispo_enabled or self._filtres_compte > 0:
            self._apply_filters()

    # ── Menu contextuel de l'arbre ───────────────────────────────

    def _on_tree_context_menu(self, pos) -> None:
        """Affiche le menu contextuel pour un élément de l'arbre."""
        item = self._dossier_tree.itemAt(pos)
        if item is None:
            return

        # Récupérer les données stockées
        item_data = item.data(DossierTreeWidget.COL_NOM, Qt.UserRole)
        if item_data is None:
            return

        data = item_data.get("data")
        if data is None:
            return

        filename = data.get("filename", "Inconnu")
        username = data.get("username", "Inconnu")

        menu = QMenu(self)
        menu.setStyleSheet(
            f"""
            QMenu {{
                background: {COLORS["BG_SURFACE"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                color: {COLORS["TEXT_PRIMARY"]};
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
            }}
            QMenu::item:selected {{
                background: rgba(COLORS['PRIMARY'], '30');
                color: {COLORS["PRIMARY"]};
            }}
            QMenu::separator {{
                height: 1px;
                background: {COLORS["BORDER"]};
                margin: 4px 8px;
            }}
            """
        )

        dl_action = QAction(f"⬇ Télécharger « {filename} »", self)
        dl_action.triggered.connect(lambda: self.page_changed.emit("Téléchargement"))
        menu.addAction(dl_action)

        browse_action = QAction(f"👤 Voir les fichiers de {username}", self)
        browse_action.triggered.connect(lambda: self._on_browse_user(username))
        menu.addAction(browse_action)

        menu.addSeparator()

        copy_action = QAction("📋 Copier le nom du fichier", self)
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(filename))
        menu.addAction(copy_action)

        block_action = QAction(f"🚫 Bloquer {username}", self)
        block_action.triggered.connect(lambda: self._on_block_user(username))
        menu.addAction(block_action)

        menu.exec(self._dossier_tree.viewport().mapToGlobal(pos))

    # ── Gestion du tableau ──────────────────────────────────────

    def _add_result_row(
        self,
        file_data: object,
        username: str,
        has_free_slots: bool,
        avg_speed: int,
    ) -> None:
        """Ajoute une ligne de résultat au tableau.

        Si le nombre total de lignes dépasse ``MAX_RESULTS``,
        la ligne la plus ancienne est retirée (FIFO).
        """
        row = self._table.rowCount()

        if row >= MAX_RESULTS:
            self._table.removeRow(0)
            row = self._table.rowCount()

        self._table.insertRow(row)
        self._table.setRowHeight(row, 36)

        # pyrefly: ignore [missing-attribute]
        bitrate = _get_attr(file_data.attributes, _ATTR_BITRATE) or 0
        # pyrefly: ignore [missing-attribute]
        duration = _get_attr(file_data.attributes, _ATTR_DURATION) or 0
        # pyrefly: ignore [missing-attribute]
        filename = file_data.filename.split("\\")[-1].split("/")[-1]
        # pyrefly: ignore [missing-attribute]
        # Extraire l'extension depuis le filename (fiable) plutôt que file_data.extension (métadonnées souvent vides)
        ext = _extraire_extension(file_data.filename).upper()

        # Données brutes pour le re-filtrage + vue dossiers
        # pyrefly: ignore [missing-attribute]
        full_path = file_data.filename
        row_data = {
            # pyrefly: ignore [missing-attribute]
            "extension": _extraire_extension(file_data.filename),
            "filename": filename,
            "full_path": full_path,
            # pyrefly: ignore [missing-attribute]
            "filesize": file_data.filesize,
            "bitrate": bitrate,
            "duration": duration,
            "username": username,
            "has_free_slots": has_free_slots,
            "avg_speed": avg_speed,
        }

        # ── Colonne 0 : Extension ──
        ext_text = f"[{ext}]" if ext else "[?]"
        ext_item = TableItem(ext_text)
        ext_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, COL_EXTENSION, ext_item)

        # ── Colonne 1 : Fichier (stocke les données brutes pour filtrage) ──
        fichier_item = TableItem(filename, filename.lower())
        # pyrefly: ignore [missing-attribute]
        fichier_item.setToolTip(file_data.filename)
        # pyrefly: ignore [missing-attribute]
        fichier_item.setData(Qt.UserRole + 1, row_data)
        self._table.setItem(row, COL_FICHIER, fichier_item)

        # ── Colonne 2 : Taille ──
        # pyrefly: ignore [missing-attribute]
        size_str = _format_size(file_data.filesize)
        # pyrefly: ignore [missing-attribute]
        size_item = TableItem(size_str, file_data.filesize)
        size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._table.setItem(row, COL_TAILLE, size_item)

        # ── Colonne 3 : Bitrate ──
        bitrate_str = _format_bitrate(bitrate)
        bitrate_item = TableItem(bitrate_str, bitrate)
        bitrate_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, COL_BITRATE, bitrate_item)

        # ── Colonne 4 : Durée ──
        duree_str = _format_duration(duration) if duration > 0 else "—"
        duree_item = TableItem(duree_str, duration)
        duree_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, COL_DUREE, duree_item)

        # ── Colonne 5 : Utilisateur ──
        user_item = TableItem(username, username.lower())
        user_item.setToolTip(f"👤 {username}")
        self._table.setItem(row, COL_UTILISATEUR, user_item)

        # ── Colonne 6 : Slots ──
        slots_text = "🟢" if has_free_slots else "🔴"
        slots_item = TableItem(slots_text)
        slots_item.setToolTip("Slots libres" if has_free_slots else "File d'attente")
        slots_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, COL_SLOTS, slots_item)

        # ── Colonne 7 : Vitesse ──
        speed_str = _format_speed(avg_speed) if avg_speed > 0 else "—"
        speed_item = TableItem(speed_str, avg_speed)
        speed_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._table.setItem(row, COL_VITESSE, speed_item)

        # ── Colonne 8 : DL (bouton) ──
        dl_btn = QPushButton("⬇")
        dl_btn.setFixedSize(28, 28)
        dl_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {COLORS["PRIMARY"]};
                color: {COLORS["TEXT_WHITE"]};
                border: none;
                border-radius: 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {COLORS["PRIMARY_HOVER"]};
            }}
            QPushButton:disabled {{
                background: {COLORS["BG_BTN_DISABLED"]};
                color: {COLORS["TEXT_DISABLED"]};
            }}
            """
        )
        dl_btn.setToolTip(f"Télécharger « {filename} »")
        dl_btn.setEnabled(False)
        self._table.setCellWidget(row, COL_DL, dl_btn)

        # Mettre en cache pour reconstruction de la vue dossiers
        self._result_data.append(row_data)
        if len(self._result_data) > MAX_RESULTS:
            self._result_data.pop(0)

    # ── Compteur console ────────────────────────────────────────

    def _push_result_counter(self) -> None:
        """Pousse le compteur résultats affichés/reçus dans la console de suivi."""
        if self._total_received == 0:
            return
        console = self._modes_panel.status_console
        console.push_muted(
            f"📊 {self._result_count} résultat(s) affiché(s) sur {self._total_received} reçu(s)"
        )

    # ── Nettoyage ───────────────────────────────────────────────

    def _reset_search_state(self) -> None:
        self._searching = False
        if hasattr(self, "_modes_panel"):
            self._modes_panel.set_searching(False)
        if self._search_timer is not None:
            self._search_timer.stop()

    def _clear_results(self) -> None:
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        self._table.setSortingEnabled(True)
        self._dossier_tree.clear()
        self._result_data.clear()
        self._total_received = 0

    # ── Historique des recherches ──────────────────────────────

    def _rebuild_suggestions(self) -> None:
        """Met à jour les suggestions rapides sous la barre de recherche.

        Affiche les 5 dernières recherches sous forme de boutons
        cliquables + le bouton ``📜 Historique``.
        """
        # Nettoyer les widgets existants
        for widget in self._suggestions_widgets:
            # pyrefly: ignore [missing-attribute]
            self._suggestions_row.layout().removeWidget(widget)
            widget.deleteLater()
        self._suggestions_widgets.clear()

        recent = self._search_history.get_recent()
        for entry in recent:
            q = entry["query"]
            label = q[:28] + "…" if len(q) > 28 else q
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: {COLORS["BG_SURFACE"]};
                    color: {COLORS["TEXT_SECONDARY"]};
                    border: 1px solid {COLORS["BORDER"]};
                    border-radius: 10px;
                    padding: 3px 10px;
                    font-size: 10px;
                }}
                QPushButton:hover {{
                    background: rgba(COLORS['PRIMARY'], '20');
                    border-color: {COLORS["PRIMARY"]};
                    color: {COLORS["PRIMARY"]};
                }}
                """
            )
            btn.clicked.connect(lambda checked, e=entry: self._on_suggestion_clicked(e))
            # pyrefly: ignore [missing-attribute]
            self._suggestions_row.layout().addWidget(btn)
            self._suggestions_widgets.append(btn)

        # Bouton Historique complet (toujours visible)
        # pyrefly: ignore [missing-attribute]
        self._suggestions_row.layout().addWidget(self._history_btn)

        # Ajouter un stretch pour pousser à gauche
        # pyrefly: ignore [missing-attribute]
        self._suggestions_row.layout().addStretch(1)
        self._suggestions_row.setVisible(bool(recent))

    @log_action("Cliquer sur une suggestion de recherche")
    def _on_suggestion_clicked(self, entry: dict) -> None:
        """Clique sur une suggestion d'historique : lance la recherche."""
        query = entry["query"]
        type_ = entry.get("type", "global")
        username = entry.get("username")

        # Configurer le mode approprié
        if type_ == "room" and username:
            self._enter_room_mode(username)
        elif type_ == "user" and username:
            self._enter_browse_mode(username)
        else:
            # Quitter les modes spéciaux si on était dedans
            if self._room_name:
                self._exit_room_mode()
            if self._browse_username:
                self._exit_browse_mode()

        # Remplir le champ de recherche via le panneau et lancer
        self._modes_panel.set_query(query)
        self._on_search()

    @log_action("Ouvrir l'historique des recherches")
    def _open_history_popup(self) -> None:
        """Ouvre la popup d'historique complet."""
        dialog = HistoryPopup(
            self._search_history.get_all(),
            self,
            history=self._search_history,
        )
        dialog.clear_requested.connect(self._on_history_clear)
        dialog.entries_changed.connect(self._rebuild_suggestions)
        if dialog.exec():
            selected = dialog.selected_entry
            if selected:
                self._on_suggestion_clicked(selected)

    @log_action("Vider tout l'historique")
    def _on_history_clear(self) -> None:
        """Vide tout l'historique et rafraîchit les suggestions."""
        self._search_history.clear()
        self._rebuild_suggestions()
        self._status_label.setText("🗑 Historique effacé")
