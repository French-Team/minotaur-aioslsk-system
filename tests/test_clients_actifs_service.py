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
#  Tests de ingest_membres_rooms (BoucleRooms integration)
# ═════════════════════════════════════════════════════════════════


class TestIngestMembresRooms:
    """Tests pour la méthode ingest_membres_rooms() de ClientsActifsService.

    Cette méthode reçoit les membres des salons depuis BoucleRooms
    et les intègre dans le suivi des clients actifs.
    """

    def test_ingest_membres_rooms_ajoute_nouveaux(self) -> None:
        """ingest_membres_rooms() ajoute les usernames inconnus au suivi."""
        service, _mock_soulseek, _mock_client = _make_service()
        service.demarrer()

        ajoutes: list[str] = []
        service.client_ajoute.connect(ajoutes.append)

        membres = [
            {"username": "alice", "room": "#musique", "status": "online"},
            {"username": "bob", "room": "#chat", "status": "online"},
        ]
        service.ingest_membres_rooms(membres)

        assert "alice" in service._clients
        assert "bob" in service._clients
        assert ajoutes == ["alice", "bob"]

    def test_ingest_membres_rooms_stats_online(self) -> None:
        """Les membres reçuent statut ONLINE par défaut."""
        service, _mock_soulseek, _mock_client = _make_service()
        service.demarrer()

        membres = [{"username": "alice", "room": "#musique", "status": "online"}]
        service.ingest_membres_rooms(membres)

        assert service._clients["alice"].statut == UserStatus.ONLINE

    def test_ingest_membres_rooms_username_vide_ignore(self) -> None:
        """Les entrées sans username sont ignorées silencieusement."""
        service, _mock_soulseek, _mock_client = _make_service()
        service.demarrer()

        membres = [
            {"username": "", "room": "#musique", "status": "online"},
            {"username": "alice", "room": "#musique", "status": "online"},
        ]
        service.ingest_membres_rooms(membres)

        assert "alice" in service._clients
        assert "" not in service._clients

    def test_ingest_membres_rooms_client_existant_unknown_devient_online(self) -> None:
        """Un client déjà tracked mais avec statut UNKNOWN passe à ONLINE."""
        # Pré-condition : client tracked avec statut UNKNOWN (via synchronisation initiale vide)
        service, _mock_soulseek, _mock_client = _make_service({})
        service.demarrer()

        # Injecter un client UNKNOWN manuellement
        from src.services.clients_actifs_service import ClientInfo

        service._clients["alice"] = ClientInfo(username="alice", statut=UserStatus.UNKNOWN)

        statut_changes: list[tuple[str, Any, Any]] = []
        service.client_statut_change.connect(lambda *a: statut_changes.append(a))

        # ingest avec alice (same username, from room)
        membres = [{"username": "alice", "room": "#musique", "status": "online"}]
        service.ingest_membres_rooms(membres)

        # Devrait mettre à jour UNKNOWN → ONLINE
        assert service._clients["alice"].statut == UserStatus.ONLINE
        assert len(statut_changes) == 1
        assert statut_changes[0][0] == "alice"
        assert statut_changes[0][1] == UserStatus.ONLINE
        assert statut_changes[0][2] == UserStatus.UNKNOWN

    def test_ingest_membres_rooms_client_existant_online_non_mis_a_jour(self) -> None:
        """Un client déjà ONLINE ne déclenche pas de changement de statut."""
        users = {"alice": _mock_user("alice", UserStatus.ONLINE)}
        service, _mock_soulseek, _mock_client = _make_service(users)
        service.demarrer()

        statut_changes: list[tuple[str, Any, Any]] = []
        service.client_statut_change.connect(lambda *a: statut_changes.append(a))

        membres = [{"username": "alice", "room": "#musique", "status": "online"}]
        service.ingest_membres_rooms(membres)

        # ONLINE conservé (pas de changement)
        assert service._clients["alice"].statut == UserStatus.ONLINE
        assert len(statut_changes) == 0

    def test_ingest_membres_rooms_emet_clients_synchronises(self) -> None:
        """ingest_membres_rooms() ré-émet clients_synchronises pour MAJ tableau."""
        service, _mock_soulseek, _mock_client = _make_service()
        service.demarrer()

        sync_signals: list[list[ClientInfo]] = []
        service.clients_synchronises.connect(sync_signals.append)

        membres = [
            {"username": "alice", "room": "#musique", "status": "online"},
            {"username": "bob", "room": "#chat", "status": "online"},
        ]
        service.ingest_membres_rooms(membres)

        assert len(sync_signals) == 1
        synced_usernames = {c.username for c in sync_signals[0]}
        assert "alice" in synced_usernames
        assert "bob" in synced_usernames

    def test_ingest_membres_rooms_liste_vide(self) -> None:
        """ingest_membres_rooms() avec liste vide ne crash pas."""
        service, _mock_soulseek, _mock_client = _make_service()
        service.demarrer()

        service.ingest_membres_rooms([])
        assert service._clients == {}

    def test_ingest_membres_rooms_double_appel(self) -> None:
        """Deux appels à ingest_membres_rooms() fusionnent correctement."""
        service, _mock_soulseek, _mock_client = _make_service()
        service.demarrer()

        service.ingest_membres_rooms([{"username": "alice", "room": "#musique", "status": "online"}])
        service.ingest_membres_rooms([{"username": "bob", "room": "#chat", "status": "online"}])

        assert "alice" in service._clients
        assert "bob" in service._clients
        assert service.nombre_connectes() == 2


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


# ═════════════════════════════════════════════════════════════════
#  Tests du ping par lots (Étapes 1 & 2)
# ═════════════════════════════════════════════════════════════════


class TestPingParLots:
    """Tests pour lancer_ping(), _ping_par_lots() et _on_ping_termine().

    Ces tests vérifient le pipeline ingest → ping → signal ping_termine
    → clients_valides introduit aux Étapes 1 & 2.
    """

    # ── lancer_ping() ───────────────────────────────────────────

    def test_lancer_ping_sans_cm_log_warning(self) -> None:
        """lancer_ping() sans ConnexionManager injecté ne fait rien."""
        service, _mock_soulseek, _mock_client = _make_service()
        service.demarrer()

        # _cm n'est pas injecté → warning, pas de ping
        membres = [{"username": "alice", "room": "#musique", "status": "online"}]
        service.lancer_ping(membres)

        # Aucun appel à run_coro puisque _cm est None
        assert service._ping_en_cours is False

    def test_lancer_ping_declenche_run_coro(self) -> None:
        """lancer_ping() avec _cm injecté appelle run_coro()."""
        import asyncio

        service, mock_soulseek, mock_client = _make_service()
        service.demarrer()

        # Injecter un ConnexionManager factice qui exécute réellement la coroutine
        mock_cm = MagicMock()
        mock_cm.run_coro.side_effect = lambda coro: asyncio.run(coro)
        service.set_connexion_manager(mock_cm)

        membres = [{"username": "alice", "room": "#musique", "status": "online"}]
        service.lancer_ping(membres)

        # run_coro doit avoir été appelé avec une coroutine
        mock_cm.run_coro.assert_called_once()
        call_arg = mock_cm.run_coro.call_args[0][0]
        # Vérifier que c'est une coroutine (_ping_par_lots)
        assert asyncio.iscoroutine(call_arg)

    def test_lancer_ping_ping_deja_en_cours_ignore(self) -> None:
        """lancer_ping() appelé deux fois ignore le second appel."""
        service, mock_soulseek, mock_client = _make_service()
        service.demarrer()
        mock_cm = MagicMock()
        service.set_connexion_manager(mock_cm)

        # Forcer le flag à True (simule un ping en cours)
        service._ping_en_cours = True

        membres = [{"username": "alice", "room": "#musique", "status": "online"}]
        service.lancer_ping(membres)

        # run_coro ne doit PAS être appelé
        mock_cm.run_coro.assert_not_called()

        # Nettoyer le flag pour les autres tests
        service._ping_en_cours = False

    # ── _ping_par_lots() (asynchrone) ───────────────────────────

    @pytest.mark.asyncio
    async def test_ping_par_lots_tous_repondent(self) -> None:
        """_ping_par_lots() retourne tous les usernames si tous répondent."""
        from src.services.clients_actifs_service import _LOT_PING

        service, mock_soulseek, mock_client = _make_service()
        service.demarrer()

        # Remplacer execute par une coroutine qui réussit toujours
        async def _execute_success(_command):
            return MagicMock()
        mock_client.execute = _execute_success

        # Plus de membres que _LOT_PING pour tester le découpage en lots
        membres = [
            {"username": f"user{i:03d}", "room": "#test", "status": "online"}
            for i in range(_LOT_PING + 5)
        ]

        reponses = await service._ping_par_lots(membres)

        assert len(reponses) == len(membres)
        expected = [m["username"] for m in membres]
        assert reponses == expected

    @pytest.mark.asyncio
    async def test_ping_par_lots_certains_echouent(self) -> None:
        """_ping_par_lots() ignore les usernames qui ne répondent pas."""
        service, mock_soulseek, mock_client = _make_service()
        service.demarrer()

        # Faire échouer execute pour certains usernames
        async def mock_execute(command):
            username = getattr(command, "username", "")
            if username and username.startswith("fail"):
                raise RuntimeError("Timeout ping")
            return MagicMock()

        mock_client.execute = mock_execute

        membres = [
            {"username": "alice", "room": "#test", "status": "online"},
            {"username": "fail_alice", "room": "#test", "status": "online"},
            {"username": "bob", "room": "#test", "status": "online"},
            {"username": "fail_bob", "room": "#test", "status": "online"},
            {"username": "carol", "room": "#test", "status": "online"},
        ]

        reponses = await service._ping_par_lots(membres)

        assert len(reponses) == 3
        assert "alice" in reponses
        assert "bob" in reponses
        assert "carol" in reponses
        assert "fail_alice" not in reponses
        assert "fail_bob" not in reponses

    @pytest.mark.asyncio
    async def test_ping_par_lots_username_vide_ignore(self) -> None:
        """_ping_par_lots() ignore les entrées sans username."""
        service, mock_soulseek, mock_client = _make_service()
        service.demarrer()

        async def _execute_ok(_command):
            return MagicMock()
        mock_client.execute = _execute_ok

        membres = [
            {"username": "", "room": "#test", "status": "online"},
            {"username": "alice", "room": "#test", "status": "online"},
        ]

        reponses = await service._ping_par_lots(membres)

        assert reponses == ["alice"]

    @pytest.mark.asyncio
    async def test_ping_par_lots_liste_vide(self) -> None:
        """_ping_par_lots() avec liste vide retourne [] et ne crashe pas."""
        service, mock_soulseek, mock_client = _make_service()
        service.demarrer()

        reponses = await service._ping_par_lots([])

        assert reponses == []

    @pytest.mark.asyncio
    async def test_ping_par_lots_emet_ping_termine(self) -> None:
        """_ping_par_lots() émet ping_termine avec la liste des réponses."""
        service, mock_soulseek, mock_client = _make_service()
        service.demarrer()

        async def _execute_success(_command):
            return MagicMock()
        mock_client.execute = _execute_success

        received_signals: list[list[str]] = []
        service.ping_termine.connect(received_signals.append)

        membres = [
            {"username": "alice", "room": "#test", "status": "online"},
            {"username": "bob", "room": "#test", "status": "online"},
        ]
        await service._ping_par_lots(membres)

        assert len(received_signals) == 1
        assert received_signals[0] == ["alice", "bob"]

    @pytest.mark.asyncio
    async def test_ping_par_lots_flag_ping_en_cours(self) -> None:
        """_ping_par_lots() gère le flag _ping_en_cours (True pendant, False après)."""
        service, mock_soulseek, mock_client = _make_service()
        service.demarrer()

        assert service._ping_en_cours is False

        membres = [{"username": "alice", "room": "#test", "status": "online"}]
        await service._ping_par_lots(membres)

        assert service._ping_en_cours is False  # Remis à False après

    # ── _on_ping_termine() ──────────────────────────────────────

    def test_on_ping_termine_emet_clients_valides(self) -> None:
        """_on_ping_termine() émet clients_valides avec les ClientInfo correspondants."""
        service, mock_soulseek, mock_client = _make_service()
        service.demarrer()

        # Pré-remplir _clients avec des ClientInfo
        from src.services.clients_actifs_service import ClientInfo
        from aioslsk.user.model import UserStatus

        alice = ClientInfo(username="alice", statut=UserStatus.ONLINE, pays="FR", vitesse=500_000)
        bob = ClientInfo(username="bob", statut=UserStatus.ONLINE, pays="US")
        service._clients["alice"] = alice
        service._clients["bob"] = bob

        received: list[list[ClientInfo]] = []
        service.clients_valides.connect(received.append)

        service._on_ping_termine(["alice", "bob"])

        assert len(received) == 1
        result = received[0]
        assert len(result) == 2
        assert result[0].username == "alice"
        assert result[0].pays == "FR"
        assert result[0].vitesse == 500_000
        assert result[1].username == "bob"
        assert result[1].pays == "US"

    def test_on_ping_termine_ignore_inconnus(self) -> None:
        """_on_ping_termine() ignore les usernames pas dans _clients."""
        service, mock_soulseek, mock_client = _make_service()
        service.demarrer()

        # Un seul client dans _clients (ONLINE pour passer le filtre Étape 3)
        from src.services.clients_actifs_service import ClientInfo
        from aioslsk.user.model import UserStatus

        service._clients["alice"] = ClientInfo(username="alice", statut=UserStatus.ONLINE)

        received: list[list[ClientInfo]] = []
        service.clients_valides.connect(received.append)

        # "bob" n'est pas dans _clients → ignoré
        service._on_ping_termine(["alice", "bob"])

        assert len(received) == 1
        assert len(received[0]) == 1
        assert received[0][0].username == "alice"

    def test_on_ping_termine_filtre_non_online(self) -> None:
        """_on_ping_termine() exclut les clients dont le statut n'est pas ONLINE."""
        service, mock_soulseek, mock_client = _make_service()
        service.demarrer()

        from src.services.clients_actifs_service import ClientInfo
        from aioslsk.user.model import UserStatus

        service._clients["alice"] = ClientInfo(username="alice", statut=UserStatus.ONLINE)
        service._clients["bob"] = ClientInfo(username="bob", statut=UserStatus.AWAY)
        service._clients["carol"] = ClientInfo(username="carol", statut=UserStatus.OFFLINE)
        service._clients["dave"] = ClientInfo(username="dave", statut=UserStatus.UNKNOWN)

        received: list[list[ClientInfo]] = []
        service.clients_valides.connect(received.append)

        # Tous ont répondu au ping, mais seuls les ONLINE doivent passer
        service._on_ping_termine(["alice", "bob", "carol", "dave"])

        assert len(received) == 1
        result = received[0]
        assert len(result) == 1
        assert result[0].username == "alice"

    def test_on_ping_termine_liste_vide(self) -> None:
        """_on_ping_termine() avec liste vide émet clients_valides([])."""
        service, mock_soulseek, mock_client = _make_service()
        service.demarrer()

        received: list[list[ClientInfo]] = []
        service.clients_valides.connect(received.append)

        service._on_ping_termine([])

        assert len(received) == 1
        assert received[0] == []

    # ── Pipeline ingest → ping (connexion interne) ──────────────

    def test_ingest_membres_rooms_declenche_lancer_ping(self) -> None:
        """ingest_membres_rooms() déclenche lancer_ping() après l'ingestion."""
        import asyncio

        service, mock_soulseek, mock_client = _make_service()
        service.demarrer()

        # Exécuter réellement la coroutine pour éviter RuntimeWarning
        mock_cm = MagicMock()
        mock_cm.run_coro.side_effect = lambda coro: asyncio.run(coro)
        service.set_connexion_manager(mock_cm)

        membres = [
            {"username": "alice", "room": "#musique", "status": "online"},
            {"username": "bob", "room": "#chat", "status": "online"},
        ]
        service.ingest_membres_rooms(membres)

        # Vérifier que run_coro a été appelé (indirectement via lancer_ping)
        mock_cm.run_coro.assert_called_once()
        call_arg = mock_cm.run_coro.call_args[0][0]
        assert asyncio.iscoroutine(call_arg)

    def test_ingest_ping_termine_connecte_a_on_ping_termine(self) -> None:
        """Le signal ping_termine est connecté à _on_ping_termine dans __init__."""
        service, mock_soulseek, mock_client = _make_service()

        # Vérifier la connexion interne (connectée dans __init__)
        # On vérifie en émettant ping_termine et en voyant si clients_valides est émis
        from src.services.clients_actifs_service import ClientInfo
        from aioslsk.user.model import UserStatus

        # Doit être ONLINE pour passer le filtre Étape 3
        service._clients["alice"] = ClientInfo(username="alice", statut=UserStatus.ONLINE)

        clients_valides_recus: list[list[ClientInfo]] = []
        service.clients_valides.connect(clients_valides_recus.append)

        # Émettre ping_termine → doit déclencher _on_ping_termine → émettre clients_valides
        service.ping_termine.emit(["alice"])

        assert len(clients_valides_recus) == 1
        assert clients_valides_recus[0][0].username == "alice"
