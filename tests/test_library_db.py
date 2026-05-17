"""Tests unitaires pour LibraryDB — base de données de la bibliothèque.

Chaque test utilise une base SQLite sur fichier temporaire (tmp_path)
pour garantir l'isolation et la persistance entre les connexions.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import pytest

from src.services.library_db import (
    DB_PATH,
    IGNORED_EXTENSIONS,
    SCAN_AUDIO_EXTENSIONS,
    SCHEMA_VERSION,
    LibraryDB,
    ScanResult,
    get_schema_version,
)

# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def db(tmp_path: Path) -> LibraryDB:
    """Instance LibraryDB avec une base sur fichier temporaire.

    Chaque test reçoit une base propre isolée dans tmp_path.
    """
    db_file = tmp_path / "test_bibliotheque.db"
    return LibraryDB(db_path=str(db_file))


# ═══════════════════════════════════════════════════════════════════════
# Test de ScanResult
# ═══════════════════════════════════════════════════════════════════════


class TestScanResult:
    """Vérifie le dataclass ScanResult."""

    def test_default_values(self) -> None:
        """Les valeurs par défaut sont à zéro."""
        result = ScanResult()
        assert result.folders_scanned == 0
        assert result.files_found == 0
        assert result.files_new == 0
        assert result.files_removed == 0
        assert result.errors == []
        assert result.duration_ms == 0

    def test_custom_values(self) -> None:
        """Les champs personnalisés sont correctement assignés."""
        result = ScanResult(
            folders_scanned=2,
            files_found=100,
            files_new=10,
            files_removed=3,
            errors=["err1"],
            duration_ms=1500,
        )
        assert result.folders_scanned == 2
        assert result.files_found == 100
        assert result.files_new == 10
        assert result.files_removed == 3
        assert result.errors == ["err1"]
        assert result.duration_ms == 1500


# ═══════════════════════════════════════════════════════════════════════
# Test de l'instanciation et du schéma
# ═══════════════════════════════════════════════════════════════════════


class TestInit:
    """Vérifie que LibraryDB s'initialise correctement."""

    def test_can_instantiate(self, db: LibraryDB) -> None:
        """L'instance est créée."""
        assert db is not None
        assert isinstance(db, LibraryDB)

    def test_default_db_path(self) -> None:
        """Le chemin par défaut est data/bot_bibliotheque.db."""
        instance = LibraryDB()
        assert str(instance._db_path) == str(DB_PATH)

    def test_custom_db_path(self, tmp_path: Path) -> None:
        """Un chemin personnalisé est accepté."""
        custom_path = tmp_path / "test.db"
        instance = LibraryDB(db_path=str(custom_path))
        assert str(instance._db_path) == str(custom_path)

    def test_schema_created_on_init(self, tmp_path: Path) -> None:
        """Le schéma est créé à l'initialisation."""
        db_path = tmp_path / "test_schema.db"
        instance = LibraryDB(db_path=str(db_path))
        conn = instance._connect()
        try:
            version = get_schema_version(conn)
            assert version == SCHEMA_VERSION
        finally:
            conn.close()

    def test_tables_exist(self, db: LibraryDB) -> None:
        """Les tables shared_folders et files sont créées."""
        conn = db._connect()
        try:
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
            table_names = [row[0] for row in tables]
            assert "shared_folders" in table_names
            assert "files" in table_names
        finally:
            conn.close()

    def test_audio_extensions(self, db: LibraryDB) -> None:
        """get_audio_extensions() retourne les extensions audio."""
        exts = db.get_audio_extensions()
        assert ".mp3" in exts
        assert ".flac" in exts
        assert ".wav" in exts


# ═══════════════════════════════════════════════════════════════════════
# Test des dossiers (shared_folders)
# ═══════════════════════════════════════════════════════════════════════


class TestFolders:
    """Vérifie les opérations CRUD sur les dossiers partagés."""

    def test_get_folders_empty(self, db: LibraryDB) -> None:
        """Aucun dossier au démarrage."""
        assert db.get_folders() == []

    def test_add_folder(self, db: LibraryDB) -> None:
        """add_folder() ajoute un dossier et retourne son ID."""
        folder_id = db.add_folder("/tmp/test_music")
        assert folder_id is not None
        assert isinstance(folder_id, int)
        assert folder_id > 0

    def test_add_folder_returns_existing_id(self, db: LibraryDB) -> None:
        """add_folder() retourne le même ID si le dossier existe déjà."""
        id1 = db.add_folder("/tmp/test_music")
        id2 = db.add_folder("/tmp/test_music")
        assert id1 == id2

    def test_get_folders_returns_enabled_only(self, db: LibraryDB) -> None:
        """get_folders() ne retourne que les dossiers activés (enabled=1)."""
        db.add_folder("/tmp/music1")
        db.add_folder("/tmp/music2")
        # Désactiver music2 directement en SQL
        conn = db._connect()
        try:
            conn.execute("UPDATE shared_folders SET enabled = 0 WHERE path = ?", ("/tmp/music2",))
            conn.commit()
        finally:
            conn.close()
        folders = db.get_folders()
        assert len(folders) == 1
        assert folders[0]["path"] == "/tmp/music1"

    def test_get_folder_tree_empty(self, db: LibraryDB) -> None:
        """get_folder_tree() sans dossier retourne une liste vide."""
        assert db.get_folder_tree() == []

    def test_get_folder_tree(self, db: LibraryDB) -> None:
        """get_folder_tree() retourne l'arborescence avec le file_count."""
        db.add_folder("/tmp/music1")
        tree = db.get_folder_tree()
        assert len(tree) == 1
        assert tree[0]["path"] == "/tmp/music1"
        assert "file_count" in tree[0]

    def test_remove_folder(self, db: LibraryDB) -> None:
        """remove_folder() supprime un dossier."""
        folder_id = db.add_folder("/tmp/test_remove")
        assert db.remove_folder(folder_id) is True
        assert db.get_folders() == []

    def test_remove_folder_not_found(self, db: LibraryDB) -> None:
        """remove_folder() retourne False si l'ID n'existe pas."""
        assert db.remove_folder(99999) is False

    def test_remove_folder_cascade_deletes_files(self, db: LibraryDB) -> None:
        """remove_folder() supprime les fichiers enfants via CASCADE."""
        folder_id = db.add_folder("/tmp/test_cascade")
        conn = db._connect()
        try:
            conn.execute(
                "INSERT INTO files (folder_id, path, name, size_bytes) VALUES (?, ?, ?, ?)",
                (folder_id, "/tmp/test_cascade/song.mp3", "song.mp3", 1000),
            )
            conn.execute(
                "INSERT INTO files (folder_id, path, name, size_bytes) VALUES (?, ?, ?, ?)",
                (folder_id, "/tmp/test_cascade/track.flac", "track.flac", 2000),
            )
            conn.commit()
        finally:
            conn.close()
        db.remove_folder(folder_id)
        conn = db._connect()
        try:
            count = conn.execute("SELECT COUNT(*) FROM files WHERE folder_id = ?", (folder_id,)).fetchone()[0]
            assert count == 0
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════
# Test des fichiers
# ═══════════════════════════════════════════════════════════════════════


class TestFiles:
    """Vérifie les opérations sur les fichiers."""

    @pytest.fixture(autouse=True)
    def _setup_files(self, db: LibraryDB) -> None:
        """Crée deux dossiers avec des fichiers pour les tests."""
        self._fid1 = db.add_folder("/tmp/music_rock")
        self._fid2 = db.add_folder("/tmp/music_jazz")
        conn = db._connect()
        try:
            for name, size in [("song1.mp3", 5000), ("song2.mp3", 3000), ("rock_ballad.flac", 15000)]:
                conn.execute(
                    "INSERT INTO files (folder_id, path, name, extension, size_bytes, artist, album, title) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        self._fid1,
                        f"/tmp/music_rock/{name}",
                        name,
                        Path(name).suffix,
                        size,
                        "Rock Band",
                        "Rock Album",
                        name,
                    ),
                )
            for name, size in [("jazz_standard.mp3", 8000), ("smooth_jazz.flac", 12000)]:
                conn.execute(
                    "INSERT INTO files (folder_id, path, name, extension, size_bytes, artist, album, title) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        self._fid2,
                        f"/tmp/music_jazz/{name}",
                        name,
                        Path(name).suffix,
                        size,
                        "Jazz Artist",
                        "Jazz Album",
                        name,
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    def test_get_files_all(self, db: LibraryDB) -> None:
        """get_files() retourne tous les fichiers sans filtre."""
        assert len(db.get_files()) == 5

    def test_get_files_by_folder(self, db: LibraryDB) -> None:
        """get_files(folder_id=...) filtre par dossier."""
        files = db.get_files(folder_id=self._fid1)
        assert len(files) == 3
        for f in files:
            assert f["folder_id"] == self._fid1

    def test_get_files_search(self, db: LibraryDB) -> None:
        """get_files(search=...) filtre par mot-clé."""
        files = db.get_files(search="jazz")
        assert len(files) == 2
        for f in files:
            assert "jazz" in f["name"].lower()

    def test_get_files_search_by_artist(self, db: LibraryDB) -> None:
        """get_files(search=...) cherche aussi dans artist."""
        files = db.get_files(search="Rock Band")
        assert len(files) == 3

    def test_get_files_search_by_album(self, db: LibraryDB) -> None:
        """get_files(search=...) cherche aussi dans album."""
        files = db.get_files(search="Jazz Album")
        assert len(files) == 2

    def test_get_files_sort_name_asc(self, db: LibraryDB) -> None:
        """get_files(sort_by='name', order='ASC') trie par nom croissant."""
        files = db.get_files(sort_by="name", order="ASC")
        names = [f["name"] for f in files]
        assert names == sorted(names)

    def test_get_files_sort_name_desc(self, db: LibraryDB) -> None:
        """get_files(sort_by='name', order='DESC') trie par nom décroissant."""
        files = db.get_files(sort_by="name", order="DESC")
        names = [f["name"] for f in files]
        assert names == sorted(names, reverse=True)

    def test_get_files_sort_size(self, db: LibraryDB) -> None:
        """get_files(sort_by='size_bytes') trie par taille."""
        files = db.get_files(sort_by="size_bytes", order="DESC")
        sizes = [f["size_bytes"] for f in files]
        assert sizes == sorted(sizes, reverse=True)

    def test_get_files_sort_invalid_defaults_to_name(self, db: LibraryDB) -> None:
        """get_files(sort_by='invalid') utilise 'name' par défaut."""
        files = db.get_files(sort_by="invalid_column")
        names = [f["name"] for f in files]
        assert names == sorted(names)

    def test_get_files_folder_and_search(self, db: LibraryDB) -> None:
        """get_files avec folder_id + search combinés."""
        files = db.get_files(folder_id=self._fid1, search="rock")
        # Tous les fichiers du dossier rock contiennent "rock" (insensible)
        # dans artist ("Rock Band") ou album ("Rock Album")
        assert len(files) == 3
        for f in files:
            assert "rock" in f["name"].lower() or "rock" in (f.get("artist") or "").lower()

    def test_get_files_folder_and_search_no_match(self, db: LibraryDB) -> None:
        """get_files avec folder_id + search sans résultat."""
        assert db.get_files(folder_id=self._fid2, search="heavy_metal") == []

    def test_get_files_has_folder_info(self, db: LibraryDB) -> None:
        """get_files() joint les infos du dossier (label, path)."""
        files = db.get_files(folder_id=self._fid1)
        assert len(files) >= 1
        assert "folder_label" in files[0]
        assert "folder_path" in files[0]

    def test_get_file_by_id(self, db: LibraryDB) -> None:
        """get_file() retourne un fichier par son ID."""
        files = db.get_files()
        assert len(files) > 0
        fetched = db.get_file(files[0]["id"])
        assert fetched is not None
        assert fetched["id"] == files[0]["id"]

    def test_get_file_not_found(self, db: LibraryDB) -> None:
        """get_file() retourne None si l'ID n'existe pas."""
        assert db.get_file(99999) is None

    def test_remove_file(self, db: LibraryDB) -> None:
        """remove_file() supprime un fichier de l'index."""
        files = db.get_files()
        before = len(files)
        assert db.remove_file(files[0]["id"]) is True
        assert len(db.get_files()) == before - 1

    def test_remove_file_not_found(self, db: LibraryDB) -> None:
        """remove_file() retourne False si l'ID n'existe pas."""
        assert db.remove_file(99999) is False

    def test_search_basic(self, db: LibraryDB) -> None:
        """search() trouve les fichiers par mot-clé."""
        results = db.search("rock")
        assert len(results) >= 1
        for f in results:
            assert "rock" in f["name"].lower() or "rock" in (f.get("artist") or "").lower()

    def test_search_by_folder(self, db: LibraryDB) -> None:
        """search(query, folder_id) limite à un dossier."""
        results = db.search("mp3", folder_id=self._fid1)
        assert len(results) == 2
        for f in results:
            assert f["folder_id"] == self._fid1

    def test_search_all(self, db: LibraryDB) -> None:
        """search('') retourne tous les fichiers (LIKE '%%')."""
        assert len(db.search("")) == 5


# ═══════════════════════════════════════════════════════════════════════
# Test des statistiques
# ═══════════════════════════════════════════════════════════════════════


class TestStats:
    """Vérifie les statistiques de la bibliothèque."""

    def test_get_stats_empty(self, db: LibraryDB) -> None:
        """get_stats() retourne des zéros si la base est vide."""
        stats = db.get_stats()
        assert stats["folders"] == 0
        assert stats["files"] == 0
        assert stats["audio_files"] == 0
        assert stats["total_size_bytes"] == 0

    def test_get_stats_with_data(self, db: LibraryDB) -> None:
        """get_stats() retourne les valeurs après insertion."""
        db.add_folder("/tmp/music")
        conn = db._connect()
        try:
            conn.execute(
                "INSERT INTO files (folder_id, path, name, extension, size_bytes) "
                "VALUES (1, '/tmp/music/a.mp3', 'a.mp3', '.mp3', 5000)"
            )
            conn.execute(
                "INSERT INTO files (folder_id, path, name, extension, size_bytes) "
                "VALUES (1, '/tmp/music/b.txt', 'b.txt', '.txt', 100)"
            )
            conn.commit()
        finally:
            conn.close()
        stats = db.get_stats()
        assert stats["folders"] == 1
        assert stats["files"] == 2
        assert stats["audio_files"] == 1
        assert stats["total_size_bytes"] == 5100

    def test_get_stat_cards(self, db: LibraryDB) -> None:
        """get_stat_cards() retourne les données formatées."""
        cards = db.get_stat_cards()
        assert len(cards) == 3
        assert cards[0]["label"] == "Dossiers"
        assert cards[1]["label"] == "Fichiers"
        assert cards[2]["label"] == "Audio"
        for card in cards:
            assert "value" in card
            assert "icon" in card


# ═══════════════════════════════════════════════════════════════════════
# Test du scan (scan_folder / scan_all)
# ═══════════════════════════════════════════════════════════════════════


class TestScan:
    """Vérifie le scan de fichiers sur le disque."""

    def test_scan_folder_not_found(self, db: LibraryDB) -> None:
        """scan_folder() retourne -1 si le dossier n'existe pas."""
        assert db.scan_folder("/tmp/dossier_inexistant_xyz") == -1

    def test_scan_folder_empty_dir(self, db: LibraryDB, tmp_path: Path) -> None:
        """scan_folder() sur un dossier vide retourne 0."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        assert db.scan_folder(str(empty_dir)) == 0

    def test_scan_folder_with_files(self, db: LibraryDB, tmp_path: Path) -> None:
        """scan_folder() indexe les fichiers du dossier."""
        music_dir = tmp_path / "music"
        music_dir.mkdir()
        (music_dir / "song.mp3").write_bytes(b"fake mp3 content")
        (music_dir / "track.flac").write_bytes(b"fake flac content")
        assert db.scan_folder(str(music_dir)) == 2

    def test_scan_folder_ignores_extensions(self, db: LibraryDB, tmp_path: Path) -> None:
        """scan_folder() ignore .part, .tmp, .bak, etc."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "real.mp3").write_bytes(b"real")
        (data_dir / "temp.part").write_bytes(b"temp")
        (data_dir / "backup.bak").write_bytes(b"bak")
        assert db.scan_folder(str(data_dir)) == 1  # seulement real.mp3

    def test_scan_folder_deduplicates(self, db: LibraryDB, tmp_path: Path) -> None:
        """scan_folder() ne ré-indexe pas les fichiers déjà présents."""
        music_dir = tmp_path / "dedup"
        music_dir.mkdir()
        (music_dir / "song.mp3").write_bytes(b"content")
        assert db.scan_folder(str(music_dir)) == 1  # premier scan
        assert db.scan_folder(str(music_dir)) == 0  # deuxième scan : aucun nouveau

    def test_scan_folder_removes_deleted_files(self, db: LibraryDB, tmp_path: Path) -> None:
        """scan_folder() nettoie les fichiers disparus du disque."""
        music_dir = tmp_path / "cleanup"
        music_dir.mkdir()
        (music_dir / "exists.mp3").write_bytes(b"content")
        (music_dir / "todelete.mp3").write_bytes(b"content")
        assert db.scan_folder(str(music_dir)) == 2

        # Supprimer un fichier du disque
        os.remove(str(music_dir / "todelete.mp3"))
        assert db.scan_folder(str(music_dir)) == 0  # pas de nouveaux

        files = db.get_files()
        names = [f["name"] for f in files]
        assert "todelete.mp3" not in names
        assert "exists.mp3" in names

    def test_scan_folder_updates_scanned_at(self, db: LibraryDB, tmp_path: Path) -> None:
        """scan_folder() met à jour scanned_at du dossier."""
        data_dir = tmp_path / "scantime"
        data_dir.mkdir()
        (data_dir / "file.mp3").write_bytes(b"data")
        db.scan_folder(str(data_dir))
        tree = db.get_folder_tree()
        assert len(tree) == 1
        assert tree[0]["scanned_at"] is not None

    def test_scan_folder_progress_callback(self, db: LibraryDB, tmp_path: Path) -> None:
        """scan_folder() appelle progress_callback."""
        data_dir = tmp_path / "progress"
        data_dir.mkdir()
        for i in range(3):
            (data_dir / f"track{i}.mp3").write_bytes(b"data")
        calls: list[tuple[int, int | None]] = []

        def callback(processed: int, total: int | None) -> None:
            calls.append((processed, total))

        db.scan_folder(str(data_dir), progress_callback=callback)
        assert len(calls) >= 3

    def test_scan_all_no_folders(self, db: LibraryDB) -> None:
        """scan_all() sans dossiers enregistrés retourne un ScanResult vide."""
        result = db.scan_all()
        assert isinstance(result, ScanResult)
        assert result.folders_scanned == 0

    def test_scan_all_with_folders(self, db: LibraryDB, tmp_path: Path) -> None:
        """scan_all() scanne tous les dossiers activés."""
        for name in ["scan1", "scan2"]:
            d = tmp_path / name
            d.mkdir()
            (d / f"{name}_file.mp3").write_bytes(b"data")
            db.add_folder(str(d))
        result = db.scan_all()
        assert result.folders_scanned == 2
        assert result.files_found == 2
        assert result.files_new == 2

    def test_scan_all_progress_callback(self, db: LibraryDB, tmp_path: Path) -> None:
        """scan_all() appelle progress_callback avec le total cumulé."""
        d = tmp_path / "prog"
        d.mkdir()
        (d / "a.mp3").write_bytes(b"a")
        db.add_folder(str(d))
        calls: list[tuple[int, int]] = []

        def callback(processed: int, total: int) -> None:
            calls.append((processed, total))

        db.scan_all(progress_callback=callback)
        assert len(calls) >= 1


# ═══════════════════════════════════════════════════════════════════════
# Test des helpers (tags, formats)
# ═══════════════════════════════════════════════════════════════════════


class TestHelpers:
    """Vérifie les méthodes statiques utilitaires."""

    def test_get_tag_found(self) -> None:
        """_get_tag() trouve un tag existant."""
        assert LibraryDB._get_tag({"artist": "Test Artist"}, "artist") == "Test Artist"

    def test_get_tag_not_found(self) -> None:
        """_get_tag() retourne None si le tag n'existe pas."""
        assert LibraryDB._get_tag({"title": "Test"}, "artist") is None

    def test_get_tag_with_various_cases(self) -> None:
        """_get_tag() essaie capitalize, upper, etc."""
        assert LibraryDB._get_tag({"ARTIST": "Uppercase"}, "artist") == "Uppercase"

    def test_get_tag_with_text_attr(self) -> None:
        """_get_tag() gère les objets avec attribut .text (mutagen)."""

        class MockTag:
            def __init__(self, text: list[str]):
                self.text = text

        assert LibraryDB._get_tag({"artist": MockTag(["Tagged Artist"])}, "artist") == "Tagged Artist"

    def test_get_tag_empty_text(self) -> None:
        """_get_tag() retourne None si .text est vide."""

        class MockTag:
            def __init__(self, text: list[str]):
                self.text = text

        assert LibraryDB._get_tag({"artist": MockTag([])}, "artist") is None

    def test_get_tag_int_valid(self) -> None:
        """_get_tag_int() extrait un entier."""
        assert LibraryDB._get_tag_int({"tracknumber": "3"}, "tracknumber") == 3

    def test_get_tag_int_with_slash(self) -> None:
        """_get_tag_int() gère '1/10'."""
        assert LibraryDB._get_tag_int({"tracknumber": "1/10"}, "tracknumber") == 1

    def test_get_tag_int_none(self) -> None:
        """_get_tag_int() retourne None si le tag n'existe pas."""
        assert LibraryDB._get_tag_int({}, "tracknumber") is None

    def test_get_tag_int_invalid(self) -> None:
        """_get_tag_int() retourne None si valeur invalide."""
        assert LibraryDB._get_tag_int({"tracknumber": "N/A"}, "tracknumber") is None


# ═══════════════════════════════════════════════════════════════════════
# Test des constantes
# ═══════════════════════════════════════════════════════════════════════


class TestConstants:
    """Vérifie les constantes du module."""

    def test_audio_extensions(self) -> None:
        """SCAN_AUDIO_EXTENSIONS contient les extensions audio courantes."""
        expected = {".mp3", ".flac", ".ogg", ".m4a", ".wav", ".wma", ".aac", ".opus", ".aiff", ".ape"}
        assert SCAN_AUDIO_EXTENSIONS == expected

    def test_ignored_extensions(self) -> None:
        """IGNORED_EXTENSIONS contient les extensions à ignorer."""
        expected = {".part", ".tmp", ".bak", ".lnk", ".url", ".ds_store", ".thumbs.db"}
        assert IGNORED_EXTENSIONS == expected


# ═══════════════════════════════════════════════════════════════════════
# Test du singleton get_library_db
# ═══════════════════════════════════════════════════════════════════════


class TestSingleton:
    """Vérifie le singleton get_library_db()."""

    def test_get_library_db_returns_instance(self) -> None:
        """get_library_db() retourne une instance de LibraryDB."""
        import src.services.library_db as lib_db_mod

        lib_db_mod._library_db_instance = None
        instance = lib_db_mod.get_library_db()
        assert isinstance(instance, LibraryDB)

    def test_get_library_db_singleton(self) -> None:
        """get_library_db() retourne toujours la même instance."""
        import src.services.library_db as lib_db_mod

        lib_db_mod._library_db_instance = None
        i1 = lib_db_mod.get_library_db()
        i2 = lib_db_mod.get_library_db()
        assert i1 is i2
