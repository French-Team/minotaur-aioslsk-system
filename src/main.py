from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from src.config import settings
from src.routers.connection import router as connection_router
from src.services.soulseek_client import soulseek_service

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gère le cycle de vie de l'application."""
    logging.info("Démarrage de l'application aioslsk Web Interface")
    yield
    logging.info("Arrêt de l'application — nettoyage des ressources...")
    if soulseek_service.is_connected:
        await soulseek_service.disconnect()
    logging.info("Application arrêtée")


app = FastAPI(
    title="aioslsk Web Interface",
    description="Interface web pour le client Soulseek aioslsk",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(connection_router)


@app.get("/")
async def root() -> FileResponse:
    """Sert la page HTML principale."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict:
    """Point de contrôle JSON pour les diagnostics."""
    return {
        "service": "aioslsk Web Interface",
        "version": "0.1.0",
        "status": "running",
    }


def main() -> None:
    """Point d'entrée pour lancer le serveur."""
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
