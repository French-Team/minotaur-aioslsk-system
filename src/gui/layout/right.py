"""
Zone Droite — panneau latéral droit rétractable.

Affiche les rooms (publiques et privées) dans un QTabWidget.
Le panneau complet peut se replier vers la droite en cliquant
sur le bouton « ▶ » sur le bord gauche.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from src.services.room_service import RoomService, RoomInfo
    from src.services.connexion_manager import ConnexionManager

# Largeurs
_WIDTH_EXPANDED = 280
_WIDTH_COLLAPSED = 20


class _Handle(QFrame):
    """Bouton de repli — toute la hauteur, click détecté."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("rightHandle")
        self.setFixedWidth(20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._arrow = QLabel("▶")
        self._arrow.setObjectName("handleArrow")
        self._arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._arrow)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)

    def set_arrow(self, text: str) -> None:
        self._arrow.setText(text)


class RightZone(QFrame):
    """Panneau latéral droit — onglets Public / Privé + rétractable."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # pyrefly: ignore [missing-attribute]
        self.setFrameShape(QFrame.NoFrame)
        self.setObjectName("rightZone")

        self._collapsed = True
        self._room_service: RoomService | None = None
        self._connexion_manager: ConnexionManager | None = None

        # ── Layout principal horizontal : [handle | contenu] ──
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Handle (bouton de repli sur le bord gauche) ──
        self._handle = _Handle()
        self._handle.clicked.connect(self._toggle_panel)

        # ── Zone de contenu (ce qui se cache) ──
        self._content = QWidget(self)
        self._content.setObjectName("rightContent")

        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(4)

        # ── Titre ──
        title = QLabel("LES ROOMS")
        title.setStyleSheet("color: #6c5ce7; font-size: 12px; font-weight: 700;")
        content_layout.addWidget(title)

        # ── Tabs ──
        self._tabs = QTabWidget()
        self._tabs.setObjectName("roomsTabs")

        # Style pour les QListWidget de salons (Dark sleek glassmorphism)
        list_style = """
            QListWidget {
                background-color: #151522;
                border: 1px solid #252538;
                border-radius: 8px;
                padding: 4px;
            }
            QListWidget::item {
                background-color: #1e1e2e;
                color: #e4e4ec;
                border: 1px solid #2e2e3a;
                border-radius: 6px;
                margin-bottom: 4px;
                padding: 8px 12px;
                font-size: 12px;
            }
            QListWidget::item:hover {
                background-color: #26263e;
                border-color: #6c5ce7;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #6c5ce7;
                border-color: #6c5ce7;
                color: #ffffff;
            }
        """

        # Onglet Public
        self._tab_public = QWidget()
        self._tab_public.setObjectName("tabPublic")
        lay_public = QVBoxLayout(self._tab_public)
        lay_public.setContentsMargins(4, 4, 4, 4)
        lay_public.setSpacing(4)
        
        self._list_public = QListWidget()
        self._list_public.setObjectName("listPublic")
        self._list_public.setStyleSheet(list_style)
        self._list_public.itemDoubleClicked.connect(self._on_room_double_clicked)
        lay_public.addWidget(self._list_public)
        self._tabs.addTab(self._tab_public, "Public")

        # Onglet Privé
        self._tab_prive = QWidget()
        self._tab_prive.setObjectName("tabPrive")
        lay_prive = QVBoxLayout(self._tab_prive)
        lay_prive.setContentsMargins(4, 4, 4, 4)
        lay_prive.setSpacing(4)
        
        self._list_prive = QListWidget()
        self._list_prive.setObjectName("listPrive")
        self._list_prive.setStyleSheet(list_style)
        self._list_prive.itemDoubleClicked.connect(self._on_room_double_clicked)
        lay_prive.addWidget(self._list_prive)
        self._tabs.addTab(self._tab_prive, "Privé")

        content_layout.addWidget(self._tabs, 1)

        # Assemblage
        main_layout.addWidget(self._handle, 0)  # pas d'étirement
        main_layout.addWidget(self._content, 1)  # stretch = prend l'espace

        # ── État initial : déplié par défaut ──
        self._collapsed = False
        self._apply_state()

    # ── API publique ─────────────────────────────────────────────

    @property
    def is_collapsed(self) -> bool:
        return self._collapsed

    @property
    def tabs(self) -> QTabWidget:
        return self._tabs

    def toggle(self) -> None:
        self._toggle_panel()

    def expand(self) -> None:
        if self._collapsed:
            self._toggle_panel()

    def collapse(self) -> None:
        if not self._collapsed:
            self._toggle_panel()

    def setup(self, room_service: RoomService, connexion_manager: ConnexionManager | None = None) -> None:
        """Configure le service de salons et le gestionnaire de connexion."""
        self._room_service = room_service
        self._connexion_manager = connexion_manager
        
        self._room_service.rooms_publiques_recues.connect(self._on_rooms_publiques)
        self._room_service.rooms_privees_recues.connect(self._on_rooms_privees)
        
        # Chargement initial
        self._on_rooms_publiques(self._room_service.rooms_publiques)
        self._on_rooms_privees(self._room_service.rooms_privees)

    # ── Mécanisme interne ────────────────────────────────────────

    def _toggle_panel(self) -> None:
        self._collapsed = not self._collapsed
        self._apply_state()

    def _apply_state(self) -> None:
        self._content.setVisible(not self._collapsed)
        self._handle.set_arrow("◀" if self._collapsed else "▶")
        self.setFixedWidth(_WIDTH_COLLAPSED if self._collapsed else _WIDTH_EXPANDED)

    # ── Mise à jour des salons ───────────────────────────────────

    def _on_rooms_publiques(self, rooms: list[RoomInfo]) -> None:
        """Affiche les salons publics triés par nombre de membres."""
        self._list_public.clear()
        if not rooms:
            item = QListWidgetItem("Aucun salon disponible")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list_public.addItem(item)
            return

        sorted_rooms = sorted(rooms, key=lambda r: r.user_count, reverse=True)
        for room in sorted_rooms:
            prefix = "" if room.name.startswith("#") else "#"
            item_text = f"{prefix}{room.name}  •  💬 {room.user_count}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, room.name)
            item.setToolTip("Double-cliquez pour rejoindre ce salon")
            self._list_public.addItem(item)

    def _on_rooms_privees(self, rooms: list[RoomInfo]) -> None:
        """Affiche les salons privés rejoints."""
        self._list_prive.clear()
        if not rooms:
            item = QListWidgetItem("Aucun salon rejoint")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list_prive.addItem(item)
            return

        sorted_rooms = sorted(rooms, key=lambda r: r.user_count, reverse=True)
        for room in sorted_rooms:
            prefix = "" if room.name.startswith("#") else "#"
            item_text = f"{prefix}{room.name}  •  💬 {room.user_count}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, room.name)
            item.setToolTip("Double-cliquez pour rejoindre ce salon")
            self._list_prive.addItem(item)

    def _on_room_double_clicked(self, item: QListWidgetItem) -> None:
        """Appelé lors du double-clic sur un salon pour le rejoindre."""
        if self._connexion_manager is None or not item.flags() & Qt.ItemFlag.ItemIsEnabled:
            return
        
        text = item.text()
        room_name = text.split("  •  ")[0]
        if room_name.startswith("#"):
            room_name = room_name[1:]
            
        self._connexion_manager.join_room(room_name)
