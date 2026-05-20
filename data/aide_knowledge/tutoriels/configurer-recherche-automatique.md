---
title: "Configurer une recherche automatique"
category: tutoriels
keywords: ["recherche", "automatique", "planifier", "programmer", "wishlist", "surveillance"]
---

## Configurer une recherche automatique

Ce tutoriel explique comment mettre en place une recherche automatique pour surveiller de nouveaux fichiers sur le réseau.

### Étape 1 : Ajouter un mot-clé à la Wishlist

1. Va dans le bot **Wishlist** (depuis le footer)
2. Clique sur **Ajouter un souhait**
3. Entre ton mot-clé (ex: "album jazz 2024")
4. Configure la fréquence de vérification

### Étape 2 : Créer une action planifiée

1. Va dans le bot **Planificateur**
2. Clique sur **Nouvelle action**
3. Choisis le type **Recherche Wishlist**
4. Définis l'horaire (ex: tous les jours à 20h)
5. Sauvegarde

### Étape 3 : Surveiller les résultats

1. Va dans le bot **Surveillance**
2. Configure les notifications pour les nouveaux résultats Wishlist
3. Active les badges dans le footer pour voir le compteur
4. Reçois des toasts lorsqu'un nouvel élément correspondant est trouvé

### Étape 4 : Automatiser le téléchargement

1. Dans le bot **Ordonnanceur**, crée une règle
2. Condition : "Nouveau résultat Wishlist"
3. Action : "Télécharger automatiquement"
4. Active la règle

### Résultat

Une fois configuré, l'application :
- Recherche automatiquement sur le réseau aux horaires définis
- Télécharge les nouveaux fichiers correspondant à tes critères
- T'avertit des nouveaux téléchargements par toast
