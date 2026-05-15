"""Ajoute l'import QLineEdit et les methodes de recherche manquantes."""
import pathlib

f = pathlib.Path('src/gui/devtool/qss_inspector.py')
text = f.read_text(encoding='utf-8-sig')

# 1. Ajouter QLineEdit dans les imports
# Chercher "QListWidget," et ajouter "QLineEdit," avant
if 'QLineEdit,' not in text:
    text = text.replace('    QListWidget,', '    QLineEdit,\n    QListWidget,', 1)
    print("1. Import QLineEdit ajoute")
else:
    print("1. QLineEdit deja importe")

# 2. Ajouter les methodes de recherche a _WidgetTree
if 'def set_search_filter' not in text:
    # Trouver la fin de select_widget
    # Chercher "p = p.parent()" et la ligne d'apres
    marker = '                p = p.parent()'
    insert = marker + """

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

    if marker in text:
        text = text.replace(marker, insert, 1)
        print("2. Methodes de recherche ajoutees")
    else:
        # Fallback: chercher sans les espaces
        for needle in ['p = p.parent()', 'p.parent()']:
            if needle in text:
                text = text.replace(needle, needle + insert, 1)
                print(f"2. Methodes ajoutees via '{needle}'")
                break
        else:
            print("2. Marqueur 'p.parent()' introuvable!")
else:
    print("2. Methodes deja presentes")

f.write_text(text, encoding='utf-8')
print("\nTermine")
