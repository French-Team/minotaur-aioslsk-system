---
title: "Système d'événements (EventBus) et écouteurs"
category: "technique"
icon: "🔔"
keywords:
  - event bus surveillance
  - systeme evenements
  - système événement
  - ecouteur evenement
  - écouteur événement
  - surveillance event
  - emit event
  - signal qt evenement
  - signal qt événement
  - singleton event bus
  - sqlite surveillance
  - purge evenement
  - purge événement
  - evenement reseau
  - événement réseau
  - evenement recherche
  - événement recherche
  - notification toast
  - bot surveillance evenement
  - bot surveillance événement
  - file evenement soulseek
  - fichier événement soulseek
  - systeme evenement
  - ecouteur evenement
  - notification toast
---

# 🔔 Système d'événements (EventBus) et écouteurs

L'application utilise un **bus d'événements centralisé** pour découpler les émetteurs d'événements des consommateurs. Chaque composant (bot, service réseau, planificateur) peut émettre un événement sans connaître les listeners — et chaque listener peut réagir sans connaître la source.

---

## 🏗️ Architecture générale

```
┌─────────────────┐     ┌──────────────────────────────────────┐     ┌─────────────────┐
│   Émetteurs     │     │            EventBus                  │     │   Écouteurs     │
│                 │     │                                      │     │                 │
│ ConnexionManager│────>│  Singleton thread-safe (QObject)     │────>│ BotSurveillance  │
│ BotRecherche    │     │  Signal: event_emitted(SurveillanceEvent) │     │  → _on_event_received │
│ BotTelechargement│    │  SQLite: data/bot_surveillance.db    │     │ MainWindow       │
│ Planificateur   │     │  Timer: purge auto (1h)              │     │  → _on_toast_event    │
│ SoulseekClient  │     │  Pause/Resume                        │     │ Logger (stdout)  │
│ BotBibliotheque │     │                                      │     │                 │
│ BotOptimiseur   │     └──────────────────────────────────────┘     └─────────────────┘
│ BotWishlist     │
└─────────────────┘
```

### Flux d'un événement

```
1. Émetteur appelle  EventBus().emit_event(severity, category, title, message, source)
2. EventBus crée     SurveillanceEvent (dataclass avec horodatage + validation)
3. Persiste en       SQLite (table events)
4. Émet via          Signal Qt event_emitted.emit(event)
5. Chaque listener   Reçoit l'objet SurveillanceEvent dans son callback connecté
```

---

## 📦 La classe EventBus

**Fichier :** `src/services/event_bus.py` — ligne 117

### Singleton thread-safe

```python
class EventBus(QObject):
    event_emitted = Signal(object)

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls, *args, **kwargs)
                    cls._instance._initialized = False
        return cls._instance
```

- Utilisation d'un **double-checked locking** pour garantir une instance unique
- Le verrou `threading.Lock()` assure la sécurité entre threads
- L'accès se fait via `EventBus()` — pas de getter, pas de variable globale

### Signal Qt

```python
event_emitted = Signal(object)
```

- Signal typé PySide6 — transmet un objet `SurveillanceEvent`
- Utilisable avec `connect()` / `emit()` / `disconnect()` standard Qt
- Compatible avec le thread principal (les signaux Qt sont thread-safe via la boucle d'événements)

### Initialisation

```python
def __init__(self):
    if self._initialized:
        return
    self._paused = False
    self._db = None
    self._ensure_data_dir()       # Crée data/ si nécessaire
    self._connect_db()            # Ouvre la connexion SQLite
    self._ensure_schema()         # Crée/migre la table events
    self._start_purge_timer()     # Timer QTimer (1h) pour purge
    self._initialized = True
```

### Persistance SQLite

**Fichier :** `data/bot_surveillance.db`

- **Version du schéma :** 2
- **Mode WAL** (Write-Ahead Logging) pour performances en écriture
- **Table `events`** avec colonnes : `id`, `timestamp`, `severity`, `category`, `title`, `message`, `source`, `details`, `created_at`
- **Index :** `timestamp`, `category`, `severity`, `source`, `created_at`

### Méthode `emit_event`

```python
def emit_event(self, severity="INFO", category="bot", title="", message="", source="", details=None) -> SurveillanceEvent | None
```

1. Vérifie que le bus n'est pas en pause (`self._paused`)
2. Crée un objet `SurveillanceEvent` avec validation des champs
3. Persiste en SQLite (INSERT)
4. Émet le signal `event_emitted.emit(event)`
5. Retourne l'événement créé

### Gestion du cycle de vie

| Méthode | Rôle |
|---|---|
| `pause()` | Suspend la collecte — `emit_event` ne fait rien |
| `resume()` | Reprend la collecte |
| `query(...)` | Requête avec filtres AND (catégorie, sévérité, source, texte, dates) |
| `get_recent(n)` | Les n derniers événements |
| `get_stats()` | Stats agrégées : total, erreurs 24h, par catégorie |
| `purge_old()` | Supprime les événements > 7 jours (retourne le nombre supprimé) |
| `_start_purge_timer()` | Timer QTimer déclenchant `purge_old()` toutes les heures |

---

## 📋 Le modèle SurveillanceEvent

**Fichier :** `src/services/event_bus.py` — ligne 80

```python
@dataclass
class SurveillanceEvent:
    id: int = 0
    timestamp: str = ""          # ISO 8601, auto-généré si vide
    severity: str = "INFO"       # "INFO" | "WARN" | "ERROR"
    category: str = "bot"        # Catégorie fonctionnelle
    title: str = ""
    message: str = ""
    source: str = ""
    details: dict[str, Any] | None = None
    created_at: str = ""
```

### Validation dans `__post_init__`

- `severity` doit être `"INFO"`, `"WARN"` ou `"ERROR"` — lève `ValueError` sinon
- `category` doit être dans une liste fermée de catégories autorisées

---

## 📡 Émetteurs d'événements

### 1. ConnexionManager — `src/services/connexion_manager.py`

| Événement | Severity | Category | Title |
|---|---|---|---|
| ✅ Connexion réussie | `INFO` | `reseau` | « Connecté à Soulseek » |
| ⚠️ Déconnexion | `WARN` | `reseau` | « Déconnecté de Soulseek » |
| ❌ Erreur de connexion | `ERROR` | `reseau` | « Erreur de connexion » |

**Source :** `"ConnexionManager"`

### 2. Bot Recherche — `src/gui/widgets/bots/bot_recherche.py`

| Événement | Severity | Category | Title |
|---|---|---|---|
| 🔍 Recherche lancée | `INFO` | `recherche` | « Recherche lancée » |
| ⏹️ Recherche arrêtée | `INFO` | `recherche` | « Recherche arrêtée par l'utilisateur » |
| ❌ Erreur de recherche | `ERROR` | `recherche` | « Erreur de recherche » |

**Source :** `"BotRecherche"`

### 3. SoulseekClient — `src/services/soulseek_client.py`

Événements liés à l'état du client réseau :
- Changements de statut de connexion
- Erreurs de protocole
- Événements asynchrones du client Soulseek

### 4. PlanificateurService — `src/services/planificateur_service.py`

Événements liés à l'exécution des tâches planifiées :
- Début/fin de tâche (`severity="INFO"`)
- Échec de tâche (`severity="ERROR"`)
- Planification annulée

### 5. Autres bots

| Bot | Fichier | Événements typiques |
|---|---|---|
| 📥 Bot Téléchargement | `bot_telechargement.py` | Début, fin, échec de téléchargement |
| 📚 Bot Bibliothèque | `bot_bibliotheque.py` | Scan, mise à jour de la bibliothèque |
| ⚡ Bot Optimiseur | `bot_optimiseur.py` | Début/fin d'optimisation, fichiers analysés |
| 🎯 Bot Wishlist | `bot_wishlist.py` | Match trouvé, recherche wishlist |

---

## 👂 Écouteurs (listeners)

### 1. Bot Surveillance — `src/gui/widgets/bots/bot_surveillance.py`

```python
EventBus().event_emitted.connect(self._on_event_received)
```

- Enregistre tous les événements dans un **tableau de bord** central
- Affiche les événements en temps réel avec leur sévérité (couleur)
- Permet le filtrage par catégorie, sévérité, source
- Accès utilisateur via le bot Surveillance

### 2. MainWindow (Toast notifications) — `src/gui/main_window.py`

```python
def _connect_toast_events(self) -> None:
    EventBus().event_emitted.connect(self._on_toast_event)
```

- Filtre les événements **ERROR** et **WARN** pour affichage toast
- Délégue à `ToastNotification.show_toast(severity, title, message)`

### 3. Logger interne — `src/services/event_bus.py` (ligne 21)

```python
EventBus().event_emitted.connect(mon_handler)
```

- Enregistre les événements dans les logs Python standard
- Utilisé pour le débogage et le suivi serveur

---

## 🍞 ToastNotification

**Fichier :** `src/gui/widgets/toast_notification.py`

Les notifications toast sont des **popups temporaires** qui s'affichent dans l'interface pour les événements importants.

### Niveaux de sévérité

| Severity | Icône | Couleur de fond | Texte |
|---|---|---|---|
| `INFO` | ℹ️ | Bleu | Blanc |
| `WARN` | ⚠️ | Orange (`#f39c12`) | Blanc |
| `ERROR` | ❌ | Rouge (`#e74c3c`) | Blanc |

**Déclenchement :** Seuls les événements de sévérité `ERROR` et `WARN` du `ConnexionManager` (et autres sources) déclenchent une notification toast.

---

## 💾 Structure de la base SQLite

**Fichier :** `data/bot_surveillance.db`

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('INFO', 'WARN', 'ERROR')),
    category TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    message TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    details TEXT DEFAULT NULL,       -- JSON
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_category ON events(category);
CREATE INDEX idx_events_severity ON events(severity);
CREATE INDEX idx_events_source ON events(source);
CREATE INDEX idx_events_created_at ON events(created_at);
```

### Politique de rétention

- **Durée de conservation :** 7 jours
- **Purge automatique :** Toutes les heures via `QTimer` — méthode `_start_purge_timer()`
- **Appel manuel :** `EventBus().purge_old()` pour déclencher la purge immédiatement

---

## 📊 Requêtage et statistiques

### `query(filtres)` — Recherche avancée

Filtres combinés en **AND** :
- `category` — égalité exacte
- `severity` — égalité exacte
- `source` — égalité exacte
- `search` — recherche textuelle dans `title`, `message`, `source`
- `date_from` / `date_to` — plage de dates
- `limit` / `offset` — pagination

### `get_recent(n)` — Derniers événements

```python
events = EventBus().get_recent(10)  # Les 10 plus récents
```

### `get_stats()` — Statistiques agrégées

```python
stats = EventBus().get_stats()
# {
#   "total": 1523,
#   "errors_24h": 3,
#   "warnings_24h": 12,
#   "today": 47,
#   "by_category": {"reseau": 890, "recherche": 420, ...}
# }
```

---

## 🔄 Cycle de vie complet d'un événement

Prenons l'exemple d'une **erreur de recherche** :

```
1. Utilisateur clique sur Rechercher
2. BotRecherche._on_search() → lance search_room()
3. Timeout ou erreur réseau → _on_search_error(msg)
4. EventBus().emit_event(
       severity="ERROR",
       category="recherche",
       title="Erreur de recherche",
       message=f"Erreur lors de la recherche : {msg}",
       source="BotRecherche"
   )
5. EventBus:
   a. Vérifie !self._paused
   b. Crée SurveillanceEvent avec validation
   c. INSERT INTO events (...)
   d. event_emitted.emit(event)
6. BotSurveillance._on_event_received(event):
   → Ajoute l'événement au tableau de bord (temps réel)
7. MainWindow._on_toast_event(event):
   → severity="ERROR" → ToastNotification.show_toast("❌", ...)
8. Logger: écrit dans les logs Python
```

---

## ⚡ Performances et scalabilité

| Aspect | Détail |
|---|---|
| **Écriture SQLite** | Mode WAL — insertion O(1), pas de blocage en lecture |
| **Signal Qt** | Asynchrone — thread-safe, ne bloque pas l'émetteur |
| **Pause** | `EventBus().pause()` pendant les opérations lourdes |
| **Purge** | Automatique toutes les heures — supprime les lignes > 7 jours |
| **Volume type** | Quelques centaines d'événements par session, < 10 000 max |

---

## 🔧 Bonnes pratiques

### Émettre un événement

```python
EventBus().emit_event(
    severity="INFO",
    category="recherche",
    title="Recherche lancée",
    message=f"Recherche de « {query} » démarrée",
    source="BotRecherche",
)
```

### Ne PAS émettre depuis un thread secondaire non-Qt

Le signal Qt doit être émis depuis le thread principal. Pour les threads, passez par `QMetaObject.invokeMethod()` ou utilisez `pyqtSignal` avec le bon contexte de thread.

### Suspendre pendant les tests

```python
EventBus().pause()
# ... opérations de test ...
EventBus().resume()
```

---

> **Voir aussi :** [Architecture de l'application](/technique/architecture-application) · [Mécanismes de threading](/technique/mecanismes-threading) · [FAQ : Événements personnalisés](/faq/evenements-personnalises) · [FAQ : Performances et limitations](/faq/performances-limitations-filtres)
