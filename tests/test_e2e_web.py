"""Tests E2E pour l'interface web FastAPI.

Couvre le cycle complet :
- Page d'accueil HTML (structure, éléments)
- Endpoints API (health, status, connect, disconnect)
- Validation des entrées/sorties
- Cycle connexion → déconnexion (mocké)
"""

from __future__ import annotations

from typing import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Fixture TestClient FastAPI avec gestion propre du lifespan."""
    with TestClient(app) as c:
        yield c


# ── Tests de la page d'accueil ───────────────────────────────────────


class TestPageAccueil:
    """Teste la page HTML principale."""

    def test_page_retourne_html(self, client: TestClient) -> None:
        """La route / doit retourner le contenu HTML."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/html; charset=utf-8"

    def test_page_contient_titre(self, client: TestClient) -> None:
        """Le titre de la page est présent."""
        resp = client.get("/")
        html = resp.text
        assert "<title>MINOTAUR AIOSLSK Systeme</title>" in html

    def test_page_contient_header(self, client: TestClient) -> None:
        """Le header avec le logo et le titre est présent."""
        resp = client.get("/")
        html = resp.text
        assert "header-logo" in html
        assert "aioslsk" in html
        assert "status-badge" in html
        assert "Déconnecté" in html

    def test_page_contient_sidebar(self, client: TestClient) -> None:
        """La sidebar avec les éléments de navigation est présente."""
        resp = client.get("/")
        html = resp.text
        assert "Recherche" in html
        assert "Téléchargements" in html
        assert "Connexion" in html

    def test_page_contient_etat_vide(self, client: TestClient) -> None:
        """L'état vide avec le message d'invitation est présent."""
        resp = client.get("/")
        html = resp.text
        assert "empty-state" in html
        assert "Contenu à venir" in html
        assert "Connectez-vous au serveur Soulseek" in html

    def test_page_contient_footer(self, client: TestClient) -> None:
        """Le footer avec la version et le statut est présent."""
        resp = client.get("/")
        html = resp.text
        assert "aioslsk Web Interface v0.1.0" in html
        assert "Serveur hors ligne" in html

    def test_page_pretty_html(self, client: TestClient) -> None:
        """Le HTML doit contenir des balises sémantiques de base."""
        resp = client.get("/")
        html = resp.text
        assert "<!DOCTYPE html>" in html
        assert '<html lang="fr">' in html
        assert "<head>" in html
        assert "<body>" in html
        assert "<header" in html
        assert "<nav" in html
        assert "<main" in html
        assert "<footer" in html


# ── Tests de l'API Health ────────────────────────────────────────────


class TestAPIHealth:
    """Teste l'endpoint /api/health."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """L'endpoint health retourne 200."""
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_health_contient_service(self, client: TestClient) -> None:
        """La réponse health contient les infos du service."""
        resp = client.get("/api/health")
        data = resp.json()
        assert data["service"] == "aioslsk Web Interface"
        assert data["version"] == "0.1.0"
        assert data["status"] == "running"

    def test_health_accepte_methodes(self, client: TestClient) -> None:
        """Seul GET est accepté sur /api/health."""
        resp_post = client.post("/api/health")
        assert resp_post.status_code == 405  # Method Not Allowed


# ── Tests de l'API Status ─────────────────────────────────────────────


class TestAPIStatus:
    """Teste l'endpoint /api/status."""

    def test_status_returns_200(self, client: TestClient) -> None:
        """L'endpoint status retourne 200."""
        resp = client.get("/api/status")
        assert resp.status_code == 200

    def test_status_default_deconnecte(self, client: TestClient) -> None:
        """Par défaut, le statut indique déconnecté."""
        resp = client.get("/api/status")
        data = resp.json()
        assert data["connected"] is False
        assert data["username"] is None
        assert data["server"] is None

    def test_status_json_structure(self, client: TestClient) -> None:
        """La structure JSON de status est correcte."""
        resp = client.get("/api/status")
        data = resp.json()
        assert "connected" in data
        assert "username" in data
        assert "server" in data
        assert isinstance(data["connected"], bool)


# ── Tests de connexion / déconnexion (mockée) ─────────────────────────


class TestAPIConnectMocke:
    """Teste le cycle connexion/déconnexion avec le service mocké."""

    def test_connect_avec_identifiants_valides(self, client: TestClient) -> None:
        """POST /api/connect avec identifiants valides."""
        # Mocker le service pour éviter un vrai appel réseau
        with patch("src.routers.connection.soulseek_service.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = "Connecté à Soulseek en tant que testuser"

            resp = client.post(
                "/api/connect",
                json={"username": "testuser", "password": "testpass"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["username"] == "testuser"
        assert "Connecté" in data["message"]

    def test_connect_appelle_service_avec_bons_params(self, client: TestClient) -> None:
        """Le service.connect est appelé avec les bons arguments."""
        with patch("src.routers.connection.soulseek_service.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = "OK"

            client.post(
                "/api/connect",
                json={"username": "alice", "password": "secret"},
            )

        mock_connect.assert_awaited_once_with(username="alice", password="secret")

    def test_connect_avec_identifiants_vides(self, client: TestClient) -> None:
        """POST /api/connect avec identifiants vides doit fonctionner (le service valide)."""
        with patch("src.routers.connection.soulseek_service.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = "Connecté"

            resp = client.post(
                "/api/connect",
                json={"username": "", "password": ""},
            )

        # Le service accepte ce qu'on lui donne, pas de validation côté routeur
        assert resp.status_code == 200
        mock_connect.assert_awaited_once()

    def test_connect_sans_body(self, client: TestClient) -> None:
        """POST /api/connect sans body → 422 (validation Pydantic)."""
        resp = client.post("/api/connect", json={})
        assert resp.status_code == 422

    def test_connect_quand_service_echoue(self, client: TestClient) -> None:
        """POST /api/connect quand le service lève une exception → 503."""
        with patch("src.routers.connection.soulseek_service.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = Exception("Connexion refusée")

            resp = client.post(
                "/api/connect",
                json={"username": "testuser", "password": "wrong"},
            )

        assert resp.status_code == 503
        assert "Impossible de se connecter" in resp.json()["detail"]

    def test_disconnect_quand_deconnecte(self, client: TestClient) -> None:
        """POST /api/disconnect quand déjà déconnecté."""
        with patch("src.routers.connection.soulseek_service.disconnect", new_callable=AsyncMock) as mock_disconnect:
            mock_disconnect.return_value = "Pas de connexion active"

            resp = client.post("/api/disconnect")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "Pas de connexion" in data["message"]

    def test_disconnect_quand_connecte(self, client: TestClient) -> None:
        """POST /api/disconnect quand connecté."""
        with patch("src.routers.connection.soulseek_service.disconnect", new_callable=AsyncMock) as mock_disconnect:
            mock_disconnect.return_value = "Déconnecté de Soulseek"

            resp = client.post("/api/disconnect")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "Déconnecté" in data["message"]

    def test_disconnect_quand_service_echoue(self, client: TestClient) -> None:
        """POST /api/disconnect quand le service lève une exception → 500."""
        with patch("src.routers.connection.soulseek_service.disconnect", new_callable=AsyncMock) as mock_disconnect:
            mock_disconnect.side_effect = Exception("Erreur interne")

            resp = client.post("/api/disconnect")

        assert resp.status_code == 500
        assert "Erreur lors de la déconnexion" in resp.json()["detail"]


# ── Tests de structure des réponses ────────────────────────────────────


class TestStructureReponses:
    """Teste la structure et les types des réponses API."""

    def test_connect_response_structure(self, client: TestClient) -> None:
        """La réponse de connect a la bonne structure Pydantic."""
        with patch("src.routers.connection.soulseek_service.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = "OK"

            resp = client.post(
                "/api/connect",
                json={"username": "bob", "password": "pass"},
            )

        data = resp.json()
        assert set(data.keys()) == {"success", "message", "username"}
        assert isinstance(data["success"], bool)
        assert isinstance(data["message"], str)
        assert isinstance(data["username"], str)

    def test_status_response_structure(self, client: TestClient) -> None:
        """La réponse de status a la bonne structure Pydantic."""
        resp = client.get("/api/status")
        data = resp.json()
        assert set(data.keys()) == {"connected", "username", "server"}
        assert isinstance(data["connected"], bool)
        # username et server peuvent être None
        assert data["username"] is None or isinstance(data["username"], str)
        assert data["server"] is None or isinstance(data["server"], str)

    def test_health_response_structure(self, client: TestClient) -> None:
        """La réponse de health a la bonne structure."""
        resp = client.get("/api/health")
        data = resp.json()
        assert set(data.keys()) == {"service", "version", "status"}
        assert isinstance(data["service"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["status"], str)
