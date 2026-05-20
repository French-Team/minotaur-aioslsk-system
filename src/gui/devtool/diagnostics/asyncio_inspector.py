"""Inspecteur de tâches asyncio — récupération et affichage thread-safe."""

from __future__ import annotations

import asyncio
import logging
import traceback
from concurrent.futures import Future
from typing import Any, Optional

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

logger = logging.getLogger(__name__)

# ── Types ───────────────────────────────────────────────────────────────

TaskInfo = tuple[str, str, str, str]
"""Structure : (nom_tâche, coroutine, état, position_pile)."""


# ── Inspecteur asyncio (thread-safe) ────────────────────────────────────

class AsyncioInspector(QObject):
    """Récupère les tâches asyncio de la boucle du thread de connexion de manière thread-safe.

    Utilise ``asyncio.run_coroutine_threadsafe()`` pour interroger la boucle
    distante sans bloquer le thread UI.

    Signaux :
        tasks_updated(list[TaskInfo]) — émis quand les tâches sont récupérées.
    """

    tasks_updated = Signal(list)  # list[TaskInfo]

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._main_window: Optional[Any] = None  # référence relâchée

    def set_main_window(self, main_window: Any) -> None:
        """Injecte la référence à la fenêtre principale pour accéder au ConnexionManager."""
        self._main_window = main_window

    def _get_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """Retourne la boucle asyncio du thread de connexion, ou None."""
        if self._main_window is None:
            return None
        mgr = getattr(self._main_window, "_connexion_manager", None)
        if mgr is None:
            return None
        thread = getattr(mgr, "_async_thread", None)
        if thread is None:
            return None
        loop: Optional[asyncio.AbstractEventLoop] = getattr(thread, "_loop", None)
        if loop is None or not loop.is_running():
            return None
        return loop

    def fetch_tasks(self) -> bool:
        """Déclenche une récupération asynchrone des tâches sur la boucle distante.

        Retourne ``True`` si la requête a été lancée, ``False`` si la boucle
        n'est pas disponible.
        """
        loop = self._get_loop()
        if loop is None:
            self.tasks_updated.emit([])
            return False

        def query_loop_tasks() -> list[TaskInfo]:
            instances = asyncio.all_tasks(loop)
            results: list[TaskInfo] = []
            for t in instances:
                coro = t.get_coro()
                frame = None
                if hasattr(coro, "cr_frame"):
                    frame = coro.cr_frame
                elif hasattr(coro, "gi_frame"):
                    frame = coro.gi_frame

                stack_str = ""
                if frame:
                    tb = traceback.extract_stack(frame)
                    if tb:
                        f_info = tb[-1]
                        filename = f_info.filename.split("/")[-1].split("\\")[-1]
                        stack_str = f"{filename}:{f_info.lineno} ({f_info.name})"

                results.append((
                    t.get_name(),
                    getattr(coro, "__qualname__", str(coro)),
                    str(getattr(t, "_state", "PENDING")),
                    stack_str,
                ))
            return results

        async def _wrapper() -> list[TaskInfo]:
            return query_loop_tasks()

        def _on_done(future: Future) -> None:
            try:
                result = future.result()
                self.tasks_updated.emit(result)
            except Exception as e:
                logger.debug("Erreur récupération tâches asyncio: %s", e)

        fut = asyncio.run_coroutine_threadsafe(_wrapper(), loop)
        fut.add_done_callback(_on_done)
        return True

    @staticmethod
    def etat_label(etat: str) -> tuple[str, str]:
        """Retourne (label_court, couleur_hex) selon l'état de la tâche."""
        mapping = {
            "PENDING":   ("EN ATTENTE", "#f9e2af"),
            "CANCELLED": ("ANNULÉE",    "#6c7086"),
            "FINISHED":  ("TERMINÉE",   "#a6e3a1"),
            "RUNNING":   ("EXÉCUTION",  "#89b4fa"),
        }
        return mapping.get(etat, (etat, "#cdd6f4"))


# ── Widget d'affichage des tâches asyncio ──────────────────────────────

class AsyncioTasksWidget(QTreeWidget):
    """Widget arborescent pour afficher les tâches asyncio.

    Utilise ``AsyncioInspector`` pour récupérer les tâches de manière
    thread-safe.
    """

    HEADERS = ["Nom de la Tâche", "Coroutine / Cible", "État", "Position / Pile d'appels"]

    def __init__(self, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.setHeaderLabels(self.HEADERS)
        self.setAlternatingRowColors(True)
        # pyrefly: ignore [missing-attribute]
        self.header().setStretchLastSection(True)
        self.setStyleSheet(
            "QTreeWidget {"
            "  background-color: #11111b;"
            "  border: 1px solid #313244;"
            "  border-radius: 4px;"
            "  font-family: 'Consolas', 'Courier New', monospace;"
            "  font-size: 10px;"
            "}"
        )

        self._inspector = AsyncioInspector(self)
        self._inspector.tasks_updated.connect(self._on_tasks)

    def set_main_window(self, main_window: Any) -> None:
        """Injecte la fenêtre principale dans l'inspecteur."""
        self._inspector.set_main_window(main_window)

    def refresh(self) -> None:
        """Déclenche une mise à jour des tâches asyncio."""
        self._inspector.fetch_tasks()

    def _on_tasks(self, tasks: list[TaskInfo]) -> None:
        """Met à jour l'affichage avec les tâches récupérées."""
        self.clear()
        if not tasks:
            item = QTreeWidgetItem(["Aucune tâche asyncio active"])
            item.setForeground(0, QColor("#6c7086"))
            self.addTopLevelItem(item)
            return

        for name, coro, state, position in tasks:
            item = QTreeWidgetItem([name, coro, state, position])
            _, couleur = AsyncioInspector.etat_label(state)
            item.setForeground(2, QColor(couleur))

            # Coloration spé selon le type de tâche
            if "login" in name.lower() or "login" in coro.lower():
                item.setForeground(0, QColor("#f9e2af"))
                item.setForeground(1, QColor("#f9e2af"))
            elif "server-ping" in name:
                item.setForeground(0, QColor("#89b4fa"))
            elif "disconnect" in name.lower():
                item.setForeground(0, QColor("#f38ba8"))

            self.addTopLevelItem(item)
