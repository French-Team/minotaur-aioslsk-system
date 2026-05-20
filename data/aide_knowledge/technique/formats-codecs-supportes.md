---
title: "Formats de fichiers et codecs supportés — Guide complet"
category: technique
keywords: ["format", "codec", "audio", "video", "extension", "fichier", "mp3", "flac", "aac", "ogg", "opus", "wav", "aiff", "wma", "ape", "m4a", "m4b", "wv", "dsf", "dff", "lossless", "lossy", "compression", "qualite", "qualité", "bitrate", "debit", "débit", "scan", "bibliotheque"]
---

# Formats de fichiers et codecs supportés — Guide complet

> **Niveau :** Intermédiaire  
> **Temps de lecture :** 10 min  
> **Catégorie :** Technique — Formats supportés

---

## 1. Extensions reconnues par l'application

L'application détecte et gère **3 catégories d'extensions** selon le contexte :

### Scan de bibliothèque (`library_db.py`)

Ces extensions sont scannées lors de l'analyse des dossiers partagés :

| Extension | Format | Codec typique | Type |
|-----------|--------|---------------|------|
| `.mp3` | MPEG Layer 3 | MP3 | Lossy |
| `.flac` | Free Lossless Audio Codec | FLAC | Lossless |
| `.ogg` | Ogg Container | Vorbis / Opus | Lossy |
| `.m4a` | MPEG-4 Part 14 | AAC / ALAC | Lossy/Lossless |
| `.wav` | Waveform Audio | PCM | Non compressé |
| `.wma` | Windows Media Audio | WMA | Lossy |
| `.aac` | Advanced Audio Coding | AAC | Lossy |
| `.opus` | Ogg Opus | Opus | Lossy |
| `.aiff` | Audio Interchange File | PCM | Non compressé |
| `.ape` | Monkey's Audio | APE | Lossless |

### Bibliothèque enrichie (`ordonnanceur_service.py`)

Pour des fonctionnalités avancées (validation, stats), ces extensions supplémentaires sont reconnues :

| Extension | Format | Codec typique | Note |
|-----------|--------|---------------|------|
| `.m4b` | MPEG-4 Audiobook | AAC | Livres audio, chapitrage |
| `.mp4` | MPEG-4 Part 14 | AAC / ALAC | Conteneur vidéo/audio |
| `.wv` | WavPack | WavPack | Lossless, hybride |
| `.dsf` | DSD Stream File | DSD | Audio haute résolution |
| `.dff` | DSD Interchange File | DSD | Audio haute résolution |

### Filtre de recherche audio (`bot_recherche.py`)

Pour le filtrage rapide dans les résultats de recherche :

| Extension | Utilité |
|-----------|---------|
| `.mp3` | Format le plus répandu, filtre par défaut |
| `.flac` | Qualité lossless, favori des audiophiles |
| `.ogg` | Format libre, qualité variable |

---

## 2. Classification des formats

### Par type de compression

```
                 Fichiers audio
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
      Lossless                     Lossy
         │                           │
    ┌────┴────┐              ┌───────┴───────┐
    ▼         ▼              ▼               ▼
Naturel   Compressé       Standard        Avancé
──────────────────────────────────────────────────────
.wav     .flac           .mp3           .aac
.aiff    .ape            .ogg(vorbis)   .opus
         .wv             .wma
         .dsf/.dff       .m4a (AAC)
```

### Lossless (sans perte)

Conserve 100% de l'information audio. Fichiers plus volumineux.

| Format | Taille relative | Usage recommandé |
|--------|----------------|------------------|
| **WAV** | 100% (référence) | Archivage, édition professionnelle |
| **AIFF** | ~100% | Studios Apple, édition |
| **FLAC** | ~50-60% | **Format lossless recommandé** — compatible, open source |
| **APE** | ~45-55% | Meilleur taux de compression, mais moins compatible |
| **WavPack** | ~50-60% | Peut aussi produire des fichiers hybrides (lossy + correctif) |
| **DSF/DFF** | ~200-400% | Audio haute résolution (DSD64/128), audiophiles |

### Lossy (avec perte)

Trade-off entre taille et qualité.

| Format | Débit typique | Qualité perçue | Usage recommandé |
|--------|---------------|----------------|------------------|
| **MP3** | 128-320 kbps | Bonne à très bonne | Format universel, compatible partout |
| **AAC** | 128-256 kbps | Meilleure que MP3 à débit égal | iTunes, YouTube, streaming |
| **OGG Vorbis** | 128-256 kbps | Comparable à AAC | Logiciel libre, jeux vidéo |
| **Opus** | 64-192 kbps | Supérieur aux autres à bas débit | Streaming, VoIP, nouveau standard |
| **WMA** | 128-192 kbps | Comparable à MP3 | Héritage Windows |

---

## 3. Guide de choix — Quel format utiliser ?

### Pour le partage sur Soulseek

| Vous êtes… | Format recommandé | Pourquoi |
|-------------|-------------------|----------|
| **Auditeur classique** | MP3 320 kbps | Compatibilité maximale, bonne qualité, fichiers légers |
| **Audiophile** | FLAC | Qualité parfaite, métadonnées riches, open source |
| **Collectionneur** | FLAC (sources) + MP3 320 (usage) | Archive lossless, usage lossy |
| **Musicien** | WAV / AIFF | Édition, pas de perte de qualité en conversion |

### Critères de qualité

```
Qualité audio perçue (échelle indicative) :

  MP3 128kbps ──── ░░░░░░░░░░░░░░░░░░░░  (moyen)
  MP3 192kbps ──── ██████░░░░░░░░░░░░░░  (correct)
  MP3 320kbps ──── ████████████░░░░░░░░  (bon)
  AAC 256kbps ───── ██████████████░░░░░░  (très bon)
  OGG 256kbps ───── ██████████████░░░░░░  (très bon)
  Opus 192kbps ──── ████████████████░░░░  (excellent)
  FLAC ───────────── ████████████████████  (parfait)
  WAV ───────────── ████████████████████  (parfait)
```

> 💡 **En pratique :** MP3 320 kbps et FLAC sont indiscernables pour 95% des auditeurs sur du matériel grand public. Le FLAC prend ~3-4x plus de place.

---

## 4. Métadonnées et tags

L'application lit les métadonnées pour afficher les informations des fichiers :

| Tag | MP3 (ID3) | FLAC (Vorbis) | WAV |
|-----|-----------|---------------|-----|
| Titre | `TIT2` | `TITLE` | ✗ |
| Artiste | `TPE1` | `ARTIST` | ✗ |
| Album | `TALB` | `ALBUM` | ✗ |
| Piste | `TRCK` | `TRACKNUMBER` | ✗ |
| Genre | `TCON` | `GENRE` | ✗ |
| Année | `TYER` / `TDRC` | `DATE` | ✗ |

> ⚠️ Les fichiers **WAV** et **AIFF** ne supportent pas nativement les métadonnées. Ils sont reconnus et scannés, mais les tags ne seront pas lisibles.

---

## 5. Formats non supportés

Bien que Soulseek permette le partage de **tout type de fichier**, l'application se concentre sur l'audio. Les extensions suivantes sont **ignorées** lors du scan :

| Extension | Raison |
|-----------|--------|
| `.exe`, `.dll`, `.bin` | Exécutables — risque de sécurité |
| `.zip`, `.rar`, `.7z` | Archives — non analysables directement |
| `.jpg`, `.png`, `.gif` | Images — non liées à l'audio |
| `.pdf`, `.doc`, `.txt` | Documents — hors scope audio |
| `.cue`, `.log` | Fichiers accompagnement (CD rip) |
| `.db`, `.ini`, `.cfg` | Fichiers système/configuration |

> L'application ne filtre pas le partage réseau de ces fichiers : un utilisateur peut toujours les télécharger depuis votre bibliothèque si vous les placez dans un dossier partagé. Mais ils ne seront **pas scannés** ni indexés.

---

## 6. Qualité minimale et validation

### Seuils de validation (`ordonnanceur_service.py`)

L'ordonnanceur valide la qualité des fichiers scannés :

```python
TAILLE_MIN_VALIDE = 1024  # 1 Ko minimum
```

Un fichier audio doit faire **au moins 1 Ko** pour être considéré comme valide. Les fichiers corrompus ou vides (0 octet) sont exclus.

### Filtrage dans la recherche

Le bot Recherche propose un filtre **« Audio uniquement »** qui limite les résultats à `.mp3`, `.flac`, `.ogg`. Ce filtre est désactivable pour voir tous les types de fichiers.

---

## 7. Formats haute résolution (Hi-Res)

L'application supporte les formats audiophiles via la bibliothèque enrichie :

| Format | Résolution | Débit | Usage |
|--------|-----------|-------|-------|
| **DSF** | DSD64 (2.8 MHz) / DSD128 (5.6 MHz) | ~5-10 Mo/s | Archivage studio, SACD |
| **DFF** | DSD64 / DSD128 | ~5-10 Mo/s | Format natif des enregistrements DSD |
| **FLAC 24-bit** | Jusqu'à 192 kHz / 24-bit | ~2-5 Mo/s | Standard Hi-Res actuel |
| **WavPack** | Jusqu'à 32-bit / 192 kHz | Variable | Hybride (lossy + correctif) |

> ⚠️ **Stockage :** Un album en DSD64 pèse typiquement **2-4 Go**. Un album FLAC 24-bit/96kHz pèse **800 Mo - 1.5 Go**.

---

## 8. Conversion vers/depuis chaque format

### Flux de conversion courants

```
Source          →   Destination        Utilité
──────────────────────────────────────────────
FLAC (source)   →   MP3 320 kbps       Usage mobile, partage
FLAC (source)   →   AAC 256 kbps       iTunes, iPhone
WAV (master)    →   FLAC               Archivage lossless
DSF (SACD rip)  →   FLAC 24-bit        Compatibilité large
MP3 128 kbps    →   MP3 320 kbps       ❌ Inutile (qualité déjà perdue)
```

> ⚠️ **Règle d'or :** On ne peut pas regagner une qualité perdue. Convertir du lossy vers du lossless **n'améliore pas** la qualité — cela augmente juste la taille du fichier.

### Outils recommandés

| Outil | Platforms | Usage |
|-------|-----------|-------|
| [Foobar2000](https://www.foobar2000.org/) | Windows | Conversion batch, tags |
| [XLD](https://tmkk.undo.jp/xld/index_e.html) | macOS | Conversion précise, extraction CD |
| [FFmpeg](https://ffmpeg.org/) | Linux/Mac/Win | Conversion ligne de commande |
| [MusicBee](https://getmusicbee.com/) | Windows | Gestion de bibliothèque + conversion |

---

## 9. Dépannage — Formats

| Problème | Cause possible | Solution |
|----------|---------------|----------|
| Un fichier MP3 n'apparaît pas dans la bibliothèque | Extension en majuscule `.MP3` | L'application est case-insensitive, vérifiez l'extension réelle |
| Fichier FLAC scanné mais pas lisible | Fichier corrompu | Ré-encodez depuis la source originale |
| WAV présent mais sans tags | WAV ne supporte pas les métadonnées | Renommez le fichier avec des infos dans le nom |
| Un fichier .zip est dans la bibliothèque | Placé dans un dossier partagé | Déplacez-le ou ajoutez `.zip` à la liste d'ignorés |
| Fichier .dsf montre une taille énorme | Normal — le DSD est volumineux | Vérifiez votre espace disque |

---

## Voir aussi

- [Configuration des partages →](/technique/configuration-partages)
- [Configuration recherche →](/technique/configuration-recherche)
- [Filtres de recherche avancée →](/tutoriels/filtres-recherche-avancee)
- [FAQ fichiers introuvables →](/faq/fichiers-introuvables)
- [Scan de la bibliothèque →](/technique/mecanismes-threading)
