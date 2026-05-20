"""
BotPlanificateur — Panneau de gestion des actions planifiées.

Dashboard, barre d'actions rapides, statistiques live, liste des actions.
"""

from __future__ import annotations

from PySide6.QtCore import QDate, Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.theme_fragments.colors import COLORS, rgba
from src.services.planificateur_service import (
    ACTION_STATUTS,
    ACTION_TYPES,
    PlanificateurService,
)

# ── Constantes ──────────────────────────────────────────────────────────────

_ACTION_LABELS: dict[str, str] = {
    "recherche": "Recherche",
    "scan": "Scan",
    "wishlist": "Wishlist",
    "optimisation": "Optimisation",
    "nettoyage": "Nettoyage",
    "telechargement": "Téléchargement",
    "classement": "Classement",
    "renommage": "Renommage",
    "deduplication": "Dédoublonnage",
    "nettoyage_temp": "Nettoyage temporaire",
}

_ACTION_ICONS: dict[str, str] = {
    "recherche": "🔍",
    "scan": "📂",
    "wishlist": "⭐",
    "optimisation": "⚙",
    "nettoyage": "🧹",
    "telechargement": "📥",
    "classement": "📂",
    "renommage": "✏️",
    "deduplication": "🗑️",
    "nettoyage_temp": "🧹",
}

_STATUT_LABELS: dict[str, str] = {
    "en_attente": "⚡ En attente",
    "planifiee": "📅 Planifiée",
    "en_cours": "🔵 En cours",
    "terminee": "✅ Terminée",
    "echouee": "❌ Échouée",
    "pause": "⏸ En pause",
}

_STATUT_COLORS: dict[str, str] = {
    "en_attente": COLORS["WARNING"],
    "planifiee": COLORS["ACCENT"],
    "en_cours": COLORS["STAT_AUDIO"],
    "terminee": COLORS["SUCCESS"],
    "echouee": COLORS["DANGER"],
    "pause": COLORS["TEXT_MUTED"],
}

_MODE_LABELS: dict[str, str] = {
    "immediat": "⚡ Immédiat",
    "planifie": "📅 Planifié",
}

# Couleurs des cartes de statut : (label, color_key, statut_db)
_STAT_CARDS: list[tuple[str, str, str]] = [
    ("⚡ En attente", "WARNING", "en_attente"),
    ("📅 Planifiées", "ACCENT", "planifiee"),
    ("🔵 En cours", "STAT_AUDIO", "en_cours"),
    ("❌ Échouées", "DANGER", "echouee"),
]

# Navigation inter-bots : type d'action → nom de la page cible
_BOT_NAVIGATION: dict[str, str | None] = {
    "recherche": "Recherche",
    "scan": "Bibliothèque",
    "wishlist": "Wishlist",
    "optimisation": "Optimiseur",
    "nettoyage": None,  # Pas de redirection (interne)
    "telechargement": "Téléchargement",
    "classement": "Ordonnanceur",
    "renommage": "Ordonnanceur",
    "deduplication": "Ordonnanceur",
    "nettoyage_temp": "Ordonnanceur",
}

# Colonnes de la table
_COL_TYPE = 0
_COL_MODE = 1
_COL_STATUT = 2
_COL_DATE = 3
_COL_ACTIONS = 4

_COL_HEADERS = ["Action", "Mode", "Statut", "Date", ""]


# ═══════════════════════════════════════════════════════════════════════════════
# ActionModal — Modal de création / édition d'action
# ═══════════════════════════════════════════════════════════════════════════════


class ActionModal(QDialog):
    """
    Modal de création / édition d'une action planifiée.

    Champs dynamiques selon le type d'action sélectionné :
    - recherche  → mots-clés
    - scan       → dossier
    - wishlist   → artiste + album
    - optimisation → profil
    - nettoyage  → âge en jours
    """

    # Champs dynamiques par type : (nom_champ, label, widget_type, [args])
    _DYNAMIC_FIELDS: dict[str, list[tuple[str, str, type, tuple]]] = {
        "recherche": [
            ("mots_cles", "Mots-clés", QLineEdit, ("Saisir les mots-clés…",)),
        ],
        "scan": [
            ("dossier", "Dossier", QLineEdit, ("Chemin du dossier…",)),
        ],
        "wishlist": [
            ("artiste", "Artiste", QLineEdit, ("Nom de l'artiste…",)),
            ("album", "Album", QLineEdit, ("Titre de l'album (optionnel)…",)),
        ],
        "optimisation": [
            (
                "profil",
                "Profil",
                QComboBox,
                (
                    "optimisation_rapide",
                    "optimisation_complete",
                    "reorganisation",
                ),
            ),
        ],
        "nettoyage": [
            ("age_jours", "Âge minimum (jours)", QSpinBox, (1, 365, 7)),
        ],
        "classement": [
            ("dossier", "Dossier source", QLineEdit, ("Chemin du dossier…",)),
            ("structure", "Structure", QLineEdit, ("{artist}/{album}/{track:02d} {title}.{ext}",)),
        ],
        "renommage": [
            ("dossier", "Dossier source", QLineEdit, ("Chemin du dossier…",)),
            ("template", "Template", QLineEdit, ("{artist} - {album} - {track:02d} {title}.{ext}",)),
        ],
        "deduplication": [
            ("dossier", "Dossier source", QLineEdit, ("Chemin du dossier…",)),
        ],
        "nettoyage_temp": [
            ("age_jours", "Âge minimum (jours)", QSpinBox, (1, 365, 7)),
        ],
    }

    def __init__(
        self,
        preset_type: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle("➕ Nouvelle action")
        self.setObjectName("actionModal")
        self.setModal(True)
        self.setMinimumWidth(480)

        # Résultat
        self._result_data: dict | None = None

        # Champs dynamiques (références)
        self._dynamic_widgets: dict[str, QWidget] = {}
        self._dynamic_container: QWidget | None = None

        self._build_ui()

        if preset_type:
            idx = self._type_cb.findData(preset_type)
            if idx >= 0:
                self._type_cb.setCurrentIndex(idx)

        self._on_type_changed(self._type_cb.currentData() or "")
        self._on_mode_changed(self._mode_cb.currentData() or "")

    # ── Construction UI ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # ── Titre ──
        title = QLabel("Créer une nouvelle action")
        title.setStyleSheet(f"color: {COLORS['ACCENT']}; font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        # ── Formulaire ──
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)
        form.setContentsMargins(0, 0, 0, 0)

        # Type d'action
        self._type_cb = QComboBox()
        for t in ACTION_TYPES:
            icon = _ACTION_ICONS.get(t, "❓")
            label = _ACTION_LABELS.get(t, t)
            self._type_cb.addItem(f"{icon}  {label}", t)
        self._type_cb.currentIndexChanged.connect(lambda: self._on_type_changed(self._type_cb.currentData() or ""))
        self._style_combo(self._type_cb)
        self._type_cb.setMinimumWidth(220)
        form.addRow("Type :", self._type_cb)

        # Mode (immédiat / planifié)
        self._mode_cb = QComboBox()
        self._mode_cb.addItem("⚡  Immédiat", "immediat")
        self._mode_cb.addItem("📅  Planifié", "planifie")
        self._mode_cb.currentIndexChanged.connect(lambda: self._on_mode_changed(self._mode_cb.currentData() or ""))
        self._style_combo(self._mode_cb)
        self._mode_cb.setMinimumWidth(200)
        form.addRow("Mode :", self._mode_cb)

        # Date / heure planifiée (visible seulement en mode planifié)
        self._date_row = QWidget()
        date_row_layout = QHBoxLayout(self._date_row)
        date_row_layout.setContentsMargins(0, 0, 0, 0)
        date_row_layout.setSpacing(8)

        self._date_picker = QDateTimeEdit()
        now = QDate.currentDate()
        self._date_picker.setCalendarPopup(True)
        self._date_picker.setDisplayFormat("yyyy-MM-dd HH:mm")
        self._date_picker.setMinimumDate(now)
        self._date_picker.setDate(now.addDays(1))
        self._date_picker.setMinimumWidth(200)
        date_row_layout.addWidget(self._date_picker)
        date_row_layout.addStretch()
        form.addRow("Date :", self._date_row)

        # ── Champs dynamiques ──
        self._dynamic_container = QWidget()
        self._dynamic_layout = QFormLayout(self._dynamic_container)
        self._dynamic_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._dynamic_layout.setSpacing(10)
        self._dynamic_layout.setContentsMargins(0, 0, 0, 0)
        form.addRow(self._dynamic_container)

        # ── Champs communs ──
        # Nom (optionnel)
        self._nom_edit = QLineEdit()
        self._nom_edit.setPlaceholderText("Laisser vide pour un nom automatique")
        self._nom_edit.setStyleSheet(
            f"QLineEdit {{"
            f"  background: {COLORS['BG_INPUT']};"
            f"  color: {COLORS['TEXT_PRIMARY']};"
            f"  border: 1px solid {COLORS['BORDER']};"
            f"  border-radius: 6px;"
            f"  padding: 6px 10px;"
            f"  font-size: 12px;"
            f"}}"
            f"QLineEdit:focus {{"
            f"  border-color: {COLORS['ACCENT']};"
            f"}}"
        )
        form.addRow("Nom :", self._nom_edit)

        # Description (optionnelle)
        self._desc_edit = QLineEdit()
        self._desc_edit.setPlaceholderText("Description optionnelle…")
        self._desc_edit.setStyleSheet(self._nom_edit.styleSheet())
        form.addRow("Description :", self._desc_edit)

        layout.addLayout(form)
        layout.addStretch()

        # ── Boutons ──
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)

        # Style des boutons
        save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
        save_btn.setText("💾  Créer l'action")
        save_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {COLORS['ACCENT']};"
            f"  color: {COLORS['TEXT_WHITE']};"
            f"  border: none; border-radius: 8px;"
            f"  padding: 8px 20px;"
            f"  font-size: 13px; font-weight: 700;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {COLORS['ACCENT_HOVER']};"
            f"}}"
        )
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setText("Annuler")
        cancel_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {COLORS['BG_BTN']};"
            f"  color: {COLORS['TEXT_MUTED']};"
            f"  border: 1px solid {COLORS['BORDER']};"
            f"  border-radius: 8px;"
            f"  padding: 8px 20px;"
            f"  font-size: 12px; font-weight: 600;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {COLORS['BG_HOVER']};"
            f"  color: {COLORS['TEXT_PRIMARY']};"
            f"}}"
        )

        layout.addWidget(buttons)

        # ── Style global ──
        self.setStyleSheet(
            f"#actionModal {{  background: {COLORS['BG_SURFACE']};  border: 1px solid {COLORS['BORDER']};}}"
        )

    def _style_combo(self, combo: QComboBox) -> None:
        """Même style de QComboBox que dans BotPlanificateur."""
        combo.setStyleSheet(
            f"QComboBox {{"
            f"  background: {COLORS['BG_INPUT']};"
            f"  color: {COLORS['TEXT_PRIMARY']};"
            f"  border: 1px solid {COLORS['BORDER']};"
            f"  border-radius: 6px;"
            f"  padding: 6px 10px;"
            f"  font-size: 12px;"
            f"}}"
            f"QComboBox:hover {{"
            f"  border-color: {COLORS['BORDER_HOVER']};"
            f"}}"
            f"QComboBox::drop-down {{"
            f"  border: none;"
            f"  width: 20px;"
            f"}}"
            f"QComboBox QAbstractItemView {{"
            f"  background: {COLORS['BG_SURFACE']};"
            f"  color: {COLORS['TEXT_PRIMARY']};"
            f"  border: 1px solid {COLORS['BORDER']};"
            f"  selection-background-color: {COLORS['BG_HOVER']};"
            f"  outline: none;"
            f"}}"
        )

    # ── Champs dynamiques ─────────────────────────────────────────────────

    def _on_type_changed(self, action_type: str) -> None:
        """Met à jour les champs dynamiques selon le type d'action."""
        # Vider l'ancien contenu
        while self._dynamic_layout.count() > 0:
            item = self._dynamic_layout.takeAt(0)
            # pyrefly: ignore [missing-attribute]
            if item.widget():
                # pyrefly: ignore [missing-attribute]
                item.widget().deleteLater()
            # pyrefly: ignore [missing-attribute]
            elif item.layout():
                # pyrefly: ignore [missing-attribute]
                self._clear_layout(item.layout())

        self._dynamic_widgets.clear()

        # Pas de type sélectionné
        if not action_type:
            return

        # Ajouter les champs pour ce type
        fields = self._DYNAMIC_FIELDS.get(action_type, [])
        for field_name, label, widget_cls, args in fields:
            widget: QWidget
            if widget_cls is QSpinBox:
                widget = QSpinBox()
                assert len(args) >= 3
                widget.setRange(args[0], args[1])  # type: ignore[arg-type]
                widget.setValue(args[2])  # type: ignore[arg-type]
                widget.setFixedWidth(100)
                widget.setStyleSheet(
                    f"QSpinBox {{"
                    f"  background: {COLORS['BG_INPUT']};"
                    f"  color: {COLORS['TEXT_PRIMARY']};"
                    f"  border: 1px solid {COLORS['BORDER']};"
                    f"  border-radius: 6px;"
                    f"  padding: 4px 8px;"
                    f"  font-size: 12px;"
                    f"}}"
                    f"QSpinBox:focus {{"
                    f"  border-color: {COLORS['ACCENT']};"
                    f"}}"
                )
            elif widget_cls is QComboBox:
                widget = QComboBox()
                for opt in args:
                    label_map = {
                        "optimisation_rapide": "Optimisation rapide",
                        "optimisation_complete": "Optimisation complète",
                        "reorganisation": "Réorganisation",
                    }
                    display = label_map.get(opt, opt.replace("_", " ").title())
                    widget.addItem(display, opt)
                widget.setMinimumWidth(200)
                self._style_combo(widget)
            else:
                # QLineEdit par défaut
                widget = QLineEdit()
                placeholder = args[0] if args else ""
                widget.setPlaceholderText(str(placeholder))
                widget.setStyleSheet(
                    f"QLineEdit {{"
                    f"  background: {COLORS['BG_INPUT']};"
                    f"  color: {COLORS['TEXT_PRIMARY']};"
                    f"  border: 1px solid {COLORS['BORDER']};"
                    f"  border-radius: 6px;"
                    f"  padding: 6px 10px;"
                    f"  font-size: 12px;"
                    f"}}"
                    f"QLineEdit:focus {{"
                    f"  border-color: {COLORS['ACCENT']};"
                    f"}}"
                )

            self._dynamic_widgets[field_name] = widget
            self._dynamic_layout.addRow(f"{label} :", widget)

    def _on_mode_changed(self, mode: str) -> None:
        """Affiche ou masque le sélecteur de date selon le mode."""
        self._date_row.setVisible(mode == "planifie")

    def _clear_layout(self, layout) -> None:
        """Supprime récursivement tous les widgets d'un layout."""
        while layout.count() > 0:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    # ── Validation & Sauvegarde ───────────────────────────────────────────

    def _on_save(self) -> None:
        """Valide les champs et accepte le dialogue."""
        action_type = self._type_cb.currentData() or ""
        if not action_type:
            return

        # Valider les champs dynamiques
        parametres: dict = {}
        for field_name, widget in self._dynamic_widgets.items():
            value: object
            if isinstance(widget, QLineEdit):
                value = widget.text().strip()
                if not value:
                    widget.setFocus()
                    widget.setStyleSheet(widget.styleSheet() + f"QLineEdit {{ border-color: {COLORS['DANGER']}; }}")
                    return
            elif isinstance(widget, QSpinBox):
                value = widget.value()
            elif isinstance(widget, QComboBox):
                value = widget.currentData()
            else:
                value = None
            parametres[field_name] = value

        mode = self._mode_cb.currentData() or "immediat"
        QDate.currentDate()

        self._result_data = {
            "type": action_type,
            "mode": mode,
            "parametres": parametres,
            "nom": self._nom_edit.text().strip() or None,
            "description": self._desc_edit.text().strip() or None,
            "prochaine_execution": (
                self._date_picker.dateTime().toString("yyyy-MM-dd HH:mm:ss") if mode == "planifie" else None
            ),
        }

        self.accept()

    @property
    def result_data(self) -> dict | None:
        """Données de l'action créée, ou None si annulé."""
        return self._result_data


# ═══════════════════════════════════════════════════════════════════════════════
# BotPlanificateur
# ═══════════════════════════════════════════════════════════════════════════════


class BotPlanificateur(QFrame):
    """Panneau de gestion des actions planifiées."""

    page_changed = Signal(str)  # navigation vers un autre bot
    unseen_count_changed = Signal(int)  # badge compteur (actions en attente)

    # ── Interrupteur ─────────────────────────────────────────────

    def demarrer(self) -> None:
        """Active l'interrupteur → démarre la boucle du planificateur.

        Lance un QTimer périodique pour vérifier et exécuter
        les actions planifiées.
        """
        if self._actif:
            return
        self._actif = True
        if self._loop_timer is None:
            self._loop_timer = QTimer(self)
            self._loop_timer.setInterval(self._loop_interval_ms)
            self._loop_timer.timeout.connect(self._on_loop_tick)
        self._loop_timer.start()
        logger.info("BotPlanificateur démarré")

    def arreter(self) -> None:
        """Désactive l'interrupteur → suspend la boucle du planificateur."""
        if not self._actif:
            return
        self._actif = False
        if self._loop_timer is not None:
            self._loop_timer.stop()
        logger.info("BotPlanificateur arrêté")

    @property
    def est_actif(self) -> bool:
        return self._actif

    def set_loop_interval(self, ms: int) -> None:
        """Configure l'intervalle de la boucle périodique."""
        self._loop_interval_ms = ms
        if self._loop_timer is not None:
            self._loop_timer.setInterval(ms)

    def _on_loop_tick(self) -> None:
        """Callback du timer — vérifie et exécute les actions planifiées."""
        logger.debug("BotPlanificateur: cycle de vérification")
        if hasattr(self, "_svc"):
            self._refresh_stats()
            self._refresh_list()

    def __init__(
        self,
        center_zone: QWidget | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._center_zone = center_zone
        self._unseen_count = 0
        self._stat_labels: dict[str, QLabel] = {}
        self._filter_statut = ""
        self._filter_type = ""
        self._filter_recherche = ""

        # Boucle périodique (interrupteur)
        self._actif = False
        self._loop_timer: QTimer | None = None
        self._loop_interval_ms = 60_000  # 1 minute par défaut

        self.setObjectName("botPlanificateur")
        # pyrefly: ignore [missing-attribute]
        self.setFrameShape(QFrame.NoFrame)

        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── Titre ──
        title = QLabel("🤖 Planificateur")
        title.setStyleSheet(f"color: {COLORS['ACCENT']}; font-size: 20px; font-weight: 700;")
        layout.addWidget(title)

        # ── Toolbar ──
        layout.addLayout(self._build_toolbar())

        # ── Actions rapides ──
        layout.addLayout(self._build_action_bar())

        # ── Stats ──
        layout.addLayout(self._build_stats_bar())

        # ── Filtres ──
        layout.addLayout(self._build_filter_bar())

        # ── Liste des actions ──
        self._build_action_list()
        layout.addWidget(self._table, stretch=1)

        # ── Connexion au service ──
        self._init_service()

    # ── Initialisation service ─────────────────────────────────────────────

    def _init_service(self) -> None:
        """Récupère le singleton PlanificateurService et connecte les signaux."""
        self._svc = PlanificateurService()
        self._svc.action_changed.connect(self._on_action_changed)
        self._pause_btn.setChecked(self._svc.paused)
        self._refresh_stats()
        self._refresh_list()

    # ── Builders UI ────────────────────────────────────────────────────────

    def _build_toolbar(self) -> QHBoxLayout:
        """Barre d'outils principale : rafraîchir, nouvelle action, pause."""
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self._refresh_btn = QPushButton("🔄 Rafraîchir")
        self._refresh_btn.setObjectName("toolbarBtn")
        self._style_tool_btn(self._refresh_btn)
        self._refresh_btn.clicked.connect(self._refresh_all)
        toolbar.addWidget(self._refresh_btn)

        self._new_action_btn = QPushButton("➕ Nouvelle action")
        self._new_action_btn.setObjectName("toolbarBtn")
        self._style_tool_btn(self._new_action_btn, accent=True)
        self._new_action_btn.clicked.connect(self._on_new_action)
        toolbar.addWidget(self._new_action_btn)

        toolbar.addStretch()

        self._pause_btn = QPushButton("⏸ Pause")
        self._pause_btn.setObjectName("pauseBtn")
        self._pause_btn.setCheckable(True)
        self._style_pause_btn(checked=False)
        self._pause_btn.toggled.connect(self._on_pause_toggled)
        toolbar.addWidget(self._pause_btn)

        return toolbar

    def _build_action_bar(self) -> QHBoxLayout:
        """Barre d'insertion rapide : 5 boutons par type d'action."""
        bar = QHBoxLayout()
        bar.setSpacing(6)

        for action_type in ACTION_TYPES:
            icon = _ACTION_ICONS.get(action_type, "❓")
            label = _ACTION_LABELS.get(action_type, action_type)
            btn = QPushButton(f"{icon} {label}")
            btn.setObjectName("actionBarBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(36)
            btn.clicked.connect(  # type: ignore[arg-type]
                lambda checked=False, t=action_type: self._on_quick_action(t)
            )
            self._style_action_btn(btn)
            bar.addWidget(btn)

        bar.addStretch()
        return bar

    def _build_stats_bar(self) -> QHBoxLayout:
        """Barre des 4 cartes de statistiques live."""
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(8)

        for label, color_key, statut in _STAT_CARDS:
            card, value_label = self._make_stat_card(label, color_key)
            self._stat_labels[statut] = value_label
            stats_layout.addWidget(card)

        stats_layout.addStretch()
        return stats_layout

    def _build_filter_bar(self) -> QHBoxLayout:
        """Barre de filtres : statut, type, recherche texte."""
        bar = QHBoxLayout()
        bar.setSpacing(8)

        # Filtre statut
        self._filter_statut_cb = QComboBox()
        self._filter_statut_cb.addItem("📊 Tous les statuts", "")
        for s in ACTION_STATUTS:
            self._filter_statut_cb.addItem(_STATUT_LABELS.get(s, s), s)
        self._filter_statut_cb.currentIndexChanged.connect(self._on_filter_changed)
        self._style_combo(self._filter_statut_cb)
        bar.addWidget(self._filter_statut_cb)

        # Filtre type
        self._filter_type_cb = QComboBox()
        self._filter_type_cb.addItem("📋 Tous les types", "")
        for t in ACTION_TYPES:
            self._filter_type_cb.addItem(f"{_ACTION_ICONS.get(t, '')} {_ACTION_LABELS.get(t, t)}", t)
        self._filter_type_cb.currentIndexChanged.connect(self._on_filter_changed)
        self._style_combo(self._filter_type_cb)
        bar.addWidget(self._filter_type_cb)

        # Recherche texte
        self._filter_search = QLineEdit()
        self._filter_search.setPlaceholderText("🔍 Rechercher par paramètres…")
        self._filter_search.setClearButtonEnabled(True)
        self._style_search(self._filter_search)
        bar.addWidget(self._filter_search, stretch=1)

        # Debounce timer pour la recherche
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._apply_search_filter)
        self._filter_search.textChanged.connect(self._on_search_debounce)

        return bar

    def _build_action_list(self) -> None:
        """Construit le tableau des actions."""
        self._table = QTableWidget()
        self._table.setObjectName("actionTable")
        self._table.setColumnCount(len(_COL_HEADERS))
        self._table.setHorizontalHeaderLabels(_COL_HEADERS)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Config des colonnes
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(_COL_TYPE, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(_COL_MODE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(_COL_STATUT, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(_COL_DATE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(_COL_ACTIONS, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(_COL_ACTIONS, 160)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Styles
        self._table.setStyleSheet(
            f"QTableWidget {{"
            f"  background: {COLORS['BG_SURFACE']};"
            f"  color: {COLORS['TEXT_PRIMARY']};"
            f"  border: 1px solid {COLORS['BORDER']};"
            f"  border-radius: 6px;"
            f"  font-size: 12px;"
            f"  outline: none;"
            f"}}"
            f"QTableWidget::item {{"
            f"  padding: 6px 10px;"
            f"}}"
            f"QTableWidget::item:selected {{"
            f"  background: {COLORS['BG_HOVER']};"
            f"  color: {COLORS['TEXT_PRIMARY']};"
            f"}}"
            f"QHeaderView::section {{"
            f"  background: {COLORS['BG_TABLE_HEADER']};"
            f"  color: {COLORS['TEXT_MUTED']};"
            f"  border: none;"
            f"  border-bottom: 1px solid {COLORS['BORDER']};"
            f"  padding: 8px 10px;"
            f"  font-size: 11px;"
            f"  font-weight: 600;"
            f"}}"
        )

    # ── Helpers UI ─────────────────────────────────────────────────────────

    def _make_stat_card(self, label: str, color_key: str) -> tuple[QFrame, QLabel]:
        """Crée une carte de statistique compacte avec valeur dynamique."""
        color = COLORS.get(color_key, COLORS["ACCENT"])
        bg = rgba(color, "20")

        card = QFrame()
        card.setObjectName("statCard")
        card.setStyleSheet(f"#statCard {{  background: {bg};  border-radius: 8px;  padding: 8px 12px;}}")
        card.setFixedHeight(60)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(2)

        value = QLabel("—")
        value.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: 700;")
        value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(value)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {COLORS['TEXT_SECONDARY']}; font-size: 10px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)

        return card, value

    def _style_tool_btn(self, btn: QPushButton, accent: bool = False) -> None:
        """Applique le style d'un bouton de toolbar."""
        if accent:
            bg = COLORS["ACCENT"]
            color = COLORS["TEXT_WHITE"]
            hover = COLORS["ACCENT_HOVER"]
        else:
            bg = COLORS["BG_BTN"]
            color = COLORS["TEXT_MUTED"]
            hover = COLORS["BG_HOVER"]
        btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {bg}; color: {color};"
            f"  border: none; border-radius: 6px;"
            f"  padding: 6px 14px; font-size: 12px; font-weight: 600;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {hover};"
            f"}}"
        )
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

    def _style_action_btn(self, btn: QPushButton) -> None:
        """Style des boutons de la barre d'actions rapides."""
        btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {COLORS['BG_BTN']};"
            f"  color: {COLORS['TEXT_SECONDARY']};"
            f"  border: 1px solid {COLORS['BORDER']};"
            f"  border-radius: 8px;"
            f"  padding: 6px 16px;"
            f"  font-size: 12px; font-weight: 600;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {COLORS['BG_HOVER']};"
            f"  color: {COLORS['TEXT_PRIMARY']};"
            f"  border-color: {COLORS['BORDER_HOVER']};"
            f"}}"
            f"QPushButton:pressed {{"
            f"  background: {COLORS['BG_PRESSED']};"
            f"}}"
        )

    def _style_pause_btn(self, checked: bool) -> None:
        """Met à jour le style du bouton Pause selon l'état."""
        if checked:
            bg = rgba(COLORS["DANGER"], "30")
            color = COLORS["DANGER"]
            hover = rgba(COLORS["DANGER"], "50")
        else:
            bg = COLORS["BG_BTN"]
            color = COLORS["TEXT_MUTED"]
            hover = COLORS["BG_HOVER"]
        self._pause_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {bg}; color: {color};"
            f"  border: 1px solid {COLORS['BORDER']};"
            f"  border-radius: 6px;"
            f"  padding: 6px 14px; font-size: 12px; font-weight: 600;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {hover};"
            f"}}"
        )

    def _style_combo(self, combo: QComboBox) -> None:
        """Style unifié pour les QComboBox de filtres."""
        combo.setStyleSheet(
            f"QComboBox {{"
            f"  background: {COLORS['BG_INPUT']};"
            f"  color: {COLORS['TEXT_PRIMARY']};"
            f"  border: 1px solid {COLORS['BORDER']};"
            f"  border-radius: 6px;"
            f"  padding: 4px 10px;"
            f"  font-size: 12px;"
            f"  min-width: 130px;"
            f"}}"
            f"QComboBox:hover {{"
            f"  border-color: {COLORS['BORDER_HOVER']};"
            f"}}"
            f"QComboBox::drop-down {{"
            f"  border: none;"
            f"  width: 20px;"
            f"}}"
            f"QComboBox QAbstractItemView {{"
            f"  background: {COLORS['BG_SURFACE']};"
            f"  color: {COLORS['TEXT_PRIMARY']};"
            f"  border: 1px solid {COLORS['BORDER']};"
            f"  selection-background-color: {COLORS['BG_HOVER']};"
            f"  outline: none;"
            f"}}"
        )

    def _style_search(self, field: QLineEdit) -> None:
        """Style pour le champ de recherche."""
        field.setStyleSheet(
            f"QLineEdit {{"
            f"  background: {COLORS['BG_INPUT']};"
            f"  color: {COLORS['TEXT_PRIMARY']};"
            f"  border: 1px solid {COLORS['BORDER']};"
            f"  border-radius: 6px;"
            f"  padding: 4px 10px;"
            f"  font-size: 12px;"
            f"}}"
            f"QLineEdit:hover {{"
            f"  border-color: {COLORS['BORDER_HOVER']};"
            f"}}"
            f"QLineEdit:focus {{"
            f"  border-color: {COLORS['ACCENT']};"
            f"}}"
        )

    def _make_row_btn(self, text: str, color: str, hover_color: str | None = None) -> QPushButton:
        """Crée un petit bouton d'action pour une ligne du tableau."""
        btn = QPushButton(text)
        btn.setFixedSize(32, 24)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        hover = hover_color or rgba(color, "40")
        btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent;"
            f"  color: {color};"
            f"  border: 1px solid {rgba(color, '44')};"
            f"  border-radius: 4px;"
            f"  font-size: 11px;"
            f"  padding: 2px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {hover};"
            f"}}"
        )
        return btn

    # ── Handlers ───────────────────────────────────────────────────────────

    def _on_action_changed(self, action_id: int, type_: str, statut: str) -> None:
        """Réagit à un changement de statut d'action. (slot)"""
        self._refresh_stats()
        self._refresh_list()

        # Navigation inter-bots quand une action démarre (clic ▶ ou auto)
        if statut == "en_cours":
            target = _BOT_NAVIGATION.get(type_)
            if target:
                self.page_changed.emit(target)

    def _on_pause_toggled(self, checked: bool) -> None:
        """Bascule la pause globale du service."""
        self._style_pause_btn(checked)
        if checked:
            self._svc.pause()
            self._pause_btn.setText("▶ Pause")
        else:
            self._svc.resume()
            self._pause_btn.setText("⏸ Pause")

    def _on_new_action(self) -> None:
        """Ouvre le modal de création d'une nouvelle action vide."""
        modal = ActionModal(parent=self)
        if modal.exec():
            data = modal.result_data
            if data:
                self._svc.create_action(
                    type_=data["type"],
                    mode=data["mode"],
                    parametres=data["parametres"],
                    nom=data["nom"],
                    description=data["description"],
                    prochaine_execution=data["prochaine_execution"],
                )
                self._refresh_all()

    def _on_quick_action(self, action_type: str) -> None:
        """Clic sur un bouton d'action rapide — ouvre le modal pré-rempli.

        Le type d'action est présélectionné et le mode par défaut est 'immediat'.
        """
        modal = ActionModal(preset_type=action_type, parent=self)
        if modal.exec():
            data = modal.result_data
            if data:
                self._svc.create_action(
                    type_=data["type"],
                    mode=data["mode"],
                    parametres=data["parametres"],
                    nom=data["nom"],
                    description=data["description"],
                    prochaine_execution=data["prochaine_execution"],
                )
                self._refresh_all()

    def _on_filter_changed(self) -> None:
        """Un filtre (statut ou type) a changé → rafraîchir la liste."""
        self._filter_statut = self._filter_statut_cb.currentData() or ""
        self._filter_type = self._filter_type_cb.currentData() or ""
        self._refresh_list()

    def _on_search_debounce(self, text: str) -> None:
        """Lance le timer de debounce pour la recherche."""
        self._filter_recherche = text
        self._search_timer.start()

    def _apply_search_filter(self) -> None:
        """Applique le filtre texte après le debounce."""
        self._refresh_list()

    def _on_executer_action(self, action_id: int) -> None:
        """Exécute manuellement une action."""
        self._svc.execute_manual(action_id)
        self._refresh_list()

    def _on_pause_action(self, action_id: int) -> None:
        """Bascule le statut pause d'une action individuelle."""
        action = self._svc.get_action(action_id)
        if action is None:
            return
        if action["statut"] == "pause":
            nouveau = "en_attente" if action["mode"] == "immediat" else "planifiee"
            self._svc.update_action(action_id, statut=nouveau)
        elif action["statut"] in ("en_attente", "planifiee"):
            self._svc.update_action(action_id, statut="pause")

    def _on_supprimer_action(self, action_id: int) -> None:
        """Supprime une action."""
        self._svc.delete_action(action_id)
        self._refresh_all()

    # ── Rafraîchissement ──────────────────────────────────────────────────

    def _refresh_all(self) -> None:
        """Rafraîchit tout (stats + liste)."""
        self._refresh_stats()
        self._refresh_list()

    def _refresh_stats(self) -> None:
        """Rafraîchit les statistiques depuis le service."""
        stats = self._svc.get_stats()

        for statut, label in self._stat_labels.items():
            count = stats.get(statut, 0)
            label.setText(str(count))

        unseen = stats.get("en_attente", 0) + stats.get("planifiee", 0)
        if unseen != self._unseen_count:
            self._unseen_count = unseen
            self.unseen_count_changed.emit(unseen)

    def _refresh_list(self) -> None:
        """Rafraîchit le contenu du tableau depuis le service."""
        actions = self._svc.list_actions(
            statut=self._filter_statut or None,
            type_=self._filter_type or None,
            limite=200,
        )

        # Filtrer par recherche texte (dans les paramètres JSON)
        if self._filter_recherche:
            lowered = self._filter_recherche.lower()
            actions = [
                a
                for a in actions
                if lowered in str(a.get("parametres", {})).lower() or lowered in str(a.get("id", "")).lower()
            ]

        self._table.setRowCount(len(actions))

        for row, action in enumerate(actions):
            action_id = action["id"]
            type_ = action["type"]
            mode = action["mode"]
            statut = action["statut"]

            # ── Colonne Type ──
            icon = _ACTION_ICONS.get(type_, "❓")
            label = _ACTION_LABELS.get(type_, type_)
            type_item = QTableWidgetItem(f"{icon}  {label}")
            type_item.setData(Qt.ItemDataRole.UserRole, action_id)
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, _COL_TYPE, type_item)

            # ── Colonne Mode ──
            mode_text = _MODE_LABELS.get(mode, mode)
            mode_item = QTableWidgetItem(mode_text)
            mode_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            mode_item.setFlags(mode_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, _COL_MODE, mode_item)

            # ── Colonne Statut ──
            statut_text = _STATUT_LABELS.get(statut, statut)
            statut_color = _STATUT_COLORS.get(statut, COLORS["TEXT_MUTED"])
            statut_item = QTableWidgetItem(f"  {statut_text}")
            statut_item.setForeground(QColor(statut_color))
            statut_item.setFlags(statut_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, _COL_STATUT, statut_item)

            # ── Colonne Date ──
            date_str = action.get("date_creation", "") or ""
            if date_str:
                # Tronquer l'heure pour lisibilité
                date_str = date_str[:16]  # "YYYY-MM-DD HH:MM"
            date_item = QTableWidgetItem(date_str)
            date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            date_item.setForeground(QColor(COLORS["TEXT_SECONDARY"]))
            self._table.setItem(row, _COL_DATE, date_item)

            # ── Colonne Actions ──
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 0, 4, 0)
            actions_layout.setSpacing(4)

            if statut in ("en_attente", "planifiee", "pause"):
                # Bouton Exécuter
                if statut != "pause":
                    exec_btn = self._make_row_btn("▶", COLORS["SUCCESS"])
                    exec_btn.clicked.connect(  # type: ignore[arg-type]
                        lambda checked=False, aid=action_id: self._on_executer_action(aid)
                    )
                    actions_layout.addWidget(exec_btn)

                # Bouton Pause/Restart
                if statut == "pause":
                    pause_btn = self._make_row_btn("▶", COLORS["WARNING"])
                    pause_btn.setToolTip("Reprendre")
                else:
                    pause_btn = self._make_row_btn("⏸", COLORS["WARNING"])
                    pause_btn.setToolTip("Mettre en pause")
                pause_btn.clicked.connect(  # type: ignore[arg-type]
                    lambda checked=False, aid=action_id: self._on_pause_action(aid)
                )
                actions_layout.addWidget(pause_btn)

            # Bouton Supprimer (toujours visible)
            del_btn = self._make_row_btn("✕", COLORS["DANGER"])
            del_btn.setToolTip("Supprimer")
            del_btn.clicked.connect(  # type: ignore[arg-type]
                lambda checked=False, aid=action_id: self._on_supprimer_action(aid)
            )
            actions_layout.addWidget(del_btn)

            self._table.setCellWidget(row, _COL_ACTIONS, actions_widget)

            # Hauteur de ligne adaptée
            self._table.setRowHeight(row, 36)

    # ── API publique ──────────────────────────────────────────────────────

    def reset_unseen_count(self) -> None:
        """Réinitialise le compteur d'actions non vues (appelé par la navigation)."""
        self._unseen_count = 0
        self.unseen_count_changed.emit(0)
