"""Tests UI pour les widgets ClientsActifsHeader.

Couverture :
  - ClientsHeaderWidget  : affichage, set_counts(), signal clicked
  - ClientRow            : création, nom, statut, signaux d'action
  - ClientsActifsHeader  : add/remove/clear, stats, gestion compteurs
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
)

from src.gui.widgets.header.clients_actifs_header import (
    ClientRow,
    ClientsActifsHeader,
    ClientsHeaderWidget,
)

# ═════════════════════════════════════════════════════════════════
#  Fixtures
# ═════════════════════════════════════════════════════════════════


@pytest.fixture
def header_widget(qapp: QApplication) -> ClientsHeaderWidget:
    """Crée un ClientsHeaderWidget (bouton de la bannière)."""
    return ClientsHeaderWidget()


@pytest.fixture
def actifs_header(qapp: QApplication) -> ClientsActifsHeader:
    """Crée un ClientsActifsHeader (page centrale)."""
    return ClientsActifsHeader()


# ═════════════════════════════════════════════════════════════════
#  Tests — ClientsHeaderWidget (bouton de la bannière)
# ═════════════════════════════════════════════════════════════════


class TestClientsHeaderWidget:
    """Bouton cliquable affiché dans la bannière principale."""

    def test_creation(self, header_widget: ClientsHeaderWidget) -> None:
        """Le widget s'instancie avec les bons defaults."""
        assert header_widget.objectName() == "clientsHeader"
        assert header_widget.cursor().shape() == Qt.CursorShape.PointingHandCursor
        assert header_widget.frameShape() == QFrame.Shape.NoFrame

    def test_title_label_exists(self, header_widget: ClientsHeaderWidget) -> None:
        """Le titre '👥  Clients' est présent."""
        title = header_widget.findChild(QLabel, "clientsHeaderTitle")
        assert title is not None
        assert "Clients" in title.text()

    def test_statut_label_exists(self, header_widget: ClientsHeaderWidget) -> None:
        """Le label de statut est présent avec les valeurs par défaut."""
        statut = header_widget.findChild(QLabel, "clientsHeaderStatut")
        assert statut is not None
        assert "Actif : 0" in statut.text()
        assert "Joignable : 0" in statut.text()

    def test_set_counts_updates_label(self, header_widget: ClientsHeaderWidget) -> None:
        """set_counts() met à jour l'affichage des compteurs."""
        header_widget.set_counts(actifs=3, joignables=5)
        statut = header_widget.findChild(QLabel, "clientsHeaderStatut")
        assert statut is not None
        assert "Actif : 3" in statut.text()
        assert "Joignable : 5" in statut.text()

    def test_set_counts_zero(self, header_widget: ClientsHeaderWidget) -> None:
        """set_counts(0, 0) réinitialise les compteurs."""
        header_widget.set_counts(actifs=10, joignables=20)
        header_widget.set_counts(actifs=0, joignables=0)
        statut = header_widget.findChild(QLabel, "clientsHeaderStatut")
        assert statut is not None
        assert "Actif : 0" in statut.text()
        assert "Joignable : 0" in statut.text()

    def test_clicked_signal_emitted(self, header_widget: ClientsHeaderWidget) -> None:
        """Le signal clicked est émis."""
        received: list[bool] = []
        header_widget.clicked.connect(lambda: received.append(True))

        header_widget.clicked.emit()

        assert len(received) == 1
        assert received[0] is True

    def test_clicked_multiple(self, header_widget: ClientsHeaderWidget) -> None:
        """Plusieurs émissions du signal."""
        received: list[int] = []
        header_widget.clicked.connect(lambda: received.append(1))

        header_widget.clicked.emit()
        header_widget.clicked.emit()
        header_widget.clicked.emit()

        assert len(received) == 3


# ═════════════════════════════════════════════════════════════════
#  Tests — ClientRow (ligne individuelle)
# ═════════════════════════════════════════════════════════════════


class TestClientRow:
    """Ligne d'affichage d'un client Soulseek."""

    def test_creation_default(self, qapp: QApplication) -> None:
        """Création par défaut : actif=True, joignable=True."""
        row = ClientRow(nom="testuser")
        assert row.objectName() == "clientRow"
        assert row.nom == "testuser"

    def test_creation_inactif(self, qapp: QApplication) -> None:
        """Client inactif et non joignable."""
        row = ClientRow(nom="offline_user", actif=False, joignable=False)
        assert row.nom == "offline_user"

    def test_nom_property(self, qapp: QApplication) -> None:
        """La propriété nom retourne le nom du client."""
        row = ClientRow(nom="SoulSeeker42")
        assert row.nom == "SoulSeeker42"

    def test_name_label(self, qapp: QApplication) -> None:
        """Le nom est affiché dans un QLabel."""
        row = ClientRow(nom="Alice")
        name_label = row.findChild(QLabel, "clientRowName")
        assert name_label is not None
        assert name_label.text() == "Alice"

    def test_has_explorer_button(self, qapp: QApplication) -> None:
        """Le bouton 📁 Explorer est présent."""
        row = ClientRow(nom="test")
        btns = row.findChildren(QPushButton)
        assert any("Explorer" in btn.text() for btn in btns)

    def test_has_favoris_button(self, qapp: QApplication) -> None:
        """Le bouton ⭐ Favoris est présent."""
        row = ClientRow(nom="test")
        btns = row.findChildren(QPushButton)
        assert any("Favoris" in btn.text() for btn in btns)

    def test_has_bannir_button(self, qapp: QApplication) -> None:
        """Le bouton 🚫 Bannir est présent."""
        row = ClientRow(nom="test")
        btns = row.findChildren(QPushButton)
        assert any("Bannir" in btn.text() for btn in btns)

    def test_explorer_signal_emitted(self, qapp: QApplication) -> None:
        """Le clic sur Explorer émet explorer_requested avec le nom."""
        received: list[str] = []
        row = ClientRow(nom="target_user")
        row.explorer_requested.connect(lambda n: received.append(n))

        # Trouver et cliquer le bouton Explorer
        for btn in row.findChildren(QPushButton):
            if "Explorer" in btn.text():
                btn.click()
                break

        assert len(received) == 1
        assert received[0] == "target_user"

    def test_favoris_signal_emitted(self, qapp: QApplication) -> None:
        """Le clic sur Favoris émet favoris_requested avec le nom."""
        received: list[str] = []
        row = ClientRow(nom="fav_user")
        row.favoris_requested.connect(lambda n: received.append(n))

        for btn in row.findChildren(QPushButton):
            if "Favoris" in btn.text():
                btn.click()
                break

        assert len(received) == 1
        assert received[0] == "fav_user"

    def test_bannir_signal_emitted(self, qapp: QApplication) -> None:
        """Le clic sur Bannir émet bannir_requested avec le nom."""
        received: list[str] = []
        row = ClientRow(nom="bad_user")
        row.bannir_requested.connect(lambda n: received.append(n))

        for btn in row.findChildren(QPushButton):
            if "Bannir" in btn.text():
                btn.click()
                break

        assert len(received) == 1
        assert received[0] == "bad_user"

    def test_signaux_independants(self, qapp: QApplication) -> None:
        """Chaque signal n'est émis que par son propre bouton."""
        explorer: list[str] = []
        favoris: list[str] = []
        bannir: list[str] = []

        row = ClientRow(nom="multi_signal_user")
        row.explorer_requested.connect(lambda n: explorer.append(n))
        row.favoris_requested.connect(lambda n: favoris.append(n))
        row.bannir_requested.connect(lambda n: bannir.append(n))

        for btn in row.findChildren(QPushButton):
            if "Explorer" in btn.text():
                btn.click()
            elif "Favoris" in btn.text():
                btn.click()
            elif "Bannir" in btn.text():
                btn.click()

        assert len(explorer) == 1
        assert len(favoris) == 1
        assert len(bannir) == 1

    def test_led_actif_vert(self, qapp: QApplication) -> None:
        """Client actif → LED verte."""
        row = ClientRow(nom="actif", actif=True)
        leds = [w for w in row.findChildren(QLabel) if w.text() == "●"]
        assert len(leds) >= 1

    def test_led_inactif_gris(self, qapp: QApplication) -> None:
        """Client inactif → LED grise."""
        row = ClientRow(nom="inactif", actif=False, joignable=True)
        # Vérifie qu'on trouve un QLabel "Actif" ou "Inactif" et que c'est "Inactif"
        labels = [w for w in row.findChildren(QLabel) if w.text() in ("Actif", "Inactif")]
        assert any(label.text() == "Inactif" for label in labels)

    def test_label_actif_present(self, qapp: QApplication) -> None:
        """Client actif → label 'Actif'."""
        row = ClientRow(nom="user1", actif=True)
        labels = [w for w in row.findChildren(QLabel) if w.text() == "Actif"]
        assert len(labels) >= 1

    def test_label_joignable_present(self, qapp: QApplication) -> None:
        """Client joignable → label 'Joignable'."""
        row = ClientRow(nom="user1", joignable=True)
        labels = [w for w in row.findChildren(QLabel) if w.text() == "Joignable"]
        assert len(labels) >= 1

    def test_label_non_joignable(self, qapp: QApplication) -> None:
        """Client non joignable → label 'Non joignable'."""
        row = ClientRow(nom="user1", actif=True, joignable=False)
        labels = [w for w in row.findChildren(QLabel) if w.text() == "Non joignable"]
        assert len(labels) >= 1

    def test_buttons_have_pointing_cursor(self, qapp: QApplication) -> None:
        """Les boutons d'action ont le curseur PointingHand."""
        row = ClientRow(nom="user")
        for btn in row.findChildren(QPushButton):
            assert btn.cursor().shape() == Qt.CursorShape.PointingHandCursor


# ═════════════════════════════════════════════════════════════════
#  Tests — ClientsActifsHeader (page centrale)
# ═════════════════════════════════════════════════════════════════


class TestClientsActifsHeader:
    """Page listant tous les clients actifs/joignables."""

    def test_creation(self, actifs_header: ClientsActifsHeader) -> None:
        """Le widget s'instancie correctement."""
        assert actifs_header.objectName() == "clientsActifsPage"
        assert actifs_header.client_count() == 0

    def test_has_header_title(self, actifs_header: ClientsActifsHeader) -> None:
        """Le titre 'Clients actifs et joignables' est présent."""
        # Cherche un QLabel avec ce texte
        found = False
        for w in actifs_header.findChildren(QLabel):
            if "Clients actifs" in w.text():
                found = True
                break
        assert found

    def test_has_stats_label(self, actifs_header: ClientsActifsHeader) -> None:
        """Le label des stats est présent avec l'objectName 'clientsStats'."""
        stats = actifs_header.findChild(QLabel, "clientsStats")
        assert stats is not None
        assert "Actif : 0" in stats.text()

    def test_has_scroll_area(self, actifs_header: ClientsActifsHeader) -> None:
        """Le widget contient une QScrollArea."""
        scroll = actifs_header.findChild(QScrollArea, "clientsScroll")
        assert scroll is not None
        assert scroll.widgetResizable() is True
        assert scroll.frameShape() == QFrame.Shape.NoFrame

    def test_add_client(self, actifs_header: ClientsActifsHeader) -> None:
        """add_client() ajoute un client et incrémente le compteur."""
        actifs_header.add_client("Alice")
        assert actifs_header.client_count() == 1

    def test_add_client_stats_actif(self, actifs_header: ClientsActifsHeader) -> None:
        """Ajout d'un client actif → stats mises à jour."""
        actifs_header.add_client("Alice", actif=True, joignable=False)
        stats = actifs_header.findChild(QLabel, "clientsStats")
        assert stats is not None
        assert "Actif : 1" in stats.text()
        assert "Joignable : 0" in stats.text()

    def test_add_client_stats_joignable(self, actifs_header: ClientsActifsHeader) -> None:
        """Ajout d'un client joignable → stats mises à jour."""
        actifs_header.add_client("Bob", actif=False, joignable=True)
        stats = actifs_header.findChild(QLabel, "clientsStats")
        assert stats is not None
        assert "Actif : 0" in stats.text()
        assert "Joignable : 1" in stats.text()

    def test_add_client_stats_both(self, actifs_header: ClientsActifsHeader) -> None:
        """Ajout d'un client actif ET joignable."""
        actifs_header.add_client("Charlie", actif=True, joignable=True)
        stats = actifs_header.findChild(QLabel, "clientsStats")
        assert stats is not None
        assert "Actif : 1" in stats.text()
        assert "Joignable : 1" in stats.text()

    def test_add_multiple_clients(self, actifs_header: ClientsActifsHeader) -> None:
        """Ajout de plusieurs clients."""
        for name in ["Alice", "Bob", "Charlie"]:
            actifs_header.add_client(name)
        assert actifs_header.client_count() == 3

    def test_remove_client(self, actifs_header: ClientsActifsHeader) -> None:
        """remove_client() supprime un client existant et retourne True."""
        actifs_header.add_client("Alice")
        result = actifs_header.remove_client("Alice")
        assert result is True
        assert actifs_header.client_count() == 0

    def test_remove_nonexistent(self, actifs_header: ClientsActifsHeader) -> None:
        """remove_client() retourne False si le client n'existe pas."""
        result = actifs_header.remove_client("ghost")
        assert result is False

    def test_remove_updates_stats(self, actifs_header: ClientsActifsHeader) -> None:
        """La suppression d'un client actif décrémente le compteur."""
        actifs_header.add_client("Alice", actif=True, joignable=True)
        actifs_header.add_client("Bob", actif=False, joignable=True)
        actifs_header.remove_client("Alice")

        stats = actifs_header.findChild(QLabel, "clientsStats")
        assert stats is not None
        assert "Actif : 0" in stats.text()  # seul Alice était actif
        assert "Joignable : 1" in stats.text()  # Bob est encore joignable

    def test_remove_reduit_total(self, actifs_header: ClientsActifsHeader) -> None:
        """La suppression réduit le total dans les stats."""
        actifs_header.add_client("Alice")
        actifs_header.add_client("Bob")
        actifs_header.remove_client("Alice")

        stats = actifs_header.findChild(QLabel, "clientsStats")
        assert stats is not None
        assert "Total : 1" in stats.text()

    def test_clear_clients_vide_liste(self, actifs_header: ClientsActifsHeader) -> None:
        """clear_clients() supprime tous les clients."""
        for name in ["A", "B", "C"]:
            actifs_header.add_client(name)
        actifs_header.clear_clients()
        assert actifs_header.client_count() == 0

    def test_clear_clients_reinitialise_stats(self, actifs_header: ClientsActifsHeader) -> None:
        """clear_clients() remet les compteurs à zéro."""
        actifs_header.add_client("Alice", actif=True, joignable=True)
        actifs_header.add_client("Bob", actif=True, joignable=False)
        actifs_header.clear_clients()

        stats = actifs_header.findChild(QLabel, "clientsStats")
        assert stats is not None
        assert "Actif : 0" in stats.text()
        assert "Joignable : 0" in stats.text()
        assert "Total : 0" in stats.text()

    def test_clear_clients_idempotent(self, actifs_header: ClientsActifsHeader) -> None:
        """clear_clients() sur une liste vide ne crash pas."""
        actifs_header.clear_clients()  # ne doit pas lever d'exception
        assert actifs_header.client_count() == 0

    def test_remove_preserve_autres(self, actifs_header: ClientsActifsHeader) -> None:
        """La suppression d'un client ne supprime pas les autres."""
        actifs_header.add_client("Alice")
        actifs_header.add_client("Bob")
        actifs_header.add_client("Charlie")

        actifs_header.remove_client("Bob")
        assert actifs_header.client_count() == 2

        # Vérifie que les noms des lignes restantes sont corrects
        noms_restants = [row.nom for row in actifs_header._rows]
        assert "Alice" in noms_restants
        assert "Charlie" in noms_restants
        assert "Bob" not in noms_restants

    def test_stats_after_multiple_ops(self, actifs_header: ClientsActifsHeader) -> None:
        """Opérations multiples : add + remove + clear."""
        actifs_header.add_client("A", actif=True, joignable=False)
        actifs_header.add_client("B", actif=False, joignable=True)
        actifs_header.add_client("C", actif=True, joignable=True)

        stats = actifs_header.findChild(QLabel, "clientsStats")
        assert stats is not None
        assert "Actif : 2" in stats.text()
        assert "Joignable : 2" in stats.text()
        assert "Total : 3" in stats.text()

        actifs_header.remove_client("A")
        stats = actifs_header.findChild(QLabel, "clientsStats")
        assert stats is not None
        assert "Actif : 1" in stats.text()
        assert "Joignable : 2" in stats.text()

        actifs_header.clear_clients()
        stats = actifs_header.findChild(QLabel, "clientsStats")
        assert stats is not None
        assert "Actif : 0" in stats.text()
        assert "Joignable : 0" in stats.text()

    def test_rows_are_client_row_instances(self, actifs_header: ClientsActifsHeader) -> None:
        """Les lignes ajoutées sont des ClientRow."""
        actifs_header.add_client("Alice")
        rows = actifs_header.findChildren(ClientRow)
        assert len(rows) == 1
        assert rows[0].nom == "Alice"

    def test_add_client_avec_meme_nom(self, actifs_header: ClientsActifsHeader) -> None:
        """Ajout de deux clients avec le même nom (pas d'unicité garantie)."""
        actifs_header.add_client("dup")
        actifs_header.add_client("dup")
        assert actifs_header.client_count() == 2
