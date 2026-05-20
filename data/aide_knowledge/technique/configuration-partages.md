---
title: "Configuration des dossiers partagés (Partages) — widgets et backend"
category: technique
keywords:
  - partages
  - partage
  - dossier
  - shared folder
  - directory
  - Soulseek
  - partager
  - partagé
  - partage
  - mode
  - acces
  - accès
  - autorisation
  - everyone
  - friends
  - amis
  - utilisateurs
  - autorises
  - autorisés
  - chemin
  - scan
  - demarrage
  - démarrage
  - library_db
  - library_scanner
  - scan_on_start
  - dossier_destination
  - telechargement
  - téléchargement
  - download
  - ConfigDirectoryPicker
  - ConfigCombo
  - ConfigEntry
  - ConfigSection
  - ConfigPage
  - optimisation
  - partages.dossier_1_chemin
  - partages.dossier_1_mode
  - partages.dossier_1_utilisateurs
  - partages.dossier_2_chemin
  - partages.dossier_2_mode
  - partages.dossier_2_utilisateurs
  - SharedDirectorySettingEntry
  - DirectoryShareMode
  - _parse_share_directory
  - soulseek_client
  - app_config
  - widget
  - interface
  - config
  - configuration
  - paramètres
  - parametres
---

## Résumé

L'application offre la possibilité de partager jusqu'à **2 dossiers** distincts sur le réseau Soulseek, chacun avec son propre mode d'accès. Cet article détaille la configuration UI (widgets `ConfigDirectoryPicker`, `ConfigCombo`, `ConfigEntry`) et le backend (`_parse_share_directory`, `DirectoryShareMode`, application aux `SharesSettings`).

```
┌─────────────────────────────────────────────────────────────────┐
│                     Optimiseur → Partages                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─ Dossier 1 ───────────────────────────────────────────────┐  │
│  │  ConfigDirectoryPicker  « partages.dossier_1_chemin »     │  │
│  │  ConfigCombo            « partages.dossier_1_mode »       │  │
│  │  ConfigEntry            « partages.dossier_1_utilisateurs »│  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌─ Dossier 2 ───────────────────────────────────────────────┐  │
│  │  ConfigDirectoryPicker  « partages.dossier_2_chemin »     │  │
│  │  ConfigCombo            « partages.dossier_2_mode »       │  │
│  │  ConfigEntry            « partages.dossier_2_utilisateurs »│  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    app_config.json (persistance)
                              │
                              ▼
                 soulseek_client.py (lecture startup)
                              │
                              ▼
              SharesSettings (aioslsk) → Réseau Soulseek
```

---

## 1. Fichiers sources

| Fichier | Rôle |
|---------|------|
| `src/gui/layout/center.py` | Construction de la `ConfigPage("Partages")` (lignes 761-823) |
| `src/services/soulseek_client.py` | Parsing et application des paramètres (lignes 121-160, 267-279, 343-346) |
| `src/services/app_config.py` | Persistance atomique des clés `partages.*` dans `app_config.json` |
| `src/services/library_db.py` | Gestion de la table `shared_folders` pour l'indexation des fichiers |

---

## 2. Interface utilisateur (widgets)

La page **Partages** est construite dans `center.py` (autour de la ligne 761) avec la structure suivante :

### 2.1 ConfigPage et ConfigSections

```python
# center.py — construction de la page Partages (pseudo-code)
page = ConfigPage("Partages")
section_d1 = ConfigSection("Dossier 1")   # ligne ~762
section_d2 = ConfigSection("Dossier 2")   # ligne ~797
```

### 2.2 Widgets par dossier

Chaque dossier contient 3 widgets :

#### a) Sélecteur de dossier — `ConfigDirectoryPicker`

| Propriété | Valeur |
|-----------|--------|
| **Label** | « Chemin du dossier » |
| **Config key** | `partages.dossier_1_chemin` / `partages.dossier_2_chemin` |
| **Placeholder** | « Sélectionnez un dossier à partager… » |

#### b) Mode de partage — `ConfigCombo`

| Propriété | Valeur |
|-----------|--------|
| **Label** | « Mode de partage » |
| **Config key** | `partages.dossier_1_mode` / `partages.dossier_2_mode` |
| **Options** | `everyone` (Tout le monde), `friends` (Amis uniquement), `users` (Utilisateurs) |

#### c) Utilisateurs autorisés — `ConfigEntry`

| Propriété | Valeur |
|-----------|--------|
| **Label** | « Utilisateurs autorisés » |
| **Config key** | `partages.dossier_1_utilisateurs` / `partages.dossier_2_utilisateurs` |
| **Placeholder** | « user1, user2 (mode 'Utilisateurs' uniquement) » |

### 2.3 Modes de partage

| Mode | Valeur `app_config` | Description | Visibilité |
|------|--------------------|-------------|------------|
| **Tout le monde** | `everyone` | Accessible à tous les utilisateurs Soulseek | Champ utilisateurs masqué |
| **Amis uniquement** | `friends` | Restreint à la liste d'amis (onglet Utilisateurs) | Champ utilisateurs masqué |
| **Utilisateurs** | `users` | Restreint à une liste CSV d'utilisateurs spécifiques | Champ utilisateurs visible |

---

## 3. Stockage dans `app_config`

Les valeurs sont persistées via `app_config.set()` dans `app_config.json`, section `partages` :

```json
{
  "partages": {
    "dossier_1_chemin": "Q:/Musique",
    "dossier_1_mode": "everyone",
    "dossier_1_utilisateurs": "",
    "dossier_2_chemin": "Q:/Prive",
    "dossier_2_mode": "users",
    "dossier_2_utilisateurs": "ami1, ami2"
  }
}
```

### Clés et valeurs par défaut

| Clé | Défaut | Type |
|-----|--------|------|
| `partages.dossier_1_chemin` | `""` (vide) | `str` (chemin) |
| `partages.dossier_1_mode` | `"everyone"` | `str` (enum) |
| `partages.dossier_1_utilisateurs` | `""` (vide) | `str` (CSV) |
| `partages.dossier_2_chemin` | `""` (vide) | `str` (chemin) |
| `partages.dossier_2_mode` | `"everyone"` | `str` (enum) |
| `partages.dossier_2_utilisateurs` | `""` (vide) | `str` (CSV) |

---

## 4. Backend — lecture au démarrage

### 4.1 Lecture des valeurs (`soulseek_client.py`, lignes 267-272)

```python
# Lecture depuis app_config
dossier_1_chemin = app_config.get("partages.dossier_1_chemin", "")
dossier_1_mode = app_config.get("partages.dossier_1_mode", "everyone")
dossier_1_utilisateurs = app_config.get("partages.dossier_1_utilisateurs", "")

dossier_2_chemin = app_config.get("partages.dossier_2_chemin", "")
dossier_2_mode = app_config.get("partages.dossier_2_mode", "everyone")
dossier_2_utilisateurs = app_config.get("partages.dossier_2_utilisateurs", "")
```

### 4.2 Fonction `_parse_share_directory` (lignes 121-143)

```python
def _parse_share_directory(
    chemin: str,
    mode_raw: str,
    utilisateurs_raw: str,
) -> SharedDirectorySettingEntry | None:
    """Construit un SharedDirectorySettingEntry à partir des valeurs de config.

    Retourne None si le chemin est vide (dossier non configuré).
    """
    if not chemin:
        return None
    try:
        mode = DirectoryShareMode(mode_raw)
    except ValueError:
        mode = DirectoryShareMode.EVERYONE      # fallback sécurisé
    utilisateurs = (
        [u.strip() for u in utilisateurs_raw.split(",") if u.strip()]
        if utilisateurs_raw else []
    )
    return SharedDirectorySettingEntry(
        path=chemin,
        share_mode=mode,
        users=utilisateurs,
    )
```

**Détails importants :**
- **Retour `None`** : si le chemin est vide → dossier ignoré (pas de partage pour ce dossier)
- **`DirectoryShareMode(mode_raw)`** : conversion de la chaîne en enum aioslsk (membres : `EVERYONE`, `FRIENDS`, `USERS`)
- **Fallback** : si `mode_raw` est invalide → `DirectoryShareMode.EVERYONE` (sécurité, tout le monde)
- **Parsing utilisateurs** : `split(",")` → `strip()` par élément → suppression des chaînes vides → `list`
- **`SharedDirectorySettingEntry`** : type aioslsk attendu par les `SharesSettings`

### 4.3 Filtrage et assemblage (lignes 274-279)

```python
dossiers_partages = list(
    filter(
        None,
        [
            _parse_share_directory(dossier_1_chemin, dossier_1_mode, dossier_1_utilisateurs),
            _parse_share_directory(dossier_2_chemin, dossier_2_mode, dossier_2_utilisateurs),
        ],
    )
)
```

`filter(None, ...)` élimine les entrées `None` (dossiers non configurés).

### 4.4 Application aux `SharesSettings` (lignes 343-346)

```python
shares=SharesSettings(
    scan_on_start=scan_on_start,         # voir §5
    download=dossier_destination,        # voir §6
    directories=dossiers_partages,       # liste filtrée de SharedDirectorySettingEntry
)
```

---

## 5. Scan au démarrage (`scan_on_start`)

- **Clé config** : `general.scan_on_start` (section Général, pas Partages)
- **Valeur par défaut** : `True`
- **Lecture** : ligne 232 `app_config.get("general.scan_on_start", True)`
- **Rôle** : Détermine si les dossiers partagés sont scannés au démarrage pour indexer les fichiers dans la base de données `library_db`

```python
scan_on_start = app_config.get("general.scan_on_start", True)
```

---

## 6. Dossier de téléchargement (`dossier_destination`)

- **Clé config** : `telechargement.dossier_destination` (section Téléchargement)
- **Rôle** : Chemin où les fichiers téléchargés sont sauvegardés
- **Application** : Passé au paramètre `download` des `SharesSettings` (ligne 345)

```python
dossier_destination = app_config.get("telechargement.dossier_destination", "")
```

---

## 7. Base de données `library_db`

La table `shared_folders` dans `library_db` gère l'indexation des fichiers partagés :

| Colonne | Type | Description |
|---------|------|-------------|
| `path` | TEXT | Chemin du dossier partagé |
| `enabled` | INTEGER | 1 = actif, 0 = désactivé |
| `scanned_at` | DATETIME | Dernier scan du dossier |

La synchronisation entre `app_config` et `library_db` est assurée par `soulseek_client.py` au démarrage via `library_scanner`.

---

## 8. Flux complet (démarrage → réseau)

```
Démarrage application
        │
        ▼
soulseek_client.py
        │
        ├── lit app_config (partages.*, general.scan_on_start, telechargement.dossier_destination)
        │
        ├── _parse_share_directory(dossier_1)
        │     ├── chemin vide ? → None (ignoré)
        │     ├── DirectoryShareMode(mode_raw) → EVERYONE / FRIENDS / USERS
        │     └── parsing utilisateurs CSV → list[str]
        │
        ├── _parse_share_directory(dossier_2)  (idem)
        │
        ├── filter(None, [...]) → élimine les dossiers non configurés
        │
        └── SharesSettings(
                scan_on_start=True,          # scanner les fichiers ?
                download="Q:/Downloads",      # dossier téléchargement
                directories=[                 # dossiers partagés valides
                    SharedDirectorySettingEntry(path="Q:/Musique", mode=EVERYONE, users=[]),
                ]
            )
                │
                ▼
         aioslsk client.init()
                │
                ├── scan_on_start ? → library_scanner.scan() → library_db (shared_folders)
                └── directories → partagés sur le réseau Soulseek
```

---

## 9. Notes techniques

- **Chemin vide = dossier ignoré** : Un dossier dont le chemin n'est pas défini est simplement ignoré par `_parse_share_directory` (retour `None`) et filtré par `filter(None, ...)`. Aucune erreur, aucun partage pour ce dossier.
- **Fallback `EVERYONE`** : Si le mode stocké est invalide (corruption, migration), le code bascule silencieusement sur `EVERYONE` — comportement permissif par défaut.
- **Parsing CSV utilisateurs** : Les espaces autour des virgules sont automatiquement supprimés via `strip()`. Les entrées vides sont ignorées.
- **Deux dossiers max** : L'interface et le backend sont limités à 2 dossiers par conception. Au-delà, modification du code nécessaire.
- **Effet au démarrage** : Les modifications de la page Partages prennent effet au prochain démarrage de l'application (le client Soulseek est initialisé une fois au lancement).
- **`library_db`** : L'indexation des fichiers (scan) est gérée séparément dans la base de données de la bibliothèque. La table `shared_folders` assure le lien entre les dossiers configurés et les fichiers indexés.

---

## Voir aussi

- [Widget config Utilisateurs et Partages](widget-config-utilisateurs-partages.md) — détails des widgets `ConfigDirectoryPicker`, `ConfigCombo`, `ConfigEntry`
- [Service app_config](service-app-config.md) — mécanisme de persistance atomique
- [Architecture de l'application](architecture-application.md) — vue d'ensemble des couches logicielles
- [Interface application](../interface/interface-application.md) — disposition des zones dans la fenêtre principale
