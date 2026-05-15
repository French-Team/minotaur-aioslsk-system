"""Patch main_window.py pour intégrer le QSS Inspector."""
import pathlib

f = pathlib.Path('src/gui/main_window.py')
text = f.read_text(encoding='utf-8')

changes = 0

# 1. Ajouter l'import de QssInspector
if 'from src.gui.devtool import QssInspector' not in text:
    text = text.replace(
        'from src.gui.layout.entry import LayoutEntry',
        'from src.gui.devtool import QssInspector\nfrom src.gui.layout.entry import LayoutEntry'
    )
    changes += 1
    print("1. Import QssInspector ajouté")

# 2. Ajouter l'initialisation du QSS Inspector APRÈS setStyleSheet
old_init = """        self.setStyleSheet(DARK_THEME)

        # Initialisation de l'interface"""
new_init = """        self.setStyleSheet(DARK_THEME)

        # QSS Inspector (DevTool) — Ctrl+Shift+I pour afficher
        self._qss_inspector = QssInspector(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self._qss_inspector)
        self._qss_inspector.hide()

        # Initialisation de l'interface"""
if old_init in text:
    text = text.replace(old_init, new_init, 1)
    changes += 1
    print("2. Initialisation QSS Inspector ajoutée")
else:
    print("2. ATTENTION : old_init introuvable!")
    # Chercher la ligne exacte
    for i, line in enumerate(text.splitlines()):
        if 'setStyleSheet(DARK_THEME)' in line:
            print(f"   -> Ligne {i+1}: {line!r}")

# 3. Ajouter le menu Outils + raccourci Ctrl+Shift+I dans _build_menu
old_menu = """        quit_action.triggered.connect(QApplication.instance().quit)
        file_menu.addAction(quit_action)"""
new_menu = """        quit_action.triggered.connect(QApplication.instance().quit)
        file_menu.addAction(quit_action)

        # Menu Outils — QSS Inspector
        tools_menu = menubar.addMenu("&Outils")
        inspect_action = QAction("QSS Inspector", self)
        inspect_action.setShortcut("Ctrl+Shift+I")
        inspect_action.setCheckable(True)
        inspect_action.toggled.connect(self._toggle_inspector)
        tools_menu.addAction(inspect_action)"""
if old_menu in text:
    text = text.replace(old_menu, new_menu, 1)
    changes += 1
    print("3. Menu Outils + raccourci Ctrl+Shift+I ajouté")
else:
    print("3. ATTENTION : old_menu introuvable!")

# 4. Ajouter la méthode _toggle_inspector et fermeture dans closeEvent
# Vérifier si _toggle_inspector existe déjà
if 'def _toggle_inspector' not in text:
    # Ajouter après le closeEvent
    old_close = """        self._connexion_manager.shutdown()
        super().closeEvent(event)

    # ── Méthodes privées ──────────────────────────────────"""
    new_close = """        if self._qss_inspector:
            self._qss_inspector.close()
        self._connexion_manager.shutdown()
        super().closeEvent(event)

    def _toggle_inspector(self, visible: bool) -> None:
        \"\"\"Affiche ou cache le QSS Inspector.\"\"\"
        if visible:
            self._qss_inspector.refresh()
            self._qss_inspector.show()
            self._qss_inspector.raise_()
        else:
            self._qss_inspector.hide()

    # ── Méthodes privées ──────────────────────────────────"""
    if old_close in text:
        text = text.replace(old_close, new_close, 1)
        changes += 1
        print("4. _toggle_inspector + fermeture closeEvent ajouté")
    else:
        print("4. ATTENTION : old_close introuvable!")
        # Debug
        for i, line in enumerate(text.splitlines()):
            if 'shutdown' in line:
                print(f"   -> Ligne {i+1}: {line!r}")
            if 'Méthodes privées' in line or 'M.thodes priv.es' in line:
                print(f"   -> Ligne {i+1}: {line!r}")

# 5. Ajouter l'import Qt pour DockWidget
if 'from PySide6.QtCore import' in text:
    # Remplacer l'import QtCore pour inclure Qt
    pass  # Qt est déjà importé via from PySide6.QtCore import Qt
elif 'from PySide6.QtCore import Qt' not in text:
    # Ajouter Qt dans l'import QtCore existant ou créer
    if 'from PySide6.QtCore import' not in text:
        print("5. ATTENTION: Qt déjà importé ou non trouvé")

# Vérifier que les imports PySide6 sont bons
if 'from PySide6.QtCore import Qt' not in text:
    # Chercher l'import QtCore
    for i, line in enumerate(text.splitlines()):
        if 'PySide6.QtCore' in line:
            print(f"   -> QtCore import ligne {i+1}: {line!r}")

f.write_text(text, encoding='utf-8')
print(f"\n✅ {changes} modifications appliquées")
