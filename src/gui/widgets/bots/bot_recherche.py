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
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
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
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.theme_fragments.colors import COLORS, rgba
from src.services.search_history import SearchHistory

if TYPE_CHECKING:
    from src.services.connexion_manager import ConnexionManager

logger = logging.getLogger(__name__)

# ── Constantes ─────────────────────────────────────────────────

EXTENSIONS_AUDIO = {".mp3", ".flac", ".ogg"}
"""Extensions autorisées (filtre automatique à la réception)."""

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
    "Extension", "Fichier", "Taille", "Bitrate", "Durée",
    "Utilisateur", "Slots", "Vitesse", "DL",
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
            self.setData(Qt.UserRole, sort_value)

    def __lt__(self, other: QTableWidgetItem) -> bool:
        my_val = self.data(Qt.UserRole)
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
                background: {COLORS['BG_SURFACE']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 8px;
            }}
            QLabel {{
                color: {COLORS['TEXT_PRIMARY']};
                font-size: 12px;
            }}
            QGroupBox {{
                color: {COLORS['TEXT_PRIMARY']};
                font-weight: 600;
                font-size: 12px;
                border: 1px solid {COLORS['BORDER']};
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
                background: {COLORS.get('BG_INPUT', '#1a1a2a')};
                color: {COLORS['TEXT_PRIMARY']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 4px;
                padding: 4px 6px;
            }}
            QSpinBox:focus {{
                border-color: {COLORS['PRIMARY']};
            }}
            QCheckBox {{
                color: {COLORS['TEXT_PRIMARY']};
                spacing: 8px;
            }}
            QSlider::groove:horizontal {{
                border: 1px solid {COLORS['BORDER']};
                height: 6px;
                background: {COLORS.get('BG_INPUT', '#1a1a2a')};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {COLORS['PRIMARY']};
                border: none;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {COLORS['PRIMARY_HOVER']};
            }}
            QLineEdit {{
                background: {COLORS.get('BG_INPUT', '#1a1a2a')};
                color: {COLORS['TEXT_PRIMARY']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['PRIMARY']};
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        # ── Titre ──
        header = QLabel("🔍 Filtres avancés")
        header.setStyleSheet(
            f"color: {COLORS['PRIMARY']}; font-size: 16px; font-weight: 700;"
        )
        layout.addWidget(header)

        # ── Groupe : Qualité ──
        qualite = QGroupBox("Qualité")
        qualite_layout = QFormLayout(qualite)
        qualite_layout.setSpacing(8)
        qualite_layout.setContentsMargins(10, 16, 10, 10)

        # Bitrate min : Slider + SpinBox côte à côte
        bitrate_row = QHBoxLayout()
        self._bitrate_slider = QSlider(Qt.Horizontal)
        self._bitrate_slider.setRange(0, 1000)
        self._bitrate_slider.setTickInterval(128)
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
        buttons = QDialogButtonBox(
            QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        buttons.accepted.connect(self._on_apply)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Apply).setStyleSheet(
            f"""
            QPushButton {{
                background: {COLORS['PRIMARY']};
                color: {COLORS['TEXT_WHITE']};
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {COLORS['PRIMARY_HOVER']};
            }}
            """
        )
        buttons.button(QDialogButtonBox.Cancel).setStyleSheet(
            f"""
            QPushButton {{
                background: {COLORS['BG_SURFACE2']};
                color: {COLORS['TEXT_PRIMARY']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 6px;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background: {COLORS['BG_HOVER']};
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
        self._slots_check.setChecked(
            self.result_state.get("slots_libres_only", False)
        )

    def _save_state(self) -> None:
        """Sauvegarde les valeurs des contrôles dans result_state."""
        self.result_state["bitrate_min"] = self._bitrate_spin.value()
        self.result_state["duration_min"] = self._duration_min.value()
        self.result_state["duration_max"] = self._duration_max.value()
        self.result_state["size_min"] = self._size_min.value()
        self.result_state["size_max"] = self._size_max.value()
        self.result_state["username"] = self._username_input.text().strip()
        self.result_state["slots_libres_only"] = self._slots_check.isChecked()

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
        self._title_label.setStyleSheet(
            f"color: {COLORS['PRIMARY']}; font-size: 16px; font-weight: 700;"
        )
        layout.addWidget(self._title_label)

        if not entries:
            empty = QLabel("Aucune recherche pour l'instant.")
            empty.setStyleSheet(
                f"color: {COLORS['TEXT_SECONDARY']}; font-size: 13px; "
                f"padding: 20px;"
            )
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(empty, 1)
            self._close_btn(layout)
            return

        # Liste défilable
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(
            f"background: transparent; border: none;"
        )

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
                    background: {COLORS['BG_SURFACE']};
                    color: {COLORS['TEXT_PRIMARY']};
                    border: 1px solid {COLORS['BORDER']};
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 12px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background: rgba(COLORS['PRIMARY'], '15');
                    border-color: {COLORS['PRIMARY']};
                }}
                """
            )

            if count > 0:
                btn.setText(
                    btn.text() + f"  —  {count} résultat{'s' if count > 1 else ''}"
                )

            if ts:
                date_part = ts[:10] if "T" in ts else ts
                btn.setText(btn.text() + f"  ({date_part})")

            btn.clicked.connect(
                lambda checked, e=entry: self._on_select(e)
            )
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
                    color: #999;
                    border: 1px solid transparent;
                    border-radius: 14px;
                    font-size: 11px;
                    font-weight: 700;
                    padding: 0;
                }}
                QPushButton:hover {{
                    color: {COLORS['DANGER_BTN']};
                    background: {COLORS['DANGER_BG_HOVER']};
                    border-color: {COLORS['DANGER_BTN']};
                }}
                """
            )
            x_btn.clicked.connect(
                lambda checked, e=entry: self._on_remove_entry(e)
            )
            row_layout.addWidget(x_btn)

            self._list_layout.addWidget(row)

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
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Mettre à jour le titre
        if self._title_label:
            self._title_label.setText(
                f"📜 Historique ({len(self._entries)} recherche(s))"
            )

        if not self._entries:
            empty = QLabel("Aucune recherche pour l'instant.")
            empty.setStyleSheet(
                f"color: {COLORS['TEXT_SECONDARY']}; font-size: 13px; "
                f"padding: 20px;"
            )
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list_layout.addWidget(empty)
            self._list_layout.addStretch(1)
            return

        self._build_entry_rows(self._entries)
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
                color: {COLORS['DANGER_BTN']};
                border: 1px solid {COLORS['DANGER_BTN']};
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            #clearHistoryBtn:hover {{
                background: {COLORS['DANGER_BG_HOVER']};
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
                background: {COLORS['PRIMARY']};
                color: {COLORS['TEXT_WHITE']};
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {COLORS['PRIMARY_HOVER']};
            }}
            """
        )
        btn.clicked.connect(self.reject)

        row.addWidget(btn)
        layout.addLayout(row)

    def _on_select(self, entry: dict) -> None:
        self.selected_entry = entry
        self.accept()

    def _on_clear(self) -> None:
        """Émet le signal pour vider l'historique et ferme la popup."""
        self.clear_requested.emit()
        self.accept()


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
        self.setFrameShape(QFrame.NoFrame)

        self._connexion_manager = connexion_manager
        self._searching = False
        self._search_timer: QTimer | None = None
        self._result_count = 0
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

        self._setup_ui()
        self._update_connected_state()

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
        title.setStyleSheet(
            f"color: {COLORS['PRIMARY']}; font-size: 18px; font-weight: 700;"
        )
        title_row.addWidget(title)

        # Badge de filtres actifs (caché si aucun filtre)
        self._filtres_badge = QLabel("")
        self._filtres_badge.setStyleSheet(
            f"""
            color: {COLORS['WARNING']};
            background: rgba(COLORS['WARNING'], '20');
            border: 1px solid {COLORS['WARNING']};
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
                color: {COLORS['TEXT_SECONDARY']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 6px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            #filtresBtn:hover {{
                border-color: {COLORS['PRIMARY']};
                color: {COLORS['PRIMARY']};
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
                color: {COLORS['PRIMARY']};
                border: 1px solid {COLORS['PRIMARY']};
                border-radius: 6px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            #audioFilterBtn:checked {{
                background: rgba(COLORS['PRIMARY'], '20');
                border-color: {COLORS['PRIMARY']};
                color: {COLORS['PRIMARY']};
            }}
            #audioFilterBtn:!checked {{
                background: transparent;
                border-color: {COLORS['BORDER']};
                color: {COLORS['TEXT_SECONDARY']};
            }}
            #audioFilterBtn:hover {{
                border-color: {COLORS['PRIMARY']};
                color: {COLORS['PRIMARY']};
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
                color: {COLORS['TEXT_SECONDARY']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 6px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            #modeDispoBtn:checked {{
                background: rgba(COLORS['SUCCESS'], '30');
                border-color: {COLORS['SUCCESS']};
                color: {COLORS['SUCCESS']};
            }}
            #modeDispoBtn:hover {{
                border-color: {COLORS['SUCCESS']};
                color: {COLORS['SUCCESS']};
            }}
            """
        )
        self._mode_dispo_btn.toggled.connect(self._on_mode_dispo_toggled)
        title_row.addWidget(self._mode_dispo_btn)

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
        self._browse_icon.setStyleSheet(
            f"font-size: 14px; background: transparent; border: none;"
        )
        banner_layout.addWidget(self._browse_icon)

        self._browse_label = QLabel("")
        self._browse_label.setStyleSheet(
            f"color: {COLORS['PRIMARY']}; font-size: 13px; font-weight: 600; "
            f"background: transparent; border: none;"
        )
        banner_layout.addWidget(self._browse_label, 1)

        self._browse_back_btn = QPushButton("← Retour à la recherche globale")
        self._browse_back_btn.setObjectName("browseBackBtn")
        self._browse_back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse_back_btn.setStyleSheet(
            f"""
            #browseBackBtn {{
                background: transparent;
                color: {COLORS['TEXT_SECONDARY']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            #browseBackBtn:hover {{
                border-color: {COLORS['PRIMARY']};
                color: {COLORS['PRIMARY']};
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
        room_icon.setStyleSheet(
            f"font-size: 14px; background: transparent; border: none;"
        )
        room_banner_layout.addWidget(room_icon)

        self._room_label = QLabel("")
        self._room_label.setStyleSheet(
            f"color: {COLORS['WARNING']}; font-size: 13px; font-weight: 600; "
            f"background: transparent; border: none;"
        )
        room_banner_layout.addWidget(self._room_label, 1)

        self._room_back_btn = QPushButton("← Retour à la recherche globale")
        self._room_back_btn.setObjectName("roomBackBtn")
        self._room_back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._room_back_btn.setStyleSheet(
            f"""
            #roomBackBtn {{
                background: transparent;
                color: {COLORS['TEXT_SECONDARY']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            #roomBackBtn:hover {{
                border-color: {COLORS['WARNING']};
                color: {COLORS['WARNING']};
            }}
            """
        )
        self._room_back_btn.clicked.connect(self._exit_room_mode)
        room_banner_layout.addWidget(self._room_back_btn)

        outer.addWidget(self._room_banner)

        # ── Barre de recherche ──
        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        # Champ salon
        room_prefix = QLabel("#")
        room_prefix.setStyleSheet(
            f"color: {COLORS['WARNING']}; font-size: 13px; font-weight: 700; "
            f"background: transparent; border: none; padding: 0;"
        )
        search_row.addWidget(room_prefix)

        self._room_input = QLineEdit()
        self._room_input.setObjectName("roomInput")
        self._room_input.setPlaceholderText("salon")
        self._room_input.setFixedWidth(100)
        self._room_input.setStyleSheet(
            f"""
            #roomInput {{
                background: {COLORS['BG_SURFACE']};
                color: {COLORS['WARNING']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 6px;
                padding: 8px 8px;
                font-size: 12px;
            }}
            #roomInput:focus {{
                border-color: {COLORS['WARNING']};
            }}
            #roomInput:disabled {{
                color: {COLORS['TEXT_DISABLED']};
            }}
            """
        )
        search_row.addWidget(self._room_input)

        self._search_input = QLineEdit()
        self._search_input.setObjectName("rechercheInput")
        self._search_input.setPlaceholderText(
            "Rechercher des fichiers audio sur Soulseek…"
        )
        self._search_input.setStyleSheet(
            f"""
            #rechercheInput {{
                background: {COLORS['BG_SURFACE']};
                color: {COLORS['TEXT_PRIMARY']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }}
            #rechercheInput:focus {{
                border-color: {COLORS['PRIMARY']};
            }}
            #rechercheInput:disabled {{
                color: {COLORS['TEXT_DISABLED']};
            }}
            """
        )
        self._search_input.returnPressed.connect(self._on_search)
        search_row.addWidget(self._search_input, 1)

        self._search_btn = QPushButton("Rechercher")
        self._search_btn.setObjectName("rechercheBtn")
        self._search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._search_btn.setStyleSheet(
            f"""
            #rechercheBtn {{
                background: {COLORS['PRIMARY']};
                color: {COLORS['TEXT_WHITE']};
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 14px;
                font-weight: 600;
            }}
            #rechercheBtn:hover {{
                background: {COLORS['PRIMARY_HOVER']};
            }}
            #rechercheBtn:disabled {{
                background: {COLORS['BG_BTN_DISABLED']};
                color: {COLORS['TEXT_DISABLED']};
            }}
            """
        )
        self._search_btn.clicked.connect(self._on_search)
        search_row.addWidget(self._search_btn)

        self._stop_btn = QPushButton("⏹ Stop")
        self._stop_btn.setObjectName("stopBtn")
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.setVisible(False)
        self._stop_btn.setStyleSheet(
            f"""
            #stopBtn {{
                background: {COLORS['DANGER_BTN']};
                color: {COLORS['TEXT_WHITE']};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 600;
            }}
            #stopBtn:hover {{
                background: {COLORS['DANGER_BTN_HOVER']};
            }}
            """
        )
        self._stop_btn.clicked.connect(self._on_stop)
        search_row.addWidget(self._stop_btn)

        outer.addLayout(search_row)

        # ── Barre d'état / compteur ──
        self._status_label = QLabel("")
        self._status_label.setStyleSheet(
            f"color: {COLORS['TEXT_SECONDARY']}; font-size: 12px;"
        )
        outer.addWidget(self._status_label)

        # ── Suggestions d'historique ──
        self._suggestions_row = QWidget()
        self._suggestions_row.setLayout(QHBoxLayout())
        self._suggestions_row.layout().setSpacing(6)
        self._suggestions_widgets: list[QPushButton] = []

        self._history_btn = QPushButton("📜 Historique")
        self._history_btn.setObjectName("historyBtn")
        self._history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._history_btn.setStyleSheet(
            f"""
            #historyBtn {{
                background: transparent;
                color: {COLORS['TEXT_SECONDARY']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 10px;
                padding: 4px 10px;
                font-size: 10px;
                font-weight: 600;
            }}
            #historyBtn:hover {{
                border-color: {COLORS['PRIMARY']};
                color: {COLORS['PRIMARY']};
            }}
            """
        )
        self._history_btn.clicked.connect(self._open_history_popup)

        self._rebuild_suggestions()
        outer.addWidget(self._suggestions_row)

        # ── Tableau de résultats ──
        self._table = QTableWidget()
        self._table.setObjectName("resultTable")
        self._table.setColumnCount(len(COLUMNS))
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)

        self._table.setStyleSheet(
            f"""
            #resultTable {{
                background: {COLORS['BG_SURFACE']};
                alternate-background-color: {COLORS.get('BG_SURFACE2', '#2a2a3a')};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 6px;
                gridline-color: transparent;
                font-size: 12px;
            }}
            #resultTable::item {{
                padding: 4px 8px;
                color: {COLORS['TEXT_PRIMARY']};
            }}
            #resultTable::item:selected {{
                background: rgba(COLORS['PRIMARY'], '50');
                color: {COLORS['TEXT_PRIMARY']};
            }}
            QHeaderView::section {{
                background: {COLORS.get('BG_HEADER', COLORS['BG_SURFACE2'])};
                color: {COLORS['TEXT_PRIMARY']};
                border: none;
                border-bottom: 1px solid {COLORS['BORDER']};
                border-right: 1px solid {COLORS['BORDER']};
                padding: 6px 8px;
                font-weight: 700;
                font-size: 11px;
            }}
            QHeaderView::section:hover {{
                background: {COLORS['BG_HOVER']};
            }}
            """
        )

        header = self._table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(COL_FICHIER, QHeaderView.Stretch)
        header.setSectionResizeMode(COL_EXTENSION, QHeaderView.Fixed)
        header.setSectionResizeMode(COL_TAILLE, QHeaderView.Fixed)
        header.setSectionResizeMode(COL_BITRATE, QHeaderView.Fixed)
        header.setSectionResizeMode(COL_DUREE, QHeaderView.Fixed)
        header.setSectionResizeMode(COL_UTILISATEUR, QHeaderView.Fixed)
        header.setSectionResizeMode(COL_SLOTS, QHeaderView.Fixed)
        header.setSectionResizeMode(COL_VITESSE, QHeaderView.Fixed)
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
        self._table.sortByColumn(COL_BITRATE, Qt.DescendingOrder)

        # Menu contextuel (clic droit)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)

        outer.addWidget(self._table, 1)

    # ── API publique ────────────────────────────────────────────

    def set_connexion_manager(self, manager: ConnexionManager) -> None:
        """Définit le gestionnaire de connexion et connecte les signaux."""
        self._connexion_manager = manager

        manager.search_result_received.connect(self._on_search_result)
        manager.connected.connect(self._on_connected)
        manager.disconnected.connect(self._on_disconnected)
        manager.error_occurred.connect(self._on_search_error)

        self._update_connected_state()

    # ── État de connexion ───────────────────────────────────────

    def _update_connected_state(self) -> None:
        """Met à jour l'interface selon l'état de connexion."""
        connected = (
            self._connexion_manager is not None
            and self._connexion_manager.is_connected
        )
        self._search_input.setEnabled(connected)
        self._search_btn.setEnabled(connected and not self._searching)

    def _on_connected(self, username: str) -> None:
        self._update_connected_state()

    def _on_disconnected(self) -> None:
        self._reset_search_state()
        self._update_connected_state()

    # ── Recherche ───────────────────────────────────────────────

    def _on_search(self) -> None:
        """Lance une recherche sur Soulseek."""
        query = self._search_input.text().strip()
        if len(query) < 2:
            self._status_label.setText(
                "📝 Minimum 2 caractères pour lancer une recherche"
            )
            return

        if self._connexion_manager is None or not self._connexion_manager.is_connected:
            self._status_label.setText("❌ Connexion perdue")
            return

        # Vérifier si un salon a été saisi dans le champ #
        room_text = self._room_input.text().strip()
        if room_text and not self._room_name:
            # Premier usage du salon : entrer en mode salon
            self._enter_room_mode(room_text)
        elif not room_text and self._room_name:
            # Salon vidé : retour en mode global et lance la recherche libre
            self._exit_room_mode()

        if self._search_timer is not None:
            self._search_timer.stop()

        self._clear_results()
        self._result_count = 0
        self._searching = True
        self._search_btn.setEnabled(False)
        self._search_btn.setVisible(False)
        self._stop_btn.setVisible(True)

        if self._room_name:
            # Mode salon : recherche dans un salon spécifique
            self._status_label.setText(
                f"🔍 Recherche de « {query} » dans #{self._room_name}…"
            )
            self._connexion_manager.search_room(self._room_name, query)
            self._search_history.add(
                query, type_="room", username=self._room_name,
            )
        elif self._browse_username:
            # Mode utilisateur : recherche chez un utilisateur spécifique
            self._status_label.setText(
                f"🔍 Recherche de « {query} » chez {self._browse_username}…"
            )
            self._connexion_manager.search_user(self._browse_username, query)
            self._search_history.add(
                query, type_="user", username=self._browse_username,
            )
        else:
            # Mode global : recherche standard
            self._status_label.setText(f"🔍 Recherche de « {query} » en cours…")
            self._connexion_manager.search(query)
            self._search_history.add(query, type_="global")

        self._rebuild_suggestions()
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._on_search_timeout)
        self._search_timer.start(30000)

    def _on_stop(self) -> None:
        """Arrête la recherche en cours et annule la requête réseau."""
        if self._connexion_manager is not None:
            self._connexion_manager.stop_search()
        self._reset_search_state()
        self._status_label.setText(
            f"⏹ Recherche arrêtée — {self._result_count} résultat(s) affiché(s)"
        )

    def _on_audio_filter_toggled(self, checked: bool) -> None:
        """Bascule le filtre audio automatique mp3/flac/ogg."""
        self._audio_filter_enabled = checked
        self._audio_filter_btn.setText(
            "🔊 Audio seulement" if checked else "🔊 Tous les fichiers"
        )
        self._apply_filters()

    def _on_mode_dispo_toggled(self, checked: bool) -> None:
        """Bascule le mode disponibilité (slots libres uniquement)."""
        self._mode_dispo_enabled = checked
        self._mode_dispo_btn.setText(
            "🟢 Mode dispo" if checked else "🔴 Mode dispo"
        )
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

        self._table.setSortingEnabled(False)
        added = 0

        for file_data in result.shared_items:
            if self._audio_filter_enabled and not _is_audio(file_data.extension):
                continue

            self._add_result_row(
                file_data=file_data,
                username=result.username,
                has_free_slots=result.has_free_slots,
                avg_speed=result.avg_speed,
            )
            added += 1

        self._table.setSortingEnabled(True)

        if added > 0:
            self._result_count += added

            if self._result_count >= MAX_RESULTS:
                if self._room_name:
                    status = (
                        f"⚠️ {MAX_RESULTS} résultats max dans #{self._room_name}"
                        f" — affinez votre recherche"
                    )
                elif self._browse_username:
                    status = (
                        f"⚠️ {MAX_RESULTS} résultats max chez"
                        f" {self._browse_username}"
                        f" — affinez votre recherche"
                    )
                else:
                    status = (
                        f"⚠️ {MAX_RESULTS} résultats max — affinez votre recherche"
                    )
            else:
                status = (
                    f"✅ {self._result_count} résultat"
                    f"{'s' if self._result_count > 1 else ''}"
                )
                if query_text:
                    if self._room_name:
                        status += (
                            f" — recherche « {query_text} »"
                            f" dans #{self._room_name}"
                        )
                    elif self._browse_username:
                        status += (
                            f" — recherche « {query_text} »"
                            f" chez {self._browse_username}"
                        )
                    else:
                        status += f" — recherche « {query_text} »"
            self._status_label.setText(status)

        # Mettre à jour le compteur dans l'historique
        if query_text and self._result_count > 0:
            if self._room_name:
                self._search_history.update_count(
                    query_text, type_="room", username=self._room_name,
                    count=self._result_count,
                )
            elif self._browse_username:
                self._search_history.update_count(
                    query_text, type_="user",
                    username=self._browse_username,
                    count=self._result_count,
                )
            else:
                self._search_history.update_count(
                    query_text, type_="global",
                    count=self._result_count,
                )

        if self._searching:
            self._searching = False
            self._stop_btn.setVisible(False)
            self._search_btn.setVisible(True)
            self._search_btn.setEnabled(True)
            self._search_btn.setText("Rechercher")
            # Appliquer les filtres sur les nouveaux résultats
            if self._mode_dispo_enabled or any(v for v in self._filter_state.values()):
                self._apply_filters()

    def _on_search_error(self, msg: str) -> None:
        if self._searching:
            self._reset_search_state()
            self._status_label.setText(f"❌ Erreur : {msg}")

    def _on_search_timeout(self) -> None:
        if self._searching:
            self._searching = False
            self._stop_btn.setVisible(False)
            self._search_btn.setVisible(True)
            self._search_btn.setEnabled(True)
            self._search_btn.setText("Rechercher")
            self._status_label.setText(
                "⏱️ La recherche continue en arrière-plan…"
            )

    # ── Filtres avancés ─────────────────────────────────────────

    def _open_filtres_modal(self) -> None:
        """Ouvre la modal de filtres avancés."""
        modal = FiltresRechercheModal(
            filter_state=self._filter_state,
            parent=self,
        )
        if modal.exec() == QDialog.Accepted:
            self._filter_state = dict(modal.result_state)
            self._apply_filters()

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
            self._filtres_badge.setText(f" {count} ")
            self._filtres_badge.setVisible(True)
        else:
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

        has_filters = (
            self._filtres_compte > 0
            or not self._audio_filter_enabled
            or self._mode_dispo_enabled
        )

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

        # Mettre à jour le statut pour refléter le filtrage
        total = self._table.rowCount()
        if total > 0:
            if visible_count < total:
                extra = []
                if self._mode_dispo_enabled:
                    extra.append("🟢 dispo")
                if self._filtres_compte > 0:
                    extra.append(
                        f"{self._filtres_compte} filtre{'s' if self._filtres_compte > 1 else ''}"
                    )
                suffix = f" — {' + '.join(extra)}" if extra else ""
                self._status_label.setText(
                    f"✅ {visible_count}/{total} résultat{'s' if total > 1 else ''}{suffix}"
                )
            else:
                extra = []
                if self._mode_dispo_enabled:
                    extra.append("🟢 dispo")
                if self._filtres_compte > 0:
                    extra.append(
                        f"{self._filtres_compte} filtre{'s' if self._filtres_compte > 1 else ''}"
                    )
                suffix = f" — {' + '.join(extra)}" if extra else ""
                self._status_label.setText(
                    f"✅ {total} résultat{'s' if total > 1 else ''}{suffix}"
                )

    # ── Menu contextuel ──────────────────────────────────────────

    def _get_row_data(self, row: int) -> dict | None:
        """Extrait les données brutes d'une ligne du tableau."""
        item = self._table.item(row, COL_FICHIER)
        if item is None:
            return None
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
                background: {COLORS['BG_SURFACE']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                color: {COLORS['TEXT_PRIMARY']};
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
            }}
            QMenu::item:selected {{
                background: rgba(COLORS['PRIMARY'], '30');
                color: {COLORS['PRIMARY']};
            }}
            QMenu::separator {{
                height: 1px;
                background: {COLORS['BORDER']};
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
        browse_action.triggered.connect(
            lambda: self._on_browse_user(username)
        )
        menu.addAction(browse_action)

        menu.addSeparator()

        # ── 📋 Copier le nom du fichier ──
        copy_action = QAction("📋 Copier le nom du fichier", self)
        copy_action.triggered.connect(
            lambda: QApplication.clipboard().setText(filename)
        )
        menu.addAction(copy_action)

        # ── 🚫 Bloquer l'utilisateur ──
        block_action = QAction(f"🚫 Bloquer {username}", self)
        block_action.triggered.connect(
            lambda: self._on_block_user(username)
        )
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
        self._search_input.setPlaceholderText(
            f"Rechercher des fichiers partagés par {username}…"
        )

    def _exit_browse_mode(self) -> None:
        """Quitte le mode navigation utilisateur."""
        self._browse_username = None
        self._browse_banner.setVisible(False)
        self._search_input.setPlaceholderText(
            "Rechercher des fichiers audio sur Soulseek…"
        )
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
        self._room_input.setText(room)
        self._search_input.setPlaceholderText(
            f"Rechercher dans #{room}…"
        )

    def _exit_room_mode(self) -> None:
        """Quitte le mode recherche dans un salon."""
        self._room_name = None
        self._room_banner.setVisible(False)
        self._room_input.clear()
        self._search_input.setPlaceholderText(
            "Rechercher des fichiers audio sur Soulseek…"
        )
        self._reset_search_state()
        self._clear_results()
        self._status_label.setText("")

    def _on_browse_user(self, username: str) -> None:
        """Lance une recherche des fichiers d'un utilisateur."""
        query = self._search_input.text().strip()
        if not query:
            self._status_label.setText(
                "📝 Entrez un terme de recherche avant de parcourir un utilisateur"
            )
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
        self._stop_btn.setVisible(True)
        self._status_label.setText(
            f"🔍 Recherche de « {query} » chez {username}…"
        )
        self._connexion_manager.search_user(username, query)

    def _on_block_user(self, username: str) -> None:
        """Ajoute un utilisateur à la liste noire."""
        if self._connexion_manager is not None:
            self._connexion_manager.block_user(username)
        self._status_label.setText(f"🚫 Utilisateur {username} bloqué")

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

        bitrate = _get_attr(file_data.attributes, _ATTR_BITRATE) or 0
        duration = _get_attr(file_data.attributes, _ATTR_DURATION) or 0
        filename = file_data.filename.split("\\")[-1].split("/")[-1]
        ext = file_data.extension.upper()

        # Données brutes pour le re-filtrage
        row_data = {
            "extension": file_data.extension.lower(),
            "filename": filename,
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
        fichier_item.setToolTip(file_data.filename)
        fichier_item.setData(Qt.UserRole + 1, row_data)
        self._table.setItem(row, COL_FICHIER, fichier_item)

        # ── Colonne 2 : Taille ──
        size_str = _format_size(file_data.filesize)
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
        slots_item.setToolTip(
            "Slots libres" if has_free_slots else "File d'attente"
        )
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
                background: {COLORS['PRIMARY']};
                color: {COLORS['TEXT_WHITE']};
                border: none;
                border-radius: 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {COLORS['PRIMARY_HOVER']};
            }}
            QPushButton:disabled {{
                background: {COLORS['BG_BTN_DISABLED']};
                color: {COLORS['TEXT_DISABLED']};
            }}
            """
        )
        dl_btn.setToolTip(f"Télécharger « {filename} »")
        dl_btn.setEnabled(False)
        self._table.setCellWidget(row, COL_DL, dl_btn)

    # ── Nettoyage ───────────────────────────────────────────────

    def _reset_search_state(self) -> None:
        self._searching = False
        self._stop_btn.setVisible(False)
        self._search_btn.setVisible(True)
        self._search_btn.setEnabled(True)
        self._search_btn.setText("Rechercher")
        if self._search_timer is not None:
            self._search_timer.stop()

    def _clear_results(self) -> None:
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        self._table.setSortingEnabled(True)

    # ── Historique des recherches ──────────────────────────────

    def _rebuild_suggestions(self) -> None:
        """Met à jour les suggestions rapides sous la barre de recherche.

        Affiche les 5 dernières recherches sous forme de boutons
        cliquables + le bouton ``📜 Historique``.
        """
        # Nettoyer les widgets existants
        for widget in self._suggestions_widgets:
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
                    background: {COLORS['BG_SURFACE']};
                    color: {COLORS['TEXT_SECONDARY']};
                    border: 1px solid {COLORS['BORDER']};
                    border-radius: 10px;
                    padding: 3px 10px;
                    font-size: 10px;
                }}
                QPushButton:hover {{
                    background: rgba(COLORS['PRIMARY'], '20');
                    border-color: {COLORS['PRIMARY']};
                    color: {COLORS['PRIMARY']};
                }}
                """
            )
            btn.clicked.connect(
                lambda checked, e=entry: self._on_suggestion_clicked(e)
            )
            self._suggestions_row.layout().addWidget(btn)
            self._suggestions_widgets.append(btn)

        # Bouton Historique complet (toujours visible)
        self._suggestions_row.layout().addWidget(self._history_btn)

        # Ajouter un stretch pour pousser à gauche
        self._suggestions_row.layout().addStretch(1)
        self._suggestions_row.setVisible(bool(recent))

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

        # Remplir le champ de recherche et lancer
        self._search_input.setText(query)
        self._on_search()

    def _open_history_popup(self) -> None:
        """Ouvre la popup d'historique complet."""
        dialog = HistoryPopup(
            self._search_history.get_all(), self,
            history=self._search_history,
        )
        dialog.clear_requested.connect(self._on_history_clear)
        dialog.entries_changed.connect(self._rebuild_suggestions)
        if dialog.exec():
            selected = dialog.selected_entry
            if selected:
                self._on_suggestion_clicked(selected)

    def _on_history_clear(self) -> None:
        """Vide tout l'historique et rafraîchit les suggestions."""
        self._search_history.clear()
        self._rebuild_suggestions()
        self._status_label.setText("🗑 Historique effacé")
