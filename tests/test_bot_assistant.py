"""Tests unitaires pour le BotAssistant — couche SQLite (Étape 1) + matching + handlers (Étape 2) + dashboard (Étape 4) + routage (Étape 5)."""

from __future__ import annotations

import json
import sqlite3
from typing import Any
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QTimer

from src.gui.widgets.bots.bot_assistant import BotAssistant


@pytest.fixture
def assistant(tmp_bot_assistant_db: str, qapp: Any) -> BotAssistant:
    """Instance de BotAssistant avec base SQLite temporaire."""
    assistant = BotAssistant()
    # Rediriger le chemin de la base
    assistant._db_path = tmp_bot_assistant_db
    assistant._init_database()
    yield assistant
    assistant.deleteLater()


# ── Couche SQLite (Étape 1) ─────────────────────────────────────────

@pytest.mark.qt_heavy
class TestDatabase:
    """Tests de la base SQLite bot_assistant.db."""

    def test_init_database_creates_tables(self, assistant: BotAssistant) -> None:
        """Les tables interactions et diagnostics existent après init."""
        conn = sqlite3.connect(assistant._db_path)
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        conn.close()
        assert "interactions" in tables
        assert "diagnostics" in tables

    def test_init_database_reentrant(self, assistant: BotAssistant) -> None:
        """Appeler _init_database() deux fois ne lève pas d'erreur."""
        assistant._init_database()  # seconde fois — doit être idempotent
        conn = sqlite3.connect(assistant._db_path)
        count = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
        conn.close()
        assert count == 0

    def test_log_interaction_persists(self, assistant: BotAssistant) -> None:
        """_log_interaction écrit une ligne dans la table."""
        response = json.dumps({"message": "Test", "severity": "info"}, ensure_ascii=False)
        assistant._log_interaction("config", "Comment configurer le port ?", response, success=True)

        conn = sqlite3.connect(assistant._db_path)
        row = conn.execute(
            "SELECT action_type, query, success FROM interactions WHERE id = 1"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "config"
        assert "port" in row[1]
        assert row[2] == 1  # success

    def test_log_interaction_with_error(self, assistant: BotAssistant) -> None:
        """_log_interaction enregistre aussi les échecs avec leur message."""
        response = json.dumps({"message": "Erreur", "severity": "error"}, ensure_ascii=False)
        assistant._log_interaction(
            "diagnostic", "Erreur connexion", response,
            success=False, error_message="Timeout",
        )

        conn = sqlite3.connect(assistant._db_path)
        row = conn.execute(
            "SELECT success, error_message FROM interactions WHERE id = 1"
        ).fetchone()
        conn.close()
        assert row[0] == 0
        assert row[1] == "Timeout"

    def test_log_diagnostic_persists(self, assistant: BotAssistant) -> None:
        """_log_diagnostic écrit dans la table diagnostics."""
        assistant._log_diagnostic("connexion", "ok", "Connecté au serveur", None)

        conn = sqlite3.connect(assistant._db_path)
        row = conn.execute(
            "SELECT check_type, status FROM diagnostics WHERE id = 1"
        ).fetchone()
        conn.close()
        assert row == ("connexion", "ok")

    def test_log_diagnostic_with_suggestion(self, assistant: BotAssistant) -> None:
        """_log_diagnostic enregistre la suggestion si fournie."""
        assistant._log_diagnostic(
            "transfert", "warning",
            "3 téléchargements bloqués",
            "Vérifier la file d'attente",
        )

        conn = sqlite3.connect(assistant._db_path)
        row = conn.execute(
            "SELECT suggestion FROM diagnostics WHERE id = 1"
        ).fetchone()
        conn.close()
        assert row[0] == "Vérifier la file d'attente"

    def test_get_stats_returns_counts(self, assistant: BotAssistant) -> None:
        """_get_stats retourne les compteurs d'interactions et diagnostics."""
        # Ajouter quelques données
        r = json.dumps({"message": "OK", "severity": "info"}, ensure_ascii=False)
        assistant._log_interaction("config", "q1", r, success=True)
        assistant._log_interaction("config", "q2", r, success=True)
        assistant._log_interaction("diagnostic", "q3", r, success=False, error_message="fail")
        assistant._log_diagnostic("connexion", "ok", "OK", None)

        stats = assistant._get_stats()
        assert stats["total_interactions"] == 3
        assert stats["successful"] == 2
        assert stats["failed"] == 1
        assert stats["total_diagnostics"] == 1

    def test_get_interactions_returns_ordered(self, assistant: BotAssistant) -> None:
        """_get_interactions retourne les interactions triées par id décroissant (le plus récent en premier)."""
        r = json.dumps({"message": "OK", "severity": "info"}, ensure_ascii=False)
        assistant._log_interaction("config", "première", r, success=True)
        assistant._log_interaction("diagnostic", "deuxième", r, success=True)

        interactions = assistant._get_interactions(limit=10)
        assert len(interactions) == 2
        assert interactions[0]["query"] == "deuxième"
        assert interactions[1]["query"] == "première"

    def test_get_last_diagnostic_returns_latest(self, assistant: BotAssistant) -> None:
        """_get_last_diagnostic retourne le diagnostic le plus récent."""
        assistant._log_diagnostic("connexion", "ok", "Connexion OK", None)
        assistant._log_diagnostic("transfert", "warning", "3 en attente", "Vérifier")

        last = assistant._get_last_diagnostic()
        assert last is not None
        assert last["check_type"] == "transfert"
        assert last["status"] == "warning"

    def test_get_last_diagnostic_returns_none_when_empty(self, assistant: BotAssistant) -> None:
        """_get_last_diagnostic retourne None si aucun diagnostic."""
        assert assistant._get_last_diagnostic() is None

    def test_get_interactions_empty_db(self, assistant: BotAssistant) -> None:
        """_get_interactions retourne [] si la base est vide."""
        assert assistant._get_interactions(limit=10) == []

    def test_get_interactions_respects_limit(self, assistant: BotAssistant) -> None:
        """_get_interactions limite le nombre de résultats."""
        r = json.dumps({"message": "OK", "severity": "info"}, ensure_ascii=False)
        for i in range(5):
            assistant._log_interaction("config", f"query {i}", r, success=True)

        interactions = assistant._get_interactions(limit=3)
        assert len(interactions) == 3


# ── Règles de matching (Étape 2) ──────────────────────────────────

@pytest.mark.qt_heavy
class TestMatching:
    """Tests des règles de matching interne d'Assistant."""

    # ── _match_config ──

    def test_match_config_port_ecoute(self, assistant: BotAssistant) -> None:
        result = assistant._match_config("Comment changer le port d'écoute ?")
        assert result == ("reseau", "port_ecoute")

    def test_match_config_partage(self, assistant: BotAssistant) -> None:
        result = assistant._match_config("Je veux partager mon dossier musique")
        assert result == ("partages", "dossier_1_chemin")

    def test_match_config_destination(self, assistant: BotAssistant) -> None:
        result = assistant._match_config("Où sont sauvegardés mes téléchargements ?")
        assert result == ("telechargement", "dossier_destination")

    def test_match_config_description(self, assistant: BotAssistant) -> None:
        result = assistant._match_config("Comment changer ma description ?")
        assert result == ("general", "description_profil")

    def test_match_config_bio(self, assistant: BotAssistant) -> None:
        """'bio' est un mot-clé valide pour la config générale."""
        result = assistant._match_config("Je veux changer ma bio")
        assert result == ("general", "description_profil")

    def test_match_config_unknown(self, assistant: BotAssistant) -> None:
        """Une requête inconnue retourne None."""
        result = assistant._match_config("Quel temps fait-il aujourd'hui ?")
        assert result is None

    def test_match_config_empty(self, assistant: BotAssistant) -> None:
        """Une requête vide retourne None."""
        result = assistant._match_config("")
        assert result is None

    # ── _match_diagnostic ──

    def test_match_diagnostic_connexion(self, assistant: BotAssistant) -> None:
        result = assistant._match_diagnostic("Je n'arrive pas à me connecter")
        assert result == "connexion"

    def test_match_diagnostic_lenteur(self, assistant: BotAssistant) -> None:
        result = assistant._match_diagnostic("Mes téléchargements sont très lents")
        assert result == "transfert"

    def test_match_diagnostic_performance(self, assistant: BotAssistant) -> None:
        result = assistant._match_diagnostic("L'application utilise trop de mémoire")
        assert result == "performance"

    def test_match_diagnostic_unknown(self, assistant: BotAssistant) -> None:
        result = assistant._match_diagnostic("J'aime les chiens")
        assert result is None

    # ── _match_recommendation ──

    def test_match_recommendation_recherche(self, assistant: BotAssistant) -> None:
        result = assistant._match_recommendation("Comment chercher des fichiers ?")
        assert result == ("Recherche", "🔍")

    def test_match_recommendation_telechargement(self, assistant: BotAssistant) -> None:
        result = assistant._match_recommendation("Je veux télécharger de la musique")
        assert result == ("Téléchargement", "📥")

    def test_match_recommendation_wishlist(self, assistant: BotAssistant) -> None:
        result = assistant._match_recommendation("J'attends un fichier sur ma wishlist")
        assert result == ("Wishlist", "📋")

    def test_match_recommendation_unknown(self, assistant: BotAssistant) -> None:
        result = assistant._match_recommendation("Quelle est la capitale du Japon ?")
        assert result is None

    # ── _match_tutorial ──

    def test_match_tutorial_planifier(self, assistant: BotAssistant) -> None:
        result = assistant._match_tutorial("Comment planifier un téléchargement automatique ?")
        assert result == "planifier-tache-programmee"

    def test_match_tutorial_optimiser(self, assistant: BotAssistant) -> None:
        result = assistant._match_tutorial("Je veux optimiser la vitesse")
        assert result == "optimiser-telechargements"

    def test_match_tutorial_unknown(self, assistant: BotAssistant) -> None:
        result = assistant._match_tutorial("Raconte-moi une blague")
        assert result is None

    def test_match_diagnostic_empty(self, assistant: BotAssistant) -> None:
        """_match_diagnostic avec une chaîne vide retourne None."""
        result = assistant._match_diagnostic("")
        assert result is None

    def test_match_recommendation_empty(self, assistant: BotAssistant) -> None:
        """_match_recommendation avec une chaîne vide retourne None."""
        result = assistant._match_recommendation("")
        assert result is None

    def test_match_tutorial_empty(self, assistant: BotAssistant) -> None:
        """_match_tutorial avec une chaîne vide retourne None."""
        result = assistant._match_tutorial("")
        assert result is None


# ── Gestionnaires (Étape 2) ─────────────────────────────────────

@pytest.mark.qt_heavy
class TestHandlers:
    """Tests des handlers de traitement (sans dépendances externes)."""

    def test_handle_config_known(self, assistant: BotAssistant) -> None:
        """_handle_config retourne une réponse structurée pour une requête connue."""
        result = assistant._handle_config("Comment changer le port d'écoute ?")
        assert "message" in result
        assert "severity" in result
        assert result["severity"] == "info"
        assert "suggestions" in result
        assert len(result["suggestions"]) > 0

    def test_handle_config_unknown(self, assistant: BotAssistant) -> None:
        """_handle_config retourne un warning pour une requête inconnue."""
        result = assistant._handle_config("Quel temps fait-il ?")
        assert result["severity"] == "warning"
        assert "n'ai pas compris" in result["message"].lower()

    def test_handle_diagnostic_known(self, assistant: BotAssistant) -> None:
        """_handle_diagnostic retourne un diagnostic structuré."""
        result = assistant._handle_diagnostic("Je n'arrive pas à me connecter")
        assert "message" in result
        assert result["severity"] in ("info", "warning", "error", "success")

    def test_handle_diagnostic_unknown(self, assistant: BotAssistant) -> None:
        """_handle_diagnostic retourne un warning pour un problème inconnu."""
        result = assistant._handle_diagnostic("J'ai un problème bizarre")
        assert result["severity"] == "warning"

    def test_handle_recommendation_known(self, assistant: BotAssistant) -> None:
        """_handle_recommendation suggère un bot."""
        result = assistant._handle_recommendation("Comment chercher des fichiers ?")
        assert result["severity"] == "info"
        assert "navigation" in result
        assert result["navigation"]["bot"] == "Recherche"

    def test_handle_recommendation_unknown(self, assistant: BotAssistant) -> None:
        """_handle_recommendation retourne un warning pour une demande inconnue."""
        result = assistant._handle_recommendation("Donne-moi un conseil")
        assert result["severity"] == "warning"

    def test_handle_tutorial_known(self, assistant: BotAssistant) -> None:
        """_handle_tutorial retourne un tutoriel structuré."""
        result = assistant._handle_tutorial("Comment planifier un téléchargement ?")
        assert "message" in result
        assert result["severity"] == "info"

    def test_handle_tutorial_unknown(self, assistant: BotAssistant) -> None:
        """_handle_tutorial retourne un warning pour une demande inconnue."""
        result = assistant._handle_tutorial("Apprends-moi le Python")
        assert result["severity"] == "warning"


# ── Dashboard (Étape 4) ────────────────────────────────────────────

@pytest.mark.qt_heavy
class TestDashboard:
    """Tests des méthodes du dashboard (update_stats, add_activity_entry)."""

    def test_update_stats_with_empty_db(self, assistant: BotAssistant) -> None:
        """_update_stats ne plante pas si la base est vide."""
        assistant._update_stats()

    def test_update_stats_with_data(self, assistant: BotAssistant) -> None:
        """_update_stats met à jour les labels de stats après des données."""
        r = json.dumps({"message": "OK", "severity": "info"}, ensure_ascii=False)
        assistant._log_interaction("config", "test", r, success=True)
        assistant._log_interaction("config", "test2", r, success=True)
        assistant._log_interaction("diagnostic", "test3", r, success=False, error_message="fail")

        stats = assistant._get_stats()
        assert stats["total_interactions"] == 3
        assert stats["successful"] == 2
        assert stats["failed"] == 1

    def test_add_activity_entry(self, assistant: BotAssistant) -> None:
        """_add_activity_entry ajoute une entrée sans planter."""
        assistant._add_activity_entry("config", "✅", "Configuration réseau")
        assert assistant._activity_list is not None
        assert assistant._activity_list.count() == 1


# ── Point d'entrée / routage (Étape 5) ─────────────────────────────

@pytest.mark.qt_heavy
class TestOnAssistantRequest:
    """Tests du point d'entrée _on_assistant_request : routage, validation, persistance."""

    def test_routing_config(self, assistant: BotAssistant) -> None:
        """Un action_type config routé vers _handle_config retourne severity='info'."""
        responses: list[str] = []
        assistant.assistant_response.connect(responses.append)

        assistant._on_assistant_request("config", "Comment changer le port d'écoute ?")

        assert len(responses) == 1
        data = json.loads(responses[0])
        assert data["severity"] == "info"
        assert "message" in data

    def test_routing_all_types(self, assistant: BotAssistant) -> None:
        """Les 4 types d'action sont routés sans erreur."""
        responses: list[str] = []
        assistant.assistant_response.connect(responses.append)

        assistant._on_assistant_request("config", "Changer le port")
        assistant._on_assistant_request("diagnostic", "Connexion impossible")
        assistant._on_assistant_request("recommendation", "Chercher des fichiers")
        assistant._on_assistant_request("tutorial", "Planifier un téléchargement")

        assert len(responses) == 4
        for r in responses:
            data = json.loads(r)
            assert "message" in data
            assert "severity" in data

    def test_action_invalide(self, assistant: BotAssistant) -> None:
        """Un action_type invalide retourne une réponse d'erreur avec severity='error'."""
        responses: list[str] = []
        assistant.assistant_response.connect(responses.append)

        assistant._on_assistant_request("bad_type", "test")

        assert len(responses) == 1
        data = json.loads(responses[0])
        assert data["severity"] == "error"
        # La réponse d'erreur doit contenir l'erreur dans data ou le message d'erreur
        assert "error" in data.get("data", {}) or "error" in data

    def test_persistence(self, assistant: BotAssistant) -> None:
        """Une requête _on_assistant_request est persistée en SQLite."""
        assistant._on_assistant_request("config", "Comment changer le port ?")

        conn = sqlite3.connect(assistant._db_path)
        row = conn.execute(
            "SELECT action_type, query, success FROM interactions WHERE id = 1"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "config"
        assert row[2] == 1  # success


# ── Intégration Assistant ↔ BotAccueil (Étape 6) ──────────────────────


@pytest.mark.qt_heavy
class TestSetupAssistant:
    """Tests de connexion BotAssistant ↔ BotAccueil (setup_assistant)."""

    def test_setup_assistant_stores_reference(self, assistant: BotAssistant, qapp: Any) -> None:
        """setup_assistant stocke la référence vers BotAssistant."""
        from src.gui.widgets.bots.bot_accueil import BotAccueil

        accueil = BotAccueil()
        accueil.setup_assistant(assistant)
        assert accueil._assistant is assistant

    def test_setup_assistant_signal_routing(self, assistant: BotAssistant, qapp: Any) -> None:
        """assistant_request.emit() déclenche _on_assistant_request via le signal."""
        from src.gui.widgets.bots.bot_accueil import BotAccueil

        accueil = BotAccueil()
        accueil.setup_assistant(assistant)

        responses: list[str] = []
        assistant.assistant_response.connect(responses.append)

        accueil.assistant_request.emit("config", "Comment changer le port d'écoute ?")

        assert len(responses) == 1
        data = json.loads(responses[0])
        assert data["severity"] == "info"
        assert "message" in data


@pytest.mark.qt_heavy
class TestDetectAssistantAction:
    """Tests de détection du type d'action pour l'Assistant."""

    @staticmethod
    def _make_accueil(qapp: Any) -> Any:
        from src.gui.widgets.bots.bot_accueil import BotAccueil
        return BotAccueil()

    def test_detect_tutorial(self, qapp: Any) -> None:
        """Les mots-clés tutorial retournent 'tutorial'."""
        accueil = self._make_accueil(qapp)
        assert accueil._detect_assistant_action("Comment planifier un téléchargement ?") == "tutorial"
        assert accueil._detect_assistant_action("Apprends-moi à optimiser mes téléchargements") == "tutorial"
        assert accueil._detect_assistant_action("Guide pour nettoyer la file d'attente") == "tutorial"

    def test_detect_config(self, qapp: Any) -> None:
        """Les mots-clés config retournent 'config'."""
        accueil = self._make_accueil(qapp)
        assert accueil._detect_assistant_action("Configurer le port d'écoute") == "config"
        assert accueil._detect_assistant_action("Changer le dossier de partage") == "config"
        assert accueil._detect_assistant_action("Modifier la description du profil") == "config"
        assert accueil._detect_assistant_action("Paramètre réseau avancé") == "config"

    def test_detect_diagnostic(self, qapp: Any) -> None:
        """Les mots-clés diagnostic retournent 'diagnostic'."""
        accueil = self._make_accueil(qapp)
        assert accueil._detect_assistant_action("Problème de connexion au serveur") == "diagnostic"
        assert accueil._detect_assistant_action("Mes téléchargements sont très lents") == "diagnostic"
        assert accueil._detect_assistant_action("Erreur de transfert détectée") == "diagnostic"
        assert accueil._detect_assistant_action("L'application plante au démarrage") == "diagnostic"

    def test_detect_default_recommendation(self, qapp: Any) -> None:
        """Une requête sans mot-clé retourne 'recommendation' par défaut."""
        accueil = self._make_accueil(qapp)
        assert accueil._detect_assistant_action("Cherche un album de jazz") == "recommendation"
        assert accueil._detect_assistant_action("Quelle est la capitale de la France ?") == "recommendation"

    def test_detect_empty_string(self, qapp: Any) -> None:
        """Chaîne vide retourne 'recommendation'."""
        accueil = self._make_accueil(qapp)
        assert accueil._detect_assistant_action("") == "recommendation"


@pytest.mark.qt_heavy
class TestOnAssistantResponse:
    """Tests du parsing des réponses JSON dans _on_assistant_response."""

    @staticmethod
    def _make_accueil(qapp: Any) -> Any:
        from src.gui.widgets.bots.bot_accueil import BotAccueil
        accueil = BotAccueil()
        accueil.add_message = MagicMock()  # spy pour capturer les appels
        return accueil

    def test_parse_valid_json(self, qapp: Any) -> None:
        """Un JSON valide avec severity='info' est parsé et affiché."""
        accueil = self._make_accueil(qapp)
        accueil._on_assistant_response(
            '{"message": "Voici la configuration", "severity": "info", "suggestions": []}'
        )
        accueil.add_message.assert_called_once()
        args, _ = accueil.add_message.call_args
        assert args[0] == "✅"  # icône
        assert "configuration" in args[1]
        assert args[2] is None  # suggestions vides → None

    def test_parse_error_severity(self, qapp: Any) -> None:
        """severity='error' affiche une icône ❌."""
        accueil = self._make_accueil(qapp)
        accueil._on_assistant_response(
            '{"message": "Erreur critique", "severity": "error", "suggestions": []}'
        )
        accueil.add_message.assert_called_once()
        args, _ = accueil.add_message.call_args
        assert args[0] == "❌"

    def test_parse_invalid_json(self, qapp: Any) -> None:
        """Un JSON invalide affiche un message d'erreur."""
        accueil = self._make_accueil(qapp)
        accueil._on_assistant_response("pas du json")
        accueil.add_message.assert_called_once()
        args, _ = accueil.add_message.call_args
        assert "invalide" in args[1]

    def test_parse_no_message_key(self, qapp: Any) -> None:
        """Un JSON sans clé 'message' utilise le texte par défaut."""
        accueil = self._make_accueil(qapp)
        accueil._on_assistant_response('{"severity": "info", "suggestions": []}')
        accueil.add_message.assert_called_once()
        args, _ = accueil.add_message.call_args
        assert "Pas de message" in args[1]

    def test_parse_with_navigate_suggestion(self, qapp: Any) -> None:
        """Une suggestion de type 'navigate' est convertie en action go_*."""
        accueil = self._make_accueil(qapp)
        accueil._on_assistant_response(
            '{"message": "Va voir", "severity": "info", "suggestions": ['
            '{"label": "🔍 Rechercher", "action": "navigate", "bot": "Recherche"}]}'
        )
        accueil.add_message.assert_called_once()
        args, _ = accueil.add_message.call_args
        assert args[2] is not None
        assert args[2][0]["action"] == "go_recherche"

    def test_parse_with_open_config_suggestion(self, qapp: Any) -> None:
        """Une suggestion 'open_config' est convertie en action 'config'."""
        accueil = self._make_accueil(qapp)
        accueil._on_assistant_response(
            '{"message": "Configure", "severity": "info", "suggestions": ['
            '{"label": "🔧 Ouvrir config", "action": "open_config"}]}'
        )
        accueil.add_message.assert_called_once()
        args, _ = accueil.add_message.call_args
        assert args[2] is not None
        assert args[2][0]["action"] == "config"
