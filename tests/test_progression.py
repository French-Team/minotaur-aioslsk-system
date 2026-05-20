"""Tests pour le widget Progression."""

from __future__ import annotations

from src.gui.widgets.progression import ProgressionWidget


class TestProgressionWidget:
    """ProgressionWidget : afficheur de progression multi-mode."""

    def test_creer_widget(self, qapp) -> None:
        """Peut créer un ProgressionWidget."""
        widget = ProgressionWidget()
        assert widget is not None
        assert isinstance(widget, ProgressionWidget)

    def test_mode_initial_percent(self, qapp) -> None:
        """Le mode par défaut est 'percent'."""
        widget = ProgressionWidget()
        assert widget.mode == "percent"

    def test_set_mode_percent(self, qapp) -> None:
        """set_mode('percent') garde le mode percent."""
        widget = ProgressionWidget()
        widget.set_mode("percent")
        assert widget.mode == "percent"
        # La barre de progression est rendue visible (setVisible)
        assert not widget._progress.isHidden()

    def test_set_mode_num(self, qapp) -> None:
        """set_mode('num') change le mode et cache la barre."""
        widget = ProgressionWidget()
        widget.set_mode("num")
        assert widget.mode == "num"
        assert widget._progress.isHidden()

    def test_set_mode_seconds(self, qapp) -> None:
        """set_mode('seconds') fonctionne."""
        widget = ProgressionWidget()
        widget.set_mode("seconds")
        assert widget.mode == "seconds"

    def test_set_mode_actions(self, qapp) -> None:
        """set_mode('actions') fonctionne."""
        widget = ProgressionWidget()
        widget.set_mode("actions")
        assert widget.mode == "actions"

    def test_set_mode_errors(self, qapp) -> None:
        """set_mode('errors') fonctionne."""
        widget = ProgressionWidget()
        widget.set_mode("errors")
        assert widget.mode == "errors"

    def test_set_value_met_a_jour_attribut(self, qapp) -> None:
        """set_value() met à jour _current et _maximum."""
        widget = ProgressionWidget()
        widget.set_value(50)
        assert widget._current == 50
        # set_value fixe _maximum au même palier
        assert widget._maximum >= 50

    def test_set_percentage(self, qapp) -> None:
        """set_percentage() met à jour _current."""
        widget = ProgressionWidget()
        widget.set_percentage(75)
        assert widget._current == 75.0

    def test_set_count(self, qapp) -> None:
        """set_count() met à jour _current."""
        widget = ProgressionWidget()
        widget.set_count(42)
        assert widget._current == 42

    def test_set_actions(self, qapp) -> None:
        """set_actions() met à jour le nombre d'actions."""
        widget = ProgressionWidget()
        widget.set_actions(12)
        assert widget._actions == 12

    def test_set_errors(self, qapp) -> None:
        """set_errors() met à jour le nombre d'erreurs."""
        widget = ProgressionWidget()
        widget.set_errors(3)
        assert widget._errors == 3

    def test_set_elapsed_zero(self, qapp) -> None:
        """set_elapsed(0) ne fait pas planter."""
        widget = ProgressionWidget()
        widget.set_mode("seconds")
        widget.set_elapsed(0)
        # Au moins un affichage non vide
        assert widget._value_label.text() != ""

    def test_set_elapsed_positif(self, qapp) -> None:
        """set_elapsed() avec secondes > 0."""
        widget = ProgressionWidget()
        widget.set_mode("seconds")
        widget.set_elapsed(65)  # 1:05
        texte = widget._value_label.text()
        assert isinstance(texte, str)
        assert texte != ""

    def test_set_elapsed_stocke_valeur(self, qapp) -> None:
        """set_elapsed() stocke la valeur dans _elapsed."""
        widget = ProgressionWidget()
        widget.set_elapsed(120)
        assert widget._elapsed == 120

    def test_mode_percent_affiche_pourcentage(self, qapp) -> None:
        """En mode percent, set_percentage() met à jour le label."""
        widget = ProgressionWidget()
        widget.set_percentage(50)
        widget._refresh_display()
        texte = widget._value_label.text()
        assert "%" in texte

    def test_mode_num_affiche_nombre(self, qapp) -> None:
        """En mode num, set_count() met à jour le label."""
        widget = ProgressionWidget()
        widget.set_mode("num")
        widget.set_count(42)
        texte = widget._value_label.text()
        assert "42" in texte

    def test_mode_actions_affiche_actions(self, qapp) -> None:
        """En mode actions, set_actions() met à jour le label."""
        widget = ProgressionWidget()
        widget.set_mode("actions")
        widget.set_actions(7)
        texte = widget._value_label.text()
        assert "7" in texte

    def test_mode_errors_affiche_erreurs(self, qapp) -> None:
        """En mode errors, set_errors() met à jour le label."""
        widget = ProgressionWidget()
        widget.set_mode("errors")
        widget.set_errors(2)
        texte = widget._value_label.text()
        assert "2" in texte

    def test_etiquette_mode_non_vide(self, qapp) -> None:
        """L'étiquette de mode contient un texte."""
        widget = ProgressionWidget()
        assert widget._mode_label.text() != ""

    def test_set_mode_invalide_leve_value_error(self, qapp) -> None:
        """set_mode() avec un mode inconnu lève ValueError."""
        import pytest
        widget = ProgressionWidget()
        with pytest.raises(ValueError, match="Mode"):
            widget.set_mode("INCONNU")
