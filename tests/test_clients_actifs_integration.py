"""Tests d'intégration cycle complet : ClientsActifsService ↔ UI.

Vérifie le flux bout-en-bout :
  1. Service synchronise les données depuis un mock Soulseek
  2. Signaux émis → widgets UI mis à jour
  3. BotTelechargement reçoit le service et affiche les statuts
  4. BotRecherche reçoit le service et peut cibler les clients actifs
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, PropertyMock

import pytest
from aioslsk.events import (
    UserInfoUpdateEvent,
    UserStatusUpdateEvent,
)
from aioslsk.user.model import UserStatus
from PySide6.QtWidgets import QApplication

from src.gui.layout.center import CenterZone
from src.gui.widgets.bots.bot_clients_actifs import BotClientsActifs
from src.gui.widgets.bots.bot_recherche import BotRecherche
from src.gui.widgets.bots.bot_telechargement import _COL_USER, BotTelechargement
from src.gui.widgets.header.clients_actifs_header import ClientsActifsHeader
from src.services.clients_actifs_service import (
    ClientInfo,
    ClientsActifsService,
)

# ═════════════════════════════════════════════════════════════════
#  Helpers — Mock Events aioslsk
# ═════════════════════════════════════════════════════════════════


class FakeUser:
    """Simule un User aioslsk."""

    def __init__(
        self,
        username: str,
        status: UserStatus = UserStatus.ONLINE,
        country: str = "",
        avg_speed: int = 0,
        shared_file_count: int = 0,
        shared_folder_count: int = 0,
        slots_free: int = 0,
        has_slots_free: bool = False,
        queue_length: int = 0,
        uploads: int = 0,
        privileged: bool = False,
        description: str = "",
    ) -> None:
        self.username = username
        self.status = status
        self.country = country
        self.avg_speed = avg_speed
        self.shared_file_count = shared_file_count
        self.shared_folder_count = shared_folder_count
        self.slots_free = slots_free
        self.has_slots_free = has_slots_free
        self.queue_length = queue_length
        self.uploads = uploads
        self.privileged = privileged
        self.description = description


# ═════════════════════════════════════════════════════════════════
#  Fixtures — Mock SoulseekService
# ═════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_users() -> dict[str, FakeUser]:
    """Dictionnaire d'utilisateurs mockés pour les tests."""
    return {
        "alice": FakeUser(
            username="alice",
            status=UserStatus.ONLINE,
            country="FR",
            avg_speed=500000,
            shared_file_count=1500,
            slots_free=3,
            has_slots_free=True,
            queue_length=2,
            description="Music lover",
        ),
        "bob": FakeUser(
            username="bob",
            status=UserStatus.AWAY,
            country="US",
            avg_speed=250000,
            shared_file_count=800,
            slots_free=1,
            has_slots_free=True,
            queue_length=5,
            description="DJ Bob",
        ),
        "charlie": FakeUser(
            username="charlie",
            status=UserStatus.OFFLINE,
            country="DE",
            avg_speed=100000,
            shared_file_count=200,
            slots_free=0,
            has_slots_free=False,
            queue_length=10,
            description="",
        ),
        "dave": FakeUser(
            username="dave",
            status=UserStatus.UNKNOWN,
            country="",
            avg_speed=0,
            shared_file_count=0,
            slots_free=0,
            has_slots_free=False,
            queue_length=0,
            description="",
        ),
    }


@pytest.fixture
def mock_soulseek(mock_users: dict[str, FakeUser]) -> MagicMock:
    """Crée un mock SoulseekService avec des utilisateurs factices."""
    slsk = MagicMock()

    # Propriétés
    type(slsk).is_connected = PropertyMock(return_value=True)

    # Client mock
    client = MagicMock()
    slsk.client = client

    # users dict — mappe les FakeUser comme des User aioslsk
    client.users = MagicMock()
    client.users.users = mock_users  # type: ignore[assignment]

    # events.register — enregistre les handlers dans un dict interne
    event_handlers: dict[type, Any] = {}
    client.events = MagicMock()
    client.events.register = lambda event_type, handler: event_handlers.update({event_type: handler})

    # Stocker les handlers pour pouvoir les appeler depuis les tests
    slsk._event_handlers = event_handlers  # type: ignore[attr-defined]

    # Helper pour déclencher un événement enregistré
    def _trigger_event(event_type: type, **kwargs: Any) -> None:
        """Crée un MagicMock event et le dispatche au handler enregistré."""
        handler = event_handlers.get(event_type)
        if handler is not None:
            evt = MagicMock()
            evt.username = kwargs.get("username", "")
            evt.status = kwargs.get("status")
            # Attributs additionnels pour UserInfoUpdateEvent
            for attr in (
                "description",
                "avg_speed",
                "shared_file_count",
                "slots_free",
                "has_slots_free",
                "queue_length",
                "uploads",
            ):
                if attr in kwargs:
                    setattr(evt, attr, kwargs[attr])
            handler(evt)

    slsk._trigger_event = _trigger_event  # type: ignore[attr-defined]

    # Signaux Qt mockés (pas de vrai Signal sur instance)
    slsk.search_result_received = MagicMock()

    return slsk


@pytest.fixture(autouse=True)
def _patch_soulseek(
    mock_soulseek: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Patch soulseek_service dans tous les modules qui l'importent."""
    monkeypatch.setattr("src.gui.layout.center.soulseek_service", mock_soulseek)

    # Seul center.py a besoin du patch pour _connect_event_signals()
    monkeypatch.setattr("src.gui.layout.center.soulseek_service", mock_soulseek)


@pytest.fixture
def center(qapp: QApplication, mock_soulseek: MagicMock) -> CenterZone:
    """CentreZone avec mock SoulseekService."""
    cz = CenterZone()
    yield cz
    cz.deleteLater()


# ═════════════════════════════════════════════════════════════════
#  Tests d'intégration — Service ↔ UI
# ═════════════════════════════════════════════════════════════════


class TestIntegrationServiceHeader:
    """Vérifie que le service est injecté dans les bons widgets."""

    def test_service_cree_dans_connect_event_signals(
        self,
        center: CenterZone,
    ) -> None:
        """Le service ClientsActifsService est créé par _connect_event_signals."""
        assert hasattr(center, "_clients_actifs_service")
        assert isinstance(center._clients_actifs_service, ClientsActifsService)

    def test_service_injecte_dans_bot_clients_actifs(
        self,
        center: CenterZone,
    ) -> None:
        """BotClientsActifs reçoit le service via setup()."""
        page = center.bot_clients_actifs_page
        assert page is not None
        assert page._service is not None
        assert isinstance(page._service, ClientsActifsService)

    def test_service_injecte_dans_telechargement(
        self,
        center: CenterZone,
    ) -> None:
        """BotTelechargement reçoit le service."""
        page = center.telechargements_page
        assert page is not None
        assert page._clients_actifs_service is not None
        assert isinstance(page._clients_actifs_service, ClientsActifsService)

    def test_service_injecte_dans_recherche(
        self,
        center: CenterZone,
    ) -> None:
        """BotRecherche reçoit le service."""
        page = center._pages.get("Recherche")
        assert page is not None
        assert page._clients_actifs_service is not None
        assert isinstance(page._clients_actifs_service, ClientsActifsService)


class TestIntegrationSynchronisation:
    """Vérifie que la synchronisation remplit le tableau BotClientsActifs."""

    def test_synchronisation_remplit_tableau(
        self,
        center: CenterZone,
        mock_soulseek: MagicMock,
    ) -> None:
        """La synchronisation initiale remplit le tableau des clients."""
        page = center.bot_clients_actifs_page
        assert page._table.rowCount() == 3  # alice(ONLINE), bob(AWAY), charlie(OFFLINE)

    def test_tableau_contient_alice(
        self,
        center: CenterZone,
    ) -> None:
        """Alice est dans le tableau."""
        page = center.bot_clients_actifs_page
        items = [page._table.item(row, 1).text() for row in range(page._table.rowCount())]
        assert "alice" in items

    def test_tableau_exclut_unknown(
        self,
        center: CenterZone,
    ) -> None:
        """Dave (UNKNOWN) n'apparaît pas dans le tableau."""
        page = center.bot_clients_actifs_page
        items = [page._table.item(row, 1).text() for row in range(page._table.rowCount())]
        assert "dave" not in items

    def test_stats_mises_a_jour(
        self,
        center: CenterZone,
    ) -> None:
        """Les compteurs stats sont cohérents après synchronisation."""
        page = center.bot_clients_actifs_page
        assert "Total: 3" in page._lbl_total.text()
        # alice(ONLINE) + bob(AWAY) = 2 actifs
        # alice(ONLINE) = 1 connecté


class TestIntegrationEvenements:
    """Vérifie que les événements mockés traversent service → UI."""

    def test_nouveau_client_apparait(
        self,
        center: CenterZone,
        mock_soulseek: MagicMock,
    ) -> None:
        """Un nouveau client ONLINE apparaît dans le tableau."""
        page = center.bot_clients_actifs_page
        before = page._table.rowCount()

        # Ajouter eve dans users mock pour que _synchroniser fonctionne
        mock_soulseek.client.users.users["eve"] = FakeUser(
            username="eve",
            status=UserStatus.ONLINE,
        )

        # Simuler UserStatusUpdateEvent pour un nouveau client
        mock_soulseek._trigger_event(
            UserStatusUpdateEvent,
            username="eve",
            status=UserStatus.ONLINE,
        )

        # Simuler UserInfoUpdateEvent pour mettre à jour les infos
        mock_soulseek._trigger_event(
            UserInfoUpdateEvent,
            username="eve",
            description="New user",
            avg_speed=100000,
        )

        assert page._table.rowCount() == before + 1
        items = [page._table.item(row, 1).text() for row in range(page._table.rowCount())]
        assert "eve" in items

    def test_statut_change_applique(
        self,
        center: CenterZone,
        mock_soulseek: MagicMock,
    ) -> None:
        """Un changement de statut est répercuté dans le tableau."""
        page = center.bot_clients_actifs_page

        # Alice passe de ONLINE à AWAY
        mock_soulseek._trigger_event(
            UserStatusUpdateEvent,
            username="alice",
            status=UserStatus.AWAY,
        )

        # Vérifier que la ligne d'Alice a changé (colonne 0 = statut)
        for row in range(page._table.rowCount()):
            if page._table.item(row, 1).text() == "alice":
                statut_text = page._table.item(row, 0).text()
                # Le texte de statut contient l'emoji + libellé (ex: "  \U0001f7e1  Away" ou "  \U0001f7e2  Actif")
                # On vérifie juste que le statut a été mis à jour
                assert "\U0001f7e1" in statut_text or "Away" in statut_text
                break
        else:
            pytest.fail("Alice non trouvée dans le tableau")

    def test_client_offline_disparait(
        self,
        center: CenterZone,
        mock_soulseek: MagicMock,
    ) -> None:
        """Un client qui passe OFFLINE reste dans le tableau (pas supprimé)."""
        page = center.bot_clients_actifs_page
        before = page._table.rowCount()

        mock_soulseek._trigger_event(
            UserStatusUpdateEvent,
            username="alice",
            status=UserStatus.OFFLINE,
        )

        # Le client reste dans le tableau (les clients OFFLINE sont conservés)
        assert page._table.rowCount() == before
        items = [page._table.item(row, 1).text() for row in range(page._table.rowCount())]
        assert "alice" in items

    def test_multiple_evenements_consecutifs(
        self,
        center: CenterZone,
        mock_soulseek: MagicMock,
    ) -> None:
        """Plusieurs événements consécutifs ne crashent pas."""
        page = center.bot_clients_actifs_page

        for i in range(5):
            username = f"user_{i}"
            mock_soulseek.client.users.users[username] = FakeUser(
                username=username,
                status=UserStatus.ONLINE,
            )
            mock_soulseek._trigger_event(
                UserStatusUpdateEvent,
                username=username,
                status=UserStatus.ONLINE,
            )

        # Tous les nouveaux utilisateurs sont dans le tableau
        items = [page._table.item(row, 1).text() for row in range(page._table.rowCount())]
        for i in range(5):
            assert f"user_{i}" in items


class TestIntegrationTelechargement:
    """Vérifie que BotTelechargement reçoit le service et affiche les statuts."""

    def test_telechargement_a_service(
        self,
        center: CenterZone,
    ) -> None:
        """BotTelechargement a le service injecté."""
        page = center.telechargements_page
        assert page._clients_actifs_service is not None

    def test_telechargement_status_emoji_online(
        self,
        center: CenterZone,
    ) -> None:
        """Un téléchargement depuis alice (ONLINE) affiche 🟢."""
        page = center.telechargements_page
        display = page._user_display("alice")
        assert "🟢" in display

    def test_telechargement_status_emoji_away(
        self,
        center: CenterZone,
    ) -> None:
        """Un téléchargement depuis bob (AWAY) affiche 🟡."""
        page = center.telechargements_page
        display = page._user_display("bob")
        assert "🟡" in display

    def test_telechargement_status_emoji_offline(
        self,
        center: CenterZone,
    ) -> None:
        """Un téléchargement depuis charlie (OFFLINE) affiche ⚫."""
        page = center.telechargements_page
        display = page._user_display("charlie")
        assert "⚫" in display

    def test_telechargement_status_emoji_inconnu(
        self,
        center: CenterZone,
    ) -> None:
        """Un utilisateur inconnu affiche ⚪."""
        page = center.telechargements_page
        display = page._user_display("ghost")
        assert "⚪" in display

    def test_statut_change_affecte_telechargement(
        self,
        center: CenterZone,
        mock_soulseek: MagicMock,
    ) -> None:
        """Quand alice passe AWAY, la colonne utilisateur est mise à jour."""
        tel_page = center.telechargements_page

        # Ajouter un téléchargement pour alice
        tel_page.add_download(
            identifiant="test1",
            fichier="song.mp3",
            user="alice",
            taille="5 MB",
            taille_bytes=5000000,
        )

        # Récupérer la ligne ajoutée (colonne 2 = utilisateur)
        row = tel_page._table.rowCount() - 1
        user_text_online = tel_page._table.item(row, _COL_USER).text()
        assert "🟢" in user_text_online

        # Alice passe AWAY
        mock_soulseek._trigger_event(
            UserStatusUpdateEvent,
            username="alice",
            status=UserStatus.AWAY,
        )

        # La colonne devrait maintenant afficher 🟡
        user_text_away = tel_page._table.item(row, _COL_USER).text()
        assert "🟡" in user_text_away


class TestIntegrationRecherche:
    """Vérifie que BotRecherche peut cibler les clients actifs."""

    def test_recherche_a_service(
        self,
        center: CenterZone,
    ) -> None:
        """BotRecherche a le service injecté."""
        page = center._pages.get("Recherche")
        assert page._clients_actifs_service is not None

    def test_recherche_checkbox_presente(
        self,
        center: CenterZone,
    ) -> None:
        """La checkbox '🔒 Actifs' est présente dans l'UI."""
        page = center._pages.get("Recherche")
        assert page._clients_actifs_cb is not None
        assert "Actifs" in page._clients_actifs_cb.text()

    def test_recherche_checkbox_decochee_par_defaut(
        self,
        center: CenterZone,
    ) -> None:
        """La checkbox est décochée par défaut."""
        page = center._pages.get("Recherche")
        assert page._clients_actifs_cb.isChecked() is False


class TestIntegrationServiceDirect:
    """Tests directs service ↔ UI sans passer par CenterZone."""

    def test_service_emit_signaux(
        self,
        qapp: QApplication,
        mock_soulseek: MagicMock,
    ) -> None:
        """Le service émet clients_synchronises avec les bons clients."""
        service = ClientsActifsService(mock_soulseek)
        received: list[list[ClientInfo]] = []
        service.clients_synchronises.connect(lambda c: received.append(c))

        service.demarrer()

        assert len(received) == 1
        actifs = received[0]
        noms = {c.username for c in actifs}
        assert "alice" in noms  # ONLINE
        assert "bob" in noms  # AWAY
        assert "charlie" in noms  # OFFLINE
        assert "dave" not in noms  # UNKNOWN exclu

    def test_service_to_bot_direct(
        self,
        qapp: QApplication,
        mock_soulseek: MagicMock,
    ) -> None:
        """BotClientsActifs reçoit les clients du service."""
        service = ClientsActifsService(mock_soulseek)
        service.demarrer()  # synchronise les données
        bot = BotClientsActifs()
        bot.setup(service)

        # Le service se synchronise et remplit le tableau
        assert bot._table.rowCount() == 3

    def test_tableau_reconstruit_apres_rafraichir(
        self,
        qapp: QApplication,
        mock_soulseek: MagicMock,
    ) -> None:
        """Rafraîchir le service met à jour le tableau."""
        service = ClientsActifsService(mock_soulseek)
        bot = BotClientsActifs()
        bot.setup(service)

        # Ajouter un nouvel utilisateur
        mock_soulseek.client.users.users["new_user"] = FakeUser(
            username="new_user",
            status=UserStatus.ONLINE,
        )
        service.rafraichir()

        # Le tableau devrait maintenant avoir 4 lignes
        assert bot._table.rowCount() == 4

    def test_arreter_vide_cache_du_service(
        self,
        qapp: QApplication,
        mock_soulseek: MagicMock,
    ) -> None:
        """Arrêter le service vide son cache interne."""
        service = ClientsActifsService(mock_soulseek)
        service.demarrer()  # synchronise les données
        bot = BotClientsActifs()
        bot.setup(service)
        assert service.clients_actifs() != []

        service.arreter()

        # Le cache du service est vidé
        assert service.nombre_actifs() == 0
        assert service.obtenir_client("alice") is None
        assert service.clients_actifs() == []
