# Spec — Mode Genre (Athéna)

> **Statut :** 📝 Proposition — à valider
> **Contexte :** Nouveau mode de recherche silo pour Athéna (BotRecherche). Totalement indépendant du mode Normal. Exploite `file_data.filename` et les chemins de dossiers des clients Arès pour dénicher des dossiers par genre musical.

---

## 1. Vision

> *"Je veux trouver les dossiers 'techno' chez les clients. Je choisis le genre 'techno', ce mode déclenche une boucle de recherche dédiée qui récupère la structure partagée d'un client, filtre les chemins qui matchent 'techno', et affiche le contenu des dossiers trouvés."*

### 1.1 Principes fondamentaux

| Principe | Valeur |
|----------|--------|
| **Silo** | Mode Genre = silo complètement séparé du mode Normal. Pas de mélange de code ou de logique |
| **Cible** | Clients de la liste **Arès** (actifs & joignables uniquement) |
| **Moteur** | `PeerGetSharesCommand` → arborescence client → filtrage par genre → `PeerGetDirectoryContentCommand` |
| **Clé** | `file_data.filename` = chemin complet = source de vérité pour l'analyse des dossiers |
| **Boucle** | Boucle de recherche dédiée, décorrélée de `_on_search()` du mode Normal |
| **Résultats** | Même tableau de résultats (`DossierTreeWidget`) que les autres modes |

### 1.2 Terminologie

| Terme | Définition |
|-------|------------|
| **Genre** | Catégorie musicale (techno, house, trance, drum & bass, etc.) |
| **Arborescence** | Structure complète des dossiers partagés d'un client (via `UserSharesReplyEvent`) |
| **Match** | Chemin de dossier qui contient le terme du genre recherché |
| **Contenu** | Fichiers présents dans un dossier matché (via `PeerGetDirectoryContentCommand`) |
| **Silo** | Mode de recherche indépendant — pas de partage de code avec les autres modes |

---

## 2. Flux de fonctionnement

```
┌─────────────────────────────────────────────────────────────────┐
│  UTILISATEUR : choisit "Techno" dans la liste des genres        │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  BOUCLE GENRE : itère sur la liste ARÈS (clients actifs)        │
│  Pour chaque client Arès :                                      │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  ÉTAPE 1 : PeerGetSharesCommand(username)                       │
│  ──────────────────────────────────────────                     │
│  → UserSharesReplyEvent.reçu avec :                             │
│    • user: User                                                 │
│    • directories: list[DirectoryData]   ← arborescence complète │
│    • locked_directories: list[DirectoryData]                    │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  ÉTAPE 2 : Filtrer les dossiers qui matchent le genre           │
│  ──────────────────────────────────────────                     │
│  Pour chaque DirectoryData dans directories :                   │
│    • Normaliser le chemin (minuscules, sans accents)            │
│    • Si "techno" dans le chemin → conserver                     │
│    • Si mot interdit dans le chemin → rejeter                   │
│                                                                  │
│  Résultat : liste de chemins matchés                            │
│  Ex: /Music/Techno/, /Techno Mix/, /Various/Techno 2024/        │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  ÉTAPE 3 : PeerGetDirectoryContentCommand(username, path)       │
│  ──────────────────────────────────────────                     │
│  Pour chaque chemin matché :                                    │
│    → UserDirectoryEvent.reçu avec le contenu du dossier         │
│    • Fichiers : nom, taille, extension                          │
│    • Sous-dossiers : nom                                        │
│                                                                  │
│  Affiche les fichiers trouvés dans le tableau                   │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  AFFICHAGE : "📁 Techno — 12 dossiers trouvés chez 8 clients"   │
│  Tableau : Client │ Dossier │ Fichiers trouvés │ DL             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. API aioslsk détaillée

### 3.1 Récupérer l'arborescence d'un client

```python
# Émet la commande pour demander les partages d'un utilisateur
# via la connexion peer-to-peer
await client.execute(PeerGetSharesCommand(username))

# Réponse reçue sous forme d'événement
@dataclass(frozen=True, slots=True)
class UserSharesReplyEvent(Event):
    user: User
    directories: list[DirectoryData]       # Dossiers partagés publics
    locked_directories: list[DirectoryData] # Dossiers verrouillés
    raw_message: PeerSharesReply.Request

# DirectoryData contient :
#   - name: str              # Nom du dossier
#   - dirs: list[str]       # Sous-dossiers
#   - files: list[FileData] # Fichiers dans ce dossier
#   - locked: bool
```

### 3.2 Récupérer le contenu d'un dossier spécifique

```python
# Demande le contenu d'un dossier précis chez un client
await client.execute(PeerGetDirectoryContentCommand(username, directory_path))

# Réponse reçue sous forme d'événement
# UserDirectoryEvent contient :
#   - user: User
#   - directory: str         # Chemin du dossier
#   - content: list[...]    # Fichiers et sous-dossiers
```

### 3.3 Recherche ciblée (mode Normal uniquement — pour mémoire)

```python
# Utilisé uniquement par le mode Normal (pas par le mode Genre)
await client.searches.search_user(username, query)
# → SearchResultEvent
```

---

## 4. Interface

### 4.1 Position dans Athéna

Le mode Genre est le **5e bouton** dans la barre des modes :

```
[🔎 Normal] [🏛 Club] [🏷 Label] [🎤 Artiste] [🎵 Genre]    ← Nouveau !
```

### 4.2 Layout du mode Genre

```
┌──────────────────────────────────────────────────────────────┐
│  🎵 Mode Genre                                               │
│                                                               │
│  Genre : [▼ Techno          ]   ← liste déroulante des genres │
│                                                               │
│  Options :                                                    │
│  ☑ Filtrer par extension audio (mp3, flac, ogg)               │
│  ☑ Limiter aux clients avec slot libre                        │
│  ☐ Exploration récursive (sous-dossiers)                      │
│                                                               │
│  [🚀 Lancer] [⏹ Stop]                                        │
│                                                               │
│  ──────────────────────────────────────────────────────       │
│                                                               │
│  📊 Résultats : 45 fichiers trouvés dans 12 dossiers          │
│  chez 8 clients                                               │
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Client       │ Dossier                     │ Fichiers │DL│ │
│  │──────────────┼─────────────────────────────┼──────────┼──│ │
│  │ DJ_Techno    │ /Music/Techno/              │ 24       │⬇ │ │
│  │ ElectroFan42 │ /Audio/Techno Mix/          │ 8        │⬇ │ │
│  │ BelgianBeats │ /Techno/Belgium/            │ 15       │⬇ │ │
│  │ ...          │ ...                         │ ...      │..│ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                               │
│  [📥 Tout télécharger] [📋 Copier les chemins]                │
└──────────────────────────────────────────────────────────────┘
```

### 4.3 Console de suivi (StatusConsole réutilisée)

Pendant l'exécution, la console affiche le déroulé :

```
[11:19:38] 🎵 Mode Genre — Recherche de « Techno »
[11:19:38] 👥 872 clients dans Arès
[11:19:38] 🔄 Étape 1/3 : Récupération des arborescences…
[11:19:39] 📁 DJ_Techno → 45 dossiers, 3 matchés
[11:19:40] 📁 ElectroFan42 → 12 dossiers, 1 matché
[11:19:41] 📁 BelgianBeats → 30 dossiers, 5 matchés
[11:19:42] ✅ 12 dossiers matchés chez 8 clients
[11:19:42] 🔄 Étape 2/3 : Récupération du contenu…
[11:19:43] 📄 DJ_Techno/Music/Techno → 24 fichiers
[11:19:44] 📄 ElectroFan42/Audio/Techno Mix → 8 fichiers
[11:19:45] ✅ Contenu récupéré pour 12/12 dossiers
[11:19:45] 📊 45 fichiers trouvés dans 12 dossiers chez 8 clients
```

---

## 5. Architecture du code

### 5.1 Nouveaux fichiers

| Fichier | Rôle |
|---------|------|
| `src/gui/widgets/bots/bot_recherche_mode_genre.py` | Classe `ModeGenre(QFrame)` — widget du mode Genre |
| `src/services/genre_service.py` | `GenreService` — logique de récupération/filtrage des arborescences |
| `data/genres.json` | Liste des genres musicaux disponibles |

### 5.2 Fichiers modifiés

| Fichier | Changement |
|---------|-----------|
| `src/gui/widgets/bots/bot_recherche.py` | 5e mode dans les boutons de mode, instanciation de `ModeGenre` |
| `src/gui/widgets/bots/bot_recherche_modes.py` | Nouveau mode dans `ModesPanel` |
| `src/services/connexion_manager.py` | Ajout de `browse_user_shares()` et `browse_user_directory()` |
| `src/services/soulseek_client.py` | Enregistrement des événements `UserSharesReplyEvent` et `UserDirectoryEvent` |

### 5.3 Structure proposée

```python
# ── ModeGenre (widget) ───────────────────────────────────────
class ModeGenre(QFrame):
    """Widget du mode Genre dans Athéna.
    
    Silo complet : pas de partage de logique avec le mode Normal.
    Utilise GenreService pour la récupération asynchrone.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._service: GenreService | None = None
        self._en_cours = False
        self._resultats: list[GenreResultat] = []
        self._build_ui()

    def set_service(self, service: GenreService) -> None:
        self._service = service
        self._service.resultat_recu.connect(self._on_resultat)
        self._service.termine.connect(self._on_termine)

    def lancer_recherche(self, genre: str) -> None:
        """Lance la boucle de recherche Genre sur Arès."""
        ...

    # ── Signaux ─────────────────────────────────────────────
    resultats_a_afficher = Signal(list)  # [GenreResultat, ...]


# ── GenreService (logique métier) ────────────────────────────
class GenreService(QObject):
    """Service asynchrone pour le mode Genre.
    
    Boucle dédiée : itère sur Arès, récupère les arborescences,
    filtre par genre, récupère le contenu des dossiers matchés.
    """

    arborescence_recue = Signal(str, list)  # username, [DirectoryData]
    dossier_match = Signal(str, str)        # username, chemin
    contenu_recu = Signal(str, str, list)   # username, chemin, fichiers
    resultat_recu = Signal(object)          # GenreResultat
    termine = Signal()

    async def execute(self, genre: str, clients: list[dict]) -> None:
        """Point d'entrée principal.
        
        1. Pour chaque client Arès → PeerGetSharesCommand
        2. Filtre les dossiers qui matchent le genre
        3. Pour chaque dossier matché → PeerGetDirectoryContentCommand
        4. Agrège les résultats
        """
        for client in clients:
            # Étape 1 : Récupérer l'arborescence
            shares = await self._request_shares(client["username"])
            if not shares:
                continue
            
            # Étape 2 : Filtrer par genre
            dossiers_match = self._filtrer_par_genre(shares, genre)
            if not dossiers_match:
                continue
            
            # Étape 3 : Récupérer le contenu
            for chemin in dossiers_match:
                contenu = await self._request_directory(
                    client["username"], chemin
                )
                if contenu:
                    resultat = GenreResultat(
                        username=client["username"],
                        chemin=chemin,
                        fichiers=contenu,
                    )
                    self.resultat_recu.emit(resultat)

        self.termine.emit()

    def _filtrer_par_genre(
        self, directories: list[DirectoryData], genre: str
    ) -> list[str]:
        """Filtre les dossiers qui contiennent le terme du genre.
        
        Normalise les chemins (minuscules, sans accents).
        Vérifie la présence du genre dans le nom du dossier.
        Exclut les chemins avec mots interdits.
        """
        ...


# ── GenreResultat (dataclass) ────────────────────────────────
@dataclass
class GenreResultat:
    username: str
    chemin: str
    fichiers: list[dict]  # nom, taille, extension
    nb_fichiers_audio: int = 0
    statut_client: str = ""
```

---

## 6. Liste des genres

### 6.1 Fichier `data/genres.json`

```json
{
  "version": "1.0",
  "genres": [
    {
      "id": "techno",
      "name": "Techno",
      "keywords": ["techno", "detroit", "berlin", "minimal"],
      "exclude": ["rock", "pop", "jazz", "video", "photo"]
    },
    {
      "id": "house",
      "name": "House",
      "keywords": ["house", "deep house", "tech house", "garage"],
      "exclude": ["rock", "pop", "jazz", "video"]
    },
    {
      "id": "trance",
      "name": "Trance",
      "keywords": ["trance", "progressive", "goa", "psytrance"],
      "exclude": ["rock", "pop", "video"]
    },
    {
      "id": "dnb",
      "name": "Drum & Bass",
      "keywords": ["drum and bass", "dnb", "drum&bass", "jungle", "liquid"],
      "exclude": ["rock", "pop", "jazz", "video"]
    },
    {
      "id": "electro",
      "name": "Electro",
      "keywords": ["electro", "electronic", "electronica"],
      "exclude": ["rock", "pop", "video"]
    },
    {
      "id": "ambient",
      "name": "Ambient / Downtempo",
      "keywords": ["ambient", "downtempo", "chill", "atmospheric"],
      "exclude": ["rock", "pop", "video", "metal"]
    },
    {
      "id": "hardcore",
      "name": "Hardcore / Gabber",
      "keywords": ["hardcore", "gabber", "hardstyle", "hardtechno"],
      "exclude": ["rock", "pop", "jazz", "video"]
    },
    {
      "id": "breakbeat",
      "name": "Breaks / Breakbeat",
      "keywords": ["breakbeat", "breaks", "big beat", "break"],
      "exclude": ["rock", "pop", "jazz", "video"]
    }
  ]
}
```

---

## 7. Contraintes techniques

### 7.1 Performance

- **Timeout par client** : 15s max pour récupérer l'arborescence (`UserSharesReplyEvent`)
- **Timeout par dossier** : 10s max pour récupérer le contenu (`UserDirectoryEvent`)
- **Rate limiting** : 500ms entre deux requêtes (évite de flooder)
- **Parallélisation** : Les clients sont traités séquentiellement (un par un) pour ne pas surcharger le réseau
- **Cache** : Les arborescences sont mises en cache en mémoire le temps de la boucle (pas de cache persistant dans cette première version)

### 7.2 Gestion des erreurs

| Erreur | Comportement |
|--------|-------------|
| Client déconnecté pendant la requête | Ignorer, passer au suivant (log) |
| Timeout arborescence (15s) | Logger + continuer |
| Timeout contenu dossier (10s) | Logger + passer au dossier suivant |
| `PeerGetSharesCommand` échoue | Logger, marquer client comme non-joignable |
| Aucun dossier matché | Message "Aucun dossier trouvé pour ce genre" |

### 7.3 Sécurité réseau

- **Respect du réseau Soulseek** : 500ms minimum entre chaque requête
- **Pas de spam** : On ne browse que les clients Arès (actifs & joignables)
- **Stop utilisateur** : Le bouton ⏹ Stop interrompt immédiatement la boucle

---

## 8. Dépendances

- **aioslsk** : `PeerGetSharesCommand`, `PeerGetDirectoryContentCommand` (déjà installé)
- **PySide6** : Interface Qt (déjà utilisé)
- **json** : Liste des genres (stdlib)
- **Pas de nouvelles dépendances**

---

## 9. Étapes d'implémentation

| # | Tâche | Statut |
|---|-------|--------|
| 1 | ✅ **Recherche API aioslsk** — `UserSharesReplyEvent`, `PeerGetSharesCommand`, `UserDirectoryEvent` | ✅ Fait |
| 2 | Ajouter `browse_user_shares()` et `browse_user_directory()` dans ConnexionManager | ❌ |
| 3 | Enregistrer les événements `UserSharesReplyEvent` et `UserDirectoryEvent` dans SoulseekService | ❌ |
| 4 | Créer `src/services/genre_service.py` — `GenreService` avec la boucle complète | ❌ |
| 5 | Créer `data/genres.json` — liste initiale des genres | ❌ |
| 6 | Créer `src/gui/widgets/bots/bot_recherche_mode_genre.py` — widget ModeGenre | ❌ |
| 7 | Intégrer le 5e bouton dans Athéna (bot_recherche.py + bot_recherche_modes.py) | ❌ |
| 8 | Câbler les signaux : ModeGenre ↔ GenreService ↔ ConnexionManager | ❌ |
| 9 | Ajouter les logs de suivi dans la console Athéna | ❌ |
| 10 | Tests manuels : lancer une recherche genre sur un client réel | ❌ |

---

## 10. Questions en suspens

- [ ] **Comment envoyer `PeerGetSharesCommand` exactement ?** (via `client.execute()` ou via `client.peer.send()` ou via la couche réseau ?)
- [ ] **`PeerGetDirectoryContentCommand`** : quel est le format exact du chemin ? (relatif ? absolu ? avec ou sans `/` en préfixe ?)
- [ ] **Structure de `DirectoryData`** : contient-il déjà les sous-dossiers et fichiers, ou faut-il rappeler `PeerGetDirectoryContentCommand` pour chaque niveau ?
- [ ] **Timeout par défaut** des requêtes peer chez aioslsk (est-ce configurable ?)
- [ ] **UserDirectoryEvent** : est-ce le nom exact de l'événement ? (le code mentionne un `UserDirectoryEvent` mais je n'ai pas vérifié son import)

---

*Spec proposée le 2026-07-05 — issue de l'analyse API aioslsk + interviews utilisateur.*
