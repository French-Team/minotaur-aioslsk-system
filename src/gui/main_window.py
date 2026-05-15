"""
Fenêtre principale de l'interface graphique aioslsk.
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import Qt, qInstallMessageHandler
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QStatusBar,
)

from src.gui.devtool import QssInspector
from src.gui.layout.entry import LayoutEntry
from src.gui.theme import DARK_THEME
from src.gui.widgets.toast_notification import ToastNotification
from src.services.app_config import get as cfg_get
from src.services.connexion_manager import ConnexionManager
from src.services.event_bus import EventBus

logger = logging.getLogger(__name__)

# ── Buffer Qt QSS Warnings ────────────────────────────────────────────────
# Intercepte les "Could not parse stylesheet" de Qt pour diagnostic
_qt_qss_warnings: list[str] = []

# ── Log des appels setStyleSheet ───────────────────────────────────────────
# Chaque entrée : (widget_cls, widget_id, stylesheet, stack_summary)
_qss_call_log: list[tuple[str, str, str, str]] = []

# Sauvegarde du setStyleSheet original (utilisé par _qss_test_against_qt)
_qss_original_setStyleSheet = None  # sera rempli par _patch_set_style_sheet()


def _qss_test_against_qt(stylesheet: str) -> list[str]:
    """Test un stylesheet contre Qt en l'appliquant à un widget caché.

    Retourne les warnings Qt générés, ou [] si valide.
    N'utilise PAS le monkey-patch (évite la pollution du log).
    """
    from PySide6.QtWidgets import QLabel

    original = _qss_original_setStyleSheet
    if original is None:
        return ["(test Qt non disponible — monkey-patch pas encore initialisé)"]

    count_before = len(_qt_qss_warnings)
    temp = QLabel()
    try:
        original(temp, stylesheet)  # contourne le monkey-patch
    finally:
        new_warnings = _qt_qss_warnings[count_before:]
        del _qt_qss_warnings[count_before:]
        temp.deleteLater()
    return new_warnings


def _qss_test_rules_raw(rules: list[str]) -> bool:
    """Test une liste de règles QSS combinées.

    Retourne True si Qt les accepte, False si Qt les rejette.
    Nettoie les warnings de test après chaque appel.
    """
    from PySide6.QtWidgets import QLabel

    original = _qss_original_setStyleSheet
    if original is None:
        return True

    combined = "\n".join(rules)
    count_before = len(_qt_qss_warnings)
    temp = QLabel()
    try:
        original(temp, combined)
    finally:
        new_count = len(_qt_qss_warnings)
        del _qt_qss_warnings[count_before:]
        temp.deleteLater()
    return new_count == count_before


def _qss_pinpoint_error(stylesheet: str) -> str:
    """Isolation par recherche binaire : trouve exactement quelle règle
    dans le stylesheet cause l'erreur de parsing Qt.

    Retourne une chaîne descriptive, ou "" si le stylesheet est valide.
    """
    import re

    # 1. Vérifie d'abord si le stylesheet complet pose problème
    # _qss_test_against_qt() retourne [] si valide, [...] si invalide
    if not _qss_test_against_qt(stylesheet):
        return ""  # pas d'erreur

    # 2. Parse le stylesheet en déclarations individuelles
    # Enlève les commentaires
    text = re.sub(r"/\*.*?\*/", "", stylesheet, flags=re.DOTALL)

    # Détecte si le stylesheet a des sélecteurs
    if "{" not in text:
        # Pas de sélecteur → liste de déclarations simples "prop: val"
        decls = [d.strip() for d in text.split(";") if d.strip()]
    else:
        # Avec sélecteurs → extrait chaque bloc et garde le sélecteur
        decls = []
        i = 0
        while i < len(text):
            brace_open = text.find("{", i)
            if brace_open == -1:
                break
            selector = text[i:brace_open].strip()
            depth = 1
            j = brace_open + 1
            while j < len(text) and depth > 0:
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                j += 1
            props_block = text[brace_open + 1 : j - 1].strip()
            if props_block:
                for prop in props_block.split(";"):
                    prop = prop.strip()
                    if prop:
                        decls.append(f"{selector} {{ {prop} }}")
            i = j

    if not decls:
        return "(impossible de découper le stylesheet)"

    # 3. Test binaire : trouve le premier sous-ensemble qui échoue
    # Approche : trouver le premier élément problématique
    # On commence par trouver la moitié problématique
    low, high = 0, len(decls)
    while low < high:
        mid = (low + high) // 2
        # Teste la première moitié [low..mid]
        if mid > low:
            first_half = decls[low:mid]
        else:
            first_half = [decls[low]]

        # Teste la première moitié
        if not _qss_test_rules_raw(first_half):
            high = mid
        else:
            low = mid

        # Évite la boucle infinie
        if high - low == 1:
            break

    # À la fin, low pointe vers la déclaration problématique
    if low < len(decls):
        return f"Qt rejette → `{decls[low][:120]}`"

    return "(impossible d'isoler — l'erreur vient peut-être d'une combinaison de règles)"


def _patch_set_style_sheet() -> None:
    """Monkey-patch QWidget.setStyleSheet pour logguer chaque appel.

    Doit être appelé AVANT la construction des widgets.
    Sauvegarde l'original pour _qss_test_against_qt().
    """
    import traceback
    from PySide6.QtWidgets import QWidget

    global _qss_original_setStyleSheet
    original = QWidget.setStyleSheet
    _qss_original_setStyleSheet = original

    def _logged_set_style_sheet(widget: QWidget, stylesheet: str) -> None:
        cls_name = widget.__class__.__name__
        name = widget.objectName() or ""
        txt = getattr(widget, "text", lambda: "")()[:40]
        widget_id = f"{name}['{txt}']" if name and txt else name or f"'{txt}'" if txt else "(sans nom)"
        # Pile d'appels : ne filtre QUE la frame du wrapper lui-même
        stack = traceback.extract_stack()
        useful = [f for f in stack if f.name != "_logged_set_style_sheet"]
        stack_summary = " | ".join(
            f"{f.filename}:{f.lineno} {f.name}" for f in useful[-4:]
        )
        _qss_call_log.append((cls_name, widget_id, stylesheet, stack_summary))
        # Appelle l'original
        original(widget, stylesheet)

    QWidget.setStyleSheet = _logged_set_style_sheet  # type: ignore[assignment]


def _qss_warning_handler(msg_type: int, *args: object) -> None:
    """Qt message handler : capture les erreurs de stylesheet Qt."""
    if args:
        message = str(args[-1])
        if "Could not parse stylesheet" in message:
            _qt_qss_warnings.append(message)
        # Réplique le comportement par défaut (affichage stderr)
        print(f"{message}", file=sys.stderr, flush=True)


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application aioslsk."""

    def __init__(self) -> None:
        super().__init__()

        # Monkey-patch setStyleSheet pour logger tous les appels (AVANT les widgets)
        _patch_set_style_sheet()

        # Intercepte les warnings Qt "Could not parse stylesheet" dès le départ
        qInstallMessageHandler(_qss_warning_handler)

        self.setWindowTitle("aioslsk — Interface Soulseek")
        self.setMinimumSize(960, 640)
        self.resize(1100, 720)

        # Applique le thème global
        self.setStyleSheet(DARK_THEME)

        # QSS Inspector (DevTool) - Ctrl+Shift+I pour afficher
        self._qss_inspector = QssInspector(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self._qss_inspector)
        self._qss_inspector.hide()

        # ── Barre de menu ──
        self._build_menu()

        # ── Layout principal via les zones ──
        self._layout = LayoutEntry()
        self.setCentralWidget(self._layout)

        # ── Barre de statut ──
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        self._status_label = QLabel("Serveur hors ligne")
        status_bar.addWidget(self._status_label)
        self._version_label = QLabel("v0.1.0")
        status_bar.addPermanentWidget(self._version_label)

        # ── Toast Notifications (overlay des événements ERROR) ──
        self._toast = ToastNotification(self)
        self._toast.raise_()
        self._connect_toast_events()

        # ── Gestionnaire de connexion Soulseek ──
        self._connect_connexion_manager()

    # ── Fermeture propre ────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent) -> None:
        """Arrête le gestionnaire de connexion avant de fermer."""
        logger.info("Fermeture de l'application…")
        if self._qss_inspector:
            self._qss_inspector.close()
        self._connexion_manager.shutdown()
        super().closeEvent(event)

    # ──────────────────────────────────────────
    #  Méthodes privées
    # ──────────────────────────────────────────

    def _connect_connexion_manager(self) -> None:
        """Crée et connecte le gestionnaire de connexion Soulseek."""
        self._connexion_manager = ConnexionManager(self)

        # Raccourcis vers les widgets UI
        connexion_header = self._layout.header.connexion_widget
        connexion_page = self._layout.center.connexion_page

        # UI → Manager
        connexion_page.login_requested.connect(self._connexion_manager.login)
        connexion_page.generate_requested.connect(
            self._connexion_manager.generate_account
        )

        # Manager → UI (page de connexion) — déjà géré dans les lambdas navigation ci-dessous
        self._connexion_manager.disconnected.connect(
            connexion_page.set_disconnected
        )
        self._connexion_manager.error_occurred.connect(
            connexion_page.show_error
        )
        self._connexion_manager.generating.connect(
            connexion_page.set_generating
        )

        # Manager → UI (header + footer + navigation)
        header = self._layout.header
        footer = self._layout.footer
        left = self._layout.left
        self._connexion_manager.connected.connect(
            lambda username: (
                header.setVisible(True),
                footer.setVisible(True),
                setattr(left, "home_button_visible", True),
                connexion_header.set_username(username),
                connexion_header.set_photo(
                    cfg_get("general.photo_profil")  # type: ignore[arg-type]
                ),
            )
        )
        self._connexion_manager.disconnected.connect(
            lambda: (
                header.setVisible(False),
                footer.setVisible(False),
                setattr(left, "home_button_visible", False),
            )
        )

        # Manager → barre de statut
        self._connexion_manager.status_changed.connect(
            self._status_label.setText
        )

        # Navigation automatique : connexion → accueil, déconnexion → connexion
        center = self._layout.center
        self._connexion_manager.connected.connect(
            lambda username: (
                connexion_page.set_connected(username),
                center.show_home(username),
            )
        )
        self._connexion_manager.disconnected.connect(
            lambda: center.show_connexion()
        )

        # Bouton "Se déconnecter" de la page de connexion
        connexion_page.disconnect_requested.connect(
            self._connexion_manager.disconnect
        )

        # Transmettre le gestionnaire aux bots (Recherche, etc.)
        center.set_connexion_manager(self._connexion_manager)

    def _connect_toast_events(self) -> None:
        """Connecte les événements ERROR/WARN de l'EventBus aux toasts."""
        EventBus().event_emitted.connect(self._on_toast_event)

    def _on_toast_event(self, event: object) -> None:
        """Affiche une notification toast pour les événements ERROR et WARN."""
        severity = getattr(event, 'severity', '')
        if severity not in ("ERROR", "WARN"):
            return
        title = getattr(event, 'title', '')
        message = getattr(event, 'message', '')
        self._toast.show_toast(severity, title, message)

    def _build_menu(self) -> None:
        """Construit la barre de menus."""
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&Fichier")
        quit_action = QAction("&Quitter", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(QApplication.instance().quit)
        file_menu.addAction(quit_action)

        # Menu Outils — QSS Inspector
        tools_menu = menubar.addMenu("&Outils")
        inspect_action = QAction("QSS Inspector", self)
        inspect_action.setShortcut("Ctrl+Shift+I")
        inspect_action.setCheckable(True)
        inspect_action.toggled.connect(self._toggle_inspector)
        tools_menu.addAction(inspect_action)


        help_menu = menubar.addMenu("&Aide")
        about_action = QAction("À &propos", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _show_about(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.about(
            self,
            "À propos — aioslsk",
            "<b>aioslsk</b><br><br>"
            "Interface graphique pour le client Soulseek aioslsk.<br><br>"
            "Version 0.1.0<br>"
            "Basé sur PySide6 et aioslsk.",
        )

    
    # ── DevTool ──────────────────────────────────────────

    def _toggle_inspector(self, visible: bool) -> None:
        """Affiche ou cache le QSS Inspector."""
        if visible:
            self._qss_inspector.refresh()
            self._qss_inspector.show()
            self._qss_inspector.raise_()
        else:
            self._qss_inspector.hide()

    @property
    def qss_warnings(self) -> list[str]:
        """Retourne les warnings QSS capturés par Qt."""
        return _qt_qss_warnings.copy()

    @property
    def qss_call_logs(self) -> list[tuple[str, str, str, str]]:
        """Retourne le log des appels setStyleSheet."""
        return _qss_call_log.copy()

    @property
    def qss_test_against_qt(self):
        """Retourne la fonction de test QSS contre Qt."""
        return _qss_test_against_qt

    @property
    def qss_pinpoint_error(self):
        """Retourne la fonction d'isolation d'erreur QSS par recherche binaire."""
        return _qss_pinpoint_error


# ──────────────────────────────────────────
    #  API publique — accès aux zones
    # ──────────────────────────────────────────

    @property
    def header(self):
        return self._layout.header

    @property
    def left(self):
        return self._layout.left

    @property
    def center(self):
        return self._layout.center

    @property
    def right(self):
        return self._layout.right

    @property
    def footer(self):
        return self._layout.footer
