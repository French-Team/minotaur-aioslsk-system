---
title: "Système de notifications Toast (ToastNotification)"
category: "technique"
icon: "🔔"
keywords:
  - notification toast soulseek
  - ToastNotification
  - toast notification systeme
  - toast notification système
  - notification flottante interface
  - notification evenement bus
  - notification événement bus
  - EventBus toast notification
  - severite notification interface
  - sévérité notification interface
  - notification ERROR interface
  - notification WARN interface
  - notification INFO interface
  - icone notification par severite
  - icône notification par sévérité
  - couleur notification par severite
  - couleur notification par sévérité
  - duree affichage toast
  - durée affichage toast
  - fondu notification animation
  - QTimer singleShot notification
  - QGraphicsOpacityEffect fondu
  - _ToastCard QFrame
  - _MAX_TOASTS 5
  - _TOAST_DURATION_MS 4000
  - _FADE_DURATION_MS 300
  - notification automatique disparition
  - notification evenement systeme
  - notification événement système
  - evenement ERROR WARN notification
  - événement ERROR WARN notification
  - empilement notification toast
  - pile notification interface
  - notification haut droite
  - notification ancree interface
  - notification ancrée interface
  - notification evenement bus
  - notification événement bus
  - systeme notification
  - système notification
  - notification evenement
  - notification événement
  - affichage notification
  - notification interface
  - notification flottante
  - notification popup
  - notification auto disparition
  - notification 4 secondes
  - 4000ms notification
  - maximum 5 toasts
  - suppression notification
  - repositionnement notification
  - troncature message 80 caracteres
  - troncature message 80 caractères
  - largeur fixe 340px toast
---


# 🔔 Système de notifications Toast (ToastNotification)

Cet article technique détaille le système de **notifications flottantes** (toasts) de l'application, qui affiche des messages temporaires pour les événements importants issus de l'EventBus.

---

## 🏗️ Architecture générale

Le système ToastNotification repose sur deux classes et s'intègre à l'EventBus via `MainWindow` :

```
EventBus().event_emitted
        │
        ▼
MainWindow._on_toast_event()     ← filtre ERROR / WARN uniquement
        │
        ▼
ToastNotification.show_toast(severity, title, message)
        │
        ▼
    ┌───┴───┐
    │       │
  Card1   Card2   ...   (max 5)
```

### Flux complet

1. Un composant émet un événement via `EventBus().emit_event()` (ex: connexion perdue, recherche terminée, erreur réseau)
2. `MainWindow._on_toast_event()` reçoit l'événement via le signal `event_emitted`
3. La méthode filtre : seuls les événements de sévérité **ERROR** ou **WARN** déclenchent un toast
4. `ToastNotification.show_toast()` crée une `_ToastCard` et l'affiche
5. La carte disparaît automatiquement après **4 secondes** avec un fondu

---

## 📁 Structure du fichier

```
src/gui/widgets/toast_notification.py  (~170 lignes)
├── Imports (logging, PySide6)
├── Constantes de configuration
├── _SEVERITY_COLORS (dict)
├── Classe _ToastCard(QFrame)
└── Classe ToastNotification(QWidget)
```

---

## ⚙️ Constantes de configuration

| Constante | Valeur | Description |
|-----------|--------|-------------|
| `_TOAST_DURATION_MS` | `4000` | Durée d'affichage avant disparition (4 secondes) |
| `_FADE_DURATION_MS` | `300` | Durée de l'animation de fondu (300 ms) |
| `_MAX_TOASTS` | `5` | Nombre maximum de toasts affichés simultanément |
| `_TOAST_MARGIN` | `16` | Marge depuis le bord de la fenêtre parente |
| `_TOAST_SPACING` | `8` | Espacement vertical entre les toasts |

---

## 🎨 Couleurs par sévérité

Le dictionnaire `_SEVERITY_COLORS` associe chaque niveau de sévérité à un tuple `(couleur_fond, couleur_texte)` :

| Sévérité | Fond | Texte | Icône |
|----------|------|-------|-------|
| `ERROR` | `#e74c3c` (rouge) | `#ffffff` (blanc) | ❌ |
| `WARN` | `#f39c12` (orange) | `#ffffff` (blanc) | ⚠️ |
| `INFO` | `#3498db` (bleu) | `#ffffff` (blanc) | ℹ️ |

**Note :** Bien que `INFO` soit défini dans les couleurs et icônes, `MainWindow._on_toast_event()` ne déclenche que les toasts de type `ERROR` et `WARN`. La sévérité `INFO` peut être utilisée pour des appels manuels si nécessaire.

---

## 🃏 Classe `_ToastCard(QFrame)`

Classe interne représentant une **carte de notification individuelle**.

### Constructeur

```python
def __init__(self, severity: str, title: str, message: str, parent=None)
```

| Paramètre | Type | Description |
|-----------|------|-------------|
| `severity` | `str` | `"ERROR"`, `"WARN"` ou `"INFO"` |
| `title` | `str` | Titre de la notification |
| `message` | `str` | Message optionnel |
| `parent` | `QWidget` | Widget parent |

### Caractéristiques visuelles

- **Largeur fixe :** 340 pixels
- **Layout :** `QHBoxLayout` avec :
  - **Icône** : `QLabel` avec l'icône correspondant à la sévérité (❌, ⚠️, ℹ️), police 18px
  - **Texte** : `QVBoxLayout` avec :
    - **Titre** : `QLabel` en **gras** (`font-weight: 600`)
    - **Message** : `QLabel` tronqué à **80 caractères** + `…` si nécessaire, taille de police réduite
- **Style :** Fond arrondi via `setStyleSheet` avec la couleur de fond et de texte selon la sévérité
- **Opacité :** Gérée via `QGraphicsOpacityEffect` avec une valeur initiale de 1.0

### Méthode `set_card_opacity(value)`

Applique un `QGraphicsOpacityEffect` à la carte avec la valeur d'opacité spécifiée (0.0 à 1.0), utilisée pour l'animation de fondu.

---

## 🪟 Classe `ToastNotification(QWidget)`

Classe principale qui gère l'**overlay de notifications**. Hérite de `QWidget`.

### Constructeur

```python
def __init__(self, parent=None)
```

- Initialise un `QVBoxLayout` avec alignement `AlignTop`
- Crée une liste vide `self._toasts` pour suivre les cartes actives
- Définit le widget parent pour le positionnement

### Méthode `show_toast(severity, title, message="")`

Point d'entrée pour afficher une notification :

1. **Vérification de la limite** : si `len(self._toasts) >= _MAX_TOASTS` (5), la carte la plus ancienne est supprimée via `_remove_toast(self._toasts[0])`
2. **Création** : `card = _ToastCard(severity, title, message, self)`
3. **Ajout** : la carte est ajoutée à `self._toasts` et au layout
4. **Positionnement** : `self._reposition()` recalcule la géométrie
5. **Visibilité** : `self.setVisible(True)` si le widget était masqué
6. **Disparition automatique** : `QTimer.singleShot(_TOAST_DURATION_MS, lambda: self._remove_toast(card))` déclenche la suppression après 4 secondes

### Méthode `_remove_toast(card)`

Supprime une carte de notification :

1. Retire la carte de `self._toasts`
2. Retire la carte du layout
3. Appelle `card.deleteLater()` pour nettoyer la mémoire
4. Si `self._toasts` est vide : `self.setVisible(False)` pour masquer l'overlay

### Méthode `_reposition()`

Calcule et applique la position du widget dans le parent :

```python
# Position : ancré en haut à droite du parent
x = parent.width() - self.sizeHint().width() - _TOAST_MARGIN
y = _TOAST_MARGIN
self.setGeometry(x, y, self.sizeHint().width(), self.sizeHint().height())
```

---

## 🔌 Intégration avec MainWindow

### Initialisation

Dans `MainWindow.__init__()` :
```python
self._toast = ToastNotification(self)          # ligne ~247
self._connect_toast_events()                   # ligne ~249
```

### Connexion des événements

```python
def _connect_toast_events(self):
    EventBus().event_emitted.connect(self._on_toast_event)
```

### Filtrage des événements

```python
def _on_toast_event(self, event):
    if event.severity in ("ERROR", "WARN"):
        self._toast.show_toast(
            severity=event.severity,
            title=event.title,
            message=event.message or "",
        )
```

**Règle de filtrage :** Seuls les événements de sévérité `ERROR` et `WARN` génèrent un toast. Les événements `INFO` (générés par exemple pour les connexions réussies, les recherches lancées, etc.) sont ignorés pour éviter la surcharge visuelle.

---

## 🔗 Interaction avec l'EventBus

Le système de toasts est un **écouteur passif** de l'EventBus. Il n'émet pas d'événements lui-même.

### Émetteurs qui génèrent des toasts ERROR/WARN

| Source | Événement | Sévérité |
|--------|-----------|----------|
| `ConnexionManager` | Connexion impossible | `ERROR` |
| `ConnexionManager` | Déconnexion inattendue | `WARN` |
| `SoulseekClient` | Erreur réseau/API | `ERROR` |
| `BotRecherche` | Erreur de recherche | `WARN` |
| `BotTéléchargement` | Échec de transfert | `ERROR` |
| `PlanificateurService` | Tâche échouée | `WARN` |
| `BotOptimiseur` | Optimisation impossible | `WARN` |

---

## 📊 Cycle de vie d'une notification

```
t=0s     Un événement ERROR/WARN est émis
         ↓
         _on_toast_event() reçoit l'événement
         ↓
         show_toast() crée la carte, l'affiche en haut à droite
         ↓
         QTimer.singleShot(4000) est lancé
         ↓
t=4s     _remove_toast() supprime la carte (deleteLater)
         ↓
         Si plus aucun toast : overlay masqué
```

### Gestion de la pile

Lorsque plusieurs toasts arrivent simultanément :

1. Les cartes s'empilent **verticalement** (de haut en bas)
2. Chaque nouvelle carte s'ajoute **en dessous** des précédentes
3. Si le nombre dépasse **5** toasts simultanés, la **plus ancienne** est supprimée
4. L'espacement entre les cartes est de **8px**

### Exemple d'affichage

```
┌──────────────────────────────────┐
│ ❌ Erreur de connexion           │  ← Toast 1 (la plus récente)
│ Impossible de contacter le serveu│
├──────────────────────────────────┤
├──────────────────────────────────┤
│ ⚠️ Recherche interrompue         │  ← Toast 2
│ Le timeout de 30s a été atteint  │
├──────────────────────────────────┤
├──────────────────────────────────┤
│ ❌ Échec du téléchargement       │  ← Toast 3 (la plus ancienne)
│ fichier.rar - timeout réseau     │
└──────────────────────────────────┘
```

---

## 🔧 Personnalisation

### Modifier la durée d'affichage

```python
_TOAST_DURATION_MS = 4000   # 4 secondes (défaut)
# _TOAST_DURATION_MS = 6000  # 6 secondes
# _TOAST_DURATION_MS = 2000  # 2 secondes
```

### Modifier le nombre maximum de toasts

```python
_MAX_TOASTS = 5   # Maximum de toasts simultanés
```

### Ajouter une sévérité personnalisée

```python
_SEVERITY_COLORS = {
    "ERROR":  ("#e74c3c", "#ffffff"),
    "WARN":   ("#f39c12", "#ffffff"),
    "INFO":   ("#3498db", "#ffffff"),
    "DEBUG":  ("#2ecc71", "#ffffff"),  # Nouvelle sévérité
}

_SEVERITY_ICONS = {
    "ERROR": "❌",
    "WARN":  "⚠️",
    "INFO":  "ℹ️",
    "DEBUG": "🐛",                     # Icône pour la nouvelle sévérité
}
```

### Activer les toasts INFO dans MainWindow

```python
# Pour afficher aussi les toasts INFO :
if event.severity in ("ERROR", "WARN", "INFO"):
    self._toast.show_toast(...)
```

---

## 🔗 Voir aussi

- `/technique/event-bus-surveillance` — Système d'événements (EventBus) et écouteurs
- `/technique/flux-donnees-evenements` — Flux de données et événements
- `/technique/systeme-theme` — Système de thème et personnalisation de l'interface
- `/technique/architecture-application` — Architecture générale de l'application
