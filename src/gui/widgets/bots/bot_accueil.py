"""
Bot Accueil — hub conversationnel avec chat simulé.

Affiche un message de bienvenue, propose des suggestions sous forme de
boutons, et peut rediriger vers les autres bots de l'Armée des 12 Bots.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from src.gui.widgets.bots.bot_assistant import BotAssistant

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.gui.theme_fragments.colors import COLORS
from src.gui.widgets.bots.bot_accueil_knowledge import KNOWLEDGE

# ── Sous-composants ─────────────────────────────────────────────


class MessageCard(QFrame):
    """Carte de message du bot avec icône et texte."""

    def __init__(self, icon: str, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("messageCard")
        self.setStyleSheet(
            "#messageCard {"
            f"  background: {COLORS['BG_HOVER']}; border: 1px solid {COLORS['TEXT_PLACEHOLDER']};"
            "  border-radius: 8px; padding: 12px;"
            "}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Icône
        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(36, 36)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 24px; background: transparent; border: none;")
        layout.addWidget(icon_lbl)

        # Texte (supporte le RichText pour gras avec ** **)
        text_lbl = QLabel(text)
        text_lbl.setWordWrap(True)
        text_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        text_lbl.setTextFormat(Qt.TextFormat.RichText)
        text_lbl.setStyleSheet(
            f"color: {COLORS['TEXT_PRIMARY']}; font-size: 13px; background: transparent; border: none;"
        )
        layout.addWidget(text_lbl, 1)


class UserMessageCard(QFrame):
    """Carte de message de l'utilisateur, alignée à gauche avec style distinct."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("userMessageCard")
        self.setStyleSheet(
            "#userMessageCard {"
            f"  background: {COLORS['BG_INPUT']}; border: 1px solid {COLORS['BORDER_CONFIG']};"
            "  border-radius: 8px; padding: 10px;"
            "}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        icon_lbl = QLabel("👤")
        icon_lbl.setFixedSize(28, 28)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 16px; background: transparent; border: none;")
        layout.addWidget(icon_lbl)

        text_lbl = QLabel(text)
        text_lbl.setWordWrap(True)
        text_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        text_lbl.setStyleSheet(
            f"color: {COLORS['TEXT_SURFACE']}; font-size: 13px; font-style: italic;"
            " background: transparent; border: none;"
        )
        layout.addWidget(text_lbl, 1)


class _SuggestionButton(QPushButton):
    """Bouton de suggestion dans la barre du bas."""

    def __init__(self, label: str, action: str, parent: QWidget | None = None) -> None:
        super().__init__(label, parent)
        self.action = action
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "QPushButton {"
            f"  background: {COLORS['BG_HOVER']}; color: {COLORS['TEXT_TERTIARY']};"
            f"  border: 1px solid {COLORS['BG_BTN_PRESSED']}; border-radius: 16px;"
            "  padding: 8px 16px; font-size: 12px;"
            "}"
            "QPushButton:hover {"
            f"  background: {COLORS['BG_BTN_DISABLED']}; border-color: {COLORS['ACCENT']}; color: {COLORS['TEXT_PRIMARY']};"
            "}"
            "QPushButton:pressed {"
            f"  background: {COLORS['BG_BTN_PRESSED']};"
            "}"
        )


# ── Bot Accueil ─────────────────────────────────────────────────


class BotAccueil(QFrame):
    """Bot Accueil — assistant conversationnel avec messages pré-formatés.

    Signaux
    -------
    page_changed : Signal(str)
        Émis pour demander la navigation vers un autre bot (1.5s après
        le message de redirection).
    """

    page_changed = Signal(str)
    assistant_request = Signal(str, str)  # action_type, query

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("botAccueil")
        self._assistant = None

        # Historique des messages (mémoire + persistance JSON)
        self._messages: list[dict] = []
        self._history_file = Path(__file__).resolve().parent.parent.parent.parent / "data" / "bot_accueil_history.json"
        self._history_file.parent.mkdir(parents=True, exist_ok=True)

        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 8)
        layout.setSpacing(0)

        # ── Zone de messages (scrollable) ──
        self._messages_widget = QWidget()
        self._messages_widget.setObjectName("messagesWidget")
        self._messages_widget.setStyleSheet("#messagesWidget { background: transparent; }")
        self._messages_layout = QVBoxLayout(self._messages_widget)
        self._messages_layout.setContentsMargins(0, 0, 0, 0)
        self._messages_layout.setSpacing(8)
        self._messages_layout.addStretch(1)  # pousse les messages vers le bas

        self._messages_area = QScrollArea()
        self._messages_area.setWidget(self._messages_widget)
        self._messages_area.setWidgetResizable(True)
        self._messages_area.setFrameShape(QFrame.Shape.NoFrame)
        self._messages_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._messages_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._messages_area.setStyleSheet("QScrollArea { background: transparent; }")

        layout.addWidget(self._messages_area, 1)

        # ── Barre de suggestions ──
        self._suggestions_bar = QWidget()
        self._suggestions_bar.setObjectName("suggestionsBar")
        self._suggestions_bar.setStyleSheet("#suggestionsBar { background: transparent; }")
        self._suggestions_layout = QHBoxLayout(self._suggestions_bar)
        self._suggestions_layout.setContentsMargins(4, 8, 4, 4)
        self._suggestions_layout.setSpacing(8)

        layout.addWidget(self._suggestions_bar, 0)

        # ── Barre de saisie ──
        self._input_bar = QWidget()
        self._input_bar.setObjectName("inputBar")
        self._input_bar.setStyleSheet("#inputBar { background: transparent; }")
        self._input_layout = QHBoxLayout(self._input_bar)
        self._input_layout.setContentsMargins(4, 4, 4, 0)
        self._input_layout.setSpacing(6)

        self._input_field = QLineEdit()
        self._input_field.setPlaceholderText("Écris ton message ici…")
        self._input_field.setStyleSheet(
            "QLineEdit {"
            f"  background: {COLORS['BG_INPUT']}; color: {COLORS['TEXT_PRIMARY']};"
            f"  border: 1px solid {COLORS['TEXT_PLACEHOLDER']}; border-radius: 12px;"
            "  padding: 8px 14px; font-size: 13px;"
            "}"
            "QLineEdit:focus {"
            f"  border-color: {COLORS['ACCENT']};"
            "}"
        )

        self._send_btn = QPushButton("Envoyer")
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setStyleSheet(
            "QPushButton {"
            f"  background: {COLORS['ACCENT']}; color: {COLORS['TEXT_WHITE']};"
            "  border: none; border-radius: 12px;"
            "  padding: 8px 18px; font-size: 13px;"
            "}"
            "QPushButton:hover {"
            f"  background: {COLORS['ACCENT_HOVER']};"
            "}"
            "QPushButton:pressed {"
            f"  background: {COLORS['ACCENT_HOVER']};"
            "}"
            "QPushButton:disabled {"
            f"  background: {COLORS['TEXT_PLACEHOLDER']}; color: {COLORS['TEXT_DISABLED']};"
            "}"
        )

        self._input_layout.addWidget(self._input_field, 1)
        self._input_layout.addWidget(self._send_btn, 0)

        # Bouton "Vider le chat" (toujours visible, pas dépendant des suggestions)
        self._clear_chat_btn = QPushButton("🗑️ Vider")
        self._clear_chat_btn.setToolTip("Effacer toute la conversation")
        self._clear_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_chat_btn.setStyleSheet(
            "QPushButton {"
            f"  background: transparent; color: {COLORS['TEXT_MUTED']};"
            f"  border: 1px solid {COLORS['TEXT_PLACEHOLDER']}; border-radius: 12px;"
            "  padding: 8px 10px; font-size: 12px;"
            "}"
            "QPushButton:hover {"
            f"  background: {COLORS['BG_HOVER']}; color: {COLORS['TEXT_PRIMARY']}; border-color: {COLORS['DANGER_BTN']};"
            "}"
        )
        self._clear_chat_btn.clicked.connect(self._on_clear_history)
        self._input_layout.addWidget(self._clear_chat_btn, 0)

        layout.addWidget(self._input_bar, 0)

        # ── Connexion des signaux ──
        self._input_field.returnPressed.connect(self._on_user_input)
        self._send_btn.clicked.connect(self._on_user_input)

        # ── Démarrer avec un chat frais (init) ──
        # On ne restaure PAS l'historique au démarrage — le chat repart à zéro.
        # L'historique est quand même sauvegardé (via add_message) et accessible
        # via le bouton "📜 Restaurer" dans les suggestions si un historique existe.
        self._show_welcome()

    # ── Affichage des messages ──────────────────────────────────

    def add_message(
        self,
        icon: str,
        text: str,
        suggestions: list[dict[str, str]] | None = None,
    ) -> None:
        """Ajoute un message du bot dans le chat.

        Paramètres
        ----------
        icon : str
            Emoji ou icône à afficher dans la carte.
        text : str
            Texte du message (support RichText de base).
        suggestions : list[dict] | None
            Liste de boutons à afficher après le message.
            Chaque dict a les clés ``label`` et ``action``.
        """
        card = MessageCard(icon, text)
        # Insérer avant le stretch (dernier élément du layout)
        self._messages_layout.insertWidget(
            self._messages_layout.count() - 1,
            card,
        )

        # Sauvegarder dans l'historique mémoire
        self._messages.append(
            {
                "type": "bot",
                "icon": icon,
                "text": text,
                "suggestions": suggestions,
                "timestamp": datetime.now().isoformat(),
            }
        )
        self._save_history()

        if suggestions is not None:
            self.set_suggestions(suggestions)

        # Auto-scroll vers le bas
        QTimer.singleShot(50, self._scroll_to_bottom)

    def set_suggestions(self, suggestions: list[dict[str, str]]) -> None:
        """Remplace les boutons de suggestion dans la barre du bas."""
        self._clear_suggestions()
        for btn_data in suggestions:
            btn = _SuggestionButton(btn_data["label"], btn_data["action"])
            btn.clicked.connect(lambda checked=False, a=btn_data["action"]: self._on_suggestion(a))
            self._suggestions_layout.addWidget(btn)
        self._suggestions_layout.addStretch(1)

    def _clear_suggestions(self) -> None:
        """Vide la barre de suggestions."""
        while self._suggestions_layout.count():
            item = self._suggestions_layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

    def _scroll_to_bottom(self) -> None:
        """Défile la zone de messages vers le bas."""
        scrollbar = self._messages_area.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    # ── Messages utilisateur ────────────────────────────────────

    def add_user_message(self, text: str) -> None:
        """Ajoute un message de l'utilisateur dans le chat."""
        card = UserMessageCard(text)
        self._messages_layout.insertWidget(
            self._messages_layout.count() - 1,
            card,
        )
        self._messages.append(
            {
                "type": "user",
                "text": text,
                "timestamp": datetime.now().isoformat(),
            }
        )
        self._save_history()
        QTimer.singleShot(50, self._scroll_to_bottom)

    # ── Moteur de matching d'intention ───────────────────────────

    def _match_intent(self, text: str) -> str | None:
        """Trouve l'intention la mieux correspondant au texte utilisateur.

        Retourne l'ID de l'entrée KNOWLEDGE correspondante, ou None
        si le score est trop bas (fallback).
        """
        if not text.strip():
            return None

        text_lower = text.lower().strip()
        words = [w for w in text_lower.split() if len(w) >= 3]

        best_match = None
        best_score = 0

        for entry_id, entry in KNOWLEDGE.items():
            keywords = entry.get("keywords", [])
            if not keywords:
                continue
            score = 0
            for keyword in keywords:
                kw = keyword.lower()
                # Match exact de mot-clé dans le texte
                if kw in text_lower:
                    score += 3
                # Match de mot individuel
                for word in words:
                    if word == kw or (len(word) >= 3 and (word.startswith(kw) or kw.startswith(word))):
                        score += 1
                        break

            if score > best_score:
                best_score = score
                best_match = entry_id

        return best_match if best_score >= 3 else None

    # ── Exécuteur d'actions (combo) ──────────────────────────────

    def _execute_actions(self, actions: list[dict]) -> None:
        """Exécute une séquence d'actions (combo actions)."""
        if not actions:
            return

        def _run_step(index: int) -> None:
            if index >= len(actions):
                return
            action = actions[index]
            atype = action.get("type", "")

            if atype == "message":
                self.add_message(
                    action.get("icon", "💬"),
                    action.get("text", ""),
                    action.get("suggestions"),
                )
                QTimer.singleShot(400, lambda: _run_step(index + 1))

            elif atype == "navigate":
                bot = action.get("bot", "")
                if bot == "Assistant":
                    self.assistant_request.emit("config", action.get("query", "Configuration"))
                else:
                    self.navigate_to(bot, action.get("icon", "➡️"))

            elif atype == "delay":
                QTimer.singleShot(
                    action.get("ms", 500),
                    lambda idx=index: _run_step(idx + 1),
                )

            elif atype == "suggestions":
                self.set_suggestions(action.get("items", []))
                QTimer.singleShot(100, lambda: _run_step(index + 1))

            else:
                _run_step(index + 1)

        _run_step(0)

    def setup_assistant(self, assistant: BotAssistant) -> None:
        """Stocke la référence vers BotAssistant et connecte les signaux."""
        self._assistant = assistant
        self.assistant_request.connect(assistant._on_assistant_request)
        assistant.assistant_response.connect(self._on_assistant_response)

    def _on_assistant_response(self, response_json: str) -> None:
        """Reçoit la réponse JSON de l'assistant, la décode et l'affiche."""
        try:
            data = json.loads(response_json)
        except Exception:
            self.add_message("❌", "Réponse JSON invalide de l'assistant.", None)
            return

        severity = data.get("severity", "info")
        message = data.get("message")
        if not message:
            message = "Pas de message de la part de l'assistant."

        icon = "✅" if severity in ("info", "success") else "❌"

        # Traiter les suggestions
        suggestions_raw = data.get("suggestions", [])
        suggestions = None
        if suggestions_raw:
            suggestions = []
            for sug in suggestions_raw:
                label = sug.get("label", "")
                action = sug.get("action", "")
                
                # Conversion des actions
                if action == "navigate":
                    bot = sug.get("bot", "")
                    action_mapped = f"go_{bot.lower()}"
                elif action == "open_config":
                    action_mapped = "config"
                else:
                    action_mapped = action
                    
                suggestions.append({
                    "label": label,
                    "action": action_mapped
                })

        self.add_message(icon, message, suggestions)

        # Naviguer si demandé
        navigation = data.get("navigation")
        if navigation:
            bot = navigation.get("bot", "")
            icon_nav = navigation.get("icon", "➡️")
            QTimer.singleShot(1500, lambda: self.navigate_to(bot, icon_nav))

    def _detect_assistant_action(self, query: str) -> str:
        """Détecte le type d'action pour l'Assistant à partir de la requête."""
        q = query.lower()
        tuto_keywords = ["planifier", "programmer", "automatique", "optimiser", "guide", "tuto", "comment", "nettoyer"]
        diag_keywords = ["problème", "erreur", "impossible", "lent", "lenteur", "plante", "bug", "crash", "panne", "connexion", "transfert", "performance", "mémoire", "cpu"]
        config_keywords = ["configurer", "changer", "modifier", "paramètre", "port", "écoute", "partage", "dossier", "description", "profil", "bio", "destination", "sauvegarde"]

        if any(w in q for w in tuto_keywords):
            return "tutorial"
        if any(w in q for w in diag_keywords):
            return "diagnostic"
        if any(w in q for w in config_keywords):
            return "config"
        return "recommendation"

    # ── Handler de saisie utilisateur ────────────────────────────

    def _on_user_input(self) -> None:
        """Handler appelé quand l'utilisateur envoie un message."""
        text = self._input_field.text().strip()
        if not text:
            return

        # Afficher le message utilisateur
        self.add_user_message(text)

        # Vider le champ
        self._input_field.clear()

        # Matcher l'intention
        intent_id = self._match_intent(text)

        _INTENT_TO_ACTION = {
            "assistant": "config",
            "config": "config",
            "diagnostic": "diagnostic",
            "recommendation": "recommendation",
            "tutorial": "tutorial",
        }

        # Si l'intention correspond à un type Assistant ou si _detect_assistant_action l'indique
        action_type = None
        if intent_id in _INTENT_TO_ACTION:
            action_type = _INTENT_TO_ACTION[intent_id]
        else:
            detected = self._detect_assistant_action(text)
            if detected in ("config", "diagnostic", "tutorial"):
                action_type = detected

        if action_type is not None:
            self.assistant_request.emit(action_type, text)
            return

        if intent_id and intent_id in KNOWLEDGE:
            entry = KNOWLEDGE[intent_id]
            self.add_message(
                entry.get("icon", "💬"),
                entry.get("response", ""),
                entry.get("suggestions"),
            )
            actions = entry.get("actions", [])
            if actions:
                QTimer.singleShot(600, lambda: self._execute_actions(actions))
        else:
            # Fallback — pas de match
            self.add_message(
                "🤔",
                "Je n'ai pas bien compris ta demande. "
                "Peux-tu reformuler ?<br><br>"
                "Tu peux aussi utiliser les suggestions ci-dessous "
                "pour me guider !",
                [
                    {"label": "🔍 Chercher", "action": "search"},
                    {"label": "📥 Téléchargements", "action": "downloads"},
                    {"label": "❓ Aide", "action": "help"},
                    {"label": "🎯 À propos", "action": "about"},
                    {"label": "🏠 Accueil", "action": "welcome"},
                ],
            )

    # ── Persistance de l'historique ─────────────────────────

    def _check_history_exists(self) -> None:
        """Vérifie si un fichier d'historique non vide existe."""
        self._has_history = self._history_file.exists() and self._history_file.stat().st_size > 10

    def _restore_history(self) -> None:
        """Restaure la conversation précédente depuis le fichier JSON.

        Lit le fichier AVANT de vider l'écran (pour ne pas perdre les données).
        """
        # 1. Lire l'historique depuis le fichier d'abord
        messages: list[dict] = []
        try:
            data = json.loads(self._history_file.read_text(encoding="utf-8"))
            messages = data.get("messages", [])
        except (json.JSONDecodeError, KeyError, OSError):
            messages = []

        if not messages:
            self._show_welcome()
            return

        # 2. Vider l'écran (sans sauvegarder le vide)
        self._messages = []
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

        # 3. Restaurer les messages
        self._messages = messages
        for msg in self._messages:
            if msg.get("type") == "bot":
                card = MessageCard(msg["icon"], msg["text"])
                self._messages_layout.insertWidget(
                    self._messages_layout.count() - 1,
                    card,
                )
            elif msg.get("type") == "user":
                card = UserMessageCard(msg["text"])
                self._messages_layout.insertWidget(
                    self._messages_layout.count() - 1,
                    card,
                )

        # 4. Restaurer les suggestions du dernier message
        last_msg = self._messages[-1]
        suggestions = last_msg.get("suggestions")
        if suggestions is not None:
            self.set_suggestions(suggestions)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _save_history(self) -> None:
        """Sauvegarde l'historique des messages dans le fichier JSON."""
        try:
            self._history_file.write_text(
                json.dumps({"messages": self._messages}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    def clear_history(self) -> None:
        """Efface l'historique, vide les messages et revient au message de bienvenue."""
        self._messages = []
        # Supprimer tous les widgets messages (sauf le stretch)
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
        self._save_history()
        self._show_welcome()

    # ── Navigation vers un autre bot ────────────────────────────

    def navigate_to(self, bot_name: str, icon: str = "➡️") -> None:
        """Affiche un message de redirection puis change de page après 1.5 s.

        Paramètres
        ----------
        bot_name : str
            Nom exact du bot cible (ex. ``\"Recherche\"``, ``\"Aide\"``).
        icon : str
            Emoji représentant le bot cible.
        """
        self.add_message(
            icon,
            f"Je t'emmène vers le bot <b>{bot_name}</b> … 🔄",
            None,
        )
        # Désactiver les suggestions pendant la redirection
        self._clear_suggestions()
        QTimer.singleShot(1500, lambda: self.page_changed.emit(bot_name))

    # ── Dialogues pré-formatés ──────────────────────────────────

    def _show_welcome(self) -> None:
        """Affiche le message de bienvenue de Zeus."""
        suggestions = [
            {"label": "🔍 Chercher un fichier", "action": "search"},
            {"label": "📥 Téléchargements", "action": "downloads"},
            {"label": "❓ Aide & explications", "action": "help"},
        ]
        # Ajouter le bouton "Restaurer" si un historique existe
        self._check_history_exists()
        if self._has_history:
            suggestions.append({"label": "📜 Conversation précédente", "action": "restore_history"})

        self.add_message(
            "👑",
            "Salut ! Je suis <b>Zeus</b>, le roi de l'Olympe et ton assistant personnel "
            "sur Soulseek.<br><br>"
            "Je suis là pour t'aider à utiliser l'appli, trouver des fichiers, "
            "gérer tes téléchargements, et te guider vers le bon dieu selon "
            "tes besoins.<br><br>"
            "Que veux-tu faire ?",
            suggestions,
        )

    def _show_about(self) -> None:
        """Affiche la description de l'Armée des 12 Bots."""
        self.add_message(
            "🎯",
            "<b>Le Panthéon des 12 Bots</b> est composé de :<br><br>"
            "👑 <b>Zeus</b> — Accueil & hub central<br>"
            "🔍 <b>Athéna</b> — Chercher des fichiers sur Soulseek<br>"
            "📥 <b>Hadès</b> — Gérer les téléchargements<br>"
            "📚 <b>Déméter</b> — Explorer la bibliothèque partagée<br>"
            "👥 <b>Arès</b> — Suivre les clients actifs<br>"
            "📋 <b>Aphrodite</b> — Souhaits automatiques<br>"
            "🛡️ <b>Artémis</b> — Surveillance et alertes<br>"
            "📅 <b>Apollon</b> — Planification et automatisation<br>"
            "🧹 <b>Poséidon</b> — Organiser et classer les fichiers<br>"
            "🔧 <b>Héphaistos</b> — Optimiser les profils<br>"
            "⚙️ <b>Héra</b> — Configuration assistée<br>"
            "❓ <b>Dionysos</b> — Guide et documentation<br><br>"
            "Et moi, <b>Zeus</b>, je suis ton point d'entrée ! 👑",
            [
                {"label": "🔍 Chercher", "action": "search"},
                {"label": "❓ Aide", "action": "help"},
                {"label": "🏠 Accueil", "action": "welcome"},
            ],
        )

    # ── Routeur d'actions ───────────────────────────────────────

    def _on_clear_history(self) -> None:
        """Efface l'historique et revient au message de bienvenue."""
        self.clear_history()

    def _on_restore_history(self) -> None:
        """Restaure la conversation précédente."""
        self._restore_history()

    def _on_suggestion(self, action: str) -> None:
        """Route une action utilisateur vers le dialogue ou la redirection appropriée."""
        route: dict[str, Callable[[], None]] = {
            "welcome": self._show_welcome,
            "search": lambda: self.navigate_to("Recherche", "🔍"),
            "downloads": lambda: self.navigate_to("Téléchargement", "📥"),
            "library": lambda: self.navigate_to("Bibliothèque", "📚"),
            "users": lambda: self.navigate_to("Utilisateurs", "👤"),
            "wishlist": lambda: self.navigate_to("Wishlist", "📋"),
            "surveillance": lambda: self.navigate_to("Surveillance", "👁️"),
            "planificateur": lambda: self.navigate_to("Planificateur", "📅"),
            "ordonnanceur": lambda: self.navigate_to("Ordonnanceur", "🧹"),
            "stats": lambda: self.navigate_to("Statistiques", "📊"),
            "config": lambda: (self.assistant_request.emit("config", "Configuration") if self._assistant is not None else self.navigate_to("Assistant", "⚙️")),
            "help": lambda: self.navigate_to("Aide", "❓"),
            "about": self._show_about,
            "clear_history": self._on_clear_history,
            "restore_history": self._on_restore_history,
        }
        handler = route.get(action, self._show_welcome)
        handler()
