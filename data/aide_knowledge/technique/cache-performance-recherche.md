---
title: Cache et performance du bot Recherche
category: technique
keywords:
  - cache performance
  - optimisation performance
  - optimisation performance
  - performance recherche
  - cache filtre
  - cache filtre
  - filtre
  - filtre
  - batch insert
  - setSortingEnabled
  - setRowHidden
  - short-circuit
  - fifo
  - row_data
  - UserRole
  - Qt.UserRole
  - SearchHistory
  - search history
  - historique recherche
  - memoire cache
  - memoire cache
  - resultat cache
  - resultat cache
  - resultat cache
  - formatage
  - performance tableau
  - QTableWidget
  - COLORS
  - style cache
  - evenement asynchrone
  - evenement asynchrone
  - EventBus
  - blockSignals
  - timeout recherche
  - timer recherche
  - debounce
---

# Cache et performance du bot Recherche

Cet article détaille les mécanismes de cache et d'optimisation de performance implémentés dans le bot Recherche (`src/gui/widgets/bots/bot_recherche.py`, 1968 lignes). L'objectif est de maintenir une interface fluide malgré le traitement en temps réel des résultats provenant du réseau Soulseek.

---

## 1. Architecture du cache

### 1.1 Cache des données brutes (`row_data` / `Qt.UserRole + 1`)

**Localisation :** `_add_result_row` (ligne 1753), `_apply_filters` (ligne 1541), `_get_row_data` (ligne 1620)

Le mécanisme central de performance : chaque ligne du tableau stocke un dictionnaire complet de ses données brutes via `Qt.UserRole + 1` sur la colonne `COL_FICHIER`. Ceci permet de **re-filtrer sans re-parser** les données.

```python
# Stockage (dans _add_result_row)
row_data = {
    "extension": file_data.extension.lower(),
    "filename": filename,
    "filesize": file_data.filesize,
    "bitrate": bitrate,
    "duration": duration,
    "username": username,
    "has_free_slots": has_free_slots,
    "avg_speed": avg_speed,
}
fichier_item.setData(Qt.UserRole + 1, row_data)

# Récupération (dans _apply_filters / _get_row_data)
data = item.data(Qt.UserRole + 1)
```

**Pourquoi `Qt.UserRole + 1` ?** Le rôle `Qt.UserRole` est utilisé par `TableItem.__lt__` pour le tri personnalisé. Le rôle suivant (`UserRole + 1`) stocke les données brutes complètes sans conflit.

**Avantage :** Évite de :
- Re-parser le nom de fichier à chaque filtrage
- Re-consulter l'objet `file_data` original (qui n'est plus disponible)
- Re-formater les données (taille, bitrate, durée) — le texte affiché est séparé des valeurs de tri

### 1.2 Cache de l'historique de recherche (`SearchHistory`)

**Fichier :** `src/services/search_history.py`
**Stockage :** `data/bot_recherche_history.json`
**Cache mémoire :** `self._entries` (`list[dict]`)
**Limite :** `MAX_HISTORY = 20`

Le système utilise un **cache à deux niveaux** :

```
┌──────────────────────┐
│   Cache mémoire      │  ← self._entries (list[dict])
│   (lecture/écriture) │     Accès instantané, pas d'I/O disque
└────────┬─────────────┘
         │ synchronisation
         ▼
┌──────────────────────┐
│   Fichier JSON       │  ← data/bot_recherche_history.json
│   (persistance)      │     Sauvegardé après chaque modification
└──────────────────────┘
```

**Optimisation :** Déduplication intégrée dans `add()` :

```python
def add(self, query, type_, username):
    # Si la même recherche existe déjà, on la remonte en tête
    for i, entry in enumerate(self._entries):
        if (entry["query"] == query and 
            entry["type"] == type_ and 
            entry.get("username") == username):
            self._entries.pop(i)
            break
    # Nouvelle entrée en tête de liste
    self._entries.insert(0, new_entry)
    # Troncature à MAX_HISTORY
    self._entries = self._entries[:MAX_HISTORY]
    self.save()
```

### 1.3 Cache de l'état des filtres (`_filter_state`)

**Localisation :** `BotRecherche.__init__` (ligne 707), `FiltresRechercheModal` (ligne 163), `_open_filtres_modal` (ligne 1472)

```python
# Valeurs par défaut dans BotRecherche.__init__
self._filter_state = {
    "bitrate_min": 0,
    "duration_min": 0,
    "duration_max": 0,
    "size_min": 0,
    "size_max": 0,
    "username": "",
    "slots_libres_only": False,
}
```

**Cycle de vie du cache :**

1. `BotRecherche` initialise `_filter_state` avec les valeurs par défaut
2. L'utilisateur clique sur **🔍 Filtres** → `FiltresRechercheModal` reçoit `_filter_state` dans son constructeur → appelle `_load_state(filter_state)` pour pré-remplir les widgets
3. L'utilisateur modifie les valeurs → `_save_state()` met à jour `self.result_state`
4. `modal.exec()` retourne `QDialog.Accepted` → `BotRecherche` met à jour `_filter_state = dict(modal.result_state)`
5. `_apply_filters()` est appelé avec les nouveaux critères

**Avantage :** Les filtres survivent entre les ouvertures/fermetures de la modal — pas besoin de les re-configurer à chaque recherche.

### 1.4 Constantes comme cache de configuration

| Constante | Valeur | Rôle |
|---|---|---|
| `MAX_RESULTS` | `200` | Limite mémoire du tableau |
| `EXTENSIONS_AUDIO` | `{".mp3", ".flac", ".ogg"}` | Ensemble figé (`set`) pour test d'appartenance O(1) |
| `COLUMNS` | `["Extension", "Fichier", "Taille", …]` | 9 labels de colonnes, 1 seule définition |
| `COL_EXTENSION` à `COL_DL` | `0` à `8` | Indices de colonnes nommés |
| `_ATTR_BITRATE`, `_ATTR_DURATION` | Entiers | Clés d'attributs Soulseek en constantes |
| `COLORS` | `dict` avec 12 couleurs | Palette unique, pas de valeurs magiques dans les stylesheets |

`EXTENSIONS_AUDIO` utilise un `set` Python (implémentation hash table) pour un test d'appartenance en **O(1)** :

```python
EXTENSIONS_AUDIO = {".mp3", ".flac", ".ogg"}

def _is_audio(extension: str) -> bool:
    return extension.lower() in EXTENSIONS_AUDIO  # O(1)
```

Le dictionnaire `COLORS` centralise les 12 couleurs du thème :

```python
COLORS = {
    "BG_PRIMARY": "#1a1a2e",
    "BG_SECONDARY": "#16213e",
    "BG_SURFACE": "#0f0f23",
    # ...
}
```

---

## 2. Optimisations de l'affichage tableau

### 2.1 Désactivation du tri pendant l'insertion batch

**Localisation :** `_on_search_result` (ligne 1361), `_add_result_row` (ligne 1753), `_clear_results` (ligne 1875)

```python
def _on_search_result(self, evt):
    # ... validation ...
    self._table.setSortingEnabled(False)   # ← DÉSACTIVÉ
    for item in result.shared_items:
        if self._audio_filter_enabled and not _is_audio(...):
            continue
        self._add_result_row(item, ...)
    self._table.setSortingEnabled(True)    # ← RÉACTIVÉ
```

**Pourquoi ?** Sans cette désactivation, `QTableWidget` trie le tableau après chaque `insertRow()`, soit un tri en **O(n log n)** × 200 insertions = ~1 400 opérations de comparaison. Avec la désactivation : **1 seul tri** à la fin du batch.

**Triple usage :**
| Contexte | Désactivation | Réactivation |
|---|---|---|
| Insertion batch (`_on_search_result`) | Ligne 1378 | Ligne 1393 |
| Nettoyage (`_clear_results`) | Ligne 1876 | Ligne 1878 |
| Réception par lots multiples | État persistant | État restauré |

### 2.2 `setRowHidden()` vs `removeRow()`

**Localisation :** `_apply_filters` (ligne 1541)

Les filtres utilisent `setRowHidden(row, True/False)` pour masquer/afficher les lignes, ce qui est **beaucoup plus efficace** que de supprimer et recréer des lignes :

| Opération | `setRowHidden()` | `removeRow()` |
|---|---|---|
| Modification | Un flag Qt | Réallocation complète |
| Complexité | O(1) par ligne | O(n) par ligne |
| Index de ligne | Préservé | Décalé |
| Réaffichage | Minimal | Complet |
| Mémoire | Inchangée | Libérée puis réallouée |

**Exception :** Le mécanisme FIFO (quand `_add_result_row` dépasse `MAX_RESULTS`) utilise `removeRow(0)` — c'est la seule opération destructive, limitée à 1 suppression par nouvel arrivant.

### 2.3 Cache du compteur de colonnes

**Localisation :** `_apply_filters`

```python
# Dans _row_matches_filters : aucune référence à columnCount()
# Le nombre de colonnes est déterminé une fois à la création du tableau
```

`Qt.UserRole + 1` ne stocke que les données sur `COL_FICHIER` (colonne 1). Les autres colonnes ne sont pas lues pendant le filtrage, ce qui évite des appels redondants à `item()`.

### 2.4 Alternance de couleurs et absence de grille

```python
self._table.setAlternatingRowColors(True)
self._table.setShowGrid(False)
```

- **`setAlternatingRowColors(True)`** : Qt utilise un renderer optimisé pour l'alternance, plus efficace qu'un stylesheet personnalisé
- **`setShowGrid(False)`** : Évite de dessiner les lignes de grille (coût proportionnel au nombre de cellules : 9 colonnes × 200 lignes = 1 800 traits par frame)

---

## 3. Optimisations du moteur de filtrage

### 3.1 Short-circuit dans `_apply_filters`

**Localisation :** Lignes 1541-1595

L'optimisation principale est le **short-circuit global** : si `has_filters` est `False`, la boucle entière est évitée.

```python
def _apply_filters(self):
    self._update_filtres_badge()
    
    has_filters = (self._filtres_compte > 0 or 
                   not self._audio_filter_enabled or 
                   self._mode_dispo_enabled)
    
    if not has_filters:
        # Aucun filtre : tout afficher en 1 passage rapide
        for row in range(self._table.rowCount()):
            self._table.setRowHidden(row, False)
        return  # ← Sortie immédiate, 0 filtrage
```

**Performance :** Si aucun filtre actif → **~200 µs** (simple passage `setRowHidden(False)`).

### 3.2 Short-circuit dans `_row_matches_filters`

**Localisation :** Lignes 1507-1539

L'évaluation des 7 critères est ordonnée du **plus rapide au plus lent** et s'arrête au premier échec :

```python
def _row_matches_filters(self, data):
    fs = self._filter_state
    
    # 1. Bitrate min (comparaison d'entier, très rapide)
    if fs["bitrate_min"] > 0 and data["bitrate"] < fs["bitrate_min"]:
        return False
    
    # 2. Durée min (entier)
    if fs["duration_min"] > 0 and data["duration"] < fs["duration_min"]:
        return False
    
    # 3. Durée max (entier)
    if fs["duration_max"] > 0 and data["duration"] > fs["duration_max"]:
        return False
    
    # 4. Taille min (entier / division)
    if fs["size_min"] > 0 and (data["filesize"] / 1_000_000) < fs["size_min"]:
        return False
    
    # 5. Taille max (entier / division)
    if fs["size_max"] > 0 and (data["filesize"] / 1_000_000) > fs["size_max"]:
        return False
    
    # 6. Utilisateur (contient, insensible à la casse)
    if fs["username"] and fs["username"].lower() not in data["username"].lower():
        return False
    
    # 7. Slots libres (dernier car booléen + appel .get())
    if fs["slots_libres_only"] and not data["has_free_slots"]:
        return False
    
    return True
```

**Ordre d'évaluation (du plus rapide au plus lent) :**

| Rang | Critère | Opération | Coût relatif |
|---|---|---|---|
| 1 | Bitrate min | `int < int` | ★☆☆ |
| 2 | Durée min | `int < int` | ★☆☆ |
| 3 | Durée max | `int > int` | ★☆☆ |
| 4 | Taille min | `int / 1_000_000 < int` | ★☆☆ |
| 5 | Taille max | `int / 1_000_000 > int` | ★☆☆ |
| 6 | Utilisateur | `str.lower() in str.lower()` | ★★☆ |
| 7 | Slots | `bool and not bool` | ★☆☆ |

**Complexité :** Dans le pire cas (200 lignes, 7 critères, toutes les lignes passent) : **200 × 7 = 1 400 opérations** soit **< 1 ms**.

### 3.3 Niveaux de filtrage séquentiel (AND élargi)

**Localisation :** `_apply_filters` (lignes 1562-1585)

Les trois sources de filtrage sont appliquées en séquence, avec short-circuit entre elles :

```
_apply_filters()
    │
    ├─ has_filters ? → Non  → setRowHidden(False) sur tout → FIN
    │
    └─ Oui → Boucle sur chaque ligne :
              │
              ├─ item existe ? → Non → setRowHidden(True)
              │
              ├─ data existe ? → Non → setRowHidden(True)
              │
              ├─ 🔊 Audio ?  → Non → matches = False
              │
              ├─ 🟢 Dispo ?  → Non → matches = False
              │
              └─ 🔍 Avancés ? → Non → matches = False
                               
              → setRowHidden(row, not matches)
              → visible_count += 1 si matches
```

---

## 4. Gestion mémoire et cycle de vie

### 4.1 FIFO avec `MAX_RESULTS = 200`

**Localisation :** `_add_result_row` (ligne 1765)

```python
MAX_RESULTS = 200  # ligne 54

def _add_result_row(self, ...):
    row = self._table.rowCount()
    
    if row >= MAX_RESULTS:
        self._table.removeRow(0)  # Supprime la plus ancienne
        row = self._table.rowCount()  # Nouvel index = 199
    
    self._table.insertRow(row)
    # ...
```

**Empreinte mémoire estimée :**

| Composant | Taille unitaire | × 200 lignes | Total |
|---|---|---|---|
| `TableItem` (9 colonnes) | ~200 o | 1 800 items | ~360 Ko |
| `row_data` dict | ~300 o | 200 dicts | ~60 Ko |
| `QPushButton` (DL) | ~500 o | 200 boutons | ~100 Ko |
| Lignes Qt internes | ~100 o | 200 | ~20 Ko |
| **Total** | | | **~540 Ko** |

Sans la limite de 200, avec 5 000 résultats : **~13,5 Mo** juste pour le tableau.

### 4.2 Nettoyage explicite de la mémoire Qt

**Localisation :** `_clear_results` (ligne 1875)

```python
def _clear_results(self):
    self._table.setSortingEnabled(False)
    self._table.setRowCount(0)  # ← Libère TOUTES les lignes en 1 appel
    self._table.setSortingEnabled(True)
```

`setRowCount(0)` supprime toutes les lignes et leurs enfants (`TableItem`, `QPushButton`) en une seule opération Qt optimisée.

**Localisation :** `_rebuild_suggestions` (ligne 1882)

```python
def _rebuild_suggestions(self):
    # Nettoyage des anciens widgets
    for widget in self._suggestions_widgets:
        self._suggestions_layout.removeWidget(widget)
        widget.deleteLater()  # ← Planifie la destruction Qt
    self._suggestions_widgets.clear()
```

`deleteLater()` planifie la destruction lors du prochain cycle d'événements Qt, évitant les `use-after-free`.

### 4.3 Menu contextuel sans cache

**Localisation :** `_on_context_menu` (ligne 1640)

```python
def _on_context_menu(self, pos):
    # ...
    menu = QMenu(self)       # ← Créé à la volée
    # ... ajout des actions ...
    menu.exec(...)           # ← Affiché
    # ← Détruit automatiquement à la fermeture (pas de référence persistante)
```

**Pourquoi pas de cache ?** Un menu contextuel avec des données dynamiques (nom fichier, nom utilisateur) ne peut pas être pré-construit. Le créer à la volée évite de garder des menus inutilisés en mémoire entre les clics droits.

---

## 5. Optimisations des signaux et événements

### 5.1 `blockSignals` pour la synchronisation bitrate

**Localisation :** `_on_bitrate_slider` (ligne 389), `_on_bitrate_spin` (ligne 394)

```python
def _on_bitrate_slider(self, value: int):
    self._bitrate_spin.blockSignals(True)   # ← Évite la récursion
    self._bitrate_spin.setValue(value)
    self._bitrate_spin.blockSignals(False)

def _on_bitrate_spin(self, value: int):
    self._bitrate_slider.blockSignals(True)  # ← Évite la récursion
    self._bitrate_slider.setValue(value)
    self._bitrate_slider.blockSignals(False)
```

**Sans `blockSignals`** : Déplacer le slider → `valueChanged` → spin se met à jour → `valueChanged` du spin → slider se met à jour → boucle infinie.

**Avec `blockSignals`** : 1 seul événement propagé, pas de boucle.

### 5.2 Timer de timeout (30s)

**Localisation :** `_on_search` (ligne ~1319)

```python
self._search_timer = QTimer(self)
self._search_timer.setSingleShot(True)  # ← Un seul déclenchement
self._search_timer.timeout.connect(self._on_search_timeout)
self._search_timer.start(30000)  # ← 30 secondes
```

**Rôle :** Si la recherche réseau ne répond pas dans les 30 secondes, le timer déclenche `_on_search_timeout` qui :

1. Passe `_searching = False`
2. Réaffiche le bouton "Rechercher"
3. Affiche : `⏱️ La recherche continue en arrière-plan…`

**Pourquoi `setSingleShot(True)` ?** Une recherche Soulseek peut retourner des résultats par lots pendant plusieurs minutes. Le timer n'est pas un timeout d'arrêt — c'est un indicateur que les résultats actifs initiaux sont arrivés. La recherche continue en arrière-plan via l'EventBus.

### 5.3 EventBus pour la communication asynchrone

**Localisation :** Tous les événements système sont émis via `EventBus().emit_event()`

```python
# Émission d'événements
EventBus().emit_event(
    severity="ERROR",
    category="recherche",
    title="Erreur de recherche",
    message=f"Erreur lors de la recherche : {msg}",
    source="BotRecherche",
)
```

**Avantage performance :** L'EventBus est asynchrone — les écouteurs sont notifiés sans bloquer le bot Recherche.

### 5.4 `NoEditTriggers` et `SingleSelection`

```python
self._table.setEditTriggers(QTableWidget.NoEditTriggers)
self._table.setSelectionMode(QTableWidget.SingleSelection)
```

- **`NoEditTriggers`** : Évite de créer des éditeurs de cellule (widgets lourds) à chaque clic
- **`SingleSelection`** : Évite de gérer des sélections multiples complexes

---

## 6. Détection précoce et validation

### 6.1 Validation de la requête avant recherche

**Localisation :** `_on_search` (ligne 1252)

```python
def _on_search(self):
    query = self._search_input.text().strip()
    if len(query) < 2:
        self._status_label.setText("📝 Entrez au moins 2 caractères")
        return  # ← Évite un appel réseau inutile
```

Une requête de moins de 2 caractères est rejetée avant tout appel réseau, économisant une requête Soulseek.

### 6.2 Filtrage audio en amont

**Localisation :** `_on_search_result` (ligne 1382)

```python
for item in result.shared_items:
    if self._audio_filter_enabled and not _is_audio(...):
        continue  # ← Évite _add_result_row pour les non-audio
    self._add_result_row(...)
```

Le filtre audio est appliqué **avant** `_add_result_row` — les fichiers non-audio ne sont même pas ajoutés au tableau. Cela réduit :
- Le nombre d'appels à `insertRow()`
- La mémoire allouée pour les `TableItem` inutiles
- Le nombre de lignes à filtrer dans `_apply_filters()`

---

## 7. Diagramme de flux de performance

```
Utilisateur tape "radiohead" → _on_search()
    │
    ├─ len(query) < 2 ? → Rejet immédiat
    │
    └─ Validation OK → _clear_results()
                        │
                        ├─ setSortingEnabled(False)
                        ├─ setRowCount(0) → Libération mémoire
                        └─ setSortingEnabled(True)
                        │
                        ├─ _search_history.add() → Mémoire + JSON
                        ├─ _search_timer.start(30000)
                        └─ _connexion_manager.search() → Réseau
                           │
                           ▼ (asynchrone)
                        _on_search_result(evt)
                           │
                           ├─ setSortingEnabled(False)
                           ├─ Pour chaque shared_item :
                           │   ├─ Filtre audio ? → skip si non-audio
                           │   └─ _add_result_row()
                           │       ├─ rowCount >= 200 ? → removeRow(0) (FIFO)
                           │       ├─ insertRow()
                           │       ├─ setData(UserRole+1, row_data)  ← CACHE
                           │       └─ setItem() x8 + setCellWidget() x1
                           ├─ _result_count += added
                           ├─ >= MAX_RESULTS ? → Avertissement ⚠️
                           └─ setSortingEnabled(True)
                           │
                           ▼ (interaction utilisateur)
                        Filtre activé → _apply_filters()
                           │
                           ├─ has_filters ? → Non → setRowHidden(False) x200 → FIN
                           │
                           └─ Oui → Pour chaque ligne :
                                     ├─ item None ? → setRowHidden(True)
                                     ├─ data None ? → setRowHidden(True)
                                     ├─ Audio ? → Non → setRowHidden(True)
                                     ├─ Dispo ? → Non → setRowHidden(True)
                                     └─ _row_matches_filters()
                                         ├─ bitrate → False ?
                                         ├─ durée   → False ?
                                         ├─ taille  → False ?
                                         ├─ user    → False ?
                                         └─ slots   → False ?
```

---

## 8. Tableau récapitulatif des optimisations

| Optimisation | Section | Gain |
|---|---|---|
| Cache `row_data` via `UserRole+1` | 1.1 | Pas de re-parsing au filtrage |
| `SearchHistory` double cache | 1.2 | Pas d'I/O disque à chaque accès |
| `setSortingEnabled(False)` batch | 2.1 | Évite n×O(n log n) tris |
| `setRowHidden()` vs `removeRow()` | 2.2 | O(1) vs O(n) par ligne filtrée |
| Short-circuit `has_filters` | 3.1 | ~200 µs si aucun filtre actif |
| Short-circuit `_row_matches_filters` | 3.2 | S'arrête au premier échec |
| `blockSignals` bitrate | 5.1 | Évite boucle infinie de signaux |
| Timer singleShot 30s | 5.2 | Pas de polling, timeout propre |
| Filtrage audio en amont | 6.2 | Évite d'ajouter des lignes inutiles |
| `EXTENSIONS_AUDIO` set O(1) | 1.4 | Test d'appartenance constant |
| FIFO removeRow(0) | 4.1 | Mémoire bornée à ~540 Ko |
| `setRowCount(0)` | 4.2 | Libération mémoire en 1 appel Qt |
| `deleteLater()` suggestions | 4.2 | Pas de use-after-free |
| Validation requête < 2 car. | 6.1 | Évite appel réseau inutile |
| `NoEditTriggers` | 5.4 | Pas d'éditeurs de cellule lourds |

---

## 9. Points d'extension et limites

### 9.1 Ajouter un nouveau type de cache

Pour ajouter un cache pour, par exemple, les icônes par extension de fichier :

```python
# Dans BotRecherche.__init__
self._ext_icon_cache: dict[str, QIcon] = {}

# Dans _add_result_row
if ext not in self._ext_icon_cache:
    self._ext_icon_cache[ext] = self._create_icon_for_ext(ext)
icon = self._ext_icon_cache[ext]
```

### 9.2 Améliorer le cache actuel

- **Limite actuelle :** `SearchHistory` sauvegarde sur disque après chaque ajout/suppression → pour 20 entrées, acceptable. Si `MAX_HISTORY` passe à 200+, envisager un batch save.
- **Limite actuelle :** `row_data` n'est jamais nettoyé du `UserRole+1` quand la ligne est supprimée par FIFO — c'est normal, `removeRow(0)` libère la mémoire Qt automatiquement.
- **Amélioration possible :** Ajouter un cache LRU pour les suggestions d'auto-complétion (pas encore implémenté).

### 9.3 Anti-patterns à éviter

| Anti-pattern | Problème | Alternative |
|---|---|---|
| `removeRow()` puis `insertRow()` pour filtrer | Réallocation O(n) | `setRowHidden()` (déjà utilisé) |
| Appeler `columnCount()` dans la boucle de filtrage | Appel virtuel Qt coûteux | Mettre en cache (`COLUMNS` length) |
| Stocker des données dans `QTableWidgetItem.setText()` et re-parser | Parsing coûteux | Stocker via `setData(UserRole+1, dict)` (déjà fait) |
| Créer un nouveau stylesheet à chaque frame | Parsing CSS coûteux | Utiliser `COLORS` constants (déjà fait) |

---

**Voir aussi :**
- [/technique/architecture-filtres](/technique/architecture-filtres) — Architecture des filtres (toggle audio, modal, badge, moteur de filtrage)
- [/guide_bots/14-colonnes-tri-recherche](/guide_bots/14-colonnes-tri-recherche) — Guide d'utilisation des colonnes et du tri
- [/guide_bots/13-filtres-format-recherche](/guide_bots/13-filtres-format-recherche) — Guide d'utilisation des filtres de format
- [/faq/performances-limitations-filtres](/faq/performances-limitations-filtres) — FAQ sur les performances et limitations des filtres
