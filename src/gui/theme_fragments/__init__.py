"""Regroupe tous les fragments CSS en un seul template avec placeholders."""

from .base import CSS as _CSS_base
from .bibliotheque import CSS as _CSS_bibliotheque
from .clients import CSS as _CSS_clients
from .colors import COLORS
from .config import CSS as _CSS_config
from .connexion import CSS as _CSS_connexion
from .downloads import CSS as _CSS_downloads
from .layout import CSS as _CSS_layout
from .misc import CSS as _CSS_misc
from .progression import CSS as _CSS_progression
from .scrollbars import CSS as _CSS_scrollbars

# Concatener tous les fragments dans l'ordre
# Ajoute un saut de ligne entre chaque fragment
TEMPLATE = (
    _CSS_base
    + "\n\n"
    + _CSS_layout
    + "\n\n"
    + _CSS_bibliotheque
    + "\n\n"
    + _CSS_connexion
    + "\n\n"
    + _CSS_progression
    + "\n\n"
    + _CSS_clients
    + "\n\n"
    + _CSS_downloads
    + "\n\n"
    + _CSS_misc
    + "\n\n"
    + _CSS_config
    + "\n\n"
    + _CSS_scrollbars
)

"""
Note: Les placeholders @KEY@ sont remplaces automatiquement
par theme.py via COLORS lors de l'import.
"""

__all__ = ["COLORS", "TEMPLATE"]
