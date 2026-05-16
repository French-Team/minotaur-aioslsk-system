"""
Bot Téléchargement — Gestion des téléchargements Soulseek.

Affiche la liste des transferts (downloads/uploads) avec progression,
statistiques, toolbar, barre de progression globale, et navigation inter-bots.

Voir `specs/bot-planificateur-spec.md` pour l'intégration planificateur.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QClipboard, QColor, QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.theme_fragments.colors import COLORS
from src.services import telechargement_history
from src.services.event_bus import EventBus

logger = logging.getLogger(__name__)

# ── Constantes ──────────────────────────────────────────────────────────────

_STATUT_COULEURS: dict[str, str] = {
    "en_cours": COLORS["SUCCESS"],
    "attente": COLORS["WARNING"],
    "termine": COLORS["PRIMARY"],
    "echoue": COLORS["DANGER"],
}

_STATUT_LIBELLES: dict[str, str] = {
    "en_cours": "En cours",
    "attente": "En attente",
    "termine": "Terminé",
    "echoue": "Échoué",
}

_STATUT_ICONES: dict[str, str] = {
    "en_cours": "🔄",
    "attente": "⏳",
    "termine": "✅",
    "echoue": "❌",
}

# Rôle Qt pour stocker le tri numérique
_SortRole = Qt.UserRole + 1


class _NumericItem(QTableWidgetItem):
    """QTableWidgetItem qui trie numériquement via _SortRole."""
    def __lt__(self, other):
        if isinstance(other, QTableWidgetItem):
            try:
                return float(self.data(_SortRole)) < float(other.data(_SortRole))
            except (TypeError, ValueError):
                pass
        return super().__lt__(other)


_COLONNES: list[tuple[str, int]] = [
    ("Fichier", 260),
    ("Taille", 90),
    ("Utilisateur", 140),
    ("Progression", 180),
    ("Vitesse", 100),
    ("Statut", 120),
]

# ── Helpers ─────────────────────────────────────────────────────────────────


def _format_taille(bytes_val: int) -> str:
    """Formate une taille en bytes en lisible."""
    if bytes_val >= 1_000_000_000:
        return f"{bytes_val / 1_000_000_000:.1f} Go"
    if bytes_val >= 1_000_000:
        return f"{bytes_val / 1_000_000:.1f} Mo"
    if bytes_val >= 1_000:
        return f"{bytes_val / 1_000:.1f} Ko"
    return f"{bytes_val} o"


def _format_vitesse(bytes_per_sec: float) -> str:
    """Formate une vitesse en bytes/s en lisible."""
    if bytes_per_sec >= 1_000_000:
        return f"{bytes_per_sec / 1_000_000:.1f} Mo/s"
    if bytes_per_sec >= 1_000:
        return f"{bytes_per_sec / 1_000:.1f} Ko/s"
    return f"{bytes_per_sec:.0f} o/s"


def _format_temps_restant(secondes: float) -> str:
    """Formate un temps restant en secondes en lisible (ex: 2m 30s)."""
    if secondes < 0 or not secondes:
        return ""
    if secondes < 60:
        return f"{int(secondes)}s"
    minutes = int(secondes // 60)
    secs = int(secondes % 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    heures = minutes // 60
    minutes = minutes % 60
    return f"{heures}h {minutes}m"


# ═══════════════════════════════════════════════════════════════════════════════
# HistoryDialog
# ═══════════════════════════════════════════════════════════════════════════════


class HistoryDialog(QDialog):
    """Dialogue d'affichage de l'historique persistant des téléchargements."""

    _COLONNES: list[tuple[str, int]] = [
        ("Fichier", 260),
        ("Taille", 80),
        ("Utilisateur", 140),
        ("Statut", 80),
        ("Vitesse", 100),
        ("Date", 160),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Historique des téléchargements")
        self.setMinimumSize(900, 500)
        self.setModal(True)
        self._build_ui()
        self._load_data()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # En-tête : titre + filtre
        header = QHBoxLayout()
        header.setSpacing(8)

        titre = QLabel("📜 Historique des téléchargements")
        titre.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 700;
            color: {COLORS['TEXT_PRIMARY']};
        """)
        header.addWidget(titre)
        header.addStretch()

        lbl_filtre = QLabel("Filtrer :")
        lbl_filtre.setStyleSheet(f"color: {COLORS['TEXT_TERTIARY']}; font-size: 11px;")
        header.addWidget(lbl_filtre)

        self._combo_filtre = QComboBox()
        self._combo_filtre.addItems(["Tous", "Terminé", "Échoué"])
        self._combo_filtre.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['BG_SURFACE2']};
                color: {COLORS['TEXT_PRIMARY']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                min-width: 120px;
            }}
            QComboBox:hover {{
                border-color: {COLORS['ACCENT']};
            }}
        """)
        self._combo_filtre.currentTextChanged.connect(self._on_filtre_changed)
        header.addWidget(self._combo_filtre)

        header.addSpacing(8)

        btn_vider = QPushButton("🗑 Vider l'historique")
        btn_vider.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_vider.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['DANGER']};
                border: 1px solid {COLORS['DANGER']};
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: rgba({int(COLORS['DANGER'][1:3], 16)}, {int(COLORS['DANGER'][3:5], 16)}, {int(COLORS['DANGER'][5:7], 16)}, 0.12);
            }}
        """)
        btn_vider.clicked.connect(self._on_vider)
        header.addWidget(btn_vider)

        layout.addLayout(header)

        # Compteur
        self._lbl_count = QLabel("")
        self._lbl_count.setStyleSheet(f"color: {COLORS['TEXT_TERTIARY']}; font-size: 11px;")
        layout.addWidget(self._lbl_count)

        # Tableau
        self._table = QTableWidget()
        self._table.setColumnCount(len(self._COLONNES))
        self._table.setHorizontalHeaderLabels([c[0] for c in self._COLONNES])
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.setSortingEnabled(False)

        header = self._table.horizontalHeader()
        header.setStretchLastSection(True)
        for i, (_name, width) in enumerate(self._COLONNES):
            self._table.setColumnWidth(i, width)

        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['BG_SURFACE']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 8px;
                gridline-color: transparent;
            }}
            QTableWidget::item {{
                padding: 6px 10px;
                font-size: 12px;
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS['BG_HOVER']};
                color: {COLORS['TEXT_PRIMARY']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['BG_SURFACE2']};
                color: {COLORS['TEXT_TERTIARY']};
                border: none;
                border-bottom: 1px solid {COLORS['BORDER']};
                padding: 8px 10px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
            }}
        """)

        layout.addWidget(self._table)

    def _load_data(self) -> None:
        """Charge les données depuis l'historique SQLite."""
        filtre = self._combo_filtre.currentText().lower()
        statut_filter: str | None = None
        if filtre == "terminé":
            statut_filter = "termine"
        elif filtre == "échoué":
            statut_filter = "echoue"

        entries = telechargement_history.get_history(
            limit=500,
            statut_filter=statut_filter,
        )
        total = telechargement_history.count_history(statut_filter)

        self._table.setRowCount(0)
        self._table.setRowCount(len(entries))

        for row, entry in enumerate(entries):
            # Fichier
            item_fichier = QTableWidgetItem(entry.get("fichier", ""))
            self._table.setItem(row, 0, item_fichier)
            # Taille
            self._table.setItem(row, 1, QTableWidgetItem(entry.get("taille", "")))
            # Utilisateur
            self._table.setItem(row, 2, QTableWidgetItem(entry.get("utilisateur", "")))
            # Statut
            statut = entry.get("statut", "")
            couleur = COLORS["SUCCESS"] if statut == "termine" else COLORS["DANGER"]
            icone = "✅" if statut == "termine" else "❌"
            libelle = "Terminé" if statut == "termine" else "Échoué"
            item_statut = QTableWidgetItem(f"{icone} {libelle}")
            item_statut.setForeground(couleur)
            self._table.setItem(row, 3, item_statut)
            # Vitesse
            self._table.setItem(row, 4, QTableWidgetItem(entry.get("vitesse_moyenne", "")))
            # Date
            date_fin = entry.get("date_fin", "")
            if date_fin and len(date_fin) >= 16:
                date_fin = date_fin[:16]  # tronquer les secondes si iso
            self._table.setItem(row, 5, QTableWidgetItem(date_fin))

        self._lbl_count.setText(f"{total} entrée{'s' if total != 1 else ''}")

    def _on_filtre_changed(self, _texte: str) -> None:
        """Recharge les données avec le nouveau filtre."""
        self._load_data()

    def _on_vider(self) -> None:
        """Vide tout l'historique."""
        from PySide6.QtWidgets import QMessageBox

        reponse = QMessageBox.question(
            self,
            "Vider l'historique",
            "Supprimer définitivement tout l'historique des téléchargements ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reponse == QMessageBox.StandardButton.Yes:
            telechargement_history.clear_history()
            self._load_data()


# ═══════════════════════════════════════════════════════════════════════════════
# BotTelechargement
# ═══════════════════════════════════════════════════════════════════════════════


class BotTelechargement(QFrame):
    """Bot de gestion des téléchargements — liste temps réel, stats, actions."""

    page_changed = Signal(str)  # navigation vers un autre bot
    unseen_count_changed = Signal(int)  # badge footer

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("botTelechargement")

        # Données internes
        self._downloads: dict[str, dict[str, Any]] = {}  # identifiant -> données
        self._setup_done: bool = False
        self._unseen_count: int = 0

        self._build_ui()

    # ── API publique ─────────────────────────────────────────────────────

    def reset_unseen_count(self) -> None:
        """Réinitialise le compteur de badge footer."""
        self._unseen_count = 0
        self.unseen_count_changed.emit(0)

    # ── Helpers tableau ──────────────────────────────────────────────────

    def _find_row(self, identifiant: str) -> int:
        """Trouve la ligne d'un téléchargement par son identifiant (stocké dans Qt.UserRole)."""
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item and item.data(Qt.UserRole) == identifiant:
                return row
        return -1

    def _get_identifiant_at(self, row: int) -> str | None:
        """Retourne l'identifiant stocké à la ligne donnée."""
        item = self._table.item(row, 0)
        if item:
            return item.data(Qt.UserRole)
        return None

    # ── Filtre ───────────────────────────────────────────────────────────

    def _apply_filter(self, statut_filter: str) -> None:
        """Masque/affiche les lignes selon le filtre de statut."""
        for row in range(self._table.rowCount()):
            identifiant = self._get_identifiant_at(row)
            if identifiant:
                data = self._downloads.get(identifiant)
                if data:
                    visible = (statut_filter == "tous" or data["statut"] == statut_filter)
                    self._table.setRowHidden(row, not visible)

    # ── Connexion backend ────────────────────────────────────────────────

    def setup(self, svc: "SoulseekService") -> None:
        """Connecte le bot aux signaux SoulseekService."""
        if self._setup_done:
            return
        self._setup_done = True
        self._service = svc

        svc.transfer_added.connect(self._on_transfer_added)
        svc.transfer_removed.connect(self._on_transfer_removed)
        svc.transfer_progress.connect(self._on_transfer_progress)
        logger.info("BotTelechargement connecté aux signaux SoulseekService")

    def _on_transfer_added(self, evt: object) -> None:
        """Un nouveau transfert a été ajouté."""
        transfer = getattr(evt, 'transfer', None)
        if transfer is None:
            return

        identifiant = transfer.remote_path
        fichier = identifiant.split("/")[-1].split("\\")[-1]
        fichiersize = getattr(transfer, 'filesize', 0)
        statut = self._transfer_statut_label(transfer)
        username = getattr(transfer, 'username', '')

        self.add_download(
            identifiant=identifiant,
            fichier=fichier,
            statut=statut,
            progression=0.0,
            vitesse="",
            taille=_format_taille(fichiersize),
            taille_bytes=fichiersize,
            user=username,
        )

        # Badge footer : incrémenter le compteur d'événements non lus
        self._unseen_count += 1
        self.unseen_count_changed.emit(self._unseen_count)

        EventBus().emit_event(
            severity="INFO",
            category="transfert",
            title="Téléchargement ajouté",
            message=f"{fichier} — {username}",
            source="telechargement",
        )
        logger.info("Transfert ajouté : %s (%s)", fichier, statut)

    def _on_transfer_removed(self, evt: object) -> None:
        """Un transfert a été supprimé."""
        transfer = getattr(evt, 'transfer', None)
        if transfer is None:
            return
        self.remove_download(transfer.remote_path)
        logger.debug("Transfert supprimé : %s", transfer.remote_path)

    def _on_transfer_progress(self, evt: object) -> None:
        """Mise à jour de progression."""
        updates = getattr(evt, 'updates', None)
        if not updates:
            return
        for transfer, prev_snap, cur_snap in updates:
            remote_path = getattr(transfer, 'remote_path', '')
            if not remote_path:
                continue
            fichiersize = getattr(transfer, 'filesize', 0)
            bytes_transfered = getattr(cur_snap, 'bytes_transfered', 0) if cur_snap else 0
            if fichiersize > 0:
                progression = (bytes_transfered / fichiersize) * 100.0
            else:
                progression = 0.0

            # Détection début de téléchargement (premiers bytes reçus)
            data = self._downloads.get(remote_path)
            if data and data["statut"] != "en_cours" and progression > 0:
                fichier = data["fichier"]
                row = self._find_row(remote_path)
                username = self._table.item(row, 2).text() if row >= 0 and self._table.item(row, 2) else ""
                EventBus().emit_event(
                    severity="INFO",
                    category="transfert",
                    title="Téléchargement démarré",
                    message=f"{fichier} — {username}",
                    source="telechargement",
                )

            self.update_progression(
                remote_path, progression,
                bytes_transfered=bytes_transfered,
            )

            # Changer le statut si l'état a changé
            cur_state = cur_snap.state if cur_snap else None
            prev_state = prev_snap.state if prev_snap else None
            if cur_state is not None and prev_state != cur_state:
                nouveau = self._transfer_state_to_statut(cur_state)
                ancien = data["statut"] if data else None
                self.change_statut(remote_path, nouveau)

                # Émettre EventBus pour les transitions importantes
                if nouveau == "termine":
                    EventBus().emit_event(
                        severity="INFO",
                        category="transfert",
                        title="Téléchargement terminé",
                        message=f"{data['fichier'] if data else remote_path}",
                        source="telechargement",
                    )
                elif nouveau == "echoue" and ancien != "echoue":
                    EventBus().emit_event(
                        severity="WARN",
                        category="transfert",
                        title="Téléchargement échoué",
                        message=f"{data['fichier'] if data else remote_path}",
                        source="telechargement",
                    )

    @staticmethod
    def _transfer_state_to_statut(state: object) -> str:
        """Convertit un TransferState.State en label de statut."""
        state_name = state.name if hasattr(state, 'name') else str(state)
        mapping = {
            "VIRGIN": "attente",
            "QUEUED": "attente",
            "INITIALIZING": "attente",
            "INCOMPLETE": "en_cours",
            "DOWNLOADING": "en_cours",
            "UPLOADING": "en_cours",
            "COMPLETE": "termine",
            "FAILED": "echoue",
            "ABORTED": "echoue",
            "PAUSED": "attente",
            "UNSET": "attente",
        }
        return mapping.get(state_name.upper(), "en_cours")

    @staticmethod
    def _transfer_statut_label(transfer: object) -> str:
        """Détermine le statut initial d'un transfert."""
        state = getattr(transfer, 'state', None)
        if state is None:
            return "attente"
        return BotTelechargement._transfer_state_to_statut(state)

    # ── Construction UI ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Construit l'interface complète."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header stats
        self._build_header(layout)

        # Toolbar
        self._build_toolbar(layout)

        # Tableau
        self._build_table(layout)

    def _build_header(self, parent: QVBoxLayout) -> None:
        """Badges de statistiques + barre de progression globale."""
        # Ligne 1: badges
        header = QHBoxLayout()
        header.setSpacing(12)

        self._badge_en_cours = self._make_badge("🔄", "En cours", COLORS["SUCCESS"])
        self._badge_attente = self._make_badge("⏳", "En attente", COLORS["WARNING"])
        self._badge_termine = self._make_badge("✅", "Terminés", COLORS["PRIMARY"])
        self._badge_echoue = self._make_badge("❌", "Échoués", COLORS["DANGER"])

        header.addWidget(self._badge_en_cours)
        header.addWidget(self._badge_attente)
        header.addWidget(self._badge_termine)
        header.addWidget(self._badge_echoue)
        header.addStretch()
        parent.addLayout(header)

        # Ligne 2: progression globale
        progress_frame = QFrame()
        progress_frame.setFixedHeight(56)
        progress_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['BG_SURFACE2']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 8px;
                padding: 4px 16px;
            }}
        """)
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setContentsMargins(12, 4, 12, 6)
        progress_layout.setSpacing(2)

        # Barre de progression globale
        self._global_progress = QProgressBar()
        self._global_progress.setObjectName("globalProgress")
        self._global_progress.setRange(0, 100)
        self._global_progress.setValue(0)
        self._global_progress.setTextVisible(False)
        self._global_progress.setFixedHeight(12)
        progress_layout.addWidget(self._global_progress)

        # Labels: taille + vitesse cumulative
        info_layout = QHBoxLayout()
        info_layout.setSpacing(16)

        self._lbl_taille = QLabel("0 o / 0 o (0%)")
        self._lbl_taille.setStyleSheet(f"""
            color: {COLORS['TEXT_SECONDARY']};
            font-size: 11px;
        """)
        info_layout.addWidget(self._lbl_taille)

        self._lbl_vitesse = QLabel("")
        self._lbl_vitesse.setStyleSheet(f"""
            color: {COLORS['SUCCESS']};
            font-size: 11px;
            font-weight: 600;
        """)
        info_layout.addWidget(self._lbl_vitesse)
        info_layout.addStretch()
        progress_layout.addLayout(info_layout)

        parent.addWidget(progress_frame)

    @staticmethod
    def _make_badge(icon: str, label: str, color: str) -> QFrame:
        """Crée un badge de statistique compact."""
        frame = QFrame()
        frame.setFixedHeight(48)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['BG_SURFACE2']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 8px;
                padding: 4px 16px;
            }}
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        ico = QLabel(icon)
        ico.setStyleSheet("font-size: 18px;")
        layout.addWidget(ico)

        col = QVBoxLayout()
        col.setSpacing(0)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"""
            color: {COLORS['TEXT_TERTIARY']};
            font-size: 10px;
            font-weight: 500;
        """)
        col.addWidget(lbl)

        val = QLabel("0")
        val.setStyleSheet(f"""
            color: {color};
            font-size: 20px;
            font-weight: 700;
        """)
        val.setObjectName(f"badgeValue_{label.lower().replace(' ', '_')}")
        col.addWidget(val)

        layout.addLayout(col)

        return frame

    def _build_toolbar(self, parent: QVBoxLayout) -> None:
        """Barre d'outils avec actions batch et filtre."""
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self._btn_resume_all = self._toolbar_btn("▶ Reprendre tout")
        self._btn_resume_all.clicked.connect(self._on_resume_all)
        toolbar.addWidget(self._btn_resume_all)

        self._btn_pause_all = self._toolbar_btn("⏸ Pause tout")
        self._btn_pause_all.clicked.connect(self._on_pause_all)
        toolbar.addWidget(self._btn_pause_all)

        self._btn_cancel_all = self._toolbar_btn_danger("✕ Tout annuler")
        self._btn_cancel_all.clicked.connect(self._on_cancel_all)
        toolbar.addWidget(self._btn_cancel_all)

        toolbar.addStretch()

        # Filtre par statut
        lbl_filtre = QLabel("Filtrer :")
        lbl_filtre.setStyleSheet(f"""
            color: {COLORS['TEXT_TERTIARY']};
            font-size: 11px;
            font-weight: 500;
        """)
        toolbar.addWidget(lbl_filtre)

        self._combo_filtre = QComboBox()
        self._combo_filtre.addItems(["Tous", "En cours", "En attente", "Terminé", "Échoué"])
        self._combo_filtre.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['BG_SURFACE2']};
                color: {COLORS['TEXT_PRIMARY']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                min-width: 120px;
            }}
            QComboBox:hover {{
                border-color: {COLORS['ACCENT']};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 6px;
            }}
        """)
        self._combo_filtre.currentTextChanged.connect(self._on_filtre_changed)
        toolbar.addWidget(self._combo_filtre)

        toolbar.addSpacing(8)

        self._btn_historique = self._toolbar_btn("📜 Historique")
        self._btn_historique.clicked.connect(self._on_show_history)
        toolbar.addWidget(self._btn_historique)

        toolbar.addSpacing(8)

        self._btn_ouvrir = self._toolbar_btn("📂 Ouvrir Downloads")
        self._btn_ouvrir.clicked.connect(self._on_ouvrir_dossier)
        toolbar.addWidget(self._btn_ouvrir)

        self._btn_vider = self._toolbar_btn_danger("🗑 Vider terminés")
        self._btn_vider.clicked.connect(self._on_clear_termines)
        toolbar.addWidget(self._btn_vider)

        parent.addLayout(toolbar)

    @staticmethod
    def _toolbar_btn(texte: str) -> QPushButton:
        """Bouton de toolbar standard."""
        btn = QPushButton(texte)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['BG_SURFACE2']};
                color: {COLORS['TEXT_PRIMARY']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['BG_HOVER']};
                border-color: {COLORS['ACCENT']};
            }}
        """)
        return btn

    @staticmethod
    def _toolbar_btn_danger(texte: str) -> QPushButton:
        """Bouton de toolbar dangereux (vider)."""
        btn = QPushButton(texte)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['DANGER']};
                border: 1px solid {COLORS['DANGER']};
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: rgba({int(COLORS['DANGER'][1:3], 16)}, {int(COLORS['DANGER'][3:5], 16)}, {int(COLORS['DANGER'][5:7], 16)}, 0.12);
            }}
        """)
        return btn

    def _build_table(self, parent: QVBoxLayout) -> None:
        """Tableau des téléchargements avec tri par colonne."""
        self._table = QTableWidget()
        self._table.setObjectName("downloadTable")
        self._table.setColumnCount(len(_COLONNES))
        self._table.setHorizontalHeaderLabels([c[0] for c in _COLONNES])

        # Style
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.setSortingEnabled(True)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)

        # Colonnes
        header = self._table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSortIndicatorShown(True)
        for i, (_name, width) in enumerate(_COLONNES):
            self._table.setColumnWidth(i, width)

        # Quand le tri change, ré-appliquer le filtre
        header.sortIndicatorChanged.connect(lambda: self._apply_filter(
            self._combo_filtre.currentText().lower()
        ))

        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['BG_SURFACE']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 8px;
                gridline-color: transparent;
            }}
            QTableWidget::item {{
                padding: 6px 10px;
                font-size: 12px;
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS['BG_HOVER']};
                color: {COLORS['TEXT_PRIMARY']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['BG_SURFACE2']};
                color: {COLORS['TEXT_TERTIARY']};
                border: none;
                border-bottom: 1px solid {COLORS['BORDER']};
                padding: 8px 10px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
            }}
        """)

        parent.addWidget(self._table)

    # ── API publique ───────────────────────────────────────────────────────

    def add_download(
        self,
        identifiant: str,
        fichier: str,
        statut: str = "en_cours",
        progression: float = 0.0,
        vitesse: str = "",
        taille: str = "",
        taille_bytes: int = 0,
        vitesse_bytes: float = 0.0,
        user: str = "",
    ) -> None:
        """Ajoute un téléchargement au tableau."""
        if identifiant in self._downloads:
            return

        row = self._table.rowCount()
        self._table.insertRow(row)

        texte_statut = f"{_STATUT_ICONES.get(statut, '')} {_STATUT_LIBELLES.get(statut, statut)}"

        # Fichier (col 0) — stocke l'identifiant dans Qt.UserRole
        item_fichier = QTableWidgetItem(fichier)
        item_fichier.setData(Qt.UserRole, identifiant)
        self._table.setItem(row, 0, item_fichier)

        self._table.setItem(row, 1, QTableWidgetItem(taille))
        self._table.setItem(row, 2, QTableWidgetItem(user))

        # Progression (col 3) — _NumericItem pour tri correct
        item_prog = _NumericItem(f"{progression:.0f}%")
        item_prog.setData(_SortRole, progression)
        self._table.setItem(row, 3, item_prog)

        self._table.setItem(row, 4, QTableWidgetItem(vitesse))

        col_statut = QTableWidgetItem(texte_statut)
        col_statut.setForeground(QColor(_STATUT_COULEURS.get(statut, COLORS["TEXT_PRIMARY"])))
        self._table.setItem(row, 5, col_statut)

        self._downloads[identifiant] = {
            "fichier": fichier,
            "statut": statut,
            "progression": progression,
            "vitesse": vitesse,
            "taille": taille,
            "taille_bytes": taille_bytes,
            "vitesse_bytes": vitesse_bytes,
            "bytes_transfered": int(progression * taille_bytes / 100) if taille_bytes > 0 else 0,
            "prev_time": 0.0,
            "user": user,
            "date_debut": datetime.now().isoformat(timespec="seconds"),
        }

        self._update_stats()
        self._update_global_progress()

    def remove_download(self, identifiant: str) -> bool:
        """Supprime un téléchargement du tableau. Retourne True si trouvé."""
        data = self._downloads.pop(identifiant, None)
        if data is None:
            return False
        row = self._find_row(identifiant)
        if row >= 0:
            self._table.removeRow(row)

        self._update_stats()
        self._update_global_progress()
        return True

    def update_progression(
        self,
        identifiant: str,
        progression: float,
        bytes_transfered: int = 0,
    ) -> None:
        """Met à jour la progression d'un téléchargement."""
        data = self._downloads.get(identifiant)
        if data is None:
            return

        # Vitesse : calcul par différence de bytes_transfered
        now = time.time()
        prev_bytes = data.get("bytes_transfered", 0)
        prev_time = data.get("prev_time", 0.0)

        vitesse_bps = 0.0
        if bytes_transfered > 0 and prev_bytes > 0 and prev_time > 0:
            dt = now - prev_time
            if dt > 0:
                vitesse_bps = (bytes_transfered - prev_bytes) / dt
                data["vitesse_bytes"] = vitesse_bps
                data["vitesse"] = _format_vitesse(vitesse_bps)
                row = self._find_row(identifiant)
                if row >= 0:
                    item_vitesse = self._table.item(row, 4)
                    if item_vitesse:
                        item_vitesse.setText(data["vitesse"])

        data["progression"] = progression
        data["bytes_transfered"] = bytes_transfered
        data["prev_time"] = now

        # Texte progression avec ETA
        restant = data.get("taille_bytes", 0) - bytes_transfered
        eta_str = ""
        if vitesse_bps > 0 and restant > 0:
            eta_sec = restant / vitesse_bps
            eta_str = f" ({_format_temps_restant(eta_sec)})"
        prog_texte = f"{progression:.0f}%{eta_str}"

        row = self._find_row(identifiant)
        if row >= 0:
            item = self._table.item(row, 3)
            if item:
                item.setText(prog_texte)
                item.setData(_SortRole, progression)

        self._update_global_progress()

    def _save_to_history(self, identifiant: str, statut: str) -> None:
        """Sauvegarde un téléchargement terminé/échoué dans l'historique persistant."""
        data = self._downloads.get(identifiant)
        if not data:
            return
        telechargement_history.add_to_history(
            identifiant=identifiant,
            fichier=data.get("fichier", ""),
            utilisateur=data.get("user", ""),
            taille=data.get("taille", ""),
            taille_bytes=data.get("taille_bytes", 0),
            statut=statut,
            vitesse_moyenne=data.get("vitesse", ""),
            vitesse_bytes=float(data.get("vitesse_bytes", 0.0)),
            date_debut=data.get("date_debut"),
        )

    def change_statut(self, identifiant: str, nouveau_statut: str) -> None:
        """Change le statut d'un téléchargement."""
        data = self._downloads.get(identifiant)
        if data is None:
            return

        ancien_statut = data["statut"]
        data["statut"] = nouveau_statut

        # Sauvegarder dans l'historique persistant si terminal
        if nouveau_statut in ("termine", "echoue") and ancien_statut not in ("termine", "echoue"):
            self._save_to_history(identifiant, nouveau_statut)

        row = self._find_row(identifiant)
        if row < 0:
            return

        if nouveau_statut == "termine":
            data["progression"] = 100.0
            # Mettre à jour la colonne Progression (index 3)
            item_prog = self._table.item(row, 3)
            if item_prog:
                item_prog.setText("100%")
                item_prog.setData(_SortRole, 100.0)

        # Mettre à jour colonne Statut (index 5)
        item = self._table.item(row, 5)
        if item:
            texte = f"{_STATUT_ICONES.get(nouveau_statut, '')} {_STATUT_LIBELLES.get(nouveau_statut, nouveau_statut)}"
            item.setText(texte)
            couleur = _STATUT_COULEURS.get(nouveau_statut, COLORS["TEXT_PRIMARY"])
            item.setForeground(QColor(couleur))

        self._update_stats()
        self._update_global_progress()

    # ── Méthodes internes ─────────────────────────────────────────────────

    def _update_stats(self) -> None:
        """Met à jour les badges de statistiques."""
        counts: dict[str, int] = {"en_cours": 0, "attente": 0, "termine": 0, "echoue": 0}
        for d in self._downloads.values():
            s = d["statut"]
            if s in counts:
                counts[s] += 1

        for badge_name, count in [
            ("en_cours", counts["en_cours"]),
            ("en_attente", counts["attente"]),
            ("terminés", counts["termine"]),
            ("échoués", counts["echoue"]),
        ]:
            label = self.findChild(QLabel, f"badgeValue_{badge_name}")
            if label:
                label.setText(str(count))

    def _update_global_progress(self) -> None:
        """Met à jour la barre de progression globale et la vitesse cumulée."""
        total_bytes = 0
        total_recus = 0
        vitesse_cumul = 0.0
        actifs = 0

        for d in self._downloads.values():
            tb = d.get("taille_bytes", 0)
            br = d.get("bytes_transfered", 0)
            s = d["statut"]

            if tb > 0:
                total_bytes += tb
                if s == "en_cours":
                    total_recus += br
                    actifs += 1
                    vitesse_cumul += d.get("vitesse_bytes", 0.0)
                elif s == "termine":
                    total_recus += tb  # considéré 100% reçu
            elif s == "en_cours":
                actifs += 1

        # Barre de progression
        if total_bytes > 0:
            pct = int(total_recus * 100 / total_bytes)
            self._global_progress.setValue(min(pct, 100))
        else:
            self._global_progress.setValue(0)

        # Labels taille
        if total_bytes > 0:
            pct_display = int(total_recus * 100 / total_bytes)
            taille_texte = (
                f"{_format_taille(total_recus)} / {_format_taille(total_bytes)} ({pct_display}%)"
            )
        else:
            taille_texte = "—"
        self._lbl_taille.setText(taille_texte)

        # Vitesse cumulative
        if actifs > 0 and vitesse_cumul > 0:
            self._lbl_vitesse.setText(f"⚡ {_format_vitesse(vitesse_cumul)}")
        else:
            self._lbl_vitesse.setText("")

    def _on_filtre_changed(self, texte: str) -> None:
        """Change le filtre d'affichage."""
        mapping = {
            "tous": "tous",
            "en cours": "en_cours",
            "en attente": "attente",
            "terminé": "termine",
            "échoué": "echoue",
        }
        statut = mapping.get(texte.lower(), "tous")
        self._apply_filter(statut)

    def _on_resume_all(self) -> None:
        """Reprend tous les téléchargements en pause/attente."""
        for identifiant in list(self._downloads.keys()):
            data = self._downloads.get(identifiant)
            if data and data["statut"] == "attente":
                self._service.resume_transfer(data["user"], identifiant)
                self.change_statut(identifiant, "en_cours")
            elif data and data["statut"] == "echoue":
                self._service.resume_transfer(data["user"], identifiant)
                self.change_statut(identifiant, "attente")

    def _on_pause_all(self) -> None:
        """Met en pause tous les téléchargements en cours."""
        for identifiant in list(self._downloads.keys()):
            data = self._downloads.get(identifiant)
            if data and data["statut"] == "en_cours":
                self._service.pause_transfer(data["user"], identifiant)
                self.change_statut(identifiant, "attente")

    def _on_cancel_all(self) -> None:
        """Annule tous les téléchargements actifs/attente."""
        for identifiant in list(self._downloads.keys()):
            data = self._downloads.get(identifiant)
            if data and data["statut"] in ("en_cours", "attente"):
                self._service.abort_transfer(data["user"], identifiant)
                self.change_statut(identifiant, "echoue")

    def _on_ouvrir_dossier(self) -> None:
        """Ouvre le dossier de téléchargement dans l'explorateur."""
        from src.services.app_config import app_config

        dossier = app_config.get("telechargement.dossier_destination", "")
        if not dossier:
            dossier = str(Path.home() / "Downloads")
        if os.path.exists(dossier):
            os.startfile(dossier)

    def _on_show_history(self) -> None:
        """Ouvre le dialogue d'historique des téléchargements."""
        dialog = HistoryDialog(self)
        dialog.exec()

    def _on_clear_termines(self) -> None:
        """Supprime tous les téléchargements terminés du tableau."""
        a_supprimer = [
            identifiant
            for identifiant, data in self._downloads.items()
            if data["statut"] in ("termine", "echoue")
        ]
        for identifiant in a_supprimer:
            self.remove_download(identifiant)

    def _on_context_menu(self, pos: Any) -> None:
        """Menu contextuel sur un téléchargement avec actions individuelles."""
        item = self._table.itemAt(pos)
        if item is None:
            return
        row = item.row()

        identifiant = self._get_identifiant_at(row)
        if identifiant is None:
            return

        data = self._downloads.get(identifiant)
        if data is None:
            return

        context = QMenu(self)
        statut = data["statut"]

        # Actions selon le statut actuel
        if statut == "en_cours":
            action_pause = QAction("⏸ Pause", self)
            action_pause.triggered.connect(
                lambda idf=identifiant, u=data["user"]: (
                    self._service.pause_transfer(u, idf),
                    self.change_statut(idf, "attente"),
                )
            )
            context.addAction(action_pause)
        elif statut == "attente":
            action_resume = QAction("▶ Reprendre", self)
            action_resume.triggered.connect(
                lambda idf=identifiant, u=data["user"]: (
                    self._service.resume_transfer(u, idf),
                    self.change_statut(idf, "en_cours"),
                )
            )
            context.addAction(action_resume)
        elif statut == "echoue":
            action_retry = QAction("⟳ Réessayer", self)
            action_retry.triggered.connect(
                lambda idf=identifiant, u=data["user"]: (
                    self._service.resume_transfer(u, idf),
                    self.change_statut(idf, "attente"),
                )
            )
            context.addAction(action_retry)
            action_reset = QAction("📤 Relancer", self)
            action_reset.triggered.connect(
                lambda idf=identifiant, u=data["user"]: (
                    self._service.resume_transfer(u, idf),
                    self.change_statut(idf, "en_cours"),
                )
            )
            context.addAction(action_reset)

        action_cancel = QAction("✕ Annuler", self)
        action_cancel.triggered.connect(lambda: self._on_annuler(identifiant))
        context.addAction(action_cancel)

        context.addSeparator()

        action_copy = QAction("📋 Copier le fichier", self)
        action_copy.triggered.connect(lambda: self._on_copier_nom(identifiant))
        context.addAction(action_copy)

        context.exec(self._table.viewport().mapToGlobal(pos))

    def _on_annuler(self, identifiant: str) -> None:
        """Annule un téléchargement via Soulseek + UI."""
        data = self._downloads.get(identifiant)
        if data:
            self._service.abort_transfer(data["user"], identifiant)
            self.change_statut(identifiant, "echoue")

    def _on_copier_nom(self, identifiant: str) -> None:
        """Copie le nom du fichier dans le presse-papier."""
        data = self._downloads.get(identifiant)
        if data:
            clipboard = QGuiApplication.clipboard()
            if clipboard:
                clipboard.setText(data["fichier"])

    # ── Propriétés ────────────────────────────────────────────────────────

    def download_count(self) -> int:
        """Nombre total de téléchargements."""
        return len(self._downloads)
