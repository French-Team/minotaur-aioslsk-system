"""
Feuille de style globale (QSS) pour l'interface aioslsk.
"""

DARK_THEME = """
/* ---- Fenêtre principale ---- */
QMainWindow {
    background-color: #0f0f13;
}

/* ---- Zones du layout ---- */
#headerZone {
    border: 1px solid #3a3a4a;
    background-color: #1c1c26;
}
#leftZone {
    border: 1px solid #3a3a4a;
    background-color: #16161e;
}
#centerZone {
    border: 1px solid #3a3a4a;
    background-color: #111118;
}
#rightZone {
    border: 1px solid #3a3a4a;
    background-color: #16161e;
}
#footerZone {
    border: 1px solid #3a3a4a;
    background-color: #1c1c26;
}

/* ---- Grilles / containers ---- */
QWidget {
    color: #e4e4ec;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

/* ---- Labels ---- */
QLabel {
    color: #e4e4ec;
    background-color: transparent;
}

/* ---- Boutons ---- */
QPushButton {
    background-color: #6c5ce7;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #7d6ef0;
}
QPushButton:pressed {
    background-color: #5a4bd1;
}
QPushButton:disabled {
    background-color: #3a3a4a;
    color: #6a6a7a;
}

/* ---- Liste (sidebar) ---- */
QListWidget {
    background-color: #1a1a22;
    border: none;
    border-right: 1px solid #2e2e3a;
    outline: none;
    padding: 8px;
}
QListWidget::item {
    color: #8a8a9a;
    padding: 10px 14px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
}
QListWidget::item:selected {
    background-color: #24242e;
    color: #6c5ce7;
}
QListWidget::item:hover:!selected {
    background-color: #24242e;
    color: #e4e4ec;
}

/* ---- Barre de menu ---- */
QMenuBar {
    background-color: #1a1a22;
    border-bottom: 1px solid #2e2e3a;
    color: #8a8a9a;
    font-size: 13px;
    padding: 2px;
}
QMenuBar::item:selected {
    background-color: #24242e;
    color: #e4e4ec;
}
QMenu {
    background-color: #1a1a22;
    border: 1px solid #2e2e3a;
    color: #e4e4ec;
}
QMenu::item:selected {
    background-color: #6c5ce7;
}

/* ---- Barre de statut ---- */
QStatusBar {
    background-color: #1a1a22;
    border-top: 1px solid #2e2e3a;
    color: #5a5a6a;
    font-size: 11px;
    padding: 4px 12px;
}
QStatusBar::item {
    border: none;
}

/* ---- Sections retractables (collapsible) ---- */
#collapsibleHeader {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    text-align: left;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 600;
    color: #8a8a9a;
}
#collapsibleHeader:hover {
    background-color: #24242e;
    color: #e4e4ec;
}
#collapsibleHeader:pressed {
    background-color: #1e1e28;
}
#collapsibleContent {
    background-color: transparent;
    border: none;
}

/* ---- Handle de repli (panneau droit) ---- */
#rightHandle {
    background-color: #1a1a22;
    border: none;
    border-right: 1px solid #2e2e3a;
    border-radius: 0;
    min-height: 0;
}
#rightHandle:hover {
    background-color: #24242e;
}
#rightHandle:hover #handleArrow {
    color: #6c5ce7;
}

/* ---- Handle de repli (panneau gauche) ---- *//* ---- Handle de repli (panneau gauche) ---- */
#leftHandle {
    background-color: #1a1a22;
    border: none;
    border-left: 1px solid #2e2e3a;
    border-radius: 0;
    min-height: 0;
}
#leftHandle:hover {
    background-color: #24242e;
}
#handleArrow {
    color: #5a5a6a;
    font-size: 10px;
    background-color: transparent;
    border: none;
    padding: 0;
}
#leftHandle:hover #handleArrow {
    color: #6c5ce7;
}

/* ---- Boutons de navigation (footer) ---- */
#footerNavButton {
    background-color: transparent;
    color: #5a5a6a;
    border: 1px solid #2e2e3a;
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 500;
}
#footerNavButton:hover {
    background-color: #24242e;
    color: #e4e4ec;
    border-color: #3a3a4a;
}
#footerNavButton:checked {
    background-color: #24242e;
    color: #6c5ce7;
    border-color: #6c5ce7;
    font-weight: 600;
}

/* ---- Boutons de navigation (panneau gauche) ---- *//* ---- Boutons de navigation (panneau gauche) ---- */
#navButton {
    background-color: transparent;
    color: #8a8a9a;
    border: none;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 500;
    text-align: left;
}
#navButton:hover {
    background-color: #24242e;
    color: #e4e4ec;
}
#navButton:checked {
    background-color: #24242e;
    color: #6c5ce7;
    font-weight: 600;
}

/* ---- Content stack (zone centrale) ---- */
#centerStack {
    border: none;
    background-color: transparent;
}

/* ---- Connexion header ---- */
#connexionHeader {
    background-color: #1a1a22;
    border: 1px solid #2e2e3a;
    border-radius: 6px;
    min-height: 40px;
}
#connexionHeader:hover {
    background-color: #24242e;
    border-color: #6c5ce7;
}

/* ---- Page de connexion ---- */
#connexionCard {
    background-color: #16161e;
    border: 1px solid #2e2e3a;
    border-radius: 10px;
}
#connexionInput {
    background-color: #1a1a22;
    color: #e4e4ec;
    border: 1px solid #2e2e3a;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 500;
}
#connexionInput:focus {
    border-color: #6c5ce7;
}
#connexionInput::placeholder {
    color: #5a5a6a;
}
#connexionBtn {
    background-color: #6c5ce7;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 10px;
    font-size: 13px;
    font-weight: 700;
    min-height: 20px;
}
#connexionBtn:hover {
    background-color: #7d6ef0;
}
#connexionBtn:pressed {
    background-color: #5a4bd1;
}
#connexionBtnSecondary {
    background-color: transparent;
    color: #6c5ce7;
    border: 1px solid #6c5ce7;
    border-radius: 6px;
    padding: 10px;
    font-size: 13px;
    font-weight: 600;
    min-height: 20px;
}
#connexionBtnSecondary:hover {
    background-color: #24242e;
}
#connexionBtnSecondary:pressed {
    background-color: #1e1e28;
}

/* ---- Progression (multi-mode) ---- */
#progressionWidget {
    background-color: #0a0a0f;
    border: 1px solid #2e2e3a;
    border-radius: 6px;
    min-height: 40px;
}
#progressionMode {
    color: #8a8a9a;
    font-size: 10px;
    font-weight: 600;
    background-color: transparent;
    border: none;
    padding: 0;
}
#progressionValue {
    color: #e4e4ec;
    font-size: 15px;
    font-weight: 700;
    background-color: transparent;
    border: none;
    padding: 0;
}
#progressionBar {
    background-color: #1a1a22;
    border: 1px solid #2e2e3a;
    border-radius: 4px;
    min-height: 8px;
    max-height: 8px;
    text-align: center;
}
#progressionBar::chunk {
    background-color: #6c5ce7;
    border-radius: 3px;
}

/* ---- Clients actifs (header + page) ---- */
#clientsHeader {
    background-color: #0a0a0f;
    border: 1px solid #2e2e3a;
    border-radius: 6px;
    min-height: 40px;
}
#clientsHeader:hover {
    border: 1px solid #6c5ce7;
}
#clientsHeaderTitle {
    color: #6c5ce7;
    font-size: 11px;
    font-weight: 600;
}
#clientsHeaderStatut {
    color: #e4e4ec;
    font-size: 13px;
    font-weight: 500;
}
#clientsActifsPage {
    background-color: transparent;
}
#clientRow {
    background-color: #14141e;
    border: 1px solid #2e2e3a;
    border-radius: 6px;
}
#clientRow:hover {
    background-color: #1a1a28;
    border: 1px solid #4a4a5a;
}
#clientsActionBtn {
    background-color: #2e2e3a;
    color: #b0b0c0;
    border: 1px solid #3a3a4a;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 500;
}
#clientsActionBtn:hover {
    background-color: #3a3a4a;
    color: #e4e4ec;
    border: 1px solid #6c5ce7;
}
#clientsActionBtn:pressed {
    background-color: #4a4a5a;
}
#clientsActionBtnDanger {
    background-color: #2e2e3a;
    color: #ff5252;
    border: 1px solid #3a3a4a;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 500;
}
#clientsActionBtnDanger:hover {
    background-color: #ff5252;
    color: #ffffff;
    border: 1px solid #ff5252;
}
#clientsActionBtnDanger:pressed {
    background-color: #d32f2f;
}
#clientsScroll {
    background-color: transparent;
    border: none;
}
#clientsListContainer {
    background-color: transparent;
}

/* ---- Téléchargements (header + page) ---- */
#telechargementsHeader {
    background-color: #0a0a0f;
    border: 1px solid #2e2e3a;
    border-radius: 6px;
    min-height: 40px;
}
#telechargementsHeader:hover {
    border: 1px solid #6c5ce7;
}
#telechargementsHeaderTitle {
    color: #6c5ce7;
    font-size: 11px;
    font-weight: 600;
}
#telechargementsHeaderStatut {
    color: #e4e4ec;
    font-size: 13px;
    font-weight: 500;
}
#telechargementsPage {
    background-color: transparent;
}
#downloadRow {
    background-color: #14141e;
    border: 1px solid #2e2e3a;
    border-radius: 6px;
}
#downloadRow:hover {
    background-color: #1a1a28;
    border: 1px solid #4a4a5a;
}
#downloadFileName {
    color: #e4e4ec;
    font-size: 13px;
    font-weight: 500;
}
#downloadProgress {
    background-color: #1a1a22;
    border: 1px solid #2e2e3a;
    border-radius: 4px;
    min-height: 14px;
    max-height: 14px;
    text-align: center;
    font-size: 10px;
}
#downloadBtnCancel {
    background-color: #2e2e3a;
    color: #ff5252;
    border: 1px solid #3a3a4a;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 500;
}
#downloadBtnCancel:hover {
    background-color: #ff5252;
    color: #ffffff;
    border: 1px solid #ff5252;
}
#downloadBtnRetry {
    background-color: #2e2e3a;
    color: #ffab00;
    border: 1px solid #3a3a4a;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 500;
}
#downloadBtnRetry:hover {
    background-color: #ffab00;
    color: #1a1a1a;
    border: 1px solid #ffab00;
}
#downloadScroll {
    background-color: transparent;
    border: none;
}
#downloadListContainer {
    background-color: transparent;
}
#downloadToolbar {
    background-color: #14141e;
    border: 1px solid #2e2e3a;
    border-radius: 6px;
    padding: 6px;
}
#toolbarBtn {
    background-color: #2e2e3a;
    color: #b0b0c0;
    border: 1px solid #3a3a4a;
    border-radius: 4px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
}
#toolbarBtn:hover {
    background-color: #3a3a4a;
    color: #e4e4ec;
    border: 1px solid #6c5ce7;
}
#toolbarBtn:pressed {
    background-color: #4a4a5a;
}
#toolbarBtnDanger {
    background-color: #2e2e3a;
    color: #ff5252;
    border: 1px solid #3a3a4a;
    border-radius: 4px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
}
#toolbarBtnDanger:hover {
    background-color: #ff5252;
    color: #ffffff;
    border: 1px solid #ff5252;
}

/* ---- Horloge digitale ---- */
#clockWidget {
    background-color: #0a0a0f;
    border: 1px solid #2e2e3a;
    border-radius: 6px;
    padding: 4px;
}
#clockLabel {
    color: #00e676;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 18px;
    font-weight: 700;
    background-color: transparent;
    border: none;
    padding: 2px 8px;
}

/* ---- Tabs (rooms) ---- */
/* ---- Tabs (rooms) ---- */
#roomsTabs::pane {
    background-color: #1a1a22;
    border: 1px solid #6c5ce7;
    border-radius: 0 0 6px 6px;
}
#roomsTabs QTabBar::tab {
    background-color: #1a1a22;
    color: #5a5a6a;
    border: 1px solid #2e2e3a;
    border-bottom: none;
    border-radius: 0;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 600;
    margin-right: 2px;
}
#roomsTabs QTabBar::tab:selected {
    background-color: #1a1a22;
    color: #6c5ce7;
    border-color: #6c5ce7;
}
#roomsTabs QTabBar::tab:hover:!selected {
    background-color: #24242e;
    color: #e4e4ec;
}
"""
