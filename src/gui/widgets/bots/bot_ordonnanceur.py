"""
Bot Ordonnanceur — Assistant d'organisation des téléchargements.

Assistant pas à pas (4 étapes) pour classer, renommer, dédoublonner
et nettoyer les fichiers téléchargés.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.gui.theme_fragments.colors import COLORS
from src.services.ordonnanceur_service import OrdonnanceurService
from src.services.planificateur_service import planificateur_service

logger = logging.getLogger(__name__)


# ── Intégration Planificateur ───────────────────────────────────────────

_ACTION_EXECUTOR: OrdonnanceurService | None = None


class _PlanificateurWorker(QObject):
    """Worker exécutant une action planifiée dans un thread dédié."""

    completed = Signal(int, bool, str)  # (action_id, succes, message)

    def __init__(
        self,
        action_id: int,
        action_type: str,
        params: dict,
    ) -> None:
        super().__init__()
        self._action_id = action_id
        self._action_type = action_type
        self._params = params

    def run(self) -> None:
        """Point d'entrée du thread. Appelé via QThread.started."""
        assert _ACTION_EXECUTOR is not None

        thread_name = threading.current_thread().name
        logger.info(
            "[Threading] Worker lance action_id=%s type=%s thread=%s",
            self._action_id,
            self._action_type,
            thread_name,
        )

        try:
            resultat = _ACTION_EXECUTOR.executer_action_planificateur(
                action_type=self._action_type,
                params=self._params,
            )
            self.completed.emit(
                self._action_id,
                resultat["succes"],
                resultat["message"],
            )
            logger.info(
                "[Threading] Worker termine action_id=%s type=%s succes=True thread=%s",
                self._action_id,
                self._action_type,
                threading.current_thread().name,
            )
        except Exception as e:
            logger.error(
                "[Threading] Worker echoue action_id=%s type=%s erreur=%s thread=%s",
                self._action_id,
                self._action_type,
                e,
                threading.current_thread().name,
            )
            self.completed.emit(
                self._action_id,
                False,
                f"Erreur : {e}",
            )


def _connect_planificateur() -> None:
    """Connecte le Planificateur à l'Ordonnanceur pour l'exécution automatique."""
    global _ACTION_EXECUTOR
    _ACTION_EXECUTOR = OrdonnanceurService()
    planificateur_service.action_changed.connect(_on_action_planifiee)


def _on_action_planifiee(action_id: int, action_type: str, statut: str) -> None:
    """Lance une action ordonnanceur dans un thread dédié (via QThread)."""
    if statut != "en_cours":
        return
    if action_type not in ("classement", "renommage", "deduplication", "nettoyage_temp"):
        return
    if _ACTION_EXECUTOR is None:
        logger.warning(
            "[Threading] Action ignoree action_id=%s type=%s: _ACTION_EXECUTOR=None",
            action_id,
            action_type,
        )
        return

    action = planificateur_service.get_action(action_id)
    if action is None:
        logger.warning(
            "[Threading] Action introuvable action_id=%s type=%s",
            action_id,
            action_type,
        )
        return

    try:
        raw = action.get("parametres", "{}")
        params = json.loads(raw) if raw else {}
    except (json.JSONDecodeError, TypeError):
        params = {}

    logger.info(
        "[Threading] Demarrage thread action_id=%s type=%s params=%s",
        action_id,
        action_type,
        params,
    )

    # Lancer dans un thread dédié pour ne pas bloquer le main thread
    worker = _PlanificateurWorker(
        action_id=action_id,
        action_type=action_type,
        params=params,
    )
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.completed.connect(_PLANIFICATEUR_RECEIVER.on_action_terminee)
    worker.completed.connect(thread.quit)
    worker.completed.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.start()


class _PlanificateurReceiver(QObject):
    """Receiver vivant dans le main thread pour les callbacks du worker.

    Garantit que complete_action() est appelé depuis le main thread
    (Qt utilise AutoConnection → QueuedConnection pour cross-thread).
    """

    def on_action_terminee(self, action_id: int, succes: bool, message: str) -> None:
        """Callback appelé quand le worker a fini (exécuté dans le main thread)."""
        logger.info(
            "[Threading] Callback action_id=%s succes=%s message=%s thread=%s",
            action_id,
            succes,
            message,
            threading.current_thread().name,
        )
        if succes:
            planificateur_service.complete_action(action_id, succes=True)
        else:
            planificateur_service.complete_action(action_id, succes=False, erreur=message)


_PLANIFICATEUR_RECEIVER = _PlanificateurReceiver()


_connect_planificateur()

# ── Constantes ──────────────────────────────────────────────────────

_STEPS = [
    "📋 Choix des opérations",
    "👀 Aperçu des modifications",
    "⚙️ Exécution en cours",
    "📊 Rapport final",
]

_OPERATIONS = [
    ("classement", "📂 Classer par artiste/album", "Déplacer les fichiers dans une arborescence Artiste/Album"),
    ("renommage", "✏️ Renommer intelligemment", "Normaliser les noms selon un template configurable"),
    ("dedoublonner", "🗑️ Dédoublonner", "Supprimer les fichiers en double (nom+taille puis hash)"),
    ("nettoyage", "🧹 Nettoyer fichiers temp", "Supprimer les fichiers .part, caches et logs obsolètes"),
]

_STEP_CIRCLE_ACTIVE = (
    f"background: {COLORS['ACCENT']}; color: #ffffff;"
    " border-radius: 12px; font-weight: 700; font-size: 13px;"
    " min-width: 24px; min-height: 24px; max-width: 24px; max-height: 24px;"
)
_STEP_CIRCLE_INACTIVE = (
    f"background: {COLORS['BG_SIDE']}; color: {COLORS['TEXT_PLACEHOLDER']};"
    " border-radius: 12px; font-weight: 600; font-size: 13px;"
    " min-width: 24px; min-height: 24px; max-width: 24px; max-height: 24px;"
)
_STEP_LABEL_ACTIVE = f"color: {COLORS['ACCENT']}; font-weight: 600; font-size: 12px;"
_STEP_LABEL_INACTIVE = f"color: {COLORS['TEXT_PLACEHOLDER']}; font-size: 12px;"

_BTN_PRIMARY = (
    f"QPushButton {{ background: {COLORS['ACCENT']}; color: #ffffff;"
    " border: none; border-radius: 6px; padding: 8px 20px;"
    " font-weight: 600; font-size: 13px; }"
    f"QPushButton:hover {{ background: {COLORS['ACCENT_HOVER']}; }}"
    f"QPushButton:pressed {{ background: {COLORS['ACCENT']}; }}"
    f"QPushButton:disabled {{ background: {COLORS['BG_SIDE']}; color: {COLORS['TEXT_PLACEHOLDER']}; }}"
)
_BTN_SECONDARY = (
    f"QPushButton {{ background: {COLORS['BG_SIDE']}; color: {COLORS['TEXT_PRIMARY']};"
    f" border: 1px solid {COLORS['BORDER']}; border-radius: 6px; padding: 8px 20px;"
    " font-weight: 500; font-size: 13px; }"
    f"QPushButton:hover {{ background: {COLORS['BORDER']}; }}"
    f"QPushButton:pressed {{ background: {COLORS['BG_SIDE']}; }}"
)
_BTN_DANGER = (
    f"QPushButton {{ background: {COLORS['DANGER_BTN']}; color: #ffffff;"
    " border: none; border-radius: 6px; padding: 8px 20px;"
    " font-weight: 600; font-size: 13px; }"
    f"QPushButton:hover {{ background: {COLORS['DANGER_BTN_HOVER']}; }}"
    "QPushButton:pressed { background: #a93226; }"
)


class _AnalyseWorker(QObject):
    """Worker exécutant l'analyse du dossier dans un thread séparé."""

    finished = Signal(object, object)  # analyse, apercu
    error = Signal(str)

    def __init__(
        self,
        service: OrdonnanceurService,
        dossier: Path,
        selected_ops: set[str],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._dossier = dossier
        self._selected_ops = selected_ops

    def run(self) -> None:
        """Point d'entrée du thread d'analyse."""
        try:
            analyse = self._service.analyser_dossier(self._dossier)
            ops_list = list(self._selected_ops)
            apercu = self._service.generer_apercu(analyse, ops_list)
            self.finished.emit(analyse, apercu)
        except Exception as e:
            self.error.emit(str(e))


class _OrdonnanceurWorker(QObject):
    """Worker exécutant les opérations dans un thread séparé."""

    started = Signal()
    progress = Signal(str, int, int)  # operation, current, total
    log = Signal(str)  # message
    completed = Signal(dict)
    error = Signal(str)
    finished = Signal()

    def __init__(
        self,
        service: OrdonnanceurService,
        apercu: dict,
        simuler: bool,
        selected_ops: set[str],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._apercu = apercu
        self._simuler = simuler
        self._selected_ops = selected_ops
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        """Point d'entrée du thread. Appelé via QThread.started."""
        self.started.emit()
        try:
            progress_cb = lambda op, cur, tot: self.progress.emit(op, cur, tot)
            resultat = self._service.executer_operations(self._apercu, simuler=self._simuler, on_progress=progress_cb)
            if self._cancelled:
                return
            self.completed.emit(resultat)
        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))
        finally:
            self.finished.emit()


class BotOrdonnanceur(QFrame):
    """Assistant pas à pas pour l'organisation des téléchargements."""

    page_changed = Signal(str)
    unseen_count_changed = Signal(int)

    def __init__(
        self,
        center_zone: QWidget | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("botOrdonnanceur")

        self._center_zone = center_zone
        self._step = 0  # 0-3
        self._unseen_count = 0

        # Service
        self._service = OrdonnanceurService()

        # Threads
        self._analyse_thread: QThread | None = None
        self._analyse_worker: _AnalyseWorker | None = None

        # Opérations sélectionnées
        self._selected_ops: set[str] = set()

        # État
        self._dossier: Path | None = None
        self._analyse: dict | None = None
        self._apercu: dict | None = None
        self._resultat: dict | None = None
        self._executer_reel: bool = False
        self._worker: _OrdonnanceurWorker | None = None
        self._thread: QThread | None = None
        self._log_lines: list[str] = []

        # Progression
        self._progress_bars: dict[str, QProgressBar] = {}

        # Widgets du wizard
        self._step_circles: list[QLabel] = []
        self._step_labels: list[QLabel] = []
        self._op_checkboxes: dict[str, QCheckBox] = {}
        self._log_label: QLabel | None = None
        self._folder_label: QLabel | None = None
        self._back_btn: QPushButton | None = None
        self._next_btn: QPushButton | None = None

        self._build_ui()

    # ── Construction UI ───────────────────────────────────────────

    def _build_ui(self) -> None:
        """Construit l'interface complète du wizard."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(0)

        # ── Header ────────────────────────────────────────────────
        header = QLabel("🧹 Ordonnanceur — Assistant d'organisation")
        header.setStyleSheet(f"color: {COLORS['ACCENT']}; font-size: 18px; font-weight: 700; padding-bottom: 4px;")
        layout.addWidget(header)

        subtitle = QLabel("Classe, renomme, dédoubleonne et nettoie tes téléchargements.")
        subtitle.setStyleSheet(f"color: {COLORS['TEXT_PLACEHOLDER']}; font-size: 12px; padding-bottom: 16px;")
        layout.addWidget(subtitle)

        # ── Barre d'étapes ────────────────────────────────────────
        self._build_step_bar(layout)

        # ── Séparateur ─────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {COLORS['BORDER']};")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # ── Zone de contenu (change selon l'étape) ────────────────
        self._content_scroll = QScrollArea()
        self._content_scroll.setWidgetResizable(True)
        self._content_scroll.setFrameShape(QFrame.NoFrame)
        self._content_scroll.setStyleSheet("background: transparent;")
        self._content_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._content_scroll, stretch=1)

        self._content_widget = QWidget()
        self._content_widget.setStyleSheet("background: transparent;")
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 16, 0, 16)
        self._content_layout.setSpacing(12)
        self._content_scroll.setWidget(self._content_widget)

        # ── Barre de navigation ───────────────────────────────────
        self._build_nav_bar(layout)

        # Afficher l'étape 1 par défaut
        self._show_step(0)

    def _build_step_bar(self, parent: QVBoxLayout) -> None:
        """Construit la barre d'étapes (cercles numérotés + libellés)."""
        step_bar = QHBoxLayout()
        step_bar.setSpacing(8)
        step_bar.setContentsMargins(0, 8, 0, 12)

        for i, step_name in enumerate(_STEPS):
            # Cercle numéroté
            circle = QLabel(str(i + 1))
            circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            circle.setFixedSize(24, 24)
            self._step_circles.append(circle)

            # Libellé
            label = QLabel(step_name)
            self._step_labels.append(label)

            step_bar.addWidget(circle)
            step_bar.addWidget(label)

            if i < len(_STEPS) - 1:
                # Trait de liaison
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setFixedHeight(1)
                line.setStyleSheet(f"color: {COLORS['BORDER']};")
                line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                step_bar.addWidget(line)

        parent.addLayout(step_bar)

    def _build_nav_bar(self, parent: QVBoxLayout) -> None:
        """Construit la barre de navigation (précédent / suivant / annuler)."""
        nav_bar = QFrame()
        nav_bar.setFixedHeight(52)
        nav_bar.setStyleSheet(f"background: {COLORS['BG_SIDE']}; border-radius: 8px;")
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(12, 8, 12, 8)

        # Annuler
        cancel_btn = QPushButton("✕ Annuler")
        cancel_btn.setStyleSheet(_BTN_DANGER)
        cancel_btn.clicked.connect(self._on_cancel)
        nav_layout.addWidget(cancel_btn)

        nav_layout.addStretch(1)

        # Précédent
        self._back_btn = QPushButton("← Précédent")
        self._back_btn.setStyleSheet(_BTN_SECONDARY)
        self._back_btn.clicked.connect(self._on_previous)
        nav_layout.addWidget(self._back_btn)

        # Suivant / Lancer
        self._next_btn = QPushButton("Suivant →")
        self._next_btn.setStyleSheet(_BTN_PRIMARY)
        self._next_btn.clicked.connect(self._on_next)
        nav_layout.addWidget(self._next_btn)

        parent.addWidget(nav_bar)

    # ── Contenu des étapes ───────────────────────────────────────

    def _clear_content(self) -> None:
        """Supprime tous les widgets de la zone de contenu."""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _show_step(self, step: int) -> None:
        """Affiche le contenu de l'étape donnée."""
        self._step = step
        self._clear_content()

        # Mettre à jour les cercles / libellés
        for i in range(len(_STEPS)):
            active = i == step
            completed = i < step
            self._step_circles[i].setStyleSheet(_STEP_CIRCLE_ACTIVE if active or completed else _STEP_CIRCLE_INACTIVE)
            self._step_labels[i].setStyleSheet(_STEP_LABEL_ACTIVE if active else _STEP_LABEL_INACTIVE)

        # Contenu spécifique à l'étape
        if step == 0:
            self._build_step1_choix()
        elif step == 1:
            self._build_step2_apercu()
        elif step == 2:
            self._build_step3_execution()
        elif step == 3:
            self._build_step4_rapport()

        # Boutons de navigation
        self._back_btn.setEnabled(step > 0)

        if step == 0:
            has_selection = len(self._selected_ops) > 0
            self._next_btn.setText("Analyser →")
            self._next_btn.setEnabled(has_selection)
        elif step == 1:
            self._next_btn.setText("🚀 Lancer l'organisation")
            self._next_btn.setEnabled(True)
        elif step == 2:
            self._next_btn.setEnabled(False)
            self._next_btn.setText("En cours…")
        elif step == 3:
            self._next_btn.setText("✓ Recommencer")
            self._next_btn.setEnabled(True)

    def _build_step1_choix(self) -> None:
        """Étape 1 : Choix des opérations."""
        title = QLabel("Étape 1/4 — Choisis les opérations à effectuer")
        title.setStyleSheet(f"color: {COLORS['ACCENT']}; font-size: 15px; font-weight: 600;")
        self._content_layout.addWidget(title)

        desc = QLabel(
            "Sélectionne une ou plusieurs opérations ci-dessous, "
            "puis clique sur <b>Analyser</b> pour voir les fichiers concernés."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {COLORS['TEXT_PLACEHOLDER']}; font-size: 12px;")
        self._content_layout.addWidget(desc)

        self._content_layout.addSpacing(8)

        # Opérations
        self._op_checkboxes: dict[str, QCheckBox] = {}
        for op_key, op_label, op_desc in _OPERATIONS:
            cb = QCheckBox(op_label)
            cb.setToolTip(op_desc)
            cb.setStyleSheet(
                f"color: {COLORS['TEXT_PRIMARY']}; font-size: 13px; font-weight: 500; spacing: 8px; padding: 4px 0px;"
            )
            cb.stateChanged.connect(lambda checked, k=op_key: self._on_op_toggle(k, checked))
            self._op_checkboxes[op_key] = cb
            self._content_layout.addWidget(cb)

            # Sous-description
            sub = QLabel(op_desc)
            sub.setStyleSheet(
                f"color: {COLORS['TEXT_PLACEHOLDER']}; font-size: 11px; padding-left: 28px; padding-bottom: 4px;"
            )
            self._content_layout.addWidget(sub)

        self._content_layout.addSpacing(12)

        # Dossier cible
        folder_section = QFrame()
        folder_section.setStyleSheet(
            f"background: {COLORS['BG_SIDE']}; border-radius: 8px; border: 1px solid {COLORS['BORDER']}; padding: 12px;"
        )
        folder_layout = QVBoxLayout(folder_section)
        folder_layout.setContentsMargins(12, 10, 12, 10)
        folder_layout.setSpacing(6)

        folder_label = QLabel("📁 Dossier à organiser")
        folder_label.setStyleSheet(f"color: {COLORS['TEXT_PRIMARY']}; font-size: 13px; font-weight: 600;")
        folder_layout.addWidget(folder_label)

        picker_row = QHBoxLayout()
        picker_row.setSpacing(8)

        self._folder_label = QLabel(str(self._dossier) if self._dossier else "Aucun dossier sélectionné")
        self._folder_label.setStyleSheet(
            f"color: {COLORS['TEXT_PLACEHOLDER']}; font-size: 12px;"
            " padding: 6px 10px;"
            f" background: {COLORS['BG_SURFACE']}; border-radius: 4px;"
        )
        self._folder_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        picker_row.addWidget(self._folder_label)

        browse_btn = QPushButton("📂 Parcourir…")
        browse_btn.setStyleSheet(
            f"QPushButton {{ background: {COLORS['ACCENT']}; color: #ffffff;"
            " border: none; border-radius: 6px; padding: 6px 16px;"
            " font-weight: 600; font-size: 12px; }"
            f"QPushButton:hover {{ background: {COLORS['ACCENT_HOVER']}; }}"
        )
        browse_btn.clicked.connect(self._on_browse_folder)
        picker_row.addWidget(browse_btn)

        folder_layout.addLayout(picker_row)
        self._content_layout.addWidget(folder_section)

        self._content_layout.addStretch(1)

    def _build_step2_apercu(self) -> None:
        """Étape 2 : Aperçu des modifications."""
        title = QLabel("Étape 2/4 — Aperçu des modifications")
        title.setStyleSheet(f"color: {COLORS['ACCENT']}; font-size: 15px; font-weight: 600;")
        self._content_layout.addWidget(title)

        if not self._apercu:
            no_data = QLabel("Aucune donnée d'aperçu disponible. Retourne à l'étape 1.")
            no_data.setStyleSheet(f"color: {COLORS['TEXT_PLACEHOLDER']}; font-size: 12px;")
            no_data.setWordWrap(True)
            self._content_layout.addWidget(no_data)
            self._content_layout.addStretch(1)
            return

        apercu = self._apercu

        desc = QLabel("Voici un résumé de ce qui va être fait. Vérifie avant de lancer !")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {COLORS['TEXT_PLACEHOLDER']}; font-size: 12px;")
        self._content_layout.addWidget(desc)

        self._content_layout.addSpacing(8)

        # Résumé des fichiers analysés
        nb_fichiers = len(self._analyse.fichiers) if self._analyse else 0
        resum = QLabel(f"📊 {nb_fichiers} fichiers analysés dans {self._dossier or '?'}")
        resum.setStyleSheet(f"color: {COLORS['ACCENT']}; font-size: 14px; font-weight: 600;")
        self._content_layout.addWidget(resum)

        # Sections d'aperçu
        sections = [
            ("renommage", "✏️ Renommage"),
            ("classement", "📂 Classement"),
            ("deduplication", "🗑️ Dédoublonnage"),
            ("nettoyage", "🧹 Nettoyage"),
        ]

        total_economie = 0
        for key, label in sections:
            section = apercu.get(key)
            if not section:
                continue

            # Compter les fichiers selon la structure de chaque opération
            if key == "deduplication":
                nb = section.get("total_doublons", 0)
            else:
                fichiers = section.get("fichiers", [])
                nb = len(fichiers)
            if nb == 0:
                continue

            # Économie selon la clé propre à chaque opération
            if key == "deduplication":
                economie = section.get("total_economise", 0) or 0
            elif key == "nettoyage":
                economie = section.get("taille_totale", 0) or 0
            else:
                economie = 0
            total_economie += economie

            card = QFrame()
            card.setStyleSheet(
                f"background: {COLORS['BG_SIDE']}; border-radius: 8px;"
                f" border: 1px solid {COLORS['BORDER']}; padding: 12px;"
            )
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(12, 8, 12, 8)

            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {COLORS['TEXT_PRIMARY']}; font-size: 13px; font-weight: 500;")
            card_layout.addWidget(lbl)
            card_layout.addStretch(1)

            if economie > 0:
                valeur = f"{nb} fichiers · {self._taille_lisible(economie)} libérés"
            else:
                valeur = f"{nb} fichiers concernés"

            val = QLabel(valeur)
            val.setStyleSheet(f"color: {COLORS['ACCENT']}; font-size: 13px; font-weight: 600;")
            card_layout.addWidget(val)

            self._content_layout.addWidget(card)

        if total_economie > 0:
            eco_label = QLabel(f"💾 Total économie estimée : {self._taille_lisible(total_economie)}")
            eco_label.setStyleSheet(f"color: {COLORS['TEXT_PRIMARY']}; font-size: 13px; font-style: italic;")
            self._content_layout.addWidget(eco_label)

        # ── Checkbox exécution réelle ──────────────────────────
        exec_cb = QCheckBox("⚡ Appliquer les modifications sur le disque")
        exec_cb.setToolTip(
            "Coché : les fichiers seront réellement renommés, déplacés et supprimés.\n"
            "Décoché : mode simulation — rien n'est modifié (par défaut)."
        )
        exec_cb.setChecked(self._executer_reel)
        exec_cb.setStyleSheet(
            f"color: {COLORS['TEXT_PRIMARY']}; font-size: 13px; font-weight: 600;"
            " spacing: 8px; padding: 12px 16px;"
            f" background: {COLORS['BG_SIDE']}; border-radius: 8px;"
            f" border: 1px solid {COLORS['DANGER_BTN']};"
        )
        exec_cb.stateChanged.connect(self._on_executer_toggle)
        self._content_layout.addWidget(exec_cb)

        self._content_layout.addStretch(1)

    def _build_step3_execution(self) -> None:
        """Étape 3 : Exécution avec progression."""
        title = QLabel("Étape 3/4 — Exécution en cours")
        title.setStyleSheet(f"color: {COLORS['ACCENT']}; font-size: 15px; font-weight: 600;")
        self._content_layout.addWidget(title)

        if not self._apercu:
            no_data = QLabel("Aucune donnée. Retourne à l'étape 1.")
            no_data.setStyleSheet(f"color: {COLORS['TEXT_PLACEHOLDER']}; font-size: 12px;")
            self._content_layout.addWidget(no_data)
            self._content_layout.addStretch(1)
            return

        info_label = QLabel("Les opérations sont en cours d'exécution…")
        info_label.setStyleSheet(f"color: {COLORS['TEXT_PLACEHOLDER']}; font-size: 12px;")
        self._content_layout.addWidget(info_label)

        self._content_layout.addSpacing(8)

        # Barres de progression par opération
        self._progress_bars.clear()
        for op_key, op_label, _ in _OPERATIONS:
            if op_key in self._selected_ops:
                op_frame = QFrame()
                op_frame.setStyleSheet(
                    f"background: {COLORS['BG_SIDE']}; border-radius: 8px;"
                    f" border: 1px solid {COLORS['BORDER']}; padding: 12px;"
                )
                op_layout = QVBoxLayout(op_frame)
                op_layout.setContentsMargins(12, 10, 12, 10)
                op_layout.setSpacing(6)

                lbl = QLabel(op_label)
                lbl.setStyleSheet(f"color: {COLORS['TEXT_PRIMARY']}; font-size: 13px; font-weight: 500;")
                op_layout.addWidget(lbl)

                pb = QProgressBar()
                pb.setRange(0, 100)
                pb.setValue(0)
                pb.setTextVisible(True)
                pb.setFixedHeight(20)
                pb.setStyleSheet(
                    f"QProgressBar {{ background: {COLORS['BORDER']};"
                    " border: none; border-radius: 10px; text-align: center;"
                    f" color: {COLORS['TEXT_PRIMARY']}; font-size: 11px; }}"
                    f"QProgressBar::chunk {{ background: {COLORS['ACCENT']};"
                    " border-radius: 10px; }}"
                )
                op_layout.addWidget(pb)
                self._progress_bars[op_key] = pb
                self._content_layout.addWidget(op_frame)

        # Log en direct
        log_label = QLabel("Journal d'exécution :")
        log_label.setStyleSheet(f"color: {COLORS['TEXT_PLACEHOLDER']}; font-size: 11px; font-weight: 500;")
        self._content_layout.addWidget(log_label)

        self._log_label = QLabel("\n".join(self._log_lines[-6:]) or "Préparation…")
        self._log_label.setWordWrap(True)
        self._log_label.setStyleSheet(
            f"color: {COLORS['TEXT_PLACEHOLDER']}; font-size: 11px;"
            f" background: {COLORS['BG_SIDE']}; border-radius: 6px;"
            f" border: 1px solid {COLORS['BORDER']}; padding: 8px;"
        )
        self._content_layout.addWidget(self._log_label)

        self._content_layout.addStretch(1)

        # Lancer l'exécution dans un thread
        self._start_execution()

    def _build_step4_rapport(self) -> None:
        """Étape 4 : Rapport final enrichi."""
        resultat = self._resultat or {}
        simulation = resultat.get("simulation", True)
        succes = resultat.get("succes", False)
        operations = resultat.get("operations", {})
        erreurs_list = resultat.get("erreurs", [])
        all_details = resultat.get("details", [])

        status_icon = "🔍" if simulation else ("✅" if succes else "⚠️")
        status_text = "Simulation" if simulation else ("Réussi" if succes else "Échec partiel")

        # ── Bouton Copier le rapport ──
        top_bar = QHBoxLayout()
        title = QLabel(f"Étape 4/4 — Rapport final {status_icon}")
        title.setStyleSheet(f"color: {COLORS['ACCENT']}; font-size: 15px; font-weight: 600;")
        top_bar.addWidget(title)
        top_bar.addStretch(1)

        btn_copier = QPushButton("📋 Copier le rapport")
        btn_copier.setStyleSheet(
            f"QPushButton {{ background: {COLORS['BG_SURFACE2']}; color: {COLORS['TEXT_PRIMARY']};"
            f" border: 1px solid {COLORS['BORDER']}; border-radius: 6px; padding: 6px 14px;"
            f" font-size: 12px; }}"
            f"QPushButton:hover {{ background: {COLORS['BG_HOVER']}; }}"
        )
        btn_copier.clicked.connect(lambda: self._copier_rapport(resultat))
        top_bar.addWidget(btn_copier)

        self._content_layout.addLayout(top_bar)

        desc = QLabel(f"Opérations terminées — {status_text}. Voici le récapitulatif :")
        desc.setStyleSheet(f"color: {COLORS['TEXT_PLACEHOLDER']}; font-size: 12px;")
        self._content_layout.addWidget(desc)

        self._content_layout.addSpacing(8)

        # ── Cartes par opération enrichies ──
        op_labels = {
            "renommage": "✏️ Renommage",
            "classement": "📂 Classement",
            "deduplication": "🗑️ Dédoublonnage",
            "nettoyage": "🧹 Nettoyage",
        }
        op_emojis = {
            "renommage": "✏️",
            "classement": "📂",
            "deduplication": "🗑️",
            "nettoyage": "🧹",
        }

        for op_key in self._selected_ops:
            stats = operations.get(op_key, {})
            nb_tente = stats.get("tente", 0)
            nb_reussi = stats.get("reussi", 0)
            nb_echoue = stats.get("echoue", 0)

            label = op_labels.get(op_key, op_key)
            status_emoji = "✅" if nb_echoue == 0 else "⚠️"

            # Ligne de stats
            parts = []
            if nb_reussi > 0:
                parts.append(f"{nb_reussi} traités")
            if nb_echoue > 0:
                parts.append(f"{nb_echoue} échoués")

            # Stats spécifiques par opération
            if op_key == "deduplication":
                nb_supprime = stats.get("supprime", 0)
                nb_renomme = stats.get("renomme_gardes", 0)
                if nb_supprime:
                    parts.append(f"{nb_supprime} supprimés")
                if nb_renomme:
                    parts.append(f"{nb_renomme} gardes renommés")
            elif op_key == "nettoyage":
                nb_supprime = stats.get("supprime", 0)
                taille_lib = stats.get("taille_lisible", None)
                if nb_supprime:
                    parts.append(f"{nb_supprime} supprimés")
                if taille_lib:
                    parts.append(f"{taille_lib} libérés")

            if parts:
                detail_str = " · ".join(parts)
            elif nb_tente > 0:
                detail_str = f"{nb_tente} fichiers"
            else:
                detail_str = "Aucun fichier traité"

            # Carte principale
            card = QFrame()
            card.setStyleSheet(
                f"background: {COLORS['BG_SIDE']}; border-radius: 8px;"
                f" border: 1px solid {COLORS['BORDER']}; padding: 10px;"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 8, 12, 8)
            card_layout.setSpacing(6)

            # Ligne titre + stats
            header_row = QHBoxLayout()
            lbl = QLabel(f"{status_emoji} {label}")
            lbl.setStyleSheet(f"color: {COLORS['TEXT_PRIMARY']}; font-size: 13px; font-weight: 600;")
            header_row.addWidget(lbl)
            header_row.addStretch(1)

            val = QLabel(detail_str)
            val.setStyleSheet(f"color: {COLORS['TEXT_PLACEHOLDER']}; font-size: 12px;")
            header_row.addWidget(val)
            card_layout.addLayout(header_row)

            # Barre de progression visuelle
            if nb_tente > 0:
                pct = int(nb_reussi / nb_tente * 100)
                bar = QProgressBar()
                bar.setRange(0, 100)
                bar.setValue(pct)
                bar.setTextVisible(True)
                bar.setFormat(f"{pct}% ({nb_reussi}/{nb_tente})")
                bar.setFixedHeight(16)
                bar.setStyleSheet(
                    f"QProgressBar {{ background: {COLORS['BG_SURFACE2']};"
                    f" border: none; border-radius: 4px; text-align: center;"
                    f" color: {COLORS['TEXT_PRIMARY']}; font-size: 10px; }}"
                    f"QProgressBar::chunk {{ background: {COLORS['ACCENT']};"
                    f" border-radius: 4px; }}"
                )
                card_layout.addWidget(bar)

            # Détails pliables
            op_details = [d for d in all_details if isinstance(d, dict) and d.get("operation") == op_key]
            if op_details:
                toggle_btn = QPushButton(f"📄 Détails ({len(op_details)} fichiers)")
                toggle_btn.setStyleSheet(
                    f"QPushButton {{ background: transparent; color: {COLORS['TEXT_PLACEHOLDER']};"
                    f" border: 1px solid {COLORS['BORDER']}; border-radius: 4px;"
                    f" padding: 4px 10px; font-size: 11px; text-align: left; }}"
                    f"QPushButton:hover {{ background: {COLORS['BG_HOVER']};"
                    f" color: {COLORS['TEXT_PRIMARY']}; }}"
                )
                toggle_btn.setCursor(Qt.PointingHandCursor)
                card_layout.addWidget(toggle_btn)

                details_panel = QFrame()
                details_panel.setStyleSheet(
                    f"background: {COLORS['BG_SURFACE2']}; border-radius: 4px; border: none; padding: 6px;"
                )
                details_layout = QVBoxLayout(details_panel)
                details_layout.setContentsMargins(8, 4, 8, 4)
                details_layout.setSpacing(2)

                max_shown = min(len(op_details), 50)
                for d in op_details[:max_shown]:
                    d_type = d.get("type", "?")
                    if d_type == "simulation":
                        emoji = "🔍"
                    elif d_type == "reussi":
                        emoji = "✅"
                    else:
                        emoji = "⚠️"

                    if op_key == "renommage":
                        ancien = d.get("ancien", "")
                        nouveau = d.get("nouveau", d.get("erreur", "?"))
                        line = f"{emoji} {Path(ancien).name} → {Path(nouveau).name}"
                    elif op_key == "classement":
                        source = d.get("source", d.get("ancien", ""))
                        dest = d.get("destination", d.get("nouveau", d.get("erreur", "?")))
                        line = f"{emoji} {Path(source).name} → {Path(dest).name}"
                    elif op_key == "deduplication":
                        fichier = d.get("fichier", d.get("ancien", d.get("erreur", "?")))
                        line = f"{emoji} {Path(str(fichier)).name}"
                    else:  # nettoyage
                        fichier = d.get("fichier", d.get("chemin", d.get("erreur", "?")))
                        taille = d.get("taille", 0)
                        t_str = f" ({self._taille_lisible(taille)})" if taille else ""
                        line = f"{emoji} {Path(str(fichier)).name}{t_str}"

                    item = QLabel(line)
                    item.setWordWrap(True)
                    item.setStyleSheet(f"color: {COLORS['TEXT_PRIMARY']}; font-size: 11px; padding: 1px 0;")
                    details_layout.addWidget(item)

                if len(op_details) > max_shown:
                    more = QLabel(f"... et {len(op_details) - max_shown} autres")
                    more.setStyleSheet(f"color: {COLORS['TEXT_PLACEHOLDER']}; font-size: 10px;")
                    details_layout.addWidget(more)

                details_panel.setVisible(False)
                card_layout.addWidget(details_panel)

                # Connexion toggle
                toggle_btn.clicked.connect(
                    lambda checked, p=details_panel, b=toggle_btn, n=len(op_details): (
                        b.setText(f"📄 Masquer les détails" if p.isVisible() else f"📄 Détails ({n} fichiers)"),
                        p.setVisible(not p.isVisible()),
                    )
                )

            self._content_layout.addWidget(card)

        # ── Erreurs ──
        if erreurs_list:
            err_frame = QFrame()
            err_frame.setStyleSheet(
                f"background: {COLORS['BG_SIDE']}; border-radius: 8px;"
                f" border: 1px solid {COLORS['DANGER_BTN']}; padding: 10px;"
            )
            err_layout = QVBoxLayout(err_frame)
            err_layout.setContentsMargins(12, 8, 12, 8)
            err_layout.setSpacing(4)

            err_title = QLabel(f"⚠️ {len(erreurs_list)} erreur(s) rencontrée(s)")
            err_title.setStyleSheet(f"color: {COLORS['DANGER_BTN']}; font-size: 13px; font-weight: 600;")
            err_layout.addWidget(err_title)

            for err in erreurs_list[:10]:
                err_op = err.get("operation", "?")
                err_file = err.get("fichier", err.get("erreur", str(err)))
                err_msg = err.get("erreur", "")
                if err_msg:
                    err_text = f"  [{err_op}] {Path(str(err_file)).name} : {err_msg}"
                else:
                    err_text = f"  • {err}"
                err_label = QLabel(err_text)
                err_label.setWordWrap(True)
                err_label.setStyleSheet(f"color: {COLORS['TEXT_PLACEHOLDER']}; font-size: 11px;")
                err_layout.addWidget(err_label)

            if len(erreurs_list) > 10:
                more_err = QLabel(f"  ... et {len(erreurs_list) - 10} autre(s) erreur(s)")
                more_err.setStyleSheet(f"color: {COLORS['TEXT_PLACEHOLDER']}; font-size: 10px;")
                err_layout.addWidget(more_err)

            self._content_layout.addWidget(err_frame)

        # ── Résumé global enrichi ──
        summary = QFrame()
        summary.setStyleSheet(
            f"background: {COLORS['BG_SIDE']}; border-radius: 8px; border: 1px solid {COLORS['BORDER']}; padding: 14px;"
        )
        summary_layout = QVBoxLayout(summary)
        summary_layout.setSpacing(4)

        total_lbl = QLabel("📊 Résumé global")
        total_lbl.setStyleSheet(f"color: {COLORS['ACCENT']}; font-size: 14px; font-weight: 700;")
        summary_layout.addWidget(total_lbl)

        # Stats globales
        total_traites = sum(o.get("reussi", 0) for o in operations.values())
        total_tentes = sum(o.get("tente", 0) for o in operations.values())
        total_erreurs = sum(o.get("echoue", 0) for o in operations.values())

        # Espace économisé par opération
        taille_par_op: dict[str, int] = {}
        for d in all_details:
            if isinstance(d, dict):
                op_name = d.get("operation", "")
                t = d.get("taille", 0) or 0
                taille_par_op[op_name] = taille_par_op.get(op_name, 0) + t

        summary_lines = []
        if total_traites > 0:
            summary_lines.append(f"✅ {total_traites} fichiers traités avec succès")
        if total_erreurs > 0:
            summary_lines.append(f"⚠️ {total_erreurs} fichiers en échec")
        if total_tentes > 0:
            summary_lines.append(f"📋 {total_tentes} fichiers tentés au total")
        summary_lines.append(f"📁 Dossier : {self._dossier or '?'}")
        if simulation:
            summary_lines.append("🔍 Mode simulation — aucune modification réelle")
        else:
            summary_lines.append("⚡ Opérations appliquées sur le disque")

        # Espace économisé par opération
        for op_key, op_label in op_labels.items():
            t = taille_par_op.get(op_key, 0)
            if t > 0:
                summary_lines.append(f"  {op_emojis.get(op_key, '•')} {op_label} : {self._taille_lisible(t)} libérés")

        for line in summary_lines:
            l = QLabel(line)
            l.setStyleSheet(f"color: {COLORS['TEXT_PRIMARY']}; font-size: 12px;")
            summary_layout.addWidget(l)

        self._content_layout.addWidget(summary)
        self._content_layout.addStretch(1)

    # ── Callbacks ─────────────────────────────────────────────────

    # ── Méthodes helpers ──────────────────────────────────────────

    @staticmethod
    def _taille_lisible(octets: int) -> str:
        """Convertit des octets en taille lisible (Ko, Mo, Go)."""
        if octets < 1024:
            return f"{octets} o"
        elif octets < 1024**2:
            return f"{octets / 1024:.1f} Ko"
        elif octets < 1024**3:
            return f"{octets / 1024**2:.1f} Mo"
        else:
            return f"{octets / 1024**3:.1f} Go"

    def _copier_rapport(self, resultat: dict) -> None:
        """Copie un résumé texte du rapport dans le presse-papier."""
        simulation = resultat.get("simulation", True)
        succes = resultat.get("succes", False)
        operations = resultat.get("operations", {})
        erreurs = resultat.get("erreurs", [])
        details = resultat.get("details", [])

        lines = []
        lines.append("=" * 50)
        lines.append("RAPPORT D'EXECUTION - ORDONNANCEUR")
        mode = "SIMULATION" if simulation else "APPLICATION"
        status = "SUCCES" if succes else "ECHEC PARTIEL"
        lines.append(f"Mode : {mode} | Statut : {status}")
        lines.append(f"Dossier : {self._dossier or '?'}")
        lines.append("=" * 50)
        lines.append("")

        op_labels = {
            "renommage": "Renommage",
            "classement": "Classement",
            "deduplication": "Dedoublonnage",
            "nettoyage": "Nettoyage",
        }

        for op_key, op_label in op_labels.items():
            if op_key not in operations:
                continue
            stats = operations[op_key]
            lines.append(f"[{op_label}]")
            if stats.get("tente", 0):
                lines.append(f"  Tente : {stats['tente']}")
            if stats.get("reussi", 0):
                lines.append(f"  Reussi : {stats['reussi']}")
            if stats.get("echoue", 0):
                lines.append(f"  Echoue : {stats['echoue']}")
            if op_key == "deduplication":
                if stats.get("supprime", 0):
                    lines.append(f"  Supprimes : {stats['supprime']}")
                if stats.get("renomme_gardes", 0):
                    lines.append(f"  Gardes renommes : {stats['renomme_gardes']}")
            elif op_key == "nettoyage":
                if stats.get("supprime", 0):
                    lines.append(f"  Supprimes : {stats['supprime']}")
                if stats.get("taille_lisible", None):
                    lines.append(f"  Liberes : {stats['taille_lisible']}")
            # Details fichiers
            op_details = [d for d in details if isinstance(d, dict) and d.get("operation") == op_key]
            if op_details:
                lines.append(f"  Fichiers ({len(op_details)}) :")
                for d in op_details[:20]:
                    d_type = d.get("type", "?")
                    prefix = "[OK]" if d_type == "reussi" else ("[SIM]" if d_type == "simulation" else "[ERR]")
                    fichier = d.get("fichier", d.get("source", d.get("ancien", d.get("chemin", "?"))))
                    lines.append(f"    {prefix} {fichier}")
                if len(op_details) > 20:
                    lines.append(f"    ... et {len(op_details) - 20} autre(s)")
            lines.append("")

        if erreurs:
            lines.append("-" * 30)
            lines.append(f"ERREURS ({len(erreurs)}) :")
            for err in erreurs:
                err_op = err.get("operation", "?")
                err_f = err.get("fichier", "")
                err_msg = err.get("erreur", "?")
                lines.append(f"  [{err_op}] {err_f} : {err_msg}")
            lines.append("")

        lines.append("=" * 50)
        lines.append("Rapport genere par l'Ordonnanceur")
        lines.append("=" * 50)

        texte = "\n".join(lines)
        QApplication.clipboard().setText(texte)

    # ── Callbacks ─────────────────────────────────────────────────

    def _on_executer_toggle(self, checked: int) -> None:
        """Met à jour le flag d'exécution réelle."""
        self._executer_reel = bool(checked)

    def _on_browse_folder(self) -> None:
        """Ouvre un QFileDialog pour choisir le dossier à organiser."""
        dossier = QFileDialog.getExistingDirectory(self, "Choisir le dossier à organiser")
        if dossier:
            self._dossier = Path(dossier)
            self._folder_label.setText(str(self._dossier))

    def _on_op_toggle(self, op_key: str, checked: int) -> None:
        """Met à jour la sélection des opérations."""
        if checked:
            self._selected_ops.add(op_key)
        else:
            self._selected_ops.discard(op_key)

        # Activer/désactiver le bouton Analyser
        has_selection = len(self._selected_ops) > 0
        self._next_btn.setEnabled(has_selection and self._dossier is not None)

    def _on_next(self) -> None:
        """Passe à l'étape suivante."""
        if self._step == 3:
            # Recommencer
            self._selected_ops.clear()
            for cb in self._op_checkboxes.values():
                cb.setChecked(False)
            self._dossier = None
            self._analyse = None
            self._apercu = None
            self._resultat = None
            self._executer_reel = False
            self._log_lines.clear()
            self._show_step(0)
        elif self._step == 0:
            # Lancer l'analyse avant de passer à l'aperçu
            self._run_analysis()
        elif self._step == 1:
            # Passer à l'exécution
            self._show_step(2)
        else:
            self._show_step(self._step + 1)

    def _run_analysis(self) -> None:
        """Lance l'analyse du dossier dans un thread séparé."""
        if not self._dossier or not self._dossier.exists():
            self._next_btn.setEnabled(True)
            self._next_btn.setText("Analyser →")
            return

        # Désactiver les boutons pendant l'analyse
        self._next_btn.setEnabled(False)
        self._next_btn.setText("Analyse en cours…")

        # Nettoyer un thread précédent
        if self._analyse_worker is not None:
            self._analyse_worker = None
        if self._analyse_thread is not None:
            self._analyse_thread.quit()
            self._analyse_thread.wait(2000)
            self._analyse_thread = None

        self._analyse_thread = QThread()
        self._analyse_worker = _AnalyseWorker(
            self._service,
            self._dossier,
            self._selected_ops,
        )
        self._analyse_worker.moveToThread(self._analyse_thread)

        self._analyse_thread.started.connect(self._analyse_worker.run)
        self._analyse_worker.finished.connect(self._on_analysis_completed)
        self._analyse_worker.error.connect(self._on_analysis_error)
        self._analyse_worker.finished.connect(self._analyse_thread.quit)
        self._analyse_worker.finished.connect(self._analyse_worker.deleteLater)
        self._analyse_worker.error.connect(self._analyse_thread.quit)
        self._analyse_worker.error.connect(self._analyse_worker.deleteLater)
        self._analyse_thread.finished.connect(self._analyse_thread.deleteLater)

        self._analyse_thread.start()

    def _on_analysis_completed(self, analyse: object, apercu: dict) -> None:
        """Callback quand l'analyse est terminée."""
        # Si l'utilisateur a navigué ailleurs, ignorer
        if self._step != 0 or self._analyse_thread is None:
            return
        self._analyse = analyse
        self._apercu = apercu
        self._analyse_thread = None
        self._analyse_worker = None
        self._show_step(1)

    def _on_analysis_error(self, error_msg: str) -> None:
        """Callback en cas d'erreur d'analyse."""
        self._analyse_thread = None
        self._analyse_worker = None
        self._next_btn.setEnabled(True)
        self._next_btn.setText("Analyser →")
        err_label = QLabel(f"❌ Erreur d'analyse : {error_msg}")
        err_label.setWordWrap(True)
        err_label.setStyleSheet(f"color: {COLORS['DANGER_BTN']}; font-size: 12px;")
        self._content_layout.addWidget(err_label)

    def _start_execution(self) -> None:
        """Lance l'exécution dans un thread séparé."""
        if not self._apercu:
            return

        simuler = not self._executer_reel

        # Nettoyer les anciens threads
        self._cleanup_thread()

        self._thread = QThread()
        self._worker = _OrdonnanceurWorker(
            self._service,
            self._apercu,
            simuler=simuler,
            selected_ops=self._selected_ops,
        )
        self._worker.moveToThread(self._thread)

        # Connecter les signaux
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_execution_progress)
        self._worker.completed.connect(self._on_execution_completed)
        self._worker.error.connect(self._on_execution_error)
        self._worker.log.connect(self._on_execution_log)

        # Nettoyage
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        # Démarrer le thread
        self._thread.start()

    def _cleanup_thread(self) -> None:
        """Nettoie un thread précédent s'il existe."""
        if self._worker is not None:
            self._worker.cancel()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
        self._worker = None
        self._thread = None

    def _on_execution_progress(self, operation: str, current: int, total: int) -> None:
        """Met à jour la barre de progression en temps réel."""
        bar = self._progress_bars.get(operation)
        if bar is not None:
            bar.setMaximum(total)
            bar.setValue(current)

    def _on_execution_log(self, message: str) -> None:
        """Met à jour le log en direct."""
        self._log_lines.append(message)
        if self._log_label is not None:
            self._log_label.setText("\n".join(self._log_lines[-6:]))

    def _on_execution_completed(self, resultat: dict) -> None:
        """Appelé quand l'exécution est terminée."""
        self._resultat = resultat
        self._show_step(3)

    def _on_execution_error(self, error_msg: str) -> None:
        """Appelé en cas d'erreur d'exécution."""
        self._resultat = {
            "succes": False,
            "simulation": True,
            "operations": {},
            "erreurs": [{"operation": "", "fichier": "", "erreur": error_msg}],
            "details": [],
        }
        self._show_step(3)

    def _on_previous(self) -> None:
        """Revient à l'étape précédente."""
        if self._step == 2:
            # Nettoyer le thread d'exécution avant de revenir en arrière
            self._cleanup_thread()
        elif self._step == 0 and self._analyse_thread is not None:
            # Annuler l'analyse en cours si on revient
            self._analyse_thread.quit()
            self._analyse_thread.wait(2000)
            self._analyse_thread = None
            self._analyse_worker = None
        if self._step > 0:
            self._show_step(self._step - 1)

    def _on_cancel(self) -> None:
        """Annule, nettoie les threads et retourne à l'accueil."""
        self._cleanup_thread()
        # Nettoyer aussi le thread d'analyse
        if self._analyse_thread is not None:
            self._analyse_thread.quit()
            self._analyse_thread.wait(2000)
            self._analyse_thread = None
            self._analyse_worker = None
        self.page_changed.emit("Accueil")

    # ── API publique ──────────────────────────────────────────────

    def reset_unseen_count(self) -> None:
        """Réinitialise le compteur de notifications non lues."""
        self._unseen_count = 0
