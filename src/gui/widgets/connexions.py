"""
Widgets de connexion Soulseek.

Contient :
  - ConnexionHeaderWidget : bouton + voyant pour le header
  - ConnexionPage         : page de connexion complète pour la zone centrale
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


# ── Couleurs du voyant ──────────────────────────────────────────

_LED_OFF = "#3a3a4a"
_LED_GREEN = "#00e676"
_LED_RED = "#ff5252"


# ═════════════════════════════════════════════════════════════════
#  Header
# ═════════════════════════════════════════════════════════════════

class ConnexionHeaderWidget(QFrame):
    """Bouton 'Connexion' avec voyant lumineux pour le header."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("connexionHeader")
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Ligne 1 — voyant + label
        top = QHBoxLayout()
        top.setSpacing(6)
        top.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._led = QLabel("●")
        self._led.setObjectName("connexionLed")
        self._led.setStyleSheet(
            f"color: {_LED_OFF}; font-size: 14px; background: transparent;"
        )
        top.addWidget(self._led)

        label = QLabel("Connexion")
        label.setObjectName("connexionHeaderLabel")
        label.setStyleSheet(
            "color: #e4e4ec; font-size: 11px; font-weight: 700;"
            " background: transparent;"
        )
        top.addWidget(label)
        layout.addLayout(top)

        # Ligne 2 — état
        self._status = QLabel("Déconnecté")
        self._status.setObjectName("connexionHeaderStatus")
        self._status.setStyleSheet(
            "color: #5a5a6a; font-size: 10px; background: transparent;"
        )
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status)

    # ── API publique ────────────────────────────────────────────

    def set_status(self, connected: bool) -> None:
        """Met à jour le voyant et le texte de statut."""
        if connected:
            self._led.setStyleSheet(
                f"color: {_LED_GREEN}; font-size: 14px; background: transparent;"
            )
            self._status.setText("Connecté")
            self._status.setStyleSheet(
                "color: #00e676; font-size: 10px; background: transparent;"
            )
        else:
            self._led.setStyleSheet(
                f"color: {_LED_RED}; font-size: 14px; background: transparent;"
            )
            self._status.setText("Déconnecté")
            self._status.setStyleSheet(
                "color: #5a5a6a; font-size: 10px; background: transparent;"
            )

    # ── Événements ──────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        self.clicked.emit()
        super().mousePressEvent(event)


# ═════════════════════════════════════════════════════════════════
#  Page de connexion (zone centrale)
# ═════════════════════════════════════════════════════════════════

class ConnexionPage(QFrame):
    """Page de connexion Soulseek avec formulaire et génération."""

    login_requested = Signal(str, str)   # (username, password)
    generate_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("connexionPage")
        self.setFrameShape(QFrame.NoFrame)

        # ── Layout principal ──
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Carte centrale
        card = QFrame()
        card.setObjectName("connexionCard")
        card.setFixedWidth(380)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        # ── Titre ──
        title = QLabel("Connexion Soulseek")
        title.setStyleSheet(
            "color: #6c5ce7; font-size: 18px; font-weight: 700;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        # ── Voyant de connexion ──
        status_row = QHBoxLayout()
        status_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_row.setSpacing(6)

        self._page_led = QLabel("●")
        self._page_led.setStyleSheet(
            f"color: {_LED_OFF}; font-size: 16px; background: transparent;"
        )
        status_row.addWidget(self._page_led)

        self._page_status = QLabel("Déconnecté")
        self._page_status.setStyleSheet(
            "color: #5a5a6a; font-size: 13px; font-weight: 600;"
        )
        status_row.addWidget(self._page_status)
        lay.addLayout(status_row)

        # ── Séparateur ──
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet("color: #2e2e3a;")
        lay.addWidget(sep1)

        # ── Formulaire ──
        self._username = QLineEdit()
        self._username.setObjectName("connexionInput")
        self._username.setPlaceholderText("Nom d'utilisateur")
        lay.addWidget(self._username)

        self._password = QLineEdit()
        self._password.setObjectName("connexionInput")
        self._password.setPlaceholderText("Mot de passe")
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        lay.addWidget(self._password)

        # ── Bouton connexion ──
        self._login_btn = QPushButton("Se connecter")
        self._login_btn.setObjectName("connexionBtn")
        self._login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._login_btn.clicked.connect(self._on_login)
        lay.addWidget(self._login_btn)

        # ── Séparateur + section nouveau compte ──
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("color: #2e2e3a;")
        lay.addWidget(sep2)

        new_label = QLabel("Nouveau sur Soulseek ?")
        new_label.setStyleSheet(
            "color: #8a8a9a; font-size: 12px; font-weight: 600;"
        )
        new_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(new_label)

        info = QLabel(
            "Générez un identifiant et un mot de passe "
            "pour créer votre compte sans pré-inscription."
        )
        info.setStyleSheet("color: #5a5a6a; font-size: 11px;")
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(info)

        self._generate_btn = QPushButton("Générer un compte")
        self._generate_btn.setObjectName("connexionBtnSecondary")
        self._generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._generate_btn.clicked.connect(self._on_generate)
        lay.addWidget(self._generate_btn)

        # ── Message ──
        self._message = QLabel("")
        self._message.setObjectName("connexionMessage")
        self._message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message.setWordWrap(True)
        lay.addWidget(self._message)

        outer.addWidget(card, 0, Qt.AlignmentFlag.AlignCenter)

    # ── API publique ────────────────────────────────────────────

    def set_connected(self, username: str | None = None) -> None:
        """Passe l'affichage en mode connecté."""
        self._page_led.setStyleSheet(
            f"color: {_LED_GREEN}; font-size: 16px; background: transparent;"
        )
        if username:
            self._page_status.setText(f"Connecté : {username}")
        else:
            self._page_status.setText("Connecté")
        self._page_status.setStyleSheet(
            "color: #00e676; font-size: 13px; font-weight: 600;"
        )
        self._username.setEnabled(False)
        self._password.setEnabled(False)
        self._login_btn.setEnabled(False)
        self._generate_btn.setEnabled(False)
        self._set_message("", "")

    def set_disconnected(self) -> None:
        """Passe l'affichage en mode déconnecté."""
        self._page_led.setStyleSheet(
            f"color: {_LED_RED}; font-size: 16px; background: transparent;"
        )
        self._page_status.setText("Déconnecté")
        self._page_status.setStyleSheet(
            "color: #5a5a6a; font-size: 13px; font-weight: 600;"
        )
        self._username.setEnabled(True)
        self._password.setEnabled(True)
        self._login_btn.setEnabled(True)
        self._generate_btn.setEnabled(True)

    def set_generating(self, in_progress: bool) -> None:
        """Désactive le formulaire pendant la génération de compte."""
        self._username.setEnabled(not in_progress)
        self._password.setEnabled(not in_progress)
        self._login_btn.setEnabled(not in_progress)
        self._generate_btn.setEnabled(not in_progress)
        if in_progress:
            self._page_led.setStyleSheet(
                "color: #ffab00; font-size: 16px; background: transparent;"
            )
            self._set_message("Génération du compte...", "#ffab00")
        else:
            self._page_led.setStyleSheet(
                "color: #ff5252; font-size: 16px; background: transparent;"
            )
            self._set_message("", "")

    def show_error(self, msg: str) -> None:
        """Affiche un message d'erreur."""
        self._set_message(msg, "#ff5252")

    def show_success(self, msg: str) -> None:
        """Affiche un message de succès."""
        self._set_message(msg, "#00e676")

    def get_username(self) -> str:
        return self._username.text().strip()

    def get_password(self) -> str:
        return self._password.text().strip()

    # ── Interne ─────────────────────────────────────────────────

    def _set_message(self, text: str, color: str) -> None:
        self._message.setText(text)
        if text:
            self._message.setStyleSheet(
                f"color: {color}; font-size: 12px; font-weight: 600;"
            )
        self._message.setVisible(bool(text))

    def _on_login(self) -> None:
        username = self.get_username()
        password = self.get_password()
        if not username or not password:
            self.show_error("Veuillez remplir tous les champs.")
            return
        self.login_requested.emit(username, password)

    def _on_generate(self) -> None:
        self.generate_requested.emit()
