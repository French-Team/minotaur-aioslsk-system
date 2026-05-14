# Spec — Bot Bibliothèque

> **Mission :** Tableau de bord de gestion des fichiers partagés — explorer, filtrer,
> lire et gérer sa bibliothèque locale partagée sur le réseau Soulseek.
> Le bot Bibliothèque **n'est pas** un explorateur de fichiers des autres utilisateurs
> (cela relève du bot Recherche), mais un gestionnaire de ses **propres** partages.

---

## 1. Principes fondamentaux

| Principe | Valeur |
|----------|--------|
| **Nature** | Nouvelle page de bot (tableau de bord), PAS un chatbot |
| **Rôle** | Gestionnaire de bibliothèque locale partagée sur Soulseek |
| **Visibilité** | UNIQUEMENT quand l'utilisateur est connecté à Soulseek |
| **Canal d'entrée** | Footer → `page_changed("Bibliothèque")` → `CenterZone.show_page("Bibliothèque")` |
| **Type d'interface** | Arborescence de dossiers + tableau de fichiers filtrable |

---

## 2. Architecture des fichiers

| Fichier | Rôle |
|---------|------|
| `src/gui/widgets/bots/bot_bibliotheque.py` | Classe principale `BotBibliotheque(QFrame)` + sous-composants UI |
| `src/services/library_db.py` | Service SQLite — scan, indexation, recherche dans la bibliothèque |
| `src/services/library_scanner.py` *(optionnel)* | Scan du disque, extraction des métadonnées audio (tags ID3) |
| `src/gui/widgets/bots/__init__.py` | Export de `BotBibliotheque` |
| `data/bot_bibliotheque.db` | Base SQLite stockant l'index des fichiers partagés (créé auto) |

---

## 3. Interface

### 3.1 Structure visuelle

```
┌──────────────────────────────────────────────────────┐
│  📂 Bibliothèque — Mes fichiers partagés            │
│  ───── stats ──────────────────────────────────────  │
│  [📁 Dossiers 5] [📄 Fichiers 1 234] [🎵 Audio 890] │
│  ───── toolbar ────────────────────────────────────  │
│  [🔍 Rechercher...           ] [🔄 Re-scanner]       │
│  ───── split ──────────────────────────────────────  │
│  ┌──────────────┐ ┌──────────────────────────────┐  │
│  │ 📁 Musique    │ │ Nom              │ Taille    │  │
│  │   📁 Jazz     │ │ track01.mp3     │ 8.2 MB    │  │
│  │   📁 Rock     │ │ track02.mp3     │ 6.1 MB    │  │
│  │ 📁 Vidéos     │ │ album.jpg       │ 120 KB    │  │
│  │ 📁 Logiciels  │ │ setlist.flac    │ 45.3 MB   │  │
│  │              │ │ ...             │           │  │
│  └──────────────┘ └──────────────────────────────┘  │
│  ───── status bar ────────────────────────────────  │
│  [📂 Musique/Rock] — 4 fichiers — 59.7 Mo           │
└──────────────────────────────────────────────────────┘
```

### 3.2 Éléments de l'interface (ordre du layout)

1. **En-tête** — `QLabel` : `"📂 Bibliothèque — Mes fichiers partagés"`
2. **Barre de stats** — `_StatCard` : dossiers / fichiers / fichiers audio
3. **Toolbar** — champ recherche + bouton 🔄 Re-scanner
4. **Vue principale** — split horizontal :
   - **Gauche** (≈280px) : arborescence des dossiers (`QTreeWidget`)
   - **Droite** (stretch) : tableau des fichiers (`QTableWidget`)
5. **Barre de statut** — dossier sélectionné + nombre de fichiers + taille totale

### 3.3 Panneau d'arborescence (gauche)

| Propriété | Valeur |
|-----------|--------|
| Widget | `QTreeWidget` avec **1 colonne** (nom du dossier) |
| Icônes | 📁 pour dossier, pas d'icône pour la racine |
| Style | Fond `#1e1e2e`, bordure `#3a3a4a` |
| Comportement | Clic → charge les fichiers du dossier dans le tableau de droite |
| Racine | `"📂 Racine"` — affiche les **dossiers de premier niveau** uniquement (pas tous les fichiers en vrac) |
| Données | Chargées depuis la SQLite (arbre construit à partir des chemins) |

**Règles :**
- Au premier chargement, la racine `"📂 Racine"` est sélectionnée
- La vue par dossier évite les gros volumes : pas de vue "tous les fichiers" dans l'arbre
- Chaque dossier affiche son nom seul (pas le chemin complet)
- Pas de drag & drop dans un premier temps
- Pas d'icônes de dossier vide (= dossier qui existe sur disque mais sans fichiers indexés)

### 3.4 Tableau des fichiers (droite)

| Colonne | Alignement | Taille | Description |
|---------|-----------|--------|-------------|
| 📄 Nom | Gauche | stretch | Nom du fichier (avec extension) |
| 📏 Taille | Droite | 100px | Taille formatée (Ko, Mo, Go) |
| 🎵 Durée | Droite | 80px | Durée audio (mm:ss) — si applicable |
| 🎧 Bitrate | Droite | 80px | Bitrate (kbps) — si fichier audio |
| 📁 Dossier | Gauche | 180px | Chemin relatif du dossier parent |
| 📅 Modifié | Droite | 120px | Date de dernière modification |

**Règles du tableau :**
- Triable par clic sur chaque en-tête de colonne
- Sélection par ligne entière (`SelectRows`)
- Pas d'édition inline
- Couleurs alternées pour lisibilité
- Barre de progression visible pendant le chargement

### 3.5 Barre de recherche

| Élément | Détail |
|---------|--------|
| Widget | `QLineEdit` avec placeholder `"🔍 Rechercher dans la bibliothèque…"` |
| Portée | Limité au **dossier sélectionné** dans l'arborescence — parcourt les **noms de fichier** + les **tags audio** (artiste, album, titre) si présents |
| Déclencheur | `textChanged` avec debounce 300ms |
| Résultats | Filtre le tableau dans le dossier actif uniquement |
| Réinitialisation | Texte vide → retour au dossier sélectionné |

**Comportement :**
- Si un dossier est sélectionné **ET** le champ recherche est vide → affiche les fichiers du dossier
- Si la recherche est active → affiche les fichiers correspondants **dans le dossier sélectionné**
- Si la recherche est vidée → retour à la vue normale du dossier
- Si la racine `"📂 Racine"` est sélectionnée, la recherche traverse **tous les dossiers** (cas particulier : vue racine = recherche globale)

### 3.6 Bouton 🔄 Re-scanner

| Propriété | Valeur |
|-----------|--------|
| Position | Dans la toolbar, à droite du champ recherche |
| Icône | `🔄` ou `🔃` |
| Action | `_on_rescan()` → scanne les dossiers partagés → met à jour la SQLite → rafraîchit l'UI |
| Pendant le scan | Affiche `"⏳ Scan en cours… X fichiers trouvés"` en barre de statut |
| Scan en arrière-plan | Utilise `QThread` ou `QTimer.singleShot(0, ...)` pour ne pas bloquer l'UI |
| Désactivé pendant scan | Le bouton et la recherche sont désactivés pendant le scan |

---

## 4. Base de données SQLite

### 4.1 Schéma

```sql
CREATE TABLE shared_folders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    path        TEXT    NOT NULL UNIQUE,       -- Chemin absolu du dossier
    label       TEXT,                           -- Nom d'affichage (par défaut = basename)
    enabled     INTEGER NOT NULL DEFAULT 1,     -- 1 = partagé, 0 = exclu
    scanned_at  TEXT,                           -- Dernier scan ISO 8601
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE files (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_id   INTEGER NOT NULL REFERENCES shared_folders(id) ON DELETE CASCADE,
    path        TEXT    NOT NULL UNIQUE,        -- Chemin absolu du fichier
    name        TEXT    NOT NULL,               -- Nom du fichier (sans chemin)
    extension   TEXT    NOT NULL DEFAULT '',     -- Extension en minuscule ('.mp3', '.flac', …)
    size_bytes  INTEGER NOT NULL DEFAULT 0,
    modified_at TEXT,                           -- mtime du fichier (ISO 8601)
    
    -- Métadonnées audio (extraites par tag reader)
    bitrate     INTEGER,                        -- kbps
    duration    INTEGER,                        -- secondes
    artist      TEXT,                           -- Tag ID3: artiste
    album       TEXT,                           -- Tag ID3: album
    title       TEXT,                           -- Tag ID3: titre
    track       INTEGER,                        -- Tag ID3: numéro de piste
    year        INTEGER,                        -- Tag ID3: année
    
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_files_folder ON files(folder_id);
CREATE INDEX idx_files_name ON files(name);
CREATE INDEX idx_files_extension ON files(extension);
CREATE INDEX idx_files_artist ON files(artist);
CREATE INDEX idx_files_album ON files(album);
CREATE INDEX idx_files_title ON files(title);
```

### 4.2 Méthodes du service `LibraryDB`

| Méthode | Retour | Description |
|---------|--------|-------------|
| `get_folders()` | `list[dict]` | Liste des dossiers partagés activés |
| `get_folder_tree()` | `list[dict]` | Arborescence complète (dict imbriqué) |
| `get_files(folder_id, search, sort_by, order)` | `list[dict]` | Fichiers d'un dossier, avec filtres |
| `get_file(id)` | `dict\|None` | Fichier unique avec toutes ses métadonnées |
| `search(query)` | `list[dict]` | Recherche plein texte (nom + tags) |
| `get_stats()` | `dict` | Nombres : dossiers, fichiers, audio, taille totale |
| `scan_folder(path)` | `int` | Scanne un dossier et indexe les nouveaux fichiers |
| `scan_all()` | `ScanResult` | Scanne tous les dossiers, retourne stats du scan |
| `remove_file(id)` | `bool` | Retire un fichier de l'index (ne supprime PAS du disque) |
| `remove_folder(id)` | `bool` | Retire un dossier et ses fichiers de l'index |
| `add_folder(path)` | `int\|None` | Ajoute un dossier à partager et le scanne |

### 4.3 ScanResult

```python
@dataclass
class ScanResult:
    folders_scanned: int
    files_found: int
    files_new: int
    files_removed: int       # fichiers qui n'existent plus sur disque
    errors: list[str]        # dossiers inaccessibles, fichiers corrompus…
    duration_ms: int
```

---

## 5. Actions sur les fichiers

### 5.1 Menu contextuel (clic droit)

Chaque fichier dans le tableau propose un menu contextuel avec :

| Action | Comportement |
|--------|-------------|
| **👁️ Voir les infos** | Ouvre une popup `FileInfoPopup` avec toutes les métadonnées |
| **▶️ Lire le fichier** | Ouvre le fichier avec l'application système par défaut (`QDesktopServices.openUrl()`) |
| **🗑️ Supprimer** | Ouvre une **popup de confirmation** demandant à l'utilisateur de choisir : |
| | → **Retirer des partages** : supprime seulement de l'index SQLite |
| | → **Supprimer du disque** : supprime l'index + efface le fichier du disque |
| | → **Annuler** : ne fait rien |

### 5.2 `FileInfoPopup`

Popup modale avec :

```
┌─────────────────────────────────────────┐
│  👁️ Informations — track01.mp3         │
│  ─────────────────────────────────────  │
│  📄 Nom        track01.mp3              │
│  📏 Taille     8 245 120 octets (8.2MB) │
│  📁 Dossier    /Musique/Rock            │
│  📅 Modifié    14/05/2026 à 14:30       │
│  ─── Audio ─────────────────────────── │
│  🎵 Artiste    Led Zeppelin             │
│  💿 Album      Physical Graffiti        │
│  🎵 Titre      Custard Pie              │
│  #️⃣ Piste      1                         │
│  📅 Année      1975                     │
│  🎧 Bitrate    320 kbps                 │
│  ⏱ Durée      4:15                      │
│  ─────────────────────────────────────  │
│          [▶️ Lire] [🗑️ Supprimer] [Fermer] │
└─────────────────────────────────────────┘
```

---

## 6. Intégration Soulseek

### 6.1 Connexion avec le partage Soulseek

Le bot Bibliothèque gère ses propres dossiers partagés **indépendamment** du système de config existant (`app_config`). La source de vérité est la **base SQLite**.

> **🔍 Résultat de la recherche — API aioslsk pour les partages**
>
> Le module `aioslsk.shares` expose tout ce qu'il faut. Voici l'API exacte :
>
> ### `SharesManager` (accessible via `client.shares`)
>
> | Méthode | Signature | Description |
> |---------|-----------|-------------|
> | **`add_shared_directory()`** | `(shared_directory: str, share_mode: DirectoryShareMode = EVERYONE, users: Optional[list[str]] = None) -> SharedDirectory` | Ajoute un dossier aux partages. Génère un alias, émet `SharedDirectoryChangeEvent`. |
> | **`remove_shared_directory()`** | `(directory: Union[str, SharedDirectory]) -> SharedDirectory` | Retire un dossier. Si un dossier parent existe, ses fichiers y sont déplacés. |
> | **`update_shared_directory()`** | `(directory: Union[str, SharedDirectory], share_mode: Optional[DirectoryShareMode] = None, users: Optional[list[str]] = None) -> SharedDirectory` | Met à jour le mode de partage d'un dossier. Retourne le dossier mis à jour. |
> | **`scan()`** | `async () -> None` | Scanne tous les dossiers partagés : fichiers + attributs audio (via `mutagen`). Émet `ScanCompleteEvent`. |
> | **`query()`** | `(query: Union[str, SearchQuery], username: Optional[str] = None, excluded_search_phrases: Optional[list[str]] = None) -> tuple[list[SharedItem], list[SharedItem]]` | Recherche dans les fichiers partagés (term map). |
> | **`get_stats()`** | `() -> tuple[int, int]` | Retourne `(folder_count, file_count)` des partages actuels. |
> | **`load_from_settings()`** | `() -> None` | Charge les dossiers depuis la config `settings.shares.directories`. |
> | **`is_directory_shared()`** | `(directory: str) -> bool` | Vérifie si un chemin est déjà partagé. |
> | **`get_shared_directory()`** | `(directory: str) -> SharedDirectory` | Récupère un `SharedDirectory` par chemin. |
>
> ### Modèles
>
> **`SharedDirectory`** (dataclass) :
> - `directory: str` — chemin relatif/visible
> - `absolute_path: str` — chemin absolu sur disque
> - `alias: str` — alias court généré automatiquement
> - `share_mode: DirectoryShareMode` — `EVERYONE`, `FRIENDS`, `USERS`, `NONE`
> - `users: list[str]` — utilisateurs autorisés (si mode `USERS`)
> - `items: set[SharedItem]` — fichiers dans ce dossier
>
> **`SharedItem`** (dataclass) :
> - `shared_directory: SharedDirectory` — dossier parent
> - `subdir: str` — sous-chemin relatif
> - `filename: str` — nom du fichier
> - `modified: float` — timestamp de modification
> - `attributes: Optional[list[tuple[int, int]]]` — attributs (paires type/valeur : bitrate, durée, etc.)
>
> ### Événements
>
> | Événement | Attributs | Description |
> |-----------|-----------|-------------|
> | **`ScanCompleteEvent`** | `folder_count: int, file_count: int` | Émis quand le scan de tous les partages est terminé |
> | **`SharedDirectoryChangeEvent`** | `shared_directory: SharedDirectory` | Émis quand un dossier est ajouté/supprimé/modifié |
>
> ### Configuration (`Settings`)
>
> ```python
> class SharesSettings(BaseModel):
>     scan_on_start: bool = True          # Scan auto au démarrage du client
>     download: str = os.getcwd()         # Dossier de téléchargement
>     directories: list[SharedDirectorySettingEntry] = []
>
> class SharedDirectorySettingEntry(BaseModel):
>     path: str
>     share_mode: DirectoryShareMode = DirectoryShareMode.EVERYONE
>     users: list[str] = Field(default_factory=list)
> ```
>
> ### Câblage avec le client
>
> ```python
> client = soulseek.Client(settings=settings, ...)
> client.start()
>
> # Le SharesManager est auto-initialisé
> client.shares  # -> SharesManager
>
> # Scan auto si settings.shares.scan_on_start == True
> # Effectué dans asyncio.create_task(self.shares.scan()) au démarrage
>
> # Ajouter un dossier partagé
> sd = client.shares.add_shared_directory("/chemin/musique")
>
> # Déclencher un scan manuel
> await client.shares.scan()
>
> # Obtenir les stats
> folders, files = client.shares.get_stats()
> ```
>
> **Tag extraction :** `mutagen` est utilisé en interne par `SharesManager._extract_attributes_callback()` pour extraire bitrate, durée, sample rate des fichiers audio.

### 6.2 Signalisation

| Signal | Émetteur | Récepteur |
|--------|----------|-----------|
| `page_changed(str)` | `BotBibliotheque` | `CenterZone.show_page()` |
| `scan_started` | `LibraryDB` | `BotBibliotheque._on_scan_started()` |
| `scan_progress(int, int)` | `LibraryDB` | `BotBibliotheque._on_scan_progress()` |
| `scan_completed(ScanResult)` | `LibraryDB` | `BotBibliotheque._on_scan_completed()` |
| `scan_error(str)` | `LibraryDB` | `BotBibliotheque._on_scan_error()` |

---

## 7. Gestion d'état

| État | UI | Comportement |
|------|----|-------------|
| **Déconnecté** | Message : `"🔒 Connecte-toi à Soulseek pour accéder à ta bibliothèque"` | Tableau + arbre désactivés |
| **Connecté — 1er accès** | Message : `"📂 Aucun dossier partagé. Ajoute des dossiers pour commencer."` | Bouton `📁 Ajouter un dossier` visible |
| **Connecté — avec données** | Arbre + tableau affichés normalement | — |
| **Scan en cours** | Barre de statut : `"⏳ Scan en cours… 542 fichiers trouvés"` | Bouton Re-scanner désactivé, UI responsive |
| **Scan terminé** | Barre de statut : `"✅ Scan terminé — 1 234 fichiers indexés en 2.3s"` | Tout réactivé, arbre rafraîchi |
| **Erreur de scan** | Notification : `"⚠️ Erreur : dossier introuvable — /Musique/Perdu"` | Les autres dossiers restent accessibles |

---

## 8. Cas aux limites

| Cas | Comportement |
|-----|-------------|
| **Dossier supprimé du disque** | Détecté au scan → fichiers marqués `files_removed` → retirés de l'index silencieusement |
| **10k+ fichiers dans un dossier** | Navigation par dossier = pas de vue \"tous les fichiers\" → pas de problème de performance |
| **Tags audio absents/corrompus** | Colonnes artiste/album/titre vides, bitrate/durée = `None` |
| **Format non-audio** | Extension non-reconnue → pas de métadonnées audio, s'affiche normalement |
| **Fichier en lecture seule** | `QDesktopServices.openUrl()` gère nativement — pas d'action spéciale |
| **Chemin trop long (Windows 260+)** | Géré par `pathlib` / `\\?\` — à noter pour le scan |
| **Dossier déjà indexé** | `add_folder()` vérifie l'unicité → retourne l'ID existant |
| **Base de données corrompue** | Détecté à l'ouverture → recréation de la base + rescan complet recommandé |

---

## 9. Contraintes techniques

| Contrainte | Valeur |
|------------|--------|
| **Dépendances** | PySide6 (QtCore, QtWidgets, QtGui), `sqlite3` (stdlib), `pathlib`, `json`, `dataclasses` |
| **Tags audio** | `mutagen` — déjà présent comme dépendance transitive d'aioslsk (utilisé pour les métadonnées audio) |
| **Scan disque** | `os.scandir()` ou `pathlib.Path.rglob()` — récursif mais threadé |
| **Thread safety SQLite** | Scan dans `QThread` séparé → connexion SQLite créée dans ce thread (`check_same_thread=False` sur la connexion partagée, ou connexion par thread) |
| **Performance** | Scan distant dans un thread séparé (`QThread`), pas dans le thread principal |
| **Stockage** | Base SQLite unique dans `data/bot_bibliotheque.db` |
| **Export** | `BotBibliotheque` exporté depuis `src/gui/widgets/bots/__init__.py` |
| **Intégration** | Pages ajoutée dans `CenterZone._build_bibliotheque_page()` — déjà référencée dans le routeur |

---

## 10. Règles & Comportement

### 10.1 Ce que le bot PEUT faire

- Afficher l'arborescence complète des dossiers partagés
- Afficher les fichiers d'un dossier avec leurs métadonnées
- Filtrer/rechercher dans tous les fichiers de la bibliothèque
- Ouvrir un fichier avec l'application système (lecteur audio/vidéo par défaut)
- Afficher les informations détaillées d'un fichier (taille, tags audio, dates)
- Supprimer un fichier des partages (avec confirmation : retrait de l'index ou suppression disque)
- Scanner/indexer automatiquement les dossiers au démarrage
- Re-scanner manuellement via un bouton dédié
- Ajouter de nouveaux dossiers à partager

### 10.2 Ce que le bot NE fait PAS (v1)

- Pas d'exploration des fichiers des autres utilisateurs (c'est le rôle du bot Recherche)
- Pas de téléchargement depuis d'autres utilisateurs
- Pas de gestion des téléchargements en cours (c'est le rôle du bot Téléchargement)
- Pas de drag & drop pour réorganiser les fichiers
- Pas de serveur web / partage HTTP
- Pas de conversion de formats audio
- Pas de synchronisation cloud
- Pas d'édition des tags audio

### 10.3 Messages clés

**Message déconnecté :**
```
🔒 Connecte-toi à Soulseek pour accéder à ta bibliothèque.
```
Suggestions → `[🔌 Connexion]`

**Message premier accès (aucun dossier partagé) :**
```
📂 Aucun dossier partagé pour l'instant.
Ajoute un dossier pour commencer à partager tes fichiers sur Soulseek.
```
Bouton → `[📁 Ajouter un dossier]`

**Message scan en cours :**
```
⏳ Scan en cours… {count} fichiers trouvés dans {dossier}
```

**Message scan terminé :**
```
✅ Scan terminé — {total} fichiers indexés en {duration}s
{new} nouveaux • {removed} supprimés • {errors} erreurs
```

**Message erreur scan dossier :**
```
⚠️ Dossier introuvable ou inaccessible : {path}
```

---

## 11. Intégration dans CenterZone

### 11.1 `center.py`

```python
from src.gui.widgets.bots.bot_bibliotheque import BotBibliotheque

class CenterZone(QFrame):
    def __init__(self, ...):
        # ...
        # Bibliothèque retiré de la boucle générique des bots (comme Accueil/Recherche)
        self._build_bibliotheque_page()

    def _build_bibliotheque_page(self) -> None:
        page = BotBibliotheque()
        page.page_changed.connect(self.show_page)
        self._pages["Bibliothèque"] = page
        self._stack.addWidget(page)
```

### 11.2 Pages concernées

| Clé | Composant | Usage |
|-----|-----------|-------|
| `"Bibliothèque"` (majuscule) | `BotBibliotheque` | Gestionnaire de bibliothèque locale |

---

## 12. Dictionnaire d'intégration (KNOWLEDGE)

Mise à jour de `bot_accueil_knowledge.py` :

```python
"bibliotheque": {
    "keywords": [
        "bibliothèque", "bibliotheque", "library", "biblio",
        "partage", "fichier", "dossier", "explorer",
        "musique", "album", "artist",
    ],
    "icon": "📂",
    "response": "Le bot <b>Bibliothèque</b> te permet d'explorer "
                "tes fichiers partagés sur Soulseek.<br><br>"
                "Tu peux naviguer par dossier, rechercher un fichier, "
                "voir ses infos et le lire directement depuis l'appli.",
    "actions": [
        {"type": "navigate", "bot": "Bibliothèque", "icon": "📂"},
    ],
    "suggestions": [
        {"label": "📂 Explorer", "action": "bibliotheque"},
        {"label": "🏠 Accueil", "action": "welcome"},
    ],
},
```

Et dans l'entrée `qui_es_tu`, ajouter `📂 Bibliothèque` à la liste des bots.

---

## 13. Schéma de la base (détail SQLite)

### 13.1 Création

Fichier : `src/services/library_db.py`

```python
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field

DB_PATH = Path("data/bot_bibliotheque.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
```

### 13.2 Migration

Pour les futures versions, un champ `schema_version` peut être ajouté :

```python
def get_schema_version(conn) -> int:
    row = conn.execute("PRAGMA user_version").fetchone()
    return row[0] if row else 0

def migrate(conn: sqlite3.Connection) -> None:
    version = get_schema_version(conn)
    if version < 1:
        conn.executescript(SCHEMA_V1)
        conn.execute("PRAGMA user_version = 1")
```

---

## 14. Étapes d'implémentation

| # | Tâche | Statut |
|---|-------|--------|
| 1 | **Service SQLite** — `library_db.py` : création, schéma, connexion, CRUD basique | ⬜ |
| 2 | **Scanner disque** — scan récursif des dossiers, extraction des tags audio | ⬜ |
| 3 | **`BotBibliotheque` — layout de base** : header, stats cards, toolbar | ⬜ |
| 4 | **Arborescence des dossiers** — `QTreeWidget` alimenté par la SQLite | ⬜ |
| 5 | **Tableau des fichiers** — `QTableWidget` avec colonnes, tri, sélection | ⬜ |
| 6 | **Recherche dans la bibliothèque** — champ texte avec debounce + requête SQL | ⬜ |
| 7 | **Re-scanner** — bouton + scan threadé + mise à jour UI | ⬜ |
| 8 | **Menu contextuel** — infos / lire / supprimer (avec popup de confirmation) | ⬜ |
| 9 | **FileInfoPopup** — fenêtre modale avec toutes les métadonnées | ⬜ |
| 10 | **Scan automatique au démarrage** — déclenché à la connexion | ⬜ |
| 11 | **Intégration aioslsk** — connexion avec l'API partagée de Soulseek | ⬜ |
| 12 | **Intégration CenterZone** — `_build_bibliotheque_page()` | ⬜ |
| 13 | **Mise à jour KNOWLEDGE** — entrée `bibliotheque` dans `bot_accueil_knowledge.py` | ⬜ |
| 14 | **Tests unitaires** — `LibraryDB` + `BotBibliotheque` (instanciation, scan, filtres) | ⬜ |
| 15 | **Spécification finalisée** | ✅ |
