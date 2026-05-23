"""Correction complète et finale de main_window.py."""
import logging
import pathlib
import re

logger = logging.getLogger("[TEMP-FIX-MW3]")

f = pathlib.Path('src/gui/main_window.py')
text = f.read_text(encoding='utf-8-sig')

# Commençons par nettoyer les doublons et ajouter ce qui manque

# 1. Supprimer le duplicata du menu Outils (les lignes avec emojis)
import re
# Trouver le bloc duplicata
dupe_pattern = r'        # \?\? Menu Outils.*?\n        tools_menu = menubar\.addMenu\("&Outils"\)\n        inspect_action = QAction\("\? &QSS Inspector.*?\n        inspect_action\.setShortcut\("Ctrl\+Shift\+I"\)\n        inspect_action\.setCheckable\(True\)\n        inspect_action\.toggled\.connect\(self\._toggle_inspector\)\n        tools_menu\.addAction\(inspect_action\)\n'
text_new = re.sub(dupe_pattern, '', text, count=1, flags=re.DOTALL)
if text_new != text:
    print("1. Duplicata menu Outils supprimé")
    text = text_new
else:
    print("1. Duplicata non trouvé")

# 2. Ajouter l'initialisation QSS Inspector APRÈS setStyleSheet
# Chercher le pattern exact
lines = text.splitlines(True)
new_lines = []
init_done = False
for i, line in enumerate(lines):
    new_lines.append(line)
    if not init_done and 'self.setStyleSheet(DARK_THEME)' in line:
        # Ajouter les lignes d'init juste après
        new_lines.append('\n')
        new_lines.append('        # QSS Inspector (DevTool) - Ctrl+Shift+I pour afficher\n')
        new_lines.append('        self._qss_inspector = QssInspector(self)\n')
        new_lines.append('        self.addDockWidget(Qt.RightDockWidgetArea, self._qss_inspector)\n')
        new_lines.append('        self._qss_inspector.hide()\n')
        init_done = True
        print(f"2. Init QSS Inspector ajoutée après ligne {i+1}")

text = ''.join(new_lines)

# 3. Vérifier que _toggle_inspector existe
if 'def _toggle_inspector' not in text:
    # Trouver le début de la section API publique
    apis = list(re.finditer(r'#.*API publique.*', text))
    if apis:
        api_pos = apis[0].start()
        # Recule jusqu'au séparateur
        prefix = text[:api_pos]
        sep_pos = prefix.rfind('#')
        # Insérer juste avant le séparateur
        toggle_code = """
    # ── DevTool ──────────────────────────────────────────

    def _toggle_inspector(self, visible: bool) -> None:
        \"\"\"Affiche ou cache le QSS Inspector.\"\"\"
        if visible:
            self._qss_inspector.refresh()
            self._qss_inspector.show()
            self._qss_inspector.raise_()
        else:
            self._qss_inspector.hide()

"""
        text = text[:sep_pos] + toggle_code + text[sep_pos:]
        print(f"3. _toggle_inspector ajoutée")
    else:
        print("3. Section API publique non trouvée")
else:
    print("3. _toggle_inspector déjà présente")

f.write_text(text, encoding='utf-8')
print("\n✅ Terminé")
