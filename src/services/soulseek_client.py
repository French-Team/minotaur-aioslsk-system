from __future__ import annotations

import asyncio
import logging
from typing import Callable

from aioslsk.client import SoulSeekClient
from aioslsk.settings import CredentialsSettings, NetworkSettings, Settings, UpnpSettings

logger = logging.getLogger(__name__)


class SoulseekService:
    """
    Service wrapper autour de SoulSeekClient.
    Gère le cycle de vie du client et expose les événements.
    """

    def __init__(self) -> None:
        self._client: SoulSeekClient | None = None
        self._username: str = ""
        self._running: bool = False

    @property
    def client(self) -> SoulSeekClient | None:
        """Retourne l'instance du client, ou None si pas connecté."""
        return self._client

    @property
    def is_connected(self) -> bool:
        """Le client est-il connecté ?"""
        return self._client is not None and self._running

    @property
    def username(self) -> str:
        return self._username

    async def connect(self, username: str, password: str) -> str:
        """
        Connecte au serveur Soulseek.

        Args:
            username: Nom d'utilisateur Soulseek.
            password: Mot de passe Soulseek.

        Returns:
            Message de statut.

        Raises:
            Exception: Si la connexion échoue.
        """
        if self.is_connected:
            return f"Déjà connecté en tant que {self._username}"

        settings = Settings(
            credentials=CredentialsSettings(
                username=username,
                password=password,
            ),
            network=NetworkSettings(
                upnp=UpnpSettings(enabled=False),
            ),
        )

        self._client = SoulSeekClient(settings)
        self._username = username

        try:
            await self._client.start()
            await self._client.login()
            self._running = True
            logger.info("Connecté à Soulseek en tant que %s", username)
            return f"Connecté à Soulseek en tant que {username}"
        except Exception as e:
            self._running = False
            await self._cleanup_client()
            logger.error("Échec de connexion: %s", e)
            raise

    async def disconnect(self) -> str:
        """
        Déconnecte du serveur Soulseek.

        Returns:
            Message de statut.
        """
        if not self.is_connected:
            return "Pas de connexion active"

        self._running = False
        await self._cleanup_client()
        logger.info("Déconnecté de Soulseek")
        return "Déconnecté de Soulseek"

    async def _cleanup_client(self) -> None:
        """Nettoie le client."""
        if self._client is not None:
            try:
                await self._client.stop()
            except Exception as e:
                logger.warning("Erreur lors du cleanup du client: %s", e)
            self._client = None


# Instance globale partagée
soulseek_service = SoulseekService()
