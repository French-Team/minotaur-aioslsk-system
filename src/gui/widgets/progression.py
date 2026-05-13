"""
Widget Progression — barre de progression multi-modes.

Modes disponibles :
  - percent  : barre de progression + pourcentage
  - num      : compteur numérique
  - seconds  : temps écoulé / restant
  - actions  : nombre d'actions effectuées
  - errors   : nombre d'erreurs
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class ProgressionWidget(QFrame):
    """Affichage multi-mode pour suivre une progression."""

    MODE_PERCENT = "percent"
    MODE_NUM = "num"
    MODE_SECONDS = "seconds"
    MODE_ACTIONS = "actions"
    MODE_ERRORS = "errors"

    _MODE_LABELS = {
        MODE_PERCENT: "📊  Progression",
        MODE_NUM: "🔢  Compteur",
        MODE_SECONDS: "⏱  Temps",
        MODE_ACTIONS: "⚡  Actions",
        MODE_ERRORS: "❌  Erreurs",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("progressionWidget")
        self.setFrameShape(QFrame.NoFrame)

        # ── Layout vertical ──
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        # Ligne du haut — indicateur de mode
        self._mode_label = QLabel("📊  Progression")
        self._mode_label.setObjectName("progressionMode")
        self._mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._mode_label)

        # Ligne du milieu — barre de progression (mode percent uniquement)
        self._progress = QProgressBar()
        self._progress.setObjectName("progressionBar")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.hide()
        layout.addWidget(self._progress)

        # Ligne du bas — valeur principale
        self._value_label = QLabel("0 %")
        self._value_label.setObjectName("progressionValue")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._value_label)

        # ── État interne ──
        self._mode: str = self.MODE_PERCENT
        self._current: float = 0.0
        self._maximum: float = 100.0
        self._errors: int = 0
        self._actions: int = 0
        self._elapsed: int = 0  # secondes

    # ── API publique ─────────────────────────────────────────────

    @property
    def mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str) -> None:
        """Change le mode d'affichage."""
        if mode not in self._MODE_LABELS:
            raise ValueError(f"Mode inconnu : {mode!r}")
        self._mode = mode
        self._mode_label.setText(self._MODE_LABELS[mode])
        self._progress.setVisible(mode == self.MODE_PERCENT)
        self._refresh_display()

    def set_value(self, current: float, maximum: float | None = None) -> None:
        """Définit la valeur courante et optionnellement le maximum."""
        self._current = current
        if maximum is not None:
            self._maximum = max(maximum, 1.0)
            self._progress.setRange(0, int(self._maximum))
        self._progress.setValue(int(self._current))
        self._refresh_display()

    def set_percentage(self, percent: float) -> None:
        """Définit directement le pourcentage (0-100)."""
        self._current = percent
        self._maximum = 100.0
        self._progress.setRange(0, 100)
        self._progress.setValue(int(percent))
        if self._mode != self.MODE_PERCENT:
            self.set_mode(self.MODE_PERCENT)
        else:
            self._refresh_display()

    def set_count(self, count: int) -> None:
        """Définit un compteur numérique (mode num)."""
        self._current = float(count)
        self._maximum = 0.0
        if self._mode != self.MODE_NUM:
            self.set_mode(self.MODE_NUM)
        else:
            self._refresh_display()

    def set_actions(self, actions: int) -> None:
        """Définit le nombre d'actions (mode actions)."""
        self._actions = actions
        if self._mode != self.MODE_ACTIONS:
            self.set_mode(self.MODE_ACTIONS)
        else:
            self._refresh_display()

    def set_errors(self, errors: int) -> None:
        """Définit le nombre d'erreurs (mode errors)."""
        self._errors = errors
        if self._mode != self.MODE_ERRORS:
            self.set_mode(self.MODE_ERRORS)
        else:
            self._refresh_display()

    def set_elapsed(self, seconds: int) -> None:
        """Définit le temps écoulé en secondes (mode seconds)."""
        self._elapsed = seconds
        if self._mode != self.MODE_SECONDS:
            self.set_mode(self.MODE_SECONDS)
        else:
            self._refresh_display()

    # ── Interne ──────────────────────────────────────────────────

    def _refresh_display(self) -> None:
        """Met à jour l'affichage selon le mode actif."""
        if self._mode == self.MODE_PERCENT:
            pct = self._current / self._maximum * 100 if self._maximum > 0 else 0.0
            self._value_label.setText(f"{pct:.0f} %")

        elif self._mode == self.MODE_NUM:
            self._value_label.setText(f"{int(self._current)}")

        elif self._mode == self.MODE_SECONDS:
            h = self._elapsed // 3600
            m = (self._elapsed % 3600) // 60
            s = self._elapsed % 60
            if h > 0:
                self._value_label.setText(f"{h}:{m:02d}:{s:02d}")
            else:
                self._value_label.setText(f"{m}:{s:02d}")

        elif self._mode == self.MODE_ACTIONS:
            self._value_label.setText(f"{self._actions} action{'s' if self._actions != 1 else ''}")

        elif self._mode == self.MODE_ERRORS:
            self._value_label.setText(f"{self._errors} erreur{'s' if self._errors != 1 else ''}")
