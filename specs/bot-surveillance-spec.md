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
