# Référence API aioslsk v1.6.3 — Vérifiée par introspection

> **Source :** Introspection directe du package `aioslsk` installé localement (`pip show aioslsk`).
> **Usage :** Cette référence sert de source unique de vérité pour toute implémentation utilisant aioslsk.
> **NE JAMAIS inventer de signatures API** — toujours se référer à ce document ou relancer `researcher-aioslsk`.

---

## Table des matières

1. [Architecture de SoulSeekClient](#1-architecture-de-soulseekclient)
2. [UserManager — `client.users`](#2-usermanager---clientusers)
3. [Modèle `User`](#3-modèle-user)
4. [ServerManager — `client.server_manager`](#4-servermanager---clientserver_manager)
5. [SearchManager — `client.searches`](#5-searchmanager---clientsearches)
6. [PeerManager — `client.peers`](#6-peermanager---clientpeers)
7. [Modèles de recherche](#7-modèles-de-recherche)
8. [Événements (EventBus)](#8-événements-eventbus)
9. [Événements clés détaillés](#9-événements-clés-détaillés)
10. [Pattern d'injection existant](#10-pattern-dinjection-existant)

---

## ⚡ Notes importantes

### aioslsk est event-driven

**Pas de polling :** les mises à jour arrivent via les événements. On ne ping pas les utilisateurs —
on s'abonne aux `UserStatusUpdateEvent` / `UserInfoUpdateEvent` et le serveur notifie
automatiquement les changements de statut des utilisateurs trackés.

### `track_user()` n'a qu'un seul paramètre

Contrairement à ce que certaines specs ont spéculé, `UserManager.track_user()` ne prend qu'un
`username: str` — pas de second paramètre `flag?`.

### `search_on_user` n'existe pas — utiliser `search_user`

La méthode correcte est `SearchManager.search_user(username, query)`. Attention :
le `SearchManager` est accessible via `client.searches`, **pas** `client.search_manager`.

### `send_ping()` ping le serveur, pas un utilisateur

`ServerManager.send_ping()` envoie un ping au **serveur Soulseek**, pas aux utilisateurs.
Il n'y a pas de ping utilisateur direct dans aioslsk — le suivi se fait via les événements.

### Mise en garde générale

Toutes les signatures de cette référence ont été **vérifiées par introspection du code source**
d'`aioslsk==1.6.3`. Ne jamais inventer de signatures — toujours se référer à ce document
ou relancer l'agent `researcher-aioslsk` / une introspection Python directe.

---

## 1. Architecture de SoulSeekClient

### Attributs du client

Tous les managers sont assignés **directement dans `__init__`** (pas de `@property`).

```python
class SoulSeekClient:
    def __init__(self, settings, event_bus=None):
        self.settings: Settings             = settings
        self.events: EventBus               = event_bus or EventBus()
        self.session: Optional[Session]     = None

        # Managers — noms RÉELS sur l'instance
        self.network: Network                      = self.create_network()
        self.distributed_network: DistributedNetwork = self.create_distributed_network()
        self.users: UserManager                     = self.create_user_manager()
        self.rooms: RoomManager                     = self.create_room_manager()
        self.interests: InterestManager             = self.create_interest_manager()
        self.shares: SharesManager                  = self.create_shares_manager(...)
        self.transfers: TransferManager             = self.create_transfer_manager(...)
        self.peers: PeerManager                     = self.create_peer_manager()
        self.searches: SearchManager                = self.create_search_manager()
        self.server_manager: ServerManager          = self.create_server_manager()

        self.services: list[BaseManager]            = [...]  # Tous les managers ci-dessus
```

### ⚠️ Pièges courants

| Mauvais (n'existe pas) | Correct |
|------------------------|---------|
| `client.user_manager` | `client.users` ✅ |
| `client.search_manager` | `client.searches` ✅ |
| `client.peer_manager` | `client.peers` ✅ |
| `client.room_manager` | `client.rooms` ✅ |
| `client.transfer_manager` | `client.transfers` ✅ |
| `client.share_manager` | `client.shares` ✅ |
| `client.interest_manager` | `client.interests` ✅ |
| `client.server_manager` | `client.server_manager` ✅ (seul avec suffixe `_manager`) |

---

## 2. UserManager — `client.users`

**Import :** `from aioslsk.peer import UserManager`

### Méthodes

```python
def get_user_object(self, username: str) -> User     # Récupère ou crée un User
def track_user(self, username: str)                   # Commence à tracker un user
def untrack_user(self, username: str)                 # Arrête de tracker
def is_tracked(self, username: str) -> bool           # Vérifie si un user est tracké
def get_self(self) -> User                            # L'utilisateur courant (notre session)
def is_self(self, username: str) -> bool              # Vérifie si c'est nous-même
```

### Propriétés

```python
users: dict[str, User]   # Tous les utilisateurs trackés (nom → User)
```

---

## 3. Modèle `User`

**Import :** `from aioslsk.user.model import User, UserStatus`

### `UserStatus` (enum)

```python
class UserStatus(IntEnum):
    UNKNOWN = -1
    OFFLINE = 0
    AWAY    = 1
    ONLINE  = 2
```

### `User.__init__`

```python
class User:
    def __init__(
        self,
        name: str,
        status: UserStatus = UserStatus.UNKNOWN,
        privileged: bool = False,
        description: Optional[str] = None,
        picture: Optional[bytes] = None,
        country: Optional[str] = None,
        avg_speed: Optional[int] = None,
        uploads: Optional[int] = None,
        shared_file_count: Optional[int] = None,
        shared_folder_count: Optional[int] = None,
        has_slots_free: Optional[bool] = None,
        slots_free: Optional[int] = None,
        upload_slots: Optional[int] = None,
        queue_length: Optional[int] = None,
        upload_permissions: UploadPermissions = UploadPermissions.UNKNOWN,
        interests: set[str] = <factory>,
        hated_interests: set[str] = <factory>,
    )
```

### Tous les champs accessibles

```python
user.name                # str — nom d'utilisateur
user.status              # UserStatus — ONLINE/AWAY/OFFLINE/UNKNOWN
user.privileged          # bool — utilisateur privilégié ?
user.description         # Optional[str] — description personnelle
user.picture             # Optional[bytes] — avatar
user.country             # Optional[str] — code pays (ex: "FR")
user.avg_speed           # Optional[int] — vitesse moyenne (kbps)
user.uploads             # Optional[int] — nombre d'uploads
user.shared_file_count   # Optional[int] — nombre de fichiers partagés
user.shared_folder_count # Optional[int] — nombre de dossiers partagés
user.has_slots_free      # Optional[bool] — slots libres ?
user.slots_free          # Optional[int] — nombre de slots libres
user.upload_slots        # Optional[int] — nombre total de slots upload
user.queue_length        # Optional[int] — taille de la file d'attente
user.upload_permissions  # UploadPermissions — permissions d'upload
user.interests           # set[str] — centres d'intérêt
user.hated_interests     # set[str] — centres d'intérêt rejetés
```

---

## 4. ServerManager — `client.server_manager`

**Import :** `from aioslsk.server import ServerManager`

### Méthodes

```python
def send_ping(self)                             # Ping le SERVEUR (pas un user)
def load_data(self)
def store_data(self)
def register_listeners(self)
def start(self)
def stop(self) -> list[asyncio.Task]
```

---

## 5. SearchManager — `client.searches`

**Import :** `from aioslsk.search.manager import SearchManager`

### Méthodes

```python
def search(self, query: str) -> SearchRequest                       # Recherche sur tout le réseau
def search_user(self, username: str, query: str) -> SearchRequest   # Recherche chez un user spécifique
def search_room(self, room: str | Room, query: str) -> SearchRequest  # Recherche dans un salon
def remove_request(self, request: SearchRequest | int)              # Annule une recherche
def load_data(self)
def store_data(self)
def register_listeners(self)
def start(self)
def stop(self) -> list[asyncio.Task]
```

### `SearchType` (enum)

```python
class SearchType(IntEnum):
    NETWORK  = 1  # Recherche réseau entier
    USER     = 2  # Recherche chez un user
    ROOM     = 3  # Recherche dans un salon
    WISHLIST = 4  # Wishlist
```

---

## 6. PeerManager — `client.peers`

**Import :** `from aioslsk.peer import PeerManager`

### Méthodes

```python
def load_data(self)
def store_data(self)
def register_listeners(self)
def start(self)
def stop(self) -> list[asyncio.Task]
```

> **Note :** `PeerManager` gère les connexions peers directes (connexions P2P entre clients
> Soulseek). Il n'a pas de méthodes spécifiques pour la fonctionnalité Clients Actifs —
> la découverte et le suivi des utilisateurs se font via `UserManager` (`client.users`)
> et les événements associés.

---

## 7. Modèles de recherche

### `SearchRequest`

**Import :** `from aioslsk.search.model import SearchRequest, SearchResult`

```python
class SearchRequest:
    ticket: int                           # Identifiant unique de la requête
    query: str                            # Terme recherché
    search_type: SearchType               # Type de recherche (NETWORK/USER/ROOM/WISHLIST)
    room: str | None                      # Salon cible (si ROOM)
    username: str | None                  # User cible (si USER)
    results: list[SearchResult]           # Résultats reçus
    started: datetime.datetime            # Horodatage de début
    timer: Timer | None                   # Timer interne
```

### `SearchResult`

```python
class SearchResult:
    ticket: int                           # Ticket de la recherche associée
    username: str                         # Nom de l'utilisateur qui a les fichiers
    has_free_slots: bool                  # Slots libres ?
    avg_speed: int                        # Vitesse moyenne (kbps)
    queue_size: int                       # Taille de la file d'attente
    shared_items: list[FileData]          # Fichiers trouvés
    locked_results: list[FileData]        # Fichiers verrouillés
```

---

## 8. Événements (EventBus)

**Souscription :** `client.events.register(EventClass, callback)`

```python
# Pattern général
self._client.events.register(
    UserStatusUpdateEvent,
    lambda evt: self._on_user_status_changed(evt)
)
```

### Tous les événements disponibles

#### Connexion & Session
| Événement | Signature |
|-----------|-----------|
| `SessionInitializedEvent` | `(session, raw_message: Login.Response)` |
| `SessionDestroyedEvent` | `(session)` |
| `ConnectionStateChangedEvent` | `(connection, state, close_reason=None)` |
| `ServerReconnectedEvent` | `()` |

#### Utilisateurs & Statuts
| Événement | Signature | 🔑 Clé |
|-----------|-----------|:------:|
| **`UserStatusUpdateEvent`** | `(before: User, current: User, raw_message)` | ⭐ |
| **`UserInfoUpdateEvent`** | `(before: User, current: User, raw_message)` | ⭐ |
| **`UserTrackingEvent`** | `(user: User, raw_message)` | ⭐ |
| `UserTrackingFailedEvent` | `(username: str, raw_message)` | |
| `UserTrackingStateChangedEvent` | `(user, state: TrackingState, raw_message=None)` | |
| `UserUntrackingEvent` | `(user: User)` | |
| `UserStatsUpdateEvent` | `(before: User, current: User, raw_message)` | |
| `BlockListChangedEvent` | `(changes: dict[str, tuple[BlockingFlag, BlockingFlag]])` | |
| `FriendListChangedEvent` | `(added: set[str], removed: set[str])` | |

#### Recherche
| Événement | Signature | 🔑 Clé |
|-----------|-----------|:------:|
| **`SearchResultEvent`** | `(query: SearchRequest, result: SearchResult)` | ⭐ |
| `SearchRequestSentEvent` | `(query: SearchRequest)` | |
| `SearchRequestReceivedEvent` | `(username, query, result_count)` | |
| `SearchRequestRemovedEvent` | `(query: SearchRequest)` | |

#### Transferts
| Événement | Signature |
|-----------|-----------|
| `TransferAddedEvent` | `(transfer)` |
| `TransferRemovedEvent` | `(transfer)` |
| `TransferProgressEvent` | `(updates: list[tuple])` |

#### Salons
| Événement | Signature |
|-----------|-----------|
| `RoomJoinedEvent` | `(room, raw_message, user=None)` |
| `RoomLeftEvent` | `(room, raw_message, user=None)` |
| `RoomMessageEvent` | `(message: RoomMessage, raw_message)` |
| `RoomListEvent` | `(rooms: list[Room], raw_message)` |
| `RoomTickersEvent` | `(room, tickers: dict[str, str], raw_message)` |
| `RoomMembersEvent` | `(room, members: list[User], raw_message)` |
| `RoomOperatorsEvent` | `(room, operators: list[User], raw_message)` |

#### Messages privés
| Événement | Signature |
|-----------|-----------|
| `PrivateMessageEvent` | `(message: ChatMessage, raw_message)` |
| `PublicMessageEvent` | `(timestamp, user, room, message, raw_message)` |
| `AdminMessageEvent` | `(message, raw_message)` |

#### Autres
| Événement | Signature |
|-----------|-----------|
| `KickedEvent` | `(raw_message)` |
| `PrivilegesUpdateEvent` | `(time_left: int, raw_message)` |
| `PeerInitializedEvent` | `(connection, requested: bool)` |
| `ScanCompleteEvent` | `(folder_count, file_count)` |
| `UserDirectoryEvent` | `(user, directory, directories, raw_message)` |
| `UserSharesReplyEvent` | `(user, directories, locked_directories, raw_message)` |

---

## 9. Événements clés détaillés

### `UserStatusUpdateEvent` ⭐

Déclenché quand le statut ONLINE/AWAY/OFFLINE d'un utilisateur **tracké** change.

```python
@dataclass
class UserStatusUpdateEvent:
    before: User          # État avant le changement
    current: User         # État après le changement
    raw_message           # Message brut du protocole (GetUserStatus.Response)
```

**Usage typique :**
```python
def _on_user_status_changed(self, evt: UserStatusUpdateEvent):
    username = evt.current.name
    new_status = evt.current.status  # UserStatus.ONLINE / AWAY / OFFLINE
    old_status = evt.before.status
```

### `UserInfoUpdateEvent` ⭐

Déclenché quand les informations détaillées d'un utilisateur changent (pays, vitesse, fichiers, slots...).

```python
@dataclass
class UserInfoUpdateEvent:
    before: User          # État avant
    current: User         # État après
    raw_message           # Message brut (PeerUserInfoReply.Request)
```

### `UserTrackingEvent` ⭐

Déclenché quand un utilisateur commence à être tracké.

```python
@dataclass
class UserTrackingEvent:
    user: User            # L'utilisateur qui est maintenant tracké
    raw_message           # Message brut (AddUser.Response)
```

### `SearchResultEvent` ⭐

Déclenché pour chaque résultat d'une recherche.

```python
@dataclass
class SearchResultEvent:
    query: SearchRequest   # La requête de recherche associée
    result: SearchResult   # Le résultat (username, fichiers, vitesse...)
```

---

## 10. Pattern d'injection existant

Le service existant `SoulseekService` expose le client via `self._client` :

```python
class SoulseekService(QObject, ABC):
    def __init__(self):
        self._client: SoulSeekClient | None = None

    # Accès aux managers :
    self._client.users                    # UserManager
    self._client.users.users              # dict[str, User] — utilisateurs trackés
    self._client.searches                 # SearchManager
    self._client.searches.search_user(username, query)
    self._client.server_manager           # ServerManager
    self._client.server_manager.send_ping()

    # Souscription aux événements :
    self._client.events.register(
        UserStatusUpdateEvent,
        lambda evt: self._handler(evt)
    )
```

> **Note :** Dans la spec `bot-clients-actifs-spec.md`, on utilise le pattern
> `soulseek_service.client.users` (propriété qui retourne `self._client`).

---

## Annexe : Résumé des noms d'attributs

| Classe | Attribut sur `SoulSeekClient` |
|--------|------------------------------|
| `UserManager` | `client.users` |
| `SearchManager` | `client.searches` |
| `ServerManager` | `client.server_manager` |
| `PeerManager` | `client.peers` |
| `RoomManager` | `client.rooms` |
| `TransferManager` | `client.transfers` |
| `SharesManager` | `client.shares` |
| `InterestManager` | `client.interests` |
| `Network` | `client.network` |
| `DistributedNetwork` | `client.distributed_network` |
| `EventBus` | `client.events` |
