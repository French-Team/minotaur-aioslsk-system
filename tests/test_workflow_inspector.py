"""Tests pour WorkflowInspector : statuts ACTIVE/STOPPED/UNKNOWN.

Vérifie que _get_bot_status() retourne le bon statut selon
le type d'objet et l'état de son interrupteur (demarrer/arreter).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QFrame, QLabel

from src.gui.devtool.workflow_inspector import WorkflowInspector


# ═══════════════════════════════════════════════════════════════════════════
#  Classes factices pour simuler les différents types d'entités
# ═══════════════════════════════════════════════════════════════════════════


class _BotAvecInterrupteur(QFrame):
    """Bot avec interrupteur (demarrer/arreter) et attribut _actif."""

    def __init__(self, actif: bool = True) -> None:
        super().__init__()
        self._actif = actif

    def demarrer(self) -> None:
        self._actif = True

    def arreter(self) -> None:
        self._actif = False


class _BotAvecEstActif(QFrame):
    """Bot avec interrupteur ET propriété est_actif (plus précis)."""

    def __init__(self, actif: bool = True) -> None:
        super().__init__()
        self._actif = actif

    def demarrer(self) -> None:
        self._actif = True

    def arreter(self) -> None:
        self._actif = False

    @property
    def est_actif(self) -> bool:
        return self._actif


class _BotSansInterrupteur(QFrame):
    """Bot statique : pas de demarrer/arreter (Aide, Accueil, Ordonnanceur)."""
    pass


class _BouclePureAvecEstActif(QObject):
    """Boucle pure QObject (BoucleRooms) avec interrupteur + est_actif."""

    def __init__(self, actif: bool = True) -> None:
        super().__init__()
        self._actif = actif

    def demarrer(self) -> None:
        self._actif = True

    def arreter(self) -> None:
        self._actif = False

    @property
    def est_actif(self) -> bool:
        return self._actif


class _BouclePureSansEstActif(QObject):
    """Boucle pure QObject avec interrupteur mais sans propriété est_actif."""

    def __init__(self, actif: bool = True) -> None:
        super().__init__()
        self._actif = actif

    def demarrer(self) -> None:
        self._actif = True

    def arreter(self) -> None:
        self._actif = False


# ═══════════════════════════════════════════════════════════════════════════
#  Tests
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.qt_heavy
class TestGetBotStatus:
    """WorkflowInspector._get_bot_status() pour les 3 statuts."""

    # Constantes de statut attendues (verrouillage contre les changements)
    ACTIF = ("🟢 ACTIVE", "#a6e3a1")
    STOP = ("🔴 STOPPED", "#f38ba8")
    INCONNU = ("⚪ UNKNOWN", "#6c7086")

    @pytest.fixture(autouse=True)
    def _setup(self, mocker, qapp) -> None:
        """Crée un WorkflowInspector avec dépendances mockées.

        Patche EventBus pour éviter les connexions au vrai bus
        et fournit un main_window factice avec un center vide.
        """
        # Patcher _connect_event_bus() pour éviter les connexions au vrai EventBus
        # On ne patche PAS EventBus lui-même pour garder isinstance(obj, EventBus) fonctionnel
        mocker.patch.object(WorkflowInspector, "_connect_event_bus")

        # Mock main_window avec center minimal
        self.mock_main = MagicMock(spec=["center"])
        self.mock_center = MagicMock()
        self.mock_center._pages = {}
        self.mock_center._clients_actifs_service = None
        self.mock_center.boucle_rooms = None
        self.mock_center._boucle_rooms = None
        self.mock_main.center = self.mock_center

        self.inspector = WorkflowInspector(self.mock_main)

    # ── QFrame AVEC interrupteur ─────────────────────────────────

    def test_bot_interrupteur_actif(self) -> None:
        """Bot avec demarrer/arreter et _actif=True → 🟢 ACTIVE."""
        bot = _BotAvecInterrupteur(actif=True)
        assert self.inspector._get_bot_status(bot) == self.ACTIF

    def test_bot_interrupteur_inactif(self) -> None:
        """Bot avec demarrer/arreter et _actif=False → 🔴 STOPPED."""
        bot = _BotAvecInterrupteur(actif=False)
        assert self.inspector._get_bot_status(bot) == self.STOP

    def test_bot_est_actif_actif(self) -> None:
        """Bot avec est_actif=True → 🟢 ACTIVE (priorité à la propriété)."""
        bot = _BotAvecEstActif(actif=True)
        assert self.inspector._get_bot_status(bot) == self.ACTIF

    def test_bot_est_actif_inactif(self) -> None:
        """Bot avec est_actif=False → 🔴 STOPPED."""
        bot = _BotAvecEstActif(actif=False)
        assert self.inspector._get_bot_status(bot) == self.STOP

    # ── QFrame SANS interrupteur (statiques) ─────────────────────

    def test_bot_sans_interrupteur(self) -> None:
        """Bot sans demarrer/arreter du tout → ⚪ UNKNOWN."""
        bot = _BotSansInterrupteur()
        assert self.inspector._get_bot_status(bot) == self.INCONNU

    # ── Boucle pure QObject (BoucleRooms) ────────────────────────

    def test_boucle_pure_est_actif_actif(self) -> None:
        """Boucle pure (QObject) est_actif=True → 🟢 ACTIVE."""
        boucle = _BouclePureAvecEstActif(actif=True)
        assert self.inspector._get_bot_status(boucle) == self.ACTIF

    def test_boucle_pure_est_actif_inactif(self) -> None:
        """Boucle pure (QObject) est_actif=False → 🔴 STOPPED."""
        boucle = _BouclePureAvecEstActif(actif=False)
        assert self.inspector._get_bot_status(boucle) == self.STOP

    def test_boucle_pure_sans_est_actif_actif(self) -> None:
        """Boucle pure sans est_actif mais _actif=True → 🟢 ACTIVE (fallback _actif)."""
        boucle = _BouclePureSansEstActif(actif=True)
        assert self.inspector._get_bot_status(boucle) == self.ACTIF

    def test_boucle_pure_sans_est_actif_inactif(self) -> None:
        """Boucle pure sans est_actif mais _actif=False → 🔴 STOPPED (fallback _actif)."""
        boucle = _BouclePureSansEstActif(actif=False)
        assert self.inspector._get_bot_status(boucle) == self.STOP


# ═══════════════════════════════════════════════════════════════════════════
#  Classes factices pour _update_loop_stats
# ═══════════════════════════════════════════════════════════════════════════


class _FakeRooms(QObject):
    """Simule BoucleRooms pour les tests de _update_loop_stats."""

    def __init__(self, actif: bool = True, nb_membres: int = 3, nb_rooms: int = 2) -> None:
        super().__init__()
        self._actif = actif
        self.membres = [QObject() for _ in range(nb_membres)]
        self.rooms = [QObject() for _ in range(nb_rooms)]

    @property
    def est_actif(self) -> bool:
        return self._actif

    def demarrer(self) -> None:
        self._actif = True

    def arreter(self) -> None:
        self._actif = False


class _FakeRoomsSansAttributs(QObject):
    """Simule BoucleRooms sans attributs membres/rooms."""

    def __init__(self, actif: bool = True) -> None:
        super().__init__()
        self._actif = actif

    @property
    def est_actif(self) -> bool:
        return self._actif

    def demarrer(self) -> None:
        self._actif = True

    def arreter(self) -> None:
        self._actif = False


class _FakeClientsActifs(QObject):
    """Simule ClientsActifsService pour les tests de _update_loop_stats."""

    def __init__(self, running: bool = True, nb_trackes: int = 10) -> None:
        super().__init__()
        self._running = running
        self._clients = {f"user{i}": QObject() for i in range(nb_trackes)}

    def ping_metrics(self) -> dict:
        return {
            "total_pings": 5,
            "total_reponses": 3,
            "taux_succes": 0.6,
            "temps_moyen": 2.5,
        }

    def demarrer(self) -> None:
        self._running = True

    def arreter(self) -> None:
        self._running = False


class _FakeClientsActifsSansPingMetrics(QObject):
    """Simule ClientsActifsService sans la méthode ping_metrics."""

    def __init__(self) -> None:
        super().__init__()
        self._running = True
        self._clients = {"alice": QObject(), "bob": QObject(), "charlie": QObject()}

    def demarrer(self) -> None:
        self._running = True

    def arreter(self) -> None:
        self._running = False


class _FakeClientsActifsZeroPing(QObject):
    """Simule ClientsActifsService sans aucun ping effectué."""

    def __init__(self) -> None:
        super().__init__()
        self._running = True
        self._clients = {"alice": QObject(), "bob": QObject()}

    def ping_metrics(self) -> dict:
        return {
            "total_pings": 0,
            "total_reponses": 0,
            "taux_succes": 0.0,
            "temps_moyen": 0.0,
        }

    def demarrer(self) -> None:
        self._running = True

    def arreter(self) -> None:
        self._running = False


class _FakeAutreEntite(QObject):
    """Simule une entité générique (Soulseek, EventBus, etc.)."""

    def __init__(self) -> None:
        super().__init__()
        self.is_connected = False


# ═══════════════════════════════════════════════════════════════════════════
#  Tests _update_loop_stats
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.qt_heavy
class TestUpdateLoopStats:
    """WorkflowInspector._update_loop_stats() pour Rooms, Clients Actifs et autres."""

    @pytest.fixture(autouse=True)
    def _setup(self, mocker, qapp) -> None:
        """Crée un WorkflowInspector avec dépendances mockées."""
        mocker.patch.object(WorkflowInspector, "_connect_event_bus")

        self.mock_main = MagicMock(spec=["center"])
        self.mock_center = MagicMock()
        self.mock_center._pages = {}
        self.mock_center._clients_actifs_service = None
        self.mock_center.boucle_rooms = None
        self.mock_center._boucle_rooms = None
        self.mock_main.center = self.mock_center

        self.inspector = WorkflowInspector(self.mock_main)

    def _add_card(self, name: str, instance: QObject) -> QFrame:
        """Crée une carte via _create_bot_card et l'injecte dans l'inspecteur."""
        card = self.inspector._create_bot_card(name, instance)
        self.inspector._bot_cards[name] = card
        self.inspector._bot_instances[name] = instance
        return card

    def _get_loop_label(self, name: str) -> QLabel | None:
        """Retourne le QLabel de la ligne boucle pour une carte donnée."""
        card = self.inspector._bot_cards.get(name)
        if card is None:
            return None
        return card.findChild(QLabel, f"loop_{name}")

    # ── Rooms ──────────────────────────────────────────────────

    def test_rooms_actif_avec_donnees(self) -> None:
        """Rooms actif avec membres + rooms → affiche les comptes."""
        instance = _FakeRooms(actif=True, nb_membres=5, nb_rooms=3)
        self._add_card("Rooms", instance)

        self.inspector._update_loop_stats("Rooms")

        lbl = self._get_loop_label("Rooms")
        assert lbl is not None
        assert not lbl.isHidden(), "le label doit être visible (setVisible(True))"
        assert "🏠 3 rooms" in lbl.text()
        assert "👥 5 membres" in lbl.text()

    def test_rooms_actif_vide(self) -> None:
        """Rooms actif sans membres ni rooms → affiche 0 partout."""
        instance = _FakeRooms(actif=True, nb_membres=0, nb_rooms=0)
        self._add_card("Rooms", instance)

        self.inspector._update_loop_stats("Rooms")

        lbl = self._get_loop_label("Rooms")
        assert lbl is not None
        assert "🏠 0 rooms" in lbl.text()
        assert "👥 0 membres" in lbl.text()

    def test_rooms_actif_sans_attributs(self) -> None:
        """Rooms actif sans attributs membres/rooms → 0 par défaut."""
        instance = _FakeRoomsSansAttributs(actif=True)
        self._add_card("Rooms", instance)

        self.inspector._update_loop_stats("Rooms")

        lbl = self._get_loop_label("Rooms")
        assert lbl is not None
        assert "🏠 0 rooms" in lbl.text()
        assert "👥 0 membres" in lbl.text()

    def test_rooms_inactif(self) -> None:
        """Rooms désactivé → affiche 'boucle arrêtée'."""
        instance = _FakeRooms(actif=False)
        self._add_card("Rooms", instance)

        self.inspector._update_loop_stats("Rooms")

        lbl = self._get_loop_label("Rooms")
        assert lbl is not None
        assert "boucle arrêtée" in lbl.text()

    # ── Clients Actifs ─────────────────────────────────────────

    def test_clients_actifs_actif_avec_metriques(self) -> None:
        """ClientsActifs actif avec métriques → affiche les stats ping."""
        instance = _FakeClientsActifs(running=True, nb_trackes=10)
        self._add_card("Clients Actifs", instance)

        self.inspector._update_loop_stats("Clients Actifs")

        lbl = self._get_loop_label("Clients Actifs")
        assert lbl is not None
        assert not lbl.isHidden(), "le label doit être visible (setVisible(True))"
        assert "👥 10 trackés" in lbl.text()
        assert "📊 3/5 réponses" in lbl.text()
        assert "60%" in lbl.text()

    def test_clients_actifs_actif_aucun_ping(self) -> None:
        """ClientsActifs actif mais 0 ping → affiche 'aucun ping'."""
        instance = _FakeClientsActifsZeroPing()
        self._add_card("Clients Actifs", instance)

        self.inspector._update_loop_stats("Clients Actifs")

        lbl = self._get_loop_label("Clients Actifs")
        assert lbl is not None
        assert "👥 2 trackés" in lbl.text()
        assert "aucun ping" in lbl.text()

    def test_clients_actifs_actif_sans_metriques(self) -> None:
        """ClientsActifs actif sans méthode ping_metrics → simple 'X trackés'."""
        instance = _FakeClientsActifsSansPingMetrics()
        self._add_card("Clients Actifs", instance)

        self.inspector._update_loop_stats("Clients Actifs")

        lbl = self._get_loop_label("Clients Actifs")
        assert lbl is not None
        assert "👥 3 trackés" in lbl.text()

    def test_clients_actifs_inactif(self) -> None:
        """ClientsActifs désactivé → affiche 'service arrêté'."""
        instance = _FakeClientsActifs(running=False)
        self._add_card("Clients Actifs", instance)

        self.inspector._update_loop_stats("Clients Actifs")

        lbl = self._get_loop_label("Clients Actifs")
        assert lbl is not None
        assert "service arrêté" in lbl.text()

    # ── Autres entités / Edge cases ────────────────────────────

    def test_cacher_pour_autre_entite(self) -> None:
        """Entité autre que Rooms/ClientsActifs → label invisible."""
        instance = _FakeAutreEntite()
        self._add_card("Soulseek", instance)

        lbl = self._get_loop_label("Soulseek")
        assert lbl is not None
        assert lbl.isHidden(), "le label doit être caché pour les entités autres que Rooms/ClientsActifs"

    def test_carte_manquante(self) -> None:
        """Carte absente → pas d'erreur."""
        # Aucune carte pour "Rooms"
        self.inspector._update_loop_stats("Rooms")
        # Ne doit pas lever d'exception

    def test_instance_manquante(self) -> None:
        """Instance absente mais carte présente → pas d'erreur."""
        instance = _FakeRooms(actif=True)
        card = self.inspector._create_bot_card("Rooms", instance)
        self.inspector._bot_cards["Rooms"] = card
        # Ne PAS ajouter l'instance dans _bot_instances

        self.inspector._update_loop_stats("Rooms")
        # Ne doit pas lever d'exception

    def test_sans_label_loop(self) -> None:
        """Carte sans label loop_* → pas d'erreur."""
        card = QFrame()
        self.inspector._bot_cards["SansLabel"] = card
        self.inspector._bot_instances["SansLabel"] = QObject()

        self.inspector._update_loop_stats("SansLabel")
        # Ne doit pas lever d'exception
