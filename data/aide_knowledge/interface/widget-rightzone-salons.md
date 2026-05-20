---
title: "Panneau RightZone et système de salons (rooms)"
category: "interface"
tags:
  - rightzone
  - rooms
  - salons
  - qtabwidget
  - panneau lateral
keywords:
  - RightZone panneau droit retractable
  - RightZone panneau droit rétractable
  - RightZone _WIDTH_EXPANDED 280px
  - RightZone _WIDTH_COLLAPSED 20px
  - RightZone _Handle poignee repli
  - RightZone _Handle poignée repli
  - RightZone _Handle mousePressEvent clicked
  - RightZone _Handle set_arrow fleche
  - RightZone _Handle set_arrow flèche
  - RightZone QTabWidget onglets Public Prive
  - RightZone QTabWidget onglets Public Privé
  - RightZone _build_tab QGridLayout placeholder
  - RightZone _apply_state etat replie
  - RightZone _apply_state état replié
  - RightZone is_collapsed propriete
  - RightZone is_collapsed propriété
  - RightZone toggle expand collapse
  - room_message_received signal salons
  - room_message_received signal salon message
  - private_message_received signal message prive
  - private_message_received signal message privé
  - connexion_manager search_room recherche salon
  - connexion_manager _do_search_room coroutine
  - connexion_manager client.searches.search_room
  - salons auto_join configuration
  - salons invitations_privees configuration privé
  - salons favoris salons favoris configuration
  - bot_accueil messageCard messages
  - QStackedWidget page accueil salon chat
  - LayoutEntry right zone grille 3x3
  - layout panneau droit horizontal handle content
  - layout panneau droit horizontal QHBoxLayout
---

# Panneau RightZone et système de salons (rooms)

## Vue d'ensemble

Le panneau droit `RightZone` est un panneau latéral rétractable dédié à l'affichage des **salons de discussion (rooms)**. Il est assemblé dans la grille 3×3 de `LayoutEntry` (colonne 2, ligne 1) et utilise un `QTabWidget` pour organiser les salons en deux catégories : **Public** et **Privé**.

```
┌──────────────────────────────────────┐
│          LayoutEntry                 │
│  ┌─────┬──────────┬────────────────┐ │
│  │     │          │   RightZone    │ │
│  │Left │  Center  │ ┌─────Handle──┐│ │
│  │Zone │   Zone   │ │◀           ││ │
│  │     │          │ ├─────────────┤│ │
│  │     │          │ │ LES ROOMS   ││ │
│  │     │          │ │ ┌─────────┐ ││ │
│  │     │          │ │ │ Public  │ ││ │
│  │     │          │ │ │ (tab)   │ ││ │
│  │     │          │ │ ├─────────┤ ││ │
│  │     │          │ │ │ Privé   │ ││ │
│  │     │          │ │ │ (tab)   │ ││ │
│  │     │          │ │ └─────────┘ ││ │
│  └─────┴──────────┴────────────────┘ │
│             Footer                   │
└──────────────────────────────────────┘
```

### Fichiers sources

| Fichier | Classe | Rôle |
|---------|--------|------|
| `src/gui/layout/right.py` | `RightZone(QFrame)` | Panneau latéral droit avec `QTabWidget` |
| `src/gui/layout/right.py` | `_Handle(QFrame)` | Poignée de contrôle repli/dépli |
| `src/gui/layout/entry.py` | `LayoutEntry(QFrame)` | Grille 3×3 qui contient `RightZone` |
| `src/gui/layout/center.py` | `CenterZone(QFrame)` | Zone centrale qui connecte les signaux de salon |
| `src/services/connexion_manager.py` | `ConnexionManager` | Méthodes `search_room`, `_do_search_room` |
| `src/services/app_config.py` | `_DEFAULTS` | Configuration `salons.*` |

---

## 1. Architecture de `RightZone`

**Fichier :** `src/gui/layout/right.py`

### Constantes

```python
_WIDTH_EXPANDED = 280
_WIDTH_COLLAPSED = 20
```

| État | Largeur | Contenu visible |
|------|---------|-----------------|
| **Déplié** | 280 px | Titre + `QTabWidget` + poignée |
| **Replié** | 20 px | Poignée seulement |

### Structure interne

```python
class RightZone(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._collapsed = False
        
        # Layout horizontal : [Handle | Content]
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Poignée de repli (bord gauche)
        self._handle = _Handle()
        self._handle.clicked.connect(self._toggle_panel)
        
        # Zone de contenu
        self._content = QFrame()
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Titre
        title = QLabel("LES ROOMS")
        content_layout.addWidget(title)
        
        # Onglets Public / Privé
        self._tabs = QTabWidget()
        tab_public = QWidget()
        self._build_tab(tab_public, "Salons publics")
        self._tabs.addTab(tab_public, "Public")
        
        tab_prive = QWidget()
        self._build_tab(tab_prive, "Salons privés")
        self._tabs.addTab(tab_prive, "Privé")
        content_layout.addWidget(self._tabs)
        
        main_layout.addWidget(self._handle)
        main_layout.addWidget(self._content)
        
        self._apply_state()  # Applique l'état initial (déplié par défaut)
```

### Contrôle d'état (`_apply_state`)

```python
def _apply_state(self):
    self._content.setVisible(not self._collapsed)
    
    if self._collapsed:
        self._handle.set_arrow("▶")
        self.setFixedWidth(_WIDTH_COLLAPSED)
    else:
        self._handle.set_arrow("◀")
        self.setFixedWidth(_WIDTH_EXPANDED)
```

### API publique

| Méthode/Propriété | Description |
|-------------------|-------------|
| `is_collapsed` | `@property` : `True` si le panneau est replié |
| `tabs` | `@property` : accès au `QTabWidget` interne |
| `toggle()` | Bascule entre déplié et replié |
| `expand()` | Déplie le panneau (280 px) |
| `collapse()` | Replie le panneau (20 px) |

---

## 2. `_Handle` — La poignée de contrôle

**Classe interne** située dans `src/gui/layout/right.py`.

```python
class _Handle(QFrame):
    clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        layout = QHBoxLayout(self)
        self._arrow = QLabel("◀")
        layout.addWidget(self._arrow)
    
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)
    
    def set_arrow(self, text):
        self._arrow.setText(text)
```

La poignée est un `QFrame` occupant toute la hauteur du panneau, avec :

| Aspect | Détail |
|--------|--------|
| **Signal** | `clicked` émis sur `mousePressEvent` |
| **Curseur** | `Qt.PointingHandCursor` (main) |
| **Flèche dépliée** | `◀` (pointe vers la gauche : "replier") |
| **Flèche repliée** | `▶` (pointe vers la droite : "déplier") |

---

## 3. `_build_tab` — Construction des onglets

```python
@staticmethod
def _build_tab(tab, placeholder_text):
    """Configure un QWidget existant avec un QGridLayout et un QLabel placeholder."""
    layout = QGridLayout(tab)
    placeholder = QLabel(placeholder_text)
    layout.addWidget(placeholder)
    return tab
```

Chaque onglet est construit en passant un `QWidget` existant et un texte placeholder. La structure en `QGridLayout` est conçue pour accueillir ultérieurement :

- Une **liste de salons** avec leur nombre d'utilisateurs
- Des **invitations** à des salons privés
- Des **champs de recherche** pour filtrer les salons
- Des **interactions** (rejoindre, quitter)

### Onglets actuels

| Onglet | Placeholder | Usage prévu |
|--------|-------------|-------------|
| **Public** | `"Salons publics"` | Liste des salons publics Soulseek, recherche de salons |
| **Privé** | `"Salons privés"` | Invitations reçues, salons privés rejoints |

---

## 4. Ordre d'initialisation et intégration

### Dans `LayoutEntry` (entry.py)

`RightZone` est placée dans la grille 3×3 à la position `(1, 2)` — colonne de droite, ligne du corps :

```python
layout.addWidget(right, 1, 2)  # row=1, col=2
```

### Déroulement au démarrage

```
MainWindow.__init__()
  └─ LayoutEntry()
       └─ RightZone()              → déplié par défaut (280px)
            ├─ _Handle()           → flèche "◀"
            └─ _content
                 ├─ QLabel("LES ROOMS")
                 └─ QTabWidget
                      ├─ Tab "Public"  → QGridLayout + QLabel placeholder
                      └─ Tab "Privé"  → QGridLayout + QLabel placeholder
```

---

## 5. Backend — Connexion des signaux de salons

### Dans `CenterZone` (center.py)

Le `CenterZone` connecte les événements de salon reçus du service Soulseek :

```python
soulseek_service.room_message_received.connect(
    lambda evt: logger.debug(
        "Message reçu dans le salon %s de %s : %s",
        evt.message.room_name,
        evt.message.username,
        evt.message.content[:80]  # Tronqué à 80 caractères
    )
)

soulseek_service.private_message_received.connect(
    lambda evt: logger.debug(
        "Message privé reçu de %s : %s",
        evt.message.username,
        evt.message.content[:80]
    )
)
```

### Dans `ConnexionManager` (connexion_manager.py)

Le gestionnaire de connexion expose deux méthodes pour interagir avec les salons :

```python
def search_room(self, room: str, query: str):
    """Lance une recherche dans un salon spécifique."""
    # Émet un statut, déclenche _do_search_room
    ...

async def _do_search_room(self, room: str, query: str):
    """Coroutine : effectue la recherche via client.searches.search_room."""
    try:
        await client.searches.search_room(room, query)
    except Exception as e:
        logger.error("Erreur recherche salon %s: %s", room, e)
        self.error_occurred.emit(str(e))
```

### Flux de réception d'un message

```
Soulseek réseau
   ↓
client.events.room_message_received
   ↓
soulseek_service.room_message_received.emit(evt)
   ↓
center.py: connecté → log + mise à jour UI
   ↓
RightZone: affichage dans l'onglet correspondant (à implémenter)
```

---

## 6. Configuration des salons

Les paramètres de salon sont stockés dans `app_config` (fichier `app_config.json`) sous la section `salons` :

| Clé | Type | Défaut | Description |
|-----|------|--------|-------------|
| `salons.auto_join` | `bool` | `True` | Rejoindre automatiquement les salons favoris au démarrage |
| `salons.invitations_privees` | `bool` | `True` | Accepter automatiquement les invitations privées |
| `salons.favoris` | `str` | `""` | Liste CSV des salons à rejoindre (ex: `#musique, #techno`) |

Ces paramètres sont configurés via l'onglet **Salons** du panneau gauche (LeftZone → page `config-salons`).

### Application au démarrage

Dans `soulseek_client.py` (lignes ~246-250), les options salons sont lues et appliquées à l'initialisation :

```python
auto_join = app_config.get("auto_join", section="salons", default=True)
invitations = app_config.get("invitations_privees", section="salons", default=True)
favoris = app_config.get("favoris", section="salons", default="")
```

---

## 7. Relation avec les autres composants

| Composant | Fichier | Relation |
|-----------|---------|----------|
| **`LayoutEntry`** | `entry.py` | Grille 3×3 : `RightZone` en colonne 2 |
| **`LeftZone`** | `left.py` | Panneau gauche symétrique, navigation config salons |
| **`CenterZone`** | `center.py` | Connecte les signaux `room_message_received` et `private_message_received` |
| **`ConfigPage (Salons)`** | `center.py` | Page `config-salons` pour configurer auto_join, invitations, favoris |
| **`FooterZone`** | `footer.py` | Bouton "Accueil" → page accueil avec chat simulé |
| **`ConnexionManager`** | `connexion_manager.py` | Méthodes `search_room`, `_do_search_room` via `client.searches` |
| **`app_config`** | `app_config.py` | Stocke les paramètres `salons.*` dans `app_config.json` |
| **`bot_accueil`** | `bots/bot_accueil.py` | Widget `messageCard` pour l'affichage des messages |

---

## 8. Architecture des salons — Schéma complet

```
┌──────────────────────────────────────────────────────────┐
│                    Interface graphique                    │
│                                                          │
│  RightZone (right.py)                                    │
│  ┌────────────────────────────────────┐                  │
│  │ QTabWidget                         │                  │
│  │  ┌──────────┐  ┌──────────┐       │                  │
│  │  │  Public   │  │  Privé   │       │                  │
│  │  │(QGridLyt) │  │(QGridLyt)│       │                  │
│  │  └──────────┘  └──────────┘       │                  │
│  └────────────────────────────────────┘                  │
│         ▲                                               │
│         │ signaux room/private_message_received          │
│         │                                                │
│  CenterZone (center.py)                                  │
│  └── connecte les événements Soulseek ──┐                │
│                                         ▼                │
└─────────────────────────────────────────────────────────┘
                                                          
┌──────────────────────────────────────────────────────────┐
│                    Services backend                       │
│                                                          │
│  ConnexionManager (connexion_manager.py)                 │
│  ├─ search_room(room, query)                             │
│  │    └─ _do_search_room(room, query)                    │
│  │         └─ client.searches.search_room(room, query)   │
│  │                                                       │
│  └─ room_message_received (signal)                       │
│       └─ client.events.room_message_received             │
│                                                          │
│  app_config (app_config.py)                              │
│  └─ section "salons" :                                   │
│       ├─ auto_join: bool                                 │
│       ├─ invitations_privees: bool                       │
│       └─ favoris: str (CSV)                              │
└──────────────────────────────────────────────────────────┘
                                                          
┌──────────────────────────────────────────────────────────┐
│                    Réseau Soulseek                        │
│                                                          │
│  client.searches.search_room(room, query)    ← aioslsk   │
│  client.events.room_message_received         ← aioslsk   │
│  client.events.private_message_received      ← aioslsk   │
└──────────────────────────────────────────────────────────┘
```

---

## 9. Interactions utilisateur

### Déplier/Replier le panneau

```python
# Clic sur la poignée :
_Handle.clicked.emit()
  └─ RightZone._toggle_panel()
       └─ self._collapsed = not self._collapsed
            └─ _apply_state()
                 ├─ self._content.setVisible(...)
                 ├─ self._handle.set_arrow("◀" ou "▶")
                 └─ self.setFixedWidth(280 ou 20)
```

### Basculement d'onglets

```python
# Clic sur "Privé" dans le QTabWidget :
tabs.setCurrentIndex(1)
  └─ Affiche le widget de l'onglet "Privé" (second tab)
```

### Recherche dans un salon

```python
# Appelé depuis une fonction de recherche (à implémenter) :
connexion_manager.search_room("#musique", "album jazz")
  └─ _do_search_room("#musique", "album jazz")
       └─ await client.searches.search_room("#musique", "album jazz")
```

---

## Résumé

| Composant | Détail |
|-----------|--------|
| **RightZone** | `QFrame`, layout `QHBoxLayout`, rétractable 280/20px |
| **_Handle** | Poignée cliquable, émet `clicked`, flèche `◀`/`▶` |
| **QTabWidget** | 2 onglets : **Public** et **Privé** (placeholders actuels) |
| **_build_tab** | `QGridLayout` + `QLabel` placeholder (extensible) |
| **Connexion signaux** | `room_message_received`, `private_message_received` → log |
| **Backend salon** | `search_room(room, query)`, `_do_search_room` coroutine |
| **Configuration** | `salons.*` dans `app_config` : auto_join, invitations, favoris |
| **Intégration** | Grille 3×3 colonne 2, accessible via `LayoutEntry.right` |
