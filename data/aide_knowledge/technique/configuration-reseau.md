---
title: "Configuration — Page Réseau"
category: technique
keywords: ["configuration", "reseau", "réseau", "connexion", "port", "upnp", "obfuscation", "serveur", "bande passante", "limite", "reconnexion"]
---

## Configuration — Page Réseau

La page **Réseau** (accessible depuis **Optimiseur** → onglet **Réseau**) regroupe tous les paramètres de connexion au réseau Soulseek.

---

### Section Connexion

| Paramètre | Clé | Défaut | Description |
|-----------|-----|--------|-------------|
| **UPnP** | `reseau.upnp` | `False` | Active le port mapping automatique via UPnP (nécessite un routeur compatible) |
| **Port d'écoute** | `reseau.port_ecoute` | `60000` | Port TCP sur lequel l'application écoute les connexions entrantes |
| **Port obfusqué** | `reseau.port_obfusque` | `60001` | Port alternatif pour les connexions obfusquées |
| **Obfuscation P2P** | `reseau.obfuscation_p2p` | `False` | Active l'obfuscation des connexions peer-to-peer pour contourner les restrictions FAI |
| **Mode connexion peer** | `reseau.mode_connexion_peer` | `race` | Stratégie de connexion : `race` (rapide), `cautious` (prudent), `aggressive` (agressif) |
| **Mode erreur d'écoute** | `reseau.mode_erreur_ecoute` | `clear` | Comportement en cas d'erreur d'écoute : `clear` (effacer), `any` (n'importe quel), `all` (tous) |

**Conseil UPnP** : Active UPnP si tu as des difficultés à recevoir des connexions entrantes. Vérifie que UPnP est activé sur ton routeur.

**Conseil ports** : Utilise les ports par défaut sauf en cas de conflit avec d'autres applications. Évite les ports bien connus (1-1024).

**Conseil obfuscation** : Active l'obfuscation P2P si ton FAI limite le trafic peer-to-peer. Peut réduire légèrement la vitesse.

**Conseil mode peer** :
- `race` : équilibré, recommandé pour la plupart des utilisateurs
- `cautious` : connexions progressives, idéal si connexion instable
- `aggressive` : maximum de connexions simultanées, meilleure vitesse mais plus de ressources

---

### Section Limites

| Paramètre | Clé | Défaut | Description |
|-----------|-----|--------|-------------|
| **Limite upload** | `reseau.limite_upload_kbps` | `0` | Limite la vitesse d'upload (kbps). `0` = illimité |
| **Limite download** | `reseau.limite_download_kbps` | `0` | Limite la vitesse de download (kbps). `0` = illimité |

**Conseil** : Si tu as une connexion limitée, définis des limites pour éviter de saturer ta bande passante. Par exemple : limite download à 80% de ton débit max.

---

### Section Reconnexion

| Paramètre | Clé | Défaut | Description |
|-----------|-----|--------|-------------|
| **Reconnexion automatique** | `reseau.reconnexion_auto` | `False` | Tente de se reconnecter automatiquement après une déconnexion |
| **Délai de reconnexion** | `reseau.reconnexion_timeout` | `10` | Temps d'attente (secondes) avant de tenter une reconnexion |

**Conseil** : Active la reconnexion automatique si ta connexion est instable. Un délai de 10-30 secondes évite les tentatives trop rapprochées.

---

### Section Serveur

| Paramètre | Clé | Défaut | Description |
|-----------|-----|--------|-------------|
| **Hôte du serveur** | `reseau.hote_serveur` | `server.slsknet.org` | Adresse du serveur Soulseek central |
| **Port du serveur** | `reseau.port_serveur` | `2416` | Port du serveur Soulseek central |

**Attention** : Ne modifie ces paramètres que si tu utilises un serveur alternatif. Les valeurs par défaut sont celles du réseau officiel Soulseek.

---

### Section UPnP avancé

| Paramètre | Clé | Défaut | Description |
|-----------|-----|--------|-------------|
| **Durée de bail** | `reseau.duree_bail_upnp` | `21600` | Durée (secondes) du bail UPnP (6h par défaut) |
| **Intervalle de vérification** | `reseau.intervalle_upnp` | `600` | Fréquence (secondes) de vérification du bail UPnP (10min par défaut) |
| **Timeout de découverte** | `reseau.timeout_upnp` | `10` | Timeout (secondes) pour la découverte UPnP |

**Conseil** : Ces paramètres avancés sont à laisser par défaut sauf si tu rencontres des problèmes spécifiques avec UPnP.
