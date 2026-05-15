"""Correction des ajouts echoues pour la barre de recherche."""
import pathlib, re

f = pathlib.Path('src/gui/devtool/qss_inspector.py')
raw = f.read_bytes()
text = raw.decode('utf-8-sig')

# 1. Ajouter la barre de recherche APRÈS "main_layout.addWidget(toolbar)"
# Chercher cette chaine ASCII-safe
toolbar_marker = 'main_layout.addWidget(toolbar)'
search_ui = """
        # Barre de recherche
        self._search_bar = QLineEdit()
        self._search_bar.setPlaceholderText("Rechercher (classe, objectName, texte)...")
        self._search_bar.textChanged.connect(self._on_search)
        main_layout.addWidget(self._search_bar)"""

if toolbar_marker in text:
    # Check if search bar already exists
    if 'self._search_bar' not in text:
        text = text.replace(toolbar_marker, toolbar_marker + search_ui, 1)
        print("1. Barre de recherche ajoutee")
    else:
        print("1. Barre de recherche deja presente")
else:
    print("1. toolbar_marker non trouve!")

# 2. Ajouter set_search_filter et _apply_search_recursive à _WidgetTree
# Trouver la fin de la methode select_widget par l'ancrage "p = item.parent()"
parent_marker = "p = item.parent()"
method_end = """            while p is not None:
                p.setExpanded(True)
                p = p.parent()"""

search_methods = """

    def set_search_filter(self, query: str) -> None:
        if not query:
            root = self.invisibleRootItem()
            for i in range(root.childCount()):
                self._apply_visibility_recursive(root.child(i), True)
            return
        query = query.lower()
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            self._apply_search_recursive(root.child(i), query)

    def _apply_search_recursive(self, item, query):
        match = False
        for col in range(item.columnCount()):
            if query in item.text(col).lower():
                match = True
                break
        child_match = False
        for i in range(item.childCount()):
            if self._apply_search_recursive(item.child(i), query):
                child_match = True
        visible = match or child_match
        item.setHidden(not visible)
        if match:
            item.setExpanded(True)
        return visible

    @staticmethod
    def _apply_visibility_recursive(item, visible):
        item.setHidden(not visible)
        for i in range(item.childCount()):
            _WidgetTree._apply_visibility_recursive(item.child(i), visible)"""

if parent_marker in text and 'def set_search_filter' not in text:
    # Trouver l'endroit exact ou inserer (apres p = p.parent())
    idx = text.find(method_end)
    if idx >= 0:
        end_idx = idx + len(method_end)
        text = text[:end_idx] + search_methods + text[end_idx:]
        print("2. Methodes de recherche ajoutees a _WidgetTree")
    else:
        print("2. method_end non trouve!")
else:
    print("2. Methodes deja presentes ou marker non trouve")

# 3. Style QLineEdit dans le CSS
style_qline = """            "QLineEdit {"
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
            """

# Chercher le bloc de style du QSplitter
splitter_style = 'QSplitter::handle'
if splitter_style in text and 'QLineEdit' not in text:
    idx = text.find('QSplitter::handle')
    if idx >= 0:
        text = text[:idx] + style_qline + text[idx:]
        print("3. Style QLineEdit ajoute")
else:
    print("3. Style QLineEdit deja present ou QSplitter non trouve")

f.write_bytes(text.encode('utf-8'))
print("\nTermine")
