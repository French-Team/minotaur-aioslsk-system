# Spécification — Bot Clients Actifs

> **Statut :** 🟡 En attente de validation avant implémentation
> **Dernière mise à jour :** 2025-06-10
> **Contexte :** Remplace le bouton "Statistiques" dans le footer. Nouveau bot qui liste les clients actifs & joignables du réseau Soulseek, et devient la source exclusive des recherches et téléchargements.
> **Renommage :** `bot_utilisateur` → `bot_optimiseur.py` (déjà fait). `Statistiques` → `Clients Actifs` (footer + centre).

---

## 1. 🎯 Objectifs

- **Lister** les clients actifs et joignables sur le réseau Soulseek
- **Tracker** les clients connectés via le réseau Soulseek (statut ONLINE/AWAY/OFFLINE)
- **Devenir la source** unique pour les recherches (bot_recherche) et les téléchargements (bot_telechargement)
- **Éviter** les files d'attente interminables sur des clients déconnectés
- **Rafraîchir** périodiquement la liste pour rester à jour

---

## 2. 🔄 Navigation & Renommage

### 2.1 Footer

| Fichier | Changement |
|---------|-----------|
| `src/gui/layout/footer.py` (L.76) | `"Statistiques"` → `"Clients Actifs"` dans `_BOT_NAMES` |

### 2.2 Centre

| Fichier | Changement |
|---------|-----------|
| `src/gui/layout/center.py` (L.102) | `"Statistiques"` → `"Clients Actifs"` dans la liste de navigation |
| `src/gui/layout/center.py` (L.22) | Remplacer import `ClientsActifsPage` → `ClientsActifsHeader` + `BotClientsActifs` |
| `src/gui/layout/center.py` (L.90) | Renommer `_build_clients_actifs_page()` → `_build_clients_actifs_header_page()` |
| `src/gui/layout/center.py` (L.228) | Renommer getter `clients_actifs_page()` → `clients_actifs_header_page()` |
| `src/gui/layout/center.py` | Ajouter `_build_clients_actifs_bot_page()` + import `BotClientsActifs` |

### 2.3 Bot Accueil

| Fichier | Changement |
|---------|-----------|
| `src/gui/widgets/bots/bot_accueil.py` | Remplacer ref "Statistiques" → "Clients Actifs" |
| `src/gui/widgets/bots/bot_accueil_knowledge.py` | Remplacer refs "Statistiques" → "Clients Actifs" (L.217, 221, 300, 341, 344) |

### 2.4 ⚠️ Plan de migration — conflit de noms dans `center.py`

**Problème :** La méthode `_build_clients_actifs_page()` existe déjà (L.239) et crée `ClientsActifsPage` (le widget header actuel, 294 lignes).
Le nouveau bot `BotClientsActifs` (~600 lignes) sera créé par une NOUVELLE méthode `_build_clients_actifs_bot_page()`.

**Plan de migration :**

| Méthode existante | Rôle actuel | Devient |
|---|---|---|
| `_build_clients_actifs_page()` | Crée `ClientsActifsPage` (header) | `_build_clients_actifs_header_page()` → crée `ClientsActifsHeader` |
| `clients_actifs_page()` (getter, L.228) | Retourne la page header | `clients_actifs_header_page()` |
| *(nouvelle)* | — | `_build_clients_actifs_bot_page()` → crée `BotClientsActifs` |
| *(nouveau getter)* | — | `clients_actifs_bot_page()` → retourne `BotClientsActifs` |

**Ordre :** 1) Renommer l'ancienne méthode/getter 2) Ajouter la nouvelle méthode 3) Mettre à jour les appels.

---

## 3. 🧱 Architecture

```
src/gui/widgets/bots/
└── bot_clients_actifs.py    # NOUVEAU — ~600 lignes estimé

src/services/
└── clients_actifs_service.py # NOUVEAU — ~300 lignes estimé

src/gui/widgets/
├── clients_actifs.py         # EXISTANT — widget header (294 lignes, à renommer + déplacer)
└── header/
    └── clients_actifs_header.py  # APRÈS RENOMMAGE — widget header dédié

src/gui/layout/
├── footer.py                 # MODIFIÉ — "Statistiques" → "Clients Actifs"
└── center.py                 # MODIFIÉ — nouvelle page bot

tests/
├── test_clients_actifs_service.py  # NOUVEAU — tests backend
├── test_bot_clients_actifs.py      # NOUVEAU — tests UI
└── test_clients_actifs_integration.py  # NOUVEAU — tests intégration (voir §8)

> 📁 **Note :** Le dossier `src/gui/widgets/header/` n'existe pas encore.
> Créer le dossier + `__init__.py` + mettre à jour les imports dans `center.py`.
```

---

## 4. 📡 Backend — `clients_actifs_service.py`

### 4.1 Responsabilités

- Interface avec `aioslsk` (`UserManager`) pour récupérer les utilisateurs trackés
- Écoute des events `UserStatusUpdateEvent` / `UserInfoUpdateEvent` pour mises à jour temps réel
- Maintien d'une liste en mémoire des clients actifs + leurs métadonnées
- Exposition de la liste via signaux `QObject`/callbacks pour le GUI

### 4.2 Sources de découverte des clients

| Source | Description | Priorité |
|--------|-------------|----------|
| **Pairs connus** | Clients avec qui on a déjà interagi (réponses recherche, connexions entrantes) | Haute |
| **Users trackés** | `UserManager.users` — utilisateurs déjà connus du réseau, statut reçu via events | Haute |
| **Réponses recherche** | Clients qui répondent à nos recherches broadcast | Haute |
| **Connexions entrantes** | Clients qui se connectent à nous pour télécharger | Moyenne |
| **Liste des files d'attente** | Clients dans notre file d'attente de téléchargement | Moyenne |

> ✅ **API aioslsk vérifiée** (via introspection locale v1.6.3) — voir §4.7 pour les signatures exactes.

### 4.3 Structure de données — `ClientInfo`

> Adapté du modèle `aioslsk.user.model.User` (vérifié sur v1.6.3).
> Les statuts utilisent l'enum `UserStatus` natif (ONLINE=2, AWAY=1, OFFLINE=0, UNKNOWN=-1).

```python
@dataclass
class ClientInfo:
    username: str
    statut: UserStatus            # ONLINE, AWAY, OFFLINE, UNKNOWN (enum natif aioslsk)
    pays: str | None              # Code pays ("FR", "US"...)
    vitesse: int | None           # Vitesse max (kbps) — `avg_speed`
    fichiers_partages: int | None # `shared_file_count`
    dossiers_partages: int | None # `shared_folder_count`
    files_attente: int | None     # `queue_length`
    slots_disponibles: int | None # `slots_free`
    slots_libres: bool            # `has_slots_free`
    description: str | None       # Description utilisateur
    privilegie: bool               # `privileged`
    interets: list[str]           # `interests` + `hated_interests`
```

> **Note :** Les attributs `ip` et `derniere_vue` ne sont pas disponibles nativement.
> `ip` n'est pas exposé par l'API aioslsk (protocole Soulseek).
> `derniere_vue` est géré côté service : timestamp mis à jour à chaque `UserStatusUpdateEvent`
> ou `UserInfoUpdateEvent` reçu pour ce client (voir §4.5).

Les statuts utilisent directement l'enum `UserStatus` d'aioslsk, avec le mapping visuel suivant :

| UserStatus | Valeur | Affichage | Icône | Action |
|------------|--------|-----------|-------|-------|
| `ONLINE` | 2 | **Actif** | 🟢 | Conservé dans la liste |
| `AWAY` | 1 | **Joignable** (absent) | 🟡 | Conservé dans la liste |
| `OFFLINE` | 0 | — | — | Retiré après 2 vérifications |
| `UNKNOWN` | -1 | *(pas affiché)* | ⚪ | Temporaire — masqué tant que statut non reçu |

```python
# aioslsk.user.model.UserStatus (natif)
class UserStatus(IntEnum):
    UNKNOWN = -1
    OFFLINE = 0
    AWAY = 1
    ONLINE = 2
```

### 4.4 API publique du service

> Architecture **event-driven** : pas de polling. Le service s'abonne aux events aioslsk
> (`UserStatusUpdateEvent`, `UserInfoUpdateEvent`) et met à jour sa liste en temps réel.

```python
class ClientsActifsService(QObject):
    # Signaux
    client_ajoute = Signal(ClientInfo)            # Nouveau client tracké découvert
    client_mis_a_jour = Signal(ClientInfo)        # Statut/infos ont changé
    client_supprime = Signal(str)                 # username — client retiré
    rafraichissement_termine = Signal(list)        # list[ClientInfo] — sync complète
    erreur = Signal(str)

    # Méthodes
    def demarrer(self) -> None                    # S'abonne aux events aioslsk + track les users
    def arreter(self) -> None                     # Se désabonne + vide la liste
    def track_user(self, username: str) -> None   # Track un nouvel utilisateur
    def untrack_user(self, username: str) -> None # Arrête de tracker
    def rafraichir(self) -> None                  # Re-synchronise avec UserManager.users
    def clients_actifs(self) -> list[ClientInfo]  # ONLINE seulement
    def clients_joignables(self) -> list[ClientInfo]  # AWAY seulement
    def tous_les_clients(self) -> list[ClientInfo]
```

### 4.5 Mise à jour des clients (event-driven)

Pas de timer de polling. Le mécanisme est entièrement **event-driven** :

1. À la connexion réseau (`demarrer()`) :
   - Récupère la liste actuelle via `client.users.users`
   - S'abonne aux events `UserStatusUpdateEvent`, `UserInfoUpdateEvent`, `UserTrackingEvent`
2. À chaque `UserStatusUpdateEvent` :
   - Compare `before.status` et `current.status`
   - Met à jour le `ClientInfo` correspondant dans la liste interne
   - Émet `client_mis_a_jour` (ou `client_ajoute` si nouveau)
3. À chaque `UserInfoUpdateEvent` :
   - Met à jour les métadonnées (pays, vitesse, fichiers, etc.)
   - Émet `client_mis_a_jour`
4. Quand un user passe OFFLINE :
   - Émet `client_supprime` après 2 cycles de vérification
   - Ou retire immédiatement si `untrack_user()` est appelé
5. Bouton **Rafraîchir** manuel : re-synchronise depuis `UserManager.users`
6. Pas de persistance entre sessions — la liste se reconstruit à chaque connexion

### 4.5.1 🔍 Stratégie de tracking — quels utilisateurs tracker ?

Le service ne peut pas tracker tous les utilisateurs du réseau (des millions). Il suit une stratégie de **découverte progressive** :

| Source | Déclencheur | Tracking appliqué |
|--------|------------|-------------------|
| **Connexions entrantes** | Un pair se connecte à nous (téléchargement) | `track_user(username)` automatique |
| **Réponses recherche** | Un pair répond à notre recherche broadcast | `track_user(username)` automatique sur les nouveaux |
| **Connexions sortantes** | On initie une connexion (recherche ciblée, téléchargement) | `track_user(username)` automatique |
| **File d'attente** | Un pair dans notre file de téléchargement | `track_user(username)` si pas déjà tracké |
| **Friends / Privilégiés** | Liste des amis déclarés dans la config | `track_user(username)` au démarrage |
| **Recherche manuelle** | L'utilisateur tape un nom dans l'UI | `track_user(username)` à la demande |

**Règles de cycle de vie :**
- Un utilisateur tracké reste dans la liste tant qu'il est ONLINE ou AWAY
- Passage OFFLINE → retiré après 2 vérifications (évite le « clignotement »)
- `untrack_user()` est appelé uniquement si l'utilisateur n'est plus référencé par aucune source
- `UserManager.users` sert d'état initial au démarrage (utilisateurs déjà trackés par d'autres parties du code)
- Pas de timer de nettoyage — le retrait est déclenché par les events `UserStatusUpdateEvent`

### 4.6 🚦 Cycle de vie du service

`ClientsActifsService` est un **singleton partagé** (voir §5.6). Son cycle de vie :

```
┌──────────────────────────────────────────────────────────┐
│ Application démarre                                      │
│   ↓                                                      │
│ Connexion au réseau Soulseek établie                     │
│   ↓                                                      │
│ clients_actifs_service.demarrer()  ← appelé auto         │
│   ├─ Récupère UserManager.users (liste initiale)         │
│   ├─ S'abonne aux events aioslsk                         │
│   │  • UserStatusUpdateEvent  ─→ client_mis_a_jour       │
│   │  • UserInfoUpdateEvent    ─→ client_mis_a_jour       │
│   │  • UserTrackingEvent      ─→ client_ajoute/supprime  │
│   └─ Émet rafraichissement_termine(liste initiale)       │
│   ↓                                                      │
│ Navigation vers la page "Clients Actifs"                 │
│   ├─ Bot page visible → reçoit les signaux               │
│   └─ Header visible → reçoit les signaux                 │
│   ↓                                                      │
│ [Events aioslsk en continu toute la session]              │
│   ↓                                                      │
│ Déconnexion du réseau / Fermeture app                    │
│   └─ clients_actifs_service.arreter()  ← appelé auto     │
│      ├─ Se désabonne des events                           │
│      ├─ Vide la liste des clients                        │
│      └─ Émet rafraichissement_termine([])                │
└──────────────────────────────────────────────────────────┘
```

**Scénarios importants :**
| Scénario | Comportement |
|----------|-------------|
| **Page non encore visitée** | Le service tourne en arrière-plan dès la connexion réseau. La page affiche "En attente des données..." le temps de recevoir le premier signal |
| **Navigation hors de la page** | Le service continue d'écouter les events. La page se déconnecte des signaux (`disconnect`). Le header continue d'être mis à jour |
| **Reconnexion au réseau** | `arreter()` → `demarrer()` — la liste est reconstruite via `UserManager.users` |
| **Première synchro en cours** | La page affiche "Récupération de la liste des clients..." avec un indicateur de chargement |
| **Aucun user tracké** | `UserManager.users` vide → la page affiche "Aucun client actif sur le réseau" — les events peupleront la liste au fil du temps |

#### 4.6.1 🔌 Accès au `SoulSeekClient`

`ClientsActifsService` n'est pas indépendant — il a besoin d'accéder au client aioslsk via `SoulseekService` :
- `user_manager` : `track_user()`, `untrack_user()`, `users`, `get_user_object()`
- `events` : `register()` pour s'abonner aux events (`UserStatusUpdateEvent`, etc.)

**Mécanisme d'injection :**

```python
class ClientsActifsService(QObject):
    def __init__(self, soulseek_service: SoulseekService, parent=None):
        super().__init__(parent)
        self._soulseek = soulseek_service  # Le singleton SoulseekService existant

    @property
    def _client(self) -> SoulSeekClient | None:
        return self._soulseek.client  # None si pas connecté

    @property
    def _user_manager(self) -> UserManager | None:
        return self._client.users if self._client else None

    def _register_events(self) -> None:
        if self._client:
            self._client.events.register(
                UserStatusUpdateEvent, self._on_user_status_update
            )
            self._client.events.register(
                UserInfoUpdateEvent, self._on_user_info_update
            )
```

> **Note :** Le pattern `client.events.register(EventClass, handler)` est le même que celui
> déjà utilisé dans `SoulseekService` (lignes 373-412 de `soulseek_client.py`).

### 4.7 ✅ API aioslsk vérifiée (v1.6.3)

> L'API a été vérifiée via introspection du code source de `aioslsk 1.6.3`.
> Aucune méthode n'est hypothétique dans ce tableau.

| Besoin | API aioslsk réelle | Priorité |
|--------|-------------------|----------|
| **Récupérer les utilisateurs trackés** | `client.users.users` → `dict[str, User]` | 🔴 Haute |
| **Tracker un utilisateur** | `client.users.track_user(username, flag?)` | 🔴 Haute |
| **Arrêter de tracker** | `client.users.untrack_user(username)` | 🔴 Haute |
| **Obtenir un objet User** | `client.users.get_user_object(username)` → `User` | 🔴 Haute |
| **Vérifier si tracké** | `client.users.is_tracked(username)` → `bool` | 🟡 Moyenne |
| **Statut utilisateur** | `User.status` (`UserStatus.ONLINE=2`, `AWAY=1`, `OFFLINE=0`) | 🔴 Haute |
| **Infos utilisateur** | `User.country`, `User.avg_speed`, `User.shared_file_count`, etc. | 🔴 Haute |
| **Slots / File** | `User.has_slots_free`, `User.slots_free`, `User.queue_length`, `User.upload_slots` | 🟡 Moyenne |
| **Event statut changé** | `UserStatusUpdateEvent(before, current)` — souscrire via `client.events.register()` | 🔴 Haute |
| **Event infos changées** | `UserInfoUpdateEvent(before, current)` | 🔴 Haute |
| **Event tracking** | `UserTrackingEvent`, `UserTrackingStateChangedEvent` | 🟡 Moyenne |
| **Recherche chez user** | `client.searches.search_user(username, query)` ✅ | 🟡 Moyenne |
| **Ping serveur** | `client.server_manager.send_ping()` — ping le serveur, pas un user | 🟢 Basse |

---

## 5. 🖥️ GUI — `bot_clients_actifs.py`

### 5.1 Classe `BotClientsActifs(QFrame)`

Héritage : `QFrame` (comme tous les autres bots). Environ 600 lignes.

### 5.2 Structure de la page

```
┌─────────────────────────────────────┐
│ Header                              │
│ 🔄 Rafraîchir  |  Statut: connecté  │
│ Clients: 42 actifs · 18 joignables  │
├─────────────────────────────────────┤
│ Tableau triable (QTableWidget)      │
│                                     │
│  Nom    │ Statut  │ Pays │ Vitesse  │
│ ───────┼─────────┼──────┼──────────│
│ User1  │ 🟢 Actif │ FR   │ 1 000 kb │
│ User2  │ 🟡 Joign │ US   │   500 kb │
│ User3  │ 🟢 Actif │ JP   │ 2 000 kb │
│ ...                                 │
├─────────────────────────────────────┤
│ Footer (bas de page)                │
│ Total: 60 clients                   │
└─────────────────────────────────────┘
```

### 5.3 Colonnes du tableau

| Colonne | Type | Triable | Description |
|---------|------|---------|-------------|
| **Nom** | Texte | ✅ | Nom d'utilisateur Soulseek |
| **Statut** | Icône + texte | ✅ | 🟢 Actif / 🟡 Joignable |
| **Pays** | Texte (2 lettres) | ✅ | Code pays (FR, US, JP...) |
| **Vitesse** | Nombre | ✅ | Vitesse max en kb/s |
| **Fichiers** | Nombre | ✅ | Nombre de fichiers partagés |
| **File attente** | Nombre | ✅ | Taille de la file d'attente |
| **Slots** | Nombre | ✅ | Slots disponibles / total |
| **Dernière vue** | Date relative | ✅ | "Il y a 2 min" |

### 5.4 Interactions

| Action | Comportement |
|--------|-------------|
| **Clic sur ligne** | Sélectionne le client |
| **Double-clic** | Ouvre le profil/explorateur du client (action future) |
| **Clic droit** | Menu contextuel : Rechercher fichiers, Voir file attente |
| **Bouton Rafraîchir** | Re-synchronise depuis `UserManager.users` (synchro manuelle) |
| **Tri** | Clic sur en-tête de colonne pour trier |

### 5.5 Intégration header

Le widget existant `ClientsActifsPage` (`src/gui/widgets/clients_actifs.py`) :
- **Renommé** en `ClientsActifsHeader` et **déplacé** vers `src/gui/widgets/header/clients_actifs_header.py`
- **Créer** le dossier `src/gui/widgets/header/` si inexistant + fichier `__init__.py`
- Le header affiche un résumé : **3-5 clients actifs récents** (pas la liste complète) + compteur "N actifs · M joignables"
- Pas de tableau complet — réservé au bot page
- Reçoit les mises à jour via `ClientsActifsService` (l'instance partagée — voir §5.6)

### 5.6 🔄 Service partagé — singleton injecté

**Règle :** `ClientsActifsService` est un **singleton**. Le header ET le bot page utilisent la MÊME instance.
Évite les tracks en double et garantit la cohérence des données.

**Mécanisme :** Injection via constructeur — le `CenterZone` (ou un autre orchestrateur) crée l'instance unique et l'injecte aux deux widgets. Pas de création dans `__init__` des widgets.

```python
# ── Dans CenterZone (orchestrateur) ──
class CenterZone:
    def __init__(self):
        self._clients_service = ClientsActifsService()
        # Lance le service dès la connexion réseau
        # ...

    def _build_clients_actifs_header_page(self):
        page = ClientsActifsHeader(self._clients_service)
        # ...

    def _build_clients_actifs_bot_page(self):
        page = BotClientsActifs(self._clients_service)
        # ...

# ── Dans BotClientsActifs ──
class BotClientsActifs(QFrame):
    def __init__(self, service: ClientsActifsService, ...):
        super().__init__(...)
        self._service = service
        self._service.rafraichissement_termine.connect(self._mettre_a_jour_tableau)
        self._service.client_ajoute.connect(self._ajouter_ligne)
        self._service.client_mis_a_jour.connect(self._mettre_a_jour_ligne)
        self._service.client_supprime.connect(self._supprimer_ligne)
        # Au cas où la page est créée après le premier cycle
        derniere_liste = self._service.tous_les_clients()
        if derniere_liste:
            self._mettre_a_jour_tableau(derniere_liste)

# ── Dans ClientsActifsHeader ──
class ClientsActifsHeader(QFrame):
    def __init__(self, service: ClientsActifsService, ...):
        super().__init__(...)
        self._service = service
        self._service.rafraichissement_termine.connect(self._mettre_a_jour_compteur)
        self._service.client_ajoute.connect(self._incrementer_compteur)
        self._service.client_supprime.connect(self._decrementer_compteur)
        # Restaurer l'état actuel
        clients = self._service.tous_les_clients()
        self._mettre_a_jour_compteur(clients)
```

---

## 6. 🔗 Intégration avec les autres bots

### 6.1 Bot Recherche (MODIFIÉ)

- `bot_recherche.py` : modifié pour utiliser la liste des clients actifs comme cible
- Au lieu de broadcast sur le réseau Soulseek entier, la recherche cible les clients de `ClientsActifsService`
- Conservation d'une option de fallback "Réseau entier" si nécessaire

**Logique :**
```python
# Avant : recherche broadcast
self._soulseek.search(query)

# Après : recherche ciblée sur clients actifs
clients = self._clients_service.clients_actifs()
for client in clients:
    # Utiliser le SearchManager d'aioslsk
    # client.searches.search_user(username, query)  # ✅ API vérifiée
    pass
```

### 6.2 Bot Téléchargement (MODIFIÉ)

- `bot_telechargement.py` : modifié pour prioriser les téléchargements vers les clients actifs
- Sélection automatique du meilleur client (vitesse + file d'attente courte)
- Éviter les files d'attente > 0 quand possible

**Logique de sélection :**
```python
def meilleur_client(self, fichier: str) -> str | None:
    clients = self._clients_service.clients_actifs()
    # Trier par : actif > joignable, puis vitesse, puis file d'attente
    return sorted(clients, key=lambda c: (
        c.statut == ClientStatut.ACTIF,
        c.vitesse or 0,
        -(c.files_attente or 999)
    ))[0].username if clients else None
```

### 6.3 📜 Specs à mettre à jour

Les modifications de `bot_recherche.py` et `bot_telechargement.py` nécessitent aussi une mise à jour de leurs specs respectives :

| Spec | Changement |
|------|-----------|
| `specs/bot-recherche-spec.md` | Ajouter la section "Ciblage clients actifs" : nouveau flux de recherche (au lieu de broadcast réseau), option fallback "Réseau entier", interaction avec `ClientsActifsService` |
| `specs/bot-telechargement-spec.md` | Ajouter la section "Priorisation clients actifs" : logique de sélection du meilleur client, comportement si aucun client actif disponible, interaction avec `ClientsActifsService` |

> **À faire** : Mettre à jour ces deux specs AVANT ou EN MÊME TEMPS que l'implémentation des tâches §9 #5 et #6.

---

## 7. ⚠️ Edge Cases & Contraintes

| Cas | Comportement attendu |
|-----|---------------------|
| **Aucun client actif** | Tableau vide, message "Aucun client actif sur le réseau" |
| **Client passe OFFLINE** | Retiré de la liste après 2 vérifications via `UserStatusUpdateEvent` |
| **Client redevient actif** | Réapparaît dans la liste |
| **Réseau déconnecté** | Liste vidée, message "Non connecté au réseau Soulseek" |
| **Status inconnu prolongé** | `User.status` reste UNKNOWN → retiré après délai |
| **Beaucoup de clients** | Tableau scrollable, pas de limite haute |
| **Beaucoup de clients trackés** | Pas de limite technique — `UserManager` gère le tracking nativement |

---

## 8. 🧪 Couverture de tests attendue

### 8.1 Tests backend — `test_clients_actifs_service.py` (~15 tests)

| Test | Description |
|------|-------------|
| `test_demarrage_arret` | Service démarre/arrête sans erreur |
| `test_rafraichir_liste_vide` | Rafraîchir sans clients connus → liste vide |
| `test_ajout_client` | Ajout d'un client émet le bon signal |
| `test_mise_a_jour_statut` | Event UserStatusUpdateEvent → ONLINE → ACTIF, OFFLINE → retiré |
| `test_clients_actifs_filtre` | `clients_actifs()` retourne uniquement les ACTIFS |
| `test_clients_joignables_filtre` | `clients_joignables()` retourne uniquement les JOIGNABLES |
| `test_statut_devient_offline` | Event UserStatusUpdateEvent → OFFLINE → retiré après 2 vérifications |
| `test_connexion_perdue` | Déconnexion réseau → tous les clients retirés |
| `test_synchro_utilisateurs` | `UserManager.users` → synchronisation initiale des clients |
| `test_pas_de_doublons` | Même utilisateur tracké 2x → pas de doublon dans la liste |

### 8.2 Tests UI — `test_bot_clients_actifs.py` (~10 tests)

| Test | Description |
|------|-------------|
| `test_creation_page` | Bot se crée sans erreur, tableau vide |
| `test_ajout_ligne_tableau` | Ajout d'un client → ligne visible dans le tableau |
| `test_mise_a_jour_ligne` | Mise à jour statut → cellule modifiée |
| `test_suppression_ligne` | Suppression client → ligne retirée |
| `test_tri_colonne` | Clic sur en-tête trie correctement |
| `test_bouton_rafraichir` | Clic sur Rafraîchir → appelle `service.rafraichir()` |
| `test_message_liste_vide` | Aucun client → message visible |
| `test_message_non_connecte` | Pas de connexion réseau → message approprié |

### 8.3 🔗 Tests d'intégration — `test_clients_actifs_integration.py` (~8 tests)

| Test | Description |
|------|-------------|
| `test_service_header_sync` | Ajout via service → header reçoit le signal et met à jour le compteur |
| `test_service_bot_sync` | Ajout via service → bot page reçoit le signal et ajoute la ligne |
| `test_service_partage` | Vérifie que header et bot page utilisent la **même instance** du service (singleton) |
| `test_recherche_clients_actifs` | `bot_recherche` utilise la liste des clients actifs pour cibler ses recherches |
| `test_telechargement_priorite` | `bot_telechargement` sélectionne le meilleur client (actif > joignable > vitesse) |
| `test_recherche_fallback` | Fallback "Réseau entier" fonctionne si `clients_actifs()` est vide |
| `test_client_devient_inactif_pendant_recherche` | Client actif devient joignable pendant une recherche → les résultats sont filtrés |
| `test_cycle_complet` | Track → event statut → ajout client → recherche → téléchargement → priorisation (parcours utilisateur complet) |

---

## 9. 📋 Ordre d'implémentation proposé

| # | Tâche | Fichiers | Estimation |
|---|-------|----------|-----------|
| 0 | **Créer dossier `src/gui/widgets/header/`** + `__init__.py` | nouveau dossier | ~5 min |
| 1 | Renommer "Statistiques" → "Clients Actifs" dans footer + centre + accueil | `footer.py`, `center.py`, `bot_accueil.py`, `bot_accueil_knowledge.py` | ~15 min |
| 1b | **Mettre à jour les specs impactées** (recherche + téléchargement) | `bot-recherche-spec.md`, `bot-telechargement-spec.md` | ~15 min |
| 2 | Renommer `_build_clients_actifs_page()` → `_build_clients_actifs_header_page()` + getter | `center.py` | ~10 min |
| 3 | Créer `ClientsActifsService` — backend event-driven + gestion liste (singleton) | `clients_actifs_service.py` | ~2 h |
| 4 | Créer `BotClientsActifs` — page tableau triable (reçoit service injecté) | `bot_clients_actifs.py` | ~2 h |
| 5 | Renommer/déplacer `ClientsActifsPage` → `ClientsActifsHeader` dans `header/` | `clients_actifs.py` → `header/clients_actifs_header.py` | ~30 min |
| 6 | Modifier `bot_recherche.py` pour cibler clients actifs | `bot_recherche.py` | ~1 h |
| 7 | Modifier `bot_telechargement.py` pour priorisation | `bot_telechargement.py` | ~1 h |
| 8 | Tests backend — service de clients actifs | `test_clients_actifs_service.py` | ~1 h |
| 9 | Tests UI — bot clients actifs | `test_bot_clients_actifs.py` | ~1 h |
| 10 | Tests intégration — cycle complet | `test_clients_actifs_integration.py` | ~1 h |

---

## 10. ❓ Questions résolues

### Architecture et composants

- [x] **Page existante `ClientsActifsPage`** : Conserver, renommer, déplacer vers le header
- [x] **Singleton service** : Oui — instance unique injectée dans header + bot page
- [x] **Compteur header** : Oui, via widget `ClientsActifsHeader` (ex-`ClientsActifsPage`)
- [x] **Conflit center.py** : Renommer `_build_clients_actifs_page()` → `_build_clients_actifs_header_page()` + ajouter `_build_clients_actifs_bot_page()`
- [x] **Dossier header** : Créer `src/gui/widgets/header/` + `__init__.py`

### UI et affichage

- [x] **Statuts affichés** : Actif + Joignable seulement
- [x] **Badge footer** : Non (comme l'Accueil et la Bibliothèque — compteur dans le header à la place)

### Backend et cycle de vie

- [x] **Source des clients** : aioslsk — `UserManager.users` + events `UserStatusUpdateEvent` / `UserInfoUpdateEvent`
- [x] **Persistance** : Non — liste reconstruite à chaque connexion
- [x] **Rafraîchissement** : Event-driven (temps réel) + bouton Rafraîchir manuel
- [x] **Démarrage service** : Automatique à la connexion réseau, arrêt à la déconnexion
- [x] **API aioslsk vérifiée** : `UserManager.track_user/untrack_user/users`, `UserStatus` enum (ONLINE/AWAY/OFFLINE), events — pas de `ping_user()` ni `list_peers()`

### Intégration inter-bots

- [x] **Intégration recherche** : Modifier `bot_recherche.py` pour cibler clients actifs
- [x] **Intégration téléchargement** : Priorisation automatique (vitesse + file)
- [x] **Specs impactées** : Mettre à jour `bot-recherche-spec.md` et `bot-telechargement-spec.md`

---

> *Spec v1.1 — En attente de validation avant implémentation.*
