---
title: Navigation utilisateur (Browse) dans le bot Recherche
category: guide_bots
keywords:
  - navigation utilisateur
  - browse utilisateur
  - browse user
  - search user
  - recherche chez utilisateur
  - rechercher chez utilisateur
  - voir fichiers utilisateur
  - browse mode
  - mode navigation
  - banniere browse
  - bannière browse
  - _enter_browse_mode
  - _exit_browse_mode
  - _on_browse_user
  - search_user
  - navigation fichier
  - navigation fichier
  - retour recherche globale
  - parcourir utilisateur
  - explore user
---

# Navigation utilisateur (Browse) dans le bot Recherche

Ce guide explique comment utiliser le mode **navigation utilisateur** (browse) pour consulter et rechercher les fichiers partagés par un utilisateur spécifique sur Soulseek.

---

## 1. Qu'est-ce que le mode navigation utilisateur ?

Le mode navigation utilisateur permet de **cibler la recherche sur un seul utilisateur** plutôt que sur l'ensemble du réseau Soulseek. Utile quand vous savez qu'un utilisateur en particulier possède les fichiers que vous cherchez.

**Différence avec la recherche globale :**

| Aspect | Recherche globale | Navigation utilisateur |
|---|---|---|
| Cible | Tout le réseau | Un seul utilisateur |
| Résultats | Provenant de multiples sources | D'un seul utilisateur |
| Performances | Variable, peut retourner 200 résultats | Ciblé, généralement plus rapide |
| Contexte | Aucun | Bannière "Fichiers de {utilisateur}" |
| Retour | — | Bouton "← Retour à la recherche globale" |

Le mode fonctionne via `_connexion_manager.search_user(username, query)` qui interroge directement les fichiers partagés par cet utilisateur sur le réseau Soulseek.

---

## 2. Comment entrer en mode navigation utilisateur

### 2.1 Depuis le menu contextuel (clic droit)

C'est la méthode la plus courante :

1. **Lancez une recherche** dans le bot Recherche (ex: "radiohead")
2. **Faites un clic droit** sur un résultat
3. **Sélectionnez** l'option **👤 Voir les fichiers de {utilisateur}**

```
┌─────────────────────────────────────────────┐
│  Résultat : song.flac — utilisateur123      │
│                                              │
│  [clic droit]                                │
│  ┌─────────────────┐                        │
│  │ ⬇ Télécharger   │                        │
│  │ 👤 Voir fichiers │ ← Cliquez ici         │
│  │ ─────────────── │                        │
│  │ 📋 Copier nom   │                        │
│  │ 🚫 Bloquer      │                        │
│  └─────────────────┘                        │
└─────────────────────────────────────────────┘
```

> **💡 Astuce :** Pas besoin de recherche préalable. Vous pouvez aussi taper le nom d'utilisateur manuellement (voir section 2.3).

### 2.2 Depuis une suggestion d'historique

Si vous avez déjà recherché chez cet utilisateur :

1. Cliquez sur la **suggestion** correspondante dans la barre sous le champ de recherche
2. Le mode navigation est automatiquement activé avec le bon utilisateur
3. La recherche est relancée immédiatement

Les suggestions sont reconnaissables par leur type : les entrées `"user"` dans l'historique rétablissent le mode browse au clic.

### 2.3 Depuis une recherche manuelle

Si vous connaissez déjà le nom de l'utilisateur :

1. **Lancez d'abord une recherche** en tapant votre requête dans le champ (ex: "beach boys")
2. Dans le menu contextuel d'un résultat, cliquez sur **👤 Voir les fichiers de {utilisateur}**
3. Le mode s'active et la recherche est relancée chez cet utilisateur

> ⚠️ **Note :** Si le champ de recherche est vide quand vous cliquez sur "👤 Voir les fichiers", le bot affiche : `📝 Entrez un terme de recherche avant de parcourir un utilisateur`.

---

## 3. L'interface en mode navigation

Quand le mode navigation est actif, une **bannière** apparaît en haut du bot Recherche :

```
┌─────────────────────────────────────────────────┐
│ 👤 Fichiers de utilisateur123                    │
│                                    [← Retour]   │
├─────────────────────────────────────────────────┤
│ [🔍 Rechercher des fichiers partagés par         │
│  utilisateur123…                      ]          │
│                                                  │
│ Résultats :                                      │
│ ┌────┬──────────┬───────┬──────┬─────┬──────┐  │
│ │EXT │ Fichier  │ Taille│Bitrate│Durée│ User │  │
│ ├────┼──────────┼───────┼──────┼─────┼──────┤  │
│ │FLAC│song1.flac│ 25 Mo │ 950  │3:45 │user1 │  │
│ │MP3 │song2.mp3 │ 10 Mo │ 320  │3:50 │user1 │  │
│ └────┴──────────┴───────┴──────┴─────┴──────┘  │
└─────────────────────────────────────────────────┘
```

### Éléments de la bannière

| Élément | Description |
|---|---|
| 👤 **Icône** | Indique que vous êtes en mode navigation utilisateur |
| **Label** | "Fichiers de {nom d'utilisateur}" — indique qui est ciblé |
| **← Retour à la recherche globale** | Bouton pour quitter le mode |

### Changements dans l'interface

- **Placeholder** du champ de recherche : `Rechercher des fichiers partagés par {utilisateur}…`
- **Statut** : Affiche `🔍 Recherche de « {requête} » chez {utilisateur}…` pendant la recherche
- **Résultats** : `✅ X résultats trouvés chez {utilisateur}` ou `⚠️ 200 résultats max chez {utilisateur} — affinez votre recherche`

---

## 4. Comment quitter le mode navigation

### 4.1 Bouton "Retour à la recherche globale"

Cliquez sur le bouton **← Retour à la recherche globale** dans la bannière. Cela :

1. Efface le nom d'utilisateur ciblé
2. Masque la bannière
3. Restaure le placeholder par défaut : `Rechercher des fichiers audio sur Soulseek…`
4. Vide les résultats (`_clear_results()`)
5. Réinitialise l'état de recherche (`_reset_search_state()`)

### 4.2 Depuis une suggestion d'historique globale

Si vous cliquez sur une suggestion d'historique de type `"global"` ou `"room"` alors que vous êtes en mode navigation utilisateur, le mode browse est automatiquement quitté avant de lancer la nouvelle recherche.

### 4.3 Déconnexion

Si la connexion Soulseek est perdue, `_on_disconnected()` appelle `_reset_search_state()` qui réinitialise l'état, mais **ne quitte pas** automatiquement le mode navigation. La bannière reste affichée, mais le champ de recherche est désactivé jusqu'à la reconnexion.

---

## 5. Cas d'utilisation pratiques

### 5.1 Voir tous les fichiers FLAC d'un utilisateur

1. Lancez une recherche sur un terme large (ex: "music" ou "*")
2. Si vous trouvez un résultat FLAC de `utilisateurX`, faites **clic droit → 👤 Voir les fichiers**
3. Le mode browse s'active avec `utilisateurX`
4. Les résultats sont filtrés par défaut via le toggle **🔊 Audio seulement**
5. Triez par la colonne **Extension** pour regrouper les FLAC en haut

### 5.2 Vérifier si un utilisateur a des fichiers rares

1. Demandez le pseudo d'un utilisateur dans un salon de discussion
2. Lancez une recherche sur un terme spécifique (ex: "beatles mono")
3. Dans le menu contextuel d'un résultat de cet utilisateur, cliquez sur **👤 Voir les fichiers**
4. Utilisez les filtres avancés (🔍 Filtres) pour préciser bitrate, durée ou taille

### 5.3 Comparer les bibliothèques de deux utilisateurs

1. Lancez une recherche → cliquez droit sur un résultat de `userA` → **👤 Voir les fichiers**
2. Notez les résultats
3. Cliquez sur **← Retour à la recherche globale**
4. Trouvez un résultat de `userB` → cliquez droit → **👤 Voir les fichiers**
5. Comparez les résultats

---

## 6. Comportement technique

### 6.1 Ordre de priorité des modes de recherche

Quand vous lancez une recherche (`_on_search`), le mode est choisi dans cet ordre :

```
1. Mode salon (room)      → search_room()
2. Mode navigation (user) → search_user(username, query)  ← BROWSE
3. Clients actifs         → search_user() pour chaque client
4. Recherche globale      → search(query)
```

Le mode **navigation utilisateur** est prioritaire sur les modes "clients actifs" et "global", mais pas sur le mode "salon". Si les deux sont actifs (browse + room), seul le salon est utilisé.

### 6.2 Historique en mode navigation

Chaque recherche en mode navigation est enregistrée dans l'historique avec :
- `type = "user"`
- `username` = nom de l'utilisateur ciblé
- `query` = terme recherché

Ceci permet de retrouver facilement une recherche utilisateur dans les suggestions.

### 6.3 Timer et timeout

Le timer de 30 secondes (`QTimer.singleShot(True)`) fonctionne aussi en mode navigation. Passé ce délai, le statut passe à :
`⏱️ La recherche continue en arrière-plan…`

La recherche Soulseek se poursuit (les résultats arrivent toujours via l'EventBus), mais l'interface indique que les résultats initiaux sont arrivés.

### 6.4 Limite de résultats

La limite `MAX_RESULTS = 200` s'applique aussi en mode navigation. Si elle est atteinte, un avertissement spécifique s'affiche :
`⚠️ 200 résultats max chez {utilisateur} — affinez votre recherche`

---

## 7. Dépannage

### 7.1 "Entrez un terme de recherche avant de parcourir un utilisateur"

**Cause :** Vous avez cliqué sur "👤 Voir les fichiers" mais le champ de recherche est vide.
**Message dans le statut :** `📝 Entrez un terme de recherche avant de parcourir un utilisateur`
**Solution :** Tapez d'abord un terme dans le champ (minimum 2 caractères), puis cliquez droit sur un résultat.

### 7.2 Le bouton "Voir les fichiers" ne fait rien

**Causes possibles :**
- L'utilisateur n'est plus connecté au réseau Soulseek
- La connexion a été perdue (vérifiez le statut de connexion en haut)
- Le menu contextuel a été ouvert sur une zone vide du tableau

### 7.3 Aucun résultat en mode navigation

**Causes possibles :**
- Le terme de recherche est trop spécifique — essayez un terme plus large
- L'utilisateur a peu de fichiers partagés
- L'utilisateur n'a que des fichiers qui ne correspondent pas au filtre **🔊 Audio seulement** (désactivez le toggle pour voir tous les fichiers)
- L'utilisateur est déconnecté — les résultats de browse ne sont disponibles que si l'utilisateur est en ligne

### 7.4 Impossible de quitter le mode navigation

**Solution :** Cliquez sur **← Retour à la recherche globale** dans la bannière. Si le bouton ne répond pas :
- Redémarrez le bot (onglet Recherche → actualisez)
- Ou cliquez sur une suggestion d'historique globale pour forcer la sortie

### 7.5 La bannière reste affichée après reconnexion

**Cause :** La déconnexion ne quitte pas automatiquement le mode navigation.
**Solution :** Cliquez sur **← Retour à la recherche globale** pour réinitialiser.

---

**Voir aussi :**
- [/guide_bots/02-bot-recherche](/guide_bots/02-bot-recherche) — Guide complet du bot Recherche
- [/guide_bots/14-colonnes-tri-recherche](/guide_bots/14-colonnes-tri-recherche) — Colonnes et tri personnalisé des résultats
- [/guide_bots/13-filtres-format-recherche](/guide_bots/13-filtres-format-recherche) — Filtres de format (audio seulement, avancés)
- [/faq/recherche-sans-resultat](/faq/recherche-sans-resultat) — Causes et solutions quand la recherche ne donne rien
