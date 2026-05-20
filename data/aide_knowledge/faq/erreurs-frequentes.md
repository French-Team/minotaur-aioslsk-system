---
title: "Erreurs fréquentes — Guide de dépannage"
category: faq
keywords: ["erreur", "bug", "plante", "crashe", "problème", "probleme", "panne", "dépannage", "depannage"]
---

## Erreurs fréquentes — Guide de dépannage

### 1. L'application ne démarre pas

- **Cause possible** : base de données corrompue ou verrouillée
- **Solution** : supprime les fichiers `.db-shm` et `.db-wal` dans le dossier `data/`
- **Solution avancée** : renomme le dossier `data/` en `data_backup/` et relance

### 2. PermissionError sur les fichiers DB

- **Cause** : un processus précédent n'a pas libéré la base de données
- **Solution** : ferme complètement l'application et relance
- **Solution Windows** : tue le processus Python dans le Gestionnaire de tâches

### 3. Le bot Accueil ne répond pas

- **Cause** : base de données d'historique verrouillée
- **Solution** : supprime `data/bot_accueil_history.json` (perte de l'historique de chat)
- **Prévention** : l'historique est sauvegardé après chaque message

### 4. Les résultats de recherche sont lents

- **Cause** : timeout trop court ou mode de connexion inadapté
- **Solution** : va dans l'Optimiseur → profil Performance
- **Solution manuelle** : augmente le timeout dans Configuration → Recherche

### 5. Les téléchargements restent en file d'attente

- **Cause** : l'utilisateur source n'a pas de slots libres
- **Solution** : cherche le même fichier chez d'autres utilisateurs
- **Solution** : active le mode "disponible" dans le bot Recherche

### 6. Impossible de démarrer une recherche

- **Cause** : l'application n'est pas connectée au réseau
- **Solution** : vérifie la connexion dans le header (icône en haut à gauche)
- **Solution** : va sur la page Connexion et reconnecte-toi
