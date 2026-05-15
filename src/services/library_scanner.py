"""Scan threadé de la bibliothèque avec progression.

``LibraryScanner`` est un ``QObject`` qui wrappe ``LibraryDB.scan_all()``
dans un ``QThread`` et émet des signaux pour que l'UI reste responsive.

Architecture ::

    BotBibliotheque (UI)
        |  scan_started / scan_progress / scan_completed / scan_error
        v
    LibraryScanner (QObject)
        |  crée un _ScanWorker dans un QThread
        v
    LibraryDB (SQLite + scan disque)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from src.services.library_db import IGNORED_EXTENSIONS, LibraryDB, ScanResult

logger = logging.getLogger(__name__)


# ── Worker interne ──────────────────────────────────────


class _ScanWorker(QObject):
    """Worker qui exécute le scan dans un thread séparé.

    Signaux :
        finished   — émis quand le scan est terminé (ou annulé)
        completed  — émis avec le ScanResult
        progress   — émis avec (processed, total) pour la barre de progression
        error      — émis en cas d'exception
    """

    finished = Signal()
    completed = Signal(object)  # ScanResult
    progress = Signal(int, int)  # processed, total
    error = Signal(str)

    def __init__(self, db: LibraryDB) -> None:
        super().__init__()
        self._db = db
        self._cancelled = False

    def run(self) -> None:
        """Point d'entrée — exécuté dans le QThread."""
        try:
            # Compter le nombre total de fichiers pour la progression
            total = self._count_files()

            if self._cancelled:
                self.finished.emit()
                return

            # Wrapper le callback de progression pour émettre via Signal
            def _progress_cb(current: int, _total: int | None) -> None:
                if not self._cancelled:
                    self.progress.emit(current, total)

            result = self._db.scan_all(progress_callback=_progress_cb)

            if not self._cancelled:
                self.completed.emit(result)
        except Exception as exc:
            logger.exception("Erreur pendant le scan threadé")
            if not self._cancelled:
                self.error.emit(str(exc))
        finally:
            self.finished.emit()

    def cancel(self) -> None:
        """Demande l'annulation du scan en cours."""
        self._cancelled = True

    def _count_files(self) -> int:
        """Compte le nombre total de fichiers à scanner.

        Itère rapidement sur tous les dossiers partagés pour estimer
        la progression.
        """
        total = 0
        try:
            folders = self._db.get_folders()
            for folder in folders:
                if self._cancelled:
                    return total
                ppath = Path(folder["path"])
                if ppath.is_dir():
                    for f in ppath.rglob("*"):
                        if f.is_file() and f.suffix.lower() not in IGNORED_EXTENSIONS:
                            total += 1
        except Exception:
            logger.warning("Impossible de compter les fichiers", exc_info=True)
        return total


# ── Scanner principal ────────────────────────────────────


class LibraryScanner(QObject):
    """Scan threadé de la bibliothèque avec signaux de progression.

    Utilisation typique ::

        scanner = LibraryScanner()
        scanner.scan_started.connect(self._on_scan_started)
        scanner.scan_progress.connect(self._on_scan_progress)
        scanner.scan_completed.connect(self._on_scan_completed)
        scanner.scan_error.connect(self._on_scan_error)
        scanner.start_scan()

    Signaux :
        scan_started   — émis quand le scan commence
        scan_progress  — émis avec (processed, total) pendant le scan
        scan_completed — émis avec l'objet ScanResult à la fin
        scan_error     — émis avec le message d'erreur en cas de problème
    """

    scan_started = Signal()
    scan_progress = Signal(int, int)  # processed, total
    scan_completed = Signal(object)  # ScanResult
    scan_error = Signal(str)

    def __init__(self, db: Optional[LibraryDB] = None, parent: Optional[QObject] = None) -> None:
        """Initialise le scanner.

        Args:
            db: Instance partagée de LibraryDB. Crée une instance par défaut
                si non fournie.
            parent: QObject parent optionnel.
        """
        super().__init__(parent)
        self._db = db or LibraryDB()
        self._worker: Optional[_ScanWorker] = None
        self._thread: Optional[QThread] = None
        self._running = False

    @property
    def is_running(self) -> bool:
        """Retourne ``True`` si un scan est en cours."""
        return self._running

    def start_scan(self) -> None:
        """Lance le scan de tous les dossiers activés dans un thread séparé.

        Si un scan est déjà en cours, cette méthode ne fait rien.
        """
        if self._running:
            logger.warning("Scan déjà en cours, ignoré")
            return

        self._running = True
        self._cancelled = False

        # Créer le thread et le worker
        self._thread = QThread(self)
        self._worker = _ScanWorker(self._db)
        self._worker.moveToThread(self._thread)

        # Connecter les signaux
        self._worker.progress.connect(self.scan_progress)
        self._worker.completed.connect(self._on_worker_completed)
        self._worker.error.connect(self._on_worker_error)
        self._worker.finished.connect(self._on_worker_finished)

        # Cycle de vie du thread
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self.scan_started.emit()
        self._thread.start()

    def cancel(self) -> None:
        """Annule le scan en cours.

        Le thread existant termine proprement (le worker vérifie
        ``_cancelled`` entre les dossiers).
        """
        if self._worker:
            self._worker.cancel()
        self._cancelled = True

    # ── Handlers internes ──────────────────────────────────

    def _on_worker_completed(self, result: ScanResult) -> None:
        """Relaye le ScanResult au signal public."""
        if not self._cancelled:
            self.scan_completed.emit(result)

    def _on_worker_error(self, message: str) -> None:
        """Relaye l'erreur au signal public."""
        if not self._cancelled:
            self.scan_error.emit(message)

    def _on_worker_finished(self) -> None:
        """Nettoie l'état après la fin du thread."""
        self._worker = None
        self._thread = None
        self._running = False
