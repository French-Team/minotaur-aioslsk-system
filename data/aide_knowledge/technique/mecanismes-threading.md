---
title: "Mécanismes de threading — QThread, Worker, asyncio et concurrence"
category: technique
keywords: ["thread", "threading", "asynchrone", "asyncio", "qthread", "worker", "concurrent", "futures", "parallelisme", "parallélisme", "concurrence", "connexion", "scan", "bibliotheque", "ordonnanceur", "performance", "ui", "bloquant", "eventloop", "event_loop"]
---

# Mécanismes de threading — QThread, Worker, asyncio et concurrence

> **Niveau :** Avancé  
> **Temps de lecture :** 15 min  
> **Catégorie :** Architecture technique — Exécution concurrente

---

## 1. Pourquoi plusieurs mécanismes ?

L'application doit gérer **3 contraintes** qui imposent des solutions de threading différentes :

| Contrainte | Problème | Solution |
|------------|----------|----------|
| **UI réactive** 🖥️ | Pas de blocage pendant les opérations longues | `QThread` + `Worker` |
| **Réseau asynchrone** 🌐 | Bibliothèque Soulseek asynchrone (`aioslsk`) | `asyncio` dans un `QThread` dédié |
| **Opérations légères** ⚡ | Tâches courtes mais nombreuses | `concurrent.futures` |

### Carte des technologies

```
┌─────────────────────────────────────────────────────────┐
│              STRATÉGIE DE THREADING                      │
├─────────────────┬───────────────┬───────────────────────┤
│   QThread +     │  _AsyncEvent │  concurrent.futures    │
│   Worker        │  LoopThread   │                       │
├─────────────────┼───────────────┼───────────────────────┤
│ Scan biblio     │ Connexion     │ Callbacks réseau      │
│ Actions planif  │ Soulseek      │ Timeouts              │
│ CRUD lourds     │ (aioslsk)     │                       │
├─────────────────┼───────────────┼───────────────────────┤
│ library_scanner │ connexion_    │ connexion_manager     │
│ bot_ordonnanceur│ manager       │                       │
│ library_db      │               │                       │
└─────────────────┴───────────────┴───────────────────────┘
```

---

## 2. QThread + Worker — Le pattern standard pour l'UI

### Principe

Le pattern **Worker** consiste à déplacer un `QObject` dans un `QThread` pour exécuter une tâche lourde sans bloquer l'interface :

```
Thread principal (UI)           QThread dédié
       │                              │
       │── worker.moveToThread(th)───>│
       │                              │
       │── signal.demarrer() ────────>│  Worker.run()
       │                              │
       │   ←── signal.completed() ────│
       │   ←── signal.progress() ─────│
       │                              │
       │── th.quit() + th.wait() ────>│  Nettoyage
```

### Utilisation dans `library_scanner.py`

```python
class _ScanWorker(QObject):
    progress = Signal(int, int)        # current, total
    completed = Signal(list)
    error = Signal(str)
    finished = Signal()

    def __init__(self, db: LibraryDB):
        super().__init__()
        self._db = db
        self._cancelled = False

    def run(self) -> None:
        """Exécuté dans le QThread — ne pas appeler directement."""
        def _progress_cb(current: int, total: int):
            if self._cancelled:
                return
            self.progress.emit(current, total)  # Thread-safe (signal Qt)

        try:
            resultats = self._db.scan_all(progress_cb=_progress_cb)
            if not self._cancelled:
                self.completed.emit(resultats)
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            self.finished.emit()
```

### Utilisation dans `bot_ordonnanceur.py`

```python
class _PlanificateurWorker(QObject):
    completed = Signal(int, bool, str)  # action_id, succes, message

    def __init__(self, action_id: int, action_type: str, params: dict):
        super().__init__()
        self._action_id = action_id
        self._action_type = action_type
        self._params = params

    def run(self) -> None:
        """Exécute l'action planifiée dans un thread séparé."""
        try:
            # Appel au service métier
            succes = _ACTION_EXECUTOR.executer_action_planificateur(
                self._action_type, self._params
            )
            self.completed.emit(self._action_id, succes, "")
        except Exception as exc:
            self.completed.emit(self._action_id, False, str(exc))
```

### Cycle de vie complet

```python
# Dans le thread principal (UI) :
def _lancer_scan(self):
    self._thread = QThread()
    self._worker = _ScanWorker(db)

    # Déplacer le worker dans le thread
    self._worker.moveToThread(self._thread)

    # Signaux
    self._thread.started.connect(self._worker.run)
    self._worker.completed.connect(self._on_scan_termine)
    self._worker.error.connect(self._on_scan_erreur)
    self._worker.finished.connect(self._thread.quit)
    self._worker.finished.connect(self._worker.deleteLater)
    self._thread.finished.connect(self._thread.deleteLater)

    # Démarrer
    self._thread.start()

def _nettoyer_thread(self):
    """Appelé pour annuler proprement."""
    self._worker._cancelled = True
    self._thread.quit()
    self._thread.wait(3000)  # Timeout 3s
```

### Points clés

| À faire | À éviter |
|---------|----------|
| ✅ `moveToThread()` avant de démarrer le thread | ❌ Hériter de `QThread` et surcharger `run()` (couplage fort) |
| ✅ Utiliser les **signaux Qt** pour la communication | ❌ Accéder aux widgets Qt depuis le worker |
| ✅ Vérifier `_cancelled` périodiquement | ❌ Laisser le thread orphelin (`deleteLater` est crucial) |
| ✅ Connecter `finished` à `quit()` + `deleteLater` | ❌ Timeout trop court (< 1s) pour `wait()` |

---

## 3. `_AsyncEventLoopThread` — asyncio dans un QThread

### Le problème

La bibliothèque Soulseek (`aioslsk`) est **asynchrone** et nécessite une boucle `asyncio`. Mais l'application est en `PySide6` (Qt), qui a sa propre boucle d'événements. Il faut donc faire cohabiter les deux boucles.

### La solution : un QThread dédié pour asyncio

```python
class _AsyncEventLoopThread(QThread):
    """QThread dédié qui fait tourner une boucle asyncio."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready_event = Event()  # threading.Event pour synchronisation

    def run(self) -> None:
        """Point d'entrée du thread — crée et lance la boucle asyncio."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        # Signaler que la boucle est prête
        self._ready_event.set()

        try:
            # Boucle asyncio (bloquante pour ce thread)
            self._loop.run_forever()
        finally:
            self._loop.close()

    def stop(self) -> None:
        """Arrêter la boucle proprement (thread-safe)."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.wait()  # Attendre la fin du thread
```

### Diagramme de flux

```
Thread principal (Qt)           _AsyncEventLoopThread
       │                              │
       │── start() ──────────────────>│  run():
       │                              │    loop = new_event_loop()
       │                              │    set_event_loop(loop)
       │                              │    _ready_event.set()
       │                              │    loop.run_forever()
       │                              │
       │── run_coroutine_threadsafe()>│  Coroutine exécutée sur la boucle
       │   ←── Future ───────────────│
       │                              │
       │── stop() ───────────────────>│  call_soon_threadsafe(loop.stop)
       │                              │  wait()
```

### Utilisation dans `ConnexionManager`

```python
class ConnexionManager(QObject):
    def __init__(self):
        self._async_thread = _AsyncEventLoopThread()
        self._async_thread.start()
        self._async_thread._ready_event.wait()  # Attendre que la boucle soit prête

    async def _connecter_soulseek(self, username: str, password: str):
        """Coroutine exécutée sur la boucle asyncio."""
        client = SoulSeekClient()
        await client.login(username, password)
        return client

    def connecter(self, username: str, password: str) -> Future:
        """Point d'entrée depuis le thread principal (non-bloquant)."""
        return asyncio.run_coroutine_threadsafe(
            self._connecter_soulseek(username, password),
            self._async_thread._loop
        )

    def fermer(self):
        self._async_thread.stop()
```

### Communication synchrone depuis la boucle asyncio

Pour envoyer un événement vers l'UI depuis la boucle asyncio :

```python
# Depuis une coroutine asyncio :
def _on_evenement_reseau(self, categorie: str, titre: str):
    """Thread-safe : utiliser call_soon_threadsafe."""
    # Solution 1 : via le signal Qt (thread-safe)
    self.event_recu.emit(categorie, titre)

    # Solution 2 : via l'EventBus (thread-safe aussi)
    EventBus().emit_event(category=categorie, title=titre)

# Appel depuis la boucle asyncio :
self._loop.call_soon_threadsafe(
    self._on_evenement_reseau, "reseau", "Connecté"
)
```

---

## 4. `concurrent.futures` — Parallélisme léger

### Usage dans l'application

`concurrent.futures.Future` est utilisé dans `connexion_manager.py` pour gérer les résultats des tâches asynchrones :

```python
from concurrent.futures import Future

class ConnexionManager(QObject):
    def executer_tache_reseau(self, coro) -> Future:
        """Exécute une coroutine sur la boucle asyncio et retourne un Future."""
        future = asyncio.run_coroutine_threadsafe(
            coro,
            self._async_thread._loop
        )
        return future  # Non-bloquant : on peut ajouter des callbacks
```

**Quand l'utiliser :**
- Pour des **opérations légères** (timeouts, vérifications rapides)
- En complément d'`asyncio`, pas en remplacement
- Quand on a besoin d'un **résultat futur** sans bloquer le thread appelant

---

## 5. `threading` — Synchronisation entre threads

### `threading.Event`

Utilisé pour la synchronisation entre le thread principal et `_AsyncEventLoopThread` :

```python
class _AsyncEventLoopThread(QThread):
    def __init__(self):
        self._ready_event = Event()

    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ready_event.set()    # ← Thread principal : « la boucle est prête »
        self._loop.run_forever()
```

### Autres usages

| Fichier | Usage | Description |
|---------|-------|-------------|
| `event_bus.py` | Événements thread-safe | `emit_event` peut être appelé depuis n'importe quel thread |
| `planificateur_service.py` | Intervalles de temps | Vérification périodique des actions à déclencher |
| `library_db.py` | Accès concurrent à SQLite | Protection contre les accès simultanés |

---

## 6. `asyncio` — La boucle événementielle réseau

### Utilisation dans `soulseek_client.py`

La bibliothèque `aioslsk` est nativement asynchrone :

```python
from aioslsk.client import SoulSeekClient

class SoulseekService:
    def __init__(self):
        self._client = SoulSeekClient(...)

    async def connecter(self, username: str, password: str):
        """Coroutine : connexion au serveur Soulseek."""
        await self._client.login(username, password)

    async def rechercher(self, requete: str):
        """Coroutine : recherche asynchrone."""
        results = await self._client.search(requete)
        return results
```

### Utilisation dans `error_translator.py`

`error_translator.py` utilise `asyncio` pour exécuter des opérations de traduction ou de traitement de messages de manière non-bloquante. Le pattern est similaire aux autres usages d'`asyncio` dans l'application : les coroutines sont exécutées sur une boucle événementielle et les résultats sont renvoyés au thread principal via des mécanismes thread-safe.

---

## 7. Matrice de choix — Quel mécanisme utiliser ?

| Si vous devez… | Utilisez… | Exemple |
|----------------|-----------|---------|
| **Scanner un dossier** (> 1s) | QThread + Worker | `library_scanner.py` |
| **Exécuter une action planifiée** | QThread + Worker | `bot_ordonnanceur.py` |
| **Lire/écrire dans SQLite** (`library_db`) | QThread (CRUD lourds) | `library_db.py` |
| **Interagir avec Soulseek** | `_AsyncEventLoopThread` + asyncio | `connexion_manager.py` |
| **Lancer une coroutine depuis l'UI** | `asyncio.run_coroutine_threadsafe()` | `connexion_manager.py` |
| **Recevoir un callback réseau** | `concurrent.futures.Future` | `connexion_manager.py` |
| **Synchroniser deux threads** | `threading.Event` | `_AsyncEventLoopThread` |
| **Émettre un événement depuis un thread** | `EventBus().emit_event()` | N'importe quel thread |
| **Notifier l'UI depuis un thread** | Signal Qt + `emit()` | Workers |

---

## 8. Bonnes pratiques et anti-patterns

### Checklist pour un nouveau Worker

```python
# ✅ Architecture correcte
class MonWorker(QObject):
    acheve = Signal(object)

    def __init__(self, data):
        super().__init__()
        self._data = data
        self._annule = False

    def run(self):
        try:
            resultat = self._traiter()
            if not self._annule:
                self.acheve.emit(resultat)
        except Exception as e:
            self.erreur.emit(str(e))
        finally:
            self.fini.emit()

    def annuler(self):
        self._annule = True
```

### Anti-patterns

| Anti-pattern | Pourquoi c'est dangereux |
|--------------|--------------------------|
| ❌ `self.label.setText("...")` depuis un Worker | Crash Qt : l'UI n'est accessible que depuis le thread principal |
| ❌ Hériter de `QThread` pour tout | Rigide, difficile à tester, pas réutilisable |
| ❌ `thread.join()` dans l'UI | Bloque l'interface pendant l'attente |
| ❌ Créer un `QTimer` dans un `QThread` | Instable, comportement indéfini |
| ❌ Oublier `moveToThread()` | Le Worker reste sur le thread principal, aucun bénéfice |
| ❌ Pas de `deleteLater` | Fuite mémoire : le Worker et le thread ne sont jamais nettoyés |

### Communication inter-threads sécurisée

```
✅ OK (thread-safe) :
   - Signal Qt : worker.acheve.connect(recepteur)
   - EventBus : EventBus().emit_event(...)
   - call_soon_threadsafe (asyncio)
   - Queue.Queue / queue.Queue

❌ PAS OK (thread-unsafe) :
   - Accès direct à un widget Qt
   - Variable partagée sans Lock
   - Appel de méthode sur un objet Qt non thread-safe
```

---

## 9. Synthèse : flux threading dans l'application

```
startup
   │
   ▼
Thread principal (Qt event loop)
   │
   ├── ConnexionManager
   │   └── _AsyncEventLoopThread (QThread)
   │       └── asyncio loop
   │           ├── SoulSeekClient.login()
   │           ├── SoulSeekClient.search()
   │           ├── call_soon_threadsafe() → signaux Qt
   │           └── run_coroutine_threadsafe() → Future
   │
   ├── LibraryScanner
   │   └── QThread + _ScanWorker
   │       └── library_db.scan_all()
   │           └── progress → signal Qt
   │
   ├── PlanificateurWorker
   │   └── QThread + Worker temporaire
   │       └── ordonnanceur_service.executer()
   │           └── completed → signal Qt
   │
   └── EventBus
       └── thread-safe (emit_event depuis n'importe où)
           └── event_emitted.emit() → thread principal
```

---

## Voir aussi

- [Architecture événementielle →](/technique/architecture-evenementielle)
- [Guide technique de l'EventBus →](/technique/guide-eventbus)
- [Exporter les données de surveillance →](/tutoriels/exporter-donnees-surveillance)
- [Règles conditionnelles →](/tutoriels/regles-conditionnelles-planificateur)
- [FAQ base de données des événements →](/faq/bases-donnees-evenements)
