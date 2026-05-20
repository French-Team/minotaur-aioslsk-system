---
title: "Ordonnanceur et Planificateur — Services d'analyse et d'automatisation"
category: technique
icon: ⚙️
keywords:
  - OrdonnanceurService
  - ordonnanceur service
  - ordonnanceur_service.py analyse
  - PlanificateurService
  - planificateur service
  - planificateur_service.py
  - PlanificationDB
  - planification bd sqlite
  - planification base donnee
  - planification base données
  - FichierInfo dataclass
  - AnalyseResultat dataclass
  - scanner dossier analyse
  - analyser fichier metadonnee
  - analyser fichier métadonnée
  - mutagen extraction tag
  - mutagen tag audio
  - fallback parsing nom fichier
  - expression reguliere parsing
  - expression régulière parsing
  - PATTERN CLASSIQUE regex
  - PATTERN SIMPLE regex
  - _parser_nom_fichier pattern
  - _detecter_doublons rapide
  - _detecter_doublons hash sha256
  - _calculer hash sha256
  - preparer renommage template
  - preparer classement artiste album
  - generer nom fichier template
  - generer chemin classement
  - deplacer vers corbeille
  - action planifiee crud
  - action planifiée crud
  - get actions dues
  - execution automatique tache
  - exécution automatique tâche
  - pause resume planificateur
  - cli ordonnanceur console
  - cli ordonnanceur argparse
  - renommage preset
  - classement preset
  - fichier audio extension
  - resoudre conflits renommage
  - résoudre conflits renommage
  - apercu operation ordonnanceur
  - aperçu opération ordonnanceur
  - executer operation lot
  - exécuter opération lot
  - nettoyage fichier audio
  - deduplication hash
  - déduplication hash
---

# ⚙️ Ordonnanceur et Planificateur — Services d'analyse et d'automatisation

## Introduction

L'application intègre deux services complémentaires pour la gestion des fichiers audio :

1. **`OrdonnanceurService`** (`ordonnanceur_service.py`, 1860 lignes) — analyse, renomme, classe, déduplique et nettoie les fichiers audio
2. **`PlanificateurService`** (`planificateur_service.py`, 726 lignes) — planifie et exécute des actions automatisées selon un calendrier

Un **CLI dédié** (`cli_ordonnanceur.py`, 450 lignes) expose les fonctionnalités de l'ordonnanceur en ligne de commande.

> Ensemble, ces services forment le backend des bots **Ordonnanceur** (bot_09) et **Planificateur** (bot_08).

---

## Architecture

```
                    Utilisateur
                        │
          ┌─────────────┴─────────────┐
          │                           │
    OrdonnanceurService         PlanificateurService
    (analyse & opérations)      (automatisation)
          │                           │
          │                           ├── PlanificationDB (SQLite)
          │                           │      actions, historique, stats
          │                           │
          ├── mutagen (tags)          └── Exécution périodique
          ├── regex (fallback)              │
          └── CLI (argparse)               │
                                           ▼
                                    OrdonnanceurService
                                    (appels automatisés)
```

---

## 1. OrdonnanceurService

### Dataclasses

#### `FichierInfo`

Stocke les métadonnées complètes d'un fichier audio :

```python
@dataclass
class FichierInfo:
    path: Path              # Chemin complet
    taille: int             # Taille en octets
    codec: str              # Codec audio (mp3, flac, etc.)
    duree: float            # Durée en secondes
    bitrate: int            # Bitrate
    sample_rate: int        # Fréquence d'échantillonnage
    artiste: str            # Nom de l'artiste
    album: str              # Nom de l'album
    titre: str              # Titre du morceau
    piste: int              # Numéro de piste
    annee: int              # Année
    genre: str              # Genre musical
    hash_sha256: str        # Empreinte SHA256
```

#### `AnalyseResultat`

Bilan complet d'une analyse de dossier :

```python
@dataclass
class AnalyseResultat:
    dossier: Path
    fichiers: list[FichierInfo]
    total_fichiers: int
    taille_totale: int       # Octets
    doublons: list           # Paires de fichiers en doublon
    duree_analyse: float     # Secondes
```

### Analyse des fichiers

#### `scanner_dossier(dossier, recursive=True)`

Parcourt un dossier et retourne la liste des fichiers audio :

```python
def scanner_dossier(self, dossier: Path, recursive: bool = True) -> list[Path]:
    if not dossier.exists():
        return []
    pattern = "**/*" if recursive else "*"
    fichiers = []
    for ext in AUDIO_EXTENSIONS:
        fichiers.extend(dossier.glob(f"{pattern}{ext}"))
    return sorted(set(fichiers))
```

Filtre par `AUDIO_EXTENSIONS` (mp3, flac, ogg, m4a, wav, etc.).

#### `analyser_fichier(path) -> FichierInfo`

Méthode centrale d'analyse avec **3 niveaux de profondeur** :

```
1. Mutagen (tags du fichier)
   ├── artiste, album, titre, piste, annee, genre
   └── codec, duree, bitrate, sample_rate
       │
       └── Si incomplet ──────────────────────────┐
                                                  ▼
2. Fallback nom de fichier (regex)
   ├── PATTERN_CLASSIQUE
   │   "Artiste - Album - 01 Titre.mp3"
   └── PATTERN_SIMPLE
       "Artiste - Titre.mp3"
       │
       └── Si toujours incomplet ────────────────┐
                                                  ▼
3. Fallback dossier parent
   └── Nom du dossier parent utilisé comme artiste
```

#### `analyser_dossier(dossier) -> AnalyseResultat`

Combine `scanner_dossier` + `analyser_fichier` sur tous les fichiers + détection de doublons.

### Détection des doublons

Deux niveaux :

```python
def _detecter_doublons_rapide(self, fichiers: list[FichierInfo]) -> list:
    """Doublons basés sur le nom (lowercase) + taille identiques."""

def _detecter_doublons_hash(self, fichiers: list[FichierInfo]) -> list:
    """Confirmation via SHA256 (lecture des 64 premiers Ko)."""

def _calculer_hash(self, chemin: Path) -> str:
    """Calcule SHA256 du fichier par blocs de 64 Ko."""
```

1. **Rapide** : nom identique (insensible) + même taille → doublon potentiel
2. **Par hash** : SHA256 des 64 premiers Ko → doublon certain

### Opérations de préparation

| Méthode | Description |
|---------|-------------|
| `preparer_renommage(analyse, template)` | Génère les nouveaux noms selon un template, détecte les conflits |
| `preparer_classement(analyse, racine, template)` | Prépare le classement artiste/album avec structure de dossiers |
| `estimer_operations(analyse)` | Estime le nombre d'opérations nécessaires |

#### `preparer_renommage()`

```python
def preparer_renommage(self, analyse: AnalyseResultat, template: str) -> dict:
    """
    Template ex: "{piste:02d} - {titre}.{ext}"
    Retourne: {
        "fichiers": [...],    # Liste des fichiers à renommer
        "total": 150,          # Nombre total
        "conflits": [...],     # Fichiers en conflit (même nom cible)
        "exemples": [...]      # 3 exemples d'aperçu
    }
    """
```

#### `preparer_classement()`

```python
def preparer_classement(self, analyse, racine, template) -> dict:
    """
    Template ex: "{artiste}/{album}/{piste:02d} - {titre}.{ext}"
    """
```

### Templates de renommage

Deux dictionnaires prédéfinis :

```python
RENOMMAGE_PRESETS = {
    "classique": "{piste:02d} - {titre}{ext}",
    "artiste_album": "{artiste} - {album} - {piste:02d} - {titre}{ext}",
    "simple": "{artiste} - {titre}{ext}",
}

CLASSEMENT_PRESETS = {
    "artiste_album": "{artiste}/{album}/{piste:02d} - {titre}{ext}",
    "artiste": "{artiste}/{titre}{ext}",
}
```

### Exécution

```python
def resoudre_conflits(self, apercu: dict) -> None:
    """Résout automatiquement les conflits (incrémentation, écrasement)."""

def generer_apercu(self, analyse, ops: list) -> dict:
    """Génère un aperçu complet des opérations avant exécution."""

def executer_operations(self, apercu: dict) -> dict:
    """Exécute les opérations en lot : renommage, classement, déduplication, nettoyage."""
```

#### `deplacer_vers_corbeille(chemin) -> Path`

```python
def deplacer_vers_corbeille(chemin: Path) -> Path:
    """Déplace un fichier vers ~/.free-buff/corbeille/
    avec horodatage en cas de collision de nom."""
```

---

## 2. PlanificateurService

### PlanificationDB (SQLite)

Gère la persistance des actions planifiées :

```python
class PlanificationDB:
    def __init__(self, db_path: Path)
    def _ensure_schema(self)                    # Crée les tables
    def create_action(self, action: dict) -> int
    def get_action(self, action_id: int) -> dict
    def update_action(self, action_id: int, data: dict)
    def delete_action(self, action_id: int)
    def list_actions(self, filters: dict = None) -> list[dict]
    def get_historique(self, action_id: int = None) -> list[dict]
    def get_stats(self) -> dict
    def get_actions_dues(self) -> list[dict]    # Actions à exécuter maintenant
    def purge_old(self, keep_days: int = 30)
    def close(self)
```

### PlanificateurService (QObject)

Service principal héritant de `QObject`, avec une architecture **singleton** (`__new__`) :

```python
class PlanificateurService(QObject):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

**Interface publique** (wraps PlanificationDB) :

| Méthode | Description |
|---------|-------------|
| `create_action(...)` | Crée une action planifiée |
| `get_action(id)` | Récupère une action |
| `update_action(id, data)` | Modifie une action |
| `delete_action(id)` | Supprime une action |
| `list_actions(filters)` | Liste les actions |
| `get_historique(id)` | Historique d'exécution |
| `get_stats()` | Statistiques globales |

**Gestion d'état** :

```python
@property
def paused(self) -> bool:
    """Le planificateur est-il en pause ?"""

def pause(self) -> None:
    """Met le planificateur en pause."""

def resume(self) -> None:
    """Reprend l'exécution automatique."""
```

**Exécution** :

```python
def execute_manual(self, action_id: int) -> dict:
    """Exécute une action immédiatement (déclenché manuellement)."""

def _on_poll(self) -> None:
    """Vérifie périodiquement les actions dues et les exécute."""

def _get_types_en_cours(self) -> list[str]:
    """Retourne les types d'actions actuellement en cours d'exécution."""
```

---

## 3. CLI Ordonnanceur

Le script `src/cli_ordonnanceur.py` expose l'ordonnanceur en ligne de commande :

```
python -m src.cli_ordonnanceur DOSSIER [options]

Options:
  --ops renommage|classement|deduplication|nettoyage
  --no-resoudre-conflits
```

Avec :
- **`Style`** : classe pour l'affichage coloré en terminal (codes ANSI)
- **`_titre()`**, **`_sous_titre()`** : formatage structuré de la sortie
- Utilise `argparse` pour le parsing des arguments

---

## Cycle de vie complet

### Analyse manuelle

```
Utilisateur → Bot Ordonnanceur → OrdonnanceurService
                                    │
                                    ├── scanner_dossier()
                                    ├── analyser_fichier() (mutagen → regex fallback)
                                    ├── analyser_dossier() (boucle + doublons)
                                    ├── preparer_renommage() / preparer_classement()
                                    ├── generer_apercu()
                                    ├── resoudre_conflits()
                                    └── executer_operations()
```

### Automatisation planifiée

```
PlanificateurService._on_poll()
    │
    ├── Vérifie get_actions_dues()
    ├── Pour chaque action due :
    │   ├── Exécute via OrdonnanceurService.executer_action_planificateur()
    │   └── Enregistre dans l'historique
    └── Attend le prochain cycle
```

---

## Conclusion

| Aspect | Ordonnanceur | Planificateur |
|--------|-------------|---------------|
| **Rôle** | Analyser et organiser les fichiers audio | Automatiser des actions planifiées |
| **Taille** | 1860 lignes | 726 lignes |
| **Stockage** | Pas de persistance | SQLite (PlanificationDB) |
| **CLI** | `cli_ordonnanceur.py` (450 lignes) | — |
| **UI** | Bot Ordonnanceur | Bot Planificateur |
| **Dépendance** | mutagen, hashlib | OrdonnanceurService |

L'ordonnanceur extrait les métadonnées via **mutagen** avec un système de **fallback à 3 niveaux** (tags → regex nom fichier → dossier parent), tandis que le planificateur ajoute une couche d'**automatisation temporelle** avec persistance SQLite et singleton.
