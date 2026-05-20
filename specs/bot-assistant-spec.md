# Bot Assistant — Spécification technique

> **Date :** 2026-03-17  
> **Objet :** Bot "Assistant" — assistant du bot Accueil (configuration, diagnostic, recommandations)  
> **Statut :** Spécification pré-implémentation

---

## 1. Concept fondamental

Le bot **Assistant** n'est **pas** un assistant pour l'utilisateur humain.  
C'est **l'assistant du BotAccueil**.

Il travaille **en coulisses** : ses réponses sont affichées **via le chat de BotAccueil**, jamais directement à l'utilisateur. Il combine trois rôles :

| Rôle | Description |
|------|-------------|
| **Délégation de tâches** | BotAccueil lui confie des tâches complexes (compréhension, formulation, exécution) |
| **Base de connaissances** | Il connaît l'état de l'application, les actions possibles, les logs |
| **Exécuteur d'actions** | Il peut suggérer ou initier des actions de configuration / diagnostic |

> ⚠️ **IMPORTANT** : Contrairement à BotAide (documentation statique), Assistant est **orienté action** — il utilise l'état réel de l'application, les logs, et les actions possibles, PAS des fichiers `.md` statiques.

---

## 2. Architecture — Dépendances et interactions

### 2.1 Dépendances

- **PySide6** (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QTimer)
- **`src.gui.widgets.bots.bot_accueil`** (BotAccueil) — communication directe Signal/Slot
- **`src.gui.layout.center`** (CenterZone) — page enregistrée comme dashboard
- **SQLite3** (stdlib) — base dédiée `bot_assistant.db`
- **`src.services.soulseek_client`** (soulseek_service) — accès à l'état de l'application
- **`src.services.event_bus`** (EventBus) — consultation des logs d'événements (lecture seule)

### 2.2 Interaction avec le bot Accueil — Vue d'ensemble

```
Utilisateur → BotAccueil (saisit un message)
    ↓
BotAccueil.match_intent() analyse l'intention
    ↓
Si intention = configuration / diagnostic / recommandation / tutoriel :
    ↓ SIGNAL/SLOT DIRECT (pas EventBus)
BotAssistant reçoit : {action_type, query}
    ↓
BotAssistant traite :
  - Consulte l'état de l'application
  - Consulte les logs récents (EventBus)
  - Consulte sa base SQLite (historique)
  - Formule une réponse structurée
    ↓ SIGNAL/SLOT DIRECT
BotAccueil reçoit : {message, suggestions, action, navigation}
    ↓
BotAccueil affiche la réponse dans le chat de l'utilisateur
    ↓ Optionnel
Assistant enregistre l'interaction dans bot_assistant.db
```

### 2.3 Diagramme de flux détaillé

```
┌─────────────────┐     Signal/Slot      ┌──────────────────────┐
│   BotAccueil    │ ◄──────────────────► │    BotAssistant      │
│  (QFrame)       │   assistant_request  │   (QFrame, coulisses)│
│                 │   assistant_response │                      │
│  Chat visible   │                      │  Dashboard visible   │
│  à l'utilisateur│                      │  (page dédiée)       │
└─────────────────┘                      └──────────┬───────────┘
                                                    │
                                                    ▼
                                           ┌──────────────────┐
                                           │  SQLite dédiée   │
                                           │ bot_assistant.db │
                                           │ (actions, logs,  │
                                           │  diagnostics)    │
                                           └──────────────────┘
```

### 2.4 Communication — Signal/Slot Qt direct

Pas d'EventBus pour la communication BotAccueil ↔ Assistant. Utilisation de signaux Qt directs :

```python
# Dans BotAccueil :
assistant_request = Signal(str, str)  # action_type (Literal["config","diagnostic","recommendation","tutorial"]), query

# Dans BotAssistant :
assistant_response = Signal(str)  # Réponse JSON avec la réponse structurée
```

**Validation du signal `assistant_request`** : `action_type` doit être une des valeurs autorisées. BotAssistant valide en interne et convertit les types invalides en réponse d'erreur :

```python
_VALID_ACTION_TYPES = frozenset({"config", "diagnostic", "recommendation", "tutorial"})

def _on_assistant_request(self, action_type: str, query: str) -> None:
    if action_type not in _VALID_ACTION_TYPES:
        logger.warning("Assistant: type d'action invalide %r", action_type)
        # Retourne une réponse d'erreur au lieu de lever une exception
        ...  # voir section 7.3 pour le traitement complet
```

### 2.5 Canal EventBus (consultation uniquement)

Assistant **consulte** l'EventBus pour obtenir les logs/événements récents (diagnostic), mais n'utilise **pas** EventBus pour recevoir ses requêtes.

---

## 3. Base de données SQLite — `bot_assistant.db`

### 3.1 Emplacement

```
data/bot_assistant.db
```

### 3.2 Tables

#### Table `interactions`

| Colonne | Type | Contrainte | Description |
|---------|------|-----------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Identifiant unique |
| `action_type` | TEXT | NOT NULL CHECK(action_type IN ('config','diagnostic','recommendation','tutorial')) | Type d'action |
| `query` | TEXT | NOT NULL | Question/requête originale de l'utilisateur |
| `response` | TEXT | NOT NULL | Réponse JSON complète |
| `success` | INTEGER | NOT NULL DEFAULT 1 | Succès de l'action (1 = oui, 0 = échec) |
| `error_message` | TEXT | | Message d'erreur si `success = 0` |
| `created_at` | TEXT | NOT NULL DEFAULT CURRENT_TIMESTAMP | Date de l'interaction |

#### Table `diagnostics`

| Colonne | Type | Contrainte | Description |
|---------|------|-----------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Identifiant unique |
| `check_type` | TEXT | NOT NULL | Type de diagnostic : `connexion`, `transfert`, `partage`, `performance` |
| `status` | TEXT | NOT NULL | `ok`, `warning`, `error` |
| `message` | TEXT | NOT NULL | Message descriptif |
| `suggestion` | TEXT | | Suggestion pour corriger le problème |
| `checked_at` | TEXT | NOT NULL DEFAULT CURRENT_TIMESTAMP | Date du diagnostic |

---

## 4. Tâches et intentions prises en charge

### 4.1 Intentions reconnues par BotAccueil → déléguées à Assistant

| Intention | Type d'action | Exemple de question utilisateur |
|-----------|--------------|-------------------------------|
| Configuration réseau | `config` | "Comment configurer le port d'écoute ?" |
| Configuration partages | `config` | "Je veux partager mon dossier musique" |
| Configuration téléchargements | `config` | "Où sont sauvegardés mes fichiers ?" |
| Configuration générale | `config` | "Comment changer ma description ?" |
| Diagnostic connexion | `diagnostic` | "Je n'arrive pas à me connecter" |
| Diagnostic lenteur | `diagnostic` | "Pourquoi mes téléchargements sont lents ?" |
| Recommandation bot | `recommendation` | "Quel bot utiliser pour chercher des fichiers ?" |
| Recommandation usage | `recommendation` | "Comment optimiser mes téléchargements ?" |
| Tutoriel étape | `tutorial` | "Comment planifier un téléchargement ?" |

### 4.2 Logique de matching interne d'Assistant

Contrairement à BotAccueil qui a `_match_intent()` basé sur des mots-clés dans KNOWLEDGE, Assistant utilise un **système de règles interne** pour chaque `_handle_*` :

```python
# Règles de matching pour _handle_config
_CONFIG_RULES: list[tuple[list[str], str, str]] = [
    # (mots_clés, type_config, réponse_clé)
    (["port", "écoute", "réseau"], "reseau", "port_ecoute"),
    (["partage", "dossier", "partager"], "partages", "dossier_1_chemin"),
    (["destination", "sauvegarde", "téléchargement"], "telechargement", "dossier_destination"),
    (["description", "profil"], "general", "description_profil"),
]

def _match_config(self, query: str) -> tuple[str, str] | None:
    """Analyse la query et retourne (section_config, clé_param) ou None."""
    q = query.lower()
    for keywords, section, key in _CONFIG_RULES:
        if any(kw in q for kw in keywords):
            return (section, key)
    return None  # Non reconnu → réponse générique
```

Même principe pour `diagnostic`, `recommendation`, `tutorial`.

### 4.3 Réponse structurée (objet JSON)

```json
{
  "message": "Réponse textuelle affichée dans le chat...",
  "severity": "info",
  "suggestions": [
    {"label": "Aller dans Configuration réseau", "action": "navigate", "bot": "Général"},
    {"label": "Voir le tutoriel détaillé", "action": "navigate", "bot": "Aide", "article": "config-reseau"}
  ],
  "navigation": {
    "bot": "Général",
    "icon": "⚙️"
  },
  "data": {
    "status": "ok",
    "details": {}
  }
}
```

### 4.4 Champs de la réponse JSON

| Champ | Type | Obligatoire | Description |
|-------|------|-------------|-------------|
| `message` | string | Oui | Texte affiché dans le chat de BotAccueil (support HTML léger) |
| `severity` | string | Oui | `info`, `warning`, `error`, `success` |
| `suggestions` | array | Non | Liste de suggestions cliquables pour l'utilisateur |
| `navigation` | object | Non | Navigation vers une autre page (bot) si pertinent |
| `data` | object | Non | Données supplémentaires (statistiques, état, etc.) |

### 4.5 Gestion d'erreurs

Si une requête échoue ou n'est pas comprise, Assistant retourne une réponse d'erreur standardisée :

```json
{
  "message": "Désolé, je n'ai pas compris ta demande. Tu peux reformuler ou consulter le bot <b>Aide</b> pour plus d'informations.",
  "severity": "warning",
  "suggestions": [
    {"label": "❓ Consulter l'Aide", "action": "navigate", "bot": "Aide"}
  ],
  "data": {"error": "unknown_intent", "query": "..."}
}
```

Cas d'échec spécifiques :

| Condition | Réponse |
|-----------|---------|
| `action_type` invalide | `ValueError` catchée en interne → réponse `severity: "error"` émise + interaction persistée en échec |
| Aucune règle de matching trouvée | `severity: "warning"`, message générique + suggestion vers Aide |
| Service soulseek injoignable | `severity: "error"`, "Impossible de consulter l'état de l'application" |
| Base SQLite inaccessible | Log + réponse "error", pas de persistance |

---

## 5. Sources de données

### 5.1 État de l'application

Assistant a accès à l'état actuel via `src.services.soulseek_client` :

| Information | Source |
|-------------|--------|
| Connecté / déconnecté | `soulseek_service.is_connected` (bool) |
| Nom d'utilisateur | `soulseek_service.username` (str) |
| Téléchargements en cours | Signaux `transfer_added` / `transfer_removed` / `transfer_progress` (pas de liste directe) |
| Partages | Via `ClientsActifsService` ou config |
| Paramètres actuels | Via les pages de configuration |

✅ **Validé après recherche code source** :
- `is_connected` (property, bool) — existe
- `username` (property, str) — existe
- `active_downloads` — **n'existe pas** ; remplacer par abonnement aux signaux transfer
- `connexion_status` — **n'existe pas** ; remplacer par `is_connected`

**Propriétés exactes du service** : `client` (SoulSeekClient | None), `is_connected` (bool),
`username` (str). Méthodes : `connect()`, `disconnect()`, `pause_transfer()`,
`resume_transfer()`, `abort_transfer()`. Signaux : `connection_changed`,
`transfer_added`, `transfer_removed`, `transfer_progress`.

### 5.2 Logs / Historique des événements — EventBus

Assistant consulte les événements via `EventBus().query()` ou `EventBus().get_recent()`.  
Les signatures exactes ont été vérifiées dans le code source (`src/services/event_bus.py`, ligne 267+) :

#### Signature de `query()`

```python
def query(
    self,
    *,
    category: str | None = None,
    severity: str | None = None,
    source: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[SurveillanceEvent]:
```

> ⚠️ Tous les paramètres sont **keyword-only** (le `*` force `category=`, pas `"transfert"` en positionnel).

#### Signature de `get_recent()`

```python
def get_recent(self, limit: int = 50) -> list[SurveillanceEvent]:
```

#### Structure de `SurveillanceEvent` (dataclass)

```python
@dataclass
class SurveillanceEvent:
    id: int = 0
    timestamp: str = ""          # ISO 8601
    severity: str = "INFO"       # "INFO" | "WARN" | "ERROR"
    category: str = "bot"        # Voir catégories ci-dessous
    title: str = ""
    message: str = ""            # Format transfert : "TELECHARGEMENT /path/file — username"
    source: str = ""             # "SoulseekService"
    details: dict[str, Any] | None = None
    created_at: str = ""
```

#### Catégories disponibles

Regroupement des constantes dans `EventBus` :

```python
CATEGORIES = (
    "reseau", "transfert", "recherche", "bibliotheque",
    "configuration", "erreur", "bot", "wishlist",
    "optimiseur", "aide",
)
```

#### Utilisation concrète pour Assistant

```python
# Obtenir les 20 derniers événements de transfert
from src.services.event_bus import EventBus
events = EventBus().query(category="transfert", limit=20)

# Analyser les messages pour extraire username + remote_path
active: dict[str, dict[str, str]] = {}  # clé = "{username}:{remote_path}"
for evt in events:
    if " — " in evt.message:
        path_part, user_part = evt.message.rsplit(" — ", 1)
        # path_part = "TELECHARGEMENT /chemin/fichier.mp3"
        # user_part = "nom_utilisateur"
        key = f"{user_part}:{path_part.split(' ', 1)[-1]}"
        active[key] = {"username": user_part, "remote_path": path_part.split(' ', 1)[-1]}

# Les données sont ensuite utilisées dans _get_recent_logs()
```

#### Méthodes d'Assistant qui utilisent EventBus

| Méthode | Appel EventBus | Usage |
|---------|---------------|-------|
| `_get_recent_logs(category, limit=20)` | `EventBus().query(category=category, limit=limit)` | Récupérer les logs pour un diagnostic |
| `_handle_diagnostic(query)` | `EventBus().query(category="reseau", limit=10)` (via `_get_recent_logs`) | Analyser les erreurs réseau récentes |
| `_get_possible_actions()` | — (pas de consultation directe) | Lister les actions possibles pour les suggestions |

#### Gestion d'erreur EventBus

Si `EventBus()` est inaccessible (base SQLite corrompue, etc.), `_get_recent_logs()`  
retourne une **liste vide** et le diagnostic continue sans logs.

### 5.3 Catalogue des actions possibles

Assistant connaît les actions que l'application peut exécuter :

| Action | Description | Paramètres |
|--------|-------------|------------|
| `navigate` | Rediriger vers un bot/page | `bot`, `icon` |

---

## 6. Dashboard (page Assistant)

### 6.1 Structure

La page "Assistant" dans CenterZone passe d'une page vide à un **dashboard temps réel** :

```
┌─────────────────────────────────────────────────────────┐
│  🤖 Assistant — Activité en coulisses                   │
│                                                         │
│  ┌─ Stats ──────────────────────────────────────────┐  │
│  │  💬 24 interactions     ⚡ 3 diagnostics          │  │
│  │  ✅ 20 succès           ❌ 1 échec                │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌─ Flux temps réel ────────────────────────────────┐  │
│  │  14:23:45  🔧  Configuration réseau → ✅       │  │
│  │  14:22:10  🔍  Diagnostic connexion → ⚠️       │  │
│  │  14:20:33  💡  Recommandation → navigation      │  │
│  │  ...                                              │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌─ Dernier diagnostic ─────────────────────────────┐  │
│  │  Connexion : ✅ OK                                │  │
│  │  Transferts : ⚠️ 3 téléchargements en attente    │  │
│  │  Partages : ✅ 2 dossiers partagés               │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 6.2 Widgets

| Widget | Description |
|--------|-------------|
| **Bannière stats** | 4 indicateurs (interactions, diagnostics, succès, échecs) |
| **Flux temps réel** | `QListWidget` avec les dernières actions. Chaque entrée = timestamp + icône + type + statut |
| **Panneau dernier diagnostic** | Résumé du dernier diagnostic exécuté avec statuts par catégorie |
| **Bouton "Rafraîchir"** | Recharge les données depuis SQLite |

### 6.3 Mise à jour — stratégie

Le dashboard se met à jour selon cette stratégie :

| Événement | Action |
|-----------|--------|
| Assistant émet `assistant_response` | → Ajoute une entrée dans le flux **si la page est visible** |
| Assistant émet `assistant_response` (page cachée) | → Rien en direct. Prochains visiteurs verront les entrées SQLite |
| Utilisateur clique sur le bouton "Assistant" dans le footer | → `show_page("Assistant")` déclenche `_update_stats()` depuis SQLite |
| Bouton "Rafraîchir" cliqué | → `_update_stats()` depuis SQLite |

**Principe** : Pas de mise à jour en arrière-plan si la page n'est pas affichée.  
Le chargement se fait **à la demande** via SQLite quand l'utilisateur visite la page.

---

## 7. Cycle de vie et comportement

### 7.1 Initialisation (`__init__`)

1. Appel constructeur parent `QFrame.__init__()`
2. Définition des signaux :
   - `assistant_response = Signal(str)` — réponse JSON vers BotAccueil
3. Initialisation de la base SQLite (`bot_assistant.db`)
4. Construction du dashboard (page visible)
5. BotAssistant est **toujours actif** (même si sa page n'est pas affichée)

### 7.2 Méthode `setup()` (appelée depuis CenterZone)

```python
def setup(self, bot_accueil: BotAccueil) -> None:
    """Connecte le bot Assistant à BotAccueil via Signal/Slot direct."""
    # BotAccueil → Assistant
    bot_accueil.assistant_request.connect(self._on_assistant_request)
    # Assistant → BotAccueil
    self.assistant_response.connect(bot_accueil._on_assistant_response)
```

### 7.3 Traitement d'une requête

```python
def _on_assistant_request(self, action_type: str, query: str) -> None:
    """Reçoit une requête de BotAccueil et retourne une réponse structurée."""

    try:
        # 1. Valider le type d'action
        if action_type not in _VALID_ACTION_TYPES:
            raise ValueError(f"Type invalide : {action_type!r}")

        # 2. Router vers le bon handler
        router = {
            "config": self._handle_config,
            "diagnostic": self._handle_diagnostic,
            "recommendation": self._handle_recommendation,
            "tutorial": self._handle_tutorial,
        }
        handler = router[action_type]
        response = handler(query)

        # 3. Émettre la réponse
        response_json = json.dumps(response, ensure_ascii=False)
        self.assistant_response.emit(response_json)

        # 4. Persister
        self._log_interaction(action_type, query, response_json, success=True)

        # 5. Mettre à jour le dashboard si visible
        if self.isVisible():
            status = "✅" if response["severity"] != "error" else "❌"
            self._add_activity_entry(action_type, status, response["message"][:60])

    except Exception as exc:
        logger.error("Assistant error: %s", exc)
        error_response = {
            "message": "Une erreur est survenue. Consulte le bot <b>Aide</b>.",
            "severity": "error",
            "suggestions": [{"label": "❓ Consulter l'Aide", "action": "navigate", "bot": "Aide"}],
            "data": {"error": str(exc)},
        }
        error_json = json.dumps(error_response, ensure_ascii=False)
        self.assistant_response.emit(error_json)
        self._log_interaction(action_type, query, error_json, success=False, error_message=str(exc))
```

### 7.4 Réception de la réponse (dans BotAccueil)

`_on_assistant_response` utilise la méthode `add_message()` (qui existe déjà dans
BotAccueil, ligne 254) pour afficher la réponse dans le chat :

```python
def _on_assistant_response(self, response_json: str) -> None:
    """Reçoit une réponse structurée d'Assistant et l'affiche dans le chat."""
    try:
        data = json.loads(response_json)
    except json.JSONDecodeError:
        logger.error("Assistant: réponse JSON invalide")
        return

    # Afficher le message dans le chat (utilise add_message() existant)
    severity = data.get("severity", "info")
    message = data.get("message", "")
    suggestions = data.get("suggestions", None)
    self.add_message(severity, message, suggestions)

    # Naviguer si demandé
    navigation = data.get("navigation")
    if navigation:
        QTimer.singleShot(1500, lambda: self.navigate_to(
            navigation.get("bot", ""),
            navigation.get("icon", "➡️"),
        ))
```

---

## 8. Schéma de la classe `BotAssistant`

```python
class BotAssistant(QFrame):
    """Assistant du bot Accueil — configuration, diagnostic, recommandations."""

    assistant_response = Signal(str)  # Réponse JSON vers BotAccueil

    def __init__(self, parent: QWidget | None = None) -> None
    def setup(self, bot_accueil: BotAccueil) -> None

    # ── Traitement des requêtes ──
    def _on_assistant_request(self, action_type: str, query: str) -> None
    def _handle_config(self, query: str) -> dict
    def _handle_diagnostic(self, query: str) -> dict
    def _handle_recommendation(self, query: str) -> dict
    def _handle_tutorial(self, query: str) -> dict

    # ── Matching interne ──
    def _match_config(self, query: str) -> tuple[str, str] | None
    def _match_diagnostic(self, query: str) -> str | None
    def _match_recommendation(self, query: str) -> str | None
    def _match_tutorial(self, query: str) -> str | None

    # ── Sources de données ──
    def _get_app_state(self) -> dict
    def _get_recent_logs(self, category: str | None = None, limit: int = 20) -> list
    def _get_possible_actions(self) -> list[dict]

    # ── Dashboard (page visible) ──
    def _build_dashboard(self) -> None
    def _update_stats(self) -> None
    def _add_activity_entry(self, action_type: str, status: str, message: str) -> None

    # ── Base de données ──
    def _init_database(self) -> None
    def _log_interaction(self, action_type: str, query: str, response: str, success: bool, error_message: str | None = None) -> None
    def _log_diagnostic(self, check_type: str, status: str, message: str, suggestion: str | None) -> None
    def _get_interactions(self, limit: int = 50) -> list[dict]
    def _get_last_diagnostic(self) -> dict | None
    def _get_stats(self) -> dict
```

### Constantes

```python
_VALID_ACTION_TYPES = frozenset({"config", "diagnostic", "recommendation", "tutorial"})

_CONFIG_RULES: list[tuple[list[str], str, str]] = [
    (["port", "écoute", "réseau"], "reseau", "port_ecoute"),
    (["partage", "dossier", "partager"], "partages", "dossier_1_chemin"),
    (["destination", "sauvegarde", "téléchargement"], "telechargement", "dossier_destination"),
    (["description", "profil", "bio"], "general", "description_profil"),
]

_DIAGNOSTIC_RULES: list[tuple[list[str], str]] = [
    (["connect", "impossible", "erreur", "timeout"], "connexion"),
    (["lent", "ralentir", "vitesse"], "transfert"),
    (["partag", "dossier", "fichier"], "partage"),
    (["performance", "mémoire", "cpu"], "performance"),
]

_RECOMMENDATION_RULES: list[tuple[list[str], str, str]] = [
    (["chercher", "recherche", "trouver", "fichier"], "Recherche", "🔍"),
    (["télécharger", "download", "recevoir"], "Téléchargement", "📥"),
    (["bibliothèque", "partagé", "fichier"], "Bibliothèque", "📚"),
    (["souhait", "wishlist", "attendre"], "Wishlist", "📋"),
]

_TUTORIAL_RULES: list[tuple[list[str], str]] = [
    (["planifier", "programmer", "automatique"], "planifier-tache-programmee"),
    (["optimiser", "vitesse", "performance"], "optimiser-telechargements"),
]
```

---

## 9. Intégration dans CenterZone

### 9.1 Dans `center.py`

Remplacer `_build_menu_page("Assistant")` (lignes 103-108) par `_build_assistant_page()` :

```python
def _build_assistant_page(self) -> None:
    """Crée la page dashboard du bot Assistant."""
    from src.gui.widgets.bots.bot_assistant import BotAssistant
    page = BotAssistant()
    self._bot_assistant = page
    self._pages["Assistant"] = page
    self._stack.addWidget(page)
```

### 9.2 Connexion BotAccueil ↔ Assistant

Dans `_connect_event_signals` (après la connexion EventBus → BotAide) :

```python
# ── Assistant → BotAccueil (Signal/Slot direct) ──
assistant = getattr(self, "_bot_assistant", None)
accueil = getattr(self, "_bot_accueil", None)
if assistant is not None and accueil is not None:
    accueil.assistant_request.connect(assistant._on_assistant_request)
    assistant.assistant_response.connect(accueil._on_assistant_response)
    logger.info("Assistant connecté à BotAccueil")
```

### 9.3 Modifications dans BotAccueil

**Nouveau signal :**
```python
assistant_request = Signal(str, str)  # action_type, query
```

**Nouvelle méthode :**
```python
def _on_assistant_response(self, response_json: str) -> None
```

### 9.4 Quatre points d'entrée pour déléguer à Assistant

Décision : **Quatre points d'entrée** peuvent déclencher une demande à Assistant.
Les trois premiers (route, KNOWLEDGE, exécution) passent une query par défaut
car ils sont déclenchés par des boutons/clics sans connaître le message original.
Le quatrième (`_match_intent`) transmet la **requête utilisateur réelle**.

#### 1. Dictionnaire `route` dans BotAccueil (ligne 627)

Déclenché par clic sur suggestion. La query est générique car le bouton
ne porte pas le message original de l'utilisateur :

```python
# AVANT :
"config": lambda: self.navigate_to("Assistant", "⚙️"),

# APRÈS :
"config": lambda: self.assistant_request.emit("config", "Configuration"),
```

Les autres entrées du dictionnaire (`search`, `downloads`, etc.) ne sont pas modifiées.

#### 2. `_execute_actions()` (ligne 379) — pattern récursif

La méthode `_execute_actions` utilise une approche **récursive** avec `_run_step`
et `QTimer.singleShot` pour gérer les délais entre les actions.

Ajout d'une règle : si une action `navigate` cible `"Assistant"`, émettre
`assistant_request` au lieu de `navigate_to`. La query vient du champ
`"query"` de l'action KNOWLEDGE (query par défaut) :

```python
def _execute_actions(self, actions: list[dict]) -> None:
    if not actions:
        return

    def _run_step(index: int) -> None:
        if index >= len(actions):
            return
        action = actions[index]
        atype = action.get("type", "")

        if atype == "navigate":
            bot = action.get("bot", "")
            if bot == "Assistant":
                self.assistant_request.emit("config", action.get("query", "Configuration"))
            else:
                self.navigate_to(bot, action.get("icon", "➡️"))

        elif atype == "message":
            self.add_message(
                action.get("icon", "💬"),
                action.get("text", ""),
                action.get("suggestions"),
            )
            QTimer.singleShot(400, lambda: _run_step(index + 1))
            return

        # Autres types (delay, suggestions) inchangés...
        _run_step(index + 1)

    _run_step(0)
```

#### 3. Entrée KNOWLEDGE "assistant" (bot_accueil_knowledge.py lignes 306-326)

L'entrée est réécrite pour ne plus avoir `{"type": "navigate", "bot": "Assistant"}`
mais plutôt une action qui sera interceptée par `_execute_actions()` (point 2) :

```python
"assistant": {
    "keywords": ["assistant", "config", "configuration", ...],
    "icon": "⚙️",
    "response": "Je demande au bot <b>Assistant</b> (en coulisses) de t'aider...",
    "actions": [
        {"type": "navigate", "bot": "Assistant", "query": "Configuration"},
    ],
    "suggestions": [
        {"label": "⚙️ Configurer", "action": "config"},
        {"label": "🏠 Accueil", "action": "welcome"},
    ],
},
```

**Règle** : La navigation vers la page "Assistant" ne se fait **plus** automatiquement.
L'utilisateur clique sur le footer s'il veut voir le dashboard.
Assistant travaille en coulisses, le chat BotAccueil affiche les réponses.

#### 4. `_match_intent()` — transmission de la requête utilisateur réelle

Ce point d'entrée est **le plus important** : quand l'utilisateur tape un message
qui correspond à une intention Assistant, la **requête originale** est transmise
tel quelle à Assistant, permettant le matching de mots-clés (`_match_config`, etc.).

Le déclenchement se fait dans le code qui traite le résultat de `_match_intent()`
(dans la méthode de saisie utilisateur de BotAccueil) :

```python
# Mapping des clés KNOWLEDGE vers les types d'action Assistant
_INTENT_TO_ACTION: dict[str, str] = {
    "assistant": "config",
    "config": "config",
    "diagnostic": "diagnostic",
    "recommendation": "recommendation",
    "tutorial": "tutorial",
}

# Zone de traitement après _match_intent()
user_message = ...  # Message original saisi par l'utilisateur
match = self._match_intent(user_message)
if match:
    entry_key, entry_data = match
    # Si l'intention correspond à un type Assistant → émettre avec la vraie query
    action_type = _INTENT_TO_ACTION.get(entry_key)
    if action_type is not None:
        self.assistant_request.emit(action_type, user_message)
        # Les actions du KNOWLEDGE ne sont PAS exécutées (remplacées par Assistant)
        # Les suggestions du KNOWLEDGE sont conservées
        return
```

**Principe** : Quand `_match_intent()` trouve une intention connue d'Assistant,
le flux normal `_execute_actions()` est **court-circuité** et remplacé par
l'émission directe de `assistant_request` avec la question originale.
Les suggestions de l'entrée KNOWLEDGE restent affichées (boutons cliquables
qui passent par le dictionnaire `route`, point 1).

### 9.5 Présentation des bots (bot_accueil_knowledge.py lignes 392-402)

Texte mis à jour pour mentionner qu'Assistant travaille en arrière-plan :

```
"Les autres bots sont : <b>Recherche</b>, ... <b>Assistant</b> (en coulisses), et <b>Aide</b>."
```

---

## 10. Fichiers à créer / modifier

### Création

| Fichier | Action |
|---------|--------|
| `src/gui/widgets/bots/bot_assistant.py` | Nouvelle classe `BotAssistant(QFrame)` — logique + dashboard |

### Modification

| Fichier | Changement |
|---------|-----------|
| `src/gui/layout/center.py` | Remplacer `_build_menu_page("Assistant")` par `_build_assistant_page()` ; connecter signaux BotAccueil ↔ Assistant dans `_connect_event_signals` |
| `src/gui/widgets/bots/bot_accueil.py` | Ajouter signal `assistant_request`, méthode `_on_assistant_response`, constante `_INTENT_TO_ACTION` ; modifier le traitement de `_match_intent()` pour court-circuiter vers Assistant avec la requête réelle |
| `src/gui/widgets/bots/bot_accueil_knowledge.py` | Supprimer/réécrire l'entrée "assistant" (plus de navigate_to) ; ajuster la présentation des bots |

### Aucune modification

| Fichier | Raison |
|---------|--------|
| `src/gui/layout/footer.py` | Le bouton "Assistant" existe déjà dans `_BOT_NAMES` (inchangé) |
| `src/services/event_bus.py` | Assistant consulte EventBus mais n'ajoute pas de catégorie dédiée |

---

## 11. Exemples de flux

### Scénario 1 — Configuration réseau

1. L'utilisateur tape dans BotAccueil : "Comment changer le port d'écoute ?"
2. `BotAccueil._match_intent()` analyse → détecte `config` 
3. BotAccueil émet `assistant_request.emit("config", "Comment changer le port d'écoute ?")`
4. `BotAssistant._on_assistant_request("config", query)` est déclenché
5. `_match_config()` trouve les mots-clés `["port", "écoute"]` → section `"reseau"`, clé `"port_ecoute"`
6. `_get_app_state()` → `{"port_ecoute": 60000}`
7. Assistant formule la réponse structurée :

```json
{
  "message": "Le port d'écoute est actuellement sur <b>60000</b>. Tu peux le modifier dans les paramètres <b>Réseau</b>.",
  "severity": "info",
  "suggestions": [
    {"label": "⚙️ Ouvrir la Configuration Réseau", "action": "navigate", "bot": "Réseau"},
    {"label": "📖 Voir le guide complet", "action": "navigate", "bot": "Aide"}
  ],
  "navigation": {"bot": "Réseau", "icon": "⚙️"},
  "data": {"port_actuel": 60000}
}
```

8. BotAccueil reçoit → affiche dans le chat
9. Après 1.5s, redirection vers la page Configuration Réseau
10. Dashboard mis à jour (si visible) + interaction enregistrée dans SQLite

### Scénario 2 — Diagnostic de connexion

1. L'utilisateur tape : "Je n'arrive pas à me connecter"
2. `_match_intent()` → détecte `diagnostic`, émet `assistant_request`
3. `_match_diagnostic()` trouve mots-clés `["connect", "impossible"]` → `check_type = "connexion"`
4. Assistant consulte :
   - `soulseek_service.connexion_status` → déconnecté
   - `EventBus().query(category="reseau", limit=10)` → 3 erreurs timeout dans les 24h
5. Assistant formule la réponse avec diagnostic complet
6. Dashboard mis à jour (si visible) + diagnostic enregistré dans SQLite

### Scénario 3 — Utilisateur consulte le dashboard

1. L'utilisateur clique sur "Assistant" dans le footer → page Assistant
2. `show_page("Assistant")` → `_update_stats()` est appelé (charge depuis SQLite)
3. Le dashboard affiche les données à jour
4. Aucune interaction nécessaire — dashboard purement informatif

---

## 12. Non-couvert (hors scope V1)

- **Interface utilisateur complexe** : Assistant n'a pas de chat, de formulaire ou de vue détaillée — seulement un dashboard passif.
- **Actions automatiques** : Pas d'auto-fix en V1. `can_auto_fix` et `auto_fix_action` sont exclus du format de réponse en V1.
- **Multi-langue** : Français uniquement.
- **Machine learning / NLP avancé** : Matching basé sur règles de mots-clés (comme `_match_intent` de BotAccueil).
- **Édition des connaissances** : Assistant utilise l'état réel de l'application, pas de fichiers `.md` statiques.
- **Contexte de session** : Chaque requête est indépendante. Pas de mémoire entre les requêtes (sauf historique SQLite).
- **EventBus injoignable** : Si EventBus() est inaccessible (base SQLite corrompue), `_get_recent_logs()` retourne une liste vide et le diagnostic continue sans logs.

---

## 13. Tests

### 13.1 Fichier de test

```
tests/test_bot_assistant.py
```

### 13.2 Conventions (alignées sur le projet existant)

| Aspect | Convention | Exemple existant |
|--------|-----------|------------------|
| **Framework** | `pytest` avec `PySide6` | `test_bot_accueil.py` |
| **Fixtures partagées** | `tests/conftest.py` : `qapp` (session), `tmp_data_dir`, `tmp_app_config` | `conftest.py` |
| **Organisation** | Classes de tests par zone fonctionnelle (`TestMatching`, `TestDatabase`, `TestHandlers`, etc.) | `TestMatchIntent`, `TestNavigateTo` |
| **Mocking** | `monkeypatch` de pytest | `test_navigate_to_signal_emitted` |
| **Signal/Slot** | Connexion de lambdas comme spies pour vérifier les émissions | `bot.page_changed.connect(lambda name: received.append(name))` |
| **Isolation** | Instances fraîches par test (via fixture) + fichiers temporaires `tmp_path` | `tmp_history_file`, `bot` |
| **Nommage** | `test_<zone>_<comportement>` | `test_match_config_port_ecoute`, `test_log_interaction_persists` |

### 13.3 Fichiers de test

| Fichier | Contenu |
|---------|---------|
| `tests/test_bot_assistant.py` | **Nouveau** — `TestDatabase`, `TestMatching`, `TestHandlers`, `TestOnAssistantRequest`, `TestDashboard`, `TestAssistantIntegration` |
| `tests/test_bot_accueil.py` | **Modifié** — ajouter la classe `TestAssistantDelegation` (flux sortant de BotAccueil) |
| `tests/conftest.py` | **Modifié** — ajouter la fixture `tmp_bot_assistant_db` |

> ⚠️ **Fixtures partagées** : Le fixture `bot` (instance BotAccueil) reste dans `test_bot_accueil.py`.
> Les tests d'intégration `TestAssistantIntegration` sont dans `test_bot_assistant.py` et
> créent leur propre instance `BotAccueil` avec `qapp` + `tmp_path` pour ne pas dépendre
> du fixture local de `test_bot_accueil.py`.

### 13.4 Fixtures

#### Dans `tests/conftest.py` (nouvelles)

```python
@pytest.fixture
def tmp_bot_assistant_db(tmp_path) -> str:
    """Crée un chemin temporaire pour bot_assistant.db."""
    db_dir = tmp_path / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "bot_assistant.db"
    return str(db_path)
```

#### Dans `tests/test_bot_assistant.py`

```python
import json
import sqlite3
import pytest
from pathlib import Path
from typing import Any
from pytest import MonkeyPatch
from PySide6.QtCore import QTimer
from src.gui.widgets.bots.bot_accueil import BotAccueil


@pytest.fixture
def assistant(tmp_bot_assistant_db: str, qapp: Any) -> "BotAssistant":
    """Instance de BotAssistant avec base SQLite temporaire."""
    from src.gui.widgets.bots.bot_assistant import BotAssistant

    assistant = BotAssistant()
    # Rediriger le chemin de la base
    assistant._db_path = tmp_bot_assistant_db
    assistant._init_database()
    yield assistant
    assistant.deleteLater()


@pytest.fixture
def bot_accueil(tmp_path: Path, qapp: Any) -> BotAccueil:
    """Instance de BotAccueil avec historique temporaire (pour les tests d'intégration)."""
    history_dir = tmp_path / "data"
    history_dir.mkdir(parents=True, exist_ok=True)
    history_file = str(history_dir / "bot_accueil_history.json")

    bot = BotAccueil()
    bot._history_file = history_file
    # Nettoyer les messages de bienvenue
    bot._messages.clear()
    yield bot
    bot.deleteLater()
```

### 13.5 Tests unitaires — `BotAssistant`

#### Classe `TestDatabase`

Tests de la couche SQLite (sans UI, sans Qt autre que `qapp`) :

```python
class TestDatabase:
    """Tests de la base SQLite bot_assistant.db."""

    def test_init_database_creates_tables(self, assistant):
        """Les tables interactions et diagnostics existent après init."""
        conn = sqlite3.connect(assistant._db_path)
        tables = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        assert "interactions" in tables
        assert "diagnostics" in tables

    def test_init_database_reentrant(self, assistant):
        """Appeler _init_database() deux fois ne lève pas d'erreur."""
        assistant._init_database()  # seconde fois
        conn = sqlite3.connect(assistant._db_path)
        count = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
        conn.close()
        assert count == 0

    def test_log_interaction_persists(self, assistant):
        """_log_interaction écrit une ligne dans la table."""
        response = json.dumps({"message": "Test", "severity": "info"}, ensure_ascii=False)
        assistant._log_interaction("config", "Comment configurer le port ?", response, success=True)

        conn = sqlite3.connect(assistant._db_path)
        row = conn.execute(
            "SELECT action_type, query, success FROM interactions WHERE id = 1"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "config"
        assert "port" in row[1]
        assert row[2] == 1  # success

    def test_log_interaction_with_error(self, assistant):
        """_log_interaction enregistre aussi les échecs avec leur message."""
        response = json.dumps({"message": "Erreur", "severity": "error"}, ensure_ascii=False)
        assistant._log_interaction("diagnostic", "Erreur connexion", response,
                                    success=False, error_message="Timeout")

        conn = sqlite3.connect(assistant._db_path)
        row = conn.execute(
            "SELECT success, error_message FROM interactions WHERE id = 1"
        ).fetchone()
        conn.close()
        assert row[0] == 0
        assert row[1] == "Timeout"

    def test_log_diagnostic_persists(self, assistant):
        """_log_diagnostic écrit dans la table diagnostics."""
        assistant._log_diagnostic("connexion", "ok", "Connecté au serveur", None)

        conn = sqlite3.connect(assistant._db_path)
        row = conn.execute(
            "SELECT check_type, status FROM diagnostics WHERE id = 1"
        ).fetchone()
        conn.close()
        assert row == ("connexion", "ok")

    def test_log_diagnostic_with_suggestion(self, assistant):
        """_log_diagnostic enregistre la suggestion si fournie."""
        assistant._log_diagnostic("transfert", "warning",
                                   "3 téléchargements bloqués",
                                   "Vérifier la file d'attente")

        conn = sqlite3.connect(assistant._db_path)
        row = conn.execute(
            "SELECT suggestion FROM diagnostics WHERE id = 1"
        ).fetchone()
        conn.close()
        assert row[0] == "Vérifier la file d'attente"

    def test_get_stats_returns_counts(self, assistant):
        """_get_stats retourne les compteurs d'interactions et diagnostics."""
        # Ajouter quelques données
        r = json.dumps({"message": "OK", "severity": "info"}, ensure_ascii=False)
        assistant._log_interaction("config", "q1", r, success=True)
        assistant._log_interaction("config", "q2", r, success=True)
        assistant._log_interaction("diagnostic", "q3", r, success=False, error_message="fail")
        assistant._log_diagnostic("connexion", "ok", "OK", None)

        stats = assistant._get_stats()
        assert stats["total_interactions"] == 3
        assert stats["successful"] == 2
        assert stats["failed"] == 1
        assert stats["total_diagnostics"] == 1

    def test_get_interactions_returns_ordered(self, assistant):
        """_get_interactions retourne les interactions triées par id décroissant (le plus récent en premier)."""
        r = json.dumps({"message": "OK", "severity": "info"}, ensure_ascii=False)
        assistant._log_interaction("config", "première", r, success=True)
        assistant._log_interaction("diagnostic", "deuxième", r, success=True)

        interactions = assistant._get_interactions(limit=10)
        assert len(interactions) == 2
        # Tri par id décroissant : la deuxième insert a l'id le plus grand
        assert interactions[0]["query"] == "deuxième"
        assert interactions[1]["query"] == "première"

    def test_get_last_diagnostic_returns_latest(self, assistant):
        """_get_last_diagnostic retourne le diagnostic le plus récent."""
        assistant._log_diagnostic("connexion", "ok", "Connexion OK", None)
        assistant._log_diagnostic("transfert", "warning", "3 en attente", "Vérifier")

        last = assistant._get_last_diagnostic()
        assert last is not None
        assert last["check_type"] == "transfert"
        assert last["status"] == "warning"

    def test_get_last_diagnostic_returns_none_when_empty(self, assistant):
        """_get_last_diagnostic retourne None si aucun diagnostic."""
        assert assistant._get_last_diagnostic() is None

    def test_get_interactions_empty_db(self, assistant):
        """_get_interactions retourne [] si la base est vide."""
        assert assistant._get_interactions(limit=10) == []

    def test_get_interactions_respects_limit(self, assistant):
        """_get_interactions limite le nombre de résultats."""
        r = json.dumps({"message": "OK", "severity": "info"}, ensure_ascii=False)
        for i in range(5):
            assistant._log_interaction("config", f"query {i}", r, success=True)

        interactions = assistant._get_interactions(limit=3)
        assert len(interactions) == 3
```

#### Classe `TestMatching`

Tests des règles de matching (purement logique, pas de dépendance Qt) :

```python
class TestMatching:
    """Tests des règles de matching interne d'Assistant."""

    # ── _match_config ──

    def test_match_config_port_ecoute(self, assistant):
        result = assistant._match_config("Comment changer le port d'écoute ?")
        assert result == ("reseau", "port_ecoute")

    def test_match_config_partage(self, assistant):
        result = assistant._match_config("Je veux partager mon dossier musique")
        assert result == ("partages", "dossier_1_chemin")

    def test_match_config_destination(self, assistant):
        result = assistant._match_config("Où sont sauvegardés mes téléchargements ?")
        assert result == ("telechargement", "dossier_destination")

    def test_match_config_description(self, assistant):
        result = assistant._match_config("Comment changer ma description ?")
        assert result == ("general", "description_profil")

    def test_match_config_bio(self, assistant):
        """'bio' est un mot-clé valide pour la config générale."""
        result = assistant._match_config("Je veux changer ma bio")
        assert result == ("general", "description_profil")

    def test_match_config_unknown(self, assistant):
        """Une requête inconnue retourne None."""
        result = assistant._match_config("Quel temps fait-il aujourd'hui ?")
        assert result is None

    def test_match_config_empty(self, assistant):
        """Une requête vide retourne None."""
        result = assistant._match_config("")
        assert result is None

    # ── _match_diagnostic ──

    def test_match_diagnostic_connexion(self, assistant):
        result = assistant._match_diagnostic("Je n'arrive pas à me connecter")
        assert result == "connexion"

    def test_match_diagnostic_lenteur(self, assistant):
        result = assistant._match_diagnostic("Mes téléchargements sont très lents")
        assert result == "transfert"

    def test_match_diagnostic_performance(self, assistant):
        result = assistant._match_diagnostic("L'application utilise trop de mémoire")
        assert result == "performance"

    def test_match_diagnostic_unknown(self, assistant):
        result = assistant._match_diagnostic("J'aime les chiens")
        assert result is None

    # ── _match_recommendation ──

    def test_match_recommendation_recherche(self, assistant):
        result = assistant._match_recommendation("Comment chercher des fichiers ?")
        assert result == ("Recherche", "🔍")

    def test_match_recommendation_telechargement(self, assistant):
        result = assistant._match_recommendation("Je veux télécharger de la musique")
        assert result == ("Téléchargement", "📥")

    def test_match_recommendation_wishlist(self, assistant):
        result = assistant._match_recommendation("J'attends un fichier sur ma wishlist")
        assert result == ("Wishlist", "📋")

    def test_match_recommendation_unknown(self, assistant):
        result = assistant._match_recommendation("Quelle est la capitale du Japon ?")
        assert result is None

    # ── _match_tutorial ──

    def test_match_tutorial_planifier(self, assistant):
        result = assistant._match_tutorial("Comment planifier un téléchargement automatique ?")
        assert result == "planifier-tache-programmee"

    def test_match_tutorial_optimiser(self, assistant):
        result = assistant._match_tutorial("Je veux optimiser la vitesse")
        assert result == "optimiser-telechargements"

    def test_match_tutorial_unknown(self, assistant):
        result = assistant._match_tutorial("Raconte-moi une blague")
        assert result is None
```

#### Classe `TestHandlers`

Tests des gestionnaires qui utilisent les règles de matching :

```python
class TestHandlers:
    """Tests des handlers de traitement (sans dépendances externes)."""

    def test_handle_config_known(self, assistant):
        """_handle_config retourne une réponse structurée pour une requête connue."""
        result = assistant._handle_config("Comment changer le port d'écoute ?")
        assert "message" in result
        assert "severity" in result
        assert result["severity"] == "info"
        assert "suggestions" in result
        assert len(result["suggestions"]) > 0

    def test_handle_config_unknown(self, assistant):
        """_handle_config retourne un warning pour une requête inconnue."""
        result = assistant._handle_config("Quel temps fait-il ?")
        assert result["severity"] == "warning"
        assert "n'ai pas compris" in result["message"].lower()

    def test_handle_diagnostic_known(self, assistant):
        """_handle_diagnostic retourne un diagnostic structuré."""
        result = assistant._handle_diagnostic("Je n'arrive pas à me connecter")
        assert "message" in result
        assert result["severity"] in ("info", "warning", "error")

    def test_handle_diagnostic_unknown(self, assistant):
        """_handle_diagnostic retourne un warning pour un problème inconnu."""
        result = assistant._handle_diagnostic("J'ai un problème bizarre")
        assert result["severity"] == "warning"

    def test_handle_recommendation_known(self, assistant):
        """_handle_recommendation suggère un bot."""
        result = assistant._handle_recommendation("Comment chercher des fichiers ?")
        assert result["severity"] == "info"
        assert "navigation" in result
        assert result["navigation"]["bot"] == "Recherche"

    def test_handle_recommendation_unknown(self, assistant):
        """_handle_recommendation retourne un warning pour une demande inconnue."""
        result = assistant._handle_recommendation("Donne-moi un conseil")
        assert result["severity"] == "warning"

    def test_handle_tutorial_known(self, assistant):
        """_handle_tutorial retourne un tutoriel structuré."""
        result = assistant._handle_tutorial("Comment planifier un téléchargement ?")
        assert "message" in result
        assert result["severity"] == "info"

    def test_handle_tutorial_unknown(self, assistant):
        """_handle_tutorial retourne un warning pour une demande inconnue."""
        result = assistant._handle_tutorial("Apprends-moi le Python")
        assert result["severity"] == "warning"
```

#### Classe `TestOnAssistantRequest`

Tests du routage et du cycle complet de traitement :

```python
class TestOnAssistantRequest:
    """Tests de _on_assistant_request (signal entrant, routage, réponse)."""

    def test_valid_action_type_triggers_handler(self, assistant):
        """Un action_type valide déclenche le handler correspondant."""
        # Espionner le signal
        received: list[str] = []
        assistant.assistant_response.connect(lambda r: received.append(r))

        assistant._on_assistant_request("config", "Comment changer le port ?")

        assert len(received) == 1
        data = json.loads(received[0])
        assert data["severity"] == "info"
        assert "port" in data["message"].lower()

    def test_invalid_action_type_returns_error_response(self, assistant):
        """Un action_type invalide → réponse d'erreur émise (ValueError catchée en interne)."""
        received: list[str] = []
        assistant.assistant_response.connect(lambda r: received.append(r))

        assistant._on_assistant_request("invalid_type", "test")

        assert len(received) == 1
        data = json.loads(received[0])
        assert data["severity"] == "error"

        # L'échec est persisté en base
        conn = sqlite3.connect(assistant._db_path)
        row = conn.execute(
            "SELECT success FROM interactions ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 0

    def test_response_persisted_to_db(self, assistant, monkeypatch):
        """La réponse est persistée en base après traitement."""
        assistant._on_assistant_request("config", "Comment partager un dossier ?")

        conn = sqlite3.connect(assistant._db_path)
        row = conn.execute(
            "SELECT action_type, success FROM interactions ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "config"
        assert row[1] == 1

    def test_lifecycle_all_action_types(self, assistant):
        """Les 4 types d'action passent par le routage sans erreur."""
        received: list[str] = []
        assistant.assistant_response.connect(lambda r: received.append(r))

        for action_type in ("config", "diagnostic", "recommendation", "tutorial"):
            assistant._on_assistant_request(action_type, f"Requête {action_type}")

        assert len(received) == 4
        for r in received:
            data = json.loads(r)
            assert "message" in data
            assert "severity" in data
```

#### Classe `TestDashboard`

Tests de la couche dashboard (sans rendu visuel, juste les méthodes de stats) :

```python
class TestDashboard:
    """Tests des méthodes du dashboard (update_stats, add_activity_entry)."""

    def test_update_stats_with_empty_db(self, assistant):
        """_update_stats ne plante pas si la base est vide."""
        # On appelle juste _update_stats, on vérifie qu'aucune exception n'est levée
        assistant._update_stats()

    def test_update_stats_with_data(self, assistant):
        """_update_stats met à jour les labels de stats après des données."""
        r = json.dumps({"message": "OK", "severity": "info"}, ensure_ascii=False)
        assistant._log_interaction("config", "test", r, success=True)
        assistant._log_interaction("config", "test2", r, success=True)
        assistant._log_interaction("diagnostic", "test3", r, success=False, error_message="fail")

        # On vérifie que _get_stats() retourne les bonnes données
        stats = assistant._get_stats()
        assert stats["total_interactions"] == 3
        assert stats["successful"] == 2
        assert stats["failed"] == 1

    def test_add_activity_entry(self, assistant):
        """_add_activity_entry ajoute une entrée sans planter."""
        assistant._add_activity_entry("config", "✅", "Configuration réseau")
        # Vérifier que la liste du dashboard contient l'entrée
        assert assistant._activity_list.count() == 1  # si un QListWidget est utilisé
```

### 13.6 Tests — `BotAccueil` (modifications)

Ces tests sont ajoutés dans le fichier `tests/test_bot_accueil.py` existant, dans une classe dédiée.

#### Classe `TestAssistantDelegation`

```python
class TestAssistantDelegation:
    """Tests de la délégation de BotAccueil vers Assistant."""

    def test_signal_assistant_request_defined(self, bot):
        """BotAccueil a bien un signal assistant_request."""
        assert hasattr(bot, "assistant_request")

    def test_config_action_emits_signal(self, bot):
        """L'action 'config' du dictionnaire route émet assistant_request."""
        received: list[tuple[str, str]] = []
        bot.assistant_request.connect(lambda at, q: received.append((at, q)))

        bot._on_suggestion("config")

        assert len(received) == 1
        assert received[0][0] == "config"

    def test_execute_actions_navigate_assistant_emits_signal(self, bot, monkeypatch):
        """_execute_actions avec navigate bot=Assistant émet assistant_request au lieu de navigate_to."""
        from PySide6.QtCore import QTimer
        monkeypatch.setattr(QTimer, "singleShot", lambda delay, cb: cb())

        received: list[tuple[str, str]] = []
        bot.assistant_request.connect(lambda at, q: received.append((at, q)))

        bot._execute_actions([{"type": "navigate", "bot": "Assistant", "query": "Configuration"}])

        assert len(received) == 1
        assert received[0][0] == "config"

    def test_execute_actions_other_bot_still_navigates(self, bot, monkeypatch):
        """_execute_actions avec un bot != Assistant navigue normalement."""
        monkeypatch.setattr(QTimer, "singleShot", lambda delay, cb: cb())

        navigate_received: list[str] = []
        bot.page_changed.connect(lambda name: navigate_received.append(name))

        assistant_received: list[tuple[str, str]] = []
        bot.assistant_request.connect(lambda at, q: assistant_received.append((at, q)))

        bot._execute_actions([{"type": "navigate", "bot": "Recherche", "icon": "🔍"}])

        assert len(navigate_received) == 1
        assert "Recherche" in navigate_received
        assert len(assistant_received) == 0

    def test_on_assistant_response_adds_message(self, bot):
        """_on_assistant_response traite le JSON et ajoute un message."""
        response = json.dumps({
            "message": "Le port est 60000",
            "severity": "info",
            "suggestions": [{"label": "Ouvrir config", "action": "navigate", "bot": "Réseau"}],
        }, ensure_ascii=False)

        bot._on_assistant_response(response)

        assert len(bot._messages) >= 1
        last_msg = bot._messages[-1]
        assert "port" in last_msg.get("text", "").lower()

    def test_on_assistant_response_invalid_json(self, bot):
        """_on_assistant_response ne plante pas avec du JSON invalide."""
        bot._on_assistant_response("ceci n'est pas du json")
        # Aucune exception levée

    def test_on_assistant_response_handles_navigation(self, bot, monkeypatch):
        """_on_assistant_response déclenche la navigation si présente dans la réponse."""
        monkeypatch.setattr(QTimer, "singleShot", lambda delay, cb: cb())

        navigate_received: list[str] = []
        bot.page_changed.connect(lambda name: navigate_received.append(name))

        response = json.dumps({
            "message": "Va dans Réseau",
            "severity": "info",
            "suggestions": [],
            "navigation": {"bot": "Réseau", "icon": "⚙️"},
        }, ensure_ascii=False)

        bot._on_assistant_response(response)
        assert "Réseau" in navigate_received
```

### 13.7 Test d'intégration — `BotAccueil` ↔ `BotAssistant`

Ces tests sont placés dans **`tests/test_bot_assistant.py`** (le nouveau fichier) et utilisent
la fixture `bot_accueil` définie localement (pas le fixture `bot` de `test_bot_accueil.py`).

> ⚠️ **Conception** : `_on_assistant_request` attrape `ValueError` en interne (section 7.3)
> et le convertit en réponse d'erreur. Le test vérifie donc la **réponse émise**,
> pas l'exception propagée.

```python
class TestAssistantIntegration:
    """Tests du flux complet BotAccueil → Assistant → BotAccueil."""

    def test_full_flow_config_request(self, bot_accueil, tmp_bot_assistant_db, qapp, monkeypatch):
        """Configuration réseau : setup() + on_suggestion → assistant_request → réponse → chat."""
        from src.gui.widgets.bots.bot_assistant import BotAssistant

        # 1. Créer un Assistant avec base temporaire
        assistant = BotAssistant()
        assistant._db_path = tmp_bot_assistant_db
        assistant._init_database()

        # 2. Utiliser setup() comme le ferait CenterZone
        assistant.setup(bot_accueil)

        # 3. Simuler le matching d'intention → délégation
        bot_accueil._on_suggestion("config")

        # 4. Vérifier que BotAssistant a traité et répondu
        assert len(bot_accueil._messages) >= 1
        last_msg = bot_accueil._messages[-1]
        assert "message" in last_msg

        # 5. Vérifier la persistance
        conn = sqlite3.connect(tmp_bot_assistant_db)
        row = conn.execute(
            "SELECT COUNT(*) FROM interactions"
        ).fetchone()
        conn.close()
        assert row[0] >= 1

        assistant.deleteLater()

    def test_full_flow_diagnostic(self, bot_accueil, tmp_bot_assistant_db, qapp):
        """Diagnostic : Assistant reçoit un action_type et affiche la réponse dans BotAccueil."""
        from src.gui.widgets.bots.bot_assistant import BotAssistant

        assistant = BotAssistant()
        assistant._db_path = tmp_bot_assistant_db
        assistant._init_database()
        assistant.setup(bot_accueil)

        # Simuler un déclenchement direct (le matching exact dépend de KNOWLEDGE)
        assistant._on_assistant_request("diagnostic", "Je n'arrive pas à me connecter")

        assert len(bot_accueil._messages) >= 1

        assistant.deleteLater()

    def test_full_flow_error_handling(self, bot_accueil, tmp_bot_assistant_db, qapp):
        """Erreur interne → réponse d'erreur émise + persistée (exception catchée en interne)."""
        from src.gui.widgets.bots.bot_assistant import BotAssistant

        assistant = BotAssistant()
        assistant._db_path = tmp_bot_assistant_db
        assistant._init_database()
        assistant.setup(bot_accueil)

        # action_type invalide → ValueError catchée → réponse d'erreur émise
        received: list[str] = []
        assistant.assistant_response.connect(lambda r: received.append(r))

        assistant._on_assistant_request("invalid_action", "test")

        # L'erreur est catchée en interne, une réponse d'erreur est émise
        assert len(received) == 1
        data = json.loads(received[0])
        assert data["severity"] == "error"
        assert "Erreur" in data["message"].lower()  # ou un message par défaut

        # L'interaction échouée est persistée
        conn = sqlite3.connect(tmp_bot_assistant_db)
        row = conn.execute(
            "SELECT success FROM interactions ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 0  # success = False

        assistant.deleteLater()
```

### 13.8 Résumé des tests

| Classe | Fichier | Nb tests | Couverture |
|--------|---------|----------|------------|
| `TestDatabase` | `test_bot_assistant.py` | 10 | SQLite : création, CRUD, stats, cas vides |
| `TestMatching` | `test_bot_assistant.py` | 16 | Règles de matching : 4 handlers × 4 cas (connu, mots-clés, inconnu, vide) |
| `TestHandlers` | `test_bot_assistant.py` | 8 | Handlers : 4 types × 2 cas (connu, inconnu) |
| `TestOnAssistantRequest` | `test_bot_assistant.py` | 4 | Routage : action valide, invalide, persistance, tous les types |
| `TestDashboard` | `test_bot_assistant.py` | 3 | Dashboard : update_stats, add_activity_entry |
| `TestAssistantDelegation` | `test_bot_accueil.py` | 7 | Signaux, _execute_actions, _on_assistant_response |
| `TestAssistantIntegration` | `test_bot_assistant.py` | 3 | Flow complet : config, diagnostic, erreur (via `setup()`) |
| **Total** | | **53** | Logique métier + intégration + cas limites |

---

## 14. Étapes d'implémentation suggérées

1. **Base SQLite** : Créer `_init_database()`, `_log_interaction()`, `_log_diagnostic()`, `_get_stats()`
2. **Tests SQLite** : Écrire et faire passer `TestDatabase` (10 tests) — valide le schéma et le CRUD
3. **Classe BotAssistant** : Structure de base avec signaux, dashboard, connexion SQLite
4. **Dashboard** : Stats, flux temps réel, dernier diagnostic, bouton Rafraîchir
5. **Gestionnaires d'actions** : `_handle_config()`, `_handle_diagnostic()`, `_handle_recommendation()`, `_handle_tutorial()` avec leurs règles de matching
6. **Tests matching + handlers** : Écrire et faire passer `TestMatching` (16 tests), `TestHandlers` (8 tests), `TestOnAssistantRequest` (4 tests)
7. **Sources de données** : `_get_app_state()`, `_get_recent_logs()`, `_get_possible_actions()`
8. **Modification BotAccueil** : Signal `assistant_request`, méthode `_on_assistant_response`, constante `_INTENT_TO_ACTION`, court-circuit de `_match_intent()` vers Assistant avec la requête réelle
9. **Tests délégation** : Écrire et faire passer `TestAssistantDelegation` (7 tests)
10. **Modification BotAccueilKnowledge** : Supprimer l'ancienne entrée "assistant" avec `navigate_to`
11. **Intégration CenterZone** : `_build_assistant_page()`, connexion des signaux
12. **Test intégration** : Écrire et faire passer `TestAssistantIntegration` (3 tests) avec la fixture `bot_accueil` locale
13. **Tests finaux** : Lancer toute la suite (`pytest tests/test_bot_assistant.py tests/test_bot_accueil.py -v`)
