"""
Page d'accueil — affichée après connexion à Soulseek.

Contient une bannière de bienvenue, un cadre de description,
et 7 flèches animées pointant vers le footer.
"""

from __future__ import annotations

import random

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class HomePage(QWidget):
    """Page d'accueil avec bannière personnalisée et flèches animées."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("pageAccueil")

        # Contiendra les animations pour éviter le garbage collection
        self._arrow_anims: list[QPropertyAnimation] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 0)
        outer.setSpacing(0)

        # ── Bannière de bienvenue ──
        welcome = QFrame()
        welcome.setObjectName("homeWelcome")
        welcome.setStyleSheet(
            "#homeWelcome {"
            "  background: #1e1e2e; border: 1px solid #2e2e3a;"
            "  border-radius: 12px; padding: 32px;"
            "}"
        )
        wl = QVBoxLayout(welcome)
        wl.setSpacing(4)
        wl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._home_greeting = QLabel("Bienvenue sur aioslsk")
        self._home_greeting.setStyleSheet(
            "color: #e4e4ec; font-size: 22px; font-weight: 700;"
        )
        self._home_greeting.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wl.addWidget(self._home_greeting)

        self._home_subtitle = QLabel("Connecté au réseau Soulseek.")
        self._home_subtitle.setStyleSheet(
            "color: #8a8a9a; font-size: 13px;"
        )
        self._home_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wl.addWidget(self._home_subtitle)

        outer.addWidget(welcome, 0, Qt.AlignmentFlag.AlignCenter)

        # ── Cadre de description ──
        description = QFrame()
        description.setObjectName("homeDescription")
        description.setStyleSheet(
            "#homeDescription {"
            "  background: #1e1e2e; border: 1px solid #2e2e3a;"
            "  border-radius: 12px; padding: 32px;"
            "}"
        )
        dl = QVBoxLayout(description)
        dl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._home_description = QLabel(
            "Aucune description renseignée."
        )
        self._home_description.setStyleSheet(
            "color: #8a8a9a; font-size: 14px;"
        )
        self._home_description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._home_description.setWordWrap(True)
        dl.addWidget(self._home_description)

        outer.addWidget(description, 0, Qt.AlignmentFlag.AlignCenter)

        # Pousseur pour coller les flèches au bord bas
        outer.addStretch(1)

        # ── Flèches animées pointant vers le footer ──
        self._build_home_arrows(outer)

    # ── API publique ─────────────────────────────────────────────

    def set_greeting(self, username: str) -> None:
        """Met à jour le message de bienvenue pour l'utilisateur connecté."""
        self._home_greeting.setText(f"Bienvenue, {username} !")
        self._home_subtitle.setText("Connecté au réseau Soulseek.")

    def set_greeting_default(self) -> None:
        """Réinitialise le message de bienvenue (état déconnecté)."""
        self._home_greeting.setText("Bienvenue sur aioslsk")
        self._home_subtitle.setText("Connecté au réseau Soulseek.")

    # ── Flèches animées ──────────────────────────────────────────

    def _build_home_arrows(self, outer: QVBoxLayout) -> None:
        """Ajoute 5 flèches animées sous la bannière de bienvenue."""
        from PySide6.QtGui import QFont, QFontMetrics

        # Calculer la taille exacte du glyphe ↓ à 66px bold
        font = QFont()
        font.setPixelSize(66)
        font.setWeight(QFont.Weight.Bold)
        fm = QFontMetrics(font)
        text_rect = fm.boundingRect("↓")
        arrow_w = text_rect.width() + 6   # 3px de padding de chaque côté
        arrow_h = text_rect.height() + 6  # 3px de padding haut/bas

        gap = 4         # écart entre les flèches
        margin = 24      # marge gauche/droite du container

        bounce_offset = 36  # rebond en pixels

        n_arrows = 7
        container_w = margin * 2 + n_arrows * arrow_w + (n_arrows - 1) * gap
        container_h = arrow_h + 12 + bounce_offset  # espace pour le rebond
        y = 6  # padding haut fixe de 6px

        # Container (pas de layout — positionnement absolu pour animer pos)
        arrows_container = QWidget()
        arrows_container.setFixedSize(int(container_w), int(container_h))

        for i in range(n_arrows):
            arrow = QLabel("↓", arrows_container)
            arrow.setStyleSheet(
                "color: #6c5ce7; font-size: 66px; font-weight: 700;"
            )
            arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
            arrow.setFixedSize(int(arrow_w), int(arrow_h))
            x = margin + i * (arrow_w + gap)
            arrow.move(int(x), int(y))

            # Animation de rebond vertical
            start_pos = arrow.pos()
            end_pos = QPoint(start_pos.x(), start_pos.y() + 36)
            bounce = QPropertyAnimation(arrow, b"pos")  # type: ignore[arg-type]
            bounce.setDuration(600)
            bounce.setLoopCount(-1)
            bounce.setKeyValueAt(0.0, start_pos)
            bounce.setKeyValueAt(0.5, end_pos)
            bounce.setKeyValueAt(1.0, start_pos)
            bounce.setEasingCurve(QEasingCurve.Type.OutSine)

            # Animation de fondu
            effect = QGraphicsOpacityEffect(arrow)
            arrow.setGraphicsEffect(effect)
            fade = QPropertyAnimation(effect, b"opacity")  # type: ignore[arg-type]
            fade.setDuration(600)
            fade.setLoopCount(-1)
            fade.setKeyValueAt(0.0, 0.4)
            fade.setKeyValueAt(0.5, 1.0)
            fade.setKeyValueAt(1.0, 0.4)

            # Départ aléatoire pour chaque flèche (0-1400ms)
            delay = random.randint(0, 1400)
            QTimer.singleShot(delay, bounce.start)
            QTimer.singleShot(delay, fade.start)

            self._arrow_anims.extend([bounce, fade])

        outer.addWidget(arrows_container, 0, Qt.AlignmentFlag.AlignCenter)
