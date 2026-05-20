---
title: "Mécanismes de threading et d'async dans le bot Recherche"
category: "technique"
icon: "🧵"
keywords:
  - threading recherche
  - async soulseek
  - QThread asyncio
  - thread asynchrone
  - signal qt thread
  - thread recherche soulseek
  - timer recherche
  - mecanisme thread
  - mécanisme thread
  - boucle asyncio
  - signal inter thread
  - signal inter-thread
  - QTimer singleShot
  - deleteLater
  - blockSignals
  - run_coroutine_threadsafe
  - thread
  - async
  - timer
  - signal inter thread
  - deleteLater
  - blockSignals
  - coroutine thread safe
  - coroutine thread sûr
  - file soulseek async
  - fichier soulseek asynchrone
  - evenement asynchrone
  - événement asynchrone
---

# 🧵 Mécanismes de threading et d'async dans le bot Recherche

Le bot Recherche utilise une **architecture hybride** combinant Qt (pour l'interface graphique) et asyncio (pour les opérations réseau). Cette section détaille comment ces mécanismes sont orchestrés pour garantir une interface réactive malgré des opérations réseau potentiellement longues.

---

## 🏗️ Architecture générale des threads

```
┌──────────────────────────────────────────────────────────────────────┐
│                   Thread Principal (UI / Qt)                          │
│                                                                       │
│  QApplication.exec() boucle d'événements                              │
│                                                                      │
│  ┌─────────────────────────────────────────────────────┐             │
│  │ BotRecherche (QWidget)                              │             │
│  │  - Signaux/Slots UI (clicked, toggled, valueChanged) │             │
│  │  - QTimer _search_timer (30s singleShot)             │             │
│  │  - Mise à jour du tableau, bannières, statuts       │             │
│  │  - deleteLater() pour nettoyage sécurisé            │             │
│  │  - blockSignals() pour synchronisation contrôlée    │             │
│  └─────────────────────────────────────────────────────┘             │
│                                                                       │
│  ConnexionManager signaux (auto-queued cross-thread)                  │
└──────────────────────────┬───────────────────────────────────────────┘
                           │
          Qt::AutoConnection → Qt::QueuedConnection (cross-thread)
                           │
┌──────────────────────────┴───────────────────────────────────────────┐
│                Thread Asyncio (_AsyncEventLoopThread)                  │
│                                                                       │
│  asyncio.new_event_loop()                                             │
│  loop.run_forever()                                                   │
│  asyncio.run_coroutine_threadsafe() pour planifier les coroutines     │
│                                                                       │
│  ┌─────────────────────────────────────────────────────┐             │
│  │ ConnexionManager — Coroutines (async def)          │             │
│  │                                                     │             │
│  │  _do_login()          await self._service.connect() │             │
│  │  _do_search()         await client.searches.search()│             │
│  │  _do_search_user()    ciblé sur un utilisateur      │             │
│  │  _do_search_room()    ciblé sur un salon            │             │
│  │  _do_disconnect()     await self._service.stop()    │             │
│  │                                                     │             │
│  │  ➡ Émettent des signaux Qt vers le thread UI       │             │
│  └─────────────────────────────────────────────────────┘             │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

### Caractéristiques

| Aspect | Thread UI | Thread Asyncio |
|---|---|---|
| **Boucle** | `QApplication.exec()` | `asyncio.run_forever()` |
| **Rôle** | Affichage, réactivité, interactions | Opérations réseau Soulseek |
| **Blocage** | Jamais bloqué (IO déportée) | Peut attendre des IO |
| **Qt Signals** | Émet et reçoit | Peut émettre (queue automatique) |

---

## 🧵 _AsyncEventLoopThread — Le pont entre Qt et asyncio

**Fichier :** `src/services/connexion_manager.py` — ligne 167

```python
class _AsyncEventLoopThread(QThread):
    """Thread Qt qui fait tourner une boucle asyncio."""

    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ready_event.set()
        try:
            self._loop.run_forever()
        finally:
            self._loop.close()
```

### Cycle de vie

1. **Création :** `self._async_thread = _AsyncEventLoopThread(self)` dans `ConnexionManager.__init__`
2. **Démarrage :** `self._async_thread.start()` — lance `run()` dans un nouveau thread
3. **Attente :** `self._async_thread.wait_ready()` — bloque jusqu'à ce que la boucle soit prête (timeout 2s)
4. **Planification :** `self._async_thread.run_coro(coro)` → `asyncio.run_coroutine_threadsafe(coro, self._loop)`
5. **Arrêt :** `self._async_thread.stop()` → `call_soon_threadsafe(self._loop.stop)` + `self.wait()`

### `run_coro()` — Planifier une coroutine

```python
def run_coro(self, coro) -> Future:
    if not self._loop:
        raise RuntimeError("La boucle asyncio n'est pas encore prête")
    return asyncio.run_coroutine_threadsafe(coro, self._loop)
```

Retourne un `concurrent.futures.Future` — l'appelant peut :
- Attendre le résultat avec `future.result(timeout=...)`
- Vérifier la complétion avec `future.done()`
- Ajouter un callback avec `future.add_done_callback()`

---

## 🔄 ConnexionManager — Pont entre les threads

**Fichier :** `src/services/connexion_manager.py` — ligne 213

### Signaux (thread-safe par Qt)

```python
class ConnexionManager(QObject):
    connected = Signal(str)
    disconnected = Signal()
    error_occurred = Signal(str)
    generating = Signal(bool)
    status_changed = Signal(str)
    search_result_received = Signal(object)
```

### Flux d'exécution d'une recherche

```
BotRecherche (UI Thread)         ConnexionManager              Thread Asyncio
     │                                │                              │
     │  _on_search()                  │                              │
     │───────search(query)───────────>│                              │
     │                                │  run_coro(_do_search)        │
     │                                │───────────────coro──────────>│
     │                                │                              │
     │                                │         await client.search()
     │                                │              │               │
     │  <──── résultats via signal ───│──────────────┘               │
     │  _on_search_result(event)      │  emit(search_result_received)│
     │                                │                              │
     │  Traitement batch + UI         │                              │
```

### Comment c'est thread-safe

Les signaux Qt utilisent `Qt::AutoConnection` par défaut :
- **Même thread** → `DirectConnection` (synchrone, appel direct du slot)
- **Threads différents** → `QueuedConnection` (asynchrone, le slot est placé dans la file d'événements du thread destinataire)

Puisque `ConnexionManager` est un `QObject` créé dans le thread UI, mais que ses coroutines s'exécutent dans le thread asyncio, **tous les signaux émis depuis le thread asyncio sont automatiquement « queued »** vers le thread UI. Le slot correspondant (ex: `_on_search_result`) s'exécute donc toujours dans le thread UI, au prochain cycle d'événements.

---

## ⏱️ QTimer — Le timer de recherche

**Fichier :** `src/gui/widgets/bots/bot_recherche.py` — ligne 1319

```python
# Création
self._search_timer = QTimer(self)

# Configuration : un seul déclenchement
self._search_timer.setSingleShot(True)

# Connexion du timeout
self._search_timer.timeout.connect(self._on_search_timeout)

# Démarrage : 30 secondes
self._search_timer.start(30000)
```

### Cycle de vie du timer

1. **Démarrage :** Dans `_on_search()` — `self._search_timer.start(30000)`
2. **Pendant :** Les résultats arrivent via `_on_search_result()` — le timer continue
3. **Timeout :** `_on_search_timeout()` est appelée après 30s → arrête la recherche, affiche le statut
4. **Arrêt manuel :** `_on_stop()` → `self._search_timer.stop()`
5. **Nouvelle recherche :** Le timer est redémarré dans `_on_search()`

### Pourquoi `singleShot` ?

- Une recherche a une durée de vie limitée à **30 secondes**
- Pas besoin de timer répétitif — le timeout marque la fin naturelle
- Si l'utilisateur relance une recherche, le timer est simplement redémarré

---

## 🔇 blockSignals — Éviter les boucles de signaux

**Fichier :** `src/gui/widgets/bots/bot_recherche.py` — lignes 389-396

```python
def _on_bitrate_slider(self, value: int) -> None:
    self._bitrate_spin.blockSignals(True)     # ← Bloquer
    self._bitrate_spin.setValue(value)         # Mise à jour programmatique
    self._bitrate_spin.blockSignals(False)    # ← Réactiver

def _on_bitrate_spin(self, value: int) -> None:
    self._bitrate_slider.blockSignals(True)   # ← Bloquer
    self._bitrate_slider.setValue(value)       # Mise à jour programmatique
    self._bitrate_slider.blockSignals(False)  # ← Réactiver
```

### Problème résolu

Sans `blockSignals`, la synchronisation slider ↔ spinbox créerait une **boucle infinie** :

```
Utilisateur bouge le slider
  → valueChanged → _on_bitrate_slider
    → spin.setValue(valeur)
      → spin.valueChanged → _on_bitrate_spin
        → slider.setValue(valeur)
          → slider.valueChanged → _on_bitrate_slider    ← boucle !
            → ...
```

Avec `blockSignals`, la mise à jour programmatique n'émet pas de signal, brisant la boucle.

---

## 🗑️ deleteLater — Nettoyage sécurisé des widgets

**Fichier :** `src/gui/widgets/bots/bot_recherche.py` — lignes 1891 (suggestions)

```python
# Dans _rebuild_suggestions()
for widget in self._suggestions_widgets:
    widget.deleteLater()      ← Reporte la suppression
self._suggestions_widgets.clear()
```

### Pourquoi `deleteLater()` et pas `delete` ou `remove` ?

- **Sécurité :** Si un widget est actuellement dans une chaîne de signaux/slots, le supprimer immédiatement pourrait causer un crash
- **Report :** `deleteLater()` planifie la suppression pour le **prochain cycle de la boucle d'événements Qt**, après que tous les signaux en cours aient été traités
- **Pattern :** Utilisé systématiquement pour les widgets créés dynamiquement (suggestions, popup d'historique)

---

## 📞 exec() — Dialogues bloquants

**Fichier :** `src/gui/widgets/bots/bot_recherche.py`

```python
# Filtres avancés — modal
filtres = FiltresRechercheModal(self._filter_state, self)
if filtres.exec() == QDialog.DialogCode.Accepted:
    self._filter_state = filtres.get_state()

# Menu contextuel
menu = QMenu(self)
menu.exec(QCursor.pos())   ← Boucle d'événements locale

# Historique
popup = HistoryPopup(self._search_history, self)
popup.exec()               ← Boucle d'événements locale
```

`exec()` lance une **boucle d'événements locale** qui bloque l'exécution de la fonction appelante sans bloquer l'UI — les événements Qt (redimensionnement, clics, etc.) continuent d'être traités.

---

## ⚡ Signaux/Slots — Tableau complet

### Signaux internes de BotRecherche

| Signal | Émetteur | Slot connecté | Type |
|---|---|---|---|
| `clear_requested = Signal()` | HistoryPopup | `_on_clear` | Local (même thread) |
| `entries_changed = Signal()` | HistoryPopup | `_rebuild_suggestions` | Local |
| `page_changed = Signal(str)` | BotRecherche | MainWindow | Local |

### Signaux du ConnexionManager (cross-thread)

| Signal | Émetteur (thread) | Slot (thread UI) | Type de connexion |
|---|---|---|---|
| `connected.emit(username)` | Asyncio | `_on_connected` | `QueuedConnection` (auto) |
| `disconnected.emit()` | Asyncio | `_on_disconnected` | `QueuedConnection` (auto) |
| `error_occurred.emit(msg)` | Asyncio | `_on_search_error` | `QueuedConnection` (auto) |
| `search_result_received.emit(event)` | Asyncio | `_on_search_result` | `QueuedConnection` (auto) |
| `status_changed.emit(msg)` | Asyncio | (EventBus) | `QueuedConnection` (auto) |

### Signaux UI (même thread)

| Signal | Émetteur | Slot |
|---|---|---|
| `_search_btn.clicked` | QPushButton | `_on_search` |
| `_search_input.returnPressed` | QLineEdit | `_on_search` |
| `_stop_btn.clicked` | QPushButton | `_on_stop` |
| `_audio_filter_btn.toggled` | QPushButton | `_on_audio_filter_toggled` |
| `_filtres_btn.clicked` | QPushButton | `_open_filtres_modal` |
| `_table.customContextMenuRequested` | QTableWidget | `_on_context_menu` |
| `_search_timer.timeout` | QTimer | `_on_search_timeout` |
| `_bitrate_slider.valueChanged` | QSlider | `_on_bitrate_slider` |

---

## 📊 Flux asynchrone complet d'une recherche

Voici le cycle de vie complet d'une recherche, en suivant l'interaction entre threads :

```
1. UI Thread: Utilisateur tape "requête" + appuie sur Entrée
   → _on_search()
   → stop timer si actif + _reset_search_state()
   → _clear_results() (setRowCount(0))
   → _search_btn.hide() + _stop_btn.show()
   → _search_timer.start(30000)

2. UI Thread: ConnexionManager.search(query)
   → self._async_thread.run_coro(self._do_search(query))
   → asyncio.run_coroutine_threadsafe(coro, loop)
   → Retourne immédiatement (non-bloquant)

3. Thread Asyncio: _do_search(query)
   → await client.searches.search(query)
   → Suspendu en attendant le réseau

4. Thread Asyncio: Résultat reçu du réseau
   → signal search_result_received.emit(event)
   → Qt::AutoConnection détecte thread différent
   → Convertit en Qt::QueuedConnection
   → Place le slot dans la file du thread UI

5. UI Thread: Prochain cycle d'événements
   → _on_search_result(event) est appelé
   → Batch insert dans le tableau
   → Vérification MAX_RESULTS
   → setSortingEnabled(True) si fin du batch

6. UI Thread: 30 secondes écoulées
   → _search_timer.timeout → _on_search_timeout()
   → stop_btn.hide() + search_btn.show()
   → Status: "⚠️ 200 résultats max..."
```

---

## 🔧 Bonnes pratiques

### 1. Ne pas bloquer le thread UI

```python
# ❌ Mauvais — bloquerait l'interface
result = requests.get("http://api.soulseek.com/...")  # IO bloquante

# ✅ Bon — déléguer au thread asyncio
self._async_thread.run_coro(self._do_network_call())
```

### 2. Émettre des signaux Qt depuis n'importe quel thread

```python
# ✅ Sûr — Qt.AutoConnection gère le cross-thread
self.connected.emit(username)   # Depuis le thread asyncio
```

### 3. Utiliser deleteLater() pour les widgets dynamiques

```python
# ✅ Sûr — suppression au prochain cycle
widget.deleteLater()

# ❌ Dangereux — peut crasher si dans une chaîne de signaux
widget.delete()
```

### 4. Synchroniser les widgets liés avec blockSignals

```python
# ✅ Sûr — évite les boucles de signaux
control.blockSignals(True)
sibling.setValue(new_value)
control.blockSignals(False)
```

### 5. Utiliser singleShot pour les timeouts uniques

```python
# ✅ Approprié — la recherche a une durée de vie unique
timer.setSingleShot(True)
timer.start(30000)

# ❌ Inapproprié — un timer persistant serait gaspillé
# timer.setInterval(30000)  # Se déclencherait toutes les 30s
```

---

> **Voir aussi :** [Architecture de l'application](/technique/architecture-application) · [Système d'événements (EventBus)](/technique/event-bus-surveillance) · [Cache et performance](/technique/cache-performance-recherche) · [FAQ : Performances et limitations](/faq/performances-limitations-filtres)
