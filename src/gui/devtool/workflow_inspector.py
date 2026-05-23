"""
Workflow & Loop Inspector — Dashboard centralisé des bots, services et flux.

Surveille en temps réel l'état de tous les bots, services et boucles de l'application.
Complète le ServiceInspector (focus réseau) par une vue orientée workflow.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from typing import Any, Optional

from src.utils.log_action import log_action

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.services.event_bus import EventBus, SurveillanceEvent
from src.services.soulseek_client import soulseek_service

logger = logging.getLogger("[WORKFLOW]")

# ── Mapping source EventBus → (nom_affiché, icône) ─────────────────────────
_SOURCE_MAP: dict[str, tuple[str, str]] = {
    "connexion_manager": ("Connexion", "🔌"),
    "soulseek_service": ("Soulseek", "📡"),
    "soulseek_client": ("Soulseek", "📡"),
    "room_service": ("Room Service", "💬"),
    "boucle_rooms": ("Rooms", "💬"),
    "clients_actifs_service": ("Clients Actifs", "👥"),
    "event_bus": ("Event Bus", "📨"),
    "bot_accueil": ("Zeus", "🏠"),
    "bot_bibliotheque": ("Déméter", "📚"),
    "bot_optimiseur": ("Héphaistos", "⚡"),
    "bot_ordonnanceur": ("Poséidon", "🧹"),
    "bot_planificateur": ("Apollon", "📅"),
    "bot_recherche": ("Athéna", "🔍"),
    "bot_surveillance": ("Artémis", "👁️"),
    "bot_telechargement": ("Hadès", "⬇️"),
    "bot_wishlist": ("Aphrodite", "⭐"),
    "bot_aide": ("Dionysos", "❓"),
    "bot_assistant": ("Héra", "🤖"),
    "bot_clients_actifs": ("Arès", "👥"),
}

# ── Ordre d'affichage des entités dans la matrice ──────────────────────────
_MATRIX_ORDER: list[str] = [
    "Connexion", "Soulseek", "Room Service", "Rooms", "Clients Actifs", "Event Bus",
    "Zeus", "Déméter", "Héphaistos", "Poséidon", "Apollon",
    "Athéna", "Artémis", "Hadès", "Aphrodite", "Arès", "Héra", "Dionysos",
]


# ── Mapping noms grecs → clés de page internes ────────────────────────────
_GREEK_TO_PAGE_KEY: dict[str, str] = {
    "Zeus":       "Accueil",
    "Athéna":     "Recherche",
    "Hadès":      "telechargements",
    "Aphrodite":  "Wishlist",
    "Déméter":    "Bibliothèque",
    "Héphaistos": "Optimiseur",
    "Artémis":    "Surveillance",
    "Apollon":    "Planificateur",
    "Poséidon":   "Ordonnanceur",
    "Arès":       "Clients Actifs",
    "Héra":       "Assistant",
    "Dionysos":   "Aide",
}


class WorkflowInspector(QDockWidget):
    """Dashboard centralisé de surveillance des bots, services et flux."""

    # ── Mapping source EventBus → (nom_affiché, icône) ──
    _SOURCE_MAP = _SOURCE_MAP

    def __init__(self, main_window: QWidget, parent: Optional[QWidget] = None) -> None:
        super().__init__("Workflow & Loop Inspector", parent)
        self._main_window = main_window
        self.setObjectName("_workflow_inspector")

        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.setMinimumWidth(480)
        self.setFeatures(
            QDockWidget.DockWidgetClosable
            | QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
        )

        # ── État interne ──
        self._paused = False
        self._refresh_count = 0
        self._event_counters: dict[str, int] = defaultdict(int)
        self._matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._timeline_buffer: deque[str] = deque(maxlen=200)
        self._known_entities: list[str] = []  # noms des entités détectées

        # Cartes bots (clé = nom affiché)
        self._bot_cards: dict[str, QFrame] = {}
        # Références aux instances réelles
        self._bot_instances: dict[str, QObject] = {}

        # ── UI ──
        self._build_ui()
        self._connect_event_bus()
        self._apply_style()

        # Scan initial après un court délai (le temps que tout soit initialisé)
        QTimer.singleShot(500, self._scan_all_bots)
        # Initialiser la matrice vide après le scan
        QTimer.singleShot(600, self._update_matrix)

        # Debounce timer pour le rafraîchissement de la matrice
        self._matrix_debounce_timer = QTimer(self)
        self._matrix_debounce_timer.setSingleShot(True)
        self._matrix_debounce_timer.setInterval(1500)  # 1.5s max entre refreshes
        self._matrix_debounce_timer.timeout.connect(self._on_matrix_debounce_timeout)
        self._matrix_dirty = False

        # ── Timer périodique : rafraîchir les statuts toutes les 2s ──
        # Indépendant des événements EventBus : certains services (ex: SoulseekService)
        # n'émettent pas d'événement quand leur statut change, donc on les interroge
        # directement à intervalle régulier.
        self._status_timer = QTimer(self)
        self._status_timer.setInterval(2000)
        self._status_timer.timeout.connect(self._refresh_cards_status)
        self._status_timer.start()

    # ─────────────────────────────────────────────────────────────────────────
    #  Construction UI
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # ── Toolbar ──
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)

        self._btn_refresh = QPushButton("🔄 Refresh")
        self._btn_refresh.setToolTip("Rafraîchir manuellement l'état de tous les bots")
        self._btn_refresh.setStyleSheet(
            "background-color: #6c5ce7; font-weight: bold; color: #ffffff; "
            "padding: 3px 10px; font-size: 10px; border-radius: 3px;"
        )
        self._btn_refresh.clicked.connect(self._refresh_all)
        toolbar.addWidget(self._btn_refresh)

        self._btn_toggle_pause = QPushButton("⏸ Pause")
        self._btn_toggle_pause.setToolTip("Suspendre/Reprendre la mise à jour événementielle")
        self._btn_toggle_pause.setStyleSheet(
            "background-color: #45475a; color: #cdd6f4; "
            "padding: 3px 8px; font-size: 9px; border-radius: 3px;"
        )
        self._btn_toggle_pause.clicked.connect(self._toggle_paused)
        toolbar.addWidget(self._btn_toggle_pause)

        self._lbl_refresh_count = QLabel("#0")
        self._lbl_refresh_count.setStyleSheet("color: #6c7086; font-size: 9px; padding-left: 4px;")
        toolbar.addWidget(self._lbl_refresh_count)

        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        # ── Splitter vertical : Cartes | Matrice | Timeline ──
        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)
        splitter.setStyleSheet("QSplitter::handle { background: #313244; height: 2px; }")

        # ── Section 1 : Cartes bots (dans une QScrollArea) ──
        scroll_cartes = QScrollArea()
        scroll_cartes.setWidgetResizable(True)
        scroll_cartes.setFrameShape(QFrame.NoFrame)
        scroll_cartes.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._cartes_container = QWidget()
        self._cartes_layout = QVBoxLayout(self._cartes_container)
        self._cartes_layout.setContentsMargins(0, 0, 0, 0)
        self._cartes_layout.setSpacing(4)
        scroll_cartes.setWidget(self._cartes_container)
        splitter.addWidget(scroll_cartes)

        # ── Section 2 : Matrice des échanges ──
        matrix_container = QWidget()
        matrix_layout = QVBoxLayout(matrix_container)
        matrix_layout.setContentsMargins(0, 0, 0, 0)
        matrix_layout.setSpacing(2)

        lbl_mat = QLabel("📊 MATRICE DES ÉCHANGES (session en cours)")
        lbl_mat.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 10px; margin-top: 2px;")
        matrix_layout.addWidget(lbl_mat)

        self._matrix_table = QTableWidget()
        self._matrix_table.setAlternatingRowColors(True)
        self._matrix_table.setStyleSheet(
            "QTableWidget {"
            "  background-color: #11111b;"
            "  border: 1px solid #313244;"
            "  border-radius: 4px;"
            "  font-family: 'Consolas', 'Courier New', monospace;"
            "  font-size: 10px;"
            "  gridline-color: #313244;"
            "}"
            "QHeaderView::section {"
            "  background-color: #181825;"
            "  color: #cdd6f4;"
            "  border: 1px solid #313244;"
            "  padding: 2px 4px;"
            "  font-size: 9px;"
            "  font-weight: bold;"
            "}"
        )
        matrix_layout.addWidget(self._matrix_table)
        splitter.addWidget(matrix_container)

        # ── Section 3 : Timeline (QTextEdit — performant, pas de recréation de widgets) ──
        timeline_container = QWidget()
        timeline_layout = QVBoxLayout(timeline_container)
        timeline_layout.setContentsMargins(0, 0, 0, 0)
        timeline_layout.setSpacing(2)

        lbl_timeline = QLabel("📈 ACTIVITÉ RÉCENTE (ring buffer 200)")
        lbl_timeline.setStyleSheet("font-weight: bold; color: #f9e2af; font-size: 10px; margin-top: 2px;")
        timeline_layout.addWidget(lbl_timeline)

        self._timeline_edit = QTextEdit()
        self._timeline_edit.setReadOnly(True)
        self._timeline_edit.setStyleSheet(
            "QTextEdit {"
            "  background: #11111b;"
            "  color: #cdd6f4;"
            "  font-family: 'Consolas', 'Courier New', monospace;"
            "  font-size: 10px;"
            "  padding: 4px;"
            "  border: 1px solid #313244;"
            "  border-radius: 4px;"
            "}"
        )
        timeline_layout.addWidget(self._timeline_edit)

        # Bouton revenir en bas de la timeline
        btn_timeline_bottom = QPushButton("⬇ Revenir en bas")
        btn_timeline_bottom.setStyleSheet(
            "font-size: 9px; padding: 2px 6px; background-color: #313244; color: #a6adc8;"
        )
        btn_timeline_bottom.clicked.connect(self._scroll_timeline_bottom)
        timeline_layout.addWidget(btn_timeline_bottom)

        splitter.addWidget(timeline_container)

        # Proportions : cartes 40%, matrice 30%, timeline 30%
        splitter.setSizes([400, 300, 300])
        main_layout.addWidget(splitter, 1)

        # ── Boutons d'action (bas) ──
        action_bar = QHBoxLayout()
        action_bar.setContentsMargins(0, 2, 0, 0)
        action_bar.setSpacing(4)

        self._btn_reset_matrix = QPushButton("🔄 Reset matrice")
        self._btn_reset_matrix.setToolTip("Remet les compteurs de la matrice à zéro")
        self._btn_reset_matrix.clicked.connect(self._on_reset_matrix)
        action_bar.addWidget(self._btn_reset_matrix)

        self._btn_export = QPushButton("📋 Exporter rapport")
        self._btn_export.setToolTip("Copie l'état complet dans le presse-papier")
        self._btn_export.clicked.connect(self._on_export_report)
        action_bar.addWidget(self._btn_export)

        self._btn_cleanup = QPushButton("🗑️ Cleanup workers")
        self._btn_cleanup.setToolTip("Nettoie les références aux workers terminés")
        self._btn_cleanup.clicked.connect(self._on_cleanup_workers)
        action_bar.addWidget(self._btn_cleanup)

        action_bar.addStretch()
        main_layout.addLayout(action_bar)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            "QDockWidget {"
            "  background: #11111b;"
            "  color: #cdd6f4;"
            "  border: 1px solid #313244;"
            "}"
            "QDockWidget::title {"
            "  background: #181825;"
            "  padding: 6px;"
            "  font-weight: 600;"
            "}"
            "QPushButton {"
            "  background: #313244;"
            "  color: #cdd6f4;"
            "  border: 1px solid #45475a;"
            "  border-radius: 4px;"
            "  padding: 4px 10px;"
            "  font-size: 10px;"
            "}"
            "QPushButton:hover {"
            "  background: #45475a;"
            "}"
            "QScrollBar:vertical {"
            "  background: #181825;"
            "  width: 8px;"
            "}"
            "QScrollBar::handle:vertical {"
            "  background: #45475a;"
            "  border-radius: 4px;"
            "  min-height: 20px;"
            "}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {"
            "  height: 0px;"
            "}"
        )

    # ─────────────────────────────────────────────────────────────────────────
    #  Connexion EventBus
    # ─────────────────────────────────────────────────────────────────────────

    def _connect_event_bus(self) -> None:
        self._eventbus = EventBus()
        self._eventbus.event_emitted.connect(self._on_event)

    def closeEvent(self, event) -> None:
        """Déconnecte impérativement l'EventBus et stoppe le debounce timer."""
        if hasattr(self, "_eventbus"):
            try:
                self._eventbus.event_emitted.disconnect(self._on_event)
            except (TypeError, RuntimeError):
                pass
        if hasattr(self, "_matrix_debounce_timer"):
            self._matrix_debounce_timer.stop()
        if hasattr(self, "_status_timer"):
            self._status_timer.stop()
        super().closeEvent(event)

    # ─────────────────────────────────────────────────────────────────────────
    #  Gestion pause / refresh
    # ─────────────────────────────────────────────────────────────────────────

    @log_action("Workflow : pause/reprise")
    def _toggle_paused(self) -> None:
        self._paused = not self._paused
        if self._paused:
            self._btn_toggle_pause.setText("▶ Play")
            self._btn_toggle_pause.setStyleSheet(
                "background-color: #a6e3a1; color: #11111b; "
                "padding: 3px 8px; font-size: 9px; border-radius: 3px;"
            )
            logger.info("WorkflowInspector: mise à jour en pause")
        else:
            self._btn_toggle_pause.setText("⏸ Pause")
            self._btn_toggle_pause.setStyleSheet(
                "background-color: #45475a; color: #cdd6f4; "
                "padding: 3px 8px; font-size: 9px; border-radius: 3px;"
            )
            logger.info("WorkflowInspector: reprise")
            self._refresh_all()

    @log_action("Workflow : rafraîchir manuellement")
    def _refresh_all(self) -> None:
        """Refresh manuel complet — rescanner bots + mettre à jour les cartes."""
        self._refresh_count += 1
        self._lbl_refresh_count.setText(f"#{self._refresh_count}")
        self._scan_all_bots()

    # ─────────────────────────────────────────────────────────────────────────
    #  Section 1 : Scan + Cartes bots
    # ─────────────────────────────────────────────────────────────────────────

    def _scan_all_bots(self) -> None:
        """Scanne toutes les sources de bots et services disponibles.

        Combine :
        - center._pages (toutes les pages du stack)
        - center._bot_* (attributs privés du centre)
        - Attributs privés de main_window (_connexion_manager, _room_service, etc.)
        - Singletons (soulseek_service, EventBus)
        - center._clients_actifs_service
        """
        bots: dict[str, QObject] = {}
        mw = self._main_window
        center = getattr(mw, "center", None)

        # ── 1. Singletons ──
        bots["Soulseek"] = soulseek_service  # type: ignore[has-type]
        bots["Event Bus"] = EventBus()

        # ── 2. Services depuis main_window ──
        cm = getattr(mw, "_connexion_manager", None)
        if cm is not None:
            bots["Connexion"] = cm
        rs = getattr(mw, "_room_service", None)
        if rs is not None:
            bots["Room Service"] = rs

        # ── 3. Services depuis center ──
        if center is not None:
            cas = getattr(center, "_clients_actifs_service", None)
            if cas is not None:
                bots["Clients Actifs"] = cas

            # BoucleRooms — boucle pure (QObject, pas de widget)
            br = getattr(center, "boucle_rooms", None) or getattr(center, "_boucle_rooms", None)
            if br is not None:
                bots["Rooms"] = br

        # ── 4. Bots Qt depuis center._pages ──
        if center is not None:
            pages = getattr(center, "_pages", {})
            for name, page in pages.items():
                if isinstance(page, QObject):
                    bots[name] = page

        # ── 5. Ajouter les alias grecs pour les pages bots ──
        for greek_name, page_key in _GREEK_TO_PAGE_KEY.items():
            if page_key in bots:
                bots[greek_name] = bots[page_key]

        self._bot_instances = bots
        self._known_entities = list(bots.keys())
        self._build_bot_cards()

    def _build_bot_cards(self) -> None:
        """Reconstruit toutes les cartes bots."""
        # Vider l'ancien layout
        while self._cartes_layout.count() > 0:
            item = self._cartes_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        self._bot_cards.clear()

        # Titre de section
        lbl_title = QLabel("📊 TABLEAU DE BORD — BOTS & SERVICES")
        lbl_title.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 10px; margin-top: 2px;")
        self._cartes_layout.addWidget(lbl_title)

        for name in _MATRIX_ORDER:
            if name in self._bot_instances:
                instance = self._bot_instances[name]
                card = self._create_bot_card(name, instance)
                self._bot_cards[name] = card
                self._cartes_layout.addWidget(card)

        # Entités supplémentaires non répertoriées dans MATRIX_ORDER
        for name, instance in self._bot_instances.items():
            if name not in self._bot_cards:
                card = self._create_bot_card(name, instance)
                self._bot_cards[name] = card
                self._cartes_layout.addWidget(card)

        self._cartes_layout.addStretch()

    def _create_bot_card(self, name: str, instance: QObject) -> QFrame:
        """Crée une carte pour un bot/service avec ses indicateurs."""
        card = QFrame()
        card.setObjectName(f"card_{name}")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setStyleSheet(
            "QFrame {"
            "  background-color: #1e1e2e;"
            "  border: 1px solid #313244;"
            "  border-radius: 6px;"
            "  padding: 4px;"
            "}"
            "QFrame:hover {"
            "  border: 1px solid #6c5ce7;"
            "  background-color: #22223a;"
            "}"
        )
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Layout horizontal : icône + infos
        h_layout = QHBoxLayout(card)
        h_layout.setContentsMargins(4, 4, 4, 4)
        h_layout.setSpacing(6)

        # Icône
        icon = self._get_icon(name)
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet("font-size: 20px;")
        lbl_icon.setFixedWidth(34)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_layout.addWidget(lbl_icon)

        # Infos
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # Ligne 1 : Nom + Statut + Uptime + Compteur événements
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        lbl_name = QLabel(name)
        lbl_name.setStyleSheet("font-weight: bold; color: #cdd6f4; font-size: 11px;")
        row1.addWidget(lbl_name)

        status, status_color = self._get_bot_status(instance)
        status_text = status.split(" ")[1] if " " in status else ""
        status_emoji = status.split(" ")[0] if " " in status else ""

        # Label unique avec HTML : emoji en petit + texte en taille normale
        # Tout dans un seul widget → le voyant reste groupé avec le texte
        lbl_status = QLabel()
        lbl_status.setObjectName(f"status_{name}")
        lbl_status.setText(
            f'<span style="font-size:6px;">{status_emoji}</span>'
            f'<span style="color:{status_color};font-weight:bold;font-size:10px;">  {status_text}</span>'
        )
        row1.addWidget(lbl_status)

        uptime = self._estimate_uptime(instance)
        lbl_uptime = QLabel(uptime)
        lbl_uptime.setStyleSheet("color: #6c7086; font-size: 9px;")
        row1.addWidget(lbl_uptime)

        row1.addStretch()

        event_count = self._event_counters.get(name, 0)
        lbl_events = QLabel(f"{event_count} events")
        lbl_events.setObjectName(f"events_{name}")
        lbl_events.setStyleSheet("color: #89b4fa; font-size: 9px;")
        row1.addWidget(lbl_events)

        info_layout.addLayout(row1)

        # Ligne 2 : Service | Threads | Timers | Mémoire
        row2 = QHBoxLayout()
        row2.setSpacing(6)

        # Sous-indicateur : état du service sous-jacent du bot
        sub_status, sub_color = self._get_service_substatus(instance)
        lbl_service = QLabel(sub_status)
        lbl_service.setObjectName(f"service_{name}")
        if sub_status:
            lbl_service.setStyleSheet(f"color: {sub_color}; font-size: 9px;")
        else:
            lbl_service.setVisible(False)
        row2.addWidget(lbl_service)

        threads = self._get_threads_for_object(instance)
        lbl_threads = QLabel(f"├─ threads: {len(threads)}")
        lbl_threads.setStyleSheet("color: #a6adc8; font-size: 9px;")
        row2.addWidget(lbl_threads)

        timers = self._get_timers_for_object(instance)
        lbl_timers = QLabel(f"timers: {len(timers)}")
        lbl_timers.setStyleSheet("color: #a6adc8; font-size: 9px;")
        row2.addWidget(lbl_timers)

        mem = self._estimate_memory(instance)
        lbl_mem = QLabel(f"mem: {mem}")
        lbl_mem.setStyleSheet("color: #6c7086; font-size: 9px;")
        if mem == "N/A":
            lbl_mem.setToolTip(
                "sys.getsizeof() ne mesure que la mémoire Python, "
                "pas la mémoire Qt/C++ sous-jacente.\n"
                "Utilisez un profileur externe pour une mesure précise."
            )
        row2.addWidget(lbl_mem)

        row2.addStretch()

        # Bouton toggle Démarrer/Arrêter si le bot expose demarrer/arreter
        has_demarrer = hasattr(instance, "demarrer") and callable(getattr(instance, "demarrer", None))
        has_arreter = hasattr(instance, "arreter") and callable(getattr(instance, "arreter", None))
        if has_demarrer and has_arreter:
            btn_toggle = QPushButton("⏹ Arrêter" if status == "🟢 ACTIVE" else "▶ Démarrer")
            btn_toggle.setObjectName(f"toggle_{name}")
            btn_toggle.setStyleSheet(
                "font-size: 9px; padding: 2px 6px;"
            )
            btn_toggle.setFixedWidth(80)
            btn_toggle.clicked.connect(lambda checked=False, n=name: self._on_toggle_bot(n))
            row2.addWidget(btn_toggle)

        info_layout.addLayout(row2)

        # Ligne 3 : Statistiques spécifiques à la boucle (Rooms, Clients Actifs)
        row3 = QHBoxLayout()
        row3.setSpacing(6)

        lbl_loop_stats = QLabel()
        lbl_loop_stats.setObjectName(f"loop_{name}")
        lbl_loop_stats.setStyleSheet("color: #585b70; font-size: 9px;")
        lbl_loop_stats.setVisible(False)  # rendu visible par _update_loop_stats
        row3.addWidget(lbl_loop_stats)
        row3.addStretch()
        info_layout.addLayout(row3)

        # Défilement vers le bas à la construction
        h_layout.addLayout(info_layout)

        # Clic sur la carte → navigation
        card.mousePressEvent = lambda event, n=name: self._on_card_clicked(n)

        return card

    def _lookup_source(self, source_raw: str) -> tuple[str, str]:
        """Cherche une source dans _SOURCE_MAP en ignorant la casse et les séparateurs.

        Résout les écarts de casing entre les valeurs réelles de event.source
        (ex: "ConnexionManager", "SoulseekService") et les clés snake_case
        de _SOURCE_MAP (ex: "connexion_manager", "soulseek_service").
        """
        if not source_raw:
            return (source_raw, "📦")
        cleaned = source_raw.lower().replace("_", "").replace("-", "").replace(" ", "")
        for key, value in _SOURCE_MAP.items():
            key_clean = key.lower().replace("_", "").replace("-", "").replace(" ", "")
            if key_clean == cleaned:
                return value
        return (source_raw, "📦")

    def _get_icon(self, name: str) -> str:
        """Retourne l'icône d'une entité."""
        for source_key, (display_name, icon) in _SOURCE_MAP.items():
            if display_name == name:
                return icon
        return "📦"

    def _get_bot_status(self, instance: QObject) -> tuple[str, str]:
        """Retourne (statut_texte, couleur) selon l'état de l'interrupteur.

        Catégories :
        - Bots Qt avec interrupteur (demarrer/arreter) → vérifie _actif/est_actif
        - Bots Qt sans interrupteur (Aide, Accueil, Ordonnanceur) → ⚪ UNKNOWN
        - EventBus → toujours ACTIVE
        - Services → flag _running ou is_connected
        - ConnexionManager → _running + thread
        - BoucleRooms (QObject avec interrupteur) → vérifie _actif/est_actif
        """
        # ── Helper : vérifie si une instance a un interrupteur ──
        def _a_interrupteur(obj: QObject) -> bool:
            return (
                hasattr(obj, "demarrer")
                and callable(getattr(obj, "demarrer", None))
                and hasattr(obj, "arreter")
                and callable(getattr(obj, "arreter", None))
            )

        # ── Helper : statut depuis _actif/est_actif ──
        def _statut_interrupteur(obj: QObject) -> tuple[str, str] | None:
            if hasattr(obj, "est_actif"):
                try:
                    if obj.est_actif:
                        return "🟢 ACTIVE", "#a6e3a1"
                    return "🔴 STOPPED", "#f38ba8"
                except Exception:
                    pass
            actif = getattr(obj, "_actif", None)
            if actif is True:
                return "🟢 ACTIVE", "#a6e3a1"
            if actif is False:
                return "🔴 STOPPED", "#f38ba8"
            return None  # état indéterminé

        # ── Catégorie 1 : Bots Qt (QFrame) ──
        if isinstance(instance, QFrame):
            if _a_interrupteur(instance):
                statut = _statut_interrupteur(instance)
                if statut is not None:
                    return statut
                # Interrupteur présent mais état inconnu → présumé actif
                return "🟢 ACTIVE", "#a6e3a1"
            # Pas d'interrupteur → bot statique (Aide, Accueil, Ordonnanceur)
            return "⚪ UNKNOWN", "#6c7086"

        # ── Catégorie 2 : EventBus ──
        if isinstance(instance, EventBus):
            return "🟢 ACTIVE", "#a6e3a1"

        # ── Catégorie 3 : is_connected (ConnexionManager, SoulseekService) ──
        if hasattr(instance, "is_connected"):
            if instance.is_connected:
                return "🟢 ACTIVE", "#a6e3a1"
            return "🔴 STOPPED", "#f38ba8"

        # ── Catégorie 4 : Services avec _running flag ──
        running = getattr(instance, "_running", None)
        if running is True:
            return "🟢 ACTIVE", "#a6e3a1"
        if running is False:
            return "🔴 STOPPED", "#f38ba8"

        # ── Catégorie 5 : ConnexionManager (thread asyncio — fallback) ──
        if hasattr(instance, "_async_thread"):
            thread = getattr(instance, "_async_thread", None)
            if thread is not None:
                alive = False
                if hasattr(thread, "is_alive") and thread.is_alive():
                    alive = True
                if hasattr(thread, "isRunning") and thread.isRunning():
                    alive = True
                if alive:
                    return "🟢 ACTIVE", "#a6e3a1"
            return "🔴 STOPPED", "#f38ba8"

        # ── Catégorie 6 : Objets non-QFrame avec interrupteur (BoucleRooms) ──
        if _a_interrupteur(instance):
            statut = _statut_interrupteur(instance)
            if statut is not None:
                return statut
            return "🟢 ACTIVE", "#a6e3a1"

        # ── Fallback : QObject sans interrupteur → UNKNOWN ──
        if isinstance(instance, QObject):
            return "⚪ UNKNOWN", "#6c7086"

        return "⚪ UNKNOWN", "#6c7086"

    def _get_service_substatus(self, instance: QObject) -> tuple[str, str]:
        """Détecte l'état du service sous-jacent d'un bot widget.

        Parcourt les attributs de service courants (``_scanner``,
        ``_service``, ``_clients_actifs_service``, etc.) et vérifie
        leur état via ``is_connected``, ``_running`` ou ``is_running``.

        Retourne ("", "") si aucun service n'est trouvé.
        """
        for attr in ("_scanner", "_service", "_clients_actifs_service",
                     "_ordonnanceur", "_soulseek"):
            service = getattr(instance, attr, None)
            if service is None:
                continue
            if not isinstance(service, QObject):
                continue

            # is_connected (SoulseekService)
            if hasattr(service, "is_connected"):
                if service.is_connected:
                    return "🔗 connecté", "#a6e3a1"
                return "🔗 déconnecté", "#f38ba8"

            # _running (RoomService, ClientsActifsService, etc.)
            running = getattr(service, "_running", None)
            if running is True:
                return "⚡ actif", "#a6e3a1"
            if running is False:
                return "⏸ arrêté", "#f38ba8"

            # is_running (LibraryScanner)
            is_running = getattr(service, "is_running", None)
            if is_running is True:
                return "🔄 scan en cours", "#f9e2af"

        return ("", "")

    def _estimate_uptime(self, instance: QObject) -> str:
        """Estime l'uptime d'un bot/service."""
        # Pour les services, vérifier _uptime_start
        uptime_start = getattr(instance, "_uptime_start", None)
        if uptime_start is not None:
            elapsed = time.time() - uptime_start
            return self._format_uptime(elapsed)

        # Alternative : chercher un timestamp de démarrage
        for attr in ("_started_at", "_demarre_at", "_connected_at"):
            val = getattr(instance, attr, None)
            if val is not None and isinstance(val, (int, float)):
                elapsed = time.time() - val
                return self._format_uptime(elapsed)

        # Vérifier si l'instance a _demarre ou _running
        running = getattr(instance, "_running", None)
        demarre = getattr(instance, "_demarre", None)
        if running or demarre:
            return "uptime: —"
        return "—"

    def _format_uptime(self, seconds: float) -> str:
        if seconds < 0:
            return "—"
        if seconds < 60:
            return f"{int(seconds)}s"
        if seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes:02d}m"

    def _get_threads_for_object(self, obj: QObject) -> list:
        """Retourne les threads associés à un objet ou ses workers."""
        threads = []
        obj_name = obj.__class__.__name__
        for t in threading.enumerate():
            name = t.name or ""
            # Vérifier si le thread a cet objet comme parent Qt
            if hasattr(t, "parent") and callable(t.parent):
                try:
                    parent = t.parent()
                    if parent is obj:
                        threads.append(t)
                except RuntimeError:
                    pass
            # Fallback: matching thread name pattern
            if obj_name in name:
                if t not in threads:
                    threads.append(t)
        return threads

    def _get_timers_for_object(self, obj: QObject) -> list:
        """Retourne les QTimer actifs enfants de l'objet."""
        return [child for child in obj.findChildren(QTimer) if child.isActive()]

    def _estimate_memory(self, obj: QObject) -> str:
        """Retourne 'N/A' — la vraie mémoire Qt/C++ n'est pas accessible depuis Python.

        sys.getsizeof retourne ~0-100 bytes pour tout widget Qt, ce qui est trompeur.
        """
        return "N/A"

    def _update_card(self, name: str) -> None:
        """Met à jour les indicateurs d'une carte existante."""
        card = self._bot_cards.get(name)
        instance = self._bot_instances.get(name)
        if card is None or instance is None:
            return

        # Mettre à jour le statut
        status, status_color = self._get_bot_status(instance)
        status_text = status.split(" ")[1] if " " in status else ""
        status_emoji = status.split(" ")[0] if " " in status else ""

        # Label unique avec HTML (emoji petit + texte normal)
        lbl_status = card.findChild(QLabel, f"status_{name}")
        if lbl_status:
            lbl_status.setText(
                f'<span style="font-size:6px;">{status_emoji}</span>'
                f'<span style="color:{status_color};font-weight:bold;font-size:10px;">  {status_text}</span>'
            )

        # Mettre à jour le compteur d'événements
        lbl_events = card.findChild(QLabel, f"events_{name}")
        if lbl_events:
            count = self._event_counters.get(name, 0)
            lbl_events.setText(f"{count} events")

        # Mettre à jour le sous-indicateur service
        lbl_service = card.findChild(QLabel, f"service_{name}")
        if lbl_service:
            sub_status, sub_color = self._get_service_substatus(instance)
            if sub_status:
                lbl_service.setText(sub_status)
                lbl_service.setStyleSheet(f"color: {sub_color}; font-size: 9px;")
                lbl_service.setVisible(True)
            else:
                lbl_service.setVisible(False)

        # Mettre à jour le bouton toggle si présent
        btn_toggle = card.findChild(QPushButton, f"toggle_{name}")
        if btn_toggle is not None:
            if status == "🟢 ACTIVE":
                btn_toggle.setText("⏹ Arrêter")
            else:
                btn_toggle.setText("▶ Démarrer")

    def _update_loop_stats(self, name: str) -> None:
        """Met à jour les statistiques spécifiques à la boucle (Rooms, Clients Actifs)."""
        card = self._bot_cards.get(name)
        instance = self._bot_instances.get(name)
        if card is None or instance is None:
            return

        lbl_loop = card.findChild(QLabel, f"loop_{name}")
        if lbl_loop is None:
            return

        if name == "Rooms":
            membres = getattr(instance, "membres", None)
            rooms = getattr(instance, "rooms", None)
            nb_membres = len(membres) if membres else 0
            nb_rooms = len(rooms) if rooms else 0
            actif = getattr(instance, "est_actif", False) or getattr(instance, "_actif", False)
            lbl_loop.setVisible(True)
            if actif:
                lbl_loop.setText(f"🏠 {nb_rooms} rooms · 👥 {nb_membres} membres")
                lbl_loop.setStyleSheet("color: #585b70; font-size: 9px;")
            else:
                lbl_loop.setText("⏸ boucle arrêtée")
                lbl_loop.setStyleSheet("color: #f38ba8; font-size: 9px;")

        elif name == "Clients Actifs":
            ping_metrics = getattr(instance, "ping_metrics", None)
            nb_trackes = len(getattr(instance, "_clients", {}))
            actif = getattr(instance, "_running", False)
            lbl_loop.setVisible(True)

            if not actif:
                lbl_loop.setText("⏸ service arrêté")
                lbl_loop.setStyleSheet("color: #f38ba8; font-size: 9px;")
            elif ping_metrics is not None:
                m = ping_metrics()
                if m["total_pings"] > 0:
                    taux = m["taux_succes"] * 100
                    lbl_loop.setText(
                        f"👥 {nb_trackes} trackés · 📊 {m['total_reponses']}/{m['total_pings']} "
                        f"réponses ({taux:.0f}%, ~{m['temps_moyen']:.1f}s/ping)"
                    )
                else:
                    lbl_loop.setText(f"👥 {nb_trackes} trackés · 📊 aucun ping")
                lbl_loop.setStyleSheet("color: #585b70; font-size: 9px;")
            else:
                lbl_loop.setText(f"👥 {nb_trackes} trackés")
                lbl_loop.setStyleSheet("color: #585b70; font-size: 9px;")

        else:
            # Masquer la ligne pour les autres entités
            lbl_loop.setVisible(False)

    def _refresh_cards_status(self) -> None:
        """Rafraîchit le statut et les stats boucle de toutes les cartes connues (timer 2s).

        Ne reconstruit pas les cartes — appelle _update_card() et
        _update_loop_stats() pour synchroniser le statut, le bouton toggle,
        le compteur d'événements, et les statistiques spécifiques aux boucles.
        """
        if self._paused:
            return
        for name in list(self._bot_instances.keys()):
            self._update_card(name)
            self._update_loop_stats(name)

    def _on_card_clicked(self, bot_name: str) -> None:
        """Navigue vers la page du bot dans le centre."""
        center = getattr(self._main_window, "center", None)
        if center is None:
            return

        # Mapping des noms de carte vers les noms de page
        page_mapping = {
            "Connexion": "connexion",
            "Soulseek": "connexion",
            "Zeus": "accueil",
            "Déméter": "Bibliothèque",
            "Héphaistos": "Optimiseur",
            "Poséidon": "Ordonnanceur",
            "Apollon": "Planificateur",
            "Athéna": "Recherche",
            "Artémis": "Surveillance",
            "Hadès": "telechargements",  # clé interne lowercase
            "Aphrodite": "Wishlist",
            "Héra": "Assistant",
            "Dionysos": "Aide",
            "Arès": "Clients Actifs",
        }
        page_name = page_mapping.get(bot_name)
        if page_name is None:
            return

        show_page = getattr(center, "show_page", None)
        if show_page:
            show_page(page_name)

    # ─────────────────────────────────────────────────────────────────────────
    #  Section 2 : Matrice d'échanges
    # ─────────────────────────────────────────────────────────────────────────

    def _update_matrix(self) -> None:
        """Reconstruit le tableau de la matrice à partir des données de _matrix uniquement."""
        # Collecter toutes les clés uniques de _matrix (sources + cibles)
        all_keys: set[str] = set()
        for source_key, targets in self._matrix.items():
            all_keys.add(source_key)
            all_keys.update(targets.keys())

        # Trier selon _MATRIX_ORDER d'abord, puis les extras
        ordered = [k for k in _MATRIX_ORDER if k in all_keys]
        extras = sorted(k for k in all_keys if k not in _MATRIX_ORDER)
        entities = ordered + extras

        if not entities:
            self._matrix_table.setRowCount(0)
            self._matrix_table.setColumnCount(0)
            return

        n = len(entities)
        self._matrix_table.setRowCount(n)
        self._matrix_table.setColumnCount(n + 1)  # +1 pour l'en-tête de ligne
        self._matrix_table.setHorizontalHeaderLabels([""] + entities)
        self._matrix_table.setVerticalHeaderLabels(entities)

        self._matrix_table.horizontalHeader().setStretchLastSection(False)
        self._matrix_table.verticalHeader().setDefaultSectionSize(22)

        for i, row_name in enumerate(entities):
            row_data = self._matrix.get(row_name, {})
            for j, col_name in enumerate(entities):
                if row_name == col_name:
                    # Diagonale : —
                    item = QTableWidgetItem("—")
                    item.setForeground(QColor("#6c7086"))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    value = row_data.get(col_name, 0)
                    item = QTableWidgetItem(str(value) if value > 0 else "—")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if value > 1000:
                        item.setForeground(QColor("#f38ba8"))  # rouge
                    elif value > 100:
                        item.setForeground(QColor("#f9e2af"))  # orange
                    else:
                        item.setForeground(QColor("#a6adc8"))  # gris
                self._matrix_table.setItem(i, j + 1, item)

            # En-tête de ligne
            header_item = QTableWidgetItem(
                self._get_icon(row_name) + " " + row_name
            )
            header_item.setFlags(header_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._matrix_table.setItem(i, 0, header_item)

        self._matrix_table.resizeColumnsToContents()

    def _increment_matrix(self, source_name: str, target_name: str) -> None:
        """Incrémente la cellule (source, target) dans la matrice."""
        self._matrix[source_name][target_name] += 1

    def _debounce_matrix_refresh(self) -> None:
        """Déclenche un rafraîchissement de la matrice avec debounce (1.5s).

        - Premier événement d'un lot : refresh immédiat (feed-back instantané)
        - Événements suivants dans les 1.5s : marque dirty, timer catch-up
        - Timeout : refresh seulement si dirty
        """
        if not self._matrix_debounce_timer.isActive():
            self._update_matrix()
        else:
            self._matrix_dirty = True
        self._matrix_debounce_timer.start()

    def _on_matrix_debounce_timeout(self) -> None:
        """Callback du debounce timer — refresh seulement si des changements ont eu lieu."""
        if self._matrix_dirty:
            self._update_matrix()
            self._matrix_dirty = False

    @log_action("Workflow : réinitialiser la matrice")
    def _on_reset_matrix(self) -> None:
        """Remet les compteurs de la matrice à zéro."""
        self._matrix.clear()
        self._event_counters.clear()
        self._matrix_debounce_timer.stop()
        self._update_matrix()

    # ─────────────────────────────────────────────────────────────────────────
    #  Section 3 : Timeline
    # ─────────────────────────────────────────────────────────────────────────

    def _append_timeline_line(self, line: str) -> None:
        """Ajoute une ligne formatée à la timeline (QTextEdit — O(1))."""
        self._timeline_buffer.append(line)

        # Afficher les 100 plus récents dans le QTextEdit
        display = list(self._timeline_buffer)[-100:]
        self._timeline_edit.setPlainText("\n".join(display))

    @log_action("Workflow : défiler la timeline en bas")
    def _scroll_timeline_bottom(self) -> None:
        """Fait défiler la timeline vers le bas."""
        scrollbar = self._timeline_edit.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    # ─────────────────────────────────────────────────────────────────────────
    #  Événements EventBus
    # ─────────────────────────────────────────────────────────────────────────

    def _on_event(self, event: SurveillanceEvent) -> None:
        """Callback appelé pour chaque événement EventBus."""
        if self._paused:
            return

        source_raw = event.source
        display_name, icon = self._lookup_source(source_raw)

        # Auto-découverte : ajouter l'entité si elle n'est pas encore connue
        if display_name not in self._known_entities:
            self._known_entities.append(display_name)

        # Mettre à jour les compteurs
        self._event_counters[display_name] += 1

        # Mettre à jour la matrice (hors diagonale — un bot ne s'envoie pas
        # d'événement à lui-même, la cible est inférée par le message/catégorie)
        matrix_changed = self._detect_target_and_increment(event, display_name)

        # Mettre à jour la carte
        self._update_card(display_name)

        # Mettre à jour la timeline
        timestamp = event.timestamp[-8:] if len(event.timestamp) >= 8 else event.timestamp
        severity_badge = {
            "ERROR": "🔴",
            "WARN": "🟡",
            "INFO": "ℹ️",
        }.get(event.severity, "ℹ️")
        line = f"[{timestamp}] {severity_badge} {icon} {display_name}: {event.title}"
        if event.message:
            line += f" — {event.message[:80]}"
        self._append_timeline_line(line)

        # Rafraîchir la matrice après chaque événement qui la modifie
        # Utilise un debounce pour éviter trop de reconstructions QTableWidget
        if matrix_changed:
            self._debounce_matrix_refresh()

    def _detect_target_and_increment(self, event: SurveillanceEvent, source_name: str) -> bool:
        """Détecte la cible probable d'un événement pour la matrice.

        Stratégie à 4 niveaux :
        1. Mots-clés dans le message (ex: "scan" → Bibliothèque, "transfert" → Téléchargement)
        2. Catégorie EventBus (reseau → Soulseek, transfert → Téléchargement, etc.)
        3. Règles sémantiques par source (Connexion → Soulseek)
        4. Event Bus comme hub par défaut

        Retourne True si la matrice a été modifiée.
        """
        msg = (event.title + " " + event.message).lower()
        category = event.category.lower()

        # ── 1. Mots-clés dans le message (les plus spécifiques d'abord) ──
        keyword_targets: list[tuple[str, str]] = [
            # Soulseek / réseau
            ("soulseek", "Soulseek"),
            ("connecté à", "Soulseek"),
            ("déconnecté de", "Soulseek"),
            ("connexion perdue", "Soulseek"),
            ("reconnecté", "Soulseek"),
            # Rooms
            ("salle", "Room Service"),
            ("salon", "Room Service"),
            ("room", "Room Service"),
            ("message reçu", "Room Service"),
            # Transferts / téléchargements → Hadès
            ("téléchargement", "Hadès"),
            ("telechargement", "Hadès"),
            ("download", "Hadès"),
            ("transfert", "Hadès"),
            ("fichier ajouté", "Hadès"),
            ("fichier terminé", "Hadès"),
            ("upload", "Hadès"),
            # Recherche → Athéna
            ("résultat", "Athéna"),
            ("resultat", "Athéna"),
            ("recherche lancée", "Athéna"),
            ("recherche terminée", "Athéna"),
            ("recherche", "Athéna"),
            ("search", "Athéna"),
            # Bibliothèque / scan → Déméter
            ("scan démarré", "Déméter"),
            ("scan terminé", "Déméter"),
            ("scan", "Déméter"),
            ("bibliothèque", "Déméter"),
            ("bibliotheque", "Déméter"),
            ("fichier ajouté à la bibliothèque", "Déméter"),
            ("fichier supprimé", "Déméter"),
            # Wishlist → Aphrodite
            ("wishlist", "Aphrodite"),
            ("souhait", "Aphrodite"),
            # Optimiseur → Héphaistos
            ("profil", "Héphaistos"),
            ("optimiseur", "Héphaistos"),
            # Planificateur → Apollon
            ("planificateur", "Apollon"),
            ("action planifiée", "Apollon"),
            ("action programmée", "Apollon"),
            ("tâche", "Apollon"),
            ("task", "Apollon"),
            ("action récurrente", "Apollon"),
            # Surveillance → Artémis
            ("surveillance", "Artémis"),
            ("alarme", "Artémis"),
            ("seuil", "Artémis"),
        ]
        for keyword, target in keyword_targets:
            if keyword in msg and target != source_name:
                self._matrix[source_name][target] += 1
                return True

        # ── 2. Détection par catégorie EventBus ──
        category_targets: list[tuple[str, str]] = [
            ("reseau", "Soulseek"),          # événements réseau → Soulseek
            ("transfert", "Hadès"),          # transferts de fichiers → Hadès
            ("recherche", "Athéna"),         # résultats de recherche → Athéna
            ("wishlist", "Aphrodite"),       # gestion des souhaits → Aphrodite
            ("bibliotheque", "Déméter"),     # scan / gestion bibliothèque → Déméter
            ("optimiseur", "Héphaistos"),    # profils / optimisation → Héphaistos
            ("erreur", "Event Bus"),          # erreur → hub
            ("configuration", "Event Bus"),   # config → hub
        ]
        for cat_key, target in category_targets:
            if cat_key in category and target != source_name:
                self._matrix[source_name][target] += 1
                return True

        # ── 3. Règles sémantiques par source ──
        source_rules: dict[str, str] = {
            "Connexion": "Soulseek",
            "Room Service": "Event Bus",
            "Déméter": "Event Bus",
            "Apollon": "Event Bus",
            "Athéna": "Soulseek",
        }
        if source_name in source_rules:
            target = source_rules[source_name]
            self._matrix[source_name][target] += 1
            return True

        # ── 4. Dernier recours : Event Bus comme hub ──
        if source_name != "Event Bus":
            self._matrix[source_name]["Event Bus"] += 1
            return True

        return False

    # ─────────────────────────────────────────────────────────────────────────
    #  Boutons d'action
    # ─────────────────────────────────────────────────────────────────────────

    @log_action("Workflow : activer/désactiver un bot")
    def _on_toggle_bot(self, bot_name: str) -> None:
        """Démarre ou arrête un bot individuellement."""
        instance = self._bot_instances.get(bot_name)
        if instance is None:
            logger.warning("WorkflowInspector: bot '%s' introuvable", bot_name)
            return

        # Vérifier le statut actuel
        status, _ = self._get_bot_status(instance)

        if status == "🟢 ACTIVE" and hasattr(instance, "arreter"):
            try:
                instance.arreter()
                logger.info("WorkflowInspector: %s arrêté", bot_name)
            except Exception as e:
                logger.error("WorkflowInspector: erreur arrêt %s — %s", bot_name, e)
        elif status == "🔴 STOPPED" and hasattr(instance, "demarrer"):
            try:
                instance.demarrer()
                logger.info("WorkflowInspector: %s démarré", bot_name)
            except Exception as e:
                logger.error("WorkflowInspector: erreur démarrage %s — %s", bot_name, e)

        # Mettre à jour la carte
        self._update_card(bot_name)

    @log_action("Workflow : exporter le rapport")
    def _on_export_report(self) -> None:
        """Copie l'état complet (tous les bots + matrice) dans le presse-papier."""
        lines = []
        lines.append("=== WORKFLOW & LOOP INSPECTOR — RAPPORT ===")
        lines.append(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Rafraîchissements: #{self._refresh_count}")
        lines.append(f"Entités surveillées: {len(self._bot_instances)}")
        lines.append("")

        lines.append("--- ÉTAT DES BOTS ---")
        for name in _MATRIX_ORDER:
            if name in self._bot_instances:
                instance = self._bot_instances[name]
                status, _ = self._get_bot_status(instance)
                events = self._event_counters.get(name, 0)
                uptime = self._estimate_uptime(instance)
                icon = self._get_icon(name)
                lines.append(f"  {icon} {name}: {status} | events: {events} | uptime: {uptime}")

        lines.append("")
        lines.append("--- MATRICE DES ÉCHANGES ---")
        entities = [e for e in _MATRIX_ORDER if e in self._known_entities]
        header = " " * 20 + " ".join(f"{e[:8]:>8}" for e in entities)
        lines.append(header)
        for row_name in entities:
            row_data = self._matrix.get(row_name, {})
            row_values = " ".join(f"{row_data.get(col, 0):>8}" for col in entities)
            lines.append(f"{row_name:<20}{row_values}")

        lines.append("")
        lines.append("--- ACTIVITÉ RÉCENTE (100 dernières lignes) ---")
        for entry in list(self._timeline_buffer)[-100:]:
            # Enlever les balises HTML
            import re
            clean = re.sub(r'<[^>]+>', '', entry)
            lines.append(clean)

        report = "\n".join(lines)
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(report)
            logger.info("WorkflowInspector: rapport exporté (%d caractères)", len(report))

    @log_action("Workflow : nettoyer les workers")
    def _on_cleanup_workers(self) -> None:
        """Nettoie les références aux workers terminés dans les widgets."""
        cleaned = 0
        for widget in QApplication.allWidgets():
            # Chercher les attributs de worker potentiels
            for attr_name in ("_current_worker", "_analyse_worker", "_export_worker", "_ordonnanceur_worker"):
                worker = getattr(widget, attr_name, None)
                if worker is not None and hasattr(worker, "isFinished"):
                    try:
                        if worker.isFinished():
                            setattr(widget, attr_name, None)
                            cleaned += 1
                    except RuntimeError:
                        setattr(widget, attr_name, None)
                        cleaned += 1

        logger.info("WorkflowInspector: %d références worker nettoyées", cleaned)

        # Mettre à jour le compteur
        status_text = f"🧹 {cleaned} worker(s) nettoyé(s)"
        self._lbl_refresh_count.setText(status_text)
        QTimer.singleShot(2000, lambda: self._lbl_refresh_count.setText(f"#{self._refresh_count}"))
