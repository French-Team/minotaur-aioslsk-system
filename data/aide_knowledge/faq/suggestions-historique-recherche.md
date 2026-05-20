---
title: "Suggestions d'historique dans le bot Recherche"
category: "faq"
icon: "⌨️"
keywords:
  - suggestion historique recherche
  - historique recherche bot
  - suggestion automatique recherche
  - SearchHistory
  - historique soulseek
  - suggestion salon historique
  - suggestion utilisateur historique
  - suggestion globale historique
  - icone suggestion historique
  - icône suggestion historique
  - supprimer suggestion historique
  - vider historique recherche
  - limite historique recherche
  - persistance historique recherche
  - suggestion historique
  - historique recherche
  - historique soulseek
  - supprimer suggestion
  - vider historique
  - limite historique
  - persistance historique
  - icone suggestion
---

# ⌨️ Suggestions d'historique dans le bot Recherche

Le bot Recherche conserve un **historique des dernières recherches** et les affiche sous forme de **suggestions cliquables** sous le champ de recherche. Ces suggestions permettent de relancer rapidement une recherche précédente, avec le bon contexte (salon, utilisateur, global).

---

## ❓ Comment fonctionne l'historique ?

➡️ Chaque fois que vous lancez une recherche, elle est enregistrée dans un fichier JSON (`data/bot_recherche_history.json`) avec les informations suivantes :

| Champ | Description |
|---|---|
| `query` | Le terme recherché |
| `type` | Contexte : `"global"`, `"room"`, `"user"`, `"clients_actifs"` |
| `username` | Nom du salon (`#salon`) ou de l'utilisateur selon le type |
| `count` | Nombre de fois que cette recherche a été effectuée |
| `timestamp` | Date et heure de la dernière exécution |

> **Stockage :** Les 20 dernières recherches sont conservées (`MAX_HISTORY = 20`).

---

## ❓ Où apparaissent les suggestions ?

➡️ Sous le champ de recherche principal, une ligne de boutons s'affiche automatiquement. Chaque bouton correspond à une recherche récente.

Les suggestions sont construites dans `_rebuild_suggestions()` :
1. Les anciens boutons sont nettoyés (`deleteLater()`)
2. Les entrées récentes sont récupérées via `_search_history.get_recent()`
3. Un bouton `QPushButton` est créé pour chaque entrée
4. Le texte est tronqué à **28 caractères** si nécessaire

---

## ❓ Quelles icônes sont utilisées selon le type de recherche ?

➡️ Chaque type de recherche a son icône :

| Type | Icône | Exemple d'affichage |
|---|---|---|
| **Global** (`"global"`) | 🌐 | `🌐  requête` |
| **Salon** (`"room"`) | 💬 | `💬  requête #nom_salon` |
| **Utilisateur** (`"user"`) | 👤 | `👤  requête nom_user` |
| **Clients actifs** (`"clients_actifs"`) | 🔒 | `🔒  requête` |

Ces icônes sont définies dans `_build_entry_rows()` selon la valeur du champ `type` de chaque entrée.

---

## ❓ Que se passe-t-il quand je clique sur une suggestion ?

➡️ La méthode `_on_suggestion_clicked()` est appelée. Son comportement dépend du type de la suggestion :

- **💬 Salon (`"room"`)** : Appelle `_enter_room_mode(username)` pour basculer en mode salon
- **👤 Utilisateur (`"user"`)** : Appelle `_enter_browse_mode(username)` pour basculer en navigation utilisateur
- **🌐 Global / 🔒 Clients actifs** : Quitte tout mode spécial (appelle `_exit_room_mode()` et `_exit_browse_mode()`)
- Dans tous les cas : le champ de recherche est rempli avec la requête et la recherche est lancée

> **Raccourci :** Un simple clic sur une suggestion suffit — pas besoin de cliquer sur 🔍 Rechercher ensuite !

---

## ❓ Puis-je supprimer une suggestion individuelle ?

➡️ **Oui.** Dans l'affichage des suggestions (lignes construites par `_build_entry_rows()`), chaque bouton de suggestion est accompagné d'un bouton `✕`.

Cliquer sur `✕` supprime cette entrée spécifique de l'historique via `SearchHistory.remove()`.

> **Comportement :** La méthode `remove()` cherche l'entrée correspondant exactement à la `query`, au `type` et au `username`, la supprime de la liste en mémoire, puis sauvegarde le fichier JSON.

---

## ❓ Puis-je vider tout l'historique ?

➡️ **Oui.** Un bouton **« Historique »** est présent en permanence dans la ligne des suggestions. Il permet d'accéder à la vue complète de l'historique (via `HistoryPopup`).

La classe `SearchHistory` expose une méthode `clear()` qui vide toutes les entrées et réécrit le fichier JSON avec une liste vide.

---

## ❓ Comment les doublons sont-ils gérés ?

➡️ La méthode `add()` de `SearchHistory` vérifie si une entrée identique (même `query`, même `type`, même `username`) existe déjà :

1. Si **oui** : l'ancienne entrée est supprimée
2. La nouvelle entrée est ajoutée en **tête** de liste (la plus récente en premier)
3. Le `count` est réinitialisé à 1
4. Le `timestamp` est mis à jour

**Résultat :** une même recherche ne peut pas apparaître deux fois dans l'historique. La refaire la remonte simplement en haut de la liste.

---

## ❓ Quelle est la limite de l'historique ?

➡️ **20 entrées maximum** (`MAX_HISTORY = 20`).

Quand vous dépassez cette limite, les entrées les plus anciennes sont automatiquement supprimées lors de l'ajout d'une nouvelle recherche (`save()` tronque la liste à `MAX_HISTORY` avant d'écrire le fichier).

> **Conseil :** Si vous avez beaucoup de recherches différentes, videz régulièrement l'historique via le bouton « Historique » pour garder des suggestions pertinentes.

---

## ❓ Les suggestions persistent-elles entre les redémarrages ?

➡️ **Oui.** L'historique est stocké dans un fichier JSON sur le disque : `data/bot_recherche_history.json`.

À chaque démarrage du bot :
1. `SearchHistory.__init__()` appelle `_load()` qui lit le fichier
2. Les entrées sont chargées en mémoire
3. Les suggestions s'affichent immédiatement

> **Fichier :** `data/bot_recherche_history.json` — ne le supprimez pas manuellement sauf si vous voulez réinitialiser l'historique.

---

## ❓ Puis-je personnaliser le nombre de suggestions affichées ?

➡️ Indirectement. La méthode `get_recent(n)` permet de spécifier le nombre d'entrées à retourner. Dans le code actuel, `_rebuild_suggestions()` appelle `get_recent()` sans argument explicite, utilisant la constante `SUGGESTION_COUNT`.

Cependant, le **nombre d'entrées conservées** est fixé à 20 (`MAX_HISTORY`). Vous ne pouvez pas augmenter cette limite sans modifier le code source.

---

## ❓ Les suggestions fonctionnent-elles avec tous les modes de recherche ?

➡️ **Oui.** Chaque type de recherche est enregistré avec son contexte :

| Type | Icône Suggestion | Restaure |
|---|---|---|
| `"global"` | 🌐 Recherche standard | Mode global |
| `"room"` | 💬 `#salon` | Mode salon + nom du salon |
| `"user"` | 👤 Utilisateur | Mode navigation + nom de l'utilisateur |
| `"clients_actifs"` | 🔒 Actifs | Mode global (le contexte actifs n'est pas restauré, mais les clients actifs sont une option de la recherche) |

> Les recherches de type `"clients_actifs"` ne restaurent pas la case 🔒 Actifs — elles sont traitées comme des recherches globales dans `_on_suggestion_clicked()`.

---

## 🛠️ Dépannage

### ❓ Les suggestions ne s'affichent pas

➡️ Vérifiez que vous avez déjà effectué au moins une recherche. L'historique est vide au premier lancement. Si le fichier `data/bot_recherche_history.json` a été supprimé ou corrompu, `_load()` échoue silencieusement et une nouvelle liste vide est initialisée.

### ❓ Une recherche récente n'apparaît pas dans les suggestions

➡️ Seules les **20 dernières recherches** sont conservées. Si vous en avez effectué plus de 20, les plus anciennes sont automatiquement supprimées. Vérifiez également que vous n'avez pas accidentellement cliqué sur `✕` à côté de cette suggestion.

### ❓ La suggestion a la mauvaise icône

➡️ Chaque suggestion affiche l'icône correspondant à son `type` (🌐 global, 💬 salon, 👤 utilisateur, 🔒 clients actifs). Si l'icône ne correspond pas, le type a probablement été mal enregistré lors de la recherche. Cela ne peut pas arriver dans un usage normal.

### ❓ Le clic sur une suggestion ne fait rien

➡️ Vérifiez que vous êtes connecté à Soulseek. `_on_suggestion_clicked()` déclenche `_on_search()` qui nécessite une connexion active. Les modes `"room"` et `"user"` nécessitent également que le gestionnaire de connexion soit initialisé.

### ❓ Je veux réinitialiser complètement l'historique

➡️ Supprimez le fichier `data/bot_recherche_history.json` et redémarrez le bot. L'historique sera vide au prochain lancement.

---

> **Voir aussi :** [Guide complet du bot Recherche](/guide_bots/02-bot-recherche) · [Navigation utilisateur (Browse)](/guide_bots/15-navigation-utilisateur-recherche) · [Salons de discussion (Room)](/guide_bots/16-salons-discussion-recherche) · [FAQ : Performances et limitations des filtres](/faq/performances-limitations-filtres)
