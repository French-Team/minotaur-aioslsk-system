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
