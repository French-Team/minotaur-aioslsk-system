---
title: "Salons de discussion (Room) dans le bot Recherche"
category: "guide_bots"
index: 16
icon: "💬"
keywords:
  - salon discussion recherche
  - room recherche soulseek
  - search_room
  - salon discussion soulseek
  - recherche salon bot
  - filtrer salon discussion
  - mode salon recherche
  - bannière salon
  - suggestion historique salon
  - priorité salon recherche
  - salon discussion
  - room
  - search room
  - banniere salon
  - suggestion historique salon
  - priorite salon recherche
  - dépanage salon
  - depannage salon
---

# 💬 Salons de discussion (Room) — Recherche par salon

Le bot Recherche permet de **restreindre une recherche à un salon de discussion** Soulseek. Au lieu de chercher sur tout le réseau ou chez un utilisateur précis, vous cherchez uniquement parmi les fichiers partagés par les utilisateurs présents dans un salon donné.

> **Quand utiliser le mode salon ?** — Lorsque vous savez que le contenu recherché est discuté dans un salon spécifique (ex : un salon dédié à un genre musical). Cela réduit le bruit par rapport à une recherche globale.

---

## ❓ Comment fonctionne la recherche par salon ?

➡️ Le champ `#` situé dans la barre d'outils permet de saisir le nom d'un salon. Quand une recherche est lancée avec un salon actif, le bot appelle `search_room(nom_du_salon, requête)` — une requête ciblée sur ce salon uniquement.

- Le nom du salon apparaît dans la **bannière 💬** en haut de l'interface
- Le statut affiche `Recherche de "requête" dans #salon`
- L'historique enregistre la recherche avec une icône 💬 et le préfixe `#`

---

## ❓ Comment entrer en mode salon ?

➡️ **Deux méthodes** :

### 1. Saisie directe dans le champ `#`

1. Tapez le nom du salon dans le champ `#` à droite de la barre d'outils
2. Saisissez votre requête dans le champ de recherche principal
3. Cliquez sur 🔍 **Rechercher** (ou Entrée)

Le passage en mode salon est automatique dès que vous cliquez sur Rechercher avec un salon rempli.

### 2. Depuis l'historique des suggestions

1. Cliquez sur le champ de recherche pour afficher les suggestions
2. Repérez une entrée précédée de `💬 #salon`
3. Cliquez dessus pour restaurer automatiquement ce contexte
4. Modifiez votre requête si nécessaire et lancez la recherche

> Chaque recherche en mode salon est enregistrée dans l'historique avec le type `"room"` et l'icône `💬`.

---

## ❓ À quoi ressemble l'interface en mode salon ?

➡️ Quand vous entrez en mode salon, plusieurs éléments changent :

### Bannière 💬 (en haut)

```
┌──────────────────────────────────────────────────┐
│ 💬 Salon : #nom_du_salon    [← Retour à la globale] │
└──────────────────────────────────────────────────┘
```

- **Icône** `💬` — identifie visuellement le mode salon
- **Label** `Salon : #nom_du_salon` — confirme le salon actif
- **Bouton** `← Retour à la recherche globale` — permet de quitter le mode

La bannière utilise un fond semi-transparent avec la couleur d'accentuation `WARNING` (orangé).

### Champ de recherche

Le texte indicatif (`placeholder`) change pour : `Rechercher dans #salon…`

### Barre d'outils

Le champ `#` est pré-rempli avec le nom du salon en cours.

### Statut

Pendant la recherche : `🔍 Recherche de "requête" dans #salon`  
Quand la limite de résultats est atteinte : `⚠️ 200 résultats max dans #salon — affinez votre recherche`

---

## ❓ Comment quitter le mode salon ?

➡️ **Deux façons :**

1. **Cliquez sur** `← Retour à la recherche globale` dans la bannière 💬
2. **Effacez le champ `#`** et lancez une nouvelle recherche

Dans les deux cas, le mode salon est désactivé :
- La bannière disparaît
- Le champ `#` est vidé
- Le placeholder redevient `Rechercher des fichiers audio sur Soulseek…`
- Les résultats précédents sont effacés
- Une recherche globale est effectuée

---

## ❓ Quelle est la priorité entre les modes ?

➡️ Le mode salon est **prioritaire** sur les autres modes de recherche.

La hiérarchie dans `_on_search` est :

```
1. Mode salon (room)        → search_room()    ← PRIORITAIRE
2. Mode navigation (browse)  → search_user()
3. Clients actifs            → boucle search_user()
4. Global                    → search()
```

**Conséquence :** si un salon est actif ET qu'un utilisateur est en mode navigation (`browse`), c'est toujours le salon qui prime. L'entrée en mode salon quitte automatiquement le mode navigation utilisateur.

---

## ❓ Les suggestions d'historique fonctionnent-elles aussi pour les salons ?

➡️ **Oui.** Chaque recherche en mode salon est sauvegardée avec son type `"room"`. Dans les suggestions, elle apparaît avec :

- **Icône** `💬` 
- **Préfixe** `#nom_du_salon`

Cliquer sur une suggestion de type `room` :
1. Rétablit le mode salon correspondant (appelle `_enter_room_mode`)
2. Remplit le champ de recherche avec la requête
3. Vous pouvez modifier la requête et relancer

> Les suggestions de type salon coexistent avec les suggestions de type `user` (👤) et `global` (🌐).

---

## ❓ Combien de résultats puis-je obtenir dans un salon ?

➡️ La même limite que les autres modes s'applique : **200 résultats maximum** (`MAX_RESULTS`).

Le comportement est identique :
- Les 200 premiers résultats sont affichés
- Quand la limite est atteinte, un message d'avertissement s'affiche
- Les résultats suivants ne sont pas ajoutés (FIFO non applicable, car la recherche s'arrête au timer)

> Si vous avez besoin de plus de résultats, essayez d'affiner votre requête ou passez en recherche globale.

---

## ❓ Puis-je utiliser les filtres en mode salon ?

➡️ **Oui, tous les filtres fonctionnent en mode salon** — audio, disponibilité, et filtres avancés.

Ils s'appliquent exactement de la même manière que lors d'une recherche globale. Rien ne change dans le comportement des filtres.

---

## ❓ Puis-je passer en navigation utilisateur depuis un salon ?

➡️ **Oui**, mais cela désactive temporairement le mode salon.

1. Faites un **clic droit** sur un résultat dans le tableau
2. Sélectionnez **👤 Voir les fichiers**
3. Le mode **navigation utilisateur** s'active (bannière 👤)
4. La bannière 💬 salon reste **cachée** mais le salon est toujours mémorisé

Pour revenir au salon, quittez le mode navigation utilisateur via `← Retour à la recherche globale`.

> À l'inverse, si vous entrez en mode salon alors que la navigation utilisateur est active, la navigation est automatiquement quittée.

---

## 🛠️ Dépannage

### ❓ Le champ `#` est grisé / inactif

➡️ Vérifiez que vous êtes connecté à Soulseek. Le champ salon est désactivé si `_connexion_manager` n'est pas initialisé.

### ❓ Je ne trouve pas le salon que je cherche

➡️ Assurez-vous d'avoir rejoint le salon au préalable via l'interface des salons de discussion Soulseek. `search_room` ne permet de chercher que dans les salons que vous avez déjà rejoints.

### ❓ Le bouton "Retour à la recherche globale" ne fonctionne pas

➡️ Vérifiez que le bot est dans un état正常. Si le problème persiste, videz manuellement le champ `#` et relancez une recherche.

### ❓ Les résultats semblent limités par rapport à la recherche globale

➡️ C'est normal — un salon ne contient qu'un sous-ensemble d'utilisateurs. Si les résultats sont insuffisants, passez en mode **Clients actifs** (case 🔒 Actifs) ou en **recherche globale**.

### ❓ La bannière salon reste affichée après une reconnexion

➡️ Le mode salon n'est pas automatiquement réinitialisé à la déconnexion. Cliquez sur `← Retour à la recherche globale` ou videz le champ `#` pour rétablir le mode global.

---

> **Voir aussi :** [Guide complet du bot Recherche](/guide_bots/02-bot-recherche) · [Navigation utilisateur (Browse)](/guide_bots/15-navigation-utilisateur-recherche) · [FAQ : Performances et limitations des filtres](/faq/performances-limitations-filtres) · [FAQ : Navigation vs Clients actifs](/faq/navigation-vs-clients-actifs)
