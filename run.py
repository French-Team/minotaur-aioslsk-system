"""
Point d'entrée principal — Interface graphique aioslsk (Soulseek).

Lancer depuis la racine du projet :
    python run.py
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from src.config import settings
from src.gui.main_window import MainWindow


def main() -> None:
    """Lance l'application graphique aioslsk."""
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Réduire le bruit des logs DEBUG internes aioslsk (requêtes distribuées P2P, etc.)
    for logger_name in (
        "aioslsk.network.connection",   # DistributedSearchRequest spam
        "aioslsk.network.network",       # UPnP, connexions peer
        "aioslsk.client",                # unhandled exceptions P2P (ConnectionRefused, etc.)
        "async_upnp_client.traffic",     # SOAP UPnP brut
        "async_upnp_client.client",
    ):
        logging.getLogger(logger_name).setLevel(logging.WARNING)

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
