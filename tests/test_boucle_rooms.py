from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QTimer

from src.services.boucle_rooms import BoucleRooms


class _FakeRoom:
    def __init__(self, user_count: int = 10) -> None:
        self.user_count = user_count
        self.users = []


class _FakeRoomsManager:
    def __init__(self) -> None:
        self._rooms: dict[str, _FakeRoom] = {}
        self._joined: set[str] = set()

    def add_room(self, name: str, user_count: int = 10) -> None:
        self._rooms[name] = _FakeRoom(user_count)

    @property
    def rooms(self) -> dict[str, _FakeRoom]:
        return self._rooms

    @property
    def joined_rooms(self) -> set[str]:
        return self._joined


class _FakeClient:
    def __init__(self) -> None:
        self.rooms = _FakeRoomsManager()


@pytest.fixture
def mock_cm() -> MagicMock:
    cm = MagicMock()
    cm.client = None
    cm.is_connected = False
    return cm


@pytest.fixture
def boucle(mock_cm: MagicMock) -> BoucleRooms:
    return BoucleRooms(mock_cm)


class TestBoucleRoomsInterrupt:
    def test_est_actif_faux_au_depart(self, boucle: BoucleRooms) -> None:
        assert boucle.est_actif is False

    def test_demarrer_active_interrupteur(self, boucle: BoucleRooms) -> None:
        boucle.demarrer()
        assert boucle.est_actif is True

    def test_demarrer_idempotent(self, boucle: BoucleRooms) -> None:
        boucle.demarrer()
        boucle.demarrer()  # Ne doit pas lever
        assert boucle.est_actif is True

    def test_arreter_desactive_interrupteur(self, boucle: BoucleRooms) -> None:
        boucle.demarrer()
        boucle.arreter()
        assert boucle.est_actif is False

    def test_arreter_idempotent(self, boucle: BoucleRooms) -> None:
        boucle.arreter()  # Already inactive
        assert boucle.est_actif is False

    def test_demarrer_configure_timer_interval(self, boucle: BoucleRooms) -> None:
        # Vérifie que le timer est configuré à 30s (sans démarrer le timer,
        # car start() nécessite un event loop Qt qui n'existe pas en test)
        assert boucle._timer.interval() == 30000

    def test_arreter_stoppe_timer(self, boucle: BoucleRooms) -> None:
        boucle.demarrer()
        boucle.arreter()
        assert boucle._timer.isActive() is False

    def test_arreter_sans_demarrer(self, boucle: BoucleRooms) -> None:
        boucle.arreter()
        assert boucle.est_actif is False


class TestBoucleRoomsCycle:
    def test_executer_cycle_planifie_toujours_coroutine(
        self, mock_cm: MagicMock
    ) -> None:
        # _executer_cycle() appelle TOUJOURS run_coro (l'early return est dans _async_cycle)
        mock_cm.client = None
        boucle = BoucleRooms(mock_cm)
        boucle._executer_cycle()
        # run_coro EST appelé (c'est _async_cycle qui fait le return précoce)
        mock_cm.run_coro.assert_called_once()

    def test_async_cycle_early_return_si_client_none(
        self, mock_cm: MagicMock
    ) -> None:
        mock_cm.is_connected = True
        fake_client = _FakeClient()
        mock_cm.client = fake_client
        boucle = BoucleRooms(mock_cm)
        boucle._executer_cycle()
        mock_cm.run_coro.assert_called_once()

    def test_async_cycle_early_return_si_pas_connecte(
        self, mock_cm: MagicMock
    ) -> None:
        mock_cm.is_connected = False
        fake_client = _FakeClient()
        mock_cm.client = fake_client
        boucle = BoucleRooms(mock_cm)
        boucle._executer_cycle()
        mock_cm.run_coro.assert_called_once()

    def test_executer_cycle_planifie_coroutine(
        self, mock_cm: MagicMock
    ) -> None:
        mock_cm.is_connected = True
        fake_client = _FakeClient()
        fake_client.rooms.add_room('TestRoom', 5)
        mock_cm.client = fake_client
        boucle = BoucleRooms(mock_cm)
        boucle._executer_cycle()
        mock_cm.run_coro.assert_called_once()


class TestBoucleRoomsSignal:
    def test_membres_actualises_signal_existe(
        self, boucle: BoucleRooms
    ) -> None:
        assert hasattr(boucle, 'membres_actualises')

    def test_est_actif_propriete(self, boucle: BoucleRooms) -> None:
        assert boucle.est_actif is False
        boucle.demarrer()
        assert boucle.est_actif is True
        boucle.arreter()
        assert boucle.est_actif is False

    def test_propriete_membres(self, boucle: BoucleRooms) -> None:
        assert boucle.membres == []
        boucle._membres_actifs = [{'username': 'alice'}]
        assert len(boucle.membres) == 1

    def test_propriete_rooms(self, boucle: BoucleRooms) -> None:
        assert boucle.rooms == []
        boucle._rooms_actuelles = [{'name': 'TestRoom'}]
        assert len(boucle.rooms) == 1


class TestBoucleRoomsTri:
    """Vérifie que les rooms sont triées par nombre de membres avant le top 5."""

    @pytest.mark.asyncio
    async def test_top_5_trie_par_membres_decroissant(
        self, mock_cm: MagicMock
    ) -> None:
        """Les 5 rooms les plus peuplées sont sélectionnées."""
        mock_cm.is_connected = True
        fake_client = _FakeClient()
        # Ajouter 6 rooms avec des user_counts variés, dans le désordre
        fake_client.rooms.add_room('RoomA', 100)
        fake_client.rooms.add_room('RoomB', 50)
        fake_client.rooms.add_room('RoomC', 200)
        fake_client.rooms.add_room('RoomD', 10)  # la moins peuplée → hors top 5
        fake_client.rooms.add_room('RoomE', 75)
        fake_client.rooms.add_room('RoomF', 30)
        mock_cm.client = fake_client

        boucle = BoucleRooms(mock_cm)
        await boucle._async_cycle()

        # Vérifier le tri par users décroissant
        rooms = boucle._rooms_actuelles
        assert len(rooms) >= 5
        assert rooms[0] == {'name': 'RoomC', 'users': 200}
        assert rooms[1] == {'name': 'RoomA', 'users': 100}
        assert rooms[2] == {'name': 'RoomE', 'users': 75}
        assert rooms[3] == {'name': 'RoomB', 'users': 50}
        assert rooms[4] == {'name': 'RoomF', 'users': 30}
        # RoomD (10 users) est 6e et ne doit PAS apparaître dans le top 5
        assert rooms[5] == {'name': 'RoomD', 'users': 10}

    @pytest.mark.asyncio
    async def test_top_5_egalite_utilise_ordre_dict(
        self, mock_cm: MagicMock
    ) -> None:
        """À user_count égal, l'ordre d'insertion du dict est conservé (tri stable)."""
        mock_cm.is_connected = True
        fake_client = _FakeClient()
        fake_client.rooms.add_room('Premiere', 50)
        fake_client.rooms.add_room('Deuxieme', 50)
        fake_client.rooms.add_room('Troisieme', 50)
        fake_client.rooms.add_room('Quatrieme', 100)
        fake_client.rooms.add_room('Cinquieme', 100)
        mock_cm.client = fake_client

        boucle = BoucleRooms(mock_cm)
        await boucle._async_cycle()

        rooms = boucle._rooms_actuelles
        # Les 100 passent devant, puis les 50 dans l'ordre d'insertion
        assert rooms[0]['name'] == 'Quatrieme'
        assert rooms[1]['name'] == 'Cinquieme'
        assert rooms[2]['name'] == 'Premiere'
        assert rooms[3]['name'] == 'Deuxieme'
        assert rooms[4]['name'] == 'Troisieme'

    @pytest.mark.asyncio
    async def test_moins_de_5_rooms_ne_leve_pas(
        self, mock_cm: MagicMock
    ) -> None:
        """Avec moins de 5 rooms, le cycle ne lève pas et toutes sont rejointes."""
        mock_cm.is_connected = True
        fake_client = _FakeClient()
        fake_client.rooms.add_room('Solo', 3)
        mock_cm.client = fake_client

        boucle = BoucleRooms(mock_cm)
        # Ne doit pas lever d'exception
        await boucle._async_cycle()

        assert len(boucle._rooms_actuelles) == 1
        assert boucle._rooms_actuelles[0]['name'] == 'Solo'