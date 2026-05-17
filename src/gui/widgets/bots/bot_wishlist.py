"""
Bot Wishlist — tableau de bord des souhaits automatiques Soulseek.

Permet de visualiser, ajouter, modifier, supprimer et superviser les
souhaits de recherche (wishlist) configurés sur Soulseek.

Ce n'est PAS un chatbot — l'utilisateur ne discute pas avec ce bot.
Les interactions se font via le bot Accueil et cette page sert à
visualiser et éditer les souhaits.
"""

from __future__ import annotations

import datetime
import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.gui.theme_fragments.colors import COLORS, rgba
from src.services import app_config
from src.services.event_bus import EventBus
from src.services.soulseek_client import soulseek_service

# ── Constantes ──────────────────────────────────────────────────

_CONFIG_KEY_WISHLIST = "recherche.souhaits"

_STYLE_STATUS_ACTIVE = COLORS["SUCCESS"]
_STYLE_STATUS_INACTIVE = COLORS["TEXT_SECONDARY"]
_STYLE_STATUS_ERROR = COLORS["DANGER_BTN"]

_LABEL_STATUS: dict[str, str] = {
    "active": "🟢 Actif",
    "inactive": "⚪ Inactif",
    "error": "❌ Erreur",
}

_COLOR_STATUS: dict[str, str] = {
    "active": _STYLE_STATUS_ACTIVE,
    "inactive": _STYLE_STATUS_INACTIVE,
    "error": _STYLE_STATUS_ERROR,
}


# ── Carte d'un souhait individuel ───────────────────────────────


class WishlistCard(QFrame):
    """Carte affichant un souhait individuel avec ses infos et actions."""

    toggled = Signal(str, bool)  # (query, new_enabled)
    edit_requested = Signal(str)  # (query)
    delete_requested = Signal(str)  # (query)
    search_now_requested = Signal(str)  # (query)

    def __init__(self, data: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._query = data["query"]
        self._enabled = data["enabled"]

        status = data.get("status", "active" if self._enabled else "inactive")
        color = _COLOR_STATUS.get(status, _STYLE_STATUS_INACTIVE)

        self.setObjectName("wishlistCard")
        border_color = color
        self.setStyleSheet(
            f"#wishlistCard {{"
            f"  background: {COLORS['BG_INPUT']}; border: 1px solid rgba(border_color, '44');"
            f"  border-radius: 8px; padding: 12px;"
            f"}}"
            f"#wishlistCard:hover {{"
            f"  border-color: {border_color};"
            f"}}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        # ── Ligne 1 : Statut + Requête ──
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        # Statut (toggle)
        self._toggle_btn = QPushButton(_LABEL_STATUS.get(status, "⚪ Inactif"))
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setFixedHeight(26)
        self._toggle_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {rgba(color, '22')}; color: {color};"
            f"  border: 1px solid {color}; border-radius: 13px;"
            f"  padding: 2px 12px; font-size: 11px; font-weight: 600;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {rgba(color, '44')};"
            f"}}"
        )
        self._toggle_btn.clicked.connect(self._on_toggle)
        row1.addWidget(self._toggle_btn)

        # Requête
        query_lbl = QLabel(f"<b>{data['query']}</b>")
        query_lbl.setWordWrap(True)
        query_lbl.setTextFormat(Qt.TextFormat.RichText)
        query_lbl.setStyleSheet(
            f"color: {COLORS['TEXT_PRIMARY']}; font-size: 14px; background: transparent; border: none;"
        )
        row1.addWidget(query_lbl, 1)

        layout.addLayout(row1)

        # ── Ligne 2 : Métadonnées ──
        row2 = QHBoxLayout()
        row2.setSpacing(16)

        results_icon = "📅" if data.get("results", 0) > 0 else "📭"
        meta_text = (
            f"{results_icon} {data.get('results', 0)} résultat(s) • Dernière : {data.get('last_search', 'jamais')}"
        )
        meta_lbl = QLabel(meta_text)
        meta_lbl.setStyleSheet(
            f"color: {COLORS['TEXT_SECONDARY']}; font-size: 12px; background: transparent; border: none;"
        )
        row2.addWidget(meta_lbl)

        # Fréquence (lecture seule, globale)
        freq_lbl = QLabel("🔄 Fréquence : globale")
        freq_lbl.setStyleSheet(
            f"color: {COLORS['TEXT_MUTED']}; font-size: 11px; background: transparent; border: none;"
        )
        row2.addWidget(freq_lbl)

        row2.addStretch(1)
        layout.addLayout(row2)

        # ── Ligne 3 : Boutons d'action ──
        row3 = QHBoxLayout()
        row3.setSpacing(6)

        self._edit_btn = _ActionButton("✏️ Modifier", COLORS["ACCENT"])
        self._edit_btn.clicked.connect(lambda: self.edit_requested.emit(self._query))
        row3.addWidget(self._edit_btn)

        self._search_btn = _ActionButton("🔍 Chercher", COLORS["SUCCESS"])
        self._search_btn.clicked.connect(lambda: self.search_now_requested.emit(self._query))
        row3.addWidget(self._search_btn)

        row3.addStretch(1)

        self._delete_btn = _ActionButton("🗑️ Supprimer", "#e74c3c")
        self._delete_btn.clicked.connect(lambda: self.delete_requested.emit(self._query))
        row3.addWidget(self._delete_btn)

        layout.addLayout(row3)

    def _on_toggle(self) -> None:
        """Bascule l'état actif/inactif du souhait."""
        self._enabled = not self._enabled
        status = "active" if self._enabled else "inactive"
        color = _COLOR_STATUS[status]
        self._toggle_btn.setText(_LABEL_STATUS[status])
        self._toggle_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {rgba(color, '22')}; color: {color};"
            f"  border: 1px solid {color}; border-radius: 13px;"
            f"  padding: 2px 12px; font-size: 11px; font-weight: 600;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {rgba(color, '44')};"
            f"}}"
        )
        self.toggled.emit(self._query, self._enabled)


class _ActionButton(QPushButton):
    """Petit bouton d'action stylisé."""

    def __init__(self, text: str, color: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent; color: {color};"
            f"  border: 1px solid {rgba(color, '44')}; border-radius: 10px;"
            f"  padding: 4px 10px; font-size: 11px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {rgba(color, '22')}; border-color: {color};"
            f"}}"
        )


# ── Filtres ─────────────────────────────────────────────────────


class _FilterButton(QPushButton):
    """Bouton de filtre (Tous / Actifs / Inactifs / Erreurs)."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setStyleSheet(
            "QPushButton {"
            f"  background: transparent; color: {COLORS['TEXT_SECONDARY']};"
            f"  border: 1px solid {COLORS['TEXT_PLACEHOLDER']}; border-radius: 14px;"
            "  padding: 6px 14px; font-size: 11px;"
            "}"
            "QPushButton:hover {"
            f"  background: {COLORS['BG_HOVER']}; color: {COLORS['TEXT_TERTIARY']};"
            "}"
            "QPushButton:checked {"
            f"  background: COLORS['ACCENT']44; color: COLORS['ACCENT'];"
            f"  border-color: COLORS['ACCENT'];"
            "}"
        )


# ── Statistiques ────────────────────────────────────────────────


class _StatCard(QFrame):
    """Badge de statistique compact (ex: '🎵 42 Actifs')."""

    def __init__(self, value: str | int, label: str, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statCardBadge")
        self.setStyleSheet(f"#statCardBadge {{  background: {COLORS['BG_BTN']}; border-radius: 4px;}}")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 10, 3)
        layout.setSpacing(4)

        value_lbl = QLabel(str(value))
        value_lbl.setStyleSheet(
            f"color: {COLORS['TEXT_PRIMARY']}; font-size: 13px; font-weight: 600;"
            " background: transparent; border: none;"
        )
        layout.addWidget(value_lbl)

        label_lbl = QLabel(label)
        label_lbl.setStyleSheet(
            f"color: {COLORS['TEXT_SECONDARY']}; font-size: 11px; background: transparent; border: none;"
        )
        layout.addWidget(label_lbl)


# ═════════════════════════════════════════════════════════════════
#  Bot Wishlist — Tableau de bord principal
# ═════════════════════════════════════════════════════════════════


class BotWishlist(QFrame):
    """Bot Wishlist — tableau de bord des souhaits automatiques Soulseek.

    Signaux
    -------
    wishlist_changed : Signal()
        Émis quand la liste des souhaits est modifiée (ajout, suppression, toggle).
    """

    wishlist_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("botWishlist")

        # Données
        self._wishlist: list[dict] = []
        self._local_metadata: dict[str, dict] = {}  # query → {results, last_search, status}
        self._filter: str = "all"  # all | active | inactive | error
        self._search_text: str = ""
        self._edit_mode: bool = False  # True pendant l'édition inline
        self._edit_old_query: str = ""

        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 8)
        layout.setSpacing(0)

        # ── 1. En-tête ──
        header = QLabel("📋 Wishlist — Souhaits automatiques")
        header.setStyleSheet(f"color: {COLORS['ACCENT']}; font-size: 18px; font-weight: 700; padding: 0 0 12px 0;")
        layout.addWidget(header)

        # ── 2. Résumé (stats) ──
        self._stats_widget = QWidget()
        self._stats_widget.setObjectName("statsWidget")
        self._stats_widget.setStyleSheet("#statsWidget { background: transparent; }")
        self._stats_layout = QHBoxLayout(self._stats_widget)
        self._stats_layout.setContentsMargins(0, 0, 0, 12)
        self._stats_layout.setSpacing(8)
        layout.addWidget(self._stats_widget)

        # ── 3. Barre d'outils ──
        toolbar = QWidget()
        toolbar.setObjectName("toolbar")
        toolbar.setStyleSheet("#toolbar { background: transparent; }")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 10)
        toolbar_layout.setSpacing(8)

        # Champ de recherche
        self._search_field = QLineEdit()
        self._search_field.setPlaceholderText("🔍 Rechercher un souhait…")
        self._search_field.setStyleSheet(
            "QLineEdit {"
            f"  background: {COLORS['BG_INPUT']}; color: {COLORS['TEXT_PRIMARY']};"
            f"  border: 1px solid {COLORS['TEXT_PLACEHOLDER']}; border-radius: 10px;"
            "  padding: 6px 12px; font-size: 12px; max-width: 220px;"
            "}"
            f"QLineEdit:focus {{ border-color: {COLORS['ACCENT']}; }}"
        )
        self._search_field.textChanged.connect(self._on_search)
        toolbar_layout.addWidget(self._search_field)

        # Filtres
        self._filter_buttons: dict[str, _FilterButton] = {}
        for f_id, f_label in [
            ("all", "📋 Tous"),
            ("active", "🟢 Actifs"),
            ("inactive", "⚪ Inactifs"),
            ("error", "❌ Erreurs"),
        ]:
            btn = _FilterButton(f_label)
            btn.clicked.connect(lambda checked=False, fid=f_id: self._apply_filter(fid))
            self._filter_buttons[f_id] = btn
            toolbar_layout.addWidget(btn)

        # Bouton "Tout cocher/décocher"
        self._toggle_all_btn = QPushButton("🔄 Tout basculer")
        self._toggle_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_all_btn.setStyleSheet(
            "QPushButton {"
            f"  background: transparent; color: {COLORS['TEXT_SECONDARY']};"
            f"  border: 1px solid {COLORS['TEXT_PLACEHOLDER']}; border-radius: 10px;"
            "  padding: 6px 12px; font-size: 11px;"
            "}"
            f"QPushButton:hover {{ background: {COLORS['BG_HOVER']}; color: {COLORS['TEXT_TERTIARY']}; }}"
        )
        self._toggle_all_btn.clicked.connect(self._on_toggle_all)
        toolbar_layout.addWidget(self._toggle_all_btn)

        toolbar_layout.addStretch(1)

        # Bouton Ajouter
        self._add_btn = QPushButton("➕ Ajouter un souhait")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.setStyleSheet(
            "QPushButton {"
            f"  background: COLORS['ACCENT']; color: {COLORS['TEXT_WHITE']};"
            "  border: none; border-radius: 10px;"
            "  padding: 6px 16px; font-size: 12px; font-weight: 600;"
            "}"
            f"QPushButton:hover {{ background: {COLORS['ACCENT_HOVER']}; }}"
            f"QPushButton:pressed {{ background: {COLORS['ACCENT_HOVER']}; }}"
        )
        self._add_btn.clicked.connect(self._on_add_click)
        toolbar_layout.addWidget(self._add_btn)

        layout.addWidget(toolbar)

        # ── 4. Zone scrollable de la liste ──
        self._list_widget = QWidget()
        self._list_widget.setObjectName("wishlistList")
        self._list_widget.setStyleSheet("#wishlistList { background: transparent; }")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        self._list_layout.addStretch(1)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidget(self._list_widget)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll_area.setStyleSheet("QScrollArea { background: transparent; }")

        layout.addWidget(self._scroll_area, 1)

        # ── 5. Barre d'ajout rapide (cachée par défaut) ──
        self._add_bar = QWidget()
        self._add_bar.setObjectName("addBar")
        self._add_bar.setStyleSheet("#addBar { background: transparent; }")
        self._add_bar.setVisible(False)
        add_bar_layout = QHBoxLayout(self._add_bar)
        add_bar_layout.setContentsMargins(0, 8, 0, 0)
        add_bar_layout.setSpacing(6)

        self._add_field = QLineEdit()
        self._add_field.setPlaceholderText("Nouveau souhait (ex: 'Pink Floyd')…")
        self._add_field.setStyleSheet(
            "QLineEdit {"
            f"  background: {COLORS['BG_INPUT']}; color: {COLORS['TEXT_PRIMARY']};"
            f"  border: 1px solid COLORS['ACCENT']; border-radius: 10px;"
            "  padding: 8px 14px; font-size: 13px;"
            "}"
        )
        self._add_field.returnPressed.connect(self._on_add_confirm)
        add_bar_layout.addWidget(self._add_field, 1)

        self._add_confirm_btn = QPushButton("Ajouter")
        self._add_confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_confirm_btn.setStyleSheet(
            "QPushButton {"
            f"  background: COLORS['ACCENT']; color: {COLORS['TEXT_WHITE']};"
            "  border: none; border-radius: 10px;"
            "  padding: 8px 16px; font-size: 13px; font-weight: 600;"
            "}"
            f"QPushButton:hover {{ background: {COLORS['ACCENT_HOVER']}; }}"
        )
        self._add_confirm_btn.clicked.connect(self._on_add_confirm)
        add_bar_layout.addWidget(self._add_confirm_btn)

        self._add_cancel_btn = QPushButton("Annuler")
        self._add_cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_cancel_btn.setStyleSheet(
            "QPushButton {"
            f"  background: transparent; color: {COLORS['TEXT_SECONDARY']};"
            f"  border: 1px solid {COLORS['TEXT_PLACEHOLDER']}; border-radius: 10px;"
            "  padding: 8px 12px; font-size: 13px;"
            "}"
            f"QPushButton:hover {{ background: {COLORS['BG_HOVER']}; color: {COLORS['TEXT_TERTIARY']}; }}"
        )
        self._add_cancel_btn.clicked.connect(self._on_add_cancel)
        add_bar_layout.addWidget(self._add_cancel_btn)

        layout.addWidget(self._add_bar, 0)

        # ── Chargement initial des données ──
        self.refresh()

    # ── Gestion des données ──────────────────────────────────

    def refresh(self) -> None:
        """Recharge la liste des souhaits et rafraîchit l'affichage."""
        self._wishlist = self._load_wishlist()
        self._rebuild()

    def _load_wishlist(self) -> list[dict]:
        """Charge les souhaits depuis ``app_config``.

        Lit la clé ``recherche.souhaits`` (CSV) et fusionne avec
        les métadonnées locales (résultats, dernière recherche, statut).
        """
        raw = app_config.get(_CONFIG_KEY_WISHLIST, "")

        # Essayer JSON d'abord, puis CSV (backward compat)
        if raw.strip().startswith("["):
            try:
                entries: list[dict] = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                entries = []
        else:
            # Fallback CSV : "query1, query2"
            entries = [{"query": q.strip(), "enabled": True} for q in raw.split(",") if q.strip()]

        queries = [e["query"] for e in entries]

        # Nettoyer les métadonnées périmées (requêtes supprimées)
        stale = [q for q in self._local_metadata if q not in queries]
        for q in stale:
            self._local_metadata.pop(q, None)

        result: list[dict] = []
        for entry in entries:
            query = entry["query"]
            enabled = entry.get("enabled", True)
            meta = self._local_metadata.get(query, {})
            result.append(
                {
                    "query": query,
                    "enabled": enabled,
                    "results": meta.get("results", 0),
                    "last_search": meta.get("last_search", "jamais"),
                    "status": meta.get("status", "active" if enabled else "inactive"),
                }
            )
        return result

    def _save_wishlist(self) -> None:
        """Persiste la liste des souhaits dans ``app_config``.

        Sauvegarde les noms de requêtes (CSV) + état enabled.
        Si le client Soulseek est connecté, synchronise aussi
        les souhaits dans ``client.settings.searches.wishlist``.
        """
        # Mettre à jour les métadonnées locales
        for w in self._wishlist:
            key = w["query"]
            if key not in self._local_metadata:
                self._local_metadata[key] = {}
            self._local_metadata[key].update(
                {
                    "enabled": w["enabled"],
                    "results": w.get("results", 0),
                    "last_search": w.get("last_search", "jamais"),
                    "status": w.get("status", "active" if w["enabled"] else "inactive"),
                }
            )

        # Persister dans app_config (JSON structuré : query + enabled)
        entries = [{"query": w["query"], "enabled": w["enabled"]} for w in self._wishlist]
        app_config.set(_CONFIG_KEY_WISHLIST, json.dumps(entries, ensure_ascii=False))

        # Synchroniser avec le client Soulseek s'il est connecté
        if soulseek_service.is_connected and soulseek_service.client is not None:
            try:
                from aioslsk.settings import WishlistSettingEntry

                soulseek_service.client.settings.searches.wishlist = [
                    WishlistSettingEntry(query=w["query"], enabled=w["enabled"]) for w in self._wishlist
                ]
            except Exception:
                pass  # Échec non bloquant

        self.wishlist_changed.emit()

    # ── Actions CRUD ─────────────────────────────────────────

    def add_wish(self, query: str) -> None:
        """Ajoute un nouveau souhait à la liste."""
        query = query.strip()
        if not query:
            return
        # Vérifier les doublons
        if any(w["query"].lower() == query.lower() for w in self._wishlist):
            return
        self._wishlist.append(
            {
                "query": query,
                "enabled": True,
                "results": 0,
                "last_search": "jamais",
                "status": "active",
            }
        )
        self._save_wishlist()
        self.refresh()

    def remove_wish(self, query: str) -> None:
        """Supprime un souhait de la liste."""
        self._wishlist = [w for w in self._wishlist if w["query"] != query]
        self._save_wishlist()
        self.refresh()
        EventBus().emit_event(
            severity="INFO",
            category="wishlist",
            title="Souhait supprimé",
            message=f"Souhait « {query} » retiré de la wishlist",
            source="BotWishlist",
        )

    def toggle_wish(self, query: str, enabled: bool) -> None:
        """Active ou désactive un souhait."""
        for w in self._wishlist:
            if w["query"] == query:
                w["enabled"] = enabled
                w["status"] = "active" if enabled else "inactive"
                break
        self._save_wishlist()
        self.refresh()

    def update_wish_query(self, old_query: str, new_query: str) -> None:
        """Modifie la requête d'un souhait."""
        new_query = new_query.strip()
        if not new_query:
            return
        for w in self._wishlist:
            if w["query"] == old_query:
                w["query"] = new_query
                break
        self._save_wishlist()
        self.refresh()

    def search_now(self, query: str) -> None:
        """Déclenche une recherche immédiate sur un souhait.

        Met à jour la date de dernière recherche et appelle
        ``ConnexionManager.search()`` si le client est connecté.
        """
        now_str = datetime.datetime.now().strftime("%H:%M")
        for w in self._wishlist:
            if w["query"] == query:
                w["last_search"] = f"à {now_str}"
                w["results"] = max(1, w.get("results", 0))
                w["status"] = "active"
                break
        self._save_wishlist()
        self.refresh()
        EventBus().emit_event(
            severity="INFO",
            category="wishlist",
            title="Recherche wishlist",
            message=f"Recherche lancée pour « {query} »",
            source="BotWishlist",
        )

        # TODO: Déclencher une vraie recherche via ConnexionManager
        # if soulseek_service.is_connected:
        #     soulseek_service.client.searches.search(query)

    # ── Construction de l'UI ─────────────────────────────────

    def _rebuild(self) -> None:
        """Reconstruit toute l'interface à partir de self._wishlist."""
        self._build_stats()
        self._build_list()

    def _build_stats(self) -> None:
        """Met à jour les cartes de statistiques."""
        # Vider les stats existantes
        while self._stats_layout.count():
            item = self._stats_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total = len(self._wishlist)
        active = sum(1 for w in self._wishlist if w.get("status") == "active")
        inactive = sum(1 for w in self._wishlist if w.get("status") == "inactive")
        errors = sum(1 for w in self._wishlist if w.get("status") == "error")

        self._stats_layout.addWidget(_StatCard(total, "Total", COLORS["ACCENT"]))
        self._stats_layout.addWidget(_StatCard(active, "Actifs", _STYLE_STATUS_ACTIVE))
        self._stats_layout.addWidget(_StatCard(inactive, "Inactifs", _STYLE_STATUS_INACTIVE))
        self._stats_layout.addWidget(_StatCard(errors, "Erreurs", _STYLE_STATUS_ERROR))
        self._stats_layout.addStretch(1)

    def _build_list(self) -> None:
        """Reconstruit la liste des cartes de souhaits."""
        # Vider la liste (sauf le stretch)
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Filtrer
        filtered = self._get_filtered_wishlist()

        if not filtered:
            empty_lbl = QLabel("Aucun souhait trouvé.\nClique sur « ➕ Ajouter un souhait » pour en créer un.")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet(
                f"color: {COLORS['TEXT_MUTED']}; font-size: 13px; padding: 40px; background: transparent;"
            )
            self._list_layout.insertWidget(0, empty_lbl)
            return

        for data in filtered:
            card = WishlistCard(data)
            card.toggled.connect(self._on_card_toggled)
            card.edit_requested.connect(self._on_card_edit)
            card.delete_requested.connect(self._on_card_delete)
            card.search_now_requested.connect(self._on_card_search)
            self._list_layout.insertWidget(self._list_layout.count() - 1, card)

    def _get_filtered_wishlist(self) -> list[dict]:
        """Retourne la liste filtrée selon le filtre actif et la recherche."""
        result = list(self._wishlist)

        # Filtre par statut
        if self._filter == "active":
            result = [w for w in result if w.get("status") == "active"]
        elif self._filter == "inactive":
            result = [w for w in result if w.get("status") == "inactive"]
        elif self._filter == "error":
            result = [w for w in result if w.get("status") == "error"]

        # Filtre textuel
        if self._search_text:
            text = self._search_text.lower()
            result = [w for w in result if text in w["query"].lower()]

        return result

    # ── Handlers UI ──────────────────────────────────────────

    def _apply_filter(self, filter_id: str) -> None:
        """Applique un filtre et met à jour l'état des boutons."""
        self._filter = filter_id
        for fid, btn in self._filter_buttons.items():
            btn.setChecked(fid == filter_id)
        self._build_list()

    def _on_search(self, text: str) -> None:
        """Handler quand l'utilisateur tape dans le champ de recherche."""
        self._search_text = text
        self._build_list()

    def _on_add_click(self) -> None:
        """Affiche la barre d'ajout rapide."""
        self._add_bar.setVisible(True)
        self._add_field.setFocus()
        self._add_field.clear()

    def _on_add_confirm(self) -> None:
        """Confirme l'ajout ou la modification d'un souhait.

        Si ``_edit_mode`` est True, on applique une modification
        au lieu d'un ajout. Évite la fragilité de la reconnexion
        de signaux.
        """
        query = self._add_field.text().strip()
        if not query:
            return
        if self._edit_mode:
            if query != self._edit_old_query:
                self.update_wish_query(self._edit_old_query, query)
            self._edit_mode = False
            self._edit_old_query = ""
        else:
            self.add_wish(query)
        self._add_field.clear()
        self._add_bar.setVisible(False)

    def _on_add_cancel(self) -> None:
        """Annule l'ajout ou la modification en cours.

        Réinitialise le mode édition et masque la barre d'ajout.
        """
        self._edit_mode = False
        self._edit_old_query = ""
        self._add_field.clear()
        self._add_bar.setVisible(False)

    def _on_toggle_all(self) -> None:
        """Bascule tous les souhaits (actif → inactif ou inactif → actif)."""
        active_count = sum(1 for w in self._wishlist if w.get("status") == "active")
        target_status = "inactive" if active_count > len(self._wishlist) / 2 else "active"
        for w in self._wishlist:
            w["enabled"] = target_status == "active"
            w["status"] = target_status
        self._save_wishlist()
        self.refresh()

    # ── Handlers des cartes ──────────────────────────────────

    def _on_card_toggled(self, query: str, enabled: bool) -> None:
        """Handler quand une carte est activée/désactivée."""
        self.toggle_wish(query, enabled)

    def _on_card_edit(self, query: str) -> None:
        """Handler quand l'utilisateur clique sur Modifier.

        Ouvre la barre d'ajout en mode édition.
        Le flag ``_edit_mode`` permet à ``_on_add_confirm``
        de distinguer ajout et modification sans reconnexion
        de signaux.
        """
        self._edit_mode = True
        self._edit_old_query = query
        self._add_bar.setVisible(True)
        self._add_field.setText(query)
        self._add_field.setFocus()
        self._add_field.selectAll()

    def _on_card_delete(self, query: str) -> None:
        """Handler quand l'utilisateur clique sur Supprimer.

        Affiche une confirmation ``QMessageBox`` avant suppression.
        """
        reply = QMessageBox.question(
            self,
            "Confirmer la suppression",
            f"Supprimer le souhait « {query} » ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.remove_wish(query)

    def _on_card_search(self, query: str) -> None:
        """Handler quand l'utilisateur clique sur Chercher."""
        self.search_now(query)
