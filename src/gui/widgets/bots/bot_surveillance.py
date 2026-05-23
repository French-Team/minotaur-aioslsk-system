"""
Bot Surveillance — watcher centralisé.

Affiche un flux d'événements en temps réel (connexion, transferts, erreurs…)
avec historique SQLite, filtres, et alertes.

Voir `docs/specs/bot-surveillance-spec.md` pour le plan complet.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QDate, Qt, QTimer, Signal

from src.utils.log_action import log_action

logger = logging.getLogger("[SURVEILLANCE]")

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.theme_fragments.colors import COLORS, rgba
from src.services.event_bus import EventBus, SurveillanceEvent

# ── Helpers ──────────────────────────────────────────────────────────────


class _StatBadge(QFrame):
    """Badge statistique compact — icône + nombre + label.

    Utilisé dans la barre d'indicateurs pour afficher
    le nombre d'erreurs, d'avertissements, etc.
    """

    def __init__(
        self,
        icon: str,
        label: str,
        color: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("statBadge")
        self.setFixedHeight(44)

        self._value = 0
        self._color = color

        # Fond du badge
        self.setStyleSheet(f"""
            #statBadge {{
                background: {COLORS["BG_SURFACE"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 8px;
                padding: 4px 12px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 14, 6)
        layout.setSpacing(8)

        # Valeur (nombre)
        self._value_lbl = QLabel("0")
        self._value_lbl.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: {color};
        """)
        layout.addWidget(self._value_lbl)

        # Label
        txt = QLabel(f"{icon}  {label}")
        txt.setStyleSheet(f"""
            font-size: 12px;
            font-weight: 500;
            color: {COLORS["TEXT_SECONDARY"]};
        """)
        layout.addWidget(txt)

    def set_value(self, value: int) -> None:
        """Met à jour la valeur affichée."""
        self._value = value
        self._value_lbl.setText(str(value))


class _FilterToggle(QPushButton):
    """Bouton toggle pour filtre par catégorie d'événement."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("filterToggle")
        self.setCheckable(True)
        self.setChecked(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(28)
        self._apply_style(checked=True)

        self.toggled.connect(self._on_toggled)

    def _on_toggled(self, checked: bool) -> None:
        self._apply_style(checked)

    def _apply_style(self, checked: bool) -> None:
        if checked:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS["ACCENT"]};
                    color: {COLORS["TEXT_WHITE"]};
                    border: none;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {COLORS["ACCENT_HOVER"]};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS["BG_BTN"]};
                    color: {COLORS["TEXT_MUTED"]};
                    border: 1px solid {COLORS["BORDER"]};
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background: {COLORS["BG_HOVER"]};
                    color: {COLORS["TEXT_SECONDARY"]};
                }}
            """)


# ── Helper : Carte d'événement ──────────────────────────────────────────


class _EventCard(QFrame):
    """Carte compacte représentant un événement dans le flux."""

    SEVERITY_ICONS = {
        "ERROR": "\U0001f534",
        "WARN": "\U0001f7e1",
        "INFO": "\U0001f535",
    }

    SEVERITY_COLORS = {
        "ERROR": "#e74c3c",
        "WARN": "#f39c12",
        "INFO": "#3498db",
    }

    # Signal émis quand l'utilisateur clique sur Détails
    detail_requested = Signal(object)  # SurveillanceEvent

    def __init__(
        self,
        event: "SurveillanceEvent",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._event = event
        self._event_id = event.id
        self._severity = event.severity
        self._category = event.category
        self._title = event.title
        self._message = event.message
        self._timestamp = event.timestamp
        self._source = event.source

        self.setObjectName("eventCard")
        self.setFixedHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)

        # Icône de sévérité
        icon = self.SEVERITY_ICONS.get(self._severity, "\u26aa")
        self._icon_lbl = QLabel(icon)
        self._icon_lbl.setFixedWidth(24)
        layout.addWidget(self._icon_lbl)

        # Timestamp (court)
        ts = self._timestamp[11:19] if len(self._timestamp) >= 19 else self._timestamp
        ts_lbl = QLabel(ts)
        ts_lbl.setStyleSheet(f"color: {COLORS['TEXT_MUTED']}; font-size: 11px; font-family: monospace;")
        ts_lbl.setFixedWidth(70)
        layout.addWidget(ts_lbl)

        # Titre (prend tout l'espace)
        self._title_lbl = QLabel(self._title)
        self._title_lbl.setStyleSheet(f"color: {COLORS['TEXT_PRIMARY']}; font-size: 12px; font-weight: 500;")
        self._title_lbl.setWordWrap(False)
        layout.addWidget(self._title_lbl, stretch=1)

        # Catégorie (petit badge)
        cat_lbl = QLabel(self._category)
        cat_lbl.setStyleSheet(f"color: {COLORS['TEXT_MUTED']}; font-size: 10px;")
        cat_lbl.setFixedWidth(80)
        cat_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(cat_lbl)

        # Boutons d'action (hover)
        self._btn_container = QFrame()
        self._btn_container.setFixedWidth(0)
        btn_layout = QHBoxLayout(self._btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(2)

        btn_style = f"""
            QPushButton {{
                background: transparent;
                color: {COLORS["TEXT_MUTED"]};
                border: none;
                padding: 2px 4px;
                font-size: 12px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background: {COLORS["BG_BTN"]};
                color: {COLORS["TEXT_PRIMARY"]};
            }}
        """

        self._copy_btn = QPushButton("\U0001f4cb")
        self._copy_btn.setToolTip("Copier les détails")
        self._copy_btn.setFixedSize(24, 24)
        self._copy_btn.setStyleSheet(btn_style)
        self._copy_btn.clicked.connect(self._copy_to_clipboard)
        btn_layout.addWidget(self._copy_btn)

        self._detail_btn = QPushButton("\U0001f50d")
        self._detail_btn.setToolTip("Voir les détails")
        self._detail_btn.setFixedSize(24, 24)
        self._detail_btn.setStyleSheet(btn_style)
        self._detail_btn.clicked.connect(self._request_detail)
        btn_layout.addWidget(self._detail_btn)

        layout.addWidget(self._btn_container)

        # Bordure gauche colorée selon sévérité
        border_color = self.SEVERITY_COLORS.get(self._severity, "transparent")
        self.setStyleSheet(f"""
            #eventCard {{
                background: {COLORS["BG_SURFACE"]};
                border-left: 3px solid {border_color};
                border-radius: 4px;
                margin: 1px 0px;
            }}
            #eventCard:hover {{
                background: {COLORS["BG_HOVER"]};
            }}
        """)

    def enterEvent(self, event: object) -> None:
        """Affiche les boutons d'action au survol."""
        self._btn_container.setFixedWidth(60)
        super().enterEvent(event)  # type: ignore[arg-type]

    def leaveEvent(self, event: object) -> None:
        """Cache les boutons d'action quand la souris quitte."""
        self._btn_container.setFixedWidth(0)
        super().leaveEvent(event)  # type: ignore[arg-type]

    def _copy_to_clipboard(self) -> None:
        """Copie les détails de l'événement dans le presse-papier."""
        from PySide6.QtGui import QGuiApplication

        icon = self.SEVERITY_ICONS.get(self._severity, "\u26aa")
        lines = [
            f"[{icon}] {self._title}",
            f"\U0001f4c5 {self._timestamp}",
            f"\U0001f3af {self._category}",
            f"\U0001f4e3 {self._message}",
            f"\U0001f4cd Source: {self._source}",
        ]
        if self._event and self._event.details:
            lines.append(f"\U0001f4ca D\u00e9tails: {self._event.details}")
        text = "\n".join(lines)
        QGuiApplication.clipboard().setText(text)

    def _request_detail(self) -> None:
        """Émet le signal pour ouvrir le popup de détails."""
        if self._event:
            self.detail_requested.emit(self._event)

    def matches_filter(self, search_text: str, active_categories: set[str]) -> bool:
        """Vérifie si la carte correspond aux filtres actuels."""
        if search_text:
            text = f"{self._title} {self._message} {self._source}".lower()
            if search_text not in text:
                return False
        if self._category not in active_categories:
            return False
        return True

    @property
    def event_id(self) -> int:
        return self._event_id

    @property
    # pyrefly: ignore [bad-override]
    def event(self) -> object:
        """Retourne l'objet SurveillanceEvent complet."""
        return self._event


# ── Classe principale ────────────────────────────────────────────────────


class BotSurveillance(QFrame):
    """Watcher centralisé — flux d'événements, historique, alertes."""

    page_changed = Signal(str)

    # Signal émis quand le nombre d'événements non lus change
    unseen_count_changed = Signal(int)

    # Nombre max d'événements dans le flux
    MAX_FEED_ITEMS = 500

    # Catégories avec leurs icônes (ordre d'affichage)
    CATEGORIES: list[tuple[str, str]] = [
        ("reseau", "🌐 Réseau"),
        ("transfert", "📥 Transferts"),
        ("recherche", "🔎 Recherche"),
        ("bibliotheque", "📚 Bibliothèque"),
        ("configuration", "⚙️ Config"),
        ("erreur", "❌ Erreurs"),
        ("bot", "🤖 Bots"),
    ]

    def __init__(
        self,
        center_zone: QWidget | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("botSurveillance")
        self._center_zone = center_zone

        # État
        self._paused = False
        self._filtres_categories: set[str] = set(cat for cat, _ in self.CATEGORIES)
        self._filtre_texte: str = ""

        # Stats affichées dans les badges
        self._stats_errors = 0
        self._stats_warns = 0
        self._stats_total = 0

        # Compteur d'événements non lus (badge footer)
        self._unseen_count = 0

        # Flux d'événements
        self._feed_cards: list[_EventCard] = []
        self._feed_layout: QVBoxLayout | None = None
        self._feed_scroll: QScrollArea | None = None
        self._auto_scroll = True
        self._actif = False
        self._loop_timer: QTimer = QTimer(self)
        self._loop_timer.setInterval(60000)  # 60s entre chaque tick
        self._loop_timer.timeout.connect(self._on_loop_tick)
        self._build_ui()

        # Connexion à l'EventBus (activée au demarrer())
        self._event_bus = EventBus()

    # ── Interrupteur ───────────────────────────────────────────────

    def demarrer(self) -> None:
        """Active l'interrupteur → démarre la boucle Surveillance."""
        if self._actif:
            return
        self._actif = True
        self._loop_timer.start()
        self._on_loop_tick()
        logger.info("BotSurveillance démarré (cycle 60s)")

    def arreter(self) -> None:
        """Désactive l'interrupteur → suspend la boucle Surveillance."""
        if not self._actif:
            return
        self._actif = False
        self._loop_timer.stop()
        logger.info("BotSurveillance arrêté")

    def _on_loop_tick(self) -> None:
        """Tick périodique : nettoie les événements obsolètes du flux."""
        if not self._actif:
            return
        # Limiter le nombre de cartes si le flux dépasse le max autorisé
        if len(self._feed_cards) > self.MAX_FEED_ITEMS:
            surplus = len(self._feed_cards) - self.MAX_FEED_ITEMS
            for _ in range(surplus):
                old_card = self._feed_cards.pop(0)
                if self._feed_layout:
                    self._feed_layout.removeWidget(old_card)
                old_card.deleteLater()
            logger.debug("BotSurveillance tick — nettoyage de %d événements", surplus)
        logger.debug("BotSurveillance tick — %d événements dans le flux", len(self._feed_cards))

    # ── Construction UI ───────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Construit la mise en page complète du bot."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # ── Titre ──
        title = QLabel("🔍 Surveillance")
        title.setStyleSheet(f"""
            QLabel {{
                font-size: 22px;
                font-weight: 700;
                color: {COLORS["TEXT_PRIMARY"]};
                padding-bottom: 2px;
            }}
        """)
        layout.addWidget(title)

        # ── Barre d'indicateurs ──
        self._build_stats_bar(layout)

        # ── Barre d'outils ──
        self._build_toolbar(layout)

        # ── Séparateur ──
        sep = QFrame()
        # pyrefly: ignore [missing-attribute]
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {COLORS['BORDER']}; max-height: 1px;")
        layout.addWidget(sep)

        # ── Flux d'événements en direct ──
        self._build_feed(layout)

    # ── Barre d'indicateurs ──────────────────────────────────────────

    def _build_stats_bar(self, parent_layout: QVBoxLayout) -> None:
        """Construit la rangée de badges statistiques + bouton pause."""
        bar = QFrame()
        bar.setObjectName("statsBar")
        bar.setFixedHeight(48)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Badges
        self._badge_errors = _StatBadge("🔴", "Erreurs 24h", COLORS["DANGER"])
        self._badge_warns = _StatBadge("🟡", "Avertiss. 24h", COLORS["WARNING"])
        self._badge_total = _StatBadge("📊", "Total aujourd'hui", COLORS["ACCENT"])

        layout.addWidget(self._badge_errors)
        layout.addWidget(self._badge_warns)
        layout.addWidget(self._badge_total)

        layout.addStretch(1)

        # Bouton Pause
        self._pause_btn = QPushButton("⏸ Pause")
        self._pause_btn.setObjectName("pauseBtn")
        self._pause_btn.setCheckable(True)
        self._pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pause_btn.setFixedHeight(32)
        self._pause_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS["BG_BTN"]};
                color: {COLORS["TEXT_PRIMARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 4px 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {COLORS["BG_HOVER"]};
                border-color: {COLORS["BORDER_HOVER"]};
            }}
            QPushButton:checked {{
                background: {COLORS["DANGER_BG_HOVER"]};
                color: {COLORS["DANGER"]};
                border-color: {COLORS["DANGER"]};
            }}
        """)
        self._pause_btn.toggled.connect(self._on_pause_toggled)
        layout.addWidget(self._pause_btn)

        parent_layout.addWidget(bar)

    # ── Barre d'outils ───────────────────────────────────────────────

    def _build_toolbar(self, parent_layout: QVBoxLayout) -> None:
        """Construit la barre d'outils : recherche + filtres + actions."""
        toolbar = QFrame()
        toolbar.setObjectName("toolbar")
        toolbar.setFixedHeight(36)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # ── Champ de recherche ──
        self._search_input = QLineEdit()
        self._search_input.setObjectName("searchInput")
        self._search_input.setPlaceholderText("🔍  Rechercher dans les événements…")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.setFixedWidth(260)
        self._search_input.setFixedHeight(28)
        self._search_input.setStyleSheet(f"""
            QLineEdit {{
                background: {COLORS["BG_INPUT"]};
                color: {COLORS["TEXT_INPUT"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 2px 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS["ACCENT"]};
            }}
            QLineEdit::placeholder {{
                color: {COLORS["TEXT_PLACEHOLDER"]};
            }}
        """)
        # Debounce 300ms sur la recherche
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._apply_filters)

        self._search_input.textChanged.connect(self._on_search_changed)
        layout.addWidget(self._search_input)

        # ── Filtres par catégorie ──
        self._filter_buttons: dict[str, _FilterToggle] = {}
        for cat, label in self.CATEGORIES:
            btn = _FilterToggle(label)
            btn.toggled.connect(lambda checked, c=cat: self._on_category_toggle(c, checked))
            layout.addWidget(btn)
            self._filter_buttons[cat] = btn

        layout.addStretch(1)

        # ── Bouton Historique ──
        self._history_btn = QPushButton("📅 Historique")
        self._history_btn.setObjectName("historyBtn")
        self._history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._history_btn.setFixedHeight(28)
        self._history_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS["BG_BTN"]};
                color: {COLORS["TEXT_PRIMARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {COLORS["BG_HOVER"]};
                border-color: {COLORS["BORDER_HOVER"]};
            }}
        """)
        self._history_btn.clicked.connect(self._show_history)
        layout.addWidget(self._history_btn)

        # ── Bouton Vider ──
        self._clear_btn = QPushButton("🗑 Vider")
        self._clear_btn.setObjectName("clearBtn")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.setFixedHeight(28)
        self._clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS["BG_BTN"]};
                color: {COLORS["TEXT_SECONDARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {COLORS["DANGER_BG_HOVER"]};
                color: {COLORS["DANGER"]};
                border-color: {COLORS["DANGER"]};
            }}
        """)
        self._clear_btn.clicked.connect(self._clear_feed)
        layout.addWidget(self._clear_btn)

        parent_layout.addWidget(toolbar)

    # ── Flux d'événements ───────────────────────────────────────────────

    def _build_feed(self, parent_layout: QVBoxLayout) -> None:
        """Construit la zone de scroll contenant les cartes d'événements."""
        self._feed_scroll = QScrollArea()
        self._feed_scroll.setObjectName("feedScroll")
        self._feed_scroll.setWidgetResizable(True)
        # pyrefly: ignore [missing-attribute]
        self._feed_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # pyrefly: ignore [missing-attribute]
        self._feed_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # pyrefly: ignore [missing-attribute]
        self._feed_scroll.setFrameShape(QFrame.NoFrame)
        self._feed_scroll.setMinimumHeight(200)
        self._feed_scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: {COLORS["BG_SURFACE"]};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS["BORDER"]};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {COLORS["BORDER_HOVER"]};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        # Conteneur interne
        container = QFrame()
        container.setObjectName("feedContainer")
        container.setStyleSheet(f"background: transparent;")

        self._feed_layout = QVBoxLayout(container)
        self._feed_layout.setContentsMargins(0, 4, 0, 4)
        self._feed_layout.setSpacing(2)
        self._feed_layout.addStretch(1)  # pousse les cartes vers le haut

        self._feed_scroll.setWidget(container)

        # Détection auto-scroll : si l'utilisateur remonte, on arrête l'auto-scroll
        scrollbar = self._feed_scroll.verticalScrollBar()
        scrollbar.valueChanged.connect(self._on_scroll_changed)

        parent_layout.addWidget(self._feed_scroll, stretch=1)

    def _on_scroll_changed(self, value: int) -> None:
        """Détecte si l'utilisateur a remonté manuellement le scroll."""
        # pyrefly: ignore [missing-attribute]
        scrollbar = self._feed_scroll.verticalScrollBar()
        at_bottom = value >= scrollbar.maximum() - 20
        self._auto_scroll = at_bottom

    # ── Gestion des événements ───────────────────────────────────────

    def _on_search_changed(self, text: str) -> None:
        """Redémarre le timer de debounce pour la recherche."""
        self._search_timer.stop()
        self._search_timer.start(300)  # 300ms

    def _on_category_toggle(self, category: str, checked: bool) -> None:
        """Bascule l'affichage d'une catégorie d'événements."""
        if checked:
            self._filtres_categories.add(category)
        else:
            self._filtres_categories.discard(category)
        self._apply_filters()

    @log_action("Mettre en pause/reprendre la surveillance")
    def _on_pause_toggled(self, paused: bool) -> None:
        """Bascule la pause (collection + affichage)."""
        self._paused = paused
        self._pause_btn.setText("▶ Reprendre" if paused else "⏸ Pause")
        if paused:
            EventBus().pause()
        else:
            EventBus().resume()

    def _on_event_received(self, event: SurveillanceEvent) -> None:
        """Reçoit un événement de l'EventBus et l'ajoute au flux."""
        if self._paused:
            return

        # Mettre à jour le compteur d'événements non lus
        # Si la page n'est pas visible, incrémenter le badge
        if not self.isVisible():
            self._unseen_count += 1
            self.unseen_count_changed.emit(self._unseen_count)

        # Mettre à jour les badges stats
        if event.severity == "ERROR":
            self._stats_errors += 1
        elif event.severity == "WARN":
            self._stats_warns += 1
        self._stats_total += 1
        self.update_stats(self._stats_errors, self._stats_warns, self._stats_total)

        card = _EventCard(event=event)

        # Insérer la carte avant le stretch
        if self._feed_layout:
            self._feed_layout.insertWidget(
                self._feed_layout.count() - 1,  # avant le stretch
                card,
            )
            self._feed_cards.append(card)
            # Connecter le signal de détail
            card.detail_requested.connect(self._show_detail_popup)

        # Appliquer les filtres en cours
        card.setVisible(
            card.matches_filter(
                self._filtre_texte,
                self._filtres_categories,
            )
        )

        # Auto-scroll vers le bas
        if self._auto_scroll and self._feed_scroll:
            scrollbar = self._feed_scroll.verticalScrollBar()
            QTimer.singleShot(50, lambda: scrollbar.setValue(scrollbar.maximum()))

        # Limiter le nombre de cartes en mémoire
        if len(self._feed_cards) > self.MAX_FEED_ITEMS:
            old_card = self._feed_cards.pop(0)
            if self._feed_layout:
                self._feed_layout.removeWidget(old_card)
            old_card.deleteLater()

    def _apply_filters(self) -> None:
        """Applique les filtres texte + catégories au flux affiché."""
        self._filtre_texte = self._search_input.text().strip().lower()
        for card in self._feed_cards:
            card.setVisible(
                card.matches_filter(
                    self._filtre_texte,
                    self._filtres_categories,
                )
            )

    @log_action("Vider le flux d'événements")
    def _clear_feed(self) -> None:
        """Vide le flux affiché (pas la base SQLite)."""
        for card in self._feed_cards:
            # pyrefly: ignore [missing-attribute]
            self._feed_layout.removeWidget(card)
            card.deleteLater()
        self._feed_cards.clear()

    def _show_detail_popup(self, event: "SurveillanceEvent") -> None:
        """Ouvre le popup de détails pour un événement."""
        popup = DetailPopup(event, self)
        popup.exec()

    @log_action("Ouvrir l'historique")
    def _show_history(self) -> None:
        """Ouvre la modal d'historique."""
        modal = HistoryModal(self)
        modal.exec()

    # ── API publique ─────────────────────────────────────────────────

    def update_stats(self, errors: int, warns: int, total: int) -> None:
        """Met à jour les badges de la barre d'indicateurs."""
        self._stats_errors = errors
        self._stats_warns = warns
        self._stats_total = total

        self._badge_errors.set_value(errors)
        self._badge_warns.set_value(warns)
        self._badge_total.set_value(total)

    def reset_unseen_count(self) -> None:
        """Réinitialise le compteur d'événements non lus (badge footer)."""
        self._unseen_count = 0
        self.unseen_count_changed.emit(0)

    def is_paused(self) -> bool:
        """Retourne True si la collecte est en pause."""
        return self._paused

    def active_categories(self) -> set[str]:
        """Retourne l'ensemble des catégories actuellement affichées."""
        return self._filtres_categories

    def search_text(self) -> str:
        """Retourne le texte de recherche actuel."""
        return self._filtre_texte


# ── Modal historique ─────────────────────────────────────────────────────


class HistoryModal(QDialog):
    """Fenêtre modale d'historique : recherche, filtres, export, suppression."""

    PAGE_SIZE = 50

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("📅 Historique des événements")
        self.setMinimumSize(900, 600)
        self.setModal(True)
        self.setObjectName("historyModal")

        # État
        self._page = 0
        self._has_more = True
        self._events: list[SurveillanceEvent] = []

        self._build_ui()
        self._load_page()

        self.setStyleSheet(f"""
            #historyModal {{
                background: {COLORS["BG_SURFACE"]};
            }}
        """)

    # ── Construction UI ────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # ── Barre de recherche (texte, dates, catégorie) ──
        filter_bar = QFrame()
        filter_bar.setObjectName("historyFilterBar")
        filter_layout = QHBoxLayout(filter_bar)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(8)

        # Recherche textuelle
        self._search_input = QLineEdit()
        self._search_input.setObjectName("historySearchInput")
        self._search_input.setPlaceholderText("🔍  Rechercher…")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.setFixedWidth(200)
        self._search_input.returnPressed.connect(self._rechercher)
        filter_layout.addWidget(self._search_input)

        filter_layout.addWidget(QLabel("Du:"))
        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setDate(QDate.currentDate().addDays(-7))
        self._date_from.setDisplayFormat("yyyy-MM-dd")
        self._date_from.setFixedWidth(130)
        filter_layout.addWidget(self._date_from)

        filter_layout.addWidget(QLabel("Au:"))
        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setDate(QDate.currentDate())
        self._date_to.setDisplayFormat("yyyy-MM-dd")
        self._date_to.setFixedWidth(130)
        filter_layout.addWidget(self._date_to)

        filter_layout.addWidget(QLabel("Catégorie:"))
        self._cat_combo = QComboBox()
        self._cat_combo.addItem("Toutes", None)
        CAT_MAP = [
            ("reseau", "🌐 Réseau"),
            ("transfert", "📥 Transferts"),
            ("recherche", "🔎 Recherche"),
            ("bibliotheque", "📚 Bibliothèque"),
            ("configuration", "⚙️ Config"),
            ("erreur", "❌ Erreurs"),
            ("bot", "🤖 Bots"),
        ]
        for val, label in CAT_MAP:
            self._cat_combo.addItem(label, val)
        self._cat_combo.setFixedWidth(150)
        filter_layout.addWidget(self._cat_combo)

        # Bouton Rechercher
        search_btn = QPushButton("🔍 Rechercher")
        search_btn.setObjectName("historySearchBtn")
        search_btn.clicked.connect(self._rechercher)
        filter_layout.addWidget(search_btn)

        filter_layout.addStretch(1)
        layout.addWidget(filter_bar)

        # ── Tableau ──
        self._table = QTableWidget()
        self._table.setObjectName("historyTable")
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(["", "Sévérité", "Date", "Catégorie", "Titre", "Source"])
        # pyrefly: ignore [missing-attribute]
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)

        header = self._table.horizontalHeader()
        # pyrefly: ignore [missing-attribute]
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.resizeSection(0, 40)
        # pyrefly: ignore [missing-attribute]
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.resizeSection(1, 80)
        # pyrefly: ignore [missing-attribute]
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.resizeSection(2, 160)
        # pyrefly: ignore [missing-attribute]
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.resizeSection(3, 100)
        # pyrefly: ignore [missing-attribute]
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        # pyrefly: ignore [missing-attribute]
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        header.resizeSection(5, 120)

        self._table.setStyleSheet(f"""
            #historyTable {{
                background: {COLORS["BG_SURFACE"]};
                color: {COLORS["TEXT_PRIMARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 8px;
                font-size: 12px;
            }}
            #historyTable::item {{
                padding: 6px 8px;
            }}
            #historyTable::item:selected {{
                background: {COLORS["BG_HOVER"]};
                color: {COLORS["TEXT_PRIMARY"]};
            }}
            QHeaderView::section {{
                background: {COLORS["BG_SURFACE"]};
                color: {COLORS["TEXT_MUTED"]};
                border: none;
                border-bottom: 1px solid {COLORS["BORDER"]};
                padding: 8px;
                font-size: 11px;
                font-weight: 600;
            }}
        """)
        layout.addWidget(self._table, stretch=1)

        # ── Barre du bas : pagination + actions ──
        bottom_bar = QFrame()
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(8)

        # Pagination
        self._load_more_btn = QPushButton("📥 Charger plus")
        self._load_more_btn.setObjectName("loadMoreBtn")
        self._load_more_btn.clicked.connect(self._load_more)
        bottom_layout.addWidget(self._load_more_btn)

        self._result_count_lbl = QLabel("")
        self._result_count_lbl.setStyleSheet(f"color: {COLORS['TEXT_MUTED']}; font-size: 11px;")
        bottom_layout.addWidget(self._result_count_lbl)

        bottom_layout.addStretch(1)

        # Export CSV
        export_csv_btn = QPushButton("📋 CSV")
        export_csv_btn.setObjectName("exportCsvBtn")
        export_csv_btn.clicked.connect(self._export_csv)
        bottom_layout.addWidget(export_csv_btn)

        # Export JSON
        export_json_btn = QPushButton("📋 JSON")
        export_json_btn.setObjectName("exportJsonBtn")
        export_json_btn.clicked.connect(self._export_json)
        bottom_layout.addWidget(export_json_btn)

        # Supprimer sélection
        delete_btn = QPushButton("🗑 Suppr. sélection")
        delete_btn.setObjectName("deleteSelBtn")
        delete_btn.clicked.connect(self._delete_selected)
        bottom_layout.addWidget(delete_btn)

        # Bouton Fermer
        close_btn = QPushButton("Fermer")
        close_btn.setObjectName("closeBtn")
        close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(close_btn)

        layout.addWidget(bottom_bar)

        # Style des boutons
        btn_style = f"""
            QPushButton {{
                background: {COLORS["BG_BTN"]};
                color: {COLORS["TEXT_PRIMARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {COLORS["BG_HOVER"]};
                border-color: {COLORS["BORDER_HOVER"]};
            }}
        """
        for btn in [self._load_more_btn, search_btn, export_csv_btn, export_json_btn, delete_btn, close_btn]:
            btn.setStyleSheet(btn_style)
            btn.setFixedHeight(30)

    # ── Requêtes ───────────────────────────────────────────────────────

    def _build_filters(self) -> dict:
        """Construit le dict de filtres à partir de l'UI."""
        filters: dict = {}
        search = self._search_input.text().strip()
        if search:
            filters["search"] = search

        cat = self._cat_combo.currentData()
        if cat is not None:
            filters["category"] = cat

        d_from = self._date_from.date().toString("yyyy-MM-dd")
        d_to = self._date_to.date().toString("yyyy-MM-dd")
        filters["date_from"] = d_from
        filters["date_to"] = f"{d_to} 23:59:59"

        return filters

    def _load_page(self) -> None:
        """Charge une page d'événements depuis l'EventBus."""
        filters = self._build_filters()
        filters["limit"] = self.PAGE_SIZE
        filters["offset"] = self._page * self.PAGE_SIZE

        events = EventBus().query(**filters)
        self._events.extend(events)
        self._has_more = len(events) >= self.PAGE_SIZE
        self._populate_table()

        total = len(self._events)
        self._result_count_lbl.setText(f"{total} résultat{'s' if total != 1 else ''}")
        self._load_more_btn.setEnabled(self._has_more)

    @log_action("Charger plus d'événements")
    def _load_more(self) -> None:
        """Charge la page suivante."""
        self._page += 1
        self._load_page()

    @log_action("Rechercher dans l'historique")
    def _rechercher(self) -> None:
        """Réinitialise la recherche (page 0)."""
        self._page = 0
        self._events.clear()
        self._load_page()

    # ── Populate tableau ───────────────────────────────────────────────

    def _populate_table(self) -> None:
        """Remplit le tableau avec les événements chargés."""
        self._table.setRowCount(len(self._events))
        SEVERITY_LABELS = {"ERROR": "🔴 Erreur", "WARN": "🟡 Avert.", "INFO": "🔵 Info"}

        for row, evt in enumerate(self._events):
            # Checkbox
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            chk.setCheckState(Qt.CheckState.Unchecked)
            chk.setData(Qt.ItemDataRole.UserRole, evt.id)
            self._table.setItem(row, 0, chk)

            # Sévérité
            sev_label = SEVERITY_LABELS.get(evt.severity, evt.severity)
            sev_item = QTableWidgetItem(sev_label)
            sev_item.setFlags(sev_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 1, sev_item)

            # Date
            date_item = QTableWidgetItem(evt.timestamp)
            date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 2, date_item)

            # Catégorie
            cat_item = QTableWidgetItem(evt.category)
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 3, cat_item)

            # Titre
            title_item = QTableWidgetItem(evt.title)
            title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 4, title_item)

            # Source
            src_item = QTableWidgetItem(evt.source)
            src_item.setFlags(src_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 5, src_item)

        self._table.resizeRowsToContents()

    # ── Export ──────────────────────────────────────────────────────────

    @log_action("Exporter en CSV")
    def _export_csv(self) -> None:
        """Exporte les événements affichés en CSV."""
        path, _ = QFileDialog.getSaveFileName(self, "Exporter en CSV", "historique.csv", "CSV (*.csv)")
        if not path:
            return

        try:
            import csv

            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Sévérité", "Date", "Catégorie", "Titre", "Message", "Source", "Détails"])
                for evt in self._events:
                    writer.writerow(
                        [
                            evt.id,
                            evt.severity,
                            evt.timestamp,
                            evt.category,
                            evt.title,
                            evt.message,
                            evt.source,
                            str(evt.details) if evt.details else "",
                        ]
                    )
            QMessageBox.information(self, "Export CSV", f"✓ {len(self._events)} événements exportés.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur CSV", f"Échec de l'export : {e}")

    @log_action("Exporter en JSON")
    def _export_json(self) -> None:
        """Exporte les événements affichés en JSON."""
        path, _ = QFileDialog.getSaveFileName(self, "Exporter en JSON", "historique.json", "JSON (*.json)")
        if not path:
            return

        try:
            import json
            from dataclasses import asdict

            data = [asdict(e) for e in self._events]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            QMessageBox.information(self, "Export JSON", f"✓ {len(self._events)} événements exportés.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur JSON", f"Échec de l'export : {e}")

    @log_action("Supprimer la sélection")
    def _delete_selected(self) -> None:
        """Supprime les événements cochés."""
        ids: list[int] = []
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                evt_id = item.data(Qt.ItemDataRole.UserRole)
                if evt_id is not None:
                    ids.append(evt_id)

        if not ids:
            QMessageBox.information(self, "Suppression", "Aucun événement sélectionné.")
            return

        reply = QMessageBox.question(
            self,
            "Confirmer",
            f"Supprimer {len(ids)} événement{'s' if len(ids) > 1 else ''} ?",
            # pyrefly: ignore [missing-attribute]
            QMessageBox.Yes | QMessageBox.No,
        )
        # pyrefly: ignore [missing-attribute]
        if reply != QMessageBox.Yes:
            return

        try:
            EventBus().delete_events(ids)
            # Retirer les événements supprimés de la liste locale
            self._events = [e for e in self._events if e.id not in ids]
            self._populate_table()
            self._result_count_lbl.setText(f"{len(self._events)} résultat{'s' if len(self._events) != 1 else ''}")
            QMessageBox.information(
                self,
                "Suppression",
                f"✓ {len(ids)} événement{'s' if len(ids) > 1 else ''} supprimé{'s' if len(ids) > 1 else ''}.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec de la suppression : {e}")


# ── Popup de détails ────────────────────────────────────────────────────


class DetailPopup(QDialog):
    """Fenêtre modale affichant les détails complets d'un événement."""

    def __init__(
        self,
        event: "SurveillanceEvent",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._event = event

        self.setWindowTitle("Détails de l'événement")
        self.setMinimumSize(520, 400)
        self.setModal(True)
        self.setObjectName("detailPopup")

        self._build_ui()

        self.setStyleSheet(f"""
            #detailPopup {{
                background: {COLORS["BG_SURFACE"]};
            }}
        """)

    # ── Construction UI ────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # ── En-tête : sévérité + titre ──
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        SEVERITY_ICONS = {"ERROR": "\U0001f534", "WARN": "\U0001f7e1", "INFO": "\U0001f535"}
        SEVERITY_LABELS = {"ERROR": "Erreur", "WARN": "Avertissement", "INFO": "Information"}
        SEVERITY_COLORS = {"ERROR": "#e74c3c", "WARN": "#f39c12", "INFO": "#3498db"}

        icon_label = QLabel(SEVERITY_ICONS.get(self._event.severity, "\u26aa"))
        icon_label.setStyleSheet("font-size: 28px;")
        icon_label.setFixedWidth(40)
        header_layout.addWidget(icon_label)

        sev_color = SEVERITY_COLORS.get(self._event.severity, "transparent")
        title_text = SEVERITY_LABELS.get(self._event.severity, self._event.severity)
        title_lbl = QLabel(self._event.title)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {COLORS["TEXT_PRIMARY"]};
        """)
        header_layout.addWidget(title_lbl, stretch=1)

        # Badge sévérité
        sev_badge = QLabel(title_text)
        sev_bg = rgba(sev_color, "22")
        sev_border = rgba(sev_color, "44")
        sev_badge.setStyleSheet(f"""
            background: {sev_bg};
            color: {sev_color};
            border: 1px solid {sev_border};
            border-radius: 10px;
            padding: 4px 12px;
            font-size: 11px;
            font-weight: 600;
        """)
        header_layout.addWidget(sev_badge)

        layout.addWidget(header)

        # ── Séparateur ──
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {COLORS['BORDER']}; max-height: 1px;")
        layout.addWidget(sep)

        # ── Grille d'informations ──
        grid = QFrame()
        grid.setObjectName("detailGrid")
        grid_layout = QGridLayout(grid)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(12)

        self._add_field(grid_layout, 0, "\U0001f4c5", "Date", self._event.timestamp)

        cat_icons = {
            "reseau": "\U0001f310",
            "transfert": "\U0001f4e5",
            "recherche": "\U0001f50e",
            "bibliotheque": "\U0001f4da",
            "configuration": "\u2699\ufe0f",
            "erreur": "\u274c",
            "bot": "\U0001f916",
        }
        cat_icon = cat_icons.get(self._event.category, "\ud83c\udfaf")
        self._add_field(grid_layout, 1, cat_icon, "Catégorie", self._event.category)

        if self._event.source:
            self._add_field(grid_layout, 2, "\ud83d\udccd", "Source", self._event.source)

        # ── Message ──
        row = grid_layout.rowCount()
        msg_icon = QLabel("\ud83d\udce3")
        msg_icon.setStyleSheet("font-size: 14px;")
        msg_icon.setFixedWidth(20)
        msg_icon.setAlignment(Qt.AlignmentFlag.AlignTop)
        grid_layout.addWidget(msg_icon, row, 0, Qt.AlignmentFlag.AlignTop)

        msg_label = QLabel("Message")
        msg_label.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {COLORS['TEXT_MUTED']};")
        grid_layout.addWidget(msg_label, row, 1, Qt.AlignmentFlag.AlignTop)

        msg_content = QLabel(self._event.message)
        msg_content.setWordWrap(True)
        msg_content.setStyleSheet(
            f"font-size: 12px; color: {COLORS['TEXT_PRIMARY']}; background: {COLORS['BG_SURFACE']}; border-radius: 6px; padding: 8px;"
        )
        grid_layout.addWidget(msg_content, row, 2)

        # ── Détails supplémentaires ──
        if self._event.details:
            row = grid_layout.rowCount()
            det_icon = QLabel("\ud83d\udcca")
            det_icon.setStyleSheet("font-size: 14px;")
            det_icon.setFixedWidth(20)
            det_icon.setAlignment(Qt.AlignmentFlag.AlignTop)
            grid_layout.addWidget(det_icon, row, 0, Qt.AlignmentFlag.AlignTop)

            det_label = QLabel("Détails")
            det_label.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {COLORS['TEXT_MUTED']};")
            grid_layout.addWidget(det_label, row, 1, Qt.AlignmentFlag.AlignTop)

            det_content = QLabel(str(self._event.details))
            det_content.setWordWrap(True)
            det_content.setStyleSheet(
                f"font-size: 12px; color: {COLORS['TEXT_PRIMARY']}; background: {COLORS['BG_SURFACE']}; border-radius: 6px; padding: 8px;"
            )
            grid_layout.addWidget(det_content, row, 2)

        grid.setStyleSheet(f"""
            #detailGrid {{
                background: transparent;
            }}
        """)
        layout.addWidget(grid, stretch=1)

        # ── Boutons d'action ──
        btn_bar = QFrame()
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)

        btn_layout.addStretch(1)

        btn_style = f"""
            QPushButton {{
                background: {COLORS["BG_BTN"]};
                color: {COLORS["TEXT_PRIMARY"]};
                border: 1px solid {COLORS["BORDER"]};
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {COLORS["BG_HOVER"]};
                border-color: {COLORS["BORDER_HOVER"]};
            }}
        """

        # Copier
        copy_btn = QPushButton("\U0001f4cb  Copier les détails")
        copy_btn.setStyleSheet(btn_style)
        copy_btn.setFixedHeight(34)
        copy_btn.clicked.connect(self._copy_details)
        btn_layout.addWidget(copy_btn)

        # Naviguer (si la catégorie le permet)
        nav_target = self._get_navigation_target()
        if nav_target:
            nav_btn = QPushButton(f"\U0001f517  Naviguer vers {nav_target}")
            nav_btn.setStyleSheet(btn_style)
            nav_btn.setFixedHeight(34)
            nav_btn.clicked.connect(self._navigate_to_source)
            btn_layout.addWidget(nav_btn)

        # Fermer
        close_btn = QPushButton("Fermer")
        close_btn.setStyleSheet(btn_style)
        close_btn.setFixedHeight(34)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addWidget(btn_bar)

    # ── Helpers ────────────────────────────────────────────────────────

    def _add_field(self, grid: QGridLayout, row: int, icon: str, label: str, value: str) -> None:
        """Ajoute une ligne clé-valeur dans la grille."""
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 14px;")
        icon_lbl.setFixedWidth(20)
        grid.addWidget(icon_lbl, row, 0)

        key_lbl = QLabel(label)
        key_lbl.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {COLORS['TEXT_MUTED']};")
        grid.addWidget(key_lbl, row, 1)

        val_lbl = QLabel(value)
        val_lbl.setWordWrap(True)
        val_lbl.setStyleSheet(f"font-size: 12px; color: {COLORS['TEXT_PRIMARY']};")
        grid.addWidget(val_lbl, row, 2)

    def _get_navigation_target(self) -> str | None:
        """Détermine la page de destination selon la catégorie de l'événement."""
        CATEGORY_PAGES = {
            "recherche": "Recherche",
            "transfert": "Téléchargement",
            "bibliotheque": "Bibliothèque",
            "reseau": "Recherche",
            "bot": "Surveillance",
            "configuration": "Recherche",
            "erreur": "Surveillance",
        }
        return CATEGORY_PAGES.get(self._event.category)

    @log_action("Copier les détails d'événement")
    def _copy_details(self) -> None:
        """Copie les détails formatés dans le presse-papier."""
        from PySide6.QtGui import QGuiApplication

        ICONS = {"ERROR": "\U0001f534", "WARN": "\U0001f7e1", "INFO": "\U0001f535"}
        icon = ICONS.get(self._event.severity, "\u26aa")
        lines = [
            f"[{icon}] {self._event.title}",
            f"",
            f"\ud83d\udcc5  Date       : {self._event.timestamp}",
            f"\ud83c\udfaf  Catégorie  : {self._event.category}",
            f"\ud83d\udccd  Source     : {self._event.source or '-'}",
            f"",
            f"\ud83d\udce3  Message    : {self._event.message}",
        ]
        if self._event.details:
            lines.append(f"\ud83d\udcca  Détails    : {self._event.details}")
        lines.append(f"")
        lines.append(f"ID: {self._event.id} | Exporté depuis Bot Surveillance")
        text = "\n".join(lines)
        QGuiApplication.clipboard().setText(text)

    @log_action("Naviguer depuis les détails")
    def _navigate_to_source(self) -> None:
        """Émet un signal pour naviguer vers la page correspondante."""
        target = self._get_navigation_target()
        if target and self.parent():
            # Remonter jusqu'au widget parent qui a le signal page_changed
            parent = self.parent()
            while parent and not hasattr(parent, "page_changed"):
                parent = parent.parent()
            if parent and hasattr(parent, "page_changed"):
                parent.page_changed.emit(target)
            self.accept()
