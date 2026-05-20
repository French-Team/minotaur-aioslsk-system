"""Bot Assistant — assistant du BotAccueil (configuration, diagnostic, recommandations).

Ce module définit la classe BotAssistant qui travaille en coulisses pour
aider BotAccueil à traiter les demandes de l'utilisateur. Il utilise une
base SQLite dédiée pour persister ses interactions et diagnostics.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

logger = logging.getLogger(__name__)

# ── Constantes ──────────────────────────────────────────────────────────

_VALID_ACTION_TYPES = frozenset({"config", "diagnostic", "recommendation", "tutorial"})

_CONFIG_RULES: list[tuple[list[str], str, str]] = [
    (["port", "écoute", "réseau"], "reseau", "port_ecoute"),
    (["partage", "dossier", "partager"], "partages", "dossier_1_chemin"),
    (["destination", "sauvegarde", "téléchargement"], "telechargement", "dossier_destination"),
    (["description", "profil", "bio"], "general", "description_profil"),
]

_DIAGNOSTIC_RULES: list[tuple[list[str], str]] = [
    (["connect", "impossible", "erreur", "timeout"], "connexion"),
    (["lent", "ralentir", "vitesse"], "transfert"),
    (["partag", "dossier", "fichier"], "partage"),
    (["performance", "mémoire", "cpu"], "performance"),
]

_RECOMMENDATION_RULES: list[tuple[list[str], str, str]] = [
    (["chercher", "recherche", "trouver"], "Recherche", "🔍"),
    (["télécharger", "download", "recevoir"], "Téléchargement", "📥"),
    (["bibliothèque", "partagé"], "Bibliothèque", "📚"),
    (["souhait", "wishlist", "attendre"], "Wishlist", "📋"),
]

_TUTORIAL_RULES: list[tuple[list[str], str]] = [
    (["planifier", "programmer", "automatique"], "planifier-tache-programmee"),
    (["optimiser", "vitesse", "performance"], "optimiser-telechargements"),
]


class BotAssistant(QFrame):
    """Assistant du bot Accueil — configuration, diagnostic, recommandations.

    Travaille en coulisses : ses réponses sont affichées via le chat de
    BotAccueil, jamais directement à l'utilisateur. Maintient une base
    SQLite dédiée (``data/bot_assistant.db``) pour l'historique.
    """

    assistant_response = Signal(str)  # Réponse JSON vers BotAccueil

    # ── Constructeur ────────────────────────────────────────────────────

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Chemin de la base SQLite
        self._db_path = str(Path(__file__).parent.parent.parent.parent / "data" / "bot_assistant.db")

        # Initialiser la base
        self._init_database()

        # Dashboard (construit dans _build_dashboard)
        self._stats_labels: dict[str, QLabel] = {}
        self._activity_list: QListWidget | None = None

        self._build_dashboard()

    # ── Méthode setup ───────────────────────────────────────────────────

    def setup(self, bot_accueil: Any) -> None:
        """Connecte le bot Assistant à BotAccueil via Signal/Slot direct."""
        # BotAccueil → Assistant
        bot_accueil.assistant_request.connect(self._on_assistant_request)  # type: ignore[attr-defined]
        # Assistant → BotAccueil
        self.assistant_response.connect(bot_accueil._on_assistant_response)  # type: ignore[attr-defined]

    # ── Base de données SQLite ──────────────────────────────────────────

    def _init_database(self) -> None:
        """Crée les tables ``interactions`` et ``diagnostics`` si elles n'existent pas.

        Appelable plusieurs fois sans risque (idempotent grâce à
        ``CREATE TABLE IF NOT EXISTS``).
        """
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT    NOT NULL
                                        CHECK(action_type IN ('config','diagnostic','recommendation','tutorial')),
                    query       TEXT    NOT NULL,
                    response    TEXT    NOT NULL,
                    success     INTEGER NOT NULL DEFAULT 1,
                    error_message TEXT,
                    created_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS diagnostics (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    check_type  TEXT    NOT NULL,
                    status      TEXT    NOT NULL,
                    message     TEXT    NOT NULL,
                    suggestion  TEXT,
                    checked_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _log_interaction(
        self,
        action_type: str,
        query: str,
        response: str,
        success: bool,
        error_message: str | None = None,
    ) -> None:
        """Enregistre une interaction dans la table ``interactions``."""
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                "INSERT INTO interactions (action_type, query, response, success, error_message) "
                "VALUES (?, ?, ?, ?, ?)",
                (action_type, query, response, 1 if success else 0, error_message),
            )
            conn.commit()
        finally:
            conn.close()

    def _log_diagnostic(
        self,
        check_type: str,
        status: str,
        message: str,
        suggestion: str | None = None,
    ) -> None:
        """Enregistre un résultat de diagnostic dans la table ``diagnostics``."""
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                "INSERT INTO diagnostics (check_type, status, message, suggestion) "
                "VALUES (?, ?, ?, ?)",
                (check_type, status, message, suggestion),
            )
            conn.commit()
        finally:
            conn.close()

    def _get_interactions(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retourne les dernières interactions, triées par ``id`` décroissant.

        Args:
            limit: Nombre maximum d'interactions à retourner.

        Returns:
            Liste de dictionnaires représentant chaque interaction, ou liste
            vide si la base est vide.
        """
        conn = sqlite3.connect(self._db_path)
        try:
            rows = conn.execute(
                "SELECT id, action_type, query, response, success, error_message, created_at "
                "FROM interactions ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [
                {
                    "id": row[0],
                    "action_type": row[1],
                    "query": row[2],
                    "response": row[3],
                    "success": bool(row[4]),
                    "error_message": row[5],
                    "created_at": row[6],
                }
                for row in rows
            ]
        finally:
            conn.close()

    def _get_last_diagnostic(self) -> dict[str, Any] | None:
        """Retourne le diagnostic le plus récent, ou ``None`` s'il n'y en a aucun."""
        conn = sqlite3.connect(self._db_path)
        try:
            row = conn.execute(
                "SELECT id, check_type, status, message, suggestion, checked_at "
                "FROM diagnostics ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            return {
                "id": row[0],
                "check_type": row[1],
                "status": row[2],
                "message": row[3],
                "suggestion": row[4],
                "checked_at": row[5],
            }
        finally:
            conn.close()

    def _get_stats(self) -> dict[str, int]:
        """Retourne les statistiques globales (interactions et diagnostics).

        Returns:
            Dictionnaire avec les clés ``total_interactions``, ``successful``,
            ``failed`` et ``total_diagnostics``.
        """
        conn = sqlite3.connect(self._db_path)
        try:
            total_interactions = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
            successful = conn.execute("SELECT COUNT(*) FROM interactions WHERE success = 1").fetchone()[0]
            failed = conn.execute("SELECT COUNT(*) FROM interactions WHERE success = 0").fetchone()[0]
            total_diagnostics = conn.execute("SELECT COUNT(*) FROM diagnostics").fetchone()[0]
            return {
                "total_interactions": total_interactions,
                "successful": successful,
                "failed": failed,
                "total_diagnostics": total_diagnostics,
            }
        finally:
            conn.close()

    # ── Dashboard ───────────────────────────────────────────────────────

    def _build_dashboard(self) -> None:
        """Construit l'interface du dashboard de la page Assistant."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Titre
        title = QLabel("🤖 Assistant — Activité en coulisses")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        # ── Stats ──
        stats_container = QFrame()
        stats_container.setStyleSheet(
            "QFrame { background: #2d2d2d; border-radius: 8px; padding: 12px; }"
        )
        stats_layout = QHBoxLayout(stats_container)

        self._stats_labels["total_interactions"] = QLabel("💬 0 interactions")
        self._stats_labels["total_diagnostics"] = QLabel("⚡ 0 diagnostics")
        self._stats_labels["successful"] = QLabel("✅ 0 succès")
        self._stats_labels["failed"] = QLabel("❌ 0 échecs")

        for label in self._stats_labels.values():
            label.setStyleSheet("font-size: 14px; padding: 0 8px;")
            stats_layout.addWidget(label)

        layout.addWidget(stats_container)

        # ── Flux temps réel ──
        activity_label = QLabel("Flux temps réel")
        activity_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 16px;")
        layout.addWidget(activity_label)

        self._activity_list = QListWidget()
        self._activity_list.setStyleSheet(
            "QListWidget { background: #252525; border: 1px solid #3a3a3a; border-radius: 6px; }"
            "QListWidget::item { padding: 6px 10px; border-bottom: 1px solid #333; }"
        )
        layout.addWidget(self._activity_list)

        # ── Dernier diagnostic ──
        diag_label = QLabel("Dernier diagnostic")
        diag_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 8px;")
        layout.addWidget(diag_label)

        self._last_diag_label = QLabel("Aucun diagnostic pour l'instant.")
        self._last_diag_label.setStyleSheet(
            "QLabel { background: #2d2d2d; border-radius: 6px; padding: 12px; font-size: 13px; }"
        )
        self._last_diag_label.setWordWrap(True)
        layout.addWidget(self._last_diag_label)

        # ── Bouton Rafraîchir ──
        refresh_btn = QPushButton("🔄 Rafraîchir")
        refresh_btn.setStyleSheet(
            "QPushButton { background: #3a7bd5; color: white; border: none; "
            "border-radius: 6px; padding: 8px 16px; font-size: 13px; }"
            "QPushButton:hover { background: #4a8be5; }"
        )
        refresh_btn.clicked.connect(self._update_stats)
        layout.addWidget(refresh_btn)

        layout.addStretch()

        # Chargement initial
        self._update_stats()

    def _update_stats(self) -> None:
        """Met à jour les labels de stats et la liste d'activité depuis SQLite."""
        stats = self._get_stats()
        self._stats_labels["total_interactions"].setText(f"💬 {stats['total_interactions']} interactions")
        self._stats_labels["total_diagnostics"].setText(f"⚡ {stats['total_diagnostics']} diagnostics")
        self._stats_labels["successful"].setText(f"✅ {stats['successful']} succès")
        self._stats_labels["failed"].setText(f"❌ {stats['failed']} échecs")

        # Dernier diagnostic
        last = self._get_last_diagnostic()
        if last:
            self._last_diag_label.setText(
                f"{last['check_type']} : {'✅' if last['status'] == 'ok' else '⚠️' if last['status'] == 'warning' else '❌'} "
                f"{last['message']}"
            )
        else:
            self._last_diag_label.setText("Aucun diagnostic pour l'instant.")

    def _add_activity_entry(self, action_type: str, status: str, message: str) -> None:
        """Ajoute une entrée dans le flux temps réel du dashboard."""
        if self._activity_list is None:
            return
        item = QListWidgetItem(f"  {status}  {action_type} — {message}")
        self._activity_list.insertItem(0, item)
        if self._activity_list.count() > 100:
            self._activity_list.takeItem(self._activity_list.count() - 1)

    # ── Traitement des requêtes ─────────────────────────────────────────

    def _on_assistant_request(self, action_type: str, query: str) -> None:
        """Reçoit une requête de BotAccueil et retourne une réponse structurée.

        Valide le type d'action, route vers le handler correspondant, émet
        la réponse via ``assistant_response`` et persiste l'interaction
        dans SQLite. Toute erreur interne est catchée et convertie en
        réponse d'erreur.
        """
        try:
            # 1. Valider le type d'action
            if action_type not in _VALID_ACTION_TYPES:
                raise ValueError(f"Type d'action invalide : {action_type!r}")

            # 2. Router vers le bon handler
            router = {
                "config": self._handle_config,
                "diagnostic": self._handle_diagnostic,
                "recommendation": self._handle_recommendation,
                "tutorial": self._handle_tutorial,
            }
            handler = router[action_type]
            response = handler(query)

            # 3. Émettre la réponse
            response_json = json.dumps(response, ensure_ascii=False)
            self.assistant_response.emit(response_json)

            # 4. Persister
            self._log_interaction(action_type, query, response_json, success=True)

            # 5. Mettre à jour le dashboard si visible
            if self.isVisible():
                status = "✅" if response["severity"] != "error" else "❌"
                self._add_activity_entry(action_type, status, response["message"][:60])

        except Exception as exc:
            logger.error("Assistant error: %s", exc)
            error_response = {
                "message": "Une erreur est survenue. Consulte le bot <b>Aide</b>.",
                "severity": "error",
                "suggestions": [{"label": "❓ Consulter l'Aide", "action": "navigate", "bot": "Aide"}],
                "data": {"error": str(exc)},
            }
            error_json = json.dumps(error_response, ensure_ascii=False)
            self.assistant_response.emit(error_json)
            safe_type = action_type if action_type in _VALID_ACTION_TYPES else "config"
            self._log_interaction(safe_type, query, error_json, success=False, error_message=str(exc))

    # ── Handlers ────────────────────────────────────────────────────────

    def _handle_config(self, query: str) -> dict[str, Any]:
        """Gère une requête de type 'config'.

        Utilise ``_match_config()`` pour identifier la section concernée
        et retourne une réponse structurée avec les suggestions appropriées.
        """
        match = self._match_config(query)
        if match is not None:
            section, key = match
            config_messages = {
                "reseau": {
                    "port_ecoute": "Le <b>port d'écoute</b> est configurable dans les paramètres Réseau. "
                                   "Le port par défaut est <b>60000</b>.",
                },
                "partages": {
                    "dossier_1_chemin": "Les <b>dossiers partagés</b> se configurent dans la page Bibliothèque. "
                                        "Tu peux ajouter ou retirer des dossiers à partager.",
                },
                "telechargement": {
                    "dossier_destination": "Le <b>dossier de destination</b> des téléchargements se configure "
                                          "dans les paramètres de téléchargement.",
                },
                "general": {
                    "description_profil": "Ta <b>description de profil</b> se modifie dans les paramètres "
                                         "généraux de l'application.",
                },
            }
            section_msgs = config_messages.get(section, {})
            msg = section_msgs.get(key, "Cette configuration est accessible depuis les paramètres.")
            return {
                "message": msg,
                "severity": "info",
                "suggestions": [
                    {"label": "⚙️ Ouvrir la Configuration", "action": "navigate", "bot": "Assistant"},
                    {"label": "📖 Voir le guide complet", "action": "navigate", "bot": "Aide"},
                ],
                "data": {"section": section, "key": key},
            }
        return {
            "message": "Désolé, je n'ai pas compris ta demande de configuration. "
                       "Tu peux reformuler ou consulter le bot <b>Aide</b> pour plus d'informations.",
            "severity": "warning",
            "suggestions": [
                {"label": "❓ Consulter l'Aide", "action": "navigate", "bot": "Aide"},
            ],
            "data": {"error": "unknown_config", "query": query},
        }

    def _handle_diagnostic(self, query: str) -> dict[str, Any]:
        """Gère une requête de type 'diagnostic'.

        Utilise ``_match_diagnostic()`` pour identifier le type de
        problème et retourne un diagnostic structuré.
        """
        check_type = self._match_diagnostic(query)
        app_state = self._get_app_state()

        if check_type == "connexion":
            if app_state.get("is_connected", False):
                msg = "✅ La connexion au serveur Soulseek est active."
                severity = "success"
            else:
                msg = "❌ Tu n'es <b>pas connecté</b> au serveur Soulseek. " \
                      "Vérifie tes paramètres réseau et essaie de te connecter."
                severity = "error"
            return {
                "message": msg,
                "severity": severity,
                "suggestions": [
                    {"label": "🔌 Voir l'état de la connexion", "action": "navigate", "bot": "Réseau"},
                    {"label": "📖 Guide de connexion", "action": "navigate", "bot": "Aide"},
                ],
                "data": {"type": "connexion", **app_state},
            }

        if check_type == "transfert":
            return {
                "message": "Les performances des transferts peuvent être influencées par "
                           "plusieurs facteurs : vitesse du réseau, paramètres de limite, "
                           "nombre de sources. Tu peux vérifier tes téléchargements dans "
                           "la page <b>Téléchargement</b>.",
                "severity": "info",
                "suggestions": [
                    {"label": "📥 Voir les téléchargements", "action": "navigate", "bot": "Téléchargement"},
                    {"label": "⚙️ Configurer les limites", "action": "navigate", "bot": "Assistant"},
                ],
                "data": {"type": "transfert"},
            }

        if check_type == "partage":
            return {
                "message": "Tes <b>dossiers partagés</b> sont visibles dans la page "
                           "Bibliothèque. Vérifie que les dossiers sont bien accessibles "
                           "et contiennent des fichiers.",
                "severity": "info",
                "suggestions": [
                    {"label": "📚 Voir la Bibliothèque", "action": "navigate", "bot": "Bibliothèque"},
                ],
                "data": {"type": "partage"},
            }

        if check_type == "performance":
            return {
                "message": "L'utilisation des ressources (mémoire, CPU) dépend du nombre "
                           "de fichiers partagés et de l'activité réseau. "
                           "Tu peux surveiller l'activité dans la page <b>Surveillance</b>.",
                "severity": "info",
                "suggestions": [
                    {"label": "📊 Voir la Surveillance", "action": "navigate", "bot": "Surveillance"},
                ],
                "data": {"type": "performance"},
            }

        return {
            "message": "Je n'ai pas pu identifier le problème. "
                       "Tu peux consulter la page <b>Surveillance</b> pour voir les événements récents.",
            "severity": "warning",
            "suggestions": [
                {"label": "📊 Voir la Surveillance", "action": "navigate", "bot": "Surveillance"},
                {"label": "❓ Consulter l'Aide", "action": "navigate", "bot": "Aide"},
            ],
            "data": {"error": "unknown_diagnostic", "query": query},
        }

    def _handle_recommendation(self, query: str) -> dict[str, Any]:
        """Gère une requête de type 'recommendation'.

        Utilise ``_match_recommendation()`` pour identifier le bot
        recommandé et retourne une réponse avec navigation.
        """
        match = self._match_recommendation(query)
        if match is not None:
            bot_name, icon = match
            rec_messages = {
                "Recherche": f"{icon} Pour <b>chercher des fichiers</b>, utilise la page Recherche. "
                            "Tu peux lancer des recherches par mots-clés et filtrer les résultats.",
                "Téléchargement": f"{icon} Pour <b>gérer tes téléchargements</b>, "
                                 "rends-toi dans la page Téléchargement. "
                                 "Tu y verras la file d'attente et les transferts en cours.",
                "Bibliothèque": f"{icon} Ta <b>bibliothèque</b> liste tous les fichiers "
                              "que tu partages. Ajoute ou retire des dossiers depuis cette page.",
                "Wishlist": f"{icon} La <b>wishlist</b> te permet de suivre les fichiers "
                          "que tu souhaites télécharger plus tard.",
            }
            msg = rec_messages.get(bot_name, f"{icon} Je te recommande d'utiliser le bot <b>{bot_name}</b>.")
            return {
                "message": msg,
                "severity": "info",
                "suggestions": [
                    {"label": f"{icon} Aller dans {bot_name}", "action": "navigate", "bot": bot_name},
                ],
                "navigation": {"bot": bot_name, "icon": icon},
                "data": {"bot": bot_name, "icon": icon},
            }
        return {
            "message": "Je n'ai pas de recommandation spécifique pour ta demande. "
                       "Tu peux consulter le bot <b>Aide</b> pour découvrir tous les bots disponibles.",
            "severity": "warning",
            "suggestions": [
                {"label": "❓ Consulter l'Aide", "action": "navigate", "bot": "Aide"},
            ],
            "data": {"error": "unknown_recommendation", "query": query},
        }

    def _handle_tutorial(self, query: str) -> dict[str, Any]:
        """Gère une requête de type 'tutorial'.

        Utilise ``_match_tutorial()`` pour identifier le tutoriel
        demandé et retourne les instructions pas à pas.
        """
        tutorial_id = self._match_tutorial(query)
        if tutorial_id is not None:
            tutorial_messages = {
                "planifier-tache-programmee": (
                    "📅 <b>Planifier un téléchargement automatique :</b><br>"
                    "1. Va dans la page <b>Wishlist</b><br>"
                    "2. Ajoute les fichiers souhaités<br>"
                    "3. Configure les paramètres de planification<br>"
                    "4. Active la surveillance automatique"
                ),
                "optimiser-telechargements": (
                    "⚡ <b>Optimiser les téléchargements :</b><br>"
                    "1. Vérifie tes limites de vitesse dans les paramètres Réseau<br>"
                    "2. Augmente le nombre de sources autorisées<br>"
                    "3. Utilise la fonction de priorisation<br>"
                    "4. Surveille les transferts dans la page Téléchargement"
                ),
            }
            msg = tutorial_messages.get(
                tutorial_id,
                f"Le tutoriel demandé est disponible dans le bot <b>Aide</b>.",
            )
            return {
                "message": msg,
                "severity": "info",
                "suggestions": [
                    {"label": "📖 Plus de tutoriels", "action": "navigate", "bot": "Aide"},
                ],
                "data": {"tutorial_id": tutorial_id},
            }
        return {
            "message": "Je n'ai pas de tutoriel pour cette demande. "
                       "Consulte le bot <b>Aide</b> pour voir tous les tutoriels disponibles.",
            "severity": "warning",
            "suggestions": [
                {"label": "📖 Consulter l'Aide", "action": "navigate", "bot": "Aide"},
            ],
            "data": {"error": "unknown_tutorial", "query": query},
        }

    # ── Matching interne ────────────────────────────────────────────────

    def _match_config(self, query: str) -> tuple[str, str] | None:
        """Analyse la query et retourne ``(section_config, clé_param)`` ou ``None``.

        Parcourt les règles ``_CONFIG_RULES`` et retourne la première
        correspondance de mots-clés.
        """
        q = query.lower()
        for keywords, section, key in _CONFIG_RULES:
            if any(kw in q for kw in keywords):
                return (section, key)
        return None

    def _match_diagnostic(self, query: str) -> str | None:
        """Analyse la query et retourne le type de diagnostic ou ``None``."""
        q = query.lower()
        for keywords, check_type in _DIAGNOSTIC_RULES:
            if any(kw in q for kw in keywords):
                return check_type
        return None

    def _match_recommendation(self, query: str) -> tuple[str, str] | None:
        """Analyse la query et retourne ``(bot, icon)`` ou ``None``."""
        q = query.lower()
        for keywords, bot, icon in _RECOMMENDATION_RULES:
            if any(kw in q for kw in keywords):
                return (bot, icon)
        return None

    def _match_tutorial(self, query: str) -> str | None:
        """Analyse la query et retourne l'ID du tutoriel ou ``None``."""
        q = query.lower()
        for keywords, tutorial_id in _TUTORIAL_RULES:
            if any(kw in q for kw in keywords):
                return tutorial_id
        return None

    # ── Sources de données ──────────────────────────────────────────────

    def _get_app_state(self) -> dict[str, Any]:
        """Retourne l'état actuel de l'application.

        Tente de consulter ``soulseek_service`` pour obtenir le statut
        de connexion. Si le service est injoignable, retourne un état
        dégradé.
        """
        try:
            from src.services.soulseek_client import soulseek_service
            return {
                "is_connected": soulseek_service.is_connected,
                "username": soulseek_service.username if soulseek_service.is_connected else None,
            }
        except Exception:
            logger.warning("Assistant: impossible de consulter soulseek_service")
            return {"is_connected": False, "username": None, "error": "service_inaccessible"}

    def _get_recent_logs(self, category: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        """Récupère les logs récents depuis l'EventBus. (Squelette pour étape ultérieure)"""
        raise NotImplementedError("À implémenter dans une étape ultérieure")

    def _get_possible_actions(self) -> list[dict[str, Any]]:
        """Liste les actions possibles pour les suggestions.

        Retourne le catalogue des actions que l'application peut exécuter.
        """
        return [
            {"action": "navigate", "description": "Rediriger vers un bot/page", "params": ["bot", "icon"]},
        ]
