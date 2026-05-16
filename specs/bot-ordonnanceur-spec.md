# Spécification — Bot Ordonnanceur

> **Statut :** ✅ Service backend + CLI terminés — 🏗️ UI Qt en cours
> **Dernière mise à jour :** 2026-06-22
> **Contexte :** Projet autonome d'organisation de fichiers audio.
>   L'Ordonnanceur a remplacé l'ancien projet "Armée des 12 Bots Soulseek".
> **Renommage :** `"Nettoyage"` → `"Ordonnanceur"` — voir §2.

---

## 🎯 Objectif

Le **Bot Ordonnanceur** est un assistant qui gère le dossier `downloads` et l'ensemble du système de fichiers de l'application. Il organise, classe, renomme, dédoublonne et nettoie les fichiers téléchargés, automatiquement ou à la demande.

Contrairement au simple nettoyage temporaire du Planificateur, l'Ordonnanceur fait de la **gestion complète** : tri par artiste/album, renommage intelligent, dédoublonnage par hash, nettoyage des fichiers temporaires, et organisation complète du disque.

---

## 1. Nom et navigation

### 1.1 Renommage

L'actuel bouton "Nettoyage" dans le footer et sa page placeholder dans le `CenterZone` sont renommés en "Ordonnanceur".

### 1.2 Changements concrets

| Fichier | Ligne | Changement |
|---------|-------|------------|
| `src/gui/layout/footer.py` | `_BOT_NAMES` (≈L.75) | `"Nettoyage"` → `"Ordonnanceur"` |
| `src/gui/layout/center.py` | boucle `_build_menu_page` dans `__init__` (≈L.98-106) | **Retirer** `"Nettoyage"` de la boucle (remplace par le builder dédié) |
| `src/gui/layout/center.py` | clé `_pages["Nettoyage"]` venant de `_build_menu_page` | Remplacé par `_pages["Ordonnanceur"]` dans le builder dédié |
| `src/gui/layout/center.py` | fichier `__init__` | Ajouter `self._build_ordonnanceur_page()` après la boucle des placeholders |
| `src/gui/widgets/bots/__init__.py` | Exports | Ajouter `BotOrdonnanceur` |
| `specs/bot-ordonnanceur-spec.md` | (ce fichier) | Nouveau — remplace l'ancienne spec "Nettoyage" si elle existait |

### 1.3 Création du bot

- Un vrai builder `_build_ordonnanceur_page()` remplace la page placeholder générée par `_build_menu_page("Ordonnanceur")`
- Le builder crée une instance de `BotOrdonnanceur` connectée au `CenterZone` et aux services
- Signal `page_changed = Signal(str)` comme les autres bots

### 1.4 Impact navigation

- Footer : `_BOT_NAMES[8]` passe de `"Nettoyage"` à `"Ordonnanceur"`
- Centre : `_build_menu_page("Nettoyage")` (dans la boucle des placeholders) renommé et remplacé par un vrai builder plus tard
- Bot Accueil : les références à `"nettoyage"` dans les suggestions et la navigation doivent être mises à jour (`bot_accueil.py` L.610, L.643)

---

## 2. Concept général

L'Ordonnanceur est un **assistant pas à pas** qui guide l'utilisateur à travers les opérations de gestion des fichiers :

```
┌─────────────────────────────────────────────────────────────┐
│  🧹 Ordonnanceur — Assistant d'organisation                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Étape 1/4 : Choisir les opérations                         │
│                                                             │
│  ☑ Classer par artiste/album   (2 340 fichiers concernés)   │
│  ☑ Renommer intelligemment     (2 340 fichiers concernés)   │
│  ☐ Dédoublonner                (estimation: ~120 doublons)  │
│  ☑ Nettoyer fichiers temp      (estimé: 45 fichiers)        │
│                                                             │
│  [🔍 Analyser]                     Dossier: C:/.../downloads│
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Étape 2/4 : Aperçu des modifications                       │
│  Étape 3/4 : Exécution + progression en direct              │
│  Étape 4/4 : Rapport final                                  │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 Mode de fonctionnement

| Mode | Déclencheur | Preview | Comportement |
|------|-------------|---------|--------------|
| **Manuel** | Clic sur bouton dans le bot | ✅ Aperçu avant exécution | Assistant pas à pas complet |
| **Auto (démarrage)** | Au lancement de l'app | ❌ Skip | Exécute les opérations configurées en arrière-plan, notification si des actions ont été faites |
| **Planifié** | Via le Planificateur (action individuelle par opération) | ❌ Skip | Exécute l'opération planifiée, log + rapport dans le Planificateur |

### 2.2 Double emploi avec le Planificateur

Le Planificateur a déjà une action `"nettoyage"` qui supprime les fichiers sous `data/tmp/` et les doublons détectés dans la bibliothèque. **Les deux coexistent** :

- Le Planificateur garde son nettoyage interne basique (fichiers temp + doublons rapides)
- L'Ordonnanceur fait de l'organisation **avancée** (classement, renommage par tags, dédoublonnage par hash, structure configurable)
- À terme, les actions basiques du Planificateur pourraient être remplacées par des appels à l'Ordonnanceur

---

## 3. Périmètre fonctionnel

### 3.1 Opérations disponibles

| # | Opération | Icône | Description | Détection |
|---|-----------|-------|-------------|-----------|
| 1 | **Classement artiste/album** | 📂 | Déplace les fichiers dans une arborescence configurable | Pattern + tags ID3 + dossier parent |
| 2 | **Renommage intelligent** | ✏️ | Normalise les noms de fichiers selon un template | Tags ID3 (fallback: pattern filename) |
| 3 | **Dédoublonnage** | 🗑️ | Détecte et supprime les fichiers en double | D'abord nom+taille (rapide), puis hash SHA256 (sûr) |
| 4 | **Nettoyage temp** | 🧹 | Supprime fichiers .part, logs, caches dans data/tmp/ | Extension + âge + dossier |

### 3.2 Dossier source

- Par défaut : le dossier de téléchargement configuré (`telechargement.dossier_destination`)
- Configurable : l'utilisateur peut choisir un autre dossier à analyser/organiser

### 3.3 Dossier destination

- **Configurable** par l'utilisateur
- Possibilités :
  - Dans le même dossier `downloads` (renommer sur place, classer en sous-dossiers)
  - Dossier séparé (ex: `downloads/Organisé/`, `Musique/`)
  - Structure personnalisée

---

## 4. Assistant pas à pas (UI)

### 4.1 Étape 1 : Choix des opérations

```
┌─────────────────────────────────────────────────────────────┐
│  🧹 Ordonnanceur                                            │
├─────────────────────────────────────────────────────────────┤
│  Dossier source : [C:/Users/.../Soulseek Downloads] [📂]    │
│  Dossier destination : [Même dossier + sous-dossiers]  [📂] │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ ☑ 📂 Classer par artiste/album                       │ │
│  │    Structure : [Artiste/Album/Titre............] [✏️]  │ │
│  │ ☑ ✏️ Renommer intelligemment                          │ │
│  │    Pattern : [{artist} - {album} - {track} {title}] [✏️]│ │
│  │ ☐ 🗑️ Dédoublonner                                     │ │
│  │    Méthode : [Nom+Taille → hash SHA256.........]       │ │
│  │ ☑ 🧹 Nettoyer fichiers temporaires                    │ │
│  │    Âge max : [7 jours.........................]         │ │
│  │ ☐ 🚀 Tout faire (mode turbo)                          │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Fichiers trouvés : 2 340 dans 156 dossiers                 │
│  [🔍 Analyser]                    [← Retour]  [→ Suivant]  │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Étape 2 : Aperçu des modifications

```
┌─────────────────────────────────────────────────────────────┐
│  🧹 Ordonnanceur — Aperçu (1 842 fichiers concernés)       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📂 Classement : 1 520 fichiers à déplacer                  │
│    ├─ ArtisteA/Album1/ (12 fichiers)                        │
│    ├─ ArtisteA/Album2/ (8 fichiers)                         │
│    └─ ... (45 artistes, 120 albums)                         │
│                                                             │
│  ✏️ Renommage : 890 fichiers à renommer                     │
│    ├─ 02 Track.mp3 → ArtisteA - Album1 - 02 Track.mp3      │
│    ├─ chanson_finale.mp3 → ArtisteB - BestOf - 07 Song.mp3 │
│    └─ ... (50 exemples)                                     │
│                                                             │
│  🗑️ Dédoublonnage : 45 doublons trouvés (1.2 Go libérables)│
│    ├─ song.mp3 (12.3 Mo) [×2] → supprimer 1 copie          │
│    └─ ... (45 fichiers)                                     │
│                                                             │
│  🧹 Temp : 32 fichiers à supprimer (340 Mo)                 │
│                                                             │
│  ⚠️ Conflits : 3 fichiers seront renommés (suffixe _2)     │
│                                                             │
│  [← Modifier]                           [✅ Exécuter →]     │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Étape 3 : Exécution avec progression

```
┌─────────────────────────────────────────────────────────────┐
│  🧹 Ordonnanceur — Exécution en cours...                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📂 Classement        ████████░░░░░░░░  45% (680/1520)     │
│                       ⚡ 12 fichiers/s — ETA: 1m 10s        │
│                                                             │
│  ✏️ Renommage         ██████░░░░░░░░░░░  30% (267/890)     │
│                       ⚡ 8 fichiers/s — ETA: 1m 18s         │
│                                                             │
│  🧹 Temp             ✅ Terminé (32 fichiers supprimés)     │
│                                                             │
│  🗑️ Dédoublonnage    ⏳ En attente...                      │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ [14:32:15] 📂 ArtisteA/Album1/ → déplacé (12 fichiers)│ │
│  │ [14:32:16] ✏️ song.mp3 → ArtisteA - Album1 - 01 ...  │ │
│  │ [14:32:16] ❌ Impossible de lire les tags de old.mp3  │ │
│  │ [14:32:17] 🧹 Supprimé: data/tmp/cache_old.bin       │ │
│  │ ...                                                  │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  [⏸️ Pause]  [✕ Annuler]                                   │
└─────────────────────────────────────────────────────────────┘
```

### 4.4 Étape 4 : Rapport final

```
┌─────────────────────────────────────────────────────────────┐
│  🧹 Ordonnanceur — ✅ Terminé (3m 42s)                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 Résumé :                                                │
│  ┌─────────────────────────────────────────┬────────────┐  │
│  │ Opération                     │ Statut  │ Détail     │  │
│  ├─────────────────────────────────────────┼────────────┤  │
│  │ 📂 Classement artiste/album   │ ✅      │ 1 520/1520 │  │
│  │ ✏️ Renommage                 │ ✅      │ 890/890    │  │
│  │ 🗑️ Dédoublonnage (45 × 1.2G)│ ✅      │ 45/45      │  │
│  │ 🧹 Nettoyage temp            │ ✅      │ 32/32      │  │
│  └─────────────────────────────────────────┴────────────┘  │
│                                                             │
│  ⚠️ 3 conflits résolus (suffixe _2)                        │
│  ⚠️ 12 fichiers illisibles (tags corrompus) → ignorés      │
│                                                             │
│  💾 Espace libéré : 1.54 Go                                 │
│  📁 Fichiers organisés dans : downloads/Organisé/           │
│                                                             │
│  [📋 Copier le rapport]        [📂 Ouvrir le dossier]       │
│  [← Retour à l'accueil]        [⟳ Relancer]                │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Extraction des métadonnées

### 5.1 Ordre de résolution

Pour déterminer l'artiste, l'album et le titre d'un fichier, l'Ordonnanceur utilise cette cascade :

1. **Pattern filename** (le plus rapide)
   - `Artiste - Album - 01 Titre.mp3` → artiste="Artiste", album="Album", titre="Titre", piste=1
   - `Artiste - Titre.mp3` → artiste="Artiste", titre="Titre"
   - `01 Titre.mp3` → titre="Titre", piste=1
   - Regex configurable

2. **Tags ID3 / Vorbis** (fallback si pattern échoue)
   - MP3 → ID3v2 (artiste, album, titre, piste)
   - FLAC → Vorbis comments
   - WAV, OGG, etc. → selon format
   - Utiliser `mutagen` ou `tinytag` (bibliothèque légère Python)

3. **Dossier parent** (fallback ultime)
   - Si le fichier est dans `downloads/Artiste/Album/track.mp3` → utiliser le dossier comme artiste/album
   - Si le fichier est directement dans `downloads/` → pas d'artiste/album connu

### 5.2 Bibliothèque

```python
# À ajouter dans requirements.txt
mutagen>=1.47.0  # Lecture des tags audio (ID3, Vorbis, APE, etc.)
```

Alternative plus légère : `tinytag` (pas de dépendances, lecture seule).

### 5.3 Structure regex par défaut

```python
# Patterns de reconnaissance de nom de fichier
_FILENAME_PATTERNS: list[re.Pattern] = [
    # "Artiste - Album - 01 Titre.ext"
    re.compile(r'^(.+?)\s*-\s*(.+?)\s*-\s*(\d{1,3})\s*(.+?)\.\w+$'),
    # "Artiste - Titre.ext"
    re.compile(r'^(.+?)\s*-\s*(.+?)\.\w+$'),
    # "01 Titre.ext"
    re.compile(r'^(\d{1,3})\s*(.+?)\.\w+$'),
    # "Artiste - 01 Titre.ext" (pas d'album)
    re.compile(r'^(.+?)\s*-\s*(\d{1,3})\s*(.+?)\.\w+$'),
]
```

---

## 6. Dédoublonnage

### 6.1 Méthode de détection

Deux passes :

1. **Passe rapide** (nom + taille)
   - Regrouper les fichiers par `(nom_fichier.lower(), taille_bytes)`
   - Signature : `tuple[str, int]`
   - O(n) en mémoire

2. **Passe sûre** (hash SHA256)
   - Pour chaque groupe de la passe 1 avec >1 fichier
   - Calculer SHA256 des 64 premiers Ko + du fichier complet si ambigu
   - Signature : `str` (hex digest)

```python
def compute_hash(path: str, fast: bool = True) -> str:
    """Calcule SHA256. fast=True = seulement les 64 premiers Ko."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        if fast:
            hasher.update(f.read(65536))  # 64 Ko
        else:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
    return hasher.hexdigest()
```

### 6.2 Règle de conservation

Quand des doublons sont trouvés, conserver :

1. Le fichier avec le meilleur taux de bitrate (qualité audio)
2. En cas d'égalité : le fichier avec le nom le plus long / le plus descriptif
3. En cas d'égalité : le fichier le plus récent
4 Sinon : le premier trouvé

### 6.3 Exclusion

- Ne pas toucher aux fichiers dans les dossiers partagés configurés (sauf si explicitement demandé)
- Ne pas dédupliquer les fichiers dans la corbeille
- Ignorer les fichiers de moins de 100 Ko (risque de faux positif élevé)

---

## 7. Renommage intelligent

### 7.1 Template par défaut

```
{artist} - {album} - {track:02d} {title}.{ext}
```

Résultat : `Nirvana - Nevermind - 01 Smells Like Teen Spirit.mp3`

### 7.2 Variables disponibles

| Variable | Description | Fallback si absente |
|----------|-------------|---------------------|
| `{artist}` | Nom de l'artiste | `Inconnu` |
| `{album}` | Nom de l'album | `Inconnu` |
| `{title}` | Titre du morceau | Nom du fichier sans extension |
| `{track}` | Numéro de piste | Chaîne vide |
| `{track:02d}` | Piste sur 2 chiffres | `00` si pas de piste |
| `{year}` | Année | Chaîne vide |
| `{ext}` | Extension du fichier | — (toujours présente) |

### 7.3 Template customisable

- Champ de texte libre dans l'étape 1 avec aperçu en direct
- Quelques presets accessibles :
  - `{artist} - {title}.{ext}` (artiste - titre)
  - `{artist} - {album} - {track:02d} {title}.{ext}` (complet)
  - `{track:02d} - {title}.{ext}` (juste numéro + titre)
  - `{artist}/{album}/{track:02d} - {title}.{ext}` (avec sous-dossiers)

---

## 8. Classement artiste/album

### 8.1 Structure cible

**Configurable** par l'utilisateur via un template de dossier (similaire au renommage) :

```
{artist}/{album}/{track:02d} {title}.{ext}
```

Résultat : `downloads/Organisé/Nirvana/Nevermind/01 Smells Like Teen Spirit.mp3`

### 8.2 Presets de structure

| Nom | Template | Résultat |
|-----|----------|----------|
| Artiste/Album | `{artist}/{album}/{track:02d} {title}.{ext}` | Nirvana/Nevermind/... |
| Genre/Artiste/Album | `{genre}/{artist}/{album}/{track:02d} {title}.{ext}` | Rock/Nirvana/Nevermind/... |
| Artiste seulement | `{artist}/{track:02d} {title}.{ext}` | Nirvana/01 ... |
| Aucun classement | (renommage sur place) | downloads/01 ... |

### 8.3 Dossier racine de sortie

Configurable :
- `Même dossier` → les fichiers sont organisés dans le dossier source
- `Dossier dédié` → exemple : `downloads/Organisé/`
- `Personnalisé` → chemin libre

---

## 9. Nettoyage temporaire

### 9.1 Cibles

| Type | Extension/Critère | Dossier |
|------|-------------------|---------|
| Fichiers partiels | `*.part` | Dossier downloads + temp |
| Caches | `*.cache`, `*.tmp` | `data/tmp/` |
| Logs anciens | `*.log` (âge > 7 jours) | `data/tmp/` |
| Fichiers orphelins | Fichiers sans correspondance dans les téléchargements actifs | Dossier downloads |

### 9.2 Filtre d'âge

- Par défaut : fichiers de plus de 7 jours
- Configurable dans l'étape 1 (jours, heures)

### 9.3 Corbeille

- Les fichiers supprimés passent d'abord par la corbeille système (optionnelle)
- Ou une corbeille interne : `data/corbeille/` (avec date de vidage automatique)

---

## 10. Intégration avec les services existants

### 10.1 Connexion aux chemins

```python
# Récupération du dossier de téléchargement configuré
from src.services.app_config import app_config

download_dir = app_config.get("telechargement.dossier_destination", "")
tmp_dir = "data/tmp/"
```

### 10.2 Intégration Planificateur

L'Ordonnanceur expose des actions individuelles que le Planificateur peut invoquer :

| Action | Paramètres | Description |
|--------|-----------|-------------|
| `ordonnanceur.classer` | `{dossier, structure}` | Classement artiste/album |
| `ordonnanceur.renommer` | `{dossier, template}` | Renommage intelligent |
| `ordonnanceur.dedupliquer` | `{dossier}` | Dédoublonnage |
| `ordonnanceur.nettoyer_temp` | `{age_max_jours}` | Nettoyage fichiers temp |

Ces actions sont exécutées **sans preview** (mode automatique) et renvoient un rapport au Planificateur.

### 10.3 Intégration Bot Accueil

Le Bot Accueil référence l'Ordonnanceur dans :
- Ses suggestions de navigation : `"Ordonnanceur"` au lieu de `"Nettoyage"`
- Sa réponse aux messages type "range", "organise", "nettoie", "classe"

### 10.4 Badge de notification

Si des opérations automatiques (démarrage, planifié) ont été exécutées et ont fait des changements, l'Ordonnanceur peut afficher un badge sur son bouton footer via `unseen_count_changed`.

---

## 11. Architecture technique

### 11.1 Classe BotOrdonnanceur

```python
class BotOrdonnanceur(QFrame):
    """Assistant pas à pas pour l'organisation des fichiers téléchargés."""

    page_changed = Signal(str)
    unseen_count_changed = Signal(int)  # badge footer

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._step = 0
        self._analysis: dict[str, Any] = {}   # résultats de l'analyse
        self._operations: dict[str, bool] = {} # opérations cochées
        self._build_ui()

    # ── UI ──
    def _build_ui(self) -> None: ...
    def _show_step(self, step: int) -> None: ...

    # ── Étape 1 : Configuration ──
    def _on_analyze(self) -> None: ...

    # ── Étape 2 : Aperçu ──
    def _build_preview(self) -> None: ...

    # ── Étape 3 : Exécution ──
    async def _execute(self) -> None: ...  # ou threading

    # ── Étape 4 : Rapport ──
    def _show_report(self, results: dict) -> None: ...

    # ── Opérations ──
    def _classer(self, source: str, dest: str, structure: str) -> Report: ...
    def _renommer(self, dossier: str, template: str) -> Report: ...
    def _deduplicate(self, dossier: str) -> Report: ...
    def _clean_temp(self, age_max_jours: int = 7) -> Report: ...
```

### 11.2 Fichiers

| Fichier | Statut | Contenu |
|---------|--------|---------|
| `src/services/ordonnanceur_service.py` | **✅ 1 652 lignes** | Service backend complet (analyse, classement, renommage, dédoublonnage, nettoyage, exécution) |
| `src/cli_ordonnanceur.py` | **✅ 432 lignes** | CLI avec preview console + `--executer` |
| `src/gui/widgets/bots/bot_ordonnanceur.py` | **🏗️ 553 lignes** | Classe `BotOrdonnanceur(QFrame)` — UI 4 étapes (service non branché) |
| `tests/test_ordonnanceur_service.py` | **✅ 128 tests** | Tests unitaires du service |
| `tests/test_cli_ordonnanceur.py` | **✅ 16 tests** | Tests du CLI |
| `specs/bot-ordonnanceur-spec.md` | ✅ | (ce fichier) |

### 11.3 Fichiers à modifier

| Fichier | Modification |
|---------|-------------|
| `src/gui/layout/footer.py` | `_BOT_NAMES` : `"Nettoyage"` → `"Ordonnanceur"` |
| `src/gui/layout/center.py` | Renommer `_build_menu_page("Nettoyage")` → `"Ordonnanceur"` |
| `src/gui/layout/center.py` | Créer `_build_ordonnanceur_page()` — remplace le placeholder |
| `src/gui/layout/center.py` | Ajouter l'appel `self._build_ordonnanceur_page()` dans `__init__` |
| `src/gui/widgets/bots/bot_accueil.py` | Mettre à jour les références "Nettoyage" → "Ordonnanceur" (L.610, L.643) |
| `src/gui/widgets/bots/bot_accueil_knowledge.py` | Mettre à jour les références "Nettoyage" → "Ordonnanceur" (L.191, L.299) |
| `src/gui/widgets/bots/__init__.py` | Ajouter `BotOrdonnanceur` dans les exports |
| `VISION.md` | Mettre à jour la table des bots (#9) |
| `data/description.json` | Mettre à jour la référence "Nettoyage" (L.25) → "Ordonnanceur" |
| `requirements.txt` | (déjà présent via `aioslsk`) `mutagen` est déjà disponible |

### 11.4 Dépendances techniques

- `mutagen` (déjà installé via `aioslsk`) — lecture tags audio (ID3, Vorbis, etc.)
- `hashlib` (standard library) — hash SHA256
- `threading` ou `QThread` / `asyncio` — exécution asynchrone des opérations
- `QFileSystemWatcher` — optionnel (surveillance du dossier downloads)
- `app_config` — lecture des chemins configurés
- `os`, `shutil`, `pathlib` — manipulation de fichiers

### 11.5 Contraintes non-fonctionnelles

- **Sécurité** : ne jamais supprimer un fichier sans confirmation (mode manuel) ou log (mode auto)
- **Corbeille** : option de mise à la corbeille avant suppression définitive
- **Prévisibilité** : l'aperçu doit montrer exactement ce qui sera fait (pas de surprise)
- **Performance** : l'analyse doit scanner 10 000 fichiers en < 5 secondes (fast path)
- **Résilience** : chaque opération est indépendante — si le renommage échoue sur un fichier, les autres continuent
- **Annulable** : l'utilisateur peut annuler l'exécution à tout moment (les fichiers déjà traités restent traités)

---

## 12. États et edge cases

| État | Comportement |
|------|-------------|
| **Dossier source inexistant** | Message d'erreur + retour étape 1, bouton pour choisir un autre dossier |
| **Aucun fichier à traiter** | Message "Tout est déjà en ordre !" + bouton "Vérifier un autre dossier" |
| **Fichiers en cours de téléchargement** | Ignorer les fichiers .part ou verrouillés, les signaler dans le rapport |
| **Permissions insuffisantes** | Log + skip individuel (pas d'arrêt complet) |
| **Tags corrompus/illisibles** | Log "Impossible de lire les tags de X" + fallback sur le nom de fichier |
| **Conflit de nom** | Ajout de suffixe `_2`, `_3`... — log dans le rapport |
| **Chemin trop long (Windows MAX_PATH)** | Warning + ignoré (ou essayer `\\?\` prefix) |
| **Annulation par l'utilisateur** | Arrêt de l'opération en cours, les fichiers déjà traités restent traités |
| **Exécution planifiée sans preview** | Skip étape 2, exécution silencieuse, rapport disponible dans le Planificateur |
| **Auto au démarrage sans changement** | Pas de notification, pas de badge |
| **Auto au démarrage avec changements** | Badge footer + notification toast |

---

## 13. Ordre d'implémentation — État réel

| # | Étape | Statut | Notes |
|---|-------|--------|-------|
| 1 | Renommage UI : `"Nettoyage"` → `"Ordonnanceur"` | ✅ | Footer, center, bot_accueil mis à jour |
| 2 | **Service d'ordonnancement** : `ordonnanceur_service.py` | **✅ 1 652 lignes** | 4 opérations + analyse + exécution |
| 3 | **CLI** : `cli_ordonnanceur.py` | **✅ 432 lignes** | Preview + `--executer` |
| 4 | **Tests backend** | **✅ 128 tests** | Service + CLI |
| 5 | **BotOrdonnanceur UI** : UI 4 étapes | **🏗️ 553 lignes** | Structure faite, service non branché |
| 6 | Intégration Planificateur | ❌ À faire | Actions individuelles exportées |
| 7 | Auto au démarrage | ❌ À faire | Hook dans main_window |
| 8 | Corbeille + sécurité | ❌ À faire | `send2trash` optionnel |
| 9 | Tests d'intégration GUI | ❌ À faire | Tests UI + service |

---

## 14. Questions en suspens (à valider)

- [x] Bibliothèque de tags : `mutagen` (déjà disponible via `aioslsk`)
- [x] Structure de classement par défaut : `{artist}/{album}/{track:02d} {title}.{ext}`
- [ ] Corbeille interne vs corbeille système (`send2trash`) ?
- [x] Mode "sec" (dry-run) : utile, à ajouter comme option dans l'étape 1
- [ ] Gestion des fichiers non-audio (PDF, images, archives) dans le dossier downloads ?

---

*Spec v1 — créée suite à interview utilisateur. En attente de validation avant implémentation.*
