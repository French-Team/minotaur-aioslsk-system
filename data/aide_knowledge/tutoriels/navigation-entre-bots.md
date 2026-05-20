---
title: "Utiliser la navigation entre bots"
category: tutoriels
keywords: ["navigation", "bot", "lien", "page_changed", "basculer", "changer", "accueil"]
---

## Utiliser la navigation entre bots

Les bots communiquent entre eux pour t'offrir une expérience fluide. Voici comment fonctionne la navigation.

### Navigation depuis l'Accueil

Le bot Accueil peut te rediriger vers n'importe quel autre bot :

1. Tape une question dans le champ de l'Accueil
2. Si la question concerne un bot spécifique, l'Accueil te renvoie vers lui
3. Exemple : tape "chercher de la musique" → redirigé vers **Recherche**

### Liens entre bots

Certains bots ont des boutons qui pointent vers d'autres bots :

| Bot source | Lien vers | Quand ? |
|------------|-----------|---------|
| **Bibliothèque** | Connexion | Si déconnecté |
| **Recherche** | Téléchargement | Quand un téléchargement est lancé |
| **Accueil** | Aide | Quand une question d'aide est détectée |
| **Accueil** | Tous les bots | Via les suggestions rapides |

### Navigation manuelle

Tu peux naviguer à tout moment en cliquant sur :

- **Footer** : barre de navigation en bas avec les 12 bots
- **Header** : icône de connexion en haut à gauche
- **Panneau gauche** : navigation secondaire avec sections

### Comment ça marche techniquement

Chaque bot a un signal `page_changed = Signal(str)`. Quand un bot émet ce signal avec le nom d'un autre bot, la **CenterZone** (zone centrale) affiche immédiatement la page correspondante. C'est un découplage propre : les bots n'ont pas besoin de se connaître mutuellement.
