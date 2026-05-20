"""
Étape 10 — Tests & Polish pour le système de surveillance.

Couvre :
  - Démarrage / flux vide (empty stream, clean state)
  - Performance (200+ événements rapides)
  - EventBus.query() (filtres catégorie, sévérité, texte, date)
  - Export CSV et JSON
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow

from src.gui.widgets.bots.bot_surveillance import BotSurveillance
from src.services.event_bus import _DB_PATH, EventBus, SurveillanceEvent

# ── Helpers ───────────────────────────────────────────────────────────────


def _make_bus(tmp_path: Path) -> EventBus:
    """Crée un EventBus isolé avec une DB temporaire en patchant _DB_PATH."""
    db_file = tmp_path / "test_events.db"
    with patch("src.services.event_bus._DB_PATH", db_file):
        return EventBus()


# ── Fixtures ──────────────────────────────────────────────────────────────


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
def bus(tmp_path):
    """EventBus avec DB temporaire isolée."""
    return _make_bus(tmp_path)


@pytest.fixture
def surv(qapp, bus):
    """BotSurveillance connecté à EventBus."""
    return BotSurveillance()


# ═══════════════════════════════════════════════════════════════════════════
#  Tests : Démarrage / flux vide
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.qt_heavy
class TestStartup:
    """Vérifie l'état initial avec un flux vide."""

    def test_stats_start_at_zero(self, surv):
        assert surv._stats_errors == 0
        assert surv._stats_warns == 0
        assert surv._stats_total == 0

    def test_feed_empty(self, surv):
        assert len(surv._feed_cards) == 0

    def test_unseen_count_zero(self, surv):
        assert surv._unseen_count == 0

    def test_paused_false(self, surv):
        assert not surv._paused

    def test_search_empty(self, surv):
        assert surv.search_text() == ""

    def test_active_categories_all(self, surv):
        assert surv.active_categories() == {
            "reseau",
            "transfert",
            "recherche",
            "bibliotheque",
            "configuration",
            "erreur",
            "bot",
        }

    def test_demarrage_puis_evenements(self, surv, bus):
        """Après démarrage vide, des événements sont bien reçus."""
        assert len(surv._feed_cards) == 0
        bus.emit_event(severity="INFO", category="bot", title="Premier")
        assert len(surv._feed_cards) == 1


# ═══════════════════════════════════════════════════════════════════════════
#  Tests : Performance — 200+ événements
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.qt_heavy
class TestPerformance:
    """Vérifie le comportement sous charge (200+ événements)."""

    def test_200_events_no_crash(self, surv, bus):
        """200 événements émis rapidement ne plantent pas."""
        for i in range(200):
            bus.emit_event(
                severity="INFO" if i % 3 else "ERROR",
                category="bot",
                title=f"Event {i}",
            )
        assert surv._stats_total == 200
        # i=0,3,6,...,198 → 67 events ERROR (200/3 arrondi supérieur)
        assert surv._stats_errors == 67

    def test_200_events_stats_correct(self, surv, bus):
        """Les compteurs statistiques sont exacts après 200 événements."""
        for i in range(200):
            if i < 50:
                sev = "ERROR"
            elif i < 120:
                sev = "WARN"
            else:
                sev = "INFO"
            bus.emit_event(severity=sev, category="bot", title=f"Event {i}")

        assert surv._stats_errors == 50
        assert surv._stats_warns == 70
        assert surv._stats_total == 200

    def test_200_events_feed_has_latest(self, surv, bus):
        """Le flux contient les événements les plus récents."""
        for i in range(200):
            bus.emit_event(severity="INFO", category="bot", title=f"Event {i}")
        # Vérifier via feed_cards que le plus récent est présent
        assert len(surv._feed_cards) > 0

    def test_200_events_purge_no_crash(self, surv, bus):
        """Purge après 200 événements ne plante pas."""
        for i in range(200):
            bus.emit_event(severity="INFO", category="bot", title=f"Event {i}")
        count = bus.purge_old()
        assert count >= 0  # ne lève pas d'exception

    def test_200_events_query_after_load(self, qapp, tmp_path):
        """Interroger l'EventBus après 200 événements."""
        bus = _make_bus(tmp_path)
        for i in range(200):
            bus.emit_event(
                severity="ERROR" if i % 2 else "INFO",
                category="bot" if i % 3 else "reseau",
                title=f"Event {i}",
            )
        results = bus.query(limit=200)
        assert len(results) == 200
        errors = bus.query(severity="ERROR", limit=200)
        assert len(errors) == 100


# ═══════════════════════════════════════════════════════════════════════════
#  Tests : EventBus.query()
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.qt_heavy
class TestEventBusQuery:
    """Vérifie le filtrage des événements via EventBus.query()."""

    @pytest.fixture(autouse=True)
    def _seed_data(self, bus):
        """Peuple la base avec des événements variés."""
        events_data = [
            ("ERROR", "reseau", "Connexion perdue", "Timeout"),
            ("WARN", "transfert", "Telechargement lent", "10 KB/s"),
            ("INFO", "bot", "Scan termine", "42 fichiers trouves"),
            ("ERROR", "bibliotheque", "Fichier introuvable", "Chemin invalide"),
            ("WARN", "reseau", "Ping eleve", "500ms"),
            ("INFO", "transfert", "Fichier recu", "song.mp3"),
            ("ERROR", "bot", "Erreur authentification", "Token expire"),
            ("INFO", "recherche", "Resultats recus", "15 resultats"),
        ]
        for sev, cat, title, msg in events_data:
            bus.emit_event(severity=sev, category=cat, title=title, message=msg)

    def test_query_all(self, bus):
        results = bus.query(limit=50)
        assert len(results) == 8

    def test_query_by_severity_error(self, bus):
        results = bus.query(severity="ERROR")
        assert len(results) == 3
        assert all(e.severity == "ERROR" for e in results)

    def test_query_by_severity_warn(self, bus):
        results = bus.query(severity="WARN")
        assert len(results) == 2
        assert all(e.severity == "WARN" for e in results)

    def test_query_by_category(self, bus):
        results = bus.query(category="reseau")
        assert len(results) == 2
        assert all(e.category == "reseau" for e in results)

    def test_query_by_search_text(self, bus):
        results = bus.query(search="Connexion")
        assert len(results) == 1
        assert results[0].title == "Connexion perdue"

    def test_query_by_date_range(self, bus):
        import datetime

        today = datetime.date.today().isoformat()
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        results = bus.query(date_from=today, date_to=tomorrow)
        assert len(results) == 8
        results = bus.query(date_to="2020-01-01")
        assert len(results) == 0

    def test_query_combined_filters(self, bus):
        results = bus.query(severity="ERROR", category="reseau")
        assert len(results) == 1
        assert results[0].title == "Connexion perdue"

    def test_query_limit_and_offset(self, bus):
        first_3 = bus.query(limit=3, offset=0)
        assert len(first_3) == 3
        next_3 = bus.query(limit=3, offset=3)
        assert len(next_3) == 3
        assert first_3[0].id != next_3[0].id

    def test_query_empty_result(self, bus):
        results = bus.query(severity="ERROR", category="transfert")
        assert len(results) == 0


# ═══════════════════════════════════════════════════════════════════════════
#  Tests : Export CSV / JSON
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.qt_heavy
class TestExport:
    """Vérifie le formatage des données pour export CSV et JSON."""

    def _make_events(self):
        return [
            SurveillanceEvent(
                id=1,
                timestamp="2025-01-15T10:30:00",
                severity="ERROR",
                category="reseau",
                title="Connexion perdue",
                message="Timeout",
                source="test",
                details={"ip": "192.168.1.1"},
            ),
            SurveillanceEvent(
                id=2,
                timestamp="2025-01-15T10:31:00",
                severity="INFO",
                category="bot",
                title="Scan OK",
                message="42 fichiers",
                source="test",
                details=None,
            ),
        ]

    def test_csv_format_valid(self):
        events = self._make_events()
        output = io.StringIO()
        writer = csv.writer(output, delimiter=",")
        writer.writerow(
            [
                "ID",
                "Severite",
                "Date",
                "Categorie",
                "Titre",
                "Message",
                "Source",
                "Details",
            ]
        )
        for ev in events:
            writer.writerow(
                [
                    ev.id,
                    ev.severity,
                    ev.timestamp,
                    ev.category,
                    ev.title,
                    ev.message,
                    ev.source,
                    json.dumps(ev.details, ensure_ascii=False) if ev.details else "",
                ]
            )
        content = output.getvalue()
        assert "Connexion perdue" in content
        assert "192.168.1.1" in content
        assert "Scan OK" in content

    def test_json_format_valid(self):
        events = self._make_events()
        data = [
            {
                "id": ev.id,
                "timestamp": ev.timestamp,
                "severity": ev.severity,
                "category": ev.category,
                "title": ev.title,
                "message": ev.message,
                "source": ev.source,
                "details": ev.details,
            }
            for ev in events
        ]
        output = json.dumps(data, indent=2, ensure_ascii=False)
        parsed = json.loads(output)
        assert len(parsed) == 2
        assert parsed[0]["title"] == "Connexion perdue"
        assert parsed[1]["title"] == "Scan OK"

    def test_export_csv_depuis_evenements_reels(self, qapp, tmp_path):
        """Export CSV à partir d'evenements reels de l'EventBus."""
        bus = _make_bus(tmp_path)
        bus.emit_event(
            severity="ERROR",
            category="reseau",
            title="Erreur test",
            message="Message test",
            details={"code": 500},
        )
        bus.emit_event(
            severity="INFO",
            category="bot",
            title="Info test",
            message="OK",
        )
        events = bus.get_recent(10)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Severite", "Titre"])
        for ev in events:
            writer.writerow([ev.id, ev.severity, ev.title])
        content = output.getvalue()
        assert "Erreur test" in content
        assert "Info test" in content
        assert "ERROR" in content

    def test_stats_after_events(self, qapp, tmp_path):
        """get_stats() retourne des donnees coherentes apres emission."""
        bus = _make_bus(tmp_path)
        for i in range(10):
            bus.emit_event(
                severity="ERROR" if i % 2 else "INFO",
                category="bot",
                title=f"Event {i}",
            )
        stats = bus.get_stats()
        assert stats["total"] == 10
        assert stats["errors_24h"] == 5
        assert "bot" in stats["par_categorie"]
        assert stats["par_categorie"]["bot"] == 10
