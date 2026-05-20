---
title: "Événements personnalisés — Puis-je créer mes propres catégories ou événements ?"
category: faq
keywords: ["personnalise", "personnalisé", "categorie", "catégorie", "evenement", "événement", "creer", "créer", "emettre", "emission", "emitter", "custom", "sur-mesure", "api", "programmation", "code", "python", "developeur", "développeur", "integration"]
---

# Événements personnalisés — Puis-je créer mes propres événements ?

> **Niveau :** Avancé  
> **Catégorie :** Développement — EventBus

---

## Questions fréquentes

### ❓ Puis-je ajouter une nouvelle catégorie d'événement ?

Les catégories sont **codées en dur** dans l'EventBus pour garantir la cohérence :

```python
# event_bus.py
CATEGORIES = (
    'reseau', 'transfert', 'recherche', 'bibliotheque',
    'configuration', 'erreur', 'bot', 'wishlist',
    'optimiseur', 'aide'
)
```

Si vous tentez d'émettre un événement avec une catégorie inconnue, l'EventBus lève une **`ValueError`** :

```python
bus.emit_event(category="ma_categorie")  # ❌ ValueError !
```

➡️ **Pour ajouter une catégorie**, il faut modifier le code source de `event_bus.py`. C'est possible si vous développez l'application (voir section 4).

➡️ **Sinon**, utilisez la catégorie existante la plus proche de votre besoin et renseignez le champ `source` pour distinguer votre composant :

```python
# ✅ Solution : utiliser 'bot' + source personnalisée
bus.emit_event(
    category="bot",
    title="Mon événement personnalisé",
    message="Ceci est un test depuis mon composant",
    source="mon_bot_perso"  # ← Identifiant unique
)
```

---

### ❓ Puis-je émettre des événements depuis mon propre code Python ?

**Oui, tout à fait.** L'EventBus est un singleton accessible depuis n'importe quel module :

```python
from src.services.event_bus import EventBus

# 1. Récupérer l'instance unique
bus = EventBus()

# 2. Émettre un événement
bus.emit_event(
    category="bot",           # Voir la liste des catégories
    severity="INFO",          # INFO, WARN ou ERROR
    title="Traitement terminé",
    message="Mon traitement s'est terminé avec succès",
    source="mon_script",      # Identifiant unique
    details={"duration": 45, "items": 123}  # Dict optionnel
)
```

> **Note :** L'EventBus est automatiquement initialisé au démarrage de l'application. Vous n'avez pas besoin de l'initialiser vous-même.

---

### ❓ Puis-je souscrire aux événements depuis mon code ?

**Oui.** Connectez-vous au signal Qt `event_emitted` :

```python
from src.services.event_bus import EventBus, SurveillanceEvent

def mon_callback(event: SurveillanceEvent):
    """Reçoit tous les événements en temps réel."""
    print(f"[{event.severity}] {event.category}: {event.title}")
    if event.details:
        print(f"  Détails: {event.details}")

# Souscrire
EventBus().event_emitted.connect(mon_callback)

# Pour se désinscrire
EventBus().event_emitted.disconnect(mon_callback)
```

**Important :**
- Le callback est appelé sur le **thread Qt principal**. Ne faites pas d'opérations bloquantes dedans.
- Pour traiter les événements sans bloquer l'UI, utilisez un `QTimer` ou un `Worker` (voir [Architecture événementielle →](/technique/architecture-evenementielle))

---

### ❓ Comment ajouter une nouvelle catégorie dans le code ?

Si vous développez l'application et souhaitez ajouter une catégorie :

1. **Modifiez le tuple `CATEGORIES`** dans `src/services/event_bus.py` :

```python
CATEGORIES = (
    'reseau', 'transfert', 'recherche', 'bibliotheque',
    'configuration', 'erreur', 'bot', 'wishlist',
    'optimiseur', 'aide', 'ma_nouvelle_categorie'  # ← Ajout
)
```

2. **Utilisez-la** dans vos `emit_event` :

```python
bus.emit_event(category="ma_nouvelle_categorie", ...)
```

3. **Mettez à jour le bot Surveillance** pour qu'il puisse filtrer par cette catégorie (si pertinent).

> ⚠️ **À savoir :** La liste des catégories est validée **à l'initialisation** de chaque événement. Si vous ajoutez une catégorie, vous pouvez l'utiliser immédiatement sans autre modification du code de l'EventBus.

---

### ❓ Puis-je émettre des événements depuis un thread ?

**Oui, l'EventBus est thread-safe.** Vous pouvez appeler `emit_event` depuis un `QThread`, un `Worker` ou un thread `threading` :

```python
# Depuis un QThread (scan bibliothèque, etc.)
class MonWorker(QObject):
    def run(self):
        # ... traitement long ...
        EventBus().emit_event(
            category="bot",
            severity="INFO",
            title="Traitement terminé",
            source="mon_worker"
        )
```

> L'EventBus utilisant `pyqtSignal` en interne, l'émission est automatiquement redirigée vers le thread principal pour la distribution aux consommateurs.

---

### ❓ Puis-je ajouter des données personnalisées à un événement ?

**Oui.** Le champ `details` accepte un dictionnaire Python :

```python
bus.emit_event(
    category="transfert",
    severity="INFO",
    title="Fichier traité",
    source="mon_bot",
    details={
        "fichier": "album.zip",
        "taille_octets": 125000000,
        "source_utilisateur": "user_soulseek",
        "duree_secondes": 45
    }
)
```

**Contraintes :**
- Le dictionnaire est sérialisé en **JSON** pour le stockage SQLite
- Les types doivent être JSON-serializables (`str`, `int`, `float`, `bool`, `list`, `dict`, `None`)
- Limitez la taille à **quelques Ko** pour ne pas alourdir la base

---

### ❓ Puis-je intercepter les événements pour les envoyer ailleurs (webhook, fichier log, API) ?

**Oui, avec une règle personnalisée.** Via le Planificateur, créez une action de type **« Exécuter un script »** :

```
Règle : « Webhook événements »
Déclencheur : toutes les 5 minutes
Condition : severity = 'ERROR'
Action : exécuter le script → C:\scripts\webhook.bat
```

Ou, si vous codez en Python :

```python
# script_webhook.py
from src.services.event_bus import EventBus
import sqlite3

# Lecture directe des derniers événements
conn = sqlite3.connect("data/bot_surveillance.db")
rows = conn.execute(
    "SELECT * FROM surveillance_events "
    "WHERE timestamp > datetime('now', '-10 minutes')"
).fetchall()

# Envoyer vers votre API
for row in rows:
    requests.post("https://mon-api.com/events", json=dict(row))

conn.close()
```

> ⚠️ Attention à ne pas créer de boucle : n'émettez pas d'événement depuis le script qui traite les événements.

---

**Voir aussi :** [Guide technique de l'EventBus →](/technique/guide-eventbus) | [Flux de données des événements →](/technique/flux-donnees-evenements) | [Règles conditionnelles →](/tutoriels/regles-conditionnelles-planificateur) | [Architecture événementielle →](/technique/architecture-evenementielle)
