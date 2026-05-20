---
title: "Configuration — Page Salons"
category: "technique"
tags:
  - salons
  - configuration
  - rooms
  - parametres
keywords:
  - salons configuration page technique
  - salons configuration page technique
  - ConfigPage Salons center.py ligne 834
  - ConfigSection General ConfigToggle ConfigEntry
  - ConfigSection Général ConfigToggle ConfigEntry
  - salons.auto_join ConfigToggle defaut True
  - salons.auto_join ConfigToggle défaut True
  - salons.invitations_privees ConfigToggle defaut True
  - salons.invitations_privees ConfigToggle défaut True
  - salons.favoris ConfigEntry placeholder CSV
  - salons.favoris ConfigEntry placeholder CSV virgule
  - salons.favoris ConfigEntry Ex #musique #techno
  - soulseek_client.py ligne 246 auto_join
  - soulseek_client.py ligne 247 invitations_privees
  - soulseek_client.py ligne 250 salons_favoris
  - soulseek_client.py ligne 323 auto_join_salons
  - soulseek_client.py ligne 324 private_room_invites
  - soulseek_client.py ligne 325 _parse_interests
  - _parse_interests CSV set chaines
  - _parse_interests CSV set chaînes
  - _parse_interests split virgule strip
  - _parse_interests split virgule strip ignore vide
  - salons favoris parse interets demarrage
  - salons favoris parse intérêts démarrage
  - connexion_manager search_room recherche salon
  - connexion_manager _do_search_room async
  - connexion_manager client.searches.search_room
  - _current_search_ticket suivi ticket
  - app_config salons section defaults
  - app_config salons section défauts
  - configuration salons parametres reseau
  - configuration salons paramètres réseau
---

# Configuration — Page Salons

## Vue d'ensemble

La page **Salons** est l'une des 8 pages de configuration accessibles via le panneau gauche (`LeftZone` → `config-salons`). Elle permet de paramétrer le comportement de l'application vis-à-vis des salons de discussion (rooms) du réseau Soulseek.

```
LeftZone [Salons]
    ↓ page_changed("config-salons")
CenterZone.show_page("config-salons")
    ↓
QStackedWidget → ConfigPage("Salons")
    ├─ ConfigSection("Général")
    │    ├─ ConfigToggle("salons.auto_join")
    │    ├─ ConfigToggle("salons.invitations_privees")
    │    └─ ConfigEntry("salons.favoris")
    └─ (future sections)
```

---

## 1. Construction de la page (widgets UI)

**Fichier :** `src/gui/layout/center.py` (lignes ~834-863)

La page est construite dans la méthode `_build_config_pages()` de `CenterZone` :

```python
# Création de la page ConfigPage
salons = ConfigPage("Salons")

# Section Général
section_general = ConfigSection("Général")

# Rejoindre automatiquement les salons favoris
toggle_auto_join = ConfigToggle("Rejoindre les salons automatiquement")
toggle_auto_join.config_key = "salons.auto_join"
section_general.add(toggle_auto_join)

# Accepter les invitations aux salons privés
toggle_invitations = ConfigToggle("Accepter les invitations aux salons privés")
toggle_invitations.config_key = "salons.invitations_privees"
section_general.add(toggle_invitations)

# Liste des salons favoris (au format CSV)
entry_favoris = ConfigEntry("Salons favoris")
entry_favoris.config_key = "salons.favoris"
entry_favoris.placeholder = "Ex: #musique, #techno, #chat-francais…"
section_general.add(entry_favoris)

salons.add(section_general)
```

### Widgets utilisés

| Widget | Clé (`config_key`) | Type | Valeur par défaut |
|--------|-------------------|------|-------------------|
| `ConfigToggle` | `salons.auto_join` | `bool` | `True` |
| `ConfigToggle` | `salons.invitations_privees` | `bool` | `True` |
| `ConfigEntry` | `salons.favoris` | `str` | `""` (chaîne vide) |

### Détail des widgets

#### `ConfigToggle("Rejoindre les salons automatiquement")`
- **Classe :** `ConfigToggle` (sous-classe de `QCheckBox`)
- **config_key :** `"salons.auto_join"`
- **Défaut :** `True`
- **Comportement :** Lorsque coché, l'application rejoindra automatiquement les salons listés dans `salons.favoris` au démarrage

#### `ConfigToggle("Accepter les invitations aux salons privés")`
- **Classe :** `ConfigToggle` (sous-classe de `QCheckBox`)
- **config_key :** `"salons.invitations_privees"`
- **Défaut :** `True`
- **Comportement :** Lorsque coché, les invitations vers des salons privés sont automatiquement acceptées

#### `ConfigEntry("Salons favoris")`
- **Classe :** `ConfigEntry` (sous-classe de `QLineEdit`)
- **config_key :** `"salons.favoris"`
- **Défaut :** `""` (chaîne vide)
- **Placeholder :** `"Ex: #musique, #techno, #chat-francais…"`
- **Format :** Liste de noms de salons séparés par des virgules (CSV)

---

## 2. Stockage de la configuration

**Fichier :** `src/services/app_config.py`

Les valeurs des paramètres sont persistées dans le fichier `app_config.json` sous la section `salons` :

```json
{
  "salons": {
    "auto_join": true,
    "invitations_privees": true,
    "favoris": "#musique, #techno, #chat-francais"
  }
}
```

Les valeurs par défaut sont définies dans le dictionnaire `_DEFAULTS` :

```python
_DEFAULTS = {
    # ...
    "salons": {
        "auto_join": True,
        "invitations_privees": True,
        "favoris": "",
    },
    # ...
}
```

### Cycle de persistance

```
Utilisateur change un toggle dans l'UI
    ↓
ConfigToggle._on_toggled()
    ↓
app_config.set("salons.auto_join", valeur)
    ↓
_config["salons"]["auto_join"] = valeur
_save() → écriture atomique dans app_config.json
```

---

## 3. Lecture et application au démarrage

**Fichier :** `src/services/soulseek_client.py` (lignes ~246-250 et ~323-325)

### Lecture (lignes 246-250)

```python
# Chargement de la configuration des salons depuis app_config
auto_join_salons = bool(app_config.get("salons.auto_join", True))
invitations_privees = bool(app_config.get("salons.invitations_privees", True))
salons_favoris = app_config.get("salons.favoris", "")
```

### Transformation des favoris via `_parse_interests` (ligne 53)

```python
def _parse_interests(raw: str) -> set[str]:
    """Convertit une chaîne séparée par des virgules en ensemble d'intérêts.
    
    Nettoie les espaces et ignore les éléments vides.
    
    Args:
        raw: Chaîne brute (ex: "Rock, Jazz, Soul")
    
    Returns:
        Ensemble d'intérêts nettoyés (ex: {"Rock", "Jazz", "Soul"})
    """
    if not raw:
        return set()
    return {item.strip() for item in raw.split(",") if item.strip()}
```

### Application (lignes 323-325)

Les paramètres sont passés à la méthode d'initialisation du client Soulseek :

```python
auto_join=auto_join_salons,
private_room_invites=invitations_privees,
favorites=_parse_interests(salons_favoris),
```

`_parse_interests(salons_favoris)` transforme la chaîne CSV `"#musique, #techno, #chat-francais"` en un ensemble Python :
```python
{"#musique", "#techno", "#chat-francais"}
```

---

## 4. Interaction avec les salons (backend)

**Fichier :** `src/services/connexion_manager.py`

Le `ConnexionManager` expose des méthodes pour interagir avec les salons côté backend :

### `search_room(room, query)`

```python
def search_room(self, room: str, query: str):
    """Lance une recherche dans un salon spécifique."""
    self._async_thread.run_coro(self._do_search_room(room, query))
```

### `_do_search_room(room, query)`

```python
async def _do_search_room(self, room: str, query: str):
    """Coroutine : effectue la recherche via l'API aioslsk."""
    try:
        # Utilise client.searches.search_room() de la bibliothèque aioslsk
        ticket = await self._client.searches.search_room(room, query)
        self._current_search_ticket = ticket
        logger.info("Recherche lancée dans le salon %s : %s (ticket %s)", room, query, ticket)
    except Exception as e:
        logger.error("Erreur recherche salon %s: %s", room, e)
        self.error_occurred.emit(str(e))
```

### Réception des messages de salons

Dans `CenterZone` (center.py), les signaux sont connectés pour recevoir les messages :

```python
soulseek_service.room_message_received.connect(
    lambda evt: logger.debug(
        "Message reçu dans le salon %s de %s : %s",
        evt.message.room_name,
        evt.message.username,
        evt.message.content[:80]
    )
)
```

---

## 5. Flux complet de configuration des salons

### Au démarrage de l'application

```
Démarrage
    ↓
soulseek_client.py lit app_config
    ├─ salons.auto_join = True
    ├─ salons.invitations_privees = True
    └─ salons.favoris = "#musique, #techno"
    ↓
_parse_interests("#musique, #techno") → {"#musique", "#techno"}
    ↓
Client Soulseek initialisé avec :
    ├─ auto_join=True
    ├─ private_room_invites=True
    └─ favorites={"#musique", "#techno"}
    ↓
Connexion au serveur Soulseek
    ├─ Rejoint automatiquement #musique
    ├─ Rejoint automatiquement #techno
    └─ Attend les invitations privées
```

### Modification par l'utilisateur

```
Utilisateur modifie "Salons favoris" dans l'UI
    ↓
ConfigEntry._on_changed()
    ↓
app_config.set("salons.favoris", "Soulseek, New Albums")
    ↓
_config["salons"]["favoris"] = "Soulseek, New Albums"
_save() → écriture disque
    ↓
⚠ Les modifications prennent effet au REDÉMARRAGE de l'application
```

### Recherche dans un salon

```
Recherche dans "#musique" pour "album jazz"
    ↓
ConnexionManager.search_room("#musique", "album jazz")
    ↓
_do_search_room("#musique", "album jazz")
    ↓
client.searches.search_room("#musique", "album jazz")
    ↓
Résultats → soulseek_service.search_results_received
    ↓
Affichage dans la zone centrale (CenterZone)
```

---

## 6. Tableau récapitulatif des paramètres

| Paramètre | Clé | Widget | Type | Défaut | Application |
|-----------|-----|--------|------|--------|-------------|
| Rejoindre automatiquement | `salons.auto_join` | `ConfigToggle` | `bool` | `True` | Lecture au démarrage |
| Invitations privées | `salons.invitations_privees` | `ConfigToggle` | `bool` | `True` | Lecture au démarrage |
| Salons favoris | `salons.favoris` | `ConfigEntry` | `str` (CSV) | `""` | Parse via `_parse_interests`, lecture au démarrage |

### Fichiers impliqués

| Fichier | Rôle |
|---------|------|
| `src/gui/layout/center.py` (lignes 834-863) | Construction de la `ConfigPage("Salons")` avec ses widgets |
| `src/services/app_config.py` | Stockage et valeurs par défaut des paramètres `salons.*` |
| `src/services/soulseek_client.py` (lignes 246-250, 323-325) | Lecture et application au démarrage |
| `src/services/soulseek_client.py` (ligne 53) | Fonction `_parse_interests` pour transformer le CSV |
| `src/services/connexion_manager.py` | `search_room` / `_do_search_room` pour chercher dans un salon |

---

## 7. Notes techniques importantes

1. **Prise d'effet au démarrage** : Les paramètres de l'onglet Salons (contrairement à certains autres onglets) sont lus **uniquement au démarrage** de l'application. Les modifications ne sont pas appliquées dynamiquement. Un redémarrage est nécessaire pour prendre en compte les changements.

2. **Parsing des favoris** : La fonction `_parse_interests` utilise `split(",")` et `strip()`, ce qui signifie que :
   - Les espaces autour des virgules sont ignorés (`#musique, #techno` → `["#musique", "#techno"]`)
   - Les entrées vides sont ignorées (`#musique,, #techno` → `["#musique", "#techno"]`)
   - Les doublons sont supprimés (utilisation d'un `set`)

3. **Format des noms de salons** : Les salons Soulseek sont généralement préfixés par `#` (ex: `#musique`, `#Soulseek`), mais le système accepte les noms avec ou sans le préfixe.

4. **Recherche dans un salon** : Contrairement à une recherche globale, `search_room()` permet de limiter les résultats aux fichiers partagés par les utilisateurs présents dans un salon spécifique. Cette méthode est généralement déclenchée depuis le panneau droit (`RightZone`) ou la page de recherche.
