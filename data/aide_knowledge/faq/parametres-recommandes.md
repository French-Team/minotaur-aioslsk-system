---
title: "Paramètres recommandés pour des performances optimales"
category: faq
keywords: ["paramètre", "recommandation", "performance", "optimiser", "conseil", "vitesse", "configuration", "reglage", "réglage"]
---

## Paramètres recommandés pour des performances optimales

### Connexion standard (ADSL/VDSL, 10-30 Mbps)

| Paramètre | Valeur | Page |
|-----------|--------|------|
| Mode connexion peer | `race` (équilibré) | Réseau |
| Limite upload | `0` (illimité) | Réseau |
| Limite download | `0` (illimité) | Réseau |
| Slots upload | `2` (recommandé) | Téléchargement |
| Résultats max | `100` | Recherche |
| UPnP | Activé | Réseau |

### Connexion fibre (100+ Mbps)

| Paramètre | Valeur | Page |
|-----------|--------|------|
| Mode connexion peer | `aggressive` | Réseau |
| Limite upload | `0` (illimité) | Réseau |
| Limite download | `0` (illimité) | Réseau |
| Slots upload | `5-10` | Téléchargement |
| Résultats max | `200` | Recherche |
| UPnP | Activé | Réseau |

### Connexion limitée ou mobile

| Paramètre | Valeur | Page |
|-----------|--------|------|
| Mode connexion peer | `cautious` | Réseau |
| Limite upload | `50-100` kbps | Réseau |
| Limite download | `200-500` kbps | Réseau |
| Slots upload | `1` | Téléchargement |
| Résultats max | `50` | Recherche |
| Scan au démarrage | Désactivé | Général |

### Configuration générale recommandée

**Démarrage** :
- Connexion automatique : **Activé** (gain de temps quotidien)
- Scan au démarrage : **Activé** (sauf si bibliothèque très volumineuse)

**Recherche** :
- Timeout requête : `0` (laissé à l'UI, 30s)
- Stocker résultats : **Activé** (pour retrouver l'historique)

**Téléchargement** :
- Intervalle rapport : `250` ms (fluide sans surcharge CPU)

**Salons** :
- Auto-join : **Activé** (rejoins tes salons favoris automatiquement)
- Invitations privées : **Activé** (ne rate aucune invitation)

### Appliquer les réglages en un clic

Va dans **Optimiseur** et choisis un profil prédéfini :

| Profil | Pour qui ? |
|--------|------------|
| **Performance** | Connexion fibre, utilisation intensive |
| **Économie** | Connexion limitée, usage modéré |
| **Recherche** | Optimisé pour la recherche de fichiers rares |

Chaque profil applique automatiquement les paramètres adaptés à ton usage.
