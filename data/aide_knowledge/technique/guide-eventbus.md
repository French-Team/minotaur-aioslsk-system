---
title: "Guide technique de l'EventBus — SurveillanceEvent, catégories, stockage"
category: technique
keywords: ["eventbus", "surveillance", "evenement", "événement", "categorie", "catégorie", "severite", "sévérité", "emit", "signal", "sqlite", "persistance", "purge", "stockage", "base", "donnee", "donnée", "migration"]
---

# Guide technique de l'EventBus

> **Niveau :** Avancé  
> **Temps de lecture :** 10 min  
> **Catégorie :** Architecture technique — Référence

---

## 1. Vue d'ensemble de la classe `EventBus`

L'**`EventBus`** est un singleton héritant de `QObject` qui centralise, persiste et distribue tous les événements de l'application.

```
EventBus (QObject)
├── Signal : event_emitted(SurveillanceEvent)
├── Stockage : SQLite (data/bot_surveillance.db)
├── Timer : purge automatique toutes les 1h
└── État : pause/reprise
```

### Accès à l'instance

```python
from src.services.event_bus import EventBus

bus = EventBus()  # Retourne l'instance unique (singleton)
```

---

## 2. Le modèle de données `SurveillanceEvent`

`SurveillanceEvent` est une **dataclass** Python qui représente un événement :

```python
@dataclass
class SurveillanceEvent:
    id: int | None          # Identifiant unique (auto-généré par SQLite)
    timestamp: datetime     # Horodatage de l'événement
    severity: str           # Niveau de gravité
    category: str           # Catégorie fonctionnelle
    title: str              # Titre court de l'événement
    message: str            # Description détaillée
    source: str             # Composant émetteur (ex: "connexion_manager")
    details: dict | None    # Données supplémentaires optionnelles
```

### Validation stricte

L'initialisation valide les champs `severity` et `category` :

```python
SEVERITIES = ('INFO', 'WARN', 'ERROR')
CATEGORIES = (
    'reseau', 'transfert', 'recherche', 'bibliotheque',
    'configuration', 'erreur', 'bot', 'wishlist',
    'optimiseur', 'aide'
)
```

Si une valeur invalide est fournie, une **`ValueError`** est levée.

### Les 3 sévérités

| Sévérité | Usage | Exemple |
|----------|-------|---------|
| `INFO` | Événement normal, informationnel | « Connexion réussie en tant que user123 » |
| `WARN` | Situation anormale mais non bloquante | « Déconnecté de Soulseek » |
| `ERROR` | Échec ou problème critique | « Erreur de connexion : timeout après 30s » |

### Les 10 catégories

| Catégorie | Émetteurs typiques | Exemple d'événement |
|-----------|-------------------|---------------------|
| `reseau` | connexion_manager, soulseek_client | Connexion / déconnexion / timeout |
| `transfert` | bot_telechargement | Téléchargement terminé / échoué |
| `recherche` | bot_recherche | Recherche lancée / résultats reçus |
| `bibliotheque` | bot_bibliotheque, library_scanner | Scan terminé / fichier ajouté |
| `configuration` | config.py, app_config | Paramètre modifié / sauvegardé |
| `erreur` | Tous | Erreur non catégorisée |
| `bot` | planificateur_service | Action programmée démarrée / terminée |
| `wishlist` | bot_wishlist | Souhait trouvé / ajouté à la file |
| `optimiseur` | bot_optimiseur | Profil changé / paramètres ajustés |
| `aide` | bot_aide (EventBus) | Question posée / article consulté |

---

## 3. Émettre un événement

### Signature de `emit_event`

```python
def emit_event(
    self,
    category: str,              # Obligatoire : une des CATEGORIES
    severity: str = "INFO",     # Optionnel : INFO par défaut
    title: str = "",            # Titre court
    message: str = "",          # Description
    source: str = "",           # Composant émetteur
    details: dict | None = None # Données supplémentaires
) -> None
```

### Exemples concrets depuis le code

```python
# Connexion réussie
bus.emit_event(
    severity="INFO",
    category="reseau",
    title="Connecté à Soulseek",
    message=f"Connexion réussie en tant que {username}",
    source="connexion_manager"
)

# Échec de connexion
bus.emit_event(
    severity="ERROR",
    category="reseau",
    title="Erreur de connexion",
    message=msg[:200],  # Tronqué à 200 caractères
    source="connexion_manager"
)

# Action de planification terminée
bus.emit_event(
    category="bot",
    severity="INFO",
    title="planificateur.action_terminee",
    message=f"{type_label} → Succès",
    source="planificateur"
)
```

### Comportement en cas de pause

Si le bus est en pause (`is_paused = True`), l'appel à `emit_event` est **ignoré silencieusement** :

```python
bus.pause()
bus.emit_event(...)  # Ignoré — rien n'est persisté ni émis
bus.resume()
bus.emit_event(...)  # Normal
```

---

## 4. Souscrire aux événements

### Mécanisme : signal Qt

L'EventBus expose un **signal Qt** `event_emitted` :

```python
event_emitted = pyqtSignal(object)  # object = SurveillanceEvent
```

Pour souscrire, connectez une fonction au signal :

```python
# Dans main_window.py
EventBus().event_emitted.connect(self._on_event)

def _on_event(self, event: SurveillanceEvent):
    """Callback appelé à chaque nouvel événement."""
    # Mise à jour de l'UI
    self._update_notification_badge(event)
```

### Consommateurs actuels

| Composant | Action |
|-----------|--------|
| `main_window.py` | Met à jour les badges de notification |
| `bot_surveillance.py` | Affiche les événements en temps réel |

> Les autres composants (recherche, téléchargement, etc.) **émettent** des événements mais ne souscrivent pas — ils utilisent leurs propres signaux Qt internes pour les mises à jour UI.

---

## 5. Stockage SQLite

### Base de données

- **Fichier** : `data/bot_surveillance.db`
- **Mode** : WAL (Write-Ahead Logging) pour les performances

### Schéma

```sql
CREATE TABLE IF NOT EXISTS surveillance_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,      -- ISO 8601 (ex: "2025-03-15T14:30:00")
    severity TEXT NOT NULL,       -- 'INFO' | 'WARN' | 'ERROR'
    category TEXT NOT NULL,       -- Une des CATEGORIES
    title TEXT NOT NULL,          -- Titre court
    message TEXT NOT NULL,        -- Description
    source TEXT NOT NULL DEFAULT '',
    details TEXT                  -- JSON optionnel
);

-- Index pour les requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_timestamp ON surveillance_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_category ON surveillance_events(category);
CREATE INDEX IF NOT EXISTS idx_severity ON surveillance_events(severity);
CREATE INDEX IF NOT EXISTS idx_source ON surveillance_events(source);
```

### Versionnage et migration

La base utilise `PRAGMA user_version` pour gérer les migrations :

```python
PRAGMA user_version;  # Lit le numéro de version
# Si version < N : exécute les migrations
# Puis : PRAGMA user_version = N
```

---

## 6. Purge automatique

Un **`QTimer`** interne déclenche la purge toutes les heures :

| Propriété | Valeur |
|-----------|--------|
| Intervalle | 3600 secondes (1h) |
| Rétention | 7 jours |
| Méthode | `purge_old()` |

```python
def purge_old(self) -> None:
    """Supprime les événements de plus de 7 jours."""
    seuil = datetime.now() - timedelta(days=7)
    cursor = self._db.execute(
        "DELETE FROM surveillance_events WHERE timestamp < ?",
        (seuil.isoformat(),)
    )
    # WAL checkpoint pour compacter la base
    self._db.execute("PRAGMA wal_checkpoint(TRUNCATE);")
```

### Fréquence de purge recommandée

| Usage | Rétention | Intervalle purge |
|-------|-----------|------------------|
| Défaut | 7 jours | 1 heure |
| Serveur 24/7 | 14-30 jours | 6 heures (à configurer) |
| Station de travail | 3 jours | 30 minutes |

---

## 7. Bonnes pratiques pour l'émission

### Quand utiliser `emit_event`

✅ **Émettez un événement quand :**
- Une opération critique se termine (succès ou échec)
- L'état du réseau change (connecté/déconnecté)
- Une action utilisateur est enregistrée (recherche, téléchargement)
- Une tâche planifiée s'exécute

❌ **N'émettez pas pour :**
- Les mises à jour UI fréquentes (préférez les signaux Qt directs)
- Les événements qui se produisent > 10 fois par seconde (risque de saturation SQLite)
- Les informations déjà tracées ailleurs (logs fichier, debug)

### Format des messages

| Bon | Mauvais |
|-----|---------|
| « Connexion réussie en tant que user123 » | « ok » |
| « Téléchargement terminé : album.zip (125 Mo) » | « fini » |
| « Erreur de connexion : timeout après 30s » | « erreur reseau » |

> Le `title` doit permettre d'identifier l'événement en un coup d'œil.
> Le `message` doit être auto-suffisant (compréhensible sans contexte externe).

---

## Voir aussi

- [Architecture événementielle — Vue d'ensemble →](/technique/architecture-evenementielle)
- [Flux de données des événements →](/technique/flux-donnees-evenements)
- [Exporter les données de surveillance →](/tutoriels/exporter-donnees-surveillance)
- [Configuration debug →](/technique/configuration-debug)
- [FAQ outils de diagnostic →](/faq/debug-journaux)
