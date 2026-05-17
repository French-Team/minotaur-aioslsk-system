"""
Widgets pour l'affichage des clients actifs / joignables.

Composants :
  - ClientsHeaderWidget : bouton cliquable dans le header (colonne 1)
  - ClientRow : ligne individuelle d'un client (nom | statut | actions)
  - ClientsActifsHeader : en-tête listant tous les clients
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

# ── Constantes ───────────────────────────────────────────────────
_OFF = "#3a3a4a"
_GREEN = "#00e676"
_ORANGE = "#ffab00"
_RED = "#ff5252"
_GRAY = "#5a5a6a"


# ═══════════════════════════════════════════════════════════════════
#  Header — widget cliquable dans la bannière
# ═══════════════════════════════════════════════════════════════════


class ClientsHeaderWidget(QFrame):
    """Bouton cliquable dans le header — colonne 1.

    Affiche le nombre de clients actifs et joignables.
    Émet ``clicked`` au clic.
    """

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("clientsHeader")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(0)

        # Ligne 1 — titre "👥  Clients"
        self._title = QLabel("👥  Clients")
        self._title.setObjectName("clientsHeaderTitle")
        self._title.setStyleSheet("color: #6c5ce7; font-size: 11px; font-weight: 600;")
        layout.addWidget(self._title)

        # Ligne 2 — statut
        self._statut = QLabel("Actif : 0  /  Joignable : 0")
        self._statut.setObjectName("clientsHeaderStatut")
        self._statut.setStyleSheet("color: #e4e4ec; font-size: 13px; font-weight: 500;")
        layout.addWidget(self._statut)

    # ── API publique ─────────────────────────────────────────────

    def set_counts(self, actifs: int, joignables: int) -> None:
        """Met à jour les compteurs affichés."""
        self._statut.setText(f"Actif : {actifs}  /  Joignable : {joignables}")

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        self.clicked.emit()
        super().mousePressEvent(event)


# ═══════════════════════════════════════════════════════════════════
#  Ligne client
# ═══════════════════════════════════════════════════════════════════


class ClientRow(QFrame):
    """Ligne d'affichage d'un client Soulseek.

    Structure : nom du client | statut (actif/joignable) | boutons d'action
    """

    explorer_requested = Signal(str)  # nom du client
    favoris_requested = Signal(str)
    bannir_requested = Signal(str)

    def __init__(
        self,
        nom: str,
        actif: bool = True,
        joignable: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("clientRow")
        self._nom = nom

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(12)

        # ── Nom du client ──
        self._name_label = QLabel(nom)
        self._name_label.setObjectName("clientRowName")
        self._name_label.setStyleSheet("color: #e4e4ec; font-size: 13px; font-weight: 600; min-width: 160px;")
        layout.addWidget(self._name_label)

        # ── Statut (actif / joignable) ──
        self._led_actif = self._make_led(actif)
        self._label_actif = QLabel("Actif" if actif else "Inactif")
        self._label_actif.setStyleSheet(f"color: {_GREEN if actif else _GRAY}; font-size: 12px;")

        self._led_joignable = self._make_led(joignable)
        self._label_joignable = QLabel("Joignable" if joignable else "Non joignable")
        self._label_joignable.setStyleSheet(f"color: {_GREEN if joignable else _GRAY}; font-size: 12px;")

        layout.addWidget(self._led_actif)
        layout.addWidget(self._label_actif)
        layout.addSpacing(8)
        layout.addWidget(self._led_joignable)
        layout.addWidget(self._label_joignable)

        layout.addStretch(1)

        # ── Boutons d'action ──
        self._btn_explorer = self._make_action_btn("📁  Explorer", "clientsActionBtn")
        self._btn_favoris = self._make_action_btn("⭐  Favoris", "clientsActionBtn")
        self._btn_bannir = self._make_action_btn("🚫  Bannir", "clientsActionBtnDanger")

        self._btn_explorer.clicked.connect(lambda: self.explorer_requested.emit(nom))
        self._btn_favoris.clicked.connect(lambda: self.favoris_requested.emit(nom))
        self._btn_bannir.clicked.connect(lambda: self.bannir_requested.emit(nom))

        layout.addWidget(self._btn_explorer)
        layout.addWidget(self._btn_favoris)
        layout.addWidget(self._btn_bannir)

    # ── Privé ────────────────────────────────────────────────────

    @staticmethod
    def _make_led(on: bool) -> QLabel:
        led = QLabel("●")
        led.setStyleSheet(f"color: {_GREEN if on else _OFF}; font-size: 10px;")
        led.setFixedWidth(12)
        return led

    @staticmethod
    def _make_action_btn(text: str, obj_name: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName(obj_name)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    # ── API publique ─────────────────────────────────────────────

    @property
    def nom(self) -> str:
        return self._nom


# ═══════════════════════════════════════════════════════════════════
#  Page centrale — liste des clients actifs / joignables
# ═══════════════════════════════════════════════════════════════════


class ClientsActifsHeader(QFrame):
    """En-tête listant les clients actifs et joignables.

    Chaque client est affiché sur une ligne avec :
      - nom
      - statut (actif / joignable)
      - boutons d'action (explorer, favoris, bannir)
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("clientsActifsPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(0)

        # ── En-tête de page ──
        header = QLabel("Clients actifs et joignables")
        header.setStyleSheet("color: #6c5ce7; font-size: 16px; font-weight: 700; padding-bottom: 8px;")
        layout.addWidget(header)

        # Légende
        stats = QLabel("Actif : 0  •  Joignable : 0  •  Total : 0")
        stats.setObjectName("clientsStats")
        stats.setStyleSheet("color: #5a5a6a; font-size: 12px; padding-bottom: 12px;")
        layout.addWidget(stats)

        # ── Zone scrollable avec les lignes ──
        scroll = QScrollArea()
        scroll.setObjectName("clientsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self._list_container = QWidget()
        self._list_container.setObjectName("clientsListContainer")
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        self._list_layout.addStretch(1)

        scroll.setWidget(self._list_container)
        layout.addWidget(scroll)

        # Compteurs
        self._actifs = 0
        self._joignables = 0
        self._rows: list[ClientRow] = []
        self._client_states: dict[str, tuple[bool, bool]] = {}  # nom -> (actif, joignable)

    # ── API publique ─────────────────────────────────────────────

    def clear_clients(self) -> None:
        """Supprime toutes les lignes client."""
        for row in self._rows:
            self._list_layout.removeWidget(row)
            row.deleteLater()
        self._rows.clear()
        self._client_states.clear()
        self._actifs = 0
        self._joignables = 0
        self._update_stats()

    def add_client(self, nom: str, actif: bool = True, joignable: bool = True) -> None:
        """Ajoute un client à la liste."""
        row = ClientRow(nom, actif=actif, joignable=joignable)
        # Insérer avant le stretch final
        self._list_layout.insertWidget(self._list_layout.count() - 1, row)
        self._rows.append(row)
        self._client_states[nom] = (actif, joignable)

        if actif:
            self._actifs += 1
        if joignable:
            self._joignables += 1
        self._update_stats()

    def remove_client(self, nom: str) -> bool:
        """Supprime un client par son nom. Retourne True si trouvé."""
        for row in self._rows:
            if row.nom == nom:
                # Décrémenter les compteurs avant suppression
                etat = self._client_states.pop(nom, (False, False))
                if etat[0]:  # actif
                    self._actifs -= 1
                if etat[1]:  # joignable
                    self._joignables -= 1

                self._list_layout.removeWidget(row)
                self._rows.remove(row)
                row.deleteLater()
                self._update_stats()
                return True
        return False

    def client_count(self) -> int:
        return len(self._rows)

    # ── Privé ────────────────────────────────────────────────────

    def _update_stats(self) -> None:
        stats = self.findChild(QLabel, "clientsStats")
        if stats:
            stats.setText(f"Actif : {self._actifs}  •  Joignable : {self._joignables}  •  Total : {len(self._rows)}")
