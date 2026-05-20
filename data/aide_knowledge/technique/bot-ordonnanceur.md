---
title: "Bot Ordonnanceur — assistant d'organisation des téléchargements"
category: technique
keywords:
  - ordonnanceur
  - ordonnancement
  - bot
  - assistant
  - organisation
  - classement
  - classer
  - renommer
  - renommage
  - dedoublonner
  - dedoublonnage
  - dédoublonner
  - dédoublonnage
  - nettoyage
  - fichier temp
  - corbeille
  - wizard
  - etape
  - étape
  - apercu
  - aperçu
  - execution
  - exécution
  - rapport
  - planificateur
  - planification
  - planifie
  - planifié
  - tache
  - tâche
  - service
  - worker
  - thread
  - QThread
  - analyse
  - service
  - OrdonnanceurService
  - planificateur_service
  - PlanificateurService
  - _AnalyseWorker
  - _OrdonnanceurWorker
  - _PlanificateurWorker
  - Action
  - template
  - metadata
  - metadonnées
  - mutagènes
  - mutagen
  - hash
  - SHA256
  - FichierInfo
  - AnalyseResultat
  - simulation
  - executer
  - exécuter
  - configuration
  - bot_ordonnanceur
  - center_zone
  - _build_ordonnanceur_page
  - page_changed
  - unseen_count_changed
  - QFrame
  - QScrollArea
  - bot
  - widgets
  - GUI
  - interface
---

## Résumé

Le **bot Ordonnanceur** est un assistant interactif en 4 étapes (`QFrame`, 1 373 lignes) dédié à l'organisation des fichiers téléchargés : classement par artiste/album, renommage intelligent, dédoublonnage et nettoyage. Il s'appuie sur `OrdonnanceurService` (analyse + métadonnées + templates) et `planificateur_service` (exécution planifiée) avec un système de workers multithreadés (`QThread`) pour ne pas bloquer l'interface.

```
┌─────────────────────────────────────────────────────────────────┐
│                 Bot Ordonnanceur (QFrame)                        │
├─────────────────────────────────────────────────────────────────┤
│  [① Choix] ── [② Aperçu] ── [③ Exécution] ── [④ Rapport]      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Step 1 : Checkboxes d'opérations + sélecteur de dossier        │
│  Step 2 : Tableau récapitulatif des modifications                │
│  Step 3 : Barre de progression temps réel + logs                │
│  Step 4 : Résumé final + bouton copier rapport                  │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  [Annuler]    [Précédent]    [Suivant / Lancer / Recommencer]   │
└─────────────────────────────────────────────────────────────────┘
         │
         ├── OrdonnanceurService (analyse, métadonnées, templates)
         ├── planificateur_service (CRON, persistance SQLite)
         └── Workers QThread (_AnalyseWorker, _OrdonnanceurWorker)
```

---

## 1. Fichiers sources

| Fichier | Lignes | Rôle |
|---------|--------|------|
| `src/gui/widgets/bots/bot_ordonnanceur.py` | 1 373 | Widget `BotOrdonnanceur`, workers, UI, navigation |
| `src/gui/layout/center.py` | 317-323 | `_build_ordonnanceur_page()` : instanciation et intégration dans `CenterZone` |
| `src/services/ordonnanceur_service.py` | — | `OrdonnanceurService`, `FichierInfo`, `AnalyseResultat` |
| `src/services/planificateur_service.py` | — | `PlanificateurService` (singleton), `PlanificationDB` |
| `src/gui/widgets/bots/bot_accueil_knowledge.py` | — | Métadonnées et description pour l'aide contextuelle |
| `src/gui/layout/footer.py` | — | Bouton de navigation « 🧹 Ordonnanceur » |

---

## 2. Intégration dans CenterZone

La page est construite dans `center.py` (lignes 317-323) :

```python
def _build_ordonnanceur_page(self) -> None:
    widget = BotOrdonnanceur(center_zone=self)
    self._bot_ordonnanceur = widget
    self._pages["Ordonnanceur"] = widget
    self._stack.addWidget(widget)
    widget.page_changed.connect(self.show_page)
```

- Le bot reçoit `center_zone=self` pour pouvoir changer de page (boutons d'action → navigation).
- Enregistré dans `self._pages["Ordonnanceur"]`.
- Signal `page_changed(str)` connecté à `CenterZone.show_page()`.
- Signal `unseen_count_changed(int)` pour la mise à jour du badge de notification dans le footer.

---

## 3. Architecture du bot

### 3.1 Classe `BotOrdonnanceur(QFrame)` (ligne 306)

| Propriété | Valeur |
|-----------|--------|
| **Héritage** | `QFrame` |
| **Signaux** | `page_changed(str)`, `unseen_count_changed(int)` |
| **Steps** | 4 (0-3) : Choix, Aperçu, Exécution, Rapport |
| **Service** | `self._service = OrdonnanceurService()` |

### 3.2 Layout général (`_build_ui`, ligne 371)

```
QVBoxLayout
  ├── Header (titre + description)
  ├── Step bar (_build_step_bar) : cercles numérotés ①-②-③-④
  ├── QScrollArea (contenu dynamique — change selon l'étape)
  └── Navigation bar (_build_nav_bar) : [Annuler] [Précédent] [Suivant]
```

### 3.3 Barre d'étapes (`_build_step_bar`, ligne 417)

```python
_STEPS = [
    "📋 Choix des opérations",
    "👀 Aperçu des modifications",
    "⚙️ Exécution en cours",
    "📊 Rapport final",
]
```

Chaque étape est représentée par un cercle numéroté (24×24 px) et un label. Le style actif utilise la couleur `ACCENT`, l'inactif utilise `BG_SIDE` + `TEXT_PLACEHOLDER`.

### 3.4 Barre de navigation (`_build_nav_bar`, ligne 448)

Boutons dynamiques selon l'étape :

| Étape | Boutons |
|-------|---------|
| 0 (Choix) | [Annuler] [Suivant → Analyser] |
| 1 (Aperçu) | [Annuler] [Précédent] [Suivant → Lancer] |
| 2 (Exécution) | [Annuler] |
| 3 (Rapport) | [Recommencer] |

---

## 4. Les 4 étapes du wizard

### 4.1 Étape 1 — Choix des opérations (`_build_step1_choix`, ligne 527)

L'utilisateur sélectionne une ou plusieurs opérations via des `QCheckBox` et choisit un dossier cible.

```python
_OPERATIONS = [
    ("classement", "📂 Classer par artiste/album",
     "Déplacer les fichiers dans une arborescence Artiste/Album"),
    ("renommage", "✏️ Renommer intelligemment",
     "Normaliser les noms selon un template configurable"),
    ("dedoublonner", "🗑️ Dédoublonner",
     "Supprimer les fichiers en double (nom+taille puis hash)"),
    ("nettoyage", "🧹 Nettoyer fichiers temp",
     "Supprimer les fichiers .part, caches et logs obsolètes"),
]
```

- Chaque `QCheckBox` a un `QLabel` de description en dessous (retrait 28px).
- Les checkboxes sont stockées dans `self._op_checkboxes: dict[str, QCheckBox]`.
- Signal `stateChanged` → `_on_op_toggle(op_key, checked)`.
- Sélecteur de dossier : `QFrame` avec `QLabel` (chemin) + `QPushButton` "📂 Parcourir…".
- Bouton "Parcourir" connecté à `_on_browse_folder` (ouvre `QFileDialog.getExistingDirectory`).

### 4.2 Étape 2 — Aperçu (`_build_step2_apercu`, ligne 604)

- Affiche les résultats de l'analyse sous forme de tableau (`QTableWidget`).
- Colonnes : fichier, opération proposée, taille, statut.
- Permet de visualiser l'impact avant validation.
- Généré par `_AnalyseWorker` (voir §5).

### 4.3 Étape 3 — Exécution (`_build_step3_execution`, ligne 712)

- Barre de progression temps réel (`QProgressBar`).
- Logs défilants (`QTextEdit` en lecture seule) avec mise à jour via signal `log(str)`.
- Bouton « Annuler » actif → appelle `_OrdonnanceurWorker.cancel()`.
- Exécutée par `_OrdonnanceurWorker` (voir §5).

### 4.4 Étape 4 — Rapport (`_build_step4_rapport`, ligne 783)

- Résumé texte des opérations effectuées : fichiers classés, renommés, doublons supprimés, nettoyés.
- Bouton « 📋 Copier le rapport » → `_copier_rapport()` génère un texte formaté et l'écrit dans le presse-papier système via `QApplication.clipboard()`.

---

## 5. Workers multithreadés (QThread)

Le bot utilise 3 classes worker pour exécuter les tâches lourdes sans bloquer l'UI.

### 5.1 `_AnalyseWorker(QObject)` (ligne 241)

| Propriété | Valeur |
|-----------|--------|
| **Rôle** | Analyse d'un dossier dans un thread séparé |
| **Signaux** | `finished(object, object)` → `(AnalyseResultat, list[OperationApercu])` |
| | `error(str)` |
| **Méthode** | `run()` → appelle `service.analyser_dossier()` + `service.generer_apercu()` |

### 5.2 `_OrdonnanceurWorker(QObject)` (ligne 270)

| Propriété | Valeur |
|-----------|--------|
| **Rôle** | Exécution des opérations dans un thread séparé |
| **Signaux** | `started()`, `progress(str, int, int)`, `log(str)`, `completed(dict)`, `error(str)`, `finished()` |
| **Méthodes** | `run()` → exécute les opérations | `cancel()` → drapeau `_cancelled = True` |

### 5.3 `_PlanificateurWorker(QObject)` (ligne 43)

| Propriété | Valeur |
|-----------|--------|
| **Rôle** | Exécution d'une action planifiée dans un thread dédié |
| **Signaux** | `completed(action_id, succes, message)` |
| **Méthodes** | `__init__(action_id, action_type, params)` | `run()` → utilise `_ACTION_EXECUTOR` |

### 5.4 Cycle de vie d'un thread (`_run_analysis`, ligne 1211)

```python
def _run_analysis(self) -> None:
    # 1. Nettoyage thread précédent
    self._cleanup_thread()
    # 2. Création du thread et du worker
    self._analyse_thread = QThread()
    self._analyse_worker = _AnalyseWorker(
        self._service, self._dossier, self._selected_ops
    )
    self._analyse_worker.moveToThread(self._analyse_thread)
    # 3. Connexion des signaux
    self._analyse_thread.started.connect(self._analyse_worker.run)
    self._analyse_worker.finished.connect(self._on_analysis_completed)
    self._analyse_worker.finished.connect(self._analyse_thread.quit)
    self._analyse_worker.finished.connect(self._analyse_worker.deleteLater)
    self._analyse_thread.finished.connect(self._analyse_thread.deleteLater)
    # 4. Démarrage
    self._analyse_thread.start()
```

---

## 6. Backend — `OrdonnanceurService`

Service central d'analyse, d'organisation et de nettoyage de la bibliothèque audio.

### 6.1 Classes de données

#### `FichierInfo` (dataclass)
Stocke toutes les métadonnées d'un fichier audio :
- **Tags** : `artist`, `album`, `title`, `track_number`, `year`, `genre`
- **Technique** : `format`, `bitrate`, `sample_rate`, `duration`, `size`
- **Dédoublonnage** : `hash_sha256`, `is_duplicate`, `duplicate_group`
- **Analyse** : `erreurs[]`, `sans_tags`, `chemin_relatif`

#### `AnalyseResultat`
Contexte global d'une analyse de dossier :
- `fichiers: list[FichierInfo]`
- `statistiques: dict` (total, par format, doublons, sans tags)
- `dossier: Path`

### 6.2 Fonctionnalités clés

#### Analyse et métadonnées
- Scan récursif des dossiers, filtre par extensions audio.
- Taille minimale : `TAILLE_MIN_VALIDE = 100 Ko`.
- Extraction via **mutagen** (ID3, Vorbis, MP4/iTunes).
- Fallback regex sur nom de fichier (`PATTERN_CLASSIQUE`, `PATTERN_SIMPLE`) puis dossier parent.

#### Dédoublonnage (deux passes)
1. **Rapide** : `nom.lower()` + `taille` → groupes suspects.
2. **Confirmée** : `SHA256` des 64 premiers Ko → hash exact.
3. **Résolution** : `_resoudre_doublons()` hiérarchise (bitrate > longueur nom > date modif).

#### Organisation et templates
- Templates configurables : `{artist} - {album} - {track:02d} {title}.{ext}`
- Corbeille dédiée : `deplacer_vers_corbeille()` avec horodatage anti-collision.

#### Workflow en deux phases
1. **Simulation** : `generer_apercu()` prépare les modifications sans les appliquer.
2. **Exécution** : `executer_operations()` applique réellement (ou simule), avec callbacks de progression et gestion d'erreurs par fichier.

---

## 7. Backend — `planificateur_service`

Service de planification d'actions (CRON-like) intégré à l'application.

### 7.1 Architecture

```python
planificateur_service = PlanificateurService()  # singleton QObject
```

| Composant | Rôle |
|-----------|------|
| `PlanningDB` | Base SQLite (`data/planificateur.db`), CRUD, purge 7 jours |
| `QTimer` polling (30s) | Vérifie les actions dues |
| `QTimer` purge (1h) | Nettoie les actions terminées depuis plus de 7 jours |
| `_MAX_RETRIES = 3` | Tentatives max avant échec définitif |
| `_BACKOFF_DELAYS` | Délais progressifs entre les tentatives |

### 7.2 Cycle de vie d'une action planifiée

```
Création (create_action)
    │
    ▼
En attente (pending)
    │
    ▼ (polling 30s)
En cours (running) — Timeout 5 min
    │
    ├── Succès → completed → récurrence ? → replanification
    │
    └── Échec → retry (max 3) → backoff delays → abandon définitif
```

### 7.3 Intégration avec le bot

```python
# bot_ordonnanceur.py
_ACTION_EXECUTOR = OrdonnanceurService()  # instance globale

# Connexion au service de planification
planificateur_service.action_changed.connect(_on_action_planifiee)

def _on_action_planifiee(action_id, action_type, statut):
    # Lance un _PlanificateurWorker dans un QThread dédié
    thread = QThread()
    worker = _PlanificateurWorker(action_id, action_type, params)
    worker.moveToThread(thread)
    # ...
    thread.start()
```

---

## 8. Flux complet (utilisation utilisateur)

```
Utilisateur clique « 🧹 Ordonnanceur » dans le footer
        │
        ▼
CenterZone.show_page("Ordonnanceur")
        │
        ▼
Étape 1 — Choix des opérations
  │  Cocher : ☑ Classement  ☑ Renommage  ☑ Dédoublonnage  ☐ Nettoyage
  │  Dossier : Q:/Downloads/Soulseek/
  │  [Analyser]
        │
        ▼
_run_analysis() → QThread + _AnalyseWorker
  │  OrdonnanceurService.analyser_dossier(dossier)
  │  OrdonnanceurService.generer_apercu(ops, dossier)
        │
        ▼
Étape 2 — Aperçu
  │  Tableau : 25 fichiers → 18 classés, 3 renommés, 4 doublons
  │  [Lancer]
        │
        ▼
_start_execution() → QThread + _OrdonnanceurWorker
  │  OrdonnanceurService.executer_operations(apercu, simuler=False)
  │  Progress bar + logs en temps réel
        │
        ▼
Étape 3 — Exécution (barre de progression)
  │  ████████████████░░░░░ 75%
  │  ✓ Classement : 18/18 fichiers
  │  ✓ Renommage : 3/3 fichiers
  │  ✓ Dédoublonnage : 4 doublons supprimés
        │
        ▼
Étape 4 — Rapport final
  │  25 fichiers traités, 4 doublons supprimés
  │  [📋 Copier le rapport]  [Recommencer]
```

---

## 9. Notes techniques

- **Multithreading systématique** : toutes les opérations lourdes (analyse, exécution) sont déléguées à des `QThread` avec des workers dédiés. L'UI reste réactive pendant le traitement.
- **Nettoyage des threads** : `_cleanup_thread()` et `deleteLater()` garantissent l'absence de fuites mémoire après chaque cycle d'analyse/exécution.
- **`_PlanificateurReceiver` singleton** : `_PLANIFICATEUR_RECEIVER` est une instance unique de `QObject` dans le thread principal qui reçoit les callbacks des `_PlanificateurWorker` via des connexions Qt sécurisées inter-threads.
- **Deux phases simulation/exécution** : l'étape 2 (aperçu) utilise `generer_apercu()` qui ne modifie pas le disque. L'étape 3 (exécution) utilise `executer_operations()` qui applique réellement les changements.
- **Corbeille intégrée** : les fichiers supprimés (dédoublonnage, nettoyage) sont déplacés vers un dossier corbeille avec horodatage, pas supprimés définitivement.
- **Mutagen pour les métadonnées** : supporte ID3 (MP3), Vorbis (FLAC, OGG), MP4/iTunes (M4A, AAC). Fallback regex sur le nom de fichier si les tags sont absents.
- **Planificateur persistant** : les actions planifiées survivent au redémarrage de l'application grâce à la base SQLite `planificateur.db`.

---

## Voir aussi

- [Guide du bot Ordonnanceur](../guide_bots/09-bot-ordonnanceur.md) — guide utilisateur (fonctionnalités, recommandations)
- [Architecture événementielle](architecture-evenementielle.md) — EventBus, QThread, Workers
- [Formats et codecs supportés](formats-codecs-supportes.md) — extensions audio supportées par l'analyse
- [Configuration des téléchargements](configuration-telechargement.md) — dossier de destination, slots
- [Guide navigation interface](../interface/guide-navigation-interface.md) — accès au bot via le footer
