"""Décorateur @log_action — tracer les clics sur les boutons dans tous les widgets.

Usage :
    from src.utils.log_action import log_action

    class MonWidget(QFrame):
        @log_action("Démarrer la recherche")
        def _on_search(self) -> None:
            ...
"""

from __future__ import annotations

import functools
import logging

logger = logging.getLogger("[ACTION-LOG]")


def log_action(action_name: str):
    """Décorateur qui logge un [ACTION] avant d'exécuter la méthode.

    Paramètres
    ----------
    action_name : str
        Nom lisible de l'action (ex: "Démarrer la recherche", "Arrêter le scan").

    Exemple
    -------
        @log_action("Démarrer la recherche")
        def _on_search(self) -> None:
            ...

    Le log apparaît dans l'onglet Flux des Logs du ServiceInspector
    avec le format : ``[ACTION-LOG] [ACTION] <action_name>``.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            logger.info("[ACTION] %s", action_name)
            return func(self, *args, **kwargs)
        return wrapper
    return decorator
