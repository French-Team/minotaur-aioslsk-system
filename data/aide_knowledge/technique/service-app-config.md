---
title: "Service AppConfig : stockage et gestion de la configuration"
category: technique
tags:
  - configuration
  - stockage
  - service
  - persistance
  - json
keywords:
  - app config service stockage
  - app config service get set reset
  - app config service get set reset dictionary
  - app config valeurs par defaut
  - app config valeurs par défaut
  - app config defaults toutes categories
  - _DEFAULTS dictionnaire complet
  - _DEFAULTS general reseau recherche
  - _DEFAULTS réseau recherche
  - _DEFAULTS telechargement utilisateurs partages salons debug
  - _DEFAULTS téléchargement utilisateurs partages salons debug
  - app_config.json fichier configuration
  - app_config.json persistence disque
  - app_config.json persisténce disque
  - ecriture atomique json .tmp replace
  - écriture atomique json .tmp replace
  - fichier temporaire ecriture atomique
  - fichier temporaire écriture atomique
  - _load lecture fichier fallback defaults
  - _load lecture fichier fallback défauts
  - _load fusion donnees chargees defaults
  - _load fusion données chargées defaults
  - _load erreur json fallback defaults logger warning
  - _save ecriture disque immediate
  - _save écriture disque immédiate
  - _write_file atomique tmp replace path
  - singleton _config lazy loading
  - lazy loading chargement differe
  - lazy loading chargement différé
  - get cle notation pointee
  - get clé notation pointée
  - get fallback config defaults default
  - get fallback config défauts default
  - set mise a jour memoire ecriture disque
  - set mise à jour mémoire écriture disque
  - set sauvegarde immediate
  - set sauvegarde immédiate
  - reset cle specifique ou total
  - reset clé spécifique ou total
  - reset restaure defaults sauvegarde
  - reset restaure défauts sauvegarde
  - dictionary copie dictionnaire courant
  - import app config patterns module fonction
  - utilisation app config soulseek client
  - utilisation app config connexion manager
  - utilisation app config widgets config
  - pattern cle categorie champ pointe
  - pattern clé catégorie champ pointée
  - 8 categories configuration dominees
  - 8 catégories configuration domaines
  - 171 lignes service configuration
  - 58 cles configuration total
  - 58 clés configuration total
---

# Service AppConfig : stockage et gestion de la configuration

## Vue d'ensemble

Le module `src/services/app_config.py` (171 lignes) est le **service central de persistance de la configuration** de l'application. Il expose une API simple de type dictionnaire clé-valeur avec notation pointée, stockée dans un fichier JSON et chargée paresseusement au premier accès.

```
┌─────────────────────────────────────────────────────────────┐
│                    Architecture AppConfig                     │
│                                                              │
│  ┌──────────────┐    API publique        ┌────────────────┐  │
│  │  centre.py   │ ◄───────────────────►  │ app_config     │  │
│  │  config.py   │    get/set/reset/      │ (singleton)    │  │
│  │  widgets     │    dictionary()        │                │  │
│  └──────────────┘                        │  _config: dict │  │
│                                          │  _DEFAULTS     │  │
│  ┌──────────────┐                        │                │  │
│  │  soulseek_   │ ◄── get()              │  _load()       │  │
│  │  client.py   │                        │  _save()       │  │
│  └──────────────┘                        │  _write_file() │  │
│                                          └───────┬────────┘  │
│  ┌──────────────┐                                │           │
│  │  connexion_  │ ◄── get() / set()              │           │
│  │  manager.py  │                                ▼           │
│  └──────────────┘                        ┌────────────────┐  │
│                                           │ app_config.json│  │
│  ┌──────────────┐                        │ (JSON, racine) │  │
│  │  autres      │ ◄── get()              └────────────────┘  │
│  │  modules     │                                             │
│  └──────────────┘                                             │
└─────────────────────────────────────────────────────────────┘
```

### Principe de fonctionnement

```
Premier accès à app_config.get() ou .set()
        │
        ▼
_ensure_loaded() → _config is None ?
        │
        ├── Oui → _load()
        │           ├── app_config.json existe ?
        │           │     ├── Oui → lire JSON + fusionner avec _DEFAULTS
        │           │     └── Non → créer fichier avec _DEFAULTS
        │           └── _config = dict fusionné
        │
        └── Non → utiliser _config existant
                │
                ▼
          Opération : get/set/reset/dictionary
```

---

## 1. Stockage : fichier JSON

### Emplacement

```python
_CONFIG_FILE = Path(__file__).resolve().parent.parent.parent / "app_config.json"
```

Le fichier est situé à la **racine du projet** :

```
free-buff-aioslsk/
├── app_config.json          ← Fichier de configuration (JSON, auto-généré)
├── src/
│   ├── services/
│   │   ├── app_config.py   ← Ce module (171 lignes)
│   │   └── ...
│   └── ...
└── ...
```

### Format

```json
{
    "general": {
        "scan_on_start": true,
        "description_profil": "",
        "photo_profil": "",
        "interets_aimes": "",
        "interets_detestes": "",
        "connexion_automatique": false
    },
    "reseau": {
        "nom_utilisateur": "",
        "mot_de_passe": "",
        "upnp": false,
        "port_ecoute": 60000,
        "port_obfusque": 60001,
        "obfuscation_p2p": false,
        "mode_connexion_peer": "race",
        "limite_upload_kbps": 0,
        "limite_download_kbps": 0,
        "reconnexion_auto": false,
        "reconnexion_timeout": 10,
        "hote_serveur": "server.slsknet.org",
        "port_serveur": 2416,
        "mode_erreur_ecoute": "clear",
        "duree_bail_upnp": 21600,
        "intervalle_upnp": 600,
        "timeout_upnp": 10
    },
    "recherche": {
        "nb_resultats_max": 100,
        "nb_max_memoire": 500,
        "stocker_resultats": true,
        "timeout_requete": 0,
        "timeout_souhaits": -1,
        "souhaits": ""
    },
    "telechargement": {
        "slots_upload": 2,
        "dossier_destination": "",
        "intervalle_rapport": 250
    },
    "utilisateurs": {
        "liste_amis": "",
        "liste_bloques": ""
    },
    "partages": {
        "dossier_1_chemin": "",
        "dossier_1_mode": "everyone",
        "dossier_1_utilisateurs": "",
        "dossier_2_chemin": "",
        "dossier_2_mode": "everyone",
        "dossier_2_utilisateurs": ""
    },
    "salons": {
        "auto_join": true,
        "invitations_privees": true,
        "favoris": ""
    },
    "debug": {
        "search_for_parent": false,
        "ip_overrides": "",
        "log_connection_count": false
    }
}
```

### Écriture atomique

```python
def _write_file(data: dict[str, Any]) -> None:
    """Écriture atomique : fichier .tmp → replace."""
    tmp = _CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(_CONFIG_FILE)
```

| Étape | Action | Pourquoi |
|-------|--------|----------|
| 1. Écrire `.tmp` | `json.dumps(data, indent=2)` dans `app_config.json.tmp` | Évite d'écrire directement dans le fichier cible |
| 2. Remplacer | `tmp.replace(_CONFIG_FILE)` | Remplacement atomique — pas de fichier corrompu si crash pendant l'écriture |

> 💡 **Pourquoi atomique ?** Si l'écriture JSON échoue à mi-parcours, le fichier `.tmp` est tronqué mais le fichier original reste intact. Le `replace()` est une opération atomique au niveau du système de fichiers.

---

## 2. API publique

### `get(key, default=None)`

```python
def get(key: str, default: Any = None) -> Any:
    _ensure_loaded()
    # Parcourt : 1) _config 2) _DEFAULTS 3) default
    categories = key.split(".")
    if len(categories) == 2:
        cat, attr = categories
        config_val = _config.get(cat, {}).get(attr)
        if config_val is not None:
            return config_val
        default_val = _DEFAULTS.get(cat, {}).get(attr)
        if default_val is not None:
            return default_val
    return default
```

**Ordre de résolution :**
1. **`_config`** (mémoire) — valeur chargée du fichier JSON
2. **`_DEFAULTS`** (dictionnaire statique) — valeur par défaut
3. **`default`** (paramètre) — valeur de repli fournie à l'appel

**Exemples d'appels dans le projet :**
```python
# Récupération avec fallback
port = app_config.get("reseau.port_ecoute", 60000)
auto_join = app_config.get("salons.auto_join", True)

# Les appelants ajoutent souvent leur propre typage
liste_amis = app_config.get("utilisateurs.liste_amis", "")
nb_resultats = int(app_config.get("recherche.nb_resultats_max", 100))
```

### `set(key, value)`

```python
def set(key: str, value: Any) -> None:
    _ensure_loaded()
    categories = key.split(".")
    if len(categories) == 2:
        cat, attr = categories
        if cat not in _config:
            _config[cat] = {}
        _config[cat][attr] = value
    _save()
```

**Caractéristiques :**
- Met à jour la valeur en mémoire (dans `_config`)
- **Sauvegarde immédiate** sur disque via `_save()`
- Si la catégorie n'existe pas encore dans `_config`, elle est créée

**Exemples :**
```python
# Depuis connexion_manager.py
app_config.set("utilisateurs.liste_bloques", "spammer, troll")

# Depuis les widgets ConfigToggle
app_config.set("reseau.upnp", True)

# Depuis le widget de connexion
from src.services.app_config import set as config_set
config_set("general.connexion_automatique", True)
```

### `reset(key=None)`

```python
def reset(key: str | None = None) -> None:
    _ensure_loaded()
    if key is None:
        # Réinitialisation complète : restaure _DEFAULTS
        _config.clear()
        _config.update(_DEFAULTS)
    else:
        # Réinitialisation d'une clé spécifique
        categories = key.split(".")
        if len(categories) == 2:
            cat, attr = categories
            if cat in _config and attr in _config[cat]:
                _config[cat][attr] = _DEFAULTS.get(cat, {}).get(attr)
    _save()
```

| Appel | Effet |
|-------|-------|
| `reset()` | Réinitialise **tous** les paramètres aux valeurs par défaut |
| `reset("reseau.port_ecoute")` | Réinitialise **uniquement** le port d'écoute à `60000` |

### `dictionary()`

```python
def dictionary() -> dict[str, Any]:
    _ensure_loaded()
    return dict(_config)
```

Retourne une **copie** du dictionnaire de configuration courant. Utile pour l'inspection, le débogage ou l'export.

---

## 3. Fonctions internes

### `_ensure_loaded()`

```python
def _ensure_loaded() -> dict[str, Any]:
    global _config
    if _config is None:
        _config = _load()
    return _config
```

**Lazy loading** : la configuration n'est chargée qu'au premier accès, ce qui évite des opérations d'E/S superflues au démarrage pour les modules qui n'ont pas besoin de config.

### `_load()`

```python
def _load() -> dict[str, Any]:
    if not _CONFIG_FILE.exists():
        _write_file(_DEFAULTS)
        logger.info("Fichier de configuration créé : %s", _CONFIG_FILE)
        return dict(_DEFAULTS)

    try:
        data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
        # Fusion avec les valeurs par défaut pour intégrer les nouvelles clés
        fusion = dict(_DEFAULTS)
        for cat, attrs in data.items():
            if cat in fusion and isinstance(attrs, dict):
                fusion[cat].update(attrs)
            else:
                fusion[cat] = attrs
        return fusion
    except (json.JSONDecodeError, KeyError) as exc:
        logger.warning("Erreur de lecture de la configuration: %s", exc)
        return dict(_DEFAULTS)
```

| Scénario | Comportement |
|----------|-------------|
| Fichier inexistant | Crée le fichier avec `_DEFAULTS`, retourne les valeurs par défaut |
| Fichier valide | Lit le JSON et fusionne avec `_DEFAULTS` pour capter les nouvelles clés |
| JSON invalide | Log un warning, retourne `_DEFAULTS` |

> **Fusion intelligente** : si une mise à jour de l'application ajoute de nouvelles clés dans `_DEFAULTS`, `_load()` les intègre automatiquement dans la configuration existante sans perdre les réglages actuels.

### `_save()`

```python
def _save() -> None:
    if _config is not None:
        try:
            _write_file(_config)
        except OSError as exc:
            logger.error("Erreur lors de la sauvegarde de la configuration: %s", exc)
```

### `_write_file(data)`

Écriture atomique via fichier temporaire (détaillée plus haut).

---

## 4. Dictionnaire `_DEFAULTS` complet

### Général

| Clé | Type | Défaut | Description |
|-----|------|--------|-------------|
| `general.scan_on_start` | `bool` | `True` | Scanner les partages au démarrage |
| `general.description_profil` | `str` | `""` | Description du profil utilisateur |
| `general.photo_profil` | `str` | `""` | Chemin de la photo de profil |
| `general.interets_aimes` | `str` | `""` | Centres d'intérêt (aimés) |
| `general.interets_detestes` | `str` | `""` | Centres d'intérêt (détestés) |
| `general.connexion_automatique` | `bool` | `False` | Connexion auto au démarrage |

### Réseau

| Clé | Type | Défaut | Description |
|-----|------|--------|-------------|
| `reseau.nom_utilisateur` | `str` | `""` | Nom d'utilisateur Soulseek |
| `reseau.mot_de_passe` | `str` | `""` | Mot de passe Soulseek |
| `reseau.upnp` | `bool` | `False` | Port mapping UPnP |
| `reseau.port_ecoute` | `int` | `60000` | Port d'écoute P2P |
| `reseau.port_obfusque` | `int` | `60001` | Port obfusqué |
| `reseau.obfuscation_p2p` | `bool` | `False` | Obfuscation du trafic P2P |
| `reseau.mode_connexion_peer` | `str` | `"race"` | Mode de connexion peer |
| `reseau.limite_upload_kbps` | `int` | `0` | Limite upload (0 = illimité) |
| `reseau.limite_download_kbps` | `int` | `0` | Limite download (0 = illimité) |
| `reseau.reconnexion_auto` | `bool` | `False` | Reconnexion automatique |
| `reseau.reconnexion_timeout` | `int` | `10` | Délai de reconnexion (s) |
| `reseau.hote_serveur` | `str` | `"server.slsknet.org"` | Hôte du serveur |
| `reseau.port_serveur` | `int` | `2416` | Port du serveur |
| `reseau.mode_erreur_ecoute` | `str` | `"clear"` | Mode d'erreur d'écoute |
| `reseau.duree_bail_upnp` | `int` | `21600` | Durée du bail UPnP (s) |
| `reseau.intervalle_upnp` | `int` | `600` | Intervalle vérification UPnP (s) |
| `reseau.timeout_upnp` | `int` | `10` | Timeout découverte UPnP (s) |

### Recherche

| Clé | Type | Défaut | Description |
|-----|------|--------|-------------|
| `recherche.nb_resultats_max` | `int` | `100` | Nombre max de résultats |
| `recherche.nb_max_memoire` | `int` | `500` | Stockage mémoire max |
| `recherche.stocker_resultats` | `bool` | `True` | Stocker les résultats |
| `recherche.timeout_requete` | `int` | `0` | Timeout des requêtes (s) |
| `recherche.timeout_souhaits` | `int` | `-1` | Timeout des souhaits (s) |
| `recherche.souhaits` | `str` | `""` | Requêtes de souhaits |

### Téléchargement

| Clé | Type | Défaut | Description |
|-----|------|--------|-------------|
| `telechargement.slots_upload` | `int` | `2` | Slots d'upload simultanés |
| `telechargement.dossier_destination` | `str` | `""` | Dossier de destination |
| `telechargement.intervalle_rapport` | `int` | `250` | Intervalle de rapport (ms) |

### Utilisateurs

| Clé | Type | Défaut | Description |
|-----|------|--------|-------------|
| `utilisateurs.liste_amis` | `str` | `""` | Liste d'amis (CSV) |
| `utilisateurs.liste_bloques` | `str` | `""` | Utilisateurs bloqués (CSV) |

### Partages

| Clé | Type | Défaut | Description |
|-----|------|--------|-------------|
| `partages.dossier_1_chemin` | `str` | `""` | Chemin dossier 1 |
| `partages.dossier_1_mode` | `str` | `"everyone"` | Mode dossier 1 |
| `partages.dossier_1_utilisateurs` | `str` | `""` | Utilisateurs autorisés dossier 1 |
| `partages.dossier_2_chemin` | `str` | `""` | Chemin dossier 2 |
| `partages.dossier_2_mode` | `str` | `"everyone"` | Mode dossier 2 |
| `partages.dossier_2_utilisateurs` | `str` | `""` | Utilisateurs autorisés dossier 2 |

### Salons

| Clé | Type | Défaut | Description |
|-----|------|--------|-------------|
| `salons.auto_join` | `bool` | `True` | Rejoindre salons automatiquement |
| `salons.invitations_privees` | `bool` | `True` | Accepter invitations privées |
| `salons.favoris` | `str` | `""` | Salons favoris (CSV) |

### Debug

| Clé | Type | Défaut | Description |
|-----|------|--------|-------------|
| `debug.search_for_parent` | `bool` | `False` | Rechercher un parent |
| `debug.ip_overrides` | `str` | `""` | Surcharges IP (JSON) |
| `debug.log_connection_count` | `bool` | `False` | Journaliser les connexions |

---

## 5. Patterns d'utilisation dans le projet

### Importation

```python
# Pattern 1 : importer le module
from src.services import app_config
app_config.get("reseau.port_ecoute")

# Pattern 2 : importer une fonction spécifique
from src.services.app_config import set as cfg_set
cfg_set("general.connexion_automatique", True)

# Pattern 3 : importer le module directement
import src.services.app_config as app_config
```

### Consommateurs principaux

| Module | API utilisée | Usage |
|--------|-------------|-------|
| `soulseek_client.py` | `get()` | Lecture de toutes les catégories à l'initialisation |
| `connexion_manager.py` | `get()` / `set()` | Blocage utilisateur + persistance |
| `config.py` (widgets) | `get()`/`set()` | Initialisation + persistance automatique |
| `center.py` | `get()` | Peuplement des champs de configuration |
| Divers bots | `get()` | Lecture de paramètres spécifiques |

### Flux type : modification par un widget ConfigToggle

```
1. Utilisateur clique sur ConfigToggle "UPnP"
2. ConfigToggle._on_toggled(True)
3.   → app_config.set("reseau.upnp", True)
4.     → _config["reseau"]["upnp"] = True   (mémoire)
5.     → _save()
6.       → _write_file(_config)
7.         → json.dumps → app_config.json.tmp
8.         → .tmp.replace(app_config.json)
```

---

## 6. Résumé technique

| Propriété | Valeur |
|-----------|--------|
| **Fichier** | `src/services/app_config.py` |
| **Lignes** | 171 |
| **Fichier de données** | `app_config.json` (racine du projet) |
| **Format** | JSON avec indentation 2 espaces |
| **Clés totales** | 58 (réparties dans 8 catégories) |
| **API publique** | 4 fonctions : `get`, `set`, `reset`, `dictionary` |
| **Fonctions internes** | 4 : `_ensure_loaded`, `_load`, `_save`, `_write_file` |
| **Pattern** | Singleton avec lazy loading et écriture atomique |
| **Typage** | Stockage JSON natif (bool, int, str) — pas de typage strict côté get() |
| **Fusion** | `_load()` fusionne données actuelles + `_DEFAULTS` pour compatibilité ascendante |
