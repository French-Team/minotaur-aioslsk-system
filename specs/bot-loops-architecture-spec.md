# Architecture des Boucles de Bots — Spécification

> **Statut :** ✅ Implémentation complète — tests en place
> **Dernière mise à jour :** 2026-05-20
> **Contexte :** Architecture indépendante pour chaque bot, orchestrée par le BotAccueil qui analyse la demande utilisateur et déclenche les services appropriés.

---

## 1. 🎯 Vision d'ensemble

### 1.1 Principe fondamental

La boucle principale de l'application ne fait **que** :
1. Afficher la page de connexion
2. Gérer l'authentification au serveur Soulseek
3. Afficher l'Accueil et attendre les instructions de l'utilisateur

**Aucune boucle n'est lancée automatiquement au démarrage.**

Chaque **boucle** est indépendante (QTimer, thread asyncio, QThread ou events passifs).
Le **BotAccueil** est le hub central : il analyse la demande utilisateur, active l'**interrupteur** des boucles concernées, et informe l'utilisateur via des messages et des toasts.

> **Interrupteur :** chaque boucle possède un interrupteur ON/OFF indépendant.
> L'Accueil peut activer l'interrupteur pour démarrer une boucle en arrière-plan.
> Le WorkflowInspector (DevTool) permet de voir l'état des interrupteurs.

**Même la BoucleRooms n'est pas automatique.** C'est le BotAccueil qui active son interrupteur 5 secondes après la connexion,
en informant l'utilisateur : *"Je lance la mise à jour des salons et je prépare la liste des clients actifs…"*

### 1.2 Flux utilisateur typique

```
┌──────────────────────────────────────────────────────────────┐
│ 1. User démarre l'application                                │
│    → Page de connexion affichée                              │
│                                                              │
│ 2. User se connecte                                          │
│    → Accueil affiché — boucle principale en attente          │
│    → Accueil active l'interrupteur BoucleRooms (5s après)   │
│    → Message : "Je lance la mise à jour des salons…"        │
│                                                              │
│ 3. User tape : "Cherche des fichiers Jazz"                   │
│    → BotAccueil analyse la demande                           │
│    → Accueil active l'interrupteur BoucleRecherche           │
│    → Message : "🔍 J'active la boucle Recherche pour toi…"   │
│    → Toast : "✅ Boucle Recherche activée"                   │
│    → Accueil navigue vers le bot Recherche                   │
│                                                              │
│ 4. BoucleRecherche tourne en arrière-plan                    │
│    → Même si l'utilisateur change de page                    │
│                                                              │
│ 5. User va voir le WorkflowInspector (DevTool)               │
│    → Interrupteurs ON/OFF visibles                           │
│    → Permet de basculer manuellement pour debug              │
└──────────────────────────────────────────────────────────────┘
```

### 1.3 Architecture en couches

```
┌──────────────────────────────────────────────────────────┐
│                   BOUCLE PRINCIPALE                       │
│                 (Qt Event Loop main)                      │
│  Login → Attente → BotAccueil (hub) → Navigation         │
└──────────────┬───────────────────────────────────────────┘
               │
        Active l'interrupteur
               │
        ┌──────┴──────┬──────────┬──────────────┐
        ▼             ▼          ▼              ▼
┌─────────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐
│ BoucleRooms │ │ Boucle   │ │ Boucle   │ │ Boucle     │
│ (QTimer 30s)│ │ Recherche│ │ Biblio-  │ │ ...        │
│             │ │ (asyncio)│ │ thèque   │ │            │
│ *pas de     │ │          │ │(QThread) │ │            │
│  widget*    │ │          │ │          │ │            │
└──────┬──────┘ └─────┬────┘ └─────┬────┘ └──────┬─────┘
       │              │            │             │
       │        ┌─────┴─────┐      │             │
       │        │           │      │             │
       ▼        ▼           ▼      ▼             ▼
┌──────────────────────────────────────────────────────┐
│              ConnexionManager                        │
│          (thread asyncio partagé)                    │
│            client aioslsk unique                     │
└──────────────────────────────────────────────────────┘
```

> **Architecture :**
> - Les **boucles** sont des processus arrière-plan, certaines ont un widget associé (Recherche, Téléchargement…),
>   d'autres n'ont **pas de widget** du tout (Rooms).
> - Chaque boucle a un **interrupteur ON/OFF** que l'Accueil active.
> - Le **ConnexionManager** est la ressource partagée (thread asyncio, client aioslsk unique).
> - Le **WorkflowInspector** (DevTool) affiche l'état de tous les interrupteurs.

---

## 2. 🧱 Interface standard — Interrupteur de boucle

### 2.1 Les trois types d'entités

| Concept | Nature | Widget UI ? | Exemple |
|---------|--------|:-----------:|---------|
| **Bot** | Widget visible dans l'application avec **sa propre boucle** | ✅ Oui | BotRecherche, BotTelechargement, BotSurveillance |
| **Boucle pure** | Processus arrière-plan **sans widget** — juste un interrupteur | ❌ Non | BoucleRooms (pas de page, pas de UI) |
| **Bot statique** | Widget visible mais **sans boucle** (consultation, action unique) | ✅ Oui | BotAide, BotOrdonnanceur, BotAccueil |

**Règles :**
- Chaque boucle (associée à un bot ou pure) a un **interrupteur ON/OFF**
- L'interrupteur est accessible via `demarrer()` / `arreter()`
- Une **boucle pure** (Rooms) n'a pas de widget — elle tourne en arrière-plan et alimente d'autres services
- Un **bot statique** n'a pas d'interrupteur (pas de `demarrer()/arreter()`)

### 2.2 Contrat `LoopInterrupteur`

Toute boucle implémente cet interrupteur :

```python
class BoucleXxx(QObject):
    """Boucle arrière-plan avec interrupteur ON/OFF."""

    def demarrer(self) -> None:
        """Active l'interrupteur → lance la boucle.

        - Si déjà actif : ignore (log debug)
        - Lance le thread/QTimer/events
        - Log "BoucleXxx démarrée"
        """
        ...

    def arreter(self) -> None:
        """Désactive l'interrupteur → suspend la boucle.

        - Si déjà inactif : ignore (log debug)
        - Met en pause (pas de destruction)
        - Conserve les données accumulées
        - Log "BoucleXxx arrêtée"
        """
        ...

    @property
    def est_actif(self) -> bool:
        """Retourne l'état de l'interrupteur."""
        return self._actif  # ou self._timer.isActive()
```

**Cas particuliers :**
- **Bot avec boucle** (BotRecherche) : le bot contient l'interrupteur et le widget
- **Boucle pure** (BoucleRooms) : classe `QObject` seule, pas de `QFrame`
- **Bot statique** (BotAide) : pas d'interrupteur du tout

### 2.3 Règles de l'interrupteur

- **`demarrer()`** : si déjà actif → ignoré. Si connexion réseau nécessaire → vérifier `ConnexionManager.is_connected`
- **`arreter()`** : si déjà inactif → ignoré. Suspension seulement (données conservées)
- **Double activation** : ignorée silencieusement
- **Arrêt sans activation** : ignoré silencieusement

### 2.4 Principe de suspension

L'arrêt est une **suspension** — pas une destruction :
- Les timers sont stoppés mais pas supprimés
- Les données accumulées restent en mémoire
- `demarrer()` reprend là où ça s'est arrêté

---

## 3. 🔄 Types de boucles par bot

| Boucle | Portée par | Type de boucle | Interrupteur activé par | Ressource |
|--------|-----------|---------------|------------------------|-----------|
| **BoucleRooms** | `BoucleRooms(QObject)` — **aucun widget** | `QTimer` (30s) | Accueil (5s après connexion) | ConnexionManager |
| **BoucleClientsActifs** | `BotClientsActifs(QFrame)` | Events aioslsk passifs | Accueil sur demande | ConnexionManager |
| **BoucleRecherche** | `BotRecherche(QFrame)` | Thread asyncio (via CM) | Accueil sur demande | ConnexionManager |
| **BoucleTelechargement** | `BotTelechargement(QFrame)` | Thread asyncio (via CM) | Accueil sur demande | ConnexionManager |
| **BoucleSurveillance** | `BotSurveillance(QFrame)` | `QTimer` (configurable) | Accueil sur demande | ConnexionManager + EventBus |
| **BoucleBibliotheque** | `BotBibliotheque(QFrame)` | `QThread` (scan disque) | Accueil sur demande | Disque |
| **BoucleWishlist** | `BotWishlist(QFrame)` | `QTimer` (configurable) | Accueil sur demande | ConnexionManager |
| **BouclePlanificateur** | `BotPlanificateur(QFrame)` | `QTimer` (1 min) | Accueil sur demande | Base SQLite |
| **BoucleOptimiseur** | `BotOptimiseur(QFrame)` | `QTimer` (configurable) | Accueil sur demande | Disque + ConnexionManager |
| **BotOrdonnanceur** | *Pas de boucle* (action unique manuelle) | N/A | N/A | Disque |
| **BotAide** | *Pas de boucle* (consultation statique) | N/A | N/A | SQLite |
| **BotAssistant** | *Pas de boucle* (toujours actif, passif) | N/A | N/A | ConnexionManager + EventBus |
| **BotAccueil** | *Pas de boucle* (hub central, orchestre les autres) | N/A | N/A | N/A |

> **Règle :** Les boucles pures (Rooms) implémentent `demarrer()/arreter()` sur un `QObject`.
> Les boucles portées par un bot implémentent `demarrer()/arreter()` sur le `QFrame` du bot.
> Les entités sans boucle (Aide, Accueil, Ordonnanceur) n'ont pas d'interrupteur → ⚪ UNKNOWN dans le WorkflowInspector.

### 3.1 Détail par type de boucle

#### QTimer (périodique)
```python
# Pattern standard pour les boucles QTimer
class BotXxx(QFrame):
    """Bot avec boucle QTimer périodique."""

    def __init__(self):
        self._timer = QTimer(self)
        self._timer.setInterval(30_000)  # 30s par défaut
        self._timer.timeout.connect(self._execute_cycle)

    def demarrer(self):
        if self._actif:
            return
        self._actif = True
        self._execute_cycle()  # premier appel immédiat
        self._timer.start()

    def arreter(self):
        if not self._actif:
            return
        self._actif = False
        self._timer.stop()

    def _execute_cycle(self) -> None:
        """Un cycle de la boucle."""
        ...
```

#### Thread asyncio (via ConnexionManager)
```python
# Pattern pour les boucles qui utilisent le ConnexionManager
class BotXxx(QFrame):
    def demarrer(self):
        if self._actif:
            return
        self._actif = True
        # Utilise le thread asyncio partagé du ConnexionManager
        self._connexion_manager.schedule_async(self._run_async)

    def arreter(self):
        if not self._actif:
            return
        self._actif = False
        # Annule les opérations en cours
        self._connexion_manager.schedule_async(self._cancel_async)

    async def _run_async(self):
        # Code asyncio utilisant le client aioslsk partagé
        ...
```

#### Events passifs
```python
# Pattern pour les boucles event-driven
class BoucleXxx(QObject):
    def demarrer(self):
        if self._actif:
            return
        self._actif = True
        self._client = self._connexion_manager.client
        if self._client:
            self._client.events.register(SomeEvent, self._handler)

    def arreter(self):
        if not self._actif:
            return
        self._actif = False
        if self._client:
            self._client.events.unregister(SomeEvent, self._handler)
```

---

## 4. 🧠 Registre des boucles — KNOWLEDGE étendu

### 4.1 Structure

Le dictionnaire `KNOWLEDGE` dans `bot_accueil_knowledge.py` est enrichi avec des informations de cycle de vie.
Chaque entrée associe un mot-clé (demande utilisateur) à une boucle à activer :

```python
KNOWLEDGE: dict[str, BotKnowledge] = {
    "recherche": {
        "keywords": ["chercher", "recherche", "trouver", "fichier", "musique"],
        "icon": "🔍",
        "response": "Je lance le bot Recherche pour toi…",
        "loop_type": "asyncio",        # type de boucle
        "service": "BotRecherche",      # nom du bot cible
        "start_delay": 0,               # délai avant démarrage (ms)
        "auto_navigate": True,          # naviguer vers la page après démarrage ?
        "actions": [
            {"type": "start_loop", "bot": "Recherche"},
            {"type": "navigate", "bot": "Recherche", "icon": "🔍"},
        ],
        "suggestions": [...],
    },
    "telechargement": {
        "keywords": ["télécharger", "download", "recevoir", "fichier"],
        "icon": "📥",
        "response": "J'active le bot Téléchargement…",
        "loop_type": "asyncio",
        "service": "BotTelechargement",
        "start_delay": 0,
        "auto_navigate": True,
        "actions": [
            {"type": "start_loop", "bot": "Téléchargement"},
            {"type": "navigate", "bot": "Téléchargement", "icon": "📥"},
        ],
        "suggestions": [...],
    },
    "clients_actifs": {
        "keywords": ["client", "actif", "connecté", "membre", "utilisateur"],
        "icon": "👤",
        "response": "Je prépare la liste des clients actifs…",
        "loop_type": "events",           # event-driven passif
        "service": "BotClientsActifs",
        "start_delay": 0,
        "auto_navigate": True,
        "actions": [
            {"type": "start_loop", "bot": "Clients Actifs"},
            {"type": "navigate", "bot": "Clients Actifs", "icon": "👤"},
        ],
        "suggestions": [...],
    },
}
```

### 4.2 Types d'actions : `start_loop`, `stop_loop` et `start_loop_and_navigate`

```python
# Dans BotAccueil._execute_actions()
if atype == "start_loop":
    bot_name = action.get("bot", "")
    start_delay = action.get("delay", 0)
    if start_delay > 0:
        QTimer.singleShot(start_delay, lambda: self._do_start_loop(bot_name))
    else:
        self._do_start_loop(bot_name)
    QTimer.singleShot(100, lambda: _run_step(index + 1))

elif atype == "stop_loop":
    bot_name = action.get("bot", "")
    if bot_name:
        self._stop_loop(bot_name)
    QTimer.singleShot(100, lambda: _run_step(index + 1))

elif atype == "start_loop_and_navigate":
    bot_name = action.get("bot", "")
    icon_nav = action.get("icon", "➡️")
    if bot_name:
        # _do_start_loop() emits loop_started (→ toast) et gère
        # l'échec en interne (add_message ⚠️)
        self._do_start_loop(bot_name)
        self.navigate_to(bot_name, icon_nav)
    QTimer.singleShot(100, lambda: _run_step(index + 1))
```

> **Note :** `start_loop` supporte un paramètre `delay` (ms) pour différer le démarrage. `stop_loop` n'a pas de `delay` pour l'instant (asymétrie).

### 4.3 Méthodes de contrôle des boucles

```python
# Signaux
loop_started = Signal(str)  # émis quand une boucle est démarrée avec succès

def set_loop_starter(self, starter: Callable[[str], bool]) -> None:
    """Injecte la fonction qui démarre la boucle d'un bot par son nom.
    
    Appelée par CenterZone au moment de la connexion.
    starter(bot_name) → True si démarré, False sinon.
    """
    self._loop_starter = starter

def set_loop_stopper(self, stopper: Callable[[str], bool]) -> None:
    """Injecte la fonction qui arrête la boucle d'un bot par son nom.
    
    Appelée par CenterZone au moment de la connexion.
    stopper(bot_name) → True si arrêté, False sinon.
    """
    self._loop_stopper = stopper

def _start_loop(self, bot_name: str) -> bool:
    """Démarre la boucle d'un bot via le loop_starter injecté.
    
    Retourne True si la boucle a été démarrée avec succès.
    """
    if self._loop_starter is None:
        logger.warning("BotAccueil: loop_starter non configuré")
        return False
    return self._loop_starter(bot_name)

def _do_start_loop(self, bot_name: str) -> bool:
    """Démarre une boucle avec feedback utilisateur (signal + message).
    
    Émet loop_started(success) et affiche un message ⚠️ sur échec.
    """
    success = self._start_loop(bot_name)
    if success:
        self.loop_started.emit(bot_name)  # → toast dans main_window
    else:
        self.add_message("⚠️", f"Impossible de démarrer la boucle <b>{bot_name}</b>", None)
    return success

def _stop_loop(self, bot_name: str) -> bool:
    """Arrête la boucle d'un bot via le loop_stopper injecté.
    
    Retourne True si la boucle a été arrêtée avec succès.
    """
    if self._loop_stopper is None:
        logger.warning("BotAccueil: loop_stopper non configuré")
        return False
    return self._loop_stopper(bot_name)
```

**Signal `loop_started`** : émis par `_do_start_loop()` sur succès. Consommé par `main_window._connect_loop_started_signal()` qui affiche un toast.

> Note : on utilise `start_loop` / `stop_loop` (pas `start_bot` / `stop_bot`) pour insister sur le fait qu'on contrôle une **boucle**, pas un widget UI. Le bot (widget) existe déjà.

---

## 5. 🏠 BoucleRooms — Première boucle concrète (boucle pure, pas de widget)

### 5.1 Objectif

**BoucleRooms** est la **première boucle à implémenter** comme preuve de concept.
C'est une **boucle pure** : pas de widget UI, pas de page visible.
Elle tourne en arrière-plan et alimente le `ClientsActifsService`.

Son interrupteur est activé par le BotAccueil **5 secondes** après la connexion.

Objectifs :
1. Récupère la liste des salons publics via le client aioslsk
2. Rejoint les 5 premiers salons (pour avoir le droit de voir les membres)
3. Fournit la liste des membres comme **source de données** pour le bot ClientsActifs
4. Met à jour périodiquement (QTimer 30s)

### 5.2 Flux

```
Connexion réussie → Accueil affiché
    ↓
Accueil détecte la connexion
    ↓ attend 5s
Accueil : "Je lance la mise à jour des salons et je prépare la liste des clients actifs…"
    ↓ active l'interrupteur
BoucleRooms démarrée (QTimer 30s)
    ↓
1ᵉʳ cycle : récupère la liste des rooms publiques + rejoint les 5 premières
    ↓
Récupère la liste des membres pour chaque room rejointe
    ↓
Transmet la liste au ClientsActifsService
        ↓
        Compteur clients actifs mis à jour
```

### 5.3 Implémentation de la boucle (QObject, pas de QFrame)

```python
class BoucleRooms(QObject):
    """Boucle pure — pas de widget UI.
    
    Récupère périodiquement les salons publics Soulseek
    et alimente ClientsActifsService en membres actifs.
    """

    # Signal de sortie vers ClientsActifsService
    membres_actualises = Signal(list)  # list[dict] — membres actifs

    def __init__(self, connexion_manager, parent=None):
        super().__init__(parent)
        self._cm = connexion_manager
        self._actif = False
        self._timer = QTimer(self)
        self._timer.setInterval(30_000)  # 30s
        self._timer.timeout.connect(self._executer_cycle)
        self._rooms_actuelles: list[dict] = []
        self._membres_actifs: list[dict] = []

    # ── Interrupteur ──

    def demarrer(self) -> None:
        """Active l'interrupteur → démarre la BoucleRooms."""
        if self._actif:
            return
        self._actif = True
        self._executer_cycle()  # premier cycle immédiat
        self._timer.start()
        logger.info("BoucleRooms démarrée")

    def arreter(self) -> None:
        """Désactive l'interrupteur → suspend la BoucleRooms."""
        if not self._actif:
            return
        self._actif = False
        self._timer.stop()
        logger.info("BoucleRooms arrêtée")

    @property
    def est_actif(self) -> bool:
        return self._actif

    # ── Cycle de la boucle ──

    def _executer_cycle(self) -> None:
        """Un cycle : rooms → join → membres → signal."""
        self._cm.schedule_async(self._async_cycle)

    async def _async_cycle(self) -> None:
        """Cycle asynchrone utilisant le client aioslsk."""
        client = self._cm.client
        if client is None:
            return

        # 1. Récupérer la liste des rooms publiques
        rooms = client.rooms.rooms
        self._rooms_actuelles = [
            {"name": name, "users": room.user_count}
            for name, room in rooms.items()
        ]

        # 2. Rejoindre les 5 premières rooms (si pas déjà membre)
        for room_info in self._rooms_actuelles[:5]:
            name = room_info["name"]
            if name not in client.rooms.joined_rooms:
                client.rooms.join_room(name)

        # 3. Récupérer les membres des rooms rejointes
        membres = []
        for name in client.rooms.joined_rooms:
            room = client.rooms.rooms.get(name)
            if room:
                for user in room.users:
                    membres.append({
                        "username": user.name,
                        "room": name,
                        "status": user.status,
                    })

        self._membres_actifs = membres

        # 4. Émettre le signal → ClientsActifsService
        self.membres_actualises.emit(membres)

    @property
    def membres(self) -> list[dict]:
        return self._membres_actifs

    @property
    def rooms(self) -> list[dict]:
        return self._rooms_actuelles
```

### 5.4 Intégration avec ClientsActifsService

```python
# Dans CenterZone ou connexion_manager
self._boucle_rooms = BoucleRooms(connexion_manager)
self._boucle_rooms.membres_actualises.connect(
    self._clients_actifs_service.ingest_membres_rooms
)
```

> **Stockage :** `BoucleRooms` est stockée dans `CenterZone` (ou un registre central) avec les autres boucles.
> Pas de page, pas d'onglet — elle tourne purement en arrière-plan.

---

## 6. 🎮 Contrôle via BotAccueil

### 6.1 Délégation automatique

Quand l'utilisateur tape un message dans l'Accueil, le flow est :

1. `_on_user_input(text)` est appelé
2. `_match_intent(text)` trouve l'intention la plus proche
3. Si l'intention a des `actions` dans KNOWLEDGE → exécutées par `_execute_actions()`
4. `_execute_actions()` gère les actions `start_loop`, `stop_loop`, `start_loop_and_navigate`, `navigate`, `message`, `delay`, `suggestions`

### 6.2 Mécanisme de démarrage/arrêt d'une boucle

Le BotAccueil a besoin d'un **pont** vers le monde des boucles. Ce pont est une fonction callable injectée par `CenterZone` :

```python
class CenterZone(QFrame):
    def _build_accueil_page(self) -> None:
        page = BotAccueil()
        page.page_changed.connect(self.show_page)
        self._pages["Accueil"] = page
        self._stack.addWidget(page)
        # Injecter le loop starter et stopper pour permettre à l'Accueil
        # de démarrer/arrêter les boucles des bots
        page.set_loop_starter(self._start_loop)
        page.set_loop_stopper(self._stop_loop)

    def _start_loop(self, loop_name: str) -> bool:
        """Active l'interrupteur d'une boucle par son nom.
        
        Le mapping contient à la fois des bots (avec boucle) et des boucles pures.
        """
        mapping = {
            "Recherche": self._pages.get("Recherche"),
            "Téléchargement": self._pages.get("telechargements"),
            "Clients Actifs": self._pages.get("Clients Actifs"),
            "Rooms": self._boucle_rooms,             # ← boucle pure (QObject)
            "Surveillance": self._pages.get("Surveillance"),
            "Bibliothèque": self._pages.get("Bibliothèque"),
            "Wishlist": self._pages.get("Wishlist"),
            "Planificateur": self._pages.get("Planificateur"),
            "Optimiseur": self._pages.get("Optimiseur"),
            "Ordonnanceur": self._pages.get("Ordonnanceur"),
        }
        loop = mapping.get(loop_name)
        if loop is None:
            logger.warning("Boucle %s inconnue", loop_name)
            return False
        if hasattr(loop, "demarrer"):
            loop.demarrer()  # active l'interrupteur
            logger.info("Boucle %s démarrée", loop_name)
            return True
        logger.warning("%s n'a pas de méthode demarrer()", loop_name)
        return False

    def _stop_loop(self, loop_name: str) -> bool:
        """Désactive l'interrupteur d'une boucle par son nom."""
        mapping = {
            "Recherche": self._pages.get("Recherche"),
            "Téléchargement": self._pages.get("telechargements"),
            "Clients Actifs": self._pages.get("Clients Actifs"),
            "Rooms": self._boucle_rooms,
            "Surveillance": self._pages.get("Surveillance"),
            "Bibliothèque": self._pages.get("Bibliothèque"),
            "Wishlist": self._pages.get("Wishlist"),
            "Planificateur": self._pages.get("Planificateur"),
            "Optimiseur": self._pages.get("Optimiseur"),
            "Ordonnanceur": self._pages.get("Ordonnanceur"),
        }
        loop = mapping.get(loop_name)
        if loop is None:
            logger.warning("Boucle %s inconnue", loop_name)
            return False
        if hasattr(loop, "arreter"):
            loop.arreter()
            logger.info("Boucle %s arrêtée", loop_name)
            return True
        logger.warning("%s n'a pas de méthode arreter()", loop_name)
        return False
```

> `_start_loop()` et `_stop_loop()` gèrent aussi bien les boucles portées par un bot (ex: `self._pages["Recherche"].demarrer()`)
> que les boucles pures (ex: `self._boucle_rooms.demarrer()`). Toutes implémentent le même contrat `demarrer()/arreter()`.

---

## 7. 🔄 WorkflowInspector — contrôle DevTool

### 7.1 Boutons Démarrer/Arrêter une boucle

Les boutons existants dans le WorkflowInspector continuent de fonctionner comme avant. Ils appellent directement `demarrer()` / `arreter()` sur chaque bot (ce qui démarre/arrête sa boucle interne).

C'est le **seul endroit** où l'utilisateur peut contrôler les boucles manuellement (hors BotAccueil).

### 7.2 Statut temps réel

Le WorkflowInspector continue d'afficher le statut en temps réel (2s de rafraîchissement) avec :
- 🟢 ACTIF → si la boucle du bot est active
- 🔴 STOPPED → si la boucle du bot n'est pas active
- ⚪ UNKNOWN → si le bot n'a pas de boucle (pas de `demarrer()`) — Aide, Ordonnanceur, Accueil

---

## 8. 🧪 Tests

### 8.1 Tests unitaires par boucle

| Test | Description |
|------|-------------|
| `test_demarrer_arret` | demarrer() puis arreter() → boucle arrêtée correctement |
| `test_demarrer_deux_fois` | demarrer() → demarrer() → ignoré (pas de double boucle) |
| `test_arreter_sans_demarrer` | arreter() sans demarrer() → ignoré |
| `test_boucle_est_active` | Après demarrer(), est_actif = True |
| `test_boucle_est_inactive` | Après arreter(), est_actif = False |

### 8.2 Tests d'intégration

| Test | Description |
|------|-------------|
| `test_boucle_rooms_cycle` | Un cycle BoucleRooms → rooms rejointes → membres récupérés |
| `test_rooms_to_clients_actifs` | Membres rooms → signal → ClientsActifsService |
| `test_loop_starter_mapping` | `_start_loop("Recherche")` → bot.demarrer() appelé → boucle lancée |

---

## 9. 📋 Plan d'implémentation

| Étape | Tâche | Fichiers | Dépend de |
|-------|-------|----------|-----------|
| **1** | Ajouter `demarrer()/arreter()` sur tous les bots qui ont une boucle | Chaque `bot_*.py` | — |
| **2** | Implémenter `BoucleRooms(QObject)` — boucle pure (pas de widget, pas de page) | `src/services/boucle_rooms.py` | Étape 1 |
| **3** | Connecter BoucleRooms dans CenterZone + injecter `_boucle_rooms` dans le mapping | `center.py`, `clients_actifs_service.py` | Étape 2 |
| **4** | Connecter `membres_actualises` (sortie BoucleRooms) → ClientsActifsService | `center.py`, `clients_actifs_service.py` | Étape 3 |
| **5** | Ajouter `start_loop` comme type d'action dans KNOWLEDGE | `bot_accueil_knowledge.py` | Étape 1 |
| **6** | Implémenter `_start_loop()` dans BotAccueil + `set_loop_starter()` | `bot_accueil.py` | Étape 5 |
| **7** | Connecter `set_loop_starter()` depuis CenterZone | `center.py` | Étape 6 |
| **8** | Ajouter message + toast lors du démarrage d'une boucle (feedback user) | `bot_accueil.py`, `main_window.py` | Étape 6 |
| **9** | Mettre à jour WorkflowInspector pour afficher les boucles pures (Rooms) | `workflow_inspector.py` | Étape 2 |
| **10** | Tests unitaires (demarrer/arreter pour chaque boucle) | `tests/test_bot_*.py` + `tests/test_boucle_rooms.py` | Étape 1, 2 |

---

## 10. ❓ Questions résolues

- [x] **Boucle principale** : Login → Accueil → Attente. Rien d'autre.
- [x] **Déclenchement des boucles** : Automatique via le BotAccueil qui analyse la demande utilisateur. L'utilisateur ne clique pas sur "Démarrer".
- [x] **Interface standard** : `demarrer()` / `arreter()` sur chaque bot (démarre/arrête sa boucle).
- [x] **Type de boucle** : Chaque bot selon son besoin (QTimer, asyncio, QThread, events passifs).
- [x] **Registre des boucles** : KNOWLEDGE étendu dans `bot_accueil_knowledge.py`.
- [x] **Contrôle utilisateur** : Uniquement via le WorkflowInspector (DevTool).
- [x] **Arrêt = suspension** : Pas de destruction complète. Reprise rapide.
- [x] **Double start** : Ignoré silencieusement (log debug).
- [x] **Thread partagé** : Tous les bots réseau utilisent le même ConnexionManager.
- [x] **Arrière-plan** : Les boucles continuent même si la page n'est pas visible.
- [x] **Feedback user** : Message dans le chat + toast notification.
- [x] **Navigation auto** : Dépend de la demande — décidé au moment de l'implémentation de l'Accueil.
- [x] **Première boucle** : BoucleRooms (récupère rooms → rejoint 5 premières → affiche membres → source pour ClientsActifs).
- [x] **Nouveau type d'action** : `start_loop` ajouté au moteur d'actions de l'Accueil.
- [x] **Distinction Bot vs Boucle** : Un bot = un widget UI. Zero ou UNE boucle par bot.
  Boucle = processus arrière-plan (timer, thread). `demarrer()` = active son interrupteur.
- [x] **Boucle pure** : Peut exister sans widget (BoucleRooms = QObject, pas de page, pas d'onglet).
- [x] **Interrupteur** : Chaque boucle a un interrupteur ON/OFF que l'Accueil active.

---

## 11. 🔮 Prochaines étapes suggérées après cette spec

1. Implémenter l'étape 1 — ajouter `demarrer()/arreter()` sur tous les bots qui ont une boucle
2. Implémenter `BoucleRooms(QObject)` — première boucle pure (pas de widget)
3. Connecter le flux BoucleRooms → ClientsActifsService
4. Ajouter le type d'action `start_loop` dans l'Accueil
5. Étendre le KNOWLEDGE avec les informations de boucle

---

> *Spec v1.1 — Distinction Bot/Boucle clarifiée le 2026-05-19*
