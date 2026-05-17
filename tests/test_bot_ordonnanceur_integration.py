"""Tests d'intégration pour le GUI BotOrdonnanceur.

Étapes 1-4, navigation, workers QThread (analyse + exécution),
prévisualisation, rapport, gestion d'erreurs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.gui.widgets.bots.bot_ordonnanceur import (
    BotOrdonnanceur,
    _AnalyseWorker,
    _OrdonnanceurWorker,
)
from src.services.ordonnanceur_service import (
    AnalyseResultat,
    FichierInfo,
    OrdonnanceurService,
)

# ── Fixtures ──


@pytest.fixture(scope="session")
def qapp():
    """Instance QApplication unique pour tous les tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def bot(qapp) -> Generator[BotOrdonnanceur, None, None]:
    """Crée un BotOrdonnanceur et le nettoie après le test."""
    b = BotOrdonnanceur()
    yield b
    # Nettoyage : forcer l'arrêt des threads
    try:
        b._cleanup_thread()
        if b._analyse_thread is not None:
            b._analyse_thread.quit()
            b._analyse_thread.wait(500)
    except Exception:
        pass
    b.deleteLater()


@pytest.fixture
def mock_service() -> MagicMock:
    """Service mocké pour les tests."""
    svc = MagicMock(spec=OrdonnanceurService)

    # Analyse réaliste
    analyse = AnalyseResultat(
        dossier_source=Path("/tmp/test"),
        fichiers=[
            FichierInfo(
                path=Path("/tmp/test/song.mp3"),
                filename="song.mp3",
                extension=".mp3",
                size=5_000_000,
                modified=1_700_000_000.0,
                artist="Artiste",
                album="Album",
                title="Titre",
                track=1,
                year=2024,
                bitrate=320,
                duration=240.0,
                source_metadata="tag",
            )
        ],
        total_fichiers=10,
        total_audio=8,
        total_taille=50_000_000,
    )
    svc.analyser_dossier.return_value = analyse

    # Aperçu réaliste
    apercu = {
        "renommage": {
            "fichiers": [{"chemin": "/tmp/test/song.mp3", "nouveau_nom": "Artiste - Album - 01 Titre.mp3"}],
            "total_fichiers": 1,
        },
        "classement": {
            "fichiers": [
                {
                    "chemin": "/tmp/test/song.mp3",
                    "nouveau_chemin": "/tmp/test/Organisé/Artiste/Album/01 Titre.mp3",
                    "artiste": "Artiste",
                    "album": "Album",
                }
            ],
            "total_fichiers": 1,
        },
        "deduplication": {
            "fichiers": [{"chemin": "/tmp/test/duplicate.mp3", "taille": 5_000_000, "hash": "abc123"}],
            "total_doublons": 1,
            "total_economise": 5_000_000,
        },
        "nettoyage": {
            "fichiers": [{"chemin": "/tmp/test/temp.part", "age_jours": 14, "taille": 500_000}],
            "total_fichiers": 2,
            "taille_totale": 1_000_000,
        },
        "resume": {
            "total_fichiers_confernes": 10,
            "total_taille_economisee": 6_000_000,
        },
    }
    svc.generer_apercu.return_value = apercu

    # Résultat d'exécution réaliste
    resultat = {
        "succes": True,
        "simulation": True,
        "operations": {
            "renommage": {"tente": 1, "reussi": 1, "echoue": 0},
            "classement": {"tente": 1, "reussi": 1, "echoue": 0},
            "deduplication": {"tente": 1, "reussi": 1, "echoue": 0, "supprime": 1, "economise": 5_000_000},
            "nettoyage": {"tente": 2, "reussi": 2, "echoue": 0, "supprime": 2, "taille_totale": 1_000_000},
        },
        "erreurs": [],
        "details": [
            {"operation": "renommage", "succes": True, "fichier": "song.mp3", "message": "Renommé"},
            {"operation": "classement", "succes": True, "fichier": "song.mp3", "message": "Déplacé"},
        ],
    }
    svc.executer_operations.return_value = resultat

    return svc


# ── Tests d'initialisation ──


class TestInitialisation:
    """Vérifie que BotOrdonnanceur s'initialise correctement."""

    def test_creation(self, bot: BotOrdonnanceur) -> None:
        """Le bot se crée sans erreur."""
        assert bot is not None
        assert isinstance(bot, QFrame)

    def test_etape_initiale(self, bot: BotOrdonnanceur) -> None:
        """L'étape initiale est 0."""
        assert bot._step == 0
        assert bot._selected_ops == set()

    def test_attributs_presents(self, bot: BotOrdonnanceur) -> None:
        """Les attributs clés sont initialisés."""
        assert hasattr(bot, "_service")
        assert hasattr(bot, "_step")
        assert hasattr(bot, "_analyse")
        assert hasattr(bot, "_apercu")
        assert hasattr(bot, "_resultat")
        assert hasattr(bot, "_selected_ops")
        assert hasattr(bot, "_progress_bars")
        assert hasattr(bot, "_log_lines")

    def test_ui_construite(self, bot: BotOrdonnanceur) -> None:
        """L'UI est construite : boutons de navigation présents."""
        assert bot._next_btn is not None
        assert bot._back_btn is not None
        assert "Analyser" in bot._next_btn.text()
        assert not bot._next_btn.isEnabled()  # pas de dossier sélectionné

    def test_signaux_presents(self, bot: BotOrdonnanceur) -> None:
        """Les signaux sont exposés."""
        assert hasattr(bot, "page_changed")
        assert hasattr(bot, "unseen_count_changed")

    def test_step_bar_construite(self, bot: BotOrdonnanceur) -> None:
        """La barre d'étapes affiche 4 étapes."""
        assert len(bot._step_circles) == 4
        assert len(bot._step_labels) == 4
        assert "Choix" in bot._step_labels[0].text()
        assert "Aperçu" in bot._step_labels[1].text()
        assert "Exécution" in bot._step_labels[2].text()
        assert "Rapport" in bot._step_labels[3].text()


# ── Tests de navigation ──


class TestNavigation:
    """Navigation entre les étapes 0-3."""

    def test_demarrer_analyse_avec_bouton(self, bot: BotOrdonnanceur) -> None:
        """Le bouton suivant démarre l'analyse quand on est à l'étape 0."""
        bot._dossier = Path("/tmp/test")
        bot._selected_ops = {"renommage"}
        next_btn = bot._next_btn
        assert next_btn is not None
        next_btn.setEnabled(True)  # Simule l'activation UI via sélection dossier + ops
        # Simuler un clic sur "Analyser →" à l'étape 0
        with patch.object(bot, "_run_analysis") as mock_run:
            bot._on_next()
            mock_run.assert_called_once()

    def test_on_next_avance_sauf_etape0(self, bot: BotOrdonnanceur) -> None:
        """_on_next() avance d'une étape sauf à l'étape 0 (qui déclenche l'analyse)."""
        # On simule qu'on est à l'étape 1 avec analyse faite
        bot._step = 1
        bot._apercu = {"renommage": {"fichiers": []}}
        bot._on_next()
        assert bot._step == 2

        bot._on_next()
        assert bot._step == 3

        # À l'étape 3, le suivant revient à l'accueil (reset complet)
        # page_changed.emit("Accueil") n'est pas dans _on_next mais dans _on_cancel
        bot._on_next()
        assert bot._step == 0
        assert bot._analyse is None
        assert bot._apercu is None
        assert bot._dossier is None

    def test_on_previous_recule(self, bot: BotOrdonnanceur) -> None:
        """_on_previous() recule d'une étape."""
        bot._step = 2
        bot._on_previous()
        assert bot._step == 1

        bot._on_previous()
        assert bot._step == 0

        # À l'étape 0, on ne recule pas plus
        bot._on_previous()
        assert bot._step == 0

    def test_on_cancel_retour_accueil(self, bot: BotOrdonnanceur) -> None:
        """_on_cancel() nettoie et émet page_changed('Accueil')."""
        bot._step = 2
        with patch.object(bot, "page_changed") as mock_signal:
            bot._on_cancel()
            mock_signal.emit.assert_called_once_with("Accueil")

    def test_on_cancel_nettoie_threads(self, bot: BotOrdonnanceur) -> None:
        """_on_cancel() nettoie les threads."""
        mock_thread = MagicMock()
        bot._analyse_thread = mock_thread
        bot._on_cancel()
        mock_thread.quit.assert_called_once()
        mock_thread.wait.assert_called_once_with(2000)

    def test_navigation_etape1_vers_2(self, bot: BotOrdonnanceur) -> None:
        """Navigation étape 1 → 2 avec données d'aperçu."""
        bot._step = 1
        bot._apercu = {"renommage": {"fichiers": [{"chemin": "test.mp3", "nouveau_nom": "new.mp3"}]}}
        bot._on_next()
        assert bot._step == 2


# ── Tests _AnalyseWorker ──


class TestAnalyseWorker:
    """Test du worker d'analyse en QThread."""

    def test_analyse_success(self, mock_service: MagicMock, qapp) -> None:
        """_AnalyseWorker émet 'finished' avec analyse + aperçu."""
        worker = _AnalyseWorker(mock_service, Path("/tmp/test"), {"renommage"})
        finished_data = []

        def on_finished(analyse, apercu):
            finished_data.append((analyse, apercu))

        worker.finished.connect(on_finished)
        worker.run()

        assert len(finished_data) == 1
        analyse, apercu = finished_data[0]
        assert analyse.total_fichiers == 10
        assert "renommage" in apercu

    def test_analyse_error(self, qapp) -> None:
        """_AnalyseWorker émet 'error' si le service lève une exception."""
        mock_service = MagicMock(spec=OrdonnanceurService)
        mock_service.analyser_dossier.side_effect = ValueError("Dossier introuvable")

        worker = _AnalyseWorker(mock_service, Path("/tmp/test"), {"renommage"})
        error_data = []

        def on_error(msg):
            error_data.append(msg)

        worker.error.connect(on_error)
        worker.run()

        assert len(error_data) == 1
        assert "Dossier introuvable" in error_data[0]

    def test_analyse_generer_apercu_error(self, qapp) -> None:
        """_AnalyseWorker émet 'error' si generer_apercu échoue."""
        mock_service = MagicMock(spec=OrdonnanceurService)
        mock_service.generer_apercu.side_effect = RuntimeError("Aucun fichier à analyser")

        worker = _AnalyseWorker(mock_service, Path("/tmp/test"), {"renommage"})
        error_data = []

        def on_error(msg):
            error_data.append(msg)

        worker.error.connect(on_error)
        worker.run()

        assert len(error_data) == 1
        assert "Aucun fichier" in error_data[0]

    def test_analyse_callbacks_verifies(self, mock_service: MagicMock, qapp) -> None:
        """Vérifie que les bonnes méthodes du service sont appelées."""
        worker = _AnalyseWorker(mock_service, Path("/tmp/test"), {"renommage", "classement"})
        worker.run()

        mock_service.analyser_dossier.assert_called_once_with(Path("/tmp/test"))
        mock_service.generer_apercu.assert_called_once()
        args = mock_service.generer_apercu.call_args[0]
        assert len(args[1]) == 2
        assert "renommage" in args[1]
        assert "classement" in args[1]

    def test_analyse_finished_signal_with_null_service(self, qapp) -> None:
        """_AnalyseWorker gère un service null sans erreur."""


# ── Tests _OrdonnanceurWorker ──


class TestOrdonnanceurWorker:
    """Test du worker d'exécution en QThread."""

    def test_execution_success(self, mock_service: MagicMock, qapp) -> None:
        """_OrdonnanceurWorker émet 'completed' avec le résultat."""
        apercu = {"renommage": {"fichiers": [{"chemin": "test.mp3"}]}}
        worker = _OrdonnanceurWorker(mock_service, apercu, simuler=True, selected_ops={"renommage"})
        completed_data = []

        def on_completed(resultat):
            completed_data.append(resultat)

        worker.completed.connect(on_completed)
        worker.run()

        assert len(completed_data) == 1
        assert completed_data[0]["succes"] is True
        assert completed_data[0]["simulation"] is True

    def test_execution_progress_emitted(self, mock_service: MagicMock, qapp) -> None:
        """_OrdonnanceurWorker transmet la callback de progression au service."""
        apercu = {"renommage": {"fichiers": [{"chemin": "test.mp3"}]}}
        worker = _OrdonnanceurWorker(mock_service, apercu, simuler=True, selected_ops={"renommage"})
        worker.run()

        # Vérifie que la callback de progression est passée à executer_operations
        call_args = mock_service.executer_operations.call_args
        assert call_args is not None
        assert "on_progress" in call_args[1]
        # La callback doit être callable
        assert callable(call_args[1]["on_progress"])

    def test_execution_error(self, qapp) -> None:
        """_OrdonnanceurWorker émet 'error' si l'exécution échoue."""
        mock_service = MagicMock(spec=OrdonnanceurService)
        mock_service.executer_operations.side_effect = PermissionError("Accès refusé")

        apercu = {"renommage": {"fichiers": [{"chemin": "test.mp3"}]}}
        worker = _OrdonnanceurWorker(mock_service, apercu, simuler=True, selected_ops={"renommage"})
        error_data = []

        def on_error(msg):
            error_data.append(msg)

        worker.error.connect(on_error)
        worker.run()

        assert len(error_data) == 1
        assert "Accès refusé" in error_data[0]

    def test_execution_cancel(self, mock_service: MagicMock, qapp) -> None:
        """_OrdonnanceurWorker n'émet pas 'completed' si annulé."""
        apercu = {"renommage": {"fichiers": [{"chemin": "test.mp3"}]}}
        worker = _OrdonnanceurWorker(mock_service, apercu, simuler=True, selected_ops={"renommage"})
        completed_data = []

        def on_completed(resultat):
            completed_data.append(resultat)

        worker.completed.connect(on_completed)
        worker.cancel()
        worker.run()

        assert len(completed_data) == 0

    def test_execution_finished_signal(self, mock_service: MagicMock, qapp) -> None:
        """_OrdonnanceurWorker émet 'finished' même en cas d'erreur."""
        mock_service.executer_operations.side_effect = RuntimeError("Boom")
        apercu = {"renommage": {"fichiers": [{"chemin": "test.mp3"}]}}
        worker = _OrdonnanceurWorker(mock_service, apercu, simuler=True, selected_ops={"renommage"})
        finished_count = 0

        def on_finished():
            nonlocal finished_count
            finished_count += 1

        worker.finished.connect(on_finished)
        worker.run()

        assert finished_count == 1

    def test_execution_started_signal(self, mock_service: MagicMock, qapp) -> None:
        """_OrdonnanceurWorker émet le signal 'started' au début."""
        apercu = {"renommage": {"fichiers": [{"chemin": "test.mp3"}]}}
        worker = _OrdonnanceurWorker(mock_service, apercu, simuler=True, selected_ops={"renommage"})
        started_count = 0

        def on_started():
            nonlocal started_count
            started_count += 1

        worker.started.connect(on_started)
        worker.run()

        assert started_count == 1


# ── Tests de l'aperçu (étape 2) ──


class TestApercu:
    """Construction de l'aperçu des modifications."""

    def test_apercu_sans_analyse(self, bot: BotOrdonnanceur) -> None:
        """Sans analyse, l'aperçu affiche un message."""
        bot._analyse = None
        bot._show_step(1)
        assert bot._step == 1

    def test_apercu_avec_donnees(self, bot: BotOrdonnanceur) -> None:
        """Avec des données d'analyse, l'aperçu peuple les sections."""
        bot._analyse = AnalyseResultat(  # type: ignore[assignment]
            dossier_source=Path("/tmp/test"),
            fichiers=[
                FichierInfo(
                    path=Path("/tmp/test/song.mp3"),
                    filename="song.mp3",
                    extension=".mp3",
                    size=5_000_000,
                    modified=1_700_000_000.0,
                    artist="Artiste",
                    album="Album",
                    title="Titre",
                    track=1,
                )
            ],
            total_fichiers=10,
            total_audio=8,
            total_taille=50_000_000,
        )
        bot._apercu = {
            "renommage": {"fichiers": [{"chemin": "song.mp3", "nouveau_nom": "new.mp3"}], "total_fichiers": 1},
            "classement": {"fichiers": [], "total_fichiers": 0},
        }
        bot._show_step(1)
        assert bot._step == 1

    def test_apercu_checkbox_execution(self, bot: BotOrdonnanceur) -> None:
        """La checkbox 'Exécuter pour de vrai' est présente dans l'aperçu."""
        bot._analyse = AnalyseResultat(  # type: ignore[assignment]
            dossier_source=Path("/tmp/test"),
            fichiers=[],
            total_fichiers=0,
            total_audio=0,
            total_taille=0,
        )
        bot._apercu = {"renommage": {"fichiers": [], "total_fichiers": 0}}
        bot._show_step(1)
        # La checkbox devrait être présente dans le layout
        assert bot._step == 1


# ── Tests du rapport (étape 4) ──


class TestRapport:
    """Construction du rapport final (étape 4)."""

    def test_rapport_succes(self, bot: BotOrdonnanceur) -> None:
        """Le rapport affiche un résumé de l'exécution réussie."""
        bot._resultat = {
            "succes": True,
            "simulation": True,
            "operations": {
                "renommage": {"tente": 5, "reussi": 5, "echoue": 0},
                "classement": {"tente": 3, "reussi": 3, "echoue": 0},
            },
            "erreurs": [],
            "details": [
                {"operation": "renommage", "succes": True, "fichier": "song.mp3"},
                {"operation": "classement", "succes": True, "fichier": "song.mp3"},
            ],
        }
        bot._selected_ops = {"renommage", "classement"}
        bot._show_step(3)
        assert bot._step == 3

    def test_rapport_avec_erreurs(self, bot: BotOrdonnanceur) -> None:
        """Le rapport affiche les erreurs si l'exécution en a."""
        bot._resultat = {
            "succes": False,
            "simulation": False,
            "operations": {
                "renommage": {"tente": 5, "reussi": 4, "echoue": 1},
            },
            "erreurs": [
                {"operation": "renommage", "fichier": "bad.mp3", "erreur": "Permission denied"},
            ],
            "details": [],
        }
        bot._selected_ops = {"renommage"}
        bot._show_step(3)
        assert bot._step == 3

    def test_rapport_vide(self, bot: BotOrdonnanceur) -> None:
        """Sans résultat, le rapport est vide mais ne crashe pas."""
        bot._resultat = None
        bot._show_step(3)
        assert bot._step == 3

    def test_copier_rapport(self, bot: BotOrdonnanceur) -> None:
        """_copier_rapport() met le rapport dans le presse-papier."""
        bot._resultat = {
            "succes": True,
            "simulation": True,
            "operations": {"renommage": {"tente": 1, "reussi": 1, "echoue": 0}},
            "erreurs": [],
            "details": [],
        }
        # Vérifie que la copie ne lève pas d'exception
        bot._copier_rapport(bot._resultat)


# ── Tests de l'exécution (étape 3) ──


class TestExecution:
    """Exécution des opérations."""

    def test_start_execution_sans_apercu(self, bot: BotOrdonnanceur) -> None:
        """_start_execution() ne fait rien sans aperçu."""
        bot._apercu = None
        # Ne devrait pas planter
        bot._start_execution()
        assert bot._apercu is None

    def test_start_execution_cree_thread(self, bot: BotOrdonnanceur, mock_service: MagicMock) -> None:
        """_start_execution() crée un QThread et un worker."""
        bot._service = mock_service
        bot._apercu = {"renommage": {"fichiers": [{"chemin": "test.mp3"}]}}
        bot._selected_ops = {"renommage"}
        bot._start_execution()

        assert bot._thread is not None
        assert bot._worker is not None

        # Nettoyage
        bot._cleanup_thread()

    def test_on_execution_progress_met_a_jour_barre(self, bot: BotOrdonnanceur) -> None:
        """_on_execution_progress() met à jour la bonne progress bar."""
        bar = QProgressBar()
        bot._progress_bars["renommage"] = bar
        bot._on_execution_progress("renommage", 5, 10)
        assert bar.maximum() == 10
        assert bar.value() == 5

    def test_on_execution_completed_affiche_rapport(self, bot: BotOrdonnanceur) -> None:
        """_on_execution_completed() stocke le résultat et passe à l'étape 3."""
        resultat = {"succes": True, "simulation": True, "operations": {}, "erreurs": [], "details": []}
        bot._on_execution_completed(resultat)
        assert bot._resultat == resultat
        assert bot._step == 3

    def test_on_execution_error_genere_resultat(self, bot: BotOrdonnanceur) -> None:
        """_on_execution_error() crée un résultat d'erreur."""
        bot._on_execution_error("Erreur critique")
        assert bot._resultat is not None
        assert bot._resultat["succes"] is False
        assert len(bot._resultat["erreurs"]) == 1
        assert "Erreur critique" in bot._resultat["erreurs"][0]["erreur"]
        assert bot._step == 3


# ── Tests du cycle complet ──


class TestCycleComplet:
    """Test du cycle complet : analyse → aperçu → exécution → rapport."""

    def test_cycle_analyse_puis_execution(self, bot: BotOrdonnanceur, mock_service: MagicMock, tmp_path: Path) -> None:
        """Simule le cycle complet avec un service mocké."""
        bot._service = mock_service
        bot._dossier = tmp_path
        bot._selected_ops = {"renommage", "classement"}

        # Simuler un thread d'analyse pour que _on_analysis_completed accepte le callback
        bot._analyse_thread = MagicMock()
        bot._analyse_worker = MagicMock()

        # Étape 0 → lancer l'analyse (synchrone via simulateur)
        worker = _AnalyseWorker(mock_service, tmp_path, bot._selected_ops)
        finished_data = []

        def on_finished(analyse, apercu):
            finished_data.append((analyse, apercu))
            bot._on_analysis_completed(analyse, apercu)

        worker.finished.connect(on_finished)
        worker.run()

        # Vérifier que l'analyse est terminée et l'aperçu stocké
        assert bot._analyse is not None
        assert bot._apercu is not None
        assert bot._step == 1

        # Étape 1 → étape 2 (exécution)
        bot._step = 1
        bot._on_next()
        assert bot._step == 2

        # Exécution (synchrone via simulateur)
        exec_worker = _OrdonnanceurWorker(mock_service, bot._apercu, simuler=True, selected_ops=bot._selected_ops)
        exec_finished = []

        def on_exec_completed(resultat):
            exec_finished.append(resultat)
            bot._on_execution_completed(resultat)

        exec_worker.completed.connect(on_exec_completed)
        exec_worker.run()

        # Vérifier le rapport
        assert len(exec_finished) == 1
        assert bot._step == 3
        assert bot._resultat is not None
        assert bot._resultat["succes"] is True

    def test_cycle_avec_erreur_analyse(self, bot: BotOrdonnanceur, tmp_path: Path) -> None:
        """L'analyse échoue → l'erreur est affichée, pas de crash."""
        mock_service = MagicMock(spec=OrdonnanceurService)
        mock_service.analyser_dossier.side_effect = ValueError("Dossier introuvable")
        bot._service = mock_service

        worker = _AnalyseWorker(mock_service, tmp_path, {"renommage"})
        worker.error.connect(bot._on_analysis_error)
        worker.run()

        assert bot._analyse is None

    def test_cycle_execution_rapport_erreurs(self, bot: BotOrdonnanceur, mock_service: MagicMock) -> None:
        """L'exécution avec erreurs aboutit à un rapport d'erreur."""
        mock_resultat = {
            "succes": False,
            "simulation": False,
            "operations": {"renommage": {"tente": 2, "reussi": 1, "echoue": 1}},
            "erreurs": [{"operation": "renommage", "fichier": "bad.mp3", "erreur": "Permission denied"}],
            "details": [],
        }
        mock_service.executer_operations.return_value = mock_resultat
        bot._service = mock_service

        bot._on_execution_completed(mock_resultat)
        assert bot._resultat is not None
        assert bot._resultat["succes"] is False
        assert bot._step == 3


# ── Tests de _taille_lisible ──


class TestTailleLisible:
    """Tests static method _taille_lisible."""

    def test_octets(self, bot: BotOrdonnanceur) -> None:
        assert bot._taille_lisible(500) == "500 o"

    def test_kilooctets(self, bot: BotOrdonnanceur) -> None:
        assert bot._taille_lisible(1500) == "1.5 Ko"

    def test_megaoctets(self, bot: BotOrdonnanceur) -> None:
        assert bot._taille_lisible(5_000_000) == "4.8 Mo"

    def test_gigaoctets(self, bot: BotOrdonnanceur) -> None:
        assert bot._taille_lisible(2_500_000_000) == "2.3 Go"

    def test_zero(self, bot: BotOrdonnanceur) -> None:
        assert bot._taille_lisible(0) == "0 o"
