---
title: "Bot Clients Actifs — Guide complet"
category: guide_bots
keywords: ["clients", "actifs", "contacts", "utilisateurs", "statut", "connecté", "tableau"]
---

## Bot Clients Actifs

Le **bot Clients Actifs** affiche la liste des utilisateurs Soulseek avec lesquels tu interagis (downloads, uploads, browse). Il montre leur statut en temps réel.

### Interface

- **Tableau triable** : liste des utilisateurs avec colonnes configurables
- **Statut en temps réel** : connecté / déconnecté, slots libres, vitesse
- **Badge** : compteur de clients actifs dans le footer

### Informations affichées

| Colonne | Description |
|---------|-------------|
| **Utilisateur** | Nom d'utilisateur Soulseek |
| **Statut** | Connecté ou déconnecté |
| **Slots** | Nombre de slots libres / total |
| **Vitesse** | Vitesse de connexion de l'utilisateur |
| **Fichiers** | Nombre de fichiers partagés |
| **Dernière activité** | Date et heure de la dernière interaction |

### Fonctionnalités

- **Tri** : clique sur les en-têtes pour trier par colonne
- **Recherche** : cherche un utilisateur spécifique
- **Statut en direct** : mise à jour automatique via le service ClientsActifsService
- **Navigation** : clique sur un utilisateur pour voir sa bibliothèque

### Service

Le bot est connecté à un service dédié (`ClientsActifsService`) qui :
- Maintient la liste à jour automatiquement
- Détecte les connexions et déconnexions
- Met à jour les badges du footer

### Astuces

- Utilise le tri par slots pour trouver les utilisateurs disponibles
- Les badges t'informent des changements même quand tu n'es pas sur la page
- Le statut est mis à jour en temps réel sans rafraîchissement manuel
