"""Bot Bibliothèque — Gestionnaire de fichiers partagés.

Tableau de bord pour explorer, filtrer et gérer sa bibliothèque
locale partagée sur le réseau Soulseek.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

from PySide6.QtCore import QEvent, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.theme_fragments.colors import COLORS
from src.services import app_config
from src.services.event_bus import EventBus
from src.services.library_db import get_library_db
from src.services.library_scanner import LibraryScanner
from src.services.soulseek_client import soulseek_service

# ── Constantes ──────────────────────────────────────────────────────
_STAT_COLORS = {
    "dossiers": COLORS["ACCENT"],  # Violet
    "fichiers": COLORS["STAT_FILES"],  # Vert
    "audio": COLORS["STAT_AUDIO"],  # Jaune
}

_PLACEHOLDER_SEARCH = "🔍 Rechercher dans la bibliothèque…"

# Valeurs initiales avant le premier chargement depuis la base
_INIT_STATS = {
    "dossiers": 0,
    "fichiers": 0,
    "audio": 0,
}

# Cache des statistiques entre les cycles de vie (persiste même si le
# widget est recréé — évite un écran vide avant le premier chargement DB)
_STATS_CACHE: dict[str, int] | None = None

# Cache du dernier scan effectué — permet d'afficher l'historique même
# après une reconstruction du widget.
_LAST_SCAN: dict[str, int | float | str] | None = None


# ── Sous-composants ─────────────────────────────────────────────────


class _StatCard(QFrame):
    """Badge de statistique compact (ex: '📁 42 Dossiers')."""

    def __init__(self, value: str | int, label: str, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statCardBadge")
        self.setStyleSheet(f"#statCardBadge {{  background: {COLORS['BG_BTN']}; border-radius: 4px;}}")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 10, 3)
        layout.setSpacing(4)

        self._value_lbl = QLabel(str(value))
        self._value_lbl.setStyleSheet(
            f"color: {COLORS['TEXT_PRIMARY']}; font-size: 13px; font-weight: 600;"
            " background: transparent; border: none;"
        )
        layout.addWidget(self._value_lbl)

        label_lbl = QLabel(label)
        label_lbl.setObjectName("statCardLabel")
        label_lbl.setStyleSheet(
            f"color: {COLORS['TEXT_SECONDARY']}; font-size: 11px; background: transparent; border: none;"
        )
        layout.addWidget(label_lbl)

    def set_value(self, value: str | int) -> None:
        """Met à jour la valeur affichée sur le badge."""
        self._value_lbl.setText(str(value))


class _Toolbar(QFrame):
    """Barre d'outils : champ recherche + barre de progression + bouton Re-scanner."""

    search_requested = Signal(str)  # texte de recherche
    rescan_requested = Signal()  # clic sur Re-scanner

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("bibliothequeToolbar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._search_input = QLineEdit()
        self._search_input.setObjectName("bibliothequeSearch")
        self._search_input.setPlaceholderText(_PLACEHOLDER_SEARCH)
        self._search_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self._search_input)

        # Barre de progression (cachée par défaut)
        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("bibliothequeProgress")
        self._progress_bar.setValue(0)
        self._progress_bar.hide()
        layout.addWidget(self._progress_bar)

        self._rescan_btn = QPushButton("🔄 Re-scanner")
        self._rescan_btn.setObjectName("bibliothequeRescan")
        layout.addWidget(self._rescan_btn)

        # Connexions internes
        self._search_input.textChanged.connect(self._on_search_changed)
        self._rescan_btn.clicked.connect(self._on_rescan_clicked)

    # ── API publique ────────────────────────────────────────────────

    def set_search_enabled(self, enabled: bool) -> None:
        self._search_input.setEnabled(enabled)

    def set_rescan_enabled(self, enabled: bool) -> None:
        self._rescan_btn.setEnabled(enabled)

    def set_rescan_text(self, text: str) -> None:
        self._rescan_btn.setText(text)

    def set_progress_visible(self, visible: bool) -> None:
        """Affiche ou masque la barre de progression."""
        self._progress_bar.setVisible(visible)
        # Cacher le search input pendant le scan pour libérer de l'espace
        self._search_input.setVisible(not visible)

    def set_progress_range(self, maximum: int) -> None:
        """Définit le maximum de la barre de progression."""
        self._progress_bar.setRange(0, maximum)

    def set_progress_value(self, value: int) -> None:
        """Met à jour la valeur courante de la barre de progression."""
        self._progress_bar.setValue(value)

    def set_progress_format(self, fmt: str) -> None:
        """Définit le format d'affichage (ex: '%v / %m fichiers')."""
        self._progress_bar.setFormat(fmt)

    def clear_search(self) -> None:
        self._search_input.clear()

    @property
    def search_text(self) -> str:
        return self._search_input.text()

    # ── Slots internes ──────────────────────────────────────────────

    def _on_search_changed(self, text: str) -> None:
        self.search_requested.emit(text)

    def _on_rescan_clicked(self) -> None:
        self.rescan_requested.emit()


# ── FileInfoPopup ──────────────────────────────────────────────────


class _FileInfoPopup(QDialog):
    """Fenêtre modale affichant les métadonnées complètes d'un fichier.

    Affiche les infos générales (nom, taille, dossier, modification)
    et les métadonnées audio (artiste, album, titre, piste, année,
    bitrate, durée) si disponibles.
    """

    def __init__(self, file_data: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._file = file_data
        self.setWindowTitle(f"👁️ Informations — {file_data.get('name', '')}")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setObjectName("fileInfoPopup")
        self._build_ui()

    def _build_ui(self) -> None:
        """Construit l'interface de la popup."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # Titre
        title = QLabel(f"👁️ {self._file.get('name', '')}")
        title.setObjectName("fileInfoTitle")
        layout.addWidget(title)

        # Séparateur
        sep = QLabel("─" * 42)
        sep.setObjectName("fileInfoSep")
        layout.addWidget(sep)

        # Infos générales
        info_rows = [
            ("📄 Nom", self._file.get("name", "")),
            ("📏 Taille", self._format_size(self._file.get("size_bytes", 0))),
            ("📁 Dossier", self._file.get("folder_label") or self._file.get("folder_path", "")),
            ("📅 Modifié", self._format_date(self._file.get("modified_at", ""))),
        ]
        for label, value in info_rows:
            layout.addWidget(self._make_info_row(label, value))

        # Section Audio (si données disponibles)
        artist = self._file.get("artist")
        album = self._file.get("album")
        title_meta = self._file.get("title")
        if artist or album or title_meta:
            sep2 = QLabel("─── Audio ───────────────────────────────")
            sep2.setObjectName("fileInfoSepAudio")
            layout.addWidget(sep2)

            audio_rows = [
                ("🎵 Artiste", artist or "—"),
                ("💿 Album", album or "—"),
                ("🎵 Titre", title_meta or "—"),
                ("#️⃣ Piste", str(self._file.get("track", "")) if self._file.get("track") else "—"),
                ("📅 Année", str(self._file.get("year", "")) if self._file.get("year") else "—"),
                ("🎧 Bitrate", f"{self._file['bitrate']} kbps" if self._file.get("bitrate") else "—"),
                (
                    "⏱ Durée",
                    self._format_duration(self._file.get("duration", 0)) if self._file.get("duration") else "—",
                ),
            ]
            for label, value in audio_rows:
                layout.addWidget(self._make_info_row(label, value))

        # Séparateur
        sep3 = QLabel("─" * 42)
        sep3.setObjectName("fileInfoSep")
        layout.addWidget(sep3)

        # Boutons d'action
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        lire_btn = QPushButton("▶️ Lire")
        lire_btn.setObjectName("infoLireBtn")
        lire_btn.clicked.connect(self._on_lire)
        btn_layout.addWidget(lire_btn)

        suppr_btn = QPushButton("🗑️ Supprimer")
        suppr_btn.setObjectName("infoSupprBtn")
        suppr_btn.clicked.connect(self._on_supprimer)
        btn_layout.addWidget(suppr_btn)

        btn_layout.addStretch(1)

        fermer_btn = QPushButton("Fermer")
        fermer_btn.setObjectName("infoFermerBtn")
        fermer_btn.clicked.connect(self.accept)
        btn_layout.addWidget(fermer_btn)

        layout.addLayout(btn_layout)

    def _make_info_row(self, label: str, value: str) -> QWidget:
        """Crée une ligne d'information label + valeur."""
        row = QWidget()
        row.setObjectName("fileInfoRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 2, 0, 2)
        row_layout.setSpacing(8)

        lbl = QLabel(label)
        lbl.setObjectName("fileInfoLabel")
        lbl.setFixedWidth(80)
        row_layout.addWidget(lbl)

        val = QLabel(str(value) if value else "—")
        val.setObjectName("fileInfoValue")
        val.setWordWrap(True)
        row_layout.addWidget(val, stretch=1)

        return row

    # ── Slots ───────────────────────────────────────────────────────

    def _on_lire(self) -> None:
        """Ouvre le fichier avec l'application système par défaut."""
        path = self._file.get("path", "")
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        self.accept()

    def _on_supprimer(self) -> None:
        """Ouvre la confirmation de suppression."""
        self.accept()
        parent = self.parent()
        if parent and hasattr(parent, "_on_delete_file"):
            parent._on_delete_file(self._file)

    @staticmethod
    def _format_size(bytes_val: int) -> str:
        """Formate une taille en octets en unité lisible."""
        if bytes_val >= 1_073_741_824:
            return f"{bytes_val / 1_073_741_824:.1f} Go"
        if bytes_val >= 1_048_576:
            return f"{bytes_val / 1_048_576:.1f} Mo"
        if bytes_val >= 1_024:
            return f"{bytes_val / 1_024:.1f} Ko"
        return f"{bytes_val} o"

    @staticmethod
    def _format_duration(seconds: int) -> str:
        """Formate une durée en secondes en mm:ss."""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"

    @staticmethod
    def _format_date(date_str: str) -> str:
        """Formate une date ISO en format lisible (jj/mm/aaaa à hh:mm)."""
        if not date_str:
            return "—"
        try:
            dt = datetime.fromisoformat(date_str)
            return dt.strftime("%d/%m/%Y à %H:%M")
        except (ValueError, TypeError):
            return date_str


# ── Bot principal ──────────────────────────────────────────────────


class BotBibliotheque(QFrame):
    """Tableau de bord de gestion des fichiers partagés.

    Signaux
    -------
    page_changed(bot_name: str) : émis pour naviguer vers un autre bot.
    """

    page_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("botBibliotheque")

        self._actif = False
        self._loop_timer: QTimer = QTimer(self)
        self._loop_timer.setInterval(300000)  # 5 min entre chaque tick
        self._loop_timer.timeout.connect(self._on_loop_tick)
        self._stats: dict[str, int] = dict(_INIT_STATS)
        self._current_folder: str | None = None
        self._current_folder_id: int | None = None
        self._current_folder_label: str | None = None
        self._library_db = None  # initialisé paresseusement via _get_db()
        self._tree_root: QTreeWidgetItem | None = None

        # État de la recherche
        self._search_text: str = ""
        self._search_active: bool = False
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)  # debounce 300ms
        self._search_timer.timeout.connect(self._do_search)

        # État du tri
        self._sort_column: str = "name"
        self._sort_order: str = "ASC"

        # Scan threadé
        self._scanner: LibraryScanner | None = None

        # État de connexion Soulseek
        self._soulseek_connected: bool = False

        self._build_ui()

        # Vérifier la connexion Soulseek et synchroniser les dossiers
        self._update_connection_state()

        # S'abonner aux changements de connexion Soulseek
        if soulseek_service is not None:
            soulseek_service.connection_changed.connect(self._update_connection_state)

        # Charger les données après construction de l'UI
        # Utiliser le cache si disponible pour éviter un écran vide
        if _STATS_CACHE is not None and self._soulseek_connected:
            self._stats = dict(_STATS_CACHE)
            for key, card in self._stat_cards.items():
                card.set_value(self._stats.get(key, 0))

        if self._soulseek_connected:
            # Restaurer les infos du dernier scan dans la barre de statut
            if _LAST_SCAN is not None:
                self._update_status()

            # Auto-scan au démarrage si configuré
            if app_config.get("general.scan_on_start", True):
                # Décaler le scan pour laisser l'UI finir de se construire
                self._auto_scan_timer = QTimer(self)
                self._auto_scan_timer.setSingleShot(True)
                self._auto_scan_timer.setInterval(1500)
                self._auto_scan_timer.timeout.connect(self._on_rescan)
                self._auto_scan_timer.start()

    # ── Construction UI ──────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Construit l'interface complète."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. En-tête
        self._header = QLabel("📂 Bibliothèque — Mes fichiers partagés")
        self._header.setObjectName("bibliothequeHeader")
        layout.addWidget(self._header)

        # 2. Barre de stats
        self._build_stats_bar(layout)

        # 3. Toolbar (recherche + re-scanner)
        self._toolbar = _Toolbar()
        self._toolbar.rescan_requested.connect(self._on_rescan)
        self._toolbar.search_requested.connect(self._on_search_requested)
        layout.addWidget(self._toolbar)

        # 4. Vue principale (placeholder pour arbre + tableau)
        self._build_main_view(layout)

        # 5. Barre de statut
        self._status_lbl = QLabel(self._build_status_text())
        self._status_lbl.setObjectName("bibliothequeStatus")
        layout.addWidget(self._status_lbl)

    def _build_stats_bar(self, parent_layout: QVBoxLayout) -> None:
        """Construit la rangée de cartes statistiques."""
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        stats_row.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._stat_cards: dict[str, _StatCard] = {}
        configs = [
            ("dossiers", "📁 Dossiers", _STAT_COLORS["dossiers"]),
            ("fichiers", "📄 Fichiers", _STAT_COLORS["fichiers"]),
            ("audio", "🎵 Audio", _STAT_COLORS["audio"]),
        ]

        for key, label, color in configs:
            card = _StatCard(self._stats[key], label, color)
            self._stat_cards[key] = card
            stats_row.addWidget(card)

        stats_row.addStretch(1)
        parent_layout.addLayout(stats_row)

    def _build_main_view(self, parent_layout: QVBoxLayout) -> None:
        """Construit la vue principale : stacked widget avec écran déconnecté + splitter."""
        self._main_stack = QStackedWidget()

        # ── Page 0 : Écran déconnecté ─────────────────────────────
        self._disconnected_page = QWidget()
        disconnected_layout = QVBoxLayout(self._disconnected_page)
        disconnected_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        disconnected_layout.setSpacing(16)

        lock_lbl = QLabel("🔒")
        lock_lbl.setObjectName("lockIcon")
        lock_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        disconnected_layout.addWidget(lock_lbl)

        msg_lbl = QLabel("Connecte-toi à Soulseek pour accéder à ta bibliothèque.")
        msg_lbl.setObjectName("lockMessage")
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        disconnected_layout.addWidget(msg_lbl)

        self._connect_btn = QPushButton("🔌 Connexion")
        self._connect_btn.setObjectName("connectSoulseekBtn")
        # La connexion réelle est gérée ailleurs ; ce bouton émet un signal
        # pour naviguer vers la page de connexion
        self._connect_btn.clicked.connect(lambda: self.page_changed.emit("Connexion"))
        disconnected_layout.addWidget(self._connect_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self._main_stack.addWidget(self._disconnected_page)  # index 0

        # ── Page 1 : Splitter arbre + tableau ─────────────────────
        self._main_container = QWidget()
        container_layout = QVBoxLayout(self._main_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setObjectName("bibliothequeSplitter")

        # Panneau gauche — arborescence des dossiers
        self._tree_widget = QTreeWidget()
        self._tree_widget.setObjectName("folderTree")
        self._tree_widget.setHeaderHidden(True)
        self._tree_widget.setMinimumWidth(200)
        self._tree_widget.itemClicked.connect(self._on_tree_item_clicked)

        # Panneau droit — tableau des fichiers
        self._table_widget = QTableWidget(0, 6)
        self._table_widget.setObjectName("fileTable")
        self._table_widget.setHorizontalHeaderLabels(
            ["📄 Nom", "📏 Taille", "🎵 Durée", "🎧 Bitrate", "📁 Dossier", "📅 Modifié"]
        )
        self._table_widget.setAlternatingRowColors(True)
        self._table_widget.setSelectionBehavior(self._table_widget.SelectionBehavior.SelectRows)
        self._table_widget.setSelectionMode(self._table_widget.SelectionMode.SingleSelection)
        self._table_widget.setEditTriggers(self._table_widget.EditTrigger.NoEditTriggers)
        # Menu contextuel
        self._table_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table_widget.customContextMenuRequested.connect(self._on_context_menu)

        # Tri par colonnes (clic sur en-tête)
        self._table_widget.horizontalHeader().sectionClicked.connect(self._on_header_clicked)

        self._splitter.addWidget(self._tree_widget)
        self._splitter.addWidget(self._table_widget)
        self._splitter.setSizes([280, 600])

        container_layout.addWidget(self._splitter)

        self._main_stack.addWidget(self._main_container)  # index 1

        parent_layout.addWidget(self._main_stack, stretch=1)

    # ── Interrupteur ────────────────────────────────────────────────

    def demarrer(self) -> None:
        """Active l'interrupteur → démarre la boucle Bibliothèque."""
        if self._actif:
            return
        self._actif = True
        self._loop_timer.start()
        self._on_loop_tick()
        logger.info("BotBibliotheque démarré (cycle 5 min)")

    def arreter(self) -> None:
        """Désactive l'interrupteur → suspend la boucle Bibliothèque."""
        if not self._actif:
            return
        self._actif = False
        self._loop_timer.stop()
        logger.info("BotBibliotheque arrêté")

    def _on_loop_tick(self) -> None:
        """Tick périodique : rafraîchit les statistiques DB."""
        if not self._actif:
            return
        self._refresh_stats()
        logger.debug("BotBibliotheque tick — %d fichiers", self._stats.get("fichiers", 0))

    # ── API publique ────────────────────────────────────────────────

    def _update_connection_state(self) -> None:
        """Vérifie l'état de connexion Soulseek et bascule la vue."""
        connected = soulseek_service is not None and soulseek_service.is_connected
        # Court-circuit : éviter un refresh inutile si l'état n'a pas changé
        if self._soulseek_connected == connected:
            return

        self._soulseek_connected = connected

        if connected:
            self._main_stack.setCurrentIndex(1)
            self.refresh()
        else:
            self._main_stack.setCurrentIndex(0)

    def showEvent(self, event: QEvent) -> None:
        """Rafraîchit l'état de connexion quand la page devient visible."""
        # pyrefly: ignore [bad-argument-type]
        super().showEvent(event)
        self._update_connection_state()

    def refresh(self) -> None:
        """Recharge l'arborescence et les statistiques depuis la base."""
        self._load_folder_tree()
        self._refresh_stats()
        self._update_status()

    def update_stats(self, stats: dict[str, int]) -> None:
        """Met à jour les cartes de statistiques (callback externe)."""
        self._stats = dict(stats)
        for key, card in self._stat_cards.items():
            card.set_value(self._stats.get(key, 0))
        self._update_status()

    def set_status(self, text: str) -> None:
        """Affiche un message personnalisé dans la barre de statut."""
        self._status_lbl.setText(text)

    # ── Accès base de données ───────────────────────────────────────

    def _get_db(self):
        """Retourne le singleton LibraryDB (initialisation paresseuse)."""
        if self._library_db is None:
            self._library_db = get_library_db()
        return self._library_db

    # ── Construction arborescence ────────────────────────────────────

    def _load_folder_tree(self) -> None:
        """Construit l'arborescence des dossiers dans le QTreeWidget.

        Structure :
        - 📂 Racine
          |- dossier 1 (label)
          |- dossier 2 (label)

        La racine est sélectionnée par défaut au premier chargement.
        """
        self._tree_widget.clear()
        self._tree_root = QTreeWidgetItem(["📂 Racine"])
        self._tree_root.setData(0, Qt.ItemDataRole.UserRole, None)  # pas de folder_id
        self._tree_widget.addTopLevelItem(self._tree_root)

        try:
            db = self._get_db()
            folders = db.get_folders()
        except Exception:
            folders = []

        for folder in folders:
            label = folder.get("label") or folder.get("path", "")
            item = QTreeWidgetItem([f"📁 {label}"])
            item.setData(0, Qt.ItemDataRole.UserRole, folder["id"])
            self._tree_root.addChild(item)

        self._tree_root.setExpanded(True)
        self._tree_widget.setCurrentItem(self._tree_root)

    # ── Clic sur un dossier dans l'arbre ────────────────────────────

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        """Charge les fichiers du dossier sélectionné dans le tableau."""
        folder_id: int | None = item.data(0, Qt.ItemDataRole.UserRole)

        if folder_id is None:
            # Racine cliquée — vue globale
            self._current_folder = None
            self._current_folder_id = None
            self._current_folder_label = None
        else:
            label = item.text(0).removeprefix("📁 ")
            self._current_folder = label
            self._current_folder_id = folder_id
            self._current_folder_label = label

        self._load_files_for_folder()
        self._update_status()

    def _load_files_for_folder(self) -> None:
        """Charge les fichiers du dossier courant dans le QTableWidget.

        Si ``self._current_folder_id`` est ``None``, on affiche un message
        invitant à sélectionner un dossier.
        Utilise la recherche et le tri actifs si présents.
        """
        self._table_widget.setRowCount(0)
        self._table_widget.clearSpans()

        if self._current_folder_id is None and not self._search_active:
            self._table_widget.setRowCount(1)
            empty_lbl = QLabel("Sélectionne un dossier dans l'arborescence pour voir ses fichiers.")
            empty_lbl.setObjectName("bibliothequeEmpty")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table_widget.setCellWidget(0, 0, empty_lbl)
            self._table_widget.setSpan(0, 0, 1, 6)
            return

        try:
            db = self._get_db()
            # Si recherche active sur la racine, parcourir tous les dossiers
            folder_id = self._current_folder_id
            search = self._search_text if self._search_active else None
            sort_by = self._sort_column
            order = self._sort_order
            files = db.get_files(
                folder_id=folder_id,
                search=search,
                sort_by=sort_by,
                order=order,
            )
        except Exception:
            files = []

        self._table_widget.setRowCount(len(files))
        for row, f in enumerate(files):
            name_item = QTableWidgetItem(f.get("name", ""))
            # Stocker les données complètes du fichier pour le menu contextuel
            name_item.setData(Qt.ItemDataRole.UserRole, f)
            self._table_widget.setItem(row, 0, name_item)

            size_bytes = f.get("size_bytes", 0) or 0
            self._table_widget.setItem(row, 1, QTableWidgetItem(self._format_size(size_bytes)))

            duration = f.get("duration")
            self._table_widget.setItem(row, 2, QTableWidgetItem(self._format_duration(duration) if duration else ""))

            bitrate = f.get("bitrate")
            self._table_widget.setItem(row, 3, QTableWidgetItem(f"{bitrate} kbps" if bitrate else ""))

            # Utiliser le folder_label du fichier ou le dossier courant
            file_folder = f.get("folder_label") or self._current_folder_label or ""
            self._table_widget.setItem(row, 4, QTableWidgetItem(file_folder))

            modified = f.get("modified_at", "")
            self._table_widget.setItem(row, 5, QTableWidgetItem(modified or ""))

        # Ajuster les largeurs
        self._table_widget.resizeColumnsToContents()
        self._table_widget.horizontalHeader().setStretchLastSection(True)

    # ── Recherche ────────────────────────────────────────────────────

    def _on_search_requested(self, text: str) -> None:
        """Déclenche la recherche avec debounce."""
        self._search_text = text
        self._search_active = bool(text.strip())
        self._search_timer.start()  # Redémarre le timer (300ms)

    def _do_search(self) -> None:
        """Exécute la recherche dans la base de données.

        - Si la racine est sélectionnée × recherche active → traverse tous les dossiers
        - Si un dossier est sélectionné × recherche active → filtre dans ce dossier
        - Si la recherche est vidée → retour à la vue normale du dossier
        """
        self._load_files_for_folder()
        self._update_status()

    def _on_header_clicked(self, section: int) -> None:
        """Gère le clic sur un en-tête de colonne pour le tri."""
        # Correspondance colonne → champ SQL
        column_map = {
            0: "name",
            1: "size_bytes",
            2: "duration",
            3: "bitrate",
            4: "name",  # Dossier → on trie par nom
            5: "modified_at",
        }
        col_name = column_map.get(section, "name")

        # Toggle asc/desc si même colonne
        if col_name == self._sort_column:
            self._sort_order = "DESC" if self._sort_order == "ASC" else "ASC"
        else:
            self._sort_column = col_name
            self._sort_order = "ASC"

        self._load_files_for_folder()

    # ── Méthodes privées ────────────────────────────────────────────

    def _sync_shared_folders(self) -> None:
        """Synchronise les dossiers partagés depuis app_config vers LibraryDB.

        Parcourt les clés ``partages.dossier_*_chemin`` dans la configuration
        et ajoute les dossiers non-vides à la base SQLite via ``add_folder()``
        s'ils n'y sont pas déjà enregistrés.
        """
        db = self._get_db()
        config = app_config.dictionary()
        existing = db.get_folders()
        existing_paths = {f["path"] for f in existing}
        pattern = re.compile(r"^partages\.dossier_\d+_chemin$")

        for key, path in config.items():
            if not pattern.match(key):
                continue
            if not path or not isinstance(path, str):
                continue
            path = path.strip()
            if not path:
                continue
            if path in existing_paths:
                continue
            if not Path(path).is_dir():
                logger.warning("Dossier partagé introuvable : %s", path)
                continue

            db.add_folder(path)
            existing_paths.add(path)
            logger.info("Dossier partagé synchronisé : %s", path)

    def _on_rescan(self) -> None:
        """Déclenche un re-scan threadé de la bibliothèque."""
        # Créer le scanner paresseusement
        if self._scanner is None:
            db = self._get_db()
            self._scanner = LibraryScanner(db=db, parent=self)
            self._scanner.scan_started.connect(self._on_scan_started)
            self._scanner.scan_progress.connect(self._on_scan_progress)
            self._scanner.scan_completed.connect(self._on_scan_completed)
            self._scanner.scan_error.connect(self._on_scan_error)

        if self._scanner.is_running:
            return

        # Synchroniser les dossiers configurés (app_config) vers la base SQLite
        self._sync_shared_folders()

        self._scanner.start_scan()

    def _refresh_stats(self) -> None:
        """Rafraîchit les statistiques depuis la base de données.

        Met à jour le module-level ``_STATS_CACHE`` pour que les
        prochaines instances puissent afficher des données immédiatement.
        """
        global _STATS_CACHE
        try:
            db = self._get_db()
            stats = db.get_stats()
            self._stats = {
                "dossiers": stats.get("folders", 0),
                "fichiers": stats.get("files", 0),
                "audio": stats.get("audio", 0),
            }
        except Exception:
            self._stats = {"dossiers": 0, "fichiers": 0, "audio": 0}

        # Mettre à jour le cache pour les prochaines instances
        _STATS_CACHE = dict(self._stats)

        for key, card in self._stat_cards.items():
            card.set_value(self._stats.get(key, 0))

    # ── Scan threadé ─────────────────────────────────────────────────

    def _on_scan_started(self) -> None:
        """Callback : le scan a commencé."""
        self._toolbar.set_rescan_text("⏳ Scan…")
        self._toolbar.set_rescan_enabled(False)
        self._toolbar.set_search_enabled(False)
        self._toolbar.set_progress_visible(True)
        self._toolbar.set_progress_value(0)
        self._toolbar.set_progress_format("%v / %m fichiers")
        self.set_status("⏳ Scan en cours…")
        EventBus().emit_event(
            severity="INFO",
            category="bibliotheque",
            title="Scan démarré",
            message="Scan de la bibliothèque démarré",
            source="BotBibliotheque",
        )

    def _on_scan_progress(self, processed: int, total: int) -> None:
        """Callback : mise à jour de la progression du scan."""
        if total > 0:
            self._toolbar.set_progress_range(total)
            self._toolbar.set_progress_value(processed)
        self.set_status(f"⏳ Scan en cours… {processed}/{total} fichiers")

    def _on_scan_completed(self, result) -> None:
        """Callback : le scan est terminé avec succès."""
        self._toolbar.set_rescan_text("🔄 Re-scanner")
        self._toolbar.set_rescan_enabled(True)
        self._toolbar.set_search_enabled(True)
        self._toolbar.set_progress_visible(False)

        # Rafraîchir les données
        self.refresh()

        # Mémoriser le résultat dans le cache global
        global _LAST_SCAN
        _LAST_SCAN = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "files_new": result.files_new,
            "files_removed": result.files_removed,
            "errors": len(result.errors),
            "duration_ms": getattr(result, "duration_ms", 0) or 0,
            "folders_scanned": getattr(result, "folders_scanned", 0),
            "files_found": getattr(result, "files_found", 0),
        }

        # Message de résumé
        dur_ms = _LAST_SCAN["duration_ms"]
        if dur_ms:
            # pyrefly: ignore [unsupported-operation]
            dur_msg = f" ⏱️ {dur_ms / 1000:.1f}s"
        else:
            dur_msg = ""
        self.set_status(
            f"✅ Scan terminé — "
            f"{result.files_new} nouveaux, "
            f"{result.files_removed} retirés, "
            f"{len(result.errors)} erreurs"
            f"{dur_msg}"
        )
        EventBus().emit_event(
            severity="INFO",
            category="bibliotheque",
            title="Scan terminé",
            message=(
                f"Scan terminé — {result.files_new} nouveaux, "
                f"{result.files_removed} retirés, "
                f"{len(result.errors)} erreurs{dur_msg}"
            ),
            source="BotBibliotheque",
        )

    def _on_scan_error(self, message: str) -> None:
        """Callback : le scan a échoué."""
        self._toolbar.set_rescan_text("🔄 Re-scanner")
        self._toolbar.set_rescan_enabled(True)
        self._toolbar.set_search_enabled(True)
        self._toolbar.set_progress_visible(False)
        self.set_status(f"⚠️ Erreur de scan : {message}")
        EventBus().emit_event(
            severity="ERROR",
            category="bibliotheque",
            title="Erreur de scan",
            message=f"Erreur lors du scan : {message}",
            source="BotBibliotheque",
        )

    # ── Menu contextuel ─────────────────────────────────────────────

    def _on_context_menu(self, pos) -> None:
        """Affiche le menu contextuel pour le fichier sous le curseur."""
        item = self._table_widget.itemAt(pos)
        if item is None:
            return
        row = item.row()
        # Récupérer les données du fichier (stockées dans UserRole de la colonne 0)
        # pyrefly: ignore [missing-attribute]
        file_data: dict | None = self._table_widget.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if file_data is None:
            return

        menu = QMenu(self)
        menu.setObjectName("bibliothequeMenu")

        voir_action = QAction("👁️ Voir les infos", self)
        voir_action.triggered.connect(lambda: self._on_view_info(file_data))
        menu.addAction(voir_action)

        lire_action = QAction("▶️ Lire le fichier", self)
        lire_action.triggered.connect(lambda: self._on_read_file(file_data))
        menu.addAction(lire_action)

        menu.addSeparator()

        suppr_action = QAction("🗑️ Supprimer", self)
        suppr_action.triggered.connect(lambda: self._on_delete_file(file_data))
        menu.addAction(suppr_action)

        menu.exec(self._table_widget.viewport().mapToGlobal(pos))

    def _on_view_info(self, file_data: dict) -> None:
        """Ouvre la popup d'informations détaillées du fichier."""
        popup = _FileInfoPopup(file_data, self)
        popup.exec()

    def _on_read_file(self, file_data: dict) -> None:
        """Ouvre le fichier avec l'application système par défaut."""
        path = file_data.get("path", "")
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _on_delete_file(self, file_data: dict) -> None:
        """Affiche la confirmation de suppression et exécute l'action.

        Propose trois options :
        - Retirer des partages (supprime l'index SQLite seulement)
        - Supprimer du disque (index + fichier du disque)
        - Annuler
        """
        name = file_data.get("name", "")
        msg = QMessageBox(self)
        msg.setObjectName("bibliothequeMsgBox")
        msg.setWindowTitle("🗑️ Supprimer")
        msg.setText(f"Que veux-tu faire de **{name}** ?")
        msg.setInformativeText(
            "Tu peux retirer le fichier des partages sans le toucher, ou le supprimer complètement du disque."
        )

        retirer_btn = msg.addButton("Retirer des partages", QMessageBox.ButtonRole.AcceptRole)
        supprimer_btn = msg.addButton("Supprimer du disque", QMessageBox.ButtonRole.DestructiveRole)
        annuler_btn = msg.addButton("Annuler", QMessageBox.ButtonRole.RejectRole)

        msg.setDefaultButton(annuler_btn)
        msg.exec()

        clicked = msg.clickedButton()

        if clicked == annuler_btn:
            return

        file_id = file_data.get("id")
        if file_id is None:
            return

        try:
            db = self._get_db()

            if clicked == supprimer_btn:
                # Supprimer du disque d'abord
                path = file_data.get("path", "")
                if path and os.path.isfile(path):
                    try:
                        os.remove(path)
                    except OSError:
                        self.set_status("⚠️ Impossible de supprimer le fichier du disque")
                        return

            # Retirer de l'index SQLite
            if db.remove_file(file_id):
                # Recharger les fichiers du dossier courant
                self._load_files_for_folder()
                self._refresh_stats()
                self._update_status()
                if clicked == retirer_btn:
                    self.set_status(f"✅ {name} retiré des partages")
                else:
                    self.set_status(f"✅ {name} supprimé du disque")
            else:
                self.set_status(f"⚠️ Fichier introuvable dans l'index")
        except Exception:
            self.set_status("⚠️ Erreur lors de la suppression")

    def _build_status_text(self) -> str:
        """Construit le texte de la barre de statut, incluant l'historique
        du dernier scan si disponible."""
        if self._stats["fichiers"] == 0 and self._current_folder is None and not self._search_active:
            # Aucun fichier → afficher l'historique du scan si disponible
            last = self._format_last_scan()
            if last:
                return f"Prêt — Dernier scan : {last}"
            return "Prêt"

        parts: list[str] = []
        if self._current_folder:
            parts.append(f"📂 {self._current_folder}")
        elif not self._search_active:
            parts.append("📂 Tous les dossiers")
        if self._search_active:
            parts.append(f"🔍 «{self._search_text}»")
            tri = {
                "name": "Nom",
                "size_bytes": "Taille",
                "duration": "Durée",
                "bitrate": "Bitrate",
                "modified_at": "Modifié",
            }
            col_label = tri.get(self._sort_column, self._sort_column)
            direction = "↑" if self._sort_order == "ASC" else "↓"
            parts.append(f"Tri : {col_label} {direction}")
        parts.append(f"{self._stats['fichiers']} fichiers")

        # Ajouter l'info du dernier scan si on n'est pas en train de naviguer
        last = self._format_last_scan()
        if last:
            parts.append(f"🕐 {last}")

        return " — ".join(parts)

    def _format_last_scan(self) -> str:
        """Formate les infos du dernier scan pour la barre de statut.

        Retourne une chaîne vide si aucun scan n'a encore été effectué.
        """
        last = _LAST_SCAN
        if last is None:
            return ""

        ts = last.get("timestamp", "")
        dur_ms = last.get("duration_ms", 0) or 0
        files_new = last.get("files_new", 0)
        files_removed = last.get("files_removed", 0)
        errors = last.get("errors", 0)

        # Formater la date
        date_str = ""
        if ts:
            try:
                dt = datetime.fromisoformat(str(ts))
                date_str = dt.strftime("%d/%m %H:%M")
            except (ValueError, TypeError):
                date_str = str(ts)

        # Construire le résumé
        parts = []
        if date_str:
            parts.append(date_str)
        parts.append(f"+{files_new}/−{files_removed}")
        if errors:
            parts.append(f"⚠️{errors}")
        if dur_ms:
            # pyrefly: ignore [unsupported-operation]
            parts.append(f"{dur_ms / 1000:.1f}s")

        return " ⋅ ".join(parts)

    def _update_status(self) -> None:
        """Rafraîchit la barre de statut avec les stats actuelles."""
        self._status_lbl.setText(self._build_status_text())

    @staticmethod
    def _format_size(bytes_val: int) -> str:
        """Formate une taille en octets en unité lisible."""
        if bytes_val >= 1_073_741_824:
            return f"{bytes_val / 1_073_741_824:.1f} Go"
        if bytes_val >= 1_048_576:
            return f"{bytes_val / 1_048_576:.1f} Mo"
        if bytes_val >= 1_024:
            return f"{bytes_val / 1_024:.1f} Ko"
        return f"{bytes_val} o"

    @staticmethod
    def _format_duration(seconds: int) -> str:
        """Formate une durée en secondes en mm:ss."""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"
