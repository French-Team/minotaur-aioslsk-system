from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from src.models import ConnectRequest, ConnectResponse, StatusResponse
from src.services.soulseek_client import soulseek_service

logger = logging.getLogger("[CONNEXION-WEB]")

router = APIRouter(prefix="/api", tags=["connection"])


@router.post("/connect", response_model=ConnectResponse)
async def connect(body: ConnectRequest) -> ConnectResponse:
    """
    Connecte au serveur Soulseek avec les identifiants fournis.

    Le client doit être déconnecté avant d'appeler cet endpoint.
    """
    try:
        message = await soulseek_service.connect(
            username=body.username,
            password=body.password,
        )
        return ConnectResponse(
            success=True,
            message=message,
            username=body.username,
        )
    except Exception as e:
        logger.error("Erreur de connexion: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"Impossible de se connecter à Soulseek: {e}",
        )


@router.post("/disconnect", response_model=ConnectResponse)
async def disconnect() -> ConnectResponse:
    """Déconnecte du serveur Soulseek."""
    try:
        message = await soulseek_service.disconnect()
        return ConnectResponse(success=True, message=message)
    except Exception as e:
        logger.error("Erreur de déconnexion: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la déconnexion: {e}",
        )


@router.get("/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    """Retourne le statut de la connexion Soulseek."""
    return StatusResponse(
        connected=soulseek_service.is_connected,
        username=soulseek_service.username if soulseek_service.is_connected else None,
        server="server.slsknet.org:2242" if soulseek_service.is_connected else None,
    )
