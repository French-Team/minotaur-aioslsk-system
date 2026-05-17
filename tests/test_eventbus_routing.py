"""Tests complets pour vérifier le routage des événements via l'EventBus.

Couvre :
- SurveillanceEvent (validation, catégories, sévérités)
- EventBus (singleton, émission, signal, requêtes, pause, purge)
- Vérification que toutes les catégories utilisées par les bots sont valides
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject, Signal

from src.services.event_bus import _DB_PATH, EventBus, SurveillanceEvent

# ═══════════════════════════════════════════════════════════════════
# SurveillanceEvent — validation
# ═══════════════════════════════════════════════════════════════════


class TestSurveillanceEvent:
    """Validation du modèle SurveillanceEvent."""

    def test_default_values(self):
        """Un événement créé par défaut a des valeurs par défaut."""
        evt = SurveillanceEvent()
        assert evt.severity == "INFO"
        assert evt.category == "bot"
        assert evt.timestamp != ""  # auto-généré
        assert evt.id == 0

    def test_valid_severities(self):
        """Toutes les sévérités valides sont acceptées."""
        for sev in SurveillanceEvent.SEVERITIES:
            evt = SurveillanceEvent(severity=sev, category="bot")
            assert evt.severity == sev

    def test_invalid_severity_raises(self):
        """Une sévérité invalide lève une ValueError."""
        with pytest.raises(ValueError, match="Sévérité"):
            SurveillanceEvent(severity="INVALID", category="bot")

    def test_all_valid_categories(self):
        """Toutes les catégories déclarées sont acceptées."""
        for cat in SurveillanceEvent.CATEGORIES:
            evt = SurveillanceEvent(category=cat)
            assert evt.category == cat

    def test_invalid_category_raises(self):
        """Une catégorie invalide lève une ValueError."""
        with pytest.raises(ValueError, match="Catégorie"):
            SurveillanceEvent(category="categorie_inconnue")

    def test_custom_timestamp_preserved(self):
        """Un timestamp fourni manuellement n'est pas écrasé."""
        evt = SurveillanceEvent(timestamp="2025-01-01T00:00:00", category="bot")
        assert evt.timestamp == "2025-01-01T00:00:00"

    def test_details_dict(self):
        """Les détails optionnels sont stockés tels quels."""
        details = {"key": "value", "count": 42}
        evt = SurveillanceEvent(category="bot", details=details)
        assert evt.details == details


# ═══════════════════════════════════════════════════════════════════
# EventBus — unitaire (sans QApplication si possible)
# ═══════════════════════════════════════════════════════════════════


class TestEventBusSingleton:
    """L'EventBus est un singleton."""

    def test_singleton(self):
        """EventBus() retourne toujours la même instance."""
        bus1 = EventBus()
        bus2 = EventBus()
        assert bus1 is bus2

    def test_singleton_reinit(self, monkeypatch):
        """Réinitialiser _instance permet de créer un nouveau bus."""
        # Nettoyer l'instance précédente
        old = EventBus._instance
        if old is not None:
            old.shutdown()
        EventBus._instance = None

        bus = EventBus()
        assert bus is not None
        assert EventBus._instance is bus


# ═══════════════════════════════════════════════════════════════════
# EventBus — émission et réception
# ═══════════════════════════════════════════════════════════════════


class TestEventBusEmission:
    """L'émission d'événements via emit_event()."""

    @pytest.fixture
    def bus(self, monkeypatch):
        """Fixture: EventBus vierge."""
        # Désactiver la persistance SQLite pour les tests
        monkeypatch.setattr("src.services.event_bus._DB_PATH", ":memory:")
        old = EventBus._instance
        if old is not None:
            old.shutdown()
        EventBus._instance = None
        bus = EventBus()
        yield bus
        bus.shutdown()
        EventBus._instance = old

    def test_emit_returns_event(self, bus):
        """emit_event retourne un SurveillanceEvent avec un id."""
        evt = bus.emit_event(category="bot", severity="INFO", title="Test")
        assert evt is not None
        assert isinstance(evt, SurveillanceEvent)
        assert evt.id > 0  # persisté en DB
        assert evt.title == "Test"
        assert evt.category == "bot"

    def test_emit_triggers_signal(self, bus):
        """Le signal event_emitted est émis."""
        received = []

        def handler(evt):
            received.append(evt)

        bus.event_emitted.connect(handler)
        bus.emit_event(category="bot", title="Signal test")
        assert len(received) == 1
        assert received[0].title == "Signal test"

    def test_emit_all_categories(self, bus):
        """Toutes les catégories valides peuvent être émises."""
        for cat in SurveillanceEvent.CATEGORIES:
            evt = bus.emit_event(category=cat, title=f"Test {cat}")
            assert evt is not None
            assert evt.category == cat

    def test_emit_all_severities(self, bus):
        """Toutes les sévérités valides peuvent être émises."""
        for sev in SurveillanceEvent.SEVERITIES:
            evt = bus.emit_event(category="bot", severity=sev, title=f"Test {sev}")
            assert evt is not None
            assert evt.severity == sev

    def test_emit_with_source_and_details(self, bus):
        """Les champs source et details sont conservés."""
        evt = bus.emit_event(
            category="bot",
            title="Avec détails",
            message="Message important",
            source="MonBot",
            details={"nb": 3},
        )
        assert evt.source == "MonBot"
        assert evt.details == {"nb": 3}
        assert evt.message == "Message important"

    def test_emit_when_paused_returns_none(self, bus):
        """emit_event retourne None quand le bus est en pause."""
        bus.pause()
        evt = bus.emit_event(category="bot", title="Pendant pause")
        assert evt is None

    def test_emit_when_paused_no_signal(self, bus):
        """Aucun signal émis quand le bus est en pause."""
        received = []

        def handler(evt):
            received.append(evt)

        bus.event_emitted.connect(handler)
        bus.pause()
        bus.emit_event(category="bot", title="Pendant pause")
        assert len(received) == 0

    def test_resume_after_pause(self, bus):
        """Après resume, emit_event fonctionne à nouveau."""
        bus.pause()
        bus.resume()
        evt = bus.emit_event(category="bot", title="Après resume")
        assert evt is not None
        assert evt.title == "Après resume"

    def test_multiple_events_increment_ids(self, bus):
        """Les IDs des événements sont incrémentés."""
        id1 = bus.emit_event(category="bot", title="Un").id
        id2 = bus.emit_event(category="bot", title="Deux").id
        assert id2 > id1


# ═══════════════════════════════════════════════════════════════════
# EventBus — requêtes et historique
# ═══════════════════════════════════════════════════════════════════


class TestEventBusQuery:
    """Requêtes d'événements via query() et get_recent()."""

    @pytest.fixture
    def bus(self, monkeypatch):
        monkeypatch.setattr("src.services.event_bus._DB_PATH", ":memory:")
        old = EventBus._instance
        if old is not None:
            old.shutdown()
        EventBus._instance = None
        bus = EventBus()
        yield bus
        bus.shutdown()
        EventBus._instance = old

    @pytest.fixture
    def bus_with_events(self, bus):
        """EventBus avec plusieurs événements de test."""
        bus.emit_event(category="recherche", severity="INFO", title="Recherche lancée")
        bus.emit_event(category="recherche", severity="ERROR", title="Erreur")
        bus.emit_event(category="bibliotheque", severity="INFO", title="Scan terminé")
        bus.emit_event(category="bot", severity="WARN", title="Attention")
        bus.emit_event(category="wishlist", severity="INFO", title="Souhait ajouté")
        bus.emit_event(category="optimiseur", severity="ERROR", title="Profil échoué")
        return bus

    def test_query_all(self, bus_with_events):
        """query() sans filtre retourne tous les événements."""
        events = bus_with_events.query()
        assert len(events) == 6

    def test_query_by_category(self, bus_with_events):
        """query() filtré par catégorie."""
        events = bus_with_events.query(category="recherche")
        assert len(events) == 2
        assert all(e.category == "recherche" for e in events)

    def test_query_by_severity(self, bus_with_events):
        """query() filtré par sévérité."""
        events = bus_with_events.query(severity="ERROR")
        assert len(events) == 2
        assert all(e.severity == "ERROR" for e in events)

    def test_query_by_source(self, bus_with_events):
        """query() filtré par source."""
        # Tous nos événements ont source="" par défaut
        events = bus_with_events.query(source="")
        assert len(events) == 6

    def test_query_by_title_contains(self, bus_with_events):
        """query() avec filtre title partiel."""
        events = bus_with_events.query(search="Recherche")
        assert len(events) == 1
        assert events[0].title == "Recherche lancée"

    def test_query_limit(self, bus_with_events):
        """query() avec limite."""
        events = bus_with_events.query(limit=3)
        assert len(events) == 3

    def test_query_limit_and_category(self, bus_with_events):
        """query() avec limite et filtre catégorie."""
        events = bus_with_events.query(category="recherche", limit=1)
        assert len(events) == 1

    def test_get_recent(self, bus_with_events):
        """get_recent() retourne les N événements les plus récents."""
        recent = bus_with_events.get_recent(limit=3)
        assert len(recent) == 3

    def test_get_stats(self, bus_with_events):
        """get_stats() retourne les stats par catégorie et sévérité."""
        stats = bus_with_events.get_stats()
        assert isinstance(stats, dict)
        assert len(stats) >= 4  # au moins 4 catégories utilisées

    def test_get_event_by_id(self, bus_with_events):
        """get_event() retourne un événement par son ID."""
        first = bus_with_events.emit_event(category="bot", title="Cible")
        found = bus_with_events.get_event(first.id)
        assert found is not None
        assert found.id == first.id
        assert found.title == "Cible"

    def test_get_event_not_found(self, bus_with_events):
        """get_event() retourne None pour un ID inexistant."""
        assert bus_with_events.get_event(999999) is None

    def test_delete_events(self, bus_with_events):
        """delete_events() supprime des événements par IDs."""
        events = bus_with_events.query()
        ids = [e.id for e in events[:3]]
        bus_with_events.delete_events(ids)
        remaining = bus_with_events.query()
        assert len(remaining) == 3
        remaining_ids = {e.id for e in remaining}
        assert all(i not in remaining_ids for i in ids)


# ═══════════════════════════════════════════════════════════════════
# Vérification inter-bots — toutes les catégories utilisées sont valides
# ═══════════════════════════════════════════════════════════════════


class TestBotCategoriesIntegration:
    """Vérifie que les catégories utilisées par chaque bot sont valides."""

    VALID = set(SurveillanceEvent.CATEGORIES)
    SEVERITIES = set(SurveillanceEvent.SEVERITIES)

    def test_connexion_manager_categories(self):
        """ConnexionManager utilise 'reseau' — valide."""
        assert "reseau" in self.VALID

    def test_soulseek_client_categories(self):
        """SoulseekClient utilise 'transfert' — valide."""
        assert "transfert" in self.VALID

    def test_bot_recherche_categories(self):
        """BotRecherche utilise 'recherche' — valide."""
        assert "recherche" in self.VALID

    def test_bot_wishlist_categories(self):
        """BotWishlist utilise 'wishlist' — valide."""
        assert "wishlist" in self.VALID

    def test_bot_bibliotheque_categories(self):
        """BotBibliotheque utilise 'bibliotheque' — valide."""
        assert "bibliotheque" in self.VALID

    def test_bot_optimiseur_categories(self):
        """BotOptimiseur utilise 'optimiseur' — valide."""
        assert "optimiseur" in self.VALID

    def test_all_severities_used_are_valid(self):
        """Les sévérités INFO, WARN, ERROR sont toutes valides."""
        assert "INFO" in self.SEVERITIES
        assert "WARN" in self.SEVERITIES
        assert "ERROR" in self.SEVERITIES


# ═══════════════════════════════════════════════════════════════════
# Test de la purge automatique
# ═══════════════════════════════════════════════════════════════════


class TestEventBusPurge:
    """Purge automatique des événements."""

    @pytest.fixture
    def bus(self, monkeypatch):
        monkeypatch.setattr("src.services.event_bus._DB_PATH", ":memory:")
        old = EventBus._instance
        if old is not None:
            old.shutdown()
        EventBus._instance = None
        bus = EventBus()
        yield bus
        bus.shutdown()
        EventBus._instance = old

    def test_purge_old_removes_old_events(self, bus, monkeypatch):
        """purge_old() supprime les événements plus vieux que retention_days."""
        # Créer un événement
        evt = bus.emit_event(category="bot", title="Ancien")
        assert evt is not None

        # Forcer un timestamp vieux de 100 jours
        import datetime

        old_ts = (datetime.datetime.now() - datetime.timedelta(days=100)).isoformat()
        bus._db.execute(
            "UPDATE events SET timestamp = ? WHERE id = ?",
            (old_ts, evt.id),
        )
        bus._db.commit()

        # Vider les caches pour forcer une relecture
        bus._cache_recent = []
        bus._cache_stats = {}

        # Purge : supprime les événements de plus de 7 jours
        bus.purge_old()

        # L'événement devrait être supprimé
        assert bus.get_event(evt.id) is None

    def test_purge_keeps_recent_events(self, bus):
        """purge_old() garde les événements récents."""
        evt = bus.emit_event(category="bot", title="Récent")
        bus.purge_old()
        assert bus.get_event(evt.id) is not None


# ═══════════════════════════════════════════════════════════════════
# Test de la persistance SQLite
# ═══════════════════════════════════════════════════════════════════


class TestEventBusPersistence:
    """Les événements survivent à une destruction/création du bus."""

    def test_persistence_on_disk(self, monkeypatch, tmp_path):
        """Les événements persistent entre deux instances du bus."""
        db_path = str(tmp_path / "test_events.db")
        monkeypatch.setattr("src.services.event_bus._DB_PATH", db_path)

        old = EventBus._instance
        if old is not None:
            old.shutdown()
        EventBus._instance = None

        # Instance 1 : créer un événement
        bus1 = EventBus()
        evt = bus1.emit_event(category="bot", title="Persistant")
        assert evt is not None
        bus1.shutdown()
        EventBus._instance = None

        # Instance 2 : l'événement doit être lisible
        bus2 = EventBus()
        found = bus2.get_event(evt.id)
        assert found is not None
        assert found.title == "Persistant"
        bus2.shutdown()
        EventBus._instance = old


# ═══════════════════════════════════════════════════════════════════
# EventBus — shutdown (fermeture SQLite)
# ═══════════════════════════════════════════════════════════════════


class TestEventBusShutdown:
    """Vérifie que shutdown() ferme proprement la connexion SQLite."""

    @pytest.fixture
    def bus(self, monkeypatch):
        monkeypatch.setattr("src.services.event_bus._DB_PATH", ":memory:")
        old = EventBus._instance
        if old is not None:
            old.shutdown()
        EventBus._instance = None
        bus = EventBus()
        yield bus
        EventBus._instance = old

    def test_shutdown_appelle_wal_checkpoint_et_close(self, bus):
        """shutdown() exécute WAL checkpoint puis ferme la connexion."""
        mock_db = MagicMock()
        bus._db = mock_db
        bus._purge_timer = None

        bus.shutdown()

        mock_db.execute.assert_called_once_with("PRAGMA wal_checkpoint(TRUNCATE);")
        mock_db.close.assert_called_once()
        assert bus._db is None

    def test_shutdown_sans_db_ne_leve_pas(self, bus):
        """shutdown() ne lève pas d'erreur si _db est déjà None."""
        bus._db = None
        bus._purge_timer = None
        bus.shutdown()  # ne doit pas lever

    def test_shutdown_stop_purge_timer(self, bus):
        """shutdown() arrête le purge timer s'il existe."""
        mock_timer = MagicMock()
        bus._purge_timer = mock_timer
        mock_db = MagicMock()
        bus._db = mock_db

        bus.shutdown()

        mock_timer.stop.assert_called_once()
        mock_db.execute.assert_called_once_with("PRAGMA wal_checkpoint(TRUNCATE);")
        mock_db.close.assert_called_once()
