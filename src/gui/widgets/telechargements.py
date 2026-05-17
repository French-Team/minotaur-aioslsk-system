"""
Widgets pour la gestion des téléchargements.

Composants :
  - TelechargementsHeaderWidget : bouton cliquable dans le header (colonne 2)
  - TelechargementsPage : page centrale listant les téléchargements
  - DownloadRow : ligne individuelle d'un téléchargement
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# ── Constantes ───────────────────────────────────────────────────
_STATUT_COULEURS = {
    "en_cours": "#00e676",
    "attente": "#ffab00",
    "echoue": "#ff5252",
    "termine": "#6c5ce7",
}

_STATUT_LIBELLES = {
    "en_cours": "En cours",
    "attente": "En attente",
    "echoue": "Échoué",
    "termine": "Terminé",
}


# ═══════════════════════════════════════════════════════════════════
#  Header — widget cliquable dans la bannière
# ═══════════════════════════════════════════════════════════════════


class TelechargementsHeaderWidget(QFrame):
    """Bouton cliquable dans le header — colonne 2.

    Affiche le nombre de téléchargements en cours.
    Émet ``clicked`` au clic.
    """

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("telechargementsHeader")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(0)

        # Ligne 1 — titre
        self._title = QLabel("⬇  Téléchargements")
        self._title.setObjectName("telechargementsHeaderTitle")
        self._title.setStyleSheet("color: #6c5ce7; font-size: 11px; font-weight: 600;")
        layout.addWidget(self._title)

        # Ligne 2 — statut
        self._statut = QLabel("En cours : 0  •  Attente : 0")
        self._statut.setObjectName("telechargementsHeaderStatut")
        self._statut.setStyleSheet("color: #e4e4ec; font-size: 13px; font-weight: 500;")
        layout.addWidget(self._statut)

    # ── API publique ─────────────────────────────────────────────

    def set_counts(self, en_cours: int, attente: int) -> None:
        """Met à jour les compteurs affichés."""
        self._statut.setText(f"En cours : {en_cours}  •  Attente : {attente}")

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        self.clicked.emit()
        super().mousePressEvent(event)


# ═══════════════════════════════════════════════════════════════════
#  Ligne de téléchargement
# ═══════════════════════════════════════════════════════════════════


class DownloadRow(QFrame):
    """Ligne d'affichage d'un téléchargement."""

    cancel_requested = Signal(str)  # identifiant du téléchargement
    retry_requested = Signal(str)

    def __init__(
        self,
        identifiant: str,
        fichier: str,
        statut: str = "en_cours",
        progression: float = 0.0,
        vitesse: str = "",
        taille: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("downloadRow")
        self._id = identifiant

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # ── Icône statut ──
        couleur = _STATUT_COULEURS.get(statut, "#5a5a6a")
        self._led = QLabel("●")
        self._led.setStyleSheet(f"color: {couleur}; font-size: 10px;")
        self._led.setFixedWidth(14)
        layout.addWidget(self._led)

        # ── Nom du fichier ──
        self._file_label = QLabel(fichier)
        self._file_label.setObjectName("downloadFileName")
        self._file_label.setStyleSheet("color: #e4e4ec; font-size: 13px; font-weight: 500; min-width: 180px;")
        layout.addWidget(self._file_label)

        # ── Statut ──
        libelle = _STATUT_LIBELLES.get(statut, statut)
        self._status_label = QLabel(libelle)
        self._status_label.setStyleSheet(f"color: {couleur}; font-size: 12px; font-weight: 500; min-width: 80px;")
        layout.addWidget(self._status_label)

        # ── Barre de progression ──
        self._progress = QProgressBar()
        self._progress.setObjectName("downloadProgress")
        self._progress.setRange(0, 100)
        self._progress.setValue(int(progression))
        self._progress.setTextVisible(True)
        self._progress.setFixedWidth(140)
        self._progress.setFixedHeight(16)
        self._progress.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: #1a1a22;
                border: 1px solid #2e2e3a;
                border-radius: 4px;
                text-align: center;
                font-size: 10px;
                color: #b0b0c0;
            }}
            QProgressBar::chunk {{
                background-color: {couleur};
                border-radius: 3px;
            }}
            """
        )
        layout.addWidget(self._progress)

        # ── Infos complémentaires ──
        if vitesse or taille:
            infos = []
            if vitesse:
                infos.append(vitesse)
            if taille:
                infos.append(taille)
            self._info_label = QLabel("  •  ".join(infos))
            self._info_label.setStyleSheet("color: #5a5a6a; font-size: 11px;")
            layout.addWidget(self._info_label)

        layout.addStretch(1)

        # ── Boutons d'action ──
        if statut in ("en_cours", "attente"):
            self._btn_cancel = self._make_btn("✕ Annuler", "downloadBtnCancel")
            self._btn_cancel.clicked.connect(lambda: self.cancel_requested.emit(identifiant))
            layout.addWidget(self._btn_cancel)

        if statut == "echoue":
            self._btn_retry = self._make_btn("⟳ Réessayer", "downloadBtnRetry")
            self._btn_retry.clicked.connect(lambda: self.retry_requested.emit(identifiant))
            layout.addWidget(self._btn_retry)

    # ── Privé ────────────────────────────────────────────────────

    @staticmethod
    def _make_btn(text: str, obj_name: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName(obj_name)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    # ── API publique ─────────────────────────────────────────────

    @property
    def identifiant(self) -> str:
        return self._id

    def set_progression(self, value: float) -> None:
        """Met à jour la barre de progression."""
        self._progress.setValue(int(value))


# ═══════════════════════════════════════════════════════════════════
#  Page centrale — téléchargements
# ═══════════════════════════════════════════════════════════════════


class TelechargementsPage(QFrame):
    """Page centrale de gestion des téléchargements.

    Sections :
      - En cours
      - En attente
      - Échoué

    Barre d'outils en bas avec actions :
      - Tout reprendre / Tout mettre en pause
      - Ouvrir le dossier Downloads
      - Effacer la liste
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("telechargementsPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(0)

        # ── En-tête ──
        header = QLabel("Téléchargements")
        header.setStyleSheet("color: #6c5ce7; font-size: 16px; font-weight: 700; padding-bottom: 8px;")
        layout.addWidget(header)

        self._stats = QLabel("En cours : 0  •  En attente : 0  •  Échoué : 0")
        self._stats.setObjectName("downloadStats")
        self._stats.setStyleSheet("color: #5a5a6a; font-size: 12px; padding-bottom: 12px;")
        layout.addWidget(self._stats)

        # ── Zone scrollable avec les sections ──
        scroll = QScrollArea()
        scroll.setObjectName("downloadScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self._list_container = QWidget()
        self._list_container.setObjectName("downloadListContainer")
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)

        # Sections
        self._build_section("En cours", "en_cours", "#00e676")
        self._build_section("En attente", "attente", "#ffab00")
        self._build_section("Échoué", "echoue", "#ff5252")

        self._list_layout.addStretch(1)

        scroll.setWidget(self._list_container)
        layout.addWidget(scroll, 1)

        # ── Barre d'outils bas ──
        self._build_toolbar(layout)

        # Compteurs
        self._downloads: dict[str, dict] = {}  # id -> {row, section, statut}

    # ── Construction ─────────────────────────────────────────────

    def _build_section(self, titre: str, section: str, couleur: str) -> None:
        """Ajoute un bloc de section dans la liste."""
        # Titre de section
        label = QLabel(titre)
        label.setStyleSheet(f"color: {couleur}; font-size: 13px; font-weight: 700; padding: 8px 4px 4px 4px;")
        label.setObjectName(f"section_{section}")
        self._list_layout.addWidget(label)

        # Conteneur pour les rows de cette section
        container = QVBoxLayout()
        container.setContentsMargins(0, 0, 0, 0)
        container.setSpacing(2)

        # Stocker une référence pour ajouter des rows
        setattr(self, f"_section_{section}", container)

        self._list_layout.addLayout(container)

    def _build_toolbar(self, parent_layout: QVBoxLayout) -> None:
        """Barre d'outils en bas de la page."""
        toolbar = QFrame()
        toolbar.setObjectName("downloadToolbar")
        toolbar.setStyleSheet("background-color: #14141e; border: 1px solid #2e2e3a; border-radius: 6px; padding: 6px;")

        bar_layout = QHBoxLayout(toolbar)
        bar_layout.setContentsMargins(8, 4, 8, 4)
        bar_layout.setSpacing(8)

        # Boutons
        self._btn_resume = self._toolbar_btn("▶ Tout reprendre", "toolbarBtn")
        self._btn_pause = self._toolbar_btn("⏸ Tout pause", "toolbarBtn")
        self._btn_ouvrir = self._toolbar_btn("📂 Ouvrir Downloads", "toolbarBtn")
        self._btn_effacer = self._toolbar_btn("🗑 Effacer la liste", "toolbarBtnDanger")

        bar_layout.addWidget(self._btn_resume)
        bar_layout.addWidget(self._btn_pause)
        bar_layout.addStretch(1)
        bar_layout.addWidget(self._btn_ouvrir)
        bar_layout.addWidget(self._btn_effacer)

        parent_layout.addWidget(toolbar)

    @staticmethod
    def _toolbar_btn(text: str, obj_name: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName(obj_name)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setSizePolicy(
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Fixed,
        )
        return btn

    # ── API publique ─────────────────────────────────────────────

    def add_download(
        self,
        identifiant: str,
        fichier: str,
        statut: str = "en_cours",
        progression: float = 0.0,
        vitesse: str = "",
        taille: str = "",
    ) -> None:
        """Ajoute un téléchargement à la liste."""
        row = DownloadRow(
            identifiant,
            fichier,
            statut=statut,
            progression=progression,
            vitesse=vitesse,
            taille=taille,
        )

        # Déterminer la section
        section_map = {
            "en_cours": "en_cours",
            "attente": "attente",
            "echoue": "echoue",
        }
        section_key = section_map.get(statut, "en_cours")
        section_container: QVBoxLayout | None = getattr(self, f"_section_{section_key}", None)

        if section_container is not None:
            section_container.addWidget(row)

        self._downloads[identifiant] = {
            "row": row,
            "section": section_key,
            "statut": statut,
        }
        self._update_stats()

    def remove_download(self, identifiant: str) -> bool:
        """Supprime un téléchargement par son identifiant."""
        info = self._downloads.pop(identifiant, None)
        if info is None:
            return False
        row = info["row"]
        section_key = info["section"]
        section_container: QVBoxLayout | None = getattr(self, f"_section_{section_key}", None)
        if section_container is not None:
            section_container.removeWidget(row)
        row.deleteLater()
        self._update_stats()
        return True

    def update_progression(self, identifiant: str, progression: float) -> None:
        """Met à jour la barre de progression d'un téléchargement."""
        info = self._downloads.get(identifiant)
        if info is not None:
            info["row"].set_progression(progression)

    def change_statut(self, identifiant: str, nouveau_statut: str) -> None:
        """Change le statut d'un téléchargement.

        Déplace la ligne vers la section correspondante.
        """
        info = self._downloads.get(identifiant)
        if info is None:
            return

        section_map = {
            "en_cours": "en_cours",
            "attente": "attente",
            "echoue": "echoue",
        }
        nouvelle_section = section_map.get(nouveau_statut, "en_cours")
        ancienne_section = info["section"]

        if nouvelle_section == ancienne_section:
            info["statut"] = nouveau_statut
            self._update_stats()
            return

        # Déplacer la ligne
        row = info["row"]
        ancien_container: QVBoxLayout | None = getattr(self, f"_section_{ancienne_section}", None)
        nouveau_container: QVBoxLayout | None = getattr(self, f"_section_{nouvelle_section}", None)
        if ancien_container is not None:
            ancien_container.removeWidget(row)
        if nouveau_container is not None:
            nouveau_container.addWidget(row)

        info["section"] = nouvelle_section
        info["statut"] = nouveau_statut
        self._update_stats()

    def clear_all(self) -> None:
        """Supprime tous les téléchargements."""
        for identifiant in list(self._downloads.keys()):
            self.remove_download(identifiant)

    def download_count(self) -> int:
        return len(self._downloads)

    # ── Privé ────────────────────────────────────────────────────

    def _update_stats(self) -> None:
        """Met à jour le texte des statistiques."""
        en_cours = sum(1 for d in self._downloads.values() if d["statut"] == "en_cours")
        attente = sum(1 for d in self._downloads.values() if d["statut"] == "attente")
        echoue = sum(1 for d in self._downloads.values() if d["statut"] == "echoue")
        self._stats.setText(f"En cours : {en_cours}  •  En attente : {attente}  •  Échoué : {echoue}")
