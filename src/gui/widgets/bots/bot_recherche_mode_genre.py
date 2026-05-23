"""Widget du Mode Genre pour Athéna (BotRecherche).

Silo complet : pas de partage de logique avec le mode Normal.
Utilise ``GenreService`` pour la récupération asynchrone des
arborescences et le filtrage par genre.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.theme_fragments.colors import COLORS

if TYPE_CHECKING:
    from src.services.genre_service import GenreResultat, GenreService

logger = logging.getLogger("[MODE-GENRE]")

# ── Constantes ──────────────────────────────────────────────────

_COL_CLIENT = 0
_COL_DOSSIER = 1
_COL_FICHIERS = 2
_COL_AUDIO = 3
_COL_TAILLE = 4

_COLUMNS = [
    "Client",
    "Dossier",
    "Fichiers",
    "Audio",
    "Taille",
]

_EXTENSIONS_AUDIO = {"mp3", "flac", "ogg", "wav", "aac", "wma", "m4a", "ape", "opus"}


# ── Helpers ──────────────────────────────────────────────────────


def _format_size(bytes_val: int) -> str:
    if bytes_val >= 1_000_000_000:
        return f"{bytes_val / 1_000_000_000:.1f} Go"
    if bytes_val >= 1_000_000:
        return f"{bytes_val / 1_000_000:.1f} Mo"
    if bytes_val >= 1_000:
        return f"{bytes_val / 1_000:.1f} Ko"
    return f"{bytes_val} o"


def _extraire_extension(filename: str) -> str:
    if not filename:
        return ""
    basename = filename.replace("\\", "/").rstrip("/").split("/")[-1]
    if "." in basename:
        return basename.rsplit(".", 1)[-1].lower()
    return ""


# ═════════════════════════════════════════════════════════════════
#  ModeGenre — Widget
# ═════════════════════════════════════════════════════════════════


class ModeGenre(QFrame):
    """Widget du mode Genre dans Athéna.

    Affiche le sélecteur de genre, les options, les boutons de
    contrôle, et un tableau des résultats.

    Signaux
    -------
    recherche_lancee(str)
        Émis quand l'utilisateur lance une recherche (contient le genre_id).
    recherche_arretee()
        Émis quand l'utilisateur arrête la recherche.
    """

    recherche_lancee = Signal(str)  # genre_id
    recherche_arretee = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("modeGenre")

        self._en_cours = False
        self._service: GenreService | None = None
        self._resultats: list[dict[str, Any]] = []

        self._build_ui()
        self._update_etat()

    # ── Construction de l'interface ─────────────────────────────

    def _build_ui(self) -> None:
        """Construit l'interface complète du mode Genre."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ── Titre ──
        title = QLabel("🎵 Mode Genre")
        title.setStyleSheet(f"color: {COLORS['ACCENT']}; font-size: 15px; font-weight: 700;")
        layout.addWidget(title)

        # ── Ligne : genre + boutons ──
        controls = QHBoxLayout()
        controls.setSpacing(8)

        genre_label = QLabel("Genre :")
        genre_label.setStyleSheet(f"color: {COLORS['TEXT_SECONDARY']}; font-size: 12px; font-weight: 600;")
        controls.addWidget(genre_label)

        self._genre_combo = QComboBox()
        self._genre_combo.setObjectName("genreCombo")
        self._genre_combo.setMinimumWidth(180)
        self._genre_combo.setStyleSheet(
            f"""
            #genreCombo {{
                background: {COLORS["BG_SURFACE"]};
                color: {COLORS["TEXT_PRIMARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            #genreCombo:focus {{
                border-color: {COLORS["ACCENT"]};
            }}
            #genreCombo::drop-down {{
                border: none;
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
            }}
            #genreCombo QAbstractItemView {{
                background: {COLORS["BG_SURFACE"]};
                color: {COLORS["TEXT_PRIMARY"]};
                border: 1px solid {COLORS["BORDER"]};
                selection-background-color: rgba(COLORS['ACCENT'], '30');
                outline: none;
            }}
            """
        )
        controls.addWidget(self._genre_combo)

        # Bouton Lancer
        self._lancer_btn = QPushButton("🚀 Lancer")
        self._lancer_btn.setObjectName("genreLancerBtn")
        self._lancer_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._lancer_btn.setStyleSheet(
            f"""
            #genreLancerBtn {{
                background: {COLORS["SUCCESS"]};
                color: {COLORS["TEXT_WHITE"]};
                border: none;
                border-radius: 6px;
                padding: 6px 20px;
                font-size: 13px;
                font-weight: 700;
            }}
            #genreLancerBtn:hover {{
                background: {COLORS["SUCCESS_HOVER"]};
            }}
            #genreLancerBtn:disabled {{
                background: {COLORS["BG_BTN_DISABLED"]};
                color: {COLORS["TEXT_DISABLED"]};
            }}
            """
        )
        self._lancer_btn.clicked.connect(self._on_lancer)
        controls.addWidget(self._lancer_btn)

        # Bouton Stop
        self._stop_btn = QPushButton("⏹ Stop")
        self._stop_btn.setObjectName("genreStopBtn")
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.setVisible(False)
        self._stop_btn.setStyleSheet(
            f"""
            #genreStopBtn {{
                background: {COLORS["DANGER_BTN"]};
                color: {COLORS["TEXT_WHITE"]};
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            #genreStopBtn:hover {{
                background: {COLORS["DANGER_BTN_HOVER"]};
            }}
            """
        )
        self._stop_btn.clicked.connect(self._on_stop)
        controls.addWidget(self._stop_btn)

        # Bouton Effacer
        self._clear_btn = QPushButton("🗑 Effacer")
        self._clear_btn.setObjectName("genreClearBtn")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.setStyleSheet(
            f"""
            #genreClearBtn {{
                background: transparent;
                color: {COLORS["TEXT_SECONDARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 600;
            }}
            #genreClearBtn:hover {{
                border-color: {COLORS["DANGER_BTN"]};
                color: {COLORS["DANGER_BTN"]};
            }}
            """
        )
        self._clear_btn.clicked.connect(self._on_clear)
        controls.addWidget(self._clear_btn)

        controls.addStretch(1)
        layout.addLayout(controls)

        # ── Options ──
        options_row = QHBoxLayout()
        options_row.setSpacing(12)

        self._audio_only_cb = QCheckBox("🔊 Audio seulement")
        self._audio_only_cb.setChecked(True)
        self._audio_only_cb.setStyleSheet(
            f"""
            QCheckBox {{
                color: {COLORS["TEXT_SECONDARY"]};
                font-size: 11px;
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 3px;
                background: {COLORS["BG_SURFACE"]};
            }}
            QCheckBox::indicator:checked {{
                background: {COLORS["ACCENT"]};
                border-color: {COLORS["ACCENT"]};
            }}
            """
        )
        options_row.addWidget(self._audio_only_cb)

        options_row.addStretch(1)
        layout.addLayout(options_row)

        # ── Barre de statut ──
        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"color: {COLORS['TEXT_SECONDARY']}; font-size: 12px;")
        layout.addWidget(self._status_label)

        # ── Tableau des résultats ──
        self._table = QTableWidget()
        self._table.setObjectName("genreResultTable")
        self._table.setColumnCount(len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)

        self._table.setStyleSheet(
            f"""
            #genreResultTable {{
                background: {COLORS["BG_SURFACE"]};
                alternate-background-color: {COLORS.get("BG_SURFACE2", "#2a2a3a")};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                font-size: 12px;
            }}
            #genreResultTable::item {{
                padding: 4px 8px;
                color: {COLORS["TEXT_PRIMARY"]};
            }}
            #genreResultTable::item:selected {{
                background: rgba(COLORS['ACCENT'], '50');
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
        header.setSectionResizeMode(_COL_CLIENT, header.ResizeMode.Fixed)
        header.setSectionResizeMode(_COL_DOSSIER, header.ResizeMode.Stretch)
        header.setSectionResizeMode(_COL_FICHIERS, header.ResizeMode.Fixed)
        header.setSectionResizeMode(_COL_AUDIO, header.ResizeMode.Fixed)
        header.setSectionResizeMode(_COL_TAILLE, header.ResizeMode.Fixed)
        self._table.setColumnWidth(_COL_CLIENT, 140)
        self._table.setColumnWidth(_COL_FICHIERS, 80)
        self._table.setColumnWidth(_COL_AUDIO, 70)
        self._table.setColumnWidth(_COL_TAILLE, 90)

        layout.addWidget(self._table, 1)

    # ── API publique ────────────────────────────────────────────

    def set_service(self, service: GenreService) -> None:
        """Injecte le GenreService et connecte les signaux."""
        self._service = service
        self._service.resultat_recu.connect(self._on_resultat)
        self._service.termine.connect(self._on_termine)
        self._service.erreur.connect(self._on_erreur)
        self._service.progression.connect(self._on_progression)
        self._peupler_genres()

    def _peupler_genres(self) -> None:
        """Remplit le combo box avec les genres disponibles."""
        self._genre_combo.clear()
        if self._service is None:
            return
        for genre in self._service.genres_disponibles:
            self._genre_combo.addItem(f"🎵 {genre['name']}", genre["id"])
        if self._genre_combo.count() > 0:
            self._genre_combo.setCurrentIndex(0)

    def _update_etat(self) -> None:
        """Met à jour l'interface selon l'état (recherche en cours ou non)."""
        self._lancer_btn.setVisible(not self._en_cours)
        self._stop_btn.setVisible(self._en_cours)
        self._genre_combo.setEnabled(not self._en_cours)
        self._audio_only_cb.setEnabled(not self._en_cours)
        self._clear_btn.setEnabled(not self._en_cours)

    # ── Handlers ────────────────────────────────────────────────

    def _on_lancer(self) -> None:
        """Lance la recherche Genre."""
        genre_id = self._genre_combo.currentData()
        if not genre_id:
            return
        self._en_cours = True
        self._update_etat()
        self._status_label.setText(f"🎵 Recherche de « {self._genre_combo.currentText()} » en cours…")
        self._table.setRowCount(0)
        self._resultats.clear()
        self.recherche_lancee.emit(genre_id)

    def _on_stop(self) -> None:
        """Arrête la recherche en cours."""
        if self._service is not None:
            self._service.arreter()
        self._en_cours = False
        self._update_etat()
        self._status_label.setText(f"⏹ Recherche arrêtée — {len(self._resultats)} résultat(s)")
        self.recherche_arretee.emit()

    def _on_clear(self) -> None:
        """Efface les résultats."""
        self._table.setRowCount(0)
        self._resultats.clear()
        self._status_label.setText("")

    def _on_resultat(self, resultat: object) -> None:
        """Reçoit un résultat du GenreService."""
        from src.services.genre_service import GenreResultat

        if not isinstance(resultat, GenreResultat):
            return

        row_data = {
            "username": resultat.username,
            "chemin": resultat.chemin,
            "nb_fichiers": len(resultat.fichiers),
            "nb_audio": resultat.nb_fichiers_audio,
            "taille_totale": sum(f.get("filesize", 0) for f in resultat.fichiers),
            "fichiers": resultat.fichiers,
        }
        self._resultats.append(row_data)

        # Ajouter une ligne au tableau
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setRowHeight(row, 32)

        # Client
        client_item = QTableWidgetItem(f"👤 {resultat.username}")
        client_item.setToolTip(f"👤 {resultat.username}")
        self._table.setItem(row, _COL_CLIENT, client_item)

        # Dossier
        dossier_item = QTableWidgetItem(f"📁 {resultat.chemin}")
        dossier_item.setToolTip(resultat.chemin)
        self._table.setItem(row, _COL_DOSSIER, dossier_item)

        # Fichiers
        total = len(resultat.fichiers)
        fichiers_item = QTableWidgetItem(str(total))
        fichiers_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, _COL_FICHIERS, fichiers_item)

        # Audio
        audio = resultat.nb_fichiers_audio
        audio_text = str(audio) if audio > 0 else "—"
        audio_item = QTableWidgetItem(audio_text)
        audio_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, _COL_AUDIO, audio_item)

        # Taille totale
        taille = sum(f.get("filesize", 0) for f in resultat.fichiers)
        taille_item = QTableWidgetItem(_format_size(taille))
        taille_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._table.setItem(row, _COL_TAILLE, taille_item)

        # Mettre à jour le statut
        self._status_label.setText(
            f"✅ {len(self._resultats)} dossier{'s' if len(self._resultats) > 1 else ''} matché{'s' if len(self._resultats) > 1 else ''}"
        )

    def _on_termine(self) -> None:
        """La boucle GenreService est terminée."""
        self._en_cours = False
        self._update_etat()
        if self._resultats:
            self._status_label.setText(
                f"✅ Terminé — {len(self._resultats)} dossier{'s' if len(self._resultats) > 1 else ''} trouvé{'s' if len(self._resultats) > 1 else ''}"
            )
        else:
            self._status_label.setText("📭 Aucun dossier trouvé pour ce genre")

    def _on_erreur(self, msg: str) -> None:
        """Erreur du GenreService."""
        self._status_label.setText(msg)
        logger.warning("ModeGenre: %s", msg)

    def _on_progression(self, username: str, match: int, total: int) -> None:
        """Mise à jour de progression."""
        logger.debug("ModeGenre: %s → %d/%d dossiers matchés", username, match, total)
