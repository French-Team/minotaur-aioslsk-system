---
title: "QSS Inspector — Outil de développement pour le débogage des styles"
category: technique
icon: 🎨
keywords:
  - QSS Inspector devtool
  - qss inspecteur interface
  - qss_inspector.py outil
  - debogage stylesheet qt
  - débogage stylesheet qt
  - inspection widget pyside
  - arbre hierarchique widget
  - arbre hiérarchique widget
  - _WidgetTree navigation
  - _PropertyPanel propriete
  - _PropertyPanel propriété
  - onglet propriete widget
  - onglet propriété widget
  - onglet stylesheet cascade
  - onglet validation qss
  - validation qss erreur
  - _qss_errors validation
  - couleur hex 8 chiffres
  - couleur hex 3 chiffres
  - accolade desequilibree qss
  - accolade déséquilibrée qss
  - selecteur vide qss
  - sélecteur vide qss
  - point virgule manquant qss
  - _PickFilter inspection visuelle
  - clic inspect widget
  - mode inspection visuelle
  - QssInspector QDockWidget
  - toolbar rafraichir inspecter
  - toolbar rafraîchir inspecter
  - barre recherche widget
  - scan all validation globale
  - scan all qss tous widgets
  - show qt warnings logs
  - warning qt stylesheet
  - inspect widget api
  - _widget_label format
  - _widget_path chemin hierarchie
  - _widget_path chemin hiérarchie
  - _apply_style theme sombre
  - qss palette sombre
  - raccourci clavier inspection
  - inspecteur style qt
  - outil developpement theme
  - outil développement thème
  - debogage qss temps reel
  - débogage qss temps réel
  - qss inspector guide
---

# 🎨 QSS Inspector — Outil de développement pour le débogage des styles

## Introduction

Le module `src/gui/devtool/qss_inspector.py` (953 lignes) est un **outil de développement intégré** qui permet d'inspecter et de déboguer les stylesheets Qt (QSS) de l'application en temps réel.

Il offre :
- Un **arbre hiérarchique** de tous les widgets de l'application
- Un **panneau de propriétés** détaillant chaque widget sélectionné
- Une **validation QSS** statique detectant les erreurs courantes
- Un **mode d'inspection visuelle** par clic direct sur l'interface
- Une **validation globale** de tous les stylesheets de l'application

---

## Architecture

```
QssInspector (QDockWidget)
      │
      ├── Toolbar
      │   ├── 🔄 Rafraîchir
      │   ├── 👆 Inspecter (mode pick)
      │   ├── 📁 Réduire tout
      │   ├── 🔍 Scan All
      │   └── ⚠️ Qt Warnings
      │
      ├── Barre de recherche (filtre l'arbre)
      │
      └── QSplitter
            │
            ├── _WidgetTree (QTreeWidget)
            │   Colonnes : Widget | Classe
            │
            └── _PropertyPanel (QTabWidget)
                  ├── 📋 Propriétés
                  ├── 📄 Stylesheet
                  └── ✅ Validation
```

---

## 1. Validation QSS — `_qss_errors(stylesheet)`

Fonction utilitaire qui analyse statiquement le code QSS et détecte 4 types d'erreurs :

| Erreur | Détection | Exemple | Niveau |
|--------|-----------|---------|--------|
| **Couleur hex 8 chiffres** | `_RE_HEX8` | `#RRGGBBAA` non supporté par Qt | ⚠️ Warning |
| **Couleur hex 3 chiffres** | `_RE_HEX3` | `#RGB` non supporté par Qt | ⚠️ Warning |
| **Accolades déséquilibrées** | Comptage `{` vs `}` | `QWidget { color: red;` | ❌ Erreur |
| **Sélecteur vide** | `{\s*}` | `QWidget {}` | ⚠️ Warning |
| **Point-virgule manquant** | Regex après valeur | `color: red` sans `;` | ⚠️ Warning |

### Propriétés CSS classifiées

```python
_CSS_COLOR_PROPS = {"color", "background-color", "border-color",
                    "selection-color", "selection-background-color", ...}
_CSS_RECT_PROPS = {"margin", "padding", "border-width",
                   "border-radius", ...}
```

Permet de catégoriser les propriétés dans l'affichage.

---

## 2. Fonctions utilitaires

### `_widget_label(w: QWidget) -> str`

Génère un identifiant lisible pour un widget :

```python
def _widget_label(w: QWidget) -> str:
    """Format : ClassName[objectName] ou ClassName('text')"""
    if w.objectName():
        return f"{w.__class__.__name__}[{w.objectName()}]"
    if hasattr(w, "text") and w.text():
        return f"{w.__class__.__name__}('{w.text()[:20]}')"
    return w.__class__.__name__
```

### `_widget_path(w: QWidget) -> str`

Construit le chemin complet dans l'arborescence :

```python
def _widget_path(w: QWidget) -> str:
    """Exemple : MainWindow → centerWidget → QTabWidget → Button"""
    parts = []
    current = w
    while current:
        parts.append(_widget_label(current))
        current = current.parentWidget()
    return " → ".join(reversed(parts))
```

---

## 3. `_WidgetTree(QTreeWidget)` — Arbre hiérarchique

Affiche tous les widgets de l'application dans une arborescence explorable :

```python
class _WidgetTree(QTreeWidget):
    def __init__(self, on_select: Callable):
        self._on_select = on_select
        self.setHeaderLabels(["Widget", "Classe"])
        self.setAlternatingRowColors(True)
        self.setIndentation(15)
        self.itemClicked.connect(self._on_item_clicked)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        widget = item.data(0, Qt.UserRole)
        if widget:
            self._on_select(widget)

    def build_tree(self, root: QWidget):
        """Construit l'arbre récursivement à partir du widget racine."""
        self.clear()
        self._build_node(root, None)

    def _build_node(self, widget: QWidget, parent: QTreeWidgetItem):
        item = QTreeWidgetItem([_widget_label(widget),
                               widget.__class__.__name__])
        item.setData(0, Qt.UserRole, widget)
        if parent:
            parent.addChild(item)
        else:
            self.addTopLevelItem(item)
        for child in widget.findChildren(QWidget, Qt.FindDirectChildrenOnly):
            self._build_node(child, item)
```

Caractéristiques :
- **Deux colonnes** : nom du widget et classe Qt
- **Indentation** fixe de 15px
- **Lignes alternées** pour la lisibilité
- **Filtrage** via barre de recherche (masque les items non matchés)

---

## 4. `_PropertyPanel(QWidget)` — Panneau de propriétés

Affiche les détails du widget sélectionné dans 3 onglets :

### Onglet « Propriétés »

```
Identité
  Classe :     QPushButton
  Objet :      btn_search
  Héritage :   QPushButton → QAbstractButton → QWidget → QObject

Géométrie
  Position :   120, 45
  Taille :     200, 32
  Rectangle :  QRect(120, 45, 200, 32)

Size Policies
  Horizontale : Expanding
  Verticale :   Fixed

Police
  Famille :    Segoe UI
  Taille :     10pt
  Gras :       Non
```

Extrait via `inspect(widget)` :
```python
def inspect(self, widget: QWidget) -> None:
    # Propriétés de base
    geo = widget.geometry()
    info = {
        "class": widget.__class__.__name__,
        "object_name": widget.objectName(),
        "position": f"{geo.x()}, {geo.y()}",
        "size": f"{geo.width()}, {geo.height()}",
        "inheritance": " → ".join(
            c.__name__ for c in widget.__class__.__mro__
            if issubclass(c, QWidget)
        ),
    }
    # ... affichage dans le panneau
```

### Onglet « Stylesheet »

Affiche la cascade complète des stylesheets appliqués au widget :

```python
# Ordre de priorité QSS (de la plus haute à la plus basse) :
1. widget.setStyleSheet()       # Style local
2. parent.setStyleSheet()       # Styles hérités des parents
3. QApplication.setStyleSheet()  # Style global de l'app
```

Pour chaque niveau, la feuille de style est affichée dans son intégralité et la **section pertinente** (celle qui cible ce widget ou ses ancestors) est mise en évidence.

### Onglet « Validation »

Liste les erreurs QSS détectées par `_qss_errors()` :

```
⚠️  [Ligne 42] Couleur hex 8 chiffres : #2ecc71ff
    → Utiliser rgba() ou un format 6 chiffres

⚠️  [Ligne 15] Accolades déséquilibrées
    → Vérifier les fermetures { }

✅  Aucune erreur détectée
```

---

## 5. `_PickFilter` — Mode inspection visuelle

```python
class _PickFilter(QObject):
    def __init__(self, inspector):
        self._inspector = inspector
        self._active = False

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if self._active and event.type() == QEvent.MouseButtonPress:
            widget = QApplication.widgetAt(event.globalPos())
            if widget:
                self._inspector.inspect_widget(widget)
            return True
        return False
```

Quand le mode est activé :
1. Un filtre d'événements est installé sur `QApplication`
2. Cliquer sur n'importe quel widget de l'application le sélectionne dans l'inspecteur
3. Le panneau de propriétés se met à jour automatiquement

---

## 6. `QssInspector(QDockWidget)` — Interface principale

Classe principale qui intègre tous les composants :

### Toolbar

```python
class QssInspector(QDockWidget):
    def _setup_ui(self):
        toolbar = QToolBar()
        toolbar.addAction("🔄 Rafraîchir", self.refresh_tree)
        toolbar.addAction("👆 Inspecter", self.toggle_pick_mode)
        toolbar.addAction("📁 Réduire tout", self.collapse_all)
        toolbar.addAction("🔍 Scan All", self.scan_all)
        toolbar.addAction("⚠️ Qt Warnings", self.show_qt_warnings)
```

### `scan_all()`

Parcourt tous les widgets de l'application et valide leurs stylesheets :

```python
def scan_all(self) -> None:
    """Valide le QSS de tous les widgets de l'application."""
    results = []
    for widget in QApplication.allWidgets():
        errors = _qss_errors(widget.styleSheet())
        if errors:
            results.append((widget, errors))
    # Affiche les résultats dans une boîte de dialogue
```

### `show_qt_warnings()`

Affiche les warnings Qt capturés et les logs des appels `setStyleSheet` :

```python
def show_qt_warnings(self) -> None:
    """Affiche les warnings Qt interceptés."""
    warnings = self._captured_qt_warnings
    # Affiche dans une QDialog avec détails
```

### `inspect_widget(widget)`

Méthode API publique pour forcer l'inspection d'un widget spécifique :

```python
def inspect_widget(self, widget: QWidget) -> None:
    """Inspecte un widget : sélection dans l'arbre + mise à jour du panneau."""
    self._widget_tree.select_widget(widget)
    self._property_panel.inspect(widget)
```

---

## 7. Thème de l'outil

```python
def _apply_style(self) -> None:
    self.setStyleSheet("""
        QssInspector {
            background-color: #1e1e2e;
            color: #cdd6f4;
        }
        QTreeWidget {
            background-color: #181825;
            color: #cdd6f4;
            alternate-background-color: #1e1e2e;
            font-family: "Consolas", "Courier New", monospace;
        }
        QTabWidget::pane {
            background-color: #181825;
            border: 1px solid #313244;
        }
        QLabel#error {
            color: #f38ba8;
        }
        QLabel#warning {
            color: #f9e2af;
        }
        QLabel#success {
            color: #a6e3a1;
        }
    """)
```

Palette sombre cohérente avec l'application :
- Fond : `#1e1e2e` / `#181825`
- Texte : `#cdd6f4`
- Erreur : `#f38ba8` (rouge)
- Warning : `#f9e2af` (jaune)
- Succès : `#a6e3a1` (vert)
- Police : monospace (Consolas / Courier New)

---

## Utilisation

### Accès à l'outil

L'inspecteur est accessible via le menu **Aide** → **QSS Inspector** ou via un **raccourci clavier** (selon configuration).

### Workflow typique

```
1. Ouvrir QSS Inspector (Aide → QSS Inspector)
      │
2. 🔄 Rafraîchir l'arbre des widgets
      │
3. Naviguer dans l'arbre ou 👆 Inspecter pour cliquer sur un widget
      │
4. Consulter les 3 onglets :
      ├── 📋 Propriétés (classe, géométrie, polices)
      ├── 📄 Stylesheet (cascade complète)
      └── ✅ Validation (erreurs QSS détectées)
      │
5. 🔍 Scan All pour valider TOUS les widgets
      │
6. ⚠️ Qt Warnings pour vérifier les logs Qt
```

---

## Conclusion

| Aspect | Détail |
|--------|--------|
| **Taille** | 953 lignes |
| **Rôle** | Déboguer et valider les stylesheets Qt en temps réel |
| **Arbre** | Exploration hiérarchique de tous les widgets |
| **Propriétés** | Géométrie, héritage, polices, size policies |
| **Stylsheet** | Cascade complète (local → parents → app) |
| **Validation** | 5 types d'erreurs QSS détectés (couleurs, accolades, etc.) |
| **Mode pick** | Clic direct sur l'interface pour inspecter |
| **Scan global** | Validation de tous les widgets de l'application |
