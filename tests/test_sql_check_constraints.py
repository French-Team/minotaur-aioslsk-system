"""Tests des contraintes CHECK SQLite dans tous les services du projet.

Vérifie que chaque table avec une clause CHECK rejette les valeurs invalides
et accepte les valeurs valides, en utilisant des bases :memory: isolées.
"""

from __future__ import annotations

import sqlite3

import pytest


# ── Helpers ────────────────────────────────────────────────────────────────


def _execute(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> None:
    conn.execute(sql, params)
    conn.commit()


# ═══════════════════════════════════════════════════════════════════════════
# planificateur_service.py — table actions
# ═══════════════════════════════════════════════════════════════════════════

_SQL_ACTIONS = """
CREATE TABLE IF NOT EXISTS actions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    type                TEXT    NOT NULL CHECK(type IN ('recherche','scan','wishlist','optimisation','nettoyage','telechargement','classement','renommage','deduplication','nettoyage_temp')),
    parametres          TEXT    NOT NULL DEFAULT '{}',
    mode                TEXT    NOT NULL CHECK(mode IN ('immediat','planifie')),
    statut              TEXT    NOT NULL DEFAULT 'en_attente'
                                    CHECK(statut IN ('en_attente','planifiee','en_cours','terminee','echouee','pause')),
    recurrence_interval INTEGER,
    recurrence_unite    TEXT    CHECK(recurrence_unite IN ('minutes','heures','jours')),
    prochaine_execution TIMESTAMP,
    nb_tentatives       INTEGER NOT NULL DEFAULT 0,
    erreur              TEXT,
    nom                 TEXT,
    description         TEXT,
    date_creation       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    date_execution      TIMESTAMP
);
"""


class TestActionsCheckConstraints:
    """Contraintes CHECK de la table actions (planificateur_service.py)."""

    @pytest.fixture
    def conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(_SQL_ACTIONS)
        yield conn
        conn.close()

    # ── CHECK type ──────────────────────────────────────────────────────

    def test_type_valide_accepte(self, conn: sqlite3.Connection) -> None:
        """Les 10 types valides sont acceptés."""
        for t in [
            "recherche", "scan", "wishlist", "optimisation",
            "nettoyage", "telechargement", "classement",
            "renommage", "deduplication", "nettoyage_temp",
        ]:
            conn.execute(
                "INSERT INTO actions (type, mode) VALUES (?, 'immediat')", (t,)
            )
            conn.commit()

    def test_type_invalide_leve_integrity_error(self, conn: sqlite3.Connection) -> None:
        """Un type hors liste lève IntegrityError."""
        with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
            conn.execute(
                "INSERT INTO actions (type, mode) VALUES ('backup', 'immediat')"
            )
            conn.commit()

    # ── CHECK mode ──────────────────────────────────────────────────────

    def test_mode_valide_accepte(self, conn: sqlite3.Connection) -> None:
        """Les 2 modes valides sont acceptés."""
        _execute(conn, "INSERT INTO actions (type, mode) VALUES ('scan', 'immediat')")
        _execute(conn, "INSERT INTO actions (type, mode) VALUES ('scan', 'planifie')")

    def test_mode_invalide_leve_integrity_error(self, conn: sqlite3.Connection) -> None:
        """Un mode hors liste lève IntegrityError."""
        with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
            conn.execute(
                "INSERT INTO actions (type, mode) VALUES ('scan', 'manuel')"
            )
            conn.commit()

    # ── CHECK statut ─────────────────────────────────────────────────────

    def test_statut_valide_accepte(self, conn: sqlite3.Connection) -> None:
        """Les 6 statuts valides sont acceptés."""
        for s in [
            "en_attente", "planifiee", "en_cours",
            "terminee", "echouee", "pause",
        ]:
            _execute(conn,
                "INSERT INTO actions (type, mode, statut) VALUES ('scan', 'immediat', ?)",
                (s,),
            )

    def test_statut_invalide_leve_integrity_error(self, conn: sqlite3.Connection) -> None:
        """Un statut hors liste lève IntegrityError."""
        with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
            conn.execute(
                "INSERT INTO actions (type, mode, statut) VALUES ('scan', 'immediat', 'annule')"
            )
            conn.commit()

    # ── CHECK recurrence_unite ───────────────────────────────────────────

    def test_recurrence_unite_valide_accepte(self, conn: sqlite3.Connection) -> None:
        """Les 3 unités de récurrence valides sont acceptées."""
        for u in ["minutes", "heures", "jours"]:
            _execute(conn,
                "INSERT INTO actions (type, mode, recurrence_unite) VALUES ('scan', 'immediat', ?)",
                (u,),
            )

    def test_recurrence_unite_invalide_leve_integrity_error(
        self, conn: sqlite3.Connection
    ) -> None:
        """Une unité de récurrence hors liste lève IntegrityError."""
        with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
            conn.execute(
                "INSERT INTO actions (type, mode, recurrence_unite) "
                "VALUES ('scan', 'immediat', 'annees')"
            )
            conn.commit()

    def test_recurrence_unite_null_accepte(self, conn: sqlite3.Connection) -> None:
        """recurrence_unite peut être NULL (pas de NOT NULL)."""
        _execute(conn,
            "INSERT INTO actions (type, mode) VALUES ('scan', 'immediat')"
        )


# ═══════════════════════════════════════════════════════════════════════════
# telechargement_history.py — table download_history
# ═══════════════════════════════════════════════════════════════════════════

_SQL_DOWNLOAD_HISTORY = """
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
"""


class TestDownloadHistoryCheckConstraints:
    """Contraintes CHECK de la table download_history (telechargement_history.py)."""

    @pytest.fixture
    def conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        conn.executescript(_SQL_DOWNLOAD_HISTORY)
        yield conn
        conn.close()

    def test_statut_valide_accepte(self, conn: sqlite3.Connection) -> None:
        """Les 2 statuts valides sont acceptés."""
        for s in ["termine", "echoue"]:
            _execute(conn,
                "INSERT INTO download_history (identifiant, fichier, statut, date_debut) "
                "VALUES ('id1', 'fichier.mp3', ?, datetime('now'))",
                (s,),
            )

    def test_statut_invalide_leve_integrity_error(self, conn: sqlite3.Connection) -> None:
        """Un statut hors liste lève IntegrityError."""
        with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
            conn.execute(
                "INSERT INTO download_history (identifiant, fichier, statut, date_debut) "
                "VALUES ('id1', 'fichier.mp3', 'en_cours', datetime('now'))"
            )
            conn.commit()


# ═══════════════════════════════════════════════════════════════════════════
# bot_assistant.py — table interactions
# ═══════════════════════════════════════════════════════════════════════════

_SQL_INTERACTIONS = """
CREATE TABLE IF NOT EXISTS interactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT    NOT NULL
                        CHECK(action_type IN ('config','diagnostic','recommendation','tutorial')),
    query       TEXT    NOT NULL,
    response    TEXT    NOT NULL,
    success     INTEGER NOT NULL DEFAULT 1,
    error_message TEXT,
    created_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class TestInteractionsCheckConstraints:
    """Contraintes CHECK de la table interactions (bot_assistant.py)."""

    @pytest.fixture
    def conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        conn.executescript(_SQL_INTERACTIONS)
        yield conn
        conn.close()

    def test_action_type_valide_accepte(self, conn: sqlite3.Connection) -> None:
        """Les 4 types d'action valides sont acceptés."""
        for t in ["config", "diagnostic", "recommendation", "tutorial"]:
            _execute(conn,
                "INSERT INTO interactions (action_type, query, response) "
                "VALUES (?, 'test query', 'test response')",
                (t,),
            )

    def test_action_type_invalide_leve_integrity_error(
        self, conn: sqlite3.Connection
    ) -> None:
        """Un type d'action hors liste lève IntegrityError."""
        with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
            conn.execute(
                "INSERT INTO interactions (action_type, query, response) "
                "VALUES ('notification', 'test', 'test')"
            )
            conn.commit()
