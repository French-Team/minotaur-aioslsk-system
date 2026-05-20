---
title: "Configuration — Page Recherche"
category: technique
keywords: ["configuration", "recherche", "resultat", "résultat", "timeout", "souhait", "memoire", "mémoire", "stockage"]
---

## Configuration — Page Recherche

La page **Recherche** (accessible depuis **Optimiseur** → onglet **Recherche**) permet de configurer le comportement du moteur de recherche Soulseek.

---

### Section Résultats

| Paramètre | Clé | Défaut | Description |
|-----------|-----|--------|-------------|
| **Nombre max de résultats** | `recherche.nb_resultats_max` | `100` | Nombre maximum de résultats affichés dans le tableau avant FIFO |
| **Stockage mémoire max** | `recherche.nb_max_memoire` | `500` | Nombre maximum de résultats conservés en mémoire pour le filtrage et le tri |

**Conseil nb_resultats_max** :
- `50` : usage léger, économise la mémoire
- `100` : équilibré (recommandé)
- `200` : recherche intensive, plus de résultats mais plus de ressources

**Conseil nb_max_memoire** : Toujours supérieur à `nb_resultats_max`. La mémoire permet de filtrer/trier avant d'afficher.

---

### Section Envoi

| Paramètre | Clé | Défaut | Description |
|-----------|-----|--------|-------------|
| **Stocker les résultats** | `recherche.stocker_resultats` | `True` | Sauvegarde les résultats de recherche dans la base de données pour consultation ultérieure |
| **Timeout des requêtes** | `recherche.timeout_requete` | `0` | Durée max (secondes) avant arrêt d'une recherche. `0` = désactivé (timeout géré par l'UI à 30s) |
| **Timeout des souhaits** | `recherche.timeout_souhaits` | `-1` | Durée max (secondes) pour les recherches Wishlist. `-1` = désactivé |

**Conseil stockage** : Laisse activé pour pouvoir consulter l'historique des résultats dans le bot Recherche. Désactive si la base de données devient trop volumineuse.

**Conseil timeout requête** : Le timeout UI est de 30 secondes (les résultats continuent en arrière-plan). Un timeout serveur supplémentaire peut être défini ici pour libérer des ressources plus tôt.

---

### Section Souhaits

| Paramètre | Clé | Défaut | Description |
|-----------|-----|--------|-------------|
| **Requêtes de souhaits** | `recherche.souhaits` | `""` | Liste des souhaits (séparés par des virgules) pour la recherche automatique |

**Conseil** : Cette liste est utilisée par le Planificateur pour les actions de type "Recherche Wishlist". Utilise le bot **Wishlist** pour une gestion plus visuelle des souhaits.
