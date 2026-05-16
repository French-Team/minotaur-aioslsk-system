"""Tests unitaires pour BotAccueil (src/gui/widgets/bots/bot_accueil.py).

Ne teste que la logique métier (intent matching, suggestions, données,
persistance, navigation) sans dépendre du rendu UI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest
from pytest import MonkeyPatch

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QWidget

from src.gui.widgets.bots.bot_accueil import BotAccueil
from src.gui.widgets.bots.bot_accueil_knowledge import KNOWLEDGE


# ═════════════════════════════════════════════════════════════════
#  Fixtures
# ═════════════════════════════════════════════════════════════════


@pytest.fixture
def tmp_history_file(tmp_path: Path) -> Path:
    """Crée un chemin de fichier d'historique temporaire."""
    return tmp_path / "data" / "bot_accueil_history.json"


@pytest.fixture
def bot(qapp: QApplication, tmp_history_file: Path) -> BotAccueil:
    """Crée un BotAccueil avec un fichier d'historique temporaire.

    Nettoie les effets de bord de __init__ (message de bienvenue)
    et redirige _history_file vers le chemin temporaire.
    """
    bot = BotAccueil()

    # Rediriger le fichier d'historique
    bot._history_file = tmp_history_file
    bot._history_file.parent.mkdir(parents=True, exist_ok=True)

    # Nettoyer les messages créés par _show_welcome() dans __init__
    bot._messages = []
    while bot._messages_layout.count() > 1:
        item = bot._messages_layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()

    return bot


# ═════════════════════════════════════════════════════════════════
#  Tests de _match_intent
# ═════════════════════════════════════════════════════════════════
#
# Note : Les clés KNOWLEDGE sont en français :
#        - 'bonjour' (pas 'greeting')
#        - 'merci' (pas 'thanks')
#        - 'qui_es_tu' (pas 'about_identity')
#        - 'chercher' (pas 'need_search')
#        - 'telechargement' (pas 'need_download')
#        - 'soulseek' (pas 'what_is_soulseek')
#        - 'quoi_de_neuf' (pas 'check_update')
#        - 'fallback' n'a PAS de keywords — il ne peut pas matcher
#          via _match_intent. La gestion du fallback est dans
#          _on_user_input (branche else).


class TestMatchIntent:
    """Teste la logique pure de matching d'intention."""

    def test_empty_text_returns_none(self, bot: BotAccueil) -> None:
        """Texte vide → None."""
        assert bot._match_intent("") is None

    def test_whitespace_only_returns_none(self, bot: BotAccueil) -> None:
        """Espaces seulement → None."""
        assert bot._match_intent("   ") is None

    def test_bonjour(self, bot: BotAccueil) -> None:
        """'Salut' match l'entrée 'bonjour'."""
        assert bot._match_intent("Salut") == "bonjour"

    def test_bonjour_variants(self, bot: BotAccueil) -> None:
        """Différentes formulations de saluation."""
        for text in ["Bonjour", "Hello", "Coucou", "Salut toi"]:
            result = bot._match_intent(text)
            assert result == "bonjour", f"'{text}' devrait matcher bonjour, got {result}"

    def test_merci(self, bot: BotAccueil) -> None:
        """'Merci beaucoup' match l'entrée 'merci'."""
        assert bot._match_intent("Merci beaucoup") == "merci"

    def test_qui_es_tu(self, bot: BotAccueil) -> None:
        """'Qui es-tu' match l'entrée 'qui_es_tu'."""
        assert bot._match_intent("Qui es-tu") == "qui_es_tu"

    def test_chercher(self, bot: BotAccueil) -> None:
        """'Je cherche des fichiers' match l'entrée 'chercher'."""
        result = bot._match_intent("Je cherche des fichiers")
        assert result == "chercher", \
            f"'Je cherche des fichiers' devrait matcher chercher, got {result}"

    def test_telechargement(self, bot: BotAccueil) -> None:
        """'Comment télécharger' match l'entrée 'telechargement'."""
        result = bot._match_intent("Comment télécharger un fichier")
        assert result == "telechargement", \
            f"'télécharger' devrait matcher telechargement, got {result}"

    def test_soulseek(self, bot: BotAccueil) -> None:
        """'C'est quoi Soulseek' match l'entrée 'soulseek'."""
        result = bot._match_intent("C'est quoi Soulseek")
        assert result == "soulseek", \
            f"'Soulseek' devrait matcher soulseek, got {result}"

    def test_quoi_de_neuf(self, bot: BotAccueil) -> None:
        """'Quoi de neuf' match l'entrée 'quoi_de_neuf'."""
        result = bot._match_intent("Quoi de neuf")
        assert result == "quoi_de_neuf", \
            f"'Quoi de neuf' devrait matcher quoi_de_neuf, got {result}"

    def test_quoi_de_neuf_variants(self, bot: BotAccueil) -> None:
        """Variantes : 'nouveauté', 'actualité'."""
        for text in ["Nouveauté", "Actualité", "Nouveau projet"]:
            result = bot._match_intent(text)
            assert result == "quoi_de_neuf", \
                f"'{text}' devrait matcher quoi_de_neuf, got {result}"

    def test_insult_detected(self, bot: BotAccueil) -> None:
        """Insulte → fallback_insulte (a des vrais keywords)."""
        result = bot._match_intent("t'es un idiot")
        # 'idiot' est un keyword de fallback_insulte
        assert result == "fallback_insulte", \
            f"'idiot' devrait matcher fallback_insulte, got {result}"

    def test_unknown_returns_none(self, bot: BotAccueil) -> None:
        """Texte inconnu → None (fallback géré dans _on_user_input)."""
        result = bot._match_intent("xylophone jaune")
        assert result is None, \
            f"'xylophone jaune' devrait être None, got {result}"

    def test_noise_words_ignored(self, bot: BotAccueil) -> None:
        """Mots courts (< 3 lettres) ignorés → None."""
        result = bot._match_intent("ah ! le")
        assert result is None

    def test_best_score_wins(self, bot: BotAccueil) -> None:
        """Parmi plusieurs matchs, le meilleur score est choisi."""
        result = bot._match_intent("Je veux chercher des fichiers à télécharger")
        assert result is not None
        assert result in KNOWLEDGE

    def test_all_entries_have_keywords_except_fallback(
        self, bot: BotAccueil,
    ) -> None:
        """Toutes les entrées sauf 'fallback' ont des keywords de longueur >= 3."""
        for entry_id, entry in KNOWLEDGE.items():
            if entry_id == "fallback":
                continue  # fallback n'a pas de keywords volontairement
            keywords = entry.get("keywords", [])
            long_keywords = [k for k in keywords if len(k) >= 3]
            assert long_keywords, \
                f"Entrée '{entry_id}' n'a aucun keyword de longueur >= 3"


# ═════════════════════════════════════════════════════════════════
#  Tests de _on_suggestion (routing)
# ═════════════════════════════════════════════════════════════════


class TestOnSuggestion:
    """Teste le routage des actions de suggestion via spy pattern."""

    def test_welcome_action(self, bot: BotAccueil, monkeypatch: MonkeyPatch) -> None:
        """Action 'welcome' → _show_welcome()."""
        called = False
        def spy() -> None:
            nonlocal called
            called = True
        monkeypatch.setattr(bot, "_show_welcome", spy)
        bot._on_suggestion("welcome")
        assert called

    def test_about_action(self, bot: BotAccueil, monkeypatch: MonkeyPatch) -> None:
        """Action 'about' → _show_about()."""
        called = False
        def spy() -> None:
            nonlocal called
            called = True
        monkeypatch.setattr(bot, "_show_about", spy)
        bot._on_suggestion("about")
        assert called

    def test_clear_history_action(self, bot: BotAccueil, monkeypatch: MonkeyPatch) -> None:
        """Action 'clear_history' → _on_clear_history()."""
        called = False
        def spy() -> None:
            nonlocal called
            called = True
        monkeypatch.setattr(bot, "_on_clear_history", spy)
        bot._on_suggestion("clear_history")
        assert called

    def test_restore_history_action(self, bot: BotAccueil, monkeypatch: MonkeyPatch) -> None:
        """Action 'restore_history' → _on_restore_history()."""
        called = False
        def spy() -> None:
            nonlocal called
            called = True
        monkeypatch.setattr(bot, "_on_restore_history", spy)
        bot._on_suggestion("restore_history")
        assert called

    def test_navigation_actions(self, bot: BotAccueil, monkeypatch: MonkeyPatch) -> None:
        """Actions de navigation → navigate_to() avec le bon nom de bot."""
        calls: list[tuple[str, str]] = []

        def spy(bot_name: str, icon: str = "➡️") -> None:
            calls.append((bot_name, icon))

        monkeypatch.setattr(bot, "navigate_to", spy)

        nav_actions: dict[str, str] = {
            "search": "Recherche",
            "downloads": "Téléchargement",
            "library": "Bibliothèque",
            "users": "Utilisateurs",
            "wishlist": "Wishlist",
            "surveillance": "Surveillance",
            "planificateur": "Planificateur",
            "ordonnanceur": "Ordonnanceur",
            "stats": "Statistiques",
            "config": "Assistant",
            "help": "Aide",
        }

        for action, expected_bot in nav_actions.items():
            bot._on_suggestion(action)
            assert len(calls) == 1, \
                f"'{action}' devrait appeler navigate_to 1 fois"
            actual_bot, _ = calls[0]
            assert actual_bot == expected_bot, \
                f"'{action}' → '{expected_bot}', pas '{actual_bot}'"
            calls.clear()

    def test_unknown_action_falls_back_to_welcome(
        self, bot: BotAccueil, monkeypatch: MonkeyPatch,
    ) -> None:
        """Action inconnue → fallback vers _show_welcome."""
        called = False
        def spy() -> None:
            nonlocal called
            called = True
        monkeypatch.setattr(bot, "_show_welcome", spy)
        bot._on_suggestion("nonexistent_action_xyz")
        assert called


# ═════════════════════════════════════════════════════════════════
#  Tests de add_message (structure de données)
# ═════════════════════════════════════════════════════════════════


class TestAddMessage:
    """Teste que add_message() ajoute correctement les entrées à _messages."""

    def test_add_message_appends_to_list(self, bot: BotAccueil) -> None:
        """Un message est ajouté à _messages."""
        bot.add_message("🖐️", "Bonjour !")
        assert len(bot._messages) == 1

    def test_add_message_structure(self, bot: BotAccueil) -> None:
        """La structure du message est correcte."""
        bot.add_message("🔍", "Résultat de recherche")
        msg = bot._messages[0]
        assert msg["type"] == "bot"
        assert msg["icon"] == "🔍"
        assert msg["text"] == "Résultat de recherche"
        assert "timestamp" in msg

    def test_add_message_with_suggestions(self, bot: BotAccueil) -> None:
        """Les suggestions sont stockées dans le message."""
        suggestions = [
            {"label": "🔍 Chercher", "action": "search"},
            {"label": "❓ Aide", "action": "help"},
        ]
        bot.add_message("🖐️", "Que veux-tu faire ?", suggestions)
        msg = bot._messages[0]
        assert msg["suggestions"] == suggestions

    def test_add_message_no_suggestions(self, bot: BotAccueil) -> None:
        """Sans suggestions, le champ est None."""
        bot.add_message("🖐️", "Message sans suggestions")
        assert bot._messages[0]["suggestions"] is None

    def test_multiple_messages_in_order(self, bot: BotAccueil) -> None:
        """Plusieurs messages sont conservés dans l'ordre."""
        bot.add_message("1️⃣", "Premier")
        bot.add_message("2️⃣", "Deuxième")
        bot.add_message("3️⃣", "Troisième")
        assert len(bot._messages) == 3
        assert bot._messages[0]["text"] == "Premier"
        assert bot._messages[1]["text"] == "Deuxième"
        assert bot._messages[2]["text"] == "Troisième"


# ═════════════════════════════════════════════════════════════════
#  Tests de add_user_message (ajout d'un message utilisateur)
# ═════════════════════════════════════════════════════════════════
#
# Note : add_user_message() ajoute SEULEMENT le message à _messages.
#        La réponse du bot est déclenchée dans _on_user_input().
#        add_user_message ne valide PAS le texte vide (c'est fait
#        dans _on_user_input).


class TestAddUserMessage:
    def test_add_user_message_appends(self, bot: BotAccueil) -> None:
        """Ajoute un message utilisateur à _messages."""
        bot.add_user_message("Bonjour")
        assert len(bot._messages) == 1
        assert bot._messages[0]["type"] == "user"
        assert bot._messages[0]["text"] == "Bonjour"

    def test_add_user_message_structure(self, bot: BotAccueil) -> None:
        """La structure du message utilisateur est correcte."""
        bot.add_user_message("Je cherche un fichier")
        msg = bot._messages[0]
        assert msg["type"] == "user"
        assert msg["text"] == "Je cherche un fichier"
        assert "timestamp" in msg

    def test_add_user_message_empty_text_is_added(self, bot: BotAccueil) -> None:
        """add_user_message('') ajoute quand même — la validation est dans _on_user_input."""
        bot.add_user_message("")
        assert len(bot._messages) == 1

    def test_add_user_message_whitespace_is_added(self, bot: BotAccueil) -> None:
        """add_user_message('   ') ajoute quand même — la validation est dans _on_user_input."""
        bot.add_user_message("   ")
        assert len(bot._messages) == 1

    def test_add_user_message_saves_history(self, bot: BotAccueil) -> None:
        """add_user_message déclenche _save_history()."""
        bot.add_user_message("Test")
        assert bot._history_file.exists()
        data = json.loads(bot._history_file.read_text(encoding="utf-8"))
        assert len(data["messages"]) == 1
        assert data["messages"][0]["type"] == "user"

    def test_multiple_user_messages(self, bot: BotAccueil) -> None:
        """Plusieurs messages utilisateur sont conservés."""
        bot.add_user_message("Premier")
        bot.add_user_message("Deuxième")
        assert len(bot._messages) == 2
        assert bot._messages[0]["text"] == "Premier"
        assert bot._messages[1]["text"] == "Deuxième"


# ═════════════════════════════════════════════════════════════════
#  Tests de l'historique (persistance fichier)
# ═════════════════════════════════════════════════════════════════


class TestHistory:
    """Teste la persistance de l'historique des messages."""

    def test_save_history_creates_file(self, bot: BotAccueil) -> None:
        """_save_history() écrit le fichier JSON."""
        bot.add_message("🖐️", "Bonjour")
        assert bot._history_file.exists()

    def test_save_history_valid_json(self, bot: BotAccueil) -> None:
        """Le fichier d'historique contient du JSON valide."""
        bot.add_message("🖐️", "Bonjour")
        data = json.loads(bot._history_file.read_text(encoding="utf-8"))
        assert "messages" in data
        assert len(data["messages"]) == 1
        assert data["messages"][0]["text"] == "Bonjour"

    def test_save_history_multiple_messages(self, bot: BotAccueil) -> None:
        """Plusieurs messages sont persistés."""
        bot.add_message("🖐️", "Premier")
        bot.add_message("🔍", "Deuxième")
        data = json.loads(bot._history_file.read_text(encoding="utf-8"))
        assert len(data["messages"]) == 2

    def test_check_history_exists_true(self, bot: BotAccueil) -> None:
        """Fichier non vide → _has_history = True."""
        bot.add_message("🖐️", "Un message")
        bot._check_history_exists()
        assert bot._has_history is True

    def test_check_history_exists_false_no_file(self, bot: BotAccueil) -> None:
        """Pas de fichier → _has_history = False."""
        if bot._history_file.exists():
            bot._history_file.unlink()
        bot._check_history_exists()
        assert bot._has_history is False

    def test_check_history_exists_false_too_small(self, bot: BotAccueil) -> None:
        """Fichier trop petit (< 10 bytes) → False."""
        bot._history_file.write_text("{}", encoding="utf-8")
        bot._check_history_exists()
        assert bot._has_history is False

    def test_clear_history_empties_messages(self, bot: BotAccueil) -> None:
        """clear_history() vide _messages puis affiche le message de bienvenue."""
        bot.add_message("🖐️", "Ancien")
        bot.clear_history()
        # clear_history appelle _show_welcome() qui ajoute 1 message
        # Donc _messages n'est pas vide, il a le welcome
        assert len(bot._messages) >= 1
        assert bot._messages[0]["icon"] == "🖐️"

    def test_clear_history_removes_old_content(self, bot: BotAccueil) -> None:
        """Après clear_history, les anciens messages ont disparu."""
        bot.add_message("🔍", "Recherche")
        bot.add_message("📥", "Téléchargement")
        bot.clear_history()
        for msg in bot._messages:
            assert msg["text"] != "Recherche", "Les anciens messages doivent disparaître"
            assert msg["text"] != "Téléchargement"

    def test_restore_history_from_file(self, bot: BotAccueil) -> None:
        """_restore_history() restaure les messages depuis le fichier."""
        bot.add_message("🖐️", "Bonjour")
        bot.add_message("🔍", "Résultat")

        # Nettoyer la mémoire et les widgets UI
        bot._messages = []
        while bot._messages_layout.count() > 1:
            item = bot._messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        bot._restore_history()
        assert len(bot._messages) == 2
        assert bot._messages[0]["text"] == "Bonjour"
        assert bot._messages[1]["text"] == "Résultat"

    def test_restore_history_empty_file_shows_welcome(self, bot: BotAccueil) -> None:
        """Fichier vide → appelle _show_welcome (1 message)."""
        bot._history_file.write_text(
            json.dumps({"messages": []}), encoding="utf-8",
        )
        bot._restore_history()
        assert len(bot._messages) >= 1
        assert bot._messages[0]["icon"] == "🖐️"

    def test_restore_history_corrupted_file_shows_welcome(self, bot: BotAccueil) -> None:
        """Fichier corrompu → appelle _show_welcome."""
        bot._history_file.write_text("Not JSON!!!", encoding="utf-8")
        bot._restore_history()
        assert len(bot._messages) >= 1
        assert bot._messages[0]["icon"] == "🖐️"


# ═════════════════════════════════════════════════════════════════
#  Tests de navigate_to (signal de navigation)
# ═════════════════════════════════════════════════════════════════
#
# Note : navigate_to() utilise QTimer.singleShot(1500, ...).
#        Pour les tests, on monkeypatche QTimer pour exécuter
#        le callback immédiatement.


class TestNavigateTo:
    def test_navigate_to_adds_message(self, bot: BotAccueil) -> None:
        """navigate_to() ajoute un message de redirection."""
        bot.navigate_to("Recherche", "🔍")
        assert len(bot._messages) == 1
        assert "Recherche" in bot._messages[0]["text"]

    def test_navigate_to_signal_emitted(self, bot: BotAccueil, monkeypatch: MonkeyPatch) -> None:
        """Le signal page_changed est émis immédiatement (timer patché)."""
        # Patcher QTimer pour exécuter le callback immédiatement
        monkeypatch.setattr(QTimer, "singleShot", lambda delay, callback: callback())

        received: list[str] = []
        bot.page_changed.connect(lambda name: received.append(name))

        bot.navigate_to("Recherche", "🔍")

        assert len(received) == 1
        assert received[0] == "Recherche"

    def test_navigate_to_multiple_bots(self, bot: BotAccueil, monkeypatch: MonkeyPatch) -> None:
        """Navigation vers plusieurs bots différents."""
        monkeypatch.setattr(QTimer, "singleShot", lambda delay, callback: callback())

        received: list[str] = []
        bot.page_changed.connect(lambda name: received.append(name))

        bot.navigate_to("Aide", "❓")
        assert received[0] == "Aide"


# ═════════════════════════════════════════════════════════════════
#  Tests de _execute_actions (séquences d'actions)
# ═════════════════════════════════════════════════════════════════
#
# Note : _execute_actions utilise QTimer.singleShot pour les délais.
#        On teste la partie synchrone uniquement.


class TestExecuteActions:
    def test_empty_actions_does_nothing(self, bot: BotAccueil) -> None:
        """Actions vides → rien ne se passe."""
        bot._execute_actions([])
        assert len(bot._messages) == 0

    def test_single_message_action(self, bot: BotAccueil) -> None:
        """Action 'message' ajoute un message immédiatement."""
        actions = [
            {"type": "message", "icon": "💬", "text": "Test message"},
        ]
        bot._execute_actions(actions)
        assert len(bot._messages) == 1
        assert bot._messages[0]["text"] == "Test message"

    def test_message_action_with_suggestions(self, bot: BotAccueil) -> None:
        """Action 'message' avec suggestions."""
        suggestions = [{"label": "OK", "action": "welcome"}]
        actions = [
            {"type": "message", "icon": "💬", "text": "Choisis", "suggestions": suggestions},
        ]
        bot._execute_actions(actions)
        assert bot._messages[0]["suggestions"] == suggestions

    def test_single_navigate_action(self, bot: BotAccueil) -> None:
        """Action 'navigate' ajoute un message de redirection."""
        actions = [
            {"type": "navigate", "bot": "Recherche", "icon": "🔍"},
        ]
        bot._execute_actions(actions)
        assert len(bot._messages) == 1
        assert "Recherche" in bot._messages[0]["text"]

    def test_message_then_navigate(self, bot: BotAccueil) -> None:
        """Deux actions : message puis navigate — seule la première est synchrone."""
        actions = [
            {"type": "message", "icon": "💬", "text": "Préparation..."},
            {"type": "navigate", "bot": "Recherche", "icon": "🔍"},
        ]
        bot._execute_actions(actions)
        # La première action est synchrone
        assert len(bot._messages) == 1
        assert bot._messages[0]["text"] == "Préparation..."
