"""Correction du QSS Inspector apres review :
- void -> None
- closeEvent pour nettoyer eventFilter + curseur
- supprimer QTimer inutilise
- corriger double appel _toggle_pick_mode
"""
import pathlib

f = pathlib.Path('src/gui/devtool/qss_inspector.py')
text = f.read_text(encoding='utf-8-sig')

# 1. void -> None
text = text.replace('def _collapse_all(self) -> void:', 'def _collapse_all(self) -> None:')

# 2. Supprimer QTimer inutile (import)
if 'QTimer' in text:
    text = text.replace('    QTimer,\n', '')

# 3. Ajouter QCursor dans les imports si necessaire
if 'from PySide6.QtGui import QCursor' not in text:
    text = text.replace(
        'from PySide6.QtGui import QAction, QColor, QIcon',
        'from PySide6.QtGui import QAction, QColor, QCursor, QIcon'
    )

# 4. Ajouter closeEvent au QssInspector + double appel _toggle_pick_mode
# Trouver la methode _collapse_all et ajouter closeEvent avant
old_close_missing = '''    def _collapse_all(self) -> None:
        """Reduit tous les noeuds de l'arbre."""
        root = self._widget_tree.invisibleRootItem()
        for i in range(root.childCount()):
            self._collapse_recursive(root.child(i))'''

new_close_added = '''    def closeEvent(self, event):
        """Nettoie le filtre d'evenements et restaure le curseur."""
        self._pick_btn.setChecked(False)
        self._toggle_pick_mode(False)
        self._main_window.removeEventFilter(self)
        super().closeEvent(event)

    def _collapse_all(self) -> None:
        """Reduit tous les noeuds de l'arbre."""
        root = self._widget_tree.invisibleRootItem()
        for i in range(root.childCount()):
            self._collapse_recursive(root.child(i))'''

if old_close_missing in text:
    text = text.replace(old_close_missing, new_close_added, 1)
else:
    # Try without the docstring
    alt_old = '''    def _collapse_all(self) -> None:
        root = self._widget_tree.invisibleRootItem()
        for i in range(root.childCount()):
            self._collapse_recursive(root.child(i))'''
    if alt_old in text:
        text = text.replace(alt_old, new_close_added, 1)

# 5. Corriger le double appel dans _on_pick
old_on_pick = '''    def _on_pick(self, widget: QWidget) -> None:
        """Callback quand un widget est clique en mode pick."""
        self._pick_btn.setChecked(False)
        self._toggle_pick_mode(False)
        self.inspect_widget(widget)'''

new_on_pick = '''    def _on_pick(self, widget: QWidget) -> None:
        """Callback quand un widget est clique en mode pick."""
        self._pick_btn.setChecked(False)
        self.inspect_widget(widget)'''

if old_on_pick in text:
    text = text.replace(old_on_pick, new_on_pick, 1)

f.write_text(text, encoding='utf-8')
print("Fixes appliques: void -> None, closeEvent, QTimer supprime, QCursor ajoute, doublon supprime")
