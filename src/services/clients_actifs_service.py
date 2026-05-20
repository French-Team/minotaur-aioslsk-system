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

    from src.services.connexion_manager import ConnexionManager
    from src.services.soulseek_client import SoulseekService

logger = logging.getLogger(__name__)

# ── Paramètres de rate limiting pour le ping par lots ────────────

_LOT_PING = 10  # Nombre de clients pingés par lot
_DELAI_INTER_LOTS = 2.0  # Secondes entre deux lots


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
    ping_termine = Signal(list)  # [str] — usernames ayant répondu au ping
    clients_valides = Signal(list)  # [ClientInfo] — clients actifs & joignables après ping

    def __init__(
        self,
        soulseek_service: SoulseekService,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._soulseek = soulseek_service
        self._clients: dict[str, ClientInfo] = {}
        self._running = False
        self._ping_en_cours = False  # Évite les doubles pings simultanés
        self._cm: ConnexionManager | None = None  # Injecté via set_connexion_manager()

        # Minuteur pour synchroniser périodiquement les membres des salons rejoints
        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(30000)  # Toutes les 30 secondes
        self._sync_timer.timeout.connect(self._synchroniser)

        # Le cycle de vie est piloté de manière centralisée et séquentielle par le contrôleur (MainWindow)

        # Connexion interne : ping_termine → filtre → clients_valides
        self.ping_termine.connect(self._on_ping_termine)

    # ── Propriétés ──────────────────────────────────────────────

    def ingest_membres_rooms(self, membres: list[dict]) -> None:
        """Reçoit les membres des salons depuis BoucleRooms.

        Ces membres complètent le UserManager d'aioslsk avec les utilisateurs
        découverts dans les salons publics.

        Paramètres
        ----------
        membres : list[dict]
            Liste de dictionnaires avec les clés ``username``, ``room``, ``status``.
        """
        for memb in membres:
            username = memb.get("username", "")
            if not username:
                continue
            if username not in self._clients:
                info = ClientInfo(
                    username=username,
                    statut=UserStatus.ONLINE,  # From room = visible = online-ish
                )
                self._clients[username] = info
                self.client_ajoute.emit(username)
            else:
                # Already tracked via UserManager — room membership may have changed
                # Update statut to ONLINE since they're in a room (visible)
                existing = self._clients[username]
                if existing.statut == UserStatus.UNKNOWN:
                    existing.statut = UserStatus.ONLINE
                    self.client_statut_change.emit(username, UserStatus.ONLINE, UserStatus.UNKNOWN)
                logger.debug("Client %s already tracked (rooms update skipped)", username)
        # Re émette le signal de synchro pour que le tableau se mette à jour
        actifs = self.clients_actifs()
        self.clients_synchronises.emit(actifs)
        logger.debug("ClientsActifsService: ingest %d membres depuis Rooms", len(membres))

        # Déclencher le ping par lots pour valider la joignabilité des membres
        self.lancer_ping(membres)

    # ── Propriétés ──────────────────────────────────────────────

    @property
    def _client(self) -> SoulSeekClient | None:
        """Accès au client aioslsk sous-jacent (None si déconnecté)."""
        return self._soulseek.client

    # ── Cycle de vie ────────────────────────────────────────────

    def demarrer(self) -> None:
        """Démarre le service : synchronisation initiale + abonnement événements.

        Note
        ----
        Le ping par lots n'est PAS lancé automatiquement au démarrage.
        Il est déclenché via ``lancer_ping(membres)`` après réception
        des membres depuis BoucleRooms.
        """
        if self._running:
            return
        self._running = True

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

        logger.info("ClientsActifsService démarré")

    def arreter(self) -> None:
        """Arrête le service."""
        self._running = False
        self._ping_en_cours = False
        self._sync_timer.stop()
        self._clients.clear()
        logger.info("ClientsActifsService arrêté")

    def rafraichir(self) -> None:
        """Re-synchronisation manuelle (ex: reconnexion)."""
        self._synchroniser()

    # ── Injection ConnexionManager ───────────────────────────────

    def set_connexion_manager(self, manager: ConnexionManager) -> None:
        """Injecte le ConnexionManager pour exécuter des coroutines asynchrones.

        Appelé par CenterZone au moment de la connexion. Permet à
        ``lancer_ping()`` d'utiliser ``run_coro()`` au lieu d'accéder
        directement à la boucle asyncio du client aioslsk.
        """
        self._cm = manager
        logger.debug("ClientsActifsService: ConnexionManager injecté")

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

    # ── Ping par lots ───────────────────────────────────────────────

    def lancer_ping(self, membres: list[dict]) -> None:
        """Déclenche le ping par lots sur la boucle asyncio du ConnexionManager.

        Cette méthode est appelée après réception des membres depuis
        BoucleRooms pour vérifier quels clients sont réellement joignables.
        Utilise ``ConnexionManager.run_coro()`` pour exécuter la coroutine
        sur la bonne boucle asyncio.

        Paramètres
        ----------
        membres : list[dict]
            Liste des membres (username, room, status) provenant de BoucleRooms.
        """
        if self._ping_en_cours:
            logger.warning("Ping déjà en cours — ignoré")
            return

        if self._cm is None:
            logger.warning("ClientsActifsService: ConnexionManager non injecté — ping impossible")
            return

        try:
            self._cm.run_coro(self._ping_par_lots(membres))
            logger.debug("Ping par lots déclenché (%d membres)", len(membres))
        except Exception:
            logger.exception("ClientsActifsService: impossible de lancer le ping")

    async def _ping_par_lots(self, membres: list[dict]) -> list[str]:
        """Pinge les membres par lots et retourne ceux qui ont répondu.

        Découpe la liste en lots de ``_LOT_PING`` clients et attend
        ``_DELAI_INTER_LOTS`` secondes entre chaque lot pour éviter
        de saturer le réseau Soulseek.

        Paramètres
        ----------
        membres : list[dict]
            Liste des membres à pinger (username, room, status).

        Retourne
        --------
        list[str]
            Liste des usernames qui ont répondu au ping.
        """
        import asyncio
        from aioslsk.commands import GetUserStatusCommand

        self._ping_en_cours = True
        reponses: list[str] = []
        total = len(membres)
        lots_total = (total - 1) // _LOT_PING + 1 if total > 0 else 0

        try:
            for i in range(0, total, _LOT_PING):
                if not self._running:
                    break

                lot = membres[i:i + _LOT_PING]
                nb_reponses = 0

                for memb in lot:
                    username = memb.get("username", "")
                    if not username:
                        continue
                    if not self._running:
                        break
                    try:
                        await self._client.execute(GetUserStatusCommand(username))
                        reponses.append(username)
                        nb_reponses += 1
                    except Exception:
                        pass  # Pas de réponse → client non joignable

                num_lot = i // _LOT_PING + 1
                logger.debug(
                    "Lot %d/%d : %d pings, %d réponses",
                    num_lot, lots_total, len(lot), nb_reponses,
                )

                # Attendre avant le prochain lot (sauf si c'est le dernier)
                if i + _LOT_PING < total:
                    await asyncio.sleep(_DELAI_INTER_LOTS)

        finally:
            self._ping_en_cours = False

        logger.info(
            "Ping terminé : %d/%d ont répondu (lots=%d)",
            len(reponses), total, lots_total,
        )
        self.ping_termine.emit(reponses)
        return reponses

    def _on_ping_termine(self, reponses: list[str]) -> None:
        """Callback exécuté après la fin du ping asynchrone.

        Filtre les répondants pour ne garder que ceux dont le statut
        est ``ONLINE`` (actifs & joignables) et émet le résultat
        via ``clients_valides``.

        Paramètres
        ----------
        reponses : list[str]
            Usernames ayant répondu au ping.
        """
        valides = [
            self._clients[u]
            for u in reponses
            if u in self._clients and self._clients[u].statut == UserStatus.ONLINE
        ]
        self.clients_valides.emit(valides)
        logger.info("ClientsActifsService: %d clients valides après ping (ONLINE)", len(valides))