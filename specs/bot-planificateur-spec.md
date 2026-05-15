# Plan d'implémentation — Bot Planificateur

> **Statut :** 🔄 En cours
> **Dernière mise à jour :** Session en cours
> **Ce document évolue à chaque étape.**

---

## 🎯 Objectif

Le Planificateur est un hub central de gestion des actions planifiées et différées. Il permet de créer, programmer, exécuter et suivre des actions automatisées sur l'ensemble des bots de l'application (recherche, scan, wishlist, optimisation, nettoyage).

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
| 🧹 Nettoyer fichiers | *Interne* | Supprime fichiers temporaires/doublons directement (pas de redirection) |

> **Note :** L'action "Nettoyage" est exécutée **directement par le Planificateur** (service interne), contrairement aux autres actions qui redirigent vers le bot spécialisé. Aucun bot dédié n'existe actuellement pour le nettoyage.

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
      id              INTEGER PRIMARY KEY AUTOINCREMENT,
      type            TEXT    NOT NULL CHECK(type IN ('recherche','scan','wishlist','optimisation','nettoyage')),
      parametres      TEXT    NOT NULL DEFAULT '{}',   -- JSON
      mode            TEXT    NOT NULL CHECK(mode IN ('immediat','planifie')),
      statut          TEXT    NOT NULL DEFAULT 'en_attente'
                              CHECK(statut IN ('en_attente','planifiee','en_cours','terminee','echouee','pause')),
      recurrence_interval INTEGER,                     -- NULL si unique
      recurrence_unite    TEXT CHECK(recurrence_unite IN ('minutes','heures','jours')),  -- NULL si unique
      prochaine_execution TIMESTAMP,
      nb_tentatives   INTEGER NOT NULL DEFAULT 0,
      erreur          TEXT,
      date_creation   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      date_execution  TIMESTAMP
  );
  CREATE INDEX IF NOT EXISTS idx_actions_statut ON actions(statut);
  CREATE INDEX IF NOT EXISTS idx_actions_prochaine ON actions(prochaine_execution);
  CREATE INDEX IF NOT EXISTS idx_actions_created ON actions(date_creation);
  ```

  Auto-création du schéma + migration de version (comme `EventBus`).
  Purge automatique des actions terminées ou échouées > 7 jours (timer 1h).

- Méthodes CRUD :
  - `create_action(type, parametres, mode, recurrence=None) -> int`
  - `get_action(action_id) -> dict | None`
  - `update_action(action_id, **kwargs) -> bool`
  - `delete_action(action_id) -> bool`
  - `list_actions(statut=None, type=None, limite=50, offset=0) -> list[dict]`
  - `get_historique(limite=50, offset=0) -> list[dict]`
  - `get_stats() -> dict` (compteurs par statut)

- Gestionnaire de planning :
  - Timer Qt vérifiant les actions à exécuter (toutes les 30s)
  - File d'attente FIFO pour les actions immédiates
  - Exécution séquentielle (une action à la fois)
  - Timeout de 5 minutes par action (si l'action dépasse, marquée comme échouée)
  - Gestion des échecs : max 3 tentatives, délai progressif (30s → 2min → 5min)

- Signal `action_changed(action_id: int, action_type: str, statut: str)` pour l'UI

### `src/gui/widgets/bots/bot_planificateur.py`
Classe `BotPlanificateur(QFrame)` avec :
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

---

## 📋 Liste des étapes

### Étape 1 — Service PlanificateurService
- [ ] Créer `src/services/planificateur_service.py`
  - [ ] Classe `PlanificationDB` — gestion SQLite avec le schéma défini ci-dessus
  - [ ] Classe `PlanificateurService(QObject)` — singleton
  - [ ] Signal `action_changed(action_id: int, action_type: str, statut: str)`
  - [ ] Méthodes CRUD complètes + `get_stats()`
  - [ ] Timer de vérification des actions planifiées (30s)
  - [ ] File d'attente FIFO pour exécution séquentielle
  - [ ] Timeout 5min par action
  - [ ] Gestion échecs : max 3 tentatives, backoff (30s → 2min → 5min)
  - [ ] Purge auto des actions > 7 jours (timer 1h)
  - [ ] Pause globale (`pause()` / `resume()`)
  - [ ] ✅ Validation : py_compile + 10 tests unitaires

### Étape 2 — Squelette BotPlanificateur + Registration
- [ ] Créer `src/gui/widgets/bots/bot_planificateur.py`
  - [ ] Classe `BotPlanificateur(QFrame)` avec `page_changed` et `unseen_count_changed`
  - [ ] Dashboard provisoire "🚧 à construire"
- [ ] Modifier `src/gui/widgets/bots/__init__.py`
  - [ ] Importer `BotPlanificateur`
  - [ ] Ajouter à `__all__`
- [ ] Modifier `src/gui/layout/center.py`
  - [ ] Importer `BotPlanificateur`
  - [ ] Ajouter `_build_planificateur_page()`
  - [ ] Ajouter `_update_planificateur_badge(count)` (connexion badge → footer)
  - [ ] Appel dans `__init__`
- [ ] ✅ Validation : py_compile + import réussi

### Étape 3 — Dashboard + Barre d'outils
- [ ] Implémenter `_build_stats_bar()` — 4 cartes : ⚡ en attente, 📅 planifiées, 🔵 en cours, ❌ échouées
- [ ] Implémenter `_build_toolbar()`
  - [ ] 🔍 Recherche textuelle avec debounce 300ms
  - [ ] ⏸ Bouton Pause globale (bascule, icône change)
  - [ ] ➕ Bouton "Nouvelle action"
- [ ] Implémenter `_build_dashboard()` — 4 cartes statut + liste chronologique des prochaines exécutions
- [ ] Connecter le badge `unseen_count_changed` au footer via `center._update_planificateur_badge()`
- [ ] Reset du badge quand la page Planificateur devient active
- [ ] ✅ Validation : py_compile + vérification visuelle

### Étape 4 — Liste des actions
- [ ] Implémenter `_build_action_list()` — QTableWidget
- [ ] Colonnes : icône type, nom/paramètres, statut (⚡📅🔵✅❌⏸), prochaine exécution, actions (▶✏⏸🗑)
- [ ] Filtres par statut (QComboBox ou toggles)
- [ ] Recherche textuelle avec debounce 300ms
- [ ] Colorisation par statut (couleurs COLORS) et type d'action
- [ ] Tri cliquable sur les en-têtes de colonnes
- [ ] ✅ Validation : py_compile + simulation

### Étape 5 — Modal Nouvelle Action / Édition
- [ ] Créer `ActionForm(QDialog)`
  - [ ] Sélecteur type d'action (QComboBox : 🔍📂⭐⚙🧹)
  - [ ] Champs dynamiques selon le type :
    - 🔍 Recherche → mots-clés (QLineEdit)
    - ⚙ Optimisation → sélecteur profil (QComboBox, chargé depuis `BotOptimiseur`)
    - 📂 Scan → dossier cible (QLineEdit, optionnel)
    - 🧹 Nettoyage → options : temporaires, doublons, les deux (QCheckBox)
  - [ ] Mode : ⚡ immédiat / 📅 planifié (QRadioButton)
  - [ ] Date/heure d'exécution (QDateTimeEdit, visible si mode planifié)
  - [ ] Récurrence : intervalle + unité (QSpinBox + QComboBox, visible si planifié)
  - [ ] Validation des champs (type requis, mots-clés requis si recherche, etc.)
  - [ ] Mode édition : pré-remplir les champs depuis une action existante
- [ ] Connecter au bouton "➕ Nouvelle action" et au bouton ✏ de chaque ligne
- [ ] ✅ Validation : py_compile + test ouverture/fermeture + test validation

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

### Étape 7 — Connexion EventBus + Navigation inter-bots
- [ ] Connecter `PlanificateurService` à l'EventBus
  - [ ] Création → `planificateur.action_planifiee`
  - [ ] Démarrage → `planificateur.action_demarree`
  - [ ] Succès → `planificateur.action_terminee`
  - [ ] Échec → `planificateur.action_echouee` (avec raison dans le message)
- [ ] Navigation : clic "▶ Exécuter" ou exécution automatique → redirige vers le bot spécialisé
  - [ ] 🔍 Recherche → `page_changed.emit("Recherche")`
  - [ ] 📂 Scan → `page_changed.emit("Bibliothèque")`
  - [ ] ⭐ Wishlist → `page_changed.emit("Wishlist")`
  - [ ] ⚙ Optimisation → `page_changed.emit("Optimiseur")`
  - [ ] 🧹 Nettoyage → pas de redirection (interne)
- [ ] ✅ Validation : py_compile + simulation

### Étape 8 — Tests & Polish
- [ ] Vérifier la purge SQLite 7 jours
- [ ] Vérifier le comportement avec actions planifiées multiples
- [ ] Vérifier la file d'attente FIFO (priorité immédiat > planifié)
- [ ] Vérifier l'édition et suppression d'actions
- [ ] Vérifier la navigation inter-bots
- [ ] Vérifier les événements EventBus
- [ ] Vérifier le timeout 5min et le backoff des tentatives
- [ ] Vérifier la pause globale
- [ ] Vérifier le badge footer (incrément/reset)
- [ ] Code review complète
- [ ] ✅ Validation : tous les tests verts

---

## 🐛 Problèmes connus

*Aucun pour l'instant — à remplir au fil de l'implémentation.*

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
- **Icônes types** : 🔍 Recherche, 📂 Scan, ⭐ Wishlist, ⚙ Optimisation, 🧹 Nettoyage
- **Icônes modes** : ⚡ Immédiat (file FIFO), 📅 Planifié (date future)
