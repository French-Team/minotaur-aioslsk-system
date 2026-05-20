"""Moniteur temps réel de la machine à états de connexion Soulseek.

Affiche l'état des flag ``_connecting``, ``_cancel_requested``, ``is_connected``,
``_generating``, et l'état du thread asyncio. Maintient un historique des
transitions d'état pour faciliter le diagnostic des blocages.
"""

from __future__ import annotations

import datetime
import logging
from collections import deque
from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.services.app_config import get as cfg_get
from src.services.soulseek_client import soulseek_service

logger = logging.getLogger(__name__)


class ConnexionMonitorWidget(QFrame):
    """Widget de monitoring en temps réel de la connexion Soulseek.

    Affiche les drapeaux internes, l'état du thread, et un historique
    des transitions.
    """

    MAX_HISTORY = 100

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._main_window: Any = None
        self._prev_state: dict[str, Any] = {}
        self._history: deque[tuple[str, str, str]] = deque(maxlen=self.MAX_HISTORY)

        self._build_ui()

    def set_main_window(self, main_window: Any) -> None:
        """Injecte la fenêtre principale pour accéder au ConnexionManager."""
        self._main_window = main_window

    # ── Construction UI ─────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # ── Bannière titre ──
        titre = QLabel("📊  MONITEUR ÉTAT CONNEXION  (machine à états)")
        titre.setStyleSheet(
            "font-weight: bold; color: #89b4fa; font-size: 11px; "
            "background: #181825; border-radius: 4px; padding: 6px;"
        )
        layout.addWidget(titre)

        # ── Ligne 1 : Drapeaux binaires ──
        flags_frame = QFrame()
        flags_frame.setStyleSheet(
            "background-color: #1e1e2e; border: 1px solid #313244; border-radius: 6px; padding: 8px;"
        )
        flags_layout = QGridLayout(flags_frame)
        flags_layout.setSpacing(6)

        # Rangée 0 : headers
        headers = ["Drapeau", "Valeur", "État"]
        for col, h in enumerate(headers):
            lbl = QLabel(f"<b>{h}</b>")
            lbl.setStyleSheet("color: #a6adc8; font-size: 10px;")
            flags_layout.addWidget(lbl, 0, col)

        # Rangée 1 : _connecting
        flags_layout.addWidget(QLabel("_connecting :"), 1, 0)
        self._lbl_connecting = QLabel("—")
        self._lbl_connecting.setStyleSheet("font-weight: bold; font-size: 11px;")
        flags_layout.addWidget(self._lbl_connecting, 1, 1)
        self._lbl_connecting_state = QLabel("⚪")
        flags_layout.addWidget(self._lbl_connecting_state, 1, 2)

        # Rangée 2 : _cancel_requested
        flags_layout.addWidget(QLabel("_cancel_requested :"), 2, 0)
        self._lbl_cancel = QLabel("—")
        self._lbl_cancel.setStyleSheet("font-weight: bold; font-size: 11px;")
        flags_layout.addWidget(self._lbl_cancel, 2, 1)
        self._lbl_cancel_state = QLabel("⚪")
        flags_layout.addWidget(self._lbl_cancel_state, 2, 2)

        # Rangée 3 : _generating
        flags_layout.addWidget(QLabel("_generating :"), 3, 0)
        self._lbl_generating = QLabel("—")
        self._lbl_generating.setStyleSheet("font-weight: bold; font-size: 11px;")
        flags_layout.addWidget(self._lbl_generating, 3, 1)
        self._lbl_generating_state = QLabel("⚪")
        flags_layout.addWidget(self._lbl_generating_state, 3, 2)

        # Rangée 4 : is_connected (depuis le service)
        flags_layout.addWidget(QLabel("is_connected  :"), 4, 0)
        self._lbl_connected = QLabel("—")
        self._lbl_connected.setStyleSheet("font-weight: bold; font-size: 11px;")
        flags_layout.addWidget(self._lbl_connected, 4, 1)
        self._lbl_connected_state = QLabel("⚪")
        flags_layout.addWidget(self._lbl_connected_state, 4, 2)

        # Rangée 5 : Thread
        flags_layout.addWidget(QLabel("Thread asyncio :"), 5, 0)
        self._lbl_thread = QLabel("—")
        self._lbl_thread.setStyleSheet("font-weight: bold; font-size: 11px;")
        flags_layout.addWidget(self._lbl_thread, 5, 1)
        self._lbl_thread_state = QLabel("⚪")
        flags_layout.addWidget(self._lbl_thread_state, 5, 2)

        layout.addWidget(flags_frame)

        # ── Ligne 2 : Résumé machine à états ──
        etat_frame = QFrame()
        etat_frame.setStyleSheet(
            "background-color: #1e1e2e; border: 1px solid #313244; border-radius: 6px; padding: 8px;"
        )
        etat_layout = QHBoxLayout(etat_frame)

        etat_layout.addWidget(QLabel("État machine :"))
        self._lbl_machine = QLabel("OFFLINE")
        self._lbl_machine.setStyleSheet(
            "font-weight: bold; font-size: 14px; color: #f38ba8; padding: 2px 8px;"
        )
        etat_layout.addWidget(self._lbl_machine)

        etat_layout.addStretch()

        etat_layout.addWidget(QLabel("Uptime :"))
        self._lbl_uptime = QLabel("—")
        self._lbl_uptime.setStyleSheet("color: #a6adc8;")
        etat_layout.addWidget(self._lbl_uptime)

        layout.addWidget(etat_frame)

        # ── Ligne 3 : Dernière tentative ──
        last_frame = QFrame()
        last_frame.setStyleSheet(
            "background-color: #1e1e2e; border: 1px solid #313244; border-radius: 6px; padding: 8px;"
        )
        last_layout = QVBoxLayout(last_frame)

        last_layout.addWidget(QLabel("<b>🕐 Dernière tentative</b>"))
        self._lbl_last_attempt = QLabel("Aucune tentative récente")
        self._lbl_last_attempt.setStyleSheet("color: #6c7086; font-size: 10px;")
        last_layout.addWidget(self._lbl_last_attempt)

        # Sous-lignes détaillées
        details_grid = QGridLayout()
        details_grid.setSpacing(4)
        details_grid.addWidget(QLabel("Timestamp :"), 0, 0)
        self._lbl_last_ts = QLabel("—")
        self._lbl_last_ts.setStyleSheet("color: #a6adc8;")
        details_grid.addWidget(self._lbl_last_ts, 0, 1)
        details_grid.addWidget(QLabel("Utilisateur :"), 0, 2)
        self._lbl_last_user = QLabel("—")
        self._lbl_last_user.setStyleSheet("color: #a6adc8;")
        details_grid.addWidget(self._lbl_last_user, 0, 3)
        details_grid.addWidget(QLabel("Résultat :"), 0, 4)
        self._lbl_last_result = QLabel("—")
        self._lbl_last_result.setStyleSheet("color: #a6adc8;")
        details_grid.addWidget(self._lbl_last_result, 0, 5)
        last_layout.addLayout(details_grid)

        layout.addWidget(last_frame)

        # ── Ligne 4 : Historique ──
        hist_frame = QFrame()
        hist_frame.setStyleSheet(
            "background-color: #1e1e2e; border: 1px solid #313244; border-radius: 6px; padding: 8px;"
        )
        hist_layout = QVBoxLayout(hist_frame)
        hist_layout.addWidget(QLabel("<b>📜 Chronologie des transitions</b>"))

        self._history_list = QListWidget()
        self._history_list.setStyleSheet(
            "QListWidget {"
            "  background-color: #11111b;"
            "  border: 1px solid #313244;"
            "  border-radius: 4px;"
            "  font-family: 'Consolas', 'Courier New', monospace;"
            "  font-size: 10px;"
            "  color: #cdd6f4;"
            "}"
        )
        hist_layout.addWidget(self._history_list)

        layout.addWidget(hist_frame, 1)

    # ── Rafraîchissement ───────────────────────────────────────────────

    def refresh(self) -> None:
        """Met à jour tous les indicateurs. Appelé périodiquement par le timer du ServiceInspector."""
        mgr = self._get_mgr()
        if mgr is None:
            self._set_offline("N/A (pas de mgr)")
            return

        try:
            # Lecture des drapeaux
            connecting = bool(getattr(mgr, "_connecting", False))
            cancel_req = bool(getattr(mgr, "_cancel_requested", False))
            generating = bool(getattr(mgr, "_generating", False))
            is_conn = soulseek_service.is_connected

            # État du thread
            thread = getattr(mgr, "_async_thread", None)
            thread_alive = thread is not None and thread.isRunning()
            loop_ok = False
            if thread is not None:
                loop = getattr(thread, "_loop", None)
                loop_ok = loop is not None and loop.is_running()

            # Détection des transitions
            current = {
                "connecting": connecting,
                "cancel": cancel_req,
                "generating": generating,
                "connected": is_conn,
            }

            self._detect_transitions(current)

            # Mise à jour UI
            self._update_flags(connecting, cancel_req, generating, is_conn)
            self._update_thread(thread_alive, loop_ok)
            self._update_machine_state(connecting, cancel_req, generating, is_conn)

            # Uptime si connecté
            if is_conn and self._prev_state.get("connected_ts"):
                uptime = datetime.datetime.now() - self._prev_state["connected_ts"]
                self._lbl_uptime.setText(str(uptime).split(".")[0])

            self._prev_state = current

        except Exception as e:
            logger.debug("Erreur refresh moniteur connexion: %s", e)
            self._set_offline(f"Erreur: {e}")

    def _get_mgr(self) -> Any:
        """Retourne le ConnexionManager ou None."""
        if self._main_window is None:
            return None
        return getattr(self._main_window, "_connexion_manager", None)

    def _set_offline(self, reason: str) -> None:
        """Met tous les indicateurs en état inconnu."""
        for lbl in [self._lbl_connecting, self._lbl_cancel, self._lbl_generating, self._lbl_connected]:
            lbl.setText("?")
            lbl.setStyleSheet("color: #6c7086; font-weight: bold;")
        for lbl in [self._lbl_connecting_state, self._lbl_cancel_state, self._lbl_generating_state, self._lbl_connected_state]:
            lbl.setText("⚪")
        self._lbl_thread.setText(reason)
        self._lbl_thread.setStyleSheet("color: #6c7086;")
        self._lbl_thread_state.setText("⚪")
        self._lbl_machine.setText("INCONNU")
        self._lbl_machine.setStyleSheet("color: #6c7086; font-weight: bold; font-size: 14px;")

    # ── Détection des transitions ─────────────────────────────────────

    def _detect_transitions(self, current: dict[str, bool]) -> None:
        prev = self._prev_state
        ts = datetime.datetime.now().strftime("%H:%M:%S")

        # Connexion établie
        if current["connected"] and not prev.get("connected"):
            self._log_event(ts, "→ CONNECTED", "success")
            self._prev_state["connected_ts"] = datetime.datetime.now()
        elif not current["connected"] and prev.get("connected"):
            self._log_event(ts, "→ DISCONNECTED", "danger")

        # Début/fin connexion
        if current["connecting"] and not prev.get("connecting"):
            self._log_event(ts, "→ CONNECTING  (_connecting = True)", "warn")
        elif not current["connecting"] and prev.get("connecting"):
            self._log_event(ts, "→ _connecting = False", "info")

        # Annulation
        if current["cancel"] and not prev.get("cancel"):
            self._log_event(ts, "→ CANCEL REQUESTED", "danger")
        elif not current["cancel"] and prev.get("cancel"):
            self._log_event(ts, "→ Cancel cleared", "info")

        # Génération
        if current["generating"] and not prev.get("generating"):
            self._log_event(ts, "→ GENERATING (nouveau compte)", "warn")
        elif not current["generating"] and prev.get("generating"):
            self._log_event(ts, "→ Generation done", "info")

    def _log_event(self, ts: str, event: str, level: str = "info") -> None:
        """Ajoute un événement dans l'historique."""
        self._history.appendleft((ts, event, level))
        self._update_history_ui()

    def _update_history_ui(self) -> None:
        """Reconstruit la QListWidget à partir de l'historique."""
        self._history_list.clear()
        color_map = {
            "success": "#a6e3a1",
            "warn":    "#f9e2af",
            "danger":  "#f38ba8",
            "info":    "#89b4fa",
        }
        for ts, event, level in self._history:
            couleur = color_map.get(level, "#cdd6f4")
            item = QListWidgetItem(f"[{ts}]  {event}")
            item.setForeground(QColor(couleur))
            self._history_list.addItem(item)

    # ── Mise à jour UI ────────────────────────────────────────────────

    def _update_flags(self, connecting: bool, cancel: bool, generating: bool, connected: bool) -> None:
        self._set_flag(self._lbl_connecting, self._lbl_connecting_state, connecting)
        self._set_flag(self._lbl_cancel, self._lbl_cancel_state, cancel)
        self._set_flag(self._lbl_generating, self._lbl_generating_state, generating)
        self._set_flag(self._lbl_connected, self._lbl_connected_state, connected)

    def _set_flag(self, lbl_value: QLabel, lbl_state: QLabel, value: bool) -> None:
        if value:
            lbl_value.setText("True")
            lbl_value.setStyleSheet("color: #f38ba8; font-weight: bold; font-size: 11px;")
            lbl_state.setText("🔴")
        else:
            lbl_value.setText("False")
            lbl_value.setStyleSheet("color: #a6e3a1; font-weight: bold; font-size: 11px;")
            lbl_state.setText("🟢")

    def _update_thread(self, alive: bool, loop_ok: bool) -> None:
        if alive and loop_ok:
            self._lbl_thread.setText("Running ✓")
            self._lbl_thread.setStyleSheet("color: #a6e3a1; font-weight: bold;")
            self._lbl_thread_state.setText("✅")
        elif alive:
            self._lbl_thread.setText("Running (loop?)")
            self._lbl_thread.setStyleSheet("color: #f9e2af; font-weight: bold;")
            self._lbl_thread_state.setText("⚠️")
        else:
            self._lbl_thread.setText("STOPPED")
            self._lbl_thread.setStyleSheet("color: #f38ba8; font-weight: bold;")
            self._lbl_thread_state.setText("❌")

    def _update_machine_state(self, connecting: bool, cancel: bool, generating: bool, connected: bool) -> None:
        """Calcule et affiche l'état machine résumé."""
        if generating:
            label = "GENERATING"
            color = "#f9e2af"
        elif connected:
            label = "CONNECTED"
            color = "#a6e3a1"
        elif connecting and cancel:
            label = "CANCELING"
            color = "#f38ba8"
        elif connecting:
            label = "CONNECTING"
            color = "#f9e2af"
        else:
            label = "OFFLINE"
            color = "#6c7086"

        self._lbl_machine.setText(label)
        self._lbl_machine.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {color}; padding: 2px 8px;")

    # ── API pour enregistrer les tentatives ────────────────────────────

    def log_attempt(self, username: str, resultat: str) -> None:
        """Enregistre une tentative de connexion (appelé depuis le ServiceInspector)."""
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._lbl_last_ts.setText(ts)
        self._lbl_last_user.setText(username)
        self._lbl_last_result.setText(resultat)

        if "TIMEOUT" in resultat or "ÉCHEC" in resultat or "échec" in resultat.lower():
            couleur = "#f38ba8"
        elif "SUCCÈS" in resultat or "réussie" in resultat.lower():
            couleur = "#a6e3a1"
        else:
            couleur = "#f9e2af"

        self._lbl_last_attempt.setStyleSheet(f"color: {couleur}; font-size: 10px;")
        self._lbl_last_attempt.setText(
            f"Dernière tentative — {ts} | {username} → {resultat}"
        )
        self._log_event(ts, f"Tentative: {username} → {resultat}",
                        "success" if "SUCCÈS" in resultat else "danger")
