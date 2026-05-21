"""
EventBus — Bus d'événements centralisé.

Point d'entrée unique pour tous les événements de l'application.
Les services et bots émettent leurs événements ici.
BotSurveillance écoute et affiche.

Utilisation :
    from src.services.event_bus import EventBus, SurveillanceEvent

    # Émettre un événement
    EventBus().emit_event(
        category="reseau",
        severity="ERROR",
        title="Connexion perdue",
        message="Timeout après 30s sur server.slsknet.org:2416",
        source="connexion_manager",
    )

    # Écouter les événements
    EventBus().event_emitted.connect(mon_handler)
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

logger = logging.getLogger(__name__)

# ── Chemins ──────────────────────────────────────────────────────────────
_DATA_DIR = Path("data")
_DB_PATH = _DATA_DIR / "bot_surveillance.db"

# ── Schéma SQLite ────────────────────────────────────────────────────────
_SCHEMA_VERSION = 4

_SQL_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    severity    TEXT NOT NULL CHECK(severity IN ('INFO', 'WARN', 'ERROR')),
    category    TEXT NOT NULL,
    title       TEXT NOT NULL,
    message     TEXT NOT NULL,
    source      TEXT NOT NULL,
    details     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

_SQL_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC)",
    "CREATE INDEX IF NOT EXISTS idx_events_category ON events(category)",
    "CREATE INDEX IF NOT EXISTS idx_events_severity ON events(severity)",
    "CREATE INDEX IF NOT EXISTS idx_events_source ON events(source)",
    "CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at)",
]

_SQL_PRAGMAS = [
    "PRAGMA journal_mode = WAL",
    "PRAGMA foreign_keys = ON",
]


# ── Modèle ───────────────────────────────────────────────────────────────
@dataclass
class SurveillanceEvent:
    """Un événement surveillé par le système."""

    id: int = 0
    timestamp: str = ""  # ISO 8601
    severity: str = "INFO"  # INFO | WARN | ERROR
    category: str = "bot"
    title: str = ""
    message: str = ""
    source: str = ""
    details: dict[str, Any] | None = None
    created_at: str = ""

    SEVERITIES = ("INFO", "WARN", "ERROR")

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat(timespec="seconds")
        if self.severity not in self.SEVERITIES:
            raise ValueError(f"Sévérité invalide : {self.severity!r}")


# ── Service ──────────────────────────────────────────────────────────────
class EventBus(QObject):
    """
    Bus d'événements central — singleton thread-safe.

    Connecte-toi à ``event_emitted`` pour recevoir tous les événements.
    """

    event_emitted = Signal(object)  # SurveillanceEvent

    _instance: EventBus | None = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> EventBus:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls, *args, **kwargs)
                    cls._instance._initialized = False  # pyright: ignore
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_db", None) is not None:
            return
        super().__init__()

        self._db: sqlite3.Connection | None = None
        self._purge_timer: QTimer | None = None
        self._paused: bool = False
        self._ensure_data_dir()
        self._connect_db()
        self._ensure_schema()
        self._start_purge_timer()

        logger.info("EventBus initialisé — %s", _DB_PATH)

    # ── Pause / Resume ────────────────────────────────────────────────

    def pause(self) -> None:
        """Suspend la collecte des événements (pause totale)."""
        self._paused = True
        logger.info("EventBus en pause")

    def resume(self) -> None:
        """Reprend la collecte des événements."""
        self._paused = False
        logger.info("EventBus repris")

    # ── Initialisation ──────────────────────────────────────────────────

    def _ensure_data_dir(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _connect_db(self) -> None:
        try:
            self._db = sqlite3.connect(
                str(_DB_PATH),
                check_same_thread=False,
                timeout=5,
            )
            self._db.row_factory = sqlite3.Row
            for pragma in _SQL_PRAGMAS:
                self._db.execute(pragma)
            self._db.commit()
        except sqlite3.Error as exc:
            logger.critical("Impossible d'ouvrir la base SQLite %s : %s", _DB_PATH, exc)
            raise

    def _ensure_schema(self) -> None:
        assert self._db is not None

        # Lire la version actuelle de la base
        cursor = self._db.execute("PRAGMA user_version")
        version = cursor.fetchone()[0]

        if version == 0:
            # Nouvelle base — créer le schéma complet
            self._db.execute(_SQL_CREATE_TABLE)
            for idx in _SQL_INDEXES:
                self._db.execute(idx)
        elif version < _SCHEMA_VERSION:
            # Migration : recréer la table avec le schéma à jour
            # SQLite ne permet pas ALTER TABLE pour modifier CHECK
            self._db.execute("ALTER TABLE events RENAME TO events_old")
            self._db.execute(_SQL_CREATE_TABLE)

            # Lister les colonnes communes (safe même si l'ancienne table a moins de colonnes)
            old_cols = [col[1] for col in self._db.execute("PRAGMA table_info(events_old)").fetchall()]
            new_cols = [col[1] for col in self._db.execute("PRAGMA table_info(events)").fetchall()]
            common = [c for c in new_cols if c in old_cols]
            if common:
                cols = ", ".join(common)
                self._db.execute(f"INSERT INTO events ({cols}) SELECT {cols} FROM events_old")
            self._db.execute("DROP TABLE events_old")

            # Recréer les index
            for idx in _SQL_INDEXES:
                self._db.execute(idx)

        self._db.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
        self._db.commit()

    def _start_purge_timer(self) -> None:
        self._purge_timer = QTimer(self)
        self._purge_timer.timeout.connect(self.purge_old)
        self._purge_timer.start(3_600_000)  # Toutes les 1h
        # Première purge après 10s (laisse le temps à l'app de démarrer)
        QTimer.singleShot(10_000, self.purge_old)

    # ── API publique ────────────────────────────────────────────────────

    def emit_event(
        self,
        category: str,
        severity: str = "INFO",
        title: str = "",
        message: str = "",
        source: str = "",
        details: dict[str, Any] | None = None,
    ) -> SurveillanceEvent | None:
        """
        Crée un événement, le persiste en SQLite et l'émet via le signal.

        Retourne l'événement créé (avec son id SQLite).
        Retourne None si le bus est en pause.
        """
        if self._paused:
            logger.debug("EventBus en pause — événement ignoré")
            return None

        event = SurveillanceEvent(
            severity=severity,
            category=category,
            title=title,
            message=message,
            source=source,
            details=details,
        )

        # Persistance SQLite
        event.id = self._insert(event)

        # Émission Qt
        self.event_emitted.emit(event)

        logger.debug("Événement émis : [%s] %s — %s", event.severity, event.category, event.title)
        return event

    def query(
        self,
        *,
        category: str | None = None,
        severity: str | None = None,
        source: str | None = None,
        search: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SurveillanceEvent]:
        """
        Interroge l'historique avec filtres optionnels.

        Tous les filtres sont combinés avec AND.
        ``search`` cherche dans title, message et source (LIKE %text%).
        Les dates sont au format ISO (``YYYY-MM-DD`` ou ``YYYY-MM-DD HH:MM:SS``).
        """
        assert self._db is not None

        where_clauses: list[str] = []
        params: list[Any] = []

        if category:
            where_clauses.append("category = ?")
            params.append(category)
        if severity:
            where_clauses.append("severity = ?")
            params.append(severity)
        if source:
            where_clauses.append("source = ?")
            params.append(source)
        if search:
            where_clauses.append("(title LIKE ? OR message LIKE ? OR source LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like, like])
        if date_from:
            where_clauses.append("timestamp >= ?")
            params.append(date_from)
        if date_to:
            where_clauses.append("timestamp <= ?")
            params.append(date_to)

        where = ""
        if where_clauses:
            where = "WHERE " + " AND ".join(where_clauses)

        sql = f"SELECT * FROM events {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self._db.execute(sql, params).fetchall()
        return [self._row_to_event(row) for row in rows]

    def get_recent(self, limit: int = 50) -> list[SurveillanceEvent]:
        """Retourne les *limit* événements les plus récents."""
        assert self._db is not None
        rows = self._db.execute(
            "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def get_stats(self) -> dict[str, Any]:
        """
        Retourne des statistiques agrégées sur les événements.

        Retourne un dict avec :
        - total : nombre total d'événements
        - errors_24h : nombre d'ERROR dans les dernières 24h
        - warns_24h : nombre de WARN dans les dernières 24h
        - today : nombre d'événements aujourd'hui
        - par_categorie : dict {catégorie: count}
        """
        assert self._db is not None
        stats: dict[str, Any] = {}

        # Total
        stats["total"] = self._db.execute("SELECT COUNT(*) FROM events").fetchone()[0]

        # Erreurs 24h
        cutoff = (datetime.now() - timedelta(hours=24)).isoformat(timespec="seconds")
        stats["errors_24h"] = self._db.execute(
            "SELECT COUNT(*) FROM events WHERE severity = 'ERROR' AND timestamp >= ?",
            (cutoff,),
        ).fetchone()[0]

        # Warns 24h
        stats["warns_24h"] = self._db.execute(
            "SELECT COUNT(*) FROM events WHERE severity = 'WARN' AND timestamp >= ?",
            (cutoff,),
        ).fetchone()[0]

        # Aujourd'hui
        today = datetime.now().strftime("%Y-%m-%d")
        stats["today"] = self._db.execute(
            "SELECT COUNT(*) FROM events WHERE timestamp >= ?",
            (today,),
        ).fetchone()[0]

        # Par catégorie
        rows = self._db.execute(
            "SELECT category, COUNT(*) as cnt FROM events GROUP BY category ORDER BY cnt DESC"
        ).fetchall()
        stats["par_categorie"] = {row["category"]: row["cnt"] for row in rows}

        return stats

    def purge_old(self) -> int:
        """
        Supprime les événements plus vieux que 7 jours.

        Retourne le nombre d'événements supprimés.
        """
        assert self._db is not None
        cutoff = (datetime.now() - timedelta(days=7)).isoformat(timespec="seconds")
        cursor = self._db.execute("DELETE FROM events WHERE timestamp < ?", (cutoff,))
        self._db.commit()
        if cursor.rowcount > 0:
            logger.info("Purge : %d événements supprimés (avant %s)", cursor.rowcount, cutoff)
        return cursor.rowcount

    def delete_events(self, event_ids: list[int]) -> int:
        """Supprime des événements par leur id. Retourne le nombre supprimé."""
        assert self._db is not None
        if not event_ids:
            return 0
        placeholders = ",".join("?" * len(event_ids))
        cursor = self._db.execute(
            f"DELETE FROM events WHERE id IN ({placeholders})",
            event_ids,
        )
        self._db.commit()
        return cursor.rowcount

    def get_event(self, event_id: int) -> SurveillanceEvent | None:
        """Retourne un événement par son id, ou None si introuvable."""
        assert self._db is not None
        row = self._db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_event(row)

    # ── Interne ─────────────────────────────────────────────────────────

    def _insert(self, event: SurveillanceEvent) -> int:
        assert self._db is not None
        cursor = self._db.execute(
            """INSERT INTO events (timestamp, severity, category, title, message, source, details)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                event.timestamp,
                event.severity,
                event.category,
                event.title,
                event.message,
                event.source,
                json.dumps(event.details, ensure_ascii=False) if event.details else None,
            ),
        )
        self._db.commit()
        return cursor.lastrowid or 0

    def _row_to_event(self, row: sqlite3.Row) -> SurveillanceEvent:
        details: dict[str, Any] | None = None
        if row["details"]:
            try:
                details = json.loads(row["details"])
            except json.JSONDecodeError:
                details = {"_raw": row["details"]}
        return SurveillanceEvent(
            id=row["id"],
            timestamp=row["timestamp"],
            severity=row["severity"],
            category=row["category"],
            title=row["title"],
            message=row["message"],
            source=row["source"],
            details=details,
            created_at=row["created_at"],
        )

    # ── Nettoyage ───────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Ferme la connexion SQLite proprement."""
        if self._purge_timer:
            self._purge_timer.stop()
        if self._db:
            try:
                self._db.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            except sqlite3.Error as exc:
                logger.warning("Échec du checkpoint WAL au shutdown : %s", exc)
            try:
                self._db.close()
            except sqlite3.Error as exc:
                logger.warning("Échec de la fermeture de la base au shutdown : %s", exc)
            self._db = None
            logger.info("EventBus fermé")
