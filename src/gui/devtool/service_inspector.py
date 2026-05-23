"""Service & Connection Inspector — Diagnostic & Developer Tool.

Allows deep inspection of all background active asyncio tasks, raw event loop calls,
and includes an isolated socket-level Diagnostic Connection test thread to bypass the application's
entire codebase and test raw networking capabilities.
"""

from __future__ import annotations

import asyncio
import functools
import json
import logging
import platform
import re
import socket
import time
import traceback
import threading
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDockWidget,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
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
from src.utils.log_action import log_action
from security.crash_reporter import register_crash_hook

logger = logging.getLogger("[SERVICE-INSPECTOR]")


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


# ── Helper : Contexte système ──────────────────────────────────────────

def _get_system_context() -> str:
    """Retourne une chaîne formatée avec le contexte système (OS, Python, mémoire)."""
    import os as _os
    import sys as _sys
    import platform as _platform
    lines = [
        f"# OS            : {_platform.platform()}",
        f"# Python        : {_sys.version.split()[0]}",
        f"# CPU           : {_os.cpu_count()} cœurs",
    ]
    try:
        import psutil
        mem = psutil.virtual_memory()
        total_gb = mem.total / (1024 ** 3)
        avail_gb = mem.available / (1024 ** 3)
        lines.append(f"# Mémoire RAM   : {total_gb:.1f} Go total — {avail_gb:.1f} Go disponible")
    except ImportError:
        lines.append("# Mémoire RAM   : psutil non installé — info indisponible")
    return "\n".join(lines)


    # ── Service Inspector main QDockWidget ────────────────────────────────────

class ServiceInspector(QDockWidget):
    """Ancillary Developer panel to inspect and control the active Soulseek client & services."""

    # ── Presets par defaut pre-installes ──────────────────────────────────
    # Ces presets sont fusionnes avec les presets sauvegardes par l'utilisateur
    # et apparaissent toujours dans la liste, meme si filter_presets.json n'existe pas.
    _DEFAULT_PRESETS: dict[str, dict] = {
        "⚡ Debug Réseau": {
            "levels": {"error": True, "warning": False, "info": False, "debug": True},
            "services": {},
            "limit": "200",
        },
        "🔴 Erreurs uniquement": {
            "levels": {"error": True, "warning": False, "info": False, "debug": False},
            "services": {},
            "limit": "100",
        },
        "📊 Surveillance complète": {
            "levels": {"error": True, "warning": True, "info": True, "debug": True},
            "services": {},
            "limit": "200",
        },
        "🐌 Performance": {
            "levels": {"error": True, "warning": True, "info": False, "debug": False},
            "services": {},
            "limit": "50",
        },
        "🌐 Connexion & Réseau": {
            "levels": {"error": True, "warning": True, "info": True, "debug": True},
            "services": {
                "[CONNEXION]": True, "[SOULSEEK]": True, "[EVENTBUS]": True,
                "[CONNEXION-WEB]": True, "[CONNEXION-MONITOR]": True,
            },
            "limit": "200",
        },
        "🔍 Recherche & Téléchargement": {
            "levels": {"error": True, "warning": True, "info": True, "debug": True},
            "services": {
                "[RECHERCHE]": True, "[TELECHARGEMENT]": True, "[WISHLIST]": True,
                "[RECHERCHE-HIST]": True, "[RECHERCHE-MODES]": True,
                "[TELECHARGEMENT-HIST]": True,
            },
            "limit": "200",
        },
        "🤖 Bots uniquement": {
            "levels": {"error": True, "warning": True, "info": True, "debug": True},
            "services": {
                "[ACCUEIL]": True, "[SURVEILLANCE]": True, "[PLANIFICATEUR]": True,
                "[OPTIMISEUR]": True, "[AIDE]": True, "[ASSISTANT]": True,
                "[ORDONNANCEUR]": True, "[ORDONNANCEUR-UI]": True,
                "[CLIENTS-ACTIFS]": True, "[CLIENTS-ACTIFS-UI]": True,
                "[BIBLIOTHEQUE]": True, "[BIBLIOTHEQUE-DB]": True,
                "[BIBLIOTHEQUE-UI]": True,
            },
            "limit": "200",
        },
        "⚠️ Erreurs + Warnings": {
            "levels": {"error": True, "warning": True, "info": False, "debug": False},
            "services": {},
            "limit": "Tout",
        },
    }

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
        self._btn_refresh.clicked.connect(self._on_refresh_all)
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
        self._poll_timer.timeout.connect(self.refresh_all)  # timer → pas de @log_action (évite le bruit)
        self._poll_timer.start()

        # ── Crash hook : sauvegarde automatique des logs si l'app plante ──
        register_crash_hook(self._save_logs_on_crash)

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
        self._btn_refresh_tasks.clicked.connect(self._on_refresh_asyncio_tasks)
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
        btn_clear_diag.clicked.connect(self._clear_diag_console)
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

        # ── Sélecteur de limite de logs ──
        lbl_limit = QLabel("Limit :")
        lbl_limit.setStyleSheet("color: #a6adc8; font-size: 10px;")
        toolbar.addWidget(lbl_limit)

        self._log_limit = QComboBox()
        self._log_limit.addItems(["Tout", "10", "50", "100", "150", "200"])
        self._log_limit.setCurrentIndex(0)
        self._log_limit.currentIndexChanged.connect(self._reapply_log_filter)
        self._log_limit.setStyleSheet(
            "QComboBox {"
            "  background: #313244; color: #cdd6f4;"
            "  border: 1px solid #45475a; border-radius: 3px;"
            "  padding: 1px 4px; font-size: 9px;"
            "}"
            "QComboBox::drop-down {"
            "  border: none; width: 16px;"
            "}"
            "QComboBox QAbstractItemView {"
            "  background: #1e1e2e; color: #cdd6f4;"
            "  selection-background-color: #45475a;"
            "}"
        )
        toolbar.addWidget(self._log_limit)

        toolbar.addStretch()

        self._btn_save_filtered = QPushButton("💾 Enregistrer")
        self._btn_save_filtered.setToolTip("Sauvegarder les logs filtrés dans data/logs/")
        self._btn_save_filtered.setStyleSheet(
            "background-color: #45475a; color: #cdd6f4; "
            "padding: 3px 8px; font-size: 9px; border-radius: 3px;"
        )
        self._btn_save_filtered.clicked.connect(self._save_filtered_logs)
        toolbar.addWidget(self._btn_save_filtered)

        self._btn_copy_logs = QPushButton("📋 Copier")
        self._btn_copy_logs.setToolTip("Copier les logs filtrés dans le presse-papier")
        self._btn_copy_logs.setStyleSheet(
            "background-color: #45475a; color: #cdd6f4; "
            "padding: 3px 8px; font-size: 9px; border-radius: 3px;"
        )
        self._btn_copy_logs.clicked.connect(self._copy_filtered_logs)
        toolbar.addWidget(self._btn_copy_logs)

        layout.addLayout(toolbar)

        # ── Liste de filtres par service (compacte) ──
        # Utilise une QListWidget avec items checkables, scrollable verticalement
        # et prenant un minimum de place (hauteur fixe ~6 lignes).
        # Ligne titre "Services :" + boutons Tout/Aucun à droite
        services_header = QHBoxLayout()
        services_header.setContentsMargins(0, 0, 0, 0)
        services_header.setSpacing(4)

        lbl_services = QLabel("Services :")
        lbl_services.setStyleSheet("color: #a6adc8; font-size: 10px;")
        services_header.addWidget(lbl_services)

        services_header.addStretch()

        self._btn_services_all = QPushButton("Tout")
        self._btn_services_all.setFixedWidth(45)
        self._btn_services_all.setStyleSheet(
            "background: #313244; color: #cdd6f4; "
            "padding: 2px 4px; font-size: 9px; border-radius: 3px;"
        )
        self._btn_services_all.clicked.connect(self._select_all_loggers)
        services_header.addWidget(self._btn_services_all)

        self._btn_services_none = QPushButton("Aucun")
        self._btn_services_none.setFixedWidth(45)
        self._btn_services_none.setStyleSheet(
            "background: #313244; color: #cdd6f4; "
            "padding: 2px 4px; font-size: 9px; border-radius: 3px;"
        )
        self._btn_services_none.clicked.connect(self._deselect_all_loggers)
        services_header.addWidget(self._btn_services_none)

        layout.addLayout(services_header)

        self._logger_list = QListWidget()
        self._logger_list.setObjectName("loggerFilterList")
        self._logger_list.setMaximumHeight(130)
        self._logger_list.setAlternatingRowColors(True)
        self._logger_list.itemChanged.connect(self._reapply_log_filter)
        self._logger_list.setStyleSheet(
            "QListWidget#loggerFilterList {"
            "  background: #11111b;"
            "  border: 1px solid #313244;"
            "  border-radius: 4px;"
            "  font-family: 'Consolas', 'Courier New', monospace;"
            "  font-size: 9px;"
            "  padding: 2px;"
            "}"
            "QListWidget#loggerFilterList::item {"
            "  padding: 1px 4px;"
            "  min-height: 14px;"
            "}"
            "QListWidget#loggerFilterList::item:alternate {"
            "  background: #1e1e2e;"
            "}"
        )
        layout.addWidget(self._logger_list)

        # ── Barre de presets de filtres ──
        preset_bar = QHBoxLayout()
        preset_bar.setContentsMargins(0, 0, 0, 4)
        preset_bar.setSpacing(4)

        lbl_presets = QLabel("🎯 Presets :")
        lbl_presets.setStyleSheet("color: #a6adc8; font-size: 10px; font-weight: bold;")
        preset_bar.addWidget(lbl_presets)

        self._preset_combo = QComboBox()
        self._preset_combo.addItem("─ Presets ─")
        self._preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        self._preset_combo.setMinimumWidth(160)
        self._preset_combo.setStyleSheet(
            "QComboBox {"
            "  background: #313244; color: #cdd6f4;"
            "  border: 1px solid #45475a; border-radius: 3px;"
            "  padding: 1px 4px; font-size: 9px;"
            "}"
            "QComboBox::drop-down {"
            "  border: none; width: 16px;"
            "}"
            "QComboBox QAbstractItemView {"
            "  background: #1e1e2e; color: #cdd6f4;"
            "  selection-background-color: #45475a;"
            "}"
        )
        preset_bar.addWidget(self._preset_combo)

        self._btn_save_preset = QPushButton("💾 Sauver")
        self._btn_save_preset.setToolTip("Sauvegarder les filtres actuels comme preset")
        self._btn_save_preset.setStyleSheet(
            "background: #45475a; color: #cdd6f4;"
            "  padding: 2px 6px; font-size: 9px; border-radius: 3px;"
        )
        self._btn_save_preset.clicked.connect(self._save_preset)
        preset_bar.addWidget(self._btn_save_preset)

        self._btn_delete_preset = QPushButton("🗑️ Suppr.")
        self._btn_delete_preset.setToolTip("Supprimer le preset sélectionné")
        self._btn_delete_preset.setStyleSheet(
            "background: #45475a; color: #cdd6f4;"
            "  padding: 2px 6px; font-size: 9px; border-radius: 3px;"
        )
        self._btn_delete_preset.clicked.connect(self._delete_preset)
        preset_bar.addWidget(self._btn_delete_preset)

        preset_bar.addStretch()

        layout.addLayout(preset_bar)

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

        # Pré-populer les filtres avec tous les loggers connus
        self._prepopulate_logger_filters()

        # ── Presets de filtres (persistance JSON) ──
        self._presets_file = Path("data/logs/filter_presets.json")
        self._presets: dict[str, dict] = {}
        # Charger les presets utilisateur + fusionner avec les presets par défaut
        self._load_presets_from_disk()

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

    @log_action("Rafraîchir tous les onglets")
    def _on_refresh_all(self) -> None:
        """Handler bouton — rafraîchit tous les onglets avec log d'action."""
        self.refresh_all()

    def refresh_all(self) -> None:
        """Invoked periodically (timer) to update service labels and asyncio active tasks."""
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

    @log_action("Suspendre/reprendre le polling")
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

    @log_action("Démarrer/arrêter le service salons")
    def _toggle_room_service(self) -> None:
        room_svc = getattr(self._main_window, "_room_service", None)
        if room_svc is None:
            return
        if getattr(room_svc, "_running", False):
            room_svc.arreter()
        else:
            room_svc.demarrer()
        self.refresh_stats()

    @log_action("Démarrer/arrêter le service clients actifs")
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

    @log_action("Rafraîchir les tâches asyncio")
    def _on_refresh_asyncio_tasks(self) -> None:
        """Handler bouton — rafraîchit les tâches asyncio avec log d'action."""
        self.refresh_asyncio_tasks()

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

    @log_action("Lancer le diagnostic de connexion")
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

    @log_action("Vider le terminal de diagnostic")
    def _clear_diag_console(self) -> None:
        """Vide le terminal de diagnostic."""
        self._diag_console.clear()

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

    def _logger_is_checked(self, logger_name: str) -> bool:
        """Vérifie si un logger est coché dans la QListWidget."""
        for i in range(self._logger_list.count()):
            item = self._logger_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == logger_name:
                return item.checkState() == Qt.CheckState.Checked
        # Logger inconnu → affiché par défaut
        return True

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

        # Vérification du service/logger via la QListWidget
        return self._logger_is_checked(logger_name)

    def _reapply_log_filter(self) -> None:
        """Re-filtre tous les logs selon les filtres actifs + limite N derniers.

        Applique successivement :
        1. Filtres de niveau (ERROR/WARNING/INFO/DEBUG)
        2. Filtres par service/logger
        3. Limite du nombre de logs (Tout / 10 / 50 / 100 / 150 / 200)
        """
        # Déterminer la limite
        limit_txt = self._log_limit.currentText()
        limit = 0 if limit_txt == "Tout" else int(limit_txt)

        self._logs_text.clear()

        # Collecter les entrées filtrées
        filtered: list[str] = []
        for level, logger_name, html_msg in self._log_entries:
            if self._should_show_log(level, logger_name):
                filtered.append(html_msg)

        # Appliquer la limite : garder les N derniers
        if limit > 0 and len(filtered) > limit:
            filtered = filtered[-limit:]

        for html_msg in filtered:
            self._logs_text.append(html_msg)
        # pyrefly: ignore [missing-attribute]
        self._logs_text.moveCursor(QTextCursor.End)

    @log_action("Niveaux : tout sélectionner")
    def _select_all_filters(self) -> None:
        """Coche tous les filtres de niveau."""
        self._chk_error.setChecked(True)
        self._chk_warning.setChecked(True)
        self._chk_info.setChecked(True)
        self._chk_debug.setChecked(True)

    @log_action("Niveaux : tout désélectionner")
    def _deselect_all_filters(self) -> None:
        """Décoche tous les filtres de niveau."""
        self._chk_error.setChecked(False)
        self._chk_warning.setChecked(False)
        self._chk_info.setChecked(False)
        self._chk_debug.setChecked(False)

    @log_action("Copier les logs filtrés dans le presse-papier")
    def _copy_filtered_logs(self) -> None:
        """Copie le contenu visible (filtré) des logs dans le presse-papier."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self._logs_text.toPlainText())

    @log_action("Sauvegarder les logs filtrés")
    def _save_filtered_logs(self) -> None:
        """Sauvegarde UNIQUEMENT les logs filtrés (visibles) dans ``data/logs/``.

        Génère un fichier ``filtered_YYYYMMDD_HHMMSS.log`` contenant le texte
        brut (sans HTML) des logs actuellement affichés, utile pour envoyer
        un extrait ciblé à un développeur.

        Affiche un feedback visuel temporaire sur le bouton ("✅ Sauvé !")
        pour que l'utilisateur sache que la sauvegarde a bien eu lieu.
        """
        plain_text = self._logs_text.toPlainText().strip()
        if not plain_text:
            logger.info("ServiceInspector: aucun log filtré à sauvegarder")
            # Feedback visuel : bouton clignote en orange "⚠️ Vide"
            self._btn_save_filtered.setText("⚠️ Vide")
            self._btn_save_filtered.setStyleSheet(
                "background-color: #f9e2af; color: #11111b; "
                "padding: 3px 8px; font-size: 9px; border-radius: 3px;"
            )
            QTimer.singleShot(2000, self._restore_save_btn_style)
            return

        log_dir = Path("data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = log_dir / f"filtered_{timestamp}.log"

        # Extraire les infos du filtre actif pour l'en-tête
        niveaux = []
        if self._chk_error.isChecked():
            niveaux.append("ERROR")
        if self._chk_warning.isChecked():
            niveaux.append("WARNING")
        if self._chk_info.isChecked():
            niveaux.append("INFO")
        if self._chk_debug.isChecked():
            niveaux.append("DEBUG")

        services_actifs = [
            name for name in self._STANDARD_LOGGERS
            if self._logger_is_checked(name)
        ]

        limit_txt = self._log_limit.currentText()

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                ts = datetime.now()
                f.write(f"# ================================================================================\n")
                f.write(f"#  SESSION INSPECTOR — Export filtré de logs\n")
                f.write(f"# ================================================================================\n")
                f.write(f"#\n")
                f.write(f"# QUI SUIS-JE ?\n")
                f.write(f"#   Extraits ciblés de logs exportés depuis l'onglet « Flux des Logs »\n")
                f.write(f"#   du Service & Connection Inspector. Seuls les logs correspondant\n")
                f.write(f"#   aux filtres actifs au moment de l'export sont inclus.\n")
                f.write(f"#\n")
                f.write(f"# À QUOI JE SERS ?\n")
                f.write(f"#   Partager avec un développeur un extrait précis et reproductible\n")
                f.write(f"#   de logs pour diagnostiquer un problème spécifique. Les filtres\n")
                f.write(f"#   appliqués sont documentés ci-dessous.\n")
                f.write(f"#\n")
                f.write(f"# QUE FAIRE AVEC CE FICHIER ?\n")
                f.write(f"#   1. Ouvrir dans un éditeur de texte pour analyser les logs.\n")
                f.write(f"#   2. Les filtres ci-dessous indiquent le contexte exact de l'export\n")
                f.write(f"#      (niveaux, services, limite de nombre).\n")
                f.write(f"#   3. Si le problème est reproductible, fournir aussi le fichier\n")
                f.write(f"#      de session complet (inspector_*.log) pour corrélation.\n")
                f.write(f"#\n")
                f.write(f"# ================================================================================\n")
                f.write(f"# Généré le    : {ts.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Filtres niv. : {' '.join(niveaux) if niveaux else '(aucun)'}\n")
                f.write(f"# Limite       : {limit_txt}\n")
                if services_actifs:
                    f.write(f"# Services     : {', '.join(sorted(services_actifs))}\n")
                f.write(f"# Lignes       : {len(plain_text.splitlines())}\n")
                f.write(f"#\n")
                f.write(f"# --- Contexte système ---\n")
                f.write(_get_system_context() + "\n")
                f.write(f"# ================================================================================\n\n")
                f.write(plain_text)
                f.write("\n")

            logger.info("Logs filtrés sauvegardés : %s", filepath)
            # Feedback visuel : bouton passe en vert "✅ Sauvé !" 2s
            self._btn_save_filtered.setText("✅ Sauvé !")
            self._btn_save_filtered.setStyleSheet(
                "background-color: #a6e3a1; color: #11111b; font-weight: bold; "
                "padding: 3px 8px; font-size: 9px; border-radius: 3px;"
            )
            QTimer.singleShot(2000, self._restore_save_btn_style)

        except Exception as e:
            logger.warning("Impossible de sauvegarder les logs filtrés : %s", e)
            # Feedback visuel : bouton passe en rouge "❌ Erreur" 2s
            self._btn_save_filtered.setText("❌ Erreur")
            self._btn_save_filtered.setStyleSheet(
                "background-color: #f38ba8; color: #11111b; font-weight: bold; "
                "padding: 3px 8px; font-size: 9px; border-radius: 3px;"
            )
            QTimer.singleShot(2000, self._restore_save_btn_style)

    # ── Presets de filtres (sauvegarde/chargement) ──────────────────────

    def _on_preset_selected(self, index: int) -> None:
        """Charge le preset sélectionné dans le combo."""
        if index <= 0:
            return  # ignorer le placeholder "─ Presets ─"
        name = self._preset_combo.currentText()
        if name in self._presets:
            self._load_preset(name)

    @log_action("Sauvegarder un preset")
    def _save_preset(self) -> None:
        """Demande un nom et sauvegarde les filtres actuels comme preset."""
        name, ok = QInputDialog.getText(
            self, "Sauvegarder un preset",
            "Nom du preset :", text=""
        )
        if not ok or not name.strip():
            return
        name = name.strip()

        # Capturer l'état actuel de tous les filtres via la QListWidget
        services = {}
        for i in range(self._logger_list.count()):
            item = self._logger_list.item(i)
            if item:
                logger_name = item.data(Qt.ItemDataRole.UserRole)
                services[logger_name] = (item.checkState() == Qt.CheckState.Checked)

        preset: dict[str, Any] = {
            "levels": {
                "error": self._chk_error.isChecked(),
                "warning": self._chk_warning.isChecked(),
                "info": self._chk_info.isChecked(),
                "debug": self._chk_debug.isChecked(),
            },
            "services": services,
            "limit": self._log_limit.currentText(),
        }

        self._presets[name] = preset
        self._rebuild_preset_combo(name)
        self._save_presets_to_disk()
        logger.info("Preset sauvegardé : %s", name)

    def _load_preset(self, name: str) -> None:
        """Restaure l'état des filtres depuis un preset."""
        preset = self._presets.get(name)
        if preset is None:
            return

        # Restaurer les niveaux
        levels = preset.get("levels", {})
        self._chk_error.setChecked(levels.get("error", True))
        self._chk_warning.setChecked(levels.get("warning", True))
        self._chk_info.setChecked(levels.get("info", True))
        self._chk_debug.setChecked(levels.get("debug", True))

        # Restaurer la limite
        limit = preset.get("limit", "Tout")
        idx = self._log_limit.findText(limit)
        if idx >= 0:
            self._log_limit.setCurrentIndex(idx)

        # Restaurer les services via la QListWidget
        services = preset.get("services", {})
        for i in range(self._logger_list.count()):
            item = self._logger_list.item(i)
            if item:
                logger_name = item.data(Qt.ItemDataRole.UserRole)
                if logger_name and logger_name in services:
                    checked = services[logger_name]
                    item.setCheckState(
                        Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
                    )

        # Ré-appliquer le filtre
        self._reapply_log_filter()
        logger.info("Preset chargé : %s", name)

    @log_action("Supprimer un preset")
    def _delete_preset(self) -> None:
        """Supprime le preset actuellement sélectionné."""
        name = self._preset_combo.currentText()
        if name in self._presets:
            del self._presets[name]
            self._rebuild_preset_combo()
            self._save_presets_to_disk()
            logger.info("Preset supprimé : %s", name)

    def _rebuild_preset_combo(self, select_name: str | None = None) -> None:
        """Reconstruit la liste déroulante des presets."""
        self._preset_combo.blockSignals(True)
        self._preset_combo.clear()
        self._preset_combo.addItem("─ Presets ─")
        for name in sorted(self._presets.keys()):
            self._preset_combo.addItem(name)
        self._preset_combo.blockSignals(False)

        if select_name and select_name in self._presets:
            idx = self._preset_combo.findText(select_name)
            if idx >= 0:
                self._preset_combo.setCurrentIndex(idx)

    def _save_presets_to_disk(self) -> None:
        """Persiste les presets dans ``data/logs/filter_presets.json``."""
        try:
            self._presets_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._presets_file, "w", encoding="utf-8") as f:
                json.dump(self._presets, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning("Impossible de sauvegarder les presets : %s", e)

    def _load_presets_from_disk(self) -> None:
        """Charge les presets depuis ``data/logs/filter_presets.json``
        et les fusionne avec les presets par défaut pré-installés.

        Les presets utilisateur écrasent les defaults en cas de conflit de nom.
        Les defaults absents du fichier sont quand même ajoutés au combo.
        """
        merged: dict[str, dict] = deepcopy(self._DEFAULT_PRESETS)

        if self._presets_file.exists():
            try:
                with open(self._presets_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    merged.update(data)
            except Exception as e:
                logger.warning("Impossible de charger les presets : %s", e)

        self._presets = merged
        self._rebuild_preset_combo()
        logger.debug("%d presets chargés (%d par défaut + utilisateur)",
                     len(self._presets), len(self._DEFAULT_PRESETS))

    # ── Loggers standards connus (pré-population des filtres) ──
    _STANDARD_LOGGERS: list[str] = [
        # Phase 1 — Core services
        "[CONNEXION]", "[SOULSEEK]", "[EVENTBUS]",
        # Phase 2 — Boucles et bots
        "[ROOMS-LOOP]", "[CLIENTS-ACTIFS]", "[RECHERCHE]",
        "[TELECHARGEMENT]", "[SURVEILLANCE]", "[WISHLIST]",
        "[PLANIFICATEUR]", "[ACCUEIL]", "[OPTIMISEUR]",
        # Phase 3 — Services secondaires
        "[ROOMS-SERVICE]", "[BIBLIOTHEQUE]", "[WORKFLOW]",
        # Phase 4a — Services / infrastructure
        "[APP-CONFIG]", "[CONNEXION-WEB]", "[BIBLIOTHEQUE-DB]",
        "[ORDONNANCEUR]", "[MAIN-WINDOW]", "[RECHERCHE-HIST]",
        "[QSS-INSPECTOR]", "[SERVICE-INSPECTOR]", "[CENTER-ZONE]",
        "[CLIENTS-ACTIFS-UI]", "[PLANIFICATEUR-SRV]", "[TOAST]",
        "[TELECHARGEMENT-HIST]",
        # Phase 4b — Widgets / diagnostics / bots restants
        "[ASYNCIO-INSPECTOR]", "[ORDONNANCEUR-UI]", "[CONNEXION-MONITOR]",
        "[TIMEOUT-CTRL]", "[SYSINTERNALS]", "[AIDE]",
        "[ASSISTANT]", "[BIBLIOTHEQUE-UI]", "[RECHERCHE-MODES]",
        # Actions utilisateur
        "[ACTION-LOG]",
        # Diagnostics
        "[DIAG]",
    ]

    def _prepopulate_logger_filters(self) -> None:
        """Crée les items de filtre pour tous les loggers standards.

        Appelée une fois dans _setup_tab_logs() pour que les filtres
        soient disponibles dès l'ouverture de l'onglet, sans attendre
        qu'un premier log arrive.
        """
        for name in self._STANDARD_LOGGERS:
            self._update_logger_filters(name)

    def _update_logger_filters(self, logger_name: str) -> None:
        """Ajoute une entrée dans la QListWidget pour un nouveau logger.

        Crée un QListWidgetItem checkable avec le nom court du logger
        et le nom complet en tooltip. Tous les nouveaux loggers sont
        cochés par défaut.
        """
        # Vérifier si déjà présent
        for i in range(self._logger_list.count()):
            item = self._logger_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == logger_name:
                return

        # Nom d'affichage : retirer les crochets pour plus de lisibilité
        display_name = logger_name.strip("[]")

        list_item = QListWidgetItem(display_name)
        list_item.setFlags(list_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        list_item.setCheckState(Qt.CheckState.Checked)
        list_item.setToolTip(logger_name)
        list_item.setData(Qt.ItemDataRole.UserRole, logger_name)

        self._logger_list.addItem(list_item)

    def _select_all_loggers(self) -> None:
        """Coche tous les filtres de service."""
        for i in range(self._logger_list.count()):
            item = self._logger_list.item(i)
            if item:
                item.setCheckState(Qt.CheckState.Checked)

    def _deselect_all_loggers(self) -> None:
        """Décoche tous les filtres de service."""
        for i in range(self._logger_list.count()):
            item = self._logger_list.item(i)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)

    def append_log(self, level: str, logger_name: str, msg: str) -> None:
        """Append services logs inside scrollable console tab."""
        if not self._logs_text:
            return

        # Ajouter la checkbox pour ce logger si nouveau (dynamique)
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

        # Vérifier si une limite est active → ré-appliquer le filtre complet
        limit_txt = self._log_limit.currentText()
        if limit_txt != "Tout":
            limit = int(limit_txt)
            # Compter le nombre actuel de logs visibles
            visible = sum(1 for lv, ln, _ in self._log_entries
                         if self._should_show_log(lv, ln))
            if visible > limit:
                self._reapply_log_filter()
                return

        # N'afficher que si le filtre le permet
        if self._should_show_log(level, logger_name):
            self._logs_text.append(html_msg)
            # pyrefly: ignore [missing-attribute]
            self._logs_text.moveCursor(QTextCursor.End)

    def showEvent(self, event) -> None:
        """L'inspecteur devient visible → relance le timer de rafraîchissement."""
        if hasattr(self, "_poll_timer") and not self._poll_timer.isActive():
            self._poll_timer.start()
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        """L'inspecteur est masqué → arrête le timer pour ne pas spam la boucle asyncio.

        Le ServiceInspector spamme la boucle asyncio toutes les 1,5 s via
        ``asyncio.run_coroutine_threadsafe()``. Quand le dock est fermé/caché,
        on coupe le timer pour éviter de noyer la boucle et causer un crash.
        """
        if hasattr(self, "_poll_timer") and self._poll_timer.isActive():
            self._poll_timer.stop()
        super().hideEvent(event)

    def closeEvent(self, event) -> None:
        """Ferme l'inspecteur et sauvegarde tous les logs collectés dans un fichier."""
        self._save_logs()
        logging.getLogger().removeHandler(self._log_handler)
        self._poll_timer.stop()
        super().closeEvent(event)

    def _write_log_file(self, filepath: Path, entries: list, is_crash: bool = False) -> None:
        """Écrit les entrées de log dans un fichier avec l'en-tête approprié.

        Méthode partagée par ``_save_logs()`` et ``_save_logs_on_crash()``
        pour éviter la duplication de code.

        Paramètres
        ----------
        filepath : Path
            Chemin complet du fichier à écrire.
        entries : list
            Liste des entrées (level, logger_name, html_msg).
        is_crash : bool
            Si True, en-tête "CRASH" avec message explicite.
        """
        ts = datetime.now()
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# ================================================================================\n")
            if is_crash:
                f.write(f"#  SESSION INSPECTOR — CRASH — Arrêt brutal de l'application\n")
                f.write(f"# ================================================================================\n")
                f.write(f"#\n")
                f.write(f"# ❌ JE VIENS DE PLANTER !\n")
                f.write(f"#    Vérifier les logs et lancer un 'code-review' sur le code\n")
                f.write(f"#    pour identifier la cause racine.\n")
                f.write(f"#    Corréler avec le crash report 'security/crash_*.log'.\n")
                f.write(f"#\n")
                f.write(f"# QUI SUIS-JE ?\n")
                f.write(f"#   Archive intégrale de logs sauvegardée automatiquement lors\n")
                f.write(f"#   de l'arrêt brutal de l'application (crash).\n")
                f.write(f"#\n")
                f.write(f"# À QUOI JE SERS ?\n")
                f.write(f"#   Permettre une analyse rétrospective immédiate de la session\n")
                f.write(f"#   qui a précédé le crash, sans perte d'information.\n")
                f.write(f"#\n")
                f.write(f"# QUE FAIRE AVEC CE FICHIER ?\n")
                f.write(f"#   1. Ouvrir ce fichier en même temps que le crash report\n")
                f.write(f"#      (security/crash_*.log) pour une corrélation temporelle.\n")
                f.write(f"#   2. Chercher les dernières entrées avant le crash pour\n")
                f.write(f"#      identifier le contexte de l'erreur.\n")
                f.write(f"#   3. Transmettre les deux fichiers au développeur.\n")
                f.write(f"#\n")
            else:
                f.write(f"#  SESSION INSPECTOR — Journal complet de session\n")
                f.write(f"# ================================================================================\n")
                f.write(f"#\n")
                f.write(f"# QUI SUIS-JE ?\n")
                f.write(f"#   Archive intégrale de tous les logs émis par l'application aioslsk\n")
                f.write(f"#   pendant la session de l'outil Service & Connection Inspector.\n")
                f.write(f"#\n")
                f.write(f"# À QUOI JE SERS ?\n")
                f.write(f"#   Permettre une analyse rétrospective complète du comportement de\n")
                f.write(f"#   l'application : tous les niveaux (ERROR, WARNING, INFO, DEBUG)\n")
                f.write(f"#   et tous les services (aioslsk, src.services, src.gui, boucle_rooms)\n")
                f.write(f"#   sont enregistrés sans filtre pour ne rien perdre.\n")
                f.write(f"#\n")
                f.write(f"# QUE FAIRE AVEC CE FICHIER ?\n")
                f.write(f"#   1. Ouvrir dans un éditeur de texte ou un outil d'analyse de logs.\n")
                f.write(f"#   2. Filtrer par niveau ([ERROR], [WARNING], [INFO], [DEBUG]) pour\n")
                f.write(f"#      isoler les événements importants.\n")
                f.write(f"#   3. Filtrer par service ((aioslsk.events), (boucle_rooms), …) pour\n")
                f.write(f"#      cibler un module spécifique.\n")
                f.write(f"#   4. Corréler avec un éventuel crash report (security/crash_*.log)\n")
                f.write(f"#      survenu au même moment.\n")
                f.write(f"#\n")
            f.write(f"# ================================================================================\n")
            ctx = _get_system_context()
            f.write(f"# Généré le  : {ts.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Entrées    : {len(entries)}\n")
            f.write(f"#\n")
            f.write(f"# --- Contexte système ---\n")
            f.write(ctx + "\n")
            f.write(f"# ================================================================================\n\n")
            for level, logger_name, html_msg in entries:
                text = re.sub(r"<[^>]+>", "", html_msg).strip()
                f.write(f"[{level}] ({logger_name}) {text}\n")

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
            self._write_log_file(filepath, self._log_entries, is_crash=False)
            logger.info("Logs sauvegardés : %s (%d entrées)", filepath, len(self._log_entries))
        except Exception as e:
            logger.warning("Impossible de sauvegarder les logs : %s", e)

    def _save_logs_on_crash(self) -> None:
        """Hook appelé par le Crash Reporter avant ``os._exit(1)``.

        Sauvegarde les logs avec un indicateur "CRASH" dans le fichier
        et dans l'en-tête. Cette méthode est thread-safe (pas de Qt)
        et n'utilise pas ``logging`` pour éviter les re-entrées.
        """
        # Copier la liste pour éviter les modifications concurrentes
        entries = list(self._log_entries)
        if not entries:
            return
        log_dir = Path("data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = log_dir / f"inspector_{timestamp}_crash.log"
        try:
            self._write_log_file(filepath, entries, is_crash=True)
        except Exception:
            pass  # on ne peut plus rien faire

    def _restore_save_btn_style(self) -> None:
        """Restaure le style par défaut du bouton Enregistrer après le feedback visuel."""
        self._btn_save_filtered.setText("\U0001f4be Enregistrer")
        self._btn_save_filtered.setStyleSheet(
            "background-color: #45475a; color: #cdd6f4; "
            "padding: 3px 8px; font-size: 9px; border-radius: 3px;"
        )
        logger.debug("ServiceInspector: bouton Enregistrer restauré")

