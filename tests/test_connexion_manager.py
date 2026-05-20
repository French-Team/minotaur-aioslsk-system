"""Tests du gestionnaire de connexion Soulseek (connexion_manager.py).

Couvre :
  - _generer_identifiants()  — génération aléatoire de comptes
  - _AsyncEventLoopThread   — thread asyncio interne
  - ConnexionManager        — API publique (avec mocks)
"""

from __future__ import annotations

import concurrent.futures
from unittest.mock import MagicMock, PropertyMock

import pytest

from src.services.connexion_manager import (
    ConnexionManager,
    _AsyncEventLoopThread,
    _generer_identifiants,
)


# ── Helper : mock de run_coro qui ferme la coroutine ────────────
# Evite le RuntimeWarning "coroutine was never awaited" en appelant
# .close() sur la coroutine que le mock ne consomme pas.


def _mock_run_coro(coro):
    """Mock de _AsyncEventLoopThread.run_coro qui ferme la coroutine.

    Les tests qui mockent run_coro veulent juste vérifier que la méthode
    est appelée, pas exécuter la coroutine. Sans ce close(), Python
    lève un RuntimeWarning car la coroutine n'est jamais awaitée.
    """
    coro.close()
    return MagicMock(spec=concurrent.futures.Future)


# ═══════════════════════════════════════════════════════════════════
#  _generer_identifiants
# ═══════════════════════════════════════════════════════════════════


class TestGenererIdentifiants:
    def test_retourne_tuple_de_deux_strings(self):
        username, password = _generer_identifiants()
        assert isinstance(username, str)
        assert isinstance(password, str)

    def test_username_non_vide(self):
        username, _ = _generer_identifiants()
        assert len(username) > 0

    def test_password_taille_12(self):
        _, password = _generer_identifiants()
        assert len(password) == 12

    def test_password_alphanumerique(self):
        _, password = _generer_identifiants()
        assert password.isascii()

    def test_username_contient_pas_despaces(self):
        username, _ = _generer_identifiants()
        assert " " not in username

    def test_generations_differentes(self):
        """Deux appels consécutifs produisent des résultats différents
        (probabiliste mais statistiquement certain sur 2 appels)."""
        u1, p1 = _generer_identifiants()
        u2, p2 = _generer_identifiants()
        assert (u1, p1) != (u2, p2)

    def test_username_contient_uniquement_lettres_tiret_underscore(self):
        username, _ = _generer_identifiants()
        assert all(c.isalpha() or c in "-_" for c in username)


# ═══════════════════════════════════════════════════════════════════
#  _AsyncEventLoopThread
# ═══════════════════════════════════════════════════════════════════


class TestAsyncEventLoopThread:
    def test_creer_thread(self):
        """On peut créer un _AsyncEventLoopThread sans planter."""
        thread = _AsyncEventLoopThread()
        assert thread is not None
        assert not thread.isRunning()

    def test_run_coro_leve_runtime_error_sans_boucle(self):
        """run_coro() avant run() lève RuntimeError."""
        thread = _AsyncEventLoopThread()
        with pytest.raises(RuntimeError, match="boucle asyncio"):
            thread.run_coro(lambda: None)  # type: ignore[arg-type]

    def test_stop_sans_demarrer_ne_plante_pas(self):
        thread = _AsyncEventLoopThread()
        thread.stop()  # ne devrait pas planter

    def test_wait_ready_timeout_ne_plante_pas(self):
        thread = _AsyncEventLoopThread()
        thread.wait_ready(0.01)  # timeout rapide, ne devrait pas planter


# ═══════════════════════════════════════════════════════════════════
#  ConnexionManager
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.qt_heavy
class TestConnexionManagerInit:
    """Teste l'instanciation et les propriétés de base."""

    def test_creation_avec_mocks(self, mocker, qapp):
        """On peut créer un ConnexionManager si les dépendances sont mockées."""
        mocker.patch("src.services.connexion_manager._AsyncEventLoopThread")
        mock_svc = mocker.patch("src.services.connexion_manager.soulseek_service")
        mock_svc.search_result_received = MagicMock()
        cm = ConnexionManager()
        assert cm is not None

    def test_is_connected_delegue_au_service(self, mocker, qapp):
        mocker.patch("src.services.connexion_manager._AsyncEventLoopThread")
        mock_svc = mocker.patch("src.services.connexion_manager.soulseek_service")
        mock_svc.search_result_received = MagicMock()
        type(mock_svc).is_connected = PropertyMock(return_value=True)

        cm = ConnexionManager()
        assert cm.is_connected is True

    def test_username_delegue_au_service(self, mocker, qapp):
        mocker.patch("src.services.connexion_manager._AsyncEventLoopThread")
        mock_svc = mocker.patch("src.services.connexion_manager.soulseek_service")
        mock_svc.search_result_received = MagicMock()
        type(mock_svc).username = PropertyMock(return_value="TestUser")

        cm = ConnexionManager()
        assert cm.username == "TestUser"


@pytest.mark.qt_heavy
class TestConnexionManagerSearch:
    """Méthodes de recherche — search, search_user, search_room, stop_search."""

    @pytest.fixture
    def cm(self, mocker, qapp):
        """Fixture : ConnexionManager avec toutes les dépendances mockées."""
        mocker.patch("src.services.connexion_manager._AsyncEventLoopThread")
        mock_svc = mocker.patch("src.services.connexion_manager.soulseek_service")
        mock_svc.search_result_received = MagicMock()
        type(mock_svc).is_connected = PropertyMock(return_value=True)
        cm = ConnexionManager()
        cm._async_thread.run_coro = MagicMock(side_effect=_mock_run_coro)
        return cm

    def test_search_emet_status_changed(self, cm):
        emissions: list[str] = []
        cm.status_changed.connect(lambda msg: emissions.append(msg))
        cm.search("test query")
        assert any("Recherche" in e for e in emissions)

    def test_search_appelle_run_coro(self, cm):
        cm.search("test query")
        cm._async_thread.run_coro.assert_called_once()

    def test_search_sans_connexion_emet_erreur(self, mocker, qapp):
        mocker.patch("src.services.connexion_manager._AsyncEventLoopThread")
        mock_svc = mocker.patch("src.services.connexion_manager.soulseek_service")
        mock_svc.search_result_received = MagicMock()
        type(mock_svc).is_connected = PropertyMock(return_value=False)

        cm = ConnexionManager()
        emissions: list[str] = []
        cm.error_occurred.connect(lambda msg: emissions.append(msg))
        cm.search("test")
        assert any("Pas connecté" in e for e in emissions)

    def test_search_user_appelle_run_coro(self, cm):
        cm.search_user("peer_user", "query")
        cm._async_thread.run_coro.assert_called_once()

    def test_search_user_sans_connexion_emet_erreur(self, mocker, qapp):
        mocker.patch("src.services.connexion_manager._AsyncEventLoopThread")
        mock_svc = mocker.patch("src.services.connexion_manager.soulseek_service")
        mock_svc.search_result_received = MagicMock()
        type(mock_svc).is_connected = PropertyMock(return_value=False)

        cm = ConnexionManager()
        emissions: list[str] = []
        cm.error_occurred.connect(lambda msg: emissions.append(msg))
        cm.search_user("user", "q")
        assert any("Pas connecté" in e for e in emissions)

    def test_search_room_appelle_run_coro(self, cm):
        cm.search_room("#general", "query")
        cm._async_thread.run_coro.assert_called_once()

    def test_search_room_sans_connexion_emet_erreur(self, mocker, qapp):
        mocker.patch("src.services.connexion_manager._AsyncEventLoopThread")
        mock_svc = mocker.patch("src.services.connexion_manager.soulseek_service")
        mock_svc.search_result_received = MagicMock()
        type(mock_svc).is_connected = PropertyMock(return_value=False)

        cm = ConnexionManager()
        emissions: list[str] = []
        cm.error_occurred.connect(lambda msg: emissions.append(msg))
        cm.search_room("#general", "q")
        assert any("Pas connecté" in e for e in emissions)

    def test_stop_search_sans_ticket_ne_fait_rien(self, cm):
        cm._current_search_ticket = None
        cm.stop_search()
        cm._async_thread.run_coro.assert_not_called()

    def test_stop_search_avec_ticket_appelle_run_coro(self, cm):
        cm._current_search_ticket = 42
        cm.stop_search()
        cm._async_thread.run_coro.assert_called_once()


@pytest.mark.qt_heavy
class TestConnexionManagerBlockUser:
    """Méthode block_user."""

    @pytest.fixture
    def cm(self, mocker, qapp, tmp_app_config):
        mocker.patch("src.services.connexion_manager._AsyncEventLoopThread")
        mock_svc = mocker.patch("src.services.connexion_manager.soulseek_service")
        mock_svc.search_result_received = MagicMock()
        cm = ConnexionManager()
        return cm

    def test_block_user_nouveau_met_a_jour_config(self, cm, tmp_app_config):
        cm.block_user("malicious_user")
        from src.services import app_config

        bloque = app_config.get("utilisateurs.liste_bloques", "")
        assert "malicious_user" in bloque

    def test_block_user_deja_bloque_ne_duplique_pas(self, cm, tmp_app_config):
        from src.services import app_config

        app_config.set("utilisateurs.liste_bloques", "existing_user")
        cm.block_user("existing_user")
        bloque = app_config.get("utilisateurs.liste_bloques", "")
        assert bloque == "existing_user"

    def test_block_user_emet_status_changed(self, cm, tmp_app_config):
        emissions: list[str] = []
        cm.status_changed.connect(lambda msg: emissions.append(msg))
        cm.block_user("spammer")
        assert any("bloqué" in e for e in emissions)


@pytest.mark.qt_heavy
class TestConnexionManagerLogin:
    """Méthodes login, auto_login, generate_account."""

    @pytest.fixture
    def cm(self, mocker, qapp):
        mocker.patch("src.services.connexion_manager._AsyncEventLoopThread")
        mock_svc = mocker.patch("src.services.connexion_manager.soulseek_service")
        mock_svc.search_result_received = MagicMock()
        type(mock_svc).is_connected = PropertyMock(return_value=False)
        cm = ConnexionManager()
        cm._async_thread.run_coro = MagicMock(side_effect=_mock_run_coro)
        return cm

    def test_login_emet_status_changed(self, cm):
        emissions: list[str] = []
        cm.status_changed.connect(lambda msg: emissions.append(msg))
        cm.login("user", "pass")
        assert any("Connexion en cours" in e for e in emissions)

    def test_login_appelle_run_coro(self, cm):
        cm.login("user", "pass")
        cm._async_thread.run_coro.assert_called_once()

    def test_login_ignore_si_deja_connecte(self, mocker, qapp):
        """Quand is_connected=True, login() ne lance pas de nouvelle connexion."""
        mocker.patch("src.services.connexion_manager._AsyncEventLoopThread")
        mock_svc = mocker.patch("src.services.connexion_manager.soulseek_service")
        mock_svc.search_result_received = MagicMock()
        type(mock_svc).is_connected = PropertyMock(return_value=True)
        cm = ConnexionManager()
        cm._async_thread.run_coro = MagicMock(side_effect=_mock_run_coro)

        emissions: list[str] = []
        cm.status_changed.connect(lambda msg: emissions.append(msg))
        cm.login("user", "pass")
        assert any("Déjà connecté" in e for e in emissions)
        cm._async_thread.run_coro.assert_not_called()

    def test_login_ignore_si_connexion_en_cours(self, cm):
        """Quand _connecting=True, login() ne lance pas de nouvelle connexion."""
        cm._connecting = True
        emissions: list[str] = []
        cm.error_occurred.connect(lambda msg: emissions.append(msg))
        cm.login("user", "pass")
        assert any("déjà en cours" in e for e in emissions)
        cm._async_thread.run_coro.assert_not_called()

    def test_auto_login_sans_config_ne_fait_rien(self, cm):
        cm._async_thread.run_coro.reset_mock()
        cm.auto_login()
        cm._async_thread.run_coro.assert_not_called()

    def test_auto_login_avec_config_appelle_run_coro(self, mocker, cm, tmp_app_config):
        from src.services import app_config

        app_config.set("general.connexion_automatique", True)
        app_config.set("reseau.nom_utilisateur", "saved_user")
        app_config.set("reseau.mot_de_passe", "saved_pass")

        cm._async_thread.run_coro.reset_mock()
        cm.auto_login()
        cm._async_thread.run_coro.assert_called_once()

    def test_generate_account_emet_generating_true(self, cm):
        emissions: list[bool] = []
        cm.generating.connect(lambda v: emissions.append(v))
        cm.generate_account()
        assert True in emissions

    def test_generate_account_appelle_run_coro(self, cm):
        cm.generate_account()
        cm._async_thread.run_coro.assert_called_once()

    def test_generate_account_ignore_si_connexion_en_cours(self, cm):
        """Quand _connecting=True, generate_account() ne lance pas non plus."""
        cm._connecting = True
        emissions: list[str] = []
        cm.error_occurred.connect(lambda msg: emissions.append(msg))
        cm.generate_account()
        assert any("déjà en cours" in e for e in emissions)
        cm._async_thread.run_coro.assert_not_called()


@pytest.mark.qt_heavy
class TestConnexionManagerDisconnect:
    """Méthodes disconnect et shutdown."""

    @pytest.fixture
    def cm(self, mocker, qapp):
        mocker.patch("src.services.connexion_manager._AsyncEventLoopThread")
        mock_svc = mocker.patch("src.services.connexion_manager.soulseek_service")
        mock_svc.search_result_received = MagicMock()
        cm = ConnexionManager()
        cm._async_thread.run_coro = MagicMock(side_effect=_mock_run_coro)
        return cm

    def test_disconnect_emet_status_changed(self, cm):
        emissions: list[str] = []
        cm.status_changed.connect(lambda msg: emissions.append(msg))
        cm.disconnect()
        assert any("Déconnexion" in e for e in emissions)

    def test_disconnect_appelle_run_coro(self, cm):
        cm.disconnect()
        cm._async_thread.run_coro.assert_called_once()

    def test_shutdown_appelle_stop(self, cm):
        cm._async_thread.stop = MagicMock()
        cm.shutdown()
        cm._async_thread.stop.assert_called_once()

    def test_shutdown_appelle_disconnect_si_connecte(self, mocker, cm):
        type(cm._service).is_connected = PropertyMock(return_value=True)
        future_mock = MagicMock()
        # Custom side_effect that returns future_mock but still closes the coroutine
        def _mock_with_future(coro):
            coro.close()
            return future_mock
        cm._async_thread.run_coro = MagicMock(side_effect=_mock_with_future)
        cm.shutdown()
        cm._async_thread.run_coro.assert_called()


@pytest.mark.qt_heavy
class TestConnexionManagerSignaux:
    """Vérifie le câblage des signaux à l'EventBus."""

    @pytest.fixture
    def cm(self, mocker, qapp):
        mocker.patch("src.services.connexion_manager._AsyncEventLoopThread")
        mock_svc = mocker.patch("src.services.connexion_manager.soulseek_service")
        mock_svc.search_result_received = MagicMock()
        # Mock EventBus pour éviter les effets de bord
        mocker.patch("src.services.connexion_manager.EventBus")
        return ConnexionManager()

    def test_search_result_received_relaye(self, cm):
        """Le signal search_result_received du service est relayé."""
        # On vérifie que le signal mock a bien été connecté
        cm._service.search_result_received.connect.assert_called_once_with(
            cm.search_result_received.emit
        )
