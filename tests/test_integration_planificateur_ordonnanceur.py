"""Tests d'intégration Planificateur ←→ Ordonnanceur.

Couvre :
- La méthode `executer_action_planificateur()` d'OrdonnanceurService
- Les fonctions du connecteur module-level dans bot_ordonnanceur.py
  (_PlanificateurWorker, _PlanificateurReceiver, _on_action_planifiee)
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Generator

import pytest
from pytest import MonkeyPatch

from src.services.ordonnanceur_service import OrdonnanceurService

# ── Helpers ────────────────────────────────────────────────────────────


def _creer_fichier_temp(dossier: Path, nom: str, age_jours: int = 0) -> Path:
    """Crée un fichier temporaire avec un âge donné."""
    path = dossier / nom
    path.write_text("temp data", encoding="utf-8")
    if age_jours > 0:
        ancien = datetime.now() - timedelta(days=age_jours)
        os.utime(path, (ancien.timestamp(), ancien.timestamp()))
    return path


# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def service() -> OrdonnanceurService:
    """Fixture fournissant une instance fraîche d'OrdonnanceurService."""
    return OrdonnanceurService()


@pytest.fixture
def tmp_audio_dir() -> Generator[Path, None, None]:
    """Répertoire temporaire pour les tests de fichiers audio."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch: MonkeyPatch) -> Generator[None, None, None]:
    """Isole les bases SQLite dans un répertoire temporaire pour chaque test.

    Calqué sur la fixture du même nom dans test_planificateur.py.
    Évite les effets de bord entre tests et protège la DB de dev.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # PlanificateurService
        monkeypatch.setattr(
            "src.services.planificateur_service._DB_PATH",
            Path(tmpdir) / "planificateur.db",
        )
        monkeypatch.setattr(
            "src.services.planificateur_service._DATA_DIR",
            Path(tmpdir),
        )

        # EventBus — même répertoire isolé
        monkeypatch.setattr(
            "src.services.event_bus._DB_PATH",
            Path(tmpdir) / "eventbus.db",
        )
        monkeypatch.setattr(
            "src.services.event_bus._DATA_DIR",
            Path(tmpdir),
        )

        from src.services.event_bus import EventBus

        if EventBus._instance is not None:
            try:
                EventBus._instance.shutdown()
            except Exception:
                pass
        EventBus._instance = None

        # Forcer une instance fraîche de PlanificateurService avec les paths patchés
        from src.services.planificateur_service import PlanificateurService

        if PlanificateurService._instance is not None:
            try:
                PlanificateurService._instance._db.close()
            except Exception:
                pass
        PlanificateurService._instance = None
        _isolated_svc = PlanificateurService()

        # Patcher la référence module-level dans bot_ordonnanceur (si déjà importé)
        try:
            import src.gui.widgets.bots.bot_ordonnanceur as _bot_ord

            _bot_ord.planificateur_service = _isolated_svc
            # Reconnecter le signal sur l'instance fraîche
            _bot_ord.planificateur_service.action_changed.connect(_bot_ord._on_action_planifiee)
        except (ImportError, AttributeError):
            pass

        yield

        # Nettoyage EventBus (après le yield pour libérer le verrou avant suppression tempdir)
        if EventBus._instance is not None:
            try:
                EventBus._instance.shutdown()
            except Exception:
                pass
            EventBus._instance = None

        # Nettoyage PlanificateurService — fermer TOUTES les connexions au tempdir
        # pour éviter PermissionError Windows.
        try:
            if PlanificateurService._instance is not None:
                PlanificateurService._instance._db.close()
        except Exception:
            pass
        # L'instance créée dans ce setup peut différer de _instance
        # si une autre fixture (planif_svc) a reset le singleton entre-temps.
        try:
            _isolated_svc._db.close()
        except Exception:
            pass
        PlanificateurService._instance = None


@pytest.fixture
def planif_svc(_isolate_db: None) -> Any:
    """Fixture fournissant PlanificateurService isolé.

    Dépend de _isolate_db pour avoir une DB temporaire.
    """
    from src.services.planificateur_service import PlanificateurService

    # Forcer une nouvelle instance (singleton reset par _isolate_db)
    PlanificateurService._instance = None
    svc = PlanificateurService()
    return svc


# ═══════════════════════════════════════════════════════════════════════
# Tests pour executer_action_planificateur()
# ═══════════════════════════════════════════════════════════════════════


class TestExecuterActionPlanificateur:
    """Teste la méthode OrdonnanceurService.executer_action_planificateur()."""

    # ── Type inconnu ───────────────────────────────────────────────

    def test_type_inconnu(self, service: OrdonnanceurService) -> None:
        """Un type d'action inconnu retourne succes=False."""
        resultat = service.executer_action_planificateur(
            action_type="bidon",
            params={},
        )
        assert resultat["succes"] is False
        assert "inconnu" in resultat["message"].lower()

    # ── Dossier inexistant ─────────────────────────────────────────

    def test_dossier_inexistant_renommage(
        self,
        service: OrdonnanceurService,
    ) -> None:
        """Un dossier inexistant est géré sans erreur (scanner retourne [])."""
        resultat = service.executer_action_planificateur(
            action_type="renommage",
            params={"dossier": "/tmp/inexistant_XXXXXXXX"},
        )
        assert resultat["succes"] is True
        assert "0/0" in resultat["message"]

    def test_dossier_inexistant_classement(
        self,
        service: OrdonnanceurService,
    ) -> None:
        """Même test pour classement."""
        resultat = service.executer_action_planificateur(
            action_type="classement",
            params={"dossier": "/tmp/inexistant_XXXXXXXX"},
        )
        assert resultat["succes"] is True

    def test_dossier_inexistant_deduplication(
        self,
        service: OrdonnanceurService,
    ) -> None:
        """Même test pour deduplication."""
        resultat = service.executer_action_planificateur(
            action_type="deduplication",
            params={"dossier": "/tmp/inexistant_XXXXXXXX"},
        )
        assert resultat["succes"] is True

    # ── Nettoyage avec dossier inexistant ──────────────────────────

    def test_nettoyage_dossier_inexistant(
        self,
        service: OrdonnanceurService,
    ) -> None:
        """Le nettoyage d'un dossier inexistant est géré."""
        with tempfile.TemporaryDirectory() as tmp:
            dossier = Path(tmp)
            resultat = service.executer_action_planificateur(
                action_type="nettoyage_temp",
                params={"dossier": str(dossier), "age_jours": 7},
            )
            assert resultat["succes"] is True
            assert resultat["ops"]["tente"] == 0

    # ── Nettoyage avec fichiers ────────────────────────────────────

    def test_nettoyage_temp_supprime_fichiers_ages(
        self,
        service: OrdonnanceurService,
    ) -> None:
        """Le nettoyage supprime les fichiers de plus de N jours."""
        with tempfile.TemporaryDirectory() as tmp:
            dossier = Path(tmp)
            _creer_fichier_temp(dossier, "recent.tmp", age_jours=0)
            _creer_fichier_temp(dossier, "ancien.tmp", age_jours=30)

            sous_dossier = dossier / "sous"
            sous_dossier.mkdir()
            _creer_fichier_temp(sous_dossier, "old.cache", age_jours=14)

            resultat = service.executer_action_planificateur(
                action_type="nettoyage_temp",
                params={"dossier": str(dossier), "age_jours": 7},
            )
            assert resultat["succes"] is True
            assert resultat["ops"]["supprime"] >= 2

    def test_nettoyage_temp_garde_fichiers_recents(
        self,
        service: OrdonnanceurService,
    ) -> None:
        """Le nettoyage garde les fichiers de moins de N jours."""
        with tempfile.TemporaryDirectory() as tmp:
            dossier = Path(tmp)
            _creer_fichier_temp(dossier, "recent.tmp", age_jours=0)
            _creer_fichier_temp(dossier, "hier.tmp", age_jours=1)

            resultat = service.executer_action_planificateur(
                action_type="nettoyage_temp",
                params={"dossier": str(dossier), "age_jours": 7},
            )
            assert resultat["succes"] is True
            assert resultat["ops"]["supprime"] == 0

    # ── Dossier vide ───────────────────────────────────────────────

    def test_renommage_dossier_vide(
        self,
        service: OrdonnanceurService,
        tmp_audio_dir: Path,
    ) -> None:
        """Renommage avec un dossier vide est un succès (0 fichiers)."""
        resultat = service.executer_action_planificateur(
            action_type="renommage",
            params={"dossier": str(tmp_audio_dir)},
        )
        assert resultat["succes"] is True
        assert resultat["ops"]["tente"] == 0

    def test_classement_dossier_vide(
        self,
        service: OrdonnanceurService,
        tmp_audio_dir: Path,
    ) -> None:
        """Classement avec un dossier vide est un succès (0 fichiers)."""
        resultat = service.executer_action_planificateur(
            action_type="classement",
            params={"dossier": str(tmp_audio_dir)},
        )
        assert resultat["succes"] is True
        assert resultat["ops"]["tente"] == 0

    def test_deduplication_dossier_vide(
        self,
        service: OrdonnanceurService,
        tmp_audio_dir: Path,
    ) -> None:
        """Dédoublonnage avec un dossier vide est un succès (0 doublons)."""
        resultat = service.executer_action_planificateur(
            action_type="deduplication",
            params={"dossier": str(tmp_audio_dir)},
        )
        assert resultat["succes"] is True
        assert "ops" in resultat

    # ── Validation des paramètres ──────────────────────────────────

    def test_renommage_avec_template(
        self,
        service: OrdonnanceurService,
        tmp_audio_dir: Path,
    ) -> None:
        """Le paramètre template est bien transmis pour le renommage."""
        resultat = service.executer_action_planificateur(
            action_type="renommage",
            params={
                "dossier": str(tmp_audio_dir),
                "template": "{artist} - {title}.{ext}",
            },
        )
        assert resultat["succes"] is True

    def test_classement_avec_template(
        self,
        service: OrdonnanceurService,
        tmp_audio_dir: Path,
    ) -> None:
        """Le paramètre template est bien transmis pour le classement."""
        resultat = service.executer_action_planificateur(
            action_type="classement",
            params={
                "dossier": str(tmp_audio_dir),
                "template": "{artist}/{title}.{ext}",
            },
        )
        assert resultat["succes"] is True

    def test_nettoyage_avec_age_personnalise(
        self,
        service: OrdonnanceurService,
    ) -> None:
        """Le paramètre age_jours est bien transmis pour le nettoyage."""
        with tempfile.TemporaryDirectory() as tmp:
            dossier = Path(tmp)
            resultat = service.executer_action_planificateur(
                action_type="nettoyage_temp",
                params={"dossier": str(dossier), "age_jours": 1},
            )
            assert resultat["succes"] is True

    def test_nettoyage_age_defaut(
        self,
        service: OrdonnanceurService,
    ) -> None:
        """Si age_jours n'est pas fourni, la valeur par défaut (7) est utilisée."""
        with tempfile.TemporaryDirectory() as tmp:
            dossier = Path(tmp)
            _creer_fichier_temp(dossier, "ancien.tmp", age_jours=14)
            resultat = service.executer_action_planificateur(
                action_type="nettoyage_temp",
                params={"dossier": str(dossier)},
            )
            assert resultat["succes"] is True
            assert resultat["ops"]["supprime"] >= 1

    # ── Structure du retour ────────────────────────────────────────

    def test_structure_retour_succes(
        self,
        service: OrdonnanceurService,
        tmp_audio_dir: Path,
    ) -> None:
        """Le retour contient toutes les clés attendues en cas de succès."""
        resultat = service.executer_action_planificateur(
            action_type="renommage",
            params={"dossier": str(tmp_audio_dir)},
        )
        assert "succes" in resultat
        assert "message" in resultat
        assert "details" in resultat
        assert "ops" in resultat
        assert "erreurs" in resultat

    def test_structure_retour_erreur(
        self,
        service: OrdonnanceurService,
    ) -> None:
        """Le retour contient les bonnes clés en cas d'erreur de type."""
        resultat = service.executer_action_planificateur(
            action_type="inconnu",
            params={},
        )
        assert "succes" in resultat
        assert "message" in resultat
        assert "details" in resultat

    # ── Callback on_progress ───────────────────────────────────────

    def test_on_progress_callback(
        self,
        service: OrdonnanceurService,
    ) -> None:
        """Le callback on_progress est appelé pendant l'exécution."""
        appels: list[tuple[str, int, int]] = []

        def progress(section: str, fait: int, total: int) -> None:
            appels.append((section, fait, total))

        with tempfile.TemporaryDirectory() as tmp:
            dossier = Path(tmp)
            _creer_fichier_temp(dossier, "ancien.tmp", age_jours=14)
            _creer_fichier_temp(dossier, "vieux.tmp", age_jours=30)

            service.executer_action_planificateur(
                action_type="nettoyage_temp",
                params={"dossier": str(dossier), "age_jours": 7},
                on_progress=progress,
            )
            assert len(appels) >= 1
            assert appels[0][0] == "nettoyage"


# ═══════════════════════════════════════════════════════════════════════
# Tests pour le connecteur module-level (bot_ordonnanceur.py)
# ═══════════════════════════════════════════════════════════════════════

# NOTE : l'import de bot_ordonnanceur déclenche _connect_planificateur()
# au niveau module. Pour les tests unitaires du connecteur, on force un
# rechargement du module avec la DB isolée (via _isolate_db autouse).


@pytest.mark.qt_heavy
class TestPlanificateurWorker:
    """Teste _PlanificateurWorker (signal + run) sans thread réel."""

    def test_worker_run_complete(
        self,
        qapp: Any,
        _isolate_db: None,
    ) -> None:
        """Worker.run() émet completed avec succes=True."""
        # Importer après que l'isolation DB est en place
        from src.gui.widgets.bots.bot_ordonnanceur import (
            _ACTION_EXECUTOR,
            _PlanificateurWorker,
        )

        # Après import, le module-level _connect_planificateur() a déjà
        # initialisé _ACTION_EXECUTOR avec la DB isolée
        assert _ACTION_EXECUTOR is not None

        signaux: list[tuple] = []

        def on_completed(action_id: int, succes: bool, message: str) -> None:
            signaux.append((action_id, succes, message))

        with tempfile.TemporaryDirectory() as tmp:
            dossier = Path(tmp)
            worker = _PlanificateurWorker(
                action_id=42,
                action_type="nettoyage_temp",
                params={"dossier": str(dossier), "age_jours": 7},
            )
            worker.completed.connect(on_completed)
            worker.run()

            assert len(signaux) == 1
            action_id, succes, message = signaux[0]
            assert action_id == 42
            assert succes is True

    def test_worker_run_exception(
        self,
        qapp: Any,
        _isolate_db: None,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """Worker.run() émet completed avec succes=False sur exception."""
        from src.gui.widgets.bots.bot_ordonnanceur import (
            _ACTION_EXECUTOR,
            _PlanificateurWorker,
        )

        assert _ACTION_EXECUTOR is not None

        # Forcer une exception dans executer_action_planificateur
        def _fake_exec(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("Erreur forcée par le test")

        monkeypatch.setattr(
            _ACTION_EXECUTOR,
            "executer_action_planificateur",
            _fake_exec,
        )

        signaux: list[tuple] = []

        def on_completed(action_id: int, succes: bool, message: str) -> None:
            signaux.append((action_id, succes, message))

        worker = _PlanificateurWorker(
            action_id=42,
            action_type="renommage",
            params={"dossier": "/tmp"},
        )
        worker.completed.connect(on_completed)
        worker.run()

        assert len(signaux) == 1
        action_id, succes, message = signaux[0]
        assert action_id == 42
        assert succes is False
        assert "Erreur" in message or "Erreur" in message


@pytest.mark.qt_heavy
class TestPlanificateurReceiver:
    """Teste _PlanificateurReceiver (callback dans le main thread).

    On recharge bot_ordonnanceur via importlib.reload() après l'isolation
    DB (_isolate_db autouse) pour que le module-level planificateur_service
    soit une instance fraîche avec la DB isolée.
    """

    def _setup(self):
        """Crée un PlanificateurService frais avec la DB isolée
        (patched par _isolate_db autouse) et le patch dans le module
        bot_ordonnanceur pour que _on_action_planifiee et le receiver
        utilisent la bonne instance.
        """
        from src.gui.widgets.bots import bot_ordonnanceur
        from src.services.planificateur_service import PlanificateurService

        # Déconnecter l'ancien signal s'il existe
        old_svc = getattr(bot_ordonnanceur, "planificateur_service", None)
        if old_svc is not None:
            try:
                old_svc.action_changed.disconnect(bot_ordonnanceur._on_action_planifiee)
            except (TypeError, RuntimeError):
                pass

        # Reset singleton et créer instance fraîche (DB isolée)
        PlanificateurService._instance = None
        fresh_svc = PlanificateurService()

        # Patcher la référence module-level de bot_ordonnanceur
        bot_ordonnanceur.planificateur_service = fresh_svc

        # Reconnecter le signal sur la nouvelle instance
        fresh_svc.action_changed.connect(bot_ordonnanceur._on_action_planifiee)

        return fresh_svc, bot_ordonnanceur._PLANIFICATEUR_RECEIVER

    def _teardown(self, planif_svc: Any) -> None:
        """Ferme les connexions DB pour éviter les PermissionError Windows.
        _isolate_db autouse gère déjà EventBus.shutdown en fin de test.
        """
        try:
            planif_svc._db.close()
        except Exception:
            pass
        # Vider le cache de modules pour que le prochain _setup()
        # obtienne un singleton frais
        from src.services.planificateur_service import PlanificateurService

        PlanificateurService._instance = None

    def test_receiver_complete_succes(
        self,
        qapp: Any,
        _isolate_db: None,
    ) -> None:
        """on_action_terminee appelle complete_action(succes=True) → terminee."""
        planif_svc, receiver = self._setup()

        # Créer une action dans la DB isolée
        action_id = planif_svc.create_action(
            type_="renommage",
            parametres={"dossier": "/tmp"},
            mode="immediat",
        )
        assert action_id > 0

        # Déconnecter temporairement _on_action_planifiee pour éviter
        # qu'il ne spawn un QThread pendant execute_manual.
        from src.gui.widgets.bots.bot_ordonnanceur import _on_action_planifiee

        planif_svc.action_changed.disconnect(_on_action_planifiee)
        planif_svc.execute_manual(action_id)
        planif_svc.action_changed.connect(_on_action_planifiee)

        # Vérifier qu'on est en cours
        action = planif_svc.get_action(action_id)
        assert action is not None
        assert action["statut"] == "en_cours"

        # Appeler le receiver (utilise le planificateur_service rechargé)
        receiver.on_action_terminee(
            action_id=action_id,
            succes=True,
            message="Succès test",
        )

        qapp.processEvents()

        # Vérifier que l'action est marquée terminee
        action = planif_svc.get_action(action_id)
        assert action is not None
        assert action["statut"] == "terminee", f"Statut attendu: terminee, obtenu: {action['statut']}"

        self._teardown(planif_svc)

    def test_receiver_complete_echec(
        self,
        qapp: Any,
        _isolate_db: None,
    ) -> None:
        """on_action_terminee appelle complete_action(succes=False)."""
        planif_svc, receiver = self._setup()

        action_id = planif_svc.create_action(
            type_="classement",
            parametres={"dossier": "/tmp"},
            mode="immediat",
        )
        assert action_id > 0

        # Déconnecter _on_action_planifiee temporairement
        from src.gui.widgets.bots.bot_ordonnanceur import _on_action_planifiee

        planif_svc.action_changed.disconnect(_on_action_planifiee)
        planif_svc.execute_manual(action_id)
        planif_svc.action_changed.connect(_on_action_planifiee)

        action = planif_svc.get_action(action_id)
        assert action is not None
        assert action["statut"] == "en_cours"

        receiver.on_action_terminee(
            action_id=action_id,
            succes=False,
            message="Erreur test",
        )

        qapp.processEvents()

        action = planif_svc.get_action(action_id)
        assert action is not None
        # Après échec: "terminee" (final) ou "planifiee" (retry)
        assert action["statut"] in ("terminee", "planifiee"), f"Statut inattendu: {action['statut']}"

        self._teardown(planif_svc)


@pytest.mark.qt_heavy
class TestConnecteurPlanificateur:
    """Teste les fonctions du connecteur module-level.

    Tous les imports de bot_ordonnanceur se font après l'isolation DB
    (autouse _isolate_db) pour éviter les effets de bord.
    """

    def test_connect_planificateur_initialise(
        self,
        qapp: Any,
        _isolate_db: None,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """_connect_planificateur() initialise _ACTION_EXECUTOR et connecte le signal."""
        import src.gui.widgets.bots.bot_ordonnanceur as connector_module

        # Forcer la réinitialisation si déjà importé
        connector_module._ACTION_EXECUTOR = None

        connector_module._connect_planificateur()

        assert connector_module._ACTION_EXECUTOR is not None

    def test_on_action_planifiee_filtre_statut(
        self,
        qapp: Any,
        _isolate_db: None,
    ) -> None:
        """Les actions avec statut != 'en_cours' sont ignorées (retour silencieux)."""
        from src.gui.widgets.bots.bot_ordonnanceur import (
            _on_action_planifiee,
        )

        # Tous les statuts non "en_cours" doivent être ignorés sans erreur
        for statut in ("en_attente", "planifiee", "terminee", "echouee"):
            _on_action_planifiee(1, "renommage", statut)

    def test_on_action_planifiee_filtre_type(
        self,
        qapp: Any,
        _isolate_db: None,
    ) -> None:
        """Les types d'action inconnus (hors ordonnanceur) sont ignorés."""
        from src.gui.widgets.bots.bot_ordonnanceur import (
            _on_action_planifiee,
        )

        # Type non-ordonnanceur — doit être filtré avant toute action
        _on_action_planifiee(1, "recherche", "en_cours")

    def test_on_action_planifiee_action_introuvable(
        self,
        qapp: Any,
        _isolate_db: None,
    ) -> None:
        """Une action introuvable en DB est ignorée."""
        from src.gui.widgets.bots.bot_ordonnanceur import (
            _on_action_planifiee,
        )

        # DB isolée garantie vide → l'ID 1 n'existe pas → doit être ignoré
        _on_action_planifiee(1, "renommage", "en_cours")


@pytest.mark.qt_heavy
class TestIntegrationPlanificateurOrdonnanceur:
    """Tests d'intégration complets : Planificateur → Ordonnanceur.

    Utilise _isolate_db (autouse) pour avoir une DB fraîche à chaque test.
    """

    def test_cycle_complet_renommage(
        self,
        qapp: Any,
        planif_svc: Any,
    ) -> None:
        """Cycle complet : création action → exécution manuelle → complétion."""
        from src.gui.widgets.bots.bot_ordonnanceur import (
            _ACTION_EXECUTOR,
            _connect_planificateur,
        )

        if _ACTION_EXECUTOR is None:
            _connect_planificateur()

        with tempfile.TemporaryDirectory() as tmp:
            dossier = Path(tmp)

            # Créer une action de renommage dans le Planificateur
            action_id = planif_svc.create_action(
                type_="renommage",
                parametres={
                    "dossier": str(dossier),
                    "template": "{artist} - {title}.{ext}",
                },
                mode="immediat",
            )
            assert action_id > 0

            # Vérifier que l'action est bien créée avec le bon type
            action = planif_svc.get_action(action_id)
            assert action is not None
            assert action["type"] == "renommage"
            assert action["statut"] == "en_attente"

            # Exécuter manuellement (déclenche le signal action_changed)
            planif_svc.execute_manual(action_id)

            # L'action est passée en "en_cours"
            action = planif_svc.get_action(action_id)
            assert action is not None
            assert action["statut"] == "en_cours"

            # Compléter l'action avec succès
            planif_svc.complete_action(action_id, succes=True)

            action = planif_svc.get_action(action_id)
            assert action is not None
            assert action["statut"] == "terminee", f"Statut attendu: terminee, obtenu: {action['statut']}"

    def test_cycle_complet_echec(
        self,
        qapp: Any,
        planif_svc: Any,
    ) -> None:
        """Cycle complet avec échec (complete_action avec erreur)."""
        from src.gui.widgets.bots.bot_ordonnanceur import (
            _ACTION_EXECUTOR,
            _connect_planificateur,
        )

        if _ACTION_EXECUTOR is None:
            _connect_planificateur()

        action_id = planif_svc.create_action(
            type_="classement",
            parametres={"dossier": "/tmp/inexistant"},
            mode="immediat",
        )
        assert action_id > 0

        planif_svc.execute_manual(action_id)

        action = planif_svc.get_action(action_id)
        assert action is not None
        assert action["statut"] == "en_cours"

        planif_svc.complete_action(
            action_id,
            succes=False,
            erreur="Erreur simulée",
        )

        action = planif_svc.get_action(action_id)
        assert action is not None
        # Après échec: "terminee" (final) ou "planifiee" (retry)
        assert action["statut"] in ("terminee", "planifiee")
