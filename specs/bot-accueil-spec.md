# Spec — Bot Accueil

> **Mission :** Assistant conversationnel — hub central qui accueille l'utilisateur,
> discute de l'app, comprend les demandes en langage naturel, et délègue aux
> autres bots via un dictionnaire de connaissances.

---

## 1. Principes fondamentaux

| Principe | Valeur |
|----------|--------|
| **Nature** | Nouvelle page de bot, PAS l'ancienne `HomePage` |
| **Rôle** | Chatbot conversationnel avec champ de saisie libre |
| **Personnalité** | Amical et décontracté (tutoiement, ton chaleureux) |
| **Visibilité** | UNIQUEMENT quand l'utilisateur est connecté à Soulseek |
| **Canal d'entrée** | Footer → `page_changed("Accueil")` → `CenterZone.show_page("Accueil")` |
| **Interaction** | Saisie libre **et** boutons de suggestion (hybride) |

---

## 2. Architecture des fichiers

| Fichier | Rôle |
|---------|------|
| `src/gui/widgets/bots/bot_accueil.py` | Classe principale `BotAccueil(QFrame)` + sous-composants UI |
| `src/gui/widgets/bots/bot_accueil_knowledge.py` | Dictionnaire `KNOWLEDGE` avec toutes les entrées de dialogue |
| `src/gui/widgets/bots/__init__.py` | Export de `BotAccueil` |
| `src/data/bot_accueil_history.json` | Persistance de l'historique des conversations (créé auto) |

---

## 3. Interface — Chatbot

### 3.1 Structure visuelle

```
┌────────────────────────────────────────┐
│  ┌──────────────────────────────────┐  │
│  │ 🖐️ Salut ! Je suis le bot      │  │
│  │ Accueil... Que veux-tu faire ?  │  │  ← MessageCard (bot)
│  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │ 👤 je veux chercher un fichier  │  │  ← UserMessageCard (utilisateur)
│  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │ 🔍 Bien sûr ! Le bot Recherche  │  │
│  │ est spécialisé... Je t'envoie   │  │
│  └──────────────────────────────────┘  │
│                                        │
│  ─── suggestions ─────────────────    │
│  [🔍 Oui, cherche !] [🏠 Accueil]     │
│  ─── input bar ────────────────────   │
│  ┌──────────────────[🗑️ Vider][Envoyer] │
│  │ Écris ton message ici…           │ │
│  └──────────────────────────────────┘ │
└────────────────────────────────────────┘
```

### 3.2 Éléments de l'interface (ordre du layout)

1. **Zone de messages** (`QScrollArea`, stretch 1) — messages empilés du bas vers le haut
2. **Barre de suggestions** (`QWidget`, hauteur fixe) — boutons dynamiques uniquement
3. **Barre de saisie** (`QWidget`, hauteur fixe) — `QLineEdit` + bouton `Envoyer` + bouton `🗑️ Vider`

### 3.3 Cartes de message

#### MessageCard (bot)

| Propriété | Valeur |
|-----------|--------|
| Fond | `#2a2a3a` |
| Bordure | `1px solid #3a3a4a` |
| Border-radius | `8px` |
| Padding | `12px` |
| Icône | Emoji 24px dans cercle 36×36 |
| Texte | `#e4e4ec` — `RichText` (supporte `<b>`, `<br>`) |
| Largeur max | 100% du conteneur |

#### UserMessageCard (utilisateur)

| Propriété | Valeur |
|-----------|--------|
| Fond | `#1e1e2e` |
| Bordure | `1px solid #3a3a5a` |
| Border-radius | `8px` |
| Alignement | **Gauche** |
| Icône | 👤 16px |
| Texte | `#a0a0d0` — italic, RichText |
| Style distinct | Plus sombre que les messages du bot |

### 3.4 Barre de saisie

| Élément | Style |
|---------|-------|
| `QLineEdit` | Fond `#1e1e2e`, bordure `#3a3a4a`, border-radius `12px`, placeholder "Écris ton message ici…" |
| Focus | Bordure `#6c5ce7` (violet) |
| Bouton `Envoyer` | Fond `#6c5ce7`, hover `#7c6cf7`, pressed `#5b4cd6`, disabled `#3a3a4a` |
| Déclencheur | `returnPressed` **ou** clic sur `Envoyer` |

### 3.5 Bouton 🗑️ Vider le chat (permanent)

- Situé dans la **barre de saisie**, à droite du bouton Envoyer
- **Toujours visible** — pas dépendant des suggestions (ne disparaît pas quand on clique sur une suggestion)
- Fond transparent `#5a5a6a`, bordure `#3a3a4a`, `border-radius: 12px`
- **Hover :** fond `#2a2a3a`, texte `#e4e4ec`, **bordure rouge `#e74c3c`** pour signaler l'action destructive
- Appelle `_on_clear_history()` → `clear_history()` → vide les messages + sauvegarde JSON vide → re-affiche bienvenue

---

## 4. Dictionnaire de connaissances (KNOWLEDGE)

### 4.1 Structure d'une entrée

```python
KNOWLEDGE: dict[str, dict] = {
    "chercher": {
        "keywords": ["chercher", "recherche", "trouver", ...],
        "icon": "🔍",
        "response": "Bien sûr ! Le bot <b>Recherche</b>...",
        "actions": [                         # optionnel
            {"type": "navigate", "bot": "Recherche"},
        ],
        "suggestions": [                     # optionnel
            {"label": "🔍 Oui, cherche !", "action": "chercher"},
        ],
    },
}
```

| Clé | Type | Obligatoire | Description |
|-----|------|-------------|-------------|
| `keywords` | `list[str]` | Oui | Mots-clés déclencheurs (matché insensiblement) |
| `icon` | `str` | Oui | Emoji affiché dans la carte de réponse |
| `response` | `str` | Oui | Texte de réponse (support RichText : `<b>`, `<br>`) |
| `actions` | `list[dict]` | Non | Actions à exécuter **après** la réponse (delay 600ms) |
| `suggestions` | `list[dict]` | Non | Boutons de suggestion affichés après la réponse |

### 4.2 Types d'actions (combo actions)

| Type | Paramètres | Effet |
|------|------------|-------|
| `message` | `icon`, `text`, `suggestions` | Ajoute un message bot supplémentaire (400ms après) |
| `navigate` | `bot`, `icon` | Message redirection → 1.5s → `page_changed.emit(bot)` |
| `delay` | `ms` | Attend N millisecondes avant l'action suivante |
| `suggestions` | `items` | Remplace les suggestions sans message |

### 4.3 Exemple de combo action (entrée "aide")

```python
"aide": {
    "keywords": ["aide", "help", "comment", "problème", ...],
    "icon": "❓",
    "response": "Tu as besoin d'explications...",
    "actions": [
        {"type": "navigate", "bot": "Aide"},  # redirige vers le bot Aide
    ],
    "suggestions": [
        {"label": "❓ Aide-moi !", "action": "aide"},
        {"label": "🏠 Accueil", "action": "welcome"},
    ],
}
```

### 4.4 Catalogue complet des entrées (18 entrées)

| ID | Type | Keywords | Actions | Suggestions |
|----|------|----------|---------|-------------|
| `chercher` | → Bot | chercher, recherche, trouver, fichier… | navigate → Recherche | Chercher, Accueil |
| `telechargement` | → Bot | téléchargement, dl, download… | navigate → Téléchargement | DL, Accueil |
| `aide` | → Bot | aide, help, comment, problème… | navigate → Aide | Aide, Accueil |
| `bibliotheque` | → Bot | bibliothèque, explorer, dossier… | navigate → Bibliothèque | Explorer, Accueil |
| `utilisateurs` | → Bot | utilisateurs, amis, contact… | navigate → Utilisateurs | Contacts, Accueil |
| `wishlist` | → Bot | wishlist, souhait, automatique… | navigate → Wishlist | Wishlist, Accueil |
| `surveillance` | → Bot | surveillance, alerte, notification… | navigate → Surveillance | Alertes, Accueil |
| `planificateur` | → Bot | planificateur, tâche, automatisation… | navigate → Planificateur | Planifier, Accueil |
| `nettoyage` | → Bot | nettoyage, organiser, ranger… | navigate → Nettoyage | Nettoyer, Accueil |
| `statistiques` | → Bot | statistiques, stats, dashboard… | navigate → Statistiques | Stats, Accueil |
| `assistant` | → Bot | assistant, config, paramètre… | navigate → Assistant | Configurer, Accueil |
| `bonjour` | Général | bonjour, salut, hey, hello… | — | Chercher, DL, Aide, Retour |
| `merci` | Général | merci, thanks, super, génial… | — | Chercher, Aide, Accueil |
| `qui_es_tu` | Général | qui es-tu, présentation, armée… | — | 12 bots, Chercher, Aide, Accueil |
| `soulseek` | Général | soulseek, slsk, p2p, réseau… | — | Chercher, Aide, Accueil |
| `quoi_de_neuf` | Général | quoi de neuf, nouveau, actu… | — | Surveillance, Stats, Accueil |
| `fallback` | Fallback | *(match jamais par mot-clé)* | — | Chercher, DL, Aide, About, Accueil |
| `fallback_insulte` | Fallback | connard, idiot, merde, fuck… | — | Désolé, Aide |

---

## 5. Moteur de matching d'intention

### 5.1 `_match_intent(text: str) -> str | None`

```python
def _match_intent(self, text: str) -> str | None:
```

**Algorithme :**
1. Normalise le texte (lowercase, strip)
2. Extrait les mots de ≥ 3 caractères
3. Pour chaque entrée `KNOWLEDGE` :
   - Match exact du keyword dans le texte : **+3 points**
   - Match partiel (un mot ≥ 3 car. commence par le keyword ou vice-versa) : **+1 point**
4. Retourne l'ID avec le **meilleur score**
5. Si **best_score < 3** → retourne `None` (fallback)

### 5.2 Parcours d'une interaction utilisateur

```
Utilisateur tape → _on_user_input()
  ├─ 1. add_user_message(text)        → affiche UserMessageCard
  ├─ 2. _match_intent(text)           → trouve l'intention
  ├─ 3. Si match :
  │     ├─ add_message(icon, response, suggestions)  → MessageCard
  │     └─ si actions : QTimer 600ms → _execute_actions(actions)
  └─ 4. Si aucun match (fallback) :
        └─ add_message("Je n'ai pas bien compris...", suggestions)
```

### 5.3 Fallback

- **Entrée `fallback`** : réutilisée par `_on_user_input` quand aucun match atteint le seuil
- **Entrée `fallback_insulte`** : match les insultes (connard, idiot, merde…) → réponse diplomatique
- Les deux fallbacks offrent des suggestions pour remettre l'utilisateur sur la bonne voie

---

## 6. Exécuteur d'actions (combos)

### 6.1 `_execute_actions(actions: list[dict])`

Exécute une séquence d'actions enchaînées via `QTimer.singleShot` :

```
_run_step(0)
  ├─ action[0]: "message"   → add_message() → timer 400ms → _run_step(1)
  ├─ action[1]: "delay"     → timer N ms    → _run_step(2)
  ├─ action[2]: "navigate"  → navigate_to() → STOP (gère son propre timer)
  ├─ action[3]: "suggestions" → set_suggestions() → timer 100ms → _run_step(4)
  └─ action[4]: "message"   → add_message() → timer 400ms → _run_step(5)
```

**Notes :**
- `navigate` est terminal (appelle son propre `QTimer.singleShot(1500)` interne)
- `delay` capture correctement `index` via `lambda idx=index: _run_step(idx + 1)`
- Les autres actions passent `index + 1` directement

---

## 7. Navigation vers un autre bot

### 7.1 `navigate_to(bot_name: str, icon: str = "➡️")`

1. Ajoute un message : `"Je t'emmène vers le bot <b>{bot_name}</b> … 🔄"`
2. Vide les suggestions (`_clear_suggestions`)
3. `QTimer.singleShot(1500, ...)` → `self.page_changed.emit(bot_name)`

### 7.2 Noms de bots supportés (dans le routeur)

| Action | Bot cible | Signal |
|--------|-----------|--------|
| `search` | `Recherche` | `page_changed.emit("Recherche")` |
| `downloads` | `Téléchargement` | `page_changed.emit("Téléchargement")` |
| `help` | `Aide` | `page_changed.emit("Aide")` |
| `library` | `Bibliothèque` | `page_changed.emit("Bibliothèque")` |
| `users` | `Utilisateurs` | `page_changed.emit("Utilisateurs")` |
| `wishlist` | `Wishlist` | `page_changed.emit("Wishlist")` |
| `surveillance` | `Surveillance` | `page_changed.emit("Surveillance")` |
| `planificateur` | `Planificateur` | `page_changed.emit("Planificateur")` |
| `nettoyage` | `Nettoyage` | `page_changed.emit("Nettoyage")` |
| `stats` | `Statistiques` | `page_changed.emit("Statistiques")` |
| `config` | `Assistant` | `page_changed.emit("Assistant")` |
| `about` | *(interne)* | `_show_about()` |
| `welcome` | *(interne)* | `_show_welcome()` |
| `clear_history` | *(interne)* | `_on_clear_history()` → `clear_history()` |
| `restore_history` | *(interne)* | `_on_restore_history()` → `_restore_history()` |

---

## 8. Persistance de l'historique

### 8.1 Stockage

- **Fichier :** `data/bot_accueil_history.json` (relatif à la racine du projet, dossier `src/`)
- **Création automatique** du dossier parent dans `__init__` (`mkdir(parents=True, exist_ok=True)`)
- **Format :**

```json
{
  "messages": [
    {
      "type": "bot",
      "icon": "🖐️",
      "text": "Salut ! Je suis le bot <b>Accueil</b>...",
      "suggestions": [
        {"label": "🔍 Chercher un fichier", "action": "search"}
      ],
      "timestamp": "2026-05-14T14:30:00"
    },
    {
      "type": "user",
      "text": "je veux chercher un fichier",
      "timestamp": "2026-05-14T14:30:05"
    }
  ]
}
```

### 8.2 Méthodes

| Méthode | Quand | Effet |
|---------|-------|-------|
| `_check_history_exists()` | Dans `_show_welcome()` | Vérifie si le fichier JSON existe et a une taille > 10 octets → définit `self._has_history` |
| `_restore_history()` | Bouton "📜 Conversation précédente" | Lit le fichier **avant** de vider l'écran, restaure tous les messages et les suggestions du dernier message |
| `_save_history()` | Après chaque `add_message()` ou `add_user_message()` | Sauvegarde l'état actuel de `self._messages` dans le fichier JSON |
| `clear_history()` | Bouton 🗑️ Vider | Vide `_messages`, supprime tous les widgets, **sauvegarde** le JSON vide, affiche bienvenue |
| `_on_restore_history()` | Routeur `restore_history` | Appelle `_restore_history()` |
| `_on_clear_history()` | Routeur `clear_history` | Appelle `clear_history()` |

### 8.3 Comportement au démarrage

- **`__init__` NE charge pas l'historique** — le chat repart toujours **à zéro** avec `_show_welcome()`
- L'historique est **toujours sauvegardé** (via `_save_history()` dans `add_message()` / `add_user_message()`)
- Si un historique non vide existe, le message de bienvenue propose **"📜 Conversation précédente"**
- Cliquer sur ce bouton → `_restore_history()` :
  1. Lit d'abord le fichier JSON dans une variable locale
  2. Vérifie qu'il y a des messages
  3. Vide l'écran **sans** appeler `_save_history()` (pour ne pas écraser les données)
  4. Rejou tous les messages (bot + user) dans l'ordre
  5. Restaure les suggestions du dernier message
- ⚠️ **Bug fix critique** : `_restore_history()` lit le fichier **AVANT** de vider l'écran, pour éviter que `clear_history()` → `_save_history()` écrase le fichier avec `{"messages": []}`

### 8.4 Gestion des erreurs

- `json.JSONDecodeError` → fichier corrompu → historique réinitialisé (retour au message de bienvenue)
- `KeyError` → message mal formé → historique réinitialisé
- `OSError` → écriture impossible → ignoré silencieusement

---

## 9. Intégration dans CenterZone

### 9.1 `center.py`

```python
from src.gui.widgets.bots.bot_accueil import BotAccueil

class CenterZone(QFrame):
    def __init__(self, ...):
        # ...
        # "Accueil" et "Recherche" retirés de la boucle générique des bots
        for name in ("Téléchargement", "Bibliothèque", ...):
            self._build_menu_page(name)

        self._build_accueil_page()     # construit BotAccueil séparément
        self._build_recherche_page()   # construit BotRecherche séparément
        self._build_home_page()        # HomePage pour post-connexion

    def _build_accueil_page(self) -> None:
        page = BotAccueil()
        page.page_changed.connect(self.show_page)
        self._pages["Accueil"] = page
        self._stack.addWidget(page)
```

### 9.2 Pages (deux pages distinctes)

| Clé | Composant | Usage |
|-----|-----------|-------|
| `"accueil"` (minuscule) | `HomePage` | Page post-connexion actuelle (bannière de bienvenue) |
| `"Accueil"` (majuscule) | `BotAccueil` | Nouveau chatbot, accessible depuis le footer |

---

## 10. Contraintes techniques

- **Dépendances** : PySide6 uniquement (QtCore, QtWidgets) + `json` + `datetime` + `pathlib`
- **Pas de dépendances externes** (pas d'API, pas de LLM, pas de réseau)
- **Tous les dialogues sont pré-formatés** dans le dictionnaire `KNOWLEDGE`
- **Le matching est purement lexical** (mots-clés, pas d'IA)
- **Signal `page_changed`** compatible avec les autres composants (Header, Footer, LeftPanel)
- **L'input field se vide** après chaque envoi et reste focusé

---

## 11. Règles & Comportement

### 11.1 Ce que le bot PEUT faire

- Comprendre des demandes en langage naturel (matching par mots-clés)
- Afficher des messages avec icônes et texte formaté (RichText)
- Proposer des suggestions contextuelles
- Exécuter des combos d'actions (message → delay → navigate)
- Rediriger vers n'importe quel autre bot après 1.5s
- Sauvegarder et restaurer l'historique des conversations
- Gérer les insultes avec diplomatie

### 11.2 Ce que le bot NE fait PAS

- Pas de recherche directe sur Soulseek (délègue au bot Recherche)
- Pas de téléchargement / gestion de fichiers (délègue au bot Téléchargement)
- Pas de stats en temps réel (délègue au bot Statistiques)
- Pas d'API externe ou d'IA générative
- Pas de connexion à Soulseek directement

### 11.3 Messages clés

**Message de bienvenue :**
```
🖐️ Salut ! Je suis le bot Accueil, ton assistant personnel sur Soulseek.

Je suis là pour t'aider à utiliser l'appli, trouver des fichiers,
gérer tes téléchargements, et te guider vers le bon bot selon
tes besoins.

Que veux-tu faire ?
```
Suggestions → `[🔍 Chercher un fichier] [📥 Téléchargements] [❓ Aide & explications]`

Si un historique de conversation existe (`data/bot_accueil_history.json` > 10 octets) :
```
Suggestions → `[🔍 Chercher un fichier] [📥 Téléchargements] [❓ Aide & explications] [📜 Conversation précédente]`
```

**Message d'erreur (fallback) :**
```
🤔 Je n'ai pas bien compris ta demande. Peux-tu reformuler ?

Tu peux aussi utiliser les suggestions ci-dessous pour me guider !
```
Suggestions → `[🔍 Chercher] [📥 Téléchargements] [❓ Aide] [🎯 À propos] [🏠 Accueil]`

**Réponse aux insultes :**
```
😅 Woah, doucement ! Je suis là pour t'aider, pas pour me disputer.
Si quelque chose ne va pas, dis-moi ce qui ne fonctionne pas
et je ferai de mon mieux pour t'aider !
```
Suggestions → `[🫤 Désolé…] [❓ Aide]`

---

## 12. Étapes d'implémentation (historique)

| # | Tâche | Statut |
|---|-------|--------|
| 1 | Créer `bot_accueil.py` avec layout, scroll, suggestions bar | ✅ |
| 2 | `MessageCard` — cartes avec icônes + texte RichText | ✅ |
| 3 | Arborescence dialogues + routeur `_on_suggestion` | ✅ |
| 4 | `navigate_to()` avec timer 1.5s + `page_changed.emit()` | ✅ |
| 5 | Persistance historique JSON (`_save_history` / `clear_history`) | ✅ |
| 6 | Intégration dans `CenterZone` (signal `page_changed`, page `"Accueil"`) | ✅ |
| 7 | **Champ de saisie** (`QLineEdit` + bouton Envoyer) | ✅ |
| 8 | **Dictionnaire de connaissances** (`KNOWLEDGE` — 18 entrées) | ✅ |
| 9 | **Moteur de matching** (`_match_intent` — scoring par mots-clés) | ✅ |
| 10 | **Exécuteur de combos** (`_execute_actions` — message/delay/navigate) | ✅ |
| 11 | **UserMessageCard** — messages utilisateur avec style distinct | ✅ |
| 12 | Bouton 🗑️ dans barre de suggestions + `clear_history()` | ✅ |
| 13 | Spécification mise à jour (v1) | ✅ |
| 14 | **Chat init à zéro** — `_load_history()` supprimé de `__init__`, remplacé par `_show_welcome()` + `_check_history_exists()` | ✅ |
| 15 | **Bouton 🗑️ déplacé** dans la barre de saisie (toujours visible) — `_add_clear_history_btn()` supprimé | ✅ |
| 16 | **Bouton "📜 Conversation précédente"** — `_restore_history()` avec bug fix (lecture avant clear) | ✅ |
| 17 | **Bug fix** `_restore_history()` lisait le fichier après l'avoir vidé — maintenant lit d'abord, nettoie sans sauvegarder | ✅ |
| 18 | Spécification mise à jour (v2) | ✅ |
