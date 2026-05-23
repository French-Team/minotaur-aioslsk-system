# Spec — Bot Recherche V2 : Workflow de Recherche par Mode

> **Statut :** 📝 Brouillon — spec issue des interviews utilisateur
> **Dernière mise à jour :** 2026-07-05
> **Contexte :** Nouveau système de recherche pour Athéna (BotRecherche) qui remplace/coexiste avec la v1. **Priorité #1 : valider qu'on peut cibler un client actif & joignable (Arès) avec une recherche standard Soulseek en mode Normal**, puis étendre aux modes Club, Label, Artiste avec exploration d'arborescence via `PeerGetDirectoryContentCommand`.

---

## 1. Principes fondamentaux

| Principe | Valeur |
|----------|--------|
| **Mission** | Dénicher des dossiers chez les clients actifs (Arès) correspondant à des clubs, labels, artistes electro, via analyse de chemins de dossiers |
| **Approche** | Exploration par silos : on vérifie d'abord les dossiers de niveau 1 (techno, house, trance...), si le client n'a pas ça, on l'oublie |
| **Moteur** | `PeerGetDirectoryContentCommand(username, directory)` — navigation dans l'arborescence dossier par dossier |
| **Phase 0** | Valider la recherche normale sur un client actif & joignable ciblé depuis Arès |
| **Phase 1** | Analyse exploratoire : examiner 3 clients réels pour comprendre les structures de dossiers partagés |
| **Déclencheur** | Zeus (BotAccueil) demande à Athéna d'exécuter une recherche en mode spécifique |
| **Consommateurs** | Tous les bots (Recherche, Wishlist, Planificateur) peuvent utiliser le MatchingService |

### Terminologie

| Terme | Définition |
|-------|------------|
| **Silo** | Niveau 1 de l'arborescence d'un client. Doit contenir des dossiers musicaux (techno, house, trance...) pour qu'on explore plus profondément |
| **MatchingService** | Service central qui matche les chemins de dossiers contre les listes de mots-clés |
| **Mode** | Club / Label / Artiste / Normal — détermine quelles listes JSON sont utilisées et quel algorithme de matching est appliqué |
| **Dénicher** | Action de retrouver le dossier recherché chez un client distant en explorant son arborescence |
| **Cache BDD** | Base SQLite qui stocke les résultats de matching pour éviter de rescanner au prochain cycle |

---

## 2. Architecture des fichiers

| Fichier | Rôle |
|---------|------|
| `specs/bot-recherche-v2-workflow-spec.md` | Cette spec |
| `src/gui/widgets/bots/bot_recherche.py` | Classe `BotRecherche` — page Athéna repensée (v2) |
| `src/services/matching_service.py` | `MatchingService` — matching de chemins dossiers |
| `src/services/matching_db.py` | Cache SQLite des résultats de matching |
| `data/matching_cache.db` | Base de données de cache persistante |
| `data/mots_cles/clubs.json` | Liste des clubs par pays (nom, mots-clés, métadonnées) |
| `data/mots_cles/labels.json` | Liste des labels par pays |
| `data/mots_cles/artistes.json` | Liste des artistes electro par pays |
| `data/mots_cles/mots_interdits.json` | Mots exclus par mode de recherche |
| `data/mots_cles/mots_silos.json` | Mots-clés autorisés pour les silos (niveau 1) |
| `src/services/connexion_manager.py` | Ajout de `browse_user_directory()` pour `PeerGetDirectoryContentCommand` |
| `src/gui/layout/center.py` | Mise à jour de `_build_recherche_page()` pour la v2 |

---

## 3. Interface Athéna (BotRecherche V2)

### 3.1 Structure visuelle — Nouveau layout

```
┌─────────────────────────────────────────────────────────────┐
│  🔍 Recherche ciblée        [⚙️ Mode Exploration] [📜 Hist.]│
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
││  [🔎 Normal] [🏛 Club] [🏷 Label] [🎤 Artiste]      │    │  ← 4 boutons de mode (Normal en premier)
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─ Zone de configuration (selon mode) ─────────────────┐    │
│  │   Pays : [▼ Belgique        ]   ← liste déroulante   │    │
│  │   Club : [▼ La Rocca        ]   ← en cascade          │    │
│  │   Mots-clés : [techno, house, trance...]              │    │
│  │                                                       │    │
│  │   [🚀 Lancer la chasse]   [⏹ Stop]                   │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─ Résultats des dossiers trouvés ─────────────────────┐    │
│  │  Client          │ Dossier trouvé        │ Match     │    │
│  │──────────────────────────────────────────────────────│    │
│  │  DJ_Techno       │ /Music/Club/La Rocca │ 92%       │    │
│  │  ElectroFan42    │ /Audio/La_Rocca_Mix  │ 85%       │    │
│  │  BelgianBeats    │ /Techno/Belgium/Rocca│ 78%       │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  [📥 Explorer le dossier] [⬇ Télécharger] [🔄 Nouveau scan]  │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Les 4 modes de recherche (Normal en premier)

#### Mode Normal (🔎) — PRIORITÉ #1 — Phase de validation
- **Barre de recherche texte** + **sélection d'un client depuis la liste Arès**
- **Mécanisme** : `client.searches.search(query)` avec filtre côté réception : on ne garde que les résultats dont le `username` correspond au client ciblé
- **Objectif** : Valider qu'on arrive à chercher et recevoir des fichiers **uniquement d'un client actif & joignable**
- **Tests de validation** :
  1. Sélectionner un client depuis la liste Arès (clients valides)
  2. Lancer une recherche (ex: "techno mix")
  3. Vérifier que les résultats sont bien filtrés par username
  4. Logger : nb résultats, latence, username cible
- **Reste compatible** : Filtres avancés, tableau triable, tout l'existant v1

#### Mode Club (🏛)
- **Listes déroulantes en cascade** : Pays → Club
- **JSON source** : `data/mots_cles/clubs.json`
- **Matching** : Chemins contenant le nom du club + mots-clés du contexte (techno, house, trance, années 90/2000, pays)
- **Exemple** : Club "La Rocca" (Belgique) → mots-clés : `la rocca, rocca, belgique, liège, 1995, 2005, techno, house`

#### Mode Label (🏷)
- **Listes déroulantes en cascade** : Pays → Label
- **JSON source** : `data/mots_cles/labels.json`
- **Matching** : Chemins contenant le nom du label + mots-clés du style
- **Exemple** : Label "R&S Records" (Belgique) → `r&s, rands, belgique, techno, trance, 1990, 2000`

#### Mode Artiste (🎤)
- **Listes déroulantes en cascade** : Pays → Artiste (ou recherche texte dans les artistes)
- **JSON source** : `data/mots_cles/artistes.json`
- **Matching** : Chemins contenant le nom de l'artiste + variantes possibles
- **Exemple** : Artiste "Jeff Mills" (USA) → `jeff mills, mills, detroit, techno, wizard`

### 3.3 Structure des données JSON

#### clubs.json — format
```json
{
  "version": "1.0",
  "meta": {
    "description": "Clubs mythiques 1995-2005 par pays",
    "source": "Recherche web / connaissances utilisateur",
    "last_updated": "2026-07-05"
  },
  "data": [
    {
      "id": "la-rocca",
      "name": "La Rocca",
      "country": "Belgique",
      "city": "Liège",
      "years_active": "1995-2005",
      "style": ["techno", "house", "trance"],
      "keywords": ["la rocca", "rocca", "liege", "belgique"],
      "variants": ["La Rocca", "Rocca Club", "LaRocca"]
    },
    {
      "id": "fuse",
      "name": "Fuse",
      "country": "Belgique",
      "city": "Bruxelles",
      "years_active": "1994-présent",
      "style": ["techno", "house", "electronic"],
      "keywords": ["fuse", "brussels", "bruxelles"],
      "variants": ["Fuse", "Fuse Club"]
    }
  ]
}
```

#### labels.json — format
```json
{
  "version": "1.0",
  "data": [
    {
      "id": "rs-records",
      "name": "R&S Records",
      "country": "Belgique",
      "city": "Gand",
      "years_active": "1984-présent",
      "style": ["techno", "trance", "electronic"],
      "keywords": ["r&s", "rands", "rs records", "ghent"],
      "variants": ["R&S Records", "R&S", "R and S"]
    }
  ]
}
```

#### artistes.json — format
```json
{
  "version": "1.0",
  "data": [
    {
      "id": "jeff-mills",
      "name": "Jeff Mills",
      "country": "USA",
      "city": "Détroit",
      "years_active": "1985-présent",
      "style": ["techno", "detroit techno"],
      "keywords": ["jeff mills", "mills", "detroit", "wizard"],
      "variants": ["Jeff Mills", "The Wizard", "True Essence"]
    }
  ]
}
```

### 3.4 Mots interdits (par mode) — `mots_interdits.json`
```json
{
  "clubs": {
    "exclude": ["rock", "samba", "indie", "video", "ebook", "pdf", "images", "jeux"],
    "priority_exclude": ["cover", "photos", "artwork"]
  },
  "labels": {
    "exclude": ["rock", "pop", "rap", "video", "ebook", "pdf"],
    "priority_exclude": ["commercial", "pop"]
  },
  "artistes": {
    "exclude": ["cover", "remix", "live", "video", "pdf"],
    "priority_exclude": ["karaoke", "bootleg"]
  }
}
```

**Important :** Le mode Normal n'utilise PAS les mots silos, ni le matching de chemins. Il utilise `SearchCommand` directement, comme la v1, mais en ciblant un username. Les silos ne sont utilisés que pour les modes Club/Label/Artiste.

### 3.5 Mots silos (niveau 1) — `mots_silos.json`
```json
{
  "silos": {
    "include": [
      "music", "musique", "audio", "mp3", "flac",
      "techno", "house", "trance", "electronic", "electro",
      "dance", "club", "mix", "sets", "vinyl", "cd",
      "partages", "shared", "downloads", "telechargements"
    ],
    "exclude": [
      "video", "films", "movies", "ebooks", "documents",
      "photos", "images", "jeux", "games", "software"
    ]
  }
}
```

---

## 4. MatchingService

### 4.1 Responsabilités

```python
class MatchingService(QObject):
    """Service central de matching de chemins de dossiers.

    Reçoit une liste de clients actifs (Arès), explore leur arborescence
    via PeerGetDirectoryContentCommand, et match les dossiers contre
    les listes de mots-clés du mode sélectionné.
    """

    matching_termine = Signal(list)  # [MatchResult, ...]
    """Émis quand le matching est terminé — contient les résultats."""

    progression = Signal(int, int)  # client_index, total_clients
    """Émis à chaque nouveau client exploré."""

    client_analyse = Signal(str, list)  # username, [dossiers_niveau1, ...]
    """Émis pour chaque client analysé, avec la structure de ses dossiers racine."""
```

### 4.2 Algorithme de matching

```
Pour chaque client actif (Arès) :
  1. Vérifier les silos (niveau 1)
     - Explorer les dossiers racine du client via PeerGetDirectoryContentCommand
     - Si au moins un dossier racine match les mots silos → continuer
     - Si AUCUN dossier musical → ignorer ce client (pas un pair audio)

  2. Explorer les niveaux 2 et 3
     - Pour chaque dossier silo trouvé, descendre dans les sous-dossiers
     - Max 3 niveaux de profondeur

  3. Matcher contre les mots-clés du mode
     - Normaliser les noms de dossiers (minuscules, sans accents)
     - Calculer un score de matching : combien de keywords sont présents dans le chemin
     - Score > 50% = dossier potentiel
     - Appliquer les mots interdits : si un mot interdit est dans le chemin → rejeté

  4. Sauvegarder dans le cache BDD
     - Si un dossier match, enregistrer (client, chemin, mode, score, timestamp)
     - Prochaine itération : checker le cache avant de rescanner
```

### 4.3 Structure MatchResult

```python
@dataclass
class MatchResult:
    username: str
    """Nom du client chez qui le dossier a été trouvé."""

    chemin_dossier: str
    """Chemin complet du dossier matché (ex: /Music/Club/La Rocca)."""

    mode: str
    """Mode de recherche qui a matché (club, label, artiste)."""

    entite_id: str
    """ID de l'entité matchée (ex: 'la-rocca')."""

    entite_nom: str
    """Nom de l'entité matchée (ex: 'La Rocca')."""

    score: float
    """Score de matching (0.0 - 1.0)."""

    mots_cles_trouves: list[str]
    """Liste des mots-clés qui ont matché dans le chemin."""

    timestamp: float
    """Quand ce matching a été fait."""

    statut_client: str
    """Statut du client au moment du matching."""

    silos_trouves: list[str]
    """Dossiers racine musicaux trouvés chez ce client."""
```

### 4.4 Logique de silo

```
Fonction verifier_silos(client_username) → (bool, liste_silos):
    """
    Explore les dossiers racine d'un client.
    
    1. Envoie PeerGetDirectoryContentCommand(username, "/")
    2. Récupère la liste des dossiers de niveau 1
    3. Match chaque nom de dossier contre mots_silos["include"]
    4. Si 0 match → client ignoré (return False, [])
    5. Si ≥ 1 match → client accepté (return True, [dossiers_matchés])
    """

Fonction explorer_niveau(chemin, profondeur, max_profondeur=3) → liste_chemins:
    """
    Explore récursivement l'arborescence jusqu'à max_profondeur.
    Pour chaque dossier :
    - Normaliser le nom
    - Vérifier les mots interdits du mode
    - Si pas de mots interdits → continuer la descente
    - Si matche les mots-clés de l'entité → ajouter aux résultats
    """
```

---

## 5. Phase 1 : Analyse exploratoire des clients

### 5.1 Objectif

Analyser 3 clients actifs (depuis Arès) pour comprendre la structure réelle de leurs dossiers partagés. Cette phase permet de :

- Valider l'hypothèse des silos (les clients electro ont-ils vraiment des dossiers "techno", "house"?)
- Observer les conventions de nommage (minuscules, underscore, espaces)
- Détecter les patterns d'organisation (par genre, par artiste, par label, par année)
- Ajuster les listes de mots-clés et mots interdits

### 5.2 Mode Exploration dans Athéna

Le mode ⚙️ **Exploration** est intégré dans Athéna. Il permet :

1. **Sélectionner un client** depuis la liste d'Arès
2. **Explorer** son arborescence jusqu'à 3 niveaux
3. **Visualiser** la structure sous forme d'arbre :
```
DJ_Techno (🟢 ONLINE)
├── Music/
│   ├── Techno/
│   │   ├── Jeff Mills
│   │   ├── Laurent Garnier
│   │   └── Compilations
│   ├── House/
│   └── Trance/
├── Video/              ← silo exclu
└── Documents/          ← silo exclu
```
4. **Stocker** les résultats en base (cache) pour analyse différée
5. **Exporter** la structure en JSON pour référence

### 5.3 Métriques collectées

Pour chaque client exploré :

| Métrique | Description |
|----------|-------------|
| Nombre de dossiers racine | Total dossiers niveau 1 |
| Dossiers musicaux | Ceux qui passent le filtre silo |
| Profondeur max | Jusqu'où va l'arborescence musicale |
| Conventions nommage | CamelCase, snake_case, espaces, points |
| Présence d'années | Y a-t-il des dossiers "1995", "2000"? |
| Organisation | Par genre / par artiste / par label / par année |

---

## 6. Cache BDD (SQLite) — `data/matching_cache.db`

### 6.1 Schéma

```sql
CREATE TABLE clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    derniere_exploration REAL NOT NULL,  -- timestamp
    statut TEXT DEFAULT 'UNKNOWN',
    nb_dossiers_racine INTEGER DEFAULT 0,
    nb_dossiers_musicaux INTEGER DEFAULT 0,
    silos_trouves TEXT DEFAULT '[]',  -- JSON array
    structure_complete TEXT DEFAULT '[]'  -- JSON — arbre complet
);

CREATE TABLE match_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    client_username TEXT NOT NULL,
    chemin_dossier TEXT NOT NULL,
    mode TEXT NOT NULL,  -- 'club', 'label', 'artiste'
    entite_id TEXT NOT NULL,
    entite_nom TEXT NOT NULL,
    score REAL NOT NULL DEFAULT 0.0,
    mots_cles_trouves TEXT NOT NULL DEFAULT '[]',  -- JSON array
    timestamp REAL NOT NULL,
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

CREATE TABLE analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    timestamp REAL NOT NULL,
    niveau_max INTEGER DEFAULT 0,
    structure TEXT NOT NULL DEFAULT '[]',  -- JSON — arbre exploré
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

CREATE INDEX idx_match_mode ON match_results(mode);
CREATE INDEX idx_match_client ON match_results(client_username);
CREATE INDEX idx_match_entite ON match_results(entite_id);
```

### 6.2 Politique de cache

| Action | Règle |
|--------|-------|
| **Écriture** | Après chaque matching réussi (client + dossier matché) |
| **Relecture** | Avant de rescanner un client, checker si le cache est encore frais (< 1h) |
| **Expiration** | Cache valide 1 heure. Après 1h, rescanner le client |
| **Nettoyage** | Si un client n'est plus actif depuis 24h, ses entrées peuvent être purgées |

> **Note :** Le cache BDD n'est pas utilisé par le mode Normal (phase de validation). Il sera créé quand les modes Club/Label/Artiste seront implémentés.

---

## 7. Intégration avec Arès (ClientsActifsService)

### 7.1 Flux de données

```
BoucleRooms → membres → ClientsActifsService → ping → clients valides
                                                       │
                                                       ▼
                                              MatchingService
                                                       │
                                                       ▼
                                              Athéna (BotRecherche v2)
                                              Wishlist, Planificateur
```

### 7.2 API ConnexionManager — Nouvelle méthode

```python
class ConnexionManager(QObject):
    async def browse_user_directory(self, username: str, directory: str = "/") -> list[dict]:
        """Explore le contenu d'un dossier partagé chez un utilisateur distant.
        
        Utilise PeerGetDirectoryContentCommand pour lister les fichiers
        et sous-dossiers d'un répertoire chez un pair Soulseek.
        
        Paramètres
        ----------
        username : str
            Nom de l'utilisateur distant.
        directory : str
            Chemin du dossier à explorer (défaut: racine "/").
        
        Retourne
        --------
        list[dict]
            Liste des entrées du dossier, chaque entrée contient :
            - name: nom du fichier/dossier
            - type: "file" ou "directory"
            - size: taille (fichiers uniquement)
            - extension: extension (fichiers uniquement)
        """
```

---

## 8. Zeus (BotAccueil) — Workflow conversationnel

### 8.1 Intentions Zeus → Athéna

Dans `KNOWLEDGE`, ajouter des intentions spécifiques :

```python
KNOWLEDGE: dict[str, dict] = {
    "club_recherche": {
        "patterns": [
            "cherche des clubs", "club mythique", "club 1995", "club 2000",
            "trouve des clubs", "recherche club", "la rocca", "fuse"
        ],
        "actions": [
            {"type": "navigate", "bot": "Recherche"},
            {"type": "set_mode", "mode": "club"},  # Nouvelle action
        ],
        "suggestions": [...]
    },
    "label_recherche": {
        "patterns": ["cherche label", "label electro", "label techno"],
        "actions": [
            {"type": "navigate", "bot": "Recherche"},
            {"type": "set_mode", "mode": "label"},
        ]
    },
    "artiste_recherche": {
        "patterns": ["cherche artiste", "artiste electro", "jeff mills"],
        "actions": [
            {"type": "navigate", "bot": "Recherche"},
            {"type": "set_mode", "mode": "artiste"},
        ]
    }
}
```

### 8.2 Boutons de raccourci Zeus

Des boutons rapides dans l'interface Zeus pour lancer directement :

- 🏛 **Club** → navigue vers Athéna en mode Club
- 🏷 **Label** → navigue vers Athéna en mode Label
- 🎤 **Artiste** → navigue vers Athéna en mode Artiste

---

## 9. Contraintes techniques

### 9.1 Dépendances

- **aioslsk** : `PeerGetDirectoryContentCommand(username, directory)` — navigation arborescence
- **PySide6** : Interface Qt
- **sqlite3** : Cache BDD (standard library)
- **json** : Listes de mots-clés

### 9.2 Performance

- Exploration limitée à **3 niveaux** de profondeur
- **Timeout par client** : 30s max d'exploration avant de passer au suivant
- **Rate limiting** : 1 exploration toutes les 2s entre deux clients (évite de flooder le réseau)
- **Cache** : Évite de rescanner les mêmes clients à chaque cycle
- **Parallélisation** : Les explorations peuvent être lancées en parallèle (asyncio gather)

### 9.3 Gestion des erreurs

| Erreur | Comportement |
|--------|-------------|
| Client déconnecté pendant l'exploration | Ignorer, passer au suivant |
| Timeout (30s) | Logger, passer au suivant |
| `PeerGetDirectoryContentCommand` échoue | Logger, marquer comme non-joignable |
| BDD inaccessible | Logger, continuer sans cache (mode dégradé) |

### 9.4 Packages supplémentaires

Aucun — tout est en standard library ou déjà existant dans le projet :
- `sqlite3` (stdlib)
- `json` (stdlib)
- `PeerGetDirectoryContentCommand` (aioslsk déjà installé)
- `ConnexionManager.run_coro()` (existant) pour exécuter les coroutines

---

## 10. Étapes d'implémentation (feuille de route)

| # | Tâche | Statut |
|---|-------|--------|
| **Phase 0 : Validation mode Normal sur un client Arès** | | |
| 1 | 👉 Chercher l'API `SearchCommand` — vérifier si `SearchCommand(query, username=nom_client)` existe ou s'il faut filtrer les résultats côté réception | ❌ |
| 2 | 👉 Créer un script/test isolé : lancer une recherche en ciblant un username spécifique depuis Arès | ❌ |
| 3 | 👉 Vérifier qu'on reçoit bien des résultats de ce client (log : nb résultats, latence, username) | ❌ |
| 4 | 👉 Si ça marche : intégrer la sélection client + recherche normale dans Athéna V2 | ❌ |
| 5 | 👉 Créer un indicateur visuel : "Résultats de [username]" dans le tableau | ❌ |
| **Phase 1 : Infrastructure** (après validation du mode Normal) | | |
| 6 | Recherche web : clubs mythiques 1995-2005 (par pays) | ❌ |
| 7 | Recherche web : labels electro par pays | ❌ |
| 8 | Recherche web : artistes electro par pays | ❌ |
| 9 | Créer les fichiers JSON : `clubs.json`, `labels.json`, `artistes.json` | ❌ |
| 10 | Créer `mots_interdits.json` et `mots_silos.json` | ❌ |
| 11 | Créer `matching_service.py` (MatchingService) | ❌ |
| 12 | Créer `matching_db.py` (cache SQLite) | ❌ |
| 13 | Ajouter `browse_user_directory()` dans ConnexionManager | ❌ |
| **Phase 2 : Analyse exploratoire** | | |
| 14 | Mode Exploration dans Athéna (arbre de dossiers 3 niveaux) | ❌ |
| 15 | Explorer 3 clients réels, collecter les structures | ❌ |
| 16 | Ajuster les listes silos/mots-clés/mots interdits | ❌ |
| **Phase 3 : Matching** | | |
| 17 | Implémenter `verifier_silos()` dans MatchingService | ❌ |
| 18 | Implémenter l'exploration récursive (3 niveaux) | ❌ |
| 19 | Implémenter le calcul de score de matching | ❌ |
| 20 | Intégrer le cache BDD | ❌ |
| **Phase 4 : Interface Athéna V2 (complète)** | | |
| 21 | Repenser le layout d'Athéna (4 boutons de mode, Normal en premier) | ❌ |
| 22 | Listes déroulantes en cascade (Pays → Entité) pour Club/Label/Artiste | ❌ |
| 23 | Panneau de résultats (dossiers trouvés) pour les modes matching | ❌ |
| 24 | Actions sur résultat : Explorer dossier, Télécharger | ❌ |
| **Phase 5 : Intégration Zeus** | | |
| 25 | Ajouter les intentions club/label/artiste dans KNOWLEDGE | ❌ |
| 26 | Boutons de raccourci dans Zeus | ❌ |
| 27 | Action `set_mode` pour BotAccueil | ❌ |
| **Phase 6 : Consommateurs** | | |
| 28 | Intégrer MatchingService dans Wishlist | ❌ |
| 29 | Intégrer MatchingService dans Planificateur | ❌ |
| **Phase 7 : Tests & Polish** | | |
| 30 | Tests unitaires MatchingService | ❌ |
| 31 | Tests intégration cache BDD | ❌ |
| 32 | Tests UI Athéna V2 | ❌ |
| 33 | Mise à jour `.aioslsk-logbook.md` | ❌ |

---

## 11. ❓ Décisions de conception

### Interface et UX

- [x] **4 boutons en haut de la page** : Normal (🔎, 1er), Club (🏛), Label (🏷), Artiste (🎤) — le Normal affiche la barre de recherche + sélection client depuis Arès, les 3 autres affichent des listes déroulantes
- [x] **Phase 0 obligatoire** : valider le mode Normal sur client spécifique AVANT de construire le matching
- [x] **Listes en cascade** : Pays → Entité (Club/Label/Artiste). Chaque sélection filtre la suivante
- [x] **Mode Exploration intégré à Athéna** (pas un outil devtool séparé) : accessible via un bouton ⚙️
- [x] **Résultats = dossiers trouvés** : On affiche les chemins de dossiers, pas directement les fichiers
- [x] **Bouton explicite « 🚀 Lancer la chasse »** : L'utilisateur configure puis lance
- [x] **Zeus conversationnel + boutons** : Les deux coexistent

### Matching et silos

- [x] **Filtre silo obligatoire** : Si le client n'a pas de dossiers musicaux niveau 1, on l'ignore
- [x] **3 niveaux de profondeur max** : Suffisant pour trouver les dossiers ciblés
- [x] **Mots interdits par mode** : Chaque mode a ses propres exclusions
- [x] **Score de matching** : Ratio de mots-clés trouvés dans le chemin complet
- [x] **Cache SQLite** : Évite les rescans inutiles, fraîcheur de 1h

### Architecture

- [x] **PeerGetDirectoryContentCommand(username, directory)** : API aioslsk pour la navigation dossier à dossier
- [x] **MatchingService centralisé** : Consommable par tous les bots (Recherche, Wishlist, Planificateur)
- [x] **Cache BDD (matching_cache.db)** : SQLite, schéma simple avec index
- [x] **Phase 1 exploratoire obligatoire** : Analyser les vrais dossiers avant de finaliser les listes
- [x] **Timeout 30s par client** : Évite de bloquer sur un client injoignable
- [x] **Rate limiting 2s entre clients** : Respect du réseau Soulseek

---

## 12. Recherches web à effectuer

Avant de commencer l'implémentation, des recherches web sont nécessaires pour alimenter les listes JSON. Domaines :

| Domaine | Ce qu'on cherche | Nombre cible |
|---------|-----------------|--------------|
| **Clubs 1995-2005** | Clubs mythiques par pays (Belgique, France, UK, Allemagne, Pays-Bas, USA) | 10-15 clubs |
| **Labels electro** | Labels par pays (R&S, Warp, Kompakt, etc.) | 10-15 labels |
| **Artistes electro** | Artistes majeurs par pays (Jeff Mills, Laurent Garnier, etc.) | 10-15 artistes |
| **Mots-clés** | Vocabulaire associé (styles, sous-genres, années) | 30-50 mots |
| **Conventions nommage** | Comment les utilisateurs nomment leurs dossiers sur Soulseek (observation) | Observations |

---

## 13. Glossaire

| Terme | Définition |
|-------|------------|
| **Silo** | Dossier racine musical chez un client. Filtre d'entrée pour l'exploration |
| **Matching** | Comparaison d'un chemin de dossier contre une liste de mots-clés |
| **Score** | Ratio [mots-clés trouvés] / [mots-clés attendus] dans le chemin |
| **Chasse** | Session d'exploration + matching sur la liste des clients actifs |
| **Entité** | Club, label ou artiste défini dans les JSON |
| **Cache** | Base SQLite qui stocke les résultats de matching pour 1h |
| **Mots interdits** | Mots qui, si présents dans le chemin, invalident le match |

---

*Spec initiale rédigée le 2026-07-05 — issue de 4 rounds d'interview utilisateur.*
