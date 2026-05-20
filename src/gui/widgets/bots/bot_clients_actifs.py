"""Widget d'affichage des clients actifs (contacts Soulseek trackés).

Affiche un tableau triable avec le statut en temps réel,
connecté au ClientsActifsService.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aioslsk.user.model import UserStatus
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.theme_fragments.colors import COLORS

if TYPE_CHECKING:
    from src.services.clients_actifs_service import (
        ClientInfo,
        ClientsActifsService,
    )

logger = logging.getLogger(__name__)

# ── Couleurs (depuis la palette centralisée) ─────────────────────

_COULEUR_ONLINE = QColor(COLORS["SUCCESS"])
_COULEUR_AWAY = QColor(COLORS["WARNING"])
_COULEUR_OFFLINE = QColor(COLORS["TEXT_MUTED"])
_COULEUR_UNKNOWN = QColor(COLORS["TEXT_PLACEHOLDER"])

_TEXTE_STATUT: dict[UserStatus, str] = {
    UserStatus.ONLINE: "Actif",
    UserStatus.AWAY: "Joignable",
    UserStatus.OFFLINE: "Déconnecté",
    UserStatus.UNKNOWN: "Inconnu",
}

_ICONE_STATUT: dict[UserStatus, str] = {
    UserStatus.ONLINE: "🟢",
    UserStatus.AWAY: "🟡",
    UserStatus.OFFLINE: "⚫",
    UserStatus.UNKNOWN: "⚪",
}

_COULEUR_STATUT: dict[UserStatus, QColor] = {
    UserStatus.ONLINE: _COULEUR_ONLINE,
    UserStatus.AWAY: _COULEUR_AWAY,
    UserStatus.OFFLINE: _COULEUR_OFFLINE,
    UserStatus.UNKNOWN: _COULEUR_UNKNOWN,
}


# ── Items de tableau avec tri personnalisé ───────────────────────


class _StatutItem(QTableWidgetItem):
    """QTableWidgetItem qui trie par valeur UserStatus."""

    def __init__(self, statut: UserStatus, texte: str) -> None:
        super().__init__(texte)
        self._statut = statut

    def __lt__(self, other: QTableWidgetItem) -> bool:
        if isinstance(other, _StatutItem):
            return self._statut.value < other._statut.value
        return super().__lt__(other)


class _NumericItem(QTableWidgetItem):
    """QTableWidgetItem qui trie numériquement."""

    def __init__(self, valeur: int, texte: str) -> None:
        super().__init__(texte)
        self._valeur = valeur

    def __lt__(self, other: QTableWidgetItem) -> bool:
        if isinstance(other, _NumericItem):
            return self._valeur < other._valeur
        return super().__lt__(other)


# ── Widget principal ────────────────────────────────────────────


class BotClientsActifs(QFrame):
    """Page des clients actifs avec tableau triable et stats."""

    page_changed = Signal(str)
    unseen_count_changed = Signal(int)

    _COLONNES: list[tuple[str, str, int]] = [
        ("statut", "Statut", 90),
        ("username", "Utilisateur", 180),
        ("pays", "Pays", 80),
        ("vitesse", "Vitesse", 90),
        ("fichiers", "Fichiers", 90),
        ("slots", "Slots", 80),
        ("file", "File", 70),
        ("description", "Description", 200),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service: ClientsActifsService | None = None
        self._setup_done = False

        self._build_ui()

    # ── Construction UI ─────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Barre d'en-tête stats ──────────────────────────────
        self._header_bar = QFrame()
        self._header_bar.setObjectName("clientsHeaderBar")
        self._header_layout = QHBoxLayout(self._header_bar)
        self._header_layout.setContentsMargins(16, 8, 16, 8)

        self._lbl_total = QLabel("Total: —")
        self._lbl_actifs = QLabel("Actifs: —")
        self._lbl_connectes = QLabel("Connectés: —")
        self._lbl_total.setStyleSheet(f"color: {COLORS['TEXT_SECONDARY']}; font-size: 12px;")
        self._lbl_actifs.setStyleSheet(f"color: {COLORS['SUCCESS']}; font-size: 12px; font-weight: bold;")
        self._lbl_connectes.setStyleSheet(f"color: {COLORS['SUCCESS_BORDER']}; font-size: 12px;")

        self._header_layout.addWidget(self._lbl_total)
        self._header_layout.addSpacing(16)
        self._header_layout.addWidget(self._lbl_actifs)
        self._header_layout.addSpacing(16)
        self._header_layout.addWidget(self._lbl_connectes)
        self._header_layout.addStretch()

        layout.addWidget(self._header_bar)

        # ── Tableau ────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setColumnCount(len(self._COLONNES))

        # En-têtes
        headers = [col[1] for col in self._COLONNES]
        self._table.setHorizontalHeaderLabels(headers)

        # Comportement
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)

        # Largeurs
        header = self._table.horizontalHeader()
        for i, (_, _, w) in enumerate(self._COLONNES):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            self._table.setColumnWidth(i, w)
        # Description prend l'espace restant
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)

        # Style (via palette centralisée)
        self._table.setStyleSheet(
            f"""
            QTableWidget {{
                background-color: {COLORS["BG_INPUT"]};
                alternate-background-color: {COLORS["BG_TABLE_ALT"]};
                border: none;
                gridline-color: transparent;
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 4px 8px;
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS["BG_TABLE_SELECTED"]};
                color: {COLORS["TEXT_WHITE"]};
            }}
            QHeaderView::section {{
                background-color: {COLORS["BG_TABLE_HEADER"]};
                color: {COLORS["TEXT_TABLE_HEADER"]};
                padding: 6px 8px;
                border: none;
                border-bottom: 1px solid {COLORS["BORDER_TABLE_HDR"]};
                font-weight: bold;
                font-size: 11px;
                text-transform: uppercase;
            }}
            """
        )

        layout.addWidget(self._table, 1)

    # ── Setup ───────────────────────────────────────────────────

    def setup(self, service: ClientsActifsService) -> None:
        """Connecte le widget au service clients actifs."""
        if self._setup_done:
            return
        self._setup_done = True

        self._service = service

        # Connexion aux signaux du service
        service.clients_synchronises.connect(self._initialiser_tableau)
        service.client_ajoute.connect(self._ajouter_ligne)
        service.client_retire.connect(self._retirer_ligne)
        service.client_statut_change.connect(self._mettre_a_jour_statut)
        service.client_info_change.connect(self._mettre_a_jour_info)

        # Rafraîchir si déjà synchronisé
        self.rafraichir()

        logger.info("BotClientsActifs connecté au service")

    def rafraichir(self) -> None:
        """Recharge les données depuis le service."""
        if self._service is None:
            return
        actifs = self._service.clients_actifs()
        self._initialiser_tableau(actifs)

    # ── Remplissage du tableau ──────────────────────────────────

    def _initialiser_tableau(self, clients: list[ClientInfo]) -> None:
        """Reconstruit le tableau avec une nouvelle liste de clients."""
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)

        for client in clients:
            self._ajouter_ligne_client(client)

        self._table.setSortingEnabled(True)
        self._mettre_a_jour_stats()

    def _ajouter_ligne(self, username: str) -> None:
        """Ajoute une ligne pour un nouveau client (via signal)."""
        if self._service is None:
            return
        client = self._service.obtenir_client(username)
        if client is None:
            return
        self._ajouter_ligne_client(client)
        self._mettre_a_jour_stats()

    def _ajouter_ligne_client(self, client: ClientInfo) -> None:
        """Ajoute une ligne pour un ClientInfo donné."""
        row = self._table.rowCount()
        self._table.insertRow(row)

        # Statut (colonne 0)
        icone = _ICONE_STATUT.get(client.statut, "⚪")
        texte = _TEXTE_STATUT.get(client.statut, "Inconnu")
        item_statut = _StatutItem(client.statut, f"  {icone}  {texte}")
        item_statut.setForeground(_COULEUR_STATUT.get(client.statut, _COULEUR_UNKNOWN))
        self._table.setItem(row, 0, item_statut)

        # Utilisateur (colonne 1)
        item_user = QTableWidgetItem(client.username)
        item_user.setForeground(QColor(COLORS["TEXT_PRIMARY"]))
        self._table.setItem(row, 1, item_user)

        # Pays (colonne 2)
        item_pays = QTableWidgetItem(client.pays if client.pays else "—")
        item_pays.setForeground(QColor(COLORS["TEXT_SECONDARY"]))
        self._table.setItem(row, 2, item_pays)

        # Vitesse (colonne 3)
        vitesse = f"{client.vitesse} kbps" if client.vitesse > 0 else "—"
        item_vitesse = _NumericItem(client.vitesse, vitesse)
        self._table.setItem(row, 3, item_vitesse)

        # Fichiers (colonne 4)
        fichiers = f"{client.fichiers_partages:,}" if client.fichiers_partages else "—"
        item_fichiers = _NumericItem(client.fichiers_partages, fichiers)
        self._table.setItem(row, 4, item_fichiers)

        # Slots (colonne 5)
        if client.slots_libres_flag:
            slots = f"{client.slots_libres} libre(s)"
        else:
            slots = "—"
        item_slots = _NumericItem(client.slots_libres if client.slots_libres_flag else 0, slots)
        self._table.setItem(row, 5, item_slots)

        # File d'attente (colonne 6)
        file_att = str(client.file_attente) if client.file_attente > 0 else "—"
        item_file = _NumericItem(client.file_attente, file_att)
        self._table.setItem(row, 6, item_file)

        # Description (colonne 7)
        desc = client.description if client.description else ""
        item_desc = QTableWidgetItem(desc)
        item_desc.setForeground(QColor(COLORS["TEXT_MUTED"]))
        self._table.setItem(row, 7, item_desc)

    def _retirer_ligne(self, username: str) -> None:
        """Retire la ligne d'un client (via signal)."""
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 1)
            if item and item.text() == username:
                self._table.removeRow(row)
                break
        self._mettre_a_jour_stats()

    # ── Mise à jour des cellules ────────────────────────────────

    def _mettre_a_jour_statut(
        self,
        username: str,
        nouveau: object,
        _ancien: object,
    ) -> None:
        """Met à jour la cellule statut pour un utilisateur."""
        statut = nouveau if isinstance(nouveau, UserStatus) else UserStatus.UNKNOWN
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 1)
            if item and item.text() == username:
                icone = _ICONE_STATUT.get(statut, "⚪")
                texte = _TEXTE_STATUT.get(statut, "Inconnu")
                couleur = _COULEUR_STATUT.get(statut, _COULEUR_UNKNOWN)

                nouveau_item = _StatutItem(statut, f"  {icone}  {texte}")
                nouveau_item.setForeground(couleur)
                self._table.setItem(row, 0, nouveau_item)
                break
        self._mettre_a_jour_stats()

    def _mettre_a_jour_info(self, username: str) -> None:
        """Met à jour les cellules info pour un utilisateur."""
        if self._service is None:
            return
        client = self._service.obtenir_client(username)
        if client is None:
            return

        for row in range(self._table.rowCount()):
            item = self._table.item(row, 1)
            if item and item.text() == username:
                self._table.setSortingEnabled(False)

                # Vitesse
                vitesse = f"{client.vitesse} kbps" if client.vitesse > 0 else "—"
                self._table.setItem(row, 3, _NumericItem(client.vitesse, vitesse))

                # Fichiers
                fichiers = f"{client.fichiers_partages:,}" if client.fichiers_partages else "—"
                self._table.setItem(row, 4, _NumericItem(client.fichiers_partages, fichiers))

                # Slots
                if client.slots_libres_flag:
                    slots = f"{client.slots_libres} libre(s)"
                else:
                    slots = "—"
                self._table.setItem(row, 5, _NumericItem(client.slots_libres if client.slots_libres_flag else 0, slots))

                # File
                file_att = str(client.file_attente) if client.file_attente > 0 else "—"
                self._table.setItem(row, 6, _NumericItem(client.file_attente, file_att))

                # Pays
                # pyrefly: ignore [missing-attribute]
                self._table.item(row, 2).setText(client.pays if client.pays else "—")

                # Description
                # pyrefly: ignore [missing-attribute]
                self._table.item(row, 7).setText(client.description or "")

                self._table.setSortingEnabled(True)
                break

    # ── Stats ──────────────────────────────────────────────────

    def _mettre_a_jour_stats(self) -> None:
        """Met à jour la barre de statistiques."""
        if self._service is None:
            return

        total = len(self._service.clients_actifs())
        actifs = self._service.nombre_actifs()
        connectes = self._service.nombre_connectes()

        self._lbl_total.setText(f"Total: {total}")
        self._lbl_actifs.setText(f"Actifs: {actifs}")
        self._lbl_connectes.setText(f"Connectés: {connectes}")

        # Badge pour la navigation
        self.unseen_count_changed.emit(actifs)
