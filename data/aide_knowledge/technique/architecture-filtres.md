---
title: "Architecture des filtres de recherche — Modal, badge et combinaison de critères"
category: technique
keywords: ["filtre", "architecture", "modal", "badge", "recherche", "critere", "combinaison", "bitrate", "duree", "durée", "taille", "extension", "utilisateur", "slot", "audio", "toggle", "qdialog", "qtablewidget", "ui", "signal"]
---

# Architecture des filtres de recherche — Modal, badge et combinaison de critères

> **Niveau :** Avancé  
> **Temps de lecture :** 15 min  
> **Catégorie :** Technique — Architecture des filtres  
> **Fichiers référencés :** `src/gui/widgets/bots/bot_recherche.py`

---

## 1. Vue d'ensemble

Le système de filtres du bot Recherche repose sur **2 mécanismes** indépendants mais combinables :

```
┌──────────────────────────────────────────────────────────────┐
│                    BotRecherche                               │
│                                                              │
│  ┌─────────────────────┐    ┌───────────────────────────┐   │
│  │  Toggle Audio        │    │  Filtres Avancés (Modal)  │   │
│  │  (QPushButton)       │    │  (FiltresRechercheModal)  │   │
│  │                      │    │                           │   │
│  │  🔊 Audio seulement  │    │  • Bitrate min (0-1000)   │   │
│  │  🔊 Tous les fichiers│    │  • Durée min/max (s)     │   │
│  └──────────┬───────────┘    │  • Taille min/max (Mo)   │   │
│             │                │  • Utilisateur (texte)    │   │
│             │                │  • Slots libres (checkbox)│   │
│             │                └─────────────┬─────────────┘   │
│             │                              │                  │
│             ▼                              ▼                  │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              _apply_filters()                         │    │
│  │  Combine : audio_filter + filtres avancés + mode dispo│    │
│  └──────────────────────┬───────────────────────────────┘    │
│                         │                                     │
│                         ▼                                     │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              _row_matches_filters()                    │    │
│  │  Évalue chaque ligne du tableau contre les critères   │    │
│  └──────────────────────┬───────────────────────────────┘    │
│                         │                                     │
│                         ▼                                     │
│  ┌──────────────────────────────────────────────────────┐    │
│  │         setRowHidden(row, True/False)                  │    │
│  │  Affiche ou masque les lignes du QTableWidget        │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### Flux des données

```
État initial          →  Configuration         →  Application
(_filter_state dict)     (FiltresRechercheModal)   (_apply_filters)

   1. _filter_state        1. Copie → result_state   1. has_filters ?
      (vide au départ)     2. _load_state()          2. _row_matches_filters()
                           3. Utilisateur modifie     3. setRowHidden()
                           4. _save_state()
                           5. _filter_state ← result_state
```

---

## 2. Architecture du toggle audio

### Variables d'état

```python
# Initialisation (constructeur)
self._audio_filter_enabled = True   # Filtre audio activé par défaut
```

### Widget

```python
self._audio_filter_btn = QPushButton("🔊 Audio seulement")
self._audio_filter_btn.setCheckable(True)
self._audio_filter_btn.setChecked(True)
self._audio_filter_btn.toggled.connect(self._on_audio_filter_toggled)
```

### Gestionnaire d'événement

```python
def _on_audio_filter_toggled(self, checked: bool) -> None:
    self._audio_filter_enabled = checked
    self._audio_filter_btn.setText(
        "🔊 Audio seulement" if checked else "🔊 Tous les fichiers"
    )
    self._apply_filters()
```

### Filtrage à l'insertion

Le filtre audio agit **à deux niveaux** :

1. **À l'insertion** des résultats (dans la boucle d'ajout) :
   ```python
   if self._audio_filter_enabled and not _is_audio(file_data.extension):
       continue  # N'ajoute pas la ligne au tableau
   ```

2. **Au re-filtrage** (dans `_row_matches_filters`) via la condition `has_filters` :
   ```python
   has_filters = (
       self._filtres_compte > 0
       or not self._audio_filter_enabled   # Si désactivé, considéré comme un filtre
       or self._mode_dispo_enabled
   )
   ```

### Extensions reconnues

```python
EXTENSIONS_AUDIO = {".mp3", ".flac", ".ogg"}

def _is_audio(extension: str) -> bool:
    return extension.lower() in EXTENSIONS_AUDIO
```

> **Note :** Seuls 3 formats sont considérés comme "audio" par le filtre rapide. Les fichiers `.opus`, `.wav`, `.aac`, `.wma`, `.ape` ne sont pas inclus et nécessitent de désactiver le filtre ou d'utiliser les filtres avancés.

---

## 3. Architecture de la modal FiltresRechercheModal

### Hiérarchie

```
FiltresRechercheModal(QDialog)
├── self.result_state: dict          # Copie de travail du state
├── _setup_ui()                      # Construction des widgets
├── _load_state()                    # Widgets ← result_state
├── _save_state()                    # Widgets → result_state
└── _on_apply()                      # Applique + ferme
```

### Widgets de filtres

```
┌─────────────────────────────────────┐
│  🔍 Filtres avancés                 │
│                                     │
│  ┌─ Qualité ───────────────────────┐│
│  │ Bitrate min : [═══●══════] 192  ││
│  └─────────────────────────────────┘│
│  ┌─ Durée ─────────────────────────┐│
│  │ Min : [0]s  Max : [0]s         ││
│  │ (0 = Aucun)                     ││
│  └─────────────────────────────────┘│
│  ┌─ Taille ────────────────────────┐│
│  │ Min : [0] Mo  Max : [0] Mo     ││
│  │ (0 = Aucun)                     ││
│  └─────────────────────────────────┘│
│  ┌─ Utilisateur ───────────────────┐│
│  │ Nom : [________________]        ││
│  │ ☐ Slots libres uniquement      ││
│  └─────────────────────────────────┘│
│                                     │
│         [Cancel]  [✔ Appliquer]     │
└─────────────────────────────────────┘
```

### Gestion d'état

```python
def _load_state(self) -> None:
    """Widgets ← result_state"""
    fs = self.result_state
    self._bitrate_slider.setValue(fs.get("bitrate_min", 0))
    self._duration_min.setValue(fs.get("duration_min", 0))
    self._duration_max.setValue(fs.get("duration_max", 0))
    self._size_min.setValue(fs.get("size_min", 0))
    self._size_max.setValue(fs.get("size_max", 0))
    self._username_input.setText(fs.get("username", ""))
    self._slots_check.setChecked(fs.get("slots_libres_only", False))

def _save_state(self) -> None:
    """Widgets → result_state"""
    self.result_state = {
        "bitrate_min": self._bitrate_slider.value(),
        "duration_min": self._duration_min.value(),
        "duration_max": self._duration_max.value(),
        "size_min": self._size_min.value(),
        "size_max": self._size_max.value(),
        "username": self._username_input.text().strip(),
        "slots_libres_only": self._slots_check.isChecked(),
    }
```

### Synchronisation bitrate (curseur + spinbox)

```python
def _on_bitrate_slider(self, value: int) -> None:
    # Bloquer les signaux pour éviter la boucle infinie
    self._bitrate_spin.blockSignals(True)
    self._bitrate_spin.setValue(value)
    self._bitrate_spin.blockSignals(False)

def _on_bitrate_spin(self, value: int) -> None:
    self._bitrate_slider.blockSignals(True)
    self._bitrate_slider.setValue(value)
    self._bitrate_slider.blockSignals(False)
```

### Ouverture de la modal

```python
def _open_filtres_modal(self):
    modal = FiltresRechercheModal(self._filter_state, self)
    if modal.exec() == QDialog.DialogCode.Accepted:
        self._filter_state = modal.result_state
        self._update_filtres_badge()
        self._apply_filters()
```

---

## 4. Architecture du badge de compteur

### Calcul du nombre de filtres actifs

```python
def _update_filtres_badge(self) -> None:
    fs = self._filter_state
    count = 0
    if fs.get("bitrate_min", 0) > 0:      count += 1
    if fs.get("duration_min", 0) > 0:     count += 1
    if fs.get("duration_max", 0) > 0:     count += 1
    if fs.get("size_min", 0) > 0:         count += 1
    if fs.get("size_max", 0) > 0:         count += 1
    if fs.get("username", ""):            count += 1
    if fs.get("slots_libres_only", False): count += 1

    self._filtres_compte = count
    self._filtres_badge.setText(str(count) if count > 0 else "")
    self._filtres_badge.setVisible(count > 0)
```

### Condition d'affichage du badge dans la barre de statut

```python
has_filters = (
    self._filtres_compte > 0       # Filtres avancés actifs
    or not self._audio_filter_enabled  # Audio toggle désactivé
    or self._mode_dispo_enabled    # Mode disponibilité actif
)
```

> **Comportement contre-intuitif :** Quand `_audio_filter_enabled = False` (toggle sur "Tous les fichiers"), le badge s'allume parce que c'est un **état non défaut**. Le toggle audio par défaut est **activé** (filtré), donc le désactiver est considéré comme un écart par rapport à la normale.

---

## 5. Combinaison des critères (moteur de filtrage)

### `_apply_filters()` — Orchestrateur

```python
def _apply_filters(self) -> None:
    has_filters = (
        self._filtres_compte > 0
        or not self._audio_filter_enabled
        or self._mode_dispo_enabled
    )

    if not has_filters:
        # Aucun filtre : tout afficher
        for row in range(self._table.rowCount()):
            self._table.setRowHidden(row, False)
        return

    # Application des filtres ligne par ligne
    for row in range(self._table.rowCount()):
        item = self._table.item(row, COL_FICHIER)
        if item is None:
            continue
        row_data = item.data(Qt.UserRole + 1)
        matches = self._row_matches_filters(row_data)
        self._table.setRowHidden(row, not matches)
```

### `_row_matches_filters()` — Évaluateur ligne

```python
def _row_matches_filters(self, data: dict) -> bool:
    fs = self._filter_state

    # 1. Filtre bitrate
    if fs.get("bitrate_min", 0) > 0 and data.get("bitrate", 0) < fs["bitrate_min"]:
        return False

    # 2. Filtre durée min
    if fs.get("duration_min", 0) > 0 and data.get("duration", 0) < fs["duration_min"]:
        return False

    # 3. Filtre durée max
    if fs.get("duration_max", 0) > 0 and data.get("duration", 0) > fs["duration_max"]:
        return False

    # 4. Filtre taille min (Mo)
    taille_mo = data.get("filesize", 0) / 1_000_000
    if fs.get("size_min", 0) > 0 and taille_mo < fs["size_min"]:
        return False

    # 5. Filtre taille max (Mo)
    if fs.get("size_max", 0) > 0 and taille_mo > fs["size_max"]:
        return False

    # 6. Filtre utilisateur (insensible à la casse)
    username_filter = fs.get("username", "")
    if username_filter and username_filter.lower() not in data.get("username", "").lower():
        return False

    # 7. Filtre slots libres
    if fs.get("slots_libres_only", False) and not data.get("has_free_slots", False):
        return False

    return True  # La ligne passe tous les filtres
```

### Ordre d'évaluation

Les critères sont évalués **dans l'ordre**, avec **short-circuit evaluation** :

```
bitrate_min → duration_min → duration_max → size_min → size_max → username → slots
```

L'ordre est choisi du plus rapide au plus lent : les comparaisons numériques (bitrate, durée) sont moins coûteuses que les comparaisons de chaînes (username).

---

## 6. Diagramme de séquence complet

```
Utilisateur           BotRecherche              FiltresRechercheModal         QTableWidget
    │                      │                          │                         │
    │  [Nouvelle recherche]│                          │                         │
    │─────────────────────>│                          │                         │
    │                      │  setSortingEnabled(False) │                         │
    │                      │──────────────────────────│────────────────────────>│
    │                      │                          │                         │
    │                      │  Pour chaque résultat :  │                         │
    │                      │  if _audio_filter_enabled│                         │
    │                      │    and not _is_audio():  │                         │
    │                      │      → continue (ignoré) │                         │
    │                      │  else:                   │                         │
    │                      │    _add_result_row()     │                         │
    │                      │──────────────────────────│────────────────────────>│
    │                      │                          │                         │
    │                      │  setSortingEnabled(True) │                         │
    │                      │──────────────────────────│────────────────────────>│
    │                      │                          │                         │
    │  [Clic 🔍 Filtres]  │                          │                         │
    │─────────────────────>│                          │                         │
    │                      │  FiltresRechercheModal(  │                         │
    │                      │    _filter_state)        │                         │
    │                      │──────────────────────────>                         │
    │                      │                          │                         │
    │  ┌───────────────────┼──────────────────────────┼─── Utilisateur modifie  │
    │  │                   │                          │    les filtres           │
    │  │  [Clic Appliquer] │                          │                         │
    │  │──────────────────>│                          │                         │
    │  │                   │  modal.exec()            │                         │
    │  │                   │  → _save_state()         │                         │
    │  │                   │  → result_state accepté  │                         │
    │  │                   │<─────────────────────────│                         │
    │  │                   │                          │                         │
    │  │                   │  _update_filtres_badge() │                         │
    │  │                   │  _apply_filters()         │                         │
    │  │                   │──────────────────────────│────────────────────────>│
    │  │                   │  setRowHidden(row, bool)  │                         │
    │  │                   │──────────────────────────│────────────────────────>│
    │  │                   │                          │                         │
    │  │  [Toggle Audio]   │                          │                         │
    │  │─────────────────────>│                       │                         │
    │  │                   │  _audio_filter_enabled = │                         │
    │  │                   │    not _audio_filter_enabled│                       │
    │  │                   │  _apply_filters()         │                         │
    │  │                   │──────────────────────────│────────────────────────>│
    │  │                   │                          │                         │
```

---

## 7. Mise à jour asynchrone (nouveaux résultats)

Quand de nouveaux résultats arrivent pendant qu'un filtre est actif, le traitement suit ce schéma :

```python
# Lors de l'arrivée de nouveaux résultats
self._table.setSortingEnabled(False)   # Désactiver le tri temporairement

for result in nouveaux_resultats:
    for file_data in result.shared_items:
        # Filtre audio à l'insertion
        if self._audio_filter_enabled and not _is_audio(file_data.extension):
            continue
        self._add_result_row(file_data, ...)

self._table.setSortingEnabled(True)    # Réactiver le tri

# Re-appliquer les filtres avancés sur les nouvelles lignes
if self._filtres_compte > 0 or self._mode_dispo_enabled:
    self._apply_filters()
```

Les nouvelles lignes sont insérées **sans tri** pour la performance, puis les filtres avancés sont **ré-appliqués** après insertion.

---

## 8. Structure des données

### `_filter_state` (état partagé)

```python
self._filter_state = {
    "bitrate_min": 0,       # 0 = pas de filtre
    "duration_min": 0,      # 0 = pas de filtre
    "duration_max": 0,      # 0 = pas de filtre
    "size_min": 0,          # 0 = pas de filtre
    "size_max": 0,          # 0 = pas de filtre
    "username": "",         # "" = pas de filtre
    "slots_libres_only": False,  # False = pas de filtre
}
```

### `row_data` (par ligne de résultat)

Stocké dans chaque ligne via `item.setData(Qt.UserRole + 1, row_data)` :

```python
{
    "bitrate": 320,
    "duration": 272,        # secondes
    "filesize": 13107200,   # octets
    "username": "soulseeker",
    "has_free_slots": True,
    "extension": ".mp3",
}
```

---

## 9. Points d'extension et personnalisation

### Ajouter une extension au filtre audio

```python
# Dans les constantes
EXTENSIONS_AUDIO = {".mp3", ".flac", ".ogg", ".opus"}  # ← ajout Opus
```

### Ajouter un nouveau filtre

1. Ajouter le widget dans `FiltresRechercheModal._setup_ui()`
2. Ajouter la clé dans `_save_state()` et `_load_state()`
3. Ajouter le comptage dans `_update_filtres_badge()`
4. Ajouter la condition dans `_row_matches_filters()`

### Ajouter un critère à `has_filters`

```python
has_filters = (
    self._filtres_compte > 0
    or not self._audio_filter_enabled
    or self._mode_dispo_enabled
    # ou nouveau_critere_actif
)
```

---

## 10. Anti-patterns et cas limites

| Problème | Cause | Solution |
|----------|-------|----------|
| **Filtres ignorés après nouvel ajout** | `setSortingEnabled(True)` après insertion sans rappeler `_apply_filters()` | ✅ L'appel est fait à la fin de `_on_new_results` |
| **Badge non mis à jour** | Fermeture de la modal sans passer par `_on_apply` (clic Cancel) | ✅ `_on_cancel` ne modifie pas `_filter_state` |
| **Ligne masquée après changement de tri** | `setRowHidden` conservé après re-tri | ✅ Le tri Qt préserve l'état caché, mais `_apply_filters` re-vérifie tout |
| **Performance dégradée (1000+ lignes)** | `_row_matches_filters` appelé pour chaque ligne à chaque modification | ✅ Limite à 200 résultats (`MAX_RESULTS`) |
| **Double filtrage audio** | Filtre audio à l'insertion + dans `_row_matches_filters` | ✅ Cohérent : le filtre d'insertion évite d'ajouter les lignes, le filtre de `has_filters` gère le toggle |

---

## Voir aussi

- [Filtres de format dans le bot Recherche — Guide utilisateur](/guide_bots/13-filtres-format-recherche)
- [Colonnes et tri personnalisé — Guide utilisateur](/guide_bots/14-colonnes-tri-recherche)
- [Formats de fichiers et codecs supportés](/technique/formats-codecs-supportes)
- [Architecture événementielle — Événements et signaux](/technique/architecture-evenementielle)
