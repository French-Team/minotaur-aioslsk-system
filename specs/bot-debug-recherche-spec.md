# Spec Debug — Recherche Athéna × Arès (aucun résultat)

## 1. Problème

**Constat :** Une recherche « techno » en mode Normal (avec « — Tous les clients — »)
ne retourne **aucun résultat** dans le tableau, alors que d'autres clients Soulseek
(Nicotine+, officiel) trouvent des résultats pour le même terme.

**Logs observés :**

| Timestamp | Message | Interprétation |
|-----------|---------|----------------|
| 20:30:42 | `🔍 Recherche de « techno » sur tout le réseau Soulseek…` | Recherche lancée (mode global broadcast) |
| 20:30:42 | `[DIAG] Recherche lancée : 'techno' (ticket 2)` | Ticket créé dans aioslsk |
| 20:31:12 | `⏱️ 30s écoulées — la recherche continue en arrière-plan` | Timeout UI passé |
| 20:34:02 | `[DIAG] ticket 2 ✅ présent dans self.requests (1 requête active)` | Toujours présent 2min après |
| — | *Aucun log `_on_search_result: reçu N fichiers`* | Handler jamais appelé |

**Autres clients Soulseek :** ✅ fonctionnent → réseau OK, terme « techno » valide.

---

## 2. Périmètre

| Élément | Statut |
|---------|--------|
| 🔎 Mode Normal | **Cible du debug** — recherche par Arès |
| 🏛 Mode Club | Hors scope (en construction — pas de données JSON) |
| 🏷 Mode Label | Hors scope (en construction) |
| 🎤 Mode Artiste | Hors scope (en construction) |
| 🛠 Sysinternals Suite | Disponible (Process Explorer, TCPView) |
| 🕵️ Service Inspector | Disponible (logs, niveaux, sauvegarde) |
| 📊 Workflow Inspector | Disponible (suivi des bots) |
| ❓ Onglet Événements | **Manquant** — signalé par l'utilisateur comme absent du Service Inspector |

---

## 3. Architecture du pipeline de recherche

```
 ┌──────────────────────────────────────────┐
 │                ModesPanel                 │
 │  ┌──────────┬────────┬───────┬────────┐  │
 │  │ Normal   │ Club   │ Label │ Artiste│  │
 │  │ (🔎)     │ (🏛)   │ (🏷)  │ (🎤)   │  │
 │  └────┬─────┴────────┴───────┴────────┘  │
 │       │ search_requested(query)           │
 └───────┼──────────────────────────────────┘
         │
         ▼
 ┌──────────────────────────────────────────┐
 │           BotRecherche._on_search()       │
 │                                           │
 │  if selected_client:                      │
 │    connexion_manager.search_user(client)  │  ← Ciblé Arès
 │  else:                                    │
 │    connexion_manager.search(query)        │  ← ⚠️ Broadcast global !
 └───────┬──────────────────────────────────┘
         │
         ▼
 ┌──────────────────────────────────────────┐
 │           ConnexionManager               │
 │                                           │
 │  Thread asyncio dédié                     │
 │  → client.searches.search(query)         │  ← API aioslsk
 │  → client.searches.search_user(u, q)     │
 │  → stocke _current_search_ticket         │
 │  → émet search_result_received (Signal)  │
 │  → timer DIAG toutes les 10s             │
 └───────┬──────────────────────────────────┘
         │
         ▼
 ┌──────────────────────────────────────────┐
 │           SoulseekService                │
 │                                           │
 │  events.register(SearchResultEvent, cb)  │  ← Enregistré dans connect()
 │  → émet search_result_received (Signal)  │
 └───────┬──────────────────────────────────┘
         │
         ▼
 ┌──────────────────────────────────────────┐
 │         BotRecherche._on_search_result()  │  ← ⛔ JAMAIS APPELÉ
 │                                           │
 │  from aioslsk.events import              │
 │    SearchResultEvent                      │
 │                                           │
 │  filtre audio mp3/flac/ogg               │
 │  ajoute au QTableWidget                  │
 │  met à jour compteur + status            │
 └──────────────────────────────────────────┘
```

### Flux des signaux

```
SoulseekService              ConnexionManager          BotRecherche
    │                             │                        │
    │  [thread async]             │  [thread UI]           │
    │                             │                        │
    │  client.events.register(    │                        │
    │    SearchResultEvent,       │                        │
    │    lambda evt:              │                        │
    │      search_result_received├─►search_result_received├─►_on_search_result()
    │        .emit(evt)          │   .emit(evt)           │     (jamais appelé)
    │                             │                        │
```

**Remarque importante :** Le thread asyncio d'aioslsk émet l'événement `SearchResultEvent`
sur sa boucle interne. Il passe par les signaux Qt (`Signal(object)`) qui sont thread-safe
et acheminent automatiquement vers le thread UI. Ce mécanisme est déjà utilisé avec succès
pour d'autres événements (transferts, messages privés, room list).

---

## 4. Hypothèses

Les hypothèses sont classées par probabilité.

### H1 — Workflow erroné : broadcast global au lieu d'Arès (haute)

**Problème :** En mode Normal avec « — Tous les clients — », le code appelle
`connexion_manager.search(query)` qui fait un **broadcast global** sur tout le réseau
Soulseek via `client.searches.search()`.

**Attendu :** La recherche doit cibler la liste des clients actifs et joignables
(Arès) par lots, en appelant `client.searches.search_user(username, query)` pour
chaque lot de clients.

**Localisation :** `src/gui/widgets/bots/bot_recherche.py`, méthode `_on_search()` (l. 1660-1700)

**Code actuel (simplifié) :**
```python
if self._selected_client_username:
    # Client unique
    self._connexion_manager.search_user(client, query)
else:
    # ⚠️ Broadcast global — pas dans Arès
    self._connexion_manager.search(query)
```

**Code attendu :**
```python
if self._selected_client_username:
    # Client unique
    self._connexion_manager.search_user(client, query)
elif self._clients_actifs_service:
    # Arès batch — envoyer à chaque client actif
    for client in self._clients_actifs_service.clients_actifs():
        self._connexion_manager.search_user(client.username, query)
```

### H2 — Handler search_result non enregistré (haute)

**Problème :** `soulseek_service` enregistre l'écouteur `SearchResultEvent` dans sa
méthode `connect()`. Si le client est réinitialisé (après une déconnexion/reconnexion
ou si la connexion est établie via un flux alternatif), les écouteurs ne sont pas
ré-enregistrés.

**Preuve :** Les logs montrent que `_on_search_result()` n'est **jamais appelé**,
même 2 minutes après le lancement. Le ticket est pourtant présent dans aioslsk.
D'autres événements (transferts) fonctionnent, donc le mécanisme des signaux Qt est
valide — c'est l'enregistrement sur `SearchResultEvent` spécifiquement qui pourrait
être défectueux.

**Localisation :** `src/services/soulseek_client.py`, méthode `connect()`, lignes ~380-390

**À vérifier dans les logs :**
- `[SOULSEEK] Tous les écouteurs d'événements ont été enregistrés avec succès.` *(présent ?)*
- Vérifier après une reconnexion si ce message réapparaît

### H3 — Filtre audio trop restrictif (moyenne)

**Problème :** `_on_search_result()` filtre automatiquement les extensions en ne
gardant que `.mp3`, `.flac`, `.ogg`. Si les résultats arrivent mais avec d'autres
extensions, ils sont comptés dans les logs mais pas ajoutés au tableau.

**Preuve partielle :** Pas de log `_on_search_result: 0 ajouté sur N reçus` non plus
— ce qui suggère que `_on_search_result()` n'est vraiment jamais appelé, pas qu'il
filtre tout.

**À vérifier :** Désactiver le filtre audio (toggle « 🔊 Audio seulement » → off)
et relancer une recherche.

### H4 — Ticket supprimé prématurément (faible)

**Problème :** Le diagnostic confirme que le ticket est présent 2 minutes après le
lancement, donc il n'est pas supprimé. De plus, le patch `remove_request` tracerait
la suppression. Hypothèse écartée.

### H5 — Problème de thread (faible)

**Problème :** L'événement `SearchResultEvent` est émis dans le thread asyncio
d'aioslsk, et le signal Qt `search_result_received` est thread-safe. Mais si
la boucle d'événements Qt n'est pas correctement sollicitée (pas de `processEvents`
ou de spin dans le thread principal), le signal pourrait ne pas être traité.

**Preuve contradictoire :** D'autres signaux fonctionnent (transferts, connexion,
messages privés) via le même mécanisme.

---

## 5. Plan d'investigation

### Phase 1 — Vérification de l'enregistrement du handler

**Objectif :** Confirmer que `SearchResultEvent` est bien enregistré dans aioslsk.

| # | Action | Résultat attendu | Sortie si OK | Sortie si KO |
|---|--------|------------------|-------------|--------------|
| 1.1 | Lancer l'app et se connecter |  |  |  |
| 1.2 | Vider les logs du Service Inspector |  |  |  |
| 1.3 | Chercher `[SOULSEEK] Tous les écouteurs` dans les logs filtrés | Message présent une fois | Handler enregistré | Handler jamais enregistré → **bug de connexion** |
| 1.4 | Lancer recherche « techno » |  |  |  |
| 1.5 | Chercher `events.register` dans les logs | Appel confirmé |  |  |
| 1.6 | Chercher `SearchResultEvent` dans les logs du Service Inspector | Aucune erreur |  |  |
| 1.7 | **Contournement** : Relancer la connexion (déconnecter/reconnecter) et refaire 1.3-1.4 |  |  |  |

**Si le handler n'est pas enregistré :** Vérifier le code dans `soulseek_service.connect()`
— l'enregistrement n'est fait qu'à la création du client, pas après une reconnexion.

### Phase 2 — Activation des logs DEBUG aioslsk

**Objectif :** Capturer les événements bruts d'aioslsk pour voir si `SearchResultEvent`
est émis.

| # | Action | Résultat attendu |
|---|--------|------------------|
| 2.1 | Dans `run.py`, ajouter `aioslsk` aux loggers avec niveau DEBUG | Logs détaillés d'aioslsk |
| 2.2 | Lancer app, connecter, chercher « techno » | |
| 2.3 | Filtrer les logs par `aioslsk` dans le Service Inspector | Voir les événements raw |
| 2.4 | Chercher `search_result`, `SearchResult`, `result` dans les logs aioslsk | Si présent → aioslsk émet l'événement → problème dans notre pipeline. Si absent → problème dans aioslsk ou réseau |

**Configuration du logger aioslsk (dans `run.py`) :**
```python
logging.getLogger("aioslsk").setLevel(logging.DEBUG)
```

### Phase 3 — Test de la recherche ciblée Arès (contournement architectural)

**Objectif :** Contourner le broadcast global et tester la recherche via Arès
manuellement, comme le workflow l'exige.

| # | Action | Résultat attendu |
|---|--------|------------------|
| 3.1 | Sélectionner UN client spécifique dans le sélecteur Arès | Le code appelle `search_user(client, query)` |
| 3.2 | Lancer recherche « techno » |  |
| 3.3 | Observer les logs DIAG : ticket créé ? | Ticket présent dans `self.requests` |
| 3.4 | Observer `_on_search_result` : appelé ? |  |
| 3.5 | Si OK pour un client : répéter pour plusieurs clients |  |
| 3.6 | Logguer le résultat | `search_user()` fonctionne → **bug = broadcast global** |

**Logs à surveiller :**
- `[DIAG] Recherche chez {username} : 'techno' (ticket N)`
- `[DIAG] ticket N ✅ présent dans self.requests`
- `_on_search_result: reçu N fichiers pour « techno » de {username}`

### Phase 4 — Audit du code et correction du workflow

**Objectif :** Modifier `_on_search()` pour qu'il cherche par lots dans la liste Arès
au lieu de faire un broadcast global.

| # | Fichier | Action |
|---|---------|--------|
| 4.1 | `bot_recherche.py` | Dans `_on_search()`, remplacer `elif not selected_client: search(query)` par un parcours des clients Arès en lots |
| 4.2 | `connexion_manager.py` | Ajouter une méthode `search_ares(clients: list[str], query: str)` qui envoie `search_user()` par lots avec délai entre chaque lot |
| 4.3 | `bot_recherche.py` | Ajouter le logging du nombre de clients Arès ciblés |
| 4.4 | `connexion_manager.py` | Gérer le nombre maximum de requêtes simultanées (rate limiting) |

**Mécanisme proposé pour les lots :**
```python
# Dans ConnexionManager
def search_ares(self, usernames: list[str], query: str) -> None:
    """
    Envoie une requête search_user() à chaque client de la liste,
    par lots de N pour éviter de saturer le réseau.
    """
    BATCH_SIZE = 5
    BATCH_DELAY_MS = 500  # délai entre chaque lot
    
    async def _do_ares_search():
        for i in range(0, len(usernames), BATCH_SIZE):
            batch = usernames[i:i + BATCH_SIZE]
            logger.info("[DIAG] Arès lot %d/%d : %d clients", 
                       i//BATCH_SIZE + 1, 
                       (len(usernames)-1)//BATCH_SIZE + 1,
                       len(batch))
            for username in batch:
                try:
                    await self._do_search_user(username, query)
                except Exception as e:
                    logger.warning("[DIAG] Arès erreur %s : %s", username, e)
            if i + BATCH_SIZE < len(usernames):
                await asyncio.sleep(BATCH_DELAY_MS / 1000)
    
    self._async_thread.run_coro(_do_ares_search())
```

**Considérations :**
- **Rate limiting :** Ne pas envoyer toutes les requêtes en même pour éviter de
  se faire bannir ou de saturer la connexion.
- **Gestion des tickets :** Chaque `search_user()` crée un ticket séparé dans
  aioslsk. Il faudra gérer plusieurs tickets simultanément.
- **Déduplication des résultats :** Un même fichier peut apparaître plusieurs fois
  (un résultat par client) → déduplication à prévoir dans le tableau.
- **Feedback UI :** Afficher la progression « Recherche chez N/M clients Arès… ».

### Phase 5 — Ajout de l'onglet Événements dans le Service Inspector

**Objectif :** Ajouter un onglet « Événements » dans le Service Inspector qui liste
tous les événements enregistrés dans aioslsk (`client.events`).

| # | Action |
|---|--------|
| 5.1 | Ajouter un onglet « Événements » dans le Service Inspector |
| 5.2 | Lister tous les événements enregistrés avec leur type et nombre de callbacks |
| 5.3 | Rafraîchir périodiquement (timer 5s) |
| 5.4 | Indiquer en vert/rouge si `SearchResultEvent` est bien enregistré |

**Données à exposer :**
```python
events = client.events._handlers  # dict: EventType → list[callable]
for event_type, handlers in events.items():
    # event_type.__name__, len(handlers)
```

---

## 6. Points de décision

### 6.1 — Architecture de la recherche Arès

Deux approches possibles :

| Approche | Avantages | Inconvénients |
|----------|-----------|---------------|
| **A. Par lots séquentiels** : Lancer N `search_user()` avec délai entre lots | Simple, pas de surcharge réseau. Logs clairs. | Lent si beaucoup de clients (ex: 2000 clients = 400 lots de 5 = 200s) |
| **B. Par lots parallèles** : Lancer N requêtes simultanées, rate-limit par ticket | Plus rapide. Géré par aioslsk. | Plus complexe. Nécessite de tracker N tickets simultanément |

**Recommandation :** Commencer par l'approche A (lots séquentiels) car plus simple
à debugger, puis optimiser vers B si nécessaire.

### 6.2 — Gestion multi-tickets

Actuellement `_current_search_ticket: int | None` ne gère qu'un seul ticket.
Pour la recherche Arès par lots, il faudra :

- Stocker un **ensemble de tickets** : `_search_tickets: set[int]`
- Le diagnostic DIAG doit iterer sur tous les tickets
- `stop_search()` doit annuler tous les tickets

### 6.3 — Déduplication des résultats

Quand on cherche « techno » chez 2000 clients, le même fichier peut apparaître
plusieurs fois. Stratégies :

| Stratégie | Description |
|-----------|-------------|
| **FIFO simple** | On garde tout, l'utilisateur voit les doublons (transparent) |
| **Par (username, filename)** | Déduplication à l'insertion dans le tableau |
| **Par hash** | Déduplication par hash SHA256 du fichier (plus fiable mais plus lourd) |

**Recommandation :** FIFO simple dans un premier temps (le comportement actuel),
puis déduplication par (username, filename) si les doublons sont gênants.

---

## 7. Logs de diagnostic utiles

### Logs à activer pour le debug

```python
# run.py — loggers à passer en DEBUG
for logger_name in (
    "aioslsk",                          # Logs bruts d'aioslsk
    "aioslsk.search",                   # Spécifique au moteur de recherche
    "[CONNEXION]",                      # Notre ConnexionManager (déjà DIAG)
    "[SOULSEEK]",                       # SoulseekService
    "[RECHERCHE]",                      # BotRecherche
    "[RECHERCHE-MODES]",                # ModesPanel
    "[DIAG]",                           # Déjà actif
):
    logging.getLogger(logger_name).setLevel(logging.DEBUG)
```

### Pattern de logs à surveiller

```
✅ [SOULSEEK] Tous les écouteurs d'événements ont été enregistrés avec succès.
   → Handler SearchResultEvent enregistré

✅ [DIAG] Recherche lancée : 'techno' (ticket 2, 1 requête(s) active(s) dans aioslsk)
   → Requête envoyée à aioslsk

✅ [DIAG] ticket 2 ✅ présent dans self.requests (1 requête(s) active(s))
   → Ticket vivant

✅ _on_search_result: reçu N fichiers pour « techno » de {username}
   → Résultats qui arrivent

❌ Aucun log _on_search_result après 60s
   → Handler jamais appelé → bug dans la chaîne d'événements
```

---

## 8. Checklist de debug (à cocher)

- [ ] **Phase 1** : Vérifier l'enregistrement de `SearchResultEvent` dans les logs
- [ ] **Phase 1.7** : Tester après reconnexion (déco/reco)
- [ ] **Phase 2** : Activer DEBUG sur `aioslsk` et capturer les événements bruts
- [ ] **Phase 3** : Tester `search_user()` sur un seul client Arès
- [ ] **Phase 3** : Noter le résultat (succès/échec) dans le logbook
- [ ] **Phase 4** : Auditer `_on_search()` et corriger le workflow
- [ ] **Phase 4.2** : Implémenter `search_ares()` dans ConnexionManager
- [ ] **Phase 4.4** : Implémenter le rate limiting (lots + délai)
- [ ] **Phase 5** : Ajouter l'onglet Événements au Service Inspector (optionnel)

---

## 9. Annexe — Codes sources référencés

| Fichier | Rôle |
|---------|------|
| `src/gui/widgets/bots/bot_recherche.py` | UI de la recherche (tableau, filtres, _on_search, _on_search_result) |
| `src/gui/widgets/bots/bot_recherche_modes.py` | Panneau des 4 modes + StatusConsole |
| `src/services/connexion_manager.py` | Pont entre UI et aioslsk (search, search_user, diagnostic tickets) |
| `src/services/soulseek_client.py` | Wrapper aioslsk (enregistrement événements, signaux Qt) |
| `src/services/clients_actifs_service.py` | Service Arès (liste des clients actifs/joignables) |
| `src/gui/devtool/service_inspector.py` | Inspecteur de logs et services |
| `src/gui/devtool/workflow_inspector.py` | Inspecteur de workflow des bots |
| `src/gui/devtool/diagnostics/sysinternals_launcher.py` | Lanceur Sysinternals |

---

*Document créé le 2026-05-22 — Plan d'investigation pour le debug de la recherche Athéna × Arès.*
