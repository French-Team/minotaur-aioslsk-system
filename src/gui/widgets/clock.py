"""
Widget Horloge numérique — affiche l'heure au format hh:mm:ss.

Peut être utilisé pour programmer des actions ultérieurement.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QTime, QTimer, Signal

logger = logging.getLogger("[CLOCK]")

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget


class ClockWidget(QFrame):
    """Horloge numérique avec mise à jour chaque seconde."""

    # Signal émis à chaque seconde avec l'heure courante (hh:mm:ss)
    tick = Signal(str)

    _FMT = "HH:mm:ss"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("clockWidget")
        # pyrefly: ignore [missing-attribute]
        self.setFrameShape(QFrame.NoFrame)

        # ── Layout centré ──
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── Affichage ──
        self._label = QLabel("00:00:00")
        self._label.setObjectName("clockLabel")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label)

        # ── Timer ──
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_time)
        self._timer.start(1000)  # chaque seconde

        # Première mise à jour immédiate
        self._update_time()

    # ── API publique ─────────────────────────────────────────────

    @property
    def time_string(self) -> str:
        """Heure courante au format hh:mm:ss."""
        return self._label.text()

    def get_time(self) -> str:
        """Retourne l'heure courante (alias public)."""
        return self.time_string

    def set_display_format(self, fmt: str) -> None:
        """Change le format d'affichage (standard Qt : 'HH:mm:ss')."""
        self._FMT = fmt
        self._update_time()

    def start(self) -> None:
        """Démarre le timer (automatique à la création)."""
        if not self._timer.isActive():
            self._timer.start(1000)

    def stop(self) -> None:
        """Arrête le timer."""
        self._timer.stop()

    # ── Interne ─────────────────────────────────────────────────

    def _update_time(self) -> None:
        now = QTime.currentTime()
        text = now.toString(self._FMT)
        self._label.setText(text)
        self.tick.emit(text)
