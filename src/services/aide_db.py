"""
Service de base de données du bot Aide.

Gère la persistance des articles d'aide (importés depuis des fichiers .md)
et l'historique des consultations.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

# ── Chemins ────────────────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DB_DIR = _PROJECT_ROOT / "data"
_DB_PATH = _DB_DIR / "bot_aide.db"
_KNOWLEDGE_DIR = _DB_DIR / "aide_knowledge"

_SCHEMA_VERSION = 1

_SQL_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS articles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category    TEXT    NOT NULL,
    title       TEXT    NOT NULL UNIQUE,
    keywords    TEXT    NOT NULL DEFAULT '[]',
    content     TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id   INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    question     TEXT    NOT NULL,
    consulted_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

# ── Helpers ────────────────────────────────────────────────────────────────

_YAML_FRONTMATTER_RE = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n(.*)",
    re.DOTALL,
)


def _parse_markdown_file(path: Path) -> dict[str, Any] | None:
    """Parse un fichier .md avec frontmatter YAML.

    Retourne un dict avec les clés ``title``, ``category``, ``keywords``,
    ``content`` ou ``None`` si le fichier est invalide.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    match = _YAML_FRONTMATTER_RE.match(raw)
    if not match:
        # Fichier sans frontmatter → utiliser le nom du fichier comme titre
        title = path.stem.replace("-", " ").replace("_", " ").title()
        return {
            "title": title,
            "category": path.parent.name,
            "keywords": json.dumps([]),
            "content": raw.strip(),
        }

    frontmatter_raw = match.group(1)
    body = match.group(2).strip()

    # Parsing YAML minimal (sans dépendance externe)
    frontmatter: dict[str, Any] = {}
    for line in frontmatter_raw.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip().strip('"').strip("'")

        if key == "keywords":
            # Supporte [mot1, mot2] ou "mot1, mot2"
            if value.startswith("[") and value.endswith("]"):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    value = [v.strip() for v in value[1:-1].split(",") if v.strip()]
            else:
                value = [v.strip() for v in value.split(",") if v.strip()]
            frontmatter[key] = json.dumps(value, ensure_ascii=False)
        else:
            frontmatter[key] = value

    return {
        "title": frontmatter.get("title", path.stem.replace("-", " ").title()),
        "category": frontmatter.get("category", path.parent.name),
        "keywords": frontmatter.get("keywords", json.dumps([])),
        "content": body,
    }


def _scan_knowledge_files(directory: Path) -> list[Path]:
    """Scanne récursivement les fichiers ``.md`` dans un répertoire."""
    if not directory.is_dir():
        return []
    return sorted(directory.rglob("*.md"))


# ── Classe principale ──────────────────────────────────────────────────────


class AideDB:
    """Base de données du bot Aide — articles d'aide et historique.

    Utilisation ::

        db = AideDB()
        db.init_database()           # Crée / importe si nécessaire
        articles = db.search("recherche")
        db.add_history(article_id=1, question="Comment chercher ?")
        history = db.get_history()
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or _DB_PATH
        self._conn: sqlite3.Connection | None = None

    # ── Connexion ───────────────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        """Retourne la connexion (créée à la demande)."""
        if self._conn is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA foreign_keys=ON;")
        return self._conn

    # ── Initialisation / Import ─────────────────────────────────────────

    def init_database(self, knowledge_dir: Path | None = None) -> int:
        """Crée les tables et importe les articles depuis les fichiers .md.

        L'import n'a lieu que si la table ``articles`` est vide.
        Retourne le nombre d'articles importés.
        """
        conn = self._get_conn()

        # Vérification / création du schéma
        cursor = conn.execute("PRAGMA user_version;")
        version = cursor.fetchone()[0]
        if version < _SCHEMA_VERSION:
            conn.executescript(_SQL_CREATE_TABLES)
            conn.execute(f"PRAGMA user_version = {_SCHEMA_VERSION};")
            conn.commit()

        # Import des fichiers .md si la table est vide
        cursor = conn.execute("SELECT COUNT(*) FROM articles;")
        count = cursor.fetchone()[0]
        if count > 0:
            return 0

        knowledge_dir = knowledge_dir or _KNOWLEDGE_DIR
        files = _scan_knowledge_files(knowledge_dir)
        if not files:
            return 0

        imported = 0
        for path in files:
            article = _parse_markdown_file(path)
            if article is None:
                continue
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO articles (category, title, keywords, content)
                       VALUES (?, ?, ?, ?)""",
                    (article["category"], article["title"],
                     article["keywords"], article["content"]),
                )
                if conn.total_changes > 0:
                    imported += 1
            except sqlite3.Error:
                continue

        conn.commit()
        return imported

    # ── Recherche ───────────────────────────────────────────────────────

    def search(self, query: str, limit: int = 20,
                category: str | None = None) -> list[dict[str, Any]]:
        """Cherche des articles par titre ou mot-clé.

        Utilise ``LIKE %query%`` sur les colonnes ``title`` et ``keywords``.
        Les résultats par titre sont prioritaires (classés en premier).

        Si ``category`` est fourni, la recherche est filtrée sur cette catégorie.
        """
        if not query or len(query.strip()) < 2:
            return []

        conn = self._get_conn()
        pattern = f"%{query.strip()}%"
        params_title = [pattern]
        params_keywords = [pattern]

        where_clause = ""
        if category:
            where_clause = " AND category = ?"
            params_title.append(category)
            params_keywords.append(category)

        # Résultats par titre (prioritaires)
        title_rows = conn.execute(
            f"""SELECT id, category, title, keywords,
                       SUBSTR(content, 1, 200) AS excerpt
                FROM articles
                WHERE title LIKE ?{where_clause}
                ORDER BY title ASC
                LIMIT ?""",
            (*params_title, limit),
        ).fetchall()

        # Compléter avec les résultats par mot-clé (déduplication en Python)
        seen = {row["id"] for row in title_rows}
        if len(title_rows) < limit:
            extra = conn.execute(
                f"""SELECT id, category, title, keywords,
                          SUBSTR(content, 1, 200) AS excerpt
                   FROM articles
                   WHERE keywords LIKE ?{where_clause}
                   ORDER BY title ASC""",
                params_keywords,
            ).fetchall()
            for row in extra:
                if row["id"] not in seen:
                    title_rows.append(row)
                    seen.add(row["id"])
                    if len(title_rows) >= limit:
                        break

        return [dict(row) for row in title_rows]

    def find_by_title(self, title: str) -> dict[str, Any] | None:
        """Cherche un article par son titre exact."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM articles WHERE title = ?",
            (title,),
        ).fetchone()
        return dict(row) if row else None

    def find_best_match(self, query: str) -> dict[str, Any] | None:
        """Trouve le meilleur article correspondant à une question.

        Stratégie :
        1. Titre exact → retourne
        2. Titre LIKE %query% → retourne
        3. Keywords LIKE %mot% → retourne
        4. Sinon → None
        """
        if not query or len(query.strip()) < 2:
            return None

        conn = self._get_conn()
        q = query.strip()

        # 1. Titre exact
        row = conn.execute(
            "SELECT * FROM articles WHERE title = ?",
            (q,),
        ).fetchone()
        if row:
            return dict(row)

        # 2. Titre LIKE
        pattern = f"%{q}%"
        row = conn.execute(
            "SELECT * FROM articles WHERE title LIKE ? LIMIT 1",
            (pattern,),
        ).fetchone()
        if row:
            return dict(row)

        # 3. Keywords — découpage en mots significatifs
        words = [w.lower() for w in q.split() if len(w) > 2]
        for word in words:
            kw_pattern = f"%{word}%"
            row = conn.execute(
                "SELECT * FROM articles WHERE keywords LIKE ? LIMIT 1",
                (kw_pattern,),
            ).fetchone()
            if row:
                return dict(row)

        # 4. Chercher chaque mot dans le titre
        for word in words:
            word_pattern = f"%{word}%"
            row = conn.execute(
                "SELECT * FROM articles WHERE title LIKE ? LIMIT 1",
                (word_pattern,),
            ).fetchone()
            if row:
                return dict(row)

        return None

    # ── Historique ──────────────────────────────────────────────────────

    def add_history(self, article_id: int, question: str) -> int:
        """Enregistre une consultation dans l'historique.

        Retourne l'ID de l'entrée créée.
        """
        conn = self._get_conn()
        cursor = conn.execute(
            "INSERT INTO history (article_id, question) VALUES (?, ?)",
            (article_id, question),
        )
        conn.commit()
        last_id = cursor.lastrowid
        return last_id if last_id is not None else 0

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retourne l'historique des consultations, du plus récent au plus ancien.

        Chaque entrée contient les champs de ``history`` joints au ``title``
        de l'article.
        """
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT h.id, h.article_id, h.question, h.consulted_at,
                      a.title, a.category
               FROM history h
               JOIN articles a ON a.id = h.article_id
               ORDER BY h.consulted_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def delete_history_entry(self, entry_id: int) -> bool:
        """Supprime une entrée de l'historique.

        Retourne ``True`` si une ligne a été supprimée.
        """
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM history WHERE id = ?", (entry_id,))
        conn.commit()
        return cursor.rowcount > 0

    def clear_history(self) -> int:
        """Vide tout l'historique.

        Retourne le nombre d'entrées supprimées.
        """
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM history")
        conn.commit()
        return cursor.rowcount

    # ── Gestion des articles ────────────────────────────────────────────

    def get_article(self, article_id: int) -> dict[str, Any] | None:
        """Retourne un article par son ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM articles WHERE id = ?",
            (article_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_all_articles(self, category: str | None = None) -> list[dict[str, Any]]:
        """Retourne tous les articles, optionnellement filtrés par catégorie."""
        conn = self._get_conn()
        if category:
            rows = conn.execute(
                "SELECT id, category, title, keywords, SUBSTR(content, 1, 200) AS excerpt FROM articles WHERE category = ? ORDER BY title",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, category, title, keywords, SUBSTR(content, 1, 200) AS excerpt FROM articles ORDER BY category, title",
            ).fetchall()
        return [dict(row) for row in rows]

    def get_categories(self) -> list[str]:
        """Retourne la liste des catégories uniques."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT DISTINCT category FROM articles ORDER BY category"
        ).fetchall()
        return [row["category"] for row in rows]

    def count_articles(self) -> int:
        """Retourne le nombre total d'articles."""
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) AS cnt FROM articles").fetchone()
        return row["cnt"] if row else 0

    def get_article_counts(self) -> dict[str, int]:
        """Retourne le nombre d'articles par catégorie (``{category: count}``).

        Utilise une seule requête ``GROUP BY`` plutôt que N appels
        individuels à ``get_all_articles``.
        """
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT category, COUNT(*) AS cnt FROM articles GROUP BY category"
        ).fetchall()
        return {row["category"]: row["cnt"] for row in rows}

    # ── Fermeture ───────────────────────────────────────────────────────

    def close(self) -> None:
        """Ferme proprement la connexion SQLite."""
        if self._conn is not None:
            self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            self._conn.close()
            self._conn = None

    def __del__(self) -> None:
        """Filet de sécurité : ferme la connexion SQLite si oubliée."""
        try:
            self.close()
        except Exception:
            pass
