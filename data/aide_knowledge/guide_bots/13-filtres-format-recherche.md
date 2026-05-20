---
title: "Filtres de format dans le bot Recherche — Audio seulement, filtres avancés"
category: guide_bots
keywords: ["filtre", "format", "extension", "audio", "recherche", "mp3", "flac", "ogg", "fichier", "resultat", "modal", "qualite", "qualité", "bitrate", "duree", "durée", "taille", "utilisateur"]
---

# Filtres de format dans le bot Recherche

> **Niveau :** Intermédiaire  
> **Temps de lecture :** 8 min  
> **Catégorie :** Guide — Bot Recherche

---

## 1. Deux niveaux de filtrage

Le bot Recherche propose **deux mécanismes** pour filtrer les résultats :

| Mécanisme | Accès | Effet |
|-----------|-------|-------|
| **🔊 Audio seulement** | Bouton toggle dans la barre d'outils | Filtre rapide : `.mp3`, `.flac`, `.ogg` uniquement |
| **🔍 Filtres avancés** | Fenêtre modale (clic sur "Filtres") | Filtres précis : extension, taille, bitrate, durée, utilisateur |

Les deux peuvent être combinés pour un filtrage précis.

---

## 2. Le toggle « Audio seulement »

### Emplacement

Un bouton toggle est situé dans la **barre d'outils** du bot Recherche, à droite du champ de recherche :

```
[🔍 Champ de recherche...]  [🔊 Audio seulement]  [🔍 Filtres]  ...
```

### Comportement

| État | Texte du bouton | Effet |
|------|-----------------|-------|
| ✅ **Activé** (par défaut) | `🔊 Audio seulement` | Seuls les fichiers `.mp3`, `.flac`, `.ogg` sont affichés |
| ❌ **Désactivé** | `🔊 Tous les fichiers` | Tous les types de fichiers sont visibles (archives, images, documents, etc.) |

### Activation par défaut

Le filtre est **activé par défaut** au lancement du bot (`_audio_filter_enabled = True`). Cela évite le bruit des fichiers non-audio (`.zip`, `.exe`, `.nfo`, `.jpg`) dans les résultats de recherche.

### Comment ça marche

```python
# Extensions audio reconnues par le filtre rapide
EXTENSIONS_AUDIO = {".mp3", ".flac", ".ogg"}
```

Quand le filtre est activé, chaque résultat de recherche est filtré via :

```python
def _is_audio(extension: str) -> bool:
    return extension.lower() in EXTENSIONS_AUDIO
```

> ⚠️ **Important :** Le filtre vérifie l'extension **telle que fournie par Soulseek**. Si un fichier a une extension insolite ou en majuscules, la comparaison est `lower()` donc insensible à la casse (`.MP3` sera reconnu).

---

## 3. La modal « Filtres avancés »

### Accès

Cliquez sur le bouton `🔍 Filtres` dans la barre d'outils pour ouvrir la fenêtre modale de filtres avancés.

### Filtres disponibles

| Filtre | Widget | Plage | Description |
|--------|--------|-------|-------------|
| **Extension** | Liste de sélection | `.mp3`, `.flac`, `.ogg`, `.wav`, `.aac`, `.wma`, `.ape`, `.opus`, `.m4a` | Filtrer par extension spécifique |
| **Taille** | Min / Max (`QSpinBox`) | 0 Ko – ∞ | Taille de fichier en kilo-octets |
| **Bitrate min.** | Curseur + `QSpinBox` | 0–1000 kbps (pas de 32) | Débit binaire minimum |
| **Durée min.** | `QSpinBox` | 0–3600 sec (0 = aucun) | Durée minimale en secondes |
| **Utilisateur** | Champ texte | — | Filtrer les résultats d'un utilisateur spécifique |

### Utilisation typique

| Objectif | Configuration |
|----------|---------------|
| **Musique de qualité** | Audio seulement ✅ + Bitrate min : 192 kbps |
| **Pistes longues (mixsets)** | Durée min : 600 sec (10 min) |
| **Fichiers volumineux** | Taille min : 10 000 Ko (~10 Mo) |
| **FLAC uniquement** | Audio seulement ❌ + Extension : `.flac` |
| **Fichier spécifique perdu** | Désactiver audio, filtrer par utilisateur connu |

### Badge de compteur

Quand des filtres avancés sont actifs, un **badge** s'affiche à côté du bouton `🔍 Filtres` :

```
[🔍 Filtres ③]   ← 3 filtres actifs
```

Le badge prend en compte :
- Le nombre de filtres configurés dans la modal
- L'état du toggle audio (si désactivé, compte comme 1 filtre actif)
- Le mode disponibilité (si actif)

---

## 4. Combinaison des filtres — Exemples concrets

### Exemple 1 : Recherche standard (qualité minimale)

```
🔊 Audio seulement  ✅  →  .mp3, .flac, .ogg
🔍 Filtres avancés      →  Bitrate min : 192 kbps
                          Durée min : 60 sec
```

➡️ Résultat : Morceaux audio de qualité correcte, pas de samples trop courts.

### Exemple 2 : Audiophile (FLAC haute résolution)

```
🔊 Audio seulement  ❌  (tous fichiers)
🔍 Filtres avancés      →  Extension : .flac
                          Bitrate min : 900 kbps
                          Taille min : 20 000 Ko
```

➡️ Résultat : Fichiers FLAC volumineux, probablement 24-bit/96kHz.

### Exemple 3 : Exploration large (tout voir)

```
🔊 Audio seulement  ❌  →  Tous les fichiers
🔍 Filtres avancés      →  (aucun)
```

➡️ Résultat : Résultats bruts tels que fournis par Soulseek, y compris archives, images, documents.

### Exemple 4 : Recherche ciblée par utilisateur

```
🔊 Audio seulement  ✅
🔍 Filtres avancés      →  Utilisateur : "fan_de_musique_2024"
                          Extension : .flac
```

➡️ Résultat : Fichiers FLAC partagés par un utilisateur spécifique.

---

## 5. Interactions et effets visuels

### Changement de texte dynamique

Le bouton `🔊 Audio seulement` change instantanément de texte quand on clique :

- ✅ **coché** → `🔊 Audio seulement`
- ❌ **décoché** → `🔊 Tous les fichiers`

### Indicateurs de statut

La barre de statut affiche l'état actuel des filtres :

```
"Recherche \"pink floyd\" — 15 résultats — 3 filtres"
```

Ou quand le filtre audio est désactivé :

```
"Recherche \"pink floyd\" — 42 résultats — Filtre audio désactivé"
```

### Mise en page des résultats

Le filtre **ne masque pas** les résultats — il les **exclut** du modèle de données. Les résultats non-audio ne sont tout simplement pas ajoutés à la liste quand le filtre est actif.

Si vous désactivez le filtre **après** une recherche, les résultats déjà chargés restent inchangés. Vous devez **lancer une nouvelle recherche** pour que le filtre prenne effet.

---

## 6. Cas pratiques — Dépannage

| Problème | Cause | Solution |
|----------|-------|----------|
| Je ne vois que des MP3/FLAC/OGG | Filtre audio activé par défaut | Cliquez sur `🔊 Audio seulement` pour passer à `🔊 Tous les fichiers` |
| Mes résultats sont trop bruyants (archives, images) | Filtre audio désactivé | Réactivez `🔊 Audio seulement` |
| Je cherche un fichier `.opus` mais il n'apparaît pas | `.opus` n'est pas dans `EXTENSIONS_AUDIO` | Désactivez le filtre audio pour voir tous les fichiers |
| Le badge « Filtres » indique 1 mais je n'ai rien configuré | Le toggle audio compte comme 1 filtre quand désactivé | C'est normal — le badge reflète l'écart par rapport aux réglages par défaut |

---

## Voir aussi

- [Bot Recherche — Guide complet](/guide_bots/02-bot-recherche)
- [Formats de fichiers et codecs supportés — Guide complet](/technique/formats-codecs-supportes)
- [Filtres de recherche avancée — Tutoriel](/tutoriels/filtres-recherche-avancee)
- [FAQ formats et codecs](/faq/formats-codecs)
