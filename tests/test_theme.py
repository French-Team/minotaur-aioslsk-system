"""Tests pour le module theme : génération du QSS."""

from __future__ import annotations

from src.gui.theme import DARK_THEME


class TestDarkTheme:
    """DARK_THEME : constant de style agrégée depuis les fragments."""

    def test_est_une_chaine(self) -> None:
        """DARK_THEME est une chaîne de caractères."""
        assert isinstance(DARK_THEME, str)

    def test_contient_regles_css(self) -> None:
        """Contient des règles CSS typiques d'un thème Qt."""
        assert "QWidget" in DARK_THEME or "QMainWindow" in DARK_THEME
        assert "{" in DARK_THEME
        assert "}" in DARK_THEME

    def test_placeholders_remplaces(self) -> None:
        """Tous les @KEY@ sont remplacés par des valeurs hexadécimales."""
        assert "@" not in DARK_THEME

    def test_contient_couleurs_hexa(self) -> None:
        """Contient des couleurs hexadécimales (#...)."""
        assert "#" in DARK_THEME

    def test_contient_commentaire(self) -> None:
        """Le thème contient au moins un commentaire CSS (/* ... */)."""
        assert "/*" in DARK_THEME
