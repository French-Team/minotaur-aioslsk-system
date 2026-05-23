# Logging Structuré — Spécification

> **Statut :** ✅ Toutes les phases (1+2+3+4) appliquées — 37 loggers dédiés
> **Dernière mise à jour :** 2026-05-22
> **Contexte :** Remplacer `logging.getLogger(__name__)` par des noms de logger dédiés (ex: `[ROOMS-LOOP]`, `[CLIENTS-ACTIFS]`) pour filtrer par composant dans le ServiceInspector.

---

## 1. 🎯 Problème

Actuellement, les logs ressemblent à ceci :

```
2026-05-22 07:35:47,788 [INFO] src.services.connexion_manager: Recherche lancée : 'techno' (ticket 2)
2026-05-22 07:35:55,063 [DEBUG] src.services.boucle_rooms: Room nicotine rejointe
2026-05-22 07:36:25,154 [DEBUG] src.gui.widgets.bots.bot_recherche: BotRecherche: 1822 clients Arès envoyés au ModesPanel
```

**Problèmes :**
1. Pas de moyen rapide de filtrer visuellement les logs par composant
2. Les préfixes sont incohérents (`BotRecherche: ` vs `Recherche lancée`)
3. Impossible de grep facilement pour un composant spécifique
4. Les logs de diagnostic `🔍 DIAG` sont mélangés avec les logs normaux

## 2. 📐 Format standardisé — Loggers dédiés

Chaque fichier utilise un **logger dédié** (ex: `logging.getLogger("[ROOMS-LOOP]")`) au lieu de `logging.getLogger(__name__)`. Cela permet au ServiceInspector de créer automatiquement une checkbox de filtre pour chaque composant.

### 2.1 Liste des loggers dédiés

| Logger | Composant | Fichier(s) |
|--------|-----------|------------|
| `[CONNEXION]` | ConnexionManager | `connexion_manager.py` |
| `[SOULSEEK]` | SoulseekService | `soulseek_client.py` |
| `[EVENTBUS]` | EventBus | `event_bus.py` |
| `[ROOMS-LOOP]` | BoucleRooms | `boucle_rooms.py` |
| `[CLIENTS-ACTIFS]` | ClientsActifsService | `clients_actifs_service.py` |
| `[RECHERCHE]` | BotRecherche | `bot_recherche.py` |
| `[TELECHARGEMENT]` | BotTelechargement | `bot_telechargement.py` |
| `[SURVEILLANCE]` | BotSurveillance | `bot_surveillance.py` |
| `[WISHLIST]` | BotWishlist | `bot_wishlist.py` |
| `[PLANIFICATEUR]` | BotPlanificateur | `bot_planificateur.py` |
| `[PLANIFICATEUR-SRV]` | PlanificateurService | `planificateur_service.py` |
| `[ACCUEIL]` | BotAccueil | `bot_accueil.py` |
| `[OPTIMISEUR]` | BotOptimiseur | `bot_optimiseur.py` |
| `[ROOMS-SERVICE]` | RoomService | `room_service.py` |
| `[BIBLIOTHEQUE]` | LibraryScanner | `library_scanner.py` |
| `[WORKFLOW]` | WorkflowInspector | `workflow_inspector.py` |

### 2.2 Format exact

```python
# AVANT (__name__)
logger = logging.getLogger(__name__)

# APRÈS (dedicated)
logger = logging.getLogger("[RECHERCHE]")
```

**Règles :**
1. Le nom du logger est TOUJOURS entre crochets, en MAJUSCULES
2. Les tirets `-` sont utilisés pour les noms composés (`CLIENTS-ACTIFS`, `ROOMS-LOOP`)
3. Les préfixes dans les messages (ex: `[CONNEXION]`) sont conservés pour la lisibilité dans les logs bruts
4. Le filtre du ServiceInspector agit sur le **nom du logger**, pas sur le message

---

## 3. 🧰 Helper de logging

Pour éviter la répétition, chaque service peut définir une constante ou un helper local :

### 3.1 Option A — Constante locale (recommandé pour commencer)

```python
# Dans chaque fichier, après le logger
_PREFIX = "[RECHERCHE]"

# Usage
logger.info("%s Recherche lancée : '%s' (ticket %s)", _PREFIX, query, ticket)
```

### 3.2 Option B — Logger personnalisé (plus tard)

```python
# src/services/logger_helper.py
class PrefixedLogger:
    """Logger avec préfixe structuré."""
    
    def __init__(self, name: str, prefix: str):
        self._logger = logging.getLogger(name)
        self._prefix = prefix
    
    def info(self, msg: str, *args, **kwargs):
        self._logger.info("%s %s", self._prefix, msg, *args, **kwargs)
    
    def debug(self, msg: str, *args, **kwargs):
        self._logger.debug("%s %s", self._prefix, msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self._logger.warning("%s %s", self._prefix, msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self._logger.error("%s %s", self._prefix, msg, *args, **kwargs)
```

### 3.3 Option C — Adapter le format du logger global

```python
# Dans main.py ou logging_config.py
class PrefixedFormatter(logging.Formatter):
    """Formatter qui ajoute un préfixe [COMPOSANT] automatiquement."""
    
    def format(self, record):
        # Le préfixe est stocké dans record.__dict__ via un filtre
        return super().format(record)
```

**Recommandation :** Commencer par l'Option A (constante locale, simple, rapide à implémenter) puis migrer vers l'Option B (helper centralisé) si besoin.

---

## 4. 🔄 Niveaux de log par composant

Chaque composant doit utiliser les niveaux de façon cohérente :

### 4.1 Définition des niveaux

| Niveau | Usage | Exemple |
|--------|-------|---------|
| `ERROR` | Panne, crash, échec fonctionnel | `[RECHERCHE] ERREUR: La recherche a échoué — serveur injoignable` |
| `WARNING` | Anomalie non bloquante, récupérable | `[CLIENTS-ACTIFS] ATTENTION: Aucun client actif détecté` |
| `INFO` | Changement d'état, étape importante | `[ROOMS-LOOP] Salon #techno rejoint (125 membres)` |
| `DEBUG` | Détail d'exécution, valeurs intermédiaires | `[RECHERCHE] Paquet reçu: ticket=3, fichiers=12` |

### 4.2 Règle anti-bruit

- **INFO** : max 1 log par cycle de boucle (résultat, pas action)
- **DEBUG** : tout le détail, activé/désactivé via config
- **WARNING** : événement inhabituel mais non critique
- **ERROR** : toujours avec `exc_info=True` si exception

---

## 5. ✅ Plan de migration — Terminé

### Phase 1 — Core services ✅

| Fichier | Logger | Fait |
|---------|--------|------|
| `connexion_manager.py` | `[CONNEXION]` | ✅ |
| `soulseek_client.py` | `[SOULSEEK]` | ✅ |
| `event_bus.py` | `[EVENTBUS]` | ✅ |

### Phase 2 — Boucles et bots ✅

| Fichier | Logger | Fait |
|---------|--------|------|
| `boucle_rooms.py` | `[ROOMS-LOOP]` | ✅ |
| `clients_actifs_service.py` | `[CLIENTS-ACTIFS]` | ✅ |
| `bot_recherche.py` | `[RECHERCHE]` | ✅ |
| `bot_telechargement.py` | `[TELECHARGEMENT]` | ✅ |
| `bot_surveillance.py` | `[SURVEILLANCE]` | ✅ |
| `bot_wishlist.py` | `[WISHLIST]` | ✅ |
| `bot_planificateur.py` | `[PLANIFICATEUR]` | ✅ |
| `bot_accueil.py` | `[ACCUEIL]` | ✅ |
| `bot_optimiseur.py` | `[OPTIMISEUR]` | ✅ |

### Phase 3 — Services secondaires ✅

| Fichier | Logger | Fait |
|---------|--------|------|
| `room_service.py` | `[ROOMS-SERVICE]` | ✅ |
| `library_scanner.py` | `[BIBLIOTHEQUE]` | ✅ |
| `workflow_inspector.py` | `[WORKFLOW]` | ✅ |

### Phase 4a — Services / Infrastructure ✅

| Fichier | Logger | Fait |
|---------|--------|------|
| `app_config.py` | `[APP-CONFIG]` | ✅ |
| `routers/connection.py` | `[CONNEXION-WEB]` | ✅ |
| `library_db.py` | `[BIBLIOTHEQUE-DB]` | ✅ |
| `ordonnanceur_service.py` | `[ORDONNANCEUR]` | ✅ |
| `main_window.py` | `[MAIN-WINDOW]` | ✅ |
| `search_history.py` | `[RECHERCHE-HIST]` | ✅ |
| `qss_inspector.py` | `[QSS-INSPECTOR]` | ✅ |
| `service_inspector.py` | `[SERVICE-INSPECTOR]` | ✅ |
| `layout/center.py` | `[CENTER-ZONE]` | ✅ |
| `planificateur_service.py` | `[PLANIFICATEUR-SRV]` | ✅ |
| `telechargement_history.py` | `[TELECHARGEMENT-HIST]` | ✅ |

### Phase 4b — Widgets / Diagnostics ✅

| Fichier | Logger | Fait |
|---------|--------|------|
| `bot_clients_actifs.py` | `[CLIENTS-ACTIFS-UI]` | ✅ |
| `toast_notification.py` | `[TOAST]` | ✅ |
| `asyncio_inspector.py` | `[ASYNCIO-INSPECTOR]` | ✅ |
| `bot_ordonnanceur.py` | `[ORDONNANCEUR-UI]` | ✅ |
| `connexion_monitor.py` | `[CONNEXION-MONITOR]` | ✅ |
| `timeout_controller.py` | `[TIMEOUT-CTRL]` | ✅ |
| `sysinternals_launcher.py` | `[SYSINTERNALS]` | ✅ |
| `bot_aide.py` | `[AIDE]` | ✅ |
| `bot_assistant.py` | `[ASSISTANT]` | ✅ |
| `bot_bibliotheque.py` | `[BIBLIOTHEQUE-UI]` | ✅ |
| `bot_recherche_modes.py` | `[RECHERCHE-MODES]` | ✅ |

### ServiceInspector — Filtres pré-populés ✅

Les checkbox de filtres pour tous les loggers ci-dessus sont créées dès l'ouverture de l'onglet « Flux des Logs » — pas besoin d'attendre qu'un premier log arrive.

> **Note :** Les logs ne sont pas utiles dans les scripts utilitaires (`_check_schema.py`, `_fix_accents.py`, `_read_eventbus.py`, `_temp_fix_/*.py`) car ils ne loggent jamais rien. Les `import logging` + `logger = ...` sont conservés dans les fichiers, mais retirés de `_STANDARD_LOGGERS` pour ne pas polluer les filtres du ServiceInspector.

**Total : 37 loggers standards** pré-populés dans `_STANDARD_LOGGERS`.

---

## 6. 🧪 Exemples concrets

### 6.1 Avant / Après

**AVANT :**
```python
# connexion_manager.py
logger.info("Connexion réussie: %s", username)
logger.info("Recherche lancée : '%s' (ticket %s)", query, ticket)
logger.warning("stop_search appelé mais aucune recherche active")

# boucle_rooms.py
logger.debug("Room %s rejointe", room_name)
logger.info("BoucleRooms: %d membres récupérés", len(membres))

# clients_actifs_service.py
logger.info("ClientsActifsService: %d clients synchronisés", len(actifs))
logger.debug("Statut %s: %s -> %s", username, ancien, nouveau)
```

**APRÈS :**
```python
# connexion_manager.py
logger.info("[CONNEXION] Connecté : %s", username)
logger.info("[RECHERCHE] Recherche lancée : '%s' (ticket %s)", query, ticket)
logger.warning("[RECHERCHE] stop_search appelé mais aucune recherche active")

# boucle_rooms.py
logger.debug("[ROOMS-LOOP] Salon #%s rejoint", room_name)
logger.info("[ROOMS-LOOP] %d membres récupérés", len(membres))

# clients_actifs_service.py
logger.info("[CLIENTS-ACTIFS] %d clients synchronisés", len(actifs))
logger.debug("[CLIENTS-ACTIFS] Statut %s: %s → %s", username, ancien, nouveau)
```

### 6.2 Filtrage visuel

Avec les préfixes, on peut facilement :

```bash
# Voir uniquement les logs de recherche
grep "\[RECHERCHE\]" logs.txt

# Voir les interactions entre connexion et rooms
grep -E "\[CONNEXION\]|\[ROOMS-LOOP\]" logs.txt

# Voir tous les diagnostics
grep "\[DIAG\]" logs.txt

# Exclure le bruit des statuts clients
grep -v "\[CLIENTS-ACTIFS\] Statut" logs.txt
```

---

## 7. 🔮 Évolution future

### 7.1 Couleurs dans la console

Quand l'application affiche les logs dans le **Service & Connection Inspector**, les préfixes pourraient être colorés :

```python
# Dans service_inspector.py
COULEURS_PREFIXES = {
    "[CONNEXION]": "#2196F3",      # Bleu
    "[RECHERCHE]": "#4CAF50",      # Vert
    "[CLIENTS-ACTIFS]": "#FFC107", # Jaune
    "[ROOMS-LOOP]": "#FF9800",     # Orange
    "[TELECHARGEMENT]": "#F44336", # Rouge
    "[SURVEILLANCE]": "#9C27B0",   # Violet
    "[DIAG]": "#FF5722",           # Orange foncé (warning)
}
```

### 7.2 Export filtré par préfixe

Le bouton "💾 Enregistrer" du Service Inspector pourrait avoir des filtres par préfixe, permettant d'exporter uniquement les logs d'un composant spécifique.

### 7.3 Métriques par composant

À terme, on pourrait compter le nombre de logs ERROR/WARNING par composant pour identifier les services les plus instables :

```python
# stats_logging.py
logs_par_composant = {
    "[RECHERCHE]": {"ERROR": 0, "WARNING": 0, "INFO": 0, "DEBUG": 0},
    "[CLIENTS-ACTIFS]": {"ERROR": 0, "WARNING": 0, "INFO": 0, "DEBUG": 0},
    ...
}
```

---

## 8. ✅ Critères de validation

| Critère | Attendue |
|---------|----------|
| Tous les logs INFO ont un préfixe | ✅ 100% |
| Tous les logs ERROR ont un préfixe | ✅ 100% |
| Les préfixes sont cohérents (même nom partout) | ✅ |
| grep `"\[RECHERCHE\]"` filtre correctement | ✅ |
| grep `"\[CLIENTS-ACTIFS\]"` filtre correctement | ✅ |
| Pas de régression fonctionnelle | ✅ Les tests passent |

---

> *Spec v1.0 — Proposition initiale le 2026-05-22*
