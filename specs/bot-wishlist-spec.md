# Spec — Bot Wishlist

> **Mission :** Tableau de bord de gestion des souhaits (recherches automatiques).
> Visualiser, ajouter, modifier, supprimer et superviser les souhaits de
> recherche configurés sur Soulseek.
>
> *Le bot Wishlist n'est PAS un chatbot. Les dialogues passent par le bot
> Accueil. Wishlist est une interface CRUD — on y vient pour voir et agir.*

---

## 1. Principes fondamentaux

| Principe | Valeur |
|----------|--------|
| **Nature** | Tableau de bord CRUD (pas un chatbot) |
| **Rôle** | Visualiser et éditer les souhaits de recherche automatique |
| **Personnalité** | Aucune — interface utilitaire, pas de dialogue |
| **Canal d'entrée** | Footer → `page_changed("Wishlist")` OU redirection depuis le bot Accueil |
| **Interaction** | Clics sur boutons, formulaires, toggles — pas de saisie libre « chat » |
| **Données** | Simulées pour l'instant (`_WISHLIST_DATA`). À connecter au backend `SoulseekService` |
| **Modèle backend** | `WishlistSettingEntry(query, enabled)` dans `soulseek_client.py` |

---

## 2. Interface — Tableau de bord

### 2.1 Structure visuelle

```
┌──────────────────────────────────────────────────────────┐
│  📋 Wishlist — Souhaits automatiques                     │
│                                                          │
│  ┌─── Statistiques ──────────────────────────────────┐  │
│  │  [9 Total]  [6 Actifs]  [2 Inactifs]  [1 Erreurs] │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─── Barre d'outils ────────────────────────────────┐  │
│  │  [🔍 Rechercher…]  [📋 Tous] [🟢 Actifs]         │  │
│  │  [⚪ Inactifs] [❌ Erreurs]  [🔄Tout basculer]    │  │
│  │                          [➕ Ajouter un souhait]   │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─── Liste scrollable ──────────────────────────────┐  │
│  │  ┌────────────────────────────────────────────┐   │  │
│  │  │ 🟢 Actif     Pink Floyd - Dark Side        │   │  │
│  │  │ 📅 3 résultat(s) • Dernière : il y a 1h    │   │  │
│  │  │ 🔄 Fréquence : globale                      │   │  │
│  │  │ [✏️ Modifier] [🔍 Chercher]  [🗑️ Supprimer] │   │  │
│  │  └────────────────────────────────────────────┘   │  │
│  │  ┌────────────────────────────────────────────┐   │  │
│  │  │ ⚪ Inactif   Massive Attack                 │   │  │
│  │  │ 📭 0 résultat(s) • Dernière : jamais       │   │  │
│  │  │ 🔄 Fréquence : globale                      │   │  │
│  │  │ [✏️ Modifier] [🔍 Chercher]  [🗑️ Supprimer] │   │  │
│  │  └────────────────────────────────────────────┘   │  │
│  │  ...                                               │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─── Barre d'ajout rapide (cachée par défaut) ──────┐  │
│  │  [Nouveau souhait (ex: 'Pink Floyd')…] [Ajouter]  │  │
│  │                                     [Annuler]      │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ───────── footer (navigation) ───────────────────────  │
└──────────────────────────────────────────────────────────┘
```

### 2.2 Sections de l'interface

| Section | Position | Description |
|---------|----------|-------------|
| **En-tête** | Haut | Titre "📋 Wishlist — Souhaits automatiques" en violet `#6c5ce7` |
| **Statistiques** | Sous l'en-tête | 4 cartes `_StatCard` : Total, Actifs, Inactifs, Erreurs |
| **Barre d'outils** | Milieu-haut | Champ recherche + 4 filtres + "Tout basculer" + "Ajouter" |
| **Liste des souhaits** | Centre | Scrollable (`QScrollArea`), chaque souhait = une `WishlistCard` |
| **Barre d'ajout** | Bas (cachée) | Champ inline + boutons Ajouter/Annuler, sert aussi pour l'édition |
| **Footer** | Bas | Navigation entre bots (existant, pas dans BotWishlist) |

### 2.3 Carte d'un souhait (`WishlistCard`)

Chaque souhait est affiché sous forme de carte verticale :

```
┌────────────────────────────────────────────────────┐
│  🟢 Actif     Pink Floyd - Dark Side               │
│  📅 3 résultat(s) • Dernière : il y a 1h           │
│  🔄 Fréquence : globale                             │
│  [✏️ Modifier] [🔍 Chercher]   [🗑️ Supprimer]      │
└────────────────────────────────────────────────────┘
```

| Élément | Implémentation |
|---------|----------------|
| **Icône statut** | `QPushButton` avec texte "🟢 Actif" / "⚪ Inactif" / "❌ Erreur" |
| **Toggle** | Clic sur le bouton de statut → cycle `_on_toggle()` → émet `toggled(query, enabled)` |
| **Couleur statut** | 🟢 `#2ecc71` | ⚪ `#7f8c8d` | ❌ `#e74c3c` |
| **Requête** | `QLabel` en gras (`<b>query</b>`) |
| **Résultats** | 📅 si > 0, 📭 si 0 |
| **Dernière recherche** | Timestamp relatif ("il y a 1h", "jamais", "à l'instant") |
| **Fréquence** | Texte fixe "🔄 Fréquence : globale" (lecture seule) |
| **Boutons d'action** | `_ActionButton` — 3 boutons : ✏️ Modifier (#3498db), 🔍 Chercher (#2ecc71), 🗑️ Supprimer (#e74c3c) |

### 2.4 Styles visuels

| Élément | Style |
|---------|-------|
| Fond de carte | `#1e1e2e`, bordure 1px couleur statut à 27% d'opacité, `border-radius: 8px` |
| Hover carte | Bordure devient opaque (couleur du statut) |
| Bouton statut | Fond couleur à 13%, bordure 1px, `border-radius: 13px`, hover → fond 27% |
| Boutons action | Transparents, bordure 1px, `border-radius: 10px`, hover → fond 13% |
| Filtres | Boutons checkables, checked → violet `#6c5ce7`, unchecked → gris `#3a3a4a` |
| Bouton Ajouter | Violet `#6c5ce7` plein, texte blanc, hover → `#7c6cf7` |

---

## 3. Fonctionnalités

### 3.1 Vue d'ensemble (statistiques)

4 cartes `_StatCard` (valeur en grand + label en petit) :

| Carte | Couleur |
|-------|---------|
| **Total** | `#6c5ce7` (violet) |
| **Actifs** | `#2ecc71` (vert) |
| **Inactifs** | `#7f8c8d` (gris) |
| **Erreurs** | `#e74c3c` (rouge) |

### 3.2 Actions sur un souhait

| Action | Déclencheur | Effet | État |
|--------|-------------|-------|------|
| **Activer/Désactiver** | Clic sur le bouton de statut 🟢/⚪/❌ | Cycle l'état local + émet `toggled` | ✅ Fonctionnel (données simulées) |
| **Modifier la requête** | Bouton ✏️ Modifier | Affiche la barre d'ajout avec le texte pré-rempli, reconnecte le bouton à `_on_edit_confirm` | ✅ Fonctionnel |
| **Supprimer** | Bouton 🗑️ Supprimer | Supprime directement (TODO: ajouter `QMessageBox` de confirmation) | ⚠️ Pas de confirmation |
| **Rechercher maintenant** | Bouton 🔍 Chercher | Incrémente le compteur + met last_search à "à l'instant" | ✅ Simulation |
| **Ajouter** | Bouton ➕ Ajouter un souhait | Affiche la barre d'ajout inline, confirmation → `add_wish(query)` | ✅ Fonctionnel |
| **Tout basculer** | Bouton 🔄 Tout basculer | Bascule tous les souhaits actifs→inactifs ou inactifs→actifs (selon majorité) | ✅ Fonctionnel |

### 3.3 Filtres et recherche

| Filtre | Effet |
|--------|-------|
| `📋 Tous` | Affiche tous les souhaits |
| `🟢 Actifs` | Affiche uniquement les souhaits avec `status == "active"` |
| `⚪ Inactifs` | Affiche uniquement les souhaits avec `status == "inactive"` |
| `❌ Erreurs` | Affiche uniquement les souhaits avec `status == "error"` |
| **Recherche textuelle** | Filtre les souhaits dont la requête contient le texte saisi (case-insensitive) |

Les filtres sont des `_FilterButton` (QPushButton checkable). Le filtre actif est stocké dans `self._filter` (`"all"` par défaut). La recherche est stockée dans `self._search_text` et filtrée via `_get_filtered_wishlist()`.

### 3.4 États vides

Quand aucun souhait ne correspond au filtre actif, un message centré s'affiche :
> "Aucun souhait trouvé. Clique sur « ➕ Ajouter un souhait » pour en créer un."

---

## 4. Intégration backend

### 4.1 État actuel : données simulées

```python
_WISHLIST_DATA: list[dict] = [
    {"query": "Pink Floyd - Dark Side", "enabled": True,  "results": 3,  "last_search": "il y a 1h",   "status": "active"},
    {"query": "Massive Attack",         "enabled": False, "results": 0,  "last_search": "jamais",      "status": "inactive"},
    {"query": "Portishead - Live",      "enabled": True,  "results": 0,  "last_search": "il y a 2h",   "status": "error"},
    # ... 9 entrées au total
]
```

Champs par entrée :
| Champ | Type | Description |
|-------|------|-------------|
| `query` | `str` | Texte de la requête |
| `enabled` | `bool` | Actif ou inactif |
| `results` | `int` | Nombre de résultats trouvés |
| `last_search` | `str` | Timestamp relatif (texte) |
| `status` | `"active"` \| `"inactive"` \| `"error"` | Statut affiché |

### 4.2 TODO Backend

| Action | Méthode dans BotWishlist | À connecter |
|--------|--------------------------|-------------|
| Charger la wishlist | `_load_wishlist()` | `SoulseekService.settings.wishlist` |
| Ajouter un souhait | `add_wish(query)` | `SoulseekService.add_wishlist(query)` |
| Supprimer un souhait | `remove_wish(query)` | `SoulseekService.remove_wishlist(query)` |
| Activer/Désactiver | `toggle_wish(query, enabled)` | `SoulseekService.toggle_wishlist(query)` |
| Modifier la requête | `update_wish_query(old, new)` | `SoulseekService.update_wishlist(old, new)` |
| Rechercher maintenant | `search_now(query)` | `SoulseekService.search_wishlist_now(query)` |
| Persister | `_save_wishlist()` | Appel API → `wishlist_changed.emit()` |

### 4.3 Modèle backend existant

```python
# Dans soulseek_client.py
class WishlistSettingEntry:
    query: str       # Texte de la requête (ex: "Pink Floyd")
    enabled: bool    # Actif ou inactif
```

Le `wishlist_request_timeout` (fréquence globale) est déjà configuré. Non modifiable depuis Wishlist.

---

## 5. Architecture technique

### 5.1 Fichiers modifiés

| Fichier | Rôle |
|---------|------|
| `src/gui/widgets/bots/bot_wishlist.py` | **Créé** — 719 lignes, classe principale + helpers |
| `src/gui/widgets/bots/__init__.py` | **Modifié** — exporte `BotWishlist` |
| `src/gui/layout/center.py` | **Modifié** — import + page dédiée |

### 5.2 Classes dans `bot_wishlist.py`

```python
class _ActionButton(QPushButton):
    """Petit bouton d'action stylisé (transparent, bordure colorée, hover)."""

class _FilterButton(QPushButton):
    """Bouton de filtre checkable (Tous / Actifs / Inactifs / Erreurs)."""

class _StatCard(QFrame):
    """Petite carte de statistique (valeur + label, fond coloré)."""

class WishlistCard(QFrame):
    """Carte affichant un souhait individuel avec infos et actions.
    
    Signaux :
        toggled = Signal(str, bool)          # (query, new_enabled)
        edit_requested = Signal(str)          # (query)
        delete_requested = Signal(str)        # (query)
        search_now_requested = Signal(str)    # (query)
    """
    # 4 signaux + constructeur + _on_toggle()

class BotWishlist(QFrame):
    """Bot Wishlist — tableau de bord des souhaits automatiques Soulseek.
    
    Signaux :
        wishlist_changed = Signal()
    """
```

### 5.3 Structure interne de `BotWishlist`

```python
class BotWishlist(QFrame):
    wishlist_changed = Signal()

    def __init__(self, parent=None):
        # Layout principal : QVBoxLayout
        #   1. En-tête (QLabel)
        #   2. Statistiques (QWidget + QHBoxLayout + _StatCard x4)
        #   3. Barre d'outils (QWidget + QHBoxLayout)
        #      - QLineEdit (recherche)
        #      - _FilterButton x4
        #      - "🔄 Tout basculer" (QPushButton)
        #      - "➕ Ajouter un souhait" (QPushButton)
        #   4. QScrollArea → liste des WishlistCard
        #   5. Barre d'ajout rapide (cachée par défaut)

    # Données
    def refresh(self) -> None               # Recharge + rebuild
    def _load_wishlist(self) -> list[dict]  # Simulé → TODO backend
    def _save_wishlist(self) -> None        # Simulé (émet signal)

    # Actions CRUD
    def add_wish(self, query: str) -> None
    def remove_wish(self, query: str) -> None
    def toggle_wish(self, query: str, enabled: bool) -> None
    def update_wish_query(self, old_query: str, new_query: str) -> None
    def search_now(self, query: str) -> None

    # Construction UI
    def _rebuild(self) -> None               # Stats + liste
    def _build_stats(self) -> None           # Reconstruit les cartes stats
    def _build_list(self) -> None            # Reconstruit la liste filtrée
    def _get_filtered_wishlist(self) -> list[dict]

    # Handlers
    def _apply_filter(self, filter_id: str) -> None
    def _on_search(self, text: str) -> None
    def _on_add_click(self) -> None
    def _on_add_confirm(self) -> None
    def _on_toggle_all(self) -> None

    # Card handlers
    def _on_card_toggled(self, query, enabled) -> None
    def _on_card_edit(self, query) -> None          # Réutilise la barre d'ajout
    def _on_edit_confirm(self, old_query) -> None   # Confirme l'édition inline
    def _on_card_delete(self, query) -> None
    def _on_card_search(self, query) -> None
```

### 5.4 Intégration dans `center.py`

```python
# Import
from src.gui.widgets.bots.bot_wishlist import BotWishlist

# Construction (dans __init__)
self._build_wishlist_page()

# Méthode dédiée
def _build_wishlist_page(self) -> None:
    page = BotWishlist()
    self._pages["Wishlist"] = page
    self._stack.addWidget(page)
```

- "Wishlist" a été retiré de la boucle générique des bots menus (`_build_menu_page`)
- La navigation footer → `page_changed("Wishlist")` continue de fonctionner
- Les suggestions du bot Accueil → `navigate_to("Wishlist", "📋")` fonctionne aussi

### 5.5 Export dans `bots/__init__.py`

```python
from src.gui.widgets.bots.bot_wishlist import BotWishlist

__all__: list[str] = [
    "BotAccueil",
    "BotWishlist",
]
```

---

## 6. Données & Connexion Soulseek

### 6.1 État actuel

```python
# Dans bot_wishlist.py
_WISHLIST_DATA: list[dict] = [...]  # 9 entrées simulées

class BotWishlist:
    def _load_wishlist(self) -> list[dict]:
        # TODO: Remplacer par un appel au backend Soulseek
        return list(_WISHLIST_DATA)

    def _save_wishlist(self) -> None:
        # TODO: Persister via le backend Soulseek
        self.wishlist_changed.emit()
```

### 6.2 À terme (backend)

```python
# Via SoulseekService
client = SoulseekClientManager.get_instance()  # ou via service injecté
settings = client.settings
wishlist = settings.wishlist  # list[WishlistSettingEntry]
timeout = settings.wishlist_request_timeout  # int (secondes)
```

---

## 7. Règles & Contraintes

### 7.1 Ce que le bot PEUT faire

- Afficher la liste complète des souhaits avec leur statut (carte par carte)
- Filtrer par statut (Tous / Actifs / Inactifs / Erreurs)
- Rechercher textuellement dans les requêtes
- Activer/Désactiver un souhait d'un clic sur son badge de statut
- Tout basculer en un clic (bascule selon la majorité)
- Modifier la requête d'un souhait existant (réutilise la barre d'ajout inline)
- Supprimer un souhait (TODO: ajouter confirmation)
- Ajouter un nouveau souhait via barre inline (Entrée ou bouton)
- Lancer une recherche immédiate sur un souhait (simulation)
- Afficher un résumé statistique (4 cartes en haut de page)

### 7.2 Ce que le bot NE fait PAS

- Pas de dialogue / chat avec l'utilisateur
- Pas de suggestion de requêtes
- Pas de modification de la fréquence globale (c'est pour le bot Assistant)
- Pas d'historique des recherches passées
- Pas de connexion directe aux autres bots
- Pas de drag & drop pour réorganiser

### 7.3 Contraintes techniques

- Utilise `PySide6` uniquement (QtCore, QtWidgets)
- Données simulées en attendant la connexion backend via `SoulseekService`
- Le toggle Actif/Inactif doit être instantané (sans rechargement de page)
- Les erreurs de connexion doivent être gérées proprement (TODO backend)
- La liste se reconstruit via `_rebuild()` après chaque modification

---

## 8. Flux utilisateur typique

### 8.1 Arrivée sur la page

```
1. Utilisateur clique sur "Wishlist" dans le footer
2. OU bot Accueil → navigate_to("Wishlist") via la suggestion
3. BotWishlist affiche :
   - Statistiques : "9 Total • 6 Actifs • 2 Inactifs • 1 Erreur"
   - Liste complète des souhaits avec cartes
   - Filtre par défaut : "📋 Tous" (coché)
```

### 8.2 Ajout d'un souhait

```
1. Utilisateur clique sur "➕ Ajouter un souhait"
2. La barre d'ajout apparaît en bas de la page
3. L'utilisateur tape : "Pink Floyd"
4. Appuie sur Entrée ou clique sur "Ajouter"
5. "Annuler" referme la barre sans ajouter
6. Le souhait apparaît dans la liste (actif par défaut, statut "active")
7. La liste se reconstruit automatiquement
```

### 8.3 Modification du texte d'un souhait

```
1. Utilisateur clique sur ✏️ Modifier dans la carte
2. La barre d'ajout apparaît avec le texte pré-rempli et sélectionné
3. Le bouton "Ajouter" est reconnecté à la fonction de modification
4. L'utilisateur modifie le texte
5. Appuie sur Entrée ou clique (le texte est reconnecté à _on_edit_confirm)
6. La modification est appliquée, la barre se referme
7. Le comportement du bouton d'ajout est restauré
```

### 8.4 Suppression d'un souhait

```
1. Utilisateur clique sur 🗑️ Supprimer
2. (TODO) Popup : "Supprimer le souhait 'query' ?" [Annuler] [Confirmer]
3. Actuellement : suppression directe sans confirmation
4. Le souhait disparaît de la liste
```

### 8.5 Recherche immédiate

```
1. Utilisateur clique sur 🔍 Chercher
2. Le compteur de résultats s'incrémente de 1 (simulation)
3. last_search passe à "à l'instant"
4. Le statut passe à "active"
5. La carte se met à jour instantanément
```

### 8.6 Tout basculer

```
1. Utilisateur clique sur "🔄 Tout basculer"
2. Si majorité d'actifs → tous deviennent inactifs
3. Si majorité d'inactifs/erreurs → tous deviennent actifs
4. Toutes les cartes se mettent à jour instantanément
```

---

## 9. Évolution future (hors scope v1)

- **Connexion backend** : Remplacer les données simulées par `SoulseekService`
- **Confirmation suppression** : Ajouter `QMessageBox` avant `remove_wish()`
- **Notifications** : Le bot Surveillance pourrait alerter quand un souhait trouve de nouveaux résultats
- **Historique** : Conserver l'historique des résultats trouvés par souhait
- **Stats avancées** : Le bot Statistiques pourrait montrer l'activité des souhaits
- **Suggestions** : Proposer des requêtes populaires basées sur les habitudes
- **Drag & drop** : Réorganiser les souhaits par priorité
- **Édition inline** : Remplacer la réutilisation de la barre d'ajout par une édition directe dans la carte

---

## 10. Étapes d'implémentation

| # | Tâche | Statut |
|---|-------|--------|
| 1 | Créer `bot_wishlist.py` — classes `BotWishlist(QFrame)` + `WishlistCard(QFrame)` + helpers | ✅ Fait |
| 2 | Layout du tableau de bord — en-tête, statistiques, barre d'outils, zone scrollable, barre d'ajout | ✅ Fait |
| 3 | `WishlistCard` — carte avec statut cliquable, infos métier, 3 boutons d'action + signaux | ✅ Fait |
| 4 | Données simulées (`_WISHLIST_DATA`) + méthodes CRUD (`add/remove/toggle/update/search`) | ✅ Fait |
| 5 | Filtres (4 boutons checkables) + recherche textuelle temps réel | ✅ Fait |
| 6 | Intégration CenterZone — retirer de la boucle menu + `_build_wishlist_page()` dédiée | ✅ Fait |
| 7 | Export dans `bots/__init__.py` + vérification syntaxe | ✅ Fait |

### Reste à faire (prochaines étapes)

- [ ] Ajouter `QMessageBox` de confirmation avant suppression
- [ ] Connecter au backend `SoulseekService` (remplacer les données simulées)
- [ ] Ajouter gestion des erreurs (client non connecté, timeout, etc.)
- [ ] Ajouter animation ou feedback après ajout/modification/suppression


---

## 11. ❓ Questions résolues

### Architecture et interface

- [x] **WishlistCard (QFrame) plutôt que QTableWidget ou QListView** : Les souhaits sont des entités avec un statut binaire (activé/désactivé), pas des colonnes de données à trier. Une carte visuelle offre un toggle visible, un bouton de recherche immédiate, et une meilleure hiérarchie d’information. QTableWidget aurait été trop rigide pour ces interactions.

- [x] **QScrollArea pour la liste (pas de limite haute)** : Contrairement aux résultats de recherche (200 max) ou aux téléchargements (limite implicite), une wishlist peut contenir 50, 100 ou 200 souhaits sans impact notable sur les performances. Un scroll infini évite à l’utilisateur de devoir paginer.

- [x] **Barre d'ajout inline (bas de page) plutôt que dialogue modal** : L’ajout d’un souhait est l’action la plus fréquente. Un champ de saisie toujours visible en bas évite d’ouvrir un dialogue à chaque ajout. Pattern cohérent avec les applications de todo list.

- [x] **4 stat cards (Total, Actifs, Inactifs, Erreurs) plutôt que 2-3** : Total + Actifs donne le ratio d’utilisation. Inactifs montre ce qui est désactivé volontairement. Erreurs alerte sur les souhaits qui ont échoué (recherche infructueuse, problème réseau). Chaque carte a un rôle distinct.

- [x] **Filtres à 4 états (boutons toggle exclusifs) plutôt que ComboBox** : Les 4 filtres (Tous, Actifs, Inactifs, Erreurs) correspondent exactement aux 4 statuts des stat cards. Des boutons toggle offrent un feedback visuel plus rapide qu’un ComboBox déroulant.

### Stockage et persistance

- [x] **Stockage JSON via `_load_wishlist()`/​`_save_wishlist()` plutôt que SQLite** : Une wishlist contient typiquement 20-100 entrées avec une structure simple (`query`, `enabled`, `date_added`). JSON est plus simple à lire/éditer manuellement et ne nécessite pas de connexion DB. SQLite serait overkill pour ce volume.

- [x] **Signal `wishlist_changed` déclenche la sauvegarde automatique** : Pattern événementiel : chaque action (add/toggle/delete/edit) émet le signal, et le handler centralise la persistance. Évite les appels `_save_wishlist()` éparpillés dans chaque méthode.

- [x] **Pas de limite explicite du nombre de souhaits** : Soulseek n’impose pas de limite sur les wishlist items. Une limite artificielle (ex: 200) frustrerait l’utilisateur. La QScrollArea gère le débordement naturellement.

- [x] **Pas d’historique des souhaits supprimés** : Contrairement aux téléchargements (où l’historique est utile pour le suivi), un souhait supprimé est simplement retiré. Pas de valeur ajoutée à garder une trace.

### Backend et connexion Soulseek

- [x] **Données simulées en attendant la connexion SoulseekService** : Les données simulées (`_WISHLIST_DATA`) ont permis de développer et tester l’UI indépendamment du backend. Architecture préparée pour le remplacement : mêmes signatures de méthode, mêmes signaux.

- [x] **Wishlist connectée via le service central SoulseekService** : L’accès aux souhaits se fera via le service central, pas un service wishlist dédié. Le chemin d’accès exact sera déterminé lors de l’intégration (settings.wishlist ou API dédiée).

- [x] **Pas de service wishlist dédié (contrairement à Téléchargement, Recherche)** : La wishlist est suffisamment simple (CRUD + statut binaire) pour être gérée directement dans le widget. Un service séparé serait une abstraction supplémentaire sans bénéfice.

- [x] **Recherche immédiate (`search_now`) délègue au Bot Recherche** : Quand l’utilisateur clique « Rechercher maintenant » sur un souhait, le bot émet `page_changed("Recherche", query)` pour naviguer vers le bot de recherche. Évite de dupliquer la logique de recherche.

### UX et interactions

- [x] **Toggle binaire (actif/inactif) plutôt que menu déroulant** : Un souhait est soit actif (recherché automatiquement) soit inactif (conservé mais pas recherché). Pas d’état intermédiaire. Le toggle visuel (cœur plein/vide, switch coloré) est instantané et intuitif.

- [x] **Édition inline (remplacement de la requête) plutôt que dialogue d’édition** : Modifier un souhait consiste à changer la chaîne de recherche. Un input inline évite l’ouverture d’un dialogue pour une action simple. Le pattern « cliquer → éditer → valider » est plus rapide.

- [x] **Confirmation de suppression manquante (todo connu)** : La spec liste explicitement l’ajout d’un `QMessageBox` de confirmation comme tâche restante. Décision volontairement reportée pour prioriser le CRUD fonctionnel.

- [x] **Recherche textuelle case-insensitive dans la wishlist** : L’utilisateur tape un terme et la liste se filtre en temps réel. Utilise `str.lower()` dans la compréhension de liste. Pas de fuzzy matching (trop complexe pour le besoin).

- [x] **Pas de Drag & Drop pour réordonner les souhaits** : Les souhaits n’ont pas d’ordre significatif (ils sont recherchés en parallèle). L’ordre d’affichage est celui d’ajout. Le Drag & Drop ajouterait de la complexité pour aucun gain fonctionnel.

### Évolution et périmètre

- [x] **Pas de notifications push (Soulseek ne les supporte pas)** : Soulseek ne fournit pas de mécanisme pour notifier quand un résultat correspond à un souhait. La vérification se fait uniquement par recherche active.

- [x] **Évolution future : wishlist partagée, suggestions automatiques** : Listé dans « Évolution future » car nécessite des fonctionnalités serveur que FreeBuff n’a pas. Préservé dans la spec pour garder la vision produit.

