"""
Tests unitaires pour le PlanificateurService (SQLite, CRUD, exécution).
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Generator

import pytest
from PySide6.QtCore import QObject, Signal

# ── Fixtures d'isolation ──────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Isole les bases SQLite dans un répertoire temporaire pour chaque test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # PlanificateurService
        db_path = Path(tmpdir) / "planificateur.db"
        monkeypatch.setattr("src.services.planificateur_service._DB_PATH", db_path)
        monkeypatch.setattr("src.services.planificateur_service._DATA_DIR", Path(tmpdir))

        # EventBus — même répertoire isolé
        monkeypatch.setattr("src.services.event_bus._DB_PATH", Path(tmpdir) / "eventbus.db")
        monkeypatch.setattr("src.services.event_bus._DATA_DIR", Path(tmpdir))

        from src.services.event_bus import EventBus

        if EventBus._instance is not None:
            try:
                EventBus._instance.shutdown()
            except Exception:
                pass
        EventBus._instance = None

        yield

        # Nettoyage EventBus
        if EventBus._instance is not None:
            try:
                EventBus._instance.shutdown()
            except Exception:
                pass
            EventBus._instance = None


@pytest.fixture
def service() -> Any:
    """Crée/réinitialise le PlanificateurService pour chaque test."""
    from src.services.planificateur_service import PlanificateurService

    # Réinitialiser le singleton
    PlanificateurService._instance = None
    svc = PlanificateurService()
    yield svc
    # Nettoyage
    svc._db.close()
    PlanificateurService._instance = None


# ═══════════════════════════════════════════════════════════════════════════
# Tests CRUD
# ═══════════════════════════════════════════════════════════════════════════


class TestCreateAction:
    """Création d'actions avec différents types et modes."""

    def test_create_immediat(self, service: Any) -> None:
        """Une action immédiate est créée avec le statut 'en_attente'."""
        action_id = service.create_action(
            type_="recherche",
            parametres={"mots_cles": "test"},
            mode="immediat",
        )
        assert action_id > 0
        action = service.get_action(action_id)
        assert action is not None
        assert action["type"] == "recherche"
        assert action["mode"] == "immediat"
        assert action["statut"] == "en_attente"
        assert action["parametres"] == {"mots_cles": "test"}

    def test_create_avec_nom_description(self, service: Any) -> None:
        """Une action avec nom et description les stocke en base."""
        action_id = service.create_action(
            type_="recherche",
            parametres={"mots_cles": "album"},
            mode="immediat",
            nom="Recherche album",
            description="Scan des résultats pour album spécifique",
        )
        assert action_id > 0
        action = service.get_action(action_id)
        assert action is not None
        assert action["nom"] == "Recherche album"
        assert action["description"] == "Scan des résultats pour album spécifique"
        assert action["statut"] == "en_attente"

    def test_create_planifie(self, service: Any) -> None:
        """Une action planifiée est créée avec le statut 'planifiee'."""
        future = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        action_id = service.create_action(
            type_="scan",
            parametres={},
            mode="planifie",
            prochaine_execution=future,
        )
        assert action_id > 0
        action = service.get_action(action_id)
        assert action is not None
        assert action["mode"] == "planifie"
        assert action["statut"] == "planifiee"
        assert action["prochaine_execution"] == future

    def test_create_recurrent(self, service: Any) -> None:
        """Une action récurrente avec intervalle est valide."""
        future = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        action_id = service.create_action(
            type_="wishlist",
            parametres={},
            mode="planifie",
            recurrence_interval=6,
            recurrence_unite="heures",
            prochaine_execution=future,
        )
        action = service.get_action(action_id)
        assert action is not None
        assert action["recurrence_interval"] == 6
        assert action["recurrence_unite"] == "heures"

    def test_create_type_invalide(self, service: Any) -> None:
        """Un type d'action invalide lève ValueError."""
        with pytest.raises(ValueError, match="invalide"):
            service.create_action(type_="inconnu", parametres={}, mode="immediat")


class TestCRUD:
    """Lecture, mise à jour, suppression."""

    def test_update_statut(self, service: Any) -> None:
        """Mettre à jour le statut d'une action fonctionne."""
        action_id = service.create_action(type_="nettoyage", parametres={}, mode="immediat")
        updated = service.update_action(action_id, statut="en_cours")
        assert updated is True
        action = service.get_action(action_id)
        assert action is not None
        assert action["statut"] == "en_cours"

    def test_update_parametres(self, service: Any) -> None:
        """Mettre à jour les paramètres JSON."""
        action_id = service.create_action(
            type_="recherche",
            parametres={"mots_cles": "initial"},
            mode="immediat",
        )
        service.update_action(action_id, parametres={"mots_cles": "modifié"})
        action = service.get_action(action_id)
        assert action is not None
        assert action["parametres"] == {"mots_cles": "modifié"}

    def test_delete_action(self, service: Any) -> None:
        """Supprimer une action retourne True et la rend inaccessible."""
        action_id = service.create_action(type_="scan", parametres={}, mode="immediat")
        deleted = service.delete_action(action_id)
        assert deleted is True
        assert service.get_action(action_id) is None

    def test_list_filtre(self, service: Any) -> None:
        """Lister les actions avec filtre par type."""
        service.create_action(type_="recherche", parametres={}, mode="immediat")
        service.create_action(type_="scan", parametres={}, mode="immediat")
        service.create_action(type_="wishlist", parametres={}, mode="immediat")

        recherches = service.list_actions(type_="recherche")
        assert len(recherches) == 1
        assert recherches[0]["type"] == "recherche"

        scans = service.list_actions(type_="scan")
        assert len(scans) == 1


class TestStats:
    """Statistiques et compteurs."""

    def test_stats_apres_creation(self, service: Any) -> None:
        """Les stats reflètent les actions créées."""
        service.create_action(type_="recherche", parametres={}, mode="immediat")
        service.create_action(type_="scan", parametres={}, mode="immediat")
        service.create_action(
            type_="wishlist",
            parametres={},
            mode="planifie",
            prochaine_execution=(datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
        )

        stats = service.get_stats()
        assert stats["en_attente"] == 2
        assert stats["planifiee"] == 1
        assert stats["en_cours"] == 0
        assert stats["terminee"] == 0
        assert stats["echouee"] == 0

    def test_stats_avec_terminaison(self, service: Any) -> None:
        """Les stats sont mises à jour après une terminaison."""
        action_id = service.create_action(type_="nettoyage", parametres={}, mode="immediat")
        service.complete_action(action_id, succes=True)

        stats = service.get_stats()
        assert stats["en_attente"] == 0
        assert stats["terminee"] == 1

    def test_stats_avec_echec(self, service: Any) -> None:
        """Les stats reflètent les échecs après 3 tentatives."""
        action_id = service.create_action(type_="recherche", parametres={}, mode="immediat")
        # Simuler 3 échecs d'affilée (sans réinitialiser nb_tentatives entre chaque)
        for _ in range(3):
            service._db.update_action(action_id, statut="en_cours")
            service.complete_action(action_id, succes=False, erreur="Erreur test")

        stats = service.get_stats()
        # Après 3 tentatives, l'action doit être marquée echouee
        assert stats["echouee"] == 1


class TestPause:
    """Pause et reprise du service."""

    def test_pause_resume(self, service: Any) -> None:
        """Le service peut être mis en pause et repris."""
        assert service.paused is False
        service.pause()
        assert service.paused is True
        service.resume()
        assert service.paused is False

    def test_pas_dexecution_pendant_pause(self, service: Any) -> None:
        """Le polling ne démarre pas d'action en pause."""
        service.create_action(
            type_="recherche",
            parametres={},
            mode="planifie",
            prochaine_execution=(datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S"),
        )
        service.pause()
        service._on_poll()
        # Aucune action ne devrait être marquée 'en_cours'
        actions = service.list_actions()
        for a in actions:
            assert a["statut"] != "en_cours"


class TestHistorique:
    """Historique des actions terminées."""

    def test_get_historique(self, service: Any) -> None:
        """Les actions terminées apparaissent dans l'historique."""
        id1 = service.create_action(type_="recherche", parametres={}, mode="immediat")
        id2 = service.create_action(type_="scan", parametres={}, mode="immediat")
        service.complete_action(id1, succes=True)
        # 3 échecs consécutifs pour atteindre le max de tentatives
        service._db.update_action(id2, statut="en_cours")
        service.complete_action(id2, succes=False, erreur="Time out 1")
        service._db.update_action(id2, statut="en_cours")
        service.complete_action(id2, succes=False, erreur="Time out 2")
        service._db.update_action(id2, statut="en_cours")
        service.complete_action(id2, succes=False, erreur="Time out 3")

        historique = service.get_historique()
        assert len(historique) == 2
        statuts = {a["statut"] for a in historique}
        assert "terminee" in statuts
        assert "echouee" in statuts


class TestExecution:
    """Exécution séquentielle, timeout, enchaînement FIFO."""

    def test_timeout_marque_echouee(self, service: Any) -> None:
        """Une action qui dépasse le timeout est marquée echouee par _on_poll."""
        action_id = service.create_action(type_="recherche", parametres={}, mode="immediat")
        # Simuler le démarrage manuel
        service.execute_manual(action_id)
        action = service.get_action(action_id)
        assert action is not None
        assert action["statut"] == "en_cours"

        # Avancer l'horloge interne pour simuler > 5 min
        import time as time_module

        service._current_action_start = time_module.time() - 301  # 5 min 1s

        # Déclencher le poll — doit détecter le timeout
        service._on_poll()

        action = service.get_action(action_id)
        assert action is not None
        assert action["statut"] == "echouee", f"Statut attendu: echouee, obtenu: {action['statut']}"
        assert "Timeout" in (action["erreur"] or "")

    def test_enchainement_fifo(self, service: Any) -> None:
        """Deux actions immédiates s'exécutent l'une après l'autre séquentiellement."""
        id1 = service.create_action(type_="recherche", parametres={"ordre": 1}, mode="immediat")
        id2 = service.create_action(type_="scan", parametres={"ordre": 2}, mode="immediat")

        # 1er _on_poll : démarre la première action (id1)
        service._on_poll()
        action1 = service.get_action(id1)
        assert action1 is not None
        assert action1["statut"] == "en_cours"
        action2 = service.get_action(id2)
        assert action2 is not None
        assert action2["statut"] == "en_attente"

        # Terminer la première action
        service.complete_action(id1, succes=True)

        # 2e _on_poll : démarre la deuxième action (id2)
        service._on_poll()
        action2 = service.get_action(id2)
        assert action2 is not None
        assert action2["statut"] == "en_cours"

        # Terminer la deuxième action
        service.complete_action(id2, succes=True)
        action2 = service.get_action(id2)
        assert action2 is not None
        assert action2["statut"] == "terminee"

    def test_actions_bloquantes_execute_manual(self, service: Any) -> None:
        """execute_manual est bloqué si un même type est déjà en_cours."""
        id1 = service.create_action(type_="recherche", parametres={"q": "alpha"}, mode="immediat")
        id2 = service.create_action(type_="recherche", parametres={"q": "beta"}, mode="immediat")

        # Lancer la première
        service.execute_manual(id1)
        assert service.get_action(id1)["statut"] == "en_cours"  # type: ignore[union-attr]

        # Tenter de lancer la seconde (même type) → bloquée silencieusement
        service.execute_manual(id2)
        assert service.get_action(id2)["statut"] == "en_attente"  # type: ignore[union-attr]

    def test_actions_bloquantes_poll(self, service: Any) -> None:
        """_on_poll saute les actions dont le type est bloqué (même type en_cours dans la DB)."""
        id1 = service.create_action(type_="recherche", parametres={"q": "a"}, mode="immediat")
        id2 = service.create_action(type_="recherche", parametres={"q": "b"}, mode="immediat")
        id3 = service.create_action(type_="scan", parametres={}, mode="immediat")

        # Démarrer id1 manuellement
        service.execute_manual(id1)
        assert service.get_action(id1)["statut"] == "en_cours"  # type: ignore[union-attr]

        # Simuler un état où _current_action_id est perdu mais la DB montre encore
        # une action 'recherche' en_cours
        service._current_action_id = None
        service._current_action_start = None

        # _on_poll doit sauter id2 (recherche bloquée car id1 est encore en_cours dans la DB)
        # et prendre id3 (scan, type différent)
        service._on_poll()
        assert service.get_action(id2)["statut"] == "en_attente"  # type: ignore[union-attr]
        assert service.get_action(id3)["statut"] == "en_cours"  # type: ignore[union-attr]

    def test_actions_non_bloquantes_types_differents(self, service: Any) -> None:
        """execute_manual bloque aussi si une action est déjà en cours (séquentiel), même de type différent."""
        id1 = service.create_action(type_="recherche", parametres={}, mode="immediat")
        id2 = service.create_action(type_="scan", parametres={}, mode="immediat")

        service.execute_manual(id1)
        assert service.get_action(id1)["statut"] == "en_cours"  # type: ignore[union-attr]

        # Bloqué par _current_action_id, même si le type est différent
        service.execute_manual(id2)
        assert service.get_action(id2)["statut"] == "en_attente"  # type: ignore[union-attr]

    def test_max_retries_echoue(self, service: Any) -> None:
        """Après 3 échecs, l'action est marquée echouee."""
        action_id = service.create_action(type_="recherche", parametres={}, mode="immediat")

        # Simuler 3 échecs sans passer par execute_manual (qui reset nb_tentatives)
        for i in range(3):
            service._db.update_action(action_id, statut="en_cours")
            service.complete_action(action_id, succes=False, erreur=f"Tentative {i + 1} échouée")

        action = service.get_action(action_id)
        assert action is not None
        assert action["statut"] == "echouee", f"Attendu echouee, obtenu {action['statut']}"
        assert action["nb_tentatives"] == 3

    def test_backoff_retry(self, service: Any) -> None:
        """Un échec replanifie l'action avec un délai de backoff et incrémente nb_tentatives."""
        action_id = service.create_action(type_="nettoyage", parametres={}, mode="immediat")

        # Démarrer via execute_manual (reset nb_tentatives)
        service.execute_manual(action_id)
        service.complete_action(action_id, succes=False, erreur="Erreur réseau")

        action = service.get_action(action_id)
        assert action is not None

        # Doit être replanifiée (1 tentative seulement → pas echouee)
        assert action["statut"] == "planifiee"
        assert action["nb_tentatives"] == 1
        assert "Erreur réseau" in (action["erreur"] or "")

        # prochaine_execution doit être dans ~30s (backoff[0] = 30s)
        assert action["prochaine_execution"] is not None

    def test_backoff_progressif(self, service: Any) -> None:
        """Les délais de backoff augmentent (30s → 2min → 5min) jusqu'à l'échec final."""
        action_id = service.create_action(type_="scan", parametres={}, mode="immediat")

        # Tentative 1 : nb_tentatives=0 → 1, backoff 30s, statut=planifiee
        service._db.update_action(action_id, statut="en_cours")
        service.complete_action(action_id, succes=False)
        action = service.get_action(action_id)
        assert action is not None
        assert action["statut"] == "planifiee"
        next1 = datetime.strptime(action["prochaine_execution"], "%Y-%m-%d %H:%M:%S")  # type: ignore[arg-type]

        # Tentative 2 : nb_tentatives=1 → 2, backoff 120s, statut=planifiee
        service._db.update_action(action_id, statut="en_cours")
        service.complete_action(action_id, succes=False)
        action = service.get_action(action_id)
        assert action is not None
        assert action["statut"] == "planifiee"
        next2 = datetime.strptime(action["prochaine_execution"], "%Y-%m-%d %H:%M:%S")  # type: ignore[arg-type]
        assert (next2 - next1).total_seconds() > 60, f"next2-next1 = {(next2 - next1).total_seconds()}s, attendu > 60"

        # Tentative 3 : nb_tentatives=2 → 3, echouee (max atteint)
        service._db.update_action(action_id, statut="en_cours")
        service.complete_action(action_id, succes=False)
        action = service.get_action(action_id)
        assert action is not None
        assert action["statut"] == "echouee", f"Attendu echouee après 3 tentatives, obtenu {action['statut']}"
        assert action["nb_tentatives"] == 3

    def test_priorite_immediat_sur_planifie(self, service: Any) -> None:
        """Une action immédiate est exécutée avant une action planifiée (même si la planifiée est due avant)."""
        # Créer d'abord une action planifiée, PUIS une immédiate
        passee = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        planifiee_id = service.create_action(
            type_="scan",
            parametres={},
            mode="planifie",
            prochaine_execution=passee,
        )
        immediat_id = service.create_action(type_="recherche", parametres={}, mode="immediat")

        # _on_poll doit prendre l'immédiate en premier (priorité FIFO)
        service._on_poll()

        immediat = service.get_action(immediat_id)
        assert immediat is not None
        assert immediat["statut"] == "en_cours", (
            f"L'action immédiate devrait être en_cours, obtenu {immediat['statut']}"
        )

        planifiee = service.get_action(planifiee_id)
        assert planifiee is not None
        assert planifiee["statut"] == "planifiee", "L'action planifiée devrait rester planifiee (pas encore exécutée)"

    def test_planifiee_non_due_ignoree(self, service: Any) -> None:
        """Une action planifiée dans le futur n'est pas récupérée par get_actions_dues."""
        future = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        service.create_action(
            type_="wishlist",
            parametres={},
            mode="planifie",
            prochaine_execution=future,
        )

        dues = service._db.get_actions_dues()
        assert len(dues) == 0, "Aucune action due dans le futur"

    def test_trois_actions_fifo(self, service: Any) -> None:
        """3 actions immédiates s'exécutent dans l'ordre FIFO."""
        ids: list[int] = []
        for i in range(3):
            aid = service.create_action(type_="recherche", parametres={"ordre": i}, mode="immediat")
            ids.append(aid)

        for idx, aid in enumerate(ids):
            service._on_poll()
            action = service.get_action(aid)
            assert action is not None
            assert action["statut"] == "en_cours", (
                f"Action {idx} (id={aid}) devrait être en_cours, obtenu {action['statut']}"
            )
            service.complete_action(aid, succes=True)

        # Vérifier que toutes sont terminées
        for aid in ids:
            action = service.get_action(aid)
            assert action is not None
            assert action["statut"] == "terminee"


class TestPurge:
    """Purge automatique des actions de plus de 7 jours."""

    def test_purge_garde_recente(self, service: Any) -> None:
        """Une action terminée récemment (< 7 jours) n'est pas supprimée par la purge."""
        action_id = service.create_action(type_="nettoyage", parametres={}, mode="immediat")
        service._db.update_action(
            action_id,
            statut="terminee",
            date_execution=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        purged = service._db.purge_old()
        assert purged == 0, "L'action récente ne devrait pas être purgée"
        assert service.get_action(action_id) is not None

    def test_purge_supprime_ancienne(self, service: Any) -> None:
        """Une action terminée il y a > 7 jours est supprimée par la purge."""
        service._db.update_action(
            service.create_action(type_="scan", parametres={}, mode="immediat"),
            statut="terminee",
            date_execution=(datetime.now() - timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S"),
        )
        service._db.update_action(
            service.create_action(type_="recherche", parametres={}, mode="immediat"),
            statut="echouee",
            erreur="Ancien échec",
            date_execution=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S"),
        )

        purged = service._db.purge_old()
        assert purged == 2, "Les 2 actions anciennes devraient être purgées"

    def test_purge_ne_touche_pas_en_cours(self, service: Any) -> None:
        """Une action en_cours (même vieille) n'est pas supprimée."""
        action_id = service.create_action(type_="optimisation", parametres={}, mode="immediat")
        service._db.update_action(
            action_id,
            statut="en_cours",
            date_execution=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S"),
        )

        purged = service._db.purge_old()
        assert purged == 0, "Les actions en_cours ne doivent pas être purgées"
        assert service.get_action(action_id) is not None

    def test_purge_ne_supprime_pas_sans_date(self, service: Any) -> None:
        """Une action terminee sans date_execution n'est pas supprimée."""
        action_id = service.create_action(type_="wishlist", parametres={}, mode="immediat")
        service._db.update_action(action_id, statut="terminee")
        # Ne pas définir date_execution → reste NULL

        purged = service._db.purge_old()
        assert purged == 0
        assert service.get_action(action_id) is not None

    def test_force_purge(self, service: Any) -> None:
        """force_purge() déclenche la purge et retourne le nombre supprimé."""
        service._db.update_action(
            service.create_action(type_="nettoyage", parametres={}, mode="immediat"),
            statut="terminee",
            date_execution=(datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S"),
        )

        deleted = service.force_purge()
        assert deleted == 1

    def test_purge_ignore_planifiee(self, service: Any) -> None:
        """Les actions planifiées ne sont jamais purgées."""
        future = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        action_id = service.create_action(
            type_="recherche",
            parametres={},
            mode="planifie",
            prochaine_execution=future,
        )

        purged = service._db.purge_old()
        assert purged == 0
        assert service.get_action(action_id) is not None


class TestSignaux:
    """Émission des signaux action_changed lors des changements de statut."""

    @pytest.fixture(autouse=True)
    def _setup_spy(self, service: Any) -> Generator[None, None, None]:
        """Ajoute un spy sur le signal action_changed avant chaque test."""
        self._signals: list[tuple[int, str, str]] = []  # type: ignore[attr-defined]

        def _spy(aid: int, atype: str, statut: str) -> None:
            self._signals.append((aid, atype, statut))  # type: ignore[attr-defined]

        service.action_changed.connect(_spy)
        yield

    def _assert_signal(self, action_id: int, action_type: str, statut: str) -> None:
        """Vérifie qu'un signal spécifique a été émis."""
        assert (action_id, action_type, statut) in self._signals, (
            f"Signal ({action_id}, {action_type}, {statut}) non trouvé parmi {self._signals}"
        )  # type: ignore[attr-defined]

    def _assert_no_signal(self, action_id: int, action_type: str, statut: str) -> None:
        """Vérifie qu'un signal spécifique n'a PAS été émis."""
        assert (action_id, action_type, statut) not in self._signals, (
            f"Signal ({action_id}, {action_type}, {statut})不应该 être émis, mais trouvé"
        )  # type: ignore[attr-defined]

    def test_signal_creation_immediat(self, service: Any) -> None:
        """La création d'une action immédiate émet le signal 'en_attente'."""
        aid = service.create_action(type_="recherche", parametres={}, mode="immediat")
        self._assert_signal(aid, "recherche", "en_attente")

    def test_signal_creation_planifie(self, service: Any) -> None:
        """La création d'une action planifiée émet le signal 'planifiee'."""
        future = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        aid = service.create_action(
            type_="scan",
            parametres={},
            mode="planifie",
            prochaine_execution=future,
        )
        self._assert_signal(aid, "scan", "planifiee")

    def test_signal_execution_manuelle(self, service: Any) -> None:
        """execute_manual émet le signal 'en_cours'."""
        aid = service.create_action(type_="nettoyage", parametres={}, mode="immediat")
        service.execute_manual(aid)
        self._assert_signal(aid, "nettoyage", "en_cours")

    def test_signal_completion_succes(self, service: Any) -> None:
        """complete_action(succes=True) émet le signal 'terminee'."""
        aid = service.create_action(type_="scan", parametres={}, mode="immediat")
        service.execute_manual(aid)
        service.complete_action(aid, succes=True)
        self._assert_signal(aid, "scan", "terminee")

    def test_signal_echec_retry(self, service: Any) -> None:
        """Un premier échec émet 'planifiee' (replanifié pour backoff)."""
        aid = service.create_action(type_="recherche", parametres={}, mode="immediat")
        service.execute_manual(aid)
        service.complete_action(aid, succes=False, erreur="Test")
        self._assert_signal(aid, "recherche", "planifiee")

    def test_signal_echec_final(self, service: Any) -> None:
        """Après 3 échecs, le signal 'echouee' est émis."""
        aid = service.create_action(type_="recherche", parametres={}, mode="immediat")
        for _ in range(3):
            service._db.update_action(aid, statut="en_cours")
            service.complete_action(aid, succes=False)
        self._assert_signal(aid, "recherche", "echouee")

    def test_signal_update_statut(self, service: Any) -> None:
        """update_action avec changement de statut émet le signal."""
        aid = service.create_action(type_="nettoyage", parametres={}, mode="immediat")
        service.update_action(aid, statut="pause")
        self._assert_signal(aid, "nettoyage", "pause")

    def test_pas_de_signal_sans_changement_statut(self, service: Any) -> None:
        """update_action sans paramètre 'statut' n'émet PAS de signal."""
        aid = service.create_action(type_="recherche", parametres={"original": True}, mode="immediat")
        # Nettoyer les signaux de création
        self._signals.clear()  # type: ignore[attr-defined]

        # Modifier seulement les paramètres (pas de statut)
        service.update_action(aid, parametres={"modifié": True})

        # Aucun nouveau signal ne devrait être émis
        assert len(self._signals) == 0, f"Aucun signal attendu, mais {len(self._signals)} émis"

    def test_signal_recurrence_replanifie(self, service: Any) -> None:
        """Une action récurrente réussie émet 'planifiee' (pas 'terminee')."""
        aid = service.create_action(
            type_="recherche",
            parametres={},
            mode="immediat",
            recurrence_interval=1,
            recurrence_unite="heures",
        )
        service.execute_manual(aid)
        service.complete_action(aid, succes=True)

        # Ne doit PAS émettre 'terminee' (récurrente → replanifiée)
        self._assert_no_signal(aid, "recherche", "terminee")
        # Doit émettre 'planifiee'
        self._assert_signal(aid, "recherche", "planifiee")


class TestEventBusEmission:
    """Vérifie que les événements EventBus sont émis aux 4 points de vie."""

    @pytest.fixture(autouse=True)
    def _setup_spy(self) -> Generator[None, None, None]:
        """Espionne les événements EventBus émis via event_emitted."""
        from src.services.event_bus import EventBus, SurveillanceEvent

        self._events: list[SurveillanceEvent] = []

        def _spy(event: SurveillanceEvent) -> None:
            self._events.append(event)

        bus = EventBus()
        bus.event_emitted.connect(_spy)
        yield
        try:
            bus.event_emitted.disconnect(_spy)
        except Exception:
            pass

    def _assert_event(self, title: str, severity: str, action_id: int, action_type: str) -> None:
        """Vérifie qu'un événement EventBus a été émis avec les bons attributs."""
        for ev in self._events:
            if (
                ev.title == title
                and ev.severity == severity
                and ev.details
                and ev.details.get("action_id") == action_id
            ):
                assert ev.details.get("action_type") == action_type, (
                    f"Type attendu: {action_type}, obtenu: {ev.details.get('action_type')}"
                )
                assert ev.category == "bot"
                assert ev.source == "planificateur"
                return
        summary = [(e.title, e.severity, e.details.get("action_id") if e.details else None) for e in self._events]
        pytest.fail(
            f"Événement ({title}, {severity}, action_id={action_id}) non trouvé "
            f"parmi {len(self._events)} événements: {summary}"
        )

    # ── 1. Création ───────────────────────────────────────────────────────

    def test_event_creation_immediat(self, service: Any) -> None:
        """create_action(mode='immediat') émet action_en_attente."""
        aid = service.create_action(type_="recherche", parametres={}, mode="immediat")
        self._assert_event("planificateur.action_en_attente", "INFO", aid, "recherche")

    def test_event_creation_planifie(self, service: Any) -> None:
        """create_action(mode='planifie') émet action_planifiee."""
        future = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        aid = service.create_action(
            type_="scan",
            parametres={},
            mode="planifie",
            prochaine_execution=future,
        )
        self._assert_event("planificateur.action_planifiee", "INFO", aid, "scan")

    # ── 2. Démarrage ──────────────────────────────────────────────────────

    def test_event_execution_manuelle(self, service: Any) -> None:
        """execute_manual émet action_demarree (manuelle)."""
        aid = service.create_action(type_="nettoyage", parametres={}, mode="immediat")
        service.execute_manual(aid)
        self._assert_event("planificateur.action_demarree", "INFO", aid, "nettoyage")

    def test_event_execution_automatique(self, service: Any) -> None:
        """_on_poll émet action_demarree (automatique)."""
        aid = service.create_action(type_="scan", parametres={}, mode="immediat")
        service._on_poll()
        self._assert_event("planificateur.action_demarree", "INFO", aid, "scan")

    # ── 3. Succès ─────────────────────────────────────────────────────────

    def test_event_completion_succes(self, service: Any) -> None:
        """complete_action(succes=True) émet action_terminee."""
        aid = service.create_action(type_="scan", parametres={}, mode="immediat")
        service.execute_manual(aid)
        service.complete_action(aid, succes=True)
        self._assert_event("planificateur.action_terminee", "INFO", aid, "scan")

    def test_event_recurrence_replanifie(self, service: Any) -> None:
        """Récurrente réussie émet action_terminee (replanifiée)."""
        aid = service.create_action(
            type_="recherche",
            parametres={},
            mode="immediat",
            recurrence_interval=1,
            recurrence_unite="heures",
        )
        service.execute_manual(aid)
        service.complete_action(aid, succes=True)
        self._assert_event("planificateur.action_terminee", "INFO", aid, "recherche")

    # ── 4. Échec ──────────────────────────────────────────────────────────

    def test_event_echec_retry(self, service: Any) -> None:
        """1 échec → action_echouee (WARN, réessai)."""
        aid = service.create_action(type_="recherche", parametres={}, mode="immediat")
        service.execute_manual(aid)
        service.complete_action(aid, succes=False, erreur="Test erreur")
        self._assert_event("planificateur.action_echouee", "WARN", aid, "recherche")

    def test_event_echec_final(self, service: Any) -> None:
        """3 échecs → action_echouee (ERROR, final)."""
        aid = service.create_action(type_="nettoyage", parametres={}, mode="immediat")
        for _ in range(3):
            service._db.update_action(aid, statut="en_cours")
            service.complete_action(aid, succes=False)
        self._assert_event("planificateur.action_echouee", "ERROR", aid, "nettoyage")
