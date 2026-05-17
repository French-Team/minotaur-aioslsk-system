"""Tests unitaires pour le CLI Ordonnanceur (src/cli_ordonnanceur.py)."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.cli_ordonnanceur import (
    _parser,
    _taille_lisible,
    afficher_apercu_console,
    main,
)


class TestTailleLisible:
    """Tests du formateur de taille."""

    def test_octets(self) -> None:
        assert _taille_lisible(0) == "0 o"
        assert _taille_lisible(512) == "512 o"
        assert _taille_lisible(1023) == "1023 o"

    def test_kilo_octets(self) -> None:
        assert _taille_lisible(1024) == "1.0 Ko"
        assert _taille_lisible(1536) == "1.5 Ko"
        assert _taille_lisible(1024 * 1024 - 1) == "1024.0 Ko"

    def test_mega_octets(self) -> None:
        taille = 1024 * 1024
        assert _taille_lisible(taille) == "1.0 Mo"
        assert _taille_lisible(taille * 10) == "10.0 Mo"

    def test_giga_octets(self) -> None:
        taille = 1024 * 1024 * 1024
        assert _taille_lisible(taille) == "1.00 Go"
        assert _taille_lisible(taille * 2) == "2.00 Go"


class TestParser:
    """Tests du parseur d'arguments."""

    def test_dossier_obligatoire(self) -> None:
        parser = _parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_dossier_positionnel(self) -> None:
        parser = _parser()
        args = parser.parse_args(["/tmp/music"])
        assert args.dossier == "/tmp/music"

    def test_ops_defaut_toutes(self) -> None:
        parser = _parser()
        args = parser.parse_args(["/tmp/music"])
        assert args.ops is None  # None = toutes les ops

    def test_ops_personnalisees(self) -> None:
        parser = _parser()
        args = parser.parse_args(["/tmp/music", "--ops", "renommage", "--ops", "classement"])
        assert args.ops == ["renommage", "classement"]

    def test_options_passees(self) -> None:
        parser = _parser()
        args = parser.parse_args(
            [
                "/tmp/music",
                "--template-renommage",
                "{artist}.{ext}",
                "--racine-classement",
                "/music",
                "--age-max",
                "14",
                "--no-resoudre-conflits",
                "--no-recursive",
            ]
        )
        assert args.template_renommage == "{artist}.{ext}"
        assert args.racine_classement == "/music"
        assert args.age_max == 14
        assert args.no_resoudre_conflits is True
        assert args.recursive is False


class TestAfficherApercuConsole:
    """Tests de l'affichage console."""

    @pytest.fixture
    def apercu_vide(self) -> dict[str, Any]:
        return {
            "resume": {
                "total_fichiers_confernes": 0,
                "total_taille_economisee": 0,
                "total_taille_lisible": "0 o",
            },
        }

    @pytest.fixture
    def apercu_complet(self) -> dict[str, Any]:
        from src.services.ordonnanceur_service import FichierInfo

        return {
            "renommage": {
                "fichiers": [
                    {
                        "info": FichierInfo(
                            path=Path("a.mp3"),
                            filename="a.mp3",
                            extension=".mp3",
                            size=1000,
                            modified=0.0,
                            artist="A",
                            album="B",
                            title="T",
                        ),
                        "nom_actuel": "a.mp3",
                        "nouveau_nom": "A - B - 01 T.mp3",
                    },
                    {
                        "info": FichierInfo(
                            path=Path("b.mp3"),
                            filename="b.mp3",
                            extension=".mp3",
                            size=2000,
                            modified=0.0,
                            artist="A",
                            album="B",
                            title="T2",
                        ),
                        "nom_actuel": "b.mp3",
                        "nouveau_nom": "A - B - 02 T2.mp3",
                    },
                ],
                "total": 2,
                "conflits": [],
                "conflits_resolus": [],
                "exemples": [],
            },
            "classement": {
                "fichiers": [
                    {
                        "info": FichierInfo(
                            path=Path("a.mp3"),
                            filename="a.mp3",
                            extension=".mp3",
                            size=1000,
                            modified=0.0,
                            artist="A",
                            album="B",
                            title="T",
                        ),
                        "chemin_actuel": "a.mp3",
                        "nouveau_chemin": Path("A/B/01 T.mp3"),
                        "artiste": "A",
                    },
                ],
                "total": 1,
                "nb_artistes": 1,
                "artistes": {"A": 1},
                "conflits": [],
                "conflits_resolus": [],
                "exemples": [],
            },
            "deduplication": {
                "groupes": [
                    {
                        "garde": FichierInfo(
                            path=Path("a.mp3"), filename="a.mp3", extension=".mp3", size=1000, modified=0.0
                        ),
                        "supprimables": [
                            FichierInfo(path=Path("b.mp3"), filename="b.mp3", extension=".mp3", size=1000, modified=0.0)
                        ],
                        "taille_economisee": 1000,
                    }
                ],
                "total_doublons": 1,
                "total_economise": 1000,
                "total_lisible": "1.0 Ko",
                "nb_groupes": 1,
                "conflits": [],
                "conflits_resolus": [],
            },
            "nettoyage": {
                "fichiers": [
                    {"path": Path("/tmp/cache.bin"), "size": 5000, "modified": 0.0},
                ],
                "total": 1,
                "taille_totale": 5000,
                "total_lisible": "5.0 Ko",
            },
            "resume": {
                "total_fichiers_confernes": 4,
                "total_taille_economisee": 6000,
                "total_taille_lisible": "6.0 Ko",
            },
        }

    def test_apercu_vide(self, apercu_vide: dict[str, Any]) -> None:
        """Aucune operation selectionnee -> resume seulement."""
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            afficher_apercu_console(apercu_vide, chemin_dossier="/test")
        output = buf.getvalue()
        assert "APERCU DES OPERATIONS" in output
        assert "RESUME" in output
        assert "0 fichiers" in output

    def test_apercu_complet(self, apercu_complet: dict[str, Any]) -> None:
        """Toutes les sections affichees avec leurs donnees."""
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            afficher_apercu_console(apercu_complet, chemin_dossier="/test")
        output = buf.getvalue()
        assert "Renommage" in output
        assert "Classement" in output
        assert "Dedoublonnage" in output
        assert "Nettoyage" in output
        assert "A - B - 01 T.mp3" in output
        # Sur Windows les Path utilisent \, donc on cherche le nom du fichier
        assert "01 T.mp3" in output
        assert "4 fichiers" in output
        assert "6.0 Ko" in output

    def test_apercu_sans_dossier(self, apercu_vide: dict[str, Any]) -> None:
        """Pas de chemin dossier -> pas de ligne Dossier."""
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            afficher_apercu_console(apercu_vide)
        output = buf.getvalue()
        assert "Dossier" not in output

    def test_apercu_operations_vides(self) -> None:
        """Sections avec 0 fichiers -> message info."""
        apercu: dict[str, Any] = {
            "renommage": {"fichiers": [], "total": 0, "conflits": [], "conflits_resolus": [], "exemples": []},
            "deduplication": {
                "groupes": [],
                "total_doublons": 0,
                "total_economise": 0,
                "total_lisible": "0 o",
                "nb_groupes": 0,
                "conflits": [],
                "conflits_resolus": [],
            },
            "resume": {"total_fichiers_confernes": 0, "total_taille_economisee": 0, "total_taille_lisible": "0 o"},
        }
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            afficher_apercu_console(apercu)
        output = buf.getvalue()
        assert "Aucun fichier a renommer" in output
        assert "Aucun doublon detecte" in output


class TestMain:
    """Tests du point d'entree main()."""

    def test_dossier_inexistant(self) -> None:
        """Dossier qui n'existe pas -> code 1 + message erreur."""
        buf = io.StringIO()
        with patch("sys.stderr", buf):
            code = main(["/tmp/ce_dossier_n_existe_pas_12345"])
        assert code == 1
        assert "n'existe pas" in buf.getvalue()

    def test_aide(self) -> None:
        """--help -> code 0."""
        with pytest.raises(SystemExit) as exc:
            _parser().parse_args(["--help"])
        assert exc.value.code == 0

    def test_dossier_valide(self, tmp_path: Path) -> None:
        """Dossier valide avec fichiers -> apercu affiche."""
        (tmp_path / "song_a.mp3").write_text("data")
        (tmp_path / "song_b.mp3").write_text("data")
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = main([str(tmp_path), "--ops", "renommage"])
        assert code == 0
        output = buf.getvalue()
        assert "APERCU DES OPERATIONS" in output
        assert "Renommage" in output
        assert "RESUME" in output
