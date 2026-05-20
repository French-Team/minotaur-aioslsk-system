---
title: "Formats et codecs — Questions courantes sur la conversion, qualité et métadonnées"
category: faq
keywords: ["format", "codec", "conversion", "convertir", "perte", "qualite", "qualité", "mp3", "flac", "wav", "aac", "ogg", "opus", "tag", "metadonnee", "métadonnée", "bitrate", "debit", "débit", "lossless", "lossy", "compresser", "taille", "audiophile", "telechargement", "téléchargement"]
---

# Formats et codecs — Questions courantes

## ❓ Puis-je convertir un fichier MP3 en FLAC pour améliorer la qualité ?

**Non.** Le MP3 est un format **avec perte** (lossy) : une fois encodé, l'information supprimée est perdue définitivement. Le convertir en FLAC (lossless) ne fera qu'augmenter la taille du fichier sans améliorer la qualité audio.

```
MP3 128 kbps  ──→  FLAC (converti)  ──→  Toujours la qualité MP3 128 kbps
                                                mais 5× plus volumineux
```

✅ **Bonne pratique :** Ne convertissez jamais du lossy vers du lossless. Gardez toujours vos sources originales en FLAC ou WAV si vous voulez une qualité parfaite.

➡️ Voir le guide complet : [Formats et codecs — Classification](/technique/formats-codecs-supportes#2-classification-des-formats)

---

## ❓ Quel est le meilleur format pour partager sur Soulseek ?

| Usage | Format recommandé | Pourquoi |
|-------|-------------------|----------|
| **Auditeur classique** | MP3 320 kbps | Compatible partout, bonne qualité, fichiers légers |
| **Audiophile** | FLAC | Qualité parfaite, métadonnées riches, open source |
| **Collectionneur** | FLAC (source) + MP3 320 (copie) | Archive lossless, usage lossy pour l'écoute mobile |
| **Musicien / Producteur** | WAV 16-bit / 24-bit | Édition, pas de perte en conversion |

> 💡 **En pratique :** MP3 320 kbps et FLAC sont **indiscernables** pour 95% des auditeurs sur du matériel grand public. Le FLAC prend ~3-4× plus de place.

➡️ Voir le [Guide de choix complet](/technique/formats-codecs-supportes#3-guide-de-choix--quel-format-utiliser-)

---

## ❓ À partir de quel bitrate un MP3 est-il de bonne qualité ?

| Bitrate | Qualité perçue | Usage |
|---------|---------------|-------|
| **128 kbps** | Moyenne | Écoute occasionnelle sur écouteurs basiques |
| **192 kbps** | Correcte | Usage courant, bon compromis taille/qualité |
| **256 kbps** | Bonne | Qualité proche du CD pour la plupart des oreilles |
| **320 kbps** | Très bonne | Qualité maximale en MP3, recommandé Soulseek |

✅ **Recommandation :** Visez **320 kbps** (ou au minimum 192 kbps) pour vos partages sur Soulseek.

---

## ❓ Comment convertir mes fichiers sans perte de qualité ?

### Règles d'or

1. **Lossless → Lossy :** OK, perte de qualité acceptable pour gagner de la place
2. **Lossy → Lossless :** ❌ Inutile, n'améliore pas la qualité
3. **Lossy → Lossy :** ❌ Double perte de qualité, à éviter absolument
4. **Lossless → Lossless :** Possible sans perte (ex: FLAC → WAV), mais rarement utile

### Flux de conversion recommandés

| Source → Destination | Utilité |
|---------------------|---------|
| FLAC → MP3 320 kbps | Usage mobile, partage |
| FLAC → AAC 256 kbps | iTunes, iPhone |
| WAV → FLAC | Archivage lossless (gain de place) |
| DSD → FLAC 24-bit | Compatibilité large |

### Outils recommandés

| Outil | Platforms | Commande exemple |
|-------|-----------|-----------------|
| [Foobar2000](https://www.foobar2000.org/) | Windows | Conversion batch via interface |
| [FFmpeg](https://ffmpeg.org/) | Linux/Mac/Win | `ffmpeg -i input.flac -b:a 320k output.mp3` |
| [XLD](https://tmkk.undo.jp/xld/index_e.html) | macOS | Conversion précise + extraction CD |

---

## ❓ Pourquoi mes tags (artiste, album, titre) sont-ils manquants dans la bibliothèque ?

### Causes possibles

| Problème | Cause | Solution |
|----------|-------|----------|
| **Tags absents** | Fichier non tagué | Utilisez [MusicBrainz Picard](https://picard.musicbrainz.org/) pour taguer automatiquement |
| **Tags illisibles** | Format sans métadonnées (WAV, AIFF) | Les fichiers WAV/AIFF ne supportent pas les tags natifs. Renommez le fichier avec les infos dans le nom. |
| **Caractères spéciaux** | Accents mal encodés | Utilisez UTF-8. Évitez les caractères exotiques dans les tags. |
| **ID3v1 vs ID3v2** | Tags ID3v1 limités (30 chars) | Préférez ID3v2 (support Unicode, champs longs) |
| **Format non standard** | Tags dans un format non reconnu | Ré-encodez avec un outil standard (MusicBrainz Picard, MP3Tag) |

### Formats et support des métadonnées

| Format | Type de tag | Support |
|--------|-------------|---------|
| MP3 | ID3v2 | ✅ Complet (Unicode, pochettes, chapitres) |
| FLAC | Vorbis Comment | ✅ Complet |
| OGG | Vorbis Comment | ✅ Complet |
| AAC/M4A | MPEG-4 Metadata | ✅ Complet |
| OPUS | Vorbis Comment | ✅ Basique (titre, artiste, album) |
| WAV | Aucun | ❌ Pas de support natif |
| AIFF | Aucun | ❌ Pas de support natif |

> 💡 **Astuce :** Un fichier WAV nommé `Artiste - Album - 01 - Titre.wav` sera bien indexé et affiché — l'application extrait les infos du nom de fichier si les tags sont absents.

➡️ Voir la section [Métadonnées et tags](/technique/formats-codecs-supportes#4-metadonnees-et-tags)

---

## ❓ Mes fichiers FLAC sont reconnus mais sans pochette. Est-ce normal ?

Oui. L'application lit les métadonnées standard (titre, artiste, album, piste) mais **n'extrait pas les pochettes incluses** dans les tags. C'est un comportement normal — la bibliothèque se concentre sur le texte des métadonnées pour l'affichage et la recherche.

Pour voir les pochettes, utilisez un lecteur dédié (Foobar2000, MusicBee, VLC).

---

## ❓ Conversion batch : comment convertir toute ma bibliothèque FLAC en MP3 ?

### Avec Foobar2000 (recommandé)

1. Ajoutez vos fichiers FLAC à la liste de lecture
2. Sélectionnez-les → clic droit → **Convert → ...**
3. Choisissez **MP3 (LAME) 320 kbps**
3. Définissez le dossier de destination
4. Lancez la conversion

### Avec FFmpeg (ligne de commande)

```bash
# Linux / Mac : Convertir tous les FLAC d'un dossier en MP3 320k
for f in *.flac; do
  ffmpeg -i "$f" -b:a 320k -map_metadata 0 "${f%.flac}.mp3"
done
```

```powershell
# Windows (PowerShell) : Convertir tous les FLAC en MP3 320k
Get-ChildItem *.flac | ForEach-Object {
  ffmpeg -i $_ -b:a 320k -map_metadata 0 "$($_.BaseName).mp3"
}
```

> L'option `-map_metadata 0` préserve les tags ID3 dans le fichier MP3 de sortie.

---

## ❓ Quelle est la différence entre un fichier 16-bit et 24-bit ?

| Résolution | Dynamique | Usage |
|------------|-----------|-------|
| **16-bit / 44.1 kHz** | ~96 dB | CD Audio (Red Book) — qualité standard |
| **24-bit / 48 kHz** | ~144 dB | Studio, mastering |
| **24-bit / 96 kHz** | ~144 dB | Hi-Res Audio, audiophile |
| **24-bit / 192 kHz** | ~144 dB | Archivage studio, sur-échantillonnage |

**En pratique :** Le 24-bit offre une plage dynamique bien supérieure, utile pour le mastering, mais **imperceptible** sur du matériel grand public. Un FLAC 16-bit/44.1kHz est parfait pour l'écoute.

> ⚠️ **Taille :** Un fichier 24-bit/96kHz prend ~2.5× plus de place qu'un 16-bit/44.1kHz.

---

## ❓ Pourquoi mon fichier OGG est-il moins bien qu'un MP3 au même bitrate ?

À bitrate égal, **OGG Vorbis** est généralement **meilleur** que MP3 (surtout en dessous de 192 kbps). Mais la qualité perçue dépend aussi :

- De l'encodeur utilisé (LAME pour MP3, libvorbis/aotuv pour OGG)
- Du contenu audio (la musique électronique compresse mieux que le classique)
- Des réglages de l'encodeur (qualité variable VBR vs débit constant CBR)

| Format | Efficacité à 128 kbps | Efficacité à 256 kbps |
|--------|----------------------|----------------------|
| MP3 | Correct | Très bon |
| AAC | Bon | Excellent |
| OGG Vorbis | Bon | Excellent |
| Opus | Excellent | Excellent |

> 💡 **Opus** est le format le plus moderne et efficace — il surpasse tous les autres à bas débit. Son adoption reste limitée pour le moment sur Soulseek.

---

## ❓ Puis-je retrouver la qualité originale d'un fichier après conversion ?

**Non.** Chaque conversion avec perte (lossy → lossy) **dégrade** la qualité de façon irréversible. C'est la **génération** — comme une photocopie de photocopie.

```
Source originale (WAV/FLAC)
        │
        ▼
   ┌────────────┐
   │ MP3 320k   │ ← 1ʳᵉ génération : excellente qualité
   └────────────┘
        │
        ▼
   ┌────────────┐
   │ MP3 128k   │ ← 2ᵉ génération : qualité moyenne
   └────────────┘
        │
        ▼
   ┌────────────┐
   │ AAC 96k    │ ← 3ᵉ génération : qualité médiocre
   └────────────┘
```

✅ **Toujours garder une copie de la source originale** en lossless (FLAC/WAV) pour pouvoir générer n'importe quel format sans perte supplémentaire.

➡️ Voir la section [Flux de conversion](/technique/formats-codecs-supportes#8-conversion-versdepuis-chaque-format)

---

## ❓ Voir aussi

- [Guide complet des formats et codecs supportés →](/technique/formats-codecs-supportes)
- [Configuration des partages →](/technique/configuration-partages)
- [Filtres de recherche avancée →](/tutoriels/filtres-recherche-avancee)
- [Fichiers téléchargés introuvables →](/faq/fichiers-introuvables)
