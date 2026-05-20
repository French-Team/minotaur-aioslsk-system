# Plan d'implémentation — Boucle Clients Actifs

> **Statut :** ✅ Implémentation en cours — Étape 1
> **Dernière mise à jour :** 2026-05-20
> **Contexte :** Bot le plus simple de l'ordre d'implémentation (Niveau 1). Pipeline de découverte et validation des clients actifs & joignables sur le réseau Soulseek.

---

## 🎯 Objectif

Pipeline capable de découvrir, valider et filtrer les clients Soulseek qui sont **véritablement actifs et joignables**. Le bot ne se contente pas d'afficher une liste — il exécute un pipeline complet :

1. **Récupérer** les rooms publiques (via BoucleRooms)
2. **Rejoindre** le top 5 des rooms (les plus peuplées)
3. **Collecter** les membres de ces rooms
4. **Pinger** ces membres par lots (10 clients / 2s) pour vérifier leur disponibilité
5. **Filtrer** pour ne garder que les clients répondant au ping **ET** ayant le statut ONLINE
6. **Afficher** la liste filtrée dans BotClientsActifs

**Différence clé avec les autres boucles :** Pas de cycle périodique automatique. Le pipeline s'exécute **une fois au démarrage** du bot, puis **à la demande** via un bouton dans le widget ou une intention dans l'Accueil.

---

## 📋 Liste des étapes

### Étape 1 — Refactor du ping existant (ClientsActifsService)

**Statut :** ❌ À faire

- [ ] Analyser `ClientsActifsService._do_ping_loop()` actuel
  - [ ] Actuellement : boucle asynchrone infinie avec 120s d'attente, ping individuel avec 0.2s de délai
  - [ ] À remplacer par un système de ping par lots déclenché ponctuellement
- [ ] Créer `ClientsActifsService._pinger_par_lots(membres: list[dict]) -> list[str]`
  - [ ] Paramètres : liste des membres (username, room, status) venant de BoucleRooms
  - [ ] Découpage en lots de **10 clients**
  - [ ] Délai de **2 secondes** entre chaque lot (paramétrable)
  - [ ] Pour chaque client : exécuter `GetUserStatusCommand(username)`
  - [ ] Retourne la liste des usernames qui ont répondu au ping
  - [ ] Timeout par ping : 5 secondes
  - [ ] Logguer chaque lot (debug) : `"Lot X/Y : N pings, M réponses"`
- [ ] Remplacer l'ancien `_do_ping_loop()` par la nouvelle approche
  - [ ] Supprimer l'ancienne méthode `_do_ping_loop()` (boucle infinie + while self._running)
  - [ ] Créer la nouvelle méthode `async _ping_par_lots(membres: list[dict]) -> list[str]`
  - [ ] La nouvelle méthode est déclenchée ponctuellement, jamais en boucle
- [ ] ✅ Validation
  - [ ] Compilation Python
  - [ ] Tests unitaires du ping par lots
  - [ ] Vérifier que le *ping task* existant ne tourne plus en boucle

### Étape 2 — Intégration BoucleRooms → Ping

**Statut :** ❌ À faire

- [ ] Modifier `ClientsActifsService.ingest_membres_rooms()` pour déclencher le ping
  - [ ] Après avoir ajouté les membres à `_clients`, appeler `_pinger_par_lots()`
  - [ ] Attendre la fin du ping avant de filtrer
  - [ ] Synchronisation : le ping est asynchrone, utiliser un callback ou signal
- [ ] Créer le signal `clients_valides = Signal(list)` dans ClientsActifsService
  - [ ] Émis après la fin du ping + filtrage
  - [ ] Payload : `list[ClientInfo]` — les clients actifs & joignables
  - [ ] Alternative : réutiliser `clients_synchronises` avec les données filtrées
- [ ] Connecter le signal à `BotClientsActifs._initialiser_tableau()`
  - [ ] Déjà connecté via `clients_synchronises` — à vérifier
  - [ ] S'assurer que le tableau se met à jour automatiquement
- [ ] ✅ Validation
  - [ ] Compilation Python
  - [ ] Test d'intégration : BoucleRooms → ingest → ping → filtrage → affichage
  - [ ] Vérifier que l'UI se met à jour avec les données filtrées

### Étape 3 — Filtrage actifs & joignables

**Statut :** ❌ À faire

- [ ] Implémenter `ClientsActifsService._filtrer_actifs_joignables(reponses_ping: list[str])`
  - [ ] Critère : username dans `reponses_ping` **ET** statut == `UserStatus.ONLINE`
  - [ ] Retourne `list[ClientInfo]` filtrée
  - [ ] Si un client répond au ping mais n'est pas ONLINE → garder pour info ? (à décider)
    - **Décision** : NE PAS garder. Seul "actif & joignable" = ping OK + ONLINE.
  - [ ] Logguer le ratio : `"Filtrage : N actifs & joignables / M candidats"`
- [ ] Mettre à jour les stats de `BotClientsActifs`
  - [ ] Barre d'en-tête : Total (candidats avant filtrage) / Actifs & joignables (après filtrage)
  - [ ] Afficher clairement la différence entre "vus dans les rooms" et "confirmés actifs"
- [ ] ✅ Validation
  - [ ] Compilation Python
  - [ ] Tests unitaires du filtrage (ping OK + ONLINE, ping OK + AWAY, pas de ping, etc.)
  - [ ] Vérifier l'affichage des stats dans le widget

### Étape 4 — Déclenchement manuel

**Statut :** ❌ À faire

- [ ] Ajouter un bouton "Rafraîchir" dans `BotClientsActifs`
  - [ ] Icône : `🔄` (ou `🔍`)
  - [ ] Position : barre d'en-tête, à droite
  - [ ] Texte : "Rafraîchir" ou juste l'icône
  - [ ] Comportement : relance le pipeline complet (BoucleRooms → membres → ping → filtrage)
  - [ ] **Problème** : `BoucleRooms._executer_cycle()` est privée. Solution : ajouter une méthode publique `rafraichir()` dans BoucleRooms qui appelle `_executer_cycle()` puis `_timer.start()` si arrêté
  - [ ] Pendant l'exécution : désactiver le bouton, afficher "Scan en cours..."
  - [ ] Réactiver à la fin
  - [ ] Tooltip : "Relance la détection complète des clients actifs"
- [ ] Ajouter l'intention `rafraichir_clients_actifs` dans `bot_accueil_knowledge.py`
  - [ ] Keywords : `rafraîchir clients actifs`, `refresh`, `mettre à jour les clients`, `actualiser`
  - [ ] Action : `start_loop` (relance Clients Actifs) ou nouvelle action `refresh`
  - [ ] Réponse : "Je relance la détection des clients actifs et joignables..."
  - [ ] Suggestions : `👥 Voir les clients`, `🏠 Accueil`
- [ ] Ajouter le routeur dans `_on_suggestion` de `bot_accueil.py` (si action `rafraichir` utilisée)
- [ ] ✅ Validation
  - [ ] Compilation Python
  - [ ] Test UI : clic sur le bouton Rafraîchir
  - [ ] Test Accueil : intention "rafraîchir clients actifs"
  - [ ] Vérifier que le bouton est désactivé pendant l'exécution

### Étape 5 — Ajustements UI

**Statut :** ❌ À faire

- [ ] Modifier la barre de stats dans `BotClientsActifs`
  - [ ] Actuel : Total / Actifs / Connectés
  - [ ] Nouveau : Candidats (membres des rooms) / Actifs & joignables (après ping) / ❌ Injouignables
  - [ ] Ajouter un indicateur "Dernière mise à jour : il y a X min"
  - [ ] Style : candidats en gris, actifs & joignables en vert, injouignables en rouge clair
- [ ] Ajouter une colonne "Dernier ping" dans le tableau ?
  - [ ] À décider — optionnel, ajoute du bruit
  - [ ] Alternative : tooltip sur le statut avec "Ping réussi à HH:MM:SS"
- [ ] Ajouter un indicateur d'état du pipeline
  - [ ] Icône dans l'en-tête : `🟢` (prêt), `🔄` (scan en cours), `⏸` (en pause/désactivé)
  - [ ] Texte : "Prêt" / "Scan en cours..." / "Inactif"
- [ ] ✅ Validation
  - [ ] Compilation Python
  - [ ] Vérification visuelle des stats

### Étape 6 — Tests & Validation

**Statut :** ❌ À faire

- [ ] Tests unitaires de `_pinger_par_lots()`
  - [ ] Lot de 5 clients → 1 lot, 5 pings
  - [ ] Lot de 15 clients → 2 lots, rate limiting respecté
  - [ ] 0 clients → aucun ping
  - [ ] Timeout → client marqué comme injoignable
- [ ] Tests unitaires de `_filtrer_actifs_joignables()`
  - [ ] Ping OK + ONLINE → actif & joignable ✅
  - [ ] Ping OK + AWAY → filtré ❌
  - [ ] Ping OK + OFFLINE → filtré ❌
  - [ ] Ping échoué + ONLINE → filtré ❌
  - [ ] Mix : 3/10 passent le filtre
- [ ] Tests d'intégration
  - [ ] BoucleRooms mockée → ClientsActifsService → ping → filtrage → signal
  - [ ] Bouton Rafraîchir → pipeline relancé
- [ ] Code review complète
- [ ] ✅ Validation : tout fonctionne de bout en bout
  - [ ] Démarrer BoucleRooms → membres → ping → affichage filtré
  - [ ] Cliquer Rafraîchir → nouveau cycle complet
  - [ ] Intention Accueil → rafraîchir
  - [ ] Pas de fuite mémoire, pas de tâche asyncio orpheline

---

## 📁 Fichiers concernés

### Modifications

| Fichier | Étape | Changement |
|---------|-------|------------|
| `src/services/clients_actifs_service.py` | 1, 2, 3 | Nouveau ping par lots, filtrage, signal |
| `src/services/boucle_rooms.py` | — | Aucun changement (reste tel quel) |
| `src/gui/widgets/bots/bot_clients_actifs.py` | 4, 5 | Bouton Rafraîchir, stats, indicateur |
| `src/gui/widgets/bots/bot_accueil_knowledge.py` | 4 | Nouvelle intention `rafraichir_clients_actifs` |
| `src/gui/widgets/bots/bot_accueil.py` | 4 | Routeur `rafraichir` si nécessaire |

### Créations

*Aucun nouveau fichier — tout est dans l'existant.*

---

## 🐛 Problèmes connus

- **Conflit potentiel entre l'ancien `_do_ping_loop()` et le nouveau `_pinger_par_lots()`** : L'ancienne méthode tourne en boucle infinie toutes les 120s. Il faut la désactiver proprement pour éviter deux pings simultanés.
- **Tâche asyncio orpheline** : Si le bot est arrêté (`arreter()`) pendant un ping en cours, la tâche asynchrone peut rester accrochée. Utiliser un mécanisme d'annulation (`asyncio.CancelledError`).
- **BoucleRooms tourne indépendamment à 30s** : Pendant que le pipeline Clients Actifs s'exécute, BoucleRooms continue son cycle. Si un nouveau signal `membres_actualises` arrive pendant un ping en cours, il faut ignorer ou bufferiser (pas de double ping simultané).

---

## 📝 Notes de conception

### Architecture du pipeline

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
│  2. Déclencher _pinger_par_lots() ───────────┐               │
└───────────────────────────────────────────────┤               │
                                                ▼               │
┌─────────────────────────────────────────────────────────────┐│
│ _pinger_par_lots(membres) : async                            ││
│  1. Découper en lots de 10 clients                           ││
│  2. Pour chaque lot :                                        ││
│     a. Exécuter GetUserStatusCommand pour chaque client      ││
│     b. Collecter les réponses (timeout 5s)                   ││
│     c. Attendre 2s avant le prochain lot                     ││
│  3. Retourner la liste des usernames qui ont répondu         ││
└─────────────────────────────────────────────────────────────┘│
                                                │               │
                                                ▼               │
┌─────────────────────────────────────────────────────────────┐│
│ _filtrer_actifs_joignables(reponses)                          ││
│  1. Garder : username in reponses AND statut == ONLINE        ││
│  2. Retourner list[ClientInfo] filtrée                       ││
└─────────────────────────────────────────────────────────────┘│
                                                │               │
                                                ▼               │
┌─────────────────────────────────────────────────────────────┐│
│ Émettre signal clients_valides / clients_synchronises         ││
│  → BotClientsActifs._initialiser_tableau()                   ││
└─────────────────────────────────────────────────────────────┘│
```

### Flux de déclenchement

```
Démarrage (demarrer())
    │
    ├─► Pipeline complet : BoucleRooms → membres → ping → filtrage → affichage
    │
    └─► Attente (pas de timer périodique)

Bouton 🔄 Rafraîchir (widget)
    │
    └─► Pipeline complet

Intention "rafraîchir clients actifs" (Accueil)
    │
    └─► start_loop → redéclenche demarrer() → pipeline complet
```

### Rate limiting

- **Taille du lot** : 10 clients (paramétrable via constante `_LOT_PING = 10`)
- **Délai inter-lots** : 2 secondes (paramétrable via constante `_DELAI_INTER_LOTS = 2.0`)
- **Timeout par ping** : 5 secondes (paramétrable)
- **Justification** : Soulseek est un réseau P2P non commercial. Envoyer trop de pings simultanés pourrait être perçu comme agressif ou saturer la connexion. 10 clients / 2s est un rythme prudent.

### Gestion des conflits

- **Ping en cours + nouveau signal BoucleRooms** : Ignorer le nouveau signal si un ping est en cours. Utiliser un flag `_ping_en_cours = False/True`.
- **Arrêt du bot pendant un ping** : Capturer `asyncio.CancelledError` et nettoyer. Le flag `_running` est vérifié entre chaque lot.
- **BoucleRooms continue pendant le ping** : C'est normal. BoucleRooms tourne indépendamment. Le nouveau signal sera traité au prochain cycle (après la fin du ping en cours).

### Paramètres exposés

| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| `_LOT_PING` | 10 | Nombre de clients pingés simultanément par lot |
| `_DELAI_INTER_LOTS` | 2.0 | Secondes d'attente entre deux lots |
| `_TIMEOUT_PING` | 5.0 | Timeout en secondes pour un ping individuel |

Ces paramètres sont des constantes de classe, modifiables directement dans `ClientsActifsService`. Pas besoin d'interface utilisateur pour les modifier dans un premier temps.

---

## ❓ Questions résolues

### Architecture

- [x] **Où placer la logique de ping par lots ?** Dans `ClientsActifsService` (pas dans BoucleRooms). BoucleRooms reste une boucle pure de collecte. ClientsActifsService orchestre la validation.
- [x] **BoucleRooms doit-elle changer ?** Non. Elle continue son cycle de 30s inchangé. ClientsActifsService s'abonne à son signal `membres_actualises` (déjà en place).
- [x] **Pipeline synchrone ou asynchrone ?** Asynchrone. Le ping utilise `GetUserStatusCommand` qui est une commande asynchrone aioslsk. `_pinger_par_lots()` est une coroutine, exécutée via `run_coro()` du ConnexionManager.

### Cycle de vie

- [x] **Période du cycle automatique ?** Pas de cycle automatique. Pipeline exécuté **une fois au démarrage**, puis **à la demande**.
- [x] **Comment rafraîchir manuellement ?** Bouton `🔄` dans le widget + intention `rafraîchir clients actifs` dans l'Accueil.
- [x] **Que se passe-t-il au démarrage ?** `BotClientsActifs.demarrer()` → `ClientsActifsService.demarrer()` → attend le prochain signal `membres_actualises` de BoucleRooms → déclenche le pipeline complet.

### Filtrage

- [x] **Critère "actif & joignable" ?** Client répond au ping (`GetUserStatusCommand` réussit) **ET** statut = `UserStatus.ONLINE`. Les clients AWAY, OFFLINE ou UNKNOWN sont exclus même s'ils répondent au ping.
- [x] **Client dans une room mais pas dans la liste pingée ?** Si un client n'a pas été pingé (ex: arrivé après le début du ping), il n'apparaît pas dans la liste filtrée. Il attendra le prochain rafraîchissement.
- [x] **Client qui change de statut après le ping ?** Géré par les événements `UserStatusUpdateEvent` déjà connectés. Le statut se met à jour en temps réel via le signal `client_statut_change`.

### Interface

- [x] **Bouton Rafraîchir dans le widget ?** Oui, dans la barre d'en-tête, côté droit. Icône `🔄`, désactivé pendant l'exécution.
- [x] **Stats à afficher ?** Candidats (membres des rooms) / Actifs & joignables (après ping) / Injouignables (ping échoué ou pas ONLINE).
- [x] **Indicateur d'état ?** Icône `🟢 Prêt` / `🔄 Scan en cours...` / `⏸ Inactif`.

---

## 🔗 Dépendances

- **BoucleRooms** : Déjà implémentée. Fournit `membres_actualises` signal. Cycle 30s.
  - **Bug corrigé** : `_rooms_actuelles` était pris non trié (`[:5]` sur itération dict). Désormais trié par `users` décroissant avant le `[:5]` pour obtenir le vrai top 5 des rooms les plus peuplées.
- **ClientsActifsService** : Existe déjà. À modifier pour ajouter le ping par lots et le filtrage.
- **BotClientsActifs (widget)** : Existe déjà. À modifier pour ajouter le bouton Rafraîchir et les nouvelles stats.
- **BotAccueil** : Existe déjà. À modifier pour ajouter l'intention `rafraichir_clients_actifs`.

---

## 📊 Niveau de complexité

**Niveau 1** (le plus simple des 8 bots)

| Critère | Évaluation |
|---------|-----------|
| Ticks par cycle | 1 seul tick (le pipeline complet est exécuté en une fois) |
| Logique décisionnelle | Simple (ping réussi + ONLINE binaire) |
| État à gérer | Flag `_ping_en_cours` + liste de clients |
| Files modifiées | 2 fichiers service, 2 fichiers widget |
| Risque de saturation | Modéré (rate limiting par lots gère ce risque) |
| Dépendances externes | BoucleRooms (déjà en place) |
