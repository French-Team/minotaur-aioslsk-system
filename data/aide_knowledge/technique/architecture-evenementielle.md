---
title: "Architecture événementielle — Vue d'ensemble"
category: technique
keywords: ["architecture", "evenement", "événement", "event", "eventbus", "signal", "slot", "qt", "pyqt", "thread", "threading", "qtimer", "asynchrone", "concurrent", "worker", "communication", "inter-bot", "flux", "donnee", "donnée"]
---

# Architecture événementielle — Vue d'ensemble

> **Niveau :** Avancé  
> **Temps de lecture :** 12 min  
> **Catégorie :** Architecture technique

---

## 1. Les 3 piliers de la communication

L'application utilise **3 mécanismes distincts** pour la communication entre composants, chacun adapté à un besoin spécifique :

```
┌─────────────────────────────────────────────────────┐
│              ARCHITECTURE ÉVÉNEMENTIELLE              │
│                                                       │
│  ┌──────────────────┐  ┌────────────┐  ┌──────────┐ │
│  │   EventBus        │  │ Signaux Qt │  │ Threads  │ │
│  │  (surveillance)   │  │  (UI)     │  │ (lourds) │ │
│  └────────┬─────────┘  └─────┬──────┘  └────┬─────┘ │
│           │                  │               │        │
│           ▼                  ▼               ▼        │
│  Persistant             Temps réel          Bloquant │
│  SQLite + purge         Synchrone UI       Async/IO  │
│  Centralisé             Découplé           Isolé     │
└──────────────────────────────────────────────────────┘
```

| Pilier | Technologie | Usage | Volatilité |
|--------|-------------|-------|------------|
| **EventBus** | `SurveillanceEvent` + SQLite | Journalisation, historique, surveillance | Persistant (7 jours) |
| **Signaux Qt** | `pyqtSignal` / `event_emitted` | Mise à jour UI, notifications | Temps réel |
| **Threads** | `QThread`, `Worker`, `threading` | Scan bibliothèque, réseau Soulseek | Éphémère |

---

## 2. L'EventBus — le système nerveux central

L'`EventBus` est le **bus d'événements centralisé** de l'application. Il est conçu comme un **singleton** accessible depuis n'importe quel composant.

### Cycle de vie d'un événement

```
[Émetteur]                [EventBus]                     [Consommateurs]
    │                         │                               │
    │  emit_event()           │                               │
    │────────────────────────>│                               │
    │                         │  1. Valide (catégorie,        │
    │                         │     sévérité)                 │
    │                         │  2. Persiste dans SQLite     │
    │                         │  3. Émet signal Qt           │
    │                         │     event_emitted.emit()     │
    │                         │──────────────┬───────────────│
    │                         │              │               │
    │                         │              ▼               │
    │                         │   ┌──────────────────┐       │
    │                         │   │ Bot Surveillance │       │
    │                         │   │ (connecté au     │       │
    │                         │   │  signal)         │       │
    │                         │   └──────────────────┘       │
    │                         │   ┌──────────────────┐       │
    │                         │   │ Toast Notification│       │
    │                         │   │ (popup UI)       │       │
    │                         │   └──────────────────┘       │
```

### Caractéristiques clés

- **Thread-safe** : peut être appelé depuis n'importe quel thread
- **Persistant** : stockage SQLite avec rétention de 7 jours
- **Timer de purge automatique** : `QTimer` toutes les heures
- **Pause/Reprise** : possibilité de suspendre l'émission et la persistance

---

## 3. Les signaux Qt — l'interface utilisateur en temps réel

Les signaux Qt assurent la **réactivité de l'interface** :

### Le signal `event_emitted`

C'est le pont entre l'EventBus et l'interface graphique :

```
┌─ EventBus ───────┐         ┌─ main_window.py ───────┐
│                   │         │                         │
│ event_emitted     │────────>│ event_emitted.connect(  │
│   .emit(event)    │         │   self._on_event)       │
│                   │         │                         │
└───────────────────┘         │ _on_event(event):       │
                              │   # Met à jour la UI    │
                              │   # Badge, notification │
                              └─────────────────────────┘
```

### Autres signaux Qt dans l'application

| Emplacement | Signal | Usage |
|-------------|--------|-------|
| `bot_surveillance.py` | `event_emitted.connect` | Affichage en temps réel des événements |
| `main_window.py` | `event_emitted.connect` | Mise à jour des badges de notification |
| `config.py` | `QTimer` | Debounce pour sauvegarde auto |
| `clock.py` | `QTimer` | Horloge du footer |
| `planificateur_service.py` | `QTimer` | Déclenchement des actions programmées |

---

## 4. Les threads — le travail lourd en arrière-plan

Les opérations bloquantes (réseau, scan disque) sont déléguées à des threads séparés pour ne pas bloquer l'UI.

### Hiérarchie des threads

```
┌─ Thread principal (UI) ─────────────────────────────┐
│  • PyQt5 event loop                                  │
│  • Toute l'interface graphique                        │
│  • Mise à jour des widgets                            │
└──────────────────────┬───────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
┌────────────────┐ ┌──────────┐ ┌──────────┐
│ QThread: scan  │ │ QThread: │ │ asyncio  │
│ bibliothèque   │ │ réseau   │ │ Soulseek │
│ (library_      │ │ (connexion│ │ client   │
│  scanner.py)   │ │ _manager)│ │          │
└────────────────┘ └──────────┘ └──────────┘
```

| Thread | Fichier | Usage |
|--------|---------|-------|
| **Scan bibliothèque** | `library_scanner.py` | Scan des dossiers partagés (Worker + QThread) |
| **Réseau** | `connexion_manager.py` | Connexion Soulseek, timeouts, reconnexion |
| **Soulseek (asyncio)** | `soulseek_client.py` | Bibliothèque asynchrone Soulseek |
| **Ordonnanceur** | `bot_ordonnanceur.py` | Traitement lourd des statistiques (Worker + QThread) |

### Communication inter-threads

Les threads **ne peuvent pas** modifier l'UI directement. Ils communiquent via :

1. **Signaux Qt** : thread sécurisé (le cadre Qt assure le pont)
2. **EventBus** : thread-safe, peut être appelé depuis n'importe où
3. **Files d'attente** : le `connexion_manager.py` utilise `concurrent.futures` pour les opérations réseau

---

## 5. QTimer — le temps qui passe

L'application utilise `QTimer` pour plusieurs tâches périodiques :

```
┌─ Timers actifs ────────────────────────────────────┐
│                                                      │
│  EventBus.purge_timer  ──── toutes les 1h           │
│  Planificateur         ──── selon règles définies   │
│  Horloge footer        ──── toutes les 1s           │
│  Config debounce       ──── 500ms après modif       │
│  Bot Accueil           ──── animation/rafraîchissement│
│  Bot Recherche         ──── debounce sur la saisie   │
│  Bot Optimiseur        ──── surveillance perf        │
│  Bot Surveillance      ──── mise à jour tableau      │
│  Bot Planificateur     ──── tick exécution           │
│  Bot Bibliothèque      ──── rafraîchissement liste   │
│  Bot Ordonnanceur      ──── mise à jour stats        │
│  Toast notification    ──── auto-fermeture           │
└──────────────────────────────────────────────────────┘
```

> 💡 Tous les timers sont sur le **thread principal** (UI). Pour les opérations longues, ils déclenchent des workers dans des threads séparés.

---

## 6. Diagramme de flux complet

Voici comment les 3 piliers interagissent lors d'un scénario typique :

### Scénario : téléchargement terminé

```
1. Soulseek reçoit la confirmation
       │
       ▼
2. connexion_manager.py détecte la fin
       │
       ├──▶ emit_event(category="transfert", ...)  ──▶ EventBus
       │       │                                         │
       │       └── SQLite (persistance)                  │
       │                                                 ▼
       │                                          event_emitted.emit()
       │                                                 │
       ▼                                                 ▼
3. bot_telechargement.py                          main_window.py
   met à jour sa liste                        affiche notification
   (signal direct)                            toast (popup)
```

### Scénario : scan de bibliothèque

```
1. Scan déclenché (manuel ou timer)
       │
       ▼
2. Worker lancé dans QThread dédié
       │
       ├──▶ Parcourt les dossiers
       ├──▶ Analyse les fichiers
       ├──▶ Écrit dans library_db
       │
       ▼
3. Signal de fin émis vers le thread principal
       │
       ▼
4. EventBus : emit_event(category="bibliotheque", ...)
       │
       ▼
5. bot_bibliotheque.py se rafraîchit
```

---

## 7. Bonnes pratiques et anti-patterns

### ✅ À faire

| Pratique | Pourquoi |
|----------|----------|
| Utiliser l'EventBus pour les événements **persistants** | Historique consultable 7 jours |
| Utiliser les signaux Qt pour les mises à jour **UI immédiates** | Thread-safe, temps réel |
| Déléguer les opérations **> 100ms** à un QThread | L'UI reste réactive |
| Vérifier `is_paused` avant d'émettre un événement critique | Évite la perte si le bus est en pause |
| Toujours fermer les connexions SQLite dans les workers | Évite les verrous de base |

### ❌ À éviter

| Anti-pattern | Problème |
|--------------|----------|
| Modifier un widget Qt depuis un thread | Crash (sauf si signal Qt) |
| Émettre des événements à très haute fréquence (> 10/s) | Sature la BDD SQLite et l'UI |
| Créer des QTimer dans des threads | Instable, préférer le thread principal |
| Oublier d'appeler `event_bus.close()` | Fichier SQLite verrouillé |

---

## Voir aussi

- [Guide technique de l'EventBus →](/technique/guide-eventbus)
- [Flux de données des événements →](/technique/flux-donnees-evenements)
- [Configuration debug →](/technique/configuration-debug)
- [FAQ outils de diagnostic →](/faq/debug-journaux)
