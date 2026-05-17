"""
Zones de l'interface aioslsk, assemblées dans entry.py.
Chaque zone est un fichier indépendant.
"""

from src.gui.layout.center import CenterZone
from src.gui.layout.footer import FooterZone
from src.gui.layout.header import HeaderZone
from src.gui.layout.left import LeftZone
from src.gui.layout.right import RightZone

__all__ = [
    "HeaderZone",
    "FooterZone",
    "LeftZone",
    "CenterZone",
    "RightZone",
]
