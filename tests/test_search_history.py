"""Tests unitaires pour ``SearchHistory`` (src/services/search_history.py)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pytest import MonkeyPatch

from src.services.search_history import MAX_HISTORY, SearchHistory


@pytest.fixture
def history(tmp_data_dir: Path, monkeypatch: MonkeyPatch) -> SearchHistory:
    """Crée une instance SearchHistory pointant vers un fichier temporaire."""
    monkeypatch.setattr(
        "src.services.search_history.HISTORY_FILE",
        tmp_data_dir / "bot_recherche_history.json",
    )
    return SearchHistory()


# ═════════════════════════════════════════════════════════════════
#  Tests d'initialisation
# ═════════════════════════════════════════════════════════════════


class TestInit:
    def test_empty_on_fresh_start(self, history: SearchHistory) -> None:
        """Un nouvel historique sans fichier doit être vide."""
        assert history.get_all() == []
        assert history.get_recent() == []

    def test_loads_existing_file(self, tmp_data_dir: Path, monkeypatch: MonkeyPatch) -> None:
        """Charge les données d'un fichier existant."""
        data_path = tmp_data_dir / "bot_recherche_history.json"
        data_path.write_text(
            json.dumps(
                {
                    "searches": [
                        {
                            "query": "test",
                            "type": "global",
                            "username": None,
                            "count": 5,
                            "timestamp": "2024-01-01T00:00:00+00:00",
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr("src.services.search_history.HISTORY_FILE", data_path)
        h = SearchHistory()
        assert len(h.get_all()) == 1
        assert h.get_all()[0]["query"] == "test"


# ═════════════════════════════════════════════════════════════════
#  Tests d'ajout
# ═════════════════════════════════════════════════════════════════


class TestAdd:
    def test_add_first_entry(self, history: SearchHistory) -> None:
        """Ajoute une première entrée."""
        history.add("Pink Floyd", "global", None)
        all_ = history.get_all()
        assert len(all_) == 1
        assert all_[0]["query"] == "Pink Floyd"
        assert all_[0]["type"] == "global"
        assert all_[0]["username"] is None
        assert all_[0]["count"] == 0
        assert "timestamp" in all_[0]

    def test_add_with_username(self, history: SearchHistory) -> None:
        """Ajoute une entrée avec un nom d'utilisateur (mode utilisateur/salon)."""
        history.add("user123 files", "user", "user123")
        entry = history.get_all()[0]
        assert entry["username"] == "user123"
        assert entry["type"] == "user"

    def test_add_with_count(self, history: SearchHistory) -> None:
        """Ajoute une entrée avec un compteur de résultats."""
        history.add("test query", "global", None, count=42)
        assert history.get_all()[0]["count"] == 42

    def test_add_multiple_entries(self, history: SearchHistory) -> None:
        """Ajoute plusieurs entrées — l'ordre doit être LIFO."""
        history.add("first", "global")
        history.add("second", "global")
        history.add("third", "global")
        all_ = history.get_all()
        assert len(all_) == 3
        assert all_[0]["query"] == "third"
        assert all_[1]["query"] == "second"
        assert all_[2]["query"] == "first"

    def test_add_dedup_same_query_type(self, history: SearchHistory) -> None:
        """Ajouter la même (query + type) déplace vers le haut et met à jour le timestamp."""
        history.add("query_a", "global", "user1", count=1)
        history.add("query_b", "global", "user2", count=2)
        history.add("query_a", "global", "user1", count=99)

        all_ = history.get_all()
        assert len(all_) == 2  # pas de doublon
        assert all_[0]["query"] == "query_a"  # remonté en haut
        assert all_[0]["count"] == 99  # count mis à jour

    def test_add_dedup_keeps_username_distinction(self, history: SearchHistory) -> None:
        """Même query mais username différent = entrées distinctes."""
        history.add("query", "user", "alice")
        history.add("query", "user", "bob")
        assert len(history.get_all()) == 2

    def test_add_dedup_keeps_type_distinction(self, history: SearchHistory) -> None:
        """Même query mais type différent = entrées distinctes."""
        history.add("test", "global", None)
        history.add("test", "user", "someone")
        assert len(history.get_all()) == 2

    def test_add_max_history_enforced(self, history: SearchHistory) -> None:
        """Ne doit pas dépasser MAX_HISTORY entrées."""
        for i in range(MAX_HISTORY + 10):
            history.add(f"query_{i}", "global", None)
        assert len(history.get_all()) == MAX_HISTORY


# ═════════════════════════════════════════════════════════════════
#  Tests de suppression
# ═════════════════════════════════════════════════════════════════


class TestRemove:
    def test_remove_existing(self, history: SearchHistory) -> None:
        """Supprime une entrée existante."""
        history.add("query_a", "global")
        history.add("query_b", "global")
        history.add("query_c", "global")

        result = history.remove("query_b", "global")
        assert result is True
        assert len(history.get_all()) == 2
        assert [e["query"] for e in history.get_all()] == ["query_c", "query_a"]

    def test_remove_nonexistent(self, history: SearchHistory) -> None:
        """Supprimer une entrée inexistante retourne False."""
        history.add("query_a", "global")
        result = history.remove("nonexistent", "global")
        assert result is False
        assert len(history.get_all()) == 1

    def test_remove_with_username(self, history: SearchHistory) -> None:
        """Supprime avec type + username précis."""
        history.add("q", "user", "alice")
        history.add("q", "user", "bob")
        history.remove("q", "user", "alice")
        assert len(history.get_all()) == 1
        assert history.get_all()[0]["username"] == "bob"


# ═════════════════════════════════════════════════════════════════
#  Tests de mise à jour du compteur
# ═════════════════════════════════════════════════════════════════


class TestUpdateCount:
    def test_update_existing(self, history: SearchHistory) -> None:
        """Met à jour le compteur d'une entrée existante."""
        history.add("test", "global", count=5)
        history.update_count("test", "global", count=10)

        entry = history.get_all()[0]
        assert entry["count"] == 10

    def test_update_nonexistent_does_nothing(self, history: SearchHistory) -> None:
        """Mettre à jour une entrée inexistante ne fait rien."""
        history.add("test", "global")
        history.update_count("nope", "global", count=42)
        assert len(history.get_all()) == 1
        assert history.get_all()[0]["count"] == 0


# ═════════════════════════════════════════════════════════════════
#  Tests de vidage (clear)
# ═════════════════════════════════════════════════════════════════


class TestClear:
    def test_clear_empties_all(self, history: SearchHistory) -> None:
        """Vider l'historique supprime toutes les entrées."""
        history.add("a", "global")
        history.add("b", "global")
        history.clear()
        assert history.get_all() == []
        assert history.get_recent() == []

    def test_clear_then_add(self, history: SearchHistory) -> None:
        """Après un clear, on peut ajouter de nouvelles entrées."""
        history.add("old", "global")
        history.clear()
        history.add("new", "global")
        assert len(history.get_all()) == 1
        assert history.get_all()[0]["query"] == "new"


# ═════════════════════════════════════════════════════════════════
#  Tests de persistance (lecture/écriture fichier)
# ═════════════════════════════════════════════════════════════════


class TestPersistence:
    def test_save_and_reload(self, tmp_data_dir: Path, monkeypatch: MonkeyPatch) -> None:
        """Les données survivent à un rechargement (nouvelle instance)."""
        data_path = tmp_data_dir / "bot_recherche_history.json"
        monkeypatch.setattr("src.services.search_history.HISTORY_FILE", data_path)

        h1 = SearchHistory()
        h1.add("persist_test", "global", None, count=7)

        h2 = SearchHistory()
        assert len(h2.get_all()) == 1
        assert h2.get_all()[0]["query"] == "persist_test"
        assert h2.get_all()[0]["count"] == 7

    def test_corrupted_file_returns_empty(self, tmp_data_dir: Path, monkeypatch: MonkeyPatch) -> None:
        """Un fichier corrompu ne doit pas planter et retourne une liste vide."""
        data_path = tmp_data_dir / "bot_recherche_history.json"
        data_path.write_text("This is not JSON!!!", encoding="utf-8")
        monkeypatch.setattr("src.services.search_history.HISTORY_FILE", data_path)

        h = SearchHistory()
        assert h.get_all() == []

    def test_truncated_json_returns_empty(self, tmp_data_dir: Path, monkeypatch: MonkeyPatch) -> None:
        """Un JSON tronqué ne doit pas planter."""
        data_path = tmp_data_dir / "bot_recherche_history.json"
        data_path.write_text('{"searches": [{"query": "test"', encoding="utf-8")
        monkeypatch.setattr("src.services.search_history.HISTORY_FILE", data_path)

        h = SearchHistory()
        assert h.get_all() == []


# ═════════════════════════════════════════════════════════════════
#  Tests de get_recent
# ═════════════════════════════════════════════════════════════════


class TestGetRecent:
    def test_get_recent_default_count(self, history: SearchHistory) -> None:
        """get_recent() retourne 5 entrées par défaut."""
        for i in range(10):
            history.add(f"q_{i}", "global")
        assert len(history.get_recent()) == 5

    def test_get_recent_custom_count(self, history: SearchHistory) -> None:
        """get_recent(n) retourne n entrées."""
        for i in range(10):
            history.add(f"q_{i}", "global")
        assert len(history.get_recent(3)) == 3
        assert history.get_recent(3)[0]["query"] == "q_9"

    def test_get_recent_less_than_count(self, history: SearchHistory) -> None:
        """Moins d'entrées que demandé = toutes les entrées."""
        history.add("only_one", "global")
        assert len(history.get_recent(10)) == 1
