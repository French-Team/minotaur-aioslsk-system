---
title: "Téléchargement lent — Causes et solutions"
category: faq
keywords: ["téléchargement", "lent", "vitesse", "slow", "queue", "file", "attente"]
---

## Téléchargement lent — Causes et solutions

### Pourquoi mon téléchargement est-il lent ?

Plusieurs facteurs peuvent ralentir un téléchargement sur Soulseek :

| Cause | Solution |
|-------|----------|
| **L'utilisateur n'a pas de slots libres** | Attends ou cherche le fichier chez un autre utilisateur |
| **Bande passante limitée** | Vérifie tes limites de vitesse dans l'Optimiseur |
| **Le fichier est rare** | Moins de sources = vitesse potentiellement plus faible |
| **Distance réseau** | Les utilisateurs loin géographiquement peuvent être plus lents |

### Comment améliorer la vitesse

1. **Utilise le mode dispo** dans le bot Recherche pour filtrer les utilisateurs avec slots libres
2. **Privilégie les fichiers avec plusieurs sources** (colonne DL)
3. **Vérifie tes limites** dans Configuration → Optimiseur → Téléchargements
4. **Évite les heures d'affluence** (soirée) quand le réseau est saturé

### Fonctionnement du téléchargement

- Le bot Téléchargement choisit automatiquement le meilleur pair (slots libres + meilleure vitesse)
- Les téléchargements s'ajoutent à une file d'attente
- Tu peux suivre la progression en temps réel dans le bot Téléchargement
