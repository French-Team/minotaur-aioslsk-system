"""Fixtures partagées pour les tests."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Generator

import pytest
from PySide6.QtWidgets import QApplication
from pytest import FixtureRequest, MonkeyPatch

# ── QApplication (nécessaire pour les widgets Qt) ────────────────


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Crée une instance QApplication unique pour toute la session de test.

    Nécessaire pour instancier des widgets Qt (QFrame, QPushButton, etc.)
    sans serveur d'affichage.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    assert isinstance(app, QApplication)
    return app


# ── Répertoire temporaire pour les données de test ────────────────


@pytest.fixture
def tmp_data_dir(monkeypatch: MonkeyPatch) -> Generator[Path, None, None]:
    """Crée un répertoire ``data/`` temporaire et l'injecte via monkeypatch.

    Utile pour les tests qui écrivent des fichiers dans ``data/``
    (notamment ``SearchHistory``).
    """
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp) / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        # On ne monkeypatch pas globalement — chaque test le fait au besoin
        yield data_dir


# ── Fichier app_config temporaire ─────────────────────────────────


@pytest.fixture
def tmp_app_config(monkeypatch: MonkeyPatch) -> Generator[Path, None, None]:
    """Crée un fichier ``app_config.json`` temporaire avec les valeurs par défaut.

    Monkeypatche ``src.services.app_config._CONFIG_FILE`` pour que les
    appels à ``app_config.get/set`` pointent vers ce fichier temporaire.
    """
    config_path = Path(tempfile.mktemp(suffix="_test_config.json"))

    # Écrire les valeurs par défaut (celles du module app_config)
    defaults: dict[str, Any] = {
        "general.scan_on_start": True,
        "general.description_profil": "",
        "general.photo_profil": "",
        "general.interets_aimes": "",
        "general.interets_detestes": "",
        "reseau.upnp": False,
        "reseau.port_ecoute": 60000,
        "reseau.port_obfusque": 60001,
        "reseau.obfuscation_p2p": False,
        "reseau.mode_connexion_peer": "race",
        "reseau.limite_upload_kbps": 0,
        "reseau.limite_download_kbps": 0,
        "reseau.reconnexion_auto": False,
        "reseau.reconnexion_timeout": 10,
        "reseau.hote_serveur": "server.slsknet.org",
        "reseau.port_serveur": 2416,
        "reseau.mode_erreur_ecoute": "clear",
        "reseau.duree_bail_upnp": 21600,
        "reseau.intervalle_upnp": 600,
        "reseau.timeout_upnp": 10,
        "recherche.nb_resultats_max": 100,
        "recherche.nb_max_memoire": 500,
        "recherche.stocker_resultats": True,
        "recherche.timeout_requete": 0,
        "recherche.timeout_souhaits": -1,
        "recherche.souhaits": "",
        "telechargement.slots_upload": 2,
        "telechargement.dossier_destination": "",
        "telechargement.intervalle_rapport": 250,
        "utilisateurs.liste_amis": "",
        "utilisateurs.liste_bloques": "",
        "partages.dossier_1_chemin": "",
        "partages.dossier_1_mode": "everyone",
        "partages.dossier_1_utilisateurs": "",
        "partages.dossier_2_chemin": "",
        "partages.dossier_2_mode": "everyone",
        "partages.dossier_2_utilisateurs": "",
        "salons.auto_join": True,
        "salons.invitations_privees": True,
        "salons.favoris": "",
        "debug.search_for_parent": False,
        "debug.ip_overrides": "",
        "debug.log_connection_count": False,
    }
    config_path.write_text(json.dumps(defaults), encoding="utf-8")

    # Rediriger app_config vers notre fichier temporaire
    import src.services.app_config as app_config_module

    monkeypatch.setattr(app_config_module, "_CONFIG_FILE", config_path)
    monkeypatch.setattr(app_config_module, "_config", None)  # force reload

    yield config_path

    # Nettoyage
    if config_path.exists():
        config_path.unlink()


@pytest.fixture
def tmp_bot_assistant_db(tmp_path: Path) -> str:
    """Crée un chemin temporaire pour bot_assistant.db."""
    db_dir = tmp_path / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "bot_assistant.db"
    return str(db_path)
