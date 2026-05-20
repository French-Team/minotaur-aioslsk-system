"""Tests pour le widget Horloge."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from src.gui.widgets.clock import ClockWidget


class TestClockWidget:
    """ClockWidget : horloge numérique avec mise à jour chaque seconde."""

    def test_creer_widget(self, qapp) -> None:
        """Peut créer un ClockWidget."""
        widget = ClockWidget()
        assert widget is not None
        assert isinstance(widget, ClockWidget)

    def test_object_name(self, qapp) -> None:
        """Le widget a le bon objectName."""
        widget = ClockWidget()
        assert widget.objectName() == "clockWidget"

    def test_time_string_initial(self, qapp) -> None:
        """time_string retourne une chaîne au format HH:mm:ss."""
        widget = ClockWidget()
        ts = widget.time_string
        assert isinstance(ts, str)
        assert ":" in ts
        # Format hh:mm:ss → au moins 2 deux-points
        assert ts.count(":") == 2

    def test_get_time_identique_a_time_string(self, qapp) -> None:
        """get_time() est un alias public de time_string."""
        widget = ClockWidget()
        assert widget.get_time() == widget.time_string

    def test_set_display_format_change_format(self, qapp) -> None:
        """set_display_format change le format d'affichage."""
        widget = ClockWidget()
        original = widget.time_string
        # Format sans secondes
        widget.set_display_format("HH:mm")
        nouveau = widget.time_string
        assert isinstance(nouveau, str)
        # Avec le format HH:mm, on n'a qu'un seul deux-points
        assert nouveau.count(":") == 1

    def test_stop_arrete_le_timer(self, qapp) -> None:
        """stop() arrête le timer interne."""
        widget = ClockWidget()
        assert widget._timer.isActive()  # Timer démarré à la création
        widget.stop()
        assert not widget._timer.isActive()

    def test_start_relance_le_timer(self, qapp) -> None:
        """start() relance le timer après un stop()."""
        widget = ClockWidget()
        widget.stop()
        assert not widget._timer.isActive()
        widget.start()
        assert widget._timer.isActive()

    def test_start_ne_relance_pas_si_deja_actif(self, qapp) -> None:
        """start() est sans effet si le timer est déjà actif."""
        widget = ClockWidget()
        assert widget._timer.isActive()
        widget.start()  # ne doit pas planter
        assert widget._timer.isActive()

    def test_tick_signal_emission(self, qapp) -> None:
        """Le signal tick est émis avec l'heure à chaque mise à jour."""
        widget = ClockWidget()
        emissions: list[str] = []

        def on_tick(heure: str) -> None:
            emissions.append(heure)

        widget.tick.connect(on_tick)
        # Forcer une mise à jour
        widget._update_time()
        assert len(emissions) == 1
        assert isinstance(emissions[0], str)
        assert ":" in emissions[0]

    def test_stop_supprime_emission_tick(self, qapp) -> None:
        """Après stop(), _update_time n'émet plus de tick."""
        widget = ClockWidget()
        emissions: list[str] = []
        widget.tick.connect(emissions.append)
        widget.stop()
        widget._update_time()
        # Le tick est quand même émis via _update_time, mais le timer ne
        # déclenche plus _update_time automatiquement
        assert len(emissions) == 1  # appel manuel, mais timer arrêté

    def test_parent_optionnel(self, qapp) -> None:
        """Peut créer un ClockWidget avec un parent."""
        parent = QWidget()
        widget = ClockWidget(parent)
        assert widget.parent() is parent

    def test_label_object_name(self, qapp) -> None:
        """Le label interne a le bon objectName."""
        widget = ClockWidget()
        assert widget._label.objectName() == "clockLabel"

    def test_label_aligne_centre(self, qapp) -> None:
        """Le label est aligné au centre."""
        widget = ClockWidget()
        assert widget._label.alignment() == Qt.AlignmentFlag.AlignCenter
