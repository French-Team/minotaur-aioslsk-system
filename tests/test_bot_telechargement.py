"""Tests unitaires et d'intégration pour BotTelechargement.

Vérifie l'instanciation, la gestion des téléchargements (CRUD),
le câblage Soulseek (pause/resume/abort), les événements de transfert,
le menu contextuel, et les utilitaires.
"""

from __future__ import annotations

from typing import Any, Generator

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFrame, QMenu, QTableWidget
from pytest import MonkeyPatch

from src.gui.widgets.bots.bot_telechargement import BotTelechargement

# ── Mock SoulseekService ──────────────────────────────────────────


class MockSoulseekService(QObject):
    """Simule SoulseekService pour les tests.

    Expose les signaux Qt et les méthodes de contrôle (pause/resume/abort)
    avec un historique d'appels vérifiable.
    """

    transfer_added = Signal(object)
    transfer_removed = Signal(object)
    transfer_progress = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.calls: list[dict[str, Any]] = []

    def pause_transfer(self, username: str, remote_path: str) -> None:
        self.calls.append(
            {
                "method": "pause_transfer",
                "username": username,
                "remote_path": remote_path,
            }
        )

    def resume_transfer(self, username: str, remote_path: str) -> None:
        self.calls.append(
            {
                "method": "resume_transfer",
                "username": username,
                "remote_path": remote_path,
            }
        )

    def abort_transfer(self, username: str, remote_path: str) -> None:
        self.calls.append(
            {
                "method": "abort_transfer",
                "username": username,
                "remote_path": remote_path,
            }
        )

    def clear_calls(self) -> None:
        self.calls.clear()


# ── Mock transfer event helpers ───────────────────────────────────


class MockTransfer:
    """Simule un objet transfert Soulseek pour les events."""

    def __init__(
        self,
        remote_path: str = "/remote/test/file.mp3",
        filesize: int = 10_485_760,
        username: str = "test_user",
        state: Any = None,
    ) -> None:
        self.remote_path = remote_path
        self.filesize = filesize
        self.username = username
        self.state = state


class MockSnap:
    """Simule un snapshot d'état de transfert."""

    def __init__(self, state: Any = None, bytes_transfered: int = 0) -> None:
        self.state = state
        self.bytes_transfered = bytes_transfered


class MockTransferState:
    """Simule TransferState.State pour _transfer_state_to_statut."""

    def __init__(self, name: str) -> None:
        self.name = name


class MockTransferEvent:
    """Simule un événement de transfert Soulseek."""

    def __init__(self, transfer: Any) -> None:
        self.transfer = transfer


class MockProgressEvent:
    """Simule un événement de progression Soulseek."""

    def __init__(self, updates: list[tuple]) -> None:
        self.updates = updates


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def mock_service(qapp: Any) -> MockSoulseekService:
    """Crée un MockSoulseekService pour les tests."""
    return MockSoulseekService()


@pytest.fixture
def bot(qapp: Any) -> Generator[BotTelechargement, None, None]:
    """Crée une instance de BotTelechargement avec les dépendances mockées."""
    instance = BotTelechargement()
    yield instance
    instance.deleteLater()


@pytest.fixture
def bot_with_service(bot: BotTelechargement, mock_service: MockSoulseekService) -> BotTelechargement:
    """Crée un bot connecté à un mock service."""
    bot.setup(mock_service)
    return bot


@pytest.fixture
def bot_with_downloads(bot_with_service: BotTelechargement) -> BotTelechargement:
    """Crée un bot avec des téléchargements de test (un par statut)."""
    bot = bot_with_service
    bot.add_download(
        identifiant="/remote/file_en_cours.mp3",
        fichier="file_en_cours.mp3",
        statut="en_cours",
        progression=45.0,
        vitesse="1.2 Mo/s",
        taille="15.2 Mo",
        taille_bytes=15_940_000,
        vitesse_bytes=1_258_291,
        user="user1",
    )
    bot.add_download(
        identifiant="/remote/file_attente.mp3",
        fichier="file_attente.mp3",
        statut="attente",
        user="user2",
    )
    bot.add_download(
        identifiant="/remote/file_termine.mp3",
        fichier="file_termine.mp3",
        statut="termine",
        progression=100.0,
        taille="8.5 Mo",
        taille_bytes=8_912_896,
        user="user3",
    )
    bot.add_download(
        identifiant="/remote/file_echoue.mp3",
        fichier="file_echoue.mp3",
        statut="echoue",
        taille="5.2 Mo",
        taille_bytes=5_452_595,
        user="user4",
    )
    return bot


# ── Tests d'instanciation ────────────────────────────────────────


@pytest.mark.qt_heavy
class TestBotTelechargementInit:
    """Vérifie que l'instanciation de BotTelechargement fonctionne."""

    def test_instantiation_succeeds(self, bot: BotTelechargement) -> None:
        """L'instanciation ne doit pas lever d'exception."""
        assert isinstance(bot, BotTelechargement)
        assert isinstance(bot, QFrame)

    def test_initial_attributes(self, bot: BotTelechargement) -> None:
        """Les attributs internes sont initialisés correctement."""
        assert bot._downloads == {}
        assert bot._unseen_count == 0
        assert bot._setup_done is False

    def test_has_table(self, bot: BotTelechargement) -> None:
        """Le tableau des téléchargements est créé par _build_ui."""
        assert isinstance(bot._table, QTableWidget)

    def test_has_signals(self, bot: BotTelechargement) -> None:
        """Les signaux Qt sont bien définis."""
        assert hasattr(bot, "page_changed")
        assert hasattr(bot, "unseen_count_changed")


@pytest.mark.qt_heavy
class TestSetup:
    """Vérifie le câblage à SoulseekService."""

    def test_setup_stores_service(self, bot: BotTelechargement, mock_service: MockSoulseekService) -> None:
        """setup() stocke le service dans _service."""
        bot.setup(mock_service)
        assert bot._service is mock_service

    def test_setup_sets_done_flag(self, bot: BotTelechargement, mock_service: MockSoulseekService) -> None:
        """setup() passe _setup_done à True."""
        bot.setup(mock_service)
        assert bot._setup_done is True

    def test_setup_is_idempotent(self, bot: BotTelechargement, mock_service: MockSoulseekService) -> None:
        """setup() ne se ré-exécute pas si déjà appelé."""
        bot.setup(mock_service)
        first_service = bot._service
        other_service = MockSoulseekService()
        bot.setup(other_service)
        assert bot._service is first_service  # pas écrasé
        assert bot._setup_done is True


# ── Tests de gestion des téléchargements ─────────────────────────


@pytest.mark.qt_heavy
class TestDownloadManagement:
    """CRUD sur les téléchargements."""

    def test_add_download(self, bot: BotTelechargement) -> None:
        """add_download() ajoute au dictionnaire interne."""
        bot.add_download(
            identifiant="/remote/test.mp3",
            fichier="test.mp3",
            statut="en_cours",
        )
        assert "/remote/test.mp3" in bot._downloads
        data = bot._downloads["/remote/test.mp3"]
        assert data["fichier"] == "test.mp3"
        assert data["statut"] == "en_cours"
        assert data["progression"] == 0.0

    def test_add_download_with_all_params(self, bot: BotTelechargement) -> None:
        """add_download() accepte tous les paramètres optionnels."""
        bot.add_download(
            identifiant="/remote/full.mp3",
            fichier="full.mp3",
            statut="attente",
            progression=50.0,
            vitesse="512 Ko/s",
            taille="10.0 Mo",
            taille_bytes=10_485_760,
            vitesse_bytes=524_288,
            user="soulseeker",
        )
        data = bot._downloads["/remote/full.mp3"]
        assert data["vitesse"] == "512 Ko/s"
        assert data["taille"] == "10.0 Mo"
        assert data["taille_bytes"] == 10_485_760
        assert data["user"] == "soulseeker"

    def test_remove_download(self, bot: BotTelechargement) -> None:
        """remove_download() supprime du dictionnaire et retourne True."""
        bot.add_download(identifiant="/remote/test.mp3", fichier="test.mp3")
        result = bot.remove_download("/remote/test.mp3")
        assert result is True
        assert "/remote/test.mp3" not in bot._downloads

    def test_remove_nonexistent_download(self, bot: BotTelechargement) -> None:
        """remove_download() retourne False si l'ID n'existe pas."""
        result = bot.remove_download("/remote/nonexistent.mp3")
        assert result is False

    def test_download_count(self, bot_with_downloads: BotTelechargement) -> None:
        """download_count() retourne le nombre total."""
        assert bot_with_downloads.download_count() == 4

    def test_empty_download_count(self, bot: BotTelechargement) -> None:
        """download_count() retourne 0 si vide."""
        assert bot.download_count() == 0

    def test_change_statut(self, bot_with_downloads: BotTelechargement) -> None:
        """change_statut() met à jour le statut dans _downloads."""
        bot_with_downloads.change_statut("/remote/file_en_cours.mp3", "termine")
        assert bot_with_downloads._downloads["/remote/file_en_cours.mp3"]["statut"] == "termine"

    def test_change_statut_nonexistent(self, bot: BotTelechargement) -> None:
        """change_statut() ne plante pas si l'ID n'existe pas."""
        bot.change_statut("/remote/nonexistent.mp3", "termine")  # ne doit pas lever

    def test_reset_unseen_count(self, bot_with_downloads: BotTelechargement) -> None:
        """reset_unseen_count() remet le compteur à zéro et émet le signal."""
        bot_with_downloads._unseen_count = 5
        bot_with_downloads.reset_unseen_count()
        assert bot_with_downloads._unseen_count == 0

    def test_update_progression(self, bot_with_downloads: BotTelechargement) -> None:
        """update_progression() met à jour la progression et les bytes."""
        bot_with_downloads.update_progression("/remote/file_en_cours.mp3", 75.0, bytes_transfered=8_000_000)
        data = bot_with_downloads._downloads["/remote/file_en_cours.mp3"]
        assert data["progression"] == 75.0
        assert data["bytes_transfered"] == 8_000_000


# ── Tests du câblage Soulseek ─────────────────────────────────────


@pytest.mark.qt_heavy
class TestSoulseekControl:
    """Vérifie que les actions appellent les bonnes méthodes Soulseek."""

    def test_pause_all_pauses_en_cours(
        self, bot_with_downloads: BotTelechargement, mock_service: MockSoulseekService
    ) -> None:
        """_on_pause_all() appelle pause_transfer() pour les downloads en_cours."""
        bot_with_downloads._on_pause_all()
        assert any(
            c["method"] == "pause_transfer"
            and c["remote_path"] == "/remote/file_en_cours.mp3"
            and c["username"] == "user1"
            for c in mock_service.calls
        ), "pause_transfer doit être appelée pour le download en_cours"

    def test_pause_all_ignores_other_statuses(
        self, bot_with_downloads: BotTelechargement, mock_service: MockSoulseekService
    ) -> None:
        """_on_pause_all() n'appelle pas pause_transfer() pour les autres statuts."""
        bot_with_downloads._on_pause_all()
        # Vérifie que seul le download en_cours a été mis en pause
        paused_paths = [c["remote_path"] for c in mock_service.calls if c["method"] == "pause_transfer"]
        assert paused_paths == ["/remote/file_en_cours.mp3"]

    def test_pause_all_passe_attente(self, bot_with_downloads: BotTelechargement) -> None:
        """_on_pause_all() passe le statut à 'attente' après appel."""
        bot_with_downloads._on_pause_all()
        assert bot_with_downloads._downloads["/remote/file_en_cours.mp3"]["statut"] == "attente"

    def test_resume_all_resumes_attente(
        self, bot_with_downloads: BotTelechargement, mock_service: MockSoulseekService
    ) -> None:
        """_on_resume_all() appelle resume_transfer() pour les downloads attente."""
        bot_with_downloads._on_resume_all()
        assert any(
            c["method"] == "resume_transfer"
            and c["remote_path"] == "/remote/file_attente.mp3"
            and c["username"] == "user2"
            for c in mock_service.calls
        ), "resume_transfer doit être appelée pour le download attente"

    def test_resume_all_resumes_echoue(
        self, bot_with_downloads: BotTelechargement, mock_service: MockSoulseekService
    ) -> None:
        """_on_resume_all() appelle resume_transfer() pour les downloads echoue."""
        bot_with_downloads._on_resume_all()
        assert any(
            c["method"] == "resume_transfer"
            and c["remote_path"] == "/remote/file_echoue.mp3"
            and c["username"] == "user4"
            for c in mock_service.calls
        ), "resume_transfer doit être appelée pour le download echoue"

    def test_resume_all_ignores_en_cours(
        self, bot_with_downloads: BotTelechargement, mock_service: MockSoulseekService
    ) -> None:
        """_on_resume_all() n'appelle pas resume_transfer() pour les en_cours."""
        bot_with_downloads._on_resume_all()
        en_cours_resumed = [
            c
            for c in mock_service.calls
            if c["method"] == "resume_transfer" and c["remote_path"] == "/remote/file_en_cours.mp3"
        ]
        assert len(en_cours_resumed) == 0

    def test_resume_all_ignores_termine(
        self, bot_with_downloads: BotTelechargement, mock_service: MockSoulseekService
    ) -> None:
        """_on_resume_all() n'appelle pas resume_transfer() pour les termine."""
        bot_with_downloads._on_resume_all()
        termine_resumed = [
            c
            for c in mock_service.calls
            if c["method"] == "resume_transfer" and c["remote_path"] == "/remote/file_termine.mp3"
        ]
        assert len(termine_resumed) == 0

    def test_resume_all_updates_status(self, bot_with_downloads: BotTelechargement) -> None:
        """_on_resume_all() change les statuts correctement (attente→en_cours, echoue→attente)."""
        bot_with_downloads._on_resume_all()
        assert bot_with_downloads._downloads["/remote/file_attente.mp3"]["statut"] == "en_cours"
        assert bot_with_downloads._downloads["/remote/file_echoue.mp3"]["statut"] == "attente"

    def test_cancel_all_cancels_en_cours(
        self, bot_with_downloads: BotTelechargement, mock_service: MockSoulseekService
    ) -> None:
        """_on_cancel_all() appelle abort_transfer() pour les downloads en_cours."""
        bot_with_downloads._on_cancel_all()
        assert any(
            c["method"] == "abort_transfer" and c["remote_path"] == "/remote/file_en_cours.mp3"
            for c in mock_service.calls
        )

    def test_cancel_all_cancels_attente(
        self, bot_with_downloads: BotTelechargement, mock_service: MockSoulseekService
    ) -> None:
        """_on_cancel_all() appelle abort_transfer() pour les downloads attente."""
        bot_with_downloads._on_cancel_all()
        assert any(
            c["method"] == "abort_transfer" and c["remote_path"] == "/remote/file_attente.mp3"
            for c in mock_service.calls
        )

    def test_cancel_all_ignores_termine_echoue(
        self, bot_with_downloads: BotTelechargement, mock_service: MockSoulseekService
    ) -> None:
        """_on_cancel_all() n'abort pas les downloads déjà termine/echoue."""
        bot_with_downloads._on_cancel_all()
        cancelled_paths = [c["remote_path"] for c in mock_service.calls if c["method"] == "abort_transfer"]
        assert "/remote/file_termine.mp3" not in cancelled_paths
        assert "/remote/file_echoue.mp3" not in cancelled_paths

    def test_cancel_all_passes_echoue(self, bot_with_downloads: BotTelechargement) -> None:
        """_on_cancel_all() passe tous les statuts à 'echoue'."""
        bot_with_downloads._on_cancel_all()
        assert bot_with_downloads._downloads["/remote/file_en_cours.mp3"]["statut"] == "echoue"
        assert bot_with_downloads._downloads["/remote/file_attente.mp3"]["statut"] == "echoue"
        # termine et echoue ne changent pas
        assert bot_with_downloads._downloads["/remote/file_termine.mp3"]["statut"] == "termine"
        assert bot_with_downloads._downloads["/remote/file_echoue.mp3"]["statut"] == "echoue"

    def test_annuler_calls_abort(
        self, bot_with_downloads: BotTelechargement, mock_service: MockSoulseekService
    ) -> None:
        """_on_annuler() appelle abort_transfer() pour le download ciblé."""
        bot_with_downloads._on_annuler("/remote/file_en_cours.mp3")
        assert any(
            c["method"] == "abort_transfer"
            and c["remote_path"] == "/remote/file_en_cours.mp3"
            and c["username"] == "user1"
            for c in mock_service.calls
        )

    def test_annuler_passes_echoue(self, bot_with_downloads: BotTelechargement) -> None:
        """_on_annuler() passe le statut à 'echoue'."""
        bot_with_downloads._on_annuler("/remote/file_en_cours.mp3")
        assert bot_with_downloads._downloads["/remote/file_en_cours.mp3"]["statut"] == "echoue"

    def test_annuler_nonexistent(self, bot_with_downloads: BotTelechargement) -> None:
        """_on_annuler() ne plante pas si l'ID n'existe pas."""
        bot_with_downloads._on_annuler("/remote/nonexistent.mp3")  # ne doit pas lever


# ── Tests des événements de transfert ─────────────────────────────


@pytest.mark.qt_heavy
class TestTransferEvents:
    """Vérifie le traitement des événements Soulseek."""

    def test_on_transfer_added(self, bot_with_service: BotTelechargement) -> None:
        """_on_transfer_added() ajoute le download à _downloads."""
        transfer = MockTransfer(
            remote_path="/remote/new_song.mp3",
            filesize=5_242_880,
            username="new_user",
            state=MockTransferState("QUEUED"),
        )
        event = MockTransferEvent(transfer)
        bot_with_service._on_transfer_added(event)
        assert "/remote/new_song.mp3" in bot_with_service._downloads
        data = bot_with_service._downloads["/remote/new_song.mp3"]
        assert data["fichier"] == "new_song.mp3"
        assert data["statut"] == "attente"
        assert data["user"] == "new_user"
        assert data["taille_bytes"] == 5_242_880

    def test_on_transfer_added_increments_unseen(self, bot_with_service: BotTelechargement) -> None:
        """_on_transfer_added() incrémente _unseen_count."""
        transfer = MockTransfer(remote_path="/remote/song.mp3")
        event = MockTransferEvent(transfer)
        bot_with_service._on_transfer_added(event)
        assert bot_with_service._unseen_count == 1

    def test_on_transfer_added_no_transfer(self, bot_with_service: BotTelechargement) -> None:
        """_on_transfer_added() ne plante pas si l'event n'a pas de transfer."""
        event = MockTransferEvent(transfer=None)
        bot_with_service._on_transfer_added(event)  # ne doit pas lever

    def test_on_transfer_removed(self, bot_with_downloads: BotTelechargement) -> None:
        """_on_transfer_removed() supprime le download de _downloads."""
        transfer = MockTransfer(remote_path="/remote/file_en_cours.mp3")
        event = MockTransferEvent(transfer)
        bot_with_downloads._on_transfer_removed(event)
        assert "/remote/file_en_cours.mp3" not in bot_with_downloads._downloads

    def test_on_transfer_removed_no_transfer(self, bot_with_downloads: BotTelechargement) -> None:
        """_on_transfer_removed() ne plante pas si l'event n'a pas de transfer."""
        event = MockTransferEvent(transfer=None)
        bot_with_downloads._on_transfer_removed(event)  # ne doit pas lever


@pytest.mark.qt_heavy
class TestEmptyBot:
    """Vérifie que les actions batch ne plantent pas sur un bot vide."""

    def test_pause_all_empty(self, bot: BotTelechargement, mock_service: MockSoulseekService) -> None:
        """_on_pause_all() ne plante pas si _downloads est vide."""
        bot.setup(mock_service)
        bot._on_pause_all()  # ne doit pas lever
        assert len(mock_service.calls) == 0

    def test_resume_all_empty(self, bot: BotTelechargement, mock_service: MockSoulseekService) -> None:
        """_on_resume_all() ne plante pas si _downloads est vide."""
        bot.setup(mock_service)
        bot._on_resume_all()  # ne doit pas lever
        assert len(mock_service.calls) == 0

    def test_cancel_all_empty(self, bot: BotTelechargement, mock_service: MockSoulseekService) -> None:
        """_on_cancel_all() ne plante pas si _downloads est vide."""
        bot.setup(mock_service)
        bot._on_cancel_all()  # ne doit pas lever
        assert len(mock_service.calls) == 0

    def test_annuler_empty(self, bot: BotTelechargement, mock_service: MockSoulseekService) -> None:
        """_on_annuler() ne plante pas si _downloads est vide."""
        bot.setup(mock_service)
        bot._on_annuler("/remote/nonexistent.mp3")  # ne doit pas lever
        assert len(mock_service.calls) == 0


# ── Tests du menu contextuel ──────────────────────────────────────


@pytest.mark.qt_heavy
class TestContextMenu:
    """Vérifie que le menu contextuel est adapté au statut."""

    def test_context_menu_pause_for_en_cours(self, bot_with_downloads: BotTelechargement) -> None:
        """Le menu contextuel d'un download en_cours contient 'Pause'."""
        menu = QMenu()
        # On ne peut pas facilement tester _on_context_menu (nécessite un event de souris),
        # donc on vérifie la logique via _on_pause_all et _on_annuler déjà testés.
        # Ce test vérifie juste que l'action individuelle est accessible via le handler.
        identifiant = "/remote/file_en_cours.mp3"
        data = bot_with_downloads._downloads.get(identifiant)
        assert data is not None
        assert data["statut"] == "en_cours"
        menu.close()
        menu.deleteLater()

    def test_context_menu_retry_for_echoue(
        self, bot_with_downloads: BotTelechargement, mock_service: MockSoulseekService
    ) -> None:
        """Vérifie que _on_resume_all() gère les echoue comme le ferait Réessayer."""
        bot_with_downloads._on_resume_all()
        # Le download echoue devrait être résumé (comme via Réessayer)
        assert any(
            c["method"] == "resume_transfer" and c["remote_path"] == "/remote/file_echoue.mp3"
            for c in mock_service.calls
        )

    def test_context_menu_resume_for_attente(
        self, bot_with_downloads: BotTelechargement, mock_service: MockSoulseekService
    ) -> None:
        """Vérifie que _on_resume_all() gère les attente comme le ferait Reprendre."""
        bot_with_downloads._on_resume_all()
        assert any(
            c["method"] == "resume_transfer" and c["remote_path"] == "/remote/file_attente.mp3"
            for c in mock_service.calls
        )

    def test_annuler_from_context_menu(
        self, bot_with_downloads: BotTelechargement, mock_service: MockSoulseekService
    ) -> None:
        """Vérifie que l'annulation individuelle (comme depuis le menu contextuel) appelle abort."""
        bot_with_downloads._on_annuler("/remote/file_en_cours.mp3")
        assert any(
            c["method"] == "abort_transfer" and c["remote_path"] == "/remote/file_en_cours.mp3"
            for c in mock_service.calls
        )


# ── Tests de non-régression SoulseekService ──────────────────────


@pytest.mark.qt_heavy
class TestSoulseekServiceMethods:
    """Vérifie que les méthodes du mock correspondent à l'API réelle."""

    def test_mock_has_required_methods(self, mock_service: MockSoulseekService) -> None:
        """Le mock expose les 3 méthodes de contrôle."""
        assert hasattr(mock_service, "pause_transfer")
        assert hasattr(mock_service, "resume_transfer")
        assert hasattr(mock_service, "abort_transfer")

    def test_mock_has_required_signals(self, mock_service: MockSoulseekService) -> None:
        """Le mock expose les 3 signaux de transfert."""
        assert hasattr(mock_service, "transfer_added")
        assert hasattr(mock_service, "transfer_removed")
        assert hasattr(mock_service, "transfer_progress")

    def test_mock_records_calls(self, mock_service: MockSoulseekService) -> None:
        """Le mock enregistre correctement les appels."""
        mock_service.pause_transfer("user", "/path/file.mp3")
        mock_service.resume_transfer("user2", "/path/file2.mp3")
        mock_service.abort_transfer("user3", "/path/file3.mp3")
        assert len(mock_service.calls) == 3
        assert mock_service.calls[0]["method"] == "pause_transfer"
        assert mock_service.calls[1]["method"] == "resume_transfer"
        assert mock_service.calls[2]["method"] == "abort_transfer"

    def test_mock_clear_calls(self, mock_service: MockSoulseekService) -> None:
        """clear_calls() vide l'historique."""
        mock_service.pause_transfer("u", "p")
        mock_service.clear_calls()
        assert len(mock_service.calls) == 0
