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

from src.services.error_translator import traduire, afficher
from src.services.soulseek_client import SoulseekService

logger = logging.getLogger(__name__)


# ── Utilitaires ─────────────────────────────────────────────────

def _generer_identifiants() -> tuple[str, str]:
    """Génère un nom d'utilisateur réaliste et un mot de passe aléatoires."""

    # ── Banques de mots ─────────────────────────────────────────────
    prenoms = [
        "Alex", "Ben", "Max", "Leo", "Jay", "Kim", "Sam", "Jules",
        "Tom", "Eli", "Zoe", "Mia", "Noa", "Lou", "Amy", "Eden",
        "Sasha", "Charlie", "Romy", "Enzo", "Nina", "Hugo", "Lena",
    ]
    musiques = [
        "Electro", "Techno", "Wave", "Beats", "Bass", "Mix",
        "Groove", "Pulse", "Rhythm", "Sound", "Drop", "Loop",
        "Vibes", "Flow", "Trance", "Pop", "Rock", "Jazz",
        "Funk", "Soul", "Punk", "Blues", "House", "Disco",
        "Reggae", "Metal", "Dub", "Step", "Swing", "Bop",
    ]
    adjectifs = [
        "Cool", "Fast", "Wild", "Neo", "Retro", "Ultra", "Mega",
        "Super", "Hyper", "Deep", "Dark", "Pure", "Acid", "Free",
        "Chill", "Raw", "Smooth", "Electric", "Lunar", "Solar",
    ]
    styles = [
        "Dance", "Techno", "Electro", "House", "Trance", "Dub",
        "Funk", "Jazz", "Retro", "Synth", "Digital", "Audio",
        "Sonic", "Wave", "Neo", "Acid", "Ambient", "Minimal",
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

    password = "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(12)
    )
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

        self._service = SoulseekService()
        self._async_thread = _AsyncEventLoopThread(self)
        self._async_thread.start()
        self._async_thread.wait_ready()

        # Transférer les signaux du service
        self._service.search_result_received.connect(
            self.search_result_received.emit
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
        self.status_changed.emit(f"Recherche : {query}")
        self._async_thread.run_coro(self._do_search(query))

    def login(self, username: str, password: str) -> None:
        """Connecte au serveur Soulseek.

        Appel non-bloquant depuis le thread UI.
        """
        self.status_changed.emit("Connexion en cours…")
        self._async_thread.run_coro(self._do_login(username, password))

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
            self.connected.emit(username)
            self.generating.emit(False)
            self.status_changed.emit(
                f"✅ Nouveau compte créé — {username}"
            )
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
            await client.searches.search(query)
            logger.info("Recherche lancée : '%s'", query)
        except Exception as e:
            message, _ = traduire(e)
            logger.error(afficher(e))
            self.error_occurred.emit(f"Erreur de recherche : {message}")

    async def _do_disconnect(self) -> None:
        """Déconnecte du serveur."""
        try:
            msg = await self._service.disconnect()
            self.disconnected.emit()
            self.status_changed.emit(msg)
        except Exception as e:
            logger.warning("Erreur lors de la déconnexion: %s", e)
