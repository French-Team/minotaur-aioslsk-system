---
title: "Bloquer un utilisateur — Liste noire et gestion"
category: faq
keywords: ["bloquer", "utilisateur", "liste noire", "blacklist", "bloqué", "bloque", "ignorer", "abus", "spam"]
---

## Bloquer un utilisateur — Liste noire et gestion

### Pourquoi bloquer un utilisateur ?

Il peut être utile de bloquer un utilisateur pour diverses raisons :

- **Ratio abusif** : il télécharge beaucoup mais ne partage rien
- **Spam** : messages indésirables ou comportement toxique
- **Fichiers de mauvaise qualité** : fichiers mal nommés, faux fichiers
- **Harcèlement** : comportement abusif ou agressif
- **Vol de bande passante** : connections répétées sans partage

### Comment bloquer un utilisateur

#### Méthode 1 : Depuis la configuration

1. Va dans **Optimiseur** → onglet **Utilisateurs**
2. Dans la section **Bloqués**, ajoute le nom d'utilisateur
3. Sépare les noms par des virgules : `"utilisateur1, utilisateur2"`
4. La liste est sauvegardée automatiquement

#### Méthode 2 : Depuis un résultat de recherche

1. Fais un clic droit sur un fichier dans le bot **Recherche**
2. Choisis **Bloquer l'utilisateur** dans le menu contextuel
3. L'utilisateur est ajouté automatiquement à la liste noire

### Effets du blocage

Quand un utilisateur est bloqué :

- ❌ Il ne peut plus télécharger depuis toi
- ❌ Ses fichiers n'apparaissent plus dans tes résultats de recherche
- ❌ Tu ne peux plus parcourir sa bibliothèque
- ✅ Il n'est pas notifié du blocage

### Débloquer un utilisateur

1. Va dans **Optimiseur** → onglet **Utilisateurs**
2. Supprime le nom de la liste des bloqués
3. Le déblocage est immédiat

### Gérer sa liste d'amis

À l'inverse, tu peux ajouter des **amis** pour :
- Leur donner un accès prioritaire à tes slots de téléchargement
- Voir leur statut de connexion dans Clients Actifs
- Favoriser les échanges avec des utilisateurs de confiance

**Méthode** : même page Utilisateurs → section **Amis** → ajoute les noms séparés par des virgules.

---

## Voir aussi

- [Blocage : configuration vs menu contextuel](bloquer-config-vs-contextuel.md) — différences techniques entre les deux méthodes de blocage
- [Configuration utilisateurs](../technique/configuration-utilisateurs.md) — détails techniques du backend de blocage
- [Widget config utilisateurs](../technique/widget-config-utilisateurs-partages.md) — interface du champ Utilisateurs dans l'Optimiseur
