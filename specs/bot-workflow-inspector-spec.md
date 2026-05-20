# Spécification — Workflow & Loop Inspector

> **Statut :** 📝 Spec — prête pour implémentation
> **Dernière mise à jour :** 2026-05-19 (v2 — corrections post-review)
> **Raccourci clavier :** `Ctrl+Shift+W`
> **Emplacement :** `src/gui/devtool/workflow_inspector.py` (nouveau dock indépendant)
> **Menu :** Outils → Workflow & Loop Inspector (checkable)

---

## 🎯 Objectif

Dashboard centralisé qui donne une **vue d'ensemble** de tous les bots, services, boucles asynchrones et flux de données de l'application. Complète le `ServiceInspector` (focus technique sur la connexion réseau) par une vue **orientée bots et workflow**.

**Problème résolu :** 12 bots + services centraux sans visibilité centralisée. Impossible de savoir :
- Quel bot tourne ? Quel bot est arrêté ?
- Quels événements chaque bot émet/reçoit ?
- Y a-t-il des boucles bloquées, des threads pendus, des timers fantômes ?
- Quel est le flux des données entre les bots (recherche → téléchargement → classement → ...) ?

---

## 1. Architecture

### 1.1 Emplacement

- **Nouveau fichier :** `src/gui/devtool/workflow_inspector.py`
- **Classe :** `WorkflowInspector(QDockWidget)`
- **Menu :** Outils → Workflow & Loop Inspector (`Ctrl+Shift+W`)
- **Registration :** Dans `src/gui/main_window.py`, ajouté comme `self.addDockWidget(...)` comme les autres devtools
- **Export :** Dans `src/gui/devtool/__init__.py`, ajouté à `__all__`

### 1.2 Héritage

```python
class WorkflowInspector(QDockWidget):
    """Dashboard centralisé de surveillance des bots, services et flux."""

    def __init__(self, main_window: QMainWindow, parent=None) -> None
```

### 1.3 Dépendances

| Dépendance | Usage |
|------------|-------|
| `src.services.event_bus.EventBus` | Écouter les événements émis → nourrir la matrice d'échanges et les indicateurs |
| `src.gui.main_window.MainWindow` | Accès aux bots via `center._pages[]` + `center._bot_*`, services via attributs privés, connexion manager |
| `threading` | `threading.enumerate()` pour lister les threads actifs |
| `sys` | `sys._current_frames()` pour les stack traces |
| `asyncio` | `asyncio.all_tasks()` pour les tâches boucle réseau |
| `QTimer` | Polling événementiel + debounce |
| `QtCore.QThread` | `QThread.isRunning()` pour détecter les workers |

---

## 2. Interface utilisateur

### 2.1 Disposition générale

```
┌──────────────────────────────────────────────────────────────────┐
│ [🔄 Refresh] [⏸ Pause] │                Compteur: #0            │ ← Toolbar
├──────────────────────────────────────────────────────────────────┤
│ 📊 TABLEAU DE BORD — BOTS & SERVICES                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 📡 Soulseek Client  │ 🟢 ONLINE  │ up: 2h34  │ 28 events │   │ ← Carte bot/service
│  │ │ ├─ asyncio tasks: 3  │ mem: 48MB  │ threads: 4  │        │
│  │ │ └─ timers: 2 (ping, refresh)                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 🔍 Recherche Bot    │ 🟢 ACTIVE  │ up: 2h34  │ 12 events │   │
│  │ │ ├─ asyncio tasks: 0  │ mem: 12MB  │ threads: 1  │        │
│  │ │ └─ timers: 1 (debounce search)                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ⬇ Téléchargement Bot│ 🟢 ACTIVE  │ up: 2h34  │ 45 events │   │
│  │ │ ├─ asyncio tasks: 2  │ mem: 32MB  │ threads: 2  │        │
│  │ │ └─ timers: 1 (progress report)                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ... (tous les bots et services)                                │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│ 📊 MATRICE DES ÉCHANGES (session en cours)                      │
├──────────────────────────────────────────────────────────────────┤
│            │ RECH   │ TÉLÉC  │ SURV   │ EVENT  │ CONNEX │       │
│────────────┼────────┼────────┼────────┼────────┼────────│       │
│ RECHERCHE  │   ·    │   8    │   5    │   3    │   0    │       │
│ TÉLÉCHARG. │   0    │   ·    │  12    │   2    │   0    │       │
│ SURVEILL.  │   0    │   0    │   ·    │   0    │   0    │       │
│ EVENTBUS   │   0    │   0    │  28    │   ·    │   0    │       │
│ CONNEXION  │   0    │   0    │   6    │   3    │   ·    │       │
│ ...        │        │        │        │        │        │       │
├──────────────────────────────────────────────────────────────────┤
│ 📈 ACTIVITÉ RÉCENTE (ring buffer 200 events)                     │
├──────────────────────────────────────────────────────────────────┤
│ [14:32:15] 🔍 Recherche → ⬇ Téléchargement: démarré DL de ...  │
│ [14:32:14] 📡 Soulseek → 🔍 Recherche: résultat reçu (15 fics) │
│ [14:32:13] ⬇ Téléchargement → 🗑️ Dédoublonnage: fichier ...    │
│ ...                                                             │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Barre d'outils (toolbar)

| Bouton | Action |
|--------|--------|
| 🔄 **Refresh** | Rafraîchir manuellement l'état de tous les bots (événementiel normalement) |
| ⏸ **Pause / ▶ Play** | Suspendre/reprendre la mise à jour événementielle |
| #0 | Compteur de rafraîchissements (pratique pour savoir si les données sont à jour) |

### 2.3 Section 1 : Tableau de bord — Bots & Services

**Colonnes par carte :**

| Champ | Source | Format |
|-------|--------|--------|
| **Nom** | Classe / service | `🔍 Recherche`, `📡 Soulseek`, `💬 RoomService`… |
| **Statut** | `isRunning()` / `_demarre` / `is_alive()` | 🟢 ACTIVE / 🔴 STOPPED / 🟡 STARTING / ⚪ UNKNOWN |
| **Uptime** | Timestamp démarrage → maintenant | `2h 34m`, `5m 12s`, `—` si arrêté |
| **Événements** | Compteur EventBus (session) | `28 events` |
| **Tâches asyncio** | `asyncio.all_tasks(boucle)` | `3 tâches` (détail au hover) |
| **Mémoire** | `getattr(obj, ...)` estimation indirecte | `48 MB` (taille Python approximative) |
| **Threads** | `threading.enumerate()` | `4 threads` |
| **Timers** | Scan QTimer actifs | `2 timers` |

**Liste des bots et services à afficher :**

| # | Nom | Icône | Classe source | Détection auto |
|---|------|-------|---------------|----------------|
| 1 | Soulseek Client | 📡 | `SoulseekService` (singleton) | Accès direct |
| 2 | Connexion Manager | 🔌 | `ConnexionManager` | `main_window._connexion_manager` |
| 3 | Event Bus | 📨 | `EventBus()` (singleton) | Accès direct |
| 4 | Room Service | 💬 | `RoomService` | `main_window._room_service` |
| 5 | Clients Actifs | 👥 | `ClientsActifsService` | `center._clients_actifs_service` |
| 6 | Accueil | 🏠 | `BotAccueil` | `center._bot_accueil` |
| 7 | Bibliothèque | 📚 | `BotBibliotheque` | `center._bibliotheque_page` |
| 8 | Optimiseur | ⚡ | `BotOptimiseur` | `center._bot_optimiseur` |
| 9 | Ordonnanceur | 🧹 | `BotOrdonnanceur` | `center._bot_ordonnanceur` |
| 10 | Planificateur | 📅 | `BotPlanificateur` | `center._bot_planificateur` |
| 11 | Recherche | 🔍 | `BotRecherche` | `center._pages["Recherche"]` |
| 12 | Surveillance | 👁️ | `BotSurveillance` | `center._bot_surveillance` |
| 13 | Téléchargement | ⬇️ | `BotTelechargement` | `center._pages["telechargements"]` (⚠️ clé interne lowercase "telechargements") |
| 14 | Wishlist | ⭐ | `BotWishlist` | `center._pages["Wishlist"]` |
| 15 | Aide | ❓ | `BotAide` (placeholder — `QWidget()` vide) | `center._pages["Aide"]` |
| 16 | Assistant | 🤖 | `BotAssistant` (placeholder — `QWidget()` vide) | `center._pages["Assistant"]` |

**Actions par carte :**

- **Au survol :** infobulle avec détails (dernière action, files d'attente, etc.)
- **Clic sur le nom :** navigue vers la page du bot dans le stack central (si applicable)
- **Bouton toggle Démarrer/Arrêter :** appel `demarrer()` / `arreter()` si le bot expose ces méthodes

### 2.4 Section 2 : Matrice des échanges (session en cours)

**Principe :** Tableau carré N×N où :
- **Lignes = émetteurs** (source de l'événement EventBus)
- **Colonnes = récepteurs** (contexte de l'événement)
- **Valeur = nombre d'événements** depuis le début de la session

**Détection auto des sources :**
- Intercepter tous les événements EventBus (`event_emitted.connect`)
- Extraire le champ `source` de chaque `SurveillanceEvent`
- Mapper automatiquement la chaîne source vers le nom d'affichage via un dictionnaire de mapping connu
- Les sources inconnues apparaissent dans une ligne "Autres" à la fin

**Mapping connu (hardcodé dans une classe `_SOURCE_MAP`) :**

| Source EventBus | Nom affiché | Icône |
|----------------|-------------|-------|
| `connexion_manager` | Connexion | 🔌 |
| `soulseek_service`, `soulseek_client` | Soulseek | 📡 |
| `room_service` | Room Service | 💬 |
| `clients_actifs_service` | Clients Actifs | 👥 |
| `event_bus`, `EventBus` | Event Bus | 📨 |
| `bot_accueil` | Accueil | 🏠 |
| `bot_bibliotheque` | Bibliothèque | 📚 |
| `bot_optimiseur` | Optimiseur | ⚡ |
| `bot_ordonnanceur` | Ordonnanceur | 🧹 |
| `bot_planificateur` | Planificateur | 📅 |
| `bot_recherche` | Recherche | 🔍 |
| `bot_surveillance` | Surveillance | 👁️ |
| `bot_telechargement` | Téléchargement | ⬇️ |
| `bot_wishlist` | Wishlist | ⭐ |
| `bot_aide` | Aide | ❓ |
| `bot_assistant` | Assistant | 🤖 |

**Comportement :**
- La diagonale est vide (un bot ne s'envoie pas d'événement à lui-même)
- Les compteurs sont reset au démarrage de l'app (session seulement)
- Les cellules avec valeur 0 affichent `—`
- Les cellules avec valeur > 0 affichent le nombre
- Les valeurs élevées (> 100) sont colorées en orange, > 1000 en rouge
- Les colonnes sont triables par nom ou par total

### 2.5 Section 3 : Activité récente (timeline)

- **Ring buffer de 200 événements** (pas une fenêtre temporelle "15 dernières secondes" — trop dépendant du volume d'événements)
- Chaque ligne : `[HH:MM:SS] Émetteur → Récepteur: message`
- Utilise le flux EventBus comme source de données
- Filtre : n'affiche que les événements avec `source` connue (mappée)
- Auto-scroll vers le bas par défaut, avec bouton ⬇ pour revenir en bas si l'utilisateur a scrollé
- Affichage limité aux **100 lignes les plus récentes** dans l'UI (le ring buffer garde 200 en mémoire, les 100 plus anciennes sont accessibles en scrollant vers le haut)
- **Nettoyage au closeEvent** : vider le ring buffer pour libérer la mémoire

### 2.6 Boutons d'action (bas du dock)

| Bouton | Action |
|--------|--------|
| 🔄 **Démarrer/Arrêter** | Toggle chaque bot individuellement (bouton présent dans chaque carte) |
| 🔄 **Reset matrice** | Remet les compteurs de la matrice à zéro (pas la timeline) |
| 📋 **Exporter rapport** | Copie l'état complet (tous les bots + matrice) dans le presse-papier |
| 🗑️ **Cleanup threads** | Nettoie les références aux workers terminés |

---

## 3. Rafraîchissement événementiel

### 3.1 Principe

Pas de polling timer (comme le ServiceInspector). Le dock se met à jour **uniquement** quand :

1. Un événement `EventBus` est émis → incrémente le compteur du bot source
2. Un bot change d'état → détecté via les signaux de démarrage/arrêt
3. L'utilisateur clique sur 🔄 Refresh

### 3.2 Connexion à l'EventBus — et déconnexion à la fermeture

```python
def _connect_event_bus(self) -> None:
    """Connecte à l'EventBus. Stocke la référence pour déconnexion."""
    self._eventbus = EventBus()
    self._eventbus.event_emitted.connect(self._on_event)

def closeEvent(self, event) -> None:
    """Déconnecte impérativement l'EventBus pour éviter les fuites de référence."""
    if hasattr(self, "_eventbus"):
        try:
            self._eventbus.event_emitted.disconnect(self._on_event)
        except (TypeError, RuntimeError):
            pass  # déjà déconnecté
    super().closeEvent(event)
```

### 3.3 Connexion aux services

- Connecter les signaux des services pour détecter les changements d'état :
  - `soulseek_service.connected` / `disconnected`
  - `connexion_manager.connected` / `disconnected`

### 3.4 Refresh manuel complet

`refresh_all()` :
1. Rescanner `center._pages` + `center._bot_*` + attributs `main_window` pour trouver tous les bots et services
2. Vérifier l'état (running/stopped) de chacun (stratégie différente selon le type)
3. Mettre à jour les cartes
4. Reconstruire la matrice d'échanges si nécessaire
5. Mettre à jour la timeline
6. Vérifier les threads actifs (`threading.enumerate()`)
7. Vérifier les tâches asyncio (boucle réseau)

---

## 4. Détection des indicateurs

### 4.1 Statut d'un bot — 3 catégories distinctes

**Les bots Qt et les services n'ont pas le même cycle de vie :**

| Catégorie | Type | Mécanisme de statut | Valeurs |
|-----------|------|---------------------|---------|
| **Services** (`RoomService`, `ClientsActifsService`, `SoulseekService`) | `QObject` avec cycle de vie | `_running: bool` | `ACTIVE` / `STOPPED` |
| **Bots Qt** (`BotAccueil`, `BotRecherche`, etc.) | `QFrame` dans le stack central | Toujours `ACTIVE` (ils vivent dans le stack, pas de cycle propre) | `ACTIVE` uniquement |
| **ConnexionManager** | Gestionnaire de connexion | `self._running` + `_async_thread.is_alive()` | `ACTIVE` / `STOPPED` |
| **EventBus** | Singleton permanent | Toujours `ACTIVE` | `ACTIVE` uniquement |

> **Note :** Les bots Qt (`BotAccueil`, `BotRecherche`, etc.) n'ont **pas** de flag `_running`, `_demarre`, ni `isRunning()`. Ils sont créés une fois et vivent dans le stack central. Leur statut est toujours `ACTIVE` tant que la page existe. Les services en revanche exposent `demarrer()` / `arreter()` avec flag `_running`.

```python
def _get_bot_status(self, name: str, instance: QObject) -> str:
    """Retourne le statut : ACTIVE / STOPPED / STARTING / UNKNOWN.
    
    La détection diffère selon le type de l'instance :
    - Services → flag _running
    - Bots Qt → toujours ACTIVE (pas de cycle propre)
    - ConnexionManager → _running + thread
    - EventBus → toujours ACTIVE
    - Autres → UNKNOWN
    """
    # ── Catégorie 1 : Bots Qt (QFrame dans le stack) ──
    if isinstance(instance, QFrame):
        return "ACTIVE"
    
    # ── Catégorie 2 : EventBus (singleton permanent) ──
    if isinstance(instance, EventBus):
        return "ACTIVE"
    
    # ── Catégorie 3 : Services avec _running flag ──
    running = getattr(instance, "_running", None)
    if running is True:
        return "ACTIVE"
    if running is False:
        return "STOPPED"

    # ── Catégorie 4 : ConnexionManager (thread asyncio) ──
    if hasattr(instance, "_async_thread"):
        thread = instance._async_thread
        if thread is not None and thread.is_alive():
            return "ACTIVE"
        return "STOPPED"

    # ── Catégorie 5 : Fallback QThread ──
    if hasattr(instance, "isRunning") and instance.isRunning():
        return "ACTIVE"
    
    return "UNKNOWN"
```

### 4.1bis Cas particulier : BotAide et BotAssistant

Ces deux pages sont des **placeholders** : dans `center._build_menu_page()`, ce sont de simples `QWidget()` vides avec un titre, **pas** des instances de `BotAide`/`BotAssistant`. Leur carte dans le WorkflowInspector aura des sous-indicateurs limités (threads, timers — tout à 0). Elles sont listées comme "Aide" et "Assistant" dans la matrice pour couvrir les événements éventuels, mais leur statut est toujours `ACTIVE`.

### 4.2 Threads

```python
def _get_threads_for_object(self, obj) -> list[str]:
    """Retourne les threads associés à un objet ou ses workers."""
    threads = []
    for t in threading.enumerate():
        name = t.name or ""
        # Vérifier si le thread appartient à ce bot
        if isinstance(t, QThread):
            parent = t.parent()
            if parent is obj:
                threads.append(t)
        # Fallback: matching thread name pattern
        if str(obj.__class__.__name__) in name:
            threads.append(t)
    return threads
```

### 4.3 Timers

```python
def _get_timers_for_object(self, obj) -> list[QTimer]:
    """Retourne les QTimer actifs enfants de l'objet."""
    return [
        child for child in obj.findChildren(QTimer)
        if child.isActive()
    ]
```

### 4.4 Tasks asyncio

Déjà disponible via `ServiceInspector.refresh_asyncio_tasks()` — à réutiliser ici pour la carte Soulseek Client.

### 4.5 Mémoire (estimation)

> ⚠️ **Limitation :** `sys.getsizeof()` ne mesure que la taille de l'objet Python, pas la mémoire Qt/C++ sous-jacente. Pour un `QWidget`, `getsizeof` retourne ≈ 0–100 bytes même si le widget utilise 50 MB en mémoire C++. 
>
> **Solution retenue :** Afficher `"N/A"` avec une infobulle expliquant la limitation. Pour une vraie mesure mémoire, utiliser un profileur externe (memory_profiler, tracemalloc). Le compteur d'événements + la détection des fuites de références (workers zombies vs workers nettoyés) sont des indicateurs plus pratiques.

```python
def _estimate_memory(self, obj) -> str:
    """Retourne la mention 'N/A' — la vraie mémoire Qt/C++ n'est pas accessible depuis Python.
    
    sys.getsizeof retourne ~0-100 bytes pour tout widget Qt, ce qui est trompeur.
    On affiche N/A avec une infobulle qui explique pourquoi.
    """
    return "N/A"
```

**Alternative future (si nécessaire) :** Utiliser `tracemalloc` pour tracker les allocations Python, ou un appel système `psutil.Process().memory_info()` pour la mémoire totale du processus — pas par bot.

---

## 5. Détection des connexions inter-bots

### 5.1 Méthode : Auto-détection par analyse du code

Au démarrage du dock, analyser les connexions Qt entre les objets :

1. Scanner tous les signaux de chaque bot (via `bot_instance.__class__.__dict__`)
2. Vérifier quels signaux sont connectés (via une méthode de détection basique)
3. Logguer les connexions trouvées

```python
def _detect_connections(self) -> dict[str, set[str]]:
    """Analyse les connexions inter-bots."""
    connections = {}
    
    # Parcourir chaque bot
    for name, instance in self._all_bots.items():
        # Chercher les signaux dans sa classe
        for attr_name in dir(instance):
            attr = getattr(instance.__class__, attr_name, None)
            if isinstance(attr, Signal):
                # Vérifier si quelqu'un est connecté
                # (approche indirecte: on regarde les cibles des signaux)
                pass
    
    return connections
```

**Alternative plus pragmatique :** Utiliser la matrice EventBus comme proxy — les connexions sont inférées par les échanges d'événements.

### 5.2 Mapping source EventBus → nom bot

Dictionnaire statique dans `_SOURCE_MAP` (voir §2.4). Au démarrage, scanner les événements reçus et mapper les sources inconnues :

```python
# Sources connues
_SOURCE_MAP = {
    "connexion_manager": ("Connexion", "🔌"),
    "soulseek_service": ("Soulseek", "📡"),
    "soulseek_client": ("Soulseek", "📡"),
    "room_service": ("Room Service", "💬"),
    "clients_actifs_service": ("Clients Actifs", "👥"),
    "event_bus": ("Event Bus", "📨"),
    "bot_accueil": ("Accueil", "🏠"),
    "bot_bibliotheque": ("Bibliothèque", "📚"),
    "bot_optimiseur": ("Optimiseur", "⚡"),
    "bot_ordonnanceur": ("Ordonnanceur", "🧹"),
    "bot_planificateur": ("Planificateur", "📅"),
    "bot_recherche": ("Recherche", "🔍"),
    "bot_surveillance": ("Surveillance", "👁️"),
    "bot_telechargement": ("Téléchargement", "⬇️"),
    "bot_wishlist": ("Wishlist", "⭐"),
    "bot_aide": ("Aide", "❓"),
    "bot_assistant": ("Assistant", "🤖"),
}
```

---

## 6. Navigation et intégration

### 6.1 Menu Outils

```python
# Dans MainWindow._build_menu()
workflow_action = QAction("Workflow & Loop Inspector", self)
workflow_action.setShortcut("Ctrl+Shift+W")
workflow_action.setCheckable(True)
workflow_action.toggled.connect(self._toggle_workflow_inspector)
tools_menu.addAction(workflow_action)
```

### 6.2 Dock

```python
# Dans MainWindow.__init__()
self._workflow_inspector = WorkflowInspector(self)
self.addDockWidget(Qt.RightDockWidgetArea, self._workflow_inspector)
self._workflow_inspector.hide()
```

### 6.3 Clic sur une carte → navigation vers le bot

```python
def _on_card_clicked(self, bot_name: str) -> None:
    """Navigue vers la page du bot dans le centre."""
    center = self._main_window.center
    if hasattr(center, "show_page"):
        center.show_page(bot_name)
```

---

## 7. Implémentation

### 7.1 Nouveaux fichiers

| Fichier | Étape |
|---------|-------|
| `src/gui/devtool/workflow_inspector.py` | 1 — Création du dock complet |

### 7.2 Fichiers à modifier

| Fichier | Changement |
|---------|------------|
| `src/gui/main_window.py` | Ajouter `_build_menu` entry + dock creation + toggle method |
| `src/gui/devtool/__init__.py` | Ajouter `WorkflowInspector` dans `__all__` et import |

### 7.3 Structure de la classe

```python
class WorkflowInspector(QDockWidget):

    # ── Mapping source EventBus → nom bot ──
    _SOURCE_MAP: dict[str, tuple[str, str]] = { ... }

    def __init__(self, main_window: QMainWindow, parent=None) -> None
    def _build_ui(self) -> None
    def _apply_style(self) -> None

    # ── Toolbar ──
    def _build_toolbar(self) -> QHBoxLayout
    def refresh_all(self) -> None
    def _toggle_polling(self) -> None

    # ── Section 1 : Cartes bots ──
    def _build_bot_cards(self) -> None
    def _create_bot_card(self, name: str, icon: str, instance: QObject) -> QFrame
    def _get_bot_status(self, name: str, instance: QObject) -> str
    def _update_card(self, card: QFrame, name: str, instance: QObject) -> None
    def _scan_all_bots(self) -> dict[str, QObject]
    def _estimate_memory(self, obj) -> str
    def _get_threads_for_object(self, obj) -> list
    def _get_timers_for_object(self, obj) -> list[QTimer]
    def _estimate_uptime(self, instance) -> str

    # ── Section 2 : Matrice ──
    def _build_matrix(self) -> None
    def _update_matrix(self) -> None
    def _reset_matrix(self) -> None
    def _on_event(self, event: SurveillanceEvent) -> None
    def _increment_matrix(self, source: str) -> None

    # ── Section 3 : Timeline ──
    def _build_timeline(self) -> None
    def _update_timeline(self, event: SurveillanceEvent) -> None
    def _append_timeline_line(self, line: str) -> None

    # ── Section 4 : Boutons d'action ──
    def _build_action_buttons(self) -> QHBoxLayout
    def _on_reset_matrix(self) -> None
    def _on_export_report(self) -> None
    def _on_toggle_bot(self, bot_name: str) -> None

    # ── Fermeture — IMPORTANT : déconnecter les signaux EventBus ──
    def closeEvent(self, event) -> None
```

### 7.4 Widgets Qt utilisés

| Widget | Usage |
|--------|-------|
| `QScrollArea` | Conteneur principal scrollable |
| `QVBoxLayout` | Layout vertical des 3 sections |
| `QFrame` | Carte de chaque bot (avec style arrondi + bordure) |
| `QGridLayout` | Disposition des infos dans une carte |
| `QLabel` | Icône, nom, statut, uptime, compteurs |
| `QPushButton` | Refresh, Pause, Reset, Exporter, Toggle bot |
| `QTableWidget` | Matrice des échanges |
| `QToolBar` | Barre d'outils du dock |
| `QSplitter` | Séparation verticale entre les 3 sections |

---

## 8. Style

Même thème que le ServiceInspector (catppuccin-like) :

```css
/* Dock */
background: #11111b; color: #cdd6f4; border: 1px solid #313244;

/* Title bar */
background: #181825; padding: 6px; font-weight: 600;

/* Bot card */
background-color: #1e1e2e; border: 1px solid #313244;
border-radius: 6px; padding: 8px;

/* Status labels */
ACTIVE → color: #a6e3a1; font-weight: bold;
STOPPED → color: #f38ba8; font-weight: bold;
STARTING → color: #f9e2af; font-weight: bold;

/* Table */
background-color: #11111b; border: 1px solid #313244;
font-family: 'Consolas', 'Courier New', monospace; font-size: 10px;

/* Scrollbar */
QScrollBar:vertical { background: #181825; width: 8px; }
QScrollBar::handle:vertical { background: #45475a; border-radius: 4px; }
```

---

## 9. Ordre d'implémentation

| # | Étape | Description | Dépend de |
|---|-------|-------------|-----------|
| 1 | Squelette dock | Créer `WorkflowInspector(QDockWidget)` + registration dans `main_window.py` + `__init__.py` | — |
| 2 | Section 1 : Cartes bots | Scanner les bots, créer les cartes avec indicateurs | #1 |
| 3 | Section 2 : Matrice | Construire la matrice N×N, connecter à l'EventBus | #1, #2 |
| 4 | Section 3 : Timeline | Afficher les événements récents formatés | #1, #3 |
| 5 | Boutons d'action | Toggle bot, Reset matrice, Exporter rapport, Cleanup | #2, #3, #4 |
| 6 | Raffinements + polish | Style, hover, navigation par clic sur carte | #5 |
| 7 | Tests | Tests d'intégration du dock avec EventBus | #6 |

---

## 10. Questions résolues

### Architecture vs ServiceInspector

- [x] **Pourquoi un dock séparé plutôt qu'un onglet dans ServiceInspector ?** Le ServiceInspector est focalisé sur la connexion réseau (état Soulseek, tâches asyncio, diagnostic brut, logs, contrôle de timeout). Le WorkflowInspector est focalisé sur les bots (état, cycles de vie, flux inter-bots, matrice d'échanges). Les deux sont complémentaires mais suffisamment différents pour justifier deux docks distincts.

- [x] **Différence avec BotSurveillance ?** BotSurveillance montre le flux d'événements EventBus (timeline). WorkflowInspector montre en plus : l'état de chaque bot, la matrice d'échanges, les threads/timers, et permet d'agir (démarrer/arrêter). Surveillance = passif, Workflow = actif + vue d'ensemble.

### Rafraîchissement

- [x] **Pourquoi événementiel plutôt que polling ?** Le polling à 1.5s (comme ServiceInspector) gaspille des cycles CPU pour n'afficher que des données qui changent peu (état des bots). L'EventBus notifie déjà tous les événements importants — autant s'en servir. Le refresh manuel reste disponible pour les cas où l'utilisateur veut forcer une mise à jour.

### Matrice

- [x] **Pourquoi session seulement et pas 24h ?** La matrice est un outil de diagnostic en direct. La persistance sur 24h ajouterait de la complexité (SQLite, purge) pour un bénéfice limité. La session actuelle suffit à identifier les patterns d'échange entre bots.

- [x] **Diagonale vide dans la matrice** : Un bot ne peut pas émettre un événement vers lui-même via l'EventBus (le champ `source` est unique par événement). La diagonale affiche `—`.

### Mapping des sources

- [x] **Mapping statique plutôt qu'auto-détection complète** : L'auto-détection totale des connexions inter-bots (analyse de code, introspection des signaux Qt) est complexe et fragile. Le mapping statique dans `_SOURCE_MAP` est fiable et rapide. Les sources inconnues sont collectées dans une ligne "Autres" — ce qui permet d'étendre le mapping progressivement.

- [x] **Pourquoi ne pas standardiser les noms de source EventBus ?** Ça casserait la compatibilité avec les émetteurs existants. Le mapping statique fait la translation sans rien casser.

### Mémoire

- [x] **Estimation grossière par `sys.getsizeof`** : `getsizeof` ne donne pas la mémoire réelle d'un objet Qt (qui est souvent en C++). C'est une approximation. Pour un outil de diagnostic, c'est suffisant — le but est de détecter les fuites mémoire évidentes (un bot qui prend 500 MB vs 10 MB). Pour des mesures précises, il faudrait `tracemalloc` (trop lourd).

---

## 11. Tests

| # | Test | Description |
|---|------|-------------|
| 1 | `test_dock_cree()` | Dock créé sans erreur, titre correct |
| 2 | `test_bots_scannes()` | Tous les bots détectés dans `center._pages` |
| 3 | `test_cartes_affichees()` | Chaque bot a une carte avec les 6 indicateurs |
| 4 | `test_matrice_initialisee()` | Matrice N×N créée avec les bons en-têtes |
| 5 | `test_evenement_matrice()` | Émission EventBus → cellule incrémentée |
| 6 | `test_timeline_affichee()` | Événement → ligne dans la timeline |
| 7 | `test_reset_matrice()` | Reset → toutes les cellules à 0 |
| 8 | `test_export_rapport()` | Copie presse-papier contient tous les états |
| 9 | `test_statut_bot()` | Bot actif → 🟢, bot arrêté → 🔴 |
| 10 | `test_toggle_bot()` | Clic toggle → bot démarré/arrêté |

---

*Spec v1 — prête pour implémentation. En attente de validation.*
