"""Service SQLite de gestion de la bibliothèque de fichiers partagés.

Stockage : ``data/bot_bibliotheque.db``
  Schéma : shared_folders + files + indexes
  Migrations : incrémentielles via PRAGMA user_version

Architecture :
  - La base SQLite est la source de vérité pour la bibliothèque
  - Le scan disque peuple la base (scan_folder / scan_all)
  - Les modifications utilisateur passent par les méthodes CRUD
  - Le scan est threadé (QThread) → gestion check_same_thread
"""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Constantes ──────────────────────────────────────────

DB_PATH = Path("data/bot_bibliotheque.db")

SCHEMA_VERSION = 1

# ── ScanResult ──────────────────────────────────────────


@dataclass
class ScanResult:
    """Résultat d'un scan complet de la bibliothèque."""

    folders_scanned: int = 0
    files_found: int = 0
    files_new: int = 0
    files_removed: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0


# ── Connexion ───────────────────────────────────────────


def get_connection() -> "sqlite3.Connection":
    """Retourne une connexion SQLite avec les PRAGMAs recommandés.

    Note pour le multithreading :
      - Utiliser ``check_same_thread=False`` si la connexion est partagée
        entre plusieurs threads (ex: scan dans un QThread).
      - Chaque thread peut aussi créer sa propre connexion.
    """
    import sqlite3

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Migration ───────────────────────────────────────────

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS shared_folders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    path        TEXT    NOT NULL UNIQUE,
    label       TEXT,
    enabled     INTEGER NOT NULL DEFAULT 1,
    scanned_at  TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS files (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_id   INTEGER NOT NULL REFERENCES shared_folders(id) ON DELETE CASCADE,
    path        TEXT    NOT NULL UNIQUE,
    name        TEXT    NOT NULL,
    extension   TEXT    NOT NULL DEFAULT '',
    size_bytes  INTEGER NOT NULL DEFAULT 0,
    modified_at TEXT,

    bitrate     INTEGER,
    duration    INTEGER,
    artist      TEXT,
    album       TEXT,
    title       TEXT,
    track       INTEGER,
    year        INTEGER,

    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_files_folder ON files(folder_id);
CREATE INDEX IF NOT EXISTS idx_files_name ON files(name);
CREATE INDEX IF NOT EXISTS idx_files_extension ON files(extension);
CREATE INDEX IF NOT EXISTS idx_files_artist ON files(artist);
CREATE INDEX IF NOT EXISTS idx_files_album ON files(album);
CREATE INDEX IF NOT EXISTS idx_files_title ON files(title);
"""


def get_schema_version(conn: "sqlite3.Connection") -> int:
    """Lit la version du schéma depuis PRAGMA user_version."""
    row = conn.execute("PRAGMA user_version").fetchone()
    return row[0] if row else 0


def migrate(conn: "sqlite3.Connection") -> None:
    """Applique les migrations nécessaires pour atteindre la dernière version."""
    version = get_schema_version(conn)

    if version < 1:
        logger.info("Migration v0 → v1 : création du schéma initial")
        conn.executescript(SCHEMA_V1)
        conn.execute("PRAGMA user_version = 1")
        conn.commit()
        logger.info("Migration v0 → v1 terminée")

    # Futures migrations : elif version < 2: ...


# ── Helper ──────────────────────────────────────────────


def _row_to_dict(row: Optional["sqlite3.Row"]) -> Optional[dict[str, Any]]:
    """Convertit une sqlite3.Row en dict (ou None)."""
    if row is None:
        return None
    return dict(row)


def _rows_to_dicts(rows: list["sqlite3.Row"]) -> list[dict[str, Any]]:
    """Convertit une liste de sqlite3.Row en liste de dict."""
    return [dict(r) for r in rows]


# ── Classe principale ────────────────────────────────────

SCAN_AUDIO_EXTENSIONS = {
    ".mp3",
    ".flac",
    ".ogg",
    ".m4a",
    ".wav",
    ".wma",
    ".aac",
    ".opus",
    ".aiff",
    ".ape",
}

IGNORED_EXTENSIONS = {
    ".part",
    ".tmp",
    ".bak",
    ".lnk",
    ".url",
    ".ds_store",
    ".thumbs.db",
}


class LibraryDB:
    """Service de gestion de la bibliothèque de fichiers partagés.

    Utilisation :
        db = LibraryDB()
        folders = db.get_folders()
        result = db.scan_all()
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path else DB_PATH
        self._ensure_schema()

    # ── Initialisation ────────────────────────────────────

    def _ensure_schema(self) -> None:
        """Vérifie/crée le schéma au démarrage."""
        conn = self._connect()
        try:
            migrate(conn)
        finally:
            conn.close()

    def _connect(self) -> "sqlite3.Connection":
        """Crée une connexion à la base (thread-safe)."""
        import sqlite3

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    # ── Dossiers ──────────────────────────────────────────

    def get_folders(self) -> list[dict[str, Any]]:
        """Retourne la liste des dossiers partagés activés."""
        conn = self._connect()
        try:
            rows = conn.execute("SELECT * FROM shared_folders WHERE enabled = 1 ORDER BY label, path").fetchall()
            return _rows_to_dicts(rows)
        finally:
            conn.close()

    def get_folder_tree(self) -> list[dict[str, Any]]:
        """Retourne l'arborescence complète des dossiers.

        Structure : liste de dicts avec ``path``, ``label``, ``id``, ``count``.
        """
        conn = self._connect()
        try:
            rows = conn.execute("""
                SELECT sf.*, COUNT(f.id) AS file_count
                FROM shared_folders sf
                LEFT JOIN files f ON f.folder_id = sf.id
                WHERE sf.enabled = 1
                GROUP BY sf.id
                ORDER BY sf.label, sf.path
            """).fetchall()
            return _rows_to_dicts(rows)
        finally:
            conn.close()

    def add_folder(self, path: str) -> Optional[int]:
        """Ajoute un dossier à partager.

        Retourne l'ID du dossier (existant ou nouvellement créé)
        ou ``None`` en cas d'erreur.
        """
        conn = self._connect()
        try:
            # Vérifier si déjà présent
            existing = conn.execute("SELECT id FROM shared_folders WHERE path = ?", (path,)).fetchone()
            if existing:
                return existing["id"]

            label = Path(path).name or path
            conn.execute(
                "INSERT INTO shared_folders (path, label) VALUES (?, ?)",
                (path, label),
            )
            conn.commit()
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        except Exception:
            logger.exception("Erreur lors de l'ajout du dossier : %s", path)
            return None
        finally:
            conn.close()

    def remove_folder(self, id: int) -> bool:
        """Retire un dossier et ses fichiers de l'index.

        Retourne ``True`` si supprimé.
        """
        conn = self._connect()
        try:
            cur = conn.execute("DELETE FROM shared_folders WHERE id = ?", (id,))
            conn.commit()
            return cur.rowcount > 0
        except Exception:
            logger.exception("Erreur lors de la suppression du dossier #%d", id)
            return False
        finally:
            conn.close()

    # ── Fichiers ──────────────────────────────────────────

    def get_files(
        self,
        folder_id: Optional[int] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        order: str = "ASC",
    ) -> list[dict[str, Any]]:
        """Retourne la liste des fichiers, filtrée et triée.

        Args:
            folder_id: Filtre par dossier (``None`` = tous les dossiers).
            search:   Recherche plein texte (nom + tags audio).
            sort_by:  Colonne de tri (``name``, ``size_bytes``, etc.).
            order:    ``ASC`` ou ``DESC``.

        Returns:
            Liste de dicts représentant les fichiers.
        """
        conn = self._connect()
        try:
            conditions: list[str] = []
            params: list[Any] = []

            if folder_id is not None:
                conditions.append("f.folder_id = ?")
                params.append(folder_id)

            if search:
                conditions.append("""
                    (f.name LIKE ? OR f.artist LIKE ? OR f.album LIKE ?
                     OR f.title LIKE ?)
                """)
                like = f"%{search}%"
                params.extend([like, like, like, like])

            where = " AND ".join(conditions) if conditions else "1"

            # Validation du tri pour éviter l'injection SQL
            allowed_sort = {
                "name",
                "size_bytes",
                "duration",
                "bitrate",
                "extension",
                "modified_at",
                "artist",
                "album",
                "title",
            }
            if sort_by is None or sort_by not in allowed_sort:
                sort_by = "name"

            order_sql = "DESC" if order.upper() == "DESC" else "ASC"

            query = f"""
                SELECT f.*, sf.label AS folder_label, sf.path AS folder_path
                FROM files f
                JOIN shared_folders sf ON sf.id = f.folder_id
                WHERE {where}
                ORDER BY f.{sort_by} {order_sql}
            """

            rows = conn.execute(query, params).fetchall()
            return _rows_to_dicts(rows)
        finally:
            conn.close()

    def get_file(self, id: int) -> Optional[dict[str, Any]]:
        """Retourne un fichier unique avec toutes ses métadonnées."""
        conn = self._connect()
        try:
            row = conn.execute(
                """
                SELECT f.*, sf.label AS folder_label, sf.path AS folder_path
                FROM files f
                JOIN shared_folders sf ON sf.id = f.folder_id
                WHERE f.id = ?
            """,
                (id,),
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()

    def remove_file(self, id: int) -> bool:
        """Retire un fichier de l'index (ne supprime PAS du disque).

        Retourne ``True`` si le fichier a été trouvé et retiré.
        """
        conn = self._connect()
        try:
            cur = conn.execute("DELETE FROM files WHERE id = ?", (id,))
            conn.commit()
            return cur.rowcount > 0
        except Exception:
            logger.exception("Erreur lors de la suppression du fichier #%d", id)
            return False
        finally:
            conn.close()

    def search(
        self,
        query: str,
        folder_id: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Recherche plein texte (nom + tags audio) dans la bibliothèque.

        Args:
            query:    Terme de recherche.
            folder_id: Limiter à un dossier spécifique (optionnel).

        Returns:
            Liste des fichiers correspondants.
        """
        conn = self._connect()
        try:
            conditions = ["(f.name LIKE ? OR f.artist LIKE ? OR f.album LIKE ? OR f.title LIKE ?)"]
            params: list[Any] = [f"%{query}%"] * 4

            if folder_id is not None:
                conditions.append("f.folder_id = ?")
                params.append(folder_id)

            where = " AND ".join(conditions)

            rows = conn.execute(
                f"""
                SELECT f.*, sf.label AS folder_label, sf.path AS folder_path
                FROM files f
                JOIN shared_folders sf ON sf.id = f.folder_id
                WHERE {where}
                ORDER BY f.name ASC
            """,
                params,
            ).fetchall()
            return _rows_to_dicts(rows)
        finally:
            conn.close()

    # ── Statistiques ──────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Retourne les statistiques de la bibliothèque.

        Returns:
            Dictionnaire avec les clés :
            ``folders``, ``files``, ``audio_files``, ``total_size_bytes``.
        """
        conn = self._connect()
        try:
            folders = conn.execute("SELECT COUNT(*) AS c FROM shared_folders WHERE enabled = 1").fetchone()[0]

            files = conn.execute("SELECT COUNT(*) AS c FROM files").fetchone()[0]

            audio = conn.execute("""
                SELECT COUNT(*) AS c FROM files
                WHERE extension IN ('.mp3','.flac','.ogg','.m4a','.wav','.wma',
                                    '.aac','.opus','.aiff','.ape')
            """).fetchone()[0]

            total_size = conn.execute("SELECT COALESCE(SUM(size_bytes), 0) AS s FROM files").fetchone()[0]

            return {
                "folders": folders,
                "files": files,
                "audio_files": audio,
                "total_size_bytes": total_size,
            }
        finally:
            conn.close()

    # ── Scan ──────────────────────────────────────────────

    def scan_folder(self, path: str, progress_callback=None) -> int:
        """Scanne un dossier sur le disque et indexe ses fichiers.

        Args:
            path: Chemin absolu du dossier à scanner.
            progress_callback: Optionnel, appelé avec ``(processed, total)``
                à chaque fichier traité. ``total`` peut être ``None`` si inconnu.

        Returns:
            Nombre de nouveaux fichiers indexés (ou -1 si dossier introuvable).
        """
        import sqlite3

        ppath = Path(path)
        if not ppath.is_dir():
            logger.warning("Dossier introuvable : %s", path)
            return -1

        # Ajouter le dossier s'il n'existe pas
        folder_id = self.add_folder(path)
        if folder_id is None:
            return -1

        conn = self._connect()
        try:
            # Collecter les chemins existants dans ce dossier
            existing = set(
                row[0] for row in conn.execute("SELECT path FROM files WHERE folder_id = ?", (folder_id,)).fetchall()
            )

            new_count = 0
            current_paths: set[str] = set()
            processed = 0

            for fpath in ppath.rglob("*"):
                if not fpath.is_file():
                    continue

                abs_path = str(fpath.resolve())
                current_paths.add(abs_path)

                extension = fpath.suffix.lower()
                if extension in IGNORED_EXTENSIONS:
                    continue

                # Compter la progression sur TOUS les fichiers traversés,
                # pas seulement les nouveaux (pour que la barre de progression
                # corresponde au total pré-compté)
                processed += 1
                if progress_callback:
                    progress_callback(processed, None)

                if abs_path in existing:
                    continue

                # Extraire les métadonnées
                stat = fpath.stat()
                modified = time.strftime(
                    "%Y-%m-%dT%H:%M:%S",
                    time.localtime(stat.st_mtime),
                )

                # Métadonnées audio
                bitrate: Optional[int] = None
                duration: Optional[int] = None
                artist: Optional[str] = None
                album: Optional[str] = None
                title: Optional[str] = None
                track: Optional[int] = None
                year: Optional[int] = None

                if extension in SCAN_AUDIO_EXTENSIONS:
                    try:
                        import mutagen

                        audio = mutagen.File(fpath)
                        if audio is not None:
                            # Info communes
                            if audio.info:
                                duration = int(audio.info.length) if hasattr(audio.info, "length") else None
                                bitrate = int(audio.info.bitrate // 1000) if hasattr(audio.info, "bitrate") else None

                            # Tags
                            if audio.tags:
                                artist = self._get_tag(audio.tags, "artist")
                                album = self._get_tag(audio.tags, "album")
                                title = self._get_tag(audio.tags, "title")
                                # noinspection PyTypeChecker
                                track = self._get_tag_int(audio.tags, "tracknumber")
                                # noinspection PyTypeChecker
                                year = self._get_tag_int(audio.tags, "date")
                    except Exception:
                        logger.debug("Impossible de lire les tags : %s", fpath.name)

                try:
                    conn.execute(
                        """
                        INSERT INTO files (folder_id, path, name, extension,
                                           size_bytes, modified_at,
                                           bitrate, duration, artist, album,
                                           title, track, year)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            folder_id,
                            abs_path,
                            fpath.name,
                            extension,
                            stat.st_size,
                            modified,
                            bitrate,
                            duration,
                            artist,
                            album,
                            title,
                            track,
                            year,
                        ),
                    )
                    new_count += 1
                except sqlite3.IntegrityError:
                    # Déjà présent (race condition), on ignore
                    pass

            # Nettoyer les fichiers supprimés du disque
            removed = existing - current_paths
            for rem_path in removed:
                conn.execute("DELETE FROM files WHERE path = ?", (rem_path,))
            removed_count = len(removed)
            if removed_count:
                logger.info("%d fichier(s) supprimé(s) (disparus du disque) dans %s", removed_count, path)

            # Mettre à jour scanned_at
            now = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
            conn.execute(
                "UPDATE shared_folders SET scanned_at = ? WHERE id = ?",
                (now, folder_id),
            )

            conn.commit()
            return new_count
        finally:
            conn.close()

    def scan_all(self, progress_callback=None) -> ScanResult:
        """Scanne tous les dossiers partagés activés.

        Args:
            progress_callback: Optionnel, appelé avec ``(processed, total)``
                à chaque fichier traité. Le total est estimé avant le scan
                pour une barre de progression précise.

        Returns:
            ScanResult avec les statistiques du scan.

        Note:
            Le calcul de ``files_removed`` se fait par différence :
            fichiers avant + nouveaux - fichiers après = fichiers supprimés.
        """
        start = time.monotonic()
        result = ScanResult()

        files_before = self.get_stats()["files"]

        folders = self.get_folders()

        # Compter le nombre total de fichiers si un callback de progression
        # est fourni (pour une barre de progression precise)
        total_files = 0
        if progress_callback:
            for folder in folders:
                ppath = Path(folder["path"])
                if ppath.is_dir():
                    for f in ppath.rglob("*"):
                        if f.is_file() and f.suffix.lower() not in IGNORED_EXTENSIONS:
                            total_files += 1

        _global_processed = [0]

        for folder in folders:
            path = folder["path"]
            if not Path(path).is_dir():
                result.errors.append(f"Dossier introuvable : {path}")
                continue

            try:
                # Wrapper callback qui cumule le compteur entre les dossiers
                if progress_callback:
                    _folder_processed = [0]

                    def _folder_cb(current, _total):
                        _global_processed[0] += current - _folder_processed[0]
                        _folder_processed[0] = current
                        progress_callback(_global_processed[0], total_files)
                else:
                    _folder_cb = None

                new_files = self.scan_folder(path, progress_callback=_folder_cb)
                if new_files >= 0:
                    result.folders_scanned += 1
                    result.files_new += new_files
                else:
                    result.errors.append(f"Erreur d'accès : {path}")
            except Exception as exc:
                result.errors.append(f"Erreur sur {path} : {exc}")
                logger.exception("Erreur lors du scan de %s", path)

        # Calculer le total de fichiers après scan
        stats = self.get_stats()
        result.files_found = stats["files"]

        # Déduire les fichiers supprimés :
        # files_before + files_new - files_removed = files_after
        # -> files_removed = files_before + files_new - files_after
        result.files_removed = max(0, files_before + result.files_new - result.files_found)

        result.duration_ms = int((time.monotonic() - start) * 1000)
        return result

    # ── Helpers tags ──────────────────────────────────────

    @staticmethod
    def _get_tag(tags: Any, key: str) -> Optional[str]:
        """Extrait une valeur textuelle d'un tag mutagen."""
        for k in (key, key.capitalize(), key.upper(), f"T{key.upper()}"):
            if k in tags:
                val = tags[k]
                if hasattr(val, "text"):
                    return str(val.text[0]) if val.text else None
                return str(val)
        return None

    @staticmethod
    def _get_tag_int(tags: Any, key: str) -> Optional[int]:
        """Extrait une valeur entière d'un tag mutagen."""
        val = LibraryDB._get_tag(tags, key)
        if val is None:
            return None
        try:
            # Parfois "1/10" → on prend la première partie
            return int(val.split("/")[0].strip())
        except (ValueError, TypeError):
            return None

    # ── Utilitaires ───────────────────────────────────────

    def get_audio_extensions(self) -> set[str]:
        """Retourne les extensions reconnues comme audio."""
        return SCAN_AUDIO_EXTENSIONS

    def get_stat_cards(self) -> list[dict[str, Any]]:
        """Retourne les données formatées pour les cartes de stats de l'UI.

        Returns:
            Liste de dicts : ``{"label": ..., "value": ..., "icon": ...}``.
        """
        stats = self.get_stats()
        return [
            {"label": "Dossiers", "value": stats["folders"], "icon": "📁"},
            {"label": "Fichiers", "value": stats["files"], "icon": "📄"},
            {"label": "Audio", "value": stats["audio_files"], "icon": "🎵"},
        ]


# ── Singleton pratique (paresseux) ──────────────────────

_library_db_instance: Optional[LibraryDB] = None


def get_library_db() -> LibraryDB:
    """Retourne l'instance singleton de LibraryDB.

    La base est créée au premier appel seulement, pas à l'import.
    """
    global _library_db_instance
    if _library_db_instance is None:
        _library_db_instance = LibraryDB()
    return _library_db_instance


# NOTE : Pas de singleton créé à l'import ici.
# Les modules qui ont besoin du singleton doivent utiliser :
#   from src.services.library_db import get_library_db
#   db = get_library_db()
