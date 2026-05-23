"""
Point d'entrée principal — Interface graphique aioslsk (Soulseek).

Lancer depuis la racine du projet :
    python run.py
"""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger("[RUN]")

from datetime import datetime
from pathlib import Path

# ── Crash Reporter : capture & sauvegarde immédiate de tout Traceback ──
from security.crash_reporter import activate as _activate_crash_reporter
_activate_crash_reporter()

from PySide6.QtWidgets import QApplication


# ── Filtre : supprimer le bruit asyncio des connexions P2P ──
class _ConnectionResetFilter(logging.Filter):
    """Filtre les ConnectionResetError / _call_connection_lost de la boucle
    asyncio (bruit P2P normal sur Soulseek — pas de crash réel).

    Ces erreurs sont des déconnexions brutales de pairs distants.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if "_call_connection_lost" in msg:
            return False
        if "ConnectionResetError" in msg:
            return False
        if "WinError 10054" in msg:
            return False
        return True

from src.config import settings
from src.gui.main_window import MainWindow

_LOG_DIR = Path("data/logs")


def _setup_file_logging(logger: logging.Logger) -> None:
    """Ajoute un FileHandler au root logger pour sauvegarder tous les logs.

    Indépendant de ServiceInspector (qui ne capture les logs qu'à partir
    de son initialisation dans MainWindow). Ce handler écrit dès le
    démarrage de ``main()``, donc même un crash précoce a une trace écrite.
    """
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = _LOG_DIR / f"session_{timestamp}.log"
        handler = logging.FileHandler(filepath, encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        ))
        logger.addHandler(handler)
        logger.info("Session log : %s", filepath)
    except Exception as e:
        logger.warning("Impossible de créer le file handler de session : %s", e)


def main() -> None:
    """Lance l'application graphique aioslsk."""
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # ── File handler pour sauvegarde intégrale de la session ──
    _setup_file_logging(logging.getLogger())

    # Réduire le bruit des logs DEBUG internes aioslsk (requêtes distribuées P2P, etc.)
    for logger_name in (
        "aioslsk.network.connection",   # DistributedSearchRequest spam
        "aioslsk.network.network",       # UPnP, connexions peer
        "async_upnp_client.traffic",     # SOAP UPnP brut
        "async_upnp_client.client",
    ):
        logging.getLogger(logger_name).setLevel(logging.ERROR)

    # Filtre plus agressif : masquer les ConnectionResetError P2P
    logging.getLogger("aioslsk.client").addFilter(_ConnectionResetFilter())
    logging.getLogger("aioslsk.client").setLevel(logging.ERROR)

    app = QApplication(sys.argv)
    app.setApplicationName("aioslsk")
    app.setOrganizationName("aioslsk")

    # Style global Qt
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
