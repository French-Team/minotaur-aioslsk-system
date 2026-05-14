"""Historique persistant des recherches du BotRecherche.

Stockage : ``data/bot_recherche_history.json``
  20 dernières recherches conservées.
  Une recherche dupliquée (même query + type + username) remonte en haut.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

HISTORY_FILE = Path("data/bot_recherche_history.json")
MAX_HISTORY = 20
SUGGESTION_COUNT = 5


class SearchHistory:
    """Gestionnaire d'historique des recherches."""

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []
        self.load()

    # ── Persistance ──────────────────────────────────────────────

    def load(self) -> None:
        """Charge l'historique depuis le disque."""
        try:
            if HISTORY_FILE.exists():
                raw = HISTORY_FILE.read_text(encoding="utf-8")
                data = json.loads(raw)
                self._entries = data.get("searches", [])
                logger.info("Historique chargé : %d entrée(s)", len(self._entries))
            else:
                self._entries = []
        except Exception:
            logger.exception("Erreur lors du chargement de l'historique")
            self._entries = []

    def save(self) -> None:
        """Sauvegarde l'historique sur le disque."""
        try:
            HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {"searches": self._entries[:MAX_HISTORY]}
            HISTORY_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug("Historique sauvegardé : %d entrée(s)", len(self._entries))
        except Exception:
            logger.exception("Erreur lors de la sauvegarde de l'historique")

    # ── Accès ────────────────────────────────────────────────────

    def get_recent(self, n: int = SUGGESTION_COUNT) -> list[dict[str, Any]]:
        """Retourne les *n* dernières entrées (les plus récentes d'abord)."""
        return self._entries[:n]

    def get_all(self) -> list[dict[str, Any]]:
        """Retourne toutes les entrées (les plus récentes d'abord)."""
        return list(self._entries)

    # ── Ajout ────────────────────────────────────────────────────

    def add(
        self,
        query: str,
        type_: str = "global",
        username: str | None = None,
        count: int = 0,
    ) -> None:
        """Ajoute une entrée dans l'historique.

        Si une entrée identique existe déjà (même ``query`` + ``type_``
        + ``username``), son timestamp est mis à jour et elle remonte
        en haut de la liste.  Sinon, une nouvelle entrée est insérée
        en tête.

        Les entrées excédentaires (au-delà de ``MAX_HISTORY``) sont
        élaguées.
        """
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")

        # Chercher un doublon
        for i, entry in enumerate(self._entries):
            if (
                entry["query"] == query
                and entry.get("type") == type_
                and entry.get("username") == username
            ):
                # Mise à jour sur place
                self._entries.pop(i)
                self._entries.insert(0, {
                    "query": query,
                    "type": type_,
                    "username": username,
                    "count": count,
                    "timestamp": now,
                })
                self.save()
                return

        # Nouvelle entrée en tête
        self._entries.insert(0, {
            "query": query,
            "type": type_,
            "username": username,
            "count": count,
            "timestamp": now,
        })

        # Élagage
        if len(self._entries) > MAX_HISTORY:
            self._entries = self._entries[:MAX_HISTORY]

        self.save()

    def remove(self, query: str, type_: str = "global",
               username: str | None = None) -> bool:
        """Supprime une entrée spécifique de l'historique.

        Retourne ``True`` si l'entrée a été trouvée et supprimée.
        """
        for i, entry in enumerate(self._entries):
            if (
                entry["query"] == query
                and entry.get("type") == type_
                and entry.get("username") == username
            ):
                self._entries.pop(i)
                self.save()
                return True
        return False

    def clear(self) -> None:
        """Supprime toutes les entrées de l'historique."""
        self._entries = []
        self.save()

    def update_count(self, query: str, type_: str = "global",
                     username: str | None = None,
                     count: int = 0) -> None:
        """Met à jour le compteur de résultats d'une entrée existante."""
        for entry in self._entries:
            if (
                entry["query"] == query
                and entry.get("type") == type_
                and entry.get("username") == username
            ):
                entry["count"] = count
                self.save()
                return
