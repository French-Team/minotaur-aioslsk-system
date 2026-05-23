"""
Gestionnaire de connexion Soulseek — pont entre l'API asynchrone (aioslsk)
et l'interface Qt (PySide6).

Maintient un thread dédié avec sa propre boucle asyncio pour exécuter
les opérations réseau sans bloquer l'interface graphique.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
import string
import traceback
from concurrent.futures import Future
from threading import Event

from aioslsk.search.manager import SearchManager
from PySide6.QtCore import QObject, QThread, QTimer, Signal

import src.services.app_config as app_config
from src.services.error_translator import afficher, traduire
from src.services.event_bus import EventBus
from src.services.soulseek_client import soulseek_service

logger = logging.getLogger("[CONNEXION]")
diag_logger = logging.getLogger("[DIAG]")

# ── Constantes de dénichage ──────────────────────────────────────
_LOT_DENICHAGE = 5  # Nombre de clients interrogés par lot
_DELAI_LOT_DENICHAGE = 1.0  # Secondes entre chaque lot


# ── Utilitaires ─────────────────────────────────────────────────


def _generer_identifiants() -> tuple[str, str]:
    """Génère un nom d'utilisateur réaliste et un mot de passe aléatoires."""

    # ── Banques de mots ─────────────────────────────────────────────
    prenoms = [
        "Alex",
        "Ben",
        "Max",
        "Leo",
        "Jay",
        "Kim",
        "Sam",
        "Jules",
        "Tom",
        "Eli",
        "Zoe",
        "Mia",
        "Noa",
        "Lou",
        "Amy",
        "Eden",
        "Sasha",
        "Charlie",
        "Romy",
        "Enzo",
        "Nina",
        "Hugo",
        "Lena",
    ]
    musiques = [
        "Electro",
        "Techno",
        "Wave",
        "Beats",
        "Bass",
        "Mix",
        "Groove",
        "Pulse",
        "Rhythm",
        "Sound",
        "Drop",
        "Loop",
        "Vibes",
        "Flow",
        "Trance",
        "Pop",
        "Rock",
        "Jazz",
        "Funk",
        "Soul",
        "Punk",
        "Blues",
        "House",
        "Disco",
        "Reggae",
        "Metal",
        "Dub",
        "Step",
        "Swing",
        "Bop",
    ]
    adjectifs = [
        "Cool",
        "Fast",
        "Wild",
        "Neo",
        "Retro",
        "Ultra",
        "Mega",
        "Super",
        "Hyper",
        "Deep",
        "Dark",
        "Pure",
        "Acid",
        "Free",
        "Chill",
        "Raw",
        "Smooth",
        "Electric",
        "Lunar",
        "Solar",
    ]
    styles = [
        "Dance",
        "Techno",
        "Electro",
        "House",
        "Trance",
        "Dub",
        "Funk",
        "Jazz",
        "Retro",
        "Synth",
        "Digital",
        "Audio",
        "Sonic",
        "Wave",
        "Neo",
        "Acid",
        "Ambient",
        "Minimal",
    ]

    # ── Patterns de composition ──
    patterns: list[tuple[str, ...]] = [
        # Prénom + style musical
        *[(p, m) for p in prenoms for m in musiques[:12]],
        # Adjectif + style
        *[(a, s) for a in adjectifs[:10] for s in styles],
        # Deux styles (sans séparateur)
        *[(s1, s2) for s1 in styles[:8] for s2 in musiques[:8] if s1 != s2],
    ]

    mot1, mot2 = secrets.choice(patterns)

    # 30 % de chance d'ajouter un séparateur (tiret ou underscore)
    if secrets.randbelow(100) < 30:
        separateur = secrets.choice(["-", "_"])
        username = f"{mot1}{separateur}{mot2}"
    else:
        username = f"{mot1}{mot2}"

    # Parfois en minuscules (20 %)
    if secrets.randbelow(100) < 20:
        username = username.lower()

    password = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    return username, password


# ═══════════════════════════════════════════════════════════════════
#  Thread asynchrone
# ═══════════════════════════════════════════════════════════════════


class _AsyncEventLoopThread(QThread):
    """Thread Qt qui fait tourner une boucle asyncio.

    Permet d'exécuter des coroutines aioslsk sans bloquer le thread UI.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready_event = Event()

    def run(self) -> None:
        """Point d'entrée du thread — lance la boucle asyncio."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        # Planifier la notification APRÈS que run_forever() ait démarré
        # et que le self-pipe de la boucle soit créé. Sans cela, un appel
        # à call_soon_threadsafe() AVANT run_forever() lèverait une erreur
        # car le self-pipe n'existe pas encore.
        self._loop.call_soon(self._ready_event.set)
        try:
            self._loop.run_forever()
        finally:
            self._loop.close()

    def stop(self) -> None:
        """Arrête proprement la boucle et le thread."""
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.wait()

    def wait_ready(self, timeout: float = 2.0) -> None:
        """Attend que la boucle asyncio soit prête."""
        self._ready_event.wait(timeout)

    def run_coro(self, coro) -> Future:
        """Planifie une coroutine sur la boucle asyncio.

        Retourne un ``concurrent.futures.Future`` pour récupérer le résultat.
        """
        if self._loop is None:
            raise RuntimeError("La boucle asyncio n'est pas encore prête")
        return asyncio.run_coroutine_threadsafe(coro, self._loop)


# ═══════════════════════════════════════════════════════════════════
#  Gestionnaire de connexion
# ═══════════════════════════════════════════════════════════════════


class ConnexionManager(QObject):
    """Gère la connexion à Soulseek depuis l'interface Qt.

    Signaux émis (thread-safe — utiliser ``AutoConnection``) :

    * ``connected(username)``  — connexion réussie
    * ``disconnected()``       — déconnexion réussie
    * ``error_occurred(msg)``  — erreur survenue
    * ``generating(v)``        — début/fin de génération de compte
    * ``status_changed(msg)``  — message de statut quelconque
    """

    connected = Signal(str)
    disconnected = Signal()
    error_occurred = Signal(str)
    generating = Signal(bool)
    status_changed = Signal(str)
    search_result_received = Signal(object)  # SearchResultEvent

    # Signaux internes pour le diagnostic (thread-safe — émis depuis le thread async)
    _diag_timer_start = Signal()
    _diag_timer_stop = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        self._service = soulseek_service
        self._async_thread = _AsyncEventLoopThread(self)
        self._async_thread.start()
        self._async_thread.wait_ready()

        # Ticket de la dernière recherche en cours (None si aucune)
        self._current_search_ticket: int | None = None

        # Flag anti-connexions concurrentes
        self._connecting: bool = False

        # Annulation demandée par l'utilisateur pendant une connexion en cours
        self._cancel_requested: bool = False

        # Transférer les signaux du service
        self._service.search_result_received.connect(self.search_result_received.emit)

        # ── Diagnostic : tracer le flux complet de la recherche aioslsk ──────
        self._install_search_diagnostics()
        self._install_peer_search_diagnostics()

        # ── Timer de diagnostic : vérifie l'état du ticket toutes les 10s ──
        self._search_diag_timer = QTimer(self)
        self._search_diag_timer.setInterval(10_000)  # 10 secondes
        self._search_diag_timer.timeout.connect(self._diagnostic_check_search)

        # Connexion des signaux internes (thread-safe — Qt achemine automatiquement
        # les émissions depuis un thread secondaire vers le thread principal)
        self._diag_timer_start.connect(self._search_diag_timer.start)
        self._diag_timer_stop.connect(self._search_diag_timer.stop)

        # ── Connexion des signaux à l'EventBus ──
        self.connected.connect(
            lambda username: EventBus().emit_event(
                severity="INFO",
                category="reseau",
                title="Connecté à Soulseek",
                message=f"Connexion réussie en tant que {username}",
                source="ConnexionManager",
            )
        )
        self.disconnected.connect(
            lambda: EventBus().emit_event(
                severity="WARN",
                category="reseau",
                title="Déconnecté de Soulseek",
                message="Le client a été déconnecté du serveur",
                source="ConnexionManager",
            )
        )
        self.error_occurred.connect(
            lambda msg: EventBus().emit_event(
                severity="ERROR",
                category="reseau",
                title="Erreur de connexion",
                message=msg if len(msg) < 200 else msg[:200],
                source="ConnexionManager",
            )
        )
        self.status_changed.connect(
            lambda msg: None  # Ignoré — trop bavard pour l'EventBus
        )

        logger.info("[CONNEXION] ConnexionManager prêt (thread asyncio lancé)")

    # ── API publique ─────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self._service.is_connected

    @property
    def client(self) -> object | None:
        """Délègue à SoulseekService.client.

        Expose l'instance ``SoulSeekClient`` (ou None si pas connecté).
        Utilisé par BoucleRooms pour accéder à ``client.rooms``.
        """
        return self._service.client

    @property
    def username(self) -> str:
        return self._service.username

    def run_coro(self, coro) -> Future:
        """Planifie une coroutine sur la boucle asyncio du thread dédié.

        Délègue à ``_AsyncEventLoopThread.run_coro()``.
        Retourne un ``concurrent.futures.Future`` pour récupérer le résultat.
        """
        return self._async_thread.run_coro(coro)

    def search(self, query: str) -> None:
        """Lance une recherche Soulseek (broadcast réseau).

        Appel non-bloquant depuis le thread UI.
        Les résultats arrivent via ``search_result_received``.

        Note
        ----
        Préférer ``batched_search()`` qui interroge les clients actifs
        par lots de 5 au lieu de broadcast sur tout le réseau.
        """
        if not self.is_connected:
            self.error_occurred.emit("Pas connecté à Soulseek")
            return
        self._current_search_ticket = None
        self.status_changed.emit(f"Recherche : {query}")
        diag_logger.info("search('%s') — lancement", query)
        self._async_thread.run_coro(self._do_search(query))

    def batched_search(self, query: str, clients: list[str]) -> None:
        """Dénichage par lots — recherche ciblée chez N clients à la fois.

        Au lieu de broadcast sur tout le réseau (qui déclenche des
        centaines de connexions P2P simultanées), interroge les clients
        actifs par lots de 5 avec un délai entre chaque lot.

        Les résultats arrivent via ``search_result_received``.

        Paramètres
        ----------
        query : str
            Terme de recherche.
        clients : list[str]
            Liste des usernames des clients à interroger.
        """
        if not self.is_connected:
            self.error_occurred.emit("Pas connecté à Soulseek")
            return
        self._current_search_ticket = None
        nb_clients = len(clients)
        self.status_changed.emit(f"Dénichage : {query} chez {nb_clients} client(s)…")
        diag_logger.info("batched_search('%s') — %d clients (lots de %d)",
                         query, nb_clients, _LOT_DENICHAGE)
        self._async_thread.run_coro(self._do_batched_search(query, clients))

    def search_user(self, username: str, query: str) -> None:
        """Recherche les fichiers d'un utilisateur spécifique.

        Appel non-bloquant depuis le thread UI.
        Les résultats arrivent via ``search_result_received``.
        """
        if not self.is_connected:
            self.error_occurred.emit("Pas connecté à Soulseek")
            return
        self._current_search_ticket = None
        self.status_changed.emit(f"Recherche chez {username} : {query}")
        diag_logger.info("search_user('%s', '%s') — lancement", username, query)
        self._async_thread.run_coro(self._do_search_user(username, query))

    def search_room(self, room: str, query: str) -> None:
        """Recherche dans un salon spécifique.

        Appel non-bloquant depuis le thread UI.
        Les résultats arrivent via ``search_result_received``.
        """
        if not self.is_connected:
            self.error_occurred.emit("Pas connecté à Soulseek")
            return
        self._current_search_ticket = None
        self.status_changed.emit(f"Recherche dans #{room} : {query}")
        diag_logger.info("search_room('%s', '%s') — lancement", room, query)
        self._async_thread.run_coro(self._do_search_room(room, query))

    def join_room(self, room: str) -> None:
        """Rejoint un salon (room) Soulseek.

        Appel non-bloquant depuis le thread UI.
        """
        if not self.is_connected:
            self.error_occurred.emit("Pas connecté à Soulseek")
            return
        self.status_changed.emit(f"Rejoint le salon #{room}...")
        self._async_thread.run_coro(self._do_join_room(room))

    def leave_room(self, room: str) -> None:
        """Quitte un salon (room) Soulseek.

        Appel non-bloquant depuis le thread UI.
        """
        if not self.is_connected:
            self.error_occurred.emit("Pas connecté à Soulseek")
            return
        self.status_changed.emit(f"Quitte le salon #{room}...")
        self._async_thread.run_coro(self._do_leave_room(room))

    def stop_search(self) -> None:
        """Annule la recherche en cours.

        Appel non-bloquant depuis le thread UI.
        Si ``_current_search_ticket`` est None, ne fait rien.
        """
        if self._current_search_ticket is None:
            logger.info("[RECHERCHE] stop_search appelé mais aucune recherche active")
            return
        diag_logger.info("stop_search() appelé pour le ticket %s", self._current_search_ticket)
        self._diag_timer_stop.emit()
        self._async_thread.run_coro(self._do_stop_search())

    def block_user(self, username: str) -> None:
        """Ajoute un utilisateur à la liste noire.

        Met à jour la configuration persistante.
        Au prochain redémarrage, l'utilisateur sera bloqué.
        """
        bloque = app_config.get("utilisateurs.liste_bloques", "")
        if username in bloque:
            logger.info("[CONNEXION] Utilisateur déjà bloqué : %s", username)
            return
        if bloque:
            bloque += f", {username}"
        else:
            bloque = username
        app_config.set("utilisateurs.liste_bloques", bloque)
        logger.info("[CONNEXION] Utilisateur bloqué : %s", username)
        self.status_changed.emit(f"🚫 Utilisateur {username} bloqué")

    def login(self, username: str, password: str) -> None:
        """Connecte au serveur Soulseek.

        Appel non-bloquant depuis le thread UI.
        """
        if self._connecting:
            logger.warning("[CONNEXION] Connexion déjà en cours — ignoré")
            self.error_occurred.emit("Connexion déjà en cours...")
            return
        if self._service.is_connected:
            self.status_changed.emit("Déjà connecté")
            return
        self._connecting = True
        self.status_changed.emit("Connexion en cours…")
        self._async_thread.run_coro(self._do_login(username, password))

    def auto_login(self) -> None:
        """Tente une reconnexion auto avec les credentials stockés.

        Vérifie d'abord le flag ``general.connexion_automatique`` dans la config.
        N'est appelé que si ce flag est True (checkbox cochée ou config activée).
        """
        if not app_config.get("general.connexion_automatique", False):
            logger.debug("[CONNEXION] Connexion automatique désactivée dans la config — skip auto_login")
            return
        username = app_config.get("reseau.nom_utilisateur", "")
        password = app_config.get("reseau.mot_de_passe", "")
        if username and password:
            logger.info("[CONNEXION] Reconnexion auto détectée pour : %s", username)
            self.status_changed.emit("Reconnexion automatique…")
            if self._connecting:
                logger.warning("[CONNEXION] auto_login: connexion déjà en cours — ignoré")
                return
            self._connecting = True
            self._async_thread.run_coro(self._do_login(username, password))
        else:
            logger.debug("[CONNEXION] Aucun credentials stockés — pas de reconnexion auto")

    def generate_account(self) -> None:
        """Génère des identifiants aléatoires et tente de se connecter.

        Soulseek crée automatiquement le compte si le nom n'existe pas.
        """
        if self._connecting:
            logger.warning("[CONNEXION] Génération de compte déjà en cours — ignoré")
            self.error_occurred.emit("Connexion déjà en cours...")
            return
        self._connecting = True
        self.generating.emit(True)
        self.status_changed.emit("Génération d'un nouveau compte…")
        self._async_thread.run_coro(self._do_generate())

    # pyrefly: ignore [bad-override]
    def disconnect(self) -> None:
        """Déconnecte du serveur Soulseek."""
        if self._connecting:
            logger.info("[CONNEXION] Annulation de la connexion en cours demandée par l'utilisateur")
            self._connecting = False
            self._cancel_requested = True
            self.status_changed.emit("Annulation de la connexion…")
            return
        self.status_changed.emit("Déconnexion…")
        self._async_thread.run_coro(self._do_disconnect())

    def shutdown(self) -> None:
        """Arrête proprement le thread asyncio (appel à la fermeture)."""
        logger.info("[CONNEXION] Arrêt du ConnexionManager…")
        if self._service.is_connected:
            future = self._async_thread.run_coro(self._do_disconnect())
            try:
                future.result(timeout=5)
            except Exception as e:
                logger.warning("[CONNEXION] Erreur lors de la déconnexion finale: %s", e)
        self._async_thread.stop()
        logger.info("[CONNEXION] ConnexionManager arrêté")

    # ── Diagnostic de la recherche ────────────────────────────────

    @staticmethod
    def _install_peer_search_diagnostics() -> None:
        """Patche aioslsk SearchManager._on_peer_search_reply avec agrégation.

        Accumule les stats des PeerSearchReply en mémoire et logue un résumé
        toutes les 30s. Seules les anomalies (ticket absent, exception) sont
        loguées immédiatement au niveau WARNING/ERROR.

        ATTENTION : le décorateur @on_message() pose l'attribut
        ``_registered_message`` sur la fonction. ``build_message_map()``
        inspecte les méthodes avec inspect.ismethod et filtre sur
        cet attribut. Notre fonction de remplacement DOIT donc le
        conserver, sinon le message ne sera plus dispatché du tout.
        """
        import threading

        original = SearchManager._on_peer_search_reply

        # Agrégateur de stats (closure thread-safe car mono-producteur)
        stats = {
            "total": 0,
            "present": 0,
            "absent": 0,
            "no_ticket": 0,
            "last_ticket": None,
            "last_username": None,
        }

        # Timer de résumé périodique — se réarme automatiquement
        _summary_timer: list[threading.Timer | None] = [None]

        def _flush_summary() -> None:
            total = stats["total"]
            if total > 0:
                diag_logger.info(
                    "[RÉSUMÉ] PeerSearchReply: %d reçus "
                    "(%d ✅ présent, %d ❌ absent, %d sans ticket) | "
                    "dernier ticket=%s, pair=%s",
                    total,
                    stats["present"],
                    stats["absent"],
                    stats["no_ticket"],
                    stats["last_ticket"],
                    stats["last_username"],
                )
                # Réarmer le timer seulement si une recherche est active
                _summary_timer[0] = threading.Timer(30.0, _flush_summary)
                _summary_timer[0].daemon = True
                _summary_timer[0].start()

        async def patched_on_peer_search_reply(self_sm, message, connection):
            ticket = getattr(message, "ticket", None)
            username = getattr(message, "username", "?")

            # Mise à jour des stats
            stats["total"] += 1
            stats["last_ticket"] = ticket
            stats["last_username"] = username

            if ticket is not None:
                present = ticket in self_sm.requests
                if present:
                    stats["present"] += 1
                else:
                    stats["absent"] += 1
                    # ⚠️ Anomalie immédiate : ticket manquant
                    diag_logger.warning(
                        "⚠️ ticket %s ABSENT dans self.requests (%d requête(s)) — pair=%s",
                        ticket, len(self_sm.requests), username,
                    )
            else:
                stats["no_ticket"] += 1

            # Appel original
            try:
                await original(self_sm, message, connection)
            except Exception as e:
                diag_logger.error(
                    "⚠️ _on_peer_search_reply EXCEPTION: %s (ticket=%s)",
                    e, ticket, exc_info=True,
                )
                raise

        # ⚠️ CRITIQUE : copier _registered_message pour que build_message_map()
        #    retrouve cette méthode dans le dispatch !
        orig_msg_attr = getattr(original, "_registered_message", None)
        if orig_msg_attr is not None:
            patched_on_peer_search_reply._registered_message = orig_msg_attr

        SearchManager._on_peer_search_reply = patched_on_peer_search_reply

        # Démarrer le timer de résumé périodique
        _summary_timer[0] = threading.Timer(30.0, _flush_summary)
        _summary_timer[0].daemon = True
        _summary_timer[0].start()

        diag_logger.info(
            "[DIAG] SearchManager._on_peer_search_reply patché (agrégé toutes les 30s)"
        )

    @staticmethod
    def _install_search_diagnostics() -> None:
        """Patche SearchManager.remove_request pour tracer les annulations.

        Seulement logué au niveau WARNING (événement rare).
        Le patcher _on_message_received a été retiré car trop bavard.
        """
        original = SearchManager.remove_request

        async def patched_remove_request(self_sm, request):
            ticket = request if isinstance(request, int) else request.ticket
            diag_logger.warning(
                "remove_request(%s) — recherche annulée ou expirée", ticket
            )
            return await original(self_sm, request)

        SearchManager.remove_request = patched_remove_request
        diag_logger.info("[DIAG] SearchManager.remove_request patché")

    def _diagnostic_check_search(self) -> None:
        """Vérifie périodiquement l'état du ticket de recherche (timer 10s).

        Exécuté dans le thread UI (QTimer). Vérifie la présence du ticket
        dans ``client.searches.requests``.
        """
        ticket = self._current_search_ticket
        if ticket is None:
            return

        client = self._service.client
        if client is None:
            diag_logger.warning("client None — recherche interrompue")
            self._search_diag_timer.stop()
            return

        # Vérification 1 : ticket présent dans requests
        requests = getattr(client.searches, "requests", None)
        if requests is None:
            diag_logger.warning("client.searches.requests introuvable")
            return

        present = ticket in requests
        nb_tickets = len(requests)

        if present:
            diag_logger.debug("ticket %s ✅ présent dans self.requests (%d requête(s) active(s))",
                         ticket, nb_tickets)
        else:
            diag_logger.error("❌ TICKET %s MANQUANT dans self.requests ! (%d requête(s) active(s))",
                         ticket, nb_tickets)
            diag_logger.error("Tickets actifs : %s", list(requests.keys()))
            # Arrêter le diagnostic — le ticket est perdu
            self._search_diag_timer.stop()



    # ── Coroutines internes (exécutées dans le thread asyncio) ──

    async def _do_login(self, username: str, password: str) -> None:
        """Tente de se connecter avec les identifiants fournis.

        Utilise un timeout de 30s (comme _do_generate) pour éviter de
        bloquer la boucle asyncio si le serveur ne répond pas.
        """
        try:
            msg = await asyncio.wait_for(
                self._service.connect(username, password),
                timeout=30.0,
            )

            # Vérifier si l'utilisateur a demandé l'annulation pendant la connexion
            if self._cancel_requested:
                self._cancel_requested = False
                logger.info("[LOGIN] Connexion annulée par l'utilisateur après login réussi — déconnexion")
                await self._service.disconnect()
                self.status_changed.emit("Connexion annulée")
                return

            logger.info("[LOGIN] Connexion réussie: %s", username)
            # Sauvegarder les credentials pour reconnexion auto
            app_config.set("reseau.nom_utilisateur", username)
            app_config.set("reseau.mot_de_passe", password)
            self.connected.emit(username)
            self.status_changed.emit(msg)

            # Récupérer la liste des salons publics au démarrage sans bloquer le login
            try:
                from aioslsk.commands import GetRoomListCommand
                asyncio.create_task(self._service.client.execute(GetRoomListCommand()))
                logger.info("[CONNEXION] Liste des salons demandée au serveur")
            except Exception as re:
                logger.warning("[CONNEXION] Impossible de récupérer la liste des salons : %s", re)
        except asyncio.TimeoutError:
            logger.error("[CONNEXION] Délai de connexion dépassé (30s) — serveur injoignable")
            self.error_occurred.emit("⏱️ Délai de connexion dépassé. Le serveur Soulseek est peut-être injoignable.")
        except Exception as e:
            message, _ = traduire(e)
            logger.error("[LOGIN] %s", afficher(e))
            self.error_occurred.emit(message)
        finally:
            self._connecting = False

    async def _do_generate(self) -> None:
        """Génère un compte et se connecte."""
        try:
            username, password = _generer_identifiants()
            logger.info("[LOGIN] Tentative de connexion avec le nouveau compte: %s", username)
            await asyncio.wait_for(
                self._service.connect(username, password),
                timeout=30.0,
            )
            logger.info("[LOGIN] Compte créé et connecté: %s", username)
            # Sauvegarder les credentials pour reconnexion auto
            app_config.set("reseau.nom_utilisateur", username)
            app_config.set("reseau.mot_de_passe", password)
            self.connected.emit(username)
            self.generating.emit(False)
            self.status_changed.emit(f"✅ Nouveau compte créé — {username}")
            
            # Récupérer la liste des salons publics au démarrage sans bloquer le login
            try:
                from aioslsk.commands import GetRoomListCommand
                asyncio.create_task(self._service.client.execute(GetRoomListCommand()))
                logger.info("[CONNEXION] Liste des salons demandée au serveur")
            except Exception as re:
                logger.warning("[CONNEXION] Impossible de récupérer la liste des salons : %s", re)
        except asyncio.TimeoutError:
            logger.error("[CONNEXION] Délai de connexion dépassé (30s) — serveur injoignable")
            self.error_occurred.emit("⏱️ Délai de connexion dépassé. Le serveur Soulseek est peut-être injoignable.")
            self.generating.emit(False)
        except Exception as e:
            message, _ = traduire(e)
            logger.error("[LOGIN] %s", afficher(e))
            self.error_occurred.emit(message)
            self.generating.emit(False)
        finally:
            self._connecting = False

    async def _do_search(self, query: str) -> None:
        """Exécute une recherche broadcast dans le thread asyncio."""
        try:
            client = self._service.client
            if client is None:
                self.error_occurred.emit("Client non initialisé")
                return
            request = await client.searches.search(query)
            self._current_search_ticket = request.ticket
            nb_tickets = len(client.searches.requests)
            diag_logger.info("Recherche lancée : '%s' (ticket %s, %d requête(s) active(s) dans aioslsk)",
                        query, request.ticket, nb_tickets)
            self._diag_timer_start.emit()
        except Exception as e:
            message, _ = traduire(e)
            diag_logger.error("Erreur lors du lancement de la recherche : %s", afficher(e))
            self._diag_timer_stop.emit()
            self.error_occurred.emit(f"Erreur de recherche : {message}")

    async def _do_batched_search(self, query: str, clients: list[str]) -> None:
        """Exécute un dénichage par lots de clients actifs.

        Découpe la liste en lots de ``_LOT_DENICHAGE`` et interroge
        chaque client via ``search_user()``. Un délai constant entre
        chaque lot évite de saturer le réseau.
        """
        total = len(clients)
        if total == 0:
            return

        try:
            client = self._service.client
            if client is None:
                self.error_occurred.emit("Client non initialisé")
                return

            for i in range(0, total, _LOT_DENICHAGE):
                batch = clients[i:i + _LOT_DENICHAGE]
                lot_num = i // _LOT_DENICHAGE + 1
                lots_total = (total - 1) // _LOT_DENICHAGE + 1

                diag_logger.info(
                    "Dénichage lot %d/%d : %s", lot_num, lots_total, batch,
                )

                # Interroger le lot en parallèle
                tasks = [client.searches.search_user(u, query) for u in batch]
                await asyncio.gather(*tasks)

                # Pause entre les lots (sauf dernier)
                if i + _LOT_DENICHAGE < total:
                    await asyncio.sleep(_DELAI_LOT_DENICHAGE)

        except Exception as e:
            diag_logger.error("Erreur lors du dénichage : %s", e, exc_info=True)
            self.error_occurred.emit(f"Erreur dénichage : {str(e)[:100]}")

    async def _do_search_user(self, username: str, query: str) -> None:
        """Recherche les fichiers d'un utilisateur spécifique."""
        try:
            client = self._service.client
            if client is None:
                self.error_occurred.emit("Client non initialisé")
                return
            request = await client.searches.search_user(username, query)
            self._current_search_ticket = request.ticket
            nb_tickets = len(client.searches.requests)
            diag_logger.info("Recherche chez %s : '%s' (ticket %s, %d requête(s) active(s))",
                        username, query, request.ticket, nb_tickets)
            self._diag_timer_start.emit()
        except Exception as e:
            message, _ = traduire(e)
            diag_logger.error("Erreur recherche utilisateur : %s", afficher(e))
            self._diag_timer_stop.emit()
            self.error_occurred.emit(f"Erreur de recherche utilisateur : {message}")

    async def _do_search_room(self, room: str, query: str) -> None:
        """Recherche dans un salon spécifique."""
        try:
            client = self._service.client
            if client is None:
                self.error_occurred.emit("Client non initialisé")
                return
            request = await client.searches.search_room(room, query)
            self._current_search_ticket = request.ticket
            nb_tickets = len(client.searches.requests)
            diag_logger.info("Recherche dans #%s : '%s' (ticket %s, %d requête(s) active(s))",
                        room, query, request.ticket, nb_tickets)
            self._diag_timer_start.emit()
        except Exception as e:
            message, _ = traduire(e)
            diag_logger.error("Erreur recherche salon : %s", afficher(e))
            self._diag_timer_stop.emit()
            self.error_occurred.emit(f"Erreur de recherche dans le salon : {message}")

    async def _do_join_room(self, room: str) -> None:
        """Exécute la commande de rejoindre un salon."""
        try:
            client = self._service.client
            if client is None:
                self.error_occurred.emit("Client non initialisé")
                return
            from aioslsk.commands import JoinRoomCommand
            await client.execute(JoinRoomCommand(room))
            logger.info("[CONNEXION] Salon #%s rejoint avec succès", room)
        except Exception as e:
            message, _ = traduire(e)
            logger.error("[CONNEXION] Erreur lors de la tentative de rejoindre #%s: %s", room, message)
            self.error_occurred.emit(f"Impossible de rejoindre #{room} : {message}")

    async def _do_leave_room(self, room: str) -> None:
        """Exécute la commande de quitter un salon."""
        try:
            client = self._service.client
            if client is None:
                self.error_occurred.emit("Client non initialisé")
                return
            from aioslsk.commands import LeaveRoomCommand
            await client.execute(LeaveRoomCommand(room))
            logger.info("[CONNEXION] Salon #%s quitté avec succès", room)
        except Exception as e:
            message, _ = traduire(e)
            logger.error("[CONNEXION] Erreur lors de la tentative de quitter #%s: %s", room, message)
            self.error_occurred.emit(f"Impossible de quitter #{room} : {message}")

    async def _do_stop_search(self) -> None:
        """Annule la recherche en cours dans le thread asyncio."""
        ticket = self._current_search_ticket
        if ticket is None:
            return
        try:
            client = self._service.client
            if client is None:
                return
            diag_logger.info("Appel de remove_request(%s) depuis _do_stop_search", ticket)
            await client.searches.remove_request(ticket)
            self._current_search_ticket = None
            self._diag_timer_stop.emit()
            logger.info("[RECHERCHE] Recherche annulée (ticket %s)", ticket)

        except Exception as e:
            message, _ = traduire(e)
            logger.warning("[RECHERCHE] Erreur lors de l'annulation de la recherche: %s", message)

    async def _do_disconnect(self) -> None:
        """Déconnecte du serveur."""
        try:
            msg = await asyncio.wait_for(
                self._service.disconnect(),
                timeout=10.0,
            )
            self.disconnected.emit()
            self.status_changed.emit(msg)
        except asyncio.TimeoutError:
            logger.warning("[CONNEXION] Délai de déconnexion dépassé (10s)")
        except Exception as e:
            logger.warning("[CONNEXION] Erreur lors de la déconnexion: %s", e)
