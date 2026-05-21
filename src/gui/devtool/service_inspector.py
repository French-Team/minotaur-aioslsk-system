"""Service & Connection Inspector — Diagnostic & Developer Tool.

Allows deep inspection of all background active asyncio tasks, raw event loop calls,
and includes an isolated socket-level Diagnostic Connection test thread to bypass the application's
entire codebase and test raw networking capabilities.
"""

from __future__ import annotations

import asyncio
import logging
import re
import socket
import time
import traceback
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QObject, Qt, QPoint, QRect, QSize, QTimer, Signal
from PySide6.QtGui import QColor, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDockWidget,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLayout,
    QLayoutItem,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.devtool.diagnostics import ConnexionMonitorWidget, TimeoutControllerWidget
from src.services.soulseek_client import soulseek_service
from src.services.app_config import get as cfg_get

logger = logging.getLogger(__name__)

# ── Custom Thread-Safe Log Handler for PySide6 ───────────────────────────

class _LogSignalEmitter(QObject):
    log_received = Signal(str, str, str)  # level, logger_name, msg


class QTextBoxLogHandler(logging.Handler):
    """Custom logging handler that emits log records to the PySide6 UI thread."""

    def __init__(self) -> None:
        super().__init__()
        self.emitter = _LogSignalEmitter()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.emitter.log_received.emit(record.levelname, record.name, msg)
        except Exception:
            self.handleError(record)


# ── Isolated Diagnostic Worker Thread ─────────────────────────────────────

class DiagnosticWorker(threading.Thread):
    """Bypasses the entire application state and library instance to perform a
    100% isolated network-level and protocol-level connection diagnostic.
    """

    def __init__(self, port: int, username: str, password: str, log_signal: Any) -> None:
        super().__init__()
        self.port = port
        self.username = username
        self.password = password
        self.log_signal = log_signal

    def log(self, message: str, success: bool | None = None) -> None:
        """Helper to send logs back to the UI."""
        if success is True:
            # pyrefly: ignore [missing-attribute]
            self.log_signal.emit(f'<font color="#a6e3a1">✅ {message}</font>')
        elif success is False:
            # pyrefly: ignore [missing-attribute]
            self.log_signal.emit(f'<font color="#f38ba8">❌ {message}</font>')
        elif success is None:
            # pyrefly: ignore [missing-attribute]
            self.log_signal.emit(f'<font color="#89b4fa">ℹ️ {message}</font>')

    def run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run_diagnostic())
        except Exception as e:
            self.log(f"Erreur fatale de diagnostic : {e}", False)
        finally:
            loop.close()

    async def _run_diagnostic(self) -> None:
        self.log("DÉBUT DU DIAGNOSTIC DE CONNEXION ISOLÉ")
        self.log(f"Cibles : server.slsknet.org sur le port {self.port}")
        self.log(f"Identifiants : utilisateur '{self.username}'")

        # 1. DNS Resolution
        self.log("Résolution DNS de 'server.slsknet.org'...")
        try:
            ip = socket.gethostbyname("server.slsknet.org")
            self.log(f"DNS résolu : server.slsknet.org -> {ip}", True)
        except Exception as e:
            self.log(f"Impossible de résoudre le DNS : {e}", False)
            self.log("💡 Diagnostic : Votre connexion internet locale ou vos serveurs DNS sont inaccessibles.", False)
            return

        # 2. Raw TCP Connect Latency
        self.log(f"Tentative de connexion TCP brute avec {ip}:{self.port}...")
        start = time.time()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("server.slsknet.org", self.port),
                timeout=5.0
            )
            latency = (time.time() - start) * 1000
            self.log(f"Connexion TCP brute réussie ! Latence : {latency:.1f} ms", True)
            writer.close()
            await writer.wait_closed()
        except asyncio.TimeoutError:
            self.log("TIMEOUT sur la connexion TCP brute (5.0s)", False)
            self.log("💡 Diagnostic : Le port ou le serveur central ignore complètement nos paquets TCP. Soit le pare-feu local bloque, soit le serveur central a banni temporairement votre adresse IP.", False)
            return
        except Exception as e:
            self.log(f"Échec de connexion TCP brute : {e}", False)
            self.log("💡 Diagnostic : Erreur réseau générique (pare-feu local, coupure internet).", False)
            return

        # 3. Protocol-Level Handshake Check
        self.log("Initialisation d'un client aioslsk 100% indépendant et isolé...")
        from aioslsk.client import SoulSeekClient
        from aioslsk.settings import (
            Settings, CredentialsSettings, UserInfoSettings, NetworkSettings,
            ListeningSettings, PeerSettings, NetworkLimitSettings, ServerSettings,
            ReconnectSettings, RoomsSettings, InterestsSettings, SearchSettings,
            SearchReceiveSettings, SearchSendSettings, SharesSettings, UpnpSettings,
            PeerConnectMode
        )
        from aioslsk.network.network import ListeningConnectionErrorMode

        settings = Settings(
            credentials=CredentialsSettings(
                username=self.username,
                password=self.password,
                info=UserInfoSettings(description="", picture=b""),
            ),
            network=NetworkSettings(
                upnp=UpnpSettings(enabled=False, lease_duration=21600, check_interval=600, search_timeout=10),
                listening=ListeningSettings(port=60002, obfuscated_port=60003, error_mode=ListeningConnectionErrorMode.CLEAR),
                peer=PeerSettings(obfuscate=False, connect_mode=PeerConnectMode.RACE),
                limits=NetworkLimitSettings(upload_speed_kbps=0, download_speed_kbps=0),
                server=ServerSettings(
                    hostname="server.slsknet.org",
                    port=self.port,
                    reconnect=ReconnectSettings(auto=False, timeout=10)
                )
            ),
            rooms=RoomsSettings(auto_join=False, private_room_invites=False, favorites=set()),
            interests=InterestsSettings(liked=set(), hated=set()),
            searches=SearchSettings(
                receive=SearchReceiveSettings(max_results=10, store_amount=10),
                send=SearchSendSettings(store_results=False, request_timeout=0, wishlist_request_timeout=-1),
                wishlist=set()
            ),
            shares=SharesSettings(scan_on_start=False, download="", directories=[])
        )

        test_client = SoulSeekClient(settings)
        try:
            self.log("Démarrage du client de test...")
            await test_client.start()
            self.log("Client réseau démarré. Envoi de l'authentification (handshake)...")
            
            # Perform login with timeout
            await asyncio.wait_for(test_client.login(), timeout=10.0)
            self.log("Authentification complétée avec succès !", True)
            self.log("💡 Diagnostic : Le réseau Soulseek et le handshake fonctionnent parfaitement sur cette IP.", True)
            self.log("👉 CONCLUSION : Les blocages constatés proviennent du code de notre propre application (deadlocks, threads bloqués, ou cycle de vie mal coordonné). Inspectez l'onglet 'Tâches Asyncio' !", True)
        except asyncio.TimeoutError:
            self.log("TIMEOUT lors de l'attente de la réponse d'authentification (10.0s)", False)
            self.log("💡 CONCLUSION : Le serveur a accepté la connexion TCP, mais ignore le handshake.", False)
            self.log("👉 ACTION : Votre IP est temporairement RATE-LIMITÉE par le serveur Soulseek central. Conseil : activez un VPN, utilisez un point d'accès 4G/5G, ou attendez 2 minutes.", False)
        except Exception as e:
            self.log(f"Erreur d'authentification Soulseek : {e}", False)
            self.log("👉 CONCLUSION : Le serveur a retourné une erreur (ex: mauvais mot de passe ou compte inexistant).", False)
        finally:
            self.log("Arrêt et nettoyage du client de test...")
            try:
                await test_client.stop()
                self.log("Client de test arrêté.", True)
            except Exception:
                pass
            self.log("FIN DU DIAGNOSTIC.")


# ── Thread-Safe Emitters for Asyncio Task Updates ───────────────────────

class _TasksSignalEmitter(QObject):
    tasks_received = Signal(list)
    diagnostic_log = Signal(str)


# ── FlowLayout : layout qui passe à la ligne automatiquement ──────────────

class _FlowLayout(QLayout):
    """Layout à flux qui dispose les widgets horizontalement et passe à la ligne
    suivante automatiquement quand il n'y a plus d'espace horizontal disponible.

    Inspiré de l'exemple Qt officiel ``basiclayouts/flowlayout.py``.
    """

    def __init__(self, parent: QWidget | None = None, margin: int = 0, spacing: int = 4) -> None:
        super().__init__(parent)
        self._item_list: list[QLayoutItem] = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def __del__(self) -> None:
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item: QLayoutItem) -> None:
        self._item_list.append(item)

    def count(self) -> int:
        return len(self._item_list)

    def itemAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), False)

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, True)

    def _do_layout(self, rect: QRect, set_geometry: bool) -> int:
        """Dispose les widgets horizontalement avec retour à la ligne.

        Retourne la hauteur totale utilisée (utile pour heightForWidth).
        """
        margins = self.contentsMargins()
        effective_rect = QRect(
            rect.x() + margins.left(),
            rect.y() + margins.top(),
            rect.width() - margins.left() - margins.right(),
            rect.height() - margins.top() - margins.bottom(),
        )

        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self._item_list:
            widget = item.widget()
            if widget is None:
                continue
            if not widget.isVisible():
                continue

            space_x = spacing
            next_x = x + item.sizeHint().width() + space_x

            if next_x - space_x > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y += line_height + spacing
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if set_geometry:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y() + margins.bottom()


# ── Service Inspector main QDockWidget ────────────────────────────────────

class ServiceInspector(QDockWidget):
    """Ancillary Developer panel to inspect and control the active Soulseek client & services."""

    def __init__(self, main_window: QWidget, parent: Optional[QWidget] = None) -> None:
        super().__init__("Service & Connection Inspector", parent)
        self._main_window = main_window
        self.setObjectName("_service_inspector")
        
        # Configure Dock attributes
        # pyrefly: ignore [missing-attribute]
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        self.setMinimumWidth(480)
        self.setFeatures(
            # pyrefly: ignore [missing-attribute]
            QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable
        )

        # ── Central Widget & Tab system ──
        central = QWidget()
        self.setWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # Signal Emitter for async updates
        self._emitter = _TasksSignalEmitter()
        self._emitter.tasks_received.connect(self._on_tasks_received)
        self._emitter.diagnostic_log.connect(self._on_diagnostic_log)

        # ── Barre d'actions (Refresh global) ──
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)

        self._btn_refresh = QPushButton("🔄 Refresh All")
        self._btn_refresh.setToolTip("Rafraîchir tous les onglets (stats, tâches, moniteur, contrôleur)")
        self._btn_refresh.setStyleSheet(
            "background-color: #6c5ce7; font-weight: bold; color: #ffffff; "
            "padding: 3px 10px; font-size: 10px; border-radius: 3px;"
        )
        self._btn_refresh.clicked.connect(self.refresh_all)
        toolbar.addWidget(self._btn_refresh)

        # Timer toggle (permet de suspendre le polling si besoin)
        self._btn_toggle_poll = QPushButton("⏸ Pause")
        self._btn_toggle_poll.setToolTip("Suspendre/Reprendre le rafraîchissement automatique")
        self._btn_toggle_poll.setStyleSheet(
            "background-color: #45475a; color: #cdd6f4; "
            "padding: 3px 8px; font-size: 9px; border-radius: 3px;"
        )
        self._btn_toggle_poll.clicked.connect(self._toggle_polling)
        toolbar.addWidget(self._btn_toggle_poll)

        # Compteur de rafraîchissement
        self._refresh_count = 0
        self._lbl_refresh_count = QLabel("#0")
        self._lbl_refresh_count.setStyleSheet("color: #6c7086; font-size: 9px; padding-left: 4px;")
        toolbar.addWidget(self._lbl_refresh_count)

        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        # Tabs
        self._tabs = QTabWidget()

        # Tab 1: Dashboard & Asyncio Tasks
        self._setup_tab_dashboard()
        
        # Tab 2: Standalone Network Diagnostic
        self._setup_tab_diagnostic()

        # Tab 3: Real-time logs
        self._setup_tab_logs()

        # Tab 4: Contrôle Connexion (moniteur + actions de débogage)
        self._setup_tab_control()

        main_layout.addWidget(self._tabs)

        # Apply custom styling matching theme
        self._apply_style()

        # Setup custom real-time logs handler
        self._log_handler = QTextBoxLogHandler()
        self._log_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] (%(name)s) %(message)s', datefmt='%H:%M:%S'))
        self._log_handler.emitter.log_received.connect(self.append_log)
        logging.getLogger().addHandler(self._log_handler)

        # Flag : l'onglet Dashboard est visible → on met à jour l'arbre des tâches
        # Remplacer le check self._tabs.currentIndex() == 0 par ce flag permet
        # de forcer la mise à jour depuis le bouton "Rafraîchir Tâches" même
        # quand l'utilisateur est sur un autre onglet.
        self._tasks_in_foreground = True
        self._tabs.currentChanged.connect(lambda idx: setattr(self, "_tasks_in_foreground", idx == 0))

        # Active poll timer (1.5 seconds) to update services status and tasks
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(1500)
        self._poll_timer.timeout.connect(self.refresh_all)
        self._poll_timer.start()

    def _setup_tab_dashboard(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # Service Status Row Grid
        lbl_dash = QLabel("📊 ÉTAT EN TEMPS RÉEL DES DAEMONS")
        lbl_dash.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 10px; margin-top: 4px;")
        layout.addWidget(lbl_dash)

        self._grid_frame = QFrame()
        self._grid_frame.setStyleSheet("background-color: #1e1e2e; border: 1px solid #313244; border-radius: 6px; padding: 6px;")
        self._grid_layout = QGridLayout(self._grid_frame)
        self._grid_layout.setSpacing(6)

        # Row 0: Network
        self._grid_layout.addWidget(QLabel("<b>Reseau Soulseek:</b>"), 0, 0)
        self._lbl_net_status = QLabel("OFFLINE")
        self._lbl_net_status.setStyleSheet("color: #f38ba8; font-weight: bold;")
        self._grid_layout.addWidget(self._lbl_net_status, 0, 1)
        self._lbl_net_info = QLabel("—")
        self._grid_layout.addWidget(self._lbl_net_info, 0, 2)

        # Row 1: Rooms
        self._grid_layout.addWidget(QLabel("<b>Room Service:</b>"), 1, 0)
        self._lbl_room_status = QLabel("STOPPED")
        self._lbl_room_status.setStyleSheet("color: #f38ba8; font-weight: bold;")
        self._grid_layout.addWidget(self._lbl_room_status, 1, 1)
        self._lbl_room_info = QLabel("—")
        self._grid_layout.addWidget(self._lbl_room_info, 1, 2)
        self._btn_room_act = QPushButton("Démarrer")
        self._btn_room_act.setStyleSheet("font-size: 9px; padding: 2px 4px;")
        self._btn_room_act.clicked.connect(self._toggle_room_service)
        self._grid_layout.addWidget(self._btn_room_act, 1, 3)

        # Row 2: Active Clients
        self._grid_layout.addWidget(QLabel("<b>Clients Actifs:</b>"), 2, 0)
        self._lbl_clients_status = QLabel("STOPPED")
        self._lbl_clients_status.setStyleSheet("color: #f38ba8; font-weight: bold;")
        self._grid_layout.addWidget(self._lbl_clients_status, 2, 1)
        self._lbl_clients_info = QLabel("—")
        self._grid_layout.addWidget(self._lbl_clients_info, 2, 2)
        self._btn_clients_act = QPushButton("Démarrer")
        self._btn_clients_act.setStyleSheet("font-size: 9px; padding: 2px 4px;")
        self._btn_clients_act.clicked.connect(self._toggle_clients_service)
        self._grid_layout.addWidget(self._btn_clients_act, 2, 3)

        layout.addWidget(self._grid_frame)

        # Task Inspector List
        lbl_tasks = QLabel("⚙️ INSPECTEUR DES TÂCHES ASYNCIO (BOUCLE RÉSEAU)")
        lbl_tasks.setStyleSheet("font-weight: bold; color: #f9e2af; font-size: 10px; margin-top: 4px;")
        layout.addWidget(lbl_tasks)

        self._tasks_tree = QTreeWidget()
        self._tasks_tree.setHeaderLabels(["Nom de la Tâche", "Coroutine / Cible", "État", "Position / Pile d'appels"])
        self._tasks_tree.setAlternatingRowColors(True)
        self._tasks_tree.header().setStretchLastSection(True)
        self._tasks_tree.setStyleSheet(
            "QTreeWidget {"
            "  background-color: #11111b;"
            "  border: 1px solid #313244;"
            "  border-radius: 4px;"
            "  font-family: 'Consolas', 'Courier New', monospace;"
            "  font-size: 10px;"
            "}"
        )
        layout.addWidget(self._tasks_tree, 1)

        # Refresh button
        self._btn_refresh_tasks = QPushButton("🔄 Rafraîchir Tâches")
        self._btn_refresh_tasks.clicked.connect(self.refresh_asyncio_tasks)
        layout.addWidget(self._btn_refresh_tasks)

        self._tabs.addTab(tab, "Démarrage & Tâches")

    def _setup_tab_diagnostic(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Description
        lbl_desc = QLabel(
            "Ce test 100% isolé contourne TOUT notre code et initialise une connexion brute "
            "pour déterminer si le gel provient de notre application, d'aioslsk, ou de votre adresse IP bannie."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #a6adc8; font-size: 11px; font-style: italic;")
        layout.addWidget(lbl_desc)

        # Credentials inputs
        inputs_frame = QFrame()
        inputs_frame.setStyleSheet("background-color: #1e1e2e; border: 1px solid #313244; border-radius: 4px; padding: 4px;")
        inputs_layout = QGridLayout(inputs_frame)
        inputs_layout.setSpacing(6)

        inputs_layout.addWidget(QLabel("Nom Utilisateur :"), 0, 0)
        self._diag_user = QLineEdit()
        self._diag_user.setPlaceholderText("Laisser vide pour config actuelle")
        inputs_layout.addWidget(self._diag_user, 0, 1)

        inputs_layout.addWidget(QLabel("Mot de Passe :"), 0, 2)
        self._diag_pass = QLineEdit()
        self._diag_pass.setEchoMode(QLineEdit.EchoMode.Password)
        inputs_layout.addWidget(self._diag_pass, 0, 3)

        inputs_layout.addWidget(QLabel("Port Serveur :"), 1, 0)
        self._diag_port = QLineEdit("2242")
        inputs_layout.addWidget(self._diag_port, 1, 1)

        layout.addWidget(inputs_frame)

        # Start button
        self._btn_run_diag = QPushButton("🚀 LANCER TEST DE DIAGNOSTIC DE CONNEXION BRUTE")
        self._btn_run_diag.setStyleSheet("background-color: #6c5ce7; font-weight: bold; color: #ffffff; padding: 6px;")
        self._btn_run_diag.clicked.connect(self._run_isolated_diagnostic)
        layout.addWidget(self._btn_run_diag)

        # Terminal text area
        self._diag_console = QTextEdit()
        self._diag_console.setReadOnly(True)
        self._diag_console.setStyleSheet(
            "QTextEdit {"
            "  background-color: #11111b;"
            "  color: #cdd6f4;"
            "  font-family: 'Consolas', 'Courier New', monospace;"
            "  font-size: 11px;"
            "  padding: 6px;"
            "  border: 1px solid #313244;"
            "  border-radius: 4px;"
            "}"
        )
        layout.addWidget(self._diag_console, 1)

        # Action to clear console
        btn_clear_diag = QPushButton("🗑️ Vider le Terminal de Diagnostic")
        btn_clear_diag.clicked.connect(self._diag_console.clear)
        layout.addWidget(btn_clear_diag)

        # Info : le moniteur de connexion suit aussi le diagnostic
        lbl_sync = QLabel("💡 Les résultats de diagnostic sont également transmis au Moniteur de Connexion (onglet 'Contrôle Connexion').")
        lbl_sync.setWordWrap(True)
        lbl_sync.setStyleSheet("color: #6c7086; font-size: 9px; font-style: italic;")
        layout.addWidget(lbl_sync)

        self._tabs.addTab(tab, "Diagnostique Brute")

    def _setup_tab_logs(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)

        # ── Barre de filtres + actions ──
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 4)
        toolbar.setSpacing(4)

        toolbar.addWidget(QLabel("Filtrer :"))

        self._chk_error = QCheckBox("ERROR")
        self._chk_error.setChecked(True)
        self._chk_error.toggled.connect(self._reapply_log_filter)
        self._chk_error.setStyleSheet("color: #f38ba8; font-size: 10px;")
        toolbar.addWidget(self._chk_error)

        self._chk_warning = QCheckBox("WARNING")
        self._chk_warning.setChecked(True)
        self._chk_warning.toggled.connect(self._reapply_log_filter)
        self._chk_warning.setStyleSheet("color: #f9e2af; font-size: 10px;")
        toolbar.addWidget(self._chk_warning)

        self._chk_info = QCheckBox("INFO")
        self._chk_info.setChecked(True)
        self._chk_info.toggled.connect(self._reapply_log_filter)
        self._chk_info.setStyleSheet("color: #89b4fa; font-size: 10px;")
        toolbar.addWidget(self._chk_info)

        self._chk_debug = QCheckBox("DEBUG")
        self._chk_debug.setChecked(True)
        self._chk_debug.toggled.connect(self._reapply_log_filter)
        self._chk_debug.setStyleSheet("color: #6c7086; font-size: 10px;")
        toolbar.addWidget(self._chk_debug)

        # Bouton "Tout sélectionner" pour les filtres
        self._btn_select_all = QPushButton("Tout")
        self._btn_select_all.setFixedWidth(40)
        self._btn_select_all.setStyleSheet(
            "background: #313244; color: #cdd6f4; "
            "padding: 2px 4px; font-size: 9px; border-radius: 3px;"
        )
        self._btn_select_all.clicked.connect(self._select_all_filters)
        toolbar.addWidget(self._btn_select_all)

        self._btn_deselect_all = QPushButton("Aucun")
        self._btn_deselect_all.setFixedWidth(45)
        self._btn_deselect_all.setStyleSheet(
            "background: #313244; color: #cdd6f4; "
            "padding: 2px 4px; font-size: 9px; border-radius: 3px;"
        )
        self._btn_deselect_all.clicked.connect(self._deselect_all_filters)
        toolbar.addWidget(self._btn_deselect_all)

        toolbar.addStretch()

        self._btn_copy_logs = QPushButton("📋 Copier les logs")
        self._btn_copy_logs.setStyleSheet(
            "background-color: #45475a; color: #cdd6f4; "
            "padding: 3px 8px; font-size: 9px; border-radius: 3px;"
        )
        self._btn_copy_logs.clicked.connect(self._copy_filtered_logs)
        toolbar.addWidget(self._btn_copy_logs)

        layout.addLayout(toolbar)

        # ── Barre de filtres par service (dynamique) ──
        service_bar = QHBoxLayout()
        service_bar.setContentsMargins(0, 0, 0, 4)
        service_bar.setSpacing(4)

        lbl_services = QLabel("Services :")
        lbl_services.setStyleSheet("color: #a6adc8; font-size: 10px;")
        service_bar.addWidget(lbl_services)

        self._loggers_container = QWidget()
        self._loggers_layout = _FlowLayout(self._loggers_container, margin=0, spacing=4)
        service_bar.addWidget(self._loggers_container)

        service_bar.addStretch()

        self._btn_logger_all = QPushButton("Tout")
        self._btn_logger_all.setFixedWidth(35)
        self._btn_logger_all.setStyleSheet(
            "background: #313244; color: #cdd6f4; "
            "padding: 2px 4px; font-size: 9px; border-radius: 3px;"
        )
        self._btn_logger_all.clicked.connect(self._select_all_loggers)
        service_bar.addWidget(self._btn_logger_all)

        self._btn_logger_none = QPushButton("Aucun")
        self._btn_logger_none.setFixedWidth(40)
        self._btn_logger_none.setStyleSheet(
            "background: #313244; color: #cdd6f4; "
            "padding: 2px 4px; font-size: 9px; border-radius: 3px;"
        )
        self._btn_logger_none.clicked.connect(self._deselect_all_loggers)
        service_bar.addWidget(self._btn_logger_none)

        layout.addLayout(service_bar)

        self._logs_text = QTextEdit()
        self._logs_text.setReadOnly(True)
        self._logs_text.setStyleSheet(
            "QTextEdit {"
            "  background: #11111b;"
            "  color: #cdd6f4;"
            "  font-family: 'Consolas', 'Courier New', monospace;"
            "  font-size: 11px;"
            "  padding: 6px;"
            "  border: 1px solid #313244;"
            "  border-radius: 4px;"
            "}"
        )
        layout.addWidget(self._logs_text)

        # Stockage des logs bruts pour re-filtrage
        self._log_entries: list[tuple[str, str, str]] = []  # (level, logger_name, html_msg)
        self._chk_loggers: dict[str, QCheckBox] = {}  # logger_name → checkbox

        self._tabs.addTab(tab, "Flux des Logs")

    def _setup_tab_control(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # ── Splitter vertical : Moniteur + Contrôleur ──
        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)
        splitter.setStyleSheet(
            "QSplitter::handle {"
            "  background: #313244;"
            "  height: 2px;"
            "}"
        )

        # Moniteur de connexion (en haut — machine à états)
        self._connexion_monitor = ConnexionMonitorWidget()
        self._connexion_monitor.set_main_window(self._main_window)
        splitter.addWidget(self._connexion_monitor)

        # Contrôleur de timeout / actions (en bas)
        self._timeout_controller = TimeoutControllerWidget()
        self._timeout_controller.set_main_window(self._main_window)
        splitter.addWidget(self._timeout_controller)

        layout.addWidget(splitter, 1)
        self._tabs.addTab(tab, "Contrôle Connexion")

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
            "QTabWidget::pane {"
            "  border: 1px solid #313244;"
            "  background: #1e1e2e;"
            "}"
            "QTabBar::tab {"
            "  background: #181825;"
            "  color: #6c7086;"
            "  padding: 6px 10px;"
            "  border: 1px solid #313244;"
            "  border-bottom: none;"
            "  border-top-left-radius: 4px;"
            "  border-top-right-radius: 4px;"
            "  font-size: 10px;"
            "}"
            "QTabBar::tab:selected {"
            "  background: #1e1e2e;"
            "  color: #cdd6f4;"
            "  border-bottom: 1px solid #1e1e2e;"
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
            "QLineEdit {"
            "  background-color: #11111b;"
            "  border: 1px solid #313244;"
            "  border-radius: 4px;"
            "  padding: 2px 4px;"
            "  color: #cdd6f4;"
            "  font-size: 10px;"
            "}"
            "QLabel {"
            "  color: #cdd6f4;"
            "  font-size: 11px;"
            "}"
        )

    # ── Service Management & Dynamic State Polling ───────────────────────────

    def refresh_all(self) -> None:
        """Invoked periodically to update service labels and asyncio active tasks."""
        self._refresh_count += 1
        self._lbl_refresh_count.setText(f"#{self._refresh_count}")

        self.refresh_stats()

        # Rafraîchir les diagnostics en permanence (tous les onglets)
        if hasattr(self, '_connexion_monitor'):
            self._connexion_monitor.refresh()
        if hasattr(self, '_timeout_controller'):
            self._timeout_controller.refresh()

        # Only query active tasks if the dashboard tab is currently selected
        if self._tasks_in_foreground:
            self.refresh_asyncio_tasks()

    def _toggle_polling(self) -> None:
        """Suspend/reprend le rafraîchissement automatique."""
        if self._poll_timer.isActive():
            self._poll_timer.stop()
            self._btn_toggle_poll.setText("▶ Play")
            self._btn_toggle_poll.setStyleSheet(
                "background-color: #a6e3a1; color: #11111b; "
                "padding: 3px 8px; font-size: 9px; border-radius: 3px;"
            )
        else:
            self._poll_timer.start()
            self._btn_toggle_poll.setText("⏸ Pause")
            self._btn_toggle_poll.setStyleSheet(
                "background-color: #45475a; color: #cdd6f4; "
                "padding: 3px 8px; font-size: 9px; border-radius: 3px;"
            )

    def refresh_stats(self) -> None:
        try:
            # 1. Soulseek connection manager
            mgr = getattr(self._main_window, "_connexion_manager", None)
            if soulseek_service.is_connected:
                self._lbl_net_status.setText("CONNECTED")
                self._lbl_net_status.setStyleSheet("color: #a6e3a1; font-weight: bold;")
                self._lbl_net_info.setText(f"{soulseek_service.username} — server.slsknet.org:{cfg_get('reseau.port_serveur', '2242')}")
            else:
                is_generating = False
                if mgr is not None:
                    is_generating = getattr(mgr, "_generating", False)
                if is_generating:
                    self._lbl_net_status.setText("GENERATING")
                    self._lbl_net_status.setStyleSheet("color: #f9e2af; font-weight: bold;")
                else:
                    self._lbl_net_status.setText("OFFLINE")
                    self._lbl_net_status.setStyleSheet("color: #f38ba8; font-weight: bold;")
                self._lbl_net_info.setText("—")

            # 2. RoomService
            room_svc = getattr(self._main_window, "_room_service", None)
            if room_svc is not None and getattr(room_svc, "_running", False):
                self._lbl_room_status.setText("RUNNING")
                self._lbl_room_status.setStyleSheet("color: #a6e3a1; font-weight: bold;")
                rooms_count = room_svc.nb_publiques + room_svc.nb_privees
                self._lbl_room_info.setText(f"{rooms_count} salon(s) — {room_svc.nb_publiques} publiques, {room_svc.nb_privees} privées")
                self._btn_room_act.setText("Arrêter")
            else:
                self._lbl_room_status.setText("STOPPED")
                self._lbl_room_status.setStyleSheet("color: #f38ba8; font-weight: bold;")
                self._lbl_room_info.setText("—")
                self._btn_room_act.setText("Démarrer")

            # 3. ClientsActifsService
            layout = getattr(self._main_window, "_layout", None)
            clients_svc = None
            if layout is not None and hasattr(layout, "center"):
                clients_svc = getattr(layout.center, "_clients_actifs_service", None)
            
            if clients_svc is not None and getattr(clients_svc, "_running", False):
                self._lbl_clients_status.setText("RUNNING")
                self._lbl_clients_status.setStyleSheet("color: #a6e3a1; font-weight: bold;")
                active_count = len(clients_svc.clients_actifs())
                self._lbl_clients_info.setText(f"{active_count} contact(s) suivi(s)")
                self._btn_clients_act.setText("Arrêter")
            else:
                self._lbl_clients_status.setText("STOPPED")
                self._lbl_clients_status.setStyleSheet("color: #f38ba8; font-weight: bold;")
                self._lbl_clients_info.setText("—")
                self._btn_clients_act.setText("Démarrer")

        except Exception as e:
            logger.debug("Error during stats refresh: %s", e)

    def _toggle_room_service(self) -> None:
        room_svc = getattr(self._main_window, "_room_service", None)
        if room_svc is None:
            return
        if getattr(room_svc, "_running", False):
            room_svc.arreter()
        else:
            room_svc.demarrer()
        self.refresh_stats()

    def _toggle_clients_service(self) -> None:
        layout = getattr(self._main_window, "_layout", None)
        if layout is None or not hasattr(layout, "center"):
            return
        clients_svc = getattr(layout.center, "_clients_actifs_service", None)
        if clients_svc is None:
            return
        if getattr(clients_svc, "_running", False):
            clients_svc.arreter()
        else:
            clients_svc.demarrer()
        self.refresh_stats()

    # ── Thread-Safe Asyncio Event Loop Inspector ─────────────────────────────

    def refresh_asyncio_tasks(self) -> None:
        """Fetch all running asyncio tasks from the Connection Thread's event loop
        to diagnose deadlocks, pending awaits, or blocked execution paths.

        Ajoute un header de diagnostic dans le QTreeWidget avec l'état de santé
        de la boucle (running/stopped, nb tâches, exceptions récentes).
        """
        mgr = getattr(self._main_window, "_connexion_manager", None)
        if mgr is None or not hasattr(mgr, "_async_thread"):
            self._update_tasks_list_ui([], "Aucun ConnexionManager — thread asyncio introuvable")
            return

        thread = getattr(mgr, "_async_thread", None)
        if thread is None:
            self._update_tasks_list_ui([], "Thread asyncio non initialisé")
            return

        loop = getattr(thread, "_loop", None)
        if loop is None:
            self._update_tasks_list_ui([], "Boucle asyncio non créée")
            return

        if not loop.is_running():
            self._update_tasks_list_ui([], "🔴 Boucle asyncio ARRÊTÉE — thread mort ou exception non gérée")
            logger.warning("ServiceInspector: la boucle asyncio du ConnexionManager est arrêtée !")
            return

        logger.debug("ServiceInspector: boucle asyncio active — lancement de l'inspection")

        # Query all tasks on their target event loop thread-safely
        # On exclut nos propres tâches d'inspection pour éviter le bruit
        total_brut = [0]  # mutable pour closure interne

        def query_loop_tasks() -> list[tuple[str, str, str, str]]:
            task_instances = asyncio.all_tasks(loop)
            total_brut[0] = len(task_instances)
            results = []
            for t in task_instances:
                coro = t.get_coro()
                qualname = getattr(coro, "__qualname__", "")

                # ══ Filtre : ignorer nos propres wrapper d'inspection ══
                # Les tâches _async_wrapper sont créées par nous-mêmes
                # pour interroger la boucle — les inclure serait du bruit.
                if "_async_wrapper" in qualname or "query_loop_tasks" in qualname:
                    continue

                frame = None
                if hasattr(coro, "cr_frame"):
                    frame = coro.cr_frame
                elif hasattr(coro, "gi_frame"):
                    frame = coro.gi_frame

                stack_str = ""
                if frame:
                    tb = traceback.extract_stack(frame)
                    if tb:
                        f_info = tb[-1]
                        filename = f_info.filename.split('/')[-1].split('\\')[-1]
                        stack_str = f"{filename}:{f_info.lineno} ({f_info.name})"

                results.append((
                    t.get_name(),
                    qualname or str(coro),
                    t._state if hasattr(t, "_state") else "PENDING",
                    stack_str
                ))
            logger.debug("ServiceInspector: %d tâches brutes, %d après filtrage", total_brut[0], len(results))
            return results

        def future_done(future) -> None:
            try:
                res = future.result()
                self._emitter.tasks_received.emit(res)
            except Exception as e:
                logger.debug("Exception fetching asyncio tasks: %s", e)

        # Dispatches standard function to run soon in loop
        fut = asyncio.run_coroutine_threadsafe(self._async_wrapper(query_loop_tasks), loop)
        fut.add_done_callback(future_done)

    async def _async_wrapper(self, sync_func) -> list:
        return sync_func()

    def _on_tasks_received(self, tasks: list) -> None:
        self._update_tasks_list_ui(tasks)

    def _update_tasks_list_ui(self, tasks: list, health_msg: str = "") -> None:
        self._tasks_tree.clear()

        # ── Ligne de diagnostic de la boucle (si présente) ──
        if health_msg:
            diag_item = QTreeWidgetItem([health_msg])
            diag_item.setForeground(0, QColor("#f9e2af" if "ARRÊTÉE" in health_msg else "#89b4fa"))
            diag_item.setFlags(Qt.ItemFlag.NoItemFlags)  # non sélectionnable
            font = diag_item.font(0)
            font.setBold(True)
            diag_item.setFont(0, font)
            self._tasks_tree.addTopLevelItem(diag_item)
            # Si la boucle est arrêtée, on s'arrête là (pas de tâches à montrer)
            if "ARRÊTÉE" in health_msg:
                return

        if not tasks:
            item = QTreeWidgetItem(["Aucune tâche asyncio active dans la boucle"])
            self._tasks_tree.addTopLevelItem(item)
            return

        for name, coro, state, position in tasks:
            item = QTreeWidgetItem([name, coro, state, position])
            
            # Change text colors depending on whether they are stuck on server calls
            if "server-ping" in name:
                item.setForeground(0, QColor("#89b4fa"))
            elif "login" in coro or "handshake" in coro or "connect" in coro:
                item.setForeground(0, QColor("#f9e2af"))
                item.setForeground(1, QColor("#f9e2af"))
            
            self._tasks_tree.addTopLevelItem(item)

    # ── Thread-Isolated Diagnostic Connectivity Test ────────────────────────

    def _run_isolated_diagnostic(self) -> None:
        """Start the isolated network test thread to prove server availability."""
        self._diag_console.clear()
        self._btn_run_diag.setEnabled(False)
        self._btn_run_diag.setText("⚠️ DIAGNOSTIC EN COURS...")

        # Extract values
        user = self._diag_user.text().strip() or cfg_get("reseau.nom_utilisateur", "TesterBeats123")
        passwd = self._diag_pass.text().strip() or cfg_get("reseau.mot_de_passe", "testpassword")
        try:
            port = int(self._diag_port.text().strip())
        except ValueError:
            port = 2242

        # Spawn worker
        worker = DiagnosticWorker(port, user, passwd, self._emitter.diagnostic_log)
        
        # Enable button back when thread finishes
        def on_thread_complete() -> None:
            self._btn_run_diag.setEnabled(True)
            self._btn_run_diag.setText("🚀 LANCER TEST DE DIAGNOSTIC DE CONNEXION BRUTE")

        # Start thread
        class MonitorThread(threading.Thread):
            def run(self) -> None:
                worker.start()
                worker.join()
                QTimer.singleShot(0, on_thread_complete)

        MonitorThread().start()

    def _on_diagnostic_log(self, html_msg: str) -> None:
        self._diag_console.append(html_msg)
        # pyrefly: ignore [missing-attribute]
        self._diag_console.moveCursor(QTextCursor.End)

        # Transmettre également au moniteur de connexion
        if hasattr(self, "_connexion_monitor"):
            # Analyser le message pour détecter les résultats de login
            if "Authentification" in html_msg and "succès" in html_msg:
                self._connexion_monitor.log_attempt(
                    self._diag_user.text().strip() or "(config)",
                    "SUCCÈS"
                )
            elif "TIMEOUT" in html_msg or "rate-limit" in html_msg.lower():
                self._connexion_monitor.log_attempt(
                    self._diag_user.text().strip() or "(config)",
                    "TIMEOUT"
                )
            elif "Échec" in html_msg or "Erreur" in html_msg:
                self._connexion_monitor.log_attempt(
                    self._diag_user.text().strip() or "(config)",
                    "ÉCHEC"
                )

    # ── Console Log Handling — Filtres & Copie ────────────────────────────

    def _should_show_log(self, level: str, logger_name: str) -> bool:
        """Retourne True si le log doit être affiché selon les filtres actifs.

        Vérifie à la fois le niveau (ERROR/WARNING/INFO/DEBUG) et
        le service/logger (filtres dynamiques).
        """
        # Vérification du niveau
        if level == "ERROR" or level == "CRITICAL":
            if not self._chk_error.isChecked():
                return False
        elif level == "WARNING":
            if not self._chk_warning.isChecked():
                return False
        elif level == "DEBUG":
            if not self._chk_debug.isChecked():
                return False
        else:  # INFO et autres
            if not self._chk_info.isChecked():
                return False

        # Vérification du service/logger
        if logger_name in self._chk_loggers:
            return self._chk_loggers[logger_name].isChecked()

        # Nouveau logger inconnu → affiché par défaut
        return True

    def _reapply_log_filter(self) -> None:
        """Re-filtre tous les logs selon les checkboxes actives."""
        self._logs_text.clear()
        for level, logger_name, html_msg in self._log_entries:
            if self._should_show_log(level, logger_name):
                self._logs_text.append(html_msg)
        # pyrefly: ignore [missing-attribute]
        self._logs_text.moveCursor(QTextCursor.End)

    def _select_all_filters(self) -> None:
        """Coche tous les filtres de niveau."""
        self._chk_error.setChecked(True)
        self._chk_warning.setChecked(True)
        self._chk_info.setChecked(True)
        self._chk_debug.setChecked(True)

    def _deselect_all_filters(self) -> None:
        """Décoche tous les filtres de niveau."""
        self._chk_error.setChecked(False)
        self._chk_warning.setChecked(False)
        self._chk_info.setChecked(False)
        self._chk_debug.setChecked(False)

    def _copy_filtered_logs(self) -> None:
        """Copie le contenu visible (filtré) des logs dans le presse-papier."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self._logs_text.toPlainText())

    def _update_logger_filters(self, logger_name: str) -> None:
        """Ajoute une checkbox pour un nouveau logger si pas déjà présent.

        Crée une checkbox avec le nom court du logger (dernier segment)
        et le nom complet en tooltip. Tous les nouveaux loggers sont
        cochés par défaut.
        """
        if logger_name in self._chk_loggers:
            return

        # Nom d'affichage : dernier segment du namespace
        display_name = logger_name.split(".")[-1]

        chk = QCheckBox(display_name)
        chk.setChecked(True)
        chk.setToolTip(logger_name)
        chk.toggled.connect(self._reapply_log_filter)
        chk.setStyleSheet("color: #a6adc8; font-size: 9px;")

        self._chk_loggers[logger_name] = chk
        self._loggers_layout.addWidget(chk)

    def _select_all_loggers(self) -> None:
        """Coche tous les filtres de service."""
        for chk in self._chk_loggers.values():
            chk.setChecked(True)

    def _deselect_all_loggers(self) -> None:
        """Décoche tous les filtres de service."""
        for chk in self._chk_loggers.values():
            chk.setChecked(False)

    def append_log(self, level: str, logger_name: str, msg: str) -> None:
        """Append services logs inside scrollable console tab."""
        if not self._logs_text:
            return

        # Restrict captured logs to system scope packages for clarity
        if not any(pkg in msg for pkg in ("src.services", "aioslsk", "src.gui")):
            return

        # Ajouter la checkbox pour ce logger si nouveau
        self._update_logger_filters(logger_name)

        color = "#cdd6f4"
        if level == "INFO":
            if "SUCCÈS" in msg or "réussie" in msg or "démarré avec" in msg:
                color = "#a6e3a1"
            else:
                color = "#89b4fa"
        elif level == "WARNING":
            color = "#f9e2af"
        elif level == "ERROR" or level == "CRITICAL":
            color = "#f38ba8"
        elif level == "DEBUG":
            color = "#6c7086"

        html_msg = f'<font color="{color}">{msg}</font>'

        # Stocker pour re-filtrage futur
        self._log_entries.append((level, logger_name, html_msg))

        # N'afficher que si le filtre le permet
        if self._should_show_log(level, logger_name):
            self._logs_text.append(html_msg)
            # pyrefly: ignore [missing-attribute]
            self._logs_text.moveCursor(QTextCursor.End)

    def closeEvent(self, event) -> None:
        """Ferme l'inspecteur et sauvegarde tous les logs collectés dans un fichier."""
        self._save_logs()
        logging.getLogger().removeHandler(self._log_handler)
        self._poll_timer.stop()
        super().closeEvent(event)

    def _save_logs(self) -> None:
        """Sauvegarde la totalité des logs bruts dans ``data/logs/``.

        Le fichier est horodaté (``inspector_YYYYMMDD_HHMMSS.log``) pour
        éviter tout écrasement. Les balises HTML sont retirées pour
        obtenir du texte clair et lisible.
        """
        if not self._log_entries:
            logger.debug("ServiceInspector: aucun log à sauvegarder")
            return

        log_dir = Path("data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = log_dir / f"inspector_{timestamp}.log"

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                # En-tête du fichier
                f.write(f"# Session Inspector — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# {len(self._log_entries)} entrées de log\n\n")

                for level, logger_name, html_msg in self._log_entries:
                    # Nettoyer le HTML pour obtenir du texte brut
                    text = re.sub(r"<[^>]+>", "", html_msg).strip()
                    f.write(f"[{level}] ({logger_name}) {text}\n")

            logger.info("Logs sauvegardés : %s (%d entrées)", filepath, len(self._log_entries))

        except Exception as e:
            logger.warning("Impossible de sauvegarder les logs : %s", e)
