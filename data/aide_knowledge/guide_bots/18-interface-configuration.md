---
title: "Interface de configuration : onglets Réseau, Recherche, Téléchargement"
category: guide_bots
tags:
  - configuration
  - parametres
  - reseau
  - recherche
  - telechargement
keywords:
  - interface configuration parametres
  - interface configuration paramètres
  - configuration onglet reseau
  - configuration onglet réseau
  - configuration onglet recherche
  - configuration onglet telechargement
  - configuration onglet téléchargement
  - ConfigPage onglets parametres
  - ConfigPage onglets paramètres
  - ConfigSection section options
  - ConfigToggle interrupteur checkbox
  - ConfigEntry champ texte
  - ConfigCombo menu deroulant
  - ConfigCombo menu déroulant
  - ConfigSpin champ numerique
  - ConfigSpin champ numérique
  - ConfigFilePicker fichier dialogue
  - ConfigDirectoryPicker dossier dialogue
  - ConfigResetBtn reinitialisation
  - ConfigResetBtn réinitialisation
  - centre zone configuration
  - _build_config_pages construction
  - centre py configuration pages
  - onglet General demarrage profil
  - onglet Général démarrage profil
  - reseau upnp port mapping
  - réseau upnp port mapping
  - reseau port ecoute 60000
  - reseau port écoute 60000
  - reseau port obfusque 60001
  - reseau port obfusqué 60001
  - reseau obfuscation p2p
  - reseau mode connexion peer race fallback
  - reseau mode connexion pair
  - reseau mode erreur ecoute clear any all
  - reseau mode erreur écoute
  - reseau limite upload kbps
  - reseau limite download kbps
  - reseau reconnexion auto delai
  - reseau reconnexion automatique délai
  - reseau serveur hote port
  - reseau serveur hôte port
  - reseau upnp avance bail verification timeout
  - reseau upnp avancé bail vérification timeout
  - recherche nb resultats max memoire
  - recherche stocker resultats timeout requete souhaits
  - recherche stocker résultats timeout requête souhaits
  - telechargement slots upload simultanes
  - telechargement slots upload simultanés
  - telechargement dossier destination
  - telechargement intervalle rapport ms
  - telechargement intervalle rapport millisecondes
  - app config cle configuration
  - app_config clé configuration
  - general scan on start connexion automatique
  - general description photo profil
  - general interets aimes detestes
  - general intérêts aimés détestés
  - utilisateurs liste amis bloques
  - utilisateurs liste amis bloqués
  - partages dossier chemin mode utilisateurs
  - partages dossier chemin mode utilisateurs autorises
  - partages dossier chemin mode utilisateurs autorisés
  - salons auto join invitations privees favoris
  - salons auto join invitations privées favoris
  - debug options debogage
  - debug options débogage
  - 8 onglets configuration parametres
  - 8 onglets configuration paramètres
  - centre zone stack pages config
---

# Interface de Configuration

## Vue d'ensemble

L'interface de configuration centralise tous les paramètres de l'application dans **8 onglets** accessibles depuis la zone centrale. Chaque onglet est une instance de `ConfigPage` (définie dans `src/gui/widgets/config.py`), construite dans `src/gui/layout/center.py` via la méthode `_build_config_pages()`.

```
┌──────────────────────────────────────────────────────┐
│  [Général] [Réseau] [Recherche] [Téléchargement]     │
│  [Utilisateurs] [Partages] [Salons] [Debug]          │
├──────────────────────────────────────────────────────┤
│                                                       │
│   ┌─ ConfigSection "Connexion" ──────────────────┐   │
│   │  UPnP                          [✓ Activer]   │   │
│   │  Port d'écoute                 [ 60000  ]    │   │
│   │  Port obfusqué                 [ 60001  ]    │   │
│   │  Obfuscation P2P               [✓ Activer]   │   │
│   │  Mode connexion peer           [ RACE   ▼]   │   │
│   │  Mode erreur d'écoute          [ Clear  ▼]   │   │
│   └──────────────────────────────────────────────┘   │
│                                                       │
│   ┌─ ConfigSection "Limites" ────────────────────┐   │
│   │  Limite upload (Kbps)       [ 0 (aucune) ]   │   │
│   │  Limite download (Kbps)     [ 0 (aucune) ]   │   │
│   └──────────────────────────────────────────────┘   │
│                                                       │
│   ┌─ ConfigSection "Reconnexion" ────────────────┐   │
│   │  Reconnexion automatique       [✓ Activer]   │   │
│   │  Délai de reconnexion (s)      [ 5       ]   │   │
│   └──────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

### Architecture des widgets

| Widget | Usage | Héritage |
|--------|-------|----------|
| `ConfigPage` | Onglet complet avec titre + `QScrollArea` | `QFrame` |
| `ConfigSection` | Groupe d'options avec titre et séparateur | `QFrame` |
| `ConfigToggle` | Interrupteur marche/arrêt (`QCheckBox`) | `QFrame` |
| `ConfigEntry` | Champ texte libre (`QLineEdit`) | `QFrame` |
| `ConfigCombo` | Menu déroulant (`QComboBox`) | `QFrame` |
| `ConfigSpin` | Champ numérique (`QSpinBox`) | `QFrame` |
| `ConfigFilePicker` | Sélecteur de fichier avec dialogue natif | `QFrame` |
| `ConfigDirectoryPicker` | Sélecteur de dossier avec dialogue natif | `QFrame` |
| `ConfigResetBtn` | Bouton réinitialisation avec confirmation | `QPushButton` |

### Persistance automatique

Chaque widget de configuration est lié à une **clé de configuration** (`config_key`) dans le format `categorie.champ` (ex: `reseau.port_ecoute`, `recherche.nb_resultats_max`). Les modifications sont automatiquement persistées via le module `src.services.app_config`.

---

## 1. Onglet Réseau

Paramètres de connexion au réseau Soulseek — couvre la connectivité P2P, les ports, la bande passante et la reconnexion.

### Section Connexion

| Champ | Widget | Clé config | Défaut | Description |
|-------|--------|------------|--------|-------------|
| **UPnP** | `ConfigToggle` | `reseau.upnp` | Activé | Port mapping automatique via UPnP |
| **Port d'écoute** | `ConfigSpin` | `reseau.port_ecoute` | 60000 | Port pour connexions entrantes P2P (1024-65535) |
| **Port obfusqué** | `ConfigSpin` | `reseau.port_obfusque` | 60001 | Port alternatif pour contourner restrictions FAI (1024-65535) |
| **Obfuscation P2P** | `ConfigToggle` | `reseau.obfuscation_p2p` | Activé | Obfusque le trafic P2P pour éviter le throttling FAI |
| **Mode connexion peer** | `ConfigCombo` | `reseau.mode_connexion_peer` | `RACE` | Stratégie de connexion (`RACE` / `FALLBACK`) |
| **Mode erreur écoute** | `ConfigCombo` | `reseau.mode_erreur_ecoute` | `Clear` | Comportement en cas d'erreur (`Clear` / `Any` / `All`) |

### Section Limites

| Champ | Widget | Clé config | Défaut | Description |
|-------|--------|------------|--------|-------------|
| **Limite upload (Kbps)** | `ConfigSpin` | `reseau.limite_upload_kbps` | 0 (aucune) | Bande passante montante max (0-100000) |
| **Limite download (Kbps)** | `ConfigSpin` | `reseau.limite_download_kbps` | 0 (aucune) | Bande passante descendante max (0-100000) |

### Section Reconnexion

| Champ | Widget | Clé config | Défaut | Description |
|-------|--------|------------|--------|-------------|
| **Reconnexion automatique** | `ConfigToggle` | `reseau.reconnexion_auto` | Activé | Reconnexion automatique après déconnexion |
| **Délai de reconnexion (s)** | `ConfigSpin` | `reseau.reconnexion_timeout` | 5 s | Temps d'attente avant reconnexion (1-300 s) |

### Section Serveur

| Champ | Widget | Clé config | Défaut | Description |
|-------|--------|------------|--------|-------------|
| **Hôte du serveur** | `ConfigEntry` | `reseau.hote_serveur` | `server.slsknet.org` | Adresse du serveur central Soulseek |
| **Port du serveur** | `ConfigSpin` | `reseau.port_serveur` | 2416 | Port du serveur central (1-65535) |

> ⚠️ **Attention** : La modification du serveur peut empêcher la connexion au réseau Soulseek. Réservé aux utilisateurs avancés.

### Section UPnP avancé

| Champ | Widget | Clé config | Défaut | Description |
|-------|--------|------------|--------|-------------|
| **Durée du bail (s)** | `ConfigSpin` | `reseau.duree_bail_upnp` | 21600 s | Durée de vie du port mapping UPnP (300-86400, pas 60) |
| **Intervalle vérification (s)** | `ConfigSpin` | `reseau.intervalle_upnp` | 600 s | Fréquence de vérification du mapping (30-3600, pas 10) |
| **Timeout découverte (s)** | `ConfigSpin` | `reseau.timeout_upnp` | 10 s | Timeout pour la découverte UPnP (1-60) |

---

## 2. Onglet Recherche

Paramètres de recherche de fichiers sur le réseau Soulseek.

### Section Résultats

| Champ | Widget | Clé config | Défaut | Description |
|-------|--------|------------|--------|-------------|
| **Nombre max de résultats** | `ConfigSpin` | `recherche.nb_resultats_max` | 100 | Nombre max de résultats affichés par recherche |
| **Stockage mémoire max** | `ConfigSpin` | `recherche.nb_max_memoire` | 500 | Nombre max de résultats conservés en mémoire |

### Section Envoi

| Champ | Widget | Clé config | Défaut | Description |
|-------|--------|------------|--------|-------------|
| **Stocker les résultats** | `ConfigToggle` | `recherche.stocker_resultats` | Activé | Conserver les résultats après fermeture de la recherche |
| **Timeout des requêtes (s)** | `ConfigSpin` | `recherche.timeout_requete` | 15 s | Délai max d'attente des résultats de recherche |
| **Timeout des souhaits (s)** | `ConfigSpin` | `recherche.timeout_souhaits` | 300 s | Délai max d'attente pour les souhaits (5 min) |

### Section Souhaits

| Champ | Widget | Clé config | Défaut | Description |
|-------|--------|------------|--------|-------------|
| **Requêtes de souhaits** | `ConfigEntry` | `recherche.souhaits` | (vide) | Termes de recherche automatique pour les souhaits (séparés par des virgules) |

> 💡 **Astuce** : Les souhaits sont des recherches automatiques lancées périodiquement. Utilisez cette section pour surveiller des fichiers spécifiques.

---

## 3. Onglet Téléchargement

Paramètres de gestion des téléchargements et des uploads.

### Section Limites

| Champ | Widget | Clé config | Défaut | Description |
|-------|--------|------------|--------|-------------|
| **Slots d'upload simultanés** | `ConfigSpin` | `telechargement.slots_upload` | 5 | Nombre max de téléchargements sortants simultanés (1-100) |

### Section Destination

| Champ | Widget | Clé config | Défaut | Description |
|-------|--------|------------|--------|-------------|
| **Dossier de destination** | `ConfigDirectoryPicker` | `telechargement.dossier_destination` | Dossier par défaut Soulseek | Dossier où les fichiers téléchargés sont sauvegardés |

### Section Rapport

| Champ | Widget | Clé config | Défaut | Description |
|-------|--------|------------|--------|-------------|
| **Intervalle de rapport (ms)** | `ConfigSpin` | `telechargement.intervalle_rapport` | 400 ms | Fréquence des rapports de progression (50-10000 ms) |

> 💡 **Astuce** : Un intervalle plus bas (100-200 ms) donne des mises à jour plus fluides mais consomme plus de CPU. 400 ms est un bon compromis.

---

## 4. Autres onglets (aperçu)

### Général

| Section | Champs |
|---------|--------|
| **Démarrage** | Scanner les partages au démarrage (`general.scan_on_start`), Connexion automatique (`general.connexion_automatique`) |
| **Profil** | Description (`general.description_profil`), Photo de profil (`general.photo_profil`) |
| **Centres d'intérêt** | J'aime (`general.interets_aimes`), Je n'aime pas (`general.interets_detestes`) |

### Utilisateurs

| Section | Champs |
|---------|--------|
| **Amis** | Liste d'amis (`utilisateurs.liste_amis`) — noms séparés par des virgules |
| **Bloqués** | Utilisateurs bloqués (`utilisateurs.liste_bloques`) — noms séparés par des virgules |

### Partages

| Section | Champs (x2 dossiers) |
|---------|----------------------|
| **Dossier 1 / 2** | Chemin (`partages.dossier_X_chemin`), Mode (`partages.dossier_X_mode` : Tout le monde / Amis uniquement / Utilisateurs), Utilisateurs autorisés (`partages.dossier_X_utilisateurs`) |

### Salons

| Champ | Widget | Clé config |
|-------|--------|------------|
| Rejoindre les salons auto. | `ConfigToggle` | `salons.auto_join` |
| Accepter invitations privées | `ConfigToggle` | `salons.invitations_privees` |
| Salons favoris | `ConfigEntry` | `salons.favoris` |

### Debug

| Champ | Widget | Clé config |
|-------|--------|------------|
| Options de débogage | `ConfigToggle` | `debug.search_for_parent` |

---

## 5. Fonctionnalités avancées

### Profils de configuration

La méthode `ConfigPage.applique_profile(data)` permet d'appliquer un ensemble de paramètres en masse :

```python
# Exemple : appliquer un profil "Haute performance"
page.applique_profile({
    "recherche.nb_resultats_max": 200,
    "telechargement.slots_upload": 10,
    "reseau.limite_upload_kbps": 5000,
})
```

### Réinitialisation

Le `ConfigResetBtn` (présent dans certains onglets) permet de réinitialiser tous les paramètres de la page à leurs valeurs par défaut, avec une confirmation via `QMessageBox`.

### Navigation rapide

- **Onglet Réseau** : Configuration réseau complète (connectivité, bande passante, UPnP)
- **Onglet Recherche** : Paramètres de recherche (résultats, timeouts, souhaits)
- **Onglet Téléchargement** : Gestion des transferts (slots, dossier, rapport)

### Accès

1. Cliquez sur l'icône ⚙️ **Configuration** dans la barre d'outils
2. Sélectionnez l'onglet souhaité
