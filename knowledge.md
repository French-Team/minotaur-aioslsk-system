# Project knowledge

This file gives Freebuff context about your project: goals, commands, conventions, and gotchas.

## What this is
Application GUI PySide6 pour le client Soulseek (aioslsk).

## Quickstart
- **Lancer l'application :** `python -m src.main`
- **Fichier de config :** `config.toml` à la racine

## Key directories
| Path | Purpose |
|------|---------|
| `src/gui/` | Interface graphique PySide6 |
| `src/gui/layout/` | Layout principal (center, left, right, footer) |
| `src/gui/widgets/bots/` | Widgets bots (clients actifs, téléchargement, surveillance, etc.) |
| `src/services/` | Backend services |
| `src/gui/theme_fragments/colors.py` | Palette de couleurs centralisée + fonction `rgba()` |
| `.in_out/.OUT-live_progression.md` | Carnet de bord du projet |

## ⚠️ RÈGLE ABSOLUE — Couleurs Qt

Qt **ne supporte PAS** les formats hexadécimaux suivants dans les stylesheets et QColor :

| Format | Exemple | Qt ? |
|--------|---------|------|
| `#RGB` (3 chiffres) | `#aaa`, `#fff`, `#888`, `#999` | ❌ NON |
| `#RRGGBBAA` (8 chiffres) | `#00e67644`, `#ff525244` | ❌ NON |
| `#RRGGBB` (6 chiffres) | `#aaaaaa`, `#ffffff` | ✅ OUI |
| `rgba(r, g, b, a)` | `rgba(0, 230, 118, 0.267)` | ✅ OUI |

**Règles :**
1. Toujours utiliser `#RRGGBB` (6 chiffres) — jamais `#RGB` (3 chiffres)
2. Pour les couleurs avec alpha, utiliser la fonction `rgba()` de `src.gui.theme_fragments.colors` — jamais `#RRGGBBAA`
3. Ne jamais concaténer `{variable}44` pour faire de l'alpha — utiliser `rgba(variable, '44')`
4. `rgba()` est importable : `from src.gui.theme_fragments.colors import COLORS, rgba`

## ⚠️ RÈGLE ABSOLUE — Palette centralisée

Ne **JAMAIS** coder des couleurs hexadécimales en dur dans un widget.
Toutes les couleurs doivent utiliser le dictionnaire `COLORS` de
`src.gui.theme_fragments.colors`.

### Comment faire (✅) :
```python
from src.gui.theme_fragments.colors import COLORS

# Stylesheet
btn.setStyleSheet(f"background: {COLORS['ACCENT']}; color: {COLORS['TEXT_WHITE']};")

# QColor direct
item.setForeground(QColor(COLORS["TEXT_PRIMARY"]))

# Constantes de classe dérivées de COLORS
_COULEUR_ACTIF = QColor(COLORS["SUCCESS"])
```

### Ne PAS faire (❌) :
```python
btn.setStyleSheet("background: #362511; color: #ffffff;")   # ❌ en dur
item.setForeground(QColor("#e0e0e0"))                       # ❌ en dur
```

### Palette disponible (clés principales) :
- `SUCCESS`, `WARNING`, `DANGER` — couleurs sémantiques
- `TEXT_PRIMARY`, `TEXT_SECONDARY`, `TEXT_MUTED`, `TEXT_PLACEHOLDER` — texte
- `BG_INPUT`, `BG_SURFACE`, `BG_SIDE`, `BG_HEADER` — fonds
- `BG_TABLE_ALT`, `BG_TABLE_SELECTED`, `BG_TABLE_HEADER` — tableaux
- `BORDER`, `BORDER_LIGHT`, `BORDER_TABLE_HDR` — bordures
- `ACCENT`, `ACCENT_HOVER` — accent principal
- Voir `src/gui/theme_fragments/colors.py` pour la liste complète

### Ajouter une couleur :
Si une nouvelle couleur est nécessaire, l'ajouter dans `colors.py` avec
une clé descriptive — pas en dur dans le widget.

## Architecture GUI
- Layout principal dans `src/gui/layout/` (center.py, left.py, footer.py, right.py)
- Bots/widgets dans `src/gui/widgets/bots/`
- Chaque bot suit le pattern : classe `BotXxx(QFrame)` avec `setup(service)` et signaux Qt

## Conventions
- **Langue :** français (noms de variables/méthodes en français)
- **Code :** Python 3.12+, type hints, PySide6
- **Signaux :** `Signal(...)` avec types stricts, pas de `object` sauf nécessité
- **Bots :** méthode `setup()` avec flag `_setup_done`, connexion aux signaux service

## Things to avoid
- Ne JAMAIS utiliser `#RGB` (3 chiffres) ou `#RRGGBBAA` (8 chiffres) dans les couleurs Qt
- Ne pas lancer de commandes destructives (git push, git commit) sans demande explicite
- Ne pas modifier les specs sans demande explicite
