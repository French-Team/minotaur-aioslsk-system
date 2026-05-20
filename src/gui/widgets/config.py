"""
Widgets de configuration réutilisables pour les pages de paramètres.

Composants :
  - ConfigSection  : cadre avec titre, regroupe des options
  - ConfigToggle   : ligne avec label + interrupteur (checkbox stylisé)
  - ConfigEntry    : ligne avec label + champ de texte
  - ConfigCombo    : ligne avec label + menu déroulant
  - ConfigSpin     : ligne avec label + champ numérique
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.services import app_config

# ═════════════════════════════════════════════════════════════════
#  ConfigSection — groupe d'options
# ═════════════════════════════════════════════════════════════════


class ConfigSection(QFrame):
    """Cadre contenant un groupe d'options de configuration.

    Utilisation ::

        section = ConfigSection("Réseau")
        section.add(ConfigToggle("Activer UPnP", "reseau.upnp"))
        section.add(ConfigEntry("Port d'écoute", "reseau.port_ecoute"))
    """

    def __init__(self, titre: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("configSection")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(6)

        # ── Titre de section ──
        title_label = QLabel(titre)
        title_label.setObjectName("configSectionTitle")
        title_label.setStyleSheet("color: #6c5ce7; font-size: 13px; font-weight: 700;")
        layout.addWidget(title_label)

        # Séparateur
        sep = QFrame()
        # pyrefly: ignore [missing-attribute]
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #2e2e3a;")
        layout.addWidget(sep)

        # Layout interne pour les options
        self._options_layout = QVBoxLayout()
        self._options_layout.setContentsMargins(0, 4, 0, 0)
        self._options_layout.setSpacing(4)
        layout.addLayout(self._options_layout)

    def add(self, widget: QWidget) -> None:
        """Ajoute une option à la section."""
        self._options_layout.addWidget(widget)


# ═════════════════════════════════════════════════════════════════
#  ConfigToggle — interrupteur on/off
# ═════════════════════════════════════════════════════════════════


class ConfigToggle(QFrame):
    """Ligne de configuration avec label + interrupteur.

    Le changement est automatiquement persisté via ``app_config``.

    Signaux :
      - toggled(bool) : émis quand l'utilisateur change la valeur
    """

    toggled = Signal(bool)

    def __init__(
        self,
        label: str,
        config_key: str,
        description: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("configRow")
        self._config_key = config_key

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)

        # ── Label + description ──
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)

        self._label = QLabel(label)
        self._label.setObjectName("configLabel")
        self._label.setStyleSheet("color: #e4e4ec; font-size: 12px; font-weight: 600;")
        text_layout.addWidget(self._label)

        if description:
            self._desc = QLabel(description)
            self._desc.setObjectName("configDesc")
            self._desc.setStyleSheet("color: #5a5a6a; font-size: 10px;")
            self._desc.setWordWrap(True)
            text_layout.addWidget(self._desc)

        layout.addLayout(text_layout, 1)

        # ── Interrupteur ──
        self._checkbox = QCheckBox()
        self._checkbox.setObjectName("configToggle")
        self._checkbox.setCursor(Qt.CursorShape.PointingHandCursor)

        # Valeur initiale depuis la config
        initial = app_config.get(config_key, False)
        self._checkbox.setChecked(bool(initial))

        self._checkbox.toggled.connect(self._on_toggled)
        layout.addWidget(self._checkbox)

    # ── API publique ─────────────────────────────────────────────

    @property
    def is_checked(self) -> bool:
        return self._checkbox.isChecked()

    def set_checked(self, value: bool) -> None:
        self._checkbox.setChecked(value)

    @property
    def config_key(self) -> str:
        return self._config_key

    # ── Interne ─────────────────────────────────────────────────

    def _on_toggled(self, checked: bool) -> None:
        app_config.set(self._config_key, checked)
        self.toggled.emit(checked)


# ═════════════════════════════════════════════════════════════════
#  Fonctions de lecture/écriture de widgets (pour applique_profile)
# ═════════════════════════════════════════════════════════════════


def _lire_valeur_widget(widget: QWidget):
    """Lit la valeur actuelle d'un widget de config.

    Supporte : ConfigToggle, ConfigEntry, ConfigCombo, ConfigSpin,
    ConfigFilePicker, ConfigDirectoryPicker.
    """
    # L'ordre des tests est important : is_checked avant value
    # car ConfigToggle n'a pas de ``value``.
    if isinstance(widget, ConfigToggle):
        return widget.is_checked
    if isinstance(widget, ConfigCombo):
        return widget.value
    if isinstance(widget, ConfigSpin):
        return widget.value
    if isinstance(widget, ConfigEntry):
        return widget.text
    if isinstance(widget, ConfigFilePicker):
        return widget.file_path
    if isinstance(widget, ConfigDirectoryPicker):
        return widget.directory
    return "?"


def _ecrire_valeur_widget(widget: QWidget, valeur) -> None:
    """Écrit une valeur sur un widget de config.

    Supporte : ConfigToggle, ConfigEntry, ConfigCombo, ConfigSpin,
    ConfigFilePicker, ConfigDirectoryPicker.
    """
    if isinstance(widget, ConfigToggle):
        widget.set_checked(bool(valeur))
    elif isinstance(widget, ConfigCombo):
        widget.set_value(str(valeur))
    elif isinstance(widget, ConfigSpin):
        widget.set_value(int(valeur))
    elif isinstance(widget, ConfigEntry):
        widget.set_text(str(valeur))
        # setText n'émet pas editingFinished → persistance manuelle
        app_config.set(widget.config_key, str(valeur))
    elif isinstance(widget, ConfigFilePicker):
        widget.set_file_path(str(valeur))
    elif isinstance(widget, ConfigDirectoryPicker):
        widget.set_directory(str(valeur))


# ═════════════════════════════════════════════════════════════════
#  ConfigEntry — champ de texte
# ═════════════════════════════════════════════════════════════════


class ConfigEntry(QFrame):
    """Ligne de configuration avec label + champ texte.

    La valeur est persistée automatiquement à la perte de focus ou
    quand l'utilisateur appuie sur Entrée.
    """

    changed = Signal(str)

    def __init__(
        self,
        label: str,
        config_key: str,
        placeholder: str = "",
        description: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("configRow")
        self._config_key = config_key

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)

        # ── Label + description ──
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)

        self._label = QLabel(label)
        self._label.setObjectName("configLabel")
        self._label.setStyleSheet("color: #e4e4ec; font-size: 12px; font-weight: 600;")
        text_layout.addWidget(self._label)

        if description:
            self._desc = QLabel(description)
            self._desc.setObjectName("configDesc")
            self._desc.setStyleSheet("color: #5a5a6a; font-size: 10px;")
            text_layout.addWidget(self._desc)

        layout.addLayout(text_layout, 1)

        # ── Champ texte ──
        self._entry = QLineEdit()
        self._entry.setObjectName("configEntry")
        self._entry.setPlaceholderText(placeholder)

        # Valeur initiale
        initial = app_config.get(config_key, "")
        self._entry.setText(str(initial) if initial is not None else "")

        # Persistance au focus perdu + Entrée
        self._entry.editingFinished.connect(self._on_changed)
        self._entry.textChanged.connect(self._on_text_changed)

        self._entry.setFixedWidth(240)
        layout.addWidget(self._entry)

    # ── API publique ─────────────────────────────────────────────

    @property
    def text(self) -> str:
        return self._entry.text()

    def set_text(self, value: str) -> None:
        self._entry.setText(value)

    @property
    def config_key(self) -> str:
        return self._config_key

    # ── Interne ─────────────────────────────────────────────────

    def _on_changed(self) -> None:
        app_config.set(self._config_key, self._entry.text())
        self.changed.emit(self._entry.text())

    def _on_text_changed(self, text: str) -> None:
        """Émet ``changed`` en temps réel (pour prévisualisation)."""
        self.changed.emit(text)


# ═════════════════════════════════════════════════════════════════
#  ConfigCombo — menu déroulant
# ═════════════════════════════════════════════════════════════════


class ConfigCombo(QFrame):
    """Ligne de configuration avec label + menu déroulant."""

    changed = Signal(str)

    def __init__(
        self,
        label: str,
        config_key: str,
        options: list[tuple[str, str]],  # (valeur_affichée, valeur_stockée)
        description: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("configRow")
        self._config_key = config_key
        self._options = options

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)

        # ── Label + description ──
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)

        self._label = QLabel(label)
        self._label.setObjectName("configLabel")
        self._label.setStyleSheet("color: #e4e4ec; font-size: 12px; font-weight: 600;")
        text_layout.addWidget(self._label)

        if description:
            self._desc = QLabel(description)
            self._desc.setObjectName("configDesc")
            self._desc.setStyleSheet("color: #5a5a6a; font-size: 10px;")
            text_layout.addWidget(self._desc)

        layout.addLayout(text_layout, 1)

        # ── Combo ──
        self._combo = QComboBox()
        self._combo.setObjectName("configCombo")

        for display, _store in options:
            self._combo.addItem(display, _store)

        # Valeur initiale
        initial = app_config.get(config_key, "")
        self._set_combo_value(str(initial) if initial is not None else "")

        self._combo.currentIndexChanged.connect(self._on_changed)

        self._combo.setFixedWidth(240)
        layout.addWidget(self._combo)

    # ── API publique ─────────────────────────────────────────────

    @property
    def value(self) -> str:
        idx = self._combo.currentIndex()
        if idx >= 0:
            return self._combo.itemData(idx)  # type: ignore[return-value]
        return ""

    def set_value(self, value: str) -> None:
        self._set_combo_value(value)
        app_config.set(self._config_key, value)

    @property
    def config_key(self) -> str:
        return self._config_key

    # ── Interne ─────────────────────────────────────────────────

    def _set_combo_value(self, value: str) -> None:
        for i in range(self._combo.count()):
            if self._combo.itemData(i) == value:
                self._combo.setCurrentIndex(i)
                return
        # Défaut : premier élément
        if self._combo.count() > 0:
            self._combo.setCurrentIndex(0)

    def _on_changed(self, index: int) -> None:
        if index >= 0:
            val = self._combo.itemData(index)
            app_config.set(self._config_key, val)
            self.changed.emit(str(val) if val is not None else "")


# ═════════════════════════════════════════════════════════════════
#  ConfigSpin — champ numérique
# ═════════════════════════════════════════════════════════════════


class ConfigSpin(QFrame):
    """Ligne de configuration avec label + champ numérique."""

    changed = Signal(int)

    def __init__(
        self,
        label: str,
        config_key: str,
        minimum: int = 0,
        maximum: int = 999999,
        step: int = 1,
        suffix: str = "",
        description: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("configRow")
        self._config_key = config_key

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)

        # ── Label + description ──
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)

        self._label = QLabel(label)
        self._label.setObjectName("configLabel")
        self._label.setStyleSheet("color: #e4e4ec; font-size: 12px; font-weight: 600;")
        text_layout.addWidget(self._label)

        if description:
            self._desc = QLabel(description)
            self._desc.setObjectName("configDesc")
            self._desc.setStyleSheet("color: #5a5a6a; font-size: 10px;")
            text_layout.addWidget(self._desc)

        layout.addLayout(text_layout, 1)

        # ── Spin ──
        self._spin = QSpinBox()
        self._spin.setObjectName("configSpin")
        self._spin.setRange(minimum, maximum)
        self._spin.setSingleStep(step)
        if suffix:
            self._spin.setSuffix(f" {suffix}")

        # Valeur initiale
        initial = app_config.get(config_key, 0)
        self._spin.setValue(int(initial) if initial is not None else 0)

        self._spin.valueChanged.connect(self._on_changed)

        self._spin.setFixedWidth(120)
        layout.addWidget(self._spin)

    # ── API publique ─────────────────────────────────────────────

    @property
    def value(self) -> int:
        return self._spin.value()

    def set_value(self, val: int) -> None:
        self._spin.setValue(val)

    @property
    def config_key(self) -> str:
        return self._config_key

    # ── Interne ─────────────────────────────────────────────────

    def _on_changed(self, value: int) -> None:
        app_config.set(self._config_key, value)
        self.changed.emit(value)


# ═════════════════════════════════════════════════════════════════
#  ConfigFilePicker — sélecteur de fichier
# ═════════════════════════════════════════════════════════════════


class ConfigFilePicker(QFrame):
    """Ligne de configuration avec label + sélecteur de fichier.

    Affiche le chemin du fichier sélectionné dans un champ en lecture
    seule et propose un bouton "Parcourir…" ouvrant une boîte de
    dialogue. Utile pour les photos de profil, dossiers, etc.

    Le chemin est persisté automatiquement dans ``app_config``.
    """

    changed = Signal(str)

    def __init__(
        self,
        label: str,
        config_key: str,
        placeholder: str = "",
        file_filter: str = "Tous les fichiers (*)",
        description: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("configRow")
        self._config_key = config_key
        self._file_filter = file_filter

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)

        # ── Label + description ──
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)

        self._label = QLabel(label)
        self._label.setObjectName("configLabel")
        self._label.setStyleSheet("color: #e4e4ec; font-size: 12px; font-weight: 600;")
        text_layout.addWidget(self._label)

        if description:
            self._desc = QLabel(description)
            self._desc.setObjectName("configDesc")
            self._desc.setStyleSheet("color: #5a5a6a; font-size: 10px;")
            text_layout.addWidget(self._desc)

        layout.addLayout(text_layout, 1)

        # ── Champ chemin (lecture seule) + bouton Parcourir ──
        entry_layout = QHBoxLayout()
        entry_layout.setSpacing(4)

        self._path = QLineEdit()
        self._path.setObjectName("configFilePicker")
        self._path.setReadOnly(True)
        self._path.setPlaceholderText(placeholder)

        # Valeur initiale
        initial = app_config.get(config_key, "")
        self._path.setText(str(initial) if initial else "")

        self._browse_btn = QPushButton("Parcourir…")
        self._browse_btn.setObjectName("configBrowseBtn")
        self._browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse_btn.setStyleSheet(
            "QPushButton {"
            "  background: #2e2e3a;"
            "  color: #e4e4ec;"
            "  border: 1px solid #3e3e4a;"
            "  border-radius: 4px;"
            "  padding: 4px 12px;"
            "  font-size: 11px;"
            "}"
            "QPushButton:hover {"
            "  background: #3e3e4a;"
            "}"
        )
        self._browse_btn.clicked.connect(self._on_browse)

        # Bouton effacer
        self._clear_btn = QPushButton("✕")
        self._clear_btn.setObjectName("configClearBtn")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.setFixedWidth(24)
        self._clear_btn.setStyleSheet(
            "QPushButton {"
            "  background: transparent;"
            "  color: #5a5a6a;"
            "  border: none;"
            "  font-size: 12px;"
            "}"
            "QPushButton:hover {"
            "  color: #e74c3c;"
            "}"
        )
        self._clear_btn.clicked.connect(self._on_clear)

        entry_layout.addWidget(self._path, 1)
        entry_layout.addWidget(self._clear_btn)
        entry_layout.addWidget(self._browse_btn)

        layout.addLayout(entry_layout)

    # ── API publique ─────────────────────────────────────────────

    @property
    def file_path(self) -> str:
        return self._path.text()

    def set_file_path(self, path: str) -> None:
        self._path.setText(path)
        app_config.set(self._config_key, path)
        self.changed.emit(path)

    @property
    def config_key(self) -> str:
        return self._config_key

    # ── Interne ─────────────────────────────────────────────────

    def _on_browse(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner un fichier",
            self._path.text() or "",
            self._file_filter,
        )
        if path:
            self.set_file_path(path)

    def _on_clear(self) -> None:
        self.set_file_path("")


class ConfigDirectoryPicker(QFrame):
    """Ligne de configuration avec label + sélecteur de dossier.

    Similaire à ``ConfigFilePicker`` mais ouvre une boîte de
    dialogue de sélection de dossier via ``QFileDialog.getExistingDirectory``.
    """

    changed = Signal(str)

    def __init__(
        self,
        label: str,
        config_key: str,
        placeholder: str = "",
        description: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("configRow")
        self._config_key = config_key

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)

        # ── Label + description ──
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)

        self._label = QLabel(label)
        self._label.setObjectName("configLabel")
        self._label.setStyleSheet("color: #e4e4ec; font-size: 12px; font-weight: 600;")
        text_layout.addWidget(self._label)

        if description:
            self._desc = QLabel(description)
            self._desc.setObjectName("configDesc")
            self._desc.setStyleSheet("color: #5a5a6a; font-size: 10px;")
            text_layout.addWidget(self._desc)

        layout.addLayout(text_layout, 1)

        # ── Champ chemin (lecture seule) + bouton Parcourir ──
        entry_layout = QHBoxLayout()
        entry_layout.setSpacing(4)

        self._path = QLineEdit()
        self._path.setObjectName("configFilePicker")
        self._path.setReadOnly(True)
        self._path.setPlaceholderText(placeholder)

        # Valeur initiale
        initial = app_config.get(config_key, "")
        self._path.setText(str(initial) if initial else "")

        self._browse_btn = QPushButton("Parcourir…")
        self._browse_btn.setObjectName("configBrowseBtn")
        self._browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse_btn.setStyleSheet(
            "QPushButton {"
            "  background: #2e2e3a;"
            "  color: #e4e4ec;"
            "  border: 1px solid #3e3e4a;"
            "  border-radius: 4px;"
            "  padding: 4px 12px;"
            "  font-size: 11px;"
            "}"
            "QPushButton:hover {"
            "  background: #3e3e4a;"
            "}"
        )
        self._browse_btn.clicked.connect(self._on_browse)

        # Bouton effacer
        self._clear_btn = QPushButton("✕")
        self._clear_btn.setObjectName("configClearBtn")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.setFixedWidth(24)
        self._clear_btn.setStyleSheet(
            "QPushButton {"
            "  background: transparent;"
            "  color: #5a5a6a;"
            "  border: none;"
            "  font-size: 12px;"
            "}"
            "QPushButton:hover {"
            "  color: #e74c3c;"
            "}"
        )
        self._clear_btn.clicked.connect(self._on_clear)

        entry_layout.addWidget(self._path, 1)
        entry_layout.addWidget(self._clear_btn)
        entry_layout.addWidget(self._browse_btn)

        layout.addLayout(entry_layout)

    # ── API publique ─────────────────────────────────────────────

    @property
    def directory(self) -> str:
        return self._path.text()

    def set_directory(self, path: str) -> None:
        self._path.setText(path)
        app_config.set(self._config_key, path)
        self.changed.emit(path)

    @property
    def config_key(self) -> str:
        return self._config_key

    # ── Interne ─────────────────────────────────────────────────

    def _on_browse(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        path = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner un dossier",
            self._path.text() or "",
        )
        if path:
            self.set_directory(path)

    def _on_clear(self) -> None:
        self.set_directory("")


# ═════════════════════════════════════════════════════════════════
#  ConfigResetBtn — bouton de réinitialisation
# ═════════════════════════════════════════════════════════════════


class ConfigResetBtn(QPushButton):
    """Bouton 'Réinitialiser les paramètres' avec confirmation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("↺ Réinitialiser les paramètres", parent)
        self.setObjectName("configResetBtn")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._on_click)

    def _on_click(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "Réinitialisation",
            "Voulez-vous vraiment réinitialiser tous les paramètres ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            app_config.reset()
            # Notification : un signal global serait mieux, mais
            # pour l'instant l'utilisateur devra redémarrer la page
            QMessageBox.information(
                self,
                "Réinitialisation",
                "Paramètres réinitialisés.\nRedémarrez l'application pour appliquer.",
            )


# ═════════════════════════════════════════════════════════════════
#  Fonctions utilitaires
# ═════════════════════════════════════════════════════════════════


def highlight_widget(widget: QWidget, duree_ms: int = 1500) -> None:
    """Met en surbrillance un widget modifié (scroll + animation).

    Args:
        widget: Le widget à mettre en évidence.
        duree_ms: Durée de la surbrillance en millisecondes.
    """
    from PySide6.QtCore import QTimer

    # 1. Scroll jusqu'au widget
    parent = widget.parent()
    while parent is not None:
        if isinstance(parent, QScrollArea):
            parent.ensureWidgetVisible(widget)
            break
        parent = parent.parent()

    # 2. Animation de surbrillance — bordure seule, pas de fond coloré
    style_original = widget.styleSheet()
    widget.setStyleSheet("border: 2px solid rgba(108, 92, 231, 0.5);")
    QTimer.singleShot(duree_ms, lambda: widget.setStyleSheet(style_original))


# ═════════════════════════════════════════════════════════════════
#  ConfigPage — page de configuration complète (scrollable)
# ═════════════════════════════════════════════════════════════════


class ConfigPage(QFrame):
    """Page de configuration complète avec défilement.

    Utilisation ::

        page = ConfigPage("Réseau")
        section = ConfigSection("Connexion")
        section.add(ConfigToggle("UPnP", "reseau.upnp"))
        page.add(section)

    Nouveautés (profil Optimiseur) :

        page.applique_profile({"reseau.upnp": True})
        # retourne [(config_key, ancienne_valeur, nouvelle_valeur, widget)]
    """

    def __init__(self, titre: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(f"page{titre}")
        self._widgets: dict[str, QWidget] = {}  # config_key → widget

        # Layout principal
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # ── Titre de page ──
        header = QLabel(titre)
        header.setObjectName("configPageTitle")
        header.setStyleSheet("color: #6c5ce7; font-size: 16px; font-weight: 700; padding: 16px 16px 8px 16px;")
        outer.addWidget(header)

        # ── Zone scrollable ──
        self._scroll = QScrollArea()
        self._scroll.setObjectName("configScroll")
        self._scroll.setWidgetResizable(True)
        # pyrefly: ignore [missing-attribute]
        self._scroll.setFrameShape(QFrame.NoFrame)

        self._content = QWidget()
        self._content.setObjectName("configContent")
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(16, 4, 16, 16)
        self._layout.setSpacing(0)
        self._layout.addStretch(1)

        self._scroll.setWidget(self._content)
        outer.addWidget(self._scroll, 1)

    # ── API publique ─────────────────────────────────────────────

    def add(self, widget: QWidget) -> None:
        """Ajoute un widget (ConfigSection, ConfigResetBtn, etc.)."""
        # Insérer avant le stretch
        self._layout.insertWidget(self._layout.count() - 1, widget)
        # Collecter les widgets de config dans le container ajouté
        self._collect_config_widgets(widget)

    def add_placeholder(self, text: str) -> None:
        """Ajoute un message placeholder (quand aucune option n'est encore disponible)."""
        placeholder = QLabel(text)
        placeholder.setObjectName("configPlaceholder")
        placeholder.setStyleSheet("color: #3a3a4a; font-size: 12px; padding: 16px;")
        self._layout.insertWidget(self._layout.count() - 1, placeholder)

    def _find_widget_by_key(self, config_key: str) -> QWidget | None:
        """Retourne le widget associé à une config_key, ou None."""
        return self._widgets.get(config_key)

    def _collect_config_widgets(self, container: QWidget) -> None:
        """Parcourt récursivement un container pour indexer les widgets de config.

        Détecte automatiquement les widgets ConfigToggle, ConfigEntry,
        ConfigCombo, ConfigSpin, ConfigFilePicker, ConfigDirectoryPicker
        via leur propriété ``config_key``.
        """
        for child in container.findChildren(QFrame):
            try:
                key = child.config_key  # type: ignore[union-attr]
                if isinstance(key, str) and key:
                    self._widgets[key] = child
            except (AttributeError, TypeError):
                pass

    def applique_profile(self, data: dict) -> list[tuple[str, str, str, QWidget | None]]:
        """Applique les valeurs d'un profil aux widgets de la page.

        Args:
            data: Dictionnaire {config_key: valeur}.

        Returns:
            Liste de (config_key, valeur_avant, valeur_après, widget_modifié).
            widget_modifié = None si le widget n'a pas été trouvé.
        """
        results: list[tuple[str, str, str, QWidget | None]] = []

        for config_key, nouvelle_valeur in data.items():
            widget = self._find_widget_by_key(config_key)
            if widget is None:
                results.append((config_key, "?", str(nouvelle_valeur), None))
                continue

            # Lire l'ancienne valeur
            ancienne = _lire_valeur_widget(widget)

            # Appliquer la nouvelle valeur
            _ecrire_valeur_widget(widget, nouvelle_valeur)

            results.append((config_key, str(ancienne), str(nouvelle_valeur), widget))

        return results
