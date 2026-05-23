"""Correction finale de main_window.py pour intégrer QSS Inspector."""
import logging
import pathlib

logger = logging.getLogger("[TEMP-FIX-MW2]")

f = pathlib.Path('src/gui/main_window.py')
text = f.read_text(encoding='utf-8')

changes = 0

# 1. Ajouter Qt dans l'import PySide6.QtGui
if 'from PySide6.QtGui import' in text and 'Qt' not in text.split('from PySide6.QtGui import')[1].split('\n')[0]:
    text = text.replace(
        'from PySide6.QtGui import QAction, QCloseEvent',
        'from PySide6.QtCore import Qt\nfrom PySide6.QtGui import QAction, QCloseEvent'
    )
    changes += 1
    print("1. Import Qt ajouté")

# 2. Ajouter l'initialisation QSS Inspector APRÈS setStyleSheet
old = "        self.setStyleSheet(DARK_THEME)\n\n        # ?? Barre de menu ??"
new = "        self.setStyleSheet(DARK_THEME)\n\n        # QSS Inspector (DevTool) - Ctrl+Shift+I\n        self._qss_inspector = QssInspector(self)\n        self.addDockWidget(Qt.RightDockWidgetArea, self._qss_inspector)\n        self._qss_inspector.hide()\n\n        # ?? Barre de menu ??"
if old in text:
    text = text.replace(old, new, 1)
    changes += 1
    print("2. Initialisation QSS Inspector ajoutée")
else:
    # Try to find what's actually there
    for i, line in enumerate(text.splitlines(), 1):
        if 'setStyleSheet(DARK_THEME)' in line:
            print(f"2. Ligne {i}: {line}")
            print(f"   Ligne {i+1}: {text.splitlines()[i] if i < len(text.splitlines()) else 'EOF'}")
            print(f"   Ligne {i+2}: {text.splitlines()[i+1] if i+1 < len(text.splitlines()) else 'EOF'}")

# 3. Supprimer le DUPLICATA du menu Outils (lignes 162-168)
duplicate = """        # ?? Menu Outils ??????????????????????????????????????????????
        tools_menu = menubar.addMenu("&Outils")
        inspect_action = QAction("? &QSS Inspector", self)
        inspect_action.setShortcut("Ctrl+Shift+I")
        inspect_action.setCheckable(True)
        inspect_action.toggled.connect(self._toggle_inspector)
        tools_menu.addAction(inspect_action)
"""
if duplicate in text:
    text = text.replace(duplicate, "", 1)
    changes += 1
    print("3. Duplicata menu Outils supprimé")
else:
    print("3. Duplicata non trouvé (déjà supprimé?)")

# 4. Ajouter la méthode _toggle_inspector (juste avant les propriétés)
marker = "    # ??????????????????????????????????????????\n    #  API publique ? acc?s aux zones"
inspector_method = """    def _toggle_inspector(self, visible: bool) -> None:
        \"\"\"Affiche ou cache le QSS Inspector.\"\"\"
        if visible:
            self._qss_inspector.refresh()
            self._qss_inspector.show()
            self._qss_inspector.raise_()
        else:
            self._qss_inspector.hide()

    # ??????????????????????????????????????????"""

# Find what's actually before the API section
lines = text.splitlines()
for i, line in enumerate(lines):
    if 'API publique' in line or 'acces aux zones' in line or 'acc?s aux zones' in line:
        # Go back to the separator
        for j in range(i-1, -1, -1):
            if '??????????' in lines[j]:
                marker_line = j
                break
        print(f"4. API section found at line {i+1}, marker at {marker_line+1}")
        
        # Check if _toggle_inspector already exists
        if 'def _toggle_inspector' in text:
            print("4. _toggle_inspector existe déjà, skipping")
        else:
            # Insert before the marker
            old_marker = '\n'.join(lines[marker_line:marker_line+3])
            new_marker = inspector_method + '\n    # ??????????????????????????????????????????\n    #  API publique ? acc?s aux zones'
            if old_marker in text:
                text = text.replace(old_marker, new_marker, 1)
                changes += 1
                print("4. _toggle_inspector ajoutée")
            else:
                print(f"4. Marker text mismatch: {old_marker[:80]!r}")
        break

f.write_text(text, encoding='utf-8')
print(f"\nTotal: {changes} modifications")
