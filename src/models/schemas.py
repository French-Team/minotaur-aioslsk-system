from __future__ import annotations

from pydantic import BaseModel


class ConnectRequest(BaseModel):
    """Requête de connexion au serveur Soulseek."""

    username: str
    password: str


class ConnectResponse(BaseModel):
    """Réponse après tentative de connexion."""

    success: bool
    message: str
    username: str | None = None


class StatusResponse(BaseModel):
    """Statut de la connexion au serveur Soulseek."""

    connected: bool
    username: str | None = None
    server: str | None = None
