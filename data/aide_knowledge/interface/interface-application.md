---
title: "Interface de l'application : layout, navigation et zones"
category: "interface"
tags:
  - interface
  - layout
  - navigation
  - architecture
keywords:
  - MainWindow QMainWindow layout 5 zones
  - LayoutEntry QGridLayout grille
  - LayoutEntry QGridLayout grille 3x3
  - header HeaderZone connexion
  - left LeftZone panneau config
  - left LeftZone panneau configuration
  - center CenterZone QStackedWidget pages
  - right RightZone panneau rooms salons
  - right RightZone panneau rooms salons
  - right RightZone onglets public prive
  - right RightZone onglets public privé
  - footer FooterZone navigation bots
  - footer FooterZone navigation 12 bots
  - footer FooterZone 12 boutons navigation
  - HeaderZone connexion header widget
  - HeaderZone connexion_widget propriete
  - HeaderZone connexion_widget propriété
  - CenterZone show page navigation centrale
  - CenterZone show page navigation centrée
  - CenterZone _pages dictionnaire widgets
  - CenterZone _pages dictionnaire widgets
  - CenterZone _build_config_pages 8 onglets
  - CenterZone _build_config_pages 8 onglets configuration
  - LeftZone panneau retractable
  - LeftZone panneau rétractable
  - LeftZone _SECTIONS 8 sections config
  - LeftZone expand collapse toggle
  - RightZone panneau retractable
  - RightZone panneau rétractable
  - RightZone rooms salons QTabWidget
  - RightZone expand collapse toggle
  - FooterZone _FooterNavButton checkable badge
  - FooterZone _FooterNavButton checkable badge notification
  - FooterZone set_badge mise a jour compteur
  - FooterZone set_badge mise à jour compteur
  - FooterZone page_button acces bouton
  - FooterZone page_button accès bouton
  - LayoutEntry QGridLayout stretch colonnes lignes
  - LayoutEntry QGridLayout 3x3 stretch
  - LayoutEntry signaux page_changed connectes
  - LayoutEntry signaux page_changed connectés
  - LayoutEntry header left center right footer
  - MainWindow _build_menu barre menu
  - MainWindow _build_menu barre menus
  - MainWindow _connect_connexion_manager
  - MainWindow closeEvent fermeture propre
  - MainWindow QssInspector devtool
  - page_changed signal navigation
  - page_changed signal navigation zone
  - QStackedWidget empilage pages
  - QStackedWidget index courant visible
  - zone retractable handle fleche
  - zone rétractable handle flèche
---

# Interface de l'application : layout, navigation et zones

## Vue d'ensemble

L'interface graphique est construite avec **PySide6 (Qt pour Python)** et suit une disposition à 5 zones organisées dans une grille 3×3. La fenêtre principale `MainWindow` (héritant de `QMainWindow`) orchestre l'ensemble via un widget central `LayoutEntry` qui assemble les zones.

```
┌─────────────────────────────────────────────┐
│                 HeaderZone                  │  ← Bannière connexion
├──────┬──────────────────────┬───────────────┤
│      │                      │               │
│ Left │     CenterZone       │   RightZone   │
│ Zone │   (QStackedWidget)   │  (Panneau     │
│Panneau│  Pages: Accueil,    │   rooms)      │
│ config│  Recherche, Config, │   Public      │
│  ←→   │  Téléchargements... │   Privé       │
│      │                      │               │
├──────┴──────────────────────┴───────────────┤
│              FooterZone                     │  ← 12 boutons navigation bots
└─────────────────────────────────────────────┘
```

### Fichiers sources

| Fichier | Classe | Rôle |
|---------|--------|------|
| `src/gui/main_window.py` | `MainWindow(QMainWindow)` | Fenêtre principale, barre de menus, statut, notifications |
| `src/gui/layout/entry.py` | `LayoutEntry(QFrame)` | Widget central assemblant les 5 zones dans une grille 3×3 |
| `src/gui/layout/header.py` | `HeaderZone(QFrame)` | Bannière supérieure avec widget de connexion |
| `src/gui/layout/left.py` | `LeftZone(QFrame)` | Panneau latéral gauche rétractable (config) |
| `src/gui/layout/center.py` | `CenterZone(QFrame)` | Zone centrale avec `QStackedWidget` et toutes les pages |
| `src/gui/layout/right.py` | `RightZone(QFrame)` | Panneau latéral droit rétractable (rooms) |
| `src/gui/layout/footer.py` | `FooterZone(QFrame)` | Barre inférieure avec 12 boutons de navigation (bots) |

---

## 1. `LayoutEntry` — L'assemblage des 5 zones

**Fichier :** `src/gui/layout/entry.py`

La classe `LayoutEntry` est le **widget central** de la `MainWindow`. Elle dispose les 5 zones dans une grille `QGridLayout` 3×3 avec marges et espacement nuls :

```python
layout = QGridLayout(self)
layout.setContentsMargins(0, 0, 0, 0)
layout.setSpacing(0)

layout.addWidget(header, 0, 0, 1, 3)  # Ligne 0 : header, toute largeur
layout.addWidget(left,   1, 0)         # Ligne 1 : left (col 0)
layout.addWidget(center, 1, 1)         # Ligne 1 : center (col 1)
layout.addWidget(right,  1, 2)         # Ligne 1 : right (col 2)
layout.addWidget(footer, 2, 0, 1, 3)  # Ligne 2 : footer, toute largeur
```

**Étirements (stretch) :**
- **Colonnes :** `col 0 = 0` (Left fixe), `col 1 = 1` (Center prend tout l'espace), `col 2 = 0` (Right fixe)
- **Lignes :** `row 0 = 0` (Header fixe), `row 1 = 1` (Body prend tout l'espace), `row 2 = 0` (Footer fixe)

**Navigation :** Les signaux `page_changed(str)` des trois zones (header, left, footer) sont connectés à `center.show_page()` pour changer la page affichée.

```python
header.page_changed.connect(center.show_page)
left.page_changed.connect(center.show_page)
footer.page_changed.connect(center.show_page)
```

---

## 2. `MainWindow` — La fenêtre principale

**Fichier :** `src/gui/main_window.py`

La classe `MainWindow` hérite de `QMainWindow` et constitue le point d'entrée de l'interface.

### Initialisation

```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Soulseek Client")
        self.resize(1200, 800)
        # Application du thème sombre
        self.setStyleSheet(DARK_THEME)
        
        # Construction du layout central
        central_widget = LayoutEntry()
        self.setCentralWidget(central_widget)
        
        # Barre de menu
        self._build_menu()
        
        # Barre de statut + notifications
        self.statusBar().showMessage("Prêt")
        self._toast = ToastNotification(self)
        
        # Gestionnaire de connexion
        self._connexion_manager = ConnexionManager()
        self._connect_connexion_manager()
```

### Barre de menus (`_build_menu`)

| Menu | Actions |
|------|---------|
| **Fichier** | Quitter (`QAction`) |
| **Outils** | QSS Inspector (devtool) |
| **Aide** | À propos |

### Fermeture (`closeEvent`)

```python
def closeEvent(self, event):
    self._connexion_manager.stop()
    self._qss_inspector.stop()
    event.accept()
```

### Connexion manager

La méthode `_connect_connexion_manager` relie les signaux du `ConnexionManager` aux composants UI :
- Connexion établie → `center.show_home(username)`
- Déconnexion → `center.show_connexion()`
- Erreurs → notifications toast

---

## 3. `HeaderZone` — La bannière supérieure

**Fichier :** `src/gui/layout/header.py`

La `HeaderZone` est un bandeau horizontal placé en haut de l'application. **Masqué par défaut**, il devient visible après connexion.

### Structure

```python
class HeaderZone(QFrame):
    page_changed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        self._connexion = ConnexionHeaderWidget()
        layout.addWidget(self._connexion)
        
        self.setVisible(False)  # Masqué par défaut
```

### API publique

| Propriété/Méthode | Type | Description |
|-------------------|------|-------------|
| `connexion_widget` | `@property` | Accès au `ConnexionHeaderWidget` interne |

### Signal

| Signal | Émetteur | Valeur |
|--------|----------|--------|
| `page_changed(str)` | Clic sur connexion_widget | `"connexion"` |

---

## 4. `LeftZone` — Panneau latéral gauche (configuration)

**Fichier :** `src/gui/layout/left.py`

Le panneau gauche est un menu de navigation rétractable dédié aux **pages de configuration**. Il alterne entre deux états :

| État | Largeur | Affichage |
|------|---------|-----------|
| Déplié | 200 px | Noms des sections + poignée |
| Replié | 20 px | Poignée seulement |

### Structure

```python
class LeftZone(QFrame):
    page_changed = Signal(str)
    
    _WIDTH_EXPANDED = 200
    _WIDTH_COLLAPSED = 20
    
    _SECTIONS = [
        "Général", "Partages", "Réseau", "Recherche",
        "Téléchargement", "Utilisateurs", "Salons", "Debug"
    ]
    
    _SECTION_TO_PAGE = {
        "Général": "config-general",
        "Partages": "config-partages",
        "Réseau": "config-reseau",
        "Recherche": "config-recherche",
        "Téléchargement": "config-telechargement",
        "Utilisateurs": "config-utilisateurs",
        "Salons": "config-salons",
        "Debug": "config-debug",
    }
```

### API publique

| Méthode/Propriété | Description |
|-------------------|-------------|
| `toggle()` | Bascule déplié/replié |
| `expand()` | Déplier le panneau |
| `collapse()` | Replier le panneau |
| `set_active(name)` | Marque un bouton actif sans émettre de signal |
| `active_page` | `@property` : nom de la page active courante |
| `page_button(name)` | Accès à l'instance `_NavButton` d'un bouton |
| `home_button_visible` | `@property` : visibilité du bouton Accueil |

### Signal

| Signal | Valeur |
|--------|--------|
| `page_changed(str)` | Nom de la page cible (ex: `"config-recherche"`) |

### Widgets internes

- `_NavButton(QPushButton)` : bouton de navigation avec état `checkable`
- `_Handle(QFrame)` : zone de contrôle avec flèche `◀`/`▶` pour replier/déplier

---

## 5. `CenterZone` — La zone centrale (QStackedWidget)

**Fichier :** `src/gui/layout/center.py`

La `CenterZone` est le cœur de l'interface. Elle utilise un `QStackedWidget` pour empiler toutes les pages et n'en afficher qu'une à la fois.

### Pages disponibles

| Méthode de construction | Nom de page | Contenu |
|------------------------|-------------|---------|
| `_build_connexion_page` | `connexion` | Formulaire d'authentification |
| `_build_home_page` | `home` | Page d'accueil post-connexion |
| `_build_accueil_page` | `accueil` | Bot Accueil |
| `_build_recherche_page` | `recherche` | Bot Recherche |
| `_build_telechargements_page` | `telechargements` | Bot Téléchargement |
| `_build_wishlist_page` | `wishlist` | Bot Wishlist |
| `_build_bibliotheque_page` | `bibliotheque` | Bot Bibliothèque |
| `_build_optimiseur_page` | `optimiseur` | Bot Optimiseur |
| `_build_surveillance_page` | `surveillance` | Bot Surveillance |
| `_build_planificateur_page` | `planificateur` | Bot Planificateur |
| `_build_ordonnanceur_page` | `ordonnanceur` | Bot Ordonnanceur |
| `_build_clients_actifs_page` | `clients-actifs` | Clients Actifs (header) |
| `_build_clients_actifs_table_page` | `clients-actifs-table` | Clients Actifs (tableau) |
| `_build_config_pages` | `config-*` | 8 onglets de configuration |

### Structure interne

```python
class CenterZone(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self._stack = QStackedWidget()
        layout.addWidget(self._stack)
        
        self._pages: dict[str, QWidget] = {}
        
        # Construction de toutes les pages
        self._build_connexion_page()
        self._build_home_page()
        self._build_accueil_page()
        # ... toutes les autres pages
```

### API publique

| Méthode/Propriété | Description |
|-------------------|-------------|
| `stack` | `@property` : accès au `QStackedWidget` |
| `current_page` | `@property` : nom de la page affichée |
| `show_page(name)` | Affiche une page par son nom (avec alias via `_PAGE_ALIASES`) |
| `show_home(username)` | Affiche la page d'accueil avec le nom d'utilisateur |
| `show_connexion()` | Affiche le formulaire de connexion |
| `page(name)` | Récupère le widget d'une page |
| `set_connexion_manager(mgr)` | Transmet le gestionnaire aux bots |
| `connexion_page` | `@property` : accès à la page connexion |
| `telechargements_page` | `@property` : accès à la page téléchargements |

### Aliasing de pages

Le dictionnaire `_PAGE_ALIASES` permet de rediriger certains noms de pages :

```python
_PAGE_ALIASES = {
    "config": "config-general",
    # ... autres alias
}
```

---

## 6. `RightZone` — Panneau latéral droit (rooms)

**Fichier :** `src/gui/layout/right.py`

Le panneau droit est un panneau rétractable dédié aux **salons de discussion** (rooms). Il alterne entre deux états :

| État | Largeur | Affichage |
|------|---------|-----------|
| Déplié | 280 px | Onglets + poignée |
| Replié | 20 px | Poignée seulement |

### Structure

```python
class RightZone(QFrame):
    _WIDTH_EXPANDED = 280
    _WIDTH_COLLAPSED = 20
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Poignée de contrôle
        self._handle = _Handle()
        
        # Zone de contenu
        self._content = QFrame()
        content_layout = QVBoxLayout(self._content)
        
        # Titre
        title = QLabel("LES ROOMS")
        content_layout.addWidget(title)
        
        # Onglets
        self._tabs = QTabWidget()
        self._tab_public = self._build_tab("Salons publics")
        self._tab_prive = self._build_tab("Salons privés")
        self._tabs.addTab(self._tab_public, "Public")
        self._tabs.addTab(self._tab_prive, "Privé")
        content_layout.addWidget(self._tabs)
        
        layout.addWidget(self._handle)
        layout.addWidget(self._content)
```

### API publique

| Méthode/Propriété | Description |
|-------------------|-------------|
| `is_collapsed` | `@property` : état du panneau |
| `tabs` | `@property` : accès au `QTabWidget` |
| `toggle()` | Bascule déplié/replié |
| `expand()` | Déplier le panneau |
| `collapse()` | Replier le panneau |

---

## 7. `FooterZone` — Barre de navigation inférieure (bots)

**Fichier :** `src/gui/layout/footer.py`

Le footer est la barre de navigation principale de l'application. **Masqué par défaut**, il devient visible après connexion. Il contient 12 boutons correspondant aux différents bots et fonctionnalités.

### Liste des boutons

```python
_BOT_NAMES = [
    "Accueil", "Recherche", "Bibliothèque", "Wishlist",
    "Téléchargement", "Surveillance", "Ordonnanceur",
    "Planificateur", "Optimiseur", "Clients actifs",
    "Assistant", "Aide"
]
```

### Structure

```python
class FooterZone(QFrame):
    page_changed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Centrer les boutons
        layout.addStretch()
        for name in _BOT_NAMES:
            btn = _FooterNavButton(name)
            btn.clicked.connect(lambda checked, n=name: self._on_button(n))
            layout.addWidget(btn)
            self._buttons[name] = btn
        layout.addStretch()
        
        self.setVisible(False)  # Masqué par défaut
```

### Widget `_FooterNavButton`

```python
class _FooterNavButton(QPushButton):
    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        self.setCheckable(True)
        self._badge = QLabel(self)
        self._badge.setVisible(False)
```

Chaque bouton est **checkable** (état actif) et peut afficher un **badge de notification** (ex: `"99+"` pour les résultats de recherche).

### API publique

| Méthode | Description |
|---------|-------------|
| `set_active(name)` | Marque un bouton actif sans émettre de signal |
| `set_badge(name, count)` | Définit/met à jour le compteur d'un bouton |
| `button(name)` | Accès à l'instance `_FooterNavButton` |
| `page_button(name)` | Accès à l'instance (synonyme) |

### Signal

| Signal | Valeur |
|--------|--------|
| `page_changed(str)` | Nom de la page cible (ex: `"recherche"`) |

---

## 8. Flux de navigation

### Démarrage

```
MainWindow.__init__()
  └─ LayoutEntry()
       ├─ HeaderZone()        → masqué
       ├─ LeftZone()          → déplié
       ├─ CenterZone()
       │    ├─ _build_connexion_page()   → visible par défaut
       │    ├─ _build_home_page()
       │    ├─ _build_*_page()           → toutes les pages
       │    └─ _build_config_pages()     → 8 onglets de config
       ├─ RightZone()         → replié par défaut
       └─ FooterZone()        → masqué
  └─ _connect_connexion_manager()
```

### Connexion réussie

```
ConnexionManager.connecté
  ├─ HeaderZone.setVisible(True)
  ├─ FooterZone.setVisible(True)
  ├─ CenterZone.show_home(username)
  └─ CentreZone.connexion_page.prefill(username)
```

### Navigation utilisateur

```
Clic footer "Recherche"
  └─ FooterZone._on_button("Recherche")
       ├─ page_changed.emit("recherche")
       └─ CenterZone.show_page("recherche")
            └─ _stack.setCurrentWidget(_pages["recherche"])
```

```
Clic left "Réseau"
  └─ LeftZone._on_button("Réseau")
       ├─ page_changed.emit("config-reseau")
       └─ CenterZone.show_page("config-reseau")
            └─ _stack.setCurrentWidget(_pages["config-reseau"])
```

---

## 9. Interactions entre zones

| Action | Source | Cible | Mécanisme |
|--------|--------|-------|-----------|
| Navigation bot | FooterZone | CenterZone | `page_changed` → `show_page` |
| Navigation config | LeftZone | CenterZone | `page_changed` → `show_page` |
| Clic connexion | HeaderZone | CenterZone | `page_changed` → `show_page` |
| Badge notifications | CenterZone | FooterZone | `footer.set_badge(name, count)` |
| État connexion | MainWindow | Header/Footer | `setVisible(True/False)` |
| Repli/Dépli | Left/Right | Left/Right | `toggle()` → resize interne |

---

## Résumé

L'interface est organisée en **5 zones** assemblées par `LayoutEntry` dans une grille `QGridLayout` 3×3 :

| Zone | Classe | Visibilité | Rôle |
|------|--------|-----------|------|
| **Header** | `HeaderZone` | Masqué → visible après connexion | Bannière avec widget connexion |
| **Left** | `LeftZone` | Toujours visible (rétractable) | Menu de navigation configuration (8 sections) |
| **Center** | `CenterZone` | Toujours visible | Zone principale avec `QStackedWidget` (14+ pages) |
| **Right** | `RightZone` | Rétractable par défaut | Panneau des rooms (salons Public/Privé) |
| **Footer** | `FooterZone` | Masqué → visible après connexion | Barre navigation 12 boutons (bots) avec badges |

La navigation est unifiée via le signal `page_changed(str)` émis par les trois zones cliquables (header, left, footer) et connecté à `CenterZone.show_page()`, qui active la page correspondante dans le `QStackedWidget`.
