"""Tests pour le widget Téléchargements."""

from __future__ import annotations

from src.gui.widgets.telechargements import (
    DownloadRow,
    TelechargementsHeaderWidget,
    TelechargementsPage,
)


class TestTelechargementsHeaderWidget:
    """TelechargementsHeaderWidget : badge de compteurs dans le header."""

    def test_creer_widget(self, qapp) -> None:
        """Peut créer un TelechargementsHeaderWidget."""
        widget = TelechargementsHeaderWidget()
        assert widget is not None
        assert isinstance(widget, TelechargementsHeaderWidget)

    def test_object_name(self, qapp) -> None:
        """Le widget a le bon objectName."""
        widget = TelechargementsHeaderWidget()
        assert widget.objectName() == "telechargementsHeader"

    def test_set_counts_avec_valeurs(self, qapp) -> None:
        """set_counts() accepte des valeurs positives."""
        widget = TelechargementsHeaderWidget()
        # Ne doit pas planter
        widget.set_counts(en_cours=3, attente=5)

    def test_set_counts_zero(self, qapp) -> None:
        """set_counts() accepte zéro."""
        widget = TelechargementsHeaderWidget()
        widget.set_counts(en_cours=0, attente=0)

    def test_set_counts_grandes_valeurs(self, qapp) -> None:
        """set_counts() accepte de grands nombres."""
        widget = TelechargementsHeaderWidget()
        widget.set_counts(en_cours=999, attente=999)


class TestDownloadRow:
    """DownloadRow : ligne individuelle d'un téléchargement."""

    def test_creer_row(self, qapp) -> None:
        """Peut créer un DownloadRow avec les paramètres minimaux."""
        row = DownloadRow(identifiant="id001", fichier="fichier.mp3")
        assert row is not None
        assert isinstance(row, DownloadRow)

    def test_object_name(self, qapp) -> None:
        """La ligne a le bon objectName."""
        row = DownloadRow(identifiant="id001", fichier="fichier.mp3")
        assert row.objectName() == "downloadRow"

    def test_identifiant_property(self, qapp) -> None:
        """La propriété identifiant retourne l'ID."""
        row = DownloadRow(identifiant="abc123", fichier="test.mp3")
        assert row.identifiant == "abc123"

    def test_creer_avec_statut_attente(self, qapp) -> None:
        """Peut créer avec statut='attente'."""
        row = DownloadRow(
            identifiant="id002",
            fichier="fichier.flac",
            statut="attente",
        )
        assert row.identifiant == "id002"

    def test_creer_avec_statut_echoue(self, qapp) -> None:
        """Peut créer avec statut='echoue'."""
        row = DownloadRow(
            identifiant="id003",
            fichier="fichier.ogg",
            statut="echoue",
        )
        assert row.identifiant == "id003"

    def test_creer_avec_tous_parametres(self, qapp) -> None:
        """Peut créer avec tous les paramètres."""
        row = DownloadRow(
            identifiant="id004",
            fichier="fichier.wav",
            statut="en_cours",
            progression=50.0,
            vitesse="2.5 MB/s",
            taille="15 MB",
        )
        assert row.identifiant == "id004"

    def test_set_progression(self, qapp) -> None:
        """set_progression() met à jour la barre sans planter."""
        row = DownloadRow(identifiant="id005", fichier="test.mp3")
        row.set_progression(75.0)
        # La barre de progression interne est mise à jour
        assert row._progress.value() == 75

    def test_set_progression_zero(self, qapp) -> None:
        """set_progression(0) fonctionne."""
        row = DownloadRow(identifiant="id006", fichier="test.mp3")
        row.set_progression(0)
        assert row._progress.value() == 0

    def test_set_progression_cent(self, qapp) -> None:
        """set_progression(100) fonctionne."""
        row = DownloadRow(identifiant="id007", fichier="test.mp3")
        row.set_progression(100)
        assert row._progress.value() == 100


class TestTelechargementsPage:
    """TelechargementsPage : page listant tous les téléchargements."""

    def test_creer_page(self, qapp) -> None:
        """Peut créer un TelechargementsPage."""
        page = TelechargementsPage()
        assert page is not None
        assert isinstance(page, TelechargementsPage)

    def test_object_name(self, qapp) -> None:
        """La page a le bon objectName."""
        page = TelechargementsPage()
        assert page.objectName() == "telechargementsPage"

    def test_download_count_initial_zero(self, qapp) -> None:
        """Au départ, download_count() == 0."""
        page = TelechargementsPage()
        assert page.download_count() == 0

    def test_add_download_ajoute_un(self, qapp) -> None:
        """add_download() ajoute un téléchargement."""
        page = TelechargementsPage()
        page.add_download("id001", "fichier.mp3")
        assert page.download_count() == 1

    def test_add_download_plusieurs(self, qapp) -> None:
        """add_download() peut ajouter plusieurs éléments."""
        page = TelechargementsPage()
        page.add_download("id001", "a.mp3")
        page.add_download("id002", "b.flac")
        page.add_download("id003", "c.ogg")
        assert page.download_count() == 3

    def test_add_download_avec_details(self, qapp) -> None:
        """add_download() avec statut et progression."""
        page = TelechargementsPage()
        page.add_download(
            identifiant="id001",
            fichier="gros_fichier.flac",
            statut="en_cours",
            progression=42.0,
            vitesse="1.5 MB/s",
            taille="20 MB",
        )
        assert page.download_count() == 1

    def test_remove_download_existant(self, qapp) -> None:
        """remove_download() retourne True pour un ID existant."""
        page = TelechargementsPage()
        page.add_download("id001", "fichier.mp3")
        assert page.remove_download("id001") is True
        assert page.download_count() == 0

    def test_remove_download_inexistant(self, qapp) -> None:
        """remove_download() retourne False pour un ID inconnu."""
        page = TelechargementsPage()
        assert page.remove_download("IDONEXISTE") is False

    def test_update_progression(self, qapp) -> None:
        """update_progression() met à jour sans planter."""
        page = TelechargementsPage()
        page.add_download("id001", "fichier.mp3")
        # Ne doit pas planter
        page.update_progression("id001", 50.0)

    def test_update_progression_inexistant(self, qapp) -> None:
        """update_progression() sur un ID inconnu ne plante pas."""
        page = TelechargementsPage()
        page.update_progression("IDONEXISTE", 50.0)

    def test_change_statut(self, qapp) -> None:
        """change_statut() change le statut sans planter."""
        page = TelechargementsPage()
        page.add_download("id001", "fichier.mp3", statut="en_cours")
        page.change_statut("id001", "attente")

    def test_change_statut_inexistant(self, qapp) -> None:
        """change_statut() sur un ID inconnu ne plante pas."""
        page = TelechargementsPage()
        page.change_statut("IDONEXISTE", "echoue")

    def test_clear_all_vide_liste(self, qapp) -> None:
        """clear_all() supprime tous les téléchargements."""
        page = TelechargementsPage()
        page.add_download("id001", "a.mp3")
        page.add_download("id002", "b.flac")
        page.clear_all()
        assert page.download_count() == 0

    def test_clear_all_sans_elements(self, qapp) -> None:
        """clear_all() sur une liste vide ne plante pas."""
        page = TelechargementsPage()
        page.clear_all()
        assert page.download_count() == 0

    def test_add_puis_remove_plusieurs(self, qapp) -> None:
        """Ajout et suppression multiples."""
        page = TelechargementsPage()
        page.add_download("id001", "a.mp3")
        page.add_download("id002", "b.flac")
        page.add_download("id003", "c.ogg")
        page.remove_download("id002")
        assert page.download_count() == 2
        # Vérifie que les bons IDs restent
        assert "id001" in page._downloads
        assert "id003" in page._downloads
        assert "id002" not in page._downloads
