"""Contrôleur de débogage pour la connexion Soulseek.

Permet de réinitialiser des flags bloqués, d'annuler une connexion en cours,
ou de simuler un timeout — sans redémarrer l'application.
"""

from __future__ import annotations

import logging
import sys
import threading
import time
import traceback
from typing import Any, Optional

from PySide6.QtCore import QThread, Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.services.app_config import get as cfg_get, set as cfg_set
from src.services.soulseek_client import soulseek_service
from src.utils.log_action import log_action

logger = logging.getLogger("[TIMEOUT-CTRL]")


class TimeoutControllerWidget(QFrame):
    """Widget de contrôle pour actions de débogage sur la connexion Soulseek.

    Permet de :
    - Réinitialiser le flag ``_connecting`` (si bloqué à True)
    - Annuler proprement une connexion en cours
    - Simuler un timeout (pour tester le comportement)
    - Voir et modifier les valeurs de timeout dans la config
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._main_window: Any = None
        self._build_ui()

    def set_main_window(self, main_window: Any) -> None:
        """Injecte la fenêtre principale pour accéder au ConnexionManager."""
        self._main_window = main_window

    # ── Construction UI ─────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Scroll area pour que tout le contenu soit accessible
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical {"
            "  background: #11111b; width: 8px; margin: 0;"
            "}"
            "QScrollBar::handle:vertical {"
            "  background: #45475a; min-height: 20px; border-radius: 4px;"
            "}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {"
            "  height: 0;"
            "}"
        )

        # Conteneur interne — tout le contenu va ici
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(2, 2, 2, 2)
        inner_layout.setSpacing(2)

        # ── Actions de débogage ──
        actions_frame = QFrame()
        actions_frame.setStyleSheet(
            "background-color: #1e1e2e; border: 1px solid #313244; border-radius: 3px; padding: 3px;"
        )
        actions_layout = QVBoxLayout(actions_frame)
        actions_layout.setContentsMargins(2, 2, 2, 2)
        actions_layout.setSpacing(2)

        actions_layout.addWidget(QLabel("<b>🎮 Actions de débogage</b>"))

        # Grille de boutons — 4 colonnes
        btn_grid = QGridLayout()
        btn_grid.setSpacing(2)

        # ── Rangée 0 : flags / connexion ──
        self._btn_reset_connecting = QPushButton("🔓 Reset _connecting")
        self._btn_reset_connecting.setToolTip("Force _connecting = False (débloque si bloqué à True)")
        self._btn_reset_connecting.setStyleSheet("background-color: #45475a;")
        self._btn_reset_connecting.clicked.connect(self._on_reset_connecting)
        btn_grid.addWidget(self._btn_reset_connecting, 0, 0)

        self._btn_cancel = QPushButton("🚫 Annuler connexion")
        self._btn_cancel.setToolTip("Appelle disconnect() pour annuler la connexion en cours")
        self._btn_cancel.setStyleSheet("background-color: #b53737;")
        self._btn_cancel.clicked.connect(self._on_cancel)
        btn_grid.addWidget(self._btn_cancel, 0, 1)

        self._btn_simulate_timeout = QPushButton("⏱️ Simuler timeout")
        self._btn_simulate_timeout.setToolTip("Force _connecting=True puis le réinitialise après 5s")
        self._btn_simulate_timeout.setStyleSheet("background-color: #b58037;")
        self._btn_simulate_timeout.clicked.connect(self._on_simulate_timeout)
        btn_grid.addWidget(self._btn_simulate_timeout, 0, 2)

        self._btn_logout = QPushButton("🔌 Forcer déconnexion")
        self._btn_logout.setToolTip("Appelle disconnect() sur le service directement")
        self._btn_logout.setStyleSheet("background-color: #b53737;")
        self._btn_logout.clicked.connect(self._on_force_disconnect)
        btn_grid.addWidget(self._btn_logout, 0, 3)

        # ── Rangée 1 : threads / workers ──
        self._btn_kill_loop = QPushButton("💀 Stop asyncio thread")
        self._btn_kill_loop.setToolTip("⚠️ Arrête le thread asyncio (cas extrême)")
        self._btn_kill_loop.setStyleSheet("background-color: #6c7086;")
        self._btn_kill_loop.clicked.connect(self._on_stop_thread)
        btn_grid.addWidget(self._btn_kill_loop, 1, 0)

        self._btn_kill_workers = QPushButton("🔪 Tuer workers bloqués")
        self._btn_kill_workers.setToolTip("Termine tous les QThread workers + asyncio thread (scan complet)")
        self._btn_kill_workers.setStyleSheet("background-color: #b53737;")
        self._btn_kill_workers.clicked.connect(self._on_kill_workers)
        btn_grid.addWidget(self._btn_kill_workers, 1, 1)

        self._btn_list_threads = QPushButton("📋 Lister threads")
        self._btn_list_threads.setToolTip("Affiche tous les threads Python actifs")
        self._btn_list_threads.setStyleSheet("background-color: #45475a;")
        self._btn_list_threads.clicked.connect(self._on_list_threads)
        btn_grid.addWidget(self._btn_list_threads, 1, 2)

        self._btn_flush_coro = QPushButton("🧹 Cleanup workers")
        self._btn_flush_coro.setToolTip("Nettoie les références aux workers terminés mais non nettoyés")
        self._btn_flush_coro.setStyleSheet("background-color: #585b70;")
        self._btn_flush_coro.clicked.connect(self._on_cleanup_workers)
        btn_grid.addWidget(self._btn_flush_coro, 1, 3)

        # ── Rangée 2 : stack trace + refresh ──
        self._btn_stack_trace = QPushButton("📚 Stack trace")
        self._btn_stack_trace.setToolTip("Affiche les traces d'appels de tous les threads via sys._current_frames()")
        self._btn_stack_trace.setStyleSheet("background-color: #6c5ce7;")
        self._btn_stack_trace.clicked.connect(self._on_stack_trace)
        btn_grid.addWidget(self._btn_stack_trace, 2, 0, 1, 2)

        self._btn_refresh_cfg = QPushButton("🔄 Recharger config")
        self._btn_refresh_cfg.setToolTip("Re-affiche les valeurs actuelles de la config")
        self._btn_refresh_cfg.setStyleSheet("background-color: #45475a;")
        self._btn_refresh_cfg.clicked.connect(self._on_refresh)
        btn_grid.addWidget(self._btn_refresh_cfg, 2, 2, 1, 2)

        actions_layout.addLayout(btn_grid)
        inner_layout.addWidget(actions_frame)

        # ── Configuration timeouts ──
        cfg_frame = QFrame()
        cfg_frame.setStyleSheet(
            "background-color: #1e1e2e; border: 1px solid #313244; border-radius: 3px; padding: 3px;"
        )
        cfg_layout = QVBoxLayout(cfg_frame)
        cfg_layout.setContentsMargins(2, 2, 2, 2)
        cfg_layout.setSpacing(2)
        cfg_layout.addWidget(QLabel("<b>⚙️ Configuration timeouts</b>"))

        cfg_grid = QGridLayout()
        cfg_grid.setSpacing(1)

        cfg_grid.addWidget(QLabel("Port serveur :"), 0, 0)
        self._lbl_port = QLabel("—")
        self._lbl_port.setStyleSheet("color: #a6adc8;")
        cfg_grid.addWidget(self._lbl_port, 0, 1)

        cfg_grid.addWidget(QLabel("Hôte serveur :"), 0, 2)
        self._lbl_host = QLabel("—")
        self._lbl_host.setStyleSheet("color: #a6adc8;")
        cfg_grid.addWidget(self._lbl_host, 0, 3)

        cfg_grid.addWidget(QLabel("Timeout login :"), 1, 0)
        self._lbl_login_timeout = QLabel("30s")
        self._lbl_login_timeout.setStyleSheet("color: #a6adc8;")
        cfg_grid.addWidget(self._lbl_login_timeout, 1, 1)

        cfg_grid.addWidget(QLabel("Timeout disconnect :"), 1, 2)
        self._lbl_disconnect_timeout = QLabel("10s")
        self._lbl_disconnect_timeout.setStyleSheet("color: #a6adc8;")
        cfg_grid.addWidget(self._lbl_disconnect_timeout, 1, 3)

        cfg_grid.addWidget(QLabel("Reconnexion auto :"), 2, 0)
        self._lbl_reconnect = QLabel("—")
        self._lbl_reconnect.setStyleSheet("color: #a6adc8;")
        cfg_grid.addWidget(self._lbl_reconnect, 2, 1)

        cfg_grid.addWidget(QLabel("Timeout reconnect :"), 2, 2)
        self._lbl_reconnect_timeout = QLabel("—")
        self._lbl_reconnect_timeout.setStyleSheet("color: #a6adc8;")
        cfg_grid.addWidget(self._lbl_reconnect_timeout, 2, 3)

        cfg_layout.addLayout(cfg_grid)
        inner_layout.addWidget(cfg_frame)

        # ── État (compact) ──
        self._lbl_direct_state = QLabel("Prêt")
        self._lbl_direct_state.setStyleSheet(
            "color: #6c7086; font-size: 9px; background: #181825; border: 1px solid #313244;"
            "border-radius: 3px; padding: 1px 4px;"
        )
        inner_layout.addWidget(self._lbl_direct_state)

        inner_layout.addStretch()

        # Monter le contenu dans la scroll area
        scroll.setWidget(inner)
        layout.addWidget(scroll)

    # ── Actions ─────────────────────────────────────────────────────────

    def _get_mgr(self) -> Any:
        if self._main_window is None:
            return None
        return getattr(self._main_window, "_connexion_manager", None)

    @log_action("Réinitialiser _connecting")
    def _on_reset_connecting(self) -> None:
        """Force _connecting = False sur le ConnexionManager."""
        mgr = self._get_mgr()
        if mgr is None:
            self._lbl_direct_state.setText("❌ Pas de ConnexionManager disponible")
            self._lbl_direct_state.setStyleSheet("color: #f38ba8; font-size: 10px;")
            return
        try:
            mgr._connecting = False
            mgr._cancel_requested = False
            logger.info("🔓 _connecting et _cancel_requested réinitialisés par l'utilisateur")
            self._lbl_direct_state.setText("✅ _connecting = False, _cancel_requested = False")
            self._lbl_direct_state.setStyleSheet("color: #a6e3a1; font-size: 10px;")
        except Exception as e:
            self._lbl_direct_state.setText(f"❌ Erreur: {e}")
            self._lbl_direct_state.setStyleSheet("color: #f38ba8; font-size: 10px;")

    @log_action("Annuler connexion")
    def _on_cancel(self) -> None:
        """Appelle disconnect() sur le ConnexionManager."""
        mgr = self._get_mgr()
        if mgr is None:
            self._lbl_direct_state.setText("❌ Pas de ConnexionManager disponible")
            self._lbl_direct_state.setStyleSheet("color: #f38ba8; font-size: 10px;")
            return
        try:
            mgr.disconnect()
            logger.info("🚫 Annulation de connexion déclenchée par l'utilisateur")
            self._lbl_direct_state.setText("✅ disconnect() appelé")
            self._lbl_direct_state.setStyleSheet("color: #a6e3a1; font-size: 10px;")
        except Exception as e:
            self._lbl_direct_state.setText(f"❌ Erreur: {e}")
            self._lbl_direct_state.setStyleSheet("color: #f38ba8; font-size: 10px;")

    @log_action("Simuler timeout")
    def _on_simulate_timeout(self) -> None:
        """Simule un timeout en forçant _connecting=True puis le réinitialise après 5s."""
        mgr = self._get_mgr()
        if mgr is None:
            self._lbl_direct_state.setText("❌ Pas de ConnexionManager disponible")
            self._lbl_direct_state.setStyleSheet("color: #f38ba8; font-size: 10px;")
            return
        try:
            mgr._connecting = True
            logger.warning("⏱️ Simulation timeout: _connecting = True")
            self._lbl_direct_state.setText("⏱️ _connecting = True (reset dans 5s)")
            self._lbl_direct_state.setStyleSheet("color: #f9e2af; font-size: 10px;")

            # Reset après 5s
            QTimer.singleShot(5000, lambda: self._reset_after_sim(mgr))
        except Exception as e:
            self._lbl_direct_state.setText(f"❌ Erreur: {e}")
            self._lbl_direct_state.setStyleSheet("color: #f38ba8; font-size: 10px;")

    def _reset_after_sim(self, mgr: Any) -> None:
        """Rétablit _connecting après simulation."""
        try:
            mgr._connecting = False
            logger.info("✅ Simulation timeout terminée: _connecting = False")
            self._lbl_direct_state.setText("✅ _connecting = False (fin simulation)")
            self._lbl_direct_state.setStyleSheet("color: #a6e3a1; font-size: 10px;")
        except Exception as e:
            self._lbl_direct_state.setText(f"❌ Erreur reset: {e}")
            self._lbl_direct_state.setStyleSheet("color: #f38ba8; font-size: 10px;")

    @log_action("Arrêter thread asyncio")
    def _on_stop_thread(self) -> None:
        """Arrête le thread asyncio (cas extrême — peut casser l'app)."""
        mgr = self._get_mgr()
        if mgr is None:
            self._lbl_direct_state.setText("❌ Pas de ConnexionManager disponible")
            self._lbl_direct_state.setStyleSheet("color: #f38ba8; font-size: 10px;")
            return
        try:
            logger.warning("💀 Arrêt forcé du thread asyncio demandé par l'utilisateur")
            thread = getattr(mgr, "_async_thread", None)
            if thread is not None:
                thread.stop()
                self._lbl_direct_state.setText("💀 Thread asyncio arrêté")
                self._lbl_direct_state.setStyleSheet("color: #f38ba8; font-size: 10px;")
            else:
                self._lbl_direct_state.setText("❌ Pas de thread asyncio")
                self._lbl_direct_state.setStyleSheet("color: #f38ba8; font-size: 10px;")
        except Exception as e:
            self._lbl_direct_state.setText(f"❌ Erreur: {e}")
            self._lbl_direct_state.setStyleSheet("color: #f38ba8; font-size: 10px;")

    @log_action("Forcer déconnexion")
    def _on_force_disconnect(self) -> None:
        """Appelle disconnect() directement sur le service (bypass ConnexionManager)."""
        try:
            logger.warning("🔌 Forçage déconnexion via soulseek_service.disconnect()")
            # Disconnect est asynchrone — on lance la coroutine sur le thread
            mgr = self._get_mgr()
            if mgr is not None:
                mgr._async_thread.run_coro(soulseek_service.disconnect())
                self._lbl_direct_state.setText("🔌 Déconnexion forcée envoyée")
                self._lbl_direct_state.setStyleSheet("color: #a6e3a1; font-size: 10px;")
            else:
                self._lbl_direct_state.setText("❌ Pas de ConnexionManager")
                self._lbl_direct_state.setStyleSheet("color: #f38ba8; font-size: 10px;")
        except Exception as e:
            self._lbl_direct_state.setText(f"❌ Erreur: {e}")
            self._lbl_direct_state.setStyleSheet("color: #f38ba8; font-size: 10px;")

    # ── Gestion des threads bloqués ────────────────────────────────────

    @log_action("Tuer workers bloqués")
    def _on_kill_workers(self) -> None:
        """Scan et termine tous les workers QThread bloqués + asyncio thread.

        Stratégie :
        1. Arrêter l'asyncio thread du ConnexionManager
        2. Scanner tous les widgets Qt pour trouver des workers QThread
        3. Tenter quit() + wait() d'abord, puis terminate() si nécessaire
        """
        tue = 0
        messages: list[str] = []

        def _graceful_stop(t: QThread, nom: str) -> None:
            """Arrête un thread proprement : quit → wait → terminate."""
            nonlocal tue
            try:
                if t.isFinished() or not t.isRunning():
                    return
                t.quit()
                if t.wait(2000):
                    messages.append(f"{nom}: quit OK ✓")
                else:
                    t.terminate()
                    if t.wait(3000):
                        messages.append(f"{nom}: terminate OK ✓")
                    else:
                        messages.append(f"{nom}: timeout (résistance)")
                tue += 1
                logger.warning("🔪 Thread terminé: %s", nom)
            except Exception as e:
                messages.append(f"{nom}: {e}")

        # 1. Terminer l'asyncio thread
        mgr = self._get_mgr()
        if mgr is not None:
            thread = getattr(mgr, "_async_thread", None)
            if thread is not None and thread.isRunning():
                try:
                    thread.stop()
                    messages.append("asyncio thread arrêté")
                    tue += 1
                except Exception as e:
                    messages.append(f"asyncio: {e}")

        # 2. Scanner tous les widgets pour trouver des workers QThread
        for widget in QApplication.allWidgets():
            for attr_name in ("_current_worker", "_analyse_worker", "_export_worker"):
                worker = getattr(widget, attr_name, None)
                if worker is not None and isinstance(worker, QThread):
                    _graceful_stop(worker, attr_name)

        if tue:
            self._set_status(f"🔪 {tue} thread(s) terminé(s) : {'; '.join(messages)}", "#f38ba8")
        else:
            self._set_status("✅ Aucun thread bloqué détecté", "#a6e3a1")

    @log_action("Lister threads")
    def _on_list_threads(self) -> None:
        """Liste tous les threads Python actifs — tronqué à 20 lignes dans l'UI, complet dans les logs."""
        lignes: list[str] = []
        for t in threading.enumerate():
            nom = t.name or "(sans nom)"
            daemon = " [daemon]" if t.daemon else ""
            ident = t.ident or 0
            alive = "✓" if t.is_alive() else "✗"
            # Identifier le type
            if isinstance(t, QThread):
                typename = "QThread"
            elif t is threading.main_thread():
                typename = "MainThread"
            else:
                typename = type(t).__name__
            lignes.append(f"#{ident:>6} {alive} {typename:<12} {nom}{daemon}")

        resultat = "\n".join(lignes)
        logger.info("📋 %d thread(s) actif(s):\n%s", len(lignes), resultat)

        # Afficher dans l'UI en tronquant à 20 lignes
        MAX_LIGNES = 20
        if len(lignes) > MAX_LIGNES:
            affichage = "\n".join(lignes[:MAX_LIGNES])
            affichage += f"\n... et {len(lignes) - MAX_LIGNES} autre(s) (voir logs)"
        else:
            affichage = resultat

        self._lbl_direct_state.setText(
            f"📋 {len(lignes)} thread(s) actif(s)\n{affichage}"
        )
        self._lbl_direct_state.setStyleSheet(
            "color: #cdd6f4; font-size: 9px; font-family: Consolas, monospace; "
            "white-space: pre;"
        )

    @log_action("Nettoyer les workers")
    def _on_cleanup_workers(self) -> None:
        """Nettoie les références aux workers non nettoyés dans les widgets."""
        nettoye = 0
        from PySide6.QtWidgets import QApplication
        for widget in QApplication.allWidgets():
            for attr_name in ("_current_worker", "_analyse_worker"):
                worker = getattr(widget, attr_name, None)
                if worker is not None and not worker.isRunning():
                    try:
                        setattr(widget, attr_name, None)
                        nettoye += 1
                        logger.info("🧹 Référence '%s' nettoyée", attr_name)
                    except Exception as e:
                        logger.debug("Cleanup %s: %s", attr_name, e)

        if nettoye:
            self._set_status(f"🧹 {nettoye} référence(s) nettoyée(s)", "#a6e3a1")
        else:
            self._set_status("✅ Aucune référence à nettoyer", "#a6adc8")

    @log_action("Afficher la stack trace")
    def _on_stack_trace(self) -> None:
        """Affiche les traces d'appels de tous les threads Python.

        Utilise ``sys._current_frames()`` pour capturer la pile d'appels
        de chaque thread actif au moment présent. Idéal pour identifier
        où un thread est bloqué (mutex, boucle infinie, appel réseau).

        Note: ``threading.settrace()`` permettrait de tracer les appels
        en continu, mais pour un instantané, ``sys._current_frames()``
        est plus pertinent car il capture l'état exact des threads.
        """
        frames = sys._current_frames()
        lignes: list[str] = []
        noms_threads = {t.ident: t.name for t in threading.enumerate() if t.ident}

        for thread_id, frame in frames.items():
            nom = noms_threads.get(thread_id, f"Thread-{thread_id}")
            daemon = ""
            for t in threading.enumerate():
                if t.ident == thread_id:
                    daemon = " [daemon]" if t.daemon else ""
                    break

            lignes.append(f"\n{'='*60}")
            lignes.append(f"🧵 Thread #{thread_id} — {nom}{daemon}")
            lignes.append(f"{'='*60}")

            # Remonter la pile d'appels
            stack = traceback.extract_stack(frame)
            for filename, lineno, funcname, text in reversed(stack):
                # Tronquer les chemins trop longs
                short_fn = filename
                if len(short_fn) > 65:
                    short_fn = "..." + short_fn[-62:]
                lignes.append(f"  📍 {short_fn}:{lineno}")
                lignes.append(f"     └─ {funcname}()")
                if text and text.strip():
                    lignes.append(f"        {text.strip()}")

        resultat = "\n".join(lignes)
        logger.info("📚 Stack trace de %d thread(s):\n%s", len(frames), resultat)

        # Affichage dans l'UI — tronqué à 15 frames par thread max
        MAX_LIGNES_THREAD = 15
        ui_lignes: list[str] = []
        for t_id, f in frames.items():
            nom = noms_threads.get(t_id, f"Thread-{t_id}")
            ui_lignes.append(f"🧵 {nom}")
            stack = traceback.extract_stack(f)
            for i, (fn, ln, func, _) in enumerate(reversed(stack)):
                if i >= MAX_LIGNES_THREAD:
                    ui_lignes.append(f"   ... ({len(stack) - MAX_LIGNES_THREAD} frames de plus)")
                    break
                short_fn = fn
                if len(short_fn) > 50:
                    short_fn = "..." + short_fn[-47:]
                ui_lignes.append(f"   {short_fn}:{ln} → {func}()")

        MAX_TOTAL = 30
        affichage = "\n".join(ui_lignes[:MAX_TOTAL])
        reste = len(ui_lignes) - MAX_TOTAL
        if reste > 0:
            affichage += f"\n... et {reste} ligne(s) de plus (voir logs)"

        self._lbl_direct_state.setText(
            f"📚 {len(frames)} thread(s) — {sum(len(traceback.extract_stack(f)) for f in frames.values())} frames\n{affichage}"
        )
        self._lbl_direct_state.setStyleSheet(
            "color: #89b4fa; font-size: 9px; font-family: Consolas, monospace; "
            "white-space: pre;"
        )

    # ── Helper ─────────────────────────────────────────────────────────

    def _set_status(self, text: str, color: str = "#cdd6f4") -> None:
        """Met à jour le label d'état en direct."""
        self._lbl_direct_state.setText(text)
        self._lbl_direct_state.setStyleSheet(f"color: {color}; font-size: 10px; font-family: Consolas, monospace;")
        QApplication.processEvents()

    # ── Rafraîchissement ───────────────────────────────────────────────

    @log_action("Recharger config")
    def _on_refresh(self) -> None:
        """Handler bouton — recharge la config avec log d'action."""
        self.refresh()

    def refresh(self) -> None:
        """Met à jour l'affichage des valeurs de timeout depuis la config (appelé par le timer)."""
        # Pas de @log_action ici car appelé toutes les 1,5s par le timer de l'inspector
        try:
            port = cfg_get("reseau.port_serveur", "2242")
            host = cfg_get("reseau.hote_serveur", "server.slsknet.org")
            reconnect = cfg_get("reseau.reconnexion_auto", False)
            reconnect_timeout = cfg_get("reseau.reconnexion_timeout", 10)

            self._lbl_port.setText(str(port))
            self._lbl_host.setText(str(host))
            self._lbl_reconnect.setText("Oui" if reconnect else "Non")
            self._lbl_reconnect_timeout.setText(f"{reconnect_timeout}s")
        except Exception as e:
            logger.debug("Erreur refresh config: %s", e)
