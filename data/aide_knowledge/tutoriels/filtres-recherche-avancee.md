---
title: "Maîtriser les filtres de recherche avancée"
category: tutoriels
keywords: ["recherche", "filtre", "filtrage", "trie", "tri", "resultat", "résultat", "mot-cle", "mot-clé", "exclusion", "motif", "regex", "pattern", "wildcard", "joker", "syntaxe", "syntax", "affine", "précis"]
---

# Maîtriser les filtres de recherche avancée

> **Niveau :** Avancé  
> **Temps de lecture :** 10 min  
> **Bots concernés :** 🔍 Recherche, 💡 Wishlist

---

## Objectif

Le bot **Recherche** propose bien plus qu'une simple barre de recherche. Ce tutoriel vous apprend à utiliser les **filtres avancés** pour trouver exactement ce que vous cherchez, avec une précision chirurgicale.

---

## 1. Les filtres rapides

Directement depuis la barre de recherche, utilisez ces **opérateurs** :

| Opérateur | Exemple | Effet |
|-----------|---------|-------|
| `+mot` | `+lossless` | Le mot **doit** apparaître |
| `-mot` | `-remix` | Le mot **ne doit pas** apparaître |
| `"phrase"` | `"best of 2024"` | Recherche la **phrase exacte** |
| `mot*` | `jaz*` | **Troncature** : jazz, jazzy, jazzfusion |
| `mot~` | `flac~` | **Orthographe approximative** : flac, flak, flack |

### Exemples concrets

| Vous cherchez… | Tapez… |
|----------------|--------|
| Du jazz en FLAC, pas de remix | `jazz +flac -remix` |
| Un album best-of de 2024 | `"best of 2024"` |
| De la musique brésilienne (bossa, samba…) | `brasil*` |
| Un fichier nommé « live » mal orthographié | `live~` |

---

## 2. Les filtres structurés

Pour un contrôle plus fin, ouvrez le **panneau de filtres** (`Filtres ⟶` dans la barre d'outils de recherche).

### Filtres disponibles

| Filtre | Options | Exemple |
|--------|---------|---------|
| **Type de fichier** | MP3 / FLAC / AAC / WAV / OGG / Autre | Ne garder que les FLAC |
| **Taille** | Plage personnalisée en Mo | `10 Mo – 100 Mo` (ni trop petit, ni un album complet) |
| **Débit** | Minimum en Kbps (MP3) | `≥ 320 Kbps` |
| **Bitrate** | Lossless / Lossy | Forcer le lossless |
| **Date d'ajout** | Moins de 24h / 7 jours / 30 jours | Fichiers récents |
| **Utilisateur** | Nom spécifique | Exclure une source |
| **Dossier** | Motif dans le chemin | `+live` ou `+acoustic` |

### Sauvegarder une combinaison de filtres

Quand vous trouvez une combinaison gagnante :

1. Configurez tous vos filtres
2. Cliquez sur **« Sauvegarder le filtre »**
3. Donnez-lui un nom (ex: « FLAC lossless récent »)

Les filtres sauvegardés apparaissent dans le menu **« Mes filtres »** pour une réutilisation instantanée.

---

## 3. Recherche par motifs (pattern matching)

Pour les utilisateurs avancés, la recherche supporte les **expressions régulières simplifiées** :

| Motif | Signification | Exemple |
|-------|---------------|---------|
| `?` | Un caractère quelconque | `d?mo` → demo, damo, dimo |
| `*` | Zéro ou plusieurs caractères | `rock*` → rock, rocks, rockband |
| `[abc]` | Un des caractères listés | `[pb]at` → pat, bat |
| `[a-z]` | Intervalle de caractères | `[a-e]` → a, b, c, d, e |
| `{mot1,mot2}` | Alternative | `{live,concert} 2024` |

### Exemples avancés

| Objectif | Syntaxe |
|----------|---------|
| Trouver « live » ou « concert » de 2024 | `{live,concert} 2024` |
| Fichiers de démo en 2 parties maximum | `demo_?` (demo_1, demo_2) |
| Exclure les versions instrumentales | `-instrumental` |

> ⚠️ Les motifs fonctionnent uniquement sur le **nom du fichier**. Pour filtrer sur les métadonnées, utilisez les filtres structurés (section 2).

---

## 4. Utiliser la Wishlist comme filtre croisé

La **Wishlist** peut être couplée à la recherche pour des requêtes semi-automatiques :

1. Configurez vos souhaits dans le bot **Wishlist**
2. Lancez une recherche normale depuis le bot **Recherche**
3. Activez l'option **« Croiser avec Wishlist »**

→ Les résultats seront marqués d'un badge 🎯 si un mot-clé de la wishlist est détecté dans le nom du fichier

```
┌─ Résultats de recherche : jazz ────────────────────┐
│                                                      │
│  🎯 Jazz Quartet - Live Session (FLAC, 85 Mo)        │
│  🎯 Best of Jazz 2024 (MP3, 320 Kbps, 125 Mo)        │
│     Smooth Jazz Collection (MP3, 128 Kbps, 45 Mo)    │
│  🎯 Miles Davis - Kind of Blue (FLAC, 250 Mo)        │
│                                                      │
│  [3 souhaits détectés sur 15 résultats]              │
└──────────────────────────────────────────────────────┘
```

---

## 5. Combiner tout : scénario avancé

### Exemple concret

Vous cherchez des **albums de jazz récents en FLAC, de bonne qualité, exclus les compilations**.

**Étape 1** — Barre de recherche : `jazz +flac -compilation -remix`

**Étape 2** — Filtres structurés :
- Type : FLAC
- Taille : 30 Mo – 300 Mo
- Débit : Lossless uniquement
- Date : Moins de 30 jours

**Étape 3** — Option Wishlist couplée activée

**Étape 4** — Lancez la recherche et triez les résultats :

| Critère de tri | Effet |
|----------------|-------|
| **Pertinence** | Meilleure correspondance textuelle |
| **Taille ↓** | Du plus lourd au plus léger |
| **Date ↓** | Du plus récent au plus ancien |
| **Disponibilité** | Sources les plus nombreuses d'abord |

---

## 6. Mémoriser ses préférences de filtres

Les filtres structurés peuvent être enregistrés comme **modèle de recherche** :

1. Configurez tous vos filtres
2. Cliquez sur **« Enregistrer comme modèle »**
3. Nommez-le (ex: « Recherche FLAC rapide »)
4. Associez-le éventuellement à un raccourci clavier

→ Vos modèles sont accessibles depuis le menu **Recherche → Mes modèles**

L'application restaure automatiquement le dernier modèle utilisé au lancement (option activable dans `Paramètres → Recherche`).

---

## Dépannage

| Problème | Solution |
|----------|----------|
| Les opérateurs `+` et `-` ne fonctionnent pas | Vérifiez qu'ils sont collés au mot : `+flac` (pas `+ flac`) |
| Un filtre semble ignoré | Les filtres s'appliquent **après** la recherche textuelle. Si aucun résultat ne passe le filtre, la liste est vide |
| Trop de résultats parasites | Utilisez la **recherche par phrase exacte** `"..."` pour réduire le bruit |

---

**Voir aussi :** [Configuration recherche →](/technique/configuration-recherche) | [Configurer une recherche automatique →](/tutoriels/configurer-recherche-automatique) | [FAQ recherche sans résultat →](/faq/recherche-sans-resultat)
