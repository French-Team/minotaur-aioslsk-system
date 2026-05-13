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

def _generer_identifiants(longueur: int = 10) -> tuple[str, str]:
    """Génère un nom d'utilisateur et un mot de passe aléatoires."""
    alphabet = string.ascii_lowercase + string.digits
    username = "slsk_" + "".join(secrets.choice(alphabet) for _ in range(longueur))
    password = "".join(secrets.choice(alphabet + string.ascii_uppercase) for _ in range(12))
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

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        self._service = SoulseekService()
        self._async_thread = _AsyncEventLoopThread(self)
        self._async_thread.start()
        self._async_thread.wait_ready()

        logger.info("ConnexionManager prêt (thread asyncio lancé)")

    # ── API publique ─────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self._service.is_connected

    @property
    def username(self) -> str:
        return self._service.username

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
            msg = await self._service.connect(username, password)
            logger.info("Compte créé et connecté: %s", username)
            self.connected.emit(username)
            self.status_changed.emit(
                f"✅ Nouveau compte créé — {username}"
            )
        except Exception as e:
            message, _ = traduire(e)
            logger.error(afficher(e))
            self.error_occurred.emit(message)
            self.generating.emit(False)

    async def _do_disconnect(self) -> None:
        """Déconnecte du serveur."""
        try:
            msg = await self._service.disconnect()
            self.disconnected.emit()
            self.status_changed.emit(msg)
        except Exception as e:
            logger.warning("Erreur lors de la déconnexion: %s", e)
