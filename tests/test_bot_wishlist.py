"""Tests unitaires pour BotWishlist (src/gui/widgets/bots/bot_wishlist.py).

Ne teste que la logique métier (données, persistance, filtres),
pas les widgets Qt ou le rendu UI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtWidgets import QApplication
from pytest import MonkeyPatch

from src.gui.widgets.bots.bot_wishlist import BotWishlist
from src.services import app_config
from src.services.event_bus import EventBus

# ═════════════════════════════════════════════════════════════════
#  Fixtures
# ═════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def _isolate_eventbus(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Isoler EventBus avec une base SQLite temporaire (évite conflits xdist)."""
    db_file = tmp_path / "test_events.db"
    monkeypatch.setattr("src.services.event_bus._DB_PATH", db_file)
    EventBus._instance = None
    yield
    bus = EventBus._instance
    if bus is not None:
        bus.shutdown()
        EventBus._instance = None


@pytest.fixture
def bot(qapp: QApplication, tmp_app_config: Path) -> BotWishlist:
    """Crée un BotWishlist avec un app_config temporaire."""
    return BotWishlist()


# ═════════════════════════════════════════════════════════════════
#  Tests d'initialisation
# ═════════════════════════════════════════════════════════════════


class TestInit:
    def test_empty_on_fresh_start(self, bot: BotWishlist) -> None:
        """Un BotWishlist sans wishlist dans app_config doit avoir _wishlist vide."""
        assert bot._wishlist == []
        assert bot._local_metadata == {}

    def test_loads_from_app_config_json(self, qapp: QApplication, tmp_app_config: Path) -> None:
        """Charge les souhaits depuis app_config au format JSON."""
        entries: list[dict[str, Any]] = [
            {"query": "Pink Floyd", "enabled": True},
            {"query": "Led Zeppelin", "enabled": False},
        ]
        app_config.set("recherche.souhaits", json.dumps(entries, ensure_ascii=False))

        bot = BotWishlist()
        assert len(bot._wishlist) == 2
        assert bot._wishlist[0]["query"] == "Pink Floyd"
        assert bot._wishlist[0]["enabled"] is True
        assert bot._wishlist[1]["query"] == "Led Zeppelin"
        assert bot._wishlist[1]["enabled"] is False

    def test_loads_from_app_config_csv_fallback(self, qapp: QApplication, tmp_app_config: Path) -> None:
        """Fallback CSV : enabled=True par défaut pour toutes les entrées."""
        app_config.set("recherche.souhaits", "Pink Floyd, Led Zeppelin")

        bot = BotWishlist()
        assert len(bot._wishlist) == 2
        assert bot._wishlist[0]["query"] == "Pink Floyd"
        assert bot._wishlist[0]["enabled"] is True
        assert bot._wishlist[1]["enabled"] is True

    def test_merges_local_metadata(self, qapp: QApplication, tmp_app_config: Path) -> None:
        """_local_metadata est fusionné avec les données chargées."""
        app_config.set("recherche.souhaits", json.dumps([{"query": "Pink Floyd", "enabled": True}]))

        bot = BotWishlist()
        bot._local_metadata = {
            "Pink Floyd": {"results": 42, "last_search": "2024-01-15", "status": "active"},
        }
        bot.refresh()

        entry = bot._wishlist[0]
        assert entry["results"] == 42
        assert entry["last_search"] == "2024-01-15"
        assert entry["status"] == "active"

    def test_cleans_stale_metadata(self, qapp: QApplication, tmp_app_config: Path) -> None:
        """Les métadonnées orphelines (query supprimée) sont nettoyées."""
        app_config.set("recherche.souhaits", json.dumps([{"query": "Pink Floyd", "enabled": True}]))

        bot = BotWishlist()
        bot._local_metadata = {
            "Pink Floyd": {"results": 10},
            "Stale Query": {"results": 5},  # n'existe plus dans app_config
        }
        bot.refresh()

        assert "Stale Query" not in bot._local_metadata
        assert "Pink Floyd" in bot._local_metadata


# ═════════════════════════════════════════════════════════════════
#  Tests d'ajout (add_wish)
# ═════════════════════════════════════════════════════════════════
#
# Note : add_wish(query) n'accepte pas de paramètre enabled.
#        Tous les souhaits sont créés activés par défaut.
#        Utiliser toggle_wish() pour désactiver ensuite.


class TestAddWish:
    def test_add_first_wish(self, bot: BotWishlist) -> None:
        """Ajoute un premier souhait."""
        bot.add_wish("Pink Floyd")
        assert len(bot._wishlist) == 1
        assert bot._wishlist[0]["query"] == "Pink Floyd"
        assert bot._wishlist[0]["enabled"] is True

    def test_add_persists_to_app_config(self, bot: BotWishlist) -> None:
        """L'ajout persiste dans app_config."""
        bot.add_wish("Test Query")
        raw = app_config.get("recherche.souhaits", "")
        parsed = json.loads(raw)
        assert len(parsed) == 1
        assert parsed[0]["query"] == "Test Query"
        assert parsed[0]["enabled"] is True

    def test_add_multiple(self, bot: BotWishlist) -> None:
        """Ajoute plusieurs souhaits."""
        bot.add_wish("A")
        bot.add_wish("B")
        bot.add_wish("C")
        assert len(bot._wishlist) == 3
        assert [e["query"] for e in bot._wishlist] == ["A", "B", "C"]

    def test_add_duplicate_does_nothing(self, bot: BotWishlist) -> None:
        """Ajouter un doublon (même query) ne crée pas de deuxième entrée."""
        bot.add_wish("Unique")
        bot.add_wish("Unique")
        assert len(bot._wishlist) == 1

    def test_add_duplicate_case_insensitive(self, bot: BotWishlist) -> None:
        """Le dédoublonnage est insensible à la casse (Pink Floyd ≈ pink floyd)."""
        bot.add_wish("Pink Floyd")
        bot.add_wish("pink floyd")  # considéré comme doublon
        assert len(bot._wishlist) == 1

    def test_add_empty_query_rejected(self, bot: BotWishlist) -> None:
        """Une query vide ne doit pas être ajoutée."""
        bot.add_wish("")
        assert len(bot._wishlist) == 0

    def test_add_whitespace_only_rejected(self, bot: BotWishlist) -> None:
        """Une query qui n'est que des espaces ne doit pas être ajoutée."""
        bot.add_wish("   ")
        assert len(bot._wishlist) == 0


# ═════════════════════════════════════════════════════════════════
#  Tests de suppression (remove_wish)
# ═════════════════════════════════════════════════════════════════


class TestRemoveWish:
    def test_remove_existing(self, bot: BotWishlist) -> None:
        """Supprime un souhait existant."""
        bot.add_wish("A")
        bot.add_wish("B")
        bot.add_wish("C")

        bot.remove_wish("B")
        assert len(bot._wishlist) == 2
        assert [e["query"] for e in bot._wishlist] == ["A", "C"]

    def test_remove_nonexistent_does_nothing(self, bot: BotWishlist) -> None:
        """Supprimer un souhait inexistant ne fait rien."""
        bot.add_wish("A")
        bot.remove_wish("NONEXISTENT")
        assert len(bot._wishlist) == 1

    def test_remove_persists_to_app_config(self, bot: BotWishlist) -> None:
        """La suppression persiste dans app_config."""
        bot.add_wish("Keep")
        bot.add_wish("RemoveMe")
        bot.remove_wish("RemoveMe")

        raw = app_config.get("recherche.souhaits", "")
        parsed = json.loads(raw)
        assert len(parsed) == 1
        assert parsed[0]["query"] == "Keep"

    def test_remove_updates_metadata(self, bot: BotWishlist) -> None:
        """Les métadonnées de la query supprimée sont nettoyées."""
        bot.add_wish("Temp")
        bot._local_metadata["Temp"] = {"results": 5, "last_search": "yesterday"}
        bot.remove_wish("Temp")
        assert "Temp" not in bot._local_metadata

    def test_remove_only_matching_query(self, bot: BotWishlist) -> None:
        """Supprime exactement la query correspondante, pas de substring."""
        bot.add_wish("Rock")
        bot.add_wish("Hard Rock")
        bot.remove_wish("Rock")
        assert len(bot._wishlist) == 1
        assert bot._wishlist[0]["query"] == "Hard Rock"


# ═════════════════════════════════════════════════════════════════
#  Tests de toggle (toggle_wish)
# ═════════════════════════════════════════════════════════════════


class TestToggleWish:
    def test_toggle_enable_to_disable(self, bot: BotWishlist) -> None:
        """Désactiver un souhait actif."""
        bot.add_wish("Test")  # créé activé par défaut
        bot.toggle_wish("Test", False)
        assert bot._wishlist[0]["enabled"] is False
        assert bot._wishlist[0]["status"] == "inactive"

    def test_toggle_disable_to_enable(self, bot: BotWishlist) -> None:
        """Activer un souhait inactif."""
        bot.add_wish("Test")
        bot.toggle_wish("Test", False)  # d'abord désactiver
        bot.toggle_wish("Test", True)  # puis réactiver
        assert bot._wishlist[0]["enabled"] is True
        assert bot._wishlist[0]["status"] == "active"

    def test_toggle_persists_to_app_config(self, bot: BotWishlist) -> None:
        """Le toggle persiste dans app_config."""
        bot.add_wish("Test")
        bot.toggle_wish("Test", False)

        raw = app_config.get("recherche.souhaits", "")
        parsed = json.loads(raw)
        assert parsed[0]["enabled"] is False

    def test_toggle_nonexistent_does_nothing(self, bot: BotWishlist) -> None:
        """Toggle sur un souhait inexistant ne fait rien."""
        bot.add_wish("Real")
        bot.toggle_wish("Fake", False)
        assert bot._wishlist[0]["enabled"] is True  # unchanged


# ═════════════════════════════════════════════════════════════════
#  Tests de mise à jour de requête (update_wish_query)
# ═════════════════════════════════════════════════════════════════
#
# Note : update_wish_query(old_query, new_query) modifie le nom
#        in-place puis appelle _save_wishlist() + refresh().
#        La clé _local_metadata reste celle de l'ancien nom
#        et sera nettoyée comme métadonnée orpheline par refresh().


class TestUpdateWishQuery:
    def test_rename_existing(self, bot: BotWishlist) -> None:
        """Renommer un souhait existant."""
        bot.add_wish("Old Name")
        bot.update_wish_query("Old Name", "New Name")
        assert len(bot._wishlist) == 1
        assert bot._wishlist[0]["query"] == "New Name"

    def test_rename_preserves_enabled_state(self, bot: BotWishlist) -> None:
        """Le renommage préserve l'état enabled."""
        bot.add_wish("Old")
        bot.toggle_wish("Old", False)
        bot.update_wish_query("Old", "New")
        assert bot._wishlist[0]["enabled"] is False

    def test_rename_persists_to_app_config(self, bot: BotWishlist) -> None:
        """Le renommage persiste dans app_config."""
        bot.add_wish("Old")
        bot.update_wish_query("Old", "New")

        raw = app_config.get("recherche.souhaits", "")
        parsed = json.loads(raw)
        assert len(parsed) == 1
        assert parsed[0]["query"] == "New"
        assert parsed[0]["enabled"] is True

    def test_rename_cleans_stale_metadata(self, bot: BotWishlist) -> None:
        """Après renommage, l'ancienne clé _local_metadata est nettoyée.

        Note : refresh() ne transfère pas les métadonnées vers le nouveau nom —
              la clé _local_metadata reste celle de l'ancien nom et est
              nettoyée comme orpheline.
        """
        bot.add_wish("Old")
        bot._local_metadata["Old"] = {"results": 10, "status": "active"}
        bot.update_wish_query("Old", "New")

        # L'ancienne clé est nettoyée
        assert "Old" not in bot._local_metadata
        # Le nouveau nom n'a pas de métadonnées (elles n'ont pas été transférées)
        assert bot._wishlist[0].get("results", 0) == 0

    def test_rename_to_duplicate_allowed(self, bot: BotWishlist) -> None:
        """update_wish_query ne vérifie pas les doublons de nom cible.

        Renommer 'ToRename' vers 'Existing' crée deux entrées avec
        le même nom (l'implémentation actuelle le permet).
        """
        bot.add_wish("Existing")
        bot.add_wish("ToRename")
        bot.update_wish_query("ToRename", "Existing")

        # Les deux entrées sont maintenant 'Existing' (pas de vérification de doublon)
        assert len(bot._wishlist) == 2
        assert bot._wishlist[0]["query"] == "Existing"
        assert bot._wishlist[1]["query"] == "Existing"

    def test_rename_nonexistent_does_nothing(self, bot: BotWishlist) -> None:
        """Renommer un souhait inexistant ne fait rien."""
        bot.add_wish("Real")
        bot.update_wish_query("Fake", "New")
        assert len(bot._wishlist) == 1
        assert bot._wishlist[0]["query"] == "Real"

    def test_rename_to_empty_does_nothing(self, bot: BotWishlist) -> None:
        """Renommer vers une chaîne vide ne fait rien."""
        bot.add_wish("Real")
        bot.update_wish_query("Real", "")
        assert bot._wishlist[0]["query"] == "Real"


# ═════════════════════════════════════════════════════════════════
#  Tests de filtrage (_get_filtered_wishlist)
# ═════════════════════════════════════════════════════════════════
#
# Note : _get_filtered_wishlist() ne prend pas de paramètres.
#        Elle utilise self._filter et self._search_text qui sont
#        définis par _apply_filter() et _on_search().


class TestGetFilteredWishlist:
    def test_filter_all(self, bot: BotWishlist) -> None:
        """Filtre 'all' retourne tous les souhaits."""
        bot.add_wish("A")
        bot.add_wish("B")
        bot._filter = "all"
        result = bot._get_filtered_wishlist()
        assert len(result) == 2

    def test_filter_active(self, bot: BotWishlist) -> None:
        """Filtre 'active' retourne uniquement les souhaits actifs."""
        bot.add_wish("A")
        bot.add_wish("B")
        bot.toggle_wish("B", False)
        bot._filter = "active"
        result = bot._get_filtered_wishlist()
        assert len(result) == 1
        assert result[0]["query"] == "A"

    def test_filter_inactive(self, bot: BotWishlist) -> None:
        """Filtre 'inactive' retourne uniquement les souhaits inactifs."""
        bot.add_wish("A")
        bot.add_wish("B")
        bot.toggle_wish("B", False)
        bot._filter = "inactive"
        result = bot._get_filtered_wishlist()
        assert len(result) == 1
        assert result[0]["query"] == "B"

    def test_filter_error(self, bot: BotWishlist) -> None:
        """Filtre 'error' retourne les souhaits en erreur."""
        bot.add_wish("A")
        bot.add_wish("B")
        bot.toggle_wish("B", False)
        # Simuler un statut error sur A
        bot._wishlist[0]["status"] = "error"
        bot._filter = "error"
        result = bot._get_filtered_wishlist()
        assert len(result) == 1
        assert result[0]["query"] == "A"

    def test_search_text(self, bot: BotWishlist) -> None:
        """Le texte de recherche filtre par query (case insensitive)."""
        bot.add_wish("Pink Floyd")
        bot.add_wish("Led Zeppelin")
        bot.add_wish("Deep Purple")
        bot._filter = "all"
        bot._search_text = "pink"
        result = bot._get_filtered_wishlist()
        assert len(result) == 1
        assert result[0]["query"] == "Pink Floyd"

    def test_search_text_partial_match(self, bot: BotWishlist) -> None:
        """La recherche supporte les correspondances partielles."""
        bot.add_wish("Pink Floyd")
        bot.add_wish("Pink Panther")
        bot.add_wish("Led Zeppelin")
        bot._filter = "all"
        bot._search_text = "Pink"
        result = bot._get_filtered_wishlist()
        assert len(result) == 2

    def test_search_text_no_match(self, bot: BotWishlist) -> None:
        """Aucun résultat si la recherche ne correspond à rien."""
        bot.add_wish("Pink Floyd")
        bot._filter = "all"
        bot._search_text = "ZZZZZ"
        result = bot._get_filtered_wishlist()
        assert len(result) == 0

    def test_filter_and_search_combined(self, bot: BotWishlist) -> None:
        """Le filtrage par statut et texte fonctionnent ensemble."""
        bot.add_wish("Pink Floyd")
        bot.add_wish("Pink Panther")
        bot.add_wish("Led Zeppelin")
        bot.toggle_wish("Pink Panther", False)
        bot._filter = "active"
        bot._search_text = "Pink"
        result = bot._get_filtered_wishlist()
        assert len(result) == 1
        assert result[0]["query"] == "Pink Floyd"

    def test_filter_all_includes_error(self, bot: BotWishlist) -> None:
        """Le filtre 'all' inclut aussi les entrées en erreur."""
        bot.add_wish("A")
        bot.add_wish("B")
        bot._wishlist[1]["status"] = "error"
        bot._filter = "all"
        result = bot._get_filtered_wishlist()
        assert len(result) == 2


# ═════════════════════════════════════════════════════════════════
#  Tests de refresh (cycle complet)
# ═════════════════════════════════════════════════════════════════


class TestRefresh:
    def test_refresh_reloads_from_app_config(self, bot: BotWishlist) -> None:
        """refresh() recharge depuis app_config."""
        bot.add_wish("From Memory")
        app_config.set("recherche.souhaits", json.dumps([{"query": "From Config", "enabled": True}]))
        bot.refresh()
        assert len(bot._wishlist) == 1
        assert bot._wishlist[0]["query"] == "From Config"

    def test_refresh_handles_empty_config(self, bot: BotWishlist) -> None:
        """refresh() avec config vide donne une liste vide."""
        bot.add_wish("Temp")
        app_config.set("recherche.souhaits", "")
        bot.refresh()
        assert bot._wishlist == []

    def test_refresh_preserves_metadata_for_existing(self, bot: BotWishlist) -> None:
        """refresh() préserve les métadonnées des queries qui existent toujours."""
        bot.add_wish("Persistent")
        bot._local_metadata["Persistent"] = {"results": 99, "status": "active"}
        bot.refresh()
        assert bot._wishlist[0]["results"] == 99


# ═════════════════════════════════════════════════════════════════
#  Tests de persistance (format JSON)
# ═════════════════════════════════════════════════════════════════


class TestPersistence:
    def test_enabled_state_saved_and_loaded(self, qapp: QApplication, tmp_app_config: Path) -> None:
        """L'état enabled survit à un cycle save/load."""
        bot1 = BotWishlist()
        bot1.add_wish("A")
        bot1.toggle_wish("A", False)
        bot1.add_wish("B")

        bot2 = BotWishlist()
        assert bot2._wishlist[0]["query"] == "A"
        assert bot2._wishlist[0]["enabled"] is False
        assert bot2._wishlist[1]["query"] == "B"
        assert bot2._wishlist[1]["enabled"] is True

    def test_json_format_in_app_config(self, bot: BotWishlist) -> None:
        """Le format dans app_config est bien du JSON valide avec query + enabled."""
        bot.add_wish("Test")
        raw = app_config.get("recherche.souhaits", "")
        parsed = json.loads(raw)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert "query" in parsed[0]
        assert "enabled" in parsed[0]

    def test_csv_to_json_migration(self, qapp: QApplication, tmp_app_config: Path) -> None:
        """Les anciennes données CSV sont lues correctement (migration)."""
        app_config.set("recherche.souhaits", "Pink Floyd, Led Zeppelin")

        bot = BotWishlist()
        assert len(bot._wishlist) == 2
        # Le save doit écrire en JSON
        bot.toggle_wish("Pink Floyd", False)

        raw = app_config.get("recherche.souhaits", "")
        assert raw.startswith("[")  # maintenant en JSON


# ═════════════════════════════════════════════════════════════════
#  Tests de search_now (recherche immédiate)
# ═════════════════════════════════════════════════════════════════


class TestSearchNow:
    def test_search_now_updates_timestamp(self, bot: BotWishlist) -> None:
        """search_now() met à jour le timestamp last_search."""
        bot.add_wish("Test")
        bot.search_now("Test")
        entry = bot._wishlist[0]
        assert "last_search" in entry
        assert entry["last_search"] is not None
        assert entry["last_search"] != "jamais"
        # Le format doit être "à HH:MM" (ex: "à 14:30")
        assert entry["last_search"].startswith("à ")

    def test_search_now_nonexistent_does_nothing(self, bot: BotWishlist) -> None:
        """search_now() sur une query inexistante ne fait rien."""
        bot.add_wish("Real")
        bot.search_now("Fake")
        assert bot._wishlist[0]["last_search"] == "jamais"


# ═════════════════════════════════════════════════════════════════
#  Tests de _on_toggle_all
# ═════════════════════════════════════════════════════════════════


class TestToggleAll:
    def test_toggle_all_disables_all_when_all_active(self, bot: BotWishlist) -> None:
        """Quand tous les souhaits sont actifs, Tout basculer les désactive tous."""
        bot.add_wish("A")
        bot.add_wish("B")
        bot._on_toggle_all()
        assert all(w["enabled"] is False for w in bot._wishlist)

    def test_toggle_all_activates_all_when_some_inactive(self, bot: BotWishlist) -> None:
        """Quand certains sont inactifs, Tout basculer les active tous."""
        bot.add_wish("A")
        bot.add_wish("B")
        bot.toggle_wish("B", False)
        bot._on_toggle_all()
        assert all(w["enabled"] is True for w in bot._wishlist)

    def test_toggle_all_with_empty_list(self, bot: BotWishlist) -> None:
        """Tout basculer avec une liste vide ne fait rien."""
        bot._on_toggle_all()  # ne doit pas planter
        assert bot._wishlist == []

    def test_toggle_all_persists(self, bot: BotWishlist) -> None:
        """Tout basculer persiste dans app_config."""
        bot.add_wish("A")
        bot._on_toggle_all()

        raw = app_config.get("recherche.souhaits", "")
        parsed = json.loads(raw)
        assert parsed[0]["enabled"] is False
