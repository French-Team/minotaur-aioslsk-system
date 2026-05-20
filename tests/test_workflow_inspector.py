"""Tests pour WorkflowInspector : statuts ACTIVE/STOPPED/UNKNOWN.

Vérifie que _get_bot_status() retourne le bon statut selon
le type d'objet et l'état de son interrupteur (demarrer/arreter).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QFrame

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
