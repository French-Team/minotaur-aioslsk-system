# pyrefly: ignore [missing-module-docstring]
# pyrefly: ignore [missing-class-docstring]

import logging

from PySide6.QtCore import QObject, QTimer, Signal

from src.services.connexion_manager import ConnexionManager

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

    # ── Cycle de la boucle ──

    def _executer_cycle(self) -> None:
        if self._cm is None:
            logger.warning("BoucleRooms: ConnexionManager non configuré")
            return
        self._cm.run_coro(self._async_cycle())

    async def _async_cycle(self) -> None:
        client = self._cm.client
        if client is None:
            return

        if not self._cm.is_connected:
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

        # 2. Rejoindre les 5 premières rooms (si pas déjà membre)
        for room_info in self._rooms_actuelles[:5]:
            name = room_info["name"]
            if name not in client.rooms.joined_rooms:
                try:
                    from aioslsk.commands import JoinRoomCommand

                    await client.execute(JoinRoomCommand(name))
                    logger.debug("Room %s rejointe", name)
                except Exception as e:
                    logger.warning("Impossible de rejoindre #%s : %s", name, e)

        # 3. Récupérer les membres des rooms rejointes
        membres = []
        for name in client.rooms.joined_rooms:
            room = client.rooms.rooms.get(name)
            if room:
                for user in room.users:
                    membres.append(
                        {"username": user.name, "room": name, "status": str(user.status)}
                    )

        self._membres_actifs = membres

        # 4. Émettre le signal → ClientsActifsService
        self.membres_actualises.emit(membres)
        logger.debug("BoucleRooms : %d membres récupérés", len(membres))

    @property
    def membres(self) -> list[dict]:
        return self._membres_actifs

    @property
    def rooms(self) -> list[dict]:
        return self._rooms_actuelles