"""
Service d'historique des téléchargements — persistance SQLite.

Stocke les téléchargements terminés ou échoués pour consultation
ultérieure. Sert de source de données pour le HistoryDialog du BotTelechargement.

Pattern : module singleton lazy, calqué sur planificateur_service.py.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Chemins ───────────────────────────────────────────────

_DATA_DIR = Path("data")
_DB_PATH = _DATA_DIR / "telechargement_history.db"
_SCHEMA_VERSION = 1

# ── SQL ──────────────────────────────────────────────────

_SQL_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS download_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    identifiant     TEXT    NOT NULL,
    fichier         TEXT    NOT NULL,
    utilisateur     TEXT    NOT NULL DEFAULT '',
    taille          TEXT    NOT NULL DEFAULT '',
    taille_bytes    INTEGER NOT NULL DEFAULT 0,
    statut          TEXT    NOT NULL CHECK(statut IN ('termine', 'echoue')),
    vitesse_moyenne TEXT    NOT NULL DEFAULT '',
    vitesse_bytes   REAL    NOT NULL DEFAULT 0.0,
    date_debut      TEXT    NOT NULL,
    date_fin        TEXT    NOT NULL DEFAULT (datetime('now')),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_history_date ON download_history(date_fin DESC);
CREATE INDEX IF NOT EXISTS idx_history_statut ON download_history(statut);
"""

# ── Connexion singleton lazy ─────────────────────────────

_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    """Retourne la connexion SQLite (initialisation lazy)."""
    global _conn
    if _conn is None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(_DB_PATH))
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL;")
        _ensure_schema()
    return _conn


def _ensure_schema() -> None:
    """Crée ou migre le schéma si nécessaire."""
    global _conn
    assert _conn is not None
    cursor = _conn.execute("PRAGMA user_version;")
    version = cursor.fetchone()[0]

    if version < 1:
        logger.info("Migration v0 → v1 : création de download_history")
        _conn.executescript(_SQL_CREATE_TABLE)
        _conn.execute(f"PRAGMA user_version = {_SCHEMA_VERSION};")
        _conn.commit()
        logger.info("Historique téléchargements : schéma v1 créé")

    # Futures migrations : elif version < 2: ...


# ── API publique ─────────────────────────────────────────


def add_to_history(
    identifiant: str,
    fichier: str,
    utilisateur: str = "",
    taille: str = "",
    taille_bytes: int = 0,
    statut: str = "termine",
    vitesse_moyenne: str = "",
    vitesse_bytes: float = 0.0,
    date_debut: str | None = None,
) -> None:
    """Ajoute un téléchargement à l'historique."""
    conn = _get_conn()
    if date_debut is None:
        date_debut = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        """
        INSERT INTO download_history
            (identifiant, fichier, utilisateur, taille, taille_bytes,
             statut, vitesse_moyenne, vitesse_bytes, date_debut)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (identifiant, fichier, utilisateur, taille, taille_bytes,
         statut, vitesse_moyenne, vitesse_bytes, date_debut),
    )
    conn.commit()
    logger.debug("Historique ajouté : %s (%s)", fichier, statut)


def get_history(
    limit: int = 200,
    offset: int = 0,
    statut_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Retourne l'historique des téléchargements, trié par date_fin DESC."""
    conn = _get_conn()
    query = "SELECT * FROM download_history"
    params: list[Any] = []

    if statut_filter and statut_filter in ("termine", "echoue"):
        query += " WHERE statut = ?"
        params.append(statut_filter)

    query += " ORDER BY date_fin DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def count_history(statut_filter: str | None = None) -> int:
    """Compte les entrées d'historique (optionnellement filtrées)."""
    conn = _get_conn()
    query = "SELECT COUNT(*) FROM download_history"
    params: list[Any] = []

    if statut_filter and statut_filter in ("termine", "echoue"):
        query += " WHERE statut = ?"
        params.append(statut_filter)

    row = conn.execute(query, params).fetchone()
    return row[0] if row else 0


def clear_history() -> int:
    """Supprime toutes les entrées de l'historique. Retourne le nombre supprimé."""
    conn = _get_conn()
    count = conn.execute("SELECT COUNT(*) FROM download_history").fetchone()[0]
    conn.execute("DELETE FROM download_history;")
    conn.commit()
    logger.info("Historique téléchargements vidé (%d entrées)", count)
    return count


def close() -> None:
    """Ferme la connexion SQLite."""
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None
        logger.debug("Connexion historique téléchargements fermée")
