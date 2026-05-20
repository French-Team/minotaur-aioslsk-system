---
title: "Système AideDB — Base de connaissances"
category: technique
icon: 🧠
keywords:
  - AideDB base connaissances
  - aide db systeme
  - aide_db.py moteur
  - bot aide connaissance
  - base connaissance sqlite
  - aide knowledge base
  - parse markdown frontmatter
  - parse yaml article
  - _parse_markdown_file
  - _scan_knowledge_files
  - init_database import
  - import article markdown
  - schema table articles
  - table articles sqlite
  - table history sqlite
  - recherche like titre
  - recherche like mot cle
  - recherche like mot-clé
  - find_best_match strategie
  - find_best_match stratégie
  - find best match
  - find_by_title
  - get_all_articles
  - get_categories
  - count_articles
  - add_history consultation
  - get_history consultation
  - delete_history_entry
  - clear_history
  - bot accueil knowledge
  - bot_accueil_knowledge.py
  - keyword matching bot aide
  - fallback reponse
  - fallback réponse
  - fallback insulte
  - suggestion navigation bot
  - navigate action bot
  - systeme connaissance
  - système connaissance
  - moteur recherche connaissance
  - base donnee article
  - base données article
  - base donnée article
  - indexation article
  - importation connaissances
  - scan fichier md
  - scan fichiers md
  - frontmatter yaml article
  - categorie article
  - catégorie article
  - mot cle declencheur
  - mot clé déclencheur
  - mot-clé déclencheur
  - reponse fallback
  - réponse fallback
  - navigation entre bots
  - historique consultation
  - wal checkpoint
  - fermeture base donnee
  - fermeture base données
  - aide_db fermeture
---

# 🧠 Système AideDB — Base de connaissances

## Introduction

Le module `src/services/aide_db.py` (405 lignes) est le **moteur de la base de connaissances** qui alimente le bot Aide. Il gère l'importation d'articles Markdown, la recherche plein texte, et l'historique des consultations.

Le fichier `src/gui/widgets/bots/bot_accueil_knowledge.py` définit quant à lui le **dictionnaire de connaissances conversationnelles** du bot Accueil (réponses, mots-clés, suggestions).

---

## Architecture

```
data/aide_knowledge/
    faq/*.md
    guide_bots/*.md          _scan_knowledge_files()
    technique/*.md        ──────────────────►  _parse_markdown_file()
    tutoriels/*.md                                   │
                                                     ▼
                                            ┌─────────────────┐
                                            │   AideDB        │
                                            │   (SQLite)      │
                                            │                 │
                                            │  articles       │
                                            │  history        │
                                            └─────────────────┘
                                                     │
                                                     ▼
                                            bot_accueil_knowledge.py
                                            (dictionnaire KNOWLEDGE
                                             pour réponses directes)
```

Deux couches distinctes :
1. **AideDB** (base de données SQLite) — articles longs, recherche plein texte, historique
2. **KNOWLEDGE** (dictionnaire Python) — réponses courtes, matching par mots-clés, navigation

---

## 1. Stockage SQLite — Schéma

```sql
CREATE TABLE articles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category    TEXT NOT NULL,
    title       TEXT NOT NULL UNIQUE,
    keywords    TEXT,       -- JSON list
    content     TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id   INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    question     TEXT,
    consulted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Table `articles`

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | INTEGER | Clé primaire auto-incrémentée |
| `category` | TEXT | Catégorie : `faq`, `guide_bots`, `technique`, `tutoriels` |
| `title` | TEXT | Titre de l'article (UNIQUE) |
| `keywords` | TEXT | Liste JSON de mots-clés pour la recherche |
| `content` | TEXT | Contenu complet en Markdown |
| `created_at` | TIMESTAMP | Date de création |
| `updated_at` | TIMESTAMP | Date de modification |

### Table `history`

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | INTEGER | Clé primaire |
| `article_id` | INTEGER | FK → `articles.id` avec CASCADE DELETE |
| `question` | TEXT | Question posée par l'utilisateur |
| `consulted_at` | TIMESTAMP | Horodatage de la consultation |

---

## 2. Importation des articles

### `_scan_knowledge_files(repertoire)`

Scanne récursivement un répertoire pour trouver tous les fichiers `.md`.

```python
def _scan_knowledge_files(repertoire: Path) -> list[Path]:
    return sorted(repertoire.rglob("*.md"))
```

### `_parse_markdown_file(chemin)`

Analyse un fichier Markdown avec frontmatter YAML :

```yaml
---
title: "Titre de l'article"
category: technique
icon: 🔧
keywords:
  - mot cle 1
  - mot cle 2
---
```

Extrait :
- `title` (obligatoire)
- `category` (obligatoire)
- `keywords` (optionnel, liste)
- `content` (tout ce qui suit le frontmatter)

### `init_database(repertoire)`

1. Crée les tables si elles n'existent pas
2. Si la table `articles` est **vide** : scanne le répertoire, parse chaque fichier, insère en base
3. Les doublons (`title` UNIQUE) sont ignorés silencieusement

> **Note** : L'import n'a lieu qu'une seule fois. Pour réimporter, il faut supprimer le fichier `bot_aide.db`.

---

## 3. Système de recherche

### `search(query, limit=10)`

Recherche par `LIKE` sur le titre et les mots-clés :

```sql
SELECT * FROM articles
WHERE title LIKE '%query%' OR keywords LIKE '%query%'
ORDER BY
    CASE WHEN title LIKE '%query%' THEN 0 ELSE 1 END,
    title
LIMIT ?
```

Les résultats avec correspondance dans le titre sont prioritaires.

### `find_best_match(query)`

Stratégie de recherche par paliers progressifs :

| Palier | Recherche | Description |
|--------|-----------|-------------|
| 1 | Titre **exact** | `title = query` (insensible à la casse) |
| 2 | Titre `LIKE` | `title LIKE '%query%'` |
| 3 | Mots-clés `LIKE` | `keywords LIKE '%query%'` |
| 4 | Mots isolés | Chaque mot du titre cherché individuellement |

Retourne le meilleur résultat ou `None`.

### `find_by_title(title)`

Recherche exacte par titre :

```python
def find_by_title(self, title: str) -> dict | None:
    return self._fetch_one("SELECT * FROM articles WHERE title = ?", (title,))
```

### `get_all_articles(category=None)`

Liste tous les articles, optionnellement filtrés par catégorie.

### `get_categories()`

Retourne la liste des catégories distinctes :
```python
def get_categories(self) -> list[str]:
    rows = self._fetch_all("SELECT DISTINCT category FROM articles ORDER BY category")
    return [row["category"] for row in rows]
```

### `count_articles()`

Retourne le nombre total d'articles.

---

## 4. Historique des consultations

```python
def add_history(self, article_id: int, question: str = "") -> None:
    """Enregistre une consultation d'article."""
    self._execute("INSERT INTO history (article_id, question) VALUES (?, ?)",
                  (article_id, question))

def get_history(self, limit: int = 20) -> list[dict]:
    """Retourne les N dernières consultations avec les infos articles."""
    return self._fetch_all("""
        SELECT h.id, h.question, h.consulted_at,
               a.id AS article_id, a.title, a.category
        FROM history h
        JOIN articles a ON a.id = h.article_id
        ORDER BY h.consulted_at DESC
        LIMIT ?
    """, (limit,))

def delete_history_entry(self, entry_id: int) -> None:
    self._execute("DELETE FROM history WHERE id = ?", (entry_id,))

def clear_history(self) -> None:
    self._execute("DELETE FROM history")
```

---

## 5. Bot Accueil — Dictionnaire KNOWLEDGE

Le fichier `bot_accueil_knowledge.py` définit un dictionnaire `KNOWLEDGE` structuré ainsi :

```python
KNOWLEDGE = {
    "chercher": {
        "keywords": ["chercher", "recherche", "trouver"],
        "icon": "🔍",
        "response": "Le bot <b>Recherche</b> permet de...",
        "actions": [{"type": "navigate", "bot": "bot_recherche"}],
        "suggestions": ["Recherche globale", "Par salon", "Par utilisateur"]
    },
    "fallback": {
        "keywords": [],
        "response": "Je n'ai pas compris...",
        "suggestions": ["Chercher un fichier", "Aide", "Configuration"]
    },
    "fallback_insulte": {
        "keywords": ["insulte1", "insulte2"],
        "response": "Restons calmes...",
        "actions": [{"type": "delay", "ms": 500}]
    }
}
```

### Fonctionnement

1. Le message utilisateur est matché **insensiblement** contre les `keywords` de chaque entrée
2. Si correspondance → affiche `icon` + `response` + `actions` + `suggestions`
3. L'action `navigate` redirige vers un autre bot de l'interface
4. Si aucune correspondance → entrée `fallback` par défaut
5. Cas particulier : `fallback_insulte` pour les messages agressifs

---

## 6. Cycle de vie complet

```
Démarrage app
      │
      ▼
AideDB.__init__()
      │
      ▼
AideDB.init_database("data/aide_knowledge")
      │
      ├── Crée les tables SQLite
      │
      └── Si vide : scanne 74 fichiers .md
                      parse frontmatter YAML
                      insère dans articles
      │
      ▼
Bot Accueil ←→ AideDB.search(query)
                    │
                    ▼
                find_best_match(query)
                    │
                    ▼
                Affiche article + add_history()
```

---

## Conclusion

Le système AideDB est un moteur de connaissances **simple mais efficace** :

- **Import** : Frontmatter YAML + Markdown → SQLite
- **Recherche** : `LIKE` sur titre et mots-clés avec stratégie à 4 paliers
- **Historique** : Traçage des consultations pour amélioration
- **Bot Accueil** : Dictionnaire KNOWLEDGE pour réponses rapides et navigation

L'architecture en deux couches (SQLite pour les articles longs + dictionnaire pour les réponses courtes) permet une maintenance aisée : ajouter un article = créer un fichier `.md`, ajouter une réponse = modifier `bot_accueil_knowledge.py`.
