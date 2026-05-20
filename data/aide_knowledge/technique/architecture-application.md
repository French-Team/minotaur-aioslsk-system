---
title: "Architecture de l'application"
category: technique
keywords: ["architecture", "structure", "composant", "pattern", "mvc", "signal", "event"]
---

## Architecture de l'application

### Vue d'ensemble

L'application est construite avec **PySide6** (Qt pour Python) et suit une architecture découplée basée sur les signaux Qt.

```
┌─────────────────────────────────────────────────────────┐
│                    MainWindow                            │
├──────────┬─────────────────────────────┬─────────────────┤
│ Header   │      CenterZone             │   (right)       │
│ (zone    │   (contenu principal)       │   (réservé)     │
│  haute)  │                             │                 │
├──────────┴─────────────────────────────┴─────────────────┤
│                    Footer (12 bots)                      │
└─────────────────────────────────────────────────────────┘
```

### Composants principaux

| Composant | Rôle |
|-----------|------|
| **MainWindow** | Fenêtre principale, orchestre les connexions | 
| **Layout** | Gère la disposition Header / Center / Footer |
| **CenterZone** | Zone centrale avec pages empilées (QStackedWidget) |
| **FooterZone** | Barre de navigation avec les 12 bots |
| **HeaderZone** | Zone haute avec statut de connexion |
| **Bot Widgets** | Pages individuelles des 12 bots (QFrame) |

### Communication entre composants

L'application utilise deux mécanismes de communication :

#### 1. Signaux Qt (page_changed, etc.)

```python
# Un bot émet un signal pour changer de page
self.page_changed.emit("Recherche")

# Le footer ou le layout capte le signal et affiche la page
footer.page_changed.connect(self.center.show_page)
```

#### 2. EventBus (événements système)

```python
# Un service émet un événement système
EventBus().emit_event(
    category="reseau",
    severity="INFO",
    title="Connecté",
    message="Connexion réussie à Soulseek"
)

# Un watcher (Surveillance) affiche l'événement
```

### Flux de données

```
Soulseek Network
      ↓
SoulseekService (aioslsk)
      ↓
ConnexionManager (découplage, thread-safe)
      ↓
Bot Widgets (interface utilisateur)
      ↓
EventBus (persistance + émission)
      ↓
Bot Surveillance (affichage en temps réel)
```

### Données persistantes

| Fichier | Contenu |
|---------|---------|
| `data/bot_surveillance.db` | Événements système (7 jours) |
| `data/bot_bibliotheque.db` | Bibliothèque locale |
| `data/planificateur.db` | Actions planifiées |
| `data/telechargement_history.db` | Historique des transferts |
| `data/bot_aide.db` | Articles d'aide et historique |
| `data/bot_accueil_history.json` | Historique de chat Accueil |
| `data/description.json` | Description des bots |
