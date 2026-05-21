"""Service de suivi des clients actifs (contacts Soulseek).

S'abonne aux événements aioslsk (UserStatusUpdate, UserInfoUpdate)
et expose l'état des clients trackés via des signaux Qt.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from aioslsk.events import (
    PrivateMessageEvent,
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

from src.services.event_bus import EventBus

logger = logging.getLogger(__name__)

# ── Paramètres de rate limiting pour le ping par lots ────────────

_LOT_PING = 10  # Nombre de clients pingés par lot
_DELAI_INTER_LOTS = 2.0  # Secondes entre deux lots
_INTERVALLE_PING_MIN = 300  # Secondes minimum entre deux pings (5 min)


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
        self._dernier_ping: float = 0.0  # timestamp du dernier ping lancé (espacement)
        self._dernier_hash_membres: int = 0  # hash du dernier lot pingé (dirty flag)

        # ── Métriques de performance ────────────────────────────
        self._total_pings: int = 0  # nombre total de pings lancés
        self._total_reponses: int = 0  # nombre total de réponses reçues
        self._temps_total_ping: float = 0.0  # temps cumulé passé à pinger (secondes)

        # Minuteur pour synchroniser périodiquement les membres des salons rejoints
        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(30000)  # Toutes les 30 secondes
        self._sync_timer.timeout.connect(self._synchroniser)

        # Le cycle de vie est piloté de manière centralisée et séquentielle par le contrôleur (MainWindow)

        # Connexion interne : ping_termine → filtre → clients_valides
        self.ping_termine.connect(self._on_ping_termine)

    # ── Métriques de performance ────────────────────────────────

    def ping_metrics(self) -> dict:
        """Retourne les métriques de performance du ping.

        Retourne
        --------
        dict
            Dictionnaire avec les clés :
            - ``total_pings`` : nombre total de candidats pingés
            - ``total_reponses`` : nombre total de réponses reçues
            - ``taux_succes`` : ratio réponses/pings (0.0 - 1.0)
            - ``temps_moyen`` : temps moyen par ping en secondes
        """
        taux = self._total_reponses / self._total_pings if self._total_pings > 0 else 0.0
        temps_moyen = self._temps_total_ping / self._total_pings if self._total_pings > 0 else 0.0
        return {
            "total_pings": self._total_pings,
            "total_reponses": self._total_reponses,
            "taux_succes": round(taux, 3),
            "temps_moyen": round(temps_moyen, 1),
        }

    def reinitialiser_metriques(self) -> None:
        """Remet tous les compteurs de métriques à zéro."""
        self._total_pings = 0
        self._total_reponses = 0
        self._temps_total_ping = 0.0

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

        # Émettre un événement pour le workflow inspector
        self._on_ingest_membres_rooms(membres)

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
            # Découverte passive : tout utilisateur qui nous envoie un MP
            # est automatiquement tracké dans client.users.users
            client.events.register(
                PrivateMessageEvent,
                self._on_private_message,
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

    def forcer_ping(self) -> None:
        """Force un ping immédiat sur tous les clients trackés.

        Appelé par le bouton 🔄 Rafraîchir de l'interface utilisateur.
        Contourne les deux gardes (espacement temporel + dirty flag)
        en appelant ``lancer_ping()`` avec ``force=True``.

        Reconstruit la liste des membres depuis le dictionnaire
        ``_clients`` interne plutôt que d'attendre BoucleRooms.
        """
        membres = [
            {
                "username": username,
                "room": "",
                "status": info.statut.name.lower() if info.statut.value != 0 else "unknown",
            }
            for username, info in self._clients.items()
            if info.statut != UserStatus.UNKNOWN
        ]
        self.lancer_ping(membres, force=True)

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
        """Un client a changé de statut (ONLINE/AWAY/OFFLINE).

        L'événement aioslsk expose ``before`` et ``current``, qui sont
        des objets ``User`` avec un attribut ``.name``.
        """
        username = evt.current.name
        nouveau = evt.current.status
        ancien = evt.before.status

        if username in self._clients:
            ancien = self._clients[username].statut
            self._clients[username].statut = nouveau
        else:
            # Nouveau client découvert via l'événement
            info = ClientInfo(username=username, statut=nouveau)
            self._clients[username] = info
            self.client_ajoute.emit(username)

        self.client_statut_change.emit(username, nouveau, ancien)
        logger.debug("Statut %s: %s -> %s", username, ancien.name if hasattr(ancien, 'name') else ancien, nouveau.name)

    def _on_user_info_update(self, evt: UserInfoUpdateEvent) -> None:
        """Les informations d'un client ont changé.

        L'événement aioslsk expose ``before`` et ``current``, qui sont
        des objets ``User`` avec les attributs métier directement.
        """
        username = evt.current.name
        if username not in self._clients:
            return

        info = self._clients[username]
        usr = evt.current

        # Mise à jour des champs disponibles depuis l'objet User
        if usr.description is not None:
            info.description = usr.description
        if usr.country is not None:
            info.pays = usr.country
        if usr.avg_speed is not None:
            info.vitesse = usr.avg_speed
        if usr.uploads is not None:
            info.uploads = usr.uploads
        if usr.shared_file_count is not None:
            info.fichiers_partages = usr.shared_file_count
        if usr.shared_folder_count is not None:
            info.dossiers_partages = usr.shared_folder_count
        if usr.slots_free is not None:
            info.slots_libres = usr.slots_free
        if usr.has_slots_free is not None:
            info.slots_libres_flag = usr.has_slots_free
        if usr.queue_length is not None:
            info.file_attente = usr.queue_length
        if usr.privileged is not None:
            info.privilege = usr.privileged

        self.client_info_change.emit(username)
        logger.debug("Info mise à jour pour %s", username)

    # ── Découverte passive d'utilisateurs ────────────────────────

    def _on_private_message(self, evt: PrivateMessageEvent) -> None:
        """Un utilisateur nous a envoyé un message privé → on le tracke.

        Le UserManager d'aioslsk tracke automatiquement l'expéditeur
        via son mécanisme interne. On n'a pas besoin de faire grand-chose
        ici — le simple fait de recevoir le message ajoute l'utilisateur
        à ``client.users.users``, qui sera récupéré au prochain cycle
        de BoucleRooms.
        """
        username = str(getattr(evt, "username", "") or getattr(evt.message, "username", ""))
        if not username:
            return

        # Si l'utilisateur n'est pas déjà tracké, l'ajouter immédiatement
        if username not in self._clients:
            info = ClientInfo(
                username=username,
                statut=UserStatus.ONLINE,  # Il nous parle → online
            )
            self._clients[username] = info
            self.client_ajoute.emit(username)
            # Ré-émettre la liste complète pour mettre à jour le tableau
            actifs = self.clients_actifs()
            self.clients_synchronises.emit(actifs)
            logger.debug("Nouvel utilisateur découvert via message privé : %s", username)

    def _on_connection_changed(self, connected: bool) -> None:
        """Déclenche le démarrage ou l'arrêt automatique selon l'état de la connexion."""
        if connected:
            self.demarrer()
        else:
            self.arreter()

    # ── Ping par lots ───────────────────────────────────────────────

    def lancer_ping(self, membres: list[dict], force: bool = False) -> None:
        """Déclenche le ping par lots sur la boucle asyncio du ConnexionManager.

        Cette méthode est appelée après réception des membres depuis
        BoucleRooms pour vérifier quels clients sont réellement joignables.
        Utilise ``ConnexionManager.run_coro()`` pour exécuter la coroutine
        sur la bonne boucle asyncio.

        Deux gardes évitent les pings trop fréquents ou inutiles :
        - **Espacement temporel** : au moins ``_INTERVALLE_PING_MIN`` secondes
          (5 minutes) entre deux pings.
        - **Flag dirty** : le hash des membres est comparé au précédent lot
          pingé. Si identique, le ping est ignoré (les membres n'ont pas changé).

        Quand ``force=True``, les deux gardes sont contournées (utilisé par
        le bouton 🔄 Rafraîchir).

        Paramètres
        ----------
        membres : list[dict]
            Liste des membres (username, room, status) provenant de BoucleRooms.
        force : bool
            Si True, ignore les gardes espacement + dirty. Par défaut False.
        """
        if self._ping_en_cours:
            logger.warning("Ping déjà en cours — ignoré")
            return

        if self._cm is None:
            logger.warning("ClientsActifsService: ConnexionManager non injecté — ping impossible")
            return

        if not force:
            # 1. Espacement temporel : 5 min minimum entre deux pings
            now = time.time()
            if now - self._dernier_ping < _INTERVALLE_PING_MIN:
                logger.debug(
                    "Ping espacement : dernier ping il y a %.0fs — ignoré",
                    now - self._dernier_ping,
                )
                EventBus().emit_event(
                    category="bot",
                    severity="INFO",
                    title="Ping ignoré (espacement)",
                    message=f"Dernier ping il y a {now - self._dernier_ping:.0f}s (min 300s)",
                    source="clients_actifs_service",
                )
                return

            # 2. Flag dirty : ne pinger que si la liste des membres a changé
            hash_courant = hash(frozenset(
                (m.get("username", ""), m.get("status", ""))
                for m in membres if m.get("username")
            ))
            if hash_courant == self._dernier_hash_membres:
                logger.debug("Ping dirty : membres identiques — ignoré")
                EventBus().emit_event(
                    category="bot",
                    severity="INFO",
                    title="Ping ignoré (dirty)",
                    message="Membres identiques au précédent ping",
                    source="clients_actifs_service",
                )
                return
            self._dernier_hash_membres = hash_courant

        self._dernier_ping = time.time()
        self._ping_en_cours = True

        EventBus().emit_event(
            category="bot",
            severity="INFO",
            title="Ping lancé",
            message=f"{len(membres)} candidats, force={'oui' if force else 'non'}",
            source="clients_actifs_service",
        )

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

        Enregistre les métriques de performance : temps d'exécution,
        nombre de candidats pingés et nombre de réponses.

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
        start_time = time.time()
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

        # Métriques
        duree = time.time() - start_time
        self._total_pings += total
        self._total_reponses += len(reponses)
        self._temps_total_ping += duree

        logger.info(
            "Ping terminé : %d/%d ont répondu (lots=%d, durée=%.1fs)",
            len(reponses), total, lots_total, duree,
        )
        self.ping_termine.emit(reponses)
        return reponses

    def _on_ingest_membres_rooms(self, membres: list[dict]) -> None:
        """Log et émet un événement après l'ingestion des membres Rooms."""
        EventBus().emit_event(
            category="bot",
            severity="INFO",
            title="Membres Rooms ingérés",
            message=f"{len(membres)} membres, {len(self._clients)} trackés",
            source="clients_actifs_service",
        )

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

        EventBus().emit_event(
            category="bot",
            severity="INFO",
            title="Ping terminé",
            message=f"{len(reponses)} réponses, {len(valides)} valides (ONLINE)",
            source="clients_actifs_service",
        )