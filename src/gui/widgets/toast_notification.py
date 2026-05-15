"""
ToastNotification — Notifications flottantes pour les événements EventBus.

Affiche des popups temporaires pour les événements de type ERROR,
positionnés en haut à droite de la fenêtre, avec auto-disparition.
"""

import logging

from PySide6.QtCore import QPropertyAnimation, QPoint, Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

# ── Couleurs par sévérité ────────────────────────────────────────────────

_SEVERITY_COLORS: dict[str, tuple[str, str]] = {
    "ERROR": ("#e74c3c", "#ffffff"),  # rouge, texte blanc
    "WARN":  ("#f39c12", "#ffffff"),  # orange, texte blanc
    "INFO":  ("#3498db", "#ffffff"),  # bleu, texte blanc
}

_TOAST_DURATION_MS = 4000      # 4 secondes avant disparition
_FADE_DURATION_MS = 300        # durée du fade in/out
_TOAST_SPACING = 8             # espacement entre toasts
_TOAST_MARGIN = 16             # marge depuis le bord
_MAX_TOASTS = 5                # nombre max de toasts simultanés


class _ToastCard(QFrame):
    """Carte de notification individuelle."""

    def __init__(self, severity: str, title: str, message: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._severity = severity
        self._title = title
        self.setObjectName("ToastCard")
        self.setFixedWidth(340)

        bg_color, text_color = _SEVERITY_COLORS.get(severity, ("#555555", "#ffffff"))

        # Layout horizontal : icône + texte
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Icône de sévérité
        icon_map = {"ERROR": "❌", "WARN": "⚠️", "INFO": "ℹ️"}
        icon = QLabel(icon_map.get(severity, "●"))
        icon.setStyleSheet(f"font-size: 16px; color: {text_color};")
        layout.addWidget(icon)

        # Texte
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-weight: 700; font-size: 13px; color: {text_color};
        """)
        text_layout.addWidget(title_label)

        if message:
            msg_label = QLabel(message[:80])
            msg_label.setStyleSheet(f"font-size: 11px; color: {text_color};")
            msg_label.setWordWrap(True)
            text_layout.addWidget(msg_label)

        layout.addLayout(text_layout, 1)

        # Style du fond
        self.setStyleSheet(f"""
            _ToastCard {{
                background-color: {bg_color};
                border-radius: 8px;
            }}
        """)

        self.setGraphicsEffect(None)
        self._opacity = 1.0

    def set_card_opacity(self, value: float) -> None:
        """Modifie l'opacité (0.0–1.0) de la carte."""
        self._opacity = max(0.0, min(1.0, value))
        style = self.styleSheet()
        # On utilise un QGraphicsOpacityEffect
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(self._opacity)
        self.setGraphicsEffect(effect)


class ToastNotification(QWidget):
    """Overlay de notifications toast, positionné en haut à droite de la fenêtre."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ToastNotification")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Layout vertical (les toasts s'empilent du haut vers le bas)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, _TOAST_MARGIN, _TOAST_MARGIN, 0)
        self._layout.setSpacing(_TOAST_SPACING)
        self._layout.setAlignment(Qt.AlignTop | Qt.AlignRight)

        self._toasts: list[_ToastCard] = []
        self.setVisible(False)
        self._parent = parent

    def show_toast(self, severity: str, title: str, message: str = "") -> None:
        """Affiche une notification toast."""
        # Limiter le nombre de toasts
        while len(self._toasts) >= _MAX_TOASTS:
            old = self._toasts.pop(0)
            self._layout.removeWidget(old)
            old.deleteLater()

        card = _ToastCard(severity, title, message, self)
        self._toasts.append(card)
        self._layout.addWidget(card)
        self.setVisible(True)

        # Ajuster la position : ancré en haut à droite du parent
        self._reposition()

        # Auto-disparition après délai
        QTimer.singleShot(_TOAST_DURATION_MS, lambda: self._remove_toast(card))

    def _remove_toast(self, card: _ToastCard) -> None:
        """Supprime une carte avec fondu."""
        if card not in self._toasts:
            return
        self._toasts.remove(card)
        self._layout.removeWidget(card)
        card.deleteLater()

        if not self._toasts:
            self.setVisible(False)

    def _reposition(self) -> None:
        """Repositionne l'overlay en haut à droite du parent."""
        if self._parent:
            parent_rect = self._parent.rect()
            self.setGeometry(
                parent_rect.width() - self.sizeHint().width() - _TOAST_MARGIN,
                0,
                self.sizeHint().width(),
                parent_rect.height(),
            )
