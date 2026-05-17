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
from concurrent.futures import Future
from threading import Event

from PySide6.QtCore import QObject, QThread, Signal

import src.services.app_config as app_config
from src.services.error_translator import afficher, traduire
from src.services.event_bus import EventBus
from src.services.soulseek_client import soulseek_service

logger = logging.getLogger(__name__)


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
        self._ready_event.set()  # la boucle est prête
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

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        self._service = soulseek_service
        self._async_thread = _AsyncEventLoopThread(self)
        self._async_thread.start()
        self._async_thread.wait_ready()

        # Ticket de la dernière recherche en cours (None si aucune)
        self._current_search_ticket: int | None = None

        # Transférer les signaux du service
        self._service.search_result_received.connect(self.search_result_received.emit)

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

        logger.info("ConnexionManager prêt (thread asyncio lancé)")

    # ── API publique ─────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self._service.is_connected

    @property
    def username(self) -> str:
        return self._service.username

    def search(self, query: str) -> None:
        """Lance une recherche Soulseek.

        Appel non-bloquant depuis le thread UI.
        Les résultats arrivent via ``search_result_received``.
        """
        if not self.is_connected:
            self.error_occurred.emit("Pas connecté à Soulseek")
            return
        self._current_search_ticket = None
        self.status_changed.emit(f"Recherche : {query}")
        self._async_thread.run_coro(self._do_search(query))

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
        self._async_thread.run_coro(self._do_search_room(room, query))

    def stop_search(self) -> None:
        """Annule la recherche en cours.

        Appel non-bloquant depuis le thread UI.
        Si ``_current_search_ticket`` est None, ne fait rien.
        """
        if self._current_search_ticket is None:
            logger.info("stop_search appelé mais aucune recherche active")
            return
        self._async_thread.run_coro(self._do_stop_search())

    def block_user(self, username: str) -> None:
        """Ajoute un utilisateur à la liste noire.

        Met à jour la configuration persistante.
        Au prochain redémarrage, l'utilisateur sera bloqué.
        """
        bloque = app_config.get("utilisateurs.liste_bloques", "")
        if username in bloque:
            logger.info("Utilisateur déjà bloqué : %s", username)
            return
        if bloque:
            bloque += f", {username}"
        else:
            bloque = username
        app_config.set("utilisateurs.liste_bloques", bloque)
        logger.info("Utilisateur bloqué : %s", username)
        self.status_changed.emit(f"🚫 Utilisateur {username} bloqué")

    def login(self, username: str, password: str) -> None:
        """Connecte au serveur Soulseek.

        Appel non-bloquant depuis le thread UI.
        """
        self.status_changed.emit("Connexion en cours…")
        self._async_thread.run_coro(self._do_login(username, password))

    def auto_login(self) -> None:
        """Tente une reconnexion auto avec les credentials stockés.

        Vérifie d'abord le flag ``general.connexion_automatique`` dans la config.
        N'est appelé que si ce flag est True (checkbox cochée ou config activée).
        """
        if not app_config.get("general.connexion_automatique", False):
            logger.debug("Connexion automatique désactivée dans la config — skip auto_login")
            return
        username = app_config.get("reseau.nom_utilisateur", "")
        password = app_config.get("reseau.mot_de_passe", "")
        if username and password:
            logger.info("Reconnexion auto détectée pour : %s", username)
            self.status_changed.emit("Reconnexion automatique…")
            self._async_thread.run_coro(self._do_login(username, password))
        else:
            logger.debug("Aucun credentials stockés — pas de reconnexion auto")

    def generate_account(self) -> None:
        """Génère des identifiants aléatoires et tente de se connecter.

        Soulseek crée automatiquement le compte si le nom n'existe pas.
        """
        self.generating.emit(True)
        self.status_changed.emit("Génération d'un nouveau compte…")
        self._async_thread.run_coro(self._do_generate())

    def disconnect(self) -> None:
        """Déconnecte du serveur Soulseek."""
        self.status_changed.emit("Déconnexion…")
        self._async_thread.run_coro(self._do_disconnect())

    def shutdown(self) -> None:
        """Arrête proprement le thread asyncio (appel à la fermeture)."""
        logger.info("Arrêt du ConnexionManager…")
        if self._service.is_connected:
            future = self._async_thread.run_coro(self._do_disconnect())
            try:
                future.result(timeout=5)
            except Exception as e:
                logger.warning("Erreur lors de la déconnexion finale: %s", e)
        self._async_thread.stop()
        logger.info("ConnexionManager arrêté")

    # ── Coroutines internes (exécutées dans le thread asyncio) ──

    async def _do_login(self, username: str, password: str) -> None:
        """Tente de se connecter avec les identifiants fournis."""
        try:
            msg = await self._service.connect(username, password)
            logger.info("Connexion réussie: %s", username)
            # Sauvegarder les credentials pour reconnexion auto
            app_config.set("reseau.nom_utilisateur", username)
            app_config.set("reseau.mot_de_passe", password)
            self.connected.emit(username)
            self.status_changed.emit(msg)
        except Exception as e:
            message, _ = traduire(e)
            logger.error(afficher(e))
            self.error_occurred.emit(message)

    async def _do_generate(self) -> None:
        """Génère un compte et se connecte."""
        try:
            username, password = _generer_identifiants()
            logger.info("Tentative de connexion avec le nouveau compte: %s", username)
            msg = await asyncio.wait_for(
                self._service.connect(username, password),
                timeout=30.0,
            )
            logger.info("Compte créé et connecté: %s", username)
            # Sauvegarder les credentials pour reconnexion auto
            app_config.set("reseau.nom_utilisateur", username)
            app_config.set("reseau.mot_de_passe", password)
            self.connected.emit(username)
            self.generating.emit(False)
            self.status_changed.emit(f"✅ Nouveau compte créé — {username}")
        except TimeoutError:
            logger.error("Délai de connexion dépassé (30s) — serveur injoignable")
            self.error_occurred.emit("⏱️ Délai de connexion dépassé. Le serveur Soulseek est peut-être injoignable.")
            self.generating.emit(False)
        except Exception as e:
            message, _ = traduire(e)
            logger.error(afficher(e))
            self.error_occurred.emit(message)
            self.generating.emit(False)

    async def _do_search(self, query: str) -> None:
        """Exécute une recherche dans le thread asyncio."""
        try:
            client = self._service.client
            if client is None:
                self.error_occurred.emit("Client non initialisé")
                return
            request = await client.searches.search(query)
            self._current_search_ticket = request.ticket
            logger.info("Recherche lancée : '%s' (ticket %s)", query, request.ticket)
        except Exception as e:
            message, _ = traduire(e)
            logger.error(afficher(e))
            self.error_occurred.emit(f"Erreur de recherche : {message}")

    async def _do_search_user(self, username: str, query: str) -> None:
        """Recherche les fichiers d'un utilisateur spécifique."""
        try:
            client = self._service.client
            if client is None:
                self.error_occurred.emit("Client non initialisé")
                return
            request = await client.searches.search_user(username, query)
            self._current_search_ticket = request.ticket
            logger.info("Recherche chez %s : '%s' (ticket %s)", username, query, request.ticket)
        except Exception as e:
            message, _ = traduire(e)
            logger.error(afficher(e))
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
            logger.info("Recherche dans #%s : '%s' (ticket %s)", room, query, request.ticket)
        except Exception as e:
            message, _ = traduire(e)
            logger.error(afficher(e))
            self.error_occurred.emit(f"Erreur de recherche dans le salon : {message}")

    async def _do_stop_search(self) -> None:
        """Annule la recherche en cours dans le thread asyncio."""
        ticket = self._current_search_ticket
        if ticket is None:
            return
        try:
            client = self._service.client
            if client is None:
                return
            await client.searches.remove_request(ticket)
            self._current_search_ticket = None
            logger.info("Recherche annulée (ticket %s)", ticket)
        except Exception as e:
            message, _ = traduire(e)
            logger.warning("Erreur lors de l'annulation: %s", message)

    async def _do_disconnect(self) -> None:
        """Déconnecte du serveur."""
        try:
            msg = await self._service.disconnect()
            self.disconnected.emit()
            self.status_changed.emit(msg)
        except Exception as e:
            logger.warning("Erreur lors de la déconnexion: %s", e)
