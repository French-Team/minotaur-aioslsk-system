---
title: "Bot Aide — Guide complet"
category: guide_bots
keywords: ["aide", "documentation", "guide", "recherche aide", "question", "article", "assistance"]
---

## Bot Aide

Le **bot Aide** est la mémoire de l'application. Il centralise toute la documentation : guides des bots, FAQ, tutoriels, et documentation technique. C'est l'allié du bot Accueil — quand l'Accueil ne peut pas répondre à une question, il te redirige vers le bot Aide.

### Interface

- **Viewer** : affiche le contenu des articles d'aide (Markdown + HTML)
- **Barre latérale** : historique des articles consultés, avec clic droit pour copier/supprimer
- **Barre de recherche** : cherche une réponse directement depuis la page Aide

### Fonctionnalités

| Fonction | Description |
|----------|-------------|
| **Recherche intelligente** | Trouve l'article le plus pertinent par titre, mots-clés ou contenu |
| **Historique** | Conserve les 50 dernières consultations avec la question posée |
| **Menu contextuel** | Clic droit sur un historique : copier titre, copier contenu, supprimer |
| **Sidebar rétractable** | Affiche ou masque la barre latérale d'historique d'un clic |
| **Déclenchement externe** | Répond aux requêtes envoyées par le bot Accueil via l'EventBus |

### Catégories d'articles

| Catégorie | Contenu |
|-----------|---------|
| **Guide des bots** | Documentation complète des 12 bots |
| **FAQ** | Questions fréquentes et solutions aux problèmes courants |
| **Tutoriels** | Guides pas à pas pour des tâches spécifiques |
| **Technique** | Détails techniques, formats supportés, API |

### Utilisation

1. **Depuis l'Accueil** : pose une question → l'Accueil te redirige vers l'Aide avec ta question
2. **Directement** : clique sur le bouton Aide dans le footer, tape ta recherche
3. **Historique** : clique sur une consultation passée pour revoir l'article

### Astuces

- Sois précis dans ta question pour de meilleurs résultats
- Consulte régulièrement les nouveaux articles pour découvrir des fonctionnalités
- La barre latérale te permet de retrouver rapidement un article consulté
