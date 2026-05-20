---
title: "Widgets de configuration : onglets Salons et Debug"
category: technique
tags:
  - configuration
  - widgets
  - salons
  - debug
  - depannage
  - débogage
  - journaux
keywords:
  - configuration onglet salons
  - configuration onglet debug
  - configuration onglet debogage
  - configuration onglet débogage
  - salons auto join toggle
  - salons auto join activé démarrage
  - salons invitations privees toggle
  - salons invitations privées toggle
  - salons favoris liste entree texte
  - salons favoris liste entrée texte
  - salons favoris placeholder dièse musique
  - ConfigToggle salons auto join
  - ConfigToggle salons invitations privees
  - ConfigToggle salons invitations privées
  - ConfigEntry salons favoris csv
  - ConfigToggle debug search for parent
  - ConfigEntry debug ip overrides json
  - ConfigToggle debug log connection count
  - debug ip overrides parse json loads
  - debug ip overrides dictionnaire vide defaut
  - debug ip overrides dictionnaire vide défaut
  - soulseek client lecture config demarrage salons
  - soulseek client lecture configuration démarrage salons
  - soulseek client salons auto join invitations privees booleens
  - soulseek client salons auto join invitations privées booléens
  - soulseek client salons favoris chaine csv
  - soulseek client salons favoris chaîne csv
  - soulseek client debug search for parent false
  - soulseek client debug ip overrides json loads
  - soulseek client debug log connection count false
  - app config valeurs par defaut salons debug
  - app config valeurs par défaut salons debug
  - section generale salons configuration
  - section générale salons configuration
  - section options debogage debug
  - section options débogage debug
  - placeholder salon dièse musique techno
  - placeholder surcharges ip json format
  - config salons description rejoindre demarrage
  - config salons description rejoindre démarrage
  - config salons description invitations privees
  - config salons description invitations privées
  - config debug description rechercher parent connexion
  - config debug description journaliser connexions logs
  - diagnostic parent bibliotheque fichier
  - diagnostic parent bibliothèque fichier
---

# Widgets de configuration : onglets Salons et Debug

## Vue d'ensemble

Les onglets **Salons** et **Debug** sont les deux derniers onglets de l'interface de configuration (8 `ConfigPage` au total). Le premier gère les salons de discussion Soulseek, le second expose des options de diagnostic avancé.

```
┌─────────────────────────────────────────────────────────────┐
│  [...] [Utilisateurs] [Partages] [Salons] [Debug]            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Salons                         │   Debug                   │
│                                                              │
│  ┌─ Général ─────────────────┐   │  ┌─ Options débogage ──┐  │
│  │ ☑ Rejoindre les salons    │   │  │ ☐ Search for parent │  │
│  │    automatiquement        │   │  │                     │  │
│  │ ☑ Accepter invitations    │   │  │ Surcharges IP (JSON)│  │
│  │    salons privés          │   │  │ [{"user": "1.2..."] │  │
│  │                           │   │  │                     │  │
│  │ Salons favoris            │   │  │ ☐ Journaliser les   │  │
│  │ [#musique, #techno, ...]  │   │  │    connexions       │  │
│  └───────────────────────────┘   │  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Architecture

| Onglet | Lignes (center.py) | Sections | Widgets |
|--------|-------------------|----------|---------|
| **Salons** | 834-865 | 1 (Général) | 2 × `ConfigToggle` + 1 × `ConfigEntry` |
| **Debug** | 866-918 | 1 (Options de débogage) | 2 × `ConfigToggle` + 1 × `ConfigEntry` |

Les deux onglets sont construits dans `center.py._build_config_pages()` et partagent la même architecture de widgets que les autres onglets (définis dans `src/gui/widgets/config.py`).

---

## 1. Onglet Salons

Gère l'inscription automatique aux salons de discussion Soulseek et les invitations privées.

### Section Général

| Champ | Widget | Clé config | Défaut | Placeholder |
|-------|--------|------------|--------|-------------|
| **Rejoindre les salons automatiquement** | `ConfigToggle` | `salons.auto_join` | `True` | — |
| **Accepter les invitations aux salons privés** | `ConfigToggle` | `salons.invitations_privees` | `True` | — |
| **Salons favoris** | `ConfigEntry` | `salons.favoris` | `""` | `#musique, #techno, #chat-francais…` |

#### `salons.auto_join` — Rejoindre les salons automatiquement

```
État activé (True)  →  Rejoint les salons favoris + salons par défaut dès la connexion
État désactivé (False) →  Aucun salon rejoint automatiquement
```

- **Description affichée :** "Rejoindre les salons favoris et les salons par défaut dès la connexion."
- **Valeur par défaut :** `True` — recommandé pour une expérience sociale active

#### `salons.invitations_privees` — Accepter les invitations aux salons privés

```
État activé (True)  →  Les autres utilisateurs peuvent vous inviter dans leurs salons privés
État désactivé (False) →  Toute invitation privée est ignorée
```

- **Description affichée :** "Permet aux autres utilisateurs de vous inviter dans des salons privés. Désactivez pour ne recevoir aucune invitation."
- **Valeur par défaut :** `True`

#### `salons.favoris` — Salons favoris

```python
# Exemple de valeur stockée
"salons.favoris": "#musique, #techno, #chat-francais"
```

- **Description affichée :** "Salons à rejoindre automatiquement au démarrage. Séparez les noms par des virgules."
- **Placeholder :** `#musique, #techno, #chat-francais…`
- **Format :** Chaîne CSV — noms de salons séparés par des virgules (avec ou sans `#`)

---

## 2. Backend : configuration des salons

### Lecture au démarrage

Dans `src/services/soulseek_client.py` (lignes ~246-250), les options salons sont lues pendant l'initialisation du client :

```python
# soulseek_client.py (initialisation)
auto_join = app_config.get("salons.auto_join", True)            # bool
invitations_privees = app_config.get("salons.invitations_privees", True)  # bool
salons_favoris = app_config.get("salons.favoris", "")            # str — CSV
```

Ces valeurs sont ensuite utilisées pour configurer les salons Soulseek :

- `auto_join` : Si `True`, le client rejoint automatiquement les salons par défaut + les favoris
- `invitations_privees` : Si `True`, le client accepte les invitations vers des salons privés
- `salons_favoris` : La chaîne CSV est parsée (séparation par virgules) pour obtenir la liste des salons à rejoindre

### Flux de démarrage

```
Démarrage de l'application
        │
        ▼
center.py._build_config_pages()
   └── ConfigPage("Salons")
        ├── ConfigToggle("salons.auto_join", default=True)
        ├── ConfigToggle("salons.invitations_privees", default=True)
        └── ConfigEntry("salons.favoris", default="")
        │
        ▼
soulseek_client.py (initialisation)
   ├── app_config.get("salons.auto_join", True)
   ├── app_config.get("salons.invitations_privees", True)
   └── app_config.get("salons.favoris", "")
        │
        ▼
Connexion au serveur Soulseek
   ├── Rejoindre salons par défaut (si auto_join)
   ├── Rejoindre salons favoris (si auto_join + liste non vide)
   └── Configurer acceptation invitations privées
```

---

## 3. Onglet Debug

Expose des options de diagnostic avancé destinées aux utilisateurs techniques pour le débogage et le dépannage.

### Section Options de débogage

| Champ | Widget | Clé config | Défaut | Description |
|-------|--------|------------|--------|-------------|
| **Rechercher un parent** | `ConfigToggle` | `debug.search_for_parent` | `False` | Recherche d'un parent lors de la connexion |
| **Surcharges IP (JSON)** | `ConfigEntry` | `debug.ip_overrides` | `""` | Surcharges d'adresses IP au format JSON |
| **Journaliser les connexions** | `ConfigToggle` | `debug.log_connection_count` | `False` | Enregistrer le nombre de connexions dans les logs |

#### `debug.search_for_parent` — Rechercher un parent

```
État activé (True)  →  Le client recherche un parent serveur lors de la connexion
État désactivé (False) →  Pas de recherche de parent (comportement normal)
```

- **Description affichée :** "Activer la recherche d'un parent lors de la connexion au serveur"
- **Valeur par défaut :** `False` — à activer uniquement pour diagnostic

> 💡 **Cas d'usage** : Permet de diagnostiquer des erreurs d'affichage des chemins de fichiers dans la bibliothèque. À désactiver après diagnostic pour éviter une surcharge inutile.

#### `debug.ip_overrides` — Surcharges IP (JSON)

```json
// Exemple de valeur valide
{"nom_utilisateur": "1.2.3.4", "autre_user": "5.6.7.8"}
```

- **Description affichée :** "Surcharges d'adresses IP au format JSON\nex: {\"username\": \"1.2.3.4\"}"
- **Valeur par défaut :** `""` (chaîne vide — aucune surcharge)

> ⚠️ **Attention** : Une mauvaise saisie JSON peut bloquer l'accès à l'utilisateur concerné. Utiliser avec précaution.

#### `debug.log_connection_count` — Journaliser les connexions

```
État activé (True)  →  Le nombre de connexions actives est enregistré dans les logs
État désactivé (False) →  Aucune journalisation des connexions
```

- **Description affichée :** "Enregistrer le nombre de connexions dans les logs"
- **Valeur par défaut :** `False` — à activer pour analyse du réseau

---

## 4. Backend : options de debug

### Lecture et parsing

Dans `src/services/soulseek_client.py` (lignes ~355-362), les options debug sont lues et parsées :

```python
# soulseek_client.py (initialisation du client)
search_for_parent = app_config.get("debug.search_for_parent", False)        # bool
log_connection_count = app_config.get("debug.log_connection_count", False)  # bool

ip_overrides_raw = app_config.get("debug.ip_overrides", "")
try:
    ip_overrides = json.loads(ip_overrides_raw) if ip_overrides_raw else {}
except json.JSONDecodeError:
    ip_overrides = {}
    logger.warning("Surcharges IP invalides (JSON mal formé) : %s", ip_overrides_raw)
```

#### Parsing des surcharges IP

| Cas | `ip_overrides_raw` | Résultat |
|-----|-------------------|----------|
| Valeur vide | `""` | `{}` (dictionnaire vide) |
| JSON valide | `'{"user": "1.2.3.4"}'` | `{"user": "1.2.3.4"}` |
| JSON invalide | `"pas du json"` | `{}` + warning dans les logs |

Les valeurs sont passées en arguments lors de l'instanciation de la configuration du client Soulseek :

```python
# Conceptuellement, les options sont passées à la config du client
client_config = {
    "search_for_parent": search_for_parent,
    "ip_overrides": ip_overrides,
    "log_connection_count": log_connection_count,
}
```

---

## 5. Comparaison des deux onglets

| Propriété | Salons | Debug |
|-----------|--------|-------|
| **Lignes (center.py)** | 834-865 (32 lignes) | 866-918 (53 lignes) |
| **Sections** | 1 : Général | 1 : Options de débogage |
| **Widgets** | 2 × `ConfigToggle` + 1 × `ConfigEntry` | 2 × `ConfigToggle` + 1 × `ConfigEntry` |
| **Clés config** | `salons.*` (3 clés) | `debug.*` (3 clés) |
| **Valeurs par défaut** | `True`, `True`, `""` | `False`, `""`, `False` |
| **Backend** | `soulseek_client.py` (lignes 246-250) | `soulseek_client.py` (lignes 355-362) |
| **Type de données** | `bool`, `bool`, `str` (CSV) | `bool`, `str` (JSON), `bool` |
| **Public cible** | Tous les utilisateurs | Utilisateurs avancés / diagnostic |

### Clés de configuration complètes

```yaml
# Onglet Salons
salons.auto_join: true              # bool — Rejoindre les salons auto.
salons.invitations_privees: true    # bool — Accepter invitations privées
salons.favoris: ""                   # str — CSV de noms de salons

# Onglet Debug
debug.search_for_parent: false      # bool — Recherche d'un parent
debug.ip_overrides: ""               # str — JSON de surcharges IP
debug.log_connection_count: false   # bool — Journalisation connexions
```

---

## 6. Résumé technique

| Propriété | Salons | Debug |
|-----------|--------|-------|
| **Objectif** | Configuration des salons de discussion | Outils de diagnostic avancé |
| **Widgets** | 3 (2 toggles + 1 champ texte) | 3 (2 toggles + 1 champ texte) |
| **Clés** | `salons.auto_join`, `salons.invitations_privees`, `salons.favoris` | `debug.search_for_parent`, `debug.ip_overrides`, `debug.log_connection_count` |
| **Parsing spécial** | CSV pour les favoris | `json.loads()` pour les surcharges IP |
| **Défaut** | Tout activé | Tout désactivé |
| **Utilisateur** | Tous | Avancé |
