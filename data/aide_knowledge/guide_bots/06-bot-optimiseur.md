---
title: "Bot Optimiseur — Guide complet"
category: guide_bots
keywords: ["optimiseur", "configuration", "paramètre", "profil", "réseau", "performance", "réglage"]
---

## Bot Optimiseur

Le **bot Optimiseur** est le tableau de bord d'optimisation centralisé. Il applique des profils prédéfinis qui modifient automatiquement les paramètres des différentes pages de configuration.

### Interface

- **Profil actif** : visualisation du profil en cours d'application
- **Galerie de profils** : liste des profils disponibles prêts à l'emploi
- **Statut** : état d'avancement de l'application d'un profil

### Profils disponibles

| Profil | Effet |
|--------|-------|
| **Performance** | Optimise les paramètres réseau pour maximiser la vitesse |
| **Économie** | Réduit la consommation de ressources (connexions limitées) |
| **Recherche** | Paramètres optimisés pour la recherche de fichiers rares |
| **Partage** | Configuration pour maximiser le partage de fichiers |
| **Personnalisé** | Profil créé par l'utilisateur selon ses besoins |

### Fonctionnement

1. Choisis un profil dans la galerie
2. L'Optimiseur applique automatiquement les réglages un par un
3. Chaque réglage est appliqué dans la page de configuration concernée
4. Un statut en direct montre la progression
5. Une fois terminé, la configuration est active

### Pages concernées

- **Réseau** : connexions, ports, bande passante
- **Recherche** : timeouts, filtres, résultats max
- **Téléchargement** : limites de vitesse, slots
- **Bibliothèque** : partage, dossiers

### Astuces

- Utilise le profil **Performance** si tu as une bonne connexion
- Passe en **Économie** si l'application utilise trop de ressources
- Crée tes propres profils personnalisés en JSON dans `data/profils/`
