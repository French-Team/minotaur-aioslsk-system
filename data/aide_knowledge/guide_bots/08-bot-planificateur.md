---
title: "Bot Planificateur — Guide complet"
category: guide_bots
keywords: ["planificateur", "planifier", "tâche", "programmer", "horaire", "automatique", "action"]
---

## Bot Planificateur

Le **bot Planificateur** permet de créer et gérer des actions planifiées. C'est le cerveau de l'automatisation : tu définis une action et son horaire, et l'application l'exécute automatiquement.

### Interface

- **Tableau de bord** : vue d'ensemble des actions planifiées avec leur statut
- **Barre d'actions rapides** : ajout, pause, reprise, suppression
- **Statistiques live** : nombre d'actions actives, en attente, terminées
- **Liste des actions** : tableau triable avec filtres

### Types d'actions

| Type | Description |
|------|-------------|
| **Recherche Wishlist** | Lance une recherche basée sur un souhait |
| **Surveillance** | Vérifie l'état du réseau et des connexions |
| **Nettoyage** | Supprime les fichiers temporaires ou obsolètes |
| **Rapport** | Génère un rapport d'activité |
| **Personnalisée** | Action définie par l'utilisateur |

### Modes d'exécution

- **Immédiat** : l'action est exécutée tout de suite
- **Planifié** : l'action est exécutée à une date/heure définie
- **Récurrent** : répétition quotidienne, hebdomadaire, mensuelle

### Statuts

| Statut | Signification |
|--------|---------------|
| ✅ **Actif** | L'action est programmée et sera exécutée |
| ⏸️ **Pause** | L'action est suspendue temporairement |
| ⏳ **En attente** | L'action attend son tour d'exécution |
| 🏁 **Terminé** | L'action a été exécutée avec succès |
| ❌ **Erreur** | L'action a échoué |
| 🛑 **Annulé** | L'action a été annulée |

### Astuces

- Combine avec la Wishlist pour des recherches automatiques programmées
- Utilise le mode récurrent pour des tâches quotidiennes
- Vérifie les logs dans Surveillance pour le suivi des exécutions
