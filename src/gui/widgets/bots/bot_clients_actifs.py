"""Widget d'affichage des clients actifs (contacts Soulseek trackés).

Affiche un tableau triable avec le statut en temps réel,
connecté au ClientsActifsService.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from aioslsk.user.model import UserStatus
from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.theme_fragments.colors import COLORS
from PySide6.QtCore import Qt

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
    rafraichir_demande = Signal()  # émis quand l'utilisateur clique Rafraîchir

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
        self._actif = False

        # Stats trackées depuis les signaux
        self._total_candidats: int = 0
        self._actifs_joignables: int = 0
        self._last_update_time: float = 0.0

        self._build_ui()

        # Timer pour mettre à jour l'affichage "Dernière mise à jour" toutes les 60s
        self._maj_timer = QTimer(self)
        self._maj_timer.setInterval(60_000)
        self._maj_timer.timeout.connect(self._update_derniere_maj)

        # Timer de sécurité pour le bouton Rafraîchir (60s max)
        self._timeout_rafraichir = QTimer(self)
        self._timeout_rafraichir.setSingleShot(True)
        self._timeout_rafraichir.setInterval(60_000)
        self._timeout_rafraichir.timeout.connect(self._on_rafraichir_timeout)

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

        # Indicateur d'état du pipeline
        self._lbl_etat = QLabel("⏸ Arrêté")
        self._lbl_etat.setStyleSheet(
            f"color: {COLORS['TEXT_MUTED']}; font-size: 12px; font-weight: bold;"
        )
        self._header_layout.addWidget(self._lbl_etat)
        self._header_layout.addSpacing(16)

        # Candidats (membres des rooms)
        self._lbl_candidats = QLabel("Candidats: —")
        self._lbl_candidats.setStyleSheet(
            f"color: {COLORS['TEXT_SECONDARY']}; font-size: 12px;"
        )
        self._header_layout.addWidget(self._lbl_candidats)
        self._header_layout.addSpacing(12)

        # Actifs & joignables (après ping + ONLINE)
        self._lbl_actifs_joignables = QLabel("Actifs: —")
        self._lbl_actifs_joignables.setStyleSheet(
            f"color: {COLORS['SUCCESS']}; font-size: 12px; font-weight: bold;"
        )
        self._header_layout.addWidget(self._lbl_actifs_joignables)
        self._header_layout.addSpacing(12)

        # Injouignables (ping échoué ou pas ONLINE)
        self._lbl_injouignables = QLabel("Injouignables: —")
        self._lbl_injouignables.setStyleSheet(
            f"color: {COLORS['WARNING']}; font-size: 12px;"
        )
        self._header_layout.addWidget(self._lbl_injouignables)
        self._header_layout.addSpacing(12)

        # Dernière mise à jour
        self._lbl_derniere_maj = QLabel("Dernière mise à jour: —")
        self._lbl_derniere_maj.setStyleSheet(
            f"color: {COLORS['TEXT_MUTED']}; font-size: 11px;"
        )
        self._header_layout.addWidget(self._lbl_derniere_maj)
        self._header_layout.addStretch()

        # ── Bouton Rafraîchir ───────────────────────────────────
        self._btn_rafraichir = QPushButton("🔄 Rafraîchir")
        self._btn_rafraichir.setToolTip(
            "Relance la détection complète des clients actifs (rooms → ping → filtrage)"
        )
        self._btn_rafraichir.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_rafraichir.setStyleSheet(
            f"""
            QPushButton {{
                background: {COLORS["BG_SURFACE"]};
                color: {COLORS["TEXT_PRIMARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {COLORS["ACCENT_HOVER"]};
                border-color: {COLORS["ACCENT"]};
                color: {COLORS["TEXT_WHITE"]};
            }}
            QPushButton:disabled {{
                background: {COLORS["BG_INPUT"]};
                color: {COLORS["TEXT_PLACEHOLDER"]};
                border-color: {COLORS["BORDER_LIGHT"]};
            }}
            """
        )
        self._btn_rafraichir.clicked.connect(self._on_rafraichir_click)
        self._header_layout.addWidget(self._btn_rafraichir)

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

    # ── Interrupteur ─────────────────────────────────────────────

    def demarrer(self) -> None:
        """Active l'interrupteur → démarre la boucle clients actifs."""
        if self._actif:
            return
        self._actif = True
        self._show_etat("prêt")
        if self._service is not None and hasattr(self._service, "demarrer"):
            self._service.demarrer()
        logger.info("BotClientsActifs démarré")

    def arreter(self) -> None:
        """Désactive l'interrupteur → suspend la boucle clients actifs."""
        if not self._actif:
            return
        self._actif = False
        self._show_etat("arrêté")
        if self._service is not None and hasattr(self._service, "arreter"):
            self._service.arreter()
        logger.info("BotClientsActifs arrêté")

    @property
    def est_actif(self) -> bool:
        return self._actif

    # ── Setup ───────────────────────────────────────────────────

    def setup(self, service: ClientsActifsService) -> None:
        """Connecte le widget au service clients actifs."""
        if self._setup_done:
            return
        self._setup_done = True

        self._service = service

        # Connexion aux signaux du service
        service.clients_synchronises.connect(self._on_clients_synchronises)
        service.clients_valides.connect(self._on_clients_valides)
        service.client_ajoute.connect(self._ajouter_ligne)
        service.client_retire.connect(self._retirer_ligne)
        service.client_statut_change.connect(self._mettre_a_jour_statut)
        service.client_info_change.connect(self._mettre_a_jour_info)

        # Démarrer le timer de mise à jour du timestamp
        self._maj_timer.start()

        # Rafraîchir si déjà synchronisé
        self.rafraichir()

        logger.info("BotClientsActifs connecté au service")

    def rafraichir(self) -> None:
        """Recharge les données depuis le service."""
        if self._service is None:
            return
        actifs = self._service.clients_actifs()
        self._initialiser_tableau(actifs)

    # ── Wrappers signaux ────────────────────────────────────────

    def _on_clients_synchronises(self, clients: list[ClientInfo]) -> None:
        """Réception du signal clients_synchronises (tous les candidats)."""
        self._total_candidats = len(clients)
        self._initialiser_tableau(clients)

    def _on_clients_valides(self, clients: list[ClientInfo]) -> None:
        """Réception du signal clients_valides (après ping + filtrage ONLINE)."""
        self._actifs_joignables = len(clients)
        self._last_update_time = time.time()
        self._show_etat("prêt")
        self._update_derniere_maj()

        # Réactiver le bouton Rafraîchir (et arrêter le timeout)
        self._btn_rafraichir.setEnabled(True)
        self._btn_rafraichir.setText("🔄 Rafraîchir")
        self._timeout_rafraichir.stop()

        self._initialiser_tableau(clients)

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
                self._table.setItem(
                    row, 4, _NumericItem(client.fichiers_partages, fichiers)
                )

                # Slots
                if client.slots_libres_flag:
                    slots = f"{client.slots_libres} libre(s)"
                else:
                    slots = "—"
                self._table.setItem(
                    row,
                    5,
                    _NumericItem(
                        client.slots_libres if client.slots_libres_flag else 0, slots
                    ),
                )

                # File
                file_att = str(client.file_attente) if client.file_attente > 0 else "—"
                self._table.setItem(
                    row, 6, _NumericItem(client.file_attente, file_att)
                )

                # Pays
                # pyrefly: ignore [missing-attribute]
                self._table.item(row, 2).setText(client.pays if client.pays else "—")

                # Description
                # pyrefly: ignore [missing-attribute]
                self._table.item(row, 7).setText(client.description or "")

                self._table.setSortingEnabled(True)
                break

    # ── Indicateur d'état ──────────────────────────────────────

    def _show_etat(self, etat: str) -> None:
        """Met à jour l'indicateur d'état du pipeline.

        Paramètres
        ----------
        etat : str
            ``\"prêt\"`` → 🟢 Prêt
            ``\"scan\"`` → 🔄 Scan en cours...
            ``\"arrêté\"`` → ⏸ Arrêté
        """
        mapping = {
            "prêt": ("🟢", "Prêt", COLORS["SUCCESS"]),
            "scan": ("🔄", "Scan en cours…", COLORS["ACCENT"]),
            "arrêté": ("⏸", "Arrêté", COLORS["TEXT_MUTED"]),
        }
        icone, texte, couleur = mapping.get(etat, ("❓", "Inconnu", COLORS["DANGER"]))
        self._lbl_etat.setText(f"{icone} {texte}")
        self._lbl_etat.setStyleSheet(
            f"color: {couleur}; font-size: 12px; font-weight: bold;"
        )

    # ── Dernière mise à jour ────────────────────────────────────

    def _update_derniere_maj(self) -> None:
        """Met à jour le label 'Dernière mise à jour' avec le temps relatif."""
        if self._last_update_time <= 0:
            self._lbl_derniere_maj.setText("Dernière mise à jour: —")
            return

        elapsed = time.time() - self._last_update_time
        if elapsed < 60:
            texte = "il y a < 1 min"
        elif elapsed < 3600:
            minutes = int(elapsed // 60)
            texte = f"il y a {minutes} min"
        elif elapsed < 86400:
            heures = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            texte = f"il y a {heures}h{minutes:02d}"
        else:
            jours = int(elapsed // 86400)
            texte = f"il y a {jours} jour(s)"

        self._lbl_derniere_maj.setText(f"Dernière mise à jour: {texte}")

    # ── Rafraîchir ────────────────────────────────────────────

    def _on_rafraichir_timeout(self) -> None:
        """Timeout de sécurité : réactive le bouton après 60s si le pipeline n'a pas répondu."""
        self._btn_rafraichir.setEnabled(True)
        self._btn_rafraichir.setText("🔄 Rafraîchir")
        if self._actif:
            self._show_etat("prêt")
        logger.warning("Timeout Rafraîchir — pipeline non terminé après 60s")

    def _on_rafraichir_click(self) -> None:
        """L'utilisateur a cliqué sur Rafraîchir → désactive le bouton et émet le signal."""
        self._btn_rafraichir.setEnabled(False)
        self._btn_rafraichir.setText("🔄 Scan en cours…")
        self._show_etat("scan")
        self._timeout_rafraichir.start()
        self.rafraichir_demande.emit()

    # ── Stats ──────────────────────────────────────────────────

    def _mettre_a_jour_stats(self) -> None:
        """Met à jour la barre de statistiques (candidats / actifs & joignables / injouignables).

        Utilise les valeurs trackées depuis les signaux pipeline (clients_synchronises
        et clients_valides). Quand un client est ajouté individuellement via un
        événement temps-réel (client_ajoute), le compteur ``_total_candidats`` n'est
        pas incrémenté — on utilise ``max(nb_lignes, total_tracké)`` pour ne jamais
        afficher un total inférieur au nombre réel de lignes.
        """
        nb_lignes = self._table.rowCount()
        total = max(self._total_candidats, nb_lignes)
        actifs = max(self._actifs_joignables, nb_lignes)
        injouignables = max(0, total - actifs)

        self._lbl_candidats.setText(f"Candidats: {total}")
        self._lbl_actifs_joignables.setText(f"Actifs & joignables: {actifs}")
        self._lbl_injouignables.setText(f"Injouignables: {injouignables}")

        # Badge pour la navigation (basé sur les actifs & joignables)
        self.unseen_count_changed.emit(actifs)
