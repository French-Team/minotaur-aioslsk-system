---
title: "Architecture des widgets de configuration (config.py)"
category: technique
tags:
  - architecture
  - widgets
  - configuration
  - design-pattern
keywords:
  - architecture widgets configuration
  - config py architecture design
  - ConfigPage QScrollArea titre
  - ConfigSection titre separateur layout
  - ConfigSection titre séparateur layout
  - ConfigToggle interrupteur checkbox
  - ConfigToggle QCheckBox app config
  - ConfigEntry champ texte QLineEdit
  - ConfigEntry QLineEdit editingFinished
  - ConfigCombo menu deroulant QComboBox
  - ConfigCombo menu déroulant QComboBox
  - ConfigCombo itemData valeur stockee
  - ConfigCombo itemData valeur stockée
  - ConfigSpin champ numerique QSpinBox
  - ConfigSpin champ numérique QSpinBox
  - ConfigFilePicker selecteur fichier
  - ConfigFilePicker sélecteur fichier
  - ConfigDirectoryPicker selecteur dossier
  - ConfigDirectoryPicker sélecteur dossier
  - ConfigResetBtn reinitialisation confirmation
  - ConfigResetBtn réinitialisation confirmation
  - QMessageBox reset confirmation
  - app config reset notification
  - lire valeur widget polymorphisme
  - lire valeur widget polymorphisme isinstance
  - ecrire valeur widget polymorphisme type dispatch
  - ecrire valeur widget ConfigEntry persistence manuelle
  - ecrire valeur widget ConfigEntry persistance manuelle
  - highlight widget surbrillance temporaire
  - highlight widget ensureWidgetVisible
  - highlight widget styleSheet border QTimer
  - ConfigPage add widget layout
  - ConfigPage add placeholder texte
  - ConfigPage collect config widgets recursif
  - ConfigPage _collect_config_widgets recursif enfants
  - ConfigPage _find_widget_by_key dictionnaire
  - ConfigPage applique profile bulk update
  - ConfigPage retourne changements rapport
  - pattern config key app config persistance
  - pattern config key app_config persistance
  - classe widget label description layout horizontal
  - classe widget label description icone
  - classe widget icône info tooltip
  - widget styleSheet configSection violet titre separateur
  - widget styleSheet configEntry border focus
  - config py 918 lignes 9 classes 3 fonctions
  - design pattern abstraction widget config
  - polymorphisme isinstance lecture ecriture
  - polymorphisme isinstance lecture écriture
  - architecture couche presentation config
  - architecture couche persistance app config
---

# Architecture des widgets de configuration (config.py)

## Vue d'ensemble

Le module `src/gui/widgets/config.py` (918 lignes) implémente un **framework de widgets de configuration** réutilisables. Il fournit 9 classes et 3 fonctions utilitaires qui permettent de construire des pages de paramètres avec persistance automatique via `app_config` et gestion de profils.

```
┌────────────────────────────────────────────────────────────┐
│                      Architecture                           │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    ConfigPage                         │   │
│  │  ┌─ Titre ──────────────────────────────────────┐    │   │
│  │  │              "Réseau"                        │    │   │
│  │  └──────────────────────────────────────────────┘    │   │
│  │  ┌─ QScrollArea ───────────────────────────────┐    │   │
│  │  │ ┌─ ConfigSection "Connexion" ────────────┐  │    │   │
│  │  │ │ ConfigToggle  UPnP                     │  │    │   │
│  │  │ │ ConfigSpin    Port d'écoute            │  │    │   │
│  │  │ │ ConfigCombo   Mode connexion           │  │    │   │
│  │  │ └────────────────────────────────────────┘  │    │   │
│  │  │ ┌─ ConfigSection "Limites" ──────────────┐  │    │   │
│  │  │ │ ConfigSpin    Limite upload            │  │    │   │
│  │  │ └────────────────────────────────────────┘  │    │   │
│  │  │ ConfigResetBtn  ↺ Réinitialiser             │    │   │
│  │  └─────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│       Chaque widget → config_key → app_config.get/set       │
└─────────────────────────────────────────────────────────────┘
```

### Principe de fonctionnement

Chaque widget de configuration :
1. Lit sa valeur initiale depuis `app_config` via sa `config_key` (dans `__init__`)
2. Persiste automatiquement les changements vers `app_config` (dans les slots `_on_changed` / `_on_toggled`)
3. Émet un signal vers l'extérieur pour notifier les changements

```
app_config.get("reseau.port_ecoute")           app_config.set("reseau.port_ecoute", 60001)
       │                                              ▲
       │   ┌──────────────────────────────────┐        │
       │   │    ConfigSpin (Port d'écoute)    │        │
       └───┤  __init__: self._spinner.setValue(│────────┘
           │  _on_changed: app_config.set()   │
           │  signal: changed(int)            │
           └──────────────────────────────────┘
                          │
                          ▼
                   Autres widgets abonnés
```

---

## 1. ConfigSection

Conteneur regroupant des options connexes avec un titre et un séparateur.

| Propriété | Valeur |
|-----------|--------|
| **Héritage** | `QFrame` |
| **Ligne** | 36 |
| **Layout** | `QVBoxLayout` (marges 0/0/0/12, spacing 6) |

### Structure interne

```
┌─ ConfigSection ─────────────────────────────────────┐
│  Titre "Connexion"          (QLabel, violet #6c5ce7) │
│  ───────────────────────    (QFrame.HLine séparateur) │
│                                                       │
│  [ConfigToggle]  UPnP                                 │
│  [ConfigSpin]    Port d'écoute                        │
│  [ConfigCombo]   Mode de connexion                    │
└───────────────────────────────────────────────────────┘
```

### Code

```python
class ConfigSection(QFrame):
    def __init__(self, titre: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("configSection")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(6)

        title_label = QLabel(titre)
        title_label.setObjectName("configSectionTitle")
        title_label.setStyleSheet("color: #6c5ce7; font-size: 13px; font-weight: 700;")
        layout.addWidget(title_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #2e2e3a;")
        layout.addWidget(sep)

        self._options_layout = QVBoxLayout()
        self._options_layout.setContentsMargins(0, 4, 0, 0)
        self._options_layout.setSpacing(4)
        layout.addLayout(self._options_layout)

    def add(self, widget: QWidget) -> None:
        """Ajoute une option à la section."""
        self._options_layout.addWidget(widget)
```

### Points clés

- Le titre est stylisé en violet (`#6c5ce7`) pour démarquer visuellement les sections
- Le séparateur utilise `QFrame.HLine` avec une couleur discrète
- Les widgets enfants sont ajoutés dans `_options_layout` (layout dédié, pas le layout principal)
- Les marges hautes du layout principal (12px en bas) créent un espacement entre sections

---

## 2. ConfigToggle

Interrupteur marche/arrêt avec persistance automatique.

| Propriété | Valeur |
|-----------|--------|
| **Héritage** | `QFrame` |
| **Ligne** | 82 |
| **Widget interne** | `QCheckBox` |
| **Signal** | `toggled(bool)` |
| **Persistance** | `app_config.set(key, bool)` sur `toggled` |

### Code

```python
class ConfigToggle(QFrame):
    toggled = Signal(bool)

    def __init__(self, label: str, config_key: str,
                 description: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self._config_key = config_key
        # ... layout setup ...
        self._checkbox = QCheckBox(label)
        # Valeur initiale depuis app_config
        valeur_initiale = app_config.get(config_key, False)
        self._checkbox.setChecked(valeur_initiale)
        self._checkbox.toggled.connect(self._on_toggled)
        # ... description optionnelle ...

    def _on_toggled(self, checked: bool) -> None:
        app_config.set(self._config_key, checked)
        self.toggled.emit(checked)

    @property
    def is_checked(self) -> bool:
        return self._checkbox.isChecked()

    def set_checked(self, value: bool) -> None:
        self._checkbox.setChecked(value)

    @property
    def config_key(self) -> str:
        return self._config_key
```

### Cycle de vie

```
[Initialisation]
    app_config.get(key, False) ──► QCheckBox.setChecked()
                                        │
[Utilisateur clique]
    QCheckBox.toggled(bool) ──► _on_toggled(checked)
                                      │
                                      ├──► app_config.set(key, checked)
                                      └──► self.toggled.emit(checked)
```

---

## 3. ConfigEntry

Champ de texte libre avec persistance au focus perdu.

| Propriété | Valeur |
|-----------|--------|
| **Héritage** | `QFrame` |
| **Ligne** | 213 |
| **Widget interne** | `QLineEdit` |
| **Signaux** | `changed(str)` |
| **Persistance** | `app_config.set(key, str)` sur `editingFinished` |

### Particularité : double connexion

```python
class ConfigEntry(QFrame):
    changed = Signal(str)

    def __init__(self, label: str, config_key: str, ...):
        # ...
        self._entry = QLineEdit()
        self._entry.setText(app_config.get(config_key, ""))
        self._entry.editingFinished.connect(self._on_changed)
        self._entry.textChanged.connect(self._on_text_changed)
```

| Signal | Slot | Usage |
|--------|------|-------|
| `editingFinished` | `_on_changed` | **Persistance** : `app_config.set()` + émission `changed` |
| `textChanged` | `_on_text_changed` | **Temps réel** : émission `changed` uniquement (sans persistance) |

> 💡 **Pourquoi deux signaux ?** `editingFinished` évite de persister à chaque frappe clavier. Le signal `changed` est émis en temps réel pour mettre à jour l'interface (ex : prévisualisation), tandis que la persistance disque n'a lieu qu'au focus perdu.

### Code de persistance manuelle

Dans `_ecrire_valeur_widget`, `ConfigEntry` a un traitement spécial :

```python
elif isinstance(widget, ConfigEntry):
    widget.set_text(str(valeur))
    # setText n'émet pas editingFinished → persistance manuelle
    app_config.set(widget.config_key, str(valeur))
```

---

## 4. ConfigCombo

Menu déroulant avec stockage de valeurs via `itemData`.

| Propriété | Valeur |
|-----------|--------|
| **Héritage** | `QFrame` |
| **Ligne** | 300 |
| **Widget interne** | `QComboBox` |
| **Signal** | `changed(str)` |
| **Persistance** | `app_config.set(key, str)` sur `currentIndexChanged` |

### Structure des options

Les options sont passées sous forme de liste de tuples `(label, valeur_stockee)` :

```python
options = [
    ("Tout le monde",     "everyone"),
    ("Amis uniquement",   "friends"),
    ("Utilisateurs",      "users"),
]
combo = ConfigCombo("Mode", "partages.mode", options=options)
```

### Recherche de valeur

```python
def _set_combo_value(self, value: str) -> None:
    """Sélectionne l'item dont itemData == value."""
    for i in range(self._combo.count()):
        if self._combo.itemData(i) == value:
            self._combo.setCurrentIndex(i)
            return
    # Fallback : premier item si existe
    if self._combo.count() > 0:
        self._combo.setCurrentIndex(0)

def _on_changed(self, index: int) -> None:
    valeur = self._combo.itemData(index)
    app_config.set(self._config_key, valeur)
    self.changed.emit(valeur)
```

### API

```python
@property
def value(self) -> str:
    return self._combo.itemData(self._combo.currentIndex())

def set_value(self, value: str) -> None:
    self._set_combo_value(value)
    app_config.set(self._config_key, value)
```

---

## 5. ConfigSpin

Champ de saisie numérique avec pas et intervalle configurables.

| Propriété | Valeur |
|-----------|--------|
| **Héritage** | `QFrame` |
| **Ligne** | 395 |
| **Widget interne** | `QSpinBox` |
| **Signal** | `changed(int)` |
| **Persistance** | `app_config.set(key, int)` sur `valueChanged` |

```python
class ConfigSpin(QFrame):
    changed = Signal(int)

    def __init__(self, label: str, config_key: str, ...):
        # ...
        self._spin = QSpinBox()
        self._spin.setMinimum(minimum)
        self._spin.setMaximum(maximum)
        self._spin.setSingleStep(step)
        self._spin.setValue(int(app_config.get(config_key, defaut)))
        self._spin.valueChanged.connect(self._on_changed)

    def _on_changed(self, value: int) -> None:
        app_config.set(self._config_key, value)
        self.changed.emit(value)

    @property
    def value(self) -> int:
        return self._spin.value()

    def set_value(self, val: int) -> None:
        self._spin.setValue(val)
```

---

## 6. ConfigFilePicker

Sélecteur de fichier avec dialogue natif `QFileDialog`.

| Propriété | Valeur |
|-----------|--------|
| **Héritage** | `QFrame` |
| **Ligne** | 478 |
| **Widgets internes** | `QLineEdit` (lecture seule) + 2 `QPushButton` |
| **Signal** | `changed(str)` |
| **Persistance** | Sur sélection ou effacement |

### Layout

```
[label]  [_______________________________]  [📁 Parcourir...]  [✕]
         QLineEdit (readOnly)               QPushButton        QPushButton
```

### Code

```python
class ConfigFilePicker(QFrame):
    changed = Signal(str)

    def __init__(self, label: str, config_key: str, ...):
        # ...
        self._path_display = QLineEdit()
        self._path_display.setReadOnly(True)
        self._path_display.setText(app_config.get(config_key, ""))

        self._browse_btn = QPushButton("Parcourir...")
        self._browse_btn.clicked.connect(self._on_browse)

        self._clear_btn = QPushButton("✕")
        self._clear_btn.clicked.connect(self._on_clear)

    def _on_browse(self) -> None:
        chemin, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner un fichier",
            self._path_display.text() or "",
        )
        if chemin:
            self.set_file_path(chemin)

    def _on_clear(self) -> None:
        self.set_file_path("")

    def set_file_path(self, path: str) -> None:
        self._path_display.setText(path)
        app_config.set(self._config_key, path)
        self.changed.emit(path)
```

---

## 7. ConfigDirectoryPicker

Sélecteur de dossier, similaire à `ConfigFilePicker` mais avec `QFileDialog.getExistingDirectory`.

| Propriété | Valeur |
|-----------|--------|
| **Héritage** | `QFrame` |
| **Ligne** | 613 |
| **Widgets internes** | `QLineEdit` (lecture seule) + 2 `QPushButton` |
| **Signal** | `changed(str)` |

```python
def _on_browse(self) -> None:
    dossier = QFileDialog.getExistingDirectory(
        self, "Sélectionner un dossier",
        self._path_display.text() or "",
    )
    if dossier:
        self.set_directory(dossier)

def set_directory(self, path: str) -> None:
    self._path_display.setText(path)
    app_config.set(self._config_key, path)
    self.changed.emit(path)
```

---

## 8. ConfigResetBtn

Bouton de réinitialisation de tous les paramètres avec confirmation.

| Propriété | Valeur |
|-----------|--------|
| **Héritage** | `QPushButton` |
| **Ligne** | 747 |
| **Texte** | `↺ Réinitialiser les paramètres` |

```python
class ConfigResetBtn(QPushButton):
    def __init__(self, parent=None):
        super().__init__("↺ Réinitialiser les paramètres", parent)
        self.clicked.connect(self._on_click)

    def _on_click(self) -> None:
        reponse = QMessageBox.question(
            self,
            "Réinitialisation",
            "Voulez-vous réinitialiser tous les paramètres ?\n"
            "Cette action est irréversible.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reponse == QMessageBox.Yes:
            app_config.reset()
            QMessageBox.information(
                self,
                "Réinitialisation",
                "Paramètres réinitialisés.\n"
                "Veuillez redémarrer l'application pour appliquer les changements.",
            )
```

> ⚠️ **Note** : Le `ConfigResetBtn` n'est pas lié à une `config_key` spécifique. Il réinitialise **tous** les paramètres de l'application via `app_config.reset()`, pas seulement ceux de la page courante.

---

## 9. Fonctions utilitaires

### `_lire_valeur_widget(widget)`

Lecture polymorphique : retourne la valeur actuelle de n'importe quel widget de config.

```python
def _lire_valeur_widget(widget: QWidget):
    if isinstance(widget, ConfigToggle):
        return widget.is_checked        # → bool
    if isinstance(widget, ConfigCombo):
        return widget.value             # → str (itemData)
    if isinstance(widget, ConfigSpin):
        return widget.value             # → int
    if isinstance(widget, ConfigEntry):
        return widget.text              # → str
    if isinstance(widget, ConfigFilePicker):
        return widget.file_path         # → str
    if isinstance(widget, ConfigDirectoryPicker):
        return widget.directory         # → str
    return "?"                          # fallback
```

### `_ecrire_valeur_widget(widget, valeur)`

Écriture polymorphique avec dispatch par type :

```python
def _ecrire_valeur_widget(widget: QWidget, valeur) -> None:
    if isinstance(widget, ConfigToggle):
        widget.set_checked(bool(valeur))
    elif isinstance(widget, ConfigCombo):
        widget.set_value(str(valeur))
    elif isinstance(widget, ConfigSpin):
        widget.set_value(int(valeur))
    elif isinstance(widget, ConfigEntry):
        widget.set_text(str(valeur))
        # setText n'émet pas editingFinished → persistance manuelle
        app_config.set(widget.config_key, str(valeur))
    elif isinstance(widget, ConfigFilePicker):
        widget.set_file_path(str(valeur))
    elif isinstance(widget, ConfigDirectoryPicker):
        widget.set_directory(str(valeur))
```

> ⚠️ **Cas spécial `ConfigEntry`** : `setText()` ne déclenche pas `editingFinished`. Une persistance manuelle via `app_config.set()` est donc nécessaire pour que la valeur soit sauvegardée.

### `highlight_widget(widget, duree_ms=1500)`

Fait défiler la vue jusqu'au widget et le met temporairement en surbrillance.

```python
def highlight_widget(widget: QWidget, duree_ms: int = 1500) -> None:
    # 1. Défilement jusqu'au widget
    parent = widget.parent()
    while parent is not None:
        if isinstance(parent, QScrollArea):
            parent.ensureWidgetVisible(widget)
            break
        parent = parent.parent()

    # 2. Surbrillance temporaire
    style_original = widget.styleSheet()
    widget.setStyleSheet("border: 2px solid rgba(108, 92, 231, 0.5);")

    QTimer.singleShot(duree_ms, lambda: widget.setStyleSheet(style_original))
```

| Étape | Action |
|-------|--------|
| **Défilement** | Parcourt la hiérarchie parentale pour trouver `QScrollArea`, puis `ensureWidgetVisible()` |
| **Surbrillance** | Bordure violette semi-transparente `rgba(108, 92, 231, 0.5)` |
| **Rétablissement** | Restaure le `styleSheet` original après `duree_ms` via `QTimer.singleShot` |

---

## 10. ConfigPage

Page complète de paramètres avec zone défilante, indexation des widgets et support des profils.

| Propriété | Valeur |
|-----------|--------|
| **Héritage** | `QFrame` |
| **Ligne** | 810 |
| **Structure** | Titre + `QScrollArea` + `_content` (QVBoxLayout) |
| **Dictionnaire** | `self._widgets: dict[str, QWidget]` — indexé par `config_key` |

### Architecture interne

```
┌─ ConfigPage ──────────────────────────────────────────┐
│  Titre "Réseau"                    (QLabel)            │
│  ┌─ QScrollArea ─────────────────────────────────┐    │
│  │  ┌─ _content (QVBoxLayout) ───────────────┐   │    │
│  │  │  ConfigSection "Connexion"              │   │    │
│  │  │    ├─ ConfigToggle "UPnP"               │   │    │
│  │  │    ├─ ConfigSpin "Port"                 │   │    │
│  │  │    └─ ConfigCombo "Mode"                │   │    │
│  │  │  ConfigSection "Limites"                │   │    │
│  │  │    └─ ConfigSpin "Upload"               │   │    │
│  │  │  ConfigResetBtn                         │   │    │
│  │  │  [stretch]                              │   │    │
│  │  └─────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  self._widgets = {                                       │
│    "reseau.upnp": <ConfigToggle>,                        │
│    "reseau.port_ecoute": <ConfigSpin>,                   │
│    ...                                                   │
│  }                                                       │
└─────────────────────────────────────────────────────────┘
```

### Méthodes

#### `add(widget)`

```python
def add(self, widget: QWidget) -> None:
    """Ajoute un widget avant le stretch final."""
    # Insère avant le dernier élément (le stretch)
    self._content.layout().insertWidget(
        self._content.layout().count() - 1, widget
    )
    self._collect_config_widgets(widget)
```

> Les widgets sont insérés avant le stretch final, ce qui les maintient en haut de la page.

#### `_collect_config_widgets(container)`

Parcourt récursivement tous les enfants `QFrame` du conteneur et indexe ceux qui possèdent une propriété `config_key` :

```python
def _collect_config_widgets(self, container: QWidget) -> None:
    """Indexe récursivement les widgets de config trouvés dans container."""
    for child in container.findChildren(QFrame):
        if hasattr(child, 'config_key'):
            key = child.config_key
            if key:
                self._widgets[key] = child
```

#### `_find_widget_by_key(config_key)`

Accès direct au dictionnaire :

```python
def _find_widget_by_key(self, config_key: str) -> QWidget | None:
    return self._widgets.get(config_key)
```

#### `applique_profile(data: dict)`

Applique un dictionnaire de valeurs en masse et retourne un rapport des modifications :

```python
def applique_profile(self, data: dict) -> list[tuple]:
    """Applique un profil de configuration en masse.

    Args:
        data: Dictionnaire {config_key: nouvelle_valeur}

    Returns:
        Liste de tuples (config_key, ancienne_valeur, nouvelle_valeur, widget)
    """
    changements = []
    for key, nouvelle_valeur in data.items():
        widget = self._find_widget_by_key(key)
        if widget is None:
            continue

        ancienne_valeur = _lire_valeur_widget(widget)
        _ecrire_valeur_widget(widget, nouvelle_valeur)
        changements.append((key, ancienne_valeur, nouvelle_valeur, widget))

    return changements
```

### Exemple d'utilisation

```python
# center.py
page_reseau = ConfigPage("Réseau")

connexion_section = ConfigSection("Connexion")
connexion_section.add(ConfigToggle("UPnP", "reseau.upnp"))
connexion_section.add(ConfigSpin("Port d'écoute", "reseau.port_ecoute", minimum=1024, maximum=65535))
connexion_section.add(ConfigCombo("Mode connexion", "reseau.mode_connexion_peer", options=[
    ("RACE", "RACE"), ("FALLBACK", "FALLBACK"),
]))
page_reseau.add(connexion_section)

page_reseau.add(ConfigResetBtn())
```

---

## 11. Diagramme de classes complet

```
┌─────────────────────────────────────────────────────────┐
│  QFrame (PySide6)                                       │
│                                                         │
│  ├── ConfigSection                                      │
│  │     - _options_layout: QVBoxLayout                   │
│  │     + add(widget)                                    │
│  │                                                      │
│  ├── ConfigToggle                                       │
│  │     - _checkbox: QCheckBox                           │
│  │     + is_checked: bool        (property)             │
│  │     + set_checked(value)                             │
│  │     + config_key: str          (property)            │
│  │     - _on_toggled(checked)                           │
│  │     ~~~~~~~~ signal: toggled(bool)                   │
│  │                                                      │
│  ├── ConfigEntry                                        │
│  │     - _entry: QLineEdit                              │
│  │     + text: str               (property)             │
│  │     + set_text(value)                                │
│  │     + config_key: str          (property)            │
│  │     - _on_changed()                                  │
│  │     - _on_text_changed(text)                         │
│  │     ~~~~~~~~ signal: changed(str)                    │
│  │                                                      │
│  ├── ConfigCombo                                        │
│  │     - _combo: QComboBox                              │
│  │     + value: str              (property)             │
│  │     + set_value(value)                               │
│  │     + config_key: str          (property)            │
│  │     - _set_combo_value(value)                        │
│  │     - _on_changed(index)                             │
│  │     ~~~~~~~~ signal: changed(str)                    │
│  │                                                      │
│  ├── ConfigSpin                                         │
│  │     - _spin: QSpinBox                                │
│  │     + value: int               (property)            │
│  │     + set_value(value)                               │
│  │     + config_key: str          (property)            │
│  │     - _on_changed(value)                             │
│  │     ~~~~~~~~ signal: changed(int)                    │
│  │                                                      │
│  ├── ConfigFilePicker                                   │
│  │     - _path_display: QLineEdit (readOnly)            │
│  │     + file_path: str           (property)            │
│  │     + set_file_path(path)                            │
│  │     + config_key: str          (property)            │
│  │     - _on_browse()     → QFileDialog.getOpenFileName │
│  │     - _on_clear()      → set_file_path("")           │
│  │     ~~~~~~~~ signal: changed(str)                    │
│  │                                                      │
│  └── ConfigDirectoryPicker                              │
│        - _path_display: QLineEdit (readOnly)            │
│        + directory: str            (property)           │
│        + set_directory(path)                            │
│        + config_key: str          (property)            │
│        - _on_browse()  → QFileDialog.getExistingDirectory│
│        - _on_clear()   → set_directory("")              │
│        ~~~~~~~~ signal: changed(str)                    │
│                                                         │
│  QPushButton                                            │
│  └── ConfigResetBtn                                     │
│        + _on_click() → QMessageBox → app_config.reset() │
│                                                         │
│  ConfigPage (QFrame)                                    │
│  ├── structure: Titre + QScrollArea + _content          │
│  ├── _widgets: dict[str, QWidget]                       │
│  ├── + add(widget)                                      │
│  ├── + add_placeholder(text)                            │
│  ├── - _collect_config_widgets(container)               │
│  ├── - _find_widget_by_key(key) → QWidget | None        │
│  └── + applique_profile(data) → list[tuple]            │
│                                                         │
│  Fonctions globales                                     │
│  ├── _lire_valeur_widget(widget) → any                 │
│  ├── _ecrire_valeur_widget(widget, valeur)              │
│  └── highlight_widget(widget, duree_ms=1500)            │
└─────────────────────────────────────────────────────────┘
```

---

## 12. Résumé technique

| Propriété | Valeur |
|-----------|--------|
| **Fichier** | `src/gui/widgets/config.py` |
| **Lignes** | 918 |
| **Classes** | 9 : `ConfigSection`, `ConfigToggle`, `ConfigEntry`, `ConfigCombo`, `ConfigSpin`, `ConfigFilePicker`, `ConfigDirectoryPicker`, `ConfigResetBtn`, `ConfigPage` |
| **Fonctions** | 3 : `_lire_valeur_widget`, `_ecrire_valeur_widget`, `highlight_widget` |
| **Signaux** | 6 × `changed(T)`, 1 × `toggled(bool)` |
| **Pattern** | Polymorphisme via `isinstance` pour lecture/écriture uniforme |
| **Persistance** | `app_config.get()` en lecture initiale, `app_config.set()` au changement |
| **Indexation** | `_collect_config_widgets()` scanne récursivement les enfants `QFrame` |
| **Profils** | `applique_profile(dict)` pour appliquer des lots de valeurs |
| **Intégration** | `center.py._build_config_pages()` construit les 8 `ConfigPage` |

### Flux typique

```
1. center.py crée ConfigPage("Réseau")
2. Ajoute des ConfigSection avec leurs widgets
3. Chaque widget lit app_config.get() dans __init__
4. L'utilisateur modifie une valeur
5. Le slot _on_changed/_on_toggled persiste via app_config.set()
6. Le signal changed/toggled est émis
7. Les contrôleurs abonnés réagissent au changement
```
