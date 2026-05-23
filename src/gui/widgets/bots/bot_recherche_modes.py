"""
Panneau des modes de recherche pour Athéna (BotRecherche).

Contient les 4 boutons de mode (Normal, Club, Label, Artiste)
et la zone de configuration qui s'adapte au mode sélectionné.

``ModesPanel`` émet des signaux vers la page Athéna qui conserve
le tableau et la logique de recherche.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.utils.log_action import log_action

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.gui.theme_fragments.colors import COLORS

if TYPE_CHECKING:
    from src.services.clients_actifs_service import ClientInfo

logger = logging.getLogger("[RECHERCHE-MODES]")

# ── Styles communs ────────────────────────────────────────────

_MODE_BTN_COMMON = f"""
    QPushButton {{
        background: transparent;
        color: {COLORS["TEXT_SECONDARY"]};
        border: 1px solid {COLORS["BORDER"]};
        border-radius: 8px;
        padding: 6px 16px;
        font-size: 12px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        border-color: {COLORS["PRIMARY"]};
        color: {COLORS["PRIMARY"]};
    }}
"""

_MODE_BTN_ACTIF = f"""
    QPushButton {{
        background: rgba({COLORS["PRIMARY"]}, '20');
        color: {COLORS["PRIMARY"]};
        border: 1px solid {COLORS["PRIMARY"]};
        border-radius: 8px;
        padding: 6px 16px;
        font-size: 12px;
        font-weight: 700;
    }}
"""


# ═══════════════════════════════════════════════════════════════
#  StatusConsole — console d'information continue
# ═══════════════════════════════════════════════════════════════


class StatusConsole(QFrame):
    """Console d'information multi-lignes avec timestamps.

    Affiche un flux continu de messages de statut colorés
    (info/succès/avertissement/erreur) pour informer l'utilisateur
    de l'état du système en temps réel.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statusConsole")
        self._max_lines = 100
        self._line_count = 0

        self.setStyleSheet(
            f"""
            #statusConsole {{
                background: rgba(COLORS['BG_SURFACE'], '80');
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        self._text = QTextEdit()
        self._text.setObjectName("consoleText")
        self._text.setReadOnly(True)
        self._text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._text.setFrameShape(QFrame.Shape.NoFrame)
        self._text.setStyleSheet(
            f"""
            #consoleText {{
                background: transparent;
                color: {COLORS["TEXT_SECONDARY"]};
                border: none;
                font-size: 11px;
                font-family: 'Consolas', 'Courier New', monospace;
                line-height: 1.4;
            }}
            #consoleText:focus {{
                border: none;
                outline: none;
            }}
            """
        )
        self._text.setMinimumHeight(60)
        self._text.setMaximumHeight(160)

        layout.addWidget(self._text)

        # ── Barre d'outils : Copier / Enregistrer ──
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 2, 0, 0)
        toolbar.setSpacing(4)

        self._btn_copier = QPushButton("📋 Copier")
        self._btn_copier.setObjectName("consoleCopyBtn")
        self._btn_copier.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_copier.setToolTip("Copier les logs dans le presse-papier")
        self._btn_copier.setStyleSheet(
            f"""
            #consoleCopyBtn {{
                background: transparent;
                color: {COLORS["TEXT_SECONDARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 4px;
                padding: 2px 10px;
                font-size: 10px;
                font-weight: 600;
            }}
            #consoleCopyBtn:hover {{
                border-color: {COLORS["ACCENT"]};
                color: {COLORS["ACCENT"]};
            }}
            """
        )
        self._btn_copier.clicked.connect(self._copier_logs)
        toolbar.addWidget(self._btn_copier)

        self._btn_enregistrer = QPushButton("💾 Enregistrer")
        self._btn_enregistrer.setObjectName("consoleSaveBtn")
        self._btn_enregistrer.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_enregistrer.setToolTip("Sauvegarder les logs dans un fichier texte")
        self._btn_enregistrer.setStyleSheet(
            f"""
            #consoleSaveBtn {{
                background: transparent;
                color: {COLORS["TEXT_SECONDARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 4px;
                padding: 2px 10px;
                font-size: 10px;
                font-weight: 600;
            }}
            #consoleSaveBtn:hover {{
                border-color: {COLORS["SUCCESS"]};
                color: {COLORS["SUCCESS"]};
            }}
            """
        )
        self._btn_enregistrer.clicked.connect(self._enregistrer_logs)
        toolbar.addWidget(self._btn_enregistrer)

        toolbar.addStretch(1)
        layout.addLayout(toolbar)

    # ── API publique ────────────────────────────────────────────

    def push_info(self, message: str) -> None:
        """Ajoute un message d'information (gris)."""
        self._push(message, COLORS["TEXT_SECONDARY"])

    def push_success(self, message: str) -> None:
        """Ajoute un message de succès (vert)."""
        self._push(message, COLORS["SUCCESS"])

    def push_warning(self, message: str) -> None:
        """Ajoute un avertissement (jaune)."""
        self._push(message, COLORS["WARNING"])

    def push_error(self, message: str) -> None:
        """Ajoute une erreur (rouge)."""
        self._push(message, COLORS["DANGER"])

    def push_muted(self, message: str) -> None:
        """Ajoute un message discret (gris clair)."""
        self._push(message, COLORS["TEXT_MUTED"])

    def clear(self) -> None:
        """Vide la console."""
        self._text.clear()
        self._line_count = 0

    @property
    def plain_text(self) -> str:
        """Retourne le contenu texte brut (sans HTML) de la console."""
        return self._text.toPlainText()

    # ── Copier / Enregistrer ────────────────────────────────────

    @log_action("Copier les logs de suivi")
    def _copier_logs(self) -> None:
        """Copie tout le contenu de la console dans le presse-papier."""
        text = self.plain_text
        if not text:
            return
        QApplication.clipboard().setText(text)
        # Feedback visuel temporaire
        self._btn_copier.setText("✅ Copié !")
        QTimer.singleShot(2000, lambda: self._btn_copier.setText("📋 Copier"))

    @log_action("Enregistrer les logs de suivi")
    def _enregistrer_logs(self) -> None:
        """Enregistre le contenu de la console dans un fichier texte.

        Sauvegarde directement dans ``data/logs/boucle-de-recherche/``
        avec un horodatage — pas de dialogue.
        """
        text = self.plain_text
        if not text:
            return

        # Dossier de destination
        dest = Path("data/logs/boucle-de-recherche")
        try:
            dest.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.push_error(f"❌ Impossible de créer le dossier {dest} : {e}")
            return

        # Nom de fichier avec timestamp
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = dest / f"logs_athena_{ts}.txt"

        try:
            filepath.write_text(text, encoding="utf-8")
            self.push_success(f"💾 Logs enregistrés : {filepath}")
        except Exception as e:
            self.push_error(f"❌ Erreur lors de l'enregistrement : {e}")

    # ── Interne ─────────────────────────────────────────────────

    def _push(self, message: str, color: str) -> None:
        """Ajoute une ligne colorée avec timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        html = f'<span style="color:{COLORS["TEXT_MUTED"]};">[{timestamp}]</span> <span style="color:{color};">{message}</span>'

        cursor = self._text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        if self._line_count > 0:
            cursor.insertHtml("<br>")

        cursor.insertHtml(html)
        self._text.setTextCursor(cursor)
        self._text.ensureCursorVisible()

        self._line_count += 1
        self._prune()

    def _prune(self) -> None:
        """Supprime les lignes les plus anciennes si le seuil est dépassé."""
        if self._line_count <= self._max_lines:
            return

        doc = self._text.document()
        block = doc.findBlockByNumber(self._line_count - self._max_lines)
        if block is not None:
            cursor = self._text.textCursor()
            cursor.setPosition(0)
            cursor.setPosition(block.position(), cursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            self._line_count = self._max_lines


# ═══════════════════════════════════════════════════════════════
#  ModesPanel
# ═══════════════════════════════════════════════════════════════


class ModesPanel(QFrame):
    """Panneau de sélection du mode de recherche + zone de configuration.

    S'importe dans ``BotRecherche`` pour alléger sa page.
    Le tableau et les résultats restent dans Athéna.

    Signaux
    -------
    mode_changed(str) : émis quand l'utilisateur change de mode (\"normal\"/\"club\"/\"label\"/\"artiste\")
    search_requested(str) : émis pour lancer une recherche (mode Normal) — contient la query
    search_stopped() : émis pour arrêter la recherche en cours
    client_ares_selected(str) : émis quand un client Arès est choisi — contient le username
    chasse_requested(str, str) : émis pour lancer une chasse (mode Club/Label/Artiste) — mode, entite_id
    """

    mode_changed = Signal(str)
    search_requested = Signal(str)
    search_stopped = Signal()
    client_ares_selected = Signal(str)
    chasse_requested = Signal(str, str)  # mode, entite_id

    # ── Mapping modes → index QStackedWidget ──
    _PAGES = {
        "normal": 0,
        "club": 1,
        "label": 2,
        "artiste": 3,
        "genre": 4,
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("modesPanel")

        self._mode_actuel: str = "normal"
        self._searching: bool = False

        # Références aux boutons de mode (pour le style actif/inactif)
        self._mode_buttons: dict[str, QPushButton] = {}

        # Références aux contrôles de la config
        self._client_combo: QComboBox | None = None
        self._search_input: QLineEdit | None = None
        self._action_btn: QPushButton | None = None
        self._stop_btn: QPushButton | None = None
        self._genre_combo: QComboBox | None = None

        # Cascading dropdowns (modes Club/Label/Artiste)
        self._pays_combo: list[QComboBox] = []
        self._entite_combo: list[QComboBox] = []
        self._mots_cles_label: list[QLabel] = []

        self._build_ui()

    # ── API publique ────────────────────────────────────────────

    @property
    def status_console(self) -> StatusConsole:
        """La console d'information continue intégrée au panneau."""
        return self._status_console

    @property
    def mode(self) -> str:
        """Mode actuellement sélectionné."""
        return self._mode_actuel

    @property
    def query(self) -> str:
        """Texte de recherche (mode Normal)."""
        if self._search_input is not None:
            return self._search_input.text().strip()
        return ""

    @property
    def client_username(self) -> str:
        """Username sélectionné dans le combo Arès (mode Normal)."""
        if self._client_combo is not None and self._client_combo.currentIndex() >= 0:
            return self._client_combo.currentText()
        return ""

    @property
    def pays(self) -> str:
        """Pays sélectionné (modes Club/Label/Artiste)."""
        idx = self._PAGES.get(self._mode_actuel, 0)
        if idx > 0 and idx <= len(self._pays_combo):
            cb = self._pays_combo[idx - 1]
            if cb is not None and cb.currentIndex() >= 0:
                return cb.currentText()
        return ""

    @property
    def entite(self) -> str:
        """Entité sélectionnée (Club/Label/Artiste)."""
        idx = self._PAGES.get(self._mode_actuel, 0)
        if idx > 0 and idx <= len(self._entite_combo):
            cb = self._entite_combo[idx - 1]
            if cb is not None and cb.currentIndex() >= 0:
                return cb.currentText()
        return ""

    def set_searching(self, searching: bool) -> None:
        """Bascule l'état de recherche (affiche/masque le bouton Stop)."""
        self._searching = searching
        if self._action_btn is not None:
            self._action_btn.setVisible(not searching)
        if self._stop_btn is not None:
            self._stop_btn.setVisible(searching)

    def update_clients_ares(self, clients: list[ClientInfo]) -> None:
        """Met à jour la liste des clients Arès dans le sélecteur (mode Normal)."""
        if self._client_combo is None:
            return
        current = self._client_combo.currentText()
        self._client_combo.blockSignals(True)
        self._client_combo.clear()
        self._client_combo.addItem("— Tous les clients —", "")
        for c in clients:
            label = f"{c.username}  ({c.statut.name})"
            self._client_combo.addItem(label, c.username)
        # Restaurer la sélection si possible
        idx = self._client_combo.findText(current)
        if idx >= 0:
            self._client_combo.setCurrentIndex(idx)
        self._client_combo.blockSignals(False)

    def set_entite_list(self, pays: str | None = None) -> None:
        """Met à jour la liste des entités (Club/Label/Artiste) dans le combo du mode actuel.

        À implémenter quand les données JSON seront chargées.
        Pour l'instant, c'est un placeholder.

        Paramètres
        ----------
        pays : str | None
            Filtre les entités par pays. Si None, toutes les entités.
        """
        # Placeholder — sera connecté aux données JSON dans une phase ultérieure
        idx = self._PAGES.get(self._mode_actuel, 0) - 1
        if idx < 0 or idx >= len(self._entite_combo):
            return
        cb = self._entite_combo[idx]
        if cb is None:
            return
        cb.blockSignals(True)
        cb.clear()
        cb.addItem("— Choisir —", "")
        # TODO: Ajouter les entités filtrées par pays depuis les JSON
        cb.blockSignals(False)

    # ── Construction de l'interface ─────────────────────────────

    def _build_ui(self) -> None:
        """Construit l'interface complète du panneau."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # ── 1. Rangée des 4 boutons de mode ──
        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)
        mode_row.setContentsMargins(0, 0, 0, 0)

        modes = [
            ("normal", "🔎 Normal"),
            ("club", "🏛 Club"),
            ("label", "🏷 Label"),
            ("artiste", "🎤 Artiste"),
            ("genre", "🎵 Genre"),
        ]

        for key, label in modes:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            btn.setStyleSheet(_MODE_BTN_COMMON)
            btn.clicked.connect(lambda checked, k=key: self._on_mode_clicked(k))
            self._mode_buttons[key] = btn
            mode_row.addWidget(btn)

        mode_row.addStretch(1)
        layout.addLayout(mode_row)

        # ── 2. Zone de configuration (QStackedWidget) ──
        self._config_stack = QStackedWidget()
        self._config_stack.setStyleSheet("background: transparent;")

        # Page 0 : Mode Normal (barre de recherche + sélecteur client)
        self._config_stack.addWidget(self._build_normal_page())

        # Page 1 : Mode Club (cascading dropdowns)
        self._config_stack.addWidget(self._build_cascade_page("Club"))

        # Page 2 : Mode Label (cascading dropdowns)
        self._config_stack.addWidget(self._build_cascade_page("Label"))

        # Page 3 : Mode Artiste (cascading dropdowns)
        self._config_stack.addWidget(self._build_cascade_page("Artiste"))

        # Page 4 : Mode Genre (sélecteur de genre + boutons)
        self._config_stack.addWidget(self._build_genre_page())

        layout.addWidget(self._config_stack)

        # ── 3. Console d'information continue ──
        self._status_console = StatusConsole()
        layout.addWidget(self._status_console)

        # ── 4. Appliquer le style initial ──
        self._update_mode_styles()

    # ── Pages de configuration ──────────────────────────────────

    def _build_normal_page(self) -> QWidget:
        """Page mode Normal : sélecteur client + barre de recherche."""
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Sélecteur de client Arès
        self._client_combo = QComboBox()
        self._client_combo.setObjectName("clientAresCombo")
        self._client_combo.setMinimumWidth(180)
        self._client_combo.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self._client_combo.addItem("— Tous les clients —", "")
        self._client_combo.setStyleSheet(
            f"""
            #clientAresCombo {{
                background: {COLORS["BG_SURFACE"]};
                color: {COLORS["TEXT_PRIMARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 8px 10px;
                font-size: 12px;
            }}
            #clientAresCombo:focus {{
                border-color: {COLORS["PRIMARY"]};
            }}
            #clientAresCombo:hover {{
                border-color: {COLORS["ACCENT"]};
            }}
            #clientAresCombo::drop-down {{
                border: none;
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
            }}
            #clientAresCombo QAbstractItemView {{
                background: {COLORS["BG_SURFACE"]};
                color: {COLORS["TEXT_PRIMARY"]};
                border: 1px solid {COLORS["BORDER"]};
                selection-background-color: rgba({COLORS["PRIMARY"]}, '30');
                outline: none;
            }}
            """
        )
        self._client_combo.currentIndexChanged.connect(self._on_client_changed)
        layout.addWidget(self._client_combo)

        # Champ de recherche
        self._search_input = QLineEdit()
        self._search_input.setObjectName("modesSearchInput")
        self._search_input.setPlaceholderText("Rechercher des fichiers audio sur Soulseek…")
        self._search_input.setStyleSheet(
            f"""
            #modesSearchInput {{
                background: {COLORS["BG_SURFACE"]};
                color: {COLORS["TEXT_PRIMARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }}
            #modesSearchInput:focus {{
                border-color: {COLORS["PRIMARY"]};
            }}
            #modesSearchInput:disabled {{
                color: {COLORS["TEXT_DISABLED"]};
            }}
            """
        )
        self._search_input.returnPressed.connect(self._on_search_action)
        layout.addWidget(self._search_input, 1)

        # Bouton Rechercher
        self._action_btn = QPushButton("🔍 Rechercher")
        self._action_btn.setObjectName("modesActionBtn")
        self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._action_btn.setStyleSheet(
            f"""
            #modesActionBtn {{
                background: {COLORS["PRIMARY"]};
                color: {COLORS["TEXT_WHITE"]};
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 14px;
                font-weight: 600;
            }}
            #modesActionBtn:hover {{
                background: {COLORS["PRIMARY_HOVER"]};
            }}
            #modesActionBtn:disabled {{
                background: {COLORS["BG_BTN_DISABLED"]};
                color: {COLORS["TEXT_DISABLED"]};
            }}
            """
        )
        self._action_btn.clicked.connect(self._on_search_action)
        layout.addWidget(self._action_btn)

        # Bouton Stop (caché par défaut)
        self._stop_btn = QPushButton("⏹ Stop")
        self._stop_btn.setObjectName("modesStopBtn")
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.setVisible(False)
        self._stop_btn.setStyleSheet(
            f"""
            #modesStopBtn {{
                background: {COLORS["DANGER_BTN"]};
                color: {COLORS["TEXT_WHITE"]};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 600;
            }}
            #modesStopBtn:hover {{
                background: {COLORS["DANGER_BTN_HOVER"]};
            }}
            """
        )
        self._stop_btn.clicked.connect(self._on_stop_action)
        layout.addWidget(self._stop_btn)

        return page

    def _build_cascade_page(self, entite_type: str) -> QWidget:
        """Page pour un mode cascade : sélecteur Pays + sélecteur Entité + mots-clés + bouton chasse.

        Paramètres
        ----------
        entite_type : str
            \"Club\", \"Label\" ou \"Artiste\" — utilisé dans les labels.
        """
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Ligne : Pays → Entité
        row = QHBoxLayout()
        row.setSpacing(8)

        # ── Pays ──
        pays_label = QLabel("🌍 Pays :")
        pays_label.setStyleSheet(f"color: {COLORS['TEXT_SECONDARY']}; font-size: 12px; font-weight: 600; background: transparent;")
        row.addWidget(pays_label)

        pays_combo = QComboBox()
        pays_combo.setObjectName(f"paysCombo{entite_type}")
        pays_combo.setMinimumWidth(160)
        pays_combo.setStyleSheet(
            f"""
            #paysCombo{entite_type} {{
                background: {COLORS["BG_SURFACE"]};
                color: {COLORS["TEXT_PRIMARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            #paysCombo{entite_type}:focus {{
                border-color: {COLORS["ACCENT"]};
            }}
            #paysCombo{entite_type}::drop-down {{
                border: none;
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
            }}
            #paysCombo{entite_type} QAbstractItemView {{
                background: {COLORS["BG_SURFACE"]};
                color: {COLORS["TEXT_PRIMARY"]};
                border: 1px solid {COLORS["BORDER"]};
                selection-background-color: rgba({COLORS["ACCENT"]}, '30');
                outline: none;
            }}
            """
        )
        pays_combo.addItem("— Tous les pays —", "")
        pays_combo.currentIndexChanged.connect(self._on_pays_changed)
        row.addWidget(pays_combo)
        self._pays_combo.append(pays_combo)

        # ── Flèche ──
        arrow = QLabel("→")
        arrow.setStyleSheet(f"color: {COLORS['TEXT_MUTED']}; font-size: 16px; font-weight: 700; padding: 0 4px; background: transparent;")
        row.addWidget(arrow)

        # ── Entité ──
        entite_label = QLabel(f"{entite_type} :")
        entite_label.setStyleSheet(f"color: {COLORS['TEXT_SECONDARY']}; font-size: 12px; font-weight: 600; background: transparent;")
        row.addWidget(entite_label)

        entite_combo = QComboBox()
        entite_combo.setObjectName(f"entiteCombo{entite_type}")
        entite_combo.setMinimumWidth(200)
        entite_combo.setStyleSheet(
            f"""
            #entiteCombo{entite_type} {{
                background: {COLORS["BG_SURFACE"]};
                color: {COLORS["TEXT_PRIMARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            #entiteCombo{entite_type}:focus {{
                border-color: {COLORS["ACCENT"]};
            }}
            #entiteCombo{entite_type}::drop-down {{
                border: none;
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
            }}
            #entiteCombo{entite_type} QAbstractItemView {{
                background: {COLORS["BG_SURFACE"]};
                color: {COLORS["TEXT_PRIMARY"]};
                border: 1px solid {COLORS["BORDER"]};
                selection-background-color: rgba({COLORS["ACCENT"]}, '30');
                outline: none;
            }}
            """
        )
        entite_combo.addItem("— Choisir —", "")
        row.addWidget(entite_combo, 1)
        self._entite_combo.append(entite_combo)

        row.addStretch(1)
        layout.addLayout(row)

        # ── Mots-clés associés ──
        mots_label = QLabel("Mots-clés : —")
        mots_label.setStyleSheet(
            f"color: {COLORS['TEXT_MUTED']}; font-size: 11px; background: transparent; padding: 2px 4px;"
        )
        layout.addWidget(mots_label)
        self._mots_cles_label.append(mots_label)

        # ── Bouton Lancer la chasse ──
        chasse_row = QHBoxLayout()
        chasse_row.setSpacing(8)

        chasse_btn = QPushButton("🚀 Lancer la chasse")
        chasse_btn.setObjectName("chasseBtn")
        chasse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        chasse_btn.setStyleSheet(
            f"""
            #chasseBtn {{
                background: {COLORS["SUCCESS"]};
                color: {COLORS["TEXT_WHITE"]};
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-size: 13px;
                font-weight: 700;
            }}
            #chasseBtn:hover {{
                background: {COLORS["SUCCESS_HOVER"]};
            }}
            #chasseBtn:disabled {{
                background: {COLORS["BG_BTN_DISABLED"]};
                color: {COLORS["TEXT_DISABLED"]};
            }}
            """
        )
        chasse_btn.clicked.connect(self._on_chasse_action)
        chasse_row.addWidget(chasse_btn)

        stop_chasse_btn = QPushButton("⏹ Stop")
        stop_chasse_btn.setObjectName("chasseStopBtn")
        stop_chasse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        stop_chasse_btn.setVisible(False)
        stop_chasse_btn.setStyleSheet(
            f"""
            #chasseStopBtn {{
                background: {COLORS["DANGER_BTN"]};
                color: {COLORS["TEXT_WHITE"]};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            #chasseStopBtn:hover {{
                background: {COLORS["DANGER_BTN_HOVER"]};
            }}
            """
        )
        stop_chasse_btn.clicked.connect(self._on_stop_chasse_action)
        chasse_row.addWidget(stop_chasse_btn)

        chasse_row.addStretch(1)
        layout.addLayout(chasse_row)

        return page

    def _build_genre_page(self) -> QWidget:
        """Page mode Genre : sélecteur de genre + bouton Lancer.

        Le widget complet ``ModeGenre`` (avec tableau et filtres)
        est dans ``BotRecherche`` — ici c'est juste la config
        minimale nécessaire pour lancer la boucle.
        """
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ── Ligne : Genre → bouton ──
        row = QHBoxLayout()
        row.setSpacing(8)

        genre_label = QLabel("🎵 Genre :")
        genre_label.setStyleSheet(f"color: {COLORS['TEXT_SECONDARY']}; font-size: 12px; font-weight: 600; background: transparent;")
        row.addWidget(genre_label)

        genre_combo = QComboBox()
        genre_combo.setObjectName("genreModeCombo")
        genre_combo.setMinimumWidth(200)
        genre_combo.setStyleSheet(
            f"""
            #genreModeCombo {{
                background: {COLORS["BG_SURFACE"]};
                color: {COLORS["TEXT_PRIMARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            #genreModeCombo:focus {{
                border-color: {COLORS["ACCENT"]};
            }}
            #genreModeCombo::drop-down {{
                border: none;
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
            }}
            #genreModeCombo QAbstractItemView {{
                background: {COLORS["BG_SURFACE"]};
                color: {COLORS["TEXT_PRIMARY"]};
                border: 1px solid {COLORS["BORDER"]};
                selection-background-color: rgba(COLORS['ACCENT'], '30');
                outline: none;
            }}
            """
        )
        genre_combo.addItem("— Choisir —", "")
        row.addWidget(genre_combo, 1)
        self._genre_combo = genre_combo

        # Bouton Lancer la chasse
        genre_btn = QPushButton("🚀 Lancer")
        genre_btn.setObjectName("genreModeBtn")
        genre_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        genre_btn.setStyleSheet(
            f"""
            #genreModeBtn {{
                background: {COLORS["SUCCESS"]};
                color: {COLORS["TEXT_WHITE"]};
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-size: 13px;
                font-weight: 700;
            }}
            #genreModeBtn:hover {{
                background: {COLORS["SUCCESS_HOVER"]};
            }}
            #genreModeBtn:disabled {{
                background: {COLORS["BG_BTN_DISABLED"]};
                color: {COLORS["TEXT_DISABLED"]};
            }}
            """
        )
        genre_btn.clicked.connect(self._on_genre_action)
        row.addWidget(genre_btn)

        # Bouton Stop
        genre_stop_btn = QPushButton("⏹ Stop")
        genre_stop_btn.setObjectName("genreModeStopBtn")
        genre_stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        genre_stop_btn.setVisible(False)
        genre_stop_btn.setStyleSheet(
            f"""
            #genreModeStopBtn {{
                background: {COLORS["DANGER_BTN"]};
                color: {COLORS["TEXT_WHITE"]};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            #genreModeStopBtn:hover {{
                background: {COLORS["DANGER_BTN_HOVER"]};
            }}
            """
        )
        genre_stop_btn.clicked.connect(self._on_stop_genre_action)
        row.addWidget(genre_stop_btn)

        row.addStretch(1)
        layout.addLayout(row)

        # ── Indication ──
        hint = QLabel("💡 Les résultats s'afficheront dans la vue dédiée en dessous")
        hint.setStyleSheet(f"color: {COLORS['TEXT_MUTED']}; font-size: 11px; background: transparent;")
        layout.addWidget(hint)

        return page

    # ── Gestion des modes ──────────────────────────────────────

    @log_action("Changer le mode de recherche")
    def _on_mode_clicked(self, mode: str) -> None:
        """Change le mode actif et bascule la page de config."""
        if mode == self._mode_actuel:
            return
        self._mode_actuel = mode

        # Basculer la page de config
        idx = self._PAGES.get(mode, 0)
        self._config_stack.setCurrentIndex(idx)

        # Mettre à jour le style des boutons
        self._update_mode_styles()

        # Émettre le signal
        self.mode_changed.emit(mode)
        logger.debug("ModesPanel: mode changé → %s", mode)

    def _update_mode_styles(self) -> None:
        """Applique le style actif/inactif aux boutons de mode."""
        for key, btn in self._mode_buttons.items():
            if key == self._mode_actuel:
                btn.setStyleSheet(_MODE_BTN_ACTIF)
            else:
                btn.setStyleSheet(_MODE_BTN_COMMON)

    # ── Actions ─────────────────────────────────────────────────

    @log_action("Lancer la recherche")
    def _on_search_action(self) -> None:
        """Lance la recherche (mode Normal)."""
        if self._search_input is None:
            return
        query = self._search_input.text().strip()
        if len(query) < 2:
            return
        self.search_requested.emit(query)

    @log_action("Arrêter la recherche")
    def _on_stop_action(self) -> None:
        """Arrête la recherche en cours (mode Normal)."""
        self.search_stopped.emit()

    @log_action("Lancer la chasse")
    def _on_chasse_action(self) -> None:
        """Lance la chasse (mode Club/Label/Artiste)."""
        idx = self._PAGES.get(self._mode_actuel, 0) - 1
        if idx < 0 or idx >= len(self._entite_combo):
            return
        entite_combo = self._entite_combo[idx]
        if entite_combo is None:
            return
        entite_id = entite_combo.currentData()
        if not entite_id:
            return
        self.chasse_requested.emit(self._mode_actuel, entite_id)

    @log_action("Lancer la recherche Genre")
    def _on_genre_action(self) -> None:
        """Lance la recherche Genre (mode Genre)."""
        if self._genre_combo is None:
            return
        genre_id = self._genre_combo.currentData()
        if not genre_id:
            return
        self.chasse_requested.emit("genre", genre_id)

    @log_action("Arrêter la recherche Genre")
    def _on_stop_genre_action(self) -> None:
        """Arrête la recherche Genre."""
        self.search_stopped.emit()

    @log_action("Arrêter la chasse")
    def _on_stop_chasse_action(self) -> None:
        """Arrête la chasse en cours."""
        self.search_stopped.emit()

    def _on_client_changed(self, index: int) -> None:
        """Un client a été sélectionné dans le combo Arès.

        Le signal est toujours émis, même pour "— Tous les clients —"
        (où username est vide), pour permettre de réinitialiser
        le client ciblé dans BotRecherche.
        """
        if self._client_combo is None:
            return
        username = self._client_combo.itemData(index) or ""
        self.client_ares_selected.emit(username)

    def _on_pays_changed(self, index: int) -> None:
        """Le pays a changé → filtrer la liste des entités."""
        self.set_entite_list(self.pays)

    # ── Focus clavier ──────────────────────────────────────────

    def set_query(self, query: str) -> None:
        """Définit le texte du champ de recherche (mode Normal).

        Paramètres
        ----------
        query : str
            Texte à placer dans le champ de recherche.
        """
        if self._search_input is not None:
            self._search_input.setText(query)

    def focus_search(self) -> None:
        """Donne le focus au champ de recherche (mode Normal)."""
        if self._search_input is not None:
            self._search_input.setFocus()
            self._search_input.selectAll()
