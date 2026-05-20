---
title: "Flux de données des événements — Circulation entre services, bots et UI"
category: technique
keywords: ["flux", "donnee", "donnée", "evenement", "événement", "circulation", "parcours", "bottelechargement", "wishlist", "recherche", "bibliotheque", "connexion", "planificateur", "scenario", "scénario"]
---

# Flux de données des événements

> **Niveau :** Avancé  
> **Temps de lecture :** 8 min  
> **Catégorie :** Architecture technique — Parcours concrets

---

## 1. Principe général

Les événements suivent un parcours en **3 étapes** dans l'application :

```
Étape 1              Étape 2              Étape 3
[Émission]           [Transit]            [Consommation]
     │                    │                    │
     ▼                    ▼                    ▼
Service/Bot ──▶   EventBus +   ──▶   UI / Bots /
(Python)           SQLite              Notifications
```

Ce document détaille les **parcours concrets** pour chaque type d'événement, basés sur le code de l'application.

---

## 2. Flux réseau — Connexion/Déconnexion

### Parcours complet

```
connexion_manager.py
    │
    ├── Connexion réussie
    │   └── emit_event(severity="INFO", category="reseau",
    │                   title="Connecté à Soulseek",
    │                   message=f"Connexion réussie en tant que {username}")
    │
    ├── Déconnexion
    │   └── emit_event(severity="WARN", category="reseau",
    │                   title="Déconnecté de Soulseek",
    │                   message="Le client a été déconnecté du serveur")
    │
    └── Erreur
        └── emit_event(severity="ERROR", category="reseau",
                        title="Erreur de connexion",
                        message=msg)  # Tronqué à 200 caractères
```

### Consommateurs

| Consommateur | Réaction |
|-------------|----------|
| **main_window.py** | Met à jour le badge de connexion dans le footer (vert/rouge) |
| **bot_surveillance.py** | Ajoute l'événement à la liste en temps réel |
| **Toast notification** | Popup en cas de déconnexion (si activé) |
| **Planificateur** | Déclenche les règles « Connexion perdue » le cas échéant |

### Code concerné

- Émetteur : `src/services/connexion_manager.py` (lignes ~58-63)
- Émetteur : `src/services/event_bus.py` (timeout interne)
- Définition du signal : `src/gui/main_window.py` (`event_emitted.connect`)

---

## 3. Flux transfert — Téléchargements

### Parcours complet

```
bot_telechargement.py
    │
    ├── Téléchargement démarré
    │   └── emit_event(category="transfert", severity="INFO",
    │                   title=f"Téléchargement : {fichier}")
    │
    ├── Téléchargement terminé
    │   └── emit_event(category="transfert", severity="INFO",
    │                   title=f"Terminé : {fichier}",
    │                   message=f"{taille} téléchargés")
    │
    ├── Téléchargement échoué
    │   └── emit_event(category="transfert", severity="WARN",
    │                   title=f"Échec : {fichier}",
    │                   message=raison_erreur)
    │
    └── File d'attente modifiée
        └── emit_event(category="transfert", severity="INFO",
                        title="File d'attente mise à jour",
                        message=f"{nb_actifs} actifs, {nb_attente} en attente")
```

### Interactions avec les autres composants

```
bot_telechargement.py
    │
    ├──▶ EventBus ──▶ bot_surveillance.py (historique)
    │
    ├──▶ Signal Qt direct ──▶ Mise à jour du compteur dans le footer
    │
    └──▶ Signal Qt direct ──▶ Mise à jour de la liste des téléchargements
```

---

## 4. Flux recherche — Requêtes et résultats

### Parcours complet

```
bot_recherche.py
    │
    ├── Recherche lancée
    │   └── emit_event(category="recherche", severity="INFO",
    │                   title=f"Recherche : {requête}")
    │
    ├── Résultats reçus
    │   └── emit_event(category="recherche", severity="INFO",
    │                   title=f"{nb} résultats pour {requête}")
    │
    └── Timeout
        └── emit_event(category="recherche", severity="WARN",
                        title=f"Timeout : {requête}")
```

### Code concerné

- Émetteur : `src/gui/widgets/bots/bot_recherche.py` (3 appels à emit_event)

---

## 5. Flux wishlist — Souhaits automatiques

### Parcours complet

```
bot_wishlist.py
    │
    ├── Souhait ajouté
    │   └── emit_event(category="wishlist", severity="INFO",
    │                   title=f"Nouveau souhait : {mot_clé}")
    │
    └── Souhait trouvé
        └── emit_event(category="wishlist", severity="INFO",
                        title=f"Souhait trouvé : {fichier}",
                        message=f"{nb_sources} sources disponibles")
```

---

## 6. Flux bibliothèque — Scan des partages

### Parcours complet

```
bot_bibliotheque.py
    │
    ├── Scan démarré
    │   └── emit_event(category="bibliotheque", severity="INFO",
    │                   title="Scan de la bibliothèque démarré")
    │
    ├── Scan terminé
    │   └── emit_event(category="bibliotheque", severity="INFO",
    │                   title=f"Scan terminé : {nb_fichiers} fichiers")
    │
    └── Scan échoué
        └── emit_event(category="bibliotheque", severity="ERROR",
                        title="Erreur de scan",
                        message=raison)
```

### Note technique : threading

Le scan de bibliothèque s'exécute dans un **QThread dédié** (`library_scanner.py`). L'émission d'événements depuis ce thread est possible car l'EventBus est thread-safe :

```
thread principal            QThread (scan)
    │                           │
    │                           ├── Parcourt les dossiers
    │                           ├── Analyse les fichiers
    │                           ├── Écrit dans library_db
    │                           └── emit_event (thread-safe)
    │                               │
    ◄───────────────────────────────┘
    │
    ├── event_emitted.emit() → UI
    └── Bot bibliothèque se rafraîchit
```

---

## 7. Flux optimiseur — Changement de profil

### Parcours complet

```
bot_optimiseur.py
    │
    ├── Profil changé
    │   └── emit_event(category="optimiseur", severity="INFO",
    │                   title=f"Profil : {nom_profil}",
    │                   message=f"Mode peer: {mode}, Upload: {limite} KB/s")
    │
    ├── Paramètre ajusté
    │   └── emit_event(category="optimiseur", severity="INFO",
    │                   title=f"Paramètre : {param} → {valeur}")
    │
    └── Profil sauvegardé
        └── emit_event(category="optimiseur", severity="INFO",
                        title=f"Profil sauvegardé : {nom}")
```

---

## 8. Flux planificateur — Actions programmées

### Parcours complet

```
planificateur_service.py
    │
    ├── Action démarrée (manuelle)
    │   └── emit_event(category="bot", severity="INFO",
    │                   title="planificateur.action_demarree",
    │                   message=f"{action_type} → Exécution manuelle")
    │
    ├── Action démarrée (automatique)
    │   └── emit_event(category="bot", severity="INFO",
    │                   title="planificateur.action_demarree",
    │                   message=f"{action_type} → Exécution automatique")
    │
    ├── Action réussie
    │   └── emit_event(category="bot", severity="INFO",
    │                   title="planificateur.action_terminee",
    │                   message=f"{type_label} → Succès")
    │
    └── Action récurrente
        └── emit_event(category="bot", severity="INFO",
                        title="planificateur.action_terminee",
                        message=f"{type_label} → Récurrente")
```

Note : le planificateur utilise un **format de titre spécifique** avec des préfixes en anglais (ex: `planificateur.action_demarree`) pour faciliter le filtrage programmatique.

---

## 9. Cartographie complète des flux

```
┌──────────────────────────────────────────────────────────────────┐
│                    CARTographie DES FLUX EVENTBUS                 │
├────────────┬──────────────┬────────────┬─────────────────────────┤
│ Catégorie  │ Émetteur      │ Qt Signal  │ Consommateur principal  │
├────────────┼──────────────┼────────────┼─────────────────────────┤
│ reseau     │ connexion_   │ Oui        │ main_window (badge)     │
│            │ manager      │            │ bot_surveillance        │
├────────────┼──────────────┼────────────┼─────────────────────────┤
│ transfert  │ bot_         │ Oui        │ bot_surveillance        │
│            │ telechargement│ (direct)  │ footer (compteur)       │
├────────────┼──────────────┼────────────┼─────────────────────────┤
│ recherche  │ bot_recherche│ Non        │ bot_surveillance        │
├────────────┼──────────────┼────────────┼─────────────────────────┤
│ biblio-    │ bot_         │ Non        │ bot_bibliotheque        │
│ thèque     │ bibliotheque │ (signal    │ (rafraîchissement)      │
│            │ library_     │  interne)  │                         │
│            │ scanner      │            │                         │
├────────────┼──────────────┼────────────┼─────────────────────────┤
│ bot        │ planificateur│ Non        │ bot_surveillance        │
│            │ _service     │            │                         │
├────────────┼──────────────┼────────────┼─────────────────────────┤
│ wishlist   │ bot_wishlist │ Non        │ bot_surveillance        │
├────────────┼──────────────┼────────────┼─────────────────────────┤
│ optimiseur │ bot_         │ Non        │ bot_surveillance        │
│            │ optimiseur   │            │                         │
├────────────┼──────────────┼────────────┼─────────────────────────┤
│ aide       │ bot_aide     │ Non        │ bot_surveillance        │
└────────────┴──────────────┴────────────┴─────────────────────────┘
```

---

## 10. Métriques et monitoring

### Ce que vous pouvez mesurer

| Métrique | Requête SQL | Interprétation |
|----------|-------------|----------------|
| Volume total | `SELECT COUNT(*) FROM surveillance_events` | Activité globale |
| Par catégorie | `SELECT category, COUNT(*) ... GROUP BY category` | Répartition |
| Taux d'erreur | `SELECT COUNT(*) WHERE severity='ERROR'` | Santé de l'app |
| Période de pointe | `SELECT strftime('%H', timestamp) ... GROUP BY 1` | Heures d'activité |
| Sources bruyantes | `SELECT source, COUNT(*) ... GROUP BY source ORDER BY 2 DESC` | Composants bavards |

### Exemple : analyse des dernières 24h

```python
from src.services.event_bus import EventBus
import sqlite3

bus = EventBus()
conn = sqlite3.connect("data/bot_surveillance.db")
conn.row_factory = sqlite3.Row

# Événements des dernières 24h
rows = conn.execute("""
    SELECT category, severity, COUNT(*) as count
    FROM surveillance_events
    WHERE timestamp > datetime('now', '-1 day')
    GROUP BY category, severity
    ORDER BY category, severity
""").fetchall()

for row in rows:
    print(f"[{row['category']:12}] {row['severity']:5}: {row['count']}")

conn.close()
```

---

## Voir aussi

- [Architecture événementielle — Vue d'ensemble →](/technique/architecture-evenementielle)
- [Guide technique de l'EventBus →](/technique/guide-eventbus)
- [Exporter les données de surveillance →](/tutoriels/exporter-donnees-surveillance)
- [Analyser les statistiques avec l'Ordonnanceur →](/tutoriels/analyser-statistiques-ordonnanceur)
