from __future__ import annotations

import ast
from typing import Any, Generator
from unittest.mock import MagicMock, PropertyMock

import pytest
from PySide6.QtWidgets import QApplication

from src.services.boucle_rooms import BoucleRooms


# ── Fake bots pour les tests ─────────────────────────────────────


class _FakeBotWithLoop:
    def __init__(self) -> None:
        self._actif = False

    def demarrer(self) -> None:
        self._actif = True

    def arreter(self) -> None:
        self._actif = False

    @property
    def est_actif(self) -> bool:
        return self._actif


class _FakeBotWithoutLoop:
    pass  # Pas de demarrer()/arreter()


class _FakeRoomsManager:
    def __init__(self) -> None:
        self._rooms: dict[str, object] = {}
        self._joined: set[str] = set()

    @property
    def rooms(self) -> dict[str, object]:
        return self._rooms

    @property
    def joined_rooms(self) -> set[str]:
        return self._joined


class _FakeClient:
    def __init__(self) -> None:
        self.rooms = _FakeRoomsManager()


class _FakeCM:
    def __init__(self) -> None:
        self.client: object | None = None
        self.is_connected = False

    def run_coro(self, coro: object) -> None:
        pass


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _patch_soulseek(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Mock soulseek_service pour éviter l'accès réseau pendant les tests."""
    mock_slsk = MagicMock()
    type(mock_slsk).is_connected = PropertyMock(return_value=False)
    monkeypatch.setattr("src.gui.layout.center.soulseek_service", mock_slsk)
    yield


@pytest.fixture
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def fake_cm() -> _FakeCM:
    return _FakeCM()


# ── Tests Start/Stop Loop mapping ───────────────────────────────


@pytest.mark.qt_heavy
class TestStartStopLoopMapping:
    @pytest.fixture
    def center(self, qapp: QApplication) -> QWidget:
        from src.gui.layout.center import CenterZone

        center = CenterZone()
        # Remplacer les pages par des fakes
        center._pages = {
            'Recherche': _FakeBotWithLoop(),
            'telechargements': _FakeBotWithLoop(),
            'Clients Actifs': _FakeBotWithLoop(),
            'Surveillance': _FakeBotWithLoop(),
            'Bibliothèque': _FakeBotWithLoop(),
            'Wishlist': _FakeBotWithLoop(),
            'Planificateur': _FakeBotWithLoop(),
            'Optimiseur': _FakeBotWithLoop(),
            'Ordonnanceur': MagicMock(),  # n'a pas demarrer()
        }
        return center

    def test_start_loop_appelle_demarrer(self, center: QWidget) -> None:
        bot = center._pages['Recherche']
        result = center._start_loop('Recherche')
        assert result is True
        assert bot.est_actif is True

    def test_stop_loop_appelle_arreter(self, center: QWidget) -> None:
        bot = center._pages['Recherche']
        bot.demarrer()  # démarrer d'abord
        result = center._stop_loop('Recherche')
        assert result is True
        assert bot.est_actif is False

    def test_start_stop_cycle_complet(self, center: QWidget) -> None:
        bot = center._pages['Clients Actifs']
        assert bot.est_actif is False

        started = center._start_loop('Clients Actifs')
        assert started is True
        assert bot.est_actif is True

        stopped = center._stop_loop('Clients Actifs')
        assert stopped is True
        assert bot.est_actif is False

    def test_start_loop_unknown_bot_retourne_false(self, center: QWidget) -> None:
        result = center._start_loop('Inconnu')
        assert result is False

    def test_stop_loop_unknown_bot_retourne_false(self, center: QWidget) -> None:
        result = center._stop_loop('Inconnu')
        assert result is False

    def test_start_loop_bot_sans_demarrer_retourne_false(self, center: QWidget) -> None:
        # Bot sans méthode demarrer() — retour False
        center._pages['BotSansLoop'] = _FakeBotWithoutLoop()
        result = center._start_loop('BotSansLoop')
        assert result is False

    def test_stop_loop_bot_sans_arreter_retourne_false(self, center: QWidget) -> None:
        # Bot sans méthode arreter() — retour False
        center._pages['BotSansLoop'] = _FakeBotWithoutLoop()
        result = center._stop_loop('BotSansLoop')
        assert result is False

    def test_start_loop_bot_sans_loop_non_crash(self, center: QWidget) -> None:
        # Bot 'SansLoop' n'a pas de méthode demarrer — retour False
        center._pages['SansLoop'] = _FakeBotWithoutLoop()
        result = center._start_loop('SansLoop')
        assert result is False

    def test_start_loop_tous_les_bots_non_rooms(self, center: QWidget) -> None:
        # On teste tous les bots sauf Rooms (qui nécessite _boucle_rooms non configuré ici)
        bots_connus = [
            'Recherche',
            'Téléchargement',
            'Clients Actifs',
            'Surveillance',
            'Bibliothèque',
            'Wishlist',
            'Planificateur',
            'Optimiseur',
        ]
        for name in bots_connus:
            result = center._start_loop(name)
            # Tous ces bots ont demarrer() donc doivent retourner True
            assert result is True, f'_start_loop({name!r}) devrait retourner True'

    def test_stop_loop_tous_les_bots_non_rooms(self, center: QWidget) -> None:
        # Miroir stop pour tous les bots non-Rooms
        bots_connus = [
            'Recherche',
            'Téléchargement',
            'Clients Actifs',
            'Surveillance',
            'Bibliothèque',
            'Wishlist',
            'Planificateur',
            'Optimiseur',
        ]
        for name in bots_connus:
            center._start_loop(name)  # démarrer d'abord
            result = center._stop_loop(name)
            # Tous ces bots ont arreter() donc doivent retourner True
            assert result is True, f'_stop_loop({name!r}) devrait retourner True'

    # ── Tests individuels pour les 5 nouveaux bots ────────────────

    def test_start_loop_recherche(self, center: QWidget) -> None:
        bot = center._pages['Recherche']
        result = center._start_loop('Recherche')
        assert result is True
        assert bot.est_actif is True

    def test_stop_loop_recherche(self, center: QWidget) -> None:
        bot = center._pages['Recherche']
        center._start_loop('Recherche')
        result = center._stop_loop('Recherche')
        assert result is True
        assert bot.est_actif is False

    def test_start_loop_telechargement(self, center: QWidget) -> None:
        bot = center._pages['telechargements']
        result = center._start_loop('Téléchargement')
        assert result is True
        assert bot.est_actif is True

    def test_stop_loop_telechargement(self, center: QWidget) -> None:
        bot = center._pages['telechargements']
        center._start_loop('Téléchargement')
        result = center._stop_loop('Téléchargement')
        assert result is True
        assert bot.est_actif is False

    def test_start_loop_surveillance(self, center: QWidget) -> None:
        bot = center._pages['Surveillance']
        result = center._start_loop('Surveillance')
        assert result is True
        assert bot.est_actif is True

    def test_stop_loop_surveillance(self, center: QWidget) -> None:
        bot = center._pages['Surveillance']
        center._start_loop('Surveillance')
        result = center._stop_loop('Surveillance')
        assert result is True
        assert bot.est_actif is False

    def test_start_loop_bibliotheque(self, center: QWidget) -> None:
        bot = center._pages['Bibliothèque']
        result = center._start_loop('Bibliothèque')
        assert result is True
        assert bot.est_actif is True

    def test_stop_loop_bibliotheque(self, center: QWidget) -> None:
        bot = center._pages['Bibliothèque']
        center._start_loop('Bibliothèque')
        result = center._stop_loop('Bibliothèque')
        assert result is True
        assert bot.est_actif is False

    def test_start_loop_optimiseur(self, center: QWidget) -> None:
        bot = center._pages['Optimiseur']
        result = center._start_loop('Optimiseur')
        assert result is True
        assert bot.est_actif is True

    def test_stop_loop_optimiseur(self, center: QWidget) -> None:
        bot = center._pages['Optimiseur']
        center._start_loop('Optimiseur')
        result = center._stop_loop('Optimiseur')
        assert result is True
        assert bot.est_actif is False


@pytest.mark.qt_heavy
class TestBoucleRoomsStartStop:
    def test_boucle_rooms_est_actif_faux_au_depart(self, fake_cm: _FakeCM) -> None:
        br = BoucleRooms(fake_cm)
        assert br.est_actif is False

    def test_boucle_rooms_demarrer_active_est_actif(self, fake_cm: _FakeCM) -> None:
        br = BoucleRooms(fake_cm)
        br.demarrer()
        assert br.est_actif is True

    def test_boucle_rooms_arreter_desactive_est_actif(self, fake_cm: _FakeCM) -> None:
        br = BoucleRooms(fake_cm)
        br.demarrer()
        br.arreter()
        assert br.est_actif is False

    def test_boucle_rooms_demarrer_idempotent(self, fake_cm: _FakeCM) -> None:
        br = BoucleRooms(fake_cm)
        br.demarrer()
        br.demarrer()  # Ne doit pas lever
        assert br.est_actif is True

    def test_boucle_rooms_arreter_idempotent(self, fake_cm: _FakeCM) -> None:
        br = BoucleRooms(fake_cm)
        br.arreter()
        assert br.est_actif is False

    def test_boucle_rooms_start_stop_cycle(self, fake_cm: _FakeCM) -> None:
        br = BoucleRooms(fake_cm)
        assert br.est_actif is False
        br.demarrer()
        assert br.est_actif is True
        br.arreter()
        assert br.est_actif is False

    def test_boucle_rooms_membres_propriete(self, fake_cm: _FakeCM) -> None:
        br = BoucleRooms(fake_cm)
        assert br.membres == []
        br._membres_actifs = [{'username': 'alice', 'room': 'Test', 'status': 'online'}]
        assert len(br.membres) == 1

    def test_boucle_rooms_rooms_propriete(self, fake_cm: _FakeCM) -> None:
        br = BoucleRooms(fake_cm)
        assert br.rooms == []
        br._rooms_actuelles = [{'name': 'TestRoom', 'users': 5}]
        assert len(br.rooms) == 1

    def test_boucle_rooms_timer_config_intervale(self, fake_cm: _FakeCM) -> None:
        br = BoucleRooms(fake_cm)
        # Vérifie que le timer est configuré à 30s sans le démarrer
        assert br._timer.interval() == 30000


@pytest.mark.qt_heavy
class TestCenterBoucleRoomsIntegration:
    @pytest.fixture
    def center_avec_boucle(self, qapp: QApplication) -> QWidget:
        from src.gui.layout.center import CenterZone

        center = CenterZone()
        return center

    def test_boucle_rooms_none_avant_connexion(self, center_avec_boucle: QWidget) -> None:
        assert center_avec_boucle._boucle_rooms is None

    def test_boucle_rooms_initialise_apres_set_connexion_manager(
        self, center_avec_boucle: QWidget
    ) -> None:
        fake_cm = MagicMock()
        fake_cm.client = None
        fake_cm.is_connected = False
        center_avec_boucle.set_connexion_manager(fake_cm)
        assert center_avec_boucle._boucle_rooms is not None
        assert isinstance(center_avec_boucle._boucle_rooms, BoucleRooms)

    def test_boucle_rooms_propriete_retourne_boucle(
        self, center_avec_boucle: QWidget
    ) -> None:
        fake_cm = MagicMock()
        fake_cm.client = None
        fake_cm.is_connected = False
        assert center_avec_boucle.boucle_rooms is None
        center_avec_boucle.set_connexion_manager(fake_cm)
        assert center_avec_boucle.boucle_rooms is not None

    def test_start_loop_rooms_demarre_boucle_rooms(
        self, center_avec_boucle: QWidget
    ) -> None:
        fake_cm = MagicMock()
        fake_cm.client = None
        fake_cm.is_connected = False
        center_avec_boucle.set_connexion_manager(fake_cm)

        result = center_avec_boucle._start_loop('Rooms')
        assert result is True
        assert center_avec_boucle._boucle_rooms.est_actif is True

    def test_stop_loop_rooms_arrete_boucle_rooms(
        self, center_avec_boucle: QWidget
    ) -> None:
        fake_cm = MagicMock()
        fake_cm.client = None
        fake_cm.is_connected = False
        center_avec_boucle.set_connexion_manager(fake_cm)

        center_avec_boucle._start_loop('Rooms')
        result = center_avec_boucle._stop_loop('Rooms')
        assert result is True
        assert center_avec_boucle._boucle_rooms.est_actif is False

    def test_stop_loop_rooms_sans_demarrer_ne_crash_pas(
        self, center_avec_boucle: QWidget
    ) -> None:
        fake_cm = MagicMock()
        fake_cm.client = None
        fake_cm.is_connected = False
        center_avec_boucle.set_connexion_manager(fake_cm)

        # arreter sans avoir demarrer
        result = center_avec_boucle._stop_loop('Rooms')
        assert result is True  # arreter est idempotent
        assert center_avec_boucle._boucle_rooms.est_actif is False

    def test_start_loop_rooms_avant_connexion_retourne_false(
        self, center_avec_boucle: QWidget
    ) -> None:
        # _boucle_rooms n'est pas encore initialisé
        result = center_avec_boucle._start_loop('Rooms')
        assert result is False


# ── Test statique : symétrie des mappings start/stop ────────────


class TestMappingSymetrie:
    """Vérifie que les dictionnaires de mapping dans _start_loop et _stop_loop
    sont identiques (mêmes clés). Si un mapping est modifié mais pas l'autre,
    ce test échoue."""

    @staticmethod
    def _extraire_mapping_keys(code: str, methode: str) -> set[str]:
        """Extrait les clés du dictionnaire mapping dans une méthode donnée.

        Gère aussi bien ``mapping = {...}`` (ast.Assign) que
        ``mapping: dict[...] = {...}`` (ast.AnnAssign).
        """
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == methode:
                for sub in ast.walk(node):
                    # AnnAssign (mapping: dict[str, ...] = {...}) ou Assign (mapping = {...})
                    if isinstance(sub, ast.AnnAssign):
                        target = sub.target
                        value = sub.value
                    elif isinstance(sub, ast.Assign):
                        target = sub.targets[0]
                        value = sub.value
                    else:
                        continue

                    if isinstance(target, ast.Name) and target.id == "mapping":
                        if isinstance(value, ast.Dict):
                            return {
                                ast.literal_eval(k) for k in value.keys
                                if isinstance(k, ast.Constant) and isinstance(k.value, str)
                            }
        return set()

    def test_mapping_start_et_stop_ont_les_memes_cles(self) -> None:
        """Les clés des deux mappings doivent être rigoureusement identiques."""
        with open("src/gui/layout/center.py", encoding="utf-8") as f:
            code = f.read()

        cles_start = self._extraire_mapping_keys(code, "_start_loop")
        cles_stop = self._extraire_mapping_keys(code, "_stop_loop")

        assert cles_start == cles_stop, (
            f"Les mappings _start_loop et _stop_loop divergent !\n"
            f"Clés en plus dans start (manquantes dans stop) : {cles_start - cles_stop}\n"
            f"Clés en plus dans stop (manquantes dans start) : {cles_stop - cles_start}"
        )

    def test_mapping_contient_les_10_cles_attendues(self) -> None:
        """Vérifie que le mapping des boucles contient les 10 clés attendues."""
        with open("src/gui/layout/center.py", encoding="utf-8") as f:
            code = f.read()

        # On vérifie les deux méthodes (elles sont identiques)
        cles = self._extraire_mapping_keys(code, "_start_loop")
        attendues = {
            "Recherche",
            "Téléchargement",
            "Clients Actifs",
            "Rooms",
            "Surveillance",
            "Bibliothèque",
            "Wishlist",
            "Planificateur",
            "Optimiseur",
            "Ordonnanceur",
        }
        assert cles == attendues, (
            f"Clés attendues manquantes : {attendues - cles}\n"
            f"Clés inattendues présentes : {cles - attendues}"
        )