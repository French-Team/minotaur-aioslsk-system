# Spec — Bot Accueil

> **Mission :** Hub central conversationnel — accueillir l'utilisateur, discuter de l'app,
> déléguer aux autres bots, rediriger vers l'aide.

---

## 1. Principes fondamentaux

| Principe | Valeur |
|----------|--------|
| **Nature** | Nouvelle page de bot, PAS l'ancienne `HomePage` |
| **Rôle** | Assistant conversationnel — interface en chat simulé |
| **Personnalité** | Amical et décontracté (tutoiement, ton chaleureux) |
| **Visibilité** | UNIQUEMENT quand l'utilisateur est connecté à Soulseek |
| **Canal d'entrée** | Footer → `page_changed("accueil")` → `CenterZone.show_page("accueil")` |

---

## 2. Interface — Chat Simulé

### 2.1 Structure visuelle

```
┌────────────────────────────────────────┐
│  ↑ zone de messages (scrollable)      │
│  ┌──────────────────────────────────┐ │
│  │ 🖐️ Salut ! Je suis le bot       │ │
│  │ Accueil. Comment puis-je        │ │
│  │ t'aider aujourd'hui ?           │ │
│  └──────────────────────────────────┘ │
│  ┌──────────────────────────────────┐ │
│  │ 🔍 Tu veux chercher un fichier  │ │
│  │ sur Soulseek ?                  │ │
│  └──────────────────────────────────┘ │
│  ...                                   │
│                                        │
│  ─── zone de suggestions ──────────   │
│  [🔍 Chercher] [📥 DL] [❓ Aide]     │
│  [📚 Bibliothèque] [👤 Amis]         │
└────────────────────────────────────────┘
```

### 2.2 Éléments de l'interface

| Élément | Description |
|---------|-------------|
| **Zone de messages** | `QScrollArea` vertical, messages empilés du bas vers le haut |
| **Messages du bot** | Cartes avec icône arrondies, fond `#2a2a3a`, bordure subtile |
| **Message de bienvenue** | Fixe, affiché à l'arrivée sur la page — salut avec présentation du bot |
| **Zone de suggestions** | Boutons en bas du chat, alignés horizontalement, changent selon le contexte |
| **Barre de défilement** | Auto-scroll vers le bas quand un nouveau message arrive |

### 2.3 Cartes de message (style)

Chaque message du bot est une **carte** avec :
- Une icône/avatar à gauche (👋, 🔍, 📥, etc.)
- Un fond de carte arrondi (`border-radius: 8px`)
- Texte en blanc cassé `#e4e4ec`
- Largeur max 80% du conteneur, alignée à gauche
- Pas de bulles utilisateur (l'utilisateur ne tape pas)

---

## 3. Suggestions & Navigation

### 3.1 Le bot choisit les suggestions

Ce n'est PAS un menu fixe. Le bot affiche dynamiquement des suggestions
sous forme de boutons en bas de l'écran. Exemples :

| Contexte | Suggestions affichées |
|----------|----------------------|
| **Arrivée sur le bot** | 🔍 Chercher un fichier, 📥 Voir les DL, ❓ Aide |
| **Après « Chercher »** | Par titre, Par utilisateur, Par filtre avancé → [Aller vers Recherche] |
| **Après « Aide »** | Configuration, Utilisation des bots, → [Aller vers Aide] |
| **Fin de conversation** | 🔍 Autre recherche, 📚 Bibliothèque, 👤 Amis |

### 3.2 Délégation automatique vers un autre bot

Quand l'utilisateur clique sur une suggestion qui implique un autre bot :

1. **Message du bot Accueil** : « Je t'emmène vers le bot Recherche ! 🔍 »
2. **Pause de 1 à 2 secondes** (via `QTimer.singleShot`)
3. **Changement de page** : `self.page_changed.emit("recherche")` → `CenterZone.show_page()`

La classe `BotAccueil` expose un signal `page_changed = Signal(str)` pour la navigation,
comme les autres composants (Footer, Header, LeftPanel).

### 3.3 Messages pré-formatés (pas de saisie libre)

L'utilisateur interagit UNIQUEMENT via les boutons de suggestion cliquables.
Pas de champ de texte / saisie libre. C'est un chat simulé.

---

## 4. Messages & Arborescence

### 4.1 Message de bienvenue

```
🖐️ Salut ! Je suis le bot Accueil, 
ton assistant personnel sur Soulseek. 

Je suis là pour t'aider à utiliser l'appli, 
trouver des fichiers, gérer tes téléchargements,
et te guider vers le bon bot selon tes besoins.

Que veux-tu faire ?
```

Suggestions après bienvenue : `[🔍 Chercher] [📥 Téléchargements] [❓ Aide]`

### 4.2 Arborescence des dialogues

```
Accueil
├── 🔍 Chercher un fichier
│   ├── → Message : « Je t'emmène vers le bot Recherche… »
│   └── → Redirection vers bot Recherche
│
├── 📥 Gérer les téléchargements
│   ├── → Message : « Direction le bot Téléchargement ! »
│   └── → Redirection vers bot Téléchargement
│
├── 📚 Bibliothèque & fichiers
│   ├── → Message : « Je te laisse avec le bot Bibliothèque. »
│   └── → Redirection vers bot Bibliothèque
│
├── 👤 Gérer mes contacts
│   ├── → Message : « Je te redirige vers les utilisateurs. »
│   └── → Redirection vers bot Utilisateurs
│
├── ❓ Aide & explications
│   ├── Comment utiliser les bots ?
│   ├── Configuration de l'appli
│   ├── → Message : « Le bot Aide va prendre le relais. »
│   └── → Redirection vers bot Aide
│
├── ⚙️ Configuration
│   ├── → Message : « Je te laisse avec l'Assistant. »
│   └── → Redirection vers bot Assistant
│
└── ℹ️ À propos de l'Armée des 12 Bots
    └── → Affiche un message décrivant les 12 bots
```

### 4.3 Suggestions génériques (toujours accessibles)

Les suggestions suivantes devraient être accessibles depuis n'importe quel état :
- `🔍 Chercher` → toujours visible
- `❓ Aide` → toujours visible
- `🏠 Accueil` → retour au message de bienvenue

---

## 5. Données & Persistance

### 5.1 Historique des conversations

**Stockage :** Fichier `data/conversations/accueil.json` ou `data/bot_accueil_history.json`

**Contenu :**
```json
{
  "sessions": [
    {
      "date": "2026-05-14T14:30:00",
      "messages": [
        { "type": "bot", "icon": "🖐️", "text": "Salut ! ...", "suggestions": [...] },
        { "type": "action", "text": "user_clicked_chercher" },
        { "type": "bot", "icon": "🔍", "text": "Je t'emmène vers le bot Recherche...", "suggestions": [...] }
      ]
    }
  ]
}
```

**Format de chaque message :**
```python
{
    "type": "bot" | "action" | "redirect",
    "icon": str,          # emoji pour la carte
    "text": str,          # texte du message
    "suggestions": [      # boutons affichés après ce message
        {"label": "🔍 Chercher", "action": "search"},
        {"label": "❓ Aide", "action": "help"}
    ],
    "timestamp": str      # ISO datetime
}
```

**Comportement :**
- Chargé au démarrage du bot (dans `__init__` ou au premier `show`)
- Affiché dans la zone de chat comme historique
- Sauvegardé quand un nouveau message est ajouté
- Optionnel : bouton « Effacer l'historique » dans la zone de suggestions

---

## 6. Architecture Technique

### 6.1 Fichier

**Emplacement :** `src/gui/widgets/bots/bot_accueil.py`

### 6.2 Classe

```python
class BotAccueil(QFrame):
    """Bot Accueil — hub conversationnel avec chat simulé."""

    page_changed = Signal(str)  # émet le nom du bot cible pour la navigation
```

### 6.3 Structure interne

```python
class BotAccueil(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("botAccueil")

        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Zone de messages (QScrollArea)
        self._messages_area = QScrollArea()
        self._messages_widget = QWidget()
        self._messages_layout = QVBoxLayout(self._messages_widget)
        # ... config scroll area

        # Zone de suggestions (en bas, fixe)
        self._suggestions_bar = QWidget()
        self._suggestions_layout = QHBoxLayout(self._suggestions_bar)
        # ... boutons de suggestions

        layout.addWidget(self._messages_area, 1)  # stretch 1
        layout.addWidget(self._suggestions_bar, 0)  # hauteur fixe

        # Charger l'historique
        self._load_history()

        # Afficher le message de bienvenue (si historique vide)
        if not self._messages:
            self._show_welcome()

    # Signaux
    page_changed = Signal(str)

    # Méthodes principales
    def add_message(self, icon: str, text: str, suggestions: list[dict]) -> None
    def set_suggestions(self, suggestions: list[dict]) -> None
    def navigate_to(self, bot_name: str) -> None  # message + timer + navigation

    # Arborescence dialogues
    def _show_welcome(self) -> None
    def _on_suggestion_clicked(self, action: str) -> None

    # Persistance
    def _load_history(self) -> None
    def _save_history(self) -> None
    def clear_history(self) -> None

    # Suggestions dynamiques
    def _get_generic_suggestions(self) -> list[dict]
```

### 6.4 Intégration dans CenterZone

**Dans `center.py` (`__init__`)** :
```python
from src.gui.widgets.bots.bot_accueil import BotAccueil

# Dans la section des pages construites (vers ligne 108) :
self._bot_accueil = BotAccueil()
self._pages["accueil"] = self._bot_accueil
self._stack.addWidget(self._bot_accueil)

# Connecter le signal de navigation
self._bot_accueil.page_changed.connect(self.show_page)
```

**Supprimer ou conserver `_build_home_page` ?**
- `_build_home_page` reste pour la `HomePage` actuelle (page d'accueil de l'app, avant connexion)
- `BotAccueil` REMPLACE la page `"accueil"` dans le dictionnaire `_pages`
- `show_home()` continue d'appeler `show_page("accueil")` mais affiche maintenant `BotAccueil`
- Si besoin : `show_home()` pourrait aussi réinitialiser le chat et re-afficher le message de bienvenue

---

## 7. Règles & Contraintes

### 7.1 Ce que le bot Accueil PEUT faire

- Afficher des messages avec icônes et texte
- Proposer des boutons de suggestion contextuels
- Attendre 1-2s puis rediriger vers un autre bot
- Charger/sauvegarder l'historique des conversations
- Connaître le nom de l'utilisateur connecté (via `set_greeting` ou équivalent)

### 7.2 Ce que le bot Accueil NE fait PAS

- Pas de saisie libre / champ de texte
- Pas de recherche directe sur Soulseek
- Pas de téléchargement / gestion de fichiers
- Pas de stats en temps réel (ça, c'est pour le bot Statistiques)

### 7.3 Contraintes techniques

- Utiliser `QTimer.singleShot` pour le délai avant redirection
- L'historique persistant doit gérer le cas où le fichier est corrompu
- Pas de dépendances lourdes (garder PySide6 + json uniquement)
- Les suggestions doivent avoir un `action` unique pour la logique de routage

---

## 8. Arborescence des actions

```python
# Routeur de suggestions
_ACTIONS = {
    "welcome":        _show_welcome,
    "search":         lambda: self.navigate_to("recherche", "🔍"),
    "downloads":      lambda: self.navigate_to("telechargement", "📥"),
    "library":        lambda: self.navigate_to("bibliotheque", "📚"),
    "users":          lambda: self.navigate_to("utilisateurs", "👤"),
    "help":           lambda: self.navigate_to("aide", "❓"),
    "config":         lambda: self.navigate_to("assistant", "⚙️"),
    "about":          _show_about,
}
```

---

## 9. Messages clés (catalogue)

### Message de bienvenue
```
🖐️ Salut ! Je suis le bot Accueil, 
ton assistant personnel sur Soulseek. 

Je suis là pour t'aider à utiliser l'appli, 
trouver des fichiers, gérer tes téléchargements,
et te guider vers le bon bot selon tes besoins.

Que veux-tu faire ?
```
Suggestions → `[🔍 Chercher] [📥 Téléchargements] [❓ Aide]`

### Redirection vers Recherche
```
🔍 Pas de souci ! Je t'emmène vers le bot Recherche,
il pourra t'aider à trouver des fichiers sur Soulseek.
```
Après 1.5s → `page_changed.emit("recherche")`

### Redirection vers Téléchargement
```
📥 Je te laisse avec le bot Téléchargement.
Il gère tout ce qui est téléchargements, files d'attente et priorisation.
```
Après 1.5s → `page_changed.emit("telechargement")`

### Redirection vers Aide
```
❓ Tu as besoin d'explications ? 
Je te redirige vers le bot Aide, il connaît tout sur l'appli
et ses 12 bots.
```
Après 1.5s → `page_changed.emit("aide")`

### À propos de l'Armée
```
🎯 L'Armée des 12 Bots est composée de :

🔍 Recherche     — Trouver des fichiers
📥 Téléchargement — Gérer les DL
📚 Bibliothèque  — Explorer les fichiers
👤 Utilisateurs  — Gérer les contacts
📋 Wishlist      — Souhaits automatiques
👁️ Surveillance  — Alertes en direct
📅 Planificateur — Actions planifiées
🧹 Nettoyage     — Organiser les fichiers
📊 Statistiques  — Tableau de bord
⚙️ Assistant     — Configuration guidée
❓ Aide          — Guide & explications

Et moi, le bot Accueil, je suis ton point d'entrée ! 🖐️
```
Suggestions → `[🔍 Chercher] [❓ Aide] [🏠 Accueil]`

---

## 10. Étapes d'implémentation

| # | Tâche | Description |
|---|-------|-------------|
| 1 | Créer `bot_accueil.py` | Classe `BotAccueil(QFrame)` avec layout, scroll, suggestions |
| 2 | Système de messages | `add_message()`, `_render_message()`, cartes avec icônes |
| 3 | Arborescence dialogues | `_ACTIONS`, routeur, messages pré-formatés |
| 4 | Navigation vers bots | `navigate_to()` avec timer avant `page_changed.emit()` |
| 5 | Persistance historique | `_load_history()`, `_save_history()`, format JSON |
| 6 | Intégration CenterZone | Remplacer le placeholder par `BotAccueil`, connecter `page_changed` |
| 7 | Suggestions dynamiques | Adapter les suggestions selon le contexte |
| 8 | Nettoyage | Supprimer l'ancien bout `_build_menu_page("accueil")` si applicable |
