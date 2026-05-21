# Boucle Clients Actifs — Spécification mise à jour

> **Statut :** ✅ Implémentation complète — toutes les fonctionnalités en place
> **Dernière mise à jour :** 2026-05-21
> **Contexte :** Pipeline de découverte, validation et affichage des clients actifs & joignables sur le réseau Soulseek.

---

## 1. 🎯 Objectif

Pipeline capable de découvrir, valider et filtrer les clients Soulseek qui sont **véritablement actifs et joignables** :

1. **Récupérer** les rooms publiques (via BoucleRooms)
2. **Rejoindre** le top 5 des rooms (les plus peuplées)
3. **Collecter** les membres de ces rooms
4. **Pinger** ces membres par lots (10 clients / 2s) pour vérifier leur disponibilité
5. **Filtrer** pour ne garder que les clients répondant au ping **ET** ayant le statut ONLINE
6. **Afficher** la liste filtrée dans BotClientsActifs

---

## 2. 🧱 Architecture du pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ BoucleRooms (cycle 30s, indépendant)                        │
│  1. Lister les rooms publiques                               │
│  2. Rejoindre le top 5 (par nb membres)                      │
│  3. Récupérer les membres → émet membres_actualises ────┐   │
└─────────────────────────────────────────────────────────┘   │
                                                              │
                   ┌───────────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ ClientsActifsService.ingest_membres_rooms(membres)           │
│  1. Ajouter les nouveaux membres à _clients                  │
│  2. Vérifier les gardes (espacement + dirty)                 │
│  3. Déclencher lancer_ping() si conditions remplies ────┐   │
└───────────────────────────────────────────────────────────┘ │
                                                              ▼
┌─────────────────────────────────────────────────────────────┐
│ _ping_par_lots(membres) : async [rate limité]                │
│  1. Découper en lots de 10 clients                           │
│  2. Pour chaque lot :                                        │
│     a. GetUserStatusCommand pour chaque client               │
│     b. Collecter les réponses (timeout explicite ou exception)│
│     c. Attendre 2s avant le prochain lot                     │
│  3. Émettre ping_termine(liste des réponses)                 │
└─────────────────────────────────────────────────────────────┘
                                                              ▼
┌─────────────────────────────────────────────────────────────┐
│ _on_ping_termine(reponses) [connecté dans __init__]          │
│  1. Filtrer : username in reponses AND statut == ONLINE      │
│  2. Émettre clients_valides(list[ClientInfo]) filtrée        │
└─────────────────────────────────────────────────────────────┘
                                                              ▼
┌─────────────────────────────────────────────────────────────┐
│ BotClientsActifs._on_clients_valides(clients)                │
│  1. Mettre à jour _actifs_joignables                         │
│  2. Mettre à jour le timestamp _last_update_time             │
│  3. Ré-afficher état 🟢 Prêt                                 │
│  4. Réactiver le bouton 🔄 Rafraîchir                        │
│  5. Reconstruire le tableau avec la liste filtrée            │
└─────────────────────────────────────────────────────────────┘
```

### Déclenchement

```
Démarrage (demarrer())
    │
    ├─► BoucleRooms démarre (cycle 30s)
    │   └─► membres_actualises → ingest_membres_rooms → ping → filtrage → affichage
    │
    └─► Attente (pas de timer périodique propre au ping)

Bouton 🔄 Rafraîchir (widget)
    │
    └─► rafraichir_demande → BoucleRooms.rafraichir() → cycle complet → ping → filtrage

Intention "rafraîchir clients actifs" (Accueil)
    │
    └─► start_loop Rooms + start_loop Clients Actifs + navigate
```

---

## 3. 📡 Composants & signaux

### 3.1 ClientsActifsService (`src/services/clients_actifs_service.py`)

**Signaux émis :**

| Signal | Type | Payload | Émis par |
|--------|------|---------|----------|
| `client_ajoute` | `Signal(str)` | username | `ingest_membres_rooms()`, `_on_user_status_update()` |
| `client_retire` | `Signal(str)` | username | méthodes externes |
| `client_statut_change` | `Signal(str, object, object)` | username, nouveau, ancien | `_on_user_status_update()` |
| `client_info_change` | `Signal(str)` | username | `_on_user_info_update()` |
| `clients_synchronises` | `Signal(list)` | `list[ClientInfo]` | `_synchroniser()`, `ingest_membres_rooms()` |
| `ping_termine` | `Signal(list)` | `list[str]` (usernames) | `_ping_par_lots()` (fin du ping asynchrone) |
| `clients_valides` | `Signal(list)` | `list[ClientInfo]` | `_on_ping_termine()` (après filtrage ONLINE) |

**Connexion interne (__init__) :**
```python
self.ping_termine.connect(self._on_ping_termine)  # ping_termine → filtrage → clients_valides
```

**Flux de déclenchement du ping :**
```python
def ingest_membres_rooms(self, membres):
    # 1. Ajouter les nouveaux membres à _clients
    # 2. Émettre clients_synchronises pour MAJ tableau
    # 3. Déclencher lancer_ping(membres) ← si conditions remplies

def lancer_ping(self, membres, force=False):
    if self._ping_en_cours: return          # ← Garde anti-doublon
    if self._cm is None: return              # ← Pas de ConnexionManager
    if not force:
        # 1. Espacement temporel (5 min)
        # 2. Flag dirty (hash membres)
        pass  # ← les deux gardes sont vérifiées ici, voir §4.1
    self._cm.run_coro(self._ping_par_lots(membres))
```

### 3.2 BoucleRooms (`src/services/boucle_rooms.py`)

| Signal | Payload | Description |
|--------|---------|-------------|
| `membres_actualises` | `list[dict]` | Membres des rooms rejointes (username, room, status) |

Connecté dans `center.py` :
```python
self._boucle_rooms.membres_actualises.connect(
    self._clients_actifs_service.ingest_membres_rooms
)
```

### 3.3 BotClientsActifs (`src/gui/widgets/bots/bot_clients_actifs.py`)

| Signal | Payload | Description |
|--------|---------|-------------|
| `rafraichir_demande` | `Signal()` | L'utilisateur clique 🔄 Rafraîchir |

Connecté dans `center.py` (set_connexion_manager) :
```python
page_clients.rafraichir_demande.connect(self._boucle_rooms.rafraichir)
```
⚠️ Flag `_rafraichir_connecte` évite les connexions multiples en cas de reconnexion.

**Réception des signaux service (via `setup()`) :**
| Signal service | Handler widget | Effet |
|----------------|----------------|-------|
| `clients_synchronises` | `_on_clients_synchronises` | Reconstruit le tableau + met à jour _total_candidats |
| `clients_valides` | `_on_clients_valides` | Met à jour _actifs_joignables, réaffiche 🟢 Prêt, réactive bouton |
| `client_ajoute` | `_ajouter_ligne` | Ajoute une ligne au tableau |
| `client_retire` | `_retirer_ligne` | Supprime une ligne |
| `client_statut_change` | `_mettre_a_jour_statut` | Met à jour la cellule statut |
| `client_info_change` | `_mettre_a_jour_info` | Met à jour les cellules info |

### 3.4 CenterZone — Injection & connexions

```python
# Dans __init__ : création des pages
self._build_clients_actifs_table_page()  # → BotClientsActifs
self._init_boucle_rooms(manager)          # → BoucleRooms (via set_connexion_manager)

# Dans _connect_event_signals :
self._clients_actifs_service = ClientsActifsService(soulseek_service)
page.setup(self._clients_actifs_service)
self._boucle_rooms.membres_actualises.connect(
    self._clients_actifs_service.ingest_membres_rooms
)

# Dans set_connexion_manager :
actifs_service.set_connexion_manager(manager)  # Injection pour run_coro
page_clients.rafraichir_demande.connect(self._boucle_rooms.rafraichir)
```

---

## 4. ✅ État d'avancement

### 4.1 Implémenté

| Composant | Statut | Détail |
|-----------|--------|--------|
| **Ping par lots** | ✅ | `_ping_par_lots()` — lots de 10, délai 2s, `GetUserStatusCommand` |
| **Filtrage ONLINE** | ✅ | `_on_ping_termine()` — garde uniquement `UserStatus.ONLINE` |
| **Signal ping_termine → clients_valides** | ✅ | Connecté dans `__init__` |
| **ingest_membres_rooms → lancer_ping** | ✅ | Déclenché automatiquement depuis BoucleRooms |
| **Clés KNOWLEDGE** | ✅ | `rafraichir_clients_actifs` avec actions complètes |
| **Bouton 🔄 Rafraîchir** | ✅ | Timeout 60s, désactivé pendant ping |
| **Stats UI** | ✅ | Candidats / Actifs & joignables / Injouignables |
| **Indicateur d'état** | ✅ | 🟢 Prêt / 🔄 Scan… / ⏸ Arrêté |
| **Dernière mise à jour** | ✅ | Timer 60s, format relatif |
| **Flag anti-doublon Rafraîchir** | ✅ | `_rafraichir_connecte` dans center.py |
| **ConnexionManager injection** | ✅ | `set_connexion_manager()` |
| **Tests ping par lots** | ✅ | 8 tests asynchrones dans `test_clients_actifs_service.py` |
| **Tests filtrage** | ✅ | 5 tests dans `TestPingParLots` |
| **Tests ingest** | ✅ | 9 tests dans `TestIngestMembresRooms` |
| **Sync timer 30s** | ✅ | `_sync_timer` re-synchronise avec UserManager.users |
| **BoucleRooms indépendante** | ✅ | Cycle 30s, top 5 rooms par nb membres |
| **Métriques de performance** | ✅ | `ping_metrics()` + `reinitialiser_metriques()` + 📊 dans l'UI |
| **Événements EventBus (Rooms)** | ✅ | Cycles, membres récupérés — visible dans timeline workflow inspector |
| **Événements EventBus (ClientsActifs)** | ✅ | Ping lancé/ignoré/terminé, ingestion — visible dans timeline & matrice |
| **Surveillance workflow inspector** | ✅ | Stats boucle (rooms/membres, métriques ping) dans carte dédiée, MAJ 2s |

### 4.2 À faire

Aucune — toutes les fonctionnalités prévues sont implémentées.

---

## 5. 🔧 Paramètres exposés

| Paramètre | Valeur | Définition | Modifiable |
|-----------|--------|------------|------------|
| `_LOT_PING` | 10 | Clients pingés simultanément par lot | Constante de classe |
| `_DELAI_INTER_LOTS` | 2.0 | Secondes entre deux lots | Constante de classe |
| `_INTERVALLE_PING_MIN` | 300 | Secondes minimum entre deux pings | Constante de classe |
| `_TIMEOUT_RAFRAICHIR` | 60 | Timeout du bouton Rafraîchir (widget) | Constante widget |

---

## 6. 🧪 Tests

### Tests existants (implémentés)

| Fichier | Groupe | Nb tests | Couvre |
|---------|--------|----------|--------|
| `test_clients_actifs_service.py` | `TestPingParLots` | ~17 | `lancer_ping`, `_ping_par_lots` (async), `_on_ping_termine`, pipeline ingest→ping, espacement, dirty, forcer_ping |
| `test_clients_actifs_service.py` | `TestMetriquesPerformance` | 6 | métriques initiales, ping réussi, partiel, cumul, reset, liste vide |
| `test_clients_actifs_service.py` | `TestIngestMembresRooms` | ~9 | ingestion, doublons, signaux, statuts |
| `test_clients_actifs_service.py` | TestFluxReel, TestEvenements, etc. | ~15 | cycle de vie, events, tri |

### Tests implémentés (espacement + dirty + force)

| Test | Description |
|------|-------------|
| `test_lancer_ping_espacement` | Ping déclenché 2x en <5 min → second ignoré |
| `test_lancer_ping_apres_espacement` | Ping déclenché 2x en >5 min → second accepté |
| `test_lancer_ping_dirty_changed` | Membres différents → ping déclenché |
| `test_lancer_ping_dirty_identical` | Membres identiques → ping ignoré |
| `test_forcer_ping_declenche_run_coro` | `forcer_ping()` déclenche bien `run_coro` |
| `test_forcer_ping_liste_vide` | `forcer_ping()` avec 0 clients → run_coro appelé avec membres vide |
| `test_forcer_ping_exclut_unknown` | `forcer_ping()` filtre les clients UNKNOWN |

---

## 7. 🔗 Dépendances

- **BoucleRooms** : ✅ Déjà implémentée. Fournit `membres_actualises`. Cycle 30s.
- **ClientsActifsService** : ✅ Implémenté. ✅ Espacement + dirty flag + `forcer_ping()`.
- **BotClientsActifs (widget)** : ✅ Implémenté. Bouton, stats, indicateur d'état.
- **BotAccueil** : ✅ Implémenté. Intention `rafraichir_clients_actifs` dans KNOWLEDGE.

---

## 8. ❓ Questions résolues

- [x] **Ping par lots dans ClientsActifsService** (pas dans BoucleRooms)
- [x] **Pipeline asynchrone** : `_ping_par_lots()` via `run_coro()` du ConnexionManager
- [x] **Pas de cycle automatique** : ping déclenché événementiellement + manuellement
- [x] **Critère actif & joignable** : ping réussi **ET** statut = ONLINE. AWAY/UNKNOWN exclus.
- [x] **Flag anti-doublon** : `_rafraichir_connecte` dans center.py
- [x] **Double source** : UserManager (utilisateurs trackés historiques) + BoucleRooms (découverte rooms) — complémentaires
- [x] **Sync timer 30s** : gardé — resynchronise périodiquement avec UserManager.users
- [x] **Espacement ping 5 min** : ✅ implémenté — `_INTERVALLE_PING_MIN = 300` dans `lancer_ping()`
- [x] **Flag dirty** : ✅ implémenté — `hash(frozenset(...))` comparé à `_dernier_hash_membres`

---

> *Spec v2.1 — Mise à jour le 2026-05-21 pour documenter la surveillance EventBus + workflow inspector.*
> **Prochaine action :** Intégration continue des tests (CI) et Dashboard de monitoring centralisé.
