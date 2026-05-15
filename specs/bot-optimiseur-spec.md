# Spécification — Bot Optimiseur

> **Contexte** : Application de chat Soulseek (PySide6). Architecture existante : bots (BotAccueil, BotWishlist, BotBibliotheque, BotRecherche) + pages de config (Général, Réseau, Recherche, Téléchargement, Utilisateurs, Partages, Salons, Debug) dans sidebar sous `CONFIGURATIONS` via `_build_config_pages()` + pages footer construites via `_build_menu_page()`. Navigation par footer + sidebar.

---

## 1. Concept général

Le **Bot Optimiseur** est un tableau de bord d'optimisation centralisé. Il permet à l'utilisateur d'appliquer des **profils prédéfinis** qui modifient automatiquement les paramètres configurés dans chaque page de configuration (Réseau, Recherche, Téléchargement, Partages, etc.).

L'Optimiseur est un **actionneur de config** : il lit un profil, navigue vers chaque page de config, modifie les widgets, montre les changements en diff, et revient automatiquement à sa page d'accueil.

---

## 2. Nom et navigation

### 2.1 Que renommer — précision critique

Il y a **deux entités "Utilisateurs"** dans l'application :

| Qui | Où | Renommer ? |
|-----|-----|-----------|
| **Page de config Utilisateurs** (amis/bloqués) | Sidebar `CONFIGURATIONS` via `_build_config_pages()` | **NON** — reste "Utilisateurs" |
| **Bouton footer + page bot associée** | Footer `_BOT_NAMES` + `_build_menu_page("Utilisateurs")` dans `center.py.__init__` | **OUI** → "Optimiseur" |

### 2.2 Changements concrets

| Fichier | Ligne | Changement |
|---------|-------|-----------|
| `src/gui/layout/footer.py` | `_BOT_NAMES` | `"Utilisateurs"` → `"Optimiseur"` |
| `src/gui/layout/center.py` | boucle `_build_menu_page` dans `__init__` | `_build_menu_page("Utilisateurs")` → `_build_menu_page("Optimiseur")` |
| `src/gui/layout/center.py` | clé `_pages["Utilisateurs"]` venant de `_build_menu_page` | `_pages["Optimiseur"]` |
| `src/gui/widgets/config.py` — config "Utilisateurs" (amis/bloqués) | **Aucun changement** | Reste `_pages["Utilisateurs"]` dans `_build_config_pages()` |

**⚠️ Attention** : Ne PAS confondre avec la config "Utilisateurs" dans `_build_config_pages()` (ligne ~580) qui reste inchangée.

### 2.3 Emplacement dans l'UI

- **Pas dans la sidebar** (left.py) — la sidebar garde "Utilisateurs" sous CONFIGURATIONS
- **Bouton dans le footer** uniquement, renommé d'"Utilisateurs" à "Optimiseur"
- La page bot est construite via `_build_menu_page` dans `center.py.__init__`, mais sera **remplacée** par un vrai builder (`_build_optimiseur_page`) qui instancie `BotOptimiseur` au lieu du placeholder vide

### 2.4 Mécanisme d'accès aux pages de config

Le `BotOptimiseur` reçoit une référence à `CenterZone` (injection de dépendances dans le builder) pour :
- Naviguer vers les pages de config : `center_zone.show_page("Réseau")`
- Accéder aux widgets de config : `center_zone.pages.get("Réseau")`
- Envoyer le signal `page_changed` (ou utiliser directement `show_page`)

**Signal** : `BotOptimiseur` expose `page_changed = Signal(str)` comme les autres bots, connecté à `CenterZone.show_page`.

---

## 3. Architecture du profil

### 3.1 Stockage

```
data/profils/
├── par_defaut.json
├── puissance_max.json
├── extreme.json
└── (autres fichiers .json ajoutés par l'utilisateur)
```

**Règle** : Chaque fichier `.json` = un profil. Le nom du fichier (sans extension) sert d'identifiant unique.

**Note** : Pas de profil nommé "Optimiser" — le nom est réservé au bot lui-même. Les profils initiaux sont : "Par défaut", "Puissance max", "Extrême".

### 3.2 Format d'un fichier profil

```json
{
  "name": "Puissance Max",
  "icon": "🚀",
  "description": "Optimise tous les paramètres pour la performance maximale",
  "order": 2,
  "params": {
    "reseau": {
      "connexion.port": 2242,
      "connexion.timeout": 30,
      "connexion.upnp": false,
      "limites.download_speed": 0,
      "limites.upload_speed": 0,
      "reconnexion.auto": true,
      "reconnexion.delay": 5
    },
    "telechargement": {
      "dl.max_parallel": 10,
      "dl.slots": 10,
      "dl.folder": ""
    },
    "recherche": {
      "search.max_results": 500,
      "search.timeout": 60,
      "search.wishlist_interval": 30
    },
    "general": {
      "profil.description": "",
      "profil.interets": ""
    }
  }
}
```

Chaque clé de premier niveau (`reseau`, `telechargement`, `recherche`) correspond à une **page de config**. Les clés internes correspondent aux `config_key` des widgets (`ConfigToggle`/`ConfigEntry`/`ConfigCombo`/`ConfigSpin`).

**Catégories exclues** : `"utilisateurs"` (liste amis/bloqués) — inapproprié pour des profils d'optimisation.

### 3.3 Métadonnées du profil

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `name` | `str` | Oui | Nom d'affichage du profil |
| `icon` | `str` | Non | Emoji ou icône (défaut: `⚙️`) |
| `description` | `str` | Non | Texte explicatif optionnel |
| `order` | `int` | Non | Ordre dans la barre d'action (défaut: alphabétique) |
| `params` | `dict` | Oui | Les paramètres par page de config |

---

## 4. Interface utilisateur

### 4.1 Disposition

```
┌─────────────────────────────────────────────────────────────┐
│  [📋 Par défaut] [🚀 Puissance Max] [🔥 Extrême]            │  ← Barre d'action
├──────────────────────────────┬──────────────────────────────┤
│                              │                              │
│        VIEWER                │        DASHBOARD             │
│    (logs temps réel)         │    (profil + diff)           │
│                              │                              │
│  [14:32:15] Navigation →     │  ┌────────────────────────┐ │
│  Réseau                      │  │  🚀 Puissance Max      │ │
│  [14:32:15] Modif:           │  │  ───────────────────── │ │
│  port: 2234 → 2242           │  │  port: 2234 → 2242    │ │
│  [14:32:16] Modif:           │  │  timeout: 15 → 30     │ │
│  timeout: 15 → 30            │  │  max_speed: 500 → 0   │ │
│  [14:32:17] ✅ Terminé       │  │  max_parallel: 3 → 10 │ │
│  (3 pages, 12 paramètres)    │  └────────────────────────┘ │
│                              │                              │
└──────────────────────────────┴──────────────────────────────┘
```

### 4.2 Barre d'action (haut)

Boutons générés **dynamiquement** depuis `data/profils/` :

- **Détection** : `QFileSystemWatcher` surveille le dossier → auto-reload
- **Bouton actif** : profil actuellement appliqué → état `checked`
- **Ordre** : par `order` dans le JSON, puis alphabétique

### 4.3 Viewer (gauche, ~60%)

**Logs en temps réel** — `QTextEdit` en lecture seule avec défilement automatique.

```
[14:32:15] 📍 Navigation → Réseau
[14:32:15]   ⚙ connexion.port : 2234 → 2242
[14:32:16]   ⚙ connexion.timeout : 15 → 30
[14:32:16] 📍 Navigation → Téléchargement
[14:32:16]   ⚙ dl.max_parallel : 3 → 10
[14:32:17] ✅ Profil "Puissance Max" appliqué (3 pages, 12 paramètres en 2.3s)
```

### 4.4 Dashboard (droite, ~40%)

Affiche le **diff** complet après application :
- **En-tête** : icône + nom du profil actif
- **Liste des diffs** : `clé : ancienne_valeur → nouvelle_valeur`
- **Statut** : ✅ Appliqué / ⚠ Partiel / ❌ Échec

---

## 5. Mécanisme d'application d'un profil

### 5.1 API des pages de config

Chaque page de config expose :

```python
def applique_profile(self, data: dict) -> list[tuple[str, str, str, QWidget | None]]:
    """
    Applique les valeurs du profil aux widgets de la page.

    Args:
        data: Dictionnaire {config_key: valeur}

    Returns:
        Liste de (config_key, valeur_avant, valeur_après, widget_modifié)
        widget_modifié = None si le widget n'a pas été trouvé
    """
```

**Où implémenter** : Dans `src/gui/widgets/config.py`, au niveau de `ConfigPage` ou par une classe mixin héritée par chaque page de config.

### 5.2 Logique complète d'application

```
1. User clique sur un bouton profil
2. Optimiseur vide les logs et le dashboard
3. Optimiseur lit et parse le fichier .json
4. Pour chaque (catégorie, params) dans le profil :
   a. Détermine la page via CATEGORIE_TO_PAGE (voir §5.3)
   b. Récupère le widget de page via center_zone._pages[nom_page]
   c. Navigue vers la page via center_zone.show_page(nom_page)
   d. Vérifie que la page a la méthode applique_profile()
   e. Appelle page.applique_profile(params) → récupère les diffs
   f. Pour chaque diff : log dans le viewer + update dashboard
   g. Pour chaque diff avec widget : scroll + highlight
   h. Attends 0.5s (pause entre les pages pour lisibilité)
5. Après la dernière page :
   a. Marque le bouton profil comme actif
   b. Attend 3s (auto-retour)
   c. Affiche message flottant "Retour Optimiseur dans Xs..." + bouton "Rester"
   d. Si timer expire → show_page("Optimiseur")
```

### 5.3 Mapping catégorie → page

```python
CATEGORIE_TO_PAGE: dict[str, str] = {
    "general":       "Général",
    "reseau":        "Réseau",
    "recherche":     "Recherche",
    "telechargement": "Téléchargement",
    "utilisateurs":  "Utilisateurs",   # page config (amis/bloqués) — optionnel
    "partages":      "Partages",
    "salons":        "Salons",
    "debug":         "Debug",
}
```

Si une catégorie du profil n'a pas de correspondance → log `⚠ Catégorie "{nom}" ignorée (page introuvable)`.

### 5.4 Récupération de la valeur "avant"

```python
# Dans applique_profile de chaque ConfigPage :
def applique_profile(self, data: dict) -> list[tuple[str, str, str, QWidget | None]]:
    results = []
    for config_key, nouvelle_valeur in data.items():
        widget = self._find_widget_by_key(config_key)  # méthode helper
        if widget is None:
            results.append((config_key, "?", str(nouvelle_valeur), None))
            continue
        ancienne = widget_get_value(widget)  # isChecked(), text(), value() selon type
        widget_set_value(widget, nouvelle_valeur)
        results.append((config_key, str(ancienne), str(nouvelle_valeur), widget))
    return results
```

### 5.5 Highlight des widgets modifiés

Quand l'Optimiseur a modifié un widget sur une page de config :

```python
def highlight_widget(widget: QWidget, duree_ms: int = 1500) -> None:
    """Fait clignoter un widget pour signaler qu'il a été modifié."""
    # 1. Scroll jusqu'au widget
    scroll_area = widget.ancestor(QScrollArea)
    if scroll_area:
        scroll_area.ensureWidgetVisible(widget)
    # 2. Animation de surbrillance
    style_original = widget.styleSheet()
    widget.setStyleSheet("background: rgba(108, 92, 231, 0.15); border: 1px solid #6c5ce7;")
    QTimer.singleShot(duree_ms, lambda: widget.setStyleSheet(style_original))
```

**Implémenté dans** : `src/gui/widgets/config.py` comme fonction utilitaire accessible depuis toutes les pages de config.

### 5.6 Auto-retour

Après la dernière modification, si l'utilisateur est sur une page de config :

1. Un **overlay semi-transparent** apparaît en haut de la page de config :
   ```
   ┌─────────────────────────────────────────┐
   │ ✅ Profil appliqué. Retour Optimiseur   │
   │    dans 3s... [⏸️ Rester ici]           │
   └─────────────────────────────────────────┘
   ```
2. Timer de 3 secondes, décrémente l'affichage chaque seconde
3. Si user clique "Rester ici" → timer annulé, overlay disparaît
4. Si timer expire → `show_page("Optimiseur")`

**Mécanisme** : Utiliser un `QFrame` flottant ajouté au layout de la page config courante, ou un `QLabel` en `setWindowFlags(Qt.ToolTip)`.

---

## 6. Fichiers à créer

| Fichier | Contenu |
|---------|---------|
| `src/gui/widgets/bots/bot_optimiseur.py` | Classe `BotOptimiseur(QFrame)` — UI complète du bot |
| `data/profils/par_defaut.json` | Profil "Par défaut" — réglages standards |
| `data/profils/puissance_max.json` | Profil "Puissance max" — performance brute |
| `data/profils/extreme.json` | Profil "Extrême" — tout débrider |

---

## 7. Fichiers à modifier

| Fichier | Modification |
|---------|-------------|
| `src/gui/layout/footer.py` | `_BOT_NAMES` : `"Utilisateurs"` → `"Optimiseur"` |
| `src/gui/layout/center.py` | Renommer `_build_menu_page("Utilisateurs")` → `"Optimiseur"` dans la boucle `__init__` + clé `_pages["Optimiseur"]` |
| `src/gui/layout/center.py` | Remplacer la page vide créée par `_build_menu_page` par une vraie instance `BotOptimiseur` → créer `_build_optimiseur_page()` qui injecte `self` (CenterZone) au BotOptimiseur |
| `src/gui/widgets/config.py` | Ajouter `applique_profile(data)`, `_find_widget_by_key()`, `highlight_widget()` à l'infrastructure ConfigPage |
| `src/gui/widgets/bots/__init__.py` | Ajouter `BotOptimiseur` dans les exports |

---

## 8. Pages de config concernées

| Page | Clé params | Paramètres typiques |
|------|------------|-------------------|
| Général | `general` | Description, photo, centres d'intérêt |
| Réseau | `reseau` | Port, timeout, UPnP, limites DL/UL, reconnexion |
| Recherche | `recherche` | Max résultats, timeout, wishlist interval |
| Téléchargement | `telechargement` | Dossier DL, slots parallèles, rapport progrès |
| Partages | `partages` | Dossiers partagés, mode d'accès |
| Salons | `salons` | Pièces automatiques |
| Debug | `debug` | Logs, verbosité |

**Exclu** : La page "Utilisateurs" (amis/bloqués) n'est pas pertinente pour des profils d'optimisation — laisser la clé dans le mapping mais ne pas l'inclure dans les profils par défaut.

---

## 9. Architecture technique

### 9.1 Classe BotOptimiseur

```python
class BotOptimiseur(QFrame):
    """Tableau de bord d'optimisation centralisé."""

    page_changed = Signal(str)  # pour la navigation (compatible avec les autres bots)

    def __init__(self, center_zone: "CenterZone", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._center_zone = center_zone
        self._watcher = QFileSystemWatcher()  # auto-reload profils
        self._build_ui()

    # ── UI ──
    def _build_ui(self) -> None:
        """Construit la barre d'action + viewer + dashboard."""
        ...

    def _reload_profiles(self) -> None:
        """Scanne data/profils/*.json et reconstruit les boutons."""

    def _on_profile_clicked(self, filename: str) -> None:
        """Applique le profil sélectionné."""

    # ── Application du profil ──
    def _apply_profile(self, data: dict) -> None:
        """Parcourt les catégories et applique via applique_profile() sur chaque page."""

    def _log(self, message: str) -> None:
        """Ajoute une ligne dans le viewer."""

    def _update_dashboard(self, diffs: list) -> None:
        """Met à jour le dashboard avec les diffs reçus."""

    def _auto_return(self) -> None:
        """Timer 3s + overlay + retour vers la page Optimiseur."""
```

### 9.2 Contraintes non-fonctionnelles

- **Maintenabilité** : chaque page de config gère sa propre logique `applique_profile()`. L'Optimiseur ne connaît PAS les widgets internes.
- **Évolutivité** : ajouter une page = lui ajouter `applique_profile()`. L'Optimiseur l'appelle automatiquement.
- **Robustesse** : si une page n'a pas `applique_profile()` → log warning + skip. Si une catégorie n'a pas de page → log warning + skip.
- **Découplage** : `BotOptimiseur` reçoit `CenterZone` par injection — pas de dépendance circulaire.

### 9.3 Dépendances techniques

- `QFileSystemWatcher` (auto-reload profils) — déjà dans PySide6
- `QTimer.singleShot` (highlight, auto-retour)
- `QScrollArea.ensureWidgetVisible` (scroll vers widget modifié)
- `json`, `os`, `glob` (lecture des profils)
- `app_config` (via les pages de config — l'Optimiseur n'y touche pas directement)

### 9.4 États possibles

| État | Comportement |
|------|-------------|
| Aucun profil dans `data/profils/` | Barre vide + message "Aucun profil trouvé" |
| Fichier JSON invalide | Log dans viewer + fichier ignoré |
| Profil déjà actif | Re-cliquer ré-applique (reset) |
| Page de config introuvable | Log warning + skip |
| Widget introuvable dans la page | Log warning + skip |
| Modifications manuelles entre-temps | `applique_profile()` lit la valeur actuelle comme "avant" |

---

## 10. Ordre d'implémentation

1. **Renommage simple** : `"Utilisateurs"` → `"Optimiseur"` dans footer + center.py (boucle `_build_menu_page`)
2. **Créer les profils initiaux** : `data/profils/par_defaut.json`, `puissance_max.json`, `extreme.json`
3. **Infrastructure `config.py`** : ajouter `applique_profile()`, `_find_widget_by_key()`, `highlight_widget()` aux pages de config
4. **BotOptimiseur UI** : créer `bot_optimiseur.py` avec viewer + dashboard + barre d'action
5. **Logique d'application** : implémenter `_apply_profile()` avec lecture JSON + navigation + auto-retour
6. **Auto-reload** : `QFileSystemWatcher` sur `data/profils/`
7. **Tests + intégration** : valider que le renommage ne casse pas la config existante + que l'application fonctionne

---

*Spec v2 — corrections appliquées suite à la revue. Validé avant implémentation.*
