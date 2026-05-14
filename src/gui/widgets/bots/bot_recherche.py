"""
Bot Recherche — interface de recherche Soulseek.

Barre de recherche en haut + zone de résultats défilante.
Chaque résultat = carte avec fichier, utilisateur, taille, extension.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.gui.theme_fragments.colors import COLORS

if TYPE_CHECKING:
    from src.services.connexion_manager import ConnexionManager

logger = logging.getLogger(__name__)

# ── Helpers ─────────────────────────────────────────────────────


def _format_size(bytes_val: int) -> str:
    if bytes_val >= 1_000_000_000:
        return f"{bytes_val / 1_000_000_000:.1f} Go"
    if bytes_val >= 1_000_000:
        return f"{bytes_val / 1_000_000:.1f} Mo"
    if bytes_val >= 1_000:
        return f"{bytes_val / 1_000:.1f} Ko"
    return f"{bytes_val} o"


def _format_bitrate(bps: int) -> str:
    if bps >= 1000:
        return f"{bps // 1000} kbps"
    return f"{bps} bps"


def _format_duration(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    return f"{m}m{s:02d}s"


# ── Attributs connus de FileData ─────────────────────────────────
_ATTR_BITRATE = 0
_ATTR_DURATION = 1
_ATTR_VBR = 2
_ATTR_SAMPLE_RATE = 4


def _get_attr(attributes: list, key: int) -> int | None:
    for attr in attributes:
        if attr.key == key:
            return attr.value
    return None


# ═════════════════════════════════════════════════════════════════
#  Carte de résultat
# ═════════════════════════════════════════════════════════════════


class SearchResultCard(QFrame):
    """Carte affichant un fichier trouvé."""

    def __init__(
        self,
        filename: str,
        username: str,
        filesize: int,
        extension: str,
        bitrate: int | None = None,
        duration: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("searchResultCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.setStyleSheet(
            f"""
            #searchResultCard {{
                background: {COLORS["BG_SURFACE"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 10px 14px;
            }}
            #searchResultCard:hover {{
                background: {COLORS["BG_HOVER"]};
                border-color: {COLORS["PRIMARY"]};
            }}
            """
        )

        grid = QHBoxLayout(self)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setSpacing(12)

        # ── Icône extension ──
        icon = QLabel(f"[{extension.upper()}]" if extension else "[?]")
        icon.setStyleSheet(
            f"color: {COLORS['PRIMARY']}; font-weight: 700; font-size: 13px;"
            f" background: {COLORS['BG_SURFACE2']}; padding: 4px 8px; border-radius: 4px;"
        )
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(icon)

        # ── Infos fichier ──
        info = QVBoxLayout()
        info.setSpacing(2)

        name_label = QLabel(filename.split("\\")[-1].split("/")[-1])
        name_label.setStyleSheet(
            f"color: {COLORS['TEXT_PRIMARY']}; font-size: 13px; font-weight: 600;"
        )
        name_label.setWordWrap(True)
        info.addWidget(name_label)

        details = []
        details.append(f"👤 {username}")
        details.append(f"📦 {_format_size(filesize)}")
        if bitrate is not None and bitrate > 0:
            details.append(f"🎵 {_format_bitrate(bitrate)}")
        if duration is not None and duration > 0:
            details.append(f"⏱ {_format_duration(duration)}")

        meta = QLabel("  ·  ".join(details))
        meta.setStyleSheet(f"color: {COLORS['TEXT_SECONDARY']}; font-size: 11px;")
        info.addWidget(meta)

        grid.addLayout(info, 1)

        # ── Bouton télécharger (placeholder) ──
        dl_btn = QPushButton("⬇")
        dl_btn.setFixedSize(32, 32)
        dl_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {COLORS['PRIMARY']};
                color: #ffffff;
                border: none;
                border-radius: 16px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: {COLORS['PRIMARY_HOVER']};
            }}
            """
        )
        dl_btn.setToolTip("Télécharger (bientôt)")
        dl_btn.setEnabled(False)
        grid.addWidget(dl_btn)


# ═════════════════════════════════════════════════════════════════
#  Page Recherche
# ═════════════════════════════════════════════════════════════════


class BotRecherche(QFrame):
    """Page de recherche Soulseek avec barre + résultats."""

    def __init__(
        self,
        connexion_manager: ConnexionManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("botRecherche")
        self.setFrameShape(QFrame.NoFrame)

        self._connexion_manager = connexion_manager
        self._searching = False
        self._search_timer: QTimer | None = None

        # ── Layout principal ──
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        # ── Titre ──
        title = QLabel("🔍 Recherche Soulseek")
        title.setStyleSheet(
            f"color: {COLORS['PRIMARY']}; font-size: 18px; font-weight: 700;"
        )
        outer.addWidget(title)

        # ── Barre de recherche ──
        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        self._search_input = QLineEdit()
        self._search_input.setObjectName("rechercheInput")
        self._search_input.setPlaceholderText(
            "Rechercher des fichiers sur Soulseek…"
        )
        self._search_input.setStyleSheet(
            f"""
            #rechercheInput {{
                background: {COLORS['BG_SURFACE']};
                color: {COLORS['TEXT_PRIMARY']};
                border: 1px solid {COLORS['BORDER']};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }}
            #rechercheInput:focus {{
                border-color: {COLORS['PRIMARY']};
            }}
            """
        )
        self._search_input.returnPressed.connect(self._on_search)
        search_row.addWidget(self._search_input, 1)

        self._search_btn = QPushButton("Rechercher")
        self._search_btn.setObjectName("rechercheBtn")
        self._search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._search_btn.setStyleSheet(
            f"""
            #rechercheBtn {{
                background: {COLORS['PRIMARY']};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 14px;
                font-weight: 600;
            }}
            #rechercheBtn:hover {{
                background: {COLORS['PRIMARY_HOVER']};
            }}
            #rechercheBtn:disabled {{
                background: {COLORS['BG_BTN_DISABLED']};
                color: {COLORS['TEXT_DISABLED']};
            }}
            """
        )
        self._search_btn.clicked.connect(self._on_search)
        search_row.addWidget(self._search_btn)

        outer.addLayout(search_row)

        # ── Statut / compteur ──
        self._status_label = QLabel("")
        self._status_label.setStyleSheet(
            f"color: {COLORS['TEXT_SECONDARY']}; font-size: 12px;"
        )
        outer.addWidget(self._status_label)

        # ── Zone de résultats (scrollable) ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        self._results_container = QWidget()
        self._results_container.setStyleSheet("background: transparent;")
        self._results_layout = QVBoxLayout(self._results_container)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.setSpacing(6)
        self._results_layout.addStretch(1)

        scroll.setWidget(self._results_container)
        outer.addWidget(scroll, 1)

        # ── État connecté ──
        self._update_connected_state()

    # ── API publique ─────────────────────────────────────────────

    def set_connexion_manager(self, manager: ConnexionManager) -> None:
        """Définit le gestionnaire de connexion et connecte les signaux."""
        self._connexion_manager = manager

        # Connecter les signaux
        manager.search_result_received.connect(self._on_search_result)
        manager.connected.connect(self._on_connected)
        manager.disconnected.connect(self._on_disconnected)
        manager.error_occurred.connect(self._on_search_error)

        self._update_connected_state()

    # ── État ─────────────────────────────────────────────────────

    def _update_connected_state(self) -> None:
        """Met à jour l'interface selon l'état de connexion."""
        connected = (
            self._connexion_manager is not None
            and self._connexion_manager.is_connected
        )
        self._search_input.setEnabled(connected)
        self._search_btn.setEnabled(connected and not self._searching)
        if not connected and not self._results_layout.count() > 1:
            self._status_label.setText(
                "🔴 Connectez-vous à Soulseek pour lancer une recherche"
            )
        elif not connected:
            self._status_label.setText(
                "🔴 Déconnecté — les recherches en cours sont perdues"
            )

    def _on_connected(self, username: str) -> None:
        """Handler connexion réussie."""
        self._update_connected_state()

    def _on_disconnected(self) -> None:
        """Handler déconnexion."""
        self._reset_search_state()
        self._update_connected_state()

    # ── Recherche ────────────────────────────────────────────────

    def _on_search(self) -> None:
        """Lance une recherche."""
        query = self._search_input.text().strip()
        if len(query) < 2:
            self._status_label.setText(
                "📝 Minimum 2 caractères pour lancer une recherche"
            )
            return

        if self._connexion_manager is None:
            self._status_label.setText("❌ Aucun gestionnaire de connexion")
            return

        if not self._connexion_manager.is_connected:
            self._status_label.setText("❌ Pas connecté à Soulseek")
            return

        # Annuler le timeout précédent si existant
        if self._search_timer is not None:
            self._search_timer.stop()

        # Vider les résultats précédents
        self._clear_results()
        self._searching = True
        self._search_btn.setEnabled(False)
        self._search_btn.setText("Recherche…")
        self._status_label.setText(f"🔍 Recherche de « {query} » en cours…")

        self._connexion_manager.search(query)

        # Timeout de sécurité — réactive le bouton après 30s
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._on_search_timeout)
        self._search_timer.start(30000)

    def _on_search_result(self, evt: object) -> None:
        """Reçoit un résultat de recherche."""
        from aioslsk.events import SearchResultEvent

        if not isinstance(evt, SearchResultEvent):
            return

        result = evt.result
        if not hasattr(result, 'shared_items') or not result.shared_items:
            return

        count_before = self._results_layout.count() - 1  # moins le stretch

        for file_data in result.shared_items:
            bitrate = _get_attr(file_data.attributes, _ATTR_BITRATE)
            duration = _get_attr(file_data.attributes, _ATTR_DURATION)

            card = SearchResultCard(
                filename=file_data.filename,
                username=result.username,
                filesize=file_data.filesize,
                extension=file_data.extension,
                bitrate=bitrate,
                duration=duration,
            )

            # Insérer avant le stretch
            self._results_layout.insertWidget(
                self._results_layout.count() - 1, card
            )

        count = self._results_layout.count() - 1  # moins le stretch
        self._status_label.setText(
            f"✅ {count} résultat{'s' if count > 1 else ''} — "
            f"recherche « {evt.query.query } »"
        )

        # Réactiver la recherche sur premier résultat
        if self._searching:
            self._searching = False
            self._search_btn.setEnabled(True)
            self._search_btn.setText("Rechercher")

    def _on_search_error(self, msg: str) -> None:
        """Handler erreur de recherche."""
        if self._searching:
            self._reset_search_state()
            self._status_label.setText(f"❌ Erreur : {msg}")

    def _on_search_timeout(self) -> None:
        """Timeout de sécurité — réactive le bouton."""
        if self._searching:
            self._searching = False
            self._search_btn.setEnabled(True)
            self._search_btn.setText("Rechercher")
            self._status_label.setText(
                "⏱️ La recherche continue en arrière-plan…"
            )

    # ── Nettoyage ────────────────────────────────────────────────

    def _reset_search_state(self) -> None:
        """Réinitialise l'état de recherche."""
        self._searching = False
        self._search_btn.setEnabled(True)
        self._search_btn.setText("Rechercher")
        if self._search_timer is not None:
            self._search_timer.stop()

    def _clear_results(self) -> None:
        """Vide tous les résultats affichés."""
        while self._results_layout.count() > 1:  # garde le stretch
            item = self._results_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
