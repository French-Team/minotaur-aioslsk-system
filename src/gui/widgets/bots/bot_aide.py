"""
Bot Aide — assistant mémoire & documentation interactive.

Page dédiée du bot Aide : affiche les articles d'aide (importés depuis
``data/aide_knowledge/``), gère l'historique des consultations, écoute
les requêtes via EventBus, et permet la recherche en direct.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

from src.utils.log_action import log_action

from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from src.gui.theme_fragments.colors import COLORS
from src.services.aide_db import AideDB
from src.services.event_bus import EventBus, SurveillanceEvent

logger = logging.getLogger("[AIDE]")

# ── Délai de debounce pour la recherche ───────────────────────────────
_SEARCH_DEBOUNCE_MS = 300
_HISTORY_LIMIT = 50


# ── Constantes de style ───────────────────────────────────────────────

_HISTORY_ITEM_STYLE = """
    QListWidget::item {
        padding: 8px 12px;
        border-bottom: 1px solid %s;
        font-size: 12px;
    }
    QListWidget::item:hover {
        background: %s;
    }
    QListWidget::item:selected {
        background: %s;
        color: %s;
    }
""" % (
    COLORS["BORDER_CONFIG"],
    COLORS["BG_HOVER"],
    COLORS["ACCENT"],
    COLORS["TEXT_PRIMARY"],
)

_SEARCH_STYLE = """
    QLineEdit {
        padding: 8px 12px;
        border: 1px solid %s;
        border-radius: 6px;
        background: %s;
        color: %s;
        font-size: 13px;
    }
    QLineEdit:focus {
        border-color: %s;
    }
    QLineEdit::placeholder {
        color: %s;
    }
""" % (
    COLORS["BORDER_CONFIG"],
    COLORS["BG_INPUT"],
    COLORS["TEXT_PRIMARY"],
    COLORS["ACCENT"],
    COLORS["TEXT_PLACEHOLDER"],
)

_VIEWER_STYLE = """
    QTextBrowser {
        background: %s;
        border: 1px solid %s;
        border-radius: 6px;
        padding: 16px;
        color: %s;
        font-size: 13px;
        line-height: 1.6;
    }
""" % (
    COLORS["BG_HOVER"],
    COLORS["BORDER_CONFIG"],
    COLORS["TEXT_PRIMARY"],
)

_TOGGLE_BTN_STYLE = """
    QPushButton {
        background: transparent;
        border: 1px solid %s;
        border-radius: 4px;
        padding: 6px 10px;
        color: %s;
        font-size: 13px;
    }
    QPushButton:hover {
        background: %s;
    }
""" % (
    COLORS["BORDER_CONFIG"],
    COLORS["TEXT_SECONDARY"],
    COLORS["BG_HOVER"],
)

# ── Style des boutons de filtre par catégorie ───────────────────────
_CAT_FILTER_STYLE = """
    QPushButton {
        padding: 4px 12px;
        border: 1px solid %s;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        background: transparent;
        color: %s;
    }
    QPushButton:hover {
        background: %s;
    }
    QPushButton:checked {
        color: #ffffff;
        border-color: transparent;
    }
""" % (
    COLORS["BORDER_CONFIG"],
    COLORS["TEXT_SECONDARY"],
    COLORS["BG_HOVER"],
)

# ── Labels et couleurs des catégories ──────────────────────────────
_CATEGORY_LABELS: dict[str, str] = {
    "faq": "FAQ",
    "guide_bots": "Guides",
    "tutoriels": "Tutoriels",
    "technique": "Technique",
    "interface": "Interface",
}

_CATEGORY_COLORS: dict[str, str] = {
    "faq": "#e67e22",
    "guide_bots": "#2ecc71",
    "tutoriels": "#3498db",
    "technique": "#9b59b6",
    "interface": "#1abc9c",
}

_CATEGORY_ICONS: dict[str, str] = {
    "faq": "❓",
    "guide_bots": "📘",
    "tutoriels": "📗",
    "technique": "🔧",
    "interface": "🖥️",
}


class BotAide(QFrame):
    """Page du bot Aide — consultation et recherche d'articles.

    Signaux
    -------
    page_changed : Signal(str)
        Émis pour naviguer vers une autre page (ex: ``"Accueil"``).
    """

    page_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("botAide")

        # Base de données
        self._db: AideDB = AideDB()
        self._db.init_database()

        # État interne
        self._current_article: dict[str, Any] | None = None
        self._sidebar_visible: bool = True
        self._history_entries: list[dict[str, Any]] = []
        self._active_category: str | None = None
        self._category_buttons: dict[str, QPushButton] = {}

        # Timer de debounce pour la recherche
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._on_search_debounce)

        # Construction de l'interface
        self._build_ui()

        # Chargement de l'historique
        self._load_history()

        # L'EventBus sera connecté via setup() depuis CenterZone

        logger.info("BotAide initialisé — %d articles en base", self._db.count_articles())

    # ── Abonnement EventBus ────────────────────────────────────────────

    def setup(self, event_bus: EventBus) -> None:
        """Connecte le bot Aide à l'EventBus (appelé depuis CenterZone)."""
        event_bus.event_emitted.connect(self._on_event)

    # ── Interface utilisateur ─────────────────────────────────────────

    def _build_ui(self) -> None:
        """Construit l'interface complète du bot Aide."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── Barre supérieure : titre + recherche ────────────────────────
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        # Titre
        title_lbl = QLabel("Aide & Documentation")
        title_lbl.setStyleSheet(
            f"color: {COLORS['ACCENT']};"
            "font-size: 18px; font-weight: 700;"
        )
        top_bar.addWidget(title_lbl)

        top_bar.addStretch(1)

        # Barre de recherche
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("🔍  Chercher une réponse...")
        self._search_input.setStyleSheet(_SEARCH_STYLE)
        self._search_input.setMinimumWidth(280)
        self._search_input.textChanged.connect(self._on_search_text_changed)
        self._search_input.returnPressed.connect(self._on_search_debounce)
        top_bar.addWidget(self._search_input)

        # Bouton toggle sidebar
        self._toggle_btn = QPushButton("☰")
        self._toggle_btn.setToolTip("Afficher / masquer l'historique")
        self._toggle_btn.setStyleSheet(_TOGGLE_BTN_STYLE)
        self._toggle_btn.setFixedWidth(36)
        self._toggle_btn.clicked.connect(self._toggle_sidebar)
        top_bar.addWidget(self._toggle_btn)

        layout.addLayout(top_bar)

        # ── Splitter : viewer + sidebar ────────────────────────────────
        # pyrefly: ignore [missing-attribute]
        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.setHandleWidth(1)

        # Viewer (QTextBrowser) — affichage de l'article
        self._viewer = QTextBrowser()
        self._viewer.setStyleSheet(_VIEWER_STYLE)
        self._viewer.setOpenExternalLinks(True)
        self._viewer.setOpenLinks(True)
        self._splitter.addWidget(self._viewer)

        # Sidebar — historique des consultations
        self._sidebar_widget = QFrame()
        self._sidebar_widget.setObjectName("sidebarAide")
        self._sidebar_widget.setStyleSheet(
            f"#sidebarAide {{ background: {COLORS['BG_INPUT']};"
            f"border: 1px solid {COLORS['BORDER_CONFIG']};"
            "border-radius: 6px; }"
        )
        sidebar_layout = QVBoxLayout(self._sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # En-tête sidebar
        self._sidebar_header = QLabel("  📋 Demandes récentes")
        self._sidebar_header.setStyleSheet(
            f"color: {COLORS['TEXT_SECONDARY']};"
            "font-size: 12px; font-weight: 600;"
            f"padding: 10px; border-bottom: 1px solid {COLORS['BORDER_CONFIG']};"
        )
        sidebar_layout.addWidget(self._sidebar_header)

        # ── Filtres par catégorie ────────────────────────────────────
        self._build_category_filters(sidebar_layout)

        # Liste d'historique
        self._history_list = QListWidget()
        self._history_list.setStyleSheet(_HISTORY_ITEM_STYLE)
        # pyrefly: ignore [missing-attribute]
        self._history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._history_list.customContextMenuRequested.connect(self._on_history_context_menu)
        self._history_list.itemClicked.connect(self._on_history_item_clicked)
        sidebar_layout.addWidget(self._history_list, 1)

        # Initialement, sidebar visible
        self._sidebar_widget.setMinimumWidth(200)
        self._sidebar_widget.setMaximumWidth(320)
        self._splitter.addWidget(self._sidebar_widget)

        # Proportions : 70% viewer / 30% sidebar
        self._splitter.setSizes([600, 250])

        layout.addWidget(self._splitter, 1)

        # ── Message d'accueil initial ───────────────────────────────────
        self._show_welcome()

    # ── Affichage ──────────────────────────────────────────────────────

    def _show_welcome(self) -> None:
        """Affiche le message de bienvenue dans le viewer."""
        welcome_html = """
        <div style="text-align: center; padding: 40px 20px;">
            <div style="font-size: 48px; margin-bottom: 16px;">📖</div>
            <h2 style="color: %s; margin-bottom: 8px;">Bienvenue dans l'Aide</h2>
            <p style="color: %s; font-size: 14px; line-height: 1.6; max-width: 500px; margin: 0 auto;">
                Pose une question dans la barre de recherche ci-dessus pour trouver
                un article, ou clique sur une entrée dans l'historique.
            </p>
            <p style="color: %s; font-size: 13px; margin-top: 24px;">
                <b>Astuce :</b> Tu peux aussi poser ta question au
                <a href="#" style="color: %s;">bot Accueil</a>
                — il te redirigera automatiquement vers l'article pertinent.
            </p>
        </div>
        """ % (
            COLORS["ACCENT"],
            COLORS["TEXT_SECONDARY"],
            COLORS["TEXT_PLACEHOLDER"],
            COLORS["ACCENT"],
        )
        self._viewer.setHtml(welcome_html)
        self._current_article = None

    def _display_article(self, article: dict[str, Any], question: str | None = None) -> None:
        """Affiche un article dans le viewer et enregistre dans l'historique.

        Paramètres
        ----------
        article : dict
            Article avec les clés ``title``, ``content``, ``category``, ``keywords``.
        question : str, optional
            Question posée par l'utilisateur (pour l'historique).
        """
        self._current_article = article
        html = self._render_content(article)
        self._viewer.setHtml(html)

        # Enregistrer dans l'historique
        if question:
            self._db.add_history(article.get("id", 0), question)
            self._load_history()
            self._ensure_sidebar_visible()

    def _render_content(self, article: dict[str, Any]) -> str:
        """Convertit un article en HTML pour le QTextBrowser."""
        title = article.get("title", "Sans titre")
        content = article.get("content", "")
        category = article.get("category", "")
        keywords_raw = article.get("keywords", "[]")

        # Parser les mots-clés
        try:
            import json
            keywords = json.loads(keywords_raw) if isinstance(keywords_raw, str) else keywords_raw
        except (json.JSONDecodeError, TypeError):
            keywords = []

        # Badge catégorie (constantes partagées)
        cat_label = _CATEGORY_LABELS.get(category, category.capitalize())
        cat_color = _CATEGORY_COLORS.get(category, "#666")

        # Construction HTML
        html_parts = []

        # En-tête
        html_parts.append(f"""
        <div style="margin-bottom: 8px;">
            <span style="display: inline-block; background: {cat_color}; color: #fff;
                         padding: 2px 10px; border-radius: 4px; font-size: 11px;
                         font-weight: 600;">{cat_label}</span>
        </div>
        <h1 style="color: {COLORS['ACCENT']};
                   font-size: 22px; margin: 0 0 4px 0;">{title}</h1>
        """)

        if keywords:
            kw_badges = "".join(
                f'<span style="display: inline-block; background: {COLORS["BG_HOVER"]};'
                f'color: {COLORS["TEXT_SECONDARY"]}; padding: 1px 8px;'
                f'border-radius: 3px; font-size: 11px; margin: 2px 4px 2px 0;">🔖 {kw}</span>'
                for kw in keywords[:8]
            )
            html_parts.append(f'<div style="margin-bottom: 16px;">{kw_badges}</div>')

        # Contenu — conversion markdown léger vers HTML
        html_content = self._markdown_to_html(content)
        html_parts.append(
            f'<div style="line-height: 1.7; color: {COLORS["TEXT_PRIMARY"]};">'
            f'{html_content}</div>'
        )

        # Pied de page
        html_parts.append(
            f'<hr style="border: none; border-top: 1px solid {COLORS["BORDER_CONFIG"]};'
            f'margin: 24px 0 8px 0;">'
            f'<p style="font-size: 11px; color: {COLORS["TEXT_PLACEHOLDER"]};">'
            f'Catégorie : {category} — {self._db.count_articles()} articles disponibles</p>'
        )

        return "".join(html_parts)

    @staticmethod
    def _markdown_to_html(md: str) -> str:
        """Conversion minimaliste de Markdown vers HTML.

        Supporte : titres (h2-h4), gras, italique, listes, code inline,
        blocs de code, liens, séparateurs.
        """
        import re

        lines = md.split("\n")
        html_lines: list[str] = []
        in_code_block = False
        code_buffer: list[str] = []
        in_list = False

        for line in lines:
            # Code block
            if line.strip().startswith("```"):
                if in_code_block:
                    html_lines.append(
                        f'<pre style="background: {COLORS["BG_INPUT"]};'
                        f'padding: 12px; border-radius: 4px; overflow-x: auto;'
                        f'font-size: 12px;">'
                        + "\n".join(code_buffer)
                        + "</pre>"
                    )
                    code_buffer = []
                    in_code_block = False
                else:
                    in_code_block = True
                continue

            if in_code_block:
                code_buffer.append(line.replace("<", "&lt;").replace(">", "&gt;"))
                continue

            stripped = line.strip()

            # Ligne vide → séparation
            if not stripped:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append("<br>")
                continue

            # Séparateur
            if stripped in ("---", "***", "___"):
                html_lines.append(
                    f'<hr style="border: none; border-top: 1px solid '
                    f'{COLORS["BORDER_CONFIG"]}; margin: 16px 0;">'
                )
                continue

            # Titres
            if stripped.startswith("#### "):
                html_lines.append(f"<h4>{stripped[5:]}</h4>")
                continue
            if stripped.startswith("### "):
                html_lines.append(f"<h3>{stripped[4:]}</h3>")
                continue
            if stripped.startswith("## "):
                html_lines.append(f"<h2>{stripped[3:]}<br></h2>")
                continue

            # Listes
            if stripped.startswith("- ") or stripped.startswith("* "):
                if not in_list:
                    html_lines.append("<ul>")
                    in_list = True
                item_text = stripped[2:]
                item_text = BotAide._inline_markdown(item_text)
                html_lines.append(f"<li>{item_text}</li>")
                continue

            # Listes numérotées
            num_match = re.match(r"^\d+\.\s+(.*)", stripped)
            if num_match:
                if not in_list:
                    html_lines.append("<ol>")
                    in_list = True
                item_text = BotAide._inline_markdown(num_match.group(1))
                html_lines.append(f"<li>{item_text}</li>")
                continue

            # Paragraphe normal
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            processed = BotAide._inline_markdown(stripped)
            html_lines.append(f"<p>{processed}</p>")

        if in_code_block:
            html_lines.append(
                f'<pre style="background: {COLORS["BG_INPUT"]};'
                f'padding: 12px; border-radius: 4px; overflow-x: auto;'
                f'font-size: 12px;">'
                + "\n".join(code_buffer)
                + "</pre>"
            )
        if in_list:
            html_lines.append("</ul>")

        return "\n".join(html_lines)

    @staticmethod
    def _inline_markdown(text: str) -> str:
        """Applique le formatage inline (gras, italique, code, liens)."""
        import re

        # Échapper les caractères HTML sauf dans les balises qu'on génère
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")

        # Images ![alt](url)
        text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1" style="max-width:100%;">', text)

        # Liens [text](url)
        text = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            r'<a href="\2" style="color: %s;">\1</a>' % COLORS["ACCENT"],
            text,
        )

        # Code inline `code`
        text = re.sub(
            r"`([^`]+)`",
            r'<code style="background: %s; padding: 1px 4px; border-radius: 3px; '
            r'font-size: 12px;">\1</code>' % COLORS["BG_INPUT"],
            text,
        )

        # Gras **text**
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)

        # Italique *text* (mais pas ** déjà traité)
        text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)

        return text

    def _show_no_result(self, query: str) -> None:
        """Affiche un message 'aucun résultat' dans le viewer."""
        no_result_html = """
        <div style="text-align: center; padding: 60px 20px;">
            <div style="font-size: 48px; margin-bottom: 16px;">🔍</div>
            <h3 style="color: %s; margin-bottom: 8px;">Aucun résultat trouvé</h3>
            <p style="color: %s; font-size: 14px;">
                Ta recherche "<strong>%s</strong>" n'a donné aucun résultat.
            </p>
            <p style="color: %s; font-size: 13px; margin-top: 16px;">
                Suggestions :<br>
                • Utilise des termes plus généraux<br>
                • Vérifie l'orthographe<br>
                • Consulte l'<a href="#" style="color: %s;">Accueil</a>
                  pour une aide contextuelle
            </p>
        </div>
        """ % (
            COLORS["ACCENT"],
            COLORS["TEXT_SECONDARY"],
            query.replace("<", "&lt;").replace(">", "&gt;"),
            COLORS["TEXT_PLACEHOLDER"],
            COLORS["ACCENT"],
        )
        self._viewer.setHtml(no_result_html)
        self._current_article = None

    # ── Sidebar — Historique ──────────────────────────────────────────

    def _load_history(self) -> None:
        """Charge l'historique depuis la base et remplit la sidebar."""
        self._history_entries = self._db.get_history(limit=_HISTORY_LIMIT)
        self._history_list.clear()

        for entry in self._history_entries:
            title = entry.get("title", "?")
            question = entry.get("question", "")
            category = entry.get("category", "")

            # Icône par catégorie
            cat_icons = {
                "faq": "❓",
                "guide_bots": "📘",
                "tutoriels": "📗",
                "technique": "🔧",
                "interface": "🖥️",
            }
            icon = cat_icons.get(category, "📄")

            # Truncature de la question
            display = question if len(question) < 60 else question[:57] + "..."
            item_text = f"{icon} {title}"
            if display and display != title:
                item_text += f"\n{display}"

            item = QListWidgetItem(item_text)
            # pyrefly: ignore [missing-attribute]
            item.setData(Qt.UserRole, entry.get("id"))
            # pyrefly: ignore [missing-attribute]
            item.setData(Qt.UserRole + 1, entry.get("article_id"))
            item.setToolTip(f"{title}\n{question}")
            self._history_list.addItem(item)

    def _on_history_item_clicked(self, item: QListWidgetItem) -> None:
        """Charge l'article dans le viewer en fonction du type de clic."""
        # pyrefly: ignore [missing-attribute]
        item_type = item.data(Qt.UserRole + 1)
        # pyrefly: ignore [missing-attribute]
        data_id = item.data(Qt.UserRole)

        if data_id is None:
            return

        if item_type in ("search_result", "category_browse"):
            # Clic sur un résultat de recherche ou un article de catégorie
            article = self._db.get_article(data_id)
            if article:
                query = self._search_input.text().strip()
                self._display_article(article, query or article.get("title", ""))
            return

        # Clic sur un historique : UserRole = entry_id, UserRole+1 = article_id
        article_id = item_type
        entry_id = data_id
        article = self._db.get_article(article_id)
        if article:
            entry = next(
                (e for e in self._history_entries if e.get("id") == entry_id),
                None,
            )
            question = entry.get("question", "") if entry else ""
            self._display_article(article, question)

    def _on_history_context_menu(self, pos) -> None:
        """Menu contextuel (clic droit) sur un élément de l'historique."""
        item = self._history_list.itemAt(pos)
        if item is None:
            return

        # pyrefly: ignore [missing-attribute]
        entry_id = item.data(Qt.UserRole)
        # pyrefly: ignore [missing-attribute]
        article_id = item.data(Qt.UserRole + 1)

        menu = QMenu(self._history_list)
        menu.setStyleSheet(
            f"QMenu {{ background: {COLORS['BG_INPUT']};"
            f"border: 1px solid {COLORS['BORDER_CONFIG']};"
            f"color: {COLORS['TEXT_PRIMARY']}; padding: 4px; }}"
            f"QMenu::item {{ padding: 6px 24px; }}"
            f"QMenu::item:selected {{ background: {COLORS['BG_HOVER']}; }}"
        )

        action_copy_title = QAction("📋 Copier le titre", menu)
        action_copy_content = QAction("📄 Copier le contenu", menu)
        action_delete = QAction("🗑️ Supprimer", menu)

        menu.addAction(action_copy_title)
        menu.addAction(action_copy_content)
        menu.addSeparator()
        menu.addAction(action_delete)

        chosen = menu.exec(self._history_list.viewport().mapToGlobal(pos))

        if chosen == action_copy_title:
            article = self._db.get_article(article_id) if article_id else None
            if article:
                clipboard = QApplication.clipboard()
                clipboard.setText(article.get("title", ""))

        elif chosen == action_copy_content:
            article = self._db.get_article(article_id) if article_id else None
            if article:
                clipboard = QApplication.clipboard()
                clipboard.setText(article.get("content", ""))

        elif chosen == action_delete:
            if entry_id:
                self._db.delete_history_entry(entry_id)
                self._load_history()

    @log_action("Aide : afficher/masquer la sidebar")
    def _toggle_sidebar(self) -> None:
        """Affiche ou masque la sidebar."""
        self._sidebar_visible = not self._sidebar_visible
        self._sidebar_widget.setVisible(self._sidebar_visible)
        self._toggle_btn.setText("☰" if self._sidebar_visible else "☷")

    def _ensure_sidebar_visible(self) -> None:
        """S'assure que la sidebar est visible (après un nouvel historique)."""
        if not self._sidebar_visible:
            self._toggle_sidebar()

    # ── Sidebar — Filtres par catégorie ────────────────────────────

    def _build_category_filters(self, parent_layout: QVBoxLayout) -> None:
        """Ajoute les boutons de filtre par catégorie dans la sidebar avec compteurs d'articles."""
        filter_bar = QFrame()
        filter_bar.setObjectName("catFilterBar")
        filter_bar.setStyleSheet(
            f"#catFilterBar {{ padding: 6px 8px; }}"
        )
        filter_layout = QHBoxLayout(filter_bar)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(4)

        # Récupérer les compteurs depuis la base (1 seule requête GROUP BY)
        total_articles = self._db.count_articles()
        category_counts = self._db.get_article_counts()

        # Bouton "Tout" (réinitialise le filtre)
        btn_all = QPushButton(f"Tout ({total_articles})")
        btn_all.setCheckable(True)
        btn_all.setChecked(True)
        # pyrefly: ignore [missing-attribute]
        btn_all.setCursor(Qt.PointingHandCursor)
        btn_all.clicked.connect(lambda: self._on_category_clicked(None))
        filter_layout.addWidget(btn_all)
        self._category_buttons["__all__"] = btn_all

        # Un bouton par catégorie
        for cat_key in sorted(_CATEGORY_LABELS.keys()):
            label = _CATEGORY_LABELS[cat_key]
            count = category_counts.get(cat_key, 0)
            color = _CATEGORY_COLORS.get(cat_key, COLORS["ACCENT"])

            btn = QPushButton(f"{label} ({count})")
            btn.setCheckable(True)
            # pyrefly: ignore [missing-attribute]
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                _CAT_FILTER_STYLE
                + f"\nQPushButton:checked {{ background: {color}; }}"
            )
            btn.clicked.connect(lambda checked, c=cat_key: self._on_category_clicked(c))
            filter_layout.addWidget(btn)
            self._category_buttons[cat_key] = btn

        filter_layout.addStretch(1)
        parent_layout.addWidget(filter_bar)

    def _animate_sidebar_transition(self, callback: Callable[[], None]) -> None:
        """Anime la transition de contenu de la sidebar.

        Effet : fondu rapide (fade-out 80ms → callback → fade-in 100ms)
        avec une courbe d'easing cubique pour un rendu fluide.
        """
        effect = QGraphicsOpacityEffect(self._history_list)
        self._history_list.setGraphicsEffect(effect)

        # Fade out
        fade_out = QPropertyAnimation(effect, b"opacity")
        fade_out.setDuration(80)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Fade in
        fade_in = QPropertyAnimation(effect, b"opacity")
        fade_in.setDuration(100)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.InCubic)

        # Séquence : fade out → callback → fade in
        def _on_fade_out_finished() -> None:
            try:
                callback()
            finally:
                fade_in.start()

        def _on_fade_in_finished() -> None:
            # Nettoyer l'effet graphique après l'animation
            # pyrefly: ignore [bad-argument-type]
            self._history_list.setGraphicsEffect(None)

        fade_out.finished.connect(_on_fade_out_finished)
        fade_in.finished.connect(_on_fade_in_finished)
        fade_out.start()

    @log_action("Aide : filtre catégorie")
    def _on_category_clicked(self, category: str | None) -> None:
        """Gère le clic sur un bouton de filtre catégorie.

        Si la barre de recherche contient du texte (>= 2 caractères),
        la recherche est relancée dans la catégorie sélectionnée.
        Sinon, les articles de la catégorie sont affichés normalement.
        """
        # Éviter le rechargement si déjà actif
        if category == self._active_category:
            return

        # Mise à jour de l'état et des boutons (immédiat)
        self._active_category = category
        for key, btn in self._category_buttons.items():
            if key == "__all__":
                btn.setChecked(category is None)
            else:
                btn.setChecked(key == category)

        # Mise à jour de l'en-tête (immédiat)
        if category is None:
            self._sidebar_header.setText("  📋 Demandes récentes")
        else:
            icon = _CATEGORY_ICONS.get(category, "📁")
            label = _CATEGORY_LABELS.get(category, category.capitalize())
            self._sidebar_header.setText(f"  {icon} {label}")

        # Si une recherche est en cours (texte >= 2 car.), relancer dans la catégorie
        search_text = self._search_input.text().strip()
        if len(search_text) >= 2:
            self._search_timer.stop()
            self._on_search_debounce()
            return

        # Contenu de la liste avec animation de transition
        if category is None:
            self._animate_sidebar_transition(self._load_history)
        else:
            self._animate_sidebar_transition(
                lambda: self._load_category_articles(category)
            )

    def _load_category_articles(self, category: str) -> None:
        """Affiche les articles d'une catégorie dans la sidebar."""
        articles = self._db.get_all_articles(category=category)
        self._history_list.clear()

        for article in articles:
            title = article.get("title", "?")
            excerpt = article.get("excerpt", "")

            icon = _CATEGORY_ICONS.get(category, "📄")
            item_text = f"{icon} {title}"
            if excerpt:
                excerpt_short = excerpt[:80].replace("\n", " ") + ("..." if len(excerpt) > 80 else "")
                item_text += f"\n   {excerpt_short}"

            item = QListWidgetItem(item_text)
            # pyrefly: ignore [missing-attribute]
            item.setData(Qt.UserRole, article.get("id"))
            # pyrefly: ignore [missing-attribute]
            item.setData(Qt.UserRole + 1, "category_browse")
            self._history_list.addItem(item)

    # ── Barre de recherche ────────────────────────────────────────────

    def _on_search_text_changed(self) -> None:
        """Déclenche le timer de debounce à chaque frappe."""
        self._search_timer.start(_SEARCH_DEBOUNCE_MS)

    def _show_search_results(self, query: str, results: list[dict]) -> None:
        """Affiche les résultats de recherche dans la sidebar."""
        if self._active_category:
            icon = _CATEGORY_ICONS.get(self._active_category, "")
            label = _CATEGORY_LABELS.get(self._active_category, "")
            self._sidebar_header.setText(f"  🔍 {icon} {label} — "
                                         f'« {query} »')
        else:
            self._sidebar_header.setText(f"  🔍 Résultats pour « {query} »")
        self._history_list.clear()
        self._search_results: list[dict] = results

        cat_icons = {
            "faq": "❓", "guide_bots": "📘", "tutoriels": "📗",
            "technique": "🔧", "interface": "🖥️",
        }

        for article in results:
            title = article.get("title", "?")
            category = article.get("category", "")
            icon = cat_icons.get(category, "📄")
            excerpt = article.get("excerpt", "")

            item_text = f"{icon} {title}"
            if excerpt:
                excerpt_short = excerpt[:80].replace("\n", " ") + ("..." if len(excerpt) > 80 else "")
                item_text += f"\n   {excerpt_short}"

            item = QListWidgetItem(item_text)
            # pyrefly: ignore [missing-attribute]
            item.setData(Qt.UserRole, article.get("id"))
            # pyrefly: ignore [missing-attribute]
            item.setData(Qt.UserRole + 1, "search_result")
            self._history_list.addItem(item)

        self._ensure_sidebar_visible()

    def _on_search_debounce(self) -> None:
        """Exécute la recherche après le délai de debounce.

        Si une catégorie est active (``_active_category``), la recherche
        est filtrée sur cette catégorie — les résultats combinés sont
        affichés dans la sidebar.
        """
        query = self._search_input.text().strip()

        if len(query) < 2:
            if not self._current_article:
                self._show_welcome()
            # Revenir au mode catégorie ou historique
            if self._active_category is not None:
                self._load_category_articles(self._active_category)
                icon = _CATEGORY_ICONS.get(self._active_category, "📁")
                label = _CATEGORY_LABELS.get(self._active_category, "")
                self._sidebar_header.setText(f"  {icon} {label}")
            else:
                self._load_history()
                self._sidebar_header.setText("  📋 Demandes récentes")
            return

        # Chercher via AideDB (filtré par catégorie si active)
        results = self._db.search(query, category=self._active_category)
        if not results:
            self._show_no_result(query)
            if self._active_category:
                icon = _CATEGORY_ICONS.get(self._active_category, "")
                label = _CATEGORY_LABELS.get(self._active_category, "")
                self._sidebar_header.setText(f"  🔍 Aucun résultat dans {icon} {label} pour « {query} »")
            else:
                self._sidebar_header.setText(f"  🔍 Aucun résultat pour « {query} »")
            self._history_list.clear()
            return

        # Afficher les résultats dans la sidebar
        self._show_search_results(query, results)

        # Afficher le premier résultat dans le viewer
        best = self._db.get_article(results[0]["id"])
        if best:
            self._display_article(best, query)

    # ── EventBus ──────────────────────────────────────────────────────

    def _on_event(self, event: SurveillanceEvent) -> None:
        """Reçoit un événement EventBus de catégorie ``aide``.

        Le bot Accueil émet un événement avec :
        - ``title`` : titre exact de l'article (optionnel)
        - ``message`` : question posée par l'utilisateur
        """
        if event.category != "aide":
            return

        self._on_aide_request(event.title, event.message)

    def _on_aide_request(self, title: str, message: str) -> None:
        """Traite une requête d'aide reçue via EventBus."""
        # 1. Chercher par titre exact
        if title:
            article = self._db.find_by_title(title)
            if article:
                self._display_article(article, message or title)
                return

        # 2. Chercher par matching intelligent
        if message:
            article = self._db.find_best_match(message)
            if article:
                self._display_article(article, message)
                return

        # 3. Aucun résultat
        self._show_no_result(message or title or "Requête inconnue")
