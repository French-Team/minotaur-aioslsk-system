"""
PlanificateurService — Service central de gestion des actions planifiées.

Singleton gérant une base SQLite (data/planificateur.db) avec :
  - CRUD des actions
  - Timer de vérification (30s)
  - File d'attente FIFO
  - Exécution séquentielle avec timeout/backoff
  - Pause globale
  - Purge auto 7 jours
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

from src.services.event_bus import EventBus

# ── Constantes ──────────────────────────────────────────────────────────────

_DATA_DIR = Path("data")
_DB_PATH = _DATA_DIR / "planificateur.db"

_SCHEMA_VERSION = 3

_SQL_CREATE_TABLE = """
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

_SQL_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_actions_statut ON actions(statut);",
    "CREATE INDEX IF NOT EXISTS idx_actions_prochaine ON actions(prochaine_execution);",
    "CREATE INDEX IF NOT EXISTS idx_actions_created ON actions(date_creation);",
]

# ── Types d'action ──────────────────────────────────────────────────────────

ACTION_TYPES = (
    "recherche",
    "scan",
    "wishlist",
    "optimisation",
    "nettoyage",
    "telechargement",
    "classement",
    "renommage",
    "deduplication",
    "nettoyage_temp",
)
ACTION_MODES = ("immediat", "planifie")
ACTION_STATUTS = ("en_attente", "planifiee", "en_cours", "terminee", "echouee", "pause")

_TIMER_INTERVAL_MS = 30_000  # 30s
_TIMEOUT_SECONDS = 300  # 5 min
_BACKOFF_DELAYS = [30, 120, 300]  # 30s, 2min, 5min
_MAX_RETRIES = 3
_PURGE_INTERVAL_MS = 3_600_000  # 1h


# ═══════════════════════════════════════════════════════════════════════════════
# PlanificationDB — Gestion SQLite
# ═══════════════════════════════════════════════════════════════════════════════


class PlanificationDB:
    """Couche d'accès SQLite pour les actions planifiées."""

    def __init__(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        import sqlite3

        self._conn = sqlite3.connect(str(_DB_PATH))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._ensure_schema()

    # ── Schéma ──────────────────────────────────────────────────────────

    def _ensure_schema(self) -> None:
        """Crée ou migre le schéma selon la version."""
        cursor = self._conn.execute("PRAGMA user_version;")
        current_version = cursor.fetchone()[0]

        if current_version < _SCHEMA_VERSION:
            if current_version == 0:
                # Création initiale
                self._conn.executescript(_SQL_CREATE_TABLE)
                for idx in _SQL_INDEXES:
                    self._conn.execute(idx)
            elif current_version == 1:
                # Migration v1 → v2 : ajouter colonnes nom et description
                self._conn.execute("ALTER TABLE actions ADD COLUMN nom TEXT;")
                self._conn.execute("ALTER TABLE actions ADD COLUMN description TEXT;")
            else:
                # Migration depuis une version antérieure
                self._conn.executescript("DROP TABLE IF EXISTS actions_old;")
                self._conn.executescript("ALTER TABLE actions RENAME TO actions_old;")
                self._conn.executescript(_SQL_CREATE_TABLE)
                # Copier les données compatibles
                try:
                    cols = [
                        "type",
                        "parametres",
                        "mode",
                        "statut",
                        "recurrence_interval",
                        "recurrence_unite",
                        "prochaine_execution",
                        "nb_tentatives",
                        "erreur",
                        "date_creation",
                        "date_execution",
                        "nom",
                        "description",
                    ]
                    self._conn.execute(
                        f"INSERT INTO actions ({','.join(cols)}) SELECT {','.join(cols)} FROM actions_old;"
                    )
                except Exception:
                    pass  # Ignorer les incompatibilités
                for idx in _SQL_INDEXES:
                    self._conn.execute(idx)
                self._conn.executescript("DROP TABLE IF EXISTS actions_old;")

            self._conn.execute(f"PRAGMA user_version = {_SCHEMA_VERSION};")
            self._conn.commit()

    # ── CRUD ────────────────────────────────────────────────────────────

    def create_action(
        self,
        type_: str,
        parametres: dict[str, Any],
        mode: str,
        recurrence_interval: int | None = None,
        recurrence_unite: str | None = None,
        prochaine_execution: str | None = None,
        nom: str | None = None,
        description: str | None = None,
    ) -> int:
        """Crée une action et retourne son ID."""
        if type_ not in ACTION_TYPES:
            raise ValueError(f"Type d'action invalide : {type_}")
        if mode not in ACTION_MODES:
            raise ValueError(f"Mode invalide : {mode}")

        statut = "planifiee" if mode == "planifie" else "en_attente"
        cursor = self._conn.execute(
            """INSERT INTO actions
               (type, parametres, mode, statut, recurrence_interval,
                recurrence_unite, prochaine_execution, nom, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                type_,
                json.dumps(parametres, ensure_ascii=False),
                mode,
                statut,
                recurrence_interval,
                recurrence_unite,
                prochaine_execution,
                nom,
                description,
            ),
        )
        self._conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def get_action(self, action_id: int) -> dict[str, Any] | None:
        """Retourne une action par son ID."""
        row = self._conn.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def update_action(self, action_id: int, **kwargs: Any) -> bool:
        """Met à jour une action. Retourne True si modifié."""
        allowed = {
            "type",
            "parametres",
            "mode",
            "statut",
            "recurrence_interval",
            "recurrence_unite",
            "prochaine_execution",
            "nb_tentatives",
            "erreur",
            "date_execution",
            "nom",
            "description",
        }
        updates: dict[str, Any] = {}
        for key, value in kwargs.items():
            if key not in allowed:
                raise ValueError(f"Champ non modifiable : {key}")
            if key == "parametres" and isinstance(value, dict):
                value = json.dumps(value, ensure_ascii=False)
            updates[key] = value

        if not updates:
            return False

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [action_id]
        cursor = self._conn.execute(f"UPDATE actions SET {set_clause} WHERE id = ?", values)
        self._conn.commit()
        return cursor.rowcount > 0

    def delete_action(self, action_id: int) -> bool:
        """Supprime une action. Retourne True si supprimé."""
        cursor = self._conn.execute("DELETE FROM actions WHERE id = ?", (action_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def list_actions(
        self,
        statut: str | None = None,
        type_: str | None = None,
        limite: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Liste les actions avec filtres optionnels."""
        query = "SELECT * FROM actions WHERE 1=1"
        params: list[Any] = []
        if statut:
            query += " AND statut = ?"
            params.append(statut)
        if type_:
            query += " AND type = ?"
            params.append(type_)
        query += " ORDER BY date_creation DESC LIMIT ? OFFSET ?"
        params.extend([limite, offset])
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_historique(self, limite: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """Liste les actions terminées ou échouées."""
        rows = self._conn.execute(
            """SELECT * FROM actions
               WHERE statut IN ('terminee', 'echouee')
               ORDER BY date_execution DESC
               LIMIT ? OFFSET ?""",
            (limite, offset),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_stats(self) -> dict[str, int]:
        """Retourne les compteurs par statut."""
        rows = self._conn.execute(
            """SELECT statut, COUNT(*) as cnt
               FROM actions
               GROUP BY statut"""
        ).fetchall()
        stats: dict[str, int] = {s: 0 for s in ACTION_STATUTS}
        for row in rows:
            stats[row["statut"]] = row["cnt"]
        return stats

    def get_actions_dues(self) -> list[dict[str, Any]]:
        """Retourne les actions dont la date d'exécution est dépassée."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows = self._conn.execute(
            """SELECT * FROM actions
               WHERE statut IN ('planifiee', 'en_attente')
                 AND (prochaine_execution IS NULL OR prochaine_execution <= ?)
               ORDER BY
                 CASE WHEN mode = 'immediat' THEN 0 ELSE 1 END,
                 prochaine_execution ASC""",
            (now,),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def purge_old(self) -> int:
        """Supprime les actions terminées ou échouées de plus de 7 jours.
        Retourne le nombre de lignes supprimées."""
        cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        cursor = self._conn.execute(
            """DELETE FROM actions
               WHERE statut IN ('terminee', 'echouee')
                 AND (date_execution IS NOT NULL AND date_execution < ?)""",
            (cutoff,),
        )
        self._conn.commit()
        return cursor.rowcount

    def close(self) -> None:
        self._conn.close()

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_dict(row: Any) -> dict[str, Any]:
        d = dict(row)
        if isinstance(d.get("parametres"), str):
            try:
                d["parametres"] = json.loads(d["parametres"])
            except (json.JSONDecodeError, TypeError):
                pass
        return d


# ═══════════════════════════════════════════════════════════════════════════════
# PlanificateurService — Singleton
# ═══════════════════════════════════════════════════════════════════════════════


class PlanificateurService(QObject):
    """Service central de gestion des actions planifiées (singleton)."""

    # Signal émis à chaque changement de statut d'une action
    action_changed = Signal(int, str, str)  # (action_id, action_type, statut)

    _instance: PlanificateurService | None = None
    _lock = threading.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> PlanificateurService:  # type: ignore[no-untyped-def]
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls, *args, **kwargs)
                    cls._instance._initialized = False  # pyright: ignore[reportAttributeAccessIssue]
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_db", None) is not None:
            return
        super().__init__()

        self._db = PlanificationDB()
        self._paused = False
        self._current_action_id: int | None = None
        self._current_action_start: float | None = None
        self._event_bus = EventBus()

        # Timer de vérification des actions à exécuter
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._on_poll)
        self._poll_timer.start(_TIMER_INTERVAL_MS)

        # Timer de purge automatique (1h)
        self._purge_timer = QTimer(self)
        self._purge_timer.timeout.connect(self._on_purge)
        self._purge_timer.start(_PURGE_INTERVAL_MS)

    # ── API publique ────────────────────────────────────────────────────

    # Déléguer les CRUD à la base

    def create_action(
        self,
        type_: str,
        parametres: dict[str, Any],
        mode: str,
        recurrence_interval: int | None = None,
        recurrence_unite: str | None = None,
        prochaine_execution: str | None = None,
        nom: str | None = None,
        description: str | None = None,
    ) -> int:
        """Crée une action et émet l'événement."""
        action_id = self._db.create_action(
            type_=type_,
            parametres=parametres,
            mode=mode,
            recurrence_interval=recurrence_interval,
            recurrence_unite=recurrence_unite,
            prochaine_execution=prochaine_execution,
            nom=nom,
            description=description,
        )
        statut = "planifiee" if mode == "planifie" else "en_attente"
        self.action_changed.emit(action_id, type_, statut)

        # EventBus — action créée
        event_name = "planificateur.action_planifiee" if mode == "planifie" else "planificateur.action_en_attente"
        self._event_bus.emit_event(
            category="bot",
            severity="INFO",
            title=event_name,
            message=f"{type_.replace('_', ' ').title()} — {statut}",
            source="planificateur",
            details={
                "action_id": action_id,
                "action_type": type_,
                "statut": statut,
                "parametres": parametres,
            },
        )
        return action_id

    def get_action(self, action_id: int) -> dict[str, Any] | None:
        return self._db.get_action(action_id)

    def update_action(self, action_id: int, **kwargs: Any) -> bool:
        result = self._db.update_action(action_id, **kwargs)
        if result and "statut" in kwargs:
            action = self._db.get_action(action_id)
            if action:
                self.action_changed.emit(action_id, action["type"], kwargs["statut"])
        return result

    def delete_action(self, action_id: int) -> bool:
        return self._db.delete_action(action_id)

    def list_actions(
        self,
        statut: str | None = None,
        type_: str | None = None,
        limite: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return self._db.list_actions(statut=statut, type_=type_, limite=limite, offset=offset)

    def get_historique(self, limite: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        return self._db.get_historique(limite=limite, offset=offset)

    def get_stats(self) -> dict[str, int]:
        return self._db.get_stats()

    # ── Pause / Resume ──────────────────────────────────────────────────

    @property
    def paused(self) -> bool:
        return self._paused

    def pause(self) -> None:
        """Met le service en pause — suspend le polling et l'exécution."""
        self._paused = True

    def resume(self) -> None:
        """Reprend le service."""
        self._paused = False

    # ── Actions bloquantes ────────────────────────────────────────────────

    def _get_types_en_cours(self) -> set[str]:
        """Retourne l'ensemble des types d'action actuellement 'en_cours'."""
        rows = self._db.list_actions(statut="en_cours")
        return {r["type"] for r in rows}

    # ── Exécution ───────────────────────────────────────────────────────

    def execute_manual(self, action_id: int) -> None:
        """Déclenche l'exécution immédiate d'une action (clic utilisateur)."""
        action = self._db.get_action(action_id)
        if action is None:
            return

        # Ne pas démarrer si une action est déjà en cours (exécution séquentielle)
        if self._current_action_id is not None:
            return

        # Vérifier les actions bloquantes (même type déjà en cours dans la DB)
        if action["type"] in self._get_types_en_cours():
            return  # Bloqué silencieusement

        self._db.update_action(
            action_id,
            statut="en_cours",
            nb_tentatives=0,
            erreur=None,
        )
        self.action_changed.emit(action_id, action["type"], "en_cours")

        # EventBus — action démarrée
        self._event_bus.emit_event(
            category="bot",
            severity="INFO",
            title="planificateur.action_demarree",
            message=f"{action['type'].replace('_', ' ').title()} — Exécution manuelle",
            source="planificateur",
            details={
                "action_id": action_id,
                "action_type": action["type"],
                "mode": action["mode"],
                "parametres": action.get("parametres"),
            },
        )

        self._current_action_id = action_id
        self._current_action_start = time.time()

    def _on_poll(self) -> None:
        """Vérifie les actions à exécuter (timer 30s)."""
        if self._paused:
            return

        # Vérifier le timeout de l'action en cours
        if self._current_action_id is not None and self._current_action_start is not None:
            elapsed = time.time() - self._current_action_start
            if elapsed > _TIMEOUT_SECONDS:
                action = self._db.get_action(self._current_action_id)
                self._db.update_action(
                    self._current_action_id,
                    statut="echouee",
                    erreur="Timeout dépassé (5 min)",
                )
                self.action_changed.emit(
                    self._current_action_id,
                    action["type"] if action else "inconnu",
                    "echouee",
                )
                self._current_action_id = None
                self._current_action_start = None

        # Si une action est déjà en cours, ne pas en lancer une autre
        if self._current_action_id is not None:
            return

        # Récupérer les actions dues
        dues = self._db.get_actions_dues()
        if not dues:
            return

        # Filtrer les actions bloquantes (même type déjà en cours dans la DB)
        types_en_cours = self._get_types_en_cours()

        # Prendre la première action non bloquée (FIFO : immédiates d'abord, puis planifiées par date)
        action: dict[str, Any] | None = None
        for candidate in dues:
            if candidate["type"] not in types_en_cours:
                action = candidate
                break

        if action is None:
            return  # Toutes les actions dues sont bloquées

        action_id = action["id"]

        # Marquer comme en cours
        self._db.update_action(action_id, statut="en_cours", nb_tentatives=0, erreur=None)
        self.action_changed.emit(action_id, action["type"], "en_cours")

        # EventBus — action démarrée (automatique)
        self._event_bus.emit_event(
            category="bot",
            severity="INFO",
            title="planificateur.action_demarree",
            message=f"{action['type'].replace('_', ' ').title()} — Exécution automatique",
            source="planificateur",
            details={
                "action_id": action_id,
                "action_type": action["type"],
                "mode": action["mode"],
            },
        )

        self._current_action_id = action_id
        self._current_action_start = time.time()

    def complete_action(self, action_id: int, succes: bool = True, erreur: str = "") -> None:
        """Marque une action comme terminée ou échouée (appelé par le bot cible)."""
        action = self._db.get_action(action_id)
        if action is None:
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        type_label = action["type"].replace("_", " ").title()

        if succes:
            # Vérifier si récurrente
            if action["recurrence_interval"] and action["recurrence_unite"]:
                # Replanifier
                from datetime import datetime as dt

                next_exec = dt.now()
                unit = action["recurrence_unite"]
                interval = action["recurrence_interval"]
                if unit == "minutes":
                    next_exec += timedelta(minutes=interval)
                elif unit == "heures":
                    next_exec += timedelta(hours=interval)
                elif unit == "jours":
                    next_exec += timedelta(days=interval)
                self._db.update_action(
                    action_id,
                    statut="planifiee",
                    date_execution=now,
                    prochaine_execution=next_exec.strftime("%Y-%m-%d %H:%M:%S"),
                    nb_tentatives=0,
                )
                self.action_changed.emit(action_id, action["type"], "planifiee")

                # EventBus — action récurrente replanifiée
                self._event_bus.emit_event(
                    category="bot",
                    severity="INFO",
                    title="planificateur.action_terminee",
                    message=f"{type_label} — Récurrente, prochaine exécution : {next_exec.strftime('%Y-%m-%d %H:%M')}",
                    source="planificateur",
                    details={
                        "action_id": action_id,
                        "action_type": action["type"],
                        "statut": "planifiee",
                        "prochaine_execution": next_exec.strftime("%Y-%m-%d %H:%M:%S"),
                    },
                )
            else:
                self._db.update_action(
                    action_id,
                    statut="terminee",
                    date_execution=now,
                )
                self.action_changed.emit(action_id, action["type"], "terminee")

                # EventBus — action terminée avec succès
                self._event_bus.emit_event(
                    category="bot",
                    severity="INFO",
                    title="planificateur.action_terminee",
                    message=f"{type_label} — Succès",
                    source="planificateur",
                    details={
                        "action_id": action_id,
                        "action_type": action["type"],
                        "statut": "terminee",
                    },
                )
        else:
            nb_tentatives = action["nb_tentatives"] + 1
            if nb_tentatives >= _MAX_RETRIES:
                erreur_msg = erreur or "Échec après 3 tentatives"
                self._db.update_action(
                    action_id,
                    statut="echouee",
                    date_execution=now,
                    nb_tentatives=nb_tentatives,
                    erreur=erreur_msg,
                )
                self.action_changed.emit(action_id, action["type"], "echouee")

                # EventBus — action échouée (final)
                self._event_bus.emit_event(
                    category="bot",
                    severity="ERROR",
                    title="planificateur.action_echouee",
                    message=f"{type_label} — {erreur_msg}",
                    source="planificateur",
                    details={
                        "action_id": action_id,
                        "action_type": action["type"],
                        "statut": "echouee",
                        "nb_tentatives": nb_tentatives,
                        "erreur": erreur_msg,
                    },
                )
            else:
                # Re-tenter après un délai de backoff
                delay = (
                    _BACKOFF_DELAYS[nb_tentatives - 1] if nb_tentatives <= len(_BACKOFF_DELAYS) else _BACKOFF_DELAYS[-1]
                )
                from datetime import datetime as dt

                erreur_msg = erreur or f"Tentative {nb_tentatives}/{_MAX_RETRIES}"
                next_try = dt.now() + timedelta(seconds=delay)
                self._db.update_action(
                    action_id,
                    statut="planifiee",
                    nb_tentatives=nb_tentatives,
                    erreur=erreur_msg,
                    prochaine_execution=next_try.strftime("%Y-%m-%d %H:%M:%S"),
                )
                self.action_changed.emit(action_id, action["type"], "planifiee")

                # EventBus — action en réessai
                self._event_bus.emit_event(
                    category="bot",
                    severity="WARN",
                    title="planificateur.action_echouee",
                    message=f"{type_label} — {erreur_msg}, prochain essai dans {delay}s",
                    source="planificateur",
                    details={
                        "action_id": action_id,
                        "action_type": action["type"],
                        "statut": "planifiee",
                        "nb_tentatives": nb_tentatives,
                        "prochaine_execution": next_try.strftime("%Y-%m-%d %H:%M:%S"),
                        "erreur": erreur_msg,
                    },
                )

        if self._current_action_id == action_id:
            self._current_action_id = None
            self._current_action_start = None

    # ── Purge ───────────────────────────────────────────────────────────

    def _on_purge(self) -> None:
        """Purge automatique des actions de plus de 7 jours."""
        deleted = self._db.purge_old()
        if deleted:
            import logging

            logging.getLogger(__name__).info(f"Purge planificateur : {deleted} action(s) supprimée(s)")

    def force_purge(self) -> int:
        """Déclenche une purge manuelle. Retourne le nombre supprimé."""
        return self._db.purge_old()


# ── Instance globale pour import ─────────────────────────────────────────────

planificateur_service = PlanificateurService()
