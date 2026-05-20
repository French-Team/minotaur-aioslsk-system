# Bot Aide — Spécification technique

> **Date :** 2026-03-17  
> **Objet :** Bot "Aide" — assistant mémoire & documentation interactive  
> **Statut :** Spécification pré-implantation

---

## 1. Objectif

Le bot **Aide** est un assistant spécialisé dans la documentation et l'aide à l'utilisation de l'application. Il constitue la **mémoire de l'application** : il centralise les connaissances (guide des bots, FAQ, tutoriels, documentation technique) et répond aux questions de l'utilisateur en affichant le contenu pertinent dans sa page dédiée.

Il travaille en **arrière-plan** (écoute les requêtes via EventBus), et affiche le résultat dans sa page.

---

## 2. Architecture — Dépendances et interactions

### 2.1 Dépendances

- **PySide6** (QFrame, QVBoxLayout, QHBoxLayout, QStackedWidget, QLabel, QTextBrowser, QPushButton, QListWidget, QSplitter, QLineEdit, QMenu, QTimer)
- **`src.services.event_bus`** — `EventBus` avec nouvelle catégorie `"aide"`
- **SQLite3** (stdlib) — base dédiée `bot_aide.db`
- **`src.gui.layout.center`** (CenterZone) — page enregistrée dans `_pages`
- **`src.gui.layout.footer`** (FooterZone) — bouton "Aide" déjà présent dans `_BOT_NAMES`

### 2.2 Interaction avec le bot Accueil

```
Utilisateur → BotAccueil (question en langage naturel)
    ↓ BotAccueil.match_intent() reconnaît une question d'aide
    ↓ BotAccueil.navigate_to("Aide", "❓") → page_changed.emit("Aide")
    ↓ BotAccueil émet un événement EventBus :
      category="aide", title="[article_title]", message=question_texte
    ↓
BotAide (écoute EventBus en arrière-plan)
    ↓ Cherche dans SQLite → trouve l'article
    ↓ Affiche le contenu dans le viewer
    ↓ Enregistre dans l'historique (sidebar)
```

### 2.3 Canal EventBus

- **Nouvelle catégorie :** `"aide"` (à ajouter dans `CATEGORIES` de `EventBus`)
- **Nouvel événement :** `SurveillanceEvent(category="aide", severity="INFO", title="article_title", message="question_texte", source="bot_accueil")`
- **Écoute :** Le bot Aide écoute toutes les émissions de catégorie `"aide"`

---

## 3. Base de données SQLite — `bot_aide.db`

### 3.1 Emplacement

```
data/bot_aide.db
```

### 3.2 Tables

#### Table `articles`

| Colonne | Type | Contrainte | Description |
|---------|------|-----------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Identifiant unique |
| `category` | TEXT | NOT NULL | Catégorie : `guide_bots`, `faq`, `tutoriel`, `technique`, `aide_contextuelle` |
| `title` | TEXT | NOT NULL UNIQUE | Titre de l'article |
| `keywords` | TEXT | NOT NULL | Mots-clés JSON array → cherche par question |
| `content` | TEXT | NOT NULL | Contenu (Markdown + HTML) |
| `created_at` | TEXT | NOT NULL DEFAULT CURRENT_TIMESTAMP | Date de création |
| `updated_at` | TEXT | NOT NULL DEFAULT CURRENT_TIMESTAMP | Date de modification |

#### Table `history`

| Colonne | Type | Contrainte | Description |
|---------|------|-----------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Identifiant unique |
| `article_id` | INTEGER | NOT NULL REFERENCES articles(id) | Article consulté |
| `question` | TEXT | NOT NULL | Texte de la question posée |
| `consulted_at` | TEXT | NOT NULL DEFAULT CURRENT_TIMESTAMP | Date de consultation |

### 3.3 Peuplement initial

Au premier lancement, la base est créée et importée depuis des fichiers `.md` dans un dossier `data/aide_knowledge/` :

```
data/aide_knowledge/
├── guide_bots/
│   ├── 01-bot-accueil.md
│   ├── 02-bot-recherche.md
│   ├── 03-bot-telechargement.md
│   ├── 04-bot-bibliotheque.md
│   ├── 05-bot-wishlist.md
│   ├── 06-bot-surveillance.md
│   ├── 07-bot-planificateur.md
│   ├── 08-bot-ordonnanceur.md
│   ├── 09-bot-optimiseur.md
│   ├── 10-bot-clients-actifs.md
│   ├── 11-bot-assistant.md
│   └── 12-bot-aide.md
├── faq/
│   ├── connexion-impossible.md
│   ├── telechargement-lent.md
│   ├── recherche-sans-resultat.md
│   └── erreurs-frequentes.md
├── tutoriels/
│   ├── configurer-recherche-automatique.md
│   ├── planifier-tache-programmee.md
│   └── optimiser-telechargements.md
└── technique/
    ├── formats-supportes.md
    ├── depistage-logs.md
    └── api-soulseek.md
```

Chaque fichier `.md` contient un **frontmatter YAML** avec les métadonnées et le corps en Markdown :

```markdown
---
title: "Bot Recherche — Guide complet"
category: guide_bots
keywords: ["recherche", "chercher", "fichier", "filtre", "résultat"]
---

## Bot Recherche

Le bot Recherche permet de...
```

**Méthode** : Une fonction `_init_database()` est appelée au premier lancement. Elle :
1. Vérifie si la table `articles` est vide
2. Scanne `data/aide_knowledge/` récursivement
3. Parse le frontmatter + body de chaque fichier `.md`
4. Insère dans la table `articles`

---

## 4. Interface utilisateur — Page du bot Aide

### 4.1 Structure générale

```
┌─────────────────────────────────────────────────────────┐
│  [🔍 Barre de recherche]            [Toggle sidebar ⏎] │
├──────────────────────────────────────┬──────────────────┤
│                                      │  ─────────────   │
│                                      │  Historique       │
│         Viewer (QTextBrowser)        │  des demandes     │
│         Contenu de l'article         │  ─────────────   │
│         Format : Markdown + HTML     │  • Guide du       │
│                                      │    bot Recherche  │
│                                      │  • Comment         │
│                                      │    configurer...   │
│                                      │  • FAQ : Connexion │
│                                      │  • ...             │
│                                      │                   │
│                                      │  [clic droit]     │
│                                      │  ├ Copier le titre│
│                                      │  ├ Copier le      │
│                                      │  │   contenu      │
│                                      │  └ Supprimer      │
└──────────────────────────────────────┴──────────────────┘
```

### 4.2 Layout

- **Widget racine** : `BotAide(QFrame)`
- **QSplitter horizontal** :
  - Gauche : Viewer (`QTextBrowser`) — occupe tout l'espace
  - Droite : Sidebar (`QListWidget` + en-tête) — rétractable, largeur ~250px
- **Barre supérieure** : Barre de recherche (`QLineEdit`) + toggle sidebar (`QPushButton`)
- **Sidebar** : `QListWidget` avec les articles historiques
  - `setContextMenuPolicy(Qt.CustomContextMenu)` pour le clic droit

### 4.3 Viewer (QTextBrowser)

- Affiche le contenu rendu en HTML
- Supporte Markdown (converti en HTML via une méthode maison ou `markdown` lib)
- Supporte HTML directement (balises `<b>`, `<a>`, `<ul>`, `<code>`)
- Défilement vertical si le contenu dépasse
- Zoom possible (Ctrl+Molette) si nécessaire
- Liens : support des liens internes (vers d'autres articles) et externes

### 4.4 Sidebar — Historique des consultations

- **Titre** : "Historique des consultations" ou "📋 Demandes récentes"
- **Contenu** : Liste des titres d'articles consultés
- **Ordre** : Du plus récent au plus ancien (dernier consulté en haut)
- **Limite** : 50 entrées max (FIFO)
- **Persistance** : Stockée dans la table `history` de `bot_aide.db`

**Menu contextuel (clic droit)** :

| Action | Comportement |
|--------|-------------|
| Copier le titre | Copie le titre de l'article dans le presse-papier (`QApplication.clipboard()`) |
| Copier le contenu | Copie tout le contenu de l'article (version texte brut) dans le presse-papier |
| Supprimer | Supprime l'entrée de l'historique (base + sidebar) |

### 4.5 Barre de recherche

- `QLineEdit` avec placeholder "🔍 Chercher une réponse..."
- Délai de 300ms après la dernière frappe avant recherche (`QTimer`)
- Recherche dans les colonnes `title` et `keywords` de la table `articles` (`LIKE %query%`)
- Résultats affichés comme suggestions dans la sidebar (ou en overlay)
- Clique sur un résultat → affiche l'article dans le viewer + enregistre dans l'historique

### 4.6 Bouton "Aide" dans le footer

Le bouton **Aide** existe déjà dans `_BOT_NAMES` du `footer.py` (ligne 78). Aucune modification nécessaire.

---

## 5. Cycle de vie et comportement en arrière-plan

### 5.1 Initialisation (`__init__`)

1. Appel constructeur parent `QFrame.__init__()`
2. Définition du signal `page_changed = Signal(str)`
3. Configuration de la base SQLite (création + import si première fois)
4. Construction de l'interface (viewer + sidebar + search)
5. Abonnement à l'EventBus (catégorie `"aide"`)
6. Chargement de l'historique depuis la base

### 5.2 Écoute EventBus (arrière-plan)

```python
def _on_aide_event(self, event: SurveillanceEvent) -> None:
    """Reçoit une requête d'aide depuis BotAccueil (ou autre)."""
    # event.title = nom de l'article cherché (optionnel)
    # event.message = question posée par l'utilisateur
    article = self._find_best_match(event.title or event.message)
    if article:
        self._display_article(article, event.message)
```

### 5.3 Algorithme de matching

```
1. Si event.title correspond exactement à un titre d'article → retourne
2. Sinon, cherche event.message dans keywords (LIKE %mot-clé%)
3. Sinon, cherche event.message dans title (LIKE %mot%)
4. Sinon, prend les mots significatifs (stopwords exclus) et cherche
5. Si toujours rien → affiche une page "Aucun résultat" avec suggestion de reformuler
```

### 5.4 Méthode `setup()` (appelée depuis CenterZone._connect_event_signals)

```python
def setup(self, event_bus: EventBus) -> None:
    """Connecte le bot Aide à l'EventBus."""
    event_bus.event_emitted.connect(self._on_event)
```

---

## 6. Intégration dans CenterZone

### 6.1 Dans `center.py`

Remplacer l'appel à `self._build_menu_page("Aide")` par une méthode dédiée :

```python
def _build_aide_page(self) -> None:
    """Crée la page du bot Aide."""
    from src.gui.widgets.bots.bot_aide import BotAide
    page = BotAide()
    page.page_changed.connect(self.show_page)
    self._pages["Aide"] = page
    self._stack.addWidget(page)
```

### 6.2 Dans `_connect_event_signals`

```python
page = self._pages.get("Aide")
if page is not None and hasattr(page, "setup"):
    page.setup(event_bus)
```

---

## 7. Schéma de la classe `BotAide`

```python
class BotAide(QFrame):
    page_changed = Signal(str)

    # ── Signaux internes ──
    _search_requested = Signal(str)  # émis après délai de debounce

    def __init__(self, parent: QWidget | None = None) -> None
    def setup(self, event_bus: EventBus) -> None

    # ── Base de données ──
    def _get_db_path(self) -> Path
    def _init_database(self) -> None
    def _import_knowledge_files(self) -> None
    def _parse_markdown_file(self, path: Path) -> dict | None
    def _find_best_match(self, query: str) -> dict | None
    def _log_history(self, article_id: int, question: str) -> None
    def _get_history(self) -> list[dict]
    def _delete_history_entry(self, entry_id: int) -> None

    # ── Interface ──
    def _build_ui(self) -> None
    def _display_article(self, article: dict, question: str | None = None) -> None
    def _show_no_result(self, query: str) -> None
    def _toggle_sidebar(self) -> None
    def _on_search_text_changed(self) -> None
    def _on_search_debounce(self) -> None
    def _on_search_result_clicked(self, article_id: int) -> None
    def _on_history_context_menu(self, pos: QPoint) -> None
    def _render_content(self, raw: str) -> str

    # ── Événements ──
    def _on_event(self, event: SurveillanceEvent) -> None
    def _on_aide_request(self, title: str, message: str) -> None
```

---

## 8. Flux utilisateur complet

### Scénario principal

1. L'utilisateur est sur la page **Accueil**
2. Il tape : *"Comment configurer le bot Recherche ?"*
3. BotAccueil reconnaît l'intention via `_match_intent` → trouve une correspondance partielle
4. BotAccueil affiche : *"Je t'emmène vers le bot Aide … 🔄"*
5. BotAccueil émet `page_changed.emit("Aide")` → CenterZone affiche la page Aide
6. BotAccueil publie un événement `category="aide"`, `title=""`, `message="Comment configurer le bot Recherche ?"` sur EventBus
7. BotAide reçoit l'événement → `_find_best_match("Comment configurer le bot Recherche ?")`
8. BotAide trouve les mots-clés "recherche", "configurer" → article *"Bot Recherche — Guide complet"*
9. BotAide affiche l'article dans le viewer
10. BotAide enregistre dans `history` (article_id + question)
11. La sidebar se met à jour avec la nouvelle entrée

### Scénario — Recherche directe depuis la page Aide

1. L'utilisateur clique sur "Aide" dans le footer → page Aide
2. Il tape *"Connexion impossible"* dans la barre de recherche
3. Après 300ms, la base est interrogée → résultats dans un dropdown
4. L'utilisateur clique sur un résultat → article affiché + historique enregistré

### Scénario — Sidebar

1. L'utilisateur clique sur une entrée dans la sidebar → l'article est rechargé dans le viewer
2. Clic droit → menu : "Copier le titre", "Copier le contenu", "Supprimer"

---

## 9. Fichiers à créer / modifier

### Création

| Fichier | Action |
|---------|--------|
| `src/gui/widgets/bots/bot_aide.py` | Nouvelle classe `BotAide(QFrame)` |
| `data/aide_knowledge/guide_bots/*.md` | Articles : guide des 12 bots |
| `data/aide_knowledge/faq/*.md` | Articles : FAQ |
| `data/aide_knowledge/tutoriels/*.md` | Articles : tutoriels |
| `data/aide_knowledge/technique/*.md` | Articles : documentation technique |

### Modification

| Fichier | Changement |
|---------|-----------|
| `src/gui/layout/center.py` | Remplacer `_build_menu_page("Aide")` par `_build_aide_page()` ; ajouter `_build_aide_page()` ; connecter dans `_connect_event_signals` |
| `src/services/event_bus.py` | Ajouter `"aide"` à `CATEGORIES` (liste des catégories) |

### Aucune modification

| Fichier | Raison |
|---------|--------|
| `src/gui/layout/footer.py` | Le bouton "Aide" existe déjà dans `_BOT_NAMES` |

---

## 10. Non-couvert (hors scope)

- **Édition des articles d'aide** : Pas d'interface d'édition — les articles sont gérés via fichiers `.md` → base.
- **Mode hors-ligne** : Le bot fonctionne toujours en local (SQLite), donc pas de mode hors-ligne spécifique.
- **Traductions / i18n** : L'aide est en français uniquement dans un premier temps.
- **Recherche full-text (FTS5)** : Pour V2 — dans un premier temps, `LIKE %query%` suffit pour le nombre d'articles (< 30).

---

## 11. Étapes d'implémentation suggérées

1. **Base SQLite** : Créer `_init_database()`, `_import_knowledge_files()`, `_find_best_match()`
2. **Articles `.md`** : Créer les fichiers de connaissance dans `data/aide_knowledge/`
3. **Interface** : `_build_ui()` avec viewer, sidebar, barre de recherche
4. **Historique** : Table `history`, chargement/affichage dans sidebar, menu contextuel
5. **EventBus** : Ajouter catégorie `"aide"`, abonnement et handler
6. **Intégration CenterZone** : Remplacer `_build_menu_page("Aide")`, connecter signaux
7. **Tests** : Tests unitaires (recherche, historique, EventBus) + test d'intégration
