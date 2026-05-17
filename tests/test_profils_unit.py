"""Tests unitaires pour _valide_profil().

Utilise des fixtures de profils JSON temporaires pour tester :
- Profil valide (cles existantes dans _DEFAULTS + _CAT_TO_PAGE)
- Categorie inconnue (absente de _CAT_TO_PAGE)
- Cle manquante (absente de _DEFAULTS)
- Type mismatch (valeur de type different de _DEFAULTS)
- JSON invalide (fichier malforme)
- Structure manquante (pas de cle "params")
- params non dict
- Categorie avec valeur non dict

Utilise ``tmp_path`` (pytest built-in) pour les fichiers temporaires,
et importe directement ``_valide_profil`` depuis ``scripts.validate_profils``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.validate_profils import _valide_profil

# ── Helpers ──────────────────────────────────────────


def _ecrire_profil(tmp_path: Path, params: dict[str, Any], nom: str = "profil") -> str:
    """Ecrit un profil JSON temporaire et retourne son chemin absolu."""
    chemin = tmp_path / f"{nom}.json"
    chemin.write_text(json.dumps({"params": params}, ensure_ascii=False), encoding="utf-8")
    return str(chemin)


# ── Tests ────────────────────────────────────────────


class TestProfilValide:
    """Cas nominal : profil dont toutes les cles existent dans _DEFAULTS et _CAT_TO_PAGE."""

    def test_toutes_cles_valides(self, tmp_path: Path) -> None:
        """Un profil avec des cles reconnues ne produit ni erreur ni warning."""
        params = {
            "general": {"scan_on_start": True},
            "reseau": {"port_ecoute": 60000, "hote_serveur": "server.slsknet.org"},
        }
        chemin = _ecrire_profil(tmp_path, params)
        nb_ok, nb_cles, warns, errs = _valide_profil(chemin)

        assert errs == []
        assert warns == []
        assert nb_ok == 3  # 3 cles valides reconnues
        assert nb_cles == 3  # 3 cles parcourues

    def test_profil_complet(self, tmp_path: Path) -> None:
        """Un profil avec toutes les categories valides passe sans erreur ni warning."""
        params = {
            "general": {"scan_on_start": True},
            "reseau": {"hote_serveur": "server.slsknet.org"},
            "recherche": {"nb_resultats_max": 100},
            "telechargement": {"slots_upload": 2},
            "utilisateurs": {"liste_amis": ""},
            "partages": {"dossier_1_chemin": ""},
            "salons": {"auto_join": True},
            "debug": {"search_for_parent": False},
        }
        chemin = _ecrire_profil(tmp_path, params)
        nb_ok, nb_cles, warns, errs = _valide_profil(chemin)

        assert errs == []
        assert warns == []
        assert nb_ok == nb_cles  # toutes les cles sont valides
        assert nb_cles == 8


class TestCategorieInconnue:
    """Categories absentes de _CAT_TO_PAGE."""

    def test_categorie_inconnue_produit_erreur(self, tmp_path: Path) -> None:
        """Une categorie qui n'est pas dans _CAT_TO_PAGE doit generer une erreur."""
        params = {"categorie_inexistante": {"foo": "bar"}}
        chemin = _ecrire_profil(tmp_path, params)
        nb_ok, nb_cles, warns, errs = _valide_profil(chemin)

        assert len(errs) == 1
        assert "Categorie inconnue" in errs[0]
        assert "categorie_inexistante" in errs[0]
        assert warns == []
        assert nb_ok == 0

    def test_categorie_inconnue_avec_valide(self, tmp_path: Path) -> None:
        """Une categorie valide est traitee meme en presence d'une categorie inconnue."""
        params = {
            "general": {"scan_on_start": True},
            "fake_category": {"some_key": 123},
        }
        chemin = _ecrire_profil(tmp_path, params)
        nb_ok, nb_cles, warns, errs = _valide_profil(chemin)

        assert len(errs) == 1  # seulement la fake_category
        assert errs[0].startswith("[fake_category]")
        assert warns == []
        assert nb_ok == 1  # general.scan_on_start est valide


class TestCleManquante:
    """Cles absentes de _DEFAULTS."""

    def test_cle_inconnue_produit_warning(self, tmp_path: Path) -> None:
        """Une cle qui n'est pas dans _DEFAULTS produit un warning (pas une erreur)."""
        params = {"general": {"cle_qui_n_existe_pas": "valeur_quelconque"}}
        chemin = _ecrire_profil(tmp_path, params)
        nb_ok, nb_cles, warns, errs = _valide_profil(chemin)

        assert errs == []
        assert len(warns) == 1
        assert "n'existe PAS dans _DEFAULTS" in warns[0]
        assert nb_ok == 0

    def test_cle_inconnue_avec_valide(self, tmp_path: Path) -> None:
        """Les cles valides sont comptees meme en presence d'une cle inconnue."""
        params = {"reseau": {"port_ecoute": 60000, "toto_magique": "valeur"}}
        chemin = _ecrire_profil(tmp_path, params)
        nb_ok, nb_cles, warns, errs = _valide_profil(chemin)

        assert errs == []
        assert len(warns) == 1
        assert "toto_magique" in warns[0]
        assert nb_ok == 1  # port_ecoute est valide


class TestTypeMismatch:
    """Valeurs de type different de _DEFAULTS."""

    def test_string_au_lieu_de_bool(self, tmp_path: Path) -> None:
        """Un bool attendu mais un string fourni produit un warning."""
        params = {"general": {"scan_on_start": "True"}}  # str au lieu de bool
        chemin = _ecrire_profil(tmp_path, params)
        nb_ok, nb_cles, warns, errs = _valide_profil(chemin)

        assert errs == []
        assert len(warns) == 1
        assert "attendu" in warns[0]
        assert "str" in warns[0]
        assert nb_ok == 1  # la cle est reconnue, seul le type differe

    def test_int_au_lieu_de_str(self, tmp_path: Path) -> None:
        """Un string attendu mais un int fourni produit un warning."""
        params = {"reseau": {"hote_serveur": 42}}  # int au lieu de str
        chemin = _ecrire_profil(tmp_path, params)
        nb_ok, nb_cles, warns, errs = _valide_profil(chemin)

        assert errs == []
        assert len(warns) == 1
        assert "attendu" in warns[0]
        assert "str" in warns[0]

    def test_float_au_lieu_de_int(self, tmp_path: Path) -> None:
        """Un float pour un int est compatible (int/float compatibles)."""
        params = {"reseau": {"port_ecoute": 60000.0}}
        chemin = _ecrire_profil(tmp_path, params)
        nb_ok, nb_cles, warns, errs = _valide_profil(chemin)

        assert errs == []
        assert warns == []  # int/float compatibles -> pas de warning


class TestFichierInvalide:
    """Fichiers JSON malformes ou inexistants."""

    def test_json_invalide(self, tmp_path: Path) -> None:
        """Un fichier non-JSON doit generer une erreur."""
        chemin = tmp_path / "invalide.json"
        chemin.write_text("ceci n'est pas du json valide {{{", encoding="utf-8")
        nb_ok, nb_cles, warns, errs = _valide_profil(str(chemin))

        assert len(errs) == 1
        assert "Impossible de lire" in errs[0]
        assert nb_ok == 0
        assert nb_cles == 0

    def test_fichier_inexistant(self, tmp_path: Path) -> None:
        """Un chemin qui n'existe pas doit generer une erreur."""
        chemin = tmp_path / "nexiste_pas.json"
        nb_ok, nb_cles, warns, errs = _valide_profil(str(chemin))

        assert len(errs) == 1
        assert "Impossible de lire" in errs[0]
        assert nb_ok == 0
        assert nb_cles == 0


class TestStructureInvalide:
    """Structure JSON invalide."""

    def test_sans_params(self, tmp_path: Path) -> None:
        """Un JSON sans la cle 'params' doit generer une erreur."""
        chemin = tmp_path / "sans_params.json"
        chemin.write_text(json.dumps({"nom": "test", "version": 1}), encoding="utf-8")
        nb_ok, nb_cles, warns, errs = _valide_profil(str(chemin))

        assert len(errs) == 1
        assert "params" in errs[0].lower()
        assert nb_ok == 0
        assert nb_cles == 0

    def test_params_non_dict(self, tmp_path: Path) -> None:
        """Un JSON avec 'params' qui n'est pas un dict doit generer une erreur."""
        chemin = tmp_path / "params_liste.json"
        chemin.write_text(json.dumps({"params": [1, 2, 3]}), encoding="utf-8")
        nb_ok, nb_cles, warns, errs = _valide_profil(str(chemin))

        assert len(errs) == 1
        assert "dict" in errs[0].lower() or "dictionnaire" in errs[0]
        assert nb_ok == 0
        assert nb_cles == 0

    def test_params_avec_string(self, tmp_path: Path) -> None:
        """Un JSON avec 'params' qui est une string doit generer une erreur."""
        chemin = tmp_path / "params_string.json"
        chemin.write_text(json.dumps({"params": "je suis une string"}), encoding="utf-8")
        nb_ok, nb_cles, warns, errs = _valide_profil(str(chemin))

        assert len(errs) == 1
        assert "dict" in errs[0].lower() or "dictionnaire" in errs[0]
        assert nb_ok == 0


class TestSousClesNonDict:
    """Categorie dont la valeur n'est pas un dict."""

    def test_categorie_valide_avec_string(self, tmp_path: Path) -> None:
        """Une categorie reconnue mais avec une valeur string produit une erreur."""
        params = {"reseau": "je suis une string directe"}
        chemin = _ecrire_profil(tmp_path, params)
        nb_ok, nb_cles, warns, errs = _valide_profil(chemin)

        assert len(errs) == 1
        assert "dictionnaire" in errs[0]
        assert warns == []
        assert nb_ok == 0

    def test_categorie_inconnue_avec_string(self, tmp_path: Path) -> None:
        """Une categorie inconnue est signalee avant le type non-dict."""
        params = {"fake": "pas un dict"}
        chemin = _ecrire_profil(tmp_path, params)
        nb_ok, nb_cles, warns, errs = _valide_profil(chemin)

        # La categorie inconnue est detectee en premier (check _CAT_TO_PAGE avant isinstance)
        assert len(errs) == 1
        assert "Categorie inconnue" in errs[0]


class TestCompteurs:
    """Verification des compteurs retournes."""

    def test_compteur_cles_parcourues(self, tmp_path: Path) -> None:
        """Le compteur nb_cles doit refleter le nombre exact de cles parcourues."""
        params = {
            "general": {"a": True, "b": False, "c": ""},
            "reseau": {"d": 1, "e": 2},
        }
        chemin = _ecrire_profil(tmp_path, params)
        nb_ok, nb_cles, warns, errs = _valide_profil(chemin)

        assert nb_cles == 5  # 3 + 2 = 5 cles au total
        # general.a/b/c ne sont pas dans _DEFAULTS
        # reseau.d/e ne sont pas dans _DEFAULTS
        assert nb_ok == 0
        assert len(warns) == 5  # chaque cle inconnue genere un warning

    def test_sous_cles_non_dict_comptage(self, tmp_path: Path) -> None:
        """Une categorie non-dict compte pour 1 dans nb_cles."""
        params = {
            "reseau": "pas un dict",
            "general": {"scan_on_start": True},
        }
        chemin = _ecrire_profil(tmp_path, params)
        nb_ok, nb_cles, warns, errs = _valide_profil(chemin)

        # reseau: 1 (non-dict), general: 1 cle
        assert nb_cles == 2
        # reseau est dans _CAT_TO_PAGE, donc l'erreur est sur la valeur non-dict
        assert len(errs) == 1
        assert nb_ok == 1  # general.scan_on_start est valide
