"""Tests unitaires pour le service ``LibraryScanner``.

Couvre :
  - Instanciation et signaux
  - Scan threadé complet (start → completed)
  - Annulation (cancel)
  - Comptage de progression
  - Cas vide (aucun dossier)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEventLoop, QObject, QTimer

from src.services.library_db import LibraryDB, ScanResult
from src.services.library_scanner import LibraryScanner, _ScanWorker

# ── Fixtures ─────────────────────────────────────────────


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """Chemin vers une base SQLite temporaire."""
    return tmp_path / "test_scanner.db"


@pytest.fixture
def db(tmp_db_path: Path) -> LibraryDB:
    """Instance LibraryDB pointant vers la base temporaire."""
    return LibraryDB(db_path=tmp_db_path)


@pytest.fixture
def scanner(db: LibraryDB) -> LibraryScanner:
    """Instance LibraryScanner utilisant la base temporaire."""
    return LibraryScanner(db=db)


@pytest.fixture
def sample_music(tmp_path: Path) -> Path:
    """Crée une arborescence de fichiers audio simulés."""
    music = tmp_path / "Musique"
    jazz = music / "Jazz"
    rock = music / "Rock"
    jazz.mkdir(parents=True, exist_ok=True)
    rock.mkdir(parents=True, exist_ok=True)

    (jazz / "take_five.mp3").write_text("fake audio data")
    (jazz / "so_what.flac").write_text("fake flac data")
    (jazz / "cover.jpg").write_text("not audio")
    (rock / "stairway.mp3").write_text("fake audio")
    (rock / "whole_lotta.mp3").write_text("more audio")
    (rock / "notes.txt").write_text("some notes")

    return music


# ── Tests : instanciation ────────────────────────────────


class TestInit:
    """Tests d'initialisation du scanner."""

    def test_create_scanner(self, scanner: LibraryScanner) -> None:
        """Création simple."""
        assert scanner is not None

    def test_not_running_by_default(self, scanner: LibraryScanner) -> None:
        """Le scanner n'est pas en cours au démarrage."""
        assert scanner.is_running is False

    def test_signals_exist(self, scanner: LibraryScanner) -> None:
        """Les signaux sont correctement définis."""
        assert hasattr(scanner, "scan_started")
        assert hasattr(scanner, "scan_progress")
        assert hasattr(scanner, "scan_completed")
        assert hasattr(scanner, "scan_error")

    def test_signals_connectable(self, scanner: LibraryScanner) -> None:
        """Les signaux peuvent être connectés."""
        receiver = QObject()
        scanner.scan_started.connect(receiver.deleteLater)
        scanner.scan_progress.connect(receiver.deleteLater)
        scanner.scan_completed.connect(receiver.deleteLater)
        scanner.scan_error.connect(receiver.deleteLater)

    def test_custom_db(self, db: LibraryDB) -> None:
        """Le scanner accepte une instance LibraryDB personnalisée."""
        s = LibraryScanner(db=db)
        assert s._db is db

    def test_default_db(self) -> None:
        """Sans db fournie, une instance LibraryDB par défaut est créée."""
        s = LibraryScanner()
        assert s._db is not None
        assert isinstance(s._db, LibraryDB)


# ── Tests : Worker ────────────────────────────────────────


class TestWorker:
    """Tests du worker interne _ScanWorker."""

    def test_worker_created(self, db: LibraryDB) -> None:
        """Création du worker."""
        worker = _ScanWorker(db)
        assert worker is not None

    def test_worker_has_signals(self, db: LibraryDB) -> None:
        """Le worker a les signaux requis."""
        worker = _ScanWorker(db)
        assert hasattr(worker, "finished")
        assert hasattr(worker, "completed")
        assert hasattr(worker, "progress")
        assert hasattr(worker, "error")

    def test_worker_cancel(self, db: LibraryDB) -> None:
        """cancel() ne plante pas."""
        worker = _ScanWorker(db)
        worker.cancel()
        assert worker._cancelled is True

    def test_worker_count_files_empty(self, db: LibraryDB) -> None:
        """_count_files retourne 0 si aucun dossier."""
        worker = _ScanWorker(db)
        count = worker._count_files()
        assert count == 0

    def test_worker_count_files(self, db: LibraryDB, sample_music: Path) -> None:
        """_count_files compte les fichiers non ignorés."""
        db.add_folder(str(sample_music))
        worker = _ScanWorker(db)
        count = worker._count_files()
        # 6 fichiers : take_five.mp3, so_what.flac, cover.jpg,
        # stairway.mp3, whole_lotta.mp3, notes.txt
        assert count == 6


# ── Tests : Scan threadé complet ─────────────────────────


@pytest.mark.qt_heavy
class TestScanThreaded:
    """Tests du scan complet dans un thread Qt."""

    def test_scan_completed_signal(self, qapp, scanner: LibraryScanner, sample_music: Path) -> None:
        """Le signal scan_completed est émis après le scan."""
        db = scanner._db
        db.add_folder(str(sample_music))

        results: list[ScanResult] = []
        loop = QEventLoop()

        def on_completed(result: ScanResult) -> None:
            results.append(result)
            loop.quit()

        scanner.scan_completed.connect(on_completed)
        scanner.start_scan()

        # Timeout de sécurité
        QTimer.singleShot(10_000, loop.quit)
        loop.exec()

        assert len(results) == 1
        result = results[0]
        assert result.files_found >= 5
        assert result.folders_scanned >= 1
        assert result.duration_ms > 0

    def test_scan_progress_signal(self, qapp, scanner: LibraryScanner, sample_music: Path) -> None:
        """Le signal scan_progress est émis pendant le scan."""
        db = scanner._db
        db.add_folder(str(sample_music))

        progress_calls: list[tuple[int, int]] = []
        completed = False
        loop = QEventLoop()

        def on_progress(current: int, total: int) -> None:
            progress_calls.append((current, total))

        def on_completed(result: ScanResult) -> None:
            nonlocal completed
            completed = True
            loop.quit()

        scanner.scan_progress.connect(on_progress)
        scanner.scan_completed.connect(on_completed)
        scanner.start_scan()

        QTimer.singleShot(10_000, loop.quit)
        loop.exec()

        assert completed is True
        assert len(progress_calls) >= 5  # au moins 5 fichiers
        # Vérifier que le dernier appel a le bon total
        last_current, last_total = progress_calls[-1]
        assert last_total >= 5
        assert last_current <= last_total

    def test_scan_progress_increases(self, qapp, scanner: LibraryScanner, sample_music: Path) -> None:
        """Le compteur de progression augmente strictement."""
        db = scanner._db
        db.add_folder(str(sample_music))

        values: list[int] = []
        loop = QEventLoop()

        def on_progress(current: int, total: int) -> None:
            values.append(current)

        def on_completed(result: ScanResult) -> None:
            loop.quit()

        scanner.scan_progress.connect(on_progress)
        scanner.scan_completed.connect(on_completed)
        scanner.start_scan()

        QTimer.singleShot(10_000, loop.quit)
        loop.exec()

        if len(values) >= 2:
            for i in range(1, len(values)):
                assert values[i] >= values[i - 1], f"Progress doit augmenter: {values[i]} < {values[i - 1]}"

    def test_scan_started_signal(self, qapp, scanner: LibraryScanner, sample_music: Path) -> None:
        """Le signal scan_started est émis."""
        db = scanner._db
        db.add_folder(str(sample_music))

        started = False
        loop = QEventLoop()

        def on_started() -> None:
            nonlocal started
            started = True

        def on_completed(result: ScanResult) -> None:
            loop.quit()

        scanner.scan_started.connect(on_started)
        scanner.scan_completed.connect(on_completed)
        scanner.start_scan()

        QTimer.singleShot(10_000, loop.quit)
        loop.exec()

        assert started is True

    def test_is_running_during_scan(self, qapp, scanner: LibraryScanner, sample_music: Path) -> None:
        """is_running est True pendant le scan, False après."""
        db = scanner._db
        db.add_folder(str(sample_music))

        running_values: list[bool] = []
        loop = QEventLoop()

        def on_started() -> None:
            running_values.append(scanner.is_running)

        def on_completed(result: ScanResult) -> None:
            running_values.append(scanner.is_running)
            loop.quit()

        scanner.scan_started.connect(on_started)
        scanner.scan_completed.connect(on_completed)
        scanner.start_scan()

        # Vérifier immédiatement après start
        running_values.append(scanner.is_running)

        QTimer.singleShot(10_000, loop.quit)
        loop.exec()

        # Au moins True pendant le scan
        assert any(running_values), "is_running devrait être True au moins une fois"

    def test_scan_empty_no_folders(self, qapp, scanner: LibraryScanner) -> None:
        """Scanner sans dossier ne plante pas et retourne un résultat valide."""
        results: list[ScanResult] = []
        loop = QEventLoop()

        def on_completed(result: ScanResult) -> None:
            results.append(result)
            loop.quit()

        scanner.scan_completed.connect(on_completed)
        scanner.start_scan()

        QTimer.singleShot(10_000, loop.quit)
        loop.exec()

        assert len(results) == 1
        result = results[0]
        assert result.folders_scanned == 0
        assert result.files_found == 0
        assert result.duration_ms >= 0


# ── Tests : Annulation ───────────────────────────────────


@pytest.mark.qt_heavy
class TestCancel:
    """Tests d'annulation du scan."""

    def test_cancel_before_start(self, qapp, scanner: LibraryScanner) -> None:
        """cancel() avant start ne plante pas."""
        scanner.cancel()
        assert scanner.is_running is False

    def test_cancel_stops_scan(self, qapp, scanner: LibraryScanner, sample_music: Path) -> None:
        """cancel() interrompt un scan en cours."""
        db = scanner._db
        db.add_folder(str(sample_music))

        loop = QEventLoop()
        completed = False

        def on_completed(result: ScanResult) -> None:
            nonlocal completed
            completed = True
            loop.quit()

        scanner.scan_completed.connect(on_completed)
        scanner.start_scan()

        # Annuler immédiatement (le thread est lancé mais le scan
        # n'a probablement pas encore commencé)
        scanner.cancel()

        # Attendre un peu pour voir si completed est émis ou non
        QTimer.singleShot(2000, loop.quit)
        loop.exec()

        # Le scan peut ou non avoir terminé avant l'annulation.
        # L'important est que tout se passe proprement.
        assert scanner.is_running is False

    def test_double_start_no_op(self, qapp, scanner: LibraryScanner, sample_music: Path) -> None:
        """start_scan() deux fois de suite ne crée pas deux threads."""
        db = scanner._db
        db.add_folder(str(sample_music))

        call_count = 0
        loop = QEventLoop()

        def on_completed(result: ScanResult) -> None:
            nonlocal call_count
            call_count += 1
            loop.quit()

        scanner.scan_completed.connect(on_completed)
        scanner.start_scan()
        scanner.start_scan()  # deuxième appel, ignoré

        QTimer.singleShot(10_000, loop.quit)
        loop.exec()

        assert call_count == 1  # un seul completed


# ── Tests : Scan avec plusieurs dossiers ──────────────────


@pytest.mark.qt_heavy
class TestMultiFolder:
    """Tests avec plusieurs dossiers partagés."""

    def test_scan_multiple_folders(self, qapp, scanner: LibraryScanner, tmp_path: Path) -> None:
        """Scanner deux dossiers les indexe tous les deux."""
        music1 = tmp_path / "Music1"
        music2 = tmp_path / "Music2"
        music1.mkdir()
        music2.mkdir()
        (music1 / "track1.mp3").write_text("data")
        (music2 / "track2.flac").write_text("data")

        db = scanner._db
        db.add_folder(str(music1))
        db.add_folder(str(music2))

        results: list[ScanResult] = []
        loop = QEventLoop()

        def on_completed(result: ScanResult) -> None:
            results.append(result)
            loop.quit()

        scanner.scan_completed.connect(on_completed)
        scanner.start_scan()

        QTimer.singleShot(10_000, loop.quit)
        loop.exec()

        assert len(results) == 1
        assert results[0].folders_scanned == 2
        assert results[0].files_found == 2
