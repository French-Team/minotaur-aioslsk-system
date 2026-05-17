# Plan d'implémentation — Bot Planificateur

> **Statut :** ✅ Service + UI terminés — Bridge Ordonnanceur intégré
> **Dernière mise à jour :** 2026-06-22
> **🟢 10 types d'actions · 712 lignes service · 1 135 lignes UI · 36 tests (9 unitaires + 27 intégration)**

---

## 🎯 Objectif

Le Planificateur est un hub central de gestion des actions planifiées et différées. Il permet de créer, programmer, exécuter et suivre des actions automatisées sur l'ensemble des bots de l'application (recherche, scan, wishlist, optimisation, nettoyage) **et de l'Ordonnanceur** (classement, renommage, déduplication, nettoyage temp).

**Navigation :** Footer (`_BOT_NAMES[7]` — "Planificateur")

---

## 📋 Fonctionnalités

### Dashboard principal
- **État des actions :** Liste des actions avec statut — `en_attente` (file FIFO), `planifiee` (date future), `en_cours`, `pause`, `terminee`, `echouee`
- **Prochaines exécutions :** Liste chronologique des actions planifiées à venir
- **Historique :** Log des actions passées (7 jours de rétention)

### Types d'actions supportés
| Action | Bot cible | Comportement |
|--------|-----------|--------------|
| 🔍 Rechercher sur Soulseek | `BotRecherche` | Lance une recherche avec mots-clés prédéfinis |
| 📂 Scanner la bibliothèque | `BotBibliotheque` | Déclenche un scan des dossiers locaux |
| ⭐ Vérifier la wishlist | `BotWishlist` | Vérifie les items wishlist sur Soulseek |
| ⚙ Appliquer optimisation | `BotOptimiseur` | Applique un profil d'optimisation |
| 📥 Téléchargement | `BotTelechargement` | Gère les téléchargements en cours |
| 📂 Classer artiste/album | `OrdonnanceurService` | Déplace fichiers dans arborescence configurable |
| ✏️ Renommer fichiers | `OrdonnanceurService` | Normalise les noms de fichiers (tags/pattern) |
| 🗑️ Dédoublonner | `OrdonnanceurService` | Supprime doublons par hash SHA256 |
| 🧹 Nettoyer fichiers temp | `OrdonnanceurService` | Supprime fichiers temporaires (âge + extension) |
| 🧹 Nettoyage interne | *Interne* | Supprime fichiers data/tmp/ + doublons rapides (pas de redirection) |

> **Note :** Les actions de l'Ordonnanceur (classement, renommage, déduplication, nettoyage_temp) sont exécutées via le bridge `executer_action_planificateur()` dans `OrdonnanceurService`. Le nettoyage interne reste exécuté directement par le Planificateur.
>
> **Nouveaux types depuis v1 :** `telechargement`, `classement`, `renommage`, `deduplication`, `nettoyage_temp` — ajoutés dans le schéma SQL pour supporter le bridge Ordonnanceur.

### Modes d'exécution
1. **⚡ Immédiat (file d'attente)** : L'action est ajoutée à une file FIFO et exécutée dès que possible (priorité haute)
2. **📅 Planifié (date/récurrence)** : Action différée à une date précise ou récurrente (toutes les X minutes/heures/jours)

Les statuts sont clairement différenciés dans l'UI :
- ⚡ **`en_attente`** — dans la file immédiate, passage prioritaire (icône éclair)
- 📅 **`planifiee`** — programmée pour une date future (icône calendrier)

Quand une action non-nettoyage est exécutée, l'interface **redirige vers le bot spécialisé** concerné via le signal `page_changed`.

### Interface de création (modal QDialog)
Formulaire paramétré avec :
- Type d'action (sélection parmi les types supportés)
- Paramètres spécifiques selon le type :
  - 🔍 Recherche → mots-clés (QLineEdit)
  - ⚙ Optimisation → sélecteur de profil existant (QComboBox, liste des profils disponibles)
  - 📂 Scan → dossier cible (optionnel, scan complet par défaut)
  - 🧹 Nettoyage → options : fichiers temporaires, doublons, les deux
- Mode : ⚡ immédiat ou 📅 planifié (QRadioButton)
- Si planifié : date/heure d'exécution (QDateTimeEdit)
- Récurrence optionnelle : intervalle + unité (QSpinBox + QComboBox : minutes/heures/jours)
- Boutons valider/annuler

### Gestion des actions
- Édition (modifier paramètres, date, récurrence)
- Suppression
- Mise en pause / reprise individuelle
- Pause globale de tout le Planificateur (bouton ⏸ dans la barre d'outils)
- Réordonnancement (changer la priorité dans la file)
- Exécution manuelle immédiate depuis la liste

### Intégration EventBus
Toutes les actions émettent des événements vers l'EventBus (surveillance) :
- `planificateur.action_planifiee` → action programmée
- `planificateur.action_demarree` → action en cours d'exécution
- `planificateur.action_terminee` → action terminée avec succès
- `planificateur.action_echouee` → action en échec avec raison

---

## 📁 Structure du service

### `src/services/planificateur_service.py`
Classe `PlanificateurService(QObject)` — singleton gérant :
- `PlanificationDB` : SQLite (`data/planificateur.db`)

  **Schéma SQL :**
  ```sql
  CREATE TABLE IF NOT EXISTS actions (
      id                  INTEGER PRIMARY KEY AUTOINCREMENT,
      type                TEXT    NOT NULL
                              CHECK(type IN ('recherche','scan','wishlist','optimisation',
                                             'nettoyage','telechargement',
                                             'classement','renommage',
                                             'deduplication','nettoyage_temp')),
      parametres          TEXT    NOT NULL DEFAULT '{}',  -- JSON
      mode                TEXT    NOT NULL CHECK(mode IN ('immediat','planifie')),
      statut              TEXT    NOT NULL DEFAULT 'en_attente'
                              CHECK(statut IN ('en_attente','planifiee','en_cours',
                                               'terminee','echouee','pause')),
      recurrence_interval INTEGER,
      recurrence_unite    TEXT    CHECK(recurrence_unite IN ('minutes','heures','jours')),
      prochaine_execution TIMESTAMP,
      nb_tentatives       INTEGER NOT NULL DEFAULT 0,
      erreur              TEXT,
      nom                 TEXT,          -- nom lisible de l'action
      description         TEXT,          -- description optionnelle
      date_creation       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      date_execution      TIMESTAMP
  );
  CREATE INDEX IF NOT EXISTS idx_actions_statut ON actions(statut);
  CREATE INDEX IF NOT EXISTS idx_actions_prochaine ON actions(prochaine_execution);
  CREATE INDEX IF NOT EXISTS idx_actions_created ON actions(date_creation);
  ```

  > **Évolution du schéma :** La spec initiale prévoyait 5 types d'actions. L'implémentation en a ajouté 5 de plus (`telechargement`, `classement`, `renommage`, `deduplication`, `nettoyage_temp`) pour supporter le bridge avec l'Ordonnanceur, ainsi que les colonnes `nom` et `description`.

  Auto-création du schéma + migration de version (comme `EventBus`).
  Purge automatique des actions terminées ou échouées > 7 jours (timer 1h).

- Méthodes CRUD :
  - `create_action(type, parametres, mode, nom="", description="", recurrence=None, prochaine_execution=None) -> int`
  - `get_action(action_id) -> dict | None`
  - `update_action(action_id, **kwargs) -> bool`
  - `delete_action(action_id) -> bool`
  - `list_actions(statut=None, type=None, limite=50, offset=0) -> list[dict]`
  - `get_historique(limite=50, offset=0) -> list[dict]`
  - `get_stats() -> dict` (compteurs par statut)
  - `get_actions_dues() -> list[dict]` (actions planifiées dont l'heure est passée)
  - `purge_old() -> int` (purge manuelle des actions > 7 jours)
  - `close() -> None` (fermeture de la connexion DB)

- Gestionnaire de planning :
  - Timer Qt vérifiant les actions à exécuter (toutes les 30s)
  - File d'attente FIFO pour les actions immédiates
  - Exécution séquentielle (une action à la fois)
  - **Verrou par type** : ne pas lancer une action si un même type est déjà en cours (évite les doublons)
  - Timeout de 5 minutes par action (si l'action dépasse, marquée comme échouée)
  - Gestion des échecs : max 3 tentatives, délai progressif (30s → 2min → 5min)

- Signal `action_changed(action_id: int, action_type: str, statut: str)` pour l'UI

- Pause globale : `pause()` / `resume()` — suspend le timer de polling + l'exécution de la file

### `src/gui/widgets/bots/bot_planificateur.py`
Classe `BotPlanificateur(QFrame)` — **1 135 lignes** — avec :
- `page_changed = Signal(str)` — navigation vers un autre bot
- `unseen_count_changed = Signal(int)` — badge compteur (actions en erreur non vues)
- Dashboard :
  - Cartes statut : ⚡ en attente, 📅 planifiées, 🔵 en cours, ❌ échouées
  - Liste chronologique des prochaines exécutions
  - Actions récentes (dernières 24h)
  - Bouton "➕ Nouvelle action"
- Barre d'outils :
  - 🔍 Recherche textuelle avec debounce 300ms
  - ⏸ Pause globale (bascule, suspend toutes les exécutions automatiques)
- Liste des actions avec :
  - Filtres par statut (QComboBox ou toggles)
  - Icône par type : 🔍📂⭐⚙🧹
  - Colonnes : type, nom/paramètres, statut (⚡📅🔵✅❌⏸), prochaine exécution, actions
  - Barre d'actions par ligne : ▶ Exécuter, ✏ Éditer, ⏸ Pause/Reprendre, 🗑 Supprimer
  - Tri par date, statut, type
- Badge footer connecté : `unseen_count_changed` → `center._update_planificateur_badge()` → `footer.set_badge("Planificateur", count)`, reset quand la page devient active
- Modal `ActionForm(QDialog)` : création/édition d'action
- Modal `ActionDetail(QDialog)` : consultation détaillée d'une action
- Connecté au service via `self._svc = PlanificateurService()` (singleton)
- Signal `action_changed` connecté à `_on_action_changed()` pour rafraîchir la liste en direct
- Appel `self._svc.execute_manual(action_id)` pour exécution manuelle depuis l'UI

---

## 📁 Fichiers concernés

### Créations
| Fichier | Étape | Description |
|---------|-------|-------------|
| `specs/bot-planificateur-spec.md` | - | Ce document |
| `src/services/planificateur_service.py` | 1 | Service + base de données |
| `src/gui/widgets/bots/bot_planificateur.py` | 2 | Widget UI complet |

### Modifications
| Fichier | Étape | Changement |
|---------|-------|------------|
| `src/gui/widgets/bots/__init__.py` | 2 | Ajouter `BotPlanificateur` |
| `src/gui/layout/center.py` | 2 | Ajouter `_build_planificateur_page()` + `_update_planificateur_badge()` |
| `src/services/event_bus.py` | 7 | Connexion des événements planificateur |
| `src/services/ordonnanceur_service.py` | 9 | Bridge `executer_action_planificateur()` — 4 nouveaux types d'action |
| `tests/test_integration_planificateur_ordonnanceur.py` | 10 | 27 tests d'intégration Planificateur ↔ Ordonnanceur |

---

## 📋 Liste des étapes — État réel

### Étape 1 — Service PlanificateurService ✅
- [x] Créer `src/services/planificateur_service.py` — **712 lignes**
  - [x] Classe singleton `PlanificateurService(QObject)` — gestion SQLite avec le schéma ci-dessus
  - [x] Signal `action_changed(action_id: int, action_type: str, statut: str)`
  - [x] Méthodes CRUD complètes : `create_action`, `get_action`, `update_action`, `delete_action`, `list_actions`, `get_historique`, `get_stats`, `get_actions_dues`, `purge_old`, `close`
  - [x] Timer de vérification des actions planifiées (30s)
  - [x] File d'attente FIFO pour exécution séquentielle
  - [x] Timeout 5min par action
  - [x] Gestion échecs : max 3 tentatives, backoff (30s → 2min → 5min)
  - [x] Purge auto des actions > 7 jours (timer 1h)
  - [x] Pause globale (`pause()` / `resume()`)
  - [x] ✅ 9 tests unitaires dans `tests/test_planificateur.py`

### Étape 2 — BotPlanificateur UI + Registration ✅
- [x] Créer `src/gui/widgets/bots/bot_planificateur.py` — **1 135 lignes**
  - [x] Classe `BotPlanificateur(QFrame)` avec `page_changed` et `unseen_count_changed`
  - [x] Dashboard complet avec cartes statut, barre d'outils, liste d'actions
- [x] Modifier `src/gui/widgets/bots/__init__.py` — import + export `BotPlanificateur`
- [x] Modifier `src/gui/layout/center.py` — `_build_planificateur_page()` + `_update_planificateur_badge()`

### Étape 3 — Dashboard + Barre d'outils ✅
- [x] `_build_stats_bar()` — 4 cartes : ⚡ en attente, 📅 planifiées, 🔵 en cours, ❌ échouées
- [x] `_build_toolbar()` : 🔍 recherche debounce 300ms, ⏸ pause globale, ➕ nouvelle action
- [x] `_build_dashboard()` — cartes statut + liste chronologique
- [x] Badge footer connecté (`unseen_count_changed` → `center._update_planificateur_badge()`)
- [x] Reset du badge quand la page devient active

### Étape 4 — Liste des actions ✅
- [x] `_build_action_list()` — QTableWidget
- [x] Colonnes : icône type, nom/paramètres, statut, prochaine exécution, actions
- [x] Filtres par statut + recherche textuelle debounce 300ms
- [x] Colorisation par statut et type d'action
- [x] Tri cliquable sur les en-têtes

### Étape 5 — Modal Nouvelle Action / Édition ✅
- [x] `ActionForm(QDialog)` — sélecteur type (🔍📂⭐⚙📥📂✏️🗑️🧹), champs dynamiques
- [x] Mode : ⚡ immédiat / 📅 planifié + date + récurrence
- [x] Validation des champs + mode édition
- [x] Connecté aux boutons "➕ Nouvelle action" et ✏ de chaque ligne

### Étape 6 — Moteur d'exécution séquentielle ✅
- [x] File FIFO : actions immédiates passent devant les planifiées
- [x] Exécution séquentielle (une à la fois)
- [x] Timeout 5 minutes par action
- [x] Gestion échecs : max 3 tentatives, backoff (30s → 2min → 5min)
- [x] **Verrou par type** : pas de lancement si même type déjà en cours
- [x] Pause globale : suspend timer + exécution
- [x] Timer polling 30s pour actions planifiées

### Étape 6 — Moteur d'exécution séquentielle + File d'attente
- [ ] Implémenter le moteur d'exécution
  - [ ] File FIFO : les actions immédiates passent devant les planifiées
  - [ ] Exécution séquentielle (une à la fois, blocage si une action est en cours)
  - [ ] Timeout 5 minutes — si l'action dépasse, marquée `echouee`
  - [ ] Gestion des échecs : max 3 tentatives, délai progressif (30s → 2min → 5min)
  - [ ] Actions bloquantes : ne pas lancer une action si un même type est déjà en cours
  - [ ] Pause globale : suspend la vérification du timer et l'exécution de la file
- [ ] Timer de polling pour actions planifiées (30s)
- [ ] ✅ Validation : py_compile + tests unitaires d'exécution

### Étape 7 — Connexion EventBus + Navigation inter-bots ✅
- [x] Connecter `PlanificateurService` à l'EventBus
  - [x] Création → `planificateur.action_planifiee` (ou `action_en_attente` si mode immédiat)
  - [x] Démarrage → `planificateur.action_demarree`
  - [x] Succès → `planificateur.action_terminee`
  - [x] Échec → `planificateur.action_echouee` (avec raison dans le message)
- [x] Navigation inter-bots via `page_changed.emit(nom_bot)`
- [x] Tous les événements catégorie `"bot"` avec sévérité `INFO` / `WARN` / `ERROR`

### Étape 8 — Tests & Polish ✅
- [x] Purge SQLite 7 jours vérifiée
- [x] Comportement actions planifiées multiples
- [x] File FIFO (priorité immédiat > planifié)
- [x] Édition et suppression d'actions
- [x] Navigation inter-bots
- [x] Événements EventBus
- [x] Timeout 5min + backoff tentatives
- [x] Pause globale
- [x] Badge footer (incrément/reset)
- [x] Code review complète
- [x] **9 tests unitaires** dans `tests/test_planificateur.py`

### Étape 9 — Bridge Ordonnanceur ✅
- [x] Ajouter 5 nouveaux types d'action au schéma SQL : `telechargement`, `classement`, `renommage`, `deduplication`, `nettoyage_temp`
- [x] `OrdonnanceurService.executer_action_planificateur()` — bridge appelé par le Planificateur
- [x] 4 actions redirigées vers l'Ordonnanceur : classement, renommage, déduplication, nettoyage_temp
- [x] Colonnes `nom` et `description` ajoutées au schéma SQL

### Étape 10 — Tests d'intégration ✅
- [x] `tests/test_integration_planificateur_ordonnanceur.py` — **27 tests**
  - [x] `TestExecuterActionPlanificateur` (14 tests) : tous les types, edge cases, callbacks
  - [x] `TestPlanificateurWorker` (2 tests) : signal succes, exception
  - [x] `TestPlanificateurReceiver` (3 tests) : complete_action succès/échec/introuvable
  - [x] `TestConnecteurPlanificateur` (3 tests) : filtres statut, type, action introuvable
  - [x] `TestIntegrationPlanificateurOrdonnanceur` (5 tests) : cycle complet création→exécution

---

## 🐛 Problèmes connus

| # | Problème | Statut |
|---|----------|--------|
| 1 | **PermissionError Windows en teardown de test** — Le SQLite WAL journal verrouille le fichier temporaire. Les 27 tests d'intégration passent logiquement mais 2 erreurs de teardown apparaissent sur Windows. Solution : checkpoint WAL + close() explicite dans le cleanup. | ⚠️ Cosmétique |
| 2 | **Schéma SQL étendu au-delà de la spec initiale** — 10 types au lieu de 5, colonnes `nom`/`description` ajoutées. La spec a été mise à jour pour refléter l'état réel. | ✅ Résolu (ce document) |

---

## 📝 Notes de conception

- **PlanificateurService** : Singleton accessible via `PlanificateurService()`, tout dans le thread Qt
- **SQLite** : Fichier `data/planificateur.db`, schéma créé automatiquement avec migration (comme EventBus)
  - Index sur `statut`, `prochaine_execution`, `date_creation` pour des requêtes rapides
- **Récurrence** : Pas de cron complet — intervalle simple (X minutes/heures/jours) + date unique
- **Exécution** : Séquentielle — une action à la fois. Les actions immédiates (file FIFO) passent avant les planifiées
- **Timeout** : 5 minutes par action. Si dépassé → `echouee` avec raison "Timeout dépassé"
- **Tentatives** : max 3, avec backoff : 30s → 2min → 5min entre chaque tentative
- **Pause globale vs individuelle** : La pause globale (`PlanificateurService._paused = True`) stoppe le timer de polling + l'exécution de la file. Elle **override** les pauses individuelles — aucune action ne peut démarrer, même celles qui ne sont pas en pause individuelle. Les actions en cours terminent normalement. Quand la pause globale est désactivée, les actions mises en pause individuellement le restent jusqu'à leur reprise manuelle
- **Navigation** : Quand une action non-nettoyage est exécutée, `page_changed.emit("Recherche")` (ou autre) redirige vers le bot concerné
- **Badge footer** : Incrémenté à chaque action `echouee` quand la page Planificateur n'est pas active. Reset au `show_page("Planificateur")`
- **Nettoyage** : Action exécutée en interne par le Planificateur (pas de bot dédié). Supprime fichiers sous `data/tmp/` et les doublons détectés dans la bibliothèque
- **Polices** : `QFont("Segoe UI", 10)` pour les listes, `QFont("Segoe UI", 9)` pour les timestamps
- **Couleurs** : Utiliser `COLORS` depuis `theme_fragments/colors.py` :
  - `en_attente` → `WARNING` / `WARNING_BG`
  - `planifiee` → `ACCENT`
  - `en_cours` → `STAT_AUDIO`
  - `terminee` → `SUCCESS`
  - `echouee` → `DANGER` / `DANGER_BG`
  - `pause` → `TEXT_MUTED`
- **Icônes types** : 🔍 Recherche, 📂 Scan, ⭐ Wishlist, ⚙ Optimisation, 📥 Téléchargement, 📂 Classement, ✏️ Renommage, 🗑️ Dédoublonnage, 🧹 Nettoyage temp, 🧹 Nettoyage interne
- **Icônes modes** : ⚡ Immédiat (file FIFO), 📅 Planifié (date future)
- **Bridge Ordonnanceur** : Les 4 actions Ordonnanceur (classement, renommage, déduplication, nettoyage_temp) sont exécutées via `OrdonnanceurService.executer_action_planificateur()` qui analyse le dossier, génère un aperçu et exécute les opérations


## ❓ Questions résolues

### Architecture et stockage

- [x] **PlanificateurService singleton avec SQLite** : Le Planificateur a besoin d'une persistance fiable pour les actions programmées. SQLite offre des requêtes filtrées (par statut, type, date) avec des index performants pour des centaines d'actions. JSON serait trop lent à filtrer et ne permettrait pas de requêtes complexes (ex : « toutes les actions planifiées avant telle heure »).
- [x] **10 types d'actions (5 initiaux + 5 ajoutés) avec CHECK dans le schéma SQL** : La contrainte CHECK dans la colonne `type` assure l'intégrité des données au niveau de la base. Impossible d'insérer un type invalide. L'extension de 5 à 10 types a été faite par migration de schéma (support du bridge Ordonnanceur).
- [x] **Colonnes nom et description ajoutées au schéma** : Permettent à l'utilisateur de nommer et décrire ses actions pour une meilleure lisibilité dans l'UI. Sans ces colonnes, les actions seraient identifiées uniquement par leur type et paramètres — peu lisible pour des actions planifiées récurrentes.
- [x] **Index sur statut, prochaine_execution, date_creation** : Les requêtes les plus fréquentes sont le filtrage par statut (liste des actions en attente) et la recherche des actions planifiées arrivées à échéance. Les index accélèrent significativement ces requêtes sur des volumes de plusieurs centaines d'actions.
- [x] **Purge automatique des actions > 7 jours (timer 1h)** : Évite l'accumulation d'actions terminées ou échouées dans la base. La rétention de 7 jours laisse un historique suffisant pour le débogage. Le timer de 1h est un bon compromis entre réactivité et charge.
- [x] **Timer de polling 30s pour les actions planifiées** : Un timer toutes les 30s vérifie si des actions planifiées doivent être exécutées. Un intervalle plus court (1s) serait excessif pour une vérification qui concerne des actions horaires ou quotidiennes. Plus long (5min) créerait un décalage trop important.

### Types d'actions et exécution

- [x] **10 types d'actions : recherche, scan, wishlist, optimisation, téléchargement, classement, renommage, déduplication, nettoyage temp, nettoyage interne** : Les 5 premiers (recherche, scan, wishlist, optimisation, nettoyage) couvrent les bots existants. Les 5 suivants (téléchargement, classement, renommage, déduplication, nettoyage temp) étendent le Planificateur vers l'Ordonnanceur via un bridge. Chaque type a une icône dédiée et des paramètres spécifiques.
- [x] **Bridge Ordonnanceur via OrdonnanceurService.executer_action_planificateur()** : Les actions d'Ordonnanceur (classement, renommage, déduplication, nettoyage temp) ne sont pas exécutées directement par le Planificateur. Elles sont déléguées à `OrdonnanceurService` qui analyse le dossier, génère un aperçu et exécute les opérations. Évite la duplication de logique et maintient la séparation des responsabilités.
- [x] **Nettoyage interne exécuté directement par le Planificateur (pas de délégation)** : Le nettoyage interne (suppression des fichiers `data/tmp/` et doublons rapides) est une opération simple qui ne nécessite pas de bot dédié. Le Planificateur l'exécute lui-même, contrairement aux actions spécifiques qui redirigent vers leurs bots respectifs.
- [x] **Verrou par type : pas de lancement si même type déjà en cours** : Empêche les doublons (ex : deux scans lancés simultanément). Sans ce verrou, l'utilisateur pourrait accidentellement lancer plusieurs fois la même action, créant des conflits ou des opérations redondantes.
- [x] **Navigation inter-bots via page_changed pour les actions non-nettoyage** : Quand une action est exécutée, l'UI redirige vers le bot spécialisé concerné (ex : « Recherche » pour une action de recherche). Le nettoyage interne reste sur la page Planificateur car il n'a pas de bot dédié.

### Modes et file d'attente

- [x] **Deux modes : immédiat (file FIFO) et planifié (date/récurrence)** : Le mode immédiat met l'action dans une file d'attente avec priorité haute. Le mode planifié programme l'action pour une date précise, avec récurrence optionnelle. Les statuts sont différenciés dans l'UI : ⚡ « en_attente » pour la file FIFO, 📅 « planifiée » pour les actions futures.
- [x] **File FIFO séquentielle : une action à la fois** : Les actions sont exécutées une par une dans l'ordre d'arrivée. Évite la contention sur les ressources partagées (Soulseek, base de données, disque). Les actions immédiates passent avant les planifiées arrivées à échéance.
- [x] **Timeout de 5 minutes par action** : Si une action dépasse 5 minutes, elle est marquée « échouée » avec la raison « Timeout dépassé ». Empêche une action bloquante de paralyser la file indéfiniment. 5 minutes est un délai suffisant pour la plupart des actions (recherche, scan, optimisation).
- [x] **Max 3 tentatives avec backoff progressif (30s → 2min → 5min)** : Une action qui échoue peut être réessayée automatiquement. Le backoff progressif évite de surcharger le système en cas d'échecs répétés. Après 3 échecs, l'action est définitivement marquée « échouée ».

### Pause et contrôle

- [x] **Pause globale (override les pauses individuelles)** : La pause globale stoppe le timer de polling et l'exécution de la file. Aucune action ne peut démarrer, même celles qui ne sont pas en pause individuelle. Les actions en cours terminent normalement. Quand la pause globale est désactivée, les actions en pause individuelle le restent.
- [x] **Pause individuelle par action** : Permet de suspendre une action spécifique sans impacter les autres. Utile pour désactiver temporairement une action récurrente sans la supprimer.
- [x] **Exécution manuelle depuis la liste (bouton ▶)** : L'utilisateur peut forcer l'exécution immédiate d'une action depuis la liste, même si elle est planifiée ou en pause. Outrepasse temporairement le planning et l'état de pause individuelle.

### Intégration et UI

- [x] **Dashboard 4 cartes statut (⚡ en attente, 📅 planifiées, 🔵 en cours, ❌ échouées)** : Les 4 états les plus pertinents pour l'utilisateur : ce qui l'attend, ce qui est programmé, ce qui est en cours, ce qui a échoué. Les statuts « terminée » et « pause » sont visibles dans la liste mais moins critiques pour un résumé rapide.
- [x] **ActionModal (QDialog) pour la création/édition d'actions** : Un modal dédié avec des champs qui changent dynamiquement selon le type d'action sélectionné (ex : mots-clés pour recherche, profil pour optimisation, dossier pour scan). Permet une validation centralisée avant création.
- [x] **Badge footer connecté via unseen_count_changed** : Le badge s'incrémente à chaque action échouée quand la page Planificateur n'est pas active. Il se réinitialise quand l'utilisateur ouvre la page. Permet à l'utilisateur de savoir immédiatement qu'une action a échoué sans surveiller constamment la liste.
- [x] **Événements EventBus (4 types : planifiée, démarrée, terminée, échouée)** : Les actions du Planificateur émettent des événements vers l'EventBus pour la surveillance centralisée. L'utilisateur peut voir l'activité du Planificateur dans le fil d'actualités (Bot Surveillance).
