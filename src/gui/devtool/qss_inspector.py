"""QSS Inspector — DevTool pour inspecter les widgets PySide6 et leurs stylesheets.

Fonctionnalités :
- Arbre hiérarchique de tous les widgets
- Propriétés détaillées (classe, objectName, geometry, stylesheet)
- Validation QSS avec détection des erreurs courantes
- Mode inspection visuelle (clic sur un widget → sélection dans l'arbre)
- Raccourci Ctrl+Shift+I pour basculer l'affichage
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from PySide6.QtCore import (
    QEvent,
    Qt,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDockWidget,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
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

logger = logging.getLogger(__name__)

# ── Constantes pour la validation QSS ─────────────────────────────────────

# Couleurs hex sur 8 chiffres (#RRGGBBAA) non supportées par Qt
_RE_HEX8 = re.compile(r"#[0-9a-fA-F]{8}\b")

# Couleurs hex sur 3 chiffres (#RGB) non supportées par Qt
_RE_HEX3 = re.compile(r"#[0-9a-fA-F]{3}\b")

# Propriétés CSS typiques, et si elles attendent une couleur ou une valeur numérique
_CSS_COLOR_PROPS = {
    "color",
    "background-color",
    "background",
    "border-color",
    "border-top-color",
    "border-right-color",
    "border-bottom-color",
    "border-left-color",
    "outline-color",
    "text-decoration-color",
    "caret-color",
    "selection-color",
    "selection-background-color",
    "alternate-background-color",
}

_CSS_RECT_PROPS = {
    "padding",
    "margin",
    "border-width",
    "border-radius",
    "padding-top",
    "padding-right",
    "padding-bottom",
    "padding-left",
    "margin-top",
    "margin-right",
    "margin-bottom",
    "margin-left",
}

# ── Fonctions utilitaires ──────────────────────────────────────────────────


def _widget_label(w: QWidget) -> str:
    """Produit un libellé lisible pour un widget : ClassName[objectName]."""
    cls = w.__class__.__name__
    name = w.objectName()
    if name:
        return f"{cls}[{name}]"
    # Tronque les textes longs
    txt = getattr(w, "text", lambda: "")()
    if txt:
        txt_short = txt.replace("\n", " ")[:28]
        return f"{cls}('{txt_short}')"
    return cls


def _widget_path(w: QWidget) -> str:
    """Chemin complet du widget dans l'arbre (séparateur →)."""
    parts = []
    cur: Optional[QWidget] = w
    while cur is not None and not isinstance(cur, QApplication):
        parts.append(_widget_label(cur))
        cur = cur.parentWidget()
    return " → ".join(reversed(parts))


def _qss_errors(stylesheet: str) -> list[str]:
    """Analyse un stylesheet QSS et retourne une liste d'erreurs détectées."""
    errors: list[str] = []

    # 1. Couleurs hex sur 8 chiffres (#RRGGBBAA) → non supportées Qt
    for m in _RE_HEX8.finditer(stylesheet):
        errors.append(f"Couleur {m.group()} sur 8 chiffres non supportée par Qt. Utiliser rgba() à la place.")

    # 2. Couleurs hex sur 3 chiffres (#RGB) → non supportées Qt
    for m in _RE_HEX3.finditer(stylesheet):
        errors.append(f"Couleur {m.group()} sur 3 chiffres non supportée par Qt. Utiliser #RRGGBB à la place.")

    # 3. Vérifie les accolades mal équilibrées
    open_br = stylesheet.count("{")
    close_br = stylesheet.count("}")
    if open_br != close_br:
        errors.append(f"Accolades déséquilibrées : {open_br} ouvertes, {close_br} fermées.")

    # 4. Vérifie les sélecteurs vides
    for m in re.finditer(r"\{\s*\}", stylesheet):
        errors.append(f"Sélecteur vide : '...{m.group()}...'")

    # 5. Vérifie les points-virgules manquants
    lines = stylesheet.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("/*") or stripped.endswith("/*"):
            continue
        if (
            ":" in stripped
            and not stripped.endswith(";")
            and not stripped.endswith("{")
            and not stripped.endswith("}")
            and not stripped.endswith(",")
        ):
            # Évite les faux positifs pour les sélecteurs
            if not stripped.startswith(".") and not stripped.startswith("#"):
                errors.append(f"Ligne {i} : point-virgule manquant — '{stripped[:60]}'")
                break  # un seul par ligne suffit

    return errors


# ── Widget d'affichage des propriétés ──────────────────────────────────────


class _PropertyPanel(QWidget):
    """Panneau affichant les propriétés d'un widget sélectionné."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._current_widget: Optional[QWidget] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── Tabs ──────────────────────────────────────────────────────────
        self._tabs = QTabWidget()

        # Tab 1 : Identité & Géométrie
        self._info_widget = QWidget()
        info_layout = QVBoxLayout(self._info_widget)
        self._info_text = QTextEdit()
        self._info_text.setReadOnly(True)
        self._info_text.setObjectName("_devtool_info")
        info_layout.addWidget(self._info_text)
        self._tabs.addTab(self._info_widget, "Propriétés")

        # Tab 2 : Stylesheet brut
        self._qss_widget = QWidget()
        qss_layout = QVBoxLayout(self._qss_widget)
        self._qss_text = QTextEdit()
        self._qss_text.setReadOnly(True)
        self._qss_text.setObjectName("_devtool_qss")
        qss_layout.addWidget(self._qss_text)
        self._tabs.addTab(self._qss_widget, "Stylesheet")

        # Tab 3 : Validation QSS
        self._validation_widget = QWidget()
        val_layout = QVBoxLayout(self._validation_widget)
        self._validation_list = QListWidget()
        self._validation_list.setObjectName("_devtool_validation")
        val_layout.addWidget(self._validation_list)
        self._tabs.addTab(self._validation_widget, "Validation")

        layout.addWidget(self._tabs)

        # Style du panneau
        self.setMinimumWidth(360)
        self._apply_style()

    def _apply_style(self) -> None:
        """Applique un style sobre au panneau."""
        self.setStyleSheet(
            "QTextEdit#_devtool_info, QTextEdit#_devtool_qss {"
            "  background: #1e1e2e;"
            "  color: #cdd6f4;"
            "  font-family: 'Consolas', 'Courier New', monospace;"
            "  font-size: 12px;"
            "  padding: 8px;"
            "  border: none;"
            "}"
            "QListWidget#_devtool_validation {"
            "  background: #1e1e2e;"
            "  color: #cdd6f4;"
            "  font-family: 'Consolas', 'Courier New', monospace;"
            "  font-size: 12px;"
            "  border: none;"
            "}"
            "QTabWidget::pane {"
            "  border: 1px solid #313244;"
            "  background: #1e1e2e;"
            "}"
            "QTabBar::tab {"
            "  background: #181825;"
            "  color: #6c7086;"
            "  padding: 6px 14px;"
            "  border: 1px solid #313244;"
            "  border-bottom: none;"
            "  border-top-left-radius: 4px;"
            "  border-top-right-radius: 4px;"
            "}"
            "QTabBar::tab:selected {"
            "  background: #1e1e2e;"
            "  color: #cdd6f4;"
            "  border-bottom: 1px solid #1e1e2e;"
            "}"
        )

    def inspect(self, widget: QWidget) -> None:
        """Affiche les propriétés du widget donné."""
        self._current_widget = widget
        path = _widget_path(widget)

        # ── Info ──────────────────────────────────────────────────────────
        geo = widget.geometry()
        min_s = widget.minimumSize()
        max_s = widget.maximumSize()
        size_policy_h = (
            widget.sizePolicy().horizontalPolicy().name
            if hasattr(widget.sizePolicy().horizontalPolicy(), "name")
            else str(widget.sizePolicy().horizontalPolicy())
        )
        size_policy_v = (
            widget.sizePolicy().verticalPolicy().name
            if hasattr(widget.sizePolicy().verticalPolicy(), "name")
            else str(widget.sizePolicy().verticalPolicy())
        )

        info_lines = [
            f"Classe        : {widget.__class__.__name__}",
            f'objectName    : "{widget.objectName()}"',
            f"Chemin        : {path}",
            "",
            "─ Géométrie ─────────────────────",
            f"  x={geo.x()}, y={geo.y()}, w={geo.width()}, h={geo.height()}",
            f"  Min          : {min_s.width()}×{min_s.height()}",
            f"  Max          : {max_s.width()}×{max_s.height()}",
            f"  Visible      : {'Oui' if widget.isVisible() else 'Non'}",
            f"  Enabled      : {'Oui' if widget.isEnabled() else 'Non'}",
            "",
            "─ Taille & Police ──────────────",
            f"  Taille pol.  : {widget.font().pointSize()}pt",
            f"  Gras         : {'Oui' if widget.font().bold() else 'Non'}",
            f"  SizePolicy H : {size_policy_h}",
            f"  SizePolicy V : {size_policy_v}",
        ]

        # Ajoute le parent s'il existe
        parent = widget.parentWidget()
        if parent is not None:
            info_lines.extend(
                [
                    "",
                    "─ Parent ────────────────────────",
                    f"  {_widget_label(parent)}",
                ]
            )

        self._info_text.setPlainText("\n".join(info_lines))

        # ── Collecte TOUS les stylesheets (local + parents + QApplication) ─
        style_chains: list[tuple[str, QWidget]] = []  # (stylesheet, widget_source)
        seen: set[int] = set()  # évite les doublons si même objet

        # Stylesheet local
        local_ss = widget.styleSheet()
        if local_ss:
            style_chains.append((local_ss, widget))
            seen.add(hash(local_ss))

        # Stylesheets des parents
        cur: QWidget | None = widget.parentWidget()
        while cur is not None:
            ss = cur.styleSheet()
            if ss and hash(ss) not in seen:
                style_chains.append((ss, cur))
                seen.add(hash(ss))
            cur = cur.parentWidget()

        # Stylesheet global QApplication
        qapp = QApplication.instance()
        if qapp is not None:
            global_ss = qapp.styleSheet()
            if global_ss and hash(global_ss) not in seen:
                style_chains.append((global_ss, qapp))
                seen.add(hash(global_ss))

        # ── Stylesheet (onglet) ───────────────────────────────────────────
        if style_chains:
            ss_parts: list[str] = []
            for ss, src in style_chains:
                label = _widget_label(src)
                ss_parts.append(f"/* ── {label} ──────────────────── */")
                ss_parts.append(ss)
            self._qss_text.setPlainText("\n".join(ss_parts))
        else:
            self._qss_text.setPlainText("(aucun stylesheet local ni hérité)")

        # ── Validation de TOUS les stylesheets collectés ─────────────────
        self._validation_list.clear()

        # En-tête : quel widget est inspecté
        header_item = QListWidgetItem(f"▸ {_widget_label(widget)}")
        header_item.setFlags(header_item.flags() & ~Qt.ItemIsSelectable)
        header_item.setForeground(QColor("#89b4fa"))  # bleu clair
        self._validation_list.addItem(header_item)

        any_errors = False
        for ss, src in style_chains:
            errs = _qss_errors(ss)
            if errs:
                any_errors = True
                label = _widget_label(src)
                # En-tête de provenance
                head = QListWidgetItem(f"── {label} ──")
                head.setFlags(head.flags() & ~Qt.ItemIsSelectable)
                head.setForeground(QColor("#a6adc8"))  # gris
                self._validation_list.addItem(head)
                for err in errs:
                    item = QListWidgetItem(f"  ⚠ {err}")
                    item.setForeground(QColor("#f9e2af"))  # jaune
                    self._validation_list.addItem(item)

        if not any_errors:
            if style_chains:
                item = QListWidgetItem("  ✓ Aucune erreur détectée (local + hérités)")
            else:
                item = QListWidgetItem("  ℹ Aucun stylesheet à valider")
            item.setForeground(QColor("#a6e3a1"))
            self._validation_list.addItem(item)

        # Reste sur l'onglet actif (laisse l'utilisateur choisir)


# ── Widget arbre des widgets ───────────────────────────────────────────────


class _WidgetTree(QTreeWidget):
    """Arbre hiérarchique des widgets de l'application."""

    widget_item_map: dict[int, QTreeWidgetItem] = {}

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setHeaderLabels(["Widget", "Classe"])
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.setAnimated(True)
        self.setIndentation(16)
        self.setAlternatingRowColors(True)
        self.itemClicked.connect(self._on_item_clicked)

        self._on_select: Optional[callable] = None

    def _on_item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        """Notifie le parent qu'un widget a été sélectionné."""
        widget_id = item.data(0, Qt.UserRole)
        if widget_id is not None and self._on_select:
            self._on_select(widget_id)

    def on_select(self, callback: callable) -> None:
        self._on_select = callback

    def rebuild(self, root: QWidget) -> None:
        """Reconstruit l'arbre à partir du widget racine."""
        self.clear()
        self.widget_item_map.clear()
        self._build_node(root, None)

    def _build_node(self, widget: QWidget, parent_item: Optional[QTreeWidgetItem]) -> None:
        """Ajoute récursivement un widget et ses enfants à l'arbre."""
        item = QTreeWidgetItem()
        item.setText(0, _widget_label(widget))
        item.setText(1, widget.__class__.__name__)
        item.setData(0, Qt.UserRole, id(widget))

        # Icône de type (simulée par du texte)
        item.setToolTip(0, _widget_path(widget))

        if parent_item is not None:
            parent_item.addChild(item)
        else:
            self.addTopLevelItem(item)

        self.widget_item_map[id(widget)] = item

        # Enfants directs
        for child in widget.children():
            if isinstance(child, QWidget) and not child.isHidden():
                self._build_node(child, item)

        # Si le nœud a des enfants, on l'expand par défaut (limité à 2 niveaux)
        if item.childCount() > 0:
            depth = self._depth(item)
            if depth < 2:
                item.setExpanded(True)

    @staticmethod
    def _depth(item: QTreeWidgetItem) -> int:
        d = 0
        p = item.parent()
        while p is not None:
            d += 1
            p = p.parent()
        return d

    def select_widget(self, widget: QWidget) -> None:
        """Sélectionne le nœud correspondant au widget dans l'arbre."""
        item = self.widget_item_map.get(id(widget))
        if item is not None:
            self.setCurrentItem(item)
            self.scrollToItem(item)
            # Déplie les parents
            p = item.parent()
            while p is not None:
                p.setExpanded(True)
                p = p.parent()

    def set_search_filter(self, query: str) -> None:
        if not query:
            root = self.invisibleRootItem()
            for i in range(root.childCount()):
                self._apply_visibility_recursive(root.child(i), True)
            return
        query = query.lower()
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            self._apply_search_recursive(root.child(i), query)

    def _apply_search_recursive(self, item, query):
        match = False
        for col in range(item.columnCount()):
            if query in item.text(col).lower():
                match = True
                break
        child_match = False
        for i in range(item.childCount()):
            if self._apply_search_recursive(item.child(i), query):
                child_match = True
        visible = match or child_match
        item.setHidden(not visible)
        if match:
            item.setExpanded(True)
        return visible

    @staticmethod
    def _apply_visibility_recursive(item, visible):
        item.setHidden(not visible)
        for i in range(item.childCount()):
            _WidgetTree._apply_visibility_recursive(item.child(i), visible)


# ── Filtre d'événements pour le mode Pick ─────────────────────────────────


class _PickFilter:
    """Filtre d'événements qui capture les clics pour le mode inspection."""

    def __init__(self, on_pick: callable) -> None:
        self._on_pick = on_pick
        self._active = False

    def set_active(self, active: bool) -> None:
        self._active = active

    def event_filter(self, obj: QWidget, event: QEvent) -> bool:
        """Intercepte les clics souris pour identifier le widget cliqué."""
        if not self._active:
            return False
        if event.type() == QEvent.MouseButtonPress:
            w = QApplication.widgetAt(event.globalPosition().toPoint())
            if w is not None and w is not obj:
                self._on_pick(w)
                return True
        return False


# ── QSS Inspector principal (QDockWidget) ─────────────────────────────────


class QssInspector(QDockWidget):
    """Panneau d'inspection QSS flottant / ancrable.

    Utilisation ::
        inspector = QssInspector(main_window)
        main_window.addDockWidget(Qt.RightDockWidgetArea, inspector)
    """

    def __init__(self, main_window: QWidget, parent: Optional[QWidget] = None) -> None:
        super().__init__("QSS Inspector", parent)
        self._main_window = main_window
        self._pick_filter = _PickFilter(self._on_pick)

        # Configuration du dock
        self.setObjectName("_qss_inspector")
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        self.setMinimumWidth(420)
        self.setFeatures(
            QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable
        )

        # ── Widget central ────────────────────────────────────────────────
        central = QWidget()
        self.setWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # ── Barre d'outils ────────────────────────────────────────────────
        toolbar = QToolBar()
        toolbar.setIconSize(central.fontMetrics().boundingRect("R").size() * 5)  # fallback

        self._refresh_btn = QPushButton("🔄 Rafraîchir")
        self._refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self._refresh_btn)

        toolbar.addSeparator()

        self._pick_btn = QPushButton("🎯 Inspecter")
        self._pick_btn.setCheckable(True)
        self._pick_btn.toggled.connect(self._toggle_pick_mode)
        toolbar.addWidget(self._pick_btn)

        toolbar.addSeparator()

        self._collapse_btn = QPushButton("📋 Réduire tout")
        self._collapse_btn.clicked.connect(self._collapse_all)
        toolbar.addWidget(self._collapse_btn)

        toolbar.addSeparator()

        self._scan_btn = QPushButton("🔍 Scan All")
        self._scan_btn.clicked.connect(self.scan_all)
        toolbar.addWidget(self._scan_btn)

        toolbar.addSeparator()

        self._warn_btn = QPushButton("⚠ Qt Warnings")
        self._warn_btn.clicked.connect(self.show_qt_warnings)
        toolbar.addWidget(self._warn_btn)

        main_layout.addWidget(toolbar)
        # Barre de recherche
        self._search_bar = QLineEdit()
        self._search_bar.setPlaceholderText("Rechercher (classe, objectName, texte)...")
        self._search_bar.textChanged.connect(self._on_search)
        main_layout.addWidget(self._search_bar)

        # ── Splitter arbre + propriétés ───────────────────────────────────
        splitter = QSplitter(Qt.Vertical)

        self._widget_tree = _WidgetTree()
        self._widget_tree.on_select(self._select_by_id)
        splitter.addWidget(self._widget_tree)

        self._property_panel = _PropertyPanel()
        splitter.addWidget(self._property_panel)

        splitter.setStretchFactor(0, 3)  # arbre : 60%
        splitter.setStretchFactor(1, 2)  # propriétés : 40%

        main_layout.addWidget(splitter)

        # ── Style ─────────────────────────────────────────────────────────
        self._apply_style()

        # Installe le filtre d'événement sur le main window
        main_window.installEventFilter(self)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            "QDockWidget {"
            "  background: #11111b;"
            "  color: #cdd6f4;"
            "  border: 1px solid #313244;"
            "  titlebar-close-icon: url(none);"
            "}"
            "QDockWidget::title {"
            "  background: #181825;"
            "  padding: 6px;"
            "  font-weight: 600;"
            "}"
            "QToolBar {"
            "  background: #181825;"
            "  border: 1px solid #313244;"
            "  border-radius: 4px;"
            "  spacing: 4px;"
            "  padding: 2px;"
            "}"
            "QPushButton {"
            "  background: #313244;"
            "  color: #cdd6f4;"
            "  border: 1px solid #45475a;"
            "  border-radius: 4px;"
            "  padding: 4px 10px;"
            "  font-size: 11px;"
            "}"
            "QPushButton:hover {"
            "  background: #45475a;"
            "}"
            "QPushButton:checked {"
            "  background: #6c5ce7;"
            "  border-color: #a78bfa;"
            "  color: #ffffff;"
            "}"
            "QTreeWidget {"
            "  background: #1e1e2e;"
            "  color: #cdd6f4;"
            "  border: 1px solid #313244;"
            "  border-radius: 4px;"
            "  font-family: 'Consolas', 'Courier New', monospace;"
            "  font-size: 12px;"
            "  alternate-background-color: #181825;"
            "}"
            "QTreeWidget::item:selected {"
            "  background: #6c5ce7;"
            "  color: #ffffff;"
            "}"
            "QSplitter::handle {"
            "  background: #313244;"
            "  height: 2px;"
            "}"
        )

    def eventFilter(self, obj: QWidget, event: QEvent) -> bool:
        """Intercepte les événements pour le mode pick."""
        if event.type() == QEvent.MouseButtonPress and self._pick_filter._active:
            return self._pick_filter.event_filter(obj, event)
        return super().eventFilter(obj, event)

    # ── API publique ──────────────────────────────────────────────────────

    def show_qt_warnings(self) -> None:
        """Affiche les warnings QSS + le log des appels setStyleSheet."""
        warnings = []
        call_logs = []
        if hasattr(self._main_window, "qss_warnings"):
            warnings = self._main_window.qss_warnings  # type: ignore[attr-defined]
        if hasattr(self._main_window, "qss_call_logs"):
            call_logs = self._main_window.qss_call_logs  # type: ignore[attr-defined]

        if not warnings and not call_logs:
            QMessageBox.information(
                self, "Qt Warnings", "Aucun warning Qt ni appel setStyleSheet capturé depuis le lancement."
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"⚠ {len(warnings)} warning(s) Qt — {len(call_logs)} appel(s) setStyleSheet")
        dialog.resize(820, 580)
        layout = QVBoxLayout(dialog)

        # ── Légende ──────────────────────────────────────────────────
        legend = QLabel(
            f"Qt a émis {len(warnings)} warning(s) 'Could not parse stylesheet'.\n"
            f"{len(call_logs)} appel(s) à setStyleSheet ont été interceptés "
            "avec leur pile d'appels.\n"
            "↓ Cherche dans la colonne 'Stylesheet' ce qui pourrait être invalide "
            "pour Qt."
        )
        legend.setWordWrap(True)
        legend.setStyleSheet("color: #f9e2af; padding: 8px;")
        layout.addWidget(legend)

        # ── Tabs : Warnings Qt + Call Log ────────────────────────────
        tabs = QTabWidget()

        # Tab 1 : Warnings Qt
        warn_widget = QWidget()
        warn_layout = QVBoxLayout(warn_widget)
        warn_text = QTextEdit()
        warn_text.setReadOnly(True)
        warn_text.setStyleSheet(
            "QTextEdit {"
            "  background: #1e1e2e; color: #f9e2af;"
            "  font-family: 'Consolas', 'Courier New', monospace;"
            "  font-size: 12px; padding: 8px;"
            "}"
        )
        warn_lines = [f"{i + 1}. {w}" for i, w in enumerate(warnings)] if warnings else ["(aucun warning)"]
        warn_text.setPlainText("\n".join(warn_lines))
        warn_layout.addWidget(warn_text)
        tabs.addTab(warn_widget, f"⚠ Qt Warnings ({len(warnings)})")

        # Tab 2 : Call Log setStyleSheet
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_text = QTextEdit()
        log_text.setReadOnly(True)
        log_text.setStyleSheet(
            "QTextEdit {"
            "  background: #1e1e2e; color: #cdd6f4;"
            "  font-family: 'Consolas', 'Courier New', monospace;"
            "  font-size: 11px; padding: 8px;"
            "}"
        )
        if call_logs:
            log_lines: list[str] = []
            for i, (cls_name, widget_id, stylesheet, stack) in enumerate(call_logs, 1):
                ss_short = stylesheet[:200].replace("\n", " ")
                log_lines.append(f"═══ #{i} — {cls_name} {widget_id} ═══")
                log_lines.append(f"  Stack : {stack}")
                log_lines.append(f"  QSS   : {ss_short}")
                if len(stylesheet) > 200:
                    log_lines.append(f"         … ({len(stylesheet)} caractères au total)")
                log_lines.append("")
            log_text.setPlainText("\n".join(log_lines))
        else:
            log_text.setPlainText("(aucun appel setStyleSheet capturé)")
        log_layout.addWidget(log_text)
        tabs.addTab(log_widget, f"📝 setStyleSheet logs ({len(call_logs)})")

        layout.addWidget(tabs)

        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec()

    def refresh(self) -> None:
        """Reconstruit l'arbre des widgets."""
        self._widget_tree.rebuild(self._main_window)
        self._select_widget(self._main_window)

    def scan_all(self) -> None:
        """Parcourt TOUS les widgets et liste ceux avec des erreurs QSS.

        Les erreurs sont groupées par source de stylesheet unique (pas de
        répétition si le même stylesheet parent impacte des centaines d'enfants).
        """
        # ── Collecte les sources de stylesheet uniques ───────────────
        # Chaque widget qui a un styleSheet() non vide est une source
        ss_sources: dict[int, tuple[str, str]] = {}  # hash -> (label, stylesheet)
        # Widgets impactés par chaque source
        ss_impact: dict[int, list[str]] = {}  # hash -> [labels des widgets impactés]

        all_widgets = [self._main_window]
        all_widgets.extend(self._main_window.findChildren(QWidget, options=Qt.FindChildrenRecursively))

        # Stylesheet QApplication (collecté une fois)
        qapp = QApplication.instance()
        if qapp is not None:
            global_ss = qapp.styleSheet()
            if global_ss:
                h = hash(global_ss)
                ss_sources[h] = ("QApplication", global_ss)
                ss_impact[h] = []

        for w in all_widgets:
            # Enregistre les widgets impactés par chaque source parente
            seen: set[int] = set()

            # Stylesheet local du widget
            local_ss = w.styleSheet()
            if local_ss:
                h = hash(local_ss)
                if h not in ss_sources:
                    ss_sources[h] = (_widget_label(w), local_ss)
                if h not in ss_impact:
                    ss_impact[h] = []
                ss_impact[h].append(_widget_label(w))
                seen.add(h)

            # Parents
            cur: QWidget | None = w.parentWidget()
            while cur is not None:
                ss = cur.styleSheet()
                if ss and hash(ss) not in seen:
                    h = hash(ss)
                    if h not in ss_sources:
                        ss_sources[h] = (_widget_label(cur), ss)
                    if h not in ss_impact:
                        ss_impact[h] = []
                    ss_impact[h].append(_widget_label(w))
                    seen.add(h)
                cur = cur.parentWidget()

            # Global (déjà enregistré)
            if qapp is not None and qapp.styleSheet():
                h = hash(qapp.styleSheet())
                if h not in seen:
                    if h not in ss_impact:
                        ss_impact[h] = []
                    ss_impact[h].append(_widget_label(w))
                    seen.add(h)

        # ── Valide chaque source unique — regex + Qt ──────────────────
        error_groups: list[tuple[str, str, list[str]]] = []  # (source_label, [widgets_impactes], [errors])
        for h, (src_label, stylesheet) in ss_sources.items():
            # 1. Notre validateur regex
            errs = _qss_errors(stylesheet)
            # 2. Validation par Qt lui-même (via widget caché)
            all_errs = list(errs)
            if hasattr(self._main_window, "qss_pinpoint_error"):
                pinpoint = self._main_window.qss_pinpoint_error(stylesheet)
                if pinpoint:
                    all_errs.append(pinpoint)
            elif hasattr(self._main_window, "qss_test_against_qt"):
                qt_errs = self._main_window.qss_test_against_qt(stylesheet)
                if qt_errs:
                    all_errs.append(f"⚠ Qt rejette ce stylesheet")

            if all_errs:
                impacted = ss_impact.get(h, [])
                error_groups.append((src_label, impacted, all_errs))

        # ── Affiche les résultats ─────────────────────────────────────
        if not error_groups:
            QMessageBox.information(
                self,
                "Scan QSS",
                "✓ Aucune erreur QSS détectée (regex + Qt) dans aucun stylesheet (local + hérité + global).",
            )
            return

        dialog = QDialog(self)
        total_widgets = sum(len(impacted) for _, impacted, _ in error_groups)
        dialog.setWindowTitle(f"⚠ {len(error_groups)} source(s) avec erreurs — {total_widgets} widget(s) impacté(s)")
        dialog.resize(700, 520)
        layout = QVBoxLayout(dialog)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setStyleSheet(
            "QTextEdit {"
            "  background: #1e1e2e; color: #cdd6f4;"
            "  font-family: 'Consolas', 'Courier New', monospace;"
            "  font-size: 12px; padding: 8px;"
            "}"
        )

        lines: list[str] = []
        for src_label, impacted, all_errs in error_groups:
            lines.append(f"═══ Source : {src_label} ═══")
            for err in all_errs:
                lines.append(f"  ⚠ {err}")
            if impacted:
                shown = impacted[:5]
                for wl in shown:
                    lines.append(f"    ◇ {wl}")
                reste = len(impacted) - 5
                if reste > 0:
                    lines.append(f"    … et {reste} autre(s) widget(s) impacté(s)")
            lines.append("")

        text.setPlainText("\n".join(lines))
        layout.addWidget(text)

        btn_layout = QHBoxLayout()
        copy_btn = QPushButton("📋 Copier")
        copy_btn.clicked.connect(
            lambda: (
                QApplication.clipboard().setText(text.toPlainText()),
                copy_btn.setText("✅ Copié !"),
            )
        )
        btn_layout.addWidget(copy_btn)
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        dialog.exec()

    def inspect_widget(self, widget: QWidget) -> None:
        """Inspecte directement un widget (sélection + propriétés)."""
        self._select_widget(widget)
        if self.isHidden():
            self.show()
        self.raise_()

    # ── Méthodes privées ──────────────────────────────────────────────────

    def _select_by_id(self, widget_id: int) -> None:
        """Sélectionne un widget par son id() Python."""
        # Cherche le widget dans les enfants du main_window
        for w in self._main_window.findChildren(QWidget, options=Qt.FindChildrenRecursively):
            if id(w) == widget_id:
                self._select_widget(w)
                return
        # Peut-être le main_window lui-même ?
        if id(self._main_window) == widget_id:
            self._select_widget(self._main_window)

    def _select_widget(self, widget: QWidget) -> None:
        """Sélectionne un widget dans l'arbre et affiche ses propriétés."""
        self._widget_tree.select_widget(widget)
        self._property_panel.inspect(widget)

    def _toggle_pick_mode(self, active: bool) -> None:
        """Active / désactive le mode inspection visuelle."""
        self._pick_filter.set_active(active)
        if active:
            QApplication.setOverrideCursor(Qt.CrossCursor)
            logger.info("Mode inspection activé — cliquez sur un widget")
        else:
            QApplication.restoreOverrideCursor()
            logger.info("Mode inspection désactivé")

    def _on_pick(self, widget: QWidget) -> None:
        """Callback quand un widget est cliqué en mode pick."""
        self._pick_btn.setChecked(False)
        self._toggle_pick_mode(False)
        self.inspect_widget(widget)

    def _collapse_all(self) -> None:  # type: ignore[name-defined]
        """Réduit tous les nœuds de l'arbre."""
        root = self._widget_tree.invisibleRootItem()
        for i in range(root.childCount()):
            self._collapse_recursive(root.child(i))

    def _on_search(self, query: str) -> None:
        """Filtre l'arbre par la requete de recherche."""
        self._widget_tree.set_search_filter(query)

    @staticmethod
    def _collapse_recursive(item: QTreeWidgetItem) -> None:
        item.setExpanded(False)
        for i in range(item.childCount()):
            QssInspector._collapse_recursive(item.child(i))
