---
title: "Système de traduction des erreurs (error_translator.py)"
category: technique
icon: 🌐
keywords:
  - error translator systeme
  - error translator système
  - traduction erreur soulseek
  - traduction erreur réseau
  - mapping erreur soulseek
  - Severite enum
  - severite enum
  - sévérité enum
  - Severite INFO WARNING ERROR SUCCES
  - fonction traduire
  - fonction emoji pour
  - fonction afficher
  - traduire exception
  - message erreur français
  - message erreur utilisateur
  - aioslsk exception traduction
  - timeout erreur traduction
  - ConnectionFailedError message
  - PeerConnectionError message
  - NoSuchUserError message
  - AuthenticationError message
  - NetworkError message
  - InvalidStateTransition erreur
  - fallback erreur inconnue
  - template message erreur
  - pattern isinstance traduction
  - niveau gravite erreur
  - niveau sévérité erreur
  - logger.error afficher
  - connexion_manager error translator
  - erreur bug interne soulseek
  - message erreur parametre
  - erreur configuration soulseek
  - erreur transfert fichier
  - erreur connexion p2p
  - erreur authentification soulseek
  - erreur session expiree
  - erreur session expirée
  - erreur port ecoute
  - erreur port écoute
  - dossier partage inaccessible
  - dossier partagé inaccessible
  - erreur serialisation
  - erreur désérialisation
  - erreur deserialisation
  - message inconnu soulseek
  - erreur placement requete
  - erreur placement requête
  - erreur lecture p2p
  - erreur ecriture p2p
  - erreur écriture p2p
  - emoji par severite
  - emoji par sévérité
  - format log erreur
  - systeme traduction
  - système traduction
  - traduction exception
  - message erreur
  - gestion erreur
  - niveau erreur
  - severite enum
  - sévérité erreur
  - erreur bug
  - erreur warning
  - erreur info
  - succes notification
  - succès notification
---

# 🌐 Système de traduction des erreurs (`error_translator.py`)

## Introduction

Le module `src/services/error_translator.py` (199 lignes) traduit les exceptions de la bibliothèque `aioslsk` et les erreurs réseau standard `asyncio` en **messages utilisateur en français**, accompagnés d'un **niveau de sévérité** et d'un **emoji**.

Il sert d'interface unique entre les erreurs techniques (exceptions Python) et l'affichage dans l'interface ou les logs.

---

## Architecture

```
Exception (aioslsk / asyncio)
        │
        ▼
  ┌─────────────────────┐
  │  error_translator   │
  │                     │
  │  traduire(exc) ─────┼──► (message_fr, Severite)
  │                     │
  │  emoji_pour(sev) ───┼──► "ℹ️" / "⚠️" / "🚨" / "✅"
  │                     │
  │  afficher(exc) ─────┼──► "[SEVERITE] message"
  └─────────────────────┘
        │
        ▼
  Logger.error()  /  Interface utilisateur
```

Le flux est simple : une exception est capturée → `traduire()` la mappe vers un message + sévérité → `emoji_pour()` donne l'icône → `afficher()` formate pour les logs.

---

## Énumération `Severite`

```python
class Severite(Enum):
    INFO    = "INFO"     # Erreur normale du réseau P2P
    WARNING = "WARNING"  # Problème de configuration ou temporaire
    ERROR   = "ERROR"    # Bug potentiel
    SUCCES  = "SUCCES"   # Succès (opération réussie)
```

Les 4 niveaux couvrent tous les cas :

| Niveau | Usage | Emoji |
|--------|-------|-------|
| `INFO` | Erreur normale du réseau P2P (timeout, déconnexion, fichier introuvable) | ℹ️ |
| `WARNING` | Problème de configuration (auth, port, dossier partagé) ou session invalide | ⚠️ |
| `ERROR` | Bug interne potentiel (transition état, sérialisation) | 🚨 |
| `SUCCES` | Opération réussie | ✅ |

---

## Fonction `traduire(exception)`

C'est le cœur du module. Elle utilise une série de `isinstance` pour mapper les exceptions vers des messages français contextualisés.

### 1. Erreurs réseau / asyncio

| Exception | Message | Sévérité |
|-----------|---------|----------|
| `asyncio.TimeoutError` | `⏱ Timeout — un peer n'a pas répondu à temps` | `INFO` |
| `asyncio.CancelledError` | `⏹ Tâche annulée — connexion interrompue` | `INFO` |

Ces deux erreurs sont normales sur le réseau P2P de Soulseek. Un timeout ne signifie pas un bug.

### 2. Connexions P2P / Utilisateurs

| Exception | Message | Sévérité |
|-----------|---------|----------|
| `ConnectionFailedError` | `🔴 Connexion P2P impossible vers {addr} — le pair est peut-être hors ligne` | `INFO` |
| `PeerConnectionError` | `⏱ Connexion indirecte (timeout) — le pair n'a pas répondu` | `INFO` |
| `NoSuchUserError` | `👤 Utilisateur introuvable — le nom est peut-être incorrect` | `WARNING` |

Les erreurs P2P sont fréquentes sur Soulseek. Les utilisateurs hors ligne ou avec un firewall strict génèrent ces exceptions.

### 3. Transferts de fichiers

| Exception | Message | Sévérité |
|-----------|---------|----------|
| `FileNotFoundError` | `📁 Fichier introuvable sur le serveur distant` | `INFO` |
| `FileNotSharedError` | `🚫 Fichier non partagé — le dossier distant a peut-être changé` | `INFO` |
| `TransferException` | `⬇ Erreur de transfert — le fichier n'a pas pu être téléchargé` | `INFO` |

### 4. Authentification / Configuration

| Exception | Message | Sévérité |
|-----------|---------|----------|
| `AuthenticationError` | `🔑 Échec d'authentification — vérifie ton mot de passe` | `WARNING` |
| `ListeningConnectionFailedError` | `🔌 Impossible d'ouvrir le port d'écoute — vérifie les paramètres réseau` | `WARNING` |
| `NetworkError` | `🌐 Erreur réseau — impossible de se connecter au serveur` | `WARNING` |
| `InvalidSessionError` | `🔄 Session invalide — reconnexion en cours` | `WARNING` |
| `SharedDirectoryError` | `📂 Erreur de dossier partagé — le répertoire n'existe pas ou est inaccessible` | `WARNING` |

Ces erreurs nécessitent une action de l'utilisateur : vérifier ses identifiants, ouvrir un port, ou corriger un chemin de dossier.

### 5. Bugs internes (ERROR)

| Exception | Message | Sévérité |
|-----------|---------|----------|
| `InvalidStateTransition` | `❌ BUG INTERNE — transition d'état invalide dans le protocole` | `ERROR` |
| `MessageSerializationError` | `❌ BUG — erreur de sérialisation d'un message sortant` | `ERROR` |
| `MessageDeserializationError` | `❌ BUG — erreur de désérialisation d'un message entrant` | `ERROR` |

Ces erreurs indiquent un vrai bug dans le code ou un message réseau mal formé.

### 6. Autres

| Exception | Message | Sévérité |
|-----------|---------|----------|
| `UnknownMessageError` | `📡 Message inconnu reçu du serveur — protocole ignoré` | `INFO` |
| `RequestPlaceFailedError` | `📋 Échec de placement de requête — le serveur a refusé la demande` | `INFO` |
| `ConnectionReadError` | `📖 Erreur de lecture sur une connexion P2P` | `INFO` |
| `ConnectionWriteError` | `✏ Erreur d'écriture sur une connexion P2P` | `INFO` |

### 7. Fallback

```python
# Si c'est une exception aioslsk non listée
if isinstance(exception, AioSlskException):
    return "❌ Erreur Soulseek — {exc}", ERROR
# Pour toute autre exception
return f"⚠️ Erreur inattendue — {exc}", WARNING
```

---

## Fonction `emoji_pour(severite)`

```python
def emoji_pour(severite: Severite) -> str:
    mapping = {
        Severite.INFO:    "ℹ️",
        Severite.WARNING: "⚠️",
        Severite.ERROR:   "🚨",
        Severite.SUCCES:  "✅",
    }
    return mapping.get(severite, "ℹ️")
```

---

## Fonction `afficher(exception)`

```python
def afficher(exception: Exception) -> str:
    message, severite = traduire(exception)
    return f"[{severite.value}] {message}"
```

Combine `traduire()` et un formatage simple pour produire une chaîne prête à être logguée.

Exemple de sortie : `[INFO] ⏱ Timeout — un peer n'a pas répondu à temps`

---

## Intégration dans l'application

Le module est utilisé principalement dans `src/services/connexion_manager.py` :

```python
from src.services.error_translator import traduire, afficher

# Dans les blocs try/except du ConnexionManager :
try:
    # opération réseau
except aioslsk_exc.ConnectionFailedError as e:
    message, _ = traduire(e)
    logger.error(afficher(e))
    self.event_bus.emit("error", message)
```

Le patron est systématique :
1. `traduire(e)` → récupère le message français (ignorant la sévérité avec `_`)
2. `afficher(e)` → formate pour le logger
3. Le message français est aussi envoyé à l'`EventBus` pour affichage dans l'interface

---

## Conclusion

Le système `error_translator.py` est un module de 199 lignes bien conçu qui :

- **Centralise** toute la logique de traduction des exceptions `aioslsk` en un seul endroit
- **Uniformise** les messages utilisateur avec des emojis et des sévérités
- **Protège** l'interface des exceptions techniques brutes (pas de traceback dans l'UI)
- **Catégorise** les erreurs : INFO (normal), WARNING (action utilisateur), ERROR (bug)
- **S'intègre** naturellement avec `EventBus` et le logger

Pour ajouter une nouvelle traduction, il suffit d'ajouter un `isinstance` dans `traduire()`.
