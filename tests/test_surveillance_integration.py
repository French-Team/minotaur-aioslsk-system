"""
Tests d'intégration : routage bout-en-bout entre EventBus et l'affichage GUI.

Vérifie que les événements émis via EventBus sont correctement reçus
et affichés par le widget BotSurveillance.
"""

import pytest
from PySide6.QtWidgets import QApplication

from src.gui.widgets.bots.bot_surveillance import BotSurveillance
from src.services.event_bus import EventBus

# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def qapp():
    """QApplication scope module."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture(autouse=True)
def reset_eventbus(monkeypatch, tmp_path):
    """
    Isole la base SQLite pour chaque test :
      1. Réinitialise le singleton EventBus
      2. Redirige _DB_PATH vers un fichier temporaire unique
         (attention : _DB_PATH est évalué à l'import du module,
          donc on patch _DB_PATH directement, pas _DATA_DIR)
    """
    EventBus._instance = None
    db_path = tmp_path / "bot_surveillance.db"
    monkeypatch.setattr("src.services.event_bus._DB_PATH", db_path)
    yield
    bus = EventBus._instance
    if bus is not None:
        bus.shutdown()
        EventBus._instance = None


@pytest.fixture
def bus():
    """EventBus prêt à l'emploi (base temporaire isolée)."""
    bus = EventBus()
    # Nettoyage défensif : garantir une base vide
    bus._db.execute("DELETE FROM events")
    bus._db.commit()
    bus._cache_recent = []
    bus._cache_stats = {}
    return bus


@pytest.fixture
def surveillance(bus, qapp):
    """Widget BotSurveillance connecté à l'EventBus."""
    widget = BotSurveillance()
    return widget


# ── Tests ────────────────────────────────────────────────────────────────


class TestSignalRouting:
    """Vérifie que les événements émis via EventBus arrivent bien dans le widget."""

    def test_event_appears_in_feed(self, surveillance, bus):
        """Un événement émis doit créer une carte dans le flux."""
        assert len(surveillance._feed_cards) == 0

        bus.emit_event(
            severity="INFO",
            category="reseau",
            title="Test de routage",
            message="Message de test",
            source="TestSource",
        )

        assert len(surveillance._feed_cards) == 1
        card = surveillance._feed_cards[0]
        assert card._event.title == "Test de routage"
        assert card._event.severity == "INFO"
        assert card._event.category == "reseau"
        assert card._event.source == "TestSource"

    def test_multiple_events_in_order(self, surveillance, bus):
        """Les événements sont ajoutés dans l'ordre d'émission."""
        for i in range(5):
            bus.emit_event(severity="INFO", category="bot", title=f"Événement {i}", source=f"Source{i}")

        assert len(surveillance._feed_cards) == 5
        for i, card in enumerate(surveillance._feed_cards):
            assert card._event.title == f"Événement {i}"

    def test_signal_disconnect_on_shutdown(self, qapp):
        """Après shutdown de l'EventBus, le widget ne reçoit plus d'événements."""
        bus1 = EventBus()
        widget = BotSurveillance()

        bus1.emit_event(severity="INFO", category="bot", title="Avant fermeture")
        assert len(widget._feed_cards) == 1

        bus1.shutdown()
        EventBus._instance = None

        # Nouvel EventBus — l'ancien widget n'est plus connecté
        bus2 = EventBus()
        bus2.emit_event(severity="INFO", category="bot", title="Après fermeture")
        assert len(widget._feed_cards) == 1  # toujours 1, pas 2

        widget.deleteLater()
        bus2.shutdown()
        EventBus._instance = None


class TestStatsIntegration:
    """Vérifie que les compteurs de statistiques sont mis à jour."""

    def test_error_increments_error_counter(self, surveillance, bus):
        """Un événement ERROR incrémente _stats_errors."""
        bus.emit_event(severity="ERROR", category="reseau", title="Erreur réseau")
        assert surveillance._stats_errors == 1
        assert surveillance._stats_total == 1
        assert surveillance._stats_warns == 0

    def test_warn_increments_warn_counter(self, surveillance, bus):
        """Un événement WARN incrémente _stats_warns."""
        bus.emit_event(severity="WARN", category="transfert", title="Avertissement")
        assert surveillance._stats_warns == 1
        assert surveillance._stats_total == 1

    def test_mixed_severities(self, surveillance, bus):
        """Plusieurs événements de sévérités différentes mettent à jour tous les compteurs."""
        bus.emit_event(severity="ERROR", category="reseau", title="Erreur 1")
        bus.emit_event(severity="WARN", category="transfert", title="Warning 1")
        bus.emit_event(severity="ERROR", category="bot", title="Erreur 2")
        bus.emit_event(severity="INFO", category="recherche", title="Info 1")
        bus.emit_event(severity="INFO", category="bibliotheque", title="Info 2")
        bus.emit_event(severity="WARN", category="configuration", title="Warning 2")

        assert surveillance._stats_errors == 2
        assert surveillance._stats_warns == 2
        assert surveillance._stats_total == 6


class TestPauseResume:
    """Vérifie le comportement pause/reprise du flux."""

    def test_pause_blocks_events(self, surveillance, bus):
        """Quand le widget est en pause, les événements ne sont pas ajoutés."""
        surveillance._paused = True
        bus.emit_event(severity="INFO", category="bot", title="Pendant pause")

        assert len(surveillance._feed_cards) == 0
        assert surveillance._stats_total == 0

    def test_resume_allows_events(self, surveillance, bus):
        """Après reprise, les événements sont à nouveau reçus."""
        surveillance._paused = True
        bus.emit_event(severity="INFO", category="bot", title="Ignoré")
        assert len(surveillance._feed_cards) == 0

        surveillance._paused = False
        bus.emit_event(severity="INFO", category="bot", title="Reçu")

        assert len(surveillance._feed_cards) == 1
        assert surveillance._feed_cards[0]._event.title == "Reçu"


class TestCategoryFiltering:
    """Vérifie que les filtres affectent la visibilité des cartes."""

    def test_text_filter_masks_non_matching(self, surveillance, bus):
        """Le filtre texte retourne False pour les cartes qui ne correspondent pas."""
        bus.emit_event(
            severity="INFO",
            category="reseau",
            title="Connexion établie",
            message="Serveur OK",
            source="Network",
        )
        bus.emit_event(
            severity="ERROR",
            category="transfert",
            title="Échec téléchargement",
            message="Fichier introuvable",
            source="Transfer",
        )

        assert len(surveillance._feed_cards) == 2

        toutes_categories = {cat for cat, _ in surveillance.CATEGORIES}
        assert not surveillance._feed_cards[0].matches_filter("téléchargement", toutes_categories)
        assert surveillance._feed_cards[1].matches_filter("téléchargement", toutes_categories)

    def test_category_filter_masks_non_matching(self, surveillance, bus):
        """Le filtre catégorie retourne False pour les cartes des autres catégories."""
        bus.emit_event(severity="INFO", category="reseau", title="Réseau")
        bus.emit_event(severity="INFO", category="transfert", title="Transfert")
        bus.emit_event(severity="INFO", category="recherche", title="Recherche")

        assert len(surveillance._feed_cards) == 3

        categories_partiel = {"reseau", "recherche"}
        assert surveillance._feed_cards[0].matches_filter("", categories_partiel)  # reseau
        assert not surveillance._feed_cards[1].matches_filter("", categories_partiel)  # transfert
        assert surveillance._feed_cards[2].matches_filter("", categories_partiel)  # recherche

    def test_default_all_categories_visible(self, surveillance, bus):
        """Par défaut, toutes les catégories sont visibles (filtre vide)."""
        bus.emit_event(severity="INFO", category="reseau", title="Réseau")
        bus.emit_event(severity="INFO", category="bibliotheque", title="Bibliothèque")

        toutes = {cat for cat, _ in surveillance.CATEGORIES}
        assert surveillance._feed_cards[0].matches_filter("", toutes)
        assert surveillance._feed_cards[1].matches_filter("", toutes)


class TestDbPersistence:
    """Vérifie la persistance des événements en base SQLite."""

    def test_events_persisted_in_db(self, bus):
        """Les événements émis sont stockés et récupérables."""
        bus.emit_event(
            severity="ERROR",
            category="reseau",
            title="Ping échoué",
            message="192.168.1.1 ne répond pas",
            source="ConnexionManager",
        )
        bus.emit_event(
            severity="INFO", category="bot", title="Recherche terminée", message="15 résultats", source="BotRecherche"
        )

        events = bus.query()
        assert len(events) == 2
        titles = [e.title for e in events]
        assert "Ping échoué" in titles
        assert "Recherche terminée" in titles

    def test_recent_events_count(self, bus):
        """get_recent() retourne le nombre demandé d'événements."""
        for i in range(10):
            bus.emit_event(severity="INFO", category="bot", title=f"Event {i}")

        recent = bus.get_recent(3)
        assert len(recent) == 3

        recent_5 = bus.get_recent(5)
        assert len(recent_5) == 5

    def test_no_event_loss_after_restart(self, bus):
        """Après shutdown/recreate, les événements sont toujours en base."""
        # Nettoyage explicite via SQL direct (garantit l'isolation)
        bus._db.execute("DELETE FROM events")
        bus._db.commit()
        bus._cache_recent = []
        bus._cache_stats = {}

        bus.emit_event(severity="WARN", category="configuration", title="Config modifiée", source="BotOptimiseur")

        bus.shutdown()
        EventBus._instance = None
        bus2 = EventBus()

        events = bus2.query()
        assert len(events) == 1
        assert events[0].title == "Config modifiée"

        bus2.shutdown()
        EventBus._instance = None

    def test_purge_removes_old_events(self, bus):
        """purge_old() supprime les événements plus vieux que 7 jours."""
        evt = bus.emit_event(severity="INFO", category="bot", title="Ancien")

        # Forcer un timestamp vieux de 10 jours
        import datetime

        old_ts = (datetime.datetime.now() - datetime.timedelta(days=10)).isoformat(timespec="seconds")
        bus._db.execute("UPDATE events SET timestamp = ? WHERE id = ?", (old_ts, evt.id))
        bus._db.commit()

        bus.purge_old()
        assert bus.get_event(evt.id) is None

    def test_purge_keeps_recent_events(self, bus):
        """purge_old() garde les événements de moins de 7 jours."""
        evt = bus.emit_event(severity="INFO", category="bot", title="Récent")
        bus.purge_old()
        assert bus.get_event(evt.id) is not None
