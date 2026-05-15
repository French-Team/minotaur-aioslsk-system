"""
Bot Optimiseur — tableau de bord d'optimisation centralisé.

Applique des profils prédéfinis qui modifient automatiquement les
paramètres de configuration des pages (Réseau, Recherche, etc.).
"""

from __future__ import annotations

from src.gui.theme_fragments.colors import rgba

import json
import os
from glob import glob
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.gui.theme_fragments.colors import COLORS
from src.gui.widgets.config import ConfigPage, highlight_widget
from src.services.event_bus import EventBus

# ─── Constantes ───────────────────────────────────────────────

_PROFILS_DIR = Path("data/profils")
_DASHBOARD_EMPTY = "Aucun profil appliqué"
_COLORS = COLORS  # alias pour le confort


# ═══════════════════════════════════════════════════════════════
#  BotOptimiseur
# ═══════════════════════════════════════════════════════════════


class BotOptimiseur(QFrame):
    """Tableau de bord d'optimisation centralisé.

    Barre d'action (profils) → Viewer (logs) | Dashboard (diff).
    """

    page_changed = Signal(str)

    def __init__(
        self,
        center_zone: QWidget | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("botOptimiseur")
        self._center_zone = center_zone
        self._profil_actif: str | None = None
        self._watcher = QFileSystemWatcher(self)
        self._boutons: list[QWidget] = []
        self._sequence: list[tuple[str, ConfigPage, dict]] = []
        self._step: int = 0
        self._applying: bool = False
        self._diffs_globaux: list[tuple[str, str, str]] = []
        self._nom_applique: str = ""
        self._icone_applique: str = ""

        self._build_ui()
        self._build_overlay()
        self._reload_profiles()
        self._setup_watcher()

    # ═══════════════════════════════════════════════════════════
    #  UI
    # ═══════════════════════════════════════════════════════════

    def _build_ui(self) -> None:
        """Construit l'interface complète : barre + split viewer|dashboard."""
        self.setStyleSheet(
            f"#botOptimiseur {{"
            f"  background: {_COLORS['BG_CENTER']};"
            f"}}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Barre d'action (profils) ──
        self._action_bar = QFrame()
        self._action_bar.setObjectName("optimiseurActionBar")
        self._action_bar.setFixedHeight(52)
        self._action_bar.setStyleSheet(
            f"#optimiseurActionBar {{"
            f"  background: {_COLORS['BG_SURFACE']};"
            f"  border-bottom: 1px solid {_COLORS['BORDER']};"
            f"}}"
        )
        self._action_layout = QHBoxLayout(self._action_bar)
        self._action_layout.setContentsMargins(12, 8, 12, 8)
        self._action_layout.setSpacing(8)

        label_profils = QLabel("⚡ Profils")
        label_profils.setStyleSheet(
            f"color: {_COLORS['TEXT_PRIMARY']};"
            f"font-size: 11px; font-weight: 600;"
            f"padding: 0 4px 0 0;"
        )
        self._action_layout.addWidget(label_profils)

        self._action_layout.addStretch(1)
        layout.addWidget(self._action_bar)

        # ── Split horizontal : Viewer | Dashboard ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(
            f"QSplitter::handle {{"
            f"  background: {_COLORS['BORDER']};"
            f"}}"
        )

        # Viewer (gauche)
        self._viewer = self._build_viewer()
        splitter.addWidget(self._viewer)

        # Dashboard (droite)
        self._dashboard = self._build_dashboard()
        splitter.addWidget(self._dashboard)

        # Ratios ~60/40
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)
        splitter.setSizes([600, 400])

        layout.addWidget(splitter, 1)

    def _build_viewer(self) -> QWidget:
        """Construit le panneau de logs en temps réel."""
        container = QFrame()
        container.setObjectName("optimiseurViewer")
        container.setStyleSheet(
            f"#optimiseurViewer {{"
            f"  background: {_COLORS['BG_DARK']};"
            f"  border-right: 1px solid {_COLORS['BORDER']};"
            f"}}"
        )

        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(12, 10, 12, 10)
        vbox.setSpacing(6)

        # En-tête
        header = QLabel("📋 Journal d'application")
        header.setStyleSheet(
            f"color: {_COLORS['TEXT_PRIMARY']};"
            f"font-size: 12px; font-weight: 700;"
        )
        vbox.addWidget(header)

        # Zone de logs
        self._log_area = QTextEdit()
        self._log_area.setObjectName("optimiseurLogs")
        self._log_area.setReadOnly(True)
        self._log_area.setStyleSheet(
            f"#optimiseurLogs {{"
            f"  background: {_COLORS['BG_MAIN']};"
            f"  color: {_COLORS['TEXT_TERTIARY']};"
            f"  font-family: 'Consolas', 'Fira Code', monospace;"
            f"  font-size: 11px;"
            f"  border: 1px solid {_COLORS['BORDER']};"
            f"  border-radius: 6px;"
            f"  padding: 8px;"
            f"}}"
        )
        vbox.addWidget(self._log_area, 1)

        # Bouton copier
        btn_copier = QPushButton("📋 Copier les logs")
        btn_copier.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copier.setStyleSheet(self._btn_style_secondaire())
        btn_copier.clicked.connect(self._copier_logs)
        vbox.addWidget(btn_copier, 0, Qt.AlignmentFlag.AlignRight)

        return container

    def _build_dashboard(self) -> QWidget:
        """Construit le panneau de dashboard (profil + diff)."""
        container = QFrame()
        container.setObjectName("optimiseurDashboard")
        container.setStyleSheet(
            f"#optimiseurDashboard {{"
            f"  background: {_COLORS['BG_CENTER']};"
            f"}}"
        )

        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(12, 10, 12, 10)
        vbox.setSpacing(6)

        # En-tête
        header = QLabel("📊 Résumé")
        header.setStyleSheet(
            f"color: {_COLORS['TEXT_PRIMARY']};"
            f"font-size: 12px; font-weight: 700;"
        )
        vbox.addWidget(header)

        # ── Carte du profil actif ──
        self._carte_profil = QFrame()
        self._carte_profil.setObjectName("carteProfil")
        self._carte_profil.setStyleSheet(
            f"#carteProfil {{"
            f"  background: {_COLORS['BG_SURFACE']};"
            f"  border: 1px solid {_COLORS['BORDER']};"
            f"  border-radius: 8px;"
            f"  padding: 12px;"
            f"}}"
        )
        carte_layout = QVBoxLayout(self._carte_profil)
        carte_layout.setContentsMargins(12, 10, 12, 10)
        carte_layout.setSpacing(4)

        self._profil_label = QLabel(_DASHBOARD_EMPTY)
        self._profil_label.setStyleSheet(
            f"color: {_COLORS['TEXT_MUTED']};"
            f"font-size: 13px; font-weight: 600;"
        )
        carte_layout.addWidget(self._profil_label)

        self._statut_label = QLabel("")
        self._statut_label.setStyleSheet(
            f"color: {_COLORS['TEXT_SECONDARY']};"
            f"font-size: 11px;"
        )
        carte_layout.addWidget(self._statut_label)

        vbox.addWidget(self._carte_profil)

        # ── Zone des diffs (scrollable) ──
        self._diff_container = QFrame()
        self._diff_container.setObjectName("diffContainer")
        self._diff_container.setStyleSheet(
            f"#diffContainer {{"
            f"  background: transparent;"
            f"  border: 1px solid {_COLORS['BORDER']};"
            f"  border-radius: 6px;"
            f"}}"
        )

        diff_vbox = QVBoxLayout(self._diff_container)
        diff_vbox.setContentsMargins(8, 8, 8, 8)
        diff_vbox.setSpacing(4)

        diff_header = QLabel("Modifications")
        diff_header.setStyleSheet(
            f"color: {_COLORS['TEXT_SECONDARY']};"
            f"font-size: 10px; font-weight: 700;"
            f"text-transform: uppercase;"
        )
        diff_vbox.addWidget(diff_header)

        self._diff_scroll = QScrollArea()
        self._diff_scroll.setWidgetResizable(True)
        self._diff_scroll.setFrameShape(QFrame.NoFrame)
        self._diff_scroll.setStyleSheet(
            f"QScrollArea {{ background: transparent; }}"
        )

        self._diff_content = QWidget()
        self._diff_content.setObjectName("diffContent")
        self._diff_content.setStyleSheet(
            f"#diffContent {{ background: transparent; }}"
        )
        self._diff_layout = QVBoxLayout(self._diff_content)
        self._diff_layout.setContentsMargins(0, 0, 0, 0)
        self._diff_layout.setSpacing(2)

        self._placeholder_diff = QLabel("⚠ Cliquez sur un profil\ndans la barre d'action")
        self._placeholder_diff.setStyleSheet(
            f"color: {_COLORS['TEXT_MUTED']};"
            f"font-size: 11px; padding: 12px;"
        )
        self._placeholder_diff.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._diff_layout.addWidget(self._placeholder_diff)
        self._diff_layout.addStretch(1)

        self._diff_scroll.setWidget(self._diff_content)
        diff_vbox.addWidget(self._diff_scroll, 1)

        vbox.addWidget(self._diff_container, 1)

        # ── Bouton reset ──
        self._reset_btn = QPushButton("↺ Réinitialiser")
        self._reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_btn.setStyleSheet(self._btn_style_danger())
        self._reset_btn.clicked.connect(self._reset_dashboard)
        vbox.addWidget(self._reset_btn, 0, Qt.AlignmentFlag.AlignRight)

        return container

    # ═══════════════════════════════════════════════════════════
    #  Styles de boutons
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _btn_style_secondaire() -> str:
        return (
            f"QPushButton {{"
            f"  background: {_COLORS['BG_BTN']};"
            f"  color: {_COLORS['TEXT_TERTIARY']};"
            f"  border: 1px solid {_COLORS['BORDER']};"
            f"  border-radius: 6px;"
            f"  padding: 4px 12px;"
            f"  font-size: 11px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {_COLORS['BG_HOVER']};"
            f"  color: {_COLORS['TEXT_PRIMARY']};"
            f"  border: 1px solid {_COLORS['BORDER_HOVER']};"
            f"}}"
            f"QPushButton:pressed {{"
            f"  background: {_COLORS['BG_PRESSED']};"
            f"}}"
        )

    @staticmethod
    def _btn_style_danger() -> str:
        return (
            f"QPushButton {{"
            f"  background: transparent;"
            f"  color: {_COLORS['DANGER']};"
            f"  border: 1px solid {rgba(_COLORS['DANGER'], '55')};"
            f"  border-radius: 6px;"
            f"  padding: 4px 12px;"
            f"  font-size: 11px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {_COLORS['DANGER_BG_HOVER']};"
            f"  border: 1px solid {_COLORS['DANGER']};"
            f"}}"
            f"QPushButton:pressed {{"
            f"  background: {_COLORS['DANGER_BG_PRESSED']};"
            f"}}"
        )

    @staticmethod
    def _btn_style_profil(actif: bool = False) -> str:
        if actif:
            return (
                f"QPushButton {{"
                f"  background: {_COLORS['BG_BTN']};"
                f"  color: {_COLORS['ACCENT']};"
                f"  border: 1px solid {_COLORS['ACCENT']};"
                f"  border-radius: 8px;"
                f"  padding: 6px 14px;"
                f"  font-size: 11px; font-weight: 600;"
                f"}}"
                f"QPushButton:hover {{"
                f"  background: {_COLORS['BG_HOVER']};"
                f"  color: {_COLORS['ACCENT_HOVER']};"
                f"}}"
            )
        return (
            f"QPushButton {{"
            f"  background: {_COLORS['BG_BTN']};"
            f"  color: {_COLORS['TEXT_TERTIARY']};"
            f"  border: 1px solid {_COLORS['BORDER']};"
            f"  border-radius: 8px;"
            f"  padding: 6px 14px;"
            f"  font-size: 11px; font-weight: 500;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {_COLORS['BG_HOVER']};"
            f"  color: {_COLORS['TEXT_PRIMARY']};"
            f"  border: 1px solid {_COLORS['BORDER_HOVER']};"
            f"}}"
            f"QPushButton:pressed {{"
            f"  background: {_COLORS['BG_PRESSED']};"
            f"}}"
        )

    # ═══════════════════════════════════════════════════════════
    #  Gestion des profils
    # ═══════════════════════════════════════════════════════════

    def _setup_watcher(self) -> None:
        """Surveille le dossier data/profils/ pour les changements."""
        if _PROFILS_DIR.exists():
            self._watcher.addPath(str(_PROFILS_DIR))
            self._watcher.directoryChanged.connect(self._reload_profiles)

    def _reload_profiles(self) -> None:
        """Scanne data/profils/*.json et reconstruit les boutons."""
        # Nettoyer les anciens boutons (sauf le label)
        for btn in self._boutons:
            self._action_layout.removeWidget(btn)
            btn.deleteLater()
        self._boutons.clear()

        if not _PROFILS_DIR.exists() or not _PROFILS_DIR.is_dir():
            self._action_layout.addStretch(1)
            return

        fichiers = sorted(glob(str(_PROFILS_DIR / "*.json")))
        profils: list[dict] = []

        for chemin in fichiers:
            try:
                with open(chemin, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if "name" not in data or "params" not in data:
                    continue
                data["_fichier"] = Path(chemin).stem
                profils.append(data)
            except (json.JSONDecodeError, OSError):
                continue

        # Trier par order puis nom
        profils.sort(key=lambda p: (p.get("order", 99), p.get("name", "")))

        for profil in profils:
            nom = profil.get("name", "Profil")
            icone = profil.get("icon", "⚙️")
            fichier = profil["_fichier"]

            btn = QPushButton(f"{icone} {nom}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._btn_style_profil(fichier == self._profil_actif))

            # Marquer comme actif si c'est le profil courant
            if fichier == self._profil_actif:
                btn.setProperty("actif", True)

            btn.clicked.connect(lambda _, f=fichier: self._on_profil_clicked(f))
            self._action_layout.addWidget(btn)
            self._boutons.append(btn)

        self._action_layout.addStretch(1)

        if not profils:
            aucun = QLabel("Aucun profil trouvé")
            aucun.setStyleSheet(
                f"color: {_COLORS['TEXT_MUTED']};"
                f"font-size: 11px; font-style: italic;"
            )
            self._action_layout.addWidget(aucun)
            self._boutons.append(aucun)

    def _on_profil_clicked(self, fichier: str) -> None:
        """Déclenché quand l'utilisateur clique sur un profil."""
        self._apply_profile(fichier)

    # ═══════════════════════════════════════════════════════════
    #  Application d'un profil
    # ═══════════════════════════════════════════════════════════

    _CAT_TO_PAGE: dict[str, str] = {
        "general": "Général",
        "reseau": "Réseau",
        "recherche": "config-recherche",
        "telechargement": "config-telechargement",
        "utilisateurs": "Utilisateurs",
        "partages": "Partages",
        "salons": "Salons",
        "debug": "Debug",
    }

    def _apply_profile(self, fichier: str) -> None:
        """Lit un profil JSON et applique les réglages page par page."""
        # Éviter les doubles clics pendant une séquence en cours
        if self._applying:
            return
        self._applying = True
        chemin = _PROFILS_DIR / f"{fichier}.json"
        try:
            with open(chemin, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self._log(f"❌ Erreur lecture profil : {e}")
            EventBus().emit_event(
                severity="ERROR",
                category="optimiseur",
                title="Erreur de lecture",
                message=f"Impossible de lire le profil {fichier}: {e}",
                source="BotOptimiseur",
            )
            return

        nom = data.get("name", fichier)
        icone = data.get("icon", "⚙️")
        params_groupes = data.get("params", {})

        if not self._center_zone:
            self._log("❌ Centre zone non disponible")
            return

        # Construire la séquence : (page_name, ConfigPage, dict_with_full_keys)
        sequence: list[tuple[str, ConfigPage, dict]] = []
        for cat_key, cat_params in params_groupes.items():
            page_name = self._CAT_TO_PAGE.get(cat_key)
            if not page_name:
                self._log(f"⚠ Catégorie inconnue : {cat_key}")
                continue

            page = self._center_zone.page(page_name)
            if page is None or not isinstance(page, ConfigPage):
                self._log(f"⚠ Page non trouvée : {page_name}")
                continue

            # Reconstruire les clés complètes (cat_key.sub_key → valeur)
            full_params: dict[str, object] = {}
            for sub_key, valeur in cat_params.items():
                # Les clés dans le JSON ont déjà le préfixe catégorie (ex: "general.scan_on_start")
                # Ne pas ajouter le préfixe à nouveau pour éviter "general.general.scan_on_start"
                full_params[sub_key] = valeur

            sequence.append((page_name, page, full_params))

        if not sequence:
            self._log("⚠ Aucune page de config ciblée")
            EventBus().emit_event(
                severity="WARN",
                category="optimiseur",
                title="Profil vide",
                message=f"Le profil {icone} {nom} ne cible aucune page de configuration",
                source="BotOptimiseur",
            )
            return

        self._log(f"🎯 Application de {icone} {nom}…")
        EventBus().emit_event(
            severity="INFO",
            category="optimiseur",
            title="Application du profil",
            message=f"Application du profil {icone} {nom} en cours…",
            source="BotOptimiseur",
        )
        self._profil_actif = fichier
        self._reload_profiles()

        # Initialiser l'état de la séquence
        self._nom_applique = nom
        self._icone_applique = icone
        self._sequence = sequence
        self._step = 0
        self._diffs_globaux = []

        self._apply_step()

    def _apply_step(self) -> None:
        """Applique les paramètres de l'étape courante, puis passe à la suivante."""
        if self._step >= len(self._sequence):
            self._finish_apply()
            return

        page_name, page, params = self._sequence[self._step]

        # Naviguer vers la page
        self._center_zone.show_page(page_name)

        # Appliquer les paramètres de cette page
        diffs = page.applique_profile(params)

        # Highlight chaque widget modifié + log
        for config_key, ancienne, nouvelle, widget in diffs:
            if widget is not None:
                highlight_widget(widget)
            if ancienne != nouvelle:
                self._log(f"  {config_key}: {ancienne} → {nouvelle}")
                self._diffs_globaux.append((config_key, ancienne, nouvelle))

        self._step += 1

        # Passer à la page suivante après 1.2s (laisser le temps de voir les highlights)
        QTimer.singleShot(1200, self._apply_step)

    def _finish_apply(self) -> None:
        """Termine l'application : retour Optimiseur + dashboard + overlay."""
        self._applying = False
        # Revenir à l'Optimiseur
        self._center_zone.show_page("Optimiseur")

        n_modifs = len(self._diffs_globaux)
        self._log(
            f"✅ {self._icone_applique} {self._nom_applique} — "
            f"{n_modifs} modification(s)"
        )
        EventBus().emit_event(
            severity="INFO",
            category="optimiseur",
            title="Profil appliqué",
            message=f"Profil {self._icone_applique} {self._nom_applique} appliqué — {n_modifs} modification(s)",
            source="BotOptimiseur",
        )

        # Mettre à jour le dashboard
        self._update_dashboard(
            self._nom_applique,
            self._icone_applique,
            self._diffs_globaux,
        )

        # Overlay de confirmation avec auto-fermeture
        self._overlay_label.setText(
            f"✅ {self._icone_applique} {self._nom_applique} appliqué — "
            f"{n_modifs} modif(s)"
        )
        self._start_overlay_timer()

    def _build_overlay(self) -> None:
        """Construit l'overlay de confirmation (caché par défaut)."""
        self._overlay = QFrame(self)
        self._overlay.setObjectName("optimiseurOverlay")
        self._overlay.setStyleSheet(
            f"#optimiseurOverlay {{"
            f"  background: {_COLORS['BG_SURFACE']};"
            f"  border: 1px solid {_COLORS['BORDER']};"
            f"  border-radius: 10px;"
            f"}}"
        )
        self._overlay.setFixedSize(320, 90)

        overlay_layout = QVBoxLayout(self._overlay)
        overlay_layout.setContentsMargins(16, 12, 16, 12)
        overlay_layout.setSpacing(6)

        self._overlay_label = QLabel("")
        self._overlay_label.setStyleSheet(
            f"color: {_COLORS['TEXT_PRIMARY']};"
            f"font-size: 12px; font-weight: 600;"
        )
        overlay_layout.addWidget(self._overlay_label)

        # Compteur + bouton
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)

        self._overlay_compteur = QLabel("")
        self._overlay_compteur.setStyleSheet(
            f"color: {_COLORS['TEXT_MUTED']};"
            f"font-size: 10px;"
        )
        bottom_row.addWidget(self._overlay_compteur)

        bottom_row.addStretch(1)

        btn_rester = QPushButton("🔒 Rester")
        btn_rester.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_rester.setStyleSheet(
            f"QPushButton {{"
            f"  background: {_COLORS['BG_BTN']};"
            f"  color: {_COLORS['ACCENT']};"
            f"  border: 1px solid {_COLORS['ACCENT']};"
            f"  border-radius: 6px;"
            f"  padding: 4px 12px;"
            f"  font-size: 11px; font-weight: 600;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {_COLORS['BG_HOVER']};"
            f"}}"
        )
        btn_rester.clicked.connect(self._hide_overlay)
        bottom_row.addWidget(btn_rester)

        overlay_layout.addLayout(bottom_row)

        self._overlay.hide()

        self._overlay_timer_id: int | None = None
        self._overlay_compte: int = 6

    def _show_overlay(self) -> None:
        """Affiche l'overlay centré dans le widget."""
        if not self._overlay:
            return

        self._overlay.adjustSize()
        parent_rect = self.rect()
        x = (parent_rect.width() - self._overlay.width()) // 2
        y = parent_rect.height() - self._overlay.height() - 20
        self._overlay.move(x, y)
        self._overlay.raise_()
        self._overlay.show()

    def _start_overlay_timer(self) -> None:
        """Démarre le compte à rebours de fermeture de l'overlay."""
        self._overlay_compte = 6
        self._overlay_compteur.setText(f"Fermeture dans {self._overlay_compte}s")

        if self._overlay_timer_id is not None:
            self.killTimer(self._overlay_timer_id)

        self._show_overlay()
        self._overlay_timer_id = self.startTimer(1000)

    def timerEvent(self, event: object) -> None:
        """Qt timer event — compte à rebours de l'overlay."""
        from PySide6.QtCore import QTimerEvent

        if not isinstance(event, QTimerEvent):
            return
        if event.timerId() != self._overlay_timer_id:
            return

        self._overlay_compte -= 1
        if self._overlay_compte <= 0:
            self._hide_overlay()
        else:
            self._overlay_compteur.setText(
                f"Fermeture dans {self._overlay_compte}s"
            )

    def _hide_overlay(self) -> None:
        """Cache l'overlay et arrête le timer."""
        if self._overlay_timer_id is not None:
            self.killTimer(self._overlay_timer_id)
            self._overlay_timer_id = None
        if self._overlay:
            self._overlay.hide()

    # ═══════════════════════════════════════════════════════════
    #  Viewer (logs)
    # ═══════════════════════════════════════════════════════════

    def _log(self, message: str) -> None:
        """Ajoute une ligne horodatée dans le viewer."""
        from datetime import datetime

        horodatage = datetime.now().strftime("%H:%M:%S")
        ligne = (
            f"<span style='color:{_COLORS['TEXT_MUTED']}'>"
            f"[{horodatage}]</span> {message}<br>"
        )
        self._log_area.append(ligne)

        # Auto-scroll vers le bas
        barre = self._log_area.verticalScrollBar()
        if barre:
            barre.setValue(barre.maximum())

    def _copier_logs(self) -> None:
        """Copie le contenu du viewer dans le presse-papier."""
        from PySide6.QtWidgets import QApplication

        texte = self._log_area.toPlainText()
        if not texte.strip():
            return
        cb = QApplication.clipboard()
        if cb:
            cb.setText(texte)

    # ═══════════════════════════════════════════════════════════
    #  Dashboard
    # ═══════════════════════════════════════════════════════════

    def _update_dashboard(
        self,
        nom_profile: str,
        icone: str,
        diffs_globaux: list[tuple[str, str, str]],
    ) -> None:
        """Met à jour le dashboard avec les diffs reçus.

        Args:
            nom_profile: Nom du profil appliqué.
            icone: Icône du profil.
            diffs_globaux: Liste de (config_key, ancienne_valeur, nouvelle_valeur).
        """
        # Mise à jour de la carte profil
        self._profil_label.setText(f"{icone} {nom_profile}")

        n_modifs = len(diffs_globaux)
        if n_modifs > 0:
            self._statut_label.setText(
                f"✅ Appliqué — {n_modifs} modification(s)"
            )
            self._statut_label.setStyleSheet(
                f"color: {_COLORS['SUCCESS']}; font-size: 11px;"
            )
        else:
            self._statut_label.setText(f"✓ Aucune modification")
            self._statut_label.setStyleSheet(
                f"color: {_COLORS['TEXT_MUTED']}; font-size: 11px;"
            )

        # Vider et reconstruire la liste des diffs
        self._vider_diffs()

        if not diffs_globaux:
            self._placeholder_diff.setText(
                "✓ Tous les paramètres\nétaient déjà à jour"
            )
            self._diff_layout.addWidget(self._placeholder_diff)
            self._diff_layout.addStretch(1)
            return

        # Ajouter les lignes de diff
        for config_key, ancienne, nouvelle in diffs_globaux:
            ligne = self._creer_ligne_diff(config_key, ancienne, nouvelle)
            self._diff_layout.addWidget(ligne)

        self._diff_layout.addStretch(1)

    def _creer_ligne_diff(
        self, config_key: str, ancienne: str, nouvelle: str
    ) -> QWidget:
        """Crée un widget représentant une ligne de diff."""
        ligne = QFrame()
        ligne.setObjectName("diffLine")
        ligne.setStyleSheet(
            f"#diffLine {{"
            f"  background: {_COLORS['BG_MAIN']};"
            f"  border: 1px solid {_COLORS['BORDER']};"
            f"  border-radius: 4px;"
            f"  padding: 4px 6px;"
            f"}}"
        )

        hbox = QHBoxLayout(ligne)
        hbox.setContentsMargins(6, 4, 6, 4)
        hbox.setSpacing(6)

        # Clé
        cle = QLabel(config_key)
        cle.setStyleSheet(
            f"color: {_COLORS['ACCENT']};"
            f"font-size: 10px; font-weight: 600;"
            f"font-family: 'Consolas', 'Fira Code', monospace;"
        )
        hbox.addWidget(cle, 1)

        # Ancienne valeur (barrée)
        ancien = QLabel(ancienne)
        ancien.setStyleSheet(
            f"color: {_COLORS['DANGER']}AA;"
            f"font-size: 10px;"
            f"font-family: 'Consolas', 'Fira Code', monospace;"
            f"text-decoration: line-through;"
        )
        hbox.addWidget(ancien)

        # Flèche
        fleche = QLabel("→")
        fleche.setStyleSheet(
            f"color: {_COLORS['TEXT_MUTED']}; font-size: 10px;"
        )
        hbox.addWidget(fleche)

        # Nouvelle valeur
        nouveau = QLabel(nouvelle)
        nouveau.setStyleSheet(
            f"color: {_COLORS['SUCCESS']};"
            f"font-size: 10px; font-weight: 600;"
            f"font-family: 'Consolas', 'Fira Code', monospace;"
        )
        hbox.addWidget(nouveau)

        return ligne

    def _vider_diffs(self) -> None:
        """Supprime tous les widgets de diff du layout (sans ré-ajouter le placeholder).

        L'appelant doit gérer le placeholder selon le contexte.
        """
        while self._diff_layout.count() > 0:
            item = self._diff_layout.takeAt(0)
            if item is not None:
                w = item.widget()
                if w is not None:
                    w.deleteLater()

        self._placeholder_diff.setText("")

    def _reset_dashboard(self) -> None:
        """Réinitialise le dashboard et les logs."""
        self._profil_label.setText(_DASHBOARD_EMPTY)
        self._statut_label.setText("")
        self._log_area.clear()
        self._vider_diffs()
        self._placeholder_diff.setText("⚠ Cliquez sur un profil\ndans la barre d'action")
        self._profil_actif = None
        self._reload_profiles()
        self._log("🔄 Tableau de bord réinitialisé")
