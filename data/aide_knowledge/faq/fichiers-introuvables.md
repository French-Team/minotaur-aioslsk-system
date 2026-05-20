---
title: "Fichiers téléchargés introuvables — Où sont mes fichiers ?"
category: faq
keywords: ["fichier", "introuvable", "téléchargement", "telechargement", "dossier", "destination", "ou", "trouver", "enregistré", "download"]
---

## Fichiers téléchargés introuvables — Où sont mes fichiers ?

### Pourquoi je ne trouve pas mes fichiers ?

| Cause | Solution |
|-------|----------|
| Aucun dossier de destination configuré | Configure un dossier dans les paramètres Téléchargement |
| Le dossier par défaut est difficile à trouver | Change le dossier vers un emplacement connu |
| Le téléchargement est encore en cours | Vérifie la progression dans le bot Téléchargement |
| Le téléchargement a échoué | Regarde les erreurs dans le bot Surveillance |

### Configurer un dossier de destination

1. Va dans **Optimiseur** → onglet **Téléchargement**
2. Dans la section **Dossier**, clique sur **Parcourir**
3. Choisis un dossier facile d'accès (ex: `C:/Musique/`, `~/Downloads/Soulseek/`)
4. Le dossier est automatiquement sauvegardé

**Organisation recommandée** :
```
📁 Téléchargements Soulseek/
├── 🎵 Nouveautés/      (téléchargements récents à trier)
├── 🗂️ Classé/          (fichiers passés par l'Ordonnanceur)
└── 📦 Archives/         (fichiers plus anciens)
```

### Utiliser l'Ordonnanceur pour classer automatiquement

Après téléchargement, utilise le bot **Ordonnanceur** pour :

1. Lancer l'assistant en 4 étapes
2. Choisir les fichiers à organiser
3. Définir des règles : classement par artiste, album, genre ou année
4. Valider l'aperçu avant application

**Astuce** : Configure un dossier "incoming" comme destination des téléchargements, puis utilise l'Ordonnanceur périodiquement pour trier dans des sous-dossiers par artiste/album.

### Vérifier l'état du téléchargement

Si tu ne vois pas le fichier :
1. Va dans **Téléchargement** (footer)
2. Vérifie la colonne **Statut** : "Terminé" ou "En cours" ?
3. Si "Terminé" : le fichier est dans le dossier de destination
4. Si "En cours" : patiente, le fichier n'est pas encore complet
5. Si "Erreur" : cherche le fichier chez un autre utilisateur
