---
title: "Widgets de configuration : onglets Utilisateurs et Partages"
category: technique
tags:
  - configuration
  - widgets
  - utilisateurs
  - partages
  - amis
  - blocage
keywords:
  - configuration onglet utilisateurs
  - configuration onglet partages
  - configuration onglet partage dossiers
  - widget config utilisateurs
  - widget config partages
  - ConfigEntry liste amis
  - ConfigEntry liste bloques
  - ConfigEntry liste bloqués
  - ConfigDirectoryPicker dossier partage
  - ConfigCombo mode partage everyone friends users
  - ConfigEntry utilisateurs autorises
  - ConfigEntry utilisateurs autorisés
  - utilisateurs liste amis app config
  - utilisateurs liste bloques app config
  - utilisateurs liste bloqués app config
  - partages dossier chemin mode utilisateurs
  - partages dossier chemin mode utilisateurs autorises
  - partages dossier chemin mode utilisateurs autorisés
  - centre zone construction pages
  - centre py build config pages
  - connexion manager block user
  - connexion manager bloquer utilisateur
  - bot recherche bloquer utilisateur
  - bot recherche clic droit bloquer
  - soulseek client lire config demarrage
  - soulseek client lecture configuration démarrage
  - library db shared folders table
  - library db partages dossier
  - library scanner scan partages
  - library scanner partage dossier
  - app config stockage liste csv
  - liste chaine separee virgule
  - liste chaîne séparée virgule
  - mode partage tout le monde
  - mode partage amis uniquement
  - mode partage utilisateurs specifiques
  - mode partage utilisateurs spécifiques
  - dossier 1 dossier 2 double partage
  - placeholder user1 user2 user3
  - placeholder spammer troll
  - section amis bloques configuration
  - section amis bloqués configuration
  - section dossier 1 2 chemin mode autorises
  - section dossier 1 2 chemin mode autorisés
  - persistance app config set get
  - evenement blocage notification statut
  - événement blocage notification statut
  - QMessageBox confirmation reinitialisation
  - QMessageBox confirmation réinitialisation
---

# Widgets de configuration : onglets Utilisateurs et Partages

## Vue d'ensemble

Les onglets **Utilisateurs** et **Partages** de l'interface de configuration gèrent respectivement les relations avec les autres utilisateurs du réseau Soulseek et les dossiers partagés localement. Tous deux sont construits dans `center.py` via `_build_config_pages()` et utilisent les widgets génériques définis dans `src/gui/widgets/config.py`.

```
┌─────────────────────────────────────────────────────────────┐
│  [Général] [Réseau] [Recherche] [Téléchargement]            │
│  [Utilisateurs] [Partages] [Salons] [Debug]                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─ ConfigSection "Amis" ──────────────────────────────┐   │
│   │  Liste d'amis    [user1, user2, user3            ]   │   │
│   │  ── Noms séparés par des virgules (ajout démarrage)  │   │
│   └──────────────────────────────────────────────────────┘   │
│                                                              │
│   ┌─ ConfigSection "Bloqués" ───────────────────────────┐   │
│   │  Utilisateurs bloqués  [spammer, troll            ]   │   │
│   │  ── Noms séparés par des virgules (restreint tout)    │   │
│   └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│   ┌─ ConfigSection "Dossier 1" ─────────────────────────┐   │
│   │  Chemin du dossier    [📁 /home/user/Musique    ]    │   │
│   │  Mode de partage      [ Tout le monde          ▼]   │   │
│   │  Utilisateurs autorisés [ friend1, friend2      ]   │   │
│   │  ── Dossier partagé avec les autres utilisateurs     │   │
│   └──────────────────────────────────────────────────────┘   │
│   ┌─ ConfigSection "Dossier 2" ─────────────────────────┐   │
│   │  Chemin du dossier    [📁 /home/user/Videos      ]   │   │
│   │  Mode de partage      [ Amis uniquement         ▼]   │   │
│   │  Utilisateurs autorisés [                           ]   │   │
│   └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Onglet Utilisateurs

Gère la liste des **amis** et des **utilisateurs bloqués**, deux listes persistées sous forme de chaînes CSV (séparées par des virgules) via `app_config`.

### Section Amis

| Propriété | Valeur |
|-----------|--------|
| **Widget** | `ConfigEntry` (champ texte) |
| **Clé config** | `utilisateurs.liste_amis` |
| **Placeholder** | `user1, user2, user3` |
| **Description** | Noms d'utilisateur à ajouter automatiquement comme amis au démarrage |

Les amis sont des utilisateurs de confiance marqués comme tels dans Soulseek. La liste est utilisée lors de l'initialisation du client via `_parse_interests()`.

### Section Bloqués

| Propriété | Valeur |
|-----------|--------|
| **Widget** | `ConfigEntry` (champ texte) |
| **Clé config** | `utilisateurs.liste_bloques` |
| **Placeholder** | `spammer, troll` |
| **Description** | Noms d'utilisateur bloqués (messages, recherches, téléchargements) |

Les utilisateurs bloqués sont restreints sur tous les plans : ils ne peuvent plus télécharger depuis votre partage, leurs fichiers sont masqués dans vos résultats de recherche, et vous n'êtes pas notifié de leurs interactions.

---

## 2. Backend : persistance et application des listes

### Structure de stockage

Les deux listes sont stockées dans `app_config` comme des chaînes de caractères simples :

```python
"utilisateurs.liste_amis": "user1, user2, user3"     # str
"utilisateurs.liste_bloques": "spammer, troll"        # str
```

### Lecture au démarrage

Dans `src/services/soulseek_client.py`, les listes sont lues pendant l'initialisation :

```python
# soulseek_client.py (initialisation, lignes ~244-245)
liste_amis = app_config.get("utilisateurs.liste_amis", "")
liste_bloques = app_config.get("utilisateurs.liste_bloques", "")
```

Ces valeurs sont ensuite parsées et appliquées lors de la configuration initiale du client Soulseek.

### Blocage depuis l'interface utilisateur

Le blocage peut également être déclenché depuis le **bot Recherche** par clic droit sur un fichier. Le flux est le suivant :

```
bot_recherche.py                   connexion_manager.py              app_config
     │                                   │                              │
     │  _on_block_user(username)          │                              │
     │─────────────────────────────────>  │                              │
     │                                   │  bloque = get("liste_bloques")│
     │                                   │──────────────────────────────>│
     │                                   │  <── "spammer" ───────────── │
     │                                   │                              │
     │                                   │  bloque += f", {username}"   │
     │                                   │  set("liste_bloques", bloque)│
     │                                   │──────────────────────────────>│
     │                                   │                              │
     │                                   │  emit status_changed("🚫...")│
     │                                   │                              │
     │  <────────────────────────────────┘                              │
```

```python
# connexion_manager.py
def block_user(self, username: str) -> None:
    bloque = app_config.get("utilisateurs.liste_bloques", "")
    if username in bloque:
        logger.info("Utilisateur déjà bloqué : %s", username)
        return
    if bloque:
        bloque += f", {username}"
    else:
        bloque = username
    app_config.set("utilisateurs.liste_bloques", bloque)
    logger.info("Utilisateur bloqué : %s", username)
    self.status_changed.emit(f"🚫 Utilisateur {username} bloqué")
```

> ⚠️ **Note** : Le blocage prend effet au démarrage suivant. L'utilisateur est ajouté à la liste persistante mais le client Soulseek doit être redémarré pour que le blocage soit pleinement actif côté serveur.

---

## 3. Onglet Partages

Gère les dossiers partagés avec le réseau Soulseek. L'interface propose **deux sections identiques** (Dossier 1 et Dossier 2), chacune permettant de configurer un dossier à partager avec son mode d'accès.

### Section Dossier 1 / Dossier 2

Chaque dossier est composé de trois widgets :

| Champ | Widget | Clé config | Valeurs / Placeholder |
|-------|--------|------------|-----------------------|
| **Chemin du dossier** | `ConfigDirectoryPicker` | `partages.dossier_X_chemin` | Sélecteur de dossier natif |
| **Mode de partage** | `ConfigCombo` | `partages.dossier_X_mode` | `everyone` / `friends` / `users` |
| **Utilisateurs autorisés** | `ConfigEntry` | `partages.dossier_X_utilisateurs` | `user1, user2 (mode 'Utilisateurs' uniquement)` |

#### Modes de partage

| Mode | Valeur stockée | Description |
|------|---------------|-------------|
| **Tout le monde** | `everyone` | Partagé avec tous les utilisateurs Soulseek |
| **Amis uniquement** | `friends` | Partagé seulement avec les amis (liste `utilisateurs.liste_amis`) |
| **Utilisateurs** | `users` | Partagé avec une liste spécifique (champ "Utilisateurs autorisés") |

> 💡 **Astuce** : Les deux dossiers permettent d'organiser le partage par catégorie (ex : Musique + Vidéos, ou Qualité + Découverte) avec des niveaux d'accès différents.

---

## 4. Backend : gestion des partages

### Stockage dans `library_db`

Les dossiers partagés sont persistés dans la base de données `library_db` via la table `shared_folders` :

```sql
CREATE TABLE IF NOT EXISTS shared_folders (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    path     TEXT NOT NULL,
    label    TEXT,
    enabled  INTEGER DEFAULT 1,
    scanned_at DATETIME
);
```

| Méthode | Description |
|---------|-------------|
| `get_shared_folders()` | Récupère les dossiers actifs (`enabled = 1`) triés par label |
| `add_shared_folder(path, label)` | Ajoute un nouveau dossier partagé |
| `remove_shared_folder(path)` | Supprime un dossier (par chemin) |
| `folder_exists(path)` | Vérifie si un dossier est déjà enregistré |

### Boucle complète d'un partage

```
Configuration (UI)
     │
     ▼
app_config.get("partages.dossier_1_chemin")  ──►  Chaîne stockée dans
app_config.get("partages.dossier_1_mode")         la configuration
app_config.get("partages.dossier_1_utilisateurs")
     │
     ▼
soulseek_client.py (initialisation)          ──►  Lecture + parsing
     │                                             _parse_blocked()
     ▼
library_db.get_shared_folders()              ──►  Dossiers actifs dans
     │                                             la base de données
     ▼
library_scanner._ScanWorker.run()            ──►  Scan des fichiers
     │                                             avec Path.rglob()
     ▼
LibraryScanner.scan_completed signal         ──►  Mise à jour de la
     │                                             bibliothèque
     ▼
Appel API Soulseek                            ──►  Dossiers visibles
     (set_shared_paths?)                           sur le réseau
```

> ℹ️ **Détail d'implémentation** : Les chemins de partage sont stockés à la fois dans `app_config` (pour la persistance de l'interface) et dans `library_db.shared_folders` (pour le scan et la gestion de la bibliothèque). Les deux sont synchronisés au démarrage via `soulseek_client.py`.

---

## 5. Architecture des widgets Config

### Widgets utilisés

| Widget | Utilisation | Spécificités |
|--------|-------------|--------------|
| `ConfigEntry` | Liste amis, bloqués, utilisateurs autorisés | Texte libre, placeholder, persistance au focus perdu |
| `ConfigDirectoryPicker` | Chemin des dossiers partagés | Dialogue `QFileDialog.GetExistingDirectory`, bouton ✕ pour effacer |
| `ConfigCombo` | Mode de partage | 3 options avec labels longs (description incluse) |

### Clés de configuration complètes

```yaml
# Onglet Utilisateurs
utilisateurs.liste_amis: "user1, user2, user3"       # str — CSV
utilisateurs.liste_bloques: "spammer, troll"          # str — CSV

# Onglet Partages — Dossier 1
partages.dossier_1_chemin: "/home/user/Musique"      # str — chemin
partages.dossier_1_mode: "everyone"                   # str — everyone|friends|users
partages.dossier_1_utilisateurs: "friend1, friend2"   # str — CSV

# Onglet Partages — Dossier 2
partages.dossier_2_chemin: ""                         # str — chemin (vide par défaut)
partages.dossier_2_mode: "everyone"                   # str — everyone|friends|users
partages.dossier_2_utilisateurs: ""                   # str — CSV (vide par défaut)
```

### Valeurs par défaut

- `liste_amis` : `""` (vide, aucun ami pré-ajouté au démarrage)
- `liste_bloques` : `""` (vide, aucun utilisateur bloqué)
- `dossier_X_chemin` : `""` (vide, aucun dossier partagé)
- `dossier_X_mode` : `"everyone"` (accessible à tous)
- `dossier_X_utilisateurs` : `""` (vide)

---

## 6. Résumé technique

| Propriété | Utilisateurs | Partages |
|-----------|-------------|----------|
| **Fichier source** | `src/gui/layout/center.py` (lignes 734-761) | `src/gui/layout/center.py` (lignes 762-833) |
| **Sections** | 2 : Amis, Bloqués | 2 : Dossier 1, Dossier 2 |
| **Widgets** | 2 × `ConfigEntry` | 2 × (`ConfigDirectoryPicker` + `ConfigCombo` + `ConfigEntry`) |
| **Clés config** | `utilisateurs.*` | `partages.dossier_{1,2}_*` |
| **Backend** | `connexion_manager.block_user()`, `soulseek_client._parse_blocked()` | `library_db.shared_folders`, `library_scanner`, `soulseek_client` |
| **Persistance** | `app_config` (chaîne CSV) | `app_config` + `library_db.shared_folders` |
| **Intégration** | Clic droit blocage depuis `bot_recherche.py` | Scan via `LibraryScanner`, scan au démarrage si `general.scan_on_start` |

---

## Voir aussi

- [Configuration utilisateurs](configuration-utilisateurs.md) — détails techniques du backend : parsing des listes, `_parse_blocked()`, `block_user()`
- [Configuration partages](configuration-partages.md) — détails techniques du backend des dossiers partagés : `_parse_share_directory()`, `DirectoryShareMode`, `SharesSettings`
- [Bloquer : config vs menu contextuel](../faq/bloquer-config-vs-contextuel.md) — différences entre les deux méthodes de blocage
