---
title: Navigation utilisateur vs Clients actifs — Quelle différence ?
category: faq
keywords:
  - navigation utilisateur
  - browse utilisateur
  - clients actifs
  - actifs
  - difference browse clients actifs
  - difference browse clients actifs
  - difference browse clients actifs
  - recherche ciblee
  - recherche ciblée
  - search_user
  - browse vs actifs
  - navigation vs actifs
  - quel mode choisir
  - mode recherche
  - priorite recherche
  - priorité recherche
  - salon recherche
  - globale recherche
  - recherche globale
---

❓ **Quelle est la différence entre "Navigation utilisateur" et "Clients actifs" ?**

➡️ Ce sont **deux modes de recherche restreinte**, mais qui fonctionnent différemment :

| Critère | 👤 Navigation utilisateur | 🔒 Clients actifs |
|---|---|---|
| **Cible** | Un seul utilisateur connu | Tous les utilisateurs connus qui sont en ligne |
| **Déclencheur** | Menu contextuel (clic droit → 👤 Voir fichiers) | Case à cocher « 🔒 Actifs » dans l'interface |
| **Nombre de requêtes** | 1 recherche (`search_user`) | N recherches (`search_user` × nombre de clients) |
| **Résultats** | D'un seul utilisateur | De plusieurs utilisateurs connus |
| **Interface** | Bannière « Fichiers de {user} » + bouton retour | Aucun changement visuel (case cochée) |
| **Historique** | Type `"user"` | Type `"clients_actifs"` |
| **Statut** | `chez {utilisateur}` | `chez X client(s) actif(s)` |
| **Quand l'utiliser** | Vous savez qui a le fichier | Vous voulez des résultats rapides sans bruit |

---

❓ **Quand utiliser la navigation utilisateur ?**

➡️ La navigation utilisateur est idéale quand vous **connaissez déjà le pseudo** de quelqu'un qui a probablement le fichier recherché.

**Exemples d'utilisation :**

| Situation | Pourquoi utiliser le browse |
|---|---|
| Un utilisateur dans un salon dit "j'ai toute la discographie" | Browse directement chez lui |
| Vous avez déjà téléchargé des fichiers de qualité chez `user123` | Browse pour voir ses autres fichiers |
| Un fichier rare trouvé chez un utilisateur | Browse pour voir tout son répertoire |
| Vous voulez comparer les bibliothèques de 2 utilisateurs précis | Browse chacun puis comparez |

**Comment y accéder :**
1. Trouvez un résultat de cet utilisateur dans une recherche
2. **Clic droit** → **👤 Voir les fichiers de {utilisateur}**
3. La bannière apparaît : `👤 Fichiers de {utilisateur}`
4. Les résultats sont filtrés à cet utilisateur uniquement
5. Cliquez sur **← Retour à la recherche globale** pour quitter

---

❓ **Quand utiliser les clients actifs ?**

➡️ Les clients actifs sont idéaux quand vous voulez **des résultats rapides et pertinents** sans le bruit de la recherche globale.

**La case « 🔒 Actifs »** se trouve dans la barre d'outils du bot Recherche, à côté du bouton de recherche :

```
[🔍 Rechercher...                               ] [Rechercher] [🔒 Actifs]
                                                              ↑
                                                    Cochez ici
```

**Avantages :**
- ✅ **Plus rapide** — la recherche est envoyée uniquement aux utilisateurs que vous connaissez et qui sont en ligne
- ✅ **Moins de bruit** — pas de résultats d'utilisateurs inconnus ou de mauvaise qualité
- ✅ **Plus fiable** — les clients actifs ont déjà été vérifiés comme étant des sources valides

**Inconvénients :**
- ❌ **Moins de résultats** — si vous connaissez peu d'utilisateurs, les résultats seront limités
- ❌ **Dépend de votre réseau** — si vous venez de commencer, la liste des clients actifs peut être vide
- ❌ **Pas de ciblage précis** — contrairement au browse, vous ne choisissez pas qui est interrogé

**Comment y accéder :**
1. Cochez la case **🔒 Actifs** dans la barre d'outils
2. Lancez une recherche normalement
3. Le bot interroge uniquement vos clients actifs connus
4. Si aucun client actif n'est trouvé, le bot **bascule automatiquement en recherche globale** avec un avertissement

> **💡 La case 🔒 Actifs reste cochée** entre les recherches. Pensez à la décocher pour revenir en recherche globale.

---

❓ **Puis-je utiliser les deux en même temps ?**

➡️ **Non** — les modes s'excluent mutuellement. L'ordre de priorité dans `_on_search` est :

```
1. Mode salon (#room)        → si _room_name est défini       → search_room()
2. Navigation utilisateur    → si _browse_username est défini → search_user()
3. Clients actifs            → si case 🔒 cochée             → search_user() × N
4. Recherche globale         → par défaut                     → search()
```

Si vous êtes en mode navigation utilisateur (bannière affichée), la case 🔒 Actifs est **ignorée** — le mode browse prend la priorité.

---

❓ **Quel est le plus rapide des deux ?**

➡️ **Les clients actifs sont généralement plus rapides** car ils limitent la requête à des utilisateurs connus et en ligne. La navigation utilisateur, bien que ciblée sur une seule personne, dépend entièrement de la disponibilité réseau de cet utilisateur.

| Mode | Durée typique | Pourquoi |
|---|---|---|
| 🌐 Recherche globale | 5-30s | Parcourt tout le réseau Soulseek |
| 🔒 Clients actifs | 2-10s | Uniquement vos contacts en ligne |
| 👤 Navigation user | 3-15s | Dépend de la disponibilité de l'utilisateur ciblé |

> **💡 Conseil :** Si vous cherchez un fichier courant (album populaire), utilisez les clients actifs pour des résultats rapides. Si vous cherchez un fichier rare chez un utilisateur spécifique, utilisez la navigation utilisateur.

---

❓ **Que se passe-t-il si je coche 🔒 Actifs mais que je n'ai aucun client actif ?**

➡️ Le bot affiche un avertissement et **bascule automatiquement en recherche globale** :

```
⚠️ Aucun client actif connu — bascule en recherche globale
```

La recherche est tout de même lancée sur l'ensemble du réseau, mais elle prendra plus de temps et retournera potentiellement plus de résultats (dont des sources inconnues).

**Pourquoi cela arrive-t-il ?**
- Vous venez de commencer à utiliser Soulseek — votre liste de contacts est vide
- Vos contacts sont tous déconnectés
- Le service `ClientsActifsService` n'a pas encore été synchronisé

**Solution :** Échangez avec d'autres utilisateurs dans les salons, téléchargez depuis différentes sources, et la liste des clients actifs se remplira progressivement.

---

❓ **Comment la liste des clients actifs est-elle construite ?**

➡️ Le service `ClientsActifsService` (dans `src/services/clients_actifs_service.py`) maintient une liste mise à jour en temps réel :

```
Événements réseau Soulseek
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  ClientsActifsService (QObject)                      │
│                                                      │
│  self._clients = {                                   │
│      "user1": ClientInfo(username="user1", ...),     │
│      "user2": ClientInfo(username="user2", ...),     │
│      ...                                             │
│  }                                                   │
│                                                      │
│  Méthodes :                                          │
│  - clients_actifs() → [ClientInfo, ...]              │
│    (retourne les clients connus, triés par nom)      │
│  - clients_tries(critère, ordre) → liste triée       │
│                                                      │
│  Événements écoutés :                                │
│  - UserStatusUpdateEvent → mise à jour statut        │
│  - UserInfoUpdateEvent → mise à jour détails         │
└─────────────────────────────────────────────────────┘
        │
        ▼
   self._clients_actifs_cb.checkState() == Checked ?
        │
        ├─ Oui → _on_search utilise _clients_actifs_service
        │         Filtre par statut ONLINE ou AWAY
        │         → search_user() pour chaque client
        │
        └─ Non → Recherche normale
```

Les clients sont suivis via :
- **Synchronisation initiale** : Parcours des contacts existants via `client.users.users`
- **Événements temps réel** : `UserStatusUpdateEvent` (connexion/déconnexion) et `UserInfoUpdateEvent` (mise à jour des infos)

---

❓ **La case 🔒 Actifs est-elle persistante entre les redémarrages ?**

➡️ **Non** — la case n'est pas sauvegardée. Elle revient à l'état décoché à chaque ouverture de l'application.

C'est différent de l'historique de recherche (`SearchHistory`) qui est persisté dans `data/bot_recherche_history.json`.

> **💡** Si vous utilisez souvent les clients actifs, prenez l'habitude de cocher la case dès le lancement du bot Recherche.

---

❓ **Puis-je voir la liste de mes clients actifs ?**

➡️ Oui, le bot **Clients Actifs** (`guide_bots/10-bot-clients-actifs`) affiche la liste complète de vos clients connus avec leur statut, leur vitesse, leurs fichiers partagés et leurs slots disponibles.

C'est utile pour :
- Voir quels utilisateurs sont en ligne avant de lancer une recherche 🔒 Actifs
- Identifier les meilleures sources (vitesse élevée, slots libres)
- Surveiller qui se connecte et se déconnecte

---

❓ **Quel mode choisir selon ma situation ?**

➡️ Guide de choix rapide :

| Situation | Mode recommandé | Pourquoi |
|---|---|---|
| « Je cherche un album populaire » | 🔒 **Clients actifs** | Rapide, peu de bruit |
| « Je veux télécharger X qui a des FLAC rares » | 👤 **Navigation user** | Ciblé sur X |
| « Je cherche dans un salon de discussion » | 🏠 **Mode salon** | Résultats spécifiques au salon |
| « Je ne trouve rien avec les autres modes » | 🌐 **Globale** | Maximum de résultats |
| « Je veux le plus de résultats possible » | 🌐 **Globale** | Tout le réseau Soulseek |
| « Je veux des résultats rapides et fiables » | 🔒 **Clients actifs** | Sources connues et en ligne |
| « Je sais exactement qui a le fichier » | 👤 **Navigation user** | 1 seul utilisateur ciblé |

---

**Voir aussi :**
- [/guide_bots/15-navigation-utilisateur-recherche](/guide_bots/15-navigation-utilisateur-recherche) — Guide complet du mode navigation utilisateur
- [/guide_bots/10-bot-clients-actifs](/guide_bots/10-bot-clients-actifs) — Guide du bot Clients Actifs
- [/guide_bots/02-bot-recherche](/guide_bots/02-bot-recherche) — Guide complet du bot Recherche
- [/faq/recherche-sans-resultat](/faq/recherche-sans-resultat) — Causes et solutions quand la recherche ne donne rien
