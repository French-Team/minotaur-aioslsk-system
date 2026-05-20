---
title: "Outils de diagnostic — Utiliser le debug et les journaux"
category: faq
keywords: ["debug", "diagnostic", "journal", "log", "depannage", "dépannage", "ip", "connexion", "erreur", "probleme", "problème"]
---

## Outils de diagnostic — Utiliser le debug et les journaux

### Activer la journalisation des connexions

Pour diagnostiquer des problèmes de connexion récurrents :

1. Va dans **Optimiseur** → onglet **Debug**
2. Active **Journaliser le nombre de connexions**
3. Va dans le bot **Surveillance**
4. Filtre par catégorie **Réseau**
5. Observe les logs : tu vois le nombre de connexions actives évoluer

**Quand l'utiliser ?**
- Connexions instables qui tombent régulièrement
- Impossible de savoir si tu es bien connecté
- Après modification des paramètres réseau (pour vérifier l'effet)

**Pense à le désactiver** après le diagnostic pour éviter de surcharger les logs.

### Que faire en cas d'erreur ?

Quand une erreur apparaît :

1. Va dans **Surveillance** → filtre par sévérité **ERROR**
2. Lis le message d'erreur exact
3. Cherche des patterns (même erreur à répétition)
4. Note l'heure de l'erreur et ce que tu faisais à ce moment

### Forcer une IP spécifique (IP overrides)

Cette option est utile dans des cas très spécifiques :
- Un utilisateur change souvent d'adresse IP
- Tu veux contourner un blocage réseau ponctuel
- Test de connexion avec un utilisateur spécifique

**Format** : `{"nom_utilisateur": "192.168.1.100"}` (format JSON)

⚠️ **Attention** : Une mauvaise configuration peut empêcher la connexion à l'utilisateur ciblé.

### Vérifier l'intégrité des fichiers partagés

Active **Search for parent** dans Debug si :
- Les chemins de fichiers dans la bibliothèque semblent incorrects
- Des fichiers partagés n'apparaissent pas dans le browse des autres utilisateurs

À désactiver après vérification.

### Réinitialiser la configuration

En dernier recours, tu peux réinitialiser tous les paramètres :

1. Va dans n'importe quelle page de configuration
2. Clique sur **Réinitialiser la configuration**
3. Confirme la réinitialisation
4. Tous les paramètres reviennent à leurs valeurs par défaut

⚠️ Cela ne supprime pas tes fichiers, seulement les paramètres de l'application.

### Processus de diagnostic complet

1. **Identifier le problème** : quoi, quand, depuis combien de temps ?
2. **Activer les outils** : journalisation des connexions dans Debug
3. **Observer les logs** : dans Surveillance, filtre par catégorie pertinente
4. **Corriger** : modifie les paramètres concernés
5. **Vérifier** : confirme que le problème est résolu
6. **Désactiver** : éteint les outils de debug pour économiser les ressources
