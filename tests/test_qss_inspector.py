"""Tests pour QSS Inspector — DevTool PySide6.

Couverture visée :
  - Fonctions module-level : _widget_label, _widget_path, _qss_errors
  - Classes internes : _PickFilter, _WidgetTree, _PropertyPanel
  - QssInspector avec main_window mocké
"""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock

import pytest
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QWidget

from src.gui.devtool.qss_inspector import (
    QssInspector,
    _PickFilter,
    _PropertyPanel,
    _WidgetTree,
    _widget_label,
    _widget_path,
    _qss_errors,
)


# ═══════════════════════════════════════════════════════════════════════════
#  Fonctions module-level (pas de qapp nécessaire)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.qt_heavy
class TestWidgetLabel:
    """_widget_label : génère ClassName[objectName]."""

    def test_object_name_present(self, qapp) -> None:
        """Avec objectName → ClassName[objectName]."""
        w = QLabel()
        w.setObjectName("mon_label")
        assert _widget_label(w) == "QLabel[mon_label]"

    def test_sans_object_name_avec_texte(self, qapp) -> None:
        """Sans objectName mais avec texte → ClassName('texte')."""
        w = QLabel("Hello World")
        assert _widget_label(w) == "QLabel('Hello World')"

    def test_texte_long_tronque(self, qapp) -> None:
        """Texte > 28 caractères → tronqué."""
        w = QLabel("A" * 50)
        assert len(_widget_label(w)) < 60  # ne contient pas les 50 A
        assert "AAA" in _widget_label(w)

    def test_sans_rien(self, qapp) -> None:
        """Sans objectName ni texte → juste ClassName."""
        w = QWidget()
        assert _widget_label(w) == "QWidget"


@pytest.mark.qt_heavy
class TestWidgetPath:
    """_widget_path : chemin hiérarchique."""

    def test_widget_seul(self, qapp) -> None:
        """Widget racine → juste son label."""
        w = QWidget()
        # Le parent est un QWidget de test
        path = _widget_path(w)
        assert "QWidget" in path

    def test_widget_avec_parent(self, qapp) -> None:
        """Widget avec parent → A → B."""
        parent = QWidget()
        child = QWidget(parent)
        parent.setObjectName("parent")
        child.setObjectName("child")
        path = _widget_path(child)
        assert "parent" in path
        assert "child" in path
        assert "→" in path


class TestQssErrors:
    """_qss_errors : valide les stylesheets QSS."""

    @staticmethod
    def test_pas_derreur_stylesheet_vide() -> None:
        """Stylesheet vide → aucune erreur."""
        assert _qss_errors("") == []

    @staticmethod
    def test_pas_derreur_stylesheet_valide() -> None:
        """Stylesheet valide → aucune erreur."""
        css = "QPushButton { color: red; background: blue; }"
        assert _qss_errors(css) == []

    @staticmethod
    def test_couleur_hex8_detectee() -> None:
        """#RRGGBBAA → erreur."""
        css = "QWidget { color: #ff000080; }"
        errs = _qss_errors(css)
        assert len(errs) == 1
        assert "8 chiffres" in errs[0]
        assert "#ff000080" in errs[0]

    @staticmethod
    def test_couleur_hex3_detectee() -> None:
        """#RGB → erreur."""
        css = "QWidget { color: #f00; }"
        errs = _qss_errors(css)
        assert len(errs) == 1
        assert "3 chiffres" in errs[0]
        assert "#f00" in errs[0]

    @staticmethod
    def test_accolades_desequilibrees() -> None:
        """Plus de { que de } → erreur."""
        css = "QWidget { color: red; "
        errs = _qss_errors(css)
        assert any("Accolades" in e for e in errs)

    @staticmethod
    def test_selecteur_vide() -> None:
        """Sélecteur vide { } → erreur."""
        css = "QWidget {  }"
        errs = _qss_errors(css)
        assert any("vide" in e for e in errs)

    @staticmethod
    def test_point_virgule_manquant() -> None:
        """Propriété sans ; en multiligne → erreur."""
        css = "QWidget {\n  color: red\n}"
        errs = _qss_errors(css)
        assert any("virgule" in e for e in errs)

    @staticmethod
    def test_hex8_et_hex3_et_accolades() -> None:
        """Plusieurs erreurs simultanées."""
        css = "QWidget { color: #f00; background: #ff000080; "
        errs = _qss_errors(css)
        assert len(errs) >= 3  # hex3 + hex8 + accolades

    @staticmethod
    def test_commentaire_ignore() -> None:
        """Les commentaires /* */ ne déclenchent pas d'erreur de ;."""
        css = "/* comment */ QWidget { color: red; }"
        assert _qss_errors(css) == []


# ═══════════════════════════════════════════════════════════════════════════
#  _PickFilter
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.qt_heavy
class TestPickFilter:
    """_PickFilter : filtre d'événements pour le mode pick."""

    def test_creer_filtre(self) -> None:
        """Création avec callback."""
        cb = MagicMock()
        pf = _PickFilter(cb)
        assert pf._on_pick is cb
        assert not pf._active

    def test_set_active(self) -> None:
        """set_active modifie l'état."""
        pf = _PickFilter(MagicMock())
        pf.set_active(True)
        assert pf._active
        pf.set_active(False)
        assert not pf._active

    def test_event_filter_inactif_retourne_false(self, qapp) -> None:
        """Quand inactif, event_filter retourne False."""
        pf = _PickFilter(MagicMock())
        w = QWidget()
        event = QMouseEvent(
            QEvent.MouseButtonPress, QPoint(0, 0), QPoint(0, 0),
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier,
        )
        assert not pf.event_filter(w, event)

    def test_event_filter_non_souris_retourne_false(self, qapp) -> None:
        """Événement non souris → False même si actif."""
        pf = _PickFilter(MagicMock())
        pf.set_active(True)
        # On crée un événement factice avec un type non-souris
        fake_event = MagicMock(spec=QEvent)
        fake_event.type.return_value = QEvent.KeyPress
        w = QWidget()
        assert not pf.event_filter(w, fake_event)


# ═══════════════════════════════════════════════════════════════════════════
#  _WidgetTree
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.qt_heavy
class TestWidgetTree:
    """_WidgetTree : arbre hiérarchique des widgets."""

    def test_creer_arbre(self, qapp) -> None:
        """Création avec en-têtes."""
        tree = _WidgetTree()
        assert tree.columnCount() == 2
        assert tree.headerItem().text(0) == "Widget"
        assert tree.headerItem().text(1) == "Classe"

    def test_rebuild_widget_unique(self, qapp) -> None:
        """Rebuild avec un widget racine."""
        tree = _WidgetTree()
        w = QWidget()
        w.setObjectName("root")
        tree.rebuild(w)
        assert tree.topLevelItemCount() == 1
        assert tree.topLevelItem(0).text(0) == "QWidget[root]"
        assert tree.topLevelItem(0).text(1) == "QWidget"

    def test_rebuild_avec_enfant(self, qapp) -> None:
        """Rebuild avec parent + enfant."""
        tree = _WidgetTree()
        parent = QWidget()
        child = QWidget(parent)
        tree.rebuild(parent)
        assert tree.topLevelItemCount() == 1
        # L'enfant doit être dans les enfants du nœud racine
        root_item = tree.topLevelItem(0)
        assert root_item.childCount() == 1
        assert root_item.child(0).text(1) == "QWidget"

    def test_select_widget(self, qapp) -> None:
        """select_widget sélectionne le bon nœud."""
        tree = _WidgetTree()
        w = QWidget()
        tree.rebuild(w)
        tree.select_widget(w)
        assert tree.currentItem() is not None
        assert tree.currentItem().text(0) == "QWidget"

    def test_select_widget_inconnu_ne_plante_pas(self, qapp) -> None:
        """select_widget avec un widget inconnu → pas d'erreur."""
        tree = _WidgetTree()
        tree.rebuild(QWidget())
        tree.select_widget(QWidget())
        # Pas d'assertion, juste vérifier que ça ne plante pas

    def test_on_select_callback(self, qapp) -> None:
        """Callback on_select déclenché au clic sur un item."""
        tree = _WidgetTree()
        cb = MagicMock()
        tree.on_select(cb)
        w = QWidget()
        tree.rebuild(w)
        # Simule un clic
        item = tree.topLevelItem(0)
        tree._on_item_clicked(item, 0)
        assert cb.called

    def test_set_search_filter_match(self, qapp) -> None:
        """Recherche trouve un widget par son nom."""
        tree = _WidgetTree()
        parent = QWidget()
        parent.setObjectName("parent")
        child = QWidget(parent)
        child.setObjectName("special_child")
        tree.rebuild(parent)
        tree.set_search_filter("special")
        # L'enfant n'est pas caché
        root_item = tree.topLevelItem(0)
        child_item = root_item.child(0)
        assert not child_item.isHidden()

    def test_set_search_filter_vide_affiche_tout(self, qapp) -> None:
        """Recherche vide → tout visible."""
        tree = _WidgetTree()
        tree.rebuild(QWidget())
        tree.set_search_filter("")
        root_item = tree.topLevelItem(0)
        assert not root_item.isHidden()

    def test_widget_item_map_apres_rebuild(self, qapp) -> None:
        """widget_item_map contient les widgets après rebuild."""
        tree = _WidgetTree()
        w = QWidget()
        tree.rebuild(w)
        assert id(w) in tree.widget_item_map
        assert tree.widget_item_map[id(w)].text(0) == "QWidget"

    def test_rebuild_reinitialise_map(self, qapp) -> None:
        """Rebuild efface l'ancienne map."""
        tree = _WidgetTree()
        w1 = QWidget()
        w1.setObjectName("first")
        tree.rebuild(w1)
        tree.rebuild(QWidget())
        assert id(w1) not in tree.widget_item_map


# ═══════════════════════════════════════════════════════════════════════════
#  _PropertyPanel
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.qt_heavy
class TestPropertyPanel:
    """_PropertyPanel : panneau de propriétés du widget sélectionné."""

    def test_creer_panneau(self, qapp) -> None:
        """Création avec tabs."""
        panel = _PropertyPanel()
        assert panel._tabs.count() == 3
        assert panel._tabs.tabText(0) == "Propriétés"
        assert panel._tabs.tabText(1) == "Stylesheet"
        assert panel._tabs.tabText(2) == "Validation"

    def test_inspect_widget_remplit_texte(self, qapp) -> None:
        """Inspect remplit le texte info avec les propriétés."""
        panel = _PropertyPanel()
        w = QWidget()
        w.setObjectName("test_widget")
        panel.inspect(w)
        text = panel._info_text.toPlainText()
        assert "QWidget" in text
        assert "test_widget" in text

    def test_inspect_widget_sans_stylesheet(self, qapp) -> None:
        """Sans stylesheet → message approprié."""
        panel = _PropertyPanel()
        w = QWidget()
        panel.inspect(w)
        assert "(aucun stylesheet" in panel._qss_text.toPlainText()

    def test_inspect_widget_avec_stylesheet(self, qapp) -> None:
        """Avec stylesheet local → affiché dans l'onglet."""
        panel = _PropertyPanel()
        w = QWidget()
        w.setStyleSheet("QWidget { color: red; }")
        panel.inspect(w)
        qss_text = panel._qss_text.toPlainText()
        assert "color: red" in qss_text

    def test_inspect_widget_valide_liste(self, qapp) -> None:
        """Validation montre les erreurs du stylesheet."""
        panel = _PropertyPanel()
        w = QWidget()
        w.setStyleSheet("QWidget { color: #f00; }")
        panel.inspect(w)
        assert panel._validation_list.count() >= 1  # header + erreur(s)

    def test_inspect_widget_pas_derreur(self, qapp) -> None:
        """Stylesheet valide → message de succès."""
        panel = _PropertyPanel()
        w = QWidget()
        w.setStyleSheet("QWidget { color: red; }")
        panel.inspect(w)
        found_ok = False
        for i in range(panel._validation_list.count()):
            item = panel._validation_list.item(i)
            if "Aucune erreur" in item.text():
                found_ok = True
                break
        assert found_ok

    def test_minimum_width(self, qapp) -> None:
        """Largeur minimale du panneau."""
        panel = _PropertyPanel()
        assert panel.minimumWidth() == 360


# ═══════════════════════════════════════════════════════════════════════════
#  QssInspector
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.qt_heavy
class TestQssInspector:
    """QssInspector avec main_window mocké."""

    @pytest.fixture(autouse=True)
    def _setup(self, mocker, qapp) -> None:
        """Patche les dépendances externes de QssInspector."""
        self.mock_main = MagicMock(spec=QWidget)
        self.mock_main.qss_warnings = PropertyMock(return_value=[])
        self.mock_main.qss_call_logs = PropertyMock(return_value=[])
        self.mock_main.findChildren = MagicMock(return_value=[])
        self.mock_main.isHidden = MagicMock(return_value=False)
        self.mock_main.show = MagicMock()
        self.mock_main.raise_ = MagicMock()

        # QssInspector dépend de widgets QT qui existent déjà (QApplication)
        self.inspector = QssInspector(self.mock_main)

    def test_creer_inspecteur(self) -> None:
        """Création avec les bons titres."""
        assert self.inspector.windowTitle() == "QSS Inspector"
        assert self.inspector.objectName() == "_qss_inspector"

    def test_contient_boutons(self) -> None:
        """Les boutons principaux sont présents."""
        assert self.inspector._refresh_btn is not None
        assert self.inspector._pick_btn is not None
        assert self.inspector._collapse_btn is not None
        assert self.inspector._scan_btn is not None
        assert self.inspector._warn_btn is not None
        assert self.inspector._search_bar is not None

    def test_refresh_appelle_rebuild(self) -> None:
        """refresh() reconstruit l'arbre et sélectionne main_window."""
        tree_mock = MagicMock()
        panel_mock = MagicMock()
        self.inspector._widget_tree = tree_mock
        self.inspector._property_panel = panel_mock

        self.inspector.refresh()

        tree_mock.rebuild.assert_called_once_with(self.mock_main)
        tree_mock.select_widget.assert_called_once_with(self.mock_main)
        # Vérifie que le panneau a bien inspecté le widget
        panel_mock.inspect.assert_called_once_with(self.mock_main)

    def test_inspect_widget_affiche_et_raise(self) -> None:
        """inspect_widget() sélectionne, montre et raise le dock."""
        w = MagicMock(spec=QWidget)
        tree_mock = MagicMock()
        panel_mock = MagicMock()
        self.inspector._widget_tree = tree_mock
        self.inspector._property_panel = panel_mock

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(self.inspector, "isHidden", lambda: True)
            mp.setattr(self.inspector, "show", MagicMock())
            mp.setattr(self.inspector, "raise_", MagicMock())
            self.inspector.inspect_widget(w)

        tree_mock.select_widget.assert_called_once_with(w)
        panel_mock.inspect.assert_called_once_with(w)

    def test_toggle_pick_mode_actif(self, qapp) -> None:
        """_toggle_pick_mode(True) active le filtre et change le curseur."""
        with pytest.MonkeyPatch().context() as mp:
            set_cursor = MagicMock()
            mp.setattr("PySide6.QtWidgets.QApplication.setOverrideCursor", set_cursor)

            self.inspector._toggle_pick_mode(True)

            assert self.inspector._pick_filter._active
            set_cursor.assert_called_once()

    def test_toggle_pick_mode_inactif(self, qapp) -> None:
        """_toggle_pick_mode(False) désactive le filtre et restaure le curseur."""
        with pytest.MonkeyPatch().context() as mp:
            restore = MagicMock()
            mp.setattr("PySide6.QtWidgets.QApplication.restoreOverrideCursor", restore)

            self.inspector._toggle_pick_mode(False)

            assert not self.inspector._pick_filter._active
            restore.assert_called_once()

    def test_on_pick(self) -> None:
        """_on_pick désactive le pick et inspecte le widget."""
        w = MagicMock(spec=QWidget)

        with pytest.MonkeyPatch().context() as mp:
            inspect = MagicMock()
            mp.setattr(self.inspector, "inspect_widget", inspect)

            self.inspector._on_pick(w)

            assert not self.inspector._pick_btn.isChecked()
            assert not self.inspector._pick_filter._active
            inspect.assert_called_once_with(w)

    def test_collapse_all(self) -> None:
        """_collapse_all réduit tous les nœuds."""
        child = MagicMock()
        child.childCount.return_value = 0

        root = MagicMock()
        root.childCount.return_value = 1
        root.child.return_value = child

        self.inspector._widget_tree = MagicMock()
        self.inspector._widget_tree.invisibleRootItem.return_value = root

        self.inspector._collapse_all()

        child.setExpanded.assert_called_once_with(False)

    def test_on_search(self) -> None:
        """_on_search délègue à _widget_tree.set_search_filter."""
        tree_mock = MagicMock()
        self.inspector._widget_tree = tree_mock

        self.inspector._on_search("test")
        tree_mock.set_search_filter.assert_called_once_with("test")

    def test_event_filter_non_mouse_passe_a_super(self) -> None:
        """Événement non souris → appel à super().eventFilter()."""
        with pytest.MonkeyPatch().context() as mp:
            super_filter = MagicMock(return_value=False)
            mp.setattr("PySide6.QtWidgets.QDockWidget.eventFilter", super_filter)

            fake_event = MagicMock(spec=QEvent)
            fake_event.type.return_value = QEvent.KeyPress

            result = self.inspector.eventFilter(self.mock_main, fake_event)
            assert not result

    def test_event_filter_mouse_pick_inactif(self) -> None:
        """Clic souris mais pick inactif → False."""
        with pytest.MonkeyPatch().context() as mp:
            super_filter = MagicMock(return_value=False)
            mp.setattr("PySide6.QtWidgets.QDockWidget.eventFilter", super_filter)

            self.inspector._pick_filter.set_active(False)

            mouse_event = MagicMock(spec=QEvent)
            mouse_event.type.return_value = QEvent.MouseButtonPress

            result = self.inspector.eventFilter(self.mock_main, mouse_event)
            assert not result
