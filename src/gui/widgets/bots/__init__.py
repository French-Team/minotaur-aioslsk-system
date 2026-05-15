"""
Bots de l'interface aioslsk — L'Armée des 12 Bots.
Chaque bot est une classe indépendante héritant de QFrame.
"""

from __future__ import annotations

from src.gui.widgets.bots.bot_accueil import BotAccueil
from src.gui.widgets.bots.bot_wishlist import BotWishlist
from src.gui.widgets.bots.bot_recherche import BotRecherche
from src.gui.widgets.bots.bot_bibliotheque import BotBibliotheque
from src.gui.widgets.bots.bot_optimiseur import BotOptimiseur


__all__: list[str] = [
    "BotAccueil",
    "BotWishlist",
    "BotRecherche",
    "BotBibliotheque",
    "BotOptimiseur",
]
