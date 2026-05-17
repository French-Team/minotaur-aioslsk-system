"""Tests unitaires pour ``ClientsActifsService`` (src/services/clients_actifs_service.py).

Teste le cycle de vie, l'accès aux données, le tri, et les événements
aioslsk (UserStatusUpdate, UserInfoUpdate).
"""

from __future__ import annotations

from dataclasses import fields
from typing import Any
from unittest.mock import MagicMock

import pytest
from aioslsk.user.model import UserStatus
from PySide6.QtCore import QObject
from pytest import MonkeyPatch

from src.services.clients_actifs_service import (
    ClientInfo,
    ClientsActifsService,
)

# ── Helpers ────────────────────────────────────────────────────────


def _mock_user(
    username: str,
    status: UserStatus = UserStatus.ONLINE,
    country: str = "FR",
    avg_speed: int = 500_000,
    shared_file_count: int = 100,
    shared_folder_count: int = 10,
    slots_free: int = 2,
    has_slots_free: bool = True,
    queue_length: int = 0,
    uploads: int = 1,
    privileged: bool = False,
    description: str = "",
) -> MagicMock:
    """Crée un faux objet User aioslsk avec les attributs donnés."""
    user = MagicMock()
    user.username = username
    user.status = status
    user.country = country
    user.avg_speed = avg_speed
    user.shared_file_count = shared_file_count
    user.shared_folder_count = shared_folder_count
    user.slots_free = slots_free
    user.has_slots_free = has_slots_free
    user.queue_length = queue_length
    user.uploads = uploads
    user.privileged = privileged
    user.description = description
    return user


def _make_service(
    users: dict[str, MagicMock] | None = None,
) -> tuple[ClientsActifsService, MagicMock, MagicMock]:
    """Crée un ClientsActifsService avec SoulseekService mocké.

    Retourne (service, mock_soulseek, mock_client).
    """
    mock_client = MagicMock()
    mock_client.users.users = users or {}

    mock_soulseek = MagicMock()
    mock_soulseek.client = mock_client

    service = ClientsActifsService(mock_soulseek)
    return service, mock_soulseek, mock_client


# ═════════════════════════════════════════════════════════════════
#  Tests du modèle ClientInfo
# ═════════════════════════════════════════════════════════════════


class TestClientInfo:
    def test_default_username_required(self) -> None:
        """username est le seul champ requis."""
        info = ClientInfo(username="testuser")
        assert info.username == "testuser"

    def test_default_status_is_unknown(self) -> None:
        """Le statut par défaut doit être UNKNOWN."""
        info = ClientInfo(username="testuser")
        assert info.statut == UserStatus.UNKNOWN

    def test_default_string_fields_empty(self) -> None:
        """Les champs texte doivent être vides par défaut."""
        info = ClientInfo(username="testuser")
        assert info.pays == ""
        assert info.description == ""

    def test_default_numeric_fields_zero(self) -> None:
        """Les champs numériques doivent être 0 par défaut."""
        info = ClientInfo(username="testuser")
        assert info.vitesse == 0
        assert info.fichiers_partages == 0
        assert info.dossiers_partages == 0
        assert info.slots_libres == 0
        assert info.file_attente == 0
        assert info.uploads == 0

    def test_default_boolean_fields_false(self) -> None:
        """Les champs booléens doivent être False par défaut."""
        info = ClientInfo(username="testuser")
        assert info.slots_libres_flag is False
        assert info.privilege is False

    def test_all_fields_assignable(self) -> None:
        """Tous les champs de la dataclass sont accessibles."""
        info = ClientInfo(
            username="alice",
            statut=UserStatus.AWAY,
            pays="US",
            vitesse=1_000_000,
            fichiers_partages=200,
            dossiers_partages=20,
            slots_libres=3,
            slots_libres_flag=True,
            file_attente=5,
            uploads=2,
            privilege=True,
            description="Hello!",
            derniere_vue=12345.0,
        )
        assert info.username == "alice"
        assert info.statut == UserStatus.AWAY
        assert info.pays == "US"
        assert info.vitesse == 1_000_000
        assert info.fichiers_partages == 200
        assert info.dossiers_partages == 20
        assert info.slots_libres == 3
        assert info.slots_libres_flag is True
        assert info.file_attente == 5
        assert info.uploads == 2
        assert info.privilege is True
        assert info.description == "Hello!"
        assert info.derniere_vue == 12345.0


# ═════════════════════════════════════════════════════════════════
#  Tests du cycle de vie
# ═════════════════════════════════════════════════════════════════


class TestCycleDeVie:
    def test_demarrer_sans_client(self) -> None:
        """demarrer() ne doit pas planter si le client aioslsk est None."""
        mock_soulseek = MagicMock()
        mock_soulseek.client = None
        service = ClientsActifsService(mock_soulseek)
        # Ne doit pas lever d'exception
        service.demarrer()
        assert service._running is True

    def test_demarrer_synchronise_users(self) -> None:
        """demarrer() doit synchroniser les users existants et émettre clients_synchronises."""
        users = {
            "alice": _mock_user("alice", UserStatus.ONLINE),
            "bob": _mock_user("bob", UserStatus.AWAY),
        }
        service, _mock_soulseek, _mock_client = _make_service(users)
        received: list[list[ClientInfo]] = []
        service.clients_synchronises.connect(received.append)

        service.demarrer()

        assert service._running is True
        assert len(received) == 1
        synced = received[0]
        assert len(synced) == 2
        noms = {c.username for c in synced}
        assert noms == {"alice", "bob"}

    def test_demarrer_idempotent(self) -> None:
        """demarrer() appelé deux fois ne doit pas re-synchroniser."""
        users = {"alice": _mock_user("alice", UserStatus.ONLINE)}
        service, _mock_soulseek, _mock_client = _make_service(users)
        received: list[list[ClientInfo]] = []
        service.clients_synchronises.connect(received.append)

        service.demarrer()
        service.demarrer()

        assert len(received) == 1  # Une seule émission

    def test_arreter_vide_le_cache(self) -> None:
        """arreter() doit vider le dictionnaire interne."""
        users = {"alice": _mock_user("alice", UserStatus.ONLINE)}
        service, _mock_soulseek, _mock_client = _make_service(users)
        service.demarrer()
        assert len(service._clients) == 1

        service.arreter()

        assert service._running is False
        assert len(service._clients) == 0

    def test_rafraichir_recharge(self) -> None:
        """rafraichir() doit re-synchroniser et ré-émettre clients_synchronises."""
        users = {"alice": _mock_user("alice", UserStatus.ONLINE)}
        service, _mock_soulseek, _mock_client = _make_service(users)
        service.demarrer()

        received: list[list[ClientInfo]] = []
        service.clients_synchronises.connect(received.append)

        # Ajouter un user entre-temps
        _mock_client.users.users = {
            "alice": _mock_user("alice", UserStatus.ONLINE),
            "bob": _mock_user("bob", UserStatus.ONLINE),
        }
        service.rafraichir()

        assert len(received) == 1
        assert len(received[0]) == 2


# ═════════════════════════════════════════════════════════════════
#  Tests d'accès aux données
# ═════════════════════════════════════════════════════════════════


class TestAccesDonnees:
    @pytest.fixture
    def service_with_clients(self) -> ClientsActifsService:
        """Service pré-rempli avec 4 clients de statuts variés."""
        users = {
            "alice": _mock_user("alice", UserStatus.ONLINE),
            "bob": _mock_user("bob", UserStatus.AWAY),
            "carol": _mock_user("carol", UserStatus.OFFLINE),
            "dave": _mock_user("dave", UserStatus.UNKNOWN),
        }
        svc, _mock_soulseek, _mock_client = _make_service(users)
        svc.demarrer()
        return svc

    def test_clients_actifs_exclut_unknown(self, service_with_clients: ClientsActifsService) -> None:
        """clients_actifs() doit exclure les clients UNKNOWN."""
        actifs = service_with_clients.clients_actifs()
        noms = {c.username for c in actifs}
        assert "dave" not in noms  # UNKNOWN exclu
        assert "alice" in noms
        assert "bob" in noms
        assert "carol" in noms  # OFFLINE inclus (pas UNKNOWN)

    def test_clients_actifs_trie_par_nom(self, service_with_clients: ClientsActifsService) -> None:
        """clients_actifs() doit trier par ordre alphabétique."""
        actifs = service_with_clients.clients_actifs()
        noms = [c.username for c in actifs]
        assert noms == sorted(noms, key=str.lower)

    def test_clients_actifs_vide(self) -> None:
        """clients_actifs() doit retourner [] si aucun client."""
        svc, _mock_soulseek, _mock_client = _make_service()
        assert svc.clients_actifs() == []

    def test_obtenir_client_existant(self, service_with_clients: ClientsActifsService) -> None:
        """obtenir_client() retourne le bon ClientInfo."""
        client = service_with_clients.obtenir_client("alice")
        assert client is not None
        assert client.username == "alice"
        assert client.statut == UserStatus.ONLINE

    def test_obtenir_client_inexistant(self, service_with_clients: ClientsActifsService) -> None:
        """obtenir_client() retourne None pour un inconnu."""
        assert service_with_clients.obtenir_client("inconnu") is None

    def test_nombre_actifs(self, service_with_clients: ClientsActifsService) -> None:
        """nombre_actifs() compte ONLINE + AWAY."""
        assert service_with_clients.nombre_actifs() == 2  # alice + bob

    def test_nombre_connectes(self, service_with_clients: ClientsActifsService) -> None:
        """nombre_connectes() compte ONLINE uniquement."""
        assert service_with_clients.nombre_connectes() == 1  # alice seulement


# ═════════════════════════════════════════════════════════════════
#  Tests de tri
# ═════════════════════════════════════════════════════════════════


class TestTri:
    @pytest.fixture
    def service(self) -> ClientsActifsService:
        """Service avec clients de différentes caractéristiques."""
        users = {
            "zeta": _mock_user(
                "zeta", UserStatus.ONLINE, avg_speed=1_000_000, shared_file_count=50, slots_free=0, queue_length=10
            ),
            "alpha": _mock_user(
                "alpha", UserStatus.AWAY, avg_speed=500_000, shared_file_count=200, slots_free=5, queue_length=0
            ),
            "beta": _mock_user(
                "beta", UserStatus.ONLINE, avg_speed=2_000_000, shared_file_count=100, slots_free=2, queue_length=3
            ),
        }
        svc, _mock_soulseek, _mock_client = _make_service(users)
        svc.demarrer()
        return svc

    def test_tri_defaut_username(self, service: ClientsActifsService) -> None:
        """Tri par défaut = username."""
        result = service.clients_tries()
        noms = [c.username for c in result]
        assert noms == ["alpha", "beta", "zeta"]

    def test_tri_username_desc(self, service: ClientsActifsService) -> None:
        """Tri username décroissant."""
        result = service.clients_tries(cle="username", ordre=False)
        noms = [c.username for c in result]
        assert noms == ["zeta", "beta", "alpha"]

    def test_tri_vitesse(self, service: ClientsActifsService) -> None:
        """Tri par vitesse (ordre croissant par défaut)."""
        result = service.clients_tries(cle="vitesse")
        vitesses = [c.vitesse for c in result]
        assert vitesses == sorted(vitesses)

    def test_tri_vitesse_desc(self, service: ClientsActifsService) -> None:
        """Tri par vitesse décroissant."""
        result = service.clients_tries(cle="vitesse", ordre=False)
        vitesses = [c.vitesse for c in result]
        assert vitesses == sorted(vitesses, reverse=True)

    def test_tri_fichiers(self, service: ClientsActifsService) -> None:
        """Tri par nombre de fichiers."""
        result = service.clients_tries(cle="fichiers")
        fichiers = [c.fichiers_partages for c in result]
        assert fichiers == sorted(fichiers)

    def test_tri_slots(self, service: ClientsActifsService) -> None:
        """Tri par slots libres."""
        result = service.clients_tries(cle="slots")
        slots = [c.slots_libres for c in result]
        assert slots == sorted(slots)

    def test_tri_file(self, service: ClientsActifsService) -> None:
        """Tri par file d'attente."""
        result = service.clients_tries(cle="file")
        files = [c.file_attente for c in result]
        assert files == sorted(files)

    def test_tri_statut(self, service: ClientsActifsService) -> None:
        """Tri par statut (ordre: ONLINE < AWAY < OFFLINE)."""
        result = service.clients_tries(cle="statut")
        statuts = [c.statut for c in result]
        # beta=ONLINE, zeta=ONLINE, alpha=AWAY
        assert statuts == [UserStatus.ONLINE, UserStatus.ONLINE, UserStatus.AWAY]

    def test_tri_statut_desc(self, service: ClientsActifsService) -> None:
        """Tri par statut décroissant."""
        result = service.clients_tries(cle="statut", ordre=False)
        statuts = [c.statut for c in result]
        # alpha=AWAY, beta=ONLINE, zeta=ONLINE
        assert statuts == [UserStatus.AWAY, UserStatus.ONLINE, UserStatus.ONLINE]

    def test_tri_cle_inconnue(self, service: ClientsActifsService) -> None:
        """Une clé inconnue doit fallback au tri par username."""
        result = service.clients_tries(cle="inconnue")
        noms = [c.username for c in result]
        assert noms == sorted(noms, key=str.lower)


# ═════════════════════════════════════════════════════════════════
#  Tests des événements
# ═════════════════════════════════════════════════════════════════


class _FakeUserStatusEvent:
    """Simule UserStatusUpdateEvent d'aioslsk."""

    def __init__(self, username: str, status: UserStatus) -> None:
        self.username = username
        self.status = status


class _FakeUserInfoEvent:
    """Simule UserInfoUpdateEvent d'aioslsk."""

    def __init__(self, username: str, **kwargs: Any) -> None:
        self.username = username
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestEvenements:
    def test_status_update_nouveau_client(self) -> None:
        """Un événement UserStatusUpdate pour un inconnu doit créer un ClientInfo."""
        service, _mock_soulseek, _mock_client = _make_service()
        service.demarrer()

        received_ajout: list[str] = []
        received_statut: list[tuple[str, Any, Any]] = []
        service.client_ajoute.connect(received_ajout.append)
        service.client_statut_change.connect(lambda *a: received_statut.append(a))

        evt = _FakeUserStatusEvent("newuser", UserStatus.ONLINE)
        service._on_user_status_update(evt)

        assert "newuser" in service._clients
        assert service._clients["newuser"].statut == UserStatus.ONLINE
        assert received_ajout == ["newuser"]
        assert len(received_statut) == 1
        assert received_statut[0][0] == "newuser"  # username
        assert received_statut[0][1] == UserStatus.ONLINE  # nouveau
        assert received_statut[0][2] == UserStatus.UNKNOWN  # ancien

    def test_status_update_client_existant(self) -> None:
        """Un événement UserStatusUpdate pour un client existant doit mettre à jour son statut."""
        users = {"alice": _mock_user("alice", UserStatus.ONLINE)}
        service, _mock_soulseek, _mock_client = _make_service(users)
        service.demarrer()

        received_statut: list[tuple[str, Any, Any]] = []
        ajout_recu: list[str] = []
        service.client_ajoute.connect(ajout_recu.append)
        service.client_statut_change.connect(lambda *a: received_statut.append(a))

        evt = _FakeUserStatusEvent("alice", UserStatus.AWAY)
        service._on_user_status_update(evt)

        assert service._clients["alice"].statut == UserStatus.AWAY
        assert ajout_recu == []  # Pas d'émission client_ajoute
        assert len(received_statut) == 1
        assert received_statut[0][0] == "alice"
        assert received_statut[0][1] == UserStatus.AWAY  # nouveau
        assert received_statut[0][2] == UserStatus.ONLINE  # ancien

    def test_status_update_offline(self) -> None:
        """Un client qui passe OFFLINE doit être mis à jour."""
        users = {"alice": _mock_user("alice", UserStatus.ONLINE)}
        service, _mock_soulseek, _mock_client = _make_service(users)
        service.demarrer()

        evt = _FakeUserStatusEvent("alice", UserStatus.OFFLINE)
        service._on_user_status_update(evt)

        assert service._clients["alice"].statut == UserStatus.OFFLINE

    def test_info_update_client_inconnu_ignore(self) -> None:
        """UserInfoUpdate pour un inconnu ne doit rien faire."""
        service, _mock_soulseek, _mock_client = _make_service()
        service.demarrer()

        received: list[str] = []
        service.client_info_change.connect(received.append)

        evt = _FakeUserInfoEvent("unknown", description="test")
        service._on_user_info_update(evt)

        assert received == []
        assert "unknown" not in service._clients

    def test_info_update_met_a_jour_champs(self) -> None:
        """UserInfoUpdate doit mettre à jour les champs disponibles."""
        users = {"alice": _mock_user("alice", UserStatus.ONLINE)}
        service, _mock_soulseek, _mock_client = _make_service(users)
        service.demarrer()

        received: list[str] = []
        service.client_info_change.connect(received.append)

        evt = _FakeUserInfoEvent(
            "alice",
            description="Nouvelle description!",
            country="DE",
            avg_speed=2_000_000,
            uploads=5,
            shared_file_count=300,
            shared_folder_count=30,
            slots_free=1,
            has_slots_free=False,
            queue_length=50,
            privileged=True,
        )
        service._on_user_info_update(evt)

        info = service._clients["alice"]
        assert info.description == "Nouvelle description!"
        assert info.pays == "DE"
        assert info.vitesse == 2_000_000
        assert info.uploads == 5
        assert info.fichiers_partages == 300
        assert info.dossiers_partages == 30
        assert info.slots_libres == 1
        assert info.slots_libres_flag is False
        assert info.file_attente == 50
        assert info.privilege is True
        assert received == ["alice"]

    def test_info_update_partiel(self) -> None:
        """UserInfoUpdate avec seulement quelques champs ne doit pas écraser les autres."""
        users = {"alice": _mock_user("alice", UserStatus.ONLINE, country="FR", description="Original")}
        service, _mock_soulseek, _mock_client = _make_service(users)
        service.demarrer()

        evt = _FakeUserInfoEvent("alice", description="Modifiée")
        service._on_user_info_update(evt)

        info = service._clients["alice"]
        assert info.description == "Modifiée"
        assert info.pays == "FR"  # Non écrasé

    def test_info_update_none_values_ignores(self) -> None:
        """UserInfoUpdate avec des valeurs None ne doit pas écraser les existantes."""
        users = {"alice": _mock_user("alice", UserStatus.ONLINE, description="Original")}
        service, _mock_soulseek, _mock_client = _make_service(users)
        service.demarrer()

        evt = _FakeUserInfoEvent("alice", description=None)
        service._on_user_info_update(evt)

        info = service._clients["alice"]
        assert info.description == "Original"  # Préservé car None


# ═════════════════════════════════════════════════════════════════
#  Tests d'intégration (simulation de flux réel)
# ═════════════════════════════════════════════════════════════════


class TestFluxReel:
    def test_cycle_complet_ajout_statut_info(self) -> None:
        """Simule un cycle complet : synchronisation → status update → info update."""
        users = {"alice": _mock_user("alice", UserStatus.ONLINE)}
        service, _mock_soulseek, _mock_client = _make_service(users)

        sync_received: list[list[ClientInfo]] = []
        service.clients_synchronises.connect(sync_received.append)

        service.demarrer()

        # Vérifier synchro initiale
        assert len(sync_received) == 1
        assert sync_received[0][0].statut == UserStatus.ONLINE

        # Alice passe AWAY
        evt = _FakeUserStatusEvent("alice", UserStatus.AWAY)
        service._on_user_status_update(evt)
        assert service._clients["alice"].statut == UserStatus.AWAY

        # Alice reçoit une mise à jour d'info
        info_evt = _FakeUserInfoEvent("alice", description="Bonjour!", slots_free=3)
        service._on_user_info_update(info_evt)
        assert service._clients["alice"].description == "Bonjour!"
        assert service._clients["alice"].slots_libres == 3

        # Vérifier compteurs
        assert service.nombre_actifs() == 1  # AWAY compte comme actif
        assert service.nombre_connectes() == 0  # plus ONLINE

    def test_clients_multiples_statuts(self) -> None:
        """Plusieurs clients de statuts différents."""
        users = {
            "a": _mock_user("a", UserStatus.ONLINE),
            "b": _mock_user("b", UserStatus.AWAY),
            "c": _mock_user("c", UserStatus.OFFLINE),
            "d": _mock_user("d", UserStatus.UNKNOWN),
        }
        service, _mock_soulseek, _mock_client = _make_service(users)
        service.demarrer()

        assert service.nombre_connectes() == 1  # a seulement
        assert service.nombre_actifs() == 2  # a + b
        actifs = service.clients_actifs()
        assert len(actifs) == 3  # a + b + c (exclut UNKNOWN)
        assert service.obtenir_client("d") is not None  # existe mais UNKNOWN
