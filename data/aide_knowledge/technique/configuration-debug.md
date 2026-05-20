---
title: "Configuration — Page Debug (Avancé)"
category: technique
keywords: ["configuration", "debug", "diagnostic", "ip", "journal", "log", "connexion", "avancé"]
---

## Configuration — Page Debug (Avancé)

La page **Debug** (accessible depuis **Optimiseur** → onglet **Debug**) contient des options de diagnostic réservées aux utilisateurs avancés.

---

### Paramètres

| Paramètre | Clé | Défaut | Description |
|-----------|-----|--------|-------------|
| **Search for parent** | `debug.search_for_parent` | `False` | Active la recherche du dossier parent pour les fichiers partagés (utile pour le débogage des chemins) |
| **IP overrides** | `debug.ip_overrides` | `""` | Surcharge d'adresses IP au format JSON (ex: `{"utilisateur": "1.2.3.4"}`) |
| **Journaliser le nombre de connexions** | `debug.log_connection_count` | `False` | Enregistre dans Surveillance le nombre de connexions actives à intervalle régulier |

---

### Utilisation

**Search for parent** :
Active cette option si tu rencontres des problèmes d'affichage des chemins de fichiers dans la bibliothèque. À désactiver après diagnostic.

**IP overrides** :
Permet de forcer une adresse IP pour un utilisateur spécifique. Utile si :
- Un utilisateur a une IP qui change fréquemment
- Tu veux contourner un blocage IP
- Format JSON : `{"nom_utilisateur": "adresse_ip"}`
**Attention** : une mauvaise configuration peut empêcher la connexion à l'utilisateur.

**Journaliser les connexions** :
- Active pour diagnostiquer des problèmes de connexion récurrents
- Les logs apparaissent dans le bot Surveillance (catégorie Réseau)
- Génère plus d'événements, à n'activer que temporairement
- Consulte les logs dans Surveillance → filtre "Réseau"

---

### Quand utiliser le Debug ?

- **Problème de connexion** : active la journalisation des connexions, consulte les logs
- **Problème de bibliothèque** : active "Search for parent", vérifie les chemins
- **Problème avec un utilisateur spécifique** : utilise IP overrides pour le diagnostiquer

N'oublie pas de désactiver ces options après le diagnostic pour économiser les ressources.
