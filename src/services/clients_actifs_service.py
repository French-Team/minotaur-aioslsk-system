"""Service de suivi des clients actifs (contacts Soulseek).

S'abonne aux événements aioslsk (UserStatusUpdate, UserInfoUpdate)
et expose l'état des clients trackés via des signaux Qt.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from aioslsk.events import (
    UserInfoUpdateEvent,
    UserStatusUpdateEvent,
)
from aioslsk.user.model import UserStatus
from PySide6.QtCore import QObject, Signal, QTimer

if TYPE_CHECKING:
    from aioslsk.client import SoulSeekClient
    from aioslsk.user.model import User

    from src.services.soulseek_client import SoulseekService

logger = logging.getLogger(__name__)


@dataclass
class ClientInfo:
    """Information consolidée sur un client Soulseek tracké."""

    username: str
    statut: UserStatus = UserStatus.UNKNOWN
    pays: str = ""
    vitesse: int = 0
    fichiers_partages: int = 0
    dossiers_partages: int = 0
    slots_libres: int = 0
    slots_libres_flag: bool = False
    file_attente: int = 0
    uploads: int = 0
    privilege: bool = False
    description: str = ""
    derniere_vue: float = 0.0  # timestamp — géré par le service


class ClientsActifsService(QObject):
    """Service événementiel de suivi des clients actifs.

    S'abonne aux événements aioslsk et expose les changements
    via des signaux Qt pour les widgets.
    """

    # ── Signaux ─────────────────────────────────────────────────

    client_ajoute = Signal(str)  # username ajouté
    client_retire = Signal(str)  # username retiré
    client_statut_change = Signal(str, object, object)  # username, nouveau statut, ancien statut
    client_info_change = Signal(str)  # username dont les infos ont changé
    clients_synchronises = Signal(list)  # liste initiale [ClientInfo, ...]

    def __init__(
        self,
        soulseek_service: SoulseekService,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._soulseek = soulseek_service
        self._clients: dict[str, ClientInfo] = {}
        self._running = False
        self._ping_task = None
        self._async_loop = None  # boucle asyncio du ConnexionManager (injectée au démarrage)

        # Minuteur pour synchroniser périodiquement les membres des salons rejoints
        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(30000)  # Toutes les 30 secondes
        self._sync_timer.timeout.connect(self._synchroniser)

        # Le cycle de vie est piloté de manière centralisée et séquentielle par le contrôleur (MainWindow)

    # ── Propriétés ──────────────────────────────────────────────

    @property
    def _client(self) -> SoulSeekClient | None:
        """Accès au client aioslsk sous-jacent (None si déconnecté)."""
        return self._soulseek.client

    # ── Cycle de vie ────────────────────────────────────────────

    def demarrer(self, async_loop=None) -> None:
        """Démarre le service : synchronisation initiale + abonnement événements.

        Args:
            async_loop: La boucle asyncio du ConnexionManager (thread réseau applicatif).
                        Si fournie, une tâche de ping légère sera lancée dessus.
        """
        if self._running:
            return
        self._running = True
        self._async_loop = async_loop

        client = self._client
        if client is None:
            logger.warning("ClientsActifsService: pas de client aioslsk — différé")
            return

        # 1. Synchronisation initiale — tracker les users déjà connus
        self._synchroniser()

        # 2. Abonnement aux événements aioslsk
        try:
            client.events.register(
                UserStatusUpdateEvent,
                self._on_user_status_update,
            )
            client.events.register(
                UserInfoUpdateEvent,
                self._on_user_info_update,
            )
        except Exception:
            logger.exception("ClientsActifsService: erreur lors de l'enregistrement des événements")

        # 3. Démarrer le minuteur de synchronisation Qt (thread UI — sans réseau)
        self._sync_timer.start()

        # 4. Lancer le ping léger sur la boucle APPLICATIVE (pas la boucle interne aioslsk)
        #    On n'exécute aucune commande réseau lourde ici — uniquement GetUserStatus
        #    pour les utilisateurs déjà suivis par aioslsk.
        if async_loop is not None:
            try:
                import asyncio
                self._ping_task = asyncio.run_coroutine_threadsafe(
                    self._do_ping_loop(), async_loop
                )
                logger.info("ClientsActifsService: tâche de ping démarrée")
            except Exception:
                logger.exception("ClientsActifsService: impossible de lancer le ping_task")
        else:
            logger.info("ClientsActifsService: pas de boucle async fournie — ping désactivé")

    def arreter(self) -> None:
        """Arrête le service."""
        self._running = False
        self._sync_timer.stop()
        if self._ping_task is not None:
            self._ping_task.cancel()
            self._ping_task = None
        self._clients.clear()
        logger.info("ClientsActifsService arrêté")

    def rafraichir(self) -> None:
        """Re-synchronisation manuelle (ex: reconnexion)."""
        self._synchroniser()

    # ── Accès aux données ───────────────────────────────────────

    def clients_actifs(self) -> list[ClientInfo]:
        """Retourne tous les clients avec statut != UNKNOWN, triés par nom."""
        return sorted(
            [c for c in self._clients.values() if c.statut != UserStatus.UNKNOWN],
            key=lambda c: c.username.lower(),
        )

    def clients_tries(
        self,
        cle: str = "username",
        ordre: bool = True,
    ) -> list[ClientInfo]:
        """Retourne les clients triés par clé (username, statut, etc.)."""
        clients = list(self._clients.values())
        reverse = not ordre
        if cle == "username":
            clients.sort(key=lambda c: c.username.lower(), reverse=reverse)
        elif cle == "statut":
            _ORDRE_STATUT = {
                UserStatus.ONLINE.value: 0,
                UserStatus.AWAY.value: 1,
                UserStatus.OFFLINE.value: 2,
                UserStatus.UNKNOWN.value: 3,
            }
            clients.sort(
                key=lambda c: (_ORDRE_STATUT.get(c.statut.value, 99), c.username.lower()),
                reverse=reverse,
            )
        elif cle == "vitesse":
            clients.sort(key=lambda c: c.vitesse, reverse=reverse)
        elif cle == "fichiers":
            clients.sort(key=lambda c: c.fichiers_partages, reverse=reverse)
        elif cle == "slots":
            clients.sort(key=lambda c: c.slots_libres, reverse=reverse)
        elif cle == "file":
            clients.sort(key=lambda c: c.file_attente, reverse=reverse)
        else:
            clients.sort(key=lambda c: c.username.lower(), reverse=reverse)
        return clients

    def obtenir_client(self, username: str) -> ClientInfo | None:
        """Retourne un client par son nom."""
        return self._clients.get(username)

    def nombre_actifs(self) -> int:
        """Nombre de clients avec statut ONLINE ou AWAY."""
        return sum(1 for c in self._clients.values() if c.statut in (UserStatus.ONLINE, UserStatus.AWAY))

    def nombre_connectes(self) -> int:
        """Nombre de clients avec statut ONLINE."""
        return sum(1 for c in self._clients.values() if c.statut == UserStatus.ONLINE)

    # ── Synchronisation ─────────────────────────────────────────

    def _synchroniser(self) -> None:
        """Synchronise l'état interne avec le UserManager d'aioslsk."""
        client = self._client
        if client is None or client.users is None:
            return

        try:
            tracked: dict[str, "User"] = client.users.users
            nouveaux: dict[str, ClientInfo] = {}

            for username, user in tracked.items():
                info = ClientInfo(
                    username=username,
                    statut=user.status,
                    pays=getattr(user, "country", "") or "",
                    vitesse=getattr(user, "avg_speed", 0) or 0,
                    fichiers_partages=getattr(user, "shared_file_count", 0) or 0,
                    dossiers_partages=getattr(user, "shared_folder_count", 0) or 0,
                    slots_libres=getattr(user, "slots_free", 0) or 0,
                    slots_libres_flag=getattr(user, "has_slots_free", False) or False,
                    file_attente=getattr(user, "queue_length", 0) or 0,
                    uploads=getattr(user, "uploads", 0) or 0,
                    privilege=getattr(user, "privileged", False) or False,
                    description=getattr(user, "description", "") or "",
                )
                nouveaux[username] = info

            self._clients = nouveaux
            actifs = self.clients_actifs()
            self.clients_synchronises.emit(actifs)
            logger.info("ClientsActifsService: %d clients synchronisés", len(actifs))

        except Exception:
            logger.exception("ClientsActifsService: erreur lors de la synchronisation")

    # ── Gestion des événements aioslsk ──────────────────────────

    def _on_user_status_update(self, evt: UserStatusUpdateEvent) -> None:
        """Un client a changé de statut (ONLINE/AWAY/OFFLINE)."""
        username = str(getattr(evt, "username"))
        nouveau = getattr(evt, "status")
        ancien = UserStatus.UNKNOWN

        if username in self._clients:
            ancien = self._clients[username].statut
            self._clients[username].statut = nouveau
        else:
            # Nouveau client découvert via l'événement
            info = ClientInfo(username=username, statut=nouveau)
            self._clients[username] = info
            self.client_ajoute.emit(username)

        self.client_statut_change.emit(username, nouveau, ancien)
        logger.debug("Statut %s: %s -> %s", username, ancien.name, nouveau.name)

    def _on_user_info_update(self, evt: UserInfoUpdateEvent) -> None:
        """Les informations d'un client ont changé."""
        username = str(getattr(evt, "username"))
        if username not in self._clients:
            return

        info = self._clients[username]
        # Mise à jour des champs disponibles depuis l'événement
        if hasattr(evt, "description") and evt.description is not None:
            info.description = evt.description
        if hasattr(evt, "country") and evt.country is not None:
            info.pays = evt.country
        if hasattr(evt, "avg_speed") and evt.avg_speed is not None:
            info.vitesse = evt.avg_speed
        if hasattr(evt, "uploads") and evt.uploads is not None:
            info.uploads = evt.uploads
        if hasattr(evt, "shared_file_count") and evt.shared_file_count is not None:
            info.fichiers_partages = evt.shared_file_count
        if hasattr(evt, "shared_folder_count") and evt.shared_folder_count is not None:
            info.dossiers_partages = evt.shared_folder_count
        if hasattr(evt, "slots_free") and evt.slots_free is not None:
            info.slots_libres = evt.slots_free
        if hasattr(evt, "has_slots_free") and evt.has_slots_free is not None:
            info.slots_libres_flag = evt.has_slots_free
        if hasattr(evt, "queue_length") and evt.queue_length is not None:
            info.file_attente = evt.queue_length
        if hasattr(evt, "privileged") and evt.privileged is not None:
            info.privilege = evt.privileged

        self.client_info_change.emit(username)
        logger.debug("Info mise à jour pour %s", username)

    def _on_connection_changed(self, connected: bool) -> None:
        """Déclenche le démarrage ou l'arrêt automatique selon l'état de la connexion."""
        if connected:
            self.demarrer()
        else:
            self.arreter()

    async def _do_ping_loop(self) -> None:
        """Boucle asyncio légère : rafraîchit le statut des utilisateurs déjà suivis.

        S'exécute sur la boucle applicative du ConnexionManager.
        N'effectue AUCUN auto-join autonome — rejoindre des salons est
        une action explicite déclenchée par l'utilisateur via l'interface.
        """
        import asyncio
        from aioslsk.commands import GetUserStatusCommand

        logger.info("ClientsActifsService: boucle de ping démarrée (intervalle=120s)")

        while self._running:
            # Attendre avant le premier ping (laisser la connexion se stabiliser)
            await asyncio.sleep(120.0)

            if not self._running:
                break

            client = self._client
            if client is None:
                break

            # Rafraîchir uniquement les utilisateurs déjà trackés par aioslsk
            current_clients = list(self._clients.keys())
            if not current_clients:
                continue

            logger.debug(
                "ClientsActifsService: ping de %d utilisateurs trackés",
                len(current_clients),
            )
            for username in current_clients:
                if not self._running:
                    break
                try:
                    # pyrefly: ignore [bad-argument-type]
                    await client.execute(GetUserStatusCommand(username))
                except Exception:
                    pass
                await asyncio.sleep(0.2)  # Délai entre chaque requête

        logger.info("ClientsActifsService: boucle de ping terminée")
