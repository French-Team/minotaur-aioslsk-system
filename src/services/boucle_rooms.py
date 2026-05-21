# pyrefly: ignore [missing-module-docstring]
# pyrefly: ignore [missing-class-docstring]

import logging

from PySide6.QtCore import QObject, QTimer, Signal

from src.services.connexion_manager import ConnexionManager
from src.services.event_bus import EventBus

logger = logging.getLogger(__name__)


class BoucleRooms(QObject):
    # Signal de sortie vers ClientsActifsService
    membres_actualises = Signal(list)  # list[dict] — membres actifs

    def __init__(self, connexion_manager: ConnexionManager, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._cm = connexion_manager
        self._actif = False
        self._timer = QTimer(self)
        self._timer.setInterval(30_000)  # 30s
        self._timer.timeout.connect(self._executer_cycle)
        self._rooms_actuelles: list[dict] = []
        self._membres_actifs: list[dict] = []

    # ── Interrupteur ──

    def demarrer(self) -> None:
        if self._actif:
            logger.debug("BoucleRooms déjà active — ignoré")
            return
        self._actif = True
        self._executer_cycle()  # premier cycle immédiat
        self._timer.start()
        logger.info("BoucleRooms démarrée")

    def arreter(self) -> None:
        if not self._actif:
            logger.debug("BoucleRooms déjà inactive — ignoré")
            return
        self._actif = False
        self._timer.stop()
        logger.info("BoucleRooms arrêtée")

    @property
    def est_actif(self) -> bool:
        return self._actif

    def rafraichir(self) -> None:
        """Déclenche un cycle immédiat de collecte des rooms/membres.

        Appelée par le bouton Rafraîchir du widget Clients Actifs.
        Ré-exécute le cycle complet : lister les rooms, rejoindre
        le top 5, collecter les membres, émettre membres_actualises.

        Si la boucle était arrêtée, le timer est redémarré.
        """
        if not self._actif:
            logger.debug("BoucleRooms inactive — démarrage par rafraichir()")
            self.demarrer()
            return
        self._executer_cycle()

    def _emettre_evenement(self, titre: str, message: str) -> None:
        """Émet un événement sur l'EventBus pour le workflow inspector."""
        EventBus().emit_event(
            category="bot",
            severity="INFO",
            title=titre,
            message=message,
            source="boucle_rooms",
        )

    # ── Cycle de la boucle ──

    def _executer_cycle(self) -> None:
        if self._cm is None:
            logger.warning("BoucleRooms: ConnexionManager non configuré")
            return
        self._cm.run_coro(self._async_cycle())

    async def _async_cycle(self) -> None:
        try:
            client = self._cm.client
            if client is None:
                logger.warning("BoucleRooms: client None — cycle ignoré")
                return

            if not self._cm.is_connected:
                logger.debug("BoucleRooms: pas connecté — cycle ignoré")
                return

            # 1. Récupérer la liste des rooms publiques
            rooms = client.rooms.rooms
            self._rooms_actuelles = [
                {"name": name, "users": room.user_count}
                for name, room in rooms.items()
            ]

            # 1b. Trier par nombre de membres décroissant pour rejoindre
            #     les 5 rooms les plus peuplées (top 5)
            self._rooms_actuelles.sort(key=lambda r: r["users"], reverse=True)
            logger.debug("BoucleRooms: %d rooms trouvées", len(self._rooms_actuelles))

            # 2. Rejoindre les 5 premières rooms (si pas déjà membre)
            # ⚠️ joined_rooms n'existe PAS comme attribut — utiliser get_joined_rooms()
            joined_rooms = client.rooms.get_joined_rooms()
            joined_names = {room.name for room in joined_rooms}
            logger.debug("BoucleRooms: %d rooms déjà rejointes", len(joined_names))

            for room_info in self._rooms_actuelles[:5]:
                name = room_info["name"]
                if name not in joined_names:
                    try:
                        from aioslsk.commands import JoinRoomCommand

                        await client.execute(JoinRoomCommand(name))
                        joined_names.add(name)
                        logger.debug("Room %s rejointe", name)
                    except Exception as e:
                        logger.warning("Impossible de rejoindre #%s : %s", name, e)

            # 3. Collecter les utilisateurs trackés par le client (client.users.users)
            #    comme source PRINCIPALE — contrairement à room.users qui est vide
            #    pour les rooms publiques, client.users.users contient TOUS les
            #    utilisateurs que le client a rencontrés (via UserStatusUpdateEvent,
            #    PrivateMessageEvent, RoomMessageEvent, etc.).
            membres = []
            usernames_vus: set[str] = set()

            # Source A : client.users.users — tous les utilisateurs trackés
            tracked = client.users.users
            for username, user in tracked.items():
                membres.append({
                    "username": user.name,
                    "room": "",
                    "status": str(user.status) if hasattr(user, "status") else "UNKNOWN",
                })
                usernames_vus.add(user.name)

            # Source B : room.users des rooms rejointes — best-effort
            # Note : souvent vide pour les rooms publiques juste après JoinRoom,
            # mais peut contenir des membres si UserJoinedRoom events sont arrivés.
            for name in joined_names:
                room = client.rooms.rooms.get(name)
                if room and hasattr(room, "users"):
                    for user in room.users:
                        if user.name not in usernames_vus:
                            membres.append({
                                "username": user.name,
                                "room": name,
                                "status": str(getattr(user, "status", "UNKNOWN")),
                            })
                            usernames_vus.add(user.name)

            self._membres_actifs = membres

            # 4. Émettre le signal → ClientsActifsService
            self.membres_actualises.emit(membres)
            logger.debug(
                "BoucleRooms : %d membres récupérés (%d depuis client.users.users, %d depuis rooms)",
                len(membres),
                len(tracked),
                len(membres) - len(tracked),
            )

            # 5. Émettre un événement pour le workflow inspector
            if membres:
                self._emettre_evenement(
                    "Cycle Rooms exécuté",
                    f"{len(self._rooms_actuelles)} rooms, {len(membres)} membres",
                )
            else:
                self._emettre_evenement(
                    "Cycle Rooms : aucune room rejointe",
                    f"{len(self._rooms_actuelles)} rooms trouvées, {len(joined_names)} rejointes",
                )

        except AttributeError as ae:
            logger.exception("BoucleRooms: attribut inexistant sur aioslsk — %s", ae)
            self._emettre_evenement(
                "Cycle Rooms : erreur API",
                f"Attribut inexistant : {ae} — l'API aioslsk a peut-être changé",
            )
        except Exception as e:
            logger.exception("BoucleRooms: erreur inattendue dans _async_cycle — %s", e)
            self._emettre_evenement(
                "Cycle Rooms : erreur",
                f"Exception : {e}",
            )

    @property
    def membres(self) -> list[dict]:
        return self._membres_actifs

    @property
    def rooms(self) -> list[dict]:
        return self._rooms_actuelles