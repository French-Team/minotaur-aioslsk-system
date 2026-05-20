---
title: "Dépistage par logs"
category: technique
keywords: ["log", "debug", "dépistage", "erreur", "trace", "diagnostic", "résoudre"]
---

## Dépistage par logs

### Où trouver les logs

Les événements système sont enregistrés dans la base de données **Surveillance** (`data/bot_surveillance.db`). Tu peux les consulter directement dans le bot **Surveillance** :

1. Va dans **Surveillance** (footer)
2. Utilise les filtres pour affiner par catégorie ou sévérité
3. Cherche un mot-clé précis dans la barre de recherche

### Comprendre les niveaux de log

| Niveau | Signification | Exemple |
|--------|---------------|---------|
| **INFO** | Information normale | "Connexion réussie", "Recherche terminée" |
| **WARN** | Avertissement | "Timeout dépassé", "Tentative échouée" |
| **ERROR** | Erreur critique | "Échec de connexion", "Base de données corrompue" |

### Catégories utiles pour le dépistage

| Catégorie | Quand l'utiliser |
|-----------|------------------|
| **Réseau** | Problèmes de connexion, déconnexions intempestives |
| **Transfert** | Téléchargements bloqués, échecs de transfert |
| **Erreur** | Tout type d'erreur système |
| **Configuration** | Problèmes après modification des paramètres |

### Scénarios de dépistage

#### Problème : "Je n'arrive pas à me connecter"

1. Filtre par catégorie → **Réseau**
2. Regarde les événements ERROR les plus récents
3. Note le message d'erreur exact (ex: "Connection refused", "Timeout")

#### Problème : "Un téléchargement échoue"

1. Filtre par catégorie → **Transfert** + sévérité → **ERROR**
2. Cherche le nom du fichier qui échoue
3. Vérifie la cause : utilisateur déconnecté, fichier introuvable, etc.

#### Problème : "L'application ralentit"

1. Vérifie le nombre d'événements WARN des dernières heures
2. Cherche des patterns répétés (même erreur plusieurs fois)
3. Nettoie l'historique si plus de 7 jours

### Logs avancés

Pour un diagnostic plus poussé, active les logs détaillés dans l'Optimiseur :

1. Va dans **Configuration** → section **Debug**
2. Active "Journaliser le nombre de connexions"
3. Les logs apparaîtront dans Surveillance avec plus de détails
