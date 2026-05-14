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
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
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
    """Widget header : avatar, username, statut et bouton déconnexion."""

    clicked = Signal()
    disconnect_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("connexionHeader")
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Largeur = contenu, pas d'étalement
        policy = self.sizePolicy()
        policy.setHorizontalPolicy(QSizePolicy.Maximum)
        self.setSizePolicy(policy)

        grid = QGridLayout(self)
        grid.setContentsMargins(8, 4, 8, 14)  # bottom = 14 pour ombre avatar
        grid.setSpacing(4)

        # ── Colonne 0 : Avatar ou initiale ──
        self._avatar = QLabel()
        self._avatar.setObjectName("headerAvatar")
        self._avatar.setFixedSize(36, 36)
        self._avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Ombre portée légère (parent = avatar pour éviter la destruction)
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self._avatar)
        shadow.setBlurRadius(8)
        shadow.setOffset(0, 1)
        shadow.setColor(Qt.GlobalColor.black)
        self._avatar.setGraphicsEffect(shadow)
        grid.addWidget(self._avatar, 0, 0, 2, 1)  # row 0-1, col 0

        # ── Colonnes 1-2, ligne 0 : Username centré sur la largeur statut+déconnexion ──
        self._username_label = QLabel("Déconnecté")
        self._username_label.setObjectName("headerUsername")
        self._username_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self._username_label, 0, 1, 1, 2)

        # ── Colonne 1, ligne 1 : Statut (badge QFrame) ──
        self._badge = QFrame()
        self._badge.setObjectName("headerStatusBadge")
        badge_layout = QHBoxLayout(self._badge)
        badge_layout.setContentsMargins(6, 2, 6, 2)
        badge_layout.setSpacing(0)
        self._status = QLabel("● Déconnecté")
        self._status.setObjectName("headerStatus")
        badge_layout.addWidget(self._status)
        grid.addWidget(self._badge, 1, 1)

        # ── Colonne 2, ligne 1 : Se déconnecter ──
        self._disconnect_btn = QPushButton("Se déconnecter")
        self._disconnect_btn.setObjectName("headerDisconnectBtn")
        self._disconnect_btn.setFlat(True)
        self._disconnect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._disconnect_btn.clicked.connect(self._on_disconnect)
        self._disconnect_btn.setVisible(False)
        grid.addWidget(self._disconnect_btn, 1, 2)

        # Pas de stretch — taille naturelle
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 0)
        grid.setColumnStretch(2, 0)

    # ── API publique ────────────────────────────────────────────

    def set_username(self, username: str) -> None:
        """Définit le nom d'utilisateur affiché et l'initiale dans l'avatar."""
        self._username_label.setText(username)
        # Initiale dans l'avatar (si pas de photo chargée)
        initial = username[0].upper() if username else "?"
        self._avatar.setText(initial)
        self._avatar.setStyleSheet(
            "background-color: #6c5ce7; color: #ffffff;"
            " font-weight: 700; font-size: 15px; border-radius: 18px;"
            " border: 2px solid #2e2e3a;"
            " min-width: 36px; min-height: 36px;"
        )

    def set_status(self, connected: bool) -> None:
        """Met à jour le statut (badge) et la visibilité du bouton déconnexion."""
        if connected:
            self._status.setText("● Connecté")
            self._status.setStyleSheet(
                "color: #00e676; font-size: 11px; font-weight: 600;"
                " background: transparent;"
            )
            self._badge.setStyleSheet(
                "background-color: #00e67618;"
                " border: 1px solid #00e67630;"
                " border-radius: 10px;"
            )
            self._disconnect_btn.setVisible(True)
        else:
            self._status.setText("● Déconnecté")
            self._status.setStyleSheet(
                "color: #5a5a6a; font-size: 11px; font-weight: 600;"
                " background: transparent;"
            )
            self._badge.setStyleSheet(
                "background-color: #5a5a6a18;"
                " border: 1px solid #5a5a6a30;"
                " border-radius: 10px;"
            )
            self._disconnect_btn.setVisible(False)
            self._username_label.setText("Déconnecté")
            self._avatar.clear()
            self._avatar.setStyleSheet("")

    def set_photo(self, path: str) -> None:
        """Charge une photo de profil circulaire depuis un chemin fichier."""
        if not path:
            return
        from PySide6.QtGui import QPixmap, QPainter, QPainterPath
        pix = QPixmap(path)
        if not pix.isNull():
            # Agrandir pour remplir le cercle (cover), puis rogner
            scaled = pix.scaled(
                36, 36,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            # Pixmap cible transparent
            rounded = QPixmap(36, 36)
            rounded.fill(Qt.GlobalColor.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addEllipse(0, 0, 36, 36)
            painter.setClipPath(path)
            # Centrer l'image dans le cercle
            x = (36 - scaled.width()) // 2
            y = (36 - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            painter.end()
            self._avatar.setPixmap(rounded)
            self._avatar.setStyleSheet("")  # plus besoin de border-radius

    # ── Événements ──────────────────────────────────────────────

    def _on_disconnect(self) -> None:
        self.disconnect_requested.emit()

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
    disconnect_requested = Signal()

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
        self._sep2 = QFrame()
        self._sep2.setFrameShape(QFrame.HLine)
        self._sep2.setStyleSheet("color: #2e2e3a;")
        lay.addWidget(self._sep2)

        self._new_label = QLabel("Nouveau sur Soulseek ?")
        self._new_label.setStyleSheet(
            "color: #8a8a9a; font-size: 12px; font-weight: 600;"
        )
        self._new_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._new_label)

        self._info_new = QLabel(
            "Générez un identifiant et un mot de passe "
            "pour créer votre compte sans pré-inscription."
        )
        self._info_new.setStyleSheet("color: #5a5a6a; font-size: 11px;")
        self._info_new.setWordWrap(True)
        self._info_new.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._info_new)

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

        # ── Bouton déconnexion (caché par défaut) ──
        self._disconnect_btn = QPushButton("Se déconnecter")
        self._disconnect_btn.setObjectName("connexionBtnDanger")
        self._disconnect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._disconnect_btn.clicked.connect(self._on_disconnect)
        self._disconnect_btn.setVisible(False)
        lay.addWidget(self._disconnect_btn)

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
        self._username.setVisible(False)
        self._password.setVisible(False)
        self._login_btn.setVisible(False)
        self._generate_btn.setVisible(False)
        self._sep2.setVisible(False)
        self._new_label.setVisible(False)
        self._info_new.setVisible(False)
        self._disconnect_btn.setVisible(True)
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
        self._username.setVisible(True)
        self._password.setVisible(True)
        self._login_btn.setVisible(True)
        self._generate_btn.setVisible(True)
        self._sep2.setVisible(True)
        self._new_label.setVisible(True)
        self._info_new.setVisible(True)
        self._disconnect_btn.setVisible(False)

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

    def _on_disconnect(self) -> None:
        self.disconnect_requested.emit()
