---
title: "Service clients actifs (ClientsActifsService)"
category: technique
icon: 👥
keywords:
  - ClientsActifsService
  - clients actifs service
  - clients_actifs_service.py
  - ClientInfo dataclass
  - client info dataclass
  - suivi client soulseek
  - client connecte liste
  - client connecté liste
  - client en ligne statut
  - synchronisation client soulseek
  - UserManager client soulseek
  - UserStatusUpdateEvent
  - UserInfoUpdateEvent
  - _on_user_status_update
  - _on_user_info_update
  - demarrer service client
  - arreter service client
  - arrêter service client
  - rafraichir liste client
  - rafraîchir liste client
  - clients_actifs methode
  - clients tries tri
  - clients triés tri
  - client tri username
  - client tri statut
  - client tri vitesse
  - client tri fichier
  - client tri slot
  - client tri file attente
  - obtenir_client
  - nombre_actifs en ligne
  - nombre_connectes
  - client ajoute signal
  - client ajouté signal
  - client retire signal
  - client retiré signal
  - client statut change signal
  - client statut changé signal
  - client info change signal
  - clients synchronises signal
  - clients synchronisés signal
  - signal client mis a jour
  - signal client mis à jour
  - service client qobject
  - etat client soulseek
  - état client soulseek
  - statut client online away unknown
  - pays client vitesse
  - partage client statistique
  - slot client file attente
  - slot client file d'attente
  - privilege client soulseek
  - description client
  - bot clients actifs backend
  - surveillance utilisateur
---

# 👥 Service clients actifs (ClientsActifsService)

## Introduction

Le module `src/services/clients_actifs_service.py` (259 lignes) gère le suivi des **utilisateurs Soulseek** que vous avez contactés ou qui vous ont contacté. Il consolide les données brutes de la bibliothèque `aioslsk` (`UserManager`) et expose des signaux Qt pour l'interface graphique.

---

## Architecture

```
aioslsk UserManager
      │
      ├── UserStatusUpdateEvent  ──────►  _on_user_status_update()
      ├── UserInfoUpdateEvent   ──────►  _on_user_info_update()
      │
      ▼
┌──────────────────────────────────┐
│       ClientsActifsService       │
│                                  │
│  self._clients: dict[str,       │
│                   ClientInfo]    │
│                                  │
│  ┌─ signaux ──────────────────┐  │
│  │ client_ajoute              │  │
│  │ client_retire              │  │
│  │ client_statut_change       │  │
│  │ client_info_change         │  │
│  │ clients_synchronises       │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
      │
      ▼
    Bot Clients Actifs (UI)
```

---

## Dataclass `ClientInfo`

```python
@dataclass
class ClientInfo:
    username: str
    statut: str           # ONLINE, AWAY, UNKNOWN
    pays: str
    vitesse: int          # vitesse moyenne (octets/s)
    fichiers: int         # nombre de fichiers partagés
    dossiers: int         # nombre de dossiers partagés
    slots: int            # slots libres / total
    file: int             # position dans la file d'attente
    privileges: bool      # utilisateur privilégié ?
    description: str      # description personnelle
```

Consolide les informations d'un utilisateur Soulseek en une structure unique.

---

## Classe `ClientsActifsService(QObject)`

### Gestion du cycle de vie

#### `demarrer()`

```python
def demarrer(self) -> None:
    self._synchroniser()
    self._event_bus.enregistrer(UserStatusUpdateEvent, self._on_user_status_update)
    self._event_bus.enregistrer(UserInfoUpdateEvent, self._on_user_info_update)
```

1. **Synchronisation initiale** : importe l'état actuel depuis le `UserManager` d'aioslsk
2. **Enregistrement des écouteurs** : deux événements `aioslsk` sont écoutés

#### `arreter()`

```python
def arreter(self) -> None:
    self._clients.clear()
    self.clients_synchronises.emit()
```

Vide la liste et émet un signal pour que l'UI se mette à jour.

#### `rafraichir()`

```python
def rafraichir(self) -> None:
    self._synchroniser()
```

Force une re-synchronisation manuelle depuis `UserManager`.

### Accès aux données

#### `clients_actifs()`

```python
@property
def clients_actifs(self) -> list[ClientInfo]:
    return sorted(
        [c for c in self._clients.values() if c.statut != "UNKNOWN"],
        key=lambda c: c.username.lower()
    )
```

Retourne les clients avec un statut connu (exclut `UNKNOWN`), triés par nom.

#### `clients_tries(cle, ordre_inverse)`

```python
def clients_tries(self, cle="username", ordre_inverse=False) -> list[ClientInfo]:
    clients = self.clients_actifs
    return sorted(clients, key=lambda c: getattr(c, cle, ""), reverse=ordre_inverse)
```

Permet de trier les clients actifs selon différentes clés :

| Clé | Description | Exemple |
|-----|-------------|---------|
| `username` | Nom d'utilisateur (ordre alphabétique) | `alice`, `bob` |
| `statut` | Statut de connexion | `ONLINE`, `AWAY` |
| `vitesse` | Vitesse moyenne (décroissant) | 50000, 12000 |
| `fichiers` | Nombre de fichiers partagés | 1500, 230 |
| `slots` | Slots libres | 5, 2 |
| `file` | Position dans la file d'attente | 0, 3 |

#### `obtenir_client(username)`

```python
def obtenir_client(self, username: str) -> ClientInfo | None:
    return self._clients.get(username)
```

Recherche un client par son nom d'utilisateur.

#### `nombre_actifs()` / `nombre_connectes()`

```python
@property
def nombre_actifs(self) -> int:
    """Clients ONLINE ou AWAY."""
    return sum(1 for c in self._clients.values() if c.statut in ("ONLINE", "AWAY"))

@property
def nombre_connectes(self) -> int:
    """Clients strictement ONLINE."""
    return sum(1 for c in self._clients.values() if c.statut == "ONLINE")
```

Deux métriques distinctes :
- **Actifs** : en ligne ou absent (`ONLINE` + `AWAY`)
- **Connectés** : strictement en ligne (`ONLINE`)

### Synchronisation avec Soulseek

#### `_synchroniser()`

```python
def _synchroniser(self) -> None:
    self._clients.clear()
    user_manager = self._connexion_manager.soulseek_client.user_manager
    for username, data in user_manager.users.items():
        self._clients[username] = ClientInfo(
            username=username,
            statut=data.status.name if data.status else "UNKNOWN",
            pays=data.country or "",
            vitesse=data.speed or 0,
            fichiers=data.files or 0,
            dossiers=data.dirs or 0,
            slots=data.slots_free or 0,
            file=data.queue_position or 0,
            privileges=data.has_privileges or False,
            description=data.description or "",
        )
    self.clients_synchronises.emit()
```

Importe l'intégralité de l'état depuis le `UserManager` d'aioslsk et émet `clients_synchronises`.

### Écouteurs d'événements

#### `_on_user_status_update(event)`

```python
def _on_user_status_update(self, event: UserStatusUpdateEvent) -> None:
    if event.username in self._clients:
        self._clients[event.username].statut = event.status.name
        self.client_statut_change.emit(event.username, event.status.name)
    elif event.status != UserStatus.UNKNOWN:
        # Nouveau client découvert
        self._synchroniser()
```

- **Client existant** : met à jour le statut et émet `client_statut_change`
- **Nouveau client** (statut connu) : déclenche une re-synchronisation complète
- **Client inconnu** (statut UNKNOWN) : ignoré

#### `_on_user_info_update(event)`

```python
def _on_user_info_update(self, event: UserInfoUpdateEvent) -> None:
    if event.username in self._clients:
        client = self._clients[event.username]
        client.pays = event.user_info.country or client.pays
        client.vitesse = event.user_info.speed or client.vitesse
        client.fichiers = event.user_info.files or client.fichiers
        client.dossiers = event.user_info.dirs or client.dossiers
        client.slots = event.user_info.slots_free or client.slots
        client.file = event.user_info.queue_position or client.file
        client.privileges = event.user_info.has_privileges or client.privileges
        client.description = event.user_info.description or client.description
        self.client_info_change.emit(event.username)
```

Met à jour les informations détaillées d'un client existant (vitesse, partage, slots, file, description, privilèges).

### Signaux

| Signal | Arguments | Déclencheur |
|--------|-----------|-------------|
| `clients_synchronises` | — | Synchronisation complète terminée (`_synchroniser()`) |
| `client_statut_change` | `str username, str statut` | Changement de statut via `_on_user_status_update` |
| `client_info_change` | `str username` | Mise à jour des infos via `_on_user_info_update` |
| `client_ajoute` | `str username` | Nouveau client découvert (via diff dans `_synchroniser`) |
| `client_retire` | `str username` | Client disparu (via diff dans `_synchroniser`) |

> **Note** : Les signaux `client_ajoute` et `client_retire` sont émis lors du diff dans `_synchroniser()` entre l'ancienne et la nouvelle liste. Le signal principal est `clients_synchronises` qui indique une mise à jour complète.

---

## Cycle de vie complet

```
Démarrage
   │
   ▼
demarrer()
   ├── _synchroniser() → importe tous les clients depuis UserManager
   │                     → émet clients_synchronises
   │
   └── Enregistre écouteurs :
       ├── UserStatusUpdateEvent → _on_user_status_update
       └── UserInfoUpdateEvent  → _on_user_info_update
   │
   ▼
Temps réel
   ├── Changement statut → client_statut_change(username, statut)
   ├── Infos mises à jour → client_info_change(username)
   └── Rafraîchir manuel → rafraichir() → _synchroniser()
   │
   ▼
Arrêt
   │
   ▼
arreter()
   ├── Vide self._clients
   └── Émet clients_synchronises (liste vide → UI se met à jour)
```

---

## Conclusion

| Aspect | Détail |
|--------|--------|
| **Rôle** | Pont entre `UserManager` d'aioslsk et l'UI — consolide les données utilisateur |
| **Données** | `ClientInfo` : statut, pays, vitesse, fichiers, slots, file, privilèges, description |
| **Synchronisation** | Import complet au démarrage, mise à jour incrémentale via événements |
| **Signaux** | 5 signaux Qt pour l'UI : ajout, retrait, statut, info, synchronisation |
| **Tri** | 6 clés de tri : username, statut, vitesse, fichiers, slots, file |
| **Métriques** | `nombre_actifs` (ONLINE+AWAY) vs `nombre_connectes` (ONLINE strict) |
