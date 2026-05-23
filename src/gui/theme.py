"""
Feuille de style globale (QSS) pour l'interface aioslsk.
Point d'entree qui aggrege les fragments CSS du dossier theme_fragments/.
Les couleurs sont centralisees dans theme_fragments/colors.py.
"""

import logging

from src.gui.theme_fragments import COLORS, TEMPLATE

logger = logging.getLogger("[THEME]")


# --- Generation du theme final -----------------------------------
# Remplace les placeholders @KEY@ par les valeurs hex dans COLORS.
_DARK_THEME_TEMPLATE = TEMPLATE

DARK_THEME = _DARK_THEME_TEMPLATE
for _key, _value in COLORS.items():
    DARK_THEME = DARK_THEME.replace(f"@{_key}@", _value)
