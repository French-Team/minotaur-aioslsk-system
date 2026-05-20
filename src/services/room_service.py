"""Service de suivi des salons (rooms) Soulseek.

S'abonne à l'événement RoomListEvent via SoulseekService
et expose les salons publics et privés via des signaux Qt.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:
    from src.services.soulseek_client import SoulseekService

logger = logging.getLogger(__name__)


@dataclass
class RoomInfo:
    """Information sur un salon Soulseek."""

    name: str
    user_count: int = 0


class RoomService(QObject):
    """Service événementiel de suivi des salons Soulseek.

    S'abonne à room_list_received (SoulseekService) et expose
    les salons publics et privés via des signaux Qt.
    """

    # ── Signaux ─────────────────────────────────────────────────

    rooms_publiques_recues = Signal(list)   # list[RoomInfo]
    rooms_privees_recues = Signal(list)     # list[RoomInfo]
    room_list_rafraichie = Signal()          # signal générique (les deux onglets)

    def __init__(
        self,
        soulseek_service: SoulseekService,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._soulseek = soulseek_service
        self._rooms_publiques: list[RoomInfo] = []
        self._rooms_privees: list[RoomInfo] = []
        self._running = False

    # ── Propriétés ──────────────────────────────────────────────

    @property
    def rooms_publiques(self) -> list[RoomInfo]:
        return list(self._rooms_publiques)

    @property
    def rooms_privees(self) -> list[RoomInfo]:
        return list(self._rooms_privees)

    @property
    def nb_publiques(self) -> int:
        return len(self._rooms_publiques)

    @property
    def nb_privees(self) -> int:
        return len(self._rooms_privees)

    # ── Cycle de vie ────────────────────────────────────────────

    def demarrer(self) -> None:
        """Démarre le service : abonnement au signal room_list_received."""
        if self._running:
            return
        self._running = True

        self._soulseek.room_list_received.connect(self._on_room_list)
        self._soulseek.connection_changed.connect(self._on_connection_changed)

        # Synchronisation initiale : si déjà connecté, récupérer les rooms
        self._synchroniser()

        logger.info("RoomService démarré")

    def arreter(self) -> None:
        """Arrête le service."""
        self._running = False
        try:
            self._soulseek.room_list_received.disconnect(self._on_room_list)
            self._soulseek.connection_changed.disconnect(self._on_connection_changed)
        except (TypeError, RuntimeError):
            pass
        self._rooms_publiques.clear()
        self._rooms_privees.clear()
        logger.info("RoomService arrêté")

    def rafraichir(self) -> None:
        """Re-synchronisation manuelle (ex: reconnexion)."""
        self._synchroniser()

    # ── Synchronisation ─────────────────────────────────────────

    def _synchroniser(self) -> None:
        """Récupère les rooms depuis le client aioslsk si connecté."""
        client = self._soulseek.client
        if client is None:
            return

        try:
            # Salons publics
            raw_publiques = client.rooms.get_public_rooms()
            self._rooms_publiques = [
                RoomInfo(name=r.name, user_count=getattr(r, "user_count", 0))
                for r in raw_publiques
            ]

            # Salons privés (rooms rejointes)
            raw_joined = client.rooms.get_joined_rooms()
            self._rooms_privees = [
                RoomInfo(name=r.name, user_count=getattr(r, "user_count", 0))
                for r in raw_joined
                if getattr(r, "is_private", False)
            ]

            # Émettre les signaux
            self.rooms_publiques_recues.emit(self._rooms_publiques)
            self.rooms_privees_recues.emit(self._rooms_privees)
            self.room_list_rafraichie.emit()

            logger.debug("RoomService: %d publiques, %d privées",
                         len(self._rooms_publiques), len(self._rooms_privees))

        except Exception:
            logger.exception("RoomService: erreur lors de la synchronisation")

    # ── Gestion des événements SoulseekService ──────────────────

    def _on_room_list(self, evt: object) -> None:
        """Réception de RoomListEvent — met à jour les listes."""
        logger.info("RoomService: RoomListEvent reçu")
        self._synchroniser()

    def _on_connection_changed(self, connected: bool) -> None:
        """Gère la connexion et déconnexion pour réinitialiser ou synchroniser les salons."""
        if connected:
            self._synchroniser()
        else:
            self._rooms_publiques.clear()
            self._rooms_privees.clear()
            self.rooms_publiques_recues.emit([])
            self.rooms_privees_recues.emit([])
            self.room_list_rafraichie.emit()
