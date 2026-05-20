---
title: "Système de thème et personnalisation de l'interface"
category: "technique"
icon: "🎨"
keywords:
  - theme application soulseek
  - thème application soulseek
  - personnalisation interface
  - theme fragments
  - DARK_THEME
  - COLORS palette
  - couleurs interface
  - QSS theme
  - feuille de style dynamique
  - theme fragments base
  - theme fragments layout
  - theme fragments bibliotheque
  - theme fragments connexion
  - theme fragments progression
  - theme fragments clients
  - theme fragments downloads
  - theme fragments misc
  - theme fragments config
  - theme fragments scrollbars
  - palette couleurs soulseek
  - personnaliser couleurs application
  - theme sombre soulseek
  - BG_MAIN BG_DARK BG_CENTER
  - PRIMARY TEXT_PRIMARY
  - theme fragments ordre
  - GENERATION THEME
  - remplacement placeholder theme
  - @KEY@ theme
  - fichier theme.py
  - theme apply
  - setStyleSheet theme
  - QSS personnalise
  - theme fragments couleurs
  - theme fragments styles
  - thème fragments styles
  - theme interface
  - personnalisation visuelle
  - couleurs hex theme
  - rgba theme
  - theme sombre
  - theme fonce
  - personnaliser theme
  - changer couleurs
  - modifier theme
  - theme fragments base layout
  - theme scrollbar
  - thème scrollbar
  - theme progression bar
  - theme boutons
  - theme navigation
  - theme configuration
  - theme bibliotheque
  - theme clients actifs
  - theme telechargements
  - theme connexion
  - 1189 lignes theme
---


# 🎨 Système de thème et personnalisation de l'interface

Cet article technique détaille l'architecture du système de thème de l'application, qui repose sur un mécanisme de **fragments QSS** avec **remplacement dynamique de placeholders** par une palette centralisée de couleurs.

---

## 🏗️ Architecture générale

Le système de thème est structuré en trois couches :

```
src/gui/
├── theme.py                      # Point d'entrée : génération du QSS final
└── theme_fragments/
    ├── __init__.py               # Assembleur : concaténation de tous les fragments
    ├── colors.py                 # Palette : dictionnaire COLORS + utilitaire rgba()
    ├── base.py                   # Styles fondamentaux (fenêtre, boutons, listes, menus)
    ├── layout.py                 # Disposition (zones, navigation, poignées)
    ├── bibliotheque.py           # Bot Bibliothèque (stat cards, arbre, popup)
    ├── connexion.py              # Page de connexion (en-tête, avatar)
    ├── progression.py            # Barres de progression
    ├── clients.py                # Panneau clients actifs
    ├── downloads.py              # Gestion des téléchargements
    ├── misc.py                   # Divers (horloge, onglets salons)
    ├── config.py                 # Configuration (lignes, toggles, champs, combos)
    └── scrollbars.py             # Barres de défilement
```

**Total : 1 189 lignes** réparties entre le point d'entrée (15 lignes) et les 11 fragments (1 174 lignes).

### Flux de génération

```
colors.py (COLORS dict)
    │
    ▼
fragments/*.py (CSS avec @KEY@)
    │
    ▼
theme_fragments/__init__.py (concatène → TEMPLATE)
    │
    ▼
theme.py (remplace @KEY@ → DARK_THEME)
    │
    ▼
main_window.py (setStyleSheet)
```

---

## 🎨 Palette de couleurs (`colors.py`)

Le fichier `colors.py` (82 lignes) définit un dictionnaire `COLORS` contenant **toutes les couleurs** de l'application sous forme de codes hexadécimaux, ainsi qu'une fonction utilitaire `rgba()` pour générer des variantes semi-transparentes.

### Structure du dictionnaire COLORS

#### Arrière-plans (BG)

| Clé | Valeur | Usage |
|-----|--------|-------|
| `BG_MAIN` | `#0f0f13` | Fond principal de la fenêtre |
| `BG_DARK` | `#0a0a0f` | Fond le plus sombre |
| `BG_CENTER` | `#111118` | Zone centrale |
| `BG_SIDE` | `#16161e` | Panneaux latéraux |
| `BG_HEADER` | `#1c1c26` | En-tête |
| `BG_SURFACE` | `#1a1a22` | Surfaces (cartes, conteneurs) |
| `BG_SURFACE2` | `#14141e` | Surface alternative |
| `BG_INPUT` | `#1e1e2e` | Champs de saisie |
| `BG_TABLE_HEADER` | `#181825` | En-tête de tableau |
| `BG_TABLE_ALT` | `#222233` | Ligne alternée de tableau |
| `BG_TABLE_SELECTED` | `#3a3a5a` | Ligne sélectionnée |

#### Interactions

| Clé | Valeur | Usage |
|-----|--------|-------|
| `BG_HOVER` | `#24242e` | Survol générique |
| `BG_PRESSED` | `#1e1e28` | Clic maintenu |
| `BG_ROW_HOVER` | `#1a1a28` | Survol de ligne |
| `BG_BTN` | `#2e2e3a` | Bouton normal |
| `BG_BTN_DISABLED` | `#3a3a4a` | Bouton désactivé |
| `BG_BTN_PRESSED` | `#4a4a5a` | Bouton enfoncé |

#### Primaire et accents

| Clé | Valeur | Usage |
|-----|--------|-------|
| `PRIMARY` | `#7E5527` | Couleur principale (orange brun) |
| `PRIMARY_HOVER` | `#5F401C` | Survol principal |
| `PRIMARY_HOVER2` | `#412A0F` | Survol secondaire |
| `PRIMARY_PRESSED` | `#44290B` | Clic principal |
| `ACCENT` | `#362511` | Accent |
| `ACCENT_HOVER` | `#3A2308` | Survol accent |

#### Texte

| Clé | Valeur | Usage |
|-----|--------|-------|
| `TEXT_PRIMARY` | `#e4e4ec` | Texte principal (gris clair) |
| `TEXT_WHITE` | `#ffffff` | Texte blanc |
| `TEXT_SECONDARY` | `#8a8a9a` | Texte secondaire |
| `TEXT_TERTIARY` | `#b0b0c0` | Texte tertiaire |
| `TEXT_SURFACE` | `#a6adc8` | Texte sur surface |
| `TEXT_MUTED` | `#5a5a6a` | Texte atténué |
| `TEXT_DISABLED` | `#6a6a7a` | Texte désactivé |
| `TEXT_PLACEHOLDER` | `#3a3a4a` | Texte indicatif |
| `TEXT_INPUT` | `#cdd6f4` | Texte dans les champs |
| `TEXT_DARK` | `#1a1a1a` | Texte sombre |
| `TEXT_TABLE_HEADER` | `#888888` | En-tête de tableau |

#### Statut

| Clé | Valeur | Usage |
|-----|--------|-------|
| `SUCCESS` | `#00e676` | Succès (vert) |
| `DANGER` | `#ff5252` | Danger/erreur (rouge) |
| `DANGER_HOVER` | `#ff7070` | Survol danger |
| `DANGER_PRESSED` | `#cc3333` | Clic danger |
| `DANGER_BTN` | `#e74c3c` | Bouton danger |
| `WARNING` | `#ffab00` | Attention (jaune) |

#### Bordures et grilles

| Clé | Valeur | Usage |
|-----|--------|-------|
| `GRIDLINE` | `#2a2a3e` | Lignes de grille |
| `BORDER` | `#2e2e3a` | Bordure standard |
| `BORDER_LIGHT` | `#3a3a4a` | Bordure claire |
| `BORDER_HOVER` | `#4a4a5a` | Bordure survolée |
| `BORDER_CONFIG` | `#3a3a5a` | Bordure configuration |
| `BORDER_TABLE_HDR` | `#2a2a3a` | Bordure en-tête tableau |

#### Statistiques

| Clé | Valeur | Usage |
|-----|--------|-------|
| `STAT_FILES` | `#00b894` | Fichiers (vert menthe) |
| `STAT_FILES_HOVER` | `#00a381` | Survol fichiers |
| `STAT_AUDIO` | `#fdcb6e` | Fichiers audio (jaune) |

### Fonction `rgba()`

```python
def rgba(hex_color: str, alpha: float) -> str:
    """Convertit une couleur hex en rgba() pour Qt."""
    # Ex: rgba("#ff5252", 0.1) → "rgba(255, 82, 82, 0.1)"
```

Utilisée dans le dictionnaire `COLORS` pour définir des variantes semi-transparentes (ex: `SUCCESS_BG`, `DANGER_BG`).

---

## 🧩 Fragments de thème

Chaque fragment est une **chaîne CSS** brute contenant des placeholders `@KEY@` qui seront remplacés par les valeurs du dictionnaire `COLORS`.

### Ordre de concaténation

L'assemblage est défini dans `theme_fragments/__init__.py` :

```python
TEMPLATE = "\n\n".join([
    _CSS_base,         # 1. Fondamentaux
    _CSS_layout,       # 2. Disposition
    _CSS_bibliotheque, # 3. Bibliothèque (le plus gros : 372 lignes)
    _CSS_connexion,    # 4. Connexion
    _CSS_progression,  # 5. Progression
    _CSS_clients,      # 6. Clients actifs
    _CSS_downloads,    # 7. Téléchargements
    _CSS_misc,         # 8. Divers
    _CSS_config,       # 9. Configuration
    _CSS_scrollbars,   # 10. Barres de défilement
])
```

L'ordre est important car les fragments peuvent se surcharger mutuellement (le dernier gagne en CSS).

---

### 1. `base.py` (65 lignes) — Fondamentaux

Styles de base pour l'ensemble de l'application :

| Sélecteur | Éléments stylisés |
|-----------|-------------------|
| `QMainWindow` | Fond `BG_MAIN` |
| `QLabel` | Texte `TEXT_PRIMARY`, fond transparent |
| `QPushButton` | États normal / `:hover` / `:pressed` / `:disabled` avec couleurs dédiées |
| `QListWidget::item` | Padding 10px/14px, coins 6px ; sélectionné → fond `BG_HOVER` + texte `PRIMARY` ; survol non sélectionné → fond `BG_HOVER` + texte `TEXT_PRIMARY` |
| `QMenuBar::item:selected` | Fond `BG_HOVER`, texte `TEXT_PRIMARY` |
| `QMenu` | Fond `BG_SURFACE`, bordure |
| `QMenu::item:selected` | Fond `PRIMARY` |
| `QStatusBar` | `border: none` |

### 2. `layout.py` (91 lignes) — Disposition

Styles pour la structure spatiale de l'application :

| Sélecteur | Éléments stylisés |
|-----------|-------------------|
| `#leftZone`, `#rightZone` | Fond `BG_SIDE` |
| `#centerZone` | Fond `BG_CENTER` |
| `#footerZone` | Fond `BG_HEADER` |
| `#collapsibleHeader` | Survol et clic avec couleurs adaptées |
| `#collapsibleContent` | Transparent, sans bordure |
| `#leftHandle`, `#rightHandle` | Fond au survol, flèche passe en `PRIMARY` |
| `#footerNavButton` | État normal / `:hover` / `:checked` (texte `PRIMARY`, bordure accentuée) |
| `#navButton` | Fond transparent, `:hover` et `:checked` → gras + couleur `PRIMARY` |

### 3. `bibliotheque.py` (372 lignes) — Bibliothèque

Le plus gros fragment. Couvre l'intégralité du bot Bibliothèque :

- **Stat Cards** (`#statCard`, `#statCardValue`, `#statCardLabel`) : Métriques (fond surface, valeur 24px grasse, label 11px atténué)
- **Toolbar** (`#bibliothequeToolbar`, `#bibliothequeSearch`, `#bibliothequeProgress`, `#bibliothequeRescan`) : Barre d'outils avec champ de recherche stylisé et barre de progression
- **FileInfoPopup** (`#fileInfoPopup`, `#fileInfoTitle`, etc.) : Popup d'info fichier avec boutons lecture/suppression/fermeture
- Arbre (`QTreeWidget`), tableau (`QTableWidget`), et divers éléments spécifiques à la bibliothèque

### 4. `connexion.py` (35 lignes) — Connexion

Page de connexion Soulseek :

| Sélecteur | Éléments stylisés |
|-----------|-------------------|
| `#connexionHeader` | Fond `BG_SURFACE`, coins 6px, hauteur min 44px, survol → `BG_HOVER` |
| `#headerAvatar` | Fond `BG_BTN_DISABLED`, texte gras, coins 18px, bordure 2px |
| `#headerUsername` | Texte `TEXT_PRIMARY`, 12px gras |

### 5. `progression.py` (38 lignes) — Barres de progression

| Sélecteur | Éléments stylisés |
|-----------|-------------------|
| `#progressionMode` | Texte `TEXT_SECONDARY`, 10px semi-gras |
| `#progressionValue` | Texte `TEXT_PRIMARY`, 15px gras |
| `#progressionBar` | Fond `BG_SURFACE`, bordure `BORDER`, coins 4px, hauteur 8px |
| `#progressionBar::chunk` | Remplissage `PRIMARY`, coins 3px |

### 6. `clients.py` (86 lignes) — Clients actifs

Panneau des clients actifs :

- **En-têtes** : Titres et compteurs avec effet de bordure au survol
- **Conteneurs** : Transparents (`#clientsActifsPage`, `#clientsScroll`, `#clientsListContainer`)
- **Lignes** (`#clientRow`) : Fond `BG_SURFACE2`, bordure arrondie, survol → couleur + bordure changées
- **Boutons** (`#clientsActionBtn`, `#clientsActionBtnDanger`) : Styles normal/danger avec états `:hover`/`:pressed`

### 7. `downloads.py` (137 lignes) — Téléchargements

Interface de gestion des téléchargements :

- **En-tête** (`#telechargementsHeader`) : Survol → valeurs en couleur primaire
- **Lignes** (`#downloadRow`) : Fond `BG_SURFACE2`, survol → `BG_ROW_HOVER`
- **Boutons Annuler/Recommencer** : Couleurs `DANGER`/`WARNING` avec inversion au survol
- **Toolbar** : Boutons avec états `:hover`/`:pressed`
- **Conteneurs** (`#downloadScroll`, `#downloadListContainer`) : Transparents

### 8. `misc.py` (39 lignes) — Divers

Éléments divers :

| Sélecteur | Éléments stylisés |
|-----------|-------------------|
| `#clockLabel` | Police Consolas, 18px gras, couleur `SUCCESS` |
| `#roomsTabs QTabBar::tab` | Fond `BG_SURFACE`, texte `TEXT_MUTED` ; `:selected` → texte `PRIMARY` + bordure primaire ; `:hover:!selected` → fond `BG_HOVER` + texte `TEXT_PRIMARY` |

### 9. `config.py` (133 lignes) — Configuration

Interface de configuration :

- **Lignes** (`#configRow`) : Fond `BG_SURFACE`, bordure, coins 6px, survol → bordure `BORDER_CONFIG`
- **Toggles** (`#configToggle`) : Commutateurs avec état `:checked`/`:unchecked` et animation au survol
- **Champs texte** (`#configEntry`) : Couleurs, bordures, focus → bordure accentuée, placeholder stylisé
- **Listes déroulantes** (`#configCombo`) : Menu déroulant avec sélection stylisée (fond + texte)
- **Boutons radios, checkbox, sliders, zones de texte**, etc.

### 10. `scrollbars.py` (52 lignes) — Barres de défilement

Barres de défilement verticales et horizontales avec une configuration symétrique :

| Élément | Normal | `:hover` | `:pressed` |
|---------|--------|----------|------------|
| Handle | `BG_BTN_DISABLED`, coins 3px, min 15px | `PRIMARY` | `PRIMARY_PRESSED` |
| Sub-line/sub-page | Masqués (height/width: 0) | — | — |

---

## ⚙️ Génération du QSS final (`theme.py`)

```python
from src.gui.theme_fragments import COLORS, TEMPLATE

DARK_THEME = TEMPLATE
for _key, _value in COLORS.items():
    DARK_THEME = DARK_THEME.replace(f"@{_key}@", _value)
```

Ce fichier (15 lignes) :
1. **Importe** `COLORS` (le dictionnaire) et `TEMPLATE` (la concaténation des fragments)
2. **Itère** sur chaque paire clé/valeur de `COLORS`
3. **Remplace** chaque occurrence de `@KEY@` par la valeur hexadécimale correspondante

**Résultat :** Une chaîne QSS complète de ~1 189 lignes stockée dans `DARK_THEME`, prête à être appliquée via `QApplication.setStyleSheet(DARK_THEME)`.

---

## 🔧 Personnalisation

### Modifier une couleur existante

Modifiez la valeur hex dans `colors.py` :
```python
COLORS = {
    "PRIMARY": "#7E5527",       # Orange brun actuel
    # "PRIMARY": "#4a90d9",     # Exemple : bleu
    "BG_MAIN": "#0f0f13",       # Fond très sombre
    # "BG_MAIN": "#1a1a2e",     # Exemple : bleu foncé
}
```

### Ajouter un nouveau sélecteur

1. Ajoutez la couleur dans `COLORS` si nécessaire
2. Ajoutez le CSS avec `@NOUVELLE_COULEUR@` dans le fragment approprié
3. Le placeholder sera automatiquement remplacé à la génération

### Ajouter un nouveau fragment

1. Créez `mon_fragment.py` dans `theme_fragments/`
2. Déclarez `CSS = """..."""` avec les sélecteurs et placeholders
3. Ajoutez l'import et la concaténation dans `__init__.py`

---

## 📊 Statistiques

| Fragment | Lignes | Poids |
|----------|--------|-------|
| `bibliotheque.py` | 372 | 31.3 % |
| `downloads.py` | 137 | 11.5 % |
| `config.py` | 133 | 11.2 % |
| `layout.py` | 91 | 7.7 % |
| `clients.py` | 86 | 7.2 % |
| `colors.py` | 82 | 6.9 % |
| `base.py` | 65 | 5.5 % |
| `scrollbars.py` | 52 | 4.4 % |
| `__init__.py` | 44 | 3.7 % |
| `misc.py` | 39 | 3.3 % |
| `progression.py` | 38 | 3.2 % |
| `connexion.py` | 35 | 2.9 % |
| `theme.py` | 15 | 1.3 % |
| **Total** | **1 189** | **100 %** |

---

## 🔗 Voir aussi

- `/technique/architecture-application` — Architecture générale de l'application
- `/technique/depistage-logs` — Débogage et journaux
- `/faq/parametres-recommandes` — Paramètres recommandés
