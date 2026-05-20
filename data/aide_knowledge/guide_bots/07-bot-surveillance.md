---
title: "Bot Surveillance — Guide complet"
category: guide_bots
keywords: ["surveillance", "watcher", "événement", "alerte", "log", "flux", "temps réel"]
---

## Bot Surveillance

Le **bot Surveillance** est le watcher centralisé de l'application. Il affiche un flux d'événements en temps réel (connexion, transferts, erreurs, etc.) avec historique SQLite, filtres, et alertes.

### Interface

- **Flux d'événements** : défilement continu des événements en temps réel
- **Filtres** : filtre par catégorie (réseau, transfert, recherche, etc.) et par sévérité
- **Badges** : compteur d'événements dans le footer (visibles depuis n'importe quelle page)
- **Barre de recherche** : cherche dans l'historique des événements

### Catégories d'événements

| Catégorie | Description |
|-----------|-------------|
| **Réseau** | Connexion, déconnexion, erreurs réseau |
| **Transfert** | Téléchargements, uploads, files d'attente |
| **Recherche** | Résultats de recherche, timeouts |
| **Bibliothèque** | Modifications de la bibliothèque partagée |
| **Configuration** | Changements de paramètres |
| **Erreur** | Toutes les erreurs système |
| **Bot** | Événements générés par les bots |
| **Wishlist** | Résultats de souhaits |
| **Optimiseur** | Application de profils |
| **Aide** | Requêtes d'aide traitées |

### Sévérités

- **INFO** : Informations générales (connexion réussie, recherche terminée)
- **WARN** : Avertissements (tentative échouée, timeout dépassé)
- **ERROR** : Erreurs (échec de connexion, fichier introuvable)

### Historique

- Stocké dans une base SQLite (`data/bot_surveillance.db`)
- Conservation : 7 jours (purge automatique)
- Requêtable : cherche des événements passés

### Astuces

- Utilise les filtres pour ne voir que ce qui t'intéresse
- Le badge dans le footer te montre le nombre d'événements non lus
- Les toasts apparaissent même quand tu n'es pas sur la page Surveillance
