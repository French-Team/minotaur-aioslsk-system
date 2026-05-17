"""
Tests unitaires pour les composants UI de la surveillance.

Couvre :
  - Footer badge (_FooterNavButton, FooterZone.set_badge)
  - Compteur unseen BotSurveillance (unseen_count_changed, reset_unseen_count)
  - ToastNotification (affichage, limite, sévérités)
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

from src.gui.layout.footer import FooterZone, _FooterNavButton
from src.gui.widgets.bots.bot_surveillance import BotSurveillance
from src.gui.widgets.toast_notification import ToastNotification
from src.services.event_bus import EventBus

# ── Fixtures (scope module, sans base SQLite) ─────────────────────────────


@pytest.fixture(scope="module")
def qapp():
    """QApplication scope module."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture(autouse=True)
def reset_eventbus():
    """Nettoie le singleton EventBus après chaque test."""
    EventBus._instance = None
    yield
    bus = EventBus._instance
    if bus is not None:
        bus.shutdown()
        EventBus._instance = None


@pytest.fixture
def bus():
    """EventBus sans persistance (tests ne touchent pas à la DB)."""
    return EventBus()


# ═══════════════════════════════════════════════════════════════════════════
#  Tests : Footer badge
# ═══════════════════════════════════════════════════════════════════════════


class TestFooterBadge:
    """Vérifie le badge de comptage sur _FooterNavButton et FooterZone.

    Les tests de visibilité utilisent QMainWindow pour que le badge
    soit effectivement visible dans une hiérarchie fenêtrée.
    """

    def test_badge_starts_hidden(self, qapp):
        """Le badge est masqué par défaut."""
        btn = _FooterNavButton("Surveillance")
        assert not btn._badge.isVisibleTo(btn)

    def test_set_badge_zero_keeps_hidden(self, qapp):
        """set_badge(0) ne rend pas le badge visible, texte vide."""
        btn = _FooterNavButton("Surveillance")
        btn.set_badge(0)
        assert btn._badge.text() == ""

    def test_set_badge_positive_shows_count(self, qapp):
        """set_badge(5) affiche '5' dans une fenêtre visible."""
        btn = _FooterNavButton("Surveillance")
        window = QMainWindow()
        window.setCentralWidget(btn)
        window.show()
        try:
            btn.set_badge(5)
            assert btn._badge.isVisible()
            assert btn._badge.text() == "5"
        finally:
            window.close()
            window.deleteLater()

    def test_set_badge_overflow_99_plus(self, qapp):
        """set_badge(100) affiche '99+' et badge visible."""
        btn = _FooterNavButton("Surveillance")
        window = QMainWindow()
        window.setCentralWidget(btn)
        window.show()
        try:
            btn.set_badge(100)
            assert btn._badge.isVisible()
            assert btn._badge.text() == "99+"
        finally:
            window.close()
            window.deleteLater()

    def test_badge_toggle_hide_show(self, qapp):
        """set_badge(5) rend visible, set_badge(0) masque."""
        btn = _FooterNavButton("Surveillance")
        window = QMainWindow()
        window.setCentralWidget(btn)
        window.show()
        try:
            btn.set_badge(5)
            assert btn._badge.isVisible()
            assert btn._badge.text() == "5"
            btn.set_badge(0)
            assert not btn._badge.isVisible()
        finally:
            window.close()
            window.deleteLater()

    def test_footer_zone_set_badge_delegates(self, qapp):
        """FooterZone.set_badge met à jour le badge du bouton."""
        footer = FooterZone()
        window = QMainWindow()
        window.setCentralWidget(footer)
        window.show()
        try:
            QApplication.processEvents()
            footer.set_badge("Surveillance", 7)
            btn = footer.button("Surveillance")
            assert btn is not None
            # isVisibleTo(btn) vérifie que le badge lui-même est visible
            # sans dépendre de la visibilité de tous les ancêtres
            assert btn._badge.isVisibleTo(btn)
            assert btn._badge.text() == "7"
        finally:
            window.close()
            window.deleteLater()

    def test_footer_zone_set_badge_unknown_name(self, qapp):
        """set_badge avec un nom inconnu ne lève pas d'exception."""
        footer = FooterZone()
        footer.set_badge("Inexistant", 5)  # must not crash

    def test_footer_zone_set_badge_multiple_buttons(self, qapp):
        """set_badge sur deux boutons différents fonctionne."""
        footer = FooterZone()
        footer.set_badge("Surveillance", 3)
        footer.set_badge("Accueil", 1)

        surv = footer.button("Surveillance")
        acc = footer.button("Accueil")
        assert surv._badge.text() == "3"
        assert acc._badge.text() == "1"


# ═══════════════════════════════════════════════════════════════════════════
#  Tests : Compteur unseen BotSurveillance
# ═══════════════════════════════════════════════════════════════════════════


class TestUnseenCounter:
    """Vérifie le compteur d'événements non lus de BotSurveillance."""

    def test_initial_unseen_count_zero(self, qapp):
        """Le compteur démarre à 0."""
        surv = BotSurveillance()
        assert surv._unseen_count == 0

    def test_event_increments_unseen_when_not_visible(self, qapp, bus):
        """Un événement émis incrémente unseen quand le widget n'est pas visible."""
        surv = BotSurveillance()
        assert surv._unseen_count == 0

        bus.emit_event(severity="INFO", category="bot", title="Test")
        assert surv._unseen_count == 1

        bus.emit_event(severity="ERROR", category="reseau", title="Erreur")
        assert surv._unseen_count == 2

    def test_unseen_signal_emitted_on_new_event(self, qapp, bus):
        """Le signal unseen_count_changed est émis avec la bonne valeur."""
        surv = BotSurveillance()
        received_counts: list[int] = []

        surv.unseen_count_changed.connect(received_counts.append)

        bus.emit_event(severity="INFO", category="bot", title="Event 1")
        assert received_counts == [1]

        bus.emit_event(severity="WARN", category="transfert", title="Event 2")
        assert received_counts == [1, 2]

    def test_reset_unseen_count(self, qapp, bus):
        """reset_unseen_count remet le compteur à 0 et émet le signal."""
        surv = BotSurveillance()

        bus.emit_event(severity="INFO", category="bot", title="A")
        bus.emit_event(severity="INFO", category="bot", title="B")
        assert surv._unseen_count == 2

        received: list[int] = []
        surv.unseen_count_changed.connect(received.append)

        surv.reset_unseen_count()
        assert surv._unseen_count == 0
        assert received == [0]

    def test_unseen_not_incremented_when_visible(self, qapp, bus):
        """Unseen n'est pas incrémenté quand le widget est visible."""
        surv = BotSurveillance()
        window = QMainWindow()
        window.setCentralWidget(surv)
        window.show()

        try:
            assert surv.isVisible()
            bus.emit_event(severity="INFO", category="bot", title="Visible event")
            assert surv._unseen_count == 0
        finally:
            window.close()
            window.deleteLater()

    def test_paused_event_not_incremented(self, qapp, bus):
        """Les événements ne sont pas reçus quand le flux est en pause."""
        surv = BotSurveillance()
        surv._paused = True

        bus.emit_event(severity="INFO", category="bot", title="Paused event")
        assert surv._unseen_count == 0  # pas incrémenté car en pause

    def test_reset_after_pause_and_resume(self, qapp, bus):
        """Après pause, unseen s'incrémente à nouveau à la reprise."""
        surv = BotSurveillance()

        bus.emit_event(severity="INFO", category="bot", title="Hors vue")
        assert surv._unseen_count == 1

        surv.reset_unseen_count()
        assert surv._unseen_count == 0

        bus.emit_event(severity="INFO", category="bot", title="Après reset")
        assert surv._unseen_count == 1


# ═══════════════════════════════════════════════════════════════════════════
#  Tests : ToastNotification
# ═══════════════════════════════════════════════════════════════════════════


class TestToastNotification:
    """Vérifie le fonctionnement des notifications toast.

    Les tests de visibilité utilisent QMainWindow pour que les widgets
    soient effectivement visibles dans une hiérarchie fenêtrée.
    """

    def test_show_toast_creates_card(self, qapp):
        """show_toast crée une carte et l'ajoute à la liste interne."""
        parent = QWidget()
        toast = ToastNotification(parent)

        assert len(toast._toasts) == 0
        toast.show_toast("ERROR", "Erreur test", "Message de test")
        assert len(toast._toasts) == 1

    def test_show_toast_multiple_stacks(self, qapp):
        """Plusieurs toasts s'empilent correctement."""
        parent = QWidget()
        toast = ToastNotification(parent)

        toast.show_toast("ERROR", "Erreur 1")
        toast.show_toast("WARN", "Avertissement 1")
        toast.show_toast("INFO", "Info 1")

        assert len(toast._toasts) == 3

    def test_show_toast_multiple_severities(self, qapp):
        """Les trois sévérités fonctionnent (ERROR, WARN, INFO)."""
        parent = QWidget()
        toast = ToastNotification(parent)

        toast.show_toast("ERROR", "Erreur test")
        toast.show_toast("WARN", "Warning test")
        toast.show_toast("INFO", "Info test")

        assert len(toast._toasts) == 3

    def test_max_toasts_limit_enforced(self, qapp):
        """La limite _MAX_TOASTS est respectée (5 max)."""
        parent = QWidget()
        toast = ToastNotification(parent)

        for i in range(7):
            toast.show_toast("INFO", f"Toast {i}")

        assert len(toast._toasts) == 5

    def test_max_toasts_removes_oldest(self, qapp):
        """Les toasts les plus anciens sont supprimés en premier."""
        parent = QWidget()
        toast = ToastNotification(parent)

        for i in range(6):  # 6 dépasse la limite de 5
            toast.show_toast("INFO", f"Toast {i}")

        assert len(toast._toasts) == 5
        # Vérifier via la liste _toasts que le plus ancien a été retiré
        titles = [c._title for c in toast._toasts]
        assert "Toast 0" not in titles
        assert all(f"Toast {i}" in titles for i in range(1, 6))

    def test_remove_toast_removes_and_hides(self, qapp):
        """Après suppression du dernier toast, l'overlay est masqué."""
        parent = QWidget()
        window = QMainWindow()
        window.setCentralWidget(parent)
        window.show()
        toast = ToastNotification(parent)
        try:
            toast.show_toast("ERROR", "Unique")
            assert toast.isVisible()

            toast._remove_toast(toast._toasts[0])
            assert len(toast._toasts) == 0
            assert not toast.isVisible()
        finally:
            window.close()
            window.deleteLater()

    def test_show_toast_signals_visible(self, qapp):
        """L'overlay devient visible quand un toast est ajouté."""
        parent = QWidget()
        window = QMainWindow()
        window.setCentralWidget(parent)
        window.show()
        toast = ToastNotification(parent)
        try:
            assert not toast.isVisible()
            toast.show_toast("ERROR", "Test")
            assert toast.isVisible()
        finally:
            window.close()
            window.deleteLater()
