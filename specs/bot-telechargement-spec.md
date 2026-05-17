# Plan d'implémentation — Bot Téléchargement

> **Statut :** ✅ Terminé — 1 198 lignes + 165 lignes service
> **Dernière mise à jour :** 2026-06-16
> **Voir aussi :** `specs/bot-recherche-spec.md` (intégration recherche → téléchargement), `.aioslsk-logbook.md` (plan général)

---

## 🎯 Objectif

Gérer, suivre et prioriser les téléchargements Soulseek en temps réel. Interface complète avec tableau triable, barre de progression globale, statistiques, actions individuelles et batch, badge footer, et historique persistant SQLite.

---

## 📋 Fonctionnalités

### 1. Tableau des téléchargements
- **6 colonnes** triables : `Fichier` (260 px), `Taille` (90 px), `Utilisateur` (140 px), `Progression` (180 px), `Vitesse` (100 px), `Statut` (120 px)
- Tri ascendant/descendant par clic sur en-tête (indicateur visible)
- `_NumericItem` — tri numérique correct pour la colonne Progression via `_SortRole = Qt.UserRole + 1`
- Alternance de couleurs, sélection de ligne, édition désactivée, grille transparente
- Scroll fluide — pas de limite haute pour le nombre de lignes

### 2. Barre de progression globale
- Affiche `X / Y Mo (Z%)` — total des bytes reçus / total à télécharger
- Barre `QProgressBar` avec pourcentage
- Vitesse cumulée en bas : `⚡ 2.5 Mo/s`
- Prend en compte les téléchargements terminés comme 100% reçus

### 3. Badges de statistiques (en-tête)
4 badges en temps réel :
| Badge | Icône | Couleur |
|-------|-------|---------|
| En cours | 🔄 | `COLORS["SUCCESS"]` |
| En attente | ⏳ | `COLORS["WARNING"]` |
| Terminés | ✅ | `COLORS["PRIMARY"]` |
| Échoués | ❌ | `COLORS["DANGER"]` |

Valeur mise à jour automatiquement par `_update_stats()` à chaque ajout/suppression/changement de statut.

### 4. Toolbar — Actions batch
| Bouton | Action | Backend |
|--------|--------|---------|
| `▶ Reprendre tout` | Reprend les téléchargements en attente + échoués | `SoulseekService.resume_transfer()` ✅ |
| `⏸ Pause tout` | Met en pause tous les téléchargements en cours | `SoulseekService.pause_transfer()` ✅ |
| `✕ Tout annuler` | Annule tous les téléchargements actifs/attente (passe en `echoue`) | `SoulseekService.abort_transfer()` ✅ |
| `📜 Historique` | Ouvre le dialogue d'historique SQLite | SQLite local |
| `📂 Ouvrir Downloads` | Ouvre le dossier de destination dans l'explorateur | Système |
| `🗑 Vider terminés` | Supprime du tableau les lignes terminées + échouées | UI locale |

### 5. Filtre par statut (ComboBox)
Options : `Tous`, `En cours`, `En attente`, `Terminé`, `Échoué`
- Masque/affiche les lignes via `setRowHidden()`
- Ré-appliqué automatiquement après un tri (connecté à `sortIndicatorChanged`)
- Mapping : les textes français sont convertis en clés internes (`en_cours`, `attente`, `termine`, `echoue`)

### 6. Menu contextuel — Actions individuelles
Sur clic droit sur une ligne, menu adapté au statut actuel. Toutes les actions sont câblées au backend Soulseek :

| Statut | Actions disponibles | Appel Soulseek |
|--------|-------------------|----------------|
| `en_cours` | ⏸ Pause, ✕ Annuler, 📋 Copier | `pause_transfer()` / `abort_transfer()` ✅ |
| `attente` | ▶ Reprendre, ✕ Annuler, 📋 Copier | `resume_transfer()` / `abort_transfer()` ✅ |
| `termine` | ✕ Annuler (supprime du tableau), 📋 Copier | — (déjà terminé) |
| `echoue` | ⟳ Réessayer (→ `attente`), 📤 Relancer (→ `en_cours`), ✕ Annuler (→ `echoue`), 📋 Copier | `resume_transfer()` / `abort_transfer()` ✅ |

### 7. Progression en temps réel avec ETA
- Mise à jour par `_on_transfer_progress()` via signal `transfer_progress` de `SoulseekService`
- Vitesse calculée par différence de `bytes_transfered` entre deux updates
- Affichage : `75% (2m 30s)` — ETA = `taille_restante / vitesse_bps`
- Formatage temps restant : `< 60s` → `Xs`, `< 60min` → `Xm Ys`, sinon `Xh Ym`
- Détection auto du début de téléchargement (premiers bytes reçus → EventBus)

### 8. Intégration SoulseekService

#### Réception (signaux Soulseek → Bot)
Connexion via `setup(svc: SoulseekService)` :
- `transfer_added` → `_on_transfer_added()` → `add_download()`
- `transfer_removed` → `_on_transfer_removed()` → `remove_download()`
- `transfer_progress` → `_on_transfer_progress()` → `update_progression()` + `change_statut()`

#### Contrôle (Bot → SoulseekService)
Le bot appelle directement `self._service.pause_transfer()` / `resume_transfer()` / `abort_transfer()` depuis les handlers synchrones Qt. Les méthodes du service utilisent `asyncio.ensure_future()` pour un appel fire-and-forget sur la boucle d'événements asyncio.

**Méthodes exposées par `SoulseekService` :**
| Méthode | Paramètres | Action Soulseek |
|---------|-----------|----------------|
| `pause_transfer(username, remote_path)` | `str, str` | `transfers.pause(transfer)` |
| `resume_transfer(username, remote_path)` | `str, str` | `transfers.download(username, path, paused=False)` |
| `abort_transfer(username, remote_path)` | `str, str` | `transfers.abort(transfer)` |

Chaque méthode vérifie `is_connected` et le `self._client` avant d'agir. `pause` et `abort` cherchent d'abord le transfert via `transfers.find_transfer(username, path, TransferDirection.DOWNLOAD)`. `resume` appelle directement `download()` (Soulseek le traite comme une reprise).

Conversion `TransferState.State` → statut interne :
| TransferState | Statut |
|--------------|--------|
| `VIRGIN`, `QUEUED`, `INITIALIZING`, `PAUSED`, `UNSET` | `attente` |
| `INCOMPLETE`, `DOWNLOADING`, `UPLOADING` | `en_cours` |
| `COMPLETE` | `termine` |
| `FAILED`, `ABORTED` | `echoue` |

Émission d'événements EventBus pour les transitions importantes :
- Téléchargement ajouté (INFO)
- Téléchargement démarré (INFO)
- Téléchargement terminé (INFO)
- Téléchargement échoué (WARN)

### 9. Badge footer (compteur)
- Incrémenté à chaque `_on_transfer_added()` — nombre d'événements non lus
- Réinitialisé via `reset_unseen_count()` quand la page Téléchargement est affichée
- Connecté dans `CenterZone._build_telechargements_page()` → `_update_telechargement_badge()` → `FooterZone.set_badge("Téléchargement", count)`

### 10. Historique persistant SQLite (`src/services/telechargement_history.py`)

Service singleton lazy, calqué sur `planificateur_service.py`.

**Schéma** — table `download_history` :
| Champ | Type | Description |
|-------|------|-------------|
| `id` | INTEGER PK AUTO | Identifiant unique |
| `identifiant` | TEXT NOT NULL | Chemin distant Soulseek |
| `fichier` | TEXT NOT NULL | Nom du fichier |
| `utilisateur` | TEXT | Utilisateur source |
| `taille` | TEXT | Taille formatée (ex: `15.2 Mo`) |
| `taille_bytes` | INTEGER | Taille en bytes |
| `statut` | TEXT CHECK | `'termine'` ou `'echoue'` |
| `vitesse_moyenne` | TEXT | Vitesse au moment de la fin |
| `vitesse_bytes` | REAL | Vitesse en bytes/s |
| `date_debut` | TEXT | Timestamp ISO du début |
| `date_fin` | TEXT DEFAULT `now()` | Timestamp ISO de la fin |
| `created_at` | TEXT DEFAULT `now()` | Timestamp de création |

Index : `idx_history_date` (date_fin DESC), `idx_history_statut` (statut)
Migration v0→v1 : création de la table, `PRAGMA user_version = 1`

**API publique :**
| Fonction | Description |
|----------|-------------|
| `add_to_history(...)` | Ajoute une entrée |
| `get_history(limit, offset, statut_filter)` | Requête paginée avec filtre optionnel |
| `count_history(statut_filter)` | Compte les entrées |
| `clear_history()` | Vide la table |
| `close()` | Ferme la connexion |

**Déclenchement :** Dans `change_statut()`, sauvegarde automatique quand le téléchargement passe EN état terminal (`termine`/`echoue`) depuis un état non-terminal (évite les doubles enregistrements).

### 11. HistoryDialog
- Dialogue modal (900x500 px minimum)
- 6 colonnes : Fichier (260), Taille (80), Utilisateur (140), Statut (80), Vitesse (100), Date (160)
- Filtre : `Tous` / `Terminé` / `Échoué`
- Compteur : `X entrées`
- Bouton `🗑 Vider l'historique` avec confirmation `QMessageBox`
- Données chargées depuis SQLite via `telechargement_history.get_history()` avec `LIMIT 500`

### 12. Stockage interne (`_downloads` dict)
```
{
    "remote/path/fichier.mp3": {
        "fichier":       str,       # Nom du fichier
        "statut":        str,       # en_cours | attente | termine | echoue
        "progression":   float,     # 0.0 — 100.0
        "vitesse":       str,       # Formaté (ex: "1.2 Mo/s")
        "taille":        str,       # Formaté (ex: "15.2 Mo")
        "taille_bytes":  int,       # Taille totale en bytes
        "vitesse_bytes": float,     # Vitesse brute en bytes/s
        "bytes_transfered": int,    # Bytes reçus
        "prev_time":     float,     # Timestamp du dernier update (time.time())
        "user":          str,       # Nom d'utilisateur distant
        "date_debut":    str,       # ISO timestamp (datetime.now())
    }
}
```

---

## 🔧 Architecture technique

### Fichiers
| Fichier | Rôle | Lignes |
|---------|------|--------|
| `src/gui/widgets/bots/bot_telechargement.py` | UI + logique du bot | ~1 215 |
| `src/services/telechargement_history.py` | Service SQLite historique | 165 |
| `src/gui/layout/center.py` | Intégration page + badge footer | (l. 242-248) |
| `src/gui/layout/footer.py` | Badge `_FooterNavButton` | (l. 30-63) |
| `src/services/soulseek_client.py` | Signaux `transfer_added/removed/progress` + contrôle `pause/resume/abort` | ~520 |

### Dépendances
- `PySide6` — QtWidgets (QTableWidget, QFrame, QDialog, QPushButton, etc.)
- `sqlite3` — stockage historique
- `datetime` / `time` — timestamps, ETA
- `src.services.telechargement_history` — service SQLite
- `src.services.event_bus` — événements système
- `src.services.soulseek_client.SoulseekService` — signaux transferts
- `src.gui.theme_fragments.colors.COLORS` — thème

### Signaux Qt
| Signal | Direction | Description |
|--------|-----------|-------------|
| `page_changed(str)` | Bot → CenterZone | Navigation vers un autre bot |
| `unseen_count_changed(int)` | Bot → Footer | Mise à jour badge footer |
| `transfer_added` | SoulseekService → Bot | Nouveau transfert |
| `transfer_removed` | SoulseekService → Bot | Transfert supprimé |
| `transfer_progress` | SoulseekService → Bot | Mise à jour progression |

### API de contrôle (appels synchrones → asyncio fire-and-forget)
| Méthode Bot | Appelle `SoulseekService` | Effet Soulseek |
|-------------|--------------------------|----------------|
| `_on_pause_all()` | `pause_transfer(user, path)` | `transfers.pause()` |
| `_on_resume_all()` | `resume_transfer(user, path)` | `transfers.download(paused=False)` |
| `_on_cancel_all()` | `abort_transfer(user, path)` | `transfers.abort()` |
| `_on_annuler(id)` | `abort_transfer(user, path)` | `transfers.abort()` |
| Menu contextuel Pause | `pause_transfer(user, path)` | `transfers.pause()` |
| Menu contextuel Reprendre | `resume_transfer(user, path)` | `transfers.download(paused=False)` |
| Menu contextuel Réessayer | `resume_transfer(user, path)` | `transfers.download(paused=False)` |
| Menu contextuel Relancer | `resume_transfer(user, path)` | `transfers.download(paused=False)` |
| Menu contextuel Annuler | `abort_transfer(user, path)` | `transfers.abort()` |

### Flow de données
```
SoulseekClient (aioslsk)
  → SoulseekService (signaux Qt)
    → BotTelechargement (UI)
      → telechargement_history (SQLite) [état final seulement]
      → EventBus (système) [transitions importantes]
      → FooterZone (badge) [compteur non lus]
```

---

## 📐 Structure du code (classes)

### `HistoryDialog(QDialog)` — L. 135-331
- `_COLONNES`: définition des colonnes
- `__init__()`: titre, taille, modal → `_build_ui()` → `_load_data()`
- `_build_ui()`: en-tête (titre + filtre + vider), compteur, tableau stylé
- `_load_data()`: requête SQLite, remplit le tableau
- `_on_filtre_changed()`: recharge avec filtre
- `_on_vider()`: confirmation → `clear_history()` → reload

### `BotTelechargement(QFrame)` — L. 338-~1215
- **Attributs :** `_downloads: dict[str, dict]`, `_setup_done: bool`, `_unseen_count: int`, `_service: SoulseekService`
- **API publique :** `reset_unseen_count()`, `setup(svc)`, `add_download(...)`, `remove_download(id)`, `update_progression(id, pct, bytes)`, `change_statut(id, nouveau)`, `download_count()`
- **Helpers tableau :** `_find_row(id)`, `_get_identifiant_at(row)`, `_apply_filter(statut)`
- **Callbacks Soulseek :** `_on_transfer_added(evt)`, `_on_transfer_removed(evt)`, `_on_transfer_progress(evt)`
- **UI :** `_build_ui()` → `_build_header()` (badges + progression), `_build_toolbar()` (actions + filtre + historique), `_build_table()`
- **Stats :** `_update_stats()` (compte par statut), `_update_global_progress()` (barre + vitesse)
- **Actions batch (câblées Soulseek) :** `_on_resume_all()` → `service.resume_transfer()`, `_on_pause_all()` → `service.pause_transfer()`, `_on_cancel_all()` → `service.abort_transfer()`, `_on_clear_termines()`, `_on_ouvrir_dossier()`
- **Actions individuelles (câblées Soulseek) :** `_on_context_menu(pos)` (Pause/Reprendre/Réessayer/Relancer → service), `_on_annuler(id)` → `service.abort_transfer()`, `_on_copier_nom(id)`
- **Historique :** `_save_to_history(id, statut)`, `_on_show_history()`
- **Helpers statiques :** `_transfer_state_to_statut(state)`, `_transfer_statut_label(transfer)`, `_toolbar_btn(text)`, `_toolbar_btn_danger(text)`, `_make_badge(icon, label, color)`

### `_NumericItem(QTableWidgetItem)` — L. 72-80
- `__lt__(other)`: compare via `_SortRole` pour tri numérique correct

### Helpers module-level — L. 95-127
- `_format_taille(bytes)`: `o`, `Ko`, `Mo`, `Go`
- `_format_vitesse(bps)`: `o/s`, `Ko/s`, `Mo/s`
- `_format_temps_restant(sec)`: `Xs`, `Xm Ys`, `Xh Ym`

### `telechargement_history.py` — module singleton
- `_get_conn()`: connexion lazy + migration auto
- `_ensure_schema()`: `PRAGMA user_version` pour migrations

---

## 🚧 Ce qui reste à faire

Le câblage backend de base est terminé ✅. Points encore ouverts :

- 📤 **Relancer échoué → `en_cours`** : actuellement appelle `resume_transfer()` (identique à Réessayer). Pour un vrai relancement, il faudrait idéalement ré-exécuter la recherche originale et démarrer un nouveau téléchargement frais plutôt que de reprendre l'ancien transfert.
- 🧪 **Tests d'intégration** : les méthodes `pause/resume/abort` n'ont pas de tests automatisés (nécessitent une connexion Soulseek réelle).

---

## ✅ Checklist de validation

- [x] Compilation sans erreur (`python -m py_compile`)
- [x] 539 tests verts (`python -m pytest tests/`)
- [x] Tri par colonne fonctionnel (numérique pour progression)
- [x] Filtre par statut correct après tri
- [x] ETA calculé et affiché en temps réel
- [x] Menu contextuel adapté au statut
- [x] Badge footer incrémenté / reset
- [x] Historique SQLite : écriture, lecture, filtre, effacement
- [x] Intégration SoulseekService (signaux transferts)
- [x] Barre de progression globale cohérente

---

## 🔄 Intégration avec les autres bots

| Bot | Relation |
|-----|----------|
| **Recherche** | Les résultats de recherche doivent pouvoir déclencher un téléchargement → ajout dans `add_download()` |
| **Wishlist** | Les souhaits automatiques peuvent lancer des téléchargements → notification via EventBus |
| **Planificateur** | Peut planifier des téléchargements récurrents |
| **Surveillance** | Événements `transfert` émis à chaque transition (ajout, début, fin, échec) |


---

## 13. ❓ Questions résolues

### Architecture et interface

- [x] **QTableWidget plutôt que QListView ou QTreeView** : Le tableau plat convient parfaitement à une liste de téléchargements où chaque entrée a les mêmes colonnes (Fichier, Taille, Progression…). QTreeView serait excessif (pas de hiérarchie). QListView n’offre pas le tri natif par colonne sans customisation supplémentaire.

- [x] **6 colonnes décidées (et pas 7 ou 8)** : Chaque colonne a un rôle identifié : Fichier (quoi), Taille (combien), Utilisateur (qui), Progression (où), Vitesse (comment vite), Statut (état). Pas de colonne « Date » dans le tableau principal car l’historique SQLite gère ça. Pas de colonne « Chemin complet » car trop large pour l’UI.

- [x] **`_NumericItem` avec `_SortRole` plutôt que cast en int** : Qt trie par défaut alphabétiquement (1, 10, 2, 20…). Surcharger `__lt__` avec une donnée numérique dans `_SortRole` (Qt.UserRole+1) est le pattern PySide6 idiomatique pour un tri numérique correct.

- [x] **Stockage `_downloads` dict (clé = chemin distant) plutôt que liste ou SQLite temps réel** : Un dict avec le chemin comme clé offre un accès O(1) pour les mises à jour fréquentes (progression, statut). SQLite écrirait trop souvent (chaque tick de progression). Une liste nécessiterait une recherche linéaire à chaque update.

- [x] **Pas de limite haute de lignes (contrairement aux 200 résultats de recherche)** : Un téléchargement actif n’est pas un résultat de recherche — l’utilisateur ne lance pas 500 téléchargements simultanés. Aucun risque de saturation. Les téléchargements terminés/échoués sont nettoyés via le bouton « Vider terminés ».

- [x] **`HistoryDialog` modal plutôt que section intégrée dans le bot** : L’historique est une donnée secondaire consultée ponctuellement. Un dialogue modal évite de charger des centaines d’entrées SQLite dans le tableau principal à chaque affichage. 900x500 px offre une visibilité suffisante.

- [x] **`LIMIT 500` dans HistoryDialog plutôt que pagination complète** : Avec un historique quotidien (quelques dizaines d’entrées par jour), 500 lignes couvrent facilement des mois. La pagination complète ajouterait de la complexité UI pour un bénéfice marginal.

### Moteur de téléchargement et états

- [x] **4 statuts internes (en_cours, attente, termine, echoue) plutôt que 8+ états Soulseek** : Les états `TransferState` (VIRGIN, QUEUED, INITIALIZING, PAUSED, INCOMPLETE, DOWNLOADING, COMPLETE, FAILED, ABORTED, UNSET) sont trop fins pour l’UI. Le mapping réduit à 4 catégories (en_cours/attente/termine/echoue) simplifie le filtre, le menu contextuel et l’affichage.

- [x] **`change_statut()` sauvegarde SQLite seulement à l’état terminal** : Évite les écritures redondantes pendant le téléchargement (chaque progression émet un statut). La condition « état terminal depuis état non-terminal » évite aussi les doubles enregistrements.

- [x] **Emissions EventBus pour les transitions importantes seulement** : Ajout, début, fin, échec. C’est le bon niveau de granularité : assez pour que les autres bots (Surveillance, Wishlist) réagissent, sans créer de bruit à chaque tick de progression.

- [x] **Conversions synchrone Qt → asyncio fire-and-forget** : `self._service.pause_transfer()` est appelée depuis un handler Qt synchrone. `SoulseekService` utilise `asyncio.ensure_future()` car l’appel Soulseek est asynchrone. Pas de `run_until_complete` qui bloquerait l’UI.

### Stockage persistant (SQLite)

- [x] **SQLite plutôt que JSON (contrairement à search_history)** : L’historique des téléchargements peut atteindre des milliers d’entrées. SQLite permet des requêtes filtrées (`WHERE statut = 'termine'`), paginées (`LIMIT 500 OFFSET 0`), et agrégées (`COUNT`). JSON nécessiterait de tout charger en mémoire pour filtrer.

- [x] **`PRAGMA user_version` pour les migrations** : Mécanisme natif SQLite simple (un entier). Évite d’importer une librairie de migration pour un schéma à une seule table. La version courante est `1`.

- [x] **Index `idx_history_date` et `idx_history_statut`** : Le dialogue d’historique filtre et trie par date fréquemment. Sans index, une table de 10 000+ entrées deviendrait lente. Ce sont les deux seules colonnes de recherche/filtrage.

### Performance et UX

- [x] **Barre de progression globale `QProgressBar`** : Calculée simplement à partir de `bytes_received / total_bytes` cumulés. Un widget personnalisé ajouterait de la complexité pour le même résultat visuel. Le pourcentage + texte « X / Y Mo » est standard et lisible.

- [x] **ETA basé sur la vitesse instantanée** : Calcul simple (`taille_restante / vitesse_bps`). Une moyenne mobile lissée serait plus précise mais ajoute de la complexité (buffer à gérer). Pour une interface de téléchargement, une approximation suffit — l’utilisateur voit la tendance.

- [x] **Filtre par statut via `setRowHidden()` plutôt que reconstruction du tableau** : `setRowHidden()` est instantané et conserve l’état du tri et de la sélection. Reconstruire le tableau à chaque changement de filtre serait plus lent et perdrait le contexte UI.

- [x] **Pas de réessai automatique des échoués** : Un échec peut être transitoire (utilisateur déconnecté) ou permanent (fichier supprimé). Une boucle de réessai automatique pourrait saturer le réseau. L’utilisateur décide manuellement via « Réessayer » ou « Relancer ».

### Intégration

- [x] **`resume_transfer()` appelle `transfers.download(paused=False)` plutôt que `transfers.resume()`** : L’API Soulseek traitent les reprises comme de nouveaux téléchargements qui reprennent automatiquement si le fichier partiel existe. Il n’y a pas de méthode `resume()` explicite. C’est un détail d’implémentation transparent pour l’UI.

- [x] **`setup(svc)` plutôt que constructeur avec service** : Pattern utilisé dans tous les bots FreeBuff. Le constructeur reste simple (parent QWidget), et le service est injecté via `setup()` quand il est disponible. Évite les problèmes d’ordre d’initialisation.

- [x] **Pas de gestion des téléchargements upload (Soulseek)** : L’interface ne montre que les DOWNLOAD. Les uploads sont gérés automatiquement par Soulseek et n’ont pas d’UI directe. Un onglet upload serait un ajout futur possible mais sort du scope actuel.

- [x] **Badge footer compteur non lus** : Même pattern que les autres bots (incrément à chaque ajout, reset à l’affichage). Cohérent avec la section « Intégration footer ».

