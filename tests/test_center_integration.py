"""Tests d'intégration pour CenterZone — focus sur la page Bibliothèque."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import PropertyMock, patch

import pytest
from PySide6.QtWidgets import QApplication, QStackedWidget

from src.gui.layout.center import CenterZone
from src.gui.widgets.bots.bot_bibliotheque import BotBibliotheque

if TYPE_CHECKING:
    from collections.abc import Generator


# ── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _mock_soulseek() -> Generator[None, None, None]:
    """Patch soulseek_service dans les deux modules qui l'importent."""
    from unittest.mock import MagicMock

    mock_slsk = MagicMock()
    type(mock_slsk).is_connected = PropertyMock(return_value=False)

    patcher1 = patch("src.gui.layout.center.soulseek_service", mock_slsk)
    patcher2 = patch(
        "src.gui.widgets.bots.bot_bibliotheque.soulseek_service",
        mock_slsk,
    )
    patcher1.start()
    patcher2.start()
    try:
        yield
    finally:
        patcher2.stop()
        patcher1.stop()


@pytest.fixture
def center(qapp: QApplication) -> Generator[CenterZone, None, None]:
    """Instance CenterZone prête pour les tests."""
    cz = CenterZone()
    try:
        yield cz
    finally:
        cz.deleteLater()


# ── Tests d'instanciation ──────────────────────────────────────────


@pytest.mark.qt_heavy
class TestInstanciation:
    """Vérifie que CenterZone s'initialise avec la page Bibliothèque."""

    def test_center_zone_can_be_instantiated(self, center: CenterZone) -> None:
        """CenterZone peut être instancié sans erreur."""
        assert center is not None
        assert isinstance(center, CenterZone)

    def test_has_pages_dict(self, center: CenterZone) -> None:
        """Le dictionnaire _pages est présent et non vide."""
        assert hasattr(center, "_pages")
        assert len(center._pages) > 0

    def test_has_stack_widget(self, center: CenterZone) -> None:
        """_stack est un QStackedWidget."""
        assert isinstance(center._stack, QStackedWidget)

    def test_current_page_returns_connexion_initially(self, center: CenterZone) -> None:
        """current_page retourne 'connexion' à l'initialisation."""
        assert center.current_page == "connexion"

    def test_show_page_unknown_does_not_crash(self, center: CenterZone) -> None:
        """show_page() avec un nom inconnu ne plante pas."""
        center.show_page("PageInexistante")
        # La page courante doit rester inchangée
        assert center.current_page == "connexion"


# ── Tests de la page Bibliothèque ──────────────────────────────────


@pytest.mark.qt_heavy
class TestPageBibliotheque:
    """Vérifie l'intégration de la page Bibliothèque dans CenterZone."""

    def test_bibliotheque_page_is_registered(self, center: CenterZone) -> None:
        """La page 'Bibliothèque' est enregistrée dans _pages."""
        assert "Bibliothèque" in center._pages

    def test_bibliotheque_page_is_botbibliotheque(self, center: CenterZone) -> None:
        """La page 'Bibliothèque' est une instance de BotBibliotheque."""
        page = center._pages["Bibliothèque"]
        assert isinstance(page, BotBibliotheque)

    def test_bibliotheque_page_in_stack(self, center: CenterZone) -> None:
        """La page Bibliothèque est bien dans le QStackedWidget."""
        page = center._pages["Bibliothèque"]
        assert center._stack.indexOf(page) >= 0

    def test_show_bibliotheque_page(self, center: CenterZone) -> None:
        """show_page('Bibliothèque') navigue vers la page."""
        center.show_page("Bibliothèque")
        assert center.current_page == "Bibliothèque"

    def test_show_bibliotheque_active_widget(self, center: CenterZone) -> None:
        """Après show_page('Bibliothèque'), le widget actif est le bon."""
        page = center._pages["Bibliothèque"]
        center.show_page("Bibliothèque")
        assert center._stack.currentWidget() is page

    def test_bibliotheque_page_has_page_changed(self, center: CenterZone) -> None:
        """La page Bibliothèque expose le signal page_changed."""
        page = center._pages["Bibliothèque"]
        assert hasattr(page, "page_changed")
        assert page.page_changed is not None

    def test_page_method_returns_bibliotheque(self, center: CenterZone) -> None:
        """page('Bibliothèque') retourne l'instance BotBibliotheque."""
        result = center.page("Bibliothèque")
        assert result is not None
        assert isinstance(result, BotBibliotheque)

    def test_page_method_returns_none_for_unknown(self, center: CenterZone) -> None:
        """page('Inconnu') retourne None."""
        assert center.page("Inconnu") is None

    def test_bibliotheque_page_built_once(self, center: CenterZone) -> None:
        """La page Bibliothèque est créée une seule fois (même instance)."""
        page1 = center._pages["Bibliothèque"]
        page2 = center.page("Bibliothèque")
        assert page1 is page2


# ── Tests de navigation ────────────────────────────────────────────


@pytest.mark.qt_heavy
class TestNavigationBots:
    """Vérifie la navigation entre pages de bots."""

    def test_navigate_from_connexion_to_bibliotheque(self, center: CenterZone) -> None:
        """Navigation depuis la page connexion vers Bibliothèque."""
        assert center.current_page == "connexion"
        center.show_page("Bibliothèque")
        assert center.current_page == "Bibliothèque"

    def test_navigate_back_to_connexion(self, center: CenterZone) -> None:
        """Navigation depuis Bibliothèque vers connexion."""
        center.show_page("Bibliothèque")
        assert center.current_page == "Bibliothèque"
        center.show_page("connexion")
        assert center.current_page == "connexion"

    def test_multiple_navigations(self, center: CenterZone) -> None:
        """Navigation multiple entre pages ne plante pas."""
        for _ in range(5):
            center.show_page("Bibliothèque")
            assert center.current_page == "Bibliothèque"
            center.show_page("connexion")
            assert center.current_page == "connexion"


# ── Tests du signal page_changed ───────────────────────────────────


@pytest.mark.qt_heavy
class TestSignalPageChanged:
    """Vérifie le câblage du signal page_changed de BotBibliotheque."""

    def test_bibliotheque_page_changed_connected(self, center: CenterZone) -> None:
        """Le signal page_changed de BotBibliotheque est connecté à CenterZone.show_page.

        On navigue d'abord vers Bibliothèque, puis on émet le signal
        depuis Bibliothèque pour vérifier que CenterZone navigue.
        """
        biblio = center._pages["Bibliothèque"]
        assert isinstance(biblio, BotBibliotheque)

        # 1. Naviguer d'abord vers Bibliothèque pour établir un point de départ
        center.show_page("Bibliothèque")
        assert center.current_page == "Bibliothèque"

        # 2. Émettre page_changed depuis Bibliothèque — le signal doit déclencher
        #    CenterZone.show_page("connexion") via le câblage
        biblio.page_changed.emit("connexion")

        # 3. CenterZone doit avoir changé de page grâce au signal
        assert center.current_page == "connexion"

    def test_bibliotheque_page_changed_self_reference(self, center: CenterZone) -> None:
        """Le signal page_changed de BotBibliotheque est émettable et capturable."""
        biblio = center._pages["Bibliothèque"]
        assert isinstance(biblio, BotBibliotheque)
        received: list[str] = []
        biblio.page_changed.connect(lambda name: received.append(name))

        biblio.page_changed.emit("Connexion")
        assert len(received) == 1
        assert received[0] == "Connexion"

    def test_show_bibliotheque_from_connexion(self, center: CenterZone) -> None:
        """show_page(\"Bibliothèque\") navigue depuis la page connexion."""
        assert center.current_page == "connexion"
        center.show_page("Bibliothèque")
        assert center.current_page == "Bibliothèque"


# ── Tests de structure interne ─────────────────────────────────────


@pytest.mark.qt_heavy
class TestStructureInterne:
    """Vérifie l'architecture interne en lien avec Bibliothèque."""

    def test_bibliotheque_page_object_name(self, center: CenterZone) -> None:
        """La page Bibliothèque a le bon objectName."""
        page = center._pages["Bibliothèque"]
        assert page.objectName() == "botBibliotheque"

    def test_bibliotheque_has_soulseek_connected_attr(self, center: CenterZone) -> None:
        """La page Bibliothèque expose _soulseek_connected."""
        page = center._pages["Bibliothèque"]
        assert hasattr(page, "_soulseek_connected")

    def test_bibliotheque_has_main_stack(self, center: CenterZone) -> None:
        """La page Bibliothèque expose _main_stack."""
        page = center._pages["Bibliothèque"]
        assert hasattr(page, "_main_stack")
        assert isinstance(page._main_stack, QStackedWidget)

    def test_bibliotheque_disconnected_page_visible_initially(self, center: CenterZone) -> None:
        """À l'init (Soulseek déconnecté), la page déconnectée est visible."""
        page = center._pages["Bibliothèque"]
        assert isinstance(page, BotBibliotheque)
        assert page._main_stack.currentIndex() == 0

    def test_stack_widget_contains_bibliotheque(self, center: CenterZone) -> None:
        """Le QStackedWidget de CenterZone contient la page Bibliothèque."""
        biblio = center._pages["Bibliothèque"]
        assert center._stack.indexOf(biblio) >= 0
