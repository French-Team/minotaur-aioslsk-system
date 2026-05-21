# Spec Debug — Diagnostic des Bots

> **Statut :** ✅ Implémentation complète — 11 problèmes corrigés
> **Dernière mise à jour :** 2026-05-21

---

## Table des matières

1. [Problème #1 — Arès : clients actifs ne montre que "moi"](#problème-1--arès--clients-actifs-ne-montre-que-moi)
2. [Problème #2 — Héra : page "en construction"](#problème-2--héra--page-affiche-en-construction-alors-que-le-bot-est-prêt)
3. [Problème #3 — RoomService invisible dans la matrice](#problème-3--roomservice-invisible-dans-la-matrice-workflowinspector)
4. [Problème #4 — Couleur #fff 3 chiffres](#problème-4--couleur-fff-sur-3-chiffres-non-supportée-par-qt)
5. [Problème #5 — Service Inspector : statut toujours "STOPPED"](#problème-5--service-inspector--roomservice-et-clientsactifsservice-toujours-stopped)
6. [Problème #6 — Couleur #333 3 chiffres dans Héra](#problème-6--couleur-333-sur-3-chiffres-dans-le-dashboard-héra)
7. [Problème #7 — Panneau \"Les Rooms\" vide après connexion](#problème-7--panneau-les-rooms-vide-alors-que-connecté)
8. [Problème #8 — Inspecteur des tâches asyncio vide](#problème-8--inspecteur-des-tâches-asyncio-naffiche-plus-rien)
9. [Problème #9 — EventBus.emit_event() : paramètres inversés (category↔source)](#problème-9--eventbusemit_event--paramètres-inversés-categorysource)
10. [Problème #10 — Audit global : paramètres inversés dans emit_event()](#problème-10--audit-global-des-34-appels-emit_event)
11. [Problème #11 — EventBus dynamique : supprimer la validation statique des catégories](#problème-11--rendre-eventbus-dynamique)

---

## Problème #1 — Arès : clients actifs ne montre que "moi"

### Symptôme

La table de `BotClientsActifs` n'affiche que l'utilisateur courant ("moi"), même après
avoir cliqué sur 🔄 Rafraîchir et attendu plusieurs cycles de `BoucleRooms` (30s).

### Flux attendu

```
BoucleRooms._async_cycle()
  ├─ 1. client.rooms.rooms → dict[str, Room] (rooms connues)
  ├─ 2. Trier par user_count → top 5
  ├─ 3. JoinRoomCommand(name) pour les non-rejointes
  ├─ 4. client.rooms.joined_rooms → membres des rooms → signal
  │
  ▼
ClientsActifsService.ingest_membres_rooms(membres)
  ├─ Ajoute les nouveaux usernames à _clients
  └─ lancer_ping(membres)
       │
       ▼
  _ping_par_lots(membres) → GetUserStatusCommand(username)
       │
       ▼
  _on_ping_termine(reponses) → filtre ONLINE → clients_valides
       │
       ▼
  BotClientsActifs → met à jour la table
```

### Analyse — 2 bugs identifiés

#### Bug #1 : `joined_rooms` n'est pas un attribut — c'est une méthode

**Fichier :** `src/services/boucle_rooms.py` — lignes 106 et 117

```python
# ❌ Bogue : joined_rooms n'est pas une propriété du RoomManager
# RoomManager n'a qu'une propriété 'rooms' et des méthodes
# get_joined_rooms() / get_public_rooms()
if name not in client.rooms.joined_rooms:       # lève AttributeError
for name in client.rooms.joined_rooms:           # lève AttributeError
```

L'accès à `client.rooms.joined_rooms` lève une `AttributeError` car `RoomManager`
n'a pas d'attribut `joined_rooms`. Cette exception est **silencieusement avalée**
car la méthode `_async_cycle()` n'a pas de gestionnaire d'erreur spécifique pour cela.

**Preuve :** Dans `RoomManager` de aioslsk :
- `rooms` : ✅ propriété → `dict[str, Room]`
- `get_joined_rooms()` : ✅ méthode → `list[Room]` (rooms où `room.joined == True`)
- `get_public_rooms()` : ✅ méthode → `list[Room]` (rooms où `room.private == False`)
- `joined_rooms` : ❌ **n'existe pas en tant qu'attribut ou propriété**

#### Bug #2 : `room.users` est vide pour les rooms publiques

Même si le Bug #1 est corrigé, `BoucleRooms` itère `room.users` qui est pratiquement
toujours vide. Dans aioslsk :

- `RoomMembersEvent` n'est émis que pour les **rooms privées** (`PrivateRoomMembers.Response`)
- Pour les **rooms publiques**, le serveur n'envoie **pas** la liste des membres après `JoinRoom`
- `room.users` ne se peuple que via `UserJoinedRoom`/`UserLeftRoom` (quand qqn entre/sort)
- Donc juste après avoir rejoint une room publique, `room.users == []`

### Correction appliquée (2026-05-21)

#### Fichier 1 : `src/services/boucle_rooms.py` — Source A `client.users.users` comme source PRINCIPALE

**Bug #1 déjà corrigé** dans le cadre du Problème #7 (`joined_rooms` → `get_joined_rooms()`).

**Bug #2 corrigé :** `room.users` (toujours vide pour les rooms publiques) remplacé par
`client.users.users` comme source **principale** :

```python
# Source A : client.users.users — TOUS les utilisateurs trackés par le UserManager
# (inclut le user courant + users découverts via UserStatusUpdateEvent,
#  PrivateMessageEvent, etc.)
tracked = client.users.users
for username, user in tracked.items():
    membres.append({...})
    usernames_vus.add(user.name)

# Source B : room.users — best-effort (souvent vide)
for name in joined_names:
    room = client.rooms.rooms.get(name)
    if room and hasattr(room, "users"):
        for user in room.users:
            if user.name not in usernames_vus:
                membres.append({...})
                usernames_vus.add(user.name)
```

**Avantage :** `client.users.users` contient TOUS les utilisateurs que le client a
rencontrés (via UserStatusUpdateEvent, PrivateMessageEvent, RoomMessageEvent, etc.),
et non plus seulement ceux des rooms (qui est vide pour les salles publiques).

#### Fichier 2 : `src/services/clients_actifs_service.py` — Découverte passive via PrivateMessageEvent

Ajout d'un abonnement à `PrivateMessageEvent` dans `demarrer()` :

```python
# Découverte passive : tout utilisateur qui nous envoie un MP
# est automatiquement ajouté à _clients
client.events.register(
    PrivateMessageEvent,
    self._on_private_message,
)
```

La méthode `_on_private_message()` ajoute immédiatement l'expéditeur à `_clients`
avec statut `ONLINE` et émet `clients_synchronises` pour mettre à jour le tableau UI.

### Impact

- **BoucleRooms** : les cycles tournent mais ne collectent jamais de membres → `membres` toujours vide
- **ClientsActifsService** : ne reçoit que l'utilisateur courant depuis `_synchroniser()` (UserManager)
- **BotClientsActifs** : table toujours vide ou ne montrant que "moi"
- **Dégradation de l'XP** : Arès ne sert à rien en l'état

### Tests de vérification

- [ ] Vérifier que `get_joined_rooms()` est bien une méthode qui retourne `list[Room]`
- [ ] Vérifier que `joined_rooms` lève bien `AttributeError`
- [ ] Vérifier que `room.users` est vide juste après `JoinRoomCommand`
- [ ] Vérifier que `UserManager.users` contient au moins l'utilisateur courant
- [ ] Après correction : vérifier que des utilisateurs apparaissent dans la table

---

## Problème #2 — Héra : page affiche "en construction" alors que le bot est prêt

### Symptôme

Quand on clique sur Héra dans le footer, la page centrale affiche "Interface du bot Assistant\n(en construction)" — un simple placeholder vide.

Pourtant, `BotAssistant` (`src/gui/widgets/bots/bot_assistant.py`) existe avec une interface complète :
- Dashboard avec stats (interactions, diagnostics, succès, échecs)
- Flux temps réel (`QListWidget`)
- Dernier diagnostic affiché
- Connexion Signal/Slot avec `BotAccueil`

Même problème pour **Dionysos (Aide)** : `BotAide` (`src/gui/widgets/bots/bot_aide.py`) est entièrement implémenté
avec recherche, viewer Markdown, historique, filtres par catégorie, mais la page montre aussi "en construction".

### Cause racine — Placeholder non écrasé

**Fichier :** `src/gui/layout/center.py`

Dans le `__init__` de `CenterZone`, les pages des bots sont construites en plusieurs passes :

```python
# 1re passe : placeholders génériques
for name in ("Surveillance", "Planificateur", "Assistant", "Aide"):
    self._build_menu_page(name)      # → QWidget + QLabel "(en construction)"

# ...

# 2e passe : vrais bots — écrasent les placeholders
self._build_surveillance_page()      # ✅ écrase "Surveillance"
self._build_planificateur_page()     # ✅ écrase "Planificateur"
# ❌ PAS de _build_assistant_page() ni _build_aide_page()
```

### Correction appliquée (2026-05-20)

**Fichier modifié :** `src/gui/layout/center.py`

1. **Imports** : `from src.gui.widgets.bots.bot_assistant import BotAssistant` et `from src.gui.widgets.bots.bot_aide import BotAide`
2. **Retrait** des placeholders "Assistant" et "Aide" de la boucle `_build_menu_page`
3. **Nouvelles méthodes** :
   - `_build_assistant_page()` — crée `BotAssistant()` et l'ajoute à `_pages["Assistant"]`
   - `_build_aide_page()` — crée `BotAide()` et l'ajoute à `_pages["Aide"]`
4. **Appel** dans `__init__` : après `_build_ordonnanceur_page()`, avant `_connect_event_signals()`
5. **Connexion des signaux** dans `_connect_event_signals()` :
   - `BotAssistant.setup(self._bot_accueil)` — connecte l'assistant au hub Zeus
   - `BotAide.setup(EventBus())` — connecte l'aide aux événements

### Tests de vérification

- [x] Syntaxe Python OK
- [x] Import des classes `BotAssistant` et `BotAide` valide
- [x] `page_changed` connecté pour `BotAide`
- [x] `BotAssistant` n'a pas de `page_changed` (pas nécessaire — page statique)
- [ ] Vérifier visuellement que les pages Héra et Dionysos affichent les vrais dashboards

---

## Problème #3 — RoomService invisible dans la matrice WorkflowInspector

### Symptôme

Dans le Workflow Inspector, la section "Matrice des échanges" et la timeline
ne montrent aucun événement provenant de RoomService. Les événements de
synchronisation des salons, démarrage/arrêt du service sont absents.

Pourtant, la carte "Room Service" apparaît bien dans le tableau de bord
(scannée depuis `main_window._room_service`), mais les compteurs d'événements
restent à 0 et la matrice est vide pour cette entrée.

### Cause racine

**Fichier :** `src/services/room_service.py`

RoomService n'appelle **jamais** `EventBus().emit_event()`. Il utilise uniquement
des signaux Qt internes (`rooms_publiques_recues`, `rooms_privees_recues`,
`room_list_rafraichie`) qui ne sont visibles que par les widgets connectés, pas
par le WorkflowInspector qui s'abonne exclusivement à l'EventBus.

```python
# ❌ Aucune émission EventBus dans RoomService
class RoomService(QObject):
    rooms_publiques_recues = Signal(list)
    rooms_privees_recues = Signal(list)
    room_list_rafraichie = Signal()

    def demarrer(self) -> None:
        self._soulseek.room_list_received.connect(...)
        self._synchroniser()
        # ❌ Pas d'emit_event

    def _synchroniser(self) -> None:
        self.rooms_publiques_recues.emit(...)     # signal Qt seulement
        self.rooms_privees_recues.emit(...)        # signal Qt seulement
        self.room_list_rafraichie.emit()            # signal Qt seulement
        # ❌ Pas d'emit_event
```

Comparé aux autres services qui émettent tous via EventBus :
- `clients_actifs_service.py` : 5 appels à `EventBus().emit_event()`
- `connexion_manager.py` : 3 appels
- `soulseek_client.py` : 3 appels
- `planificateur_service.py` : 7 appels
- `boucle_rooms.py` : 1 appel

### Correction appliquée (2026-05-20)

**Fichier modifié :** `src/services/room_service.py`

Ajout de `EventBus().emit_event()` dans 5 endroits :

| Endroit | Événement | Catégorie |
|---------|-----------|-----------|
| `demarrer()` | "Service démarré" — nb de salles | `room` |
| `arreter()` | "Service arrêté" — listes vidées | `room` |
| `_synchroniser()` | "Salons synchronisés" — nb publiques + privées | `room` |
| `_synchroniser()` exception | "Erreur synchronisation salons" → ERROR | `room` |
| `_on_connection_changed(False)` | "Salles vidées (déconnexion)" | `room` |

### Tests de vérification

- [x] Syntaxe Python OK
- [ ] Vérifier que les événements RoomService apparaissent dans la matrice/timeline
- [ ] Vérifier que le compteur d'événements s'incrémente sur la carte "Room Service"

---

## Problème #4 — Couleur `#fff` sur 3 chiffres non supportée par Qt

### Symptôme

Dans la console de diagnostic (QSS Inspector ou stderr), on voit :
```
⚠ Couleur #fff sur 3 chiffres non supportée par Qt. Utiliser #RRGGBB à la place.
  ◇ QPushButton('🔍 Analyse rapide (notre proc')
```

### Cause racine

Deux occurrences de `#fff` (format 3 chiffres) dans des Qt Stylesheets (QSS) :

1. **`src/gui/devtool/diagnostics/sysinternals_launcher.py`** — ligne 396 :
   ```python
   self._btn_analyse.setStyleSheet(
       "background-color: #6c5ce7; font-weight: bold; color: #fff;"
       #                                                                  ^^^^^ ❌ 3 chiffres
   )
   ```

2. **`src/gui/widgets/bots/bot_aide.py`** — `_CAT_FILTER_STYLE` ligne 139 :
   ```python
   QPushButton:checked {
       color: #fff;       # ❌ 3 chiffres
       border-color: transparent;
   }
   ```

Note : Les `#fff` dans le HTML généré par `_render_content()` (ligne 391) ne sont PAS
concernés — le QTextBrowser utilise un rendu CSS standard qui supporte `#fff`.

### Correction appliquée (2026-05-20)

| Fichier | Correction |
|---------|-----------|
| `src/gui/devtool/diagnostics/sysinternals_launcher.py` | `color: #fff` → `color: #ffffff` |
| `src/gui/widgets/bots/bot_aide.py` | `color: #fff` → `color: #ffffff` dans `_CAT_FILTER_STYLE` |

### Tests de vérification

- [x] Syntaxe Python OK
- [ ] Lancer l'app et vérifier qu'aucun warning `#fff` n'apparaît plus

---

## Problème #5 — Service Inspector : RoomService et ClientsActifsService toujours "STOPPED"

### Symptôme

Dans l'onglet "Démarrage & Tâches" du Service Inspector, la grille des services
affiche "STOPPED" (rouge) pour **Room Service** et **Clients Actifs** même quand
les services tournent normalement (leurs boucles actives, données qui remontent).

Les boutons d'action (Démarrer/Arrêter) ne fonctionnent pas correctement :
cliquer "Démarrer" ne change pas l'affichage car la lecture du statut est erronée.

### Cause racine

**Fichier :** `src/gui/devtool/service_inspector.py`

Deux attributs différents étaient utilisés selon les méthodes :

```python
# ✅ refresh_stats() utilisait _running — correct
if getattr(room_svc, "_running", False):
    self._lbl_room_status.setText("RUNNING")

# ❌ _toggle_room_service() utilisait _demarre — attribut inexistant
if getattr(room_svc, "_demarre", False):  # _demarre n'existe pas !
```

Les services `RoomService` et `ClientsActifsService` utilisent `_running` (pas
`_demarre`) pour suivre leur état de fonctionnement. Quand `_toggle_*()` lisait
`_demarre`, `getattr()` retournait `False` par défaut (attribut inexistant), donc :

- Si le service tourne → `_running = True` mais `_demarre = False` (par défaut)
- `_toggle_*()` voit `False` → appelle `demarrer()` au lieu de `arreter()`
- `refresh_stats()` lisait bien `_running` → affichait correctement "RUNNING"
- Mais après l'appel `_toggle_*()`, `refresh_stats()` voyait le changement → OK

### Correction appliquée (2026-05-20)

**Fichier modifié :** `src/gui/devtool/service_inspector.py`

| Méthode | Avant | Après |
|---------|-------|-------|
| `_toggle_room_service()` | `getattr(room_svc, "_demarre", False)` | `getattr(room_svc, "_running", False)` |
| `_toggle_clients_service()` | `getattr(clients_svc, "_demarre", False)` | `getattr(clients_svc, "_running", False)` |

### Tests de vérification

- [x] Syntaxe Python OK
- [x] Cohérence avec `refresh_stats()` qui utilisait déjà `_running`
- [ ] Vérifier visuellement que les statuts et boutons sont synchronisés

---

## Problème #6 — Couleur `#333` sur 3 chiffres dans le dashboard Héra

### Symptôme

Dans la console de diagnostic (QSS Inspector), on voit :
```
═══ Source : QListWidget ═══
  ⚠ Couleur #333 sur 3 chiffres non supportée par Qt. Utiliser #RRGGBB à la place.
    ◇ QListWidget
    ◇ QWidget[qt_scrollarea_viewport]
    ◇ QWidget[qt_scrollarea_hcontainer]
    ◇ QScrollBar
    ◇ QWidget[qt_scrollarea_vcontainer]
    … et 1 autre(s) widget(s) impacté(s)
```

### Cause racine

**Fichier :** `src/gui/widgets/bots/bot_assistant.py` — ligne 276

```python
"QListWidget::item { padding: 6px 10px; border-bottom: 1px solid #333; }"
#                                                            ^^^^^ ❌ 3 chiffres
```

Le style QSS du QListWidget dans le dashboard du BotAssistant (Héra) utilise
`#333` au lieu de `#333333`. Ce format 3 chiffres n'est pas supporté par Qt
pour les stylesheets.

### Correction appliquée (2026-05-20)

| Fichier | Correction |
|---------|-----------|
| `src/gui/widgets/bots/bot_assistant.py` | `border-bottom: 1px solid #333` → `border-bottom: 1px solid #333333` |

### Tests de vérification

- [x] Syntaxe Python OK
- [ ] Lancer l'app et vérifier qu'aucun warning `#333` n'apparaît plus pour QListWidget

---

## Problème #7 — Panneau "Les Rooms" vide alors que connecté

### Symptôme

Après connexion à Soulseek, le panneau latéral droit "LES ROOMS" (RightZone)
affiche les onglets Public/Privé vides ("Aucun salon disponible" / "Aucun salon rejoint")
malgré une connexion réussie et active.

Parallèlement, la boucle Rooms (BoucleRooms) qui alimente ClientsActifsService
a cessé de collecter des membres — la table Arès est figée sur l'utilisateur courant.

### Flux attendu

```
Connexion réussie → _on_connected()
  ├─ RoomService.demarrer()
  │   ├─ S'abonne à room_list_received (SoulseekService)
  │   ├─ _synchroniser() → client.rooms.get_public_rooms() + get_joined_rooms()
  │   └─ Émet rooms_publiques_recues / rooms_privees_recues → RightZone
  │
  ├─ ConnexionManager._do_login()
  │   └─ asyncio.create_task(GetRoomListCommand()) → RoomListEvent → RoomService._on_room_list()
  │
  └─ _lancer_boucle_rooms_apres_connexion()
      └─ BoucleRooms.demarrer()
          └─ _async_cycle() → client.rooms → membres → ClientsActifsService
```

### Analyse — 2 causes racines possibles

#### Cause A : La boucle asyncio s'est arrêtée

`_AsyncEventLoopThread` exécute `loop.run_forever()`. Si la boucle s'arrête
(exception fatale, `loop.stop()` appelé inopinément), alors :

- `GetRoomListCommand` planifié via `asyncio.create_task()` est annulé
  silencieusement → jamais de `RoomListEvent` → RoomService ne reçoit rien
- `BoucleRooms._async_cycle()` ne peut plus s'exécuter via `run_coro()`
- `ServiceInspector.refresh_asyncio_tasks()` voit `loop.is_running() == False`
  → affiche "Aucune tâche active"

**Preuve indirecte :** Si l'inspecteur asyncio n'affiche rien (Problème #8),
la boucle est probablement arrêtée.

#### Cause B : `GetRoomListCommand` ne reçoit pas de réponse

Même si la boucle tourne, `GetRoomListCommand` peut ne jamais recevoir de
réponse si :

- Le serveur Soulseek a changé de protocole (version mismatch)
- La commande n'est pas supportée par la version d'aioslsk installée
- Un rate-limiting du serveur bloque la réponse

### Impact

- **RightZone** : rooms vides dans les deux onglets → l'utilisateur ne voit pas les salons disponibles
- **BoucleRooms** : ne collecte aucun membre → table Arès vide (Bug #1 déjà documenté)
- **ServiceInspector** : aucune tâche asyncio visible → diagnostic impossible
- **Tous les services asynchrones** : potentiellement impactés (recherche, téléchargement)

### Correction appliquée (2026-05-21)

#### Fichier 1 : `src/services/boucle_rooms.py` — Bug `joined_rooms` + résilience

**Bug #1 corrigé : `client.rooms.joined_rooms` → `client.rooms.get_joined_rooms()`**

`joined_rooms` n'existe pas en tant qu'attribut/propriété sur `RoomManager` — c'est
une méthode `get_joined_rooms()` qui retourne `list[Room]`.

```python
# ❌ AVANT — AttributeError silencieuse à chaque cycle
if name not in client.rooms.joined_rooms:       # lève AttributeError

# ✅ APRÈS — méthode valide
joined = client.rooms.get_joined_rooms()
joined_names = {room.name for room in joined}
if name not in joined_names:
    await client.execute(JoinRoomCommand(name))
```

**Bug #2 contourné : `room.users` vide pour les rooms publiques**

La collecte des membres via `room.users` reste **best-effort** — documenté dans
le code. Les membres ne se peuplent qu'au fil du temps via `UserJoinedRoom`/`UserLeftRoom`.

**Résilience ajoutée :**
- `try/except` autour de chaque `JoinRoomCommand` individuelle (une room qui échoue
  ne bloque pas les autres)
- `try/except AttributeError` attrape les erreurs d'API aioslsk (changement de version)
- `try/except Exception` attrape toute autre exception → logguée au lieu d'être
  silencieuse
- Émission d'événements EventBus pour chaque cycle réussi ou en erreur → visible
  dans WorkflowInspector

#### Fichier 2 : `src/gui/devtool/service_inspector.py` — Diagnostic de santé de la boucle

`refresh_asyncio_tasks()` retourne maintenant des messages de diagnostic explicites :

| Condition | Message affiché dans l'arbre |
|-----------|-----------------------------|
| Aucun `ConnexionManager` | `"Aucun ConnexionManager — thread asyncio introuvable"` |
| Thread asyncio non init | `"Thread asyncio non initialisé"` |
| Boucle asyncio non créée | `"Boucle asyncio non créée"` |
| `loop.is_running() == False` | `"🔴 Boucle asyncio ARRÊTÉE — thread mort ou exception non gérée"` |
| Aucune tâche active | `"Aucune tâche asyncio active dans la boucle"` |

Le message d'arrêt de boucle est en **jaune** (`#f9e2af`) et le QTreeWidget
s'arrête là (pas de faux "aucune tâche").

### Test de diagnostic

1. Lancer le diagnostic brut (onglet "Diagnostique Brute" du ServiceInspector)
2. Si le handshake échoue → le serveur bloque notre IP (ratelimit)
3. Si le handshake réussit mais les rooms sont vides → bug applicatif

---

## Problème #8 — Inspecteur des tâches asyncio n'affiche plus rien

### Symptôme

Dans l'onglet "Démarrage & Tâches" du Service Inspector, la section
"INSPECTEUR DES TÂCHES ASYNCIO" affiche "Aucune tâche asyncio active"
ou l'arbre est complètement vide — aucune tâche réseau listée malgré
une connexion active.

### Flux attendu

```
ServiceInspector.refresh_asyncio_tasks()
  ├─ Récupère _connexion_manager._async_thread._loop
  ├─ Vérifie loop.is_running()
  ├─ query_loop_tasks() dans la boucle via asyncio.run_coroutine_threadsafe()
  │   ├─ asyncio.all_tasks(loop) → liste des tâches
  │   ├─ Filtre _async_wrapper / query_loop_tasks
  │   └─ Retourne [(name, coro, state, stack), ...]
  │
  ▼
_emitter.tasks_received.emit(tasks)
  │
  ▼
_update_tasks_list_ui(tasks) → QTreeWidget
```

### Analyse — 4 points de défaillance possibles

#### 1. Boucle asyncio arrêtée (`loop.is_running() == False`)

**Fichier :** `src/services/connexion_manager.py` — classe `_AsyncEventLoopThread`

```python
def run(self) -> None:
    self._loop = asyncio.new_event_loop()
    asyncio.set_event_loop(self._loop)
    self._loop.call_soon(self._ready_event.set)
    try:
        self._loop.run_forever()
    finally:
        self._loop.close()
```

Si `run_forever()` se termine (exception non gérée, ou `loop.stop()` externe),
la boucle est fermée et `is_running()` retourne False définitivement.

Causes possibles de l'arrêt :

- Exception non rattrapée dans une coroutine (bien qu'asyncio isole les coroutines)
- Appel intempestif à `loop.stop()` (potentiellement via une lib externe)
- Crash du thread (race condition Qt/threading)

#### 2. Le filtre exclut toutes les tâches

```python
if "_async_wrapper" in qualname or "query_loop_tasks" in qualname:
    continue
```

Après plusieurs cycles, la boucle pourrait n'avoir que la tâche d'inspection
elle-même. Si les autres tâches se sont terminées (par exemple si
`GetRoomListCommand` est terminée) ou si aucune nouvelle connexion n'est en cours,
la boucle peut être momentanément vide.

#### 3. `asyncio.run_coroutine_threadsafe()` lève une exception

```python
def future_done(future) -> None:
    try:
        res = future.result()
        self._emitter.tasks_received.emit(res)
    except Exception as e:
        logger.debug("Exception fetching asyncio tasks: %s", e)
```

Si `future.result()` lève une exception, le signal `tasks_received` n'est PAS émis.
L'arbre reste dans son état précédent (figé).

#### 4. L'onglet n'est pas sélectionné (cause UI)

```python
def refresh_all(self) -> None:
    ...
    if self._tabs.currentIndex() == 0:
        self.refresh_asyncio_tasks()
```

Le polling automatique (1.5s) n'actualise les tâches QUE si l'onglet
"Démarrage & Tâches" (index 0) est actif. Sur un autre onglet, l'arbre
est figé. Mais le bouton "Rafraîchir Tâches" force la mise à jour
indépendamment de l'onglet.

### Correction appliquée (2026-05-21)

**Fichier :** `src/gui/devtool/service_inspector.py`

4 améliorations implémentées :

1. **Logging de l'état de la boucle** : `logger.debug("ServiceInspector: boucle asyncio active — lancement de l'inspection")`
2. **Logging du nombre de tâches AVANT et APRÈS filtrage** :
   ```python
   logger.debug("ServiceInspector: %d tâches brutes, %d après filtrage", total_brut, len(results))
   ```
   via un mutable `total_brut = [0]` accessible dans la closure `query_loop_tasks()`
3. **Flag `_tasks_in_foreground`** — remplace le check d'index d'onglet :
   ```python
   self._tasks_in_foreground = True
   self._tabs.currentChanged.connect(
       lambda idx: setattr(self, "_tasks_in_foreground", idx == 0)
   )
   ```
   Le bouton "Rafraîchir Tâches" force la mise à jour même quand l'utilisateur est
   sur un autre onglet, car il appelle `refresh_asyncio_tasks()` directement
   (contourne le check `_tasks_in_foreground` car c'est un appel manuel).
4. **Messages de diagnostic déjà ajoutés** dans le cadre du Problème #7 :
   - Boucle arrêtée → "🔴 Boucle asyncio ARRÊTÉE" (rouge)
   - Thread non init, pas de boucle, etc. (messages bleus/jaunes)

### Impact

- **ServiceInspector utilisable** : l'utilisateur voit immédiatement l'état de santé
  de la boucle + le nombre de tâches avant/après filtrage dans les logs

---

## Problème #9 — EventBus.emit_event() : paramètres inversés (category↔source)

### Symptôme

```
TypeError: EventBus.emit_event() got multiple values for argument 'category'
```

Le crash survient à la déconnexion et au démarrage/arrêt de RoomService :
`_on_connection_changed()`, `arreter()`, `demarrer()`, `_synchroniser()`.

### Trace complète

```
File "src/services/room_service.py", line 230, in _on_connection_changed
    EventBus().emit_event(
        "room_service", "INFO", "Salles vidées (déconnexion)",
        "",
        category="room",
    )
TypeError: EventBus.emit_event() got multiple values for argument 'category'

File "src/services/room_service.py", line 125, in arreter
    EventBus().emit_event(
        "room_service", "INFO", "Service arrêté",
        "Désabonné de room_list_received, listes vidées",
        category="room",
    )
TypeError: EventBus.emit_event() got multiple values for argument 'category'
```

### Cause racine

**Fichier :** `src/services/room_service.py` — 5 appels `EventBus().emit_event()`

La signature de `emit_event()` est :

```python
def emit_event(
    self,
    category: str,           # ← 1er paramètre POSITIONNEL
    severity: str = "INFO",
    title: str = "",
    message: str = "",
    source: str = "",
    details: dict | None = None,
) -> SurveillanceEvent | None:
```

Les appels ajoutés dans le cadre du Problème #3 (RoomService invisible dans la
matrice WorkflowInspector) avaient **inversé l'ordre des paramètres** :

```python
# ❌ AVANT — "room_service" (source) en 1er (→ category), puis "room" en keyword
EventBus().emit_event(
    "room_service",      # → affecté à `category` !
    "INFO",              # → severity
    "Service démarré",   # → title
    "message...",        # → message
    category="room",     # ❌ CONFLIT : category déjà = "room_service"
)
```

Le premier argument `"room_service"` était censé être le `source`, mais il était
placé en position de `category`. Puis `category="room"` en keyword créait un
conflit → `TypeError: got multiple values for argument 'category'`.

### Correction appliquée (2026-05-21)

Les 5 appels ont été corrigés en utilisant des keyword arguments explicites :

```python
# ✅ APRÈS — keyword args explicites, plus d'ambiguïté
EventBus().emit_event(
    category="room",
    severity="INFO",
    title="Service démarré",
    message="...",
    source="room_service",
)
```

**Endroits corrigés :**

| Méthode | Ligne | Correction |
|---------|-------|-----------|
| `demarrer()` | ~107 | `"room_service"` (1er arg) → `category="room"` |
| `arreter()` | ~125 | `"room_service"` (1er arg) → `category="room"` |
| `_synchroniser()` (try) | ~162 | `"room_service"` (1er arg) → `category="room"` |
| `_synchroniser()` (except) | ~170 | `"room_service"` (1er arg) → `category="room"` |
| `_on_connection_changed(False)` | ~230 | `"room_service"` (1er arg) → `category="room"` |

### Leçon

- Toujours utiliser des **keyword arguments** pour `EventBus().emit_event()`,
  surtout quand il y a plus de 2 paramètres
- La signature de `emit_event()` place `category` en 1er, pas `source`
- Ne JAMAIS mélanger positionnel et keyword pour le même argument
- Vérifier la signature de la fonction cible avant d'ajouter des appels

### Bug secondaire — Catégorie "room" non autorisée

Une fois le `TypeError` corrigé, un second bug attendait : `category="room"` n'est **pas
validé** par `SurveillanceEvent` ni par la contrainte SQLite.

```python
# src/services/event_bus.py — CATEGORIES valides :
# "reseau", "transfert", "recherche", "bibliotheque",
# "configuration", "erreur", "bot", "wishlist", "optimiseur"
# ❌ "room" n'est PAS dans la liste
```

Conséquence : `SurveillanceEvent(category="room")` lève `ValueError: Catégorie invalide : 'room'`,
et l'insert SQLite échoue sur la CHECK contrainte.

#### Correction (2026-05-21)

**Fichier :** `src/services/event_bus.py`

1. Ajout de `"room"` à `SurveillanceEvent.CATEGORIES`
2. Ajout de `'room'` à la CHECK contrainte SQL : `CHECK(category IN (...'room'))`
3. Incrément de `_SCHEMA_VERSION` 2 → 3 (déclenche la migration ALTER TABLE au prochain démarrage)

### Tests de vérification

- [x] Syntaxe Python OK
- [ ] Lancer l'app → la migration SQL s'exécute (version 2 → 3)
- [ ] Se connecter/déconnecter → aucun `TypeError` ni `ValueError`
- [ ] Vérifier que les événements RoomService apparaissent dans la matrice WorkflowInspector

---

## Problème #10 — Audit global des 34 appels emit_event()

### Symptôme

Après la correction du Problème #9, on veut s'assurer qu'aucun autre appel
à `EventBus().emit_event()` dans le codebase n'a les paramètres inversés
(`source` en position de `category`, ou mélange positionnel+keyword).

### Vérification : Audit exhaustif (2026-05-21)

**Résultat : ✅ 0 paramètres inversés — tous les appels utilisent des keyword args.**

| Fichier | Nb appels | Pattern | Statut |
|---------|:---------:|---------|:------:|
| `src/services/clients_actifs_service.py` | 5 | `emit_event(category="bot", severity=..., source="clients_actifs_service")` | ✅ |
| `src/services/connexion_manager.py` | 3 | `emit_event(category="reseau", severity=..., source="ConnexionManager")` | ✅ |
| `src/services/soulseek_client.py` | 3 | `emit_event(category="transfert", severity=..., source="SoulseekService")` | ✅ |
| `src/services/boucle_rooms.py` | 1 | `emit_event(category="bot", severity=..., source="boucle_rooms")` | ✅ |
| `src/services/event_bus.py` | 1 | `emit_event(category="reseau", severity=..., source="connexion_manager")` | ✅ |
| `src/services/room_service.py` | 5 | `emit_event(category="room", ...)` **corrigé** au Problème #9 | ✅ |
| `src/gui/widgets/bots/bot_optimiseur.py` | 4 | `emit_event(category="optimiseur", ..., source="BotOptimiseur")` | ✅ |
| `src/gui/widgets/bots/bot_recherche.py` | 3 | `emit_event(category="recherche", ..., source="BotRecherche")` | ✅ |
| `src/gui/widgets/bots/bot_telechargement.py` | 4 | `emit_event(category="transfert", ..., source="telechargement")` | ✅ |
| `src/gui/widgets/bots/bot_wishlist.py` | 2 | `emit_event(category="wishlist", ..., source="BotWishlist")` | ✅ |
| `src/gui/widgets/bots/bot_bibliotheque.py` | 3 | `emit_event(category="bibliotheque", ..., source="BotBibliotheque")` | ✅ |
| **TOTAL** | **34** | — | **✅ 0 bugs** |

### Analyse des catégories utilisées

| Catégorie | Nb appels | Fichiers sources | Statut |
|:---------:|:---------:|-----------------|:------:|
| `bot` | 6 | clients_actifs_service, boucle_rooms | ✅ dans CATEGORIES |
| `reseau` | 4 | connexion_manager, event_bus | ✅ dans CATEGORIES |
| `transfert` | 7 | soulseek_client, bot_telechargement | ✅ dans CATEGORIES |
| `recherche` | 3 | bot_recherche | ✅ dans CATEGORIES |
| `wishlist` | 2 | bot_wishlist | ✅ dans CATEGORIES |
| `bibliotheque` | 3 | bot_bibliotheque | ✅ dans CATEGORIES |
| `optimiseur` | 4 | bot_optimiseur | ✅ dans CATEGORIES |
| `room` | 5 | room_service | ✅ Ajoutée au Problème #9 |

### Conclusion

- **Aucun paramètre inversé** dans tout le codebase — tous les appels utilisent
  des keyword arguments explicites
- Le seul bug était `room_service.py` (positionnel → keyword, corrigé)
- **Aucun appel** ne vient des panneaux de configuration (`src/gui/widgets/config/`)
- **8 catégories** sont utilisées sur les 10 définies dans `SurveillanceEvent.CATEGORIES`
  (uniquement `configuration` et `erreur` ne sont pas utilisées directement)

### Leçon consolidée

1. **Toujours utiliser des keyword arguments** pour `EventBus().emit_event()` —
   cela évite toute ambiguïté sur l'ordre des paramètres
2. La signature est : `emit_event(category, severity, title, message, source, details)`
   — `category` en 1er (obligatoire), `source` en 5e (optionnel)
3. Vérifier la signature AVANT d'ajouter un appel, surtout en copier-coller
4. Ajouter une entrée dans cette table d'audit quand on ajoute un nouvel appel

---

## Problème #11 — Rendre EventBus dynamique ✓

**Statut :** ✅ Implémenté le 2026-05-21

### Problème

`EventBus` et `SurveillanceEvent` validaient les catégories de façon **statique**
à deux niveaux : validation Python (`CATEGORIES`) et CHECK contrainte SQL.
Chaque nouvelle catégorie nécessitait 3 modifications + une migration de base.

### Solution appliquée

Suppression de la validation statique — les catégories sont désormais en **chaîne libre**
(n'importe quelle chaîne est acceptée).

#### 1. Python — `SurveillanceEvent.CATEGORIES` supprimé

```python
# ✅ APRÈS — plus de CATEGORIES, plus de validation
class SurveillanceEvent:
    SEVERITIES = ("INFO", "WARN", "ERROR")  # ← seul SEVERITIES subsiste

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat(timespec="seconds")
        if self.severity not in self.SEVERITIES:
            raise ValueError(f"Sévérité invalide : {self.severity!r}")
        # ✅ category n'est plus validé — n'importe quelle chaîne est acceptée
```

#### 2. SQL — CHECK contrainte supprimée

```sql
category TEXT NOT NULL,  -- ✅ plus de CHECK, chaîne libre
```

#### 3. Migration — `_SCHEMA_VERSION` 3 → 4

Contrairement à la proposition initiale, **une migration est nécessaire**.
Sans `_SCHEMA_VERSION = 4`, les bases version 3 existantes conservent l'ancienne
CHECK contrainte (`v3 < v3 = False` → pas de migration).

`v3 < v4 = True` → `ALTER TABLE events RENAME TO events_old` → création de la
nouvelle table sans CHECK → `INSERT INTO ... SELECT * FROM events_old`.

### Modifications

| Fichier | Changement |
|---------|-----------|
| `src/services/event_bus.py` | `CATEGORIES` supprimé, validation `__post_init__` retirée, CHECK SQL supprimée, `_SCHEMA_VERSION` 3→4 |
| `tests/test_eventbus_routing.py` | Tests `test_all_valid_categories`, `test_invalid_category_raises`, `test_emit_all_categories`, `test_emit_categorie_invalide_leve_value_error` supprimés. Classe `TestBotCategoriesIntegration` supprimée. `TestContrainteSQL` adapté : ne teste plus que la CHECK severity. Ajout de `test_emit_any_category` et `test_categorie_libre_reussit`. |
| `specs/bot-debug-spec.md` | Mise à jour de cette section (statut, actions cochées) |

### Tests de vérification

- [x] Syntaxe Python OK
- [x] Tests : 53/53 verts
- [x] Plus aucune référence résiduelle à `CATEGORIES` dans event_bus.py
- [x] `query()`, `get_stats()`, `get_recent()` continuent de fonctionner
- [x] `_row_to_event()` inchangé (lit `category` comme colonne, pas comme constante)
- [ ] Lancer l'app → migration v3→v4 au démarrage
- [ ] Émettre un événement avec une catégorie inconnue → OK (plus de ValueError)

### Avantages

| Avant | Après |
|-------|-------|
| ❌ Chaque nouvelle catégorie = 3 modifs + migration | ✅ Catégorie = simple chaîne, zéro maintenance |
| ❌ `ValueError` si catégorie inconnue | ✅ Jamais de crash — l'événement est toujours persisté |
| ❌ `CATEGORIES` tuple = connaissance figée | ✅ Découverte dynamique via `get_stats()["par_categorie"]` |
| ❌ Fausse sécurité (valide à l'insert, pas à la lecture) | ✅ Cohérent : la base stocke ce qu'on lui donne |

### Leçon

- Une contrainte CHECK SQL semble une bonne idée pour l'intégrité des données,
  mais dans un système événementiel où les catégories évoluent fréquemment,
  elle devient un fardeau de maintenance. Mieux vaut laisser le champ libre et
  utiliser le GROUP BY pour découvrir les catégories utilisées dynamiquement.
- Attention au piège de "pas de migration nécessaire" — vérifier que la condition
  `version < _SCHEMA_VERSION` est bien vraie pour les bases existantes.
  `_SCHEMA_VERSION` doit toujours être strictement supérieur à la dernière
  version déployée en production.
