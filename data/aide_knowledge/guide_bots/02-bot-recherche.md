---
title: "Bot Recherche — Guide complet"
category: guide_bots
keywords: ["recherche", "chercher", "fichier", "filtre", "résultat", "rechercher", "trouver"]
---

## Bot Recherche

Le **bot Recherche** permet de chercher des fichiers sur le réseau Soulseek. C'est l'outil principal pour trouver de la musique, des livres, des logiciels et tout type de fichier partagé.

### Modes de recherche

| Mode | Description |
|------|-------------|
| **Global** | Recherche sur tout le réseau Soulseek |
| **Par utilisateur** | Cherche dans la bibliothèque d'un utilisateur spécifique |
| **Par salon (room)** | Cherche dans un salon de discussion |

### Interface

- **Tableau de résultats** : 9 colonnes (Extension, Fichier, Taille, Bitrate, Durée, Utilisateur, Slots, Vitesse, DL)
- **Filtres** : Filtre modal avec badge indiquant le nombre de filtres actifs
- **Tri** : Tri par bitrate décroissant par défaut (clique sur les en-têtes pour changer)
- **Mode dispo** : Toggle pour voir uniquement les fichiers avec slots libres

### Filtres disponibles

- Extension (mp3, flac, ogg, etc.)
- Taille minimale et maximale
- Bitrate minimum
- Durée minimum
- Utilisateur spécifique

### Actions sur un résultat

- Clic droit → menu contextuel : Télécharger, Browse, Copier le nom, Bloquer l'utilisateur
- Double-clic → téléchargement rapide vers le meilleur pair disponible

### Astuces

- Minimum 2 caractères pour lancer une recherche
- Timeout à 30 secondes (les résultats continuent d'arriver en arrière-plan)
- 200 résultats max avec FIFO (les plus récents remplacent les plus anciens)
