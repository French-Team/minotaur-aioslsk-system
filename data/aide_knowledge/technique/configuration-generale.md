---
title: "Configuration générale (Général) — démarrage, profil, centres d'intérêt et backend"
category: technique
keywords:
  - general
  - général
  - configuration
  - demarrage
  - démarrage
  - scan_on_start
  - connexion_automatique
  - auto_login
  - profil
  - description
  - photo
  - profile picture
  - picture
  - interets
  - intérêts
  - centres d'interet
  - centres d'intérêt
  - liked
  - hated
  - aimes
  - aimés
  - detestes
  - détestés
  - ConfigToggle
  - ConfigEntry
  - ConfigFilePicker
  - ConfigSection
  - ConfigPage
  - Optimiseur
  - paramètres
  - parametres
  - widget
  - _parse_interests
  - _read_profile_picture
  - UserInfoSettings
  - InterestsSettings
  - SharesSettings
  - app_config
  - soulseek_client
  - connexion_manager
  - main_window
  - settings
  - reseau
  - réseau
  - credentials
  - preferences
  - préférences
---

## Résumé

La page **Général** de l'Optimiseur regroupe les paramètres de base de l'application : comportement au démarrage, profil utilisateur visible sur le réseau Soulseek et centres d'intérêt. Cet article détaille les widgets UI et le backend (`soulseek_client.py`, `connexion_manager.py`, `_parse_interests`, `_read_profile_picture`, `UserInfoSettings`, `InterestsSettings`).

```
┌─────────────────────────────────────────────────────────────────┐
│                     Optimiseur → Général                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─ Démarrage ───────────────────────────────────────────────┐  │
│  │  ConfigToggle  « general.scan_on_start »                   │  │
│  │  ConfigToggle  « general.connexion_automatique »           │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌─ Profil ──────────────────────────────────────────────────┐  │
│  │  ConfigEntry      « general.description_profil »           │  │
│  │  ConfigFilePicker « general.photo_profil »                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌─ Centres d'intérêt ───────────────────────────────────────┐  │
│  │  ConfigEntry « general.interets_aimes »                     │  │
│  │  ConfigEntry « general.interets_detestes »                  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    app_config.json (persistance)
                              │
                              ▼
                 soulseek_client.py (lecture startup)
                              │
                              ├── SharesSettings(scan_on_start)
                              ├── UserInfoSettings(description, picture)
                              └── InterestsSettings(liked, hated)
```

---

## 1. Fichiers sources

| Fichier | Rôle |
|---------|------|
| `src/gui/layout/center.py` | Construction de la `ConfigPage("Général")` (lignes ~345-430) |
| `src/services/soulseek_client.py` | Lecture et application des paramètres (lignes 232-236, 285-291, 328-329) |
| `src/services/connexion_manager.py` | `auto_login()` lit `general.connexion_automatique` (lignes 369-393) |
| `src/gui/main_window.py` | Vérifie `general.connexion_automatique` au démarrage (ligne 341) |
| `src/services/app_config.py` | Persistance des clés `general.*` dans `app_config.json` |

---

## 2. Interface utilisateur (widgets)

La page **Général** est construite dans `center.py` avec 3 sections.

### 2.1 Section Démarrage

| Widget | Label | Config key | Description |
|--------|-------|------------|-------------|
| `ConfigToggle` | Scanner les partages au démarrage | `general.scan_on_start` | Analyse les dossiers partagés au lancement (défaut: `True`) |
| `ConfigToggle` | Connexion automatique | `general.connexion_automatique` | Connecte automatiquement au serveur au démarrage (défaut: `False`) |

### 2.2 Section Profil

| Widget | Label | Config key | Placeholder |
|--------|-------|------------|-------------|
| `ConfigEntry` | Description | `general.description_profil` | « Présentez-vous aux autres utilisateurs Soulseek… » |
| `ConfigFilePicker` | Photo de profil | `general.photo_profil` | « Aucune image sélectionnée » |

### 2.3 Section Centres d'intérêt

| Widget | Label | Config key | Placeholder |
|--------|-------|------------|-------------|
| `ConfigEntry` | J'aime | `general.interets_aimes` | « Ex: Rock, Jazz, Soulseek, Production musicale… » |
| `ConfigEntry` | Je n'aime pas | `general.interets_detestes` | « Ex: Spam, Mauvaise qualité audio… » |

---

## 3. Stockage dans `app_config`

```json
{
  "general": {
    "scan_on_start": true,
    "connexion_automatique": false,
    "description_profil": "Passionné de musique électronique",
    "photo_profil": "C:/Users/.../avatar.jpg",
    "interets_aimes": "Rock, Jazz, Soulseek",
    "interets_detestes": "Spam"
  }
}
```

### Clés et valeurs par défaut

| Clé | Défaut | Type |
|-----|--------|------|
| `general.scan_on_start` | `True` | `bool` |
| `general.connexion_automatique` | `False` | `bool` |
| `general.description_profil` | `""` | `str` |
| `general.photo_profil` | `""` | `str` (chemin fichier) |
| `general.interets_aimes` | `""` | `str` (CSV) |
| `general.interets_detestes` | `""` | `str` (CSV) |

---

## 4. Backend — lecture au démarrage

### 4.1 Lecture des valeurs (`soulseek_client.py`, lignes 232-236)

```python
scan_on_start = bool(app_config.get("general.scan_on_start", True))
description_profil = app_config.get("general.description_profil", "")
photo_profil_path = app_config.get("general.photo_profil", "")
interets_aimes = _parse_interests(app_config.get("general.interets_aimes", ""))
interets_detestes = _parse_interests(app_config.get("general.interets_detestes", ""))
```

### 4.2 Application aux paramètres Soulseek

#### a) Scan au démarrage — `SharesSettings` (lignes 343-346)

```python
shares=SharesSettings(
    scan_on_start=scan_on_start,        # bool — scanner les dossiers au lancement ?
    download=dossier_destination,
    directories=dossiers_partages,
)
```

#### b) Profil utilisateur — `UserInfoSettings` (lignes 285-291)

```python
settings = Settings(
    credentials=CredentialsSettings(
        username=username,
        password=password,
        info=UserInfoSettings(
            description=description_profil,                       # texte libre
            picture=_read_profile_picture(photo_profil_path),     # bytes | None
        ),
    ),
    ...
)
```

#### c) Centres d'intérêt — `InterestsSettings` (lignes 328-329)

```python
interests=InterestsSettings(
    liked=interets_aimes,      # set[str] — issu de _parse_interests
    hated=interets_detestes,   # set[str] — issu de _parse_interests
),
```

---

## 5. Fonctions utilitaires

### 5.1 `_parse_interests` (lignes 53-60)

```python
def _parse_interests(chaines: str) -> set[str]:
    """Transforme une chaîne CSV en ensemble Python.

    Ex: "Rock, Jazz, Soulseek" → {"Rock", "Jazz", "Soulseek"}
    """
    return {s.strip() for s in chaines.split(",") if s.strip()}
```

**Détails :**
- `split(",")` → découpage CSV
- `strip()` → suppression des espaces autour
- Filtrage des chaînes vides
- Retourne un `set[str]` (pas de doublons, ordre non garanti)

### 5.2 `_read_profile_picture` (lignes 150-165)

```python
def _read_profile_picture(path: str) -> bytes | None:
    """Lit un fichier image et retourne son contenu en bytes."""
    if not path:
        return None
    try:
        with open(path, "rb") as f:
            return f.read()
    except (FileNotFoundError, PermissionError, OSError) as e:
        logger.warning("Impossible de lire la photo de profil '%s': %s", path, e)
        return None
```

**Détails :**
- Chemin vide → `None` (pas d'image)
- Lecture en mode binaire (`"rb"`)
- Gestion des erreurs : fichier inexistant, permissions, erreurs OS
- Retourne `bytes` si succès, `None` si échec

---

## 6. Connexion automatique (`connexion_automatique`)

Contrairement aux autres paramètres Général, `connexion_automatique` n'est **pas** appliqué via `soulseek_client.py`. Il est utilisé par `connexion_manager.py` et `main_window.py`.

### 6.1 Vérification au démarrage (`main_window.py`, ligne 341)

```python
auto_login = cfg_get("general.connexion_automatique", False)
if auto_login:
    self._connexion_manager.auto_login()
```

### 6.2 Méthode `auto_login` (`connexion_manager.py`, lignes 369-393)

```python
def auto_login(self) -> None:
    """Tente une reconnexion auto avec les credentials stockés."""
    if not app_config.get("general.connexion_automatique", False):
        logger.debug("Connexion automatique désactivée — skip auto_login")
        return
    username = app_config.get("reseau.nom_utilisateur", "")
    password = app_config.get("reseau.mot_de_passe", "")
    if username and password:
        logger.info("Reconnexion auto détectée pour : %s", username)
        self.status_changed.emit("Reconnexion automatique…")
        self._async_thread.run_coro(self._do_login(username, password))
    else:
        logger.debug("Aucun credentials stockés — pas de reconnexion auto")
```

**Flux de la connexion automatique :**

```
Démarrage application
        │
        ▼
main_window.py
  lit general.connexion_automatique
        │
        ├── False → rien (connexion manuelle attendue)
        │
        └── True → connexion_manager.auto_login()
                        │
                        ├── lit reseau.nom_utilisateur + reseau.mot_de_passe
                        │
                        ├── credentials vides ? → log + return
                        │
                        └── credentials OK → _async_thread.run_coro(_do_login())
```

### 6.3 Modification depuis le widget connexion (`connexions.py`, ligne 374)

```python
cfg_set("general.connexion_automatique", checked)  # checkbox "Se souvenir de moi"
```

---

## 7. Flux complet (démarrage → réseau Soulseek)

```
Démarrage application
        │
        ├── main_window: general.connexion_automatique ?
        │     └── True → connexion_manager.auto_login()
        │
        └── soulseek_client.py: initialisation
              │
              ├── lit general.scan_on_start (True/False)
              ├── lit general.description_profil (str)
              ├── lit general.photo_profil (chemin → bytes)
              ├── lit general.interets_aimes (CSV → set)
              └── lit general.interets_detestes (CSV → set)
                    │
                    ▼
              Settings(
                credentials=CredentialsSettings(
                  info=UserInfoSettings(
                    description="...",
                    picture=b"...",
                  ),
                ),
                interests=InterestsSettings(
                  liked={"Rock", "Jazz"},
                  hated={"Spam"},
                ),
                shares=SharesSettings(
                  scan_on_start=True,
                  ...
                ),
              )
                    │
                    ▼
              aioslsk client.init()
                    │
                    ├── scan_on_start ? → library_scanner.scan()
                    ├── description + picture → visibles sur le réseau
                    └── interests → filtrage de contenu recommandé
```

---

## 8. Notes techniques

- **`scan_on_start` casté en `bool`** : la lecture utilise `bool(app_config.get(...))` pour garantir un type booléen, même si la valeur stockée est un entier (0/1) ou une chaîne.
- **`_parse_interests`** : identique pour les salons favoris (`salons.favoris`) et les centres d'intérêt — fonction générique de parsing CSV → `set[str]`.
- **`_read_profile_picture` silencieux** : si le fichier photo est supprimé entre la configuration et le démarrage, l'erreur est loggée en `warning` et l'application continue sans image.
- **Connexion automatique dépendante des credentials** : activer `connexion_automatique` sans avoir stocké de nom d'utilisateur/mot de passe ne produit pas d'erreur — la connexion est simplement ignorée.
- **Prise d'effet au démarrage** : tous les paramètres Général (sauf `connexion_automatique` qui est vérifié dynamiquement) sont lus une seule fois au démarrage. Une modification dans l'UI nécessite un redémarrage pour être appliquée côté Soulseek.

---

## Voir aussi

- [Configuration des partages](configuration-partages.md) — détails de `SharesSettings.scan_on_start` et `library_scanner`
- [Configuration des salons](configuration-salons.md) — `_parse_interests()` réutilisée pour les favoris
- [Service app_config](service-app-config.md) — mécanisme de persistance atomique
- [Architecture de l'application](architecture-application.md) — vue d'ensemble des couches logicielles
