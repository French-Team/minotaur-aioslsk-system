---
title: "Configuration — Page Utilisateurs"
category: "technique"
tags:
  - utilisateurs
  - configuration
  - amis
  - bloques
keywords:
  - utilisateurs configuration page technique
  - utilisateurs configuration page technique
  - ConfigPage Utilisateurs center.py widgets
  - ConfigSection Amis ConfigEntry liste amis
  - ConfigSection Amis ConfigEntry liste amis
  - ConfigSection Bloques ConfigEntry liste bloques
  - ConfigSection Bloqués ConfigEntry liste bloqués
  - utilisateurs.liste_amis ConfigEntry placeholder user1 user2 user3
  - utilisateurs.liste_bloques ConfigEntry placeholder spammer troll
  - soulseek_client.py ligne 244 liste_amis app_config.get
  - soulseek_client.py ligne 245 liste_bloques app_config.get
  - soulseek_client.py ligne 364 friends _parse_interests liste amis
  - soulseek_client.py ligne 365 blocked _parse_blocked liste bloques
  - _parse_blocked dictionnaire utilisateur BlockingFlag
  - _parse_blocked BlockingFlag PRIVATE_MESSAGES ROOM_MESSAGES
  - _parse_interests liste CSV set chaines
  - _parse_interests liste CSV set chaînes
  - connexion_manager block_user ajout dynamique
  - connexion_manager block_user deja bloque verifie
  - connexion_manager block_user déjà bloqué vérifié
  - connexion_manager block_user concat virgule set emit
  - connexion_manager block_user status_changed emoji
  - app_config utilisateurs section defaults
  - app_config utilisateurs section défauts
  - configuration utilisateurs parametres reseau
  - configuration utilisateurs paramètres réseau
  - block_user effect immediat persistant demarrage
  - block_user effet immédiat persistant démarrage
  - liste amis bloques CSV virgules espaces
  - liste amis bloqués CSV virgules espaces
---

# Configuration — Page Utilisateurs

## Vue d'ensemble

La page **Utilisateurs** est l'une des 8 pages de configuration accessibles via le panneau gauche (`LeftZone` → `config-utilisateurs`). Elle permet de gérer les **listes d'amis** et d'**utilisateurs bloqués** du client Soulseek.

```
LeftZone [Utilisateurs]
    ↓ page_changed("config-utilisateurs")
CenterZone.show_page("config-utilisateurs")
    ↓
QStackedWidget → ConfigPage("Utilisateurs")
    ├─ ConfigSection("Amis")
    │    └─ ConfigEntry("utilisateurs.liste_amis")
    └─ ConfigSection("Bloqués")
         └─ ConfigEntry("utilisateurs.liste_bloques")
```

---

## 1. Construction de la page (widgets UI)

**Fichier :** `src/gui/layout/center.py` (lignes ~734-761)

La page est construite dans la méthode `_build_config_pages()` de `CenterZone` :

```python
# Création de la page ConfigPage
utilisateurs = ConfigPage("Utilisateurs")

# Section Amis
section_amis = ConfigSection("Amis")

entry_amis = ConfigEntry("Liste d'amis")
entry_amis.config_key = "utilisateurs.liste_amis"
entry_amis.placeholder = "user1, user2, user3"
section_amis.add(entry_amis)

utilisateurs.add(section_amis)

# Section Bloqués
section_bloques = ConfigSection("Bloqués")

entry_bloques = ConfigEntry("Utilisateurs bloqués")
entry_bloques.config_key = "utilisateurs.liste_bloques"
entry_bloques.placeholder = "spammer, troll"
section_bloques.add(entry_bloques)

utilisateurs.add(section_bloques)
```

### Widgets utilisés

| Widget | Clé (`config_key`) | Type | Valeur par défaut | Placeholder |
|--------|-------------------|------|-------------------|-------------|
| `ConfigEntry` | `utilisateurs.liste_amis` | `str` (CSV) | `""` | `user1, user2, user3` |
| `ConfigEntry` | `utilisateurs.liste_bloques` | `str` (CSV) | `""` | `spammer, troll` |

### Détail des widgets

#### `ConfigEntry("Liste d'amis")`
- **Classe :** `ConfigEntry` (sous-classe de `QLineEdit`)
- **config_key :** `"utilisateurs.liste_amis"`
- **Placeholder :** `"user1, user2, user3"`
- **Format :** Noms d'utilisateurs Soulseek séparés par des virgules (CSV)

#### `ConfigEntry("Utilisateurs bloqués")`
- **Classe :** `ConfigEntry` (sous-classe de `QLineEdit`)
- **config_key :** `"utilisateurs.liste_bloques"`
- **Placeholder :** `"spammer, troll"`
- **Format :** Noms d'utilisateurs Soulseek séparés par des virgules (CSV)

---

## 2. Stockage de la configuration

**Fichier :** `src/services/app_config.py`

Les valeurs des paramètres sont persistées dans le fichier `app_config.json` sous la section `utilisateurs` :

```json
{
  "utilisateurs": {
    "liste_amis": "ami1, ami2, ami3",
    "liste_bloques": "spammer, troll"
  }
}
```

Les valeurs par défaut sont définies dans le dictionnaire `_DEFAULTS` :

```python
_DEFAULTS = {
    # ...
    "utilisateurs": {
        "liste_amis": "",
        "liste_bloques": "",
    },
    # ...
}
```

### Cycle de persistance (via l'UI)

```
Utilisateur modifie "Liste d'amis" dans l'UI
    ↓
ConfigEntry._on_changed()
    ↓
app_config.set("utilisateurs.liste_amis", valeur)
    ↓
_config["utilisateurs"]["liste_amis"] = valeur
_save() → écriture atomique dans app_config.json
    ↓
⚠ Les modifications prennent effet au REDÉMARRAGE de l'application
```

---

## 3. Lecture et application au démarrage

**Fichier :** `src/services/soulseek_client.py`

### Lecture (lignes 244-245)

```python
# Chargement de la configuration des utilisateurs depuis app_config
liste_amis = app_config.get("utilisateurs.liste_amis", "")
liste_bloques = app_config.get("utilisateurs.liste_bloques", "")
```

### Parsing des listes

#### `_parse_interests` (ligne 53) — pour les amis

```python
def _parse_interests(raw: str) -> set[str]:
    """Convertit une chaîne séparée par des virgules en ensemble d'intérêts.
    
    Nettoie les espaces et ignore les éléments vides.
    
    Args:
        raw: Chaîne brute (ex: "user1, user2, user3")
    
    Returns:
        Ensemble de noms d'utilisateurs nettoyés (ex: {"user1", "user2", "user3"})
    """
    if not raw:
        return set()
    return {item.strip() for item in raw.split(",") if item.strip()}
```

#### `_parse_blocked` (lignes 72-82) — pour les bloqués

```python
def _parse_blocked(raw: str) -> dict[str, BlockingFlag]:
    """Convertit une chaîne CSV de noms d'utilisateurs en dictionnaire
    de flags de blocage.
    
    Args:
        raw: Chaîne brute (ex: "spammer, troll")
    
    Returns:
        Dictionnaire {utilisateur: BlockingFlag} avec tous les flags activés
    """
    if not raw or not raw.strip():
        return {}
    
    all_flags = BlockingFlag.PRIVATE_MESSAGES | BlockingFlag.ROOM_MESSAGES
    return {user.strip(): all_flags for user in raw.split(",") if user.strip()}
```

### Application au client Soulseek (lignes 364-365)

Les listes parsées sont passées à l'objet `settings` qui initialise le `SoulSeekClient` :

```python
settings = SoulSeekSettings(
    # ...
    friends=_parse_interests(liste_amis),       # → {"ami1", "ami2", "ami3"}
    blocked=_parse_blocked(liste_bloques),       # → {"spammer": all_flags, "troll": all_flags}
    # ...
)

self._client = SoulSeekClient(settings)
```

---

## 4. Ajout dynamique d'un utilisateur bloqué

**Fichier :** `src/services/connexion_manager.py` (lignes ~340-356)

En plus de la configuration statique via l'UI, l'application permet de **bloquer un utilisateur dynamiquement** (depuis la liste des clients actifs ou les résultats de recherche, par exemple).

```python
def block_user(self, username: str) -> None:
    """Ajoute un utilisateur à la liste des bloqués et persiste la configuration.
    
    Vérifie d'abord si l'utilisateur est déjà présent, puis met à jour
    la liste dans app_config et émet un signal de statut.
    
    Args:
        username: Nom de l'utilisateur à bloquer
    """
    # Récupération de la liste actuelle
    bloques = app_config.get("utilisateurs.liste_bloques", "")
    
    # Vérification si déjà bloqué
    if username in bloques:
        logger.info("Utilisateur %s déjà dans la liste des bloqués", username)
        return
    
    # Ajout à la liste (gestion de la virgule)
    if bloques:
        bloques += f", {username}"
    else:
        bloques = username
    
    # Persistance
    app_config.set("utilisateurs.liste_bloques", bloques)
    
    # Notification
    self.status_changed.emit(f"🚫 Utilisateur {username} bloqué")
```

### Détail de l'implémentation

| Étape | Code | Description |
|-------|------|-------------|
| 1. Lecture | `app_config.get("utilisateurs.liste_bloques", "")` | Récupère la liste actuelle |
| 2. Vérification | `if username in bloques: return` | Évite les doublons |
| 3. Concaténation | `bloques += f", {username}"` | Ajoute avec virgule si liste non vide |
| 4. Persistance | `app_config.set(...)` | Sauvegarde immédiate dans `app_config.json` |
| 5. Notification | `status_changed.emit(...)` | Signal UI (icône 🚫 + message) |

---

## 5. Différence entre configuration statique et blocage dynamique

| Aspect | Configuration via l'UI (ConfigEntry) | `block_user()` dynamique |
|--------|--------------------------------------|--------------------------|
| **Déclencheur** | Utilisateur édite le champ dans la page config | Action contextuelle (clic droit, menu) |
| **Effet** | Mise à jour de `app_config` uniquement | Mise à jour de `app_config` + notification UI |
| **Prise d'effet blocage** | Au redémarrage de l'application | Immédiate (persistée, mais appliquée au prochain démarrage côté Soulseek) |
| **Mécanisme** | `ConfigEntry._on_changed()` → `app_config.set()` | `block_user()` → vérification → `app_config.set()` |

> **Note importante :** Bien que `block_user()` persiste immédiatement la liste dans `app_config.json`, le blocage effectif côté réseau Soulseek (via `SoulSeekSettings.blocked`) n'est appliqué qu'au **démarrage suivant** du client, car `_parse_blocked()` est appelée uniquement lors de l'initialisation de `SoulSeekClient`.

---

## 6. Flux complet

### Au démarrage de l'application

```
Démarrage
    ↓
soulseek_client.py lit app_config
    ├─ utilisateurs.liste_amis = "ami1, ami2"
    └─ utilisateurs.liste_bloques = "spammer, troll"
    ↓
_parse_interests("ami1, ami2")   → {"ami1", "ami2"}
_parse_blocked("spammer, troll") → {"spammer": all_flags, "troll": all_flags}
    ↓
SoulSeekClient initialisé avec friends + blocked
    ↓
Connexion au serveur Soulseek
    ├─ Amis : accès prioritaire aux slots, visibilité statut
    └─ Bloqués : fichiers cachés, téléchargements refusés
```

### Blocage dynamique d'un utilisateur

```
Action utilisateur : "Bloquer cet utilisateur"
    ↓
ConnexionManager.block_user("spammer123")
    ├─ Vérifie si déjà présent dans la liste
    ├─ Ajoute "spammer123" à la liste CSV
    ├─ Sauvegarde dans app_config.json
    └─ Émet status_changed("🚫 Utilisateur spammer123 bloqué")
    ↓
⚠ Application effective au prochain démarrage
```

### Modification des listes via l'UI

```
Utilisateur modifie "Liste d'amis" dans ConfigEntry
    ↓
ConfigEntry._on_changed()
    ↓
app_config.set("utilisateurs.liste_amis", "nouveau_ami")
    ↓
_save() → écriture atomique dans app_config.json
    ↓
⚠ Modification appliquée au prochain démarrage
```

---

## 7. Tableau récapitulatif des paramètres

| Paramètre | Clé | Widget | Type | Défaut | Parsing | Application |
|-----------|-----|--------|------|--------|---------|-------------|
| Liste d'amis | `utilisateurs.liste_amis` | `ConfigEntry` | `str` (CSV) | `""` | `_parse_interests` → `set[str]` | Au démarrage (`friends`) |
| Utilisateurs bloqués | `utilisateurs.liste_bloques` | `ConfigEntry` | `str` (CSV) | `""` | `_parse_blocked` → `dict[str, BlockingFlag]` | Au démarrage (`blocked`) |

### Fichiers impliqués

| Fichier | Rôle |
|---------|------|
| `src/gui/layout/center.py` (lignes 734-761) | Construction de la `ConfigPage("Utilisateurs")` avec ses 2 `ConfigEntry` |
| `src/services/app_config.py` | Stockage et valeurs par défaut des paramètres `utilisateurs.*` |
| `src/services/soulseek_client.py` (lignes 244-245) | Lecture des listes depuis `app_config` |
| `src/services/soulseek_client.py` (lignes 53-67) | Fonction `_parse_interests` pour les amis (CSV → `set`) |
| `src/services/soulseek_client.py` (lignes 72-82) | Fonction `_parse_blocked` pour les bloqués (CSV → `dict[str, BlockingFlag]`) |
| `src/services/soulseek_client.py` (lignes 364-365) | Passage des listes parsées à `SoulSeekSettings` |
| `src/services/connexion_manager.py` (lignes 340-356) | Méthode `block_user()` pour blocage dynamique |

---

## 8. Notes techniques importantes

1. **Prise d'effet au démarrage** : Les listes d'amis et de bloqués sont lues **uniquement à l'initialisation** de `SoulSeekClient`. Les modifications via l'UI ou via `block_user()` nécessitent un redémarrage pour être appliquées effectivement côté réseau Soulseek.

2. **Parsing des listes CSV** : Les deux fonctions utilisent `split(",")` et `strip()`, avec les mêmes règles :
   - Espaces ignorés (`ami1, ami2` → `["ami1", "ami2"]`)
   - Entrées vides ignorées (`ami1,, ami2` → `["ami1", "ami2"]`)
   - Doublons supprimés pour `_parse_interests` (utilisation d'un `set`)
   - Écrasement pour `_parse_blocked` (dernière occurrence gagne dans le dict)

3. **Différence entre `_parse_interests` et `_parse_blocked`** :
   - `_parse_interests` retourne un `set[str]` (liste simple de noms)
   - `_parse_blocked` retourne un `dict[str, BlockingFlag]` (noms associés à des flags de blocage)

4. **BlockingFlag** : Les flags `PRIVATE_MESSAGES` et `ROOM_MESSAGES` sont combinés (`|`) pour appliquer un blocage complet aux utilisateurs listés.

5. **`block_user()` vs UI** : La méthode `block_user()` offre une expérience utilisateur plus riche (vérification des doublons, notification immédiate) mais les deux mécanismes aboutissent à la même persistance dans `app_config.json`.
