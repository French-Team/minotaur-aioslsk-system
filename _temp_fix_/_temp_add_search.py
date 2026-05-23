"""Ajoute une barre de recherche au _WidgetTree du QSS Inspector."""
import logging
import pathlib
import re

logger = logging.getLogger("[TEMP-ADD-SEARCH]")

f = pathlib.Path('src/gui/devtool/qss_inspector.py')
text = f.read_text(encoding='utf-8-sig')

# 1. Ajouter l'import QLineEdit dans les QtWidgets
old_imports = """from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)"""
new_imports = """from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)"""

if old_imports in text:
    text = text.replace(old_imports, new_imports)
    print("1. Import QLineEdit ajouté")
else:
    print("1. Import QLineEdit - mot-clé 'QLineEdit' déjà présent ou pattern non trouvé")

# 2. Ajouter une méthode search au _WidgetTree
# Trouver la classe _WidgetTree et ajouter une méthode search
old_tree_end = """    def select_widget(self, widget: QWidget) -> None:
        \"\"\"Selectionne le noeud correspondant au widget dans l'arbre.\"\"\"
        item = self.widget_item_map.get(id(widget))
        if item is not None:
            self.setCurrentItem(item)
            self.scrollToItem(item)
            # Deplie les parents
            p = item.parent()
            while p is not None:
                p.setExpanded(True)
                p = p.parent()"""

new_tree_end = """    def select_widget(self, widget: QWidget) -> None:
        \"\"\"Selectionne le noeud correspondant au widget dans l'arbre.\"\"\"
        item = self.widget_item_map.get(id(widget))
        if item is not None:
            self.setCurrentItem(item)
            self.scrollToItem(item)
            # Deplie les parents
            p = item.parent()
            while p is not None:
                p.setExpanded(True)
                p = p.parent()

    def set_search_filter(self, query: str) -> None:
        \"\"\"Filtre les noeuds de l'arbre par nom de classe, objectName ou texte.\"\"\"
        if not query:
            # Restaurer la visibilite de tous les noeuds
            root = self.invisibleRootItem()
            for i in range(root.childCount()):
                self._apply_visibility_recursive(root.child(i), True)
            return

        query = query.lower()
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            self._apply_search_recursive(root.child(i), query)

    def _apply_search_recursive(self, item: QTreeWidgetItem, query: str) -> bool:
        \"\"\"Applique le filtre de recherche recursivement. Retourne True si un enfant correspond.\"\"\"
        match = False

        # Verifier le texte du noeud courant
        for col in range(item.columnCount()):
            if query in item.text(col).lower():
                match = True
                break

        # Verifier les enfants
        child_match = False
        for i in range(item.childCount()):
            if self._apply_search_recursive(item.child(i), query):
                child_match = True

        visible = match or child_match
        item.setHidden(not visible)

        # Si l'item correspond, deplier
        if match:
            item.setExpanded(True)

        return visible

    @staticmethod
    def _apply_visibility_recursive(item: QTreeWidgetItem, visible: bool) -> None:
        \"\"\"Applique la visibilite recursivement.\"\"\"
        item.setHidden(not visible)
        for i in range(item.childCount()):
            _WidgetTree._apply_visibility_recursive(item.child(i), visible)"""

if old_tree_end in text:
    text = text.replace(old_tree_end, new_tree_end, 1)
    print("2. Methodes de recherche ajoutees a _WidgetTree")
else:
    print("2. ATTENTION: old_tree_end non trouve!")
    # Fallback: chercher la signature exacte
    idx = text.find('def select_widget(self, widget: QWidget) -> None:')
    if idx >= 0:
        print(f"   select_widget trouve a l'index {idx}")
    idx = text.find('p.setExpanded(True)')
    print(f"   dernier p.setExpanded trouve a l'index {idx}")

# 3. Ajouter la QLineEdit de recherche dans la UI
# Modifier le constructeur de QssInspector pour ajouter la search bar
old_ui = """        # ?? Splitter arbre + proprietes ??
        splitter = QSplitter(Qt.Vertical)"""

new_ui = """        # ?? Barre de recherche ??
        search_bar = QLineEdit()
        search_bar.setPlaceholderText("Rechercher un widget (classe, objectName, texte)...")
        search_bar.textChanged.connect(self._on_search)
        main_layout.addWidget(search_bar)

        # ?? Splitter arbre + proprietes ??
        splitter = QSplitter(Qt.Vertical)"""

if old_ui in text:
    text = text.replace(old_ui, new_ui, 1)
    print("3. Barre de recherche ajoutee dans l'interface")
else:
    print("3. ATTENTION: old_ui non trouve!")
    idx = text.find('splitter = QSplitter(Qt.Vertical)')
    print(f"   splitter trouve a l'index {idx}")

# 4. Ajouter la methode _on_search dans QssInspector
old_inspector_end = """    @staticmethod
    def _collapse_recursive(item: QTreeWidgetItem) -> None:
        item.setExpanded(False)
        for i in range(item.childCount()):
            QssInspector._collapse_recursive(item.child(i))"""

new_inspector_end = """    def _on_search(self, query: str) -> None:
        \"\"\"Filtre l'arbre par la requete de recherche.\"\"\"
        self._widget_tree.set_search_filter(query)

    @staticmethod
    def _collapse_recursive(item: QTreeWidgetItem) -> None:
        item.setExpanded(False)
        for i in range(item.childCount()):
            QssInspector._collapse_recursive(item.child(i))"""

if old_inspector_end in text:
    text = text.replace(old_inspector_end, new_inspector_end, 1)
    print("4. Methode _on_search ajoutee")
else:
    print("4. ATTENTION: old_inspector_end non trouve!")
    idx = text.find('def _collapse_recursive')
    print(f"   _collapse_recursive trouve a l'index {idx}")

# Ajouter le style de la search bar
old_style = """            "QSplitter::handle {"
            "  background: #313244;"
            "  height: 2px;"
            "}" """

new_style = """            "QLineEdit {"
            "  background: #1e1e2e;"
            "  color: #cdd6f4;"
            "  border: 1px solid #45475a;"
            "  border-radius: 4px;"
            "  padding: 4px 8px;"
            "  font-family: 'Consolas', 'Courier New', monospace;"
            "  font-size: 12px;"
            "}"
            "QLineEdit:focus {"
            "  border-color: #6c5ce7;"
            "}"
            "QSplitter::handle {"
            "  background: #313244;"
            "  height: 2px;"
            "}" """

if old_style in text:
    text = text.replace(old_style, new_style, 1)
    print("5. Style QLineEdit ajoute")
else:
    print("5. ATTENTION: old_style non trouve!")

f.write_text(text, encoding='utf-8')
print("\n=== Termine ===")
