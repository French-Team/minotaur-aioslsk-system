---
title: "Blocage : configuration vs menu contextuel — les différences"
category: faq
keywords:
  - bloquer
  - config
  - contexte
  - contextuel
  - menu
  - difference
  - différence
  - blocage
  - utilisateur
  - liste noire
  - blacklist
  - clic droit
  - Optimiseur
  - Recherche
  - bloques
  - bloqués
  - connexion_manager
  - block_user
  - app_config
---

## Résumé

L'application propose **deux façons** de bloquer un utilisateur : via le champ texte de la configuration (**Optimiseur → Utilisateurs → Bloqués**) ou via le menu contextuel du bot **Recherche** (clic droit → **Bloquer l'utilisateur**). Bien qu'elles aboutissent au même stockage persistant, leur expérience, leur immédiateté et leurs cas d'usage diffèrent.

| Aspect | Configuration (Optimiseur) | Menu contextuel (Recherche) |
|---|---|---|
| **Accès** | Navigation vers Optimiseur → onglet Utilisateurs | Clic droit sur un fichier dans le bot Recherche |
| **Format** | Champ texte CSV (saisie manuelle) | Action clic-bouton instantanée |
| **Feedback** | Message de validation du `ConfigEntry` | `status_changed.emit()` + `_status_label.setText()` |
| **Prise d'effet** | Au prochain démarrage de l'application | Au prochain démarrage (même mécanisme) |
| **Idéal pour** | Ajout en lot, gestion de la liste complète | Blocage rapide pendant une recherche |

---

## 1. La méthode « Configuration » (Optimiseur)

### Emplacement

`Optimiseur` → onglet **Utilisateurs** → section **Bloqués** → champ `utilisateurs.liste_bloques`.

### Flux technique

1. L'utilisateur tape des noms d'utilisateur séparés par des virgules dans le `ConfigEntry`.
2. La valeur est persistée via `app_config.set("utilisateurs.liste_bloques", valeur)`.
3. Au démarrage suivant, `soulseek_client.py` lit cette valeur, la transforme via `_parse_blocked()` (ligne 72), et l'applique aux `SoulSeekSettings` (ligne 365).

```python
# soulseek_client.py — lecture au démarrage (lignes 244-245)
liste_bloques = app_config.get("utilisateurs.liste_bloques", "")
# ligne 365
blocked = _parse_blocked(liste_bloques)
```

### Cas d'usage

- Ajouter **plusieurs utilisateurs** d'un coup.
- **Consulder/modifier** la liste noire existante.
- **Débloquer** un utilisateur (suppression manuelle du nom).
- Premier paramétrage après installation.

---

## 2. La méthode « Menu contextuel » (Recherche)

### Emplacement

Bot **Recherche** → clic droit sur un résultat → **🚫 Bloquer {nom_utilisateur}**.

### Flux technique

1. L'utilisateur fait un clic droit sur un fichier dans les résultats de recherche.
2. Le menu contextuel affiche l'action `block_action = QAction(f"🚫 Bloquer {username}", self)`.
3. L'action déclenche `_on_block_user(username)` qui appelle `self._connexion_manager.block_user(username)`.
4. `block_user()` vérifie si l'utilisateur n'est pas déjà bloqué, concatène son nom à la liste CSV, puis persist via `app_config.set("utilisateurs.liste_bloques", ...)`.
5. Un signal `status_changed.emit()` et un `_status_label.setText("🚫 Utilisateur X bloqué")` offrent un **retour immédiat** à l'utilisateur.

```python
# connexion_manager.py — block_user()
def block_user(self, username: str) -> None:
    bloque = app_config.get("utilisateurs.liste_bloques", "")
    if username in bloque:
        logger.info("Utilisateur déjà bloqué : %s", username)
        return
    if bloque:
        bloque += f", {username}"
    else:
        bloque = username
    app_config.set("utilisateurs.liste_bloques", bloque)
    logger.info("Utilisateur bloqué : %s", username)
    self.status_changed.emit(f"🚫 Utilisateur {username} bloqué")
```

### Cas d'usage

- Bloquer un utilisateur **pendant une recherche**, sans perdre le contexte.
- Réaction rapide face à un comportement abusif (spam, fichiers de mauvaise qualité).
- Éviter la navigation vers l'Optimiseur.

---

## 3. Comparaison détaillée

### 3.1 Persistance — identique

Les deux méthodes écrivent **au même endroit** :

```
app_config → "utilisateurs.liste_bloques" → app_config.json
```

Le mécanisme de stockage est strictement identique. Il n'y a pas de « liste contextuelle parallèle ».

### 3.2 Prise d'effet — identique

Dans les deux cas, la liste bloqués est lue **au démarrage de l'application** par `soulseek_client.py`. La modification est persistée immédiatement dans `app_config.json`, mais son effet côté Soulseek (filtrage des messages, blocage des téléchargements, masquage des fichiers) n'est appliqué qu'au **prochain redémarrage**.

> ⚠️ **Nuance** : La version actuelle ne reconnecte pas dynamiquement le client Soulseek après un changement de la liste bloqués. C'est une amélioration potentielle future.

### 3.3 Feedback utilisateur — différent

| Méthode | Feedback immédiat |
|---|---|
| **Configuration** | Le `ConfigEntry` affiche la nouvelle valeur. Pas de notification explicite. |
| **Menu contextuel** | `block_user()` émet `status_changed` + `_status_label` affiche « 🚫 Utilisateur X bloqué ». Le retour est immédiat et visible. |

### 3.4 Vérification des doublons

| Méthode | Vérification |
|---|---|
| **Configuration** | Aucune — l'utilisateur peut taper le même nom deux fois. |
| **Menu contextuel** | `block_user()` vérifie `if username in bloque` et ignore les doublons. |

### 3.5 Format de saisie

| Méthode | Format |
|---|---|
| **Configuration** | CSV : `utilisateur1, utilisateur2, ...` (saisie manuelle) |
| **Menu contextuel** | Nom ajouté automatiquement au format CSV par `block_user()` |

---

## 4. Quand utiliser quelle méthode ?

### ✅ Configuration (Optimiseur)
- Gestion de **la liste complète** (ajout/suppression en lot).
- Consultation de tous les utilisateurs bloqués.
- **Déblocage** d'un utilisateur.
- Premier paramétrage.

### ✅ Menu contextuel (Recherche)
- Blocage **rapide** pendant une navigation dans les résultats.
- Réaction à un **comportement abusif** immédiat.
- Éviter la **rupture de contexte** (rester dans la vue Recherche).

### ⛔ Quand éviter le menu contextuel ?
- Si vous voulez **débloquer** un utilisateur (le menu contextuel n'offre pas cette option).
- Si vous bloquez **plusieurs utilisateurs** d'affilée (préférez la liste CSV dans l'Optimiseur).

---

## 5. Détail technique : `block_user()`

Méthode de `ConnexionManager` qui sert de pont entre le menu contextuel et `app_config` :

```python
def block_user(self, username: str) -> None:
    bloque = app_config.get("utilisateurs.liste_bloques", "")
    if username in bloque:
        return                                    # ← évite les doublons
    bloque += f", {username}" if bloque else username
    app_config.set("utilisateurs.liste_bloques", bloque)
    self.status_changed.emit(f"🚫 Utilisateur {username} bloqué")
```

**Limitation connue** : `username in bloque` est une recherche textuelle simple. Si un nom d'utilisateur contient un nom différent mais la même sous-chaîne, la détection de doublon peut être imprécise (ex: `"utilisateur" in "super_utilisateur"` → `True`). Amélioration possible : parser le CSV en `set` via `set(map(str.strip, bloque.split(',')))` puis tester `if username in bloque_set` pour une correspondance exacte.

---

## 6. Schéma récapitulatif

```
┌─────────────────────────────────────────────────────────────────┐
│                    app_config.json                                │
│  "utilisateurs.liste_bloques": "spammer, troll99, abuse_bot"     │
└─────────────────────────────────────────────────────────────────┘
          ▲                                        ▲
          │                                        │
┌─────────┴─────────┐              ┌────────────────┴────────────────┐
│ Configuration     │              │ Menu contextuel (Recherche)     │
│ Optimiseur        │              │                                │
│                   │              │ bot_recherche.py                │
│ center.py l. 734  │              │  block_action clic droit       │
│  ConfigEntry CSV   │              │  → _on_block_user(username)    │
│                   │              │  → connexion_manager            │
│ app_config.set()   │              │    .block_user(username)       │
└───────────────────┘              │  → app_config.set()            │
                                    └────────────────────────────────┘
                                            │
                                            ▼
                                  connexion_manager.py
                                  block_user() : vérifie doublon,
                                  concatène, persist, émet signal
```

---

## Voir aussi

- [Bloquer un utilisateur](bloquer-utilisateur.md) — guide général
- [Configuration utilisateurs](../technique/configuration-utilisateurs.md) — détails techniques du backend
- [Widget config utilisateurs](../technique/widget-config-utilisateurs-partages.md) — interface du ConfigEntry
