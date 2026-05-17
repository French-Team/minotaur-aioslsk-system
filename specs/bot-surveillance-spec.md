# Plan d'implémentation — Bot Surveillance

> **Statut :** 🔄 En cours  
> **Dernière mise à jour :** Session en cours  
> **Ce document évolue à chaque étape.**

---

## 🎯 Objectif

Bot watcher centralisé qui surveille tout ce qui se passe dans le projet aioslsk.  
Hub de monitoring affichant un flux d'événements en temps réel, avec historique SQLite, filtres, et notifications.

**Navigation :** Footer (`_BOT_NAMES[7]`), pas de bouton dans la barre latérale gauche.

---

## 📋 Liste des étapes

### Étape 1 — Service EventBus (`src/services/event_bus.py`)

- [x] Créer `src/services/event_bus.py`
  - [x] Classe `SurveillanceEvent` (dataclass)
  - [x] Classe `EventBus(QObject)` avec signal `event_emitted`
  - [x] Connexion SQLite avec auto-création du schéma
  - [x] Méthodes : `emit_event()`, `query()`, `get_recent()`, `get_stats()`, `purge_old()`, `get_event()`, `delete_events()`
  - [x] Timer de purge automatique (1h)
  - [x] Singleton pattern (utilisation globale)
  - [x] ✅ Validation : py_compile + 10 tests unitaires OK

### Étape 2 — Squelette BotSurveillance + Registration

- [x] Créer `src/gui/widgets/bots/bot_surveillance.py`
  - [x] Classe `BotSurveillance(QFrame)` avec signal `page_changed`, placeholder UI "🚧 à construire"
  - [x] Page visible dans le stack via footer (clé `"Surveillance"`)
- [x] Modifier `src/gui/widgets/bots/__init__.py`
  - [x] Importer `BotSurveillance`
  - [x] Ajouter à `__all__`
- [x] Modifier `src/gui/layout/center.py`
  - [x] Importer `BotSurveillance`
  - [x] Ajouter `_build_surveillance_page()` avec registration dans `_pages["Surveillance"]` et `_stack`
  - [x] Appel dans `__init__` après `_build_optimiseur_page()`
- [x] ✅ Validation : py_compile (3 fichiers) + import réussi + pas de conflit avec `_build_menu_page` (Surveillance absent du tuple des placeholders)

### Étape 3 — Barre d'indicateurs + Barre d'outils

- [x] Implémenter `_build_stats_bar()`
  - [x] Badge Erreurs (rouge, sévérité ERROR)
  - [x] Badge Avertissements (orange, sévérité WARN)
  - [x] Badge Total (violet, événements du jour)
  - [x] Bouton ⏸ Pause (bascule, suspend collection ET affichage)
- [x] Implémenter `_build_toolbar()`
  - [x] 🔍 Champ recherche textuelle avec debounce 300ms
  - [x] Filtres catégories toggle : 🌐📥🔎📚⚙️❌🤖
  - [x] 📅 Bouton Historique
  - [x] 🗑 Bouton Vider le flux
- [x] ✅ Validation : py_compile + vérification visuelle
- [x] EventBus.pause()/resume() ajoutés + check dans emit_event (retourne None si en pause)

### Étape 4 — Flux d'événements (compact cards + auto-scroll) ✅

- [x] Implémenter `_build_feed()` — zone défilante
- [x] Implémenter `_on_event(event)` — réception et insertion
- [x] Implémenter `_create_event_card(event)` — ligne compacte
  - [x] Icône sévérité : 🔴🟡🟢
  - [x] Timestamp `[HH:MM:SS]` avec tooltip date complète
  - [x] Titre en gras
  - [x] Message court sur la même ligne
  - [x] Boutons hover : 📋 Copier, 🔍 Détails
- [x] Implémenter auto-scroll intelligent
  - [x] Auto-scroll par défaut
  - [x] Suspension si l'utilisateur scroll vers le haut
  - [x] Bouton ⬇ Retour en bas
- [x] Connecter le flux à l'EventBus
- [x] ✅ Validation : py_compile + simulation d'événements

### Étape 5 — Popup Détails ✅

- [x] Créer classe `DetailPopup(QDialog)`
  - [x] Affiche : titre, message, source, catégorie, sévérité, date précise
  - [x] Bouton 📋 Copier (copie formatée)
  - [x] Bouton 🔗 Naviguer (si applicable)
- [x] Connecter le bouton 🔍 des cartes à ce popup
- [x] ✅ Validation : py_compile + test d'ouverture

### Étape 6 — Modal Historique ✅

- [x] Créer classe `HistoryModal(QDialog)`
  - [x] 🔍 Recherche textuelle
  - [x] 📅 Filtre par date (de → à, QDateEdit)
  - [x] 🏷 Filtre par catégorie (QComboBox)
  - [x] Tableau/liste avec cases à cocher
  - [x] Boutons 📋 Exporter CSV / 📋 Exporter JSON
  - [x] Pagination (50 par page, bouton "Charger plus")
  - [x] Bouton 🗑 Supprimer sélection
- [x] Connecter le bouton 📅 Historique à cette modal
- [x] ✅ Validation : py_compile + test CRUD

### Étape 7 — Connexion aux services (signaux externes) ✅

- [x] Connecter `connexion_manager` à l'EventBus
  - [x] `connected` → émission EventBus
  - [x] `disconnected` → émission EventBus
  - [x] `error_occurred` → émission EventBus
  - [x] `status_changed` → émission EventBus
- [x] Connecter `soulseek_client` à l'EventBus
  - [x] `transfer_added` → émission EventBus
  - [x] `transfer_removed` → émission EventBus
  - [x] `transfer_progress` → émission EventBus (seulement début/fin, pas chaque progression)
- [x] ✅ Validation : py_compile + simulation de connexion/déconnexion

### Étape 8 ✅ — Connexion aux autres bots (événements inter-bots)

- [x] Connecter `BotRecherche` → EventBus (recherche lancée/terminée)
- [x] Connecter `BotWishlist` → EventBus (wishlist trouvé, erreur)
- [x] Connecter `BotBibliotheque` → EventBus (scan démarré/terminé)
- [x] Connecter `BotOptimiseur` → EventBus (profil appliqué, erreur)
- [x] ✅ Validation : py_compile + test inter-bots

### Étape 9 — Alertes hors-page

- [ ] Badge compteur dans le footer
  - [ ] Modifier `FooterZone` pour afficher un compteur (ex: "Surveillance (3)")
  - [ ] Réinitialiser le compteur quand la page Surveillance devient active
- [ ] Toast popup pour les événements ERROR
  - [ ] Créer un widget toast (coin supérieur droit, 3s, cliquable → navigation)
  - [ ] Connecter à l'EventBus pour les événements de sévérité ERROR
- [ ] ✅ Validation : py_compile + test d'affichage toast

### Étape 10 — Tests & Polish

- [ ] Vérifier la purge SQLite 7 jours
- [ ] Vérifier le comportement en pause totale
- [ ] Vérifier les performances avec 200+ événements dans le flux
- [ ] Vérifier le comportement au démarrage (flux vide, bouton Historique)
- [ ] Vérifier l'export CSV/JSON
- [ ] Code review complète
- [ ] ✅ Validation : tout fonctionne de bout en bout

---

## 📁 Fichiers concernés

### Créations
| Fichier | Étape |
|---------|-------|
| `src/services/event_bus.py` | 1 |
| `src/gui/widgets/bots/bot_surveillance.py` | 2 |

### Modifications
| Fichier | Étape | Changement |
|---------|-------|------------|
| `src/gui/widgets/bots/__init__.py` | 2 | Ajouter `BotSurveillance` |
| `src/gui/layout/center.py` | 2 | Ajouter page au stack |
| `src/gui/layout/footer.py` | 9 | Badge compteur |
| `src/services/connexion_manager.py` | 7 | Émettre vers EventBus |
| `src/services/soulseek_client.py` | 7 | Émettre vers EventBus |

---

## 🐛 Problèmes connus

*Aucun pour l'instant — à remplir au fil de l'implémentation.*

---

## 📝 Notes de conception

- **EventBus** : Singleton accessible via `EventBus()`, thread-safe (tout est dans le thread Qt)
- **SQLite** : Fichier `data/bot_surveillance.db`, schéma créé automatiquement
- **Pause** : Quand `_paused = True`, l'EventBus continue de recevoir mais `BotSurveillance` ignore les événements (ils sont perdus)
- **Compteur footer** : Incrémenté à chaque nouvel événement reçu quand la page Surveillance n'est pas active
- **Toast** : Widget `QFrame` avec timer 3s, animation de fondu, positionné en haut à droite de la fenêtre principale
- **Polices** : `QFont("Segoe UI", 10)` pour le flux, `QFont("Segoe UI", 9)` pour les timestamps
- **Couleurs** : Utiliser `COLORS` depuis `theme_fragments/colors.py` :
  - ERROR → `DANGER` / `DANGER_BG`
  - WARN → `WARNING`
  - INFO → `SUCCESS`
  - Badges → `STAT_FILES` / `STAT_AUDIO` / `ACCENT`

---

## ❓ Questions résolues

### Architecture et événements

- [x] **EventBus singleton (QObject) plutôt que signaux Qt dispersés** : Un bus d’événements centralisé évite de connecter chaque service à chaque bot individuellement. Le pattern singleton garantit une instance unique accessible de partout. QObject permet d’utiliser les signaux Qt natifs (thread-safe dans le thread Qt).

- [x] **SurveillanceEvent dataclass avec champs typés** : Une dataclass Python assure l’intégrité des données (id, title, message, source, category, severity, timestamp) sans boilerplate. Plus lisible qu’un dict, plus flexible qu’une classe manuelle.

- [x] **SQLite pour le stockage persistant des événements** : Les événements doivent être conservés entre les sessions pour l’historique et les statistiques. SQLite permet des requêtes filtrées (par date, catégorie, sévérité) et une purge programmée. JSON serait trop lent à filtrer pour des milliers d’entrées.

- [x] **Purge automatique à 7 jours (timer 1h)** : Les événements perdent de la pertinence après une semaine. Un timer horaire évite d’accumuler des millions de lignes. La purge est silencieuse et configurable dans EventBus.

- [x] **Schéma SQLite créé automatiquement (à la première connexion)** : Évite une étape manuelle de migration. `_ensure_schema()` crée la table si elle n’existe pas. Lazy initialization : la DB n’est pas ouverte tant qu’aucun événement n’est émis.

### Interface et flux

- [x] **_EventCard compact (QFrame) plutôt que QTableWidget** : Le flux d’événements est une timeline chronologique, pas un tableau de données. Les cartes permettent un affichage plus riche (icône sévérité, timestamp, titre en gras, boutons hover). QTableWidget serait trop rigide.

- [x] **QScrollArea avec auto-scroll intelligent** : Par défaut, le scroll suit automatiquement les nouveaux événements. Si l’utilisateur scroll vers le haut pour examiner un événement passé, l’auto-scroll se suspend. Un bouton « Retour en bas » apparaît. Évite de perdre le contexte utilisateur.

- [x] **MAX_FEED_ITEMS = 500 (limite mémoire)** : Sans limite, des milliers de cartes dans le QScrollArea finiraient par consommer trop de RAM. 500 est un bon compromis entre visibilité et performance.

- [x] **Toast (3s, fondu, cliquable) pour les erreurs** : Les événements ERROR sont urgents et méritent une notification immédiate, même si l’utilisateur n’est pas sur la page Surveillance. Le toast est non-bloquant (timer 3s) et cliquable pour naviguer vers l’événement. Fondu à la fermeture.

- [x] **Badge footer compteur (non lus)** : Même pattern que les autres bots (incrément à chaque événement reçu, reset à l’affichage). Cohérent avec le système de navigation existant.

### Filtres et recherche

- [x] **Filtres catégorie (boutons toggle) plutôt que ComboBox** : Les 7 catégories sont visibles d’un coup d’œil. Les boutons toggle permettent d’activer/désactiver plusieurs catégories simultanément. Un ComboBox ne permettrait qu’une sélection unique.

- [x] **Recherche textuelle avec debounce 300ms** : Évite de filtrer à chaque frappe (trop de reconstructions). 300ms est le standard UI pour un bon équilibre entre réactivité et performance. Utilise `QTimer.singleShot`.

- [x] **Filtres appliqués par masquage (setVisible) plutôt que reconstruction** : Masquer les cartes non correspondantes est instantané. Reconstruire le flux à chaque changement de filtre serait plus lent et perdrait l’état de scroll.

- [x] **3 stat badges (Erreurs, Avertissements, Total) plutôt que 4-5** : Erreurs et Avertissements sont les deux niveaux critiques à surveiller. Total donne le volume global. INFO est volontairement exclu car trop bruité.

### Historique et détails

- [x] **HistoryModal séparé (QDialog) plutôt que section intégrée** : L’historique est une fonctionnalité avancée consultée ponctuellement. Un dialogue modal évite de surcharger le flux principal. 50 entrées par page avec « Charger plus » évite de tout charger en mémoire.

- [x] **Export CSV + JSON dans HistoryModal** : CSV pour Excel/tableur, JSON pour traitement programmatique. Deux formats courants couvrent la majorité des besoins. Pas de PDF (trop complexe pour un historique d’événements).

- [x] **DetailPopup (QDialog) avec bouton Naviguer** : Les détails complets d’un événement (titre, message, source, catégorie, sévérité, date précise) dans un popup. Le bouton « Naviguer » permet d’aller à la source de l’événement (ex: transfert vers Téléchargement).

- [x] **Cases à cocher + sélection multiple dans HistoryModal** : Permet de supprimer sélectivement des événements (nettoyage ciblé) plutôt que de tout vider. La suppression est définitive (pas de corbeille).

### Intégration et contrôle

- [x] **Pause binaire (suspend collection + affichage)** : Quand la surveillance est en pause, l’EventBus ne reçoit pas les nouveaux événements. Évite de saturer l’affichage pendant une opération massive. Le bouton Pause dans la stat bar donne un contrôle immédiat.

- [x] **Connexion aux services via signaux (connexion_manager, soulseek_client)** : L’EventBus est connecté aux signaux existants (connected, disconnected, error_occurred, transfer_added/removed/progress). Pas de polling, tout est event-driven. Les événements de progression sont limités au début/fin pour éviter le bruit.

- [x] **Connexion inter-bots (Recherche, Wishlist, Bibliothèque, Optimiseur)** : Chaque bot émet ses événements importants vers l’EventBus. Pattern cohérent avec l’architecture événementielle. Évite de dupliquer la logique de logging dans chaque bot.

- [ ] **Alertes hors-page (badge footer + toast ERROR)** : Étape 9 de la spec. Badge compteur dans le footer et toast pour les événements ERROR. Pas encore implémentés.

- [ ] **Tests & polish (performances, purge, exports)** : Étape 10 de la spec. Vérifier purge 7 jours, performances avec 200+ événements, export CSV/JSON. Pas encore fait.
