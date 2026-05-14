"""
Feuille de style globale (QSS) pour l'interface aioslsk.
Toutes les couleurs sont centralisées dans COLORS pour faciliter la maintenance.
"""

# ── Palette de couleurs ──────────────────────────────────────────────────
# Les placeholders @KEY@ dans le CSS sont remplacés automatiquement.
COLORS = {
    "BG_BTN": "#2e2e3a",
    "BG_BTN_DISABLED": "#3a3a4a",
    "BG_BTN_PRESSED": "#4a4a5a",
    "BG_CENTER": "#111118",
    "BG_DARK": "#0a0a0f",
    "BG_HEADER": "#1c1c26",
    "BG_HOVER": "#24242e",
    "BG_MAIN": "#0f0f13",
    "BG_PRESSED": "#1e1e28",
    "BG_ROW_HOVER": "#1a1a28",
    "BG_SIDE": "#16161e",
    "BG_SURFACE": "#1a1a22",
    "BG_SURFACE2": "#14141e",
    "BORDER": "#2e2e3a",
    "BORDER_CONFIG": "#3a3a5a",
    "BORDER_HOVER": "#4a4a5a",
    "BORDER_LIGHT": "#3a3a4a",
    "DANGER": "#ff5252",
    "DANGER_BG_HOVER": "#2e1a1a",
    "DANGER_BG_PRESSED": "#1e1010",
    "DANGER_HOVER": "#ff7070",
    "DANGER_PRESSED": "#cc3333",
    "DANGER_PRESSED2": "#d32f2f",
    "PRIMARY": "#6c5ce7",
    "PRIMARY_HOVER": "#7d6ef0",
    "PRIMARY_HOVER2": "#7c6cf7",
    "PRIMARY_PRESSED": "#5a4bd1",
    "SUCCESS": "#00e676",
    "TEXT_DARK": "#1a1a1a",
    "TEXT_DISABLED": "#6a6a7a",
    "TEXT_MUTED": "#5a5a6a",
    "TEXT_PLACEHOLDER": "#3a3a4a",
    "TEXT_PRIMARY": "#e4e4ec",
    "TEXT_SECONDARY": "#8a8a9a",
    "TEXT_TERTIARY": "#b0b0c0",
    "TEXT_WHITE": "#ffffff",
    "WARNING": "#ffab00",
}

# ── Template CSS avec placeholders ─────────────────────────────────────────────────
_DARK_THEME_TEMPLATE = """
QMainWindow {
    background-color: @BG_MAIN@;
}

#headerZone {
    border: 1px solid @TEXT_PLACEHOLDER@;
    background-color: @BG_HEADER@;
}
#leftZone {
    border: 1px solid @TEXT_PLACEHOLDER@;
    background-color: @BG_SIDE@;
}
#centerZone {
    border: 1px solid @TEXT_PLACEHOLDER@;
    background-color: @BG_CENTER@;
}
#rightZone {
    border: 1px solid @TEXT_PLACEHOLDER@;
    background-color: @BG_SIDE@;
}
#footerZone {
    border: 1px solid @TEXT_PLACEHOLDER@;
    background-color: @BG_HEADER@;
}

QWidget {
    color: @TEXT_PRIMARY@;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

QLabel {
    color: @TEXT_PRIMARY@;
    background-color: transparent;
}

QPushButton {
    background-color: @PRIMARY@;
    color: @TEXT_WHITE@;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: @PRIMARY_HOVER@;
}
QPushButton:pressed {
    background-color: @PRIMARY_PRESSED@;
}
QPushButton:disabled {
    background-color: @TEXT_PLACEHOLDER@;
    color: @TEXT_DISABLED@;
}

QListWidget {
    background-color: @BG_SURFACE@;
    border: none;
    border-right: 1px solid @BG_BTN@;
    outline: none;
    padding: 8px;
}
QListWidget::item {
    color: @TEXT_SECONDARY@;
    padding: 10px 14px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
}
QListWidget::item:selected {
    background-color: @BG_HOVER@;
    color: @PRIMARY@;
}
QListWidget::item:hover:!selected {
    background-color: @BG_HOVER@;
    color: @TEXT_PRIMARY@;
}

QMenuBar {
    background-color: @BG_SURFACE@;
    border-bottom: 1px solid @BG_BTN@;
    color: @TEXT_SECONDARY@;
    font-size: 13px;
    padding: 2px;
}
QMenuBar::item:selected {
    background-color: @BG_HOVER@;
    color: @TEXT_PRIMARY@;
}
QMenu {
    background-color: @BG_SURFACE@;
    border: 1px solid @BG_BTN@;
    color: @TEXT_PRIMARY@;
}
QMenu::item:selected {
    background-color: @PRIMARY@;
}

QStatusBar {
    background-color: @BG_SURFACE@;
    border-top: 1px solid @BG_BTN@;
    color: @TEXT_MUTED@;
    font-size: 11px;
    padding: 4px 12px;
}
QStatusBar::item {
    border: none;
}

#collapsibleHeader {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    text-align: left;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 600;
    color: @TEXT_SECONDARY@;
}
#collapsibleHeader:hover {
    background-color: @BG_HOVER@;
    color: @TEXT_PRIMARY@;
}
#collapsibleHeader:pressed {
    background-color: @BG_PRESSED@;
}
#collapsibleContent {
    background-color: transparent;
    border: none;
}

#rightHandle {
    background-color: @BG_SURFACE@;
    border: none;
    border-right: 1px solid @BG_BTN@;
    border-radius: 0;
    min-height: 0;
}
#rightHandle:hover {
    background-color: @BG_HOVER@;
}
#rightHandle:hover #handleArrow {
    color: @PRIMARY@;
}

#leftHandle {
    background-color: @BG_SURFACE@;
    border: none;
    border-left: 1px solid @BG_BTN@;
    border-radius: 0;
    min-height: 0;
}
#leftHandle:hover {
    background-color: @BG_HOVER@;
}
#handleArrow {
    color: @TEXT_MUTED@;
    font-size: 10px;
    background-color: transparent;
    border: none;
    padding: 0;
}
#leftHandle:hover #handleArrow {
    color: @PRIMARY@;
}

#footerNavButton {
    background-color: transparent;
    color: @TEXT_MUTED@;
    border: 1px solid @BG_BTN@;
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 500;
}
#footerNavButton:hover {
    background-color: @BG_HOVER@;
    color: @TEXT_PRIMARY@;
    border-color: @TEXT_PLACEHOLDER@;
}
#footerNavButton:checked {
    background-color: @BG_HOVER@;
    color: @PRIMARY@;
    border-color: @PRIMARY@;
    font-weight: 600;
}

#navButton {
    background-color: transparent;
    color: @TEXT_SECONDARY@;
    border: none;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 500;
    text-align: left;
}
#navButton:hover {
    background-color: @BG_HOVER@;
    color: @TEXT_PRIMARY@;
}
#navButton:checked {
    background-color: @BG_HOVER@;
    color: @PRIMARY@;
    font-weight: 600;
}

#centerStack {
    border: none;
    background-color: transparent;
}

#connexionHeader {
    background-color: @BG_SURFACE@;
    border: 1px solid @BG_BTN@;
    border-radius: 6px;
    min-height: 44px;
}
#connexionHeader:hover {
    background-color: @BG_HOVER@;
    border-color: @PRIMARY@;
}

#headerAvatar {
    background-color: @TEXT_PLACEHOLDER@;
    color: @TEXT_PRIMARY@;
    font-weight: 700;
    font-size: 15px;
    border-radius: 18px;
    border: 2px solid @BG_BTN@;
    min-width: 36px;
    min-height: 36px;
}

#headerUsername {
    color: @TEXT_PRIMARY@;
    font-size: 12px;
    font-weight: 700;
    background: transparent;
}

#headerStatus {
    font-size: 11px;
    font-weight: 600;
    color: @TEXT_MUTED@;
    background: transparent;
}

#headerDisconnectBtn {
    color: @DANGER@;
    font-size: 11px;
    font-weight: 600;
    background: transparent;
    border: none;
    padding: 2px 4px;
    text-decoration: none;
}
#headerDisconnectBtn:hover {
    color: @DANGER_HOVER@;
}
#headerDisconnectBtn:pressed {
    color: @DANGER_PRESSED@;
}

#connexionCard {
    background-color: @BG_SIDE@;
    border: 1px solid @BG_BTN@;
    border-radius: 10px;
}
#connexionInput {
    background-color: @BG_SURFACE@;
    color: @TEXT_PRIMARY@;
    border: 1px solid @BG_BTN@;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 500;
}
#connexionInput:focus {
    border-color: @PRIMARY@;
}
#connexionInput::placeholder {
    color: @TEXT_MUTED@;
}
#connexionBtn {
    background-color: @PRIMARY@;
    color: @TEXT_WHITE@;
    border: none;
    border-radius: 6px;
    padding: 10px 24px;
    font-size: 13px;
    font-weight: 700;
    min-height: 20px;
}
#connexionBtn:hover {
    background-color: @PRIMARY_HOVER@;
}
#connexionBtn:pressed {
    background-color: @PRIMARY_PRESSED@;
}
#connexionBtnSecondary {
    background-color: transparent;
    color: @PRIMARY@;
    border: 1px solid @PRIMARY@;
    border-radius: 6px;
    padding: 10px 24px;
    font-size: 13px;
    font-weight: 600;
    min-height: 20px;
}
#connexionBtnSecondary:hover {
    background-color: @BG_HOVER@;
}
#connexionBtnSecondary:pressed {
    background-color: @BG_PRESSED@;
}

#connexionBtnDanger {
    background-color: transparent;
    color: @DANGER@;
    border: 1px solid @DANGER@;
    border-radius: 6px;
    padding: 10px 24px;
    font-size: 13px;
    font-weight: 600;
    min-height: 20px;
}
#connexionBtnDanger:hover {
    background-color: @DANGER_BG_HOVER@;
}
#connexionBtnDanger:pressed {
    background-color: @DANGER_BG_PRESSED@;
}

#progressionWidget {
    background-color: @BG_DARK@;
    border: 1px solid @BG_BTN@;
    border-radius: 6px;
    min-height: 40px;
}
#progressionMode {
    color: @TEXT_SECONDARY@;
    font-size: 10px;
    font-weight: 600;
    background-color: transparent;
    border: none;
    padding: 0;
}
#progressionValue {
    color: @TEXT_PRIMARY@;
    font-size: 15px;
    font-weight: 700;
    background-color: transparent;
    border: none;
    padding: 0;
}
#progressionBar {
    background-color: @BG_SURFACE@;
    border: 1px solid @BG_BTN@;
    border-radius: 4px;
    min-height: 8px;
    max-height: 8px;
    text-align: center;
}
#progressionBar::chunk {
    background-color: @PRIMARY@;
    border-radius: 3px;
}

#clientsHeader {
    background-color: @BG_DARK@;
    border: 1px solid @BG_BTN@;
    border-radius: 6px;
    min-height: 40px;
}
#clientsHeader:hover {
    border: 1px solid @PRIMARY@;
}
#clientsHeaderTitle {
    color: @PRIMARY@;
    font-size: 11px;
    font-weight: 600;
}
#clientsHeaderStatut {
    color: @TEXT_PRIMARY@;
    font-size: 13px;
    font-weight: 500;
}
#clientsActifsPage {
    background-color: transparent;
}
#clientRow {
    background-color: @BG_SURFACE2@;
    border: 1px solid @BG_BTN@;
    border-radius: 6px;
}
#clientRow:hover {
    background-color: @BG_ROW_HOVER@;
    border: 1px solid @BG_BTN_PRESSED@;
}
#clientsActionBtn {
    background-color: @BG_BTN@;
    color: @TEXT_TERTIARY@;
    border: 1px solid @TEXT_PLACEHOLDER@;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 500;
}
#clientsActionBtn:hover {
    background-color: @TEXT_PLACEHOLDER@;
    color: @TEXT_PRIMARY@;
    border: 1px solid @PRIMARY@;
}
#clientsActionBtn:pressed {
    background-color: @BG_BTN_PRESSED@;
}
#clientsActionBtnDanger {
    background-color: @BG_BTN@;
    color: @DANGER@;
    border: 1px solid @TEXT_PLACEHOLDER@;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 500;
}
#clientsActionBtnDanger:hover {
    background-color: @DANGER@;
    color: @TEXT_WHITE@;
    border: 1px solid @DANGER@;
}
#clientsActionBtnDanger:pressed {
    background-color: @DANGER_PRESSED2@;
}

#clientsScroll {
    background-color: transparent;
    border: none;
}
#clientsListContainer {
    background-color: transparent;
}

#telechargementsHeader {
    background-color: @BG_DARK@;
    border: 1px solid @BG_BTN@;
    border-radius: 6px;
    min-height: 40px;
}
#telechargementsHeader:hover {
    border: 1px solid @PRIMARY@;
}
#telechargementsHeaderTitle {
    color: @PRIMARY@;
    font-size: 11px;
    font-weight: 600;
}
#telechargementsHeaderStatut {
    color: @TEXT_PRIMARY@;
    font-size: 13px;
    font-weight: 500;
}
#telechargementsPage {
    background-color: transparent;
}
#downloadRow {
    background-color: @BG_SURFACE2@;
    border: 1px solid @BG_BTN@;
    border-radius: 6px;
}
#downloadRow:hover {
    background-color: @BG_ROW_HOVER@;
    border: 1px solid @BG_BTN_PRESSED@;
}
#downloadFileName {
    color: @TEXT_PRIMARY@;
    font-size: 13px;
    font-weight: 500;
}
#downloadProgress {
    background-color: @BG_SURFACE@;
    border: 1px solid @BG_BTN@;
    border-radius: 4px;
    min-height: 14px;
    max-height: 14px;
    text-align: center;
    font-size: 10px;
}
#downloadBtnCancel {
    background-color: @BG_BTN@;
    color: @DANGER@;
    border: 1px solid @TEXT_PLACEHOLDER@;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 500;
}
#downloadBtnCancel:hover {
    background-color: @DANGER@;
    color: @TEXT_WHITE@;
    border: 1px solid @DANGER@;
}
#downloadBtnRetry {
    background-color: @BG_BTN@;
    color: @WARNING@;
    border: 1px solid @TEXT_PLACEHOLDER@;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 500;
}
#downloadBtnRetry:hover {
    background-color: @WARNING@;
    color: @TEXT_DARK@;
    border: 1px solid @WARNING@;
}
#downloadScroll {
    background-color: transparent;
    border: none;
}
#downloadListContainer {
    background-color: transparent;
}
#downloadToolbar {
    background-color: @BG_SURFACE2@;
    border: 1px solid @BG_BTN@;
    border-radius: 6px;
    padding: 6px;
}
#toolbarBtn {
    background-color: @BG_BTN@;
    color: @TEXT_TERTIARY@;
    border: 1px solid @TEXT_PLACEHOLDER@;
    border-radius: 4px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
}
#toolbarBtn:hover {
    background-color: @TEXT_PLACEHOLDER@;
    color: @TEXT_PRIMARY@;
    border: 1px solid @PRIMARY@;
}
#toolbarBtn:pressed {
    background-color: @BG_BTN_PRESSED@;
}
#toolbarBtnDanger {
    background-color: @BG_BTN@;
    color: @DANGER@;
    border: 1px solid @TEXT_PLACEHOLDER@;
    border-radius: 4px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
}
#toolbarBtnDanger:hover {
    background-color: @DANGER@;
    color: @TEXT_WHITE@;
    border: 1px solid @DANGER@;
}

#clockWidget {
    background-color: @BG_DARK@;
    border: 1px solid @BG_BTN@;
    border-radius: 6px;
    padding: 4px;
}
#clockLabel {
    color: @SUCCESS@;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 18px;
    font-weight: 700;
    background-color: transparent;
    border: none;
    padding: 2px 8px;
}

#roomsTabs::pane {
    background-color: @BG_SURFACE@;
    border: 1px solid @PRIMARY@;
    border-radius: 0 0 6px 6px;
}
#roomsTabs QTabBar::tab {
    background-color: @BG_SURFACE@;
    color: @TEXT_MUTED@;
    border: 1px solid @BG_BTN@;
    border-bottom: none;
    border-radius: 0;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 600;
    margin-right: 2px;
}
#roomsTabs QTabBar::tab:selected {
    background-color: @BG_SURFACE@;
    color: @PRIMARY@;
    border-color: @PRIMARY@;
}
#roomsTabs QTabBar::tab:hover:!selected {
    background-color: @BG_HOVER@;
    color: @TEXT_PRIMARY@;
}

#configSection {
    background-color: transparent;
    border: none;
}

#configRow {
    background-color: @BG_SURFACE@;
    border: 1px solid @BG_BTN@;
    border-radius: 6px;
}
#configRow:hover {
    border-color: @BORDER_CONFIG@;
}

#configToggle {
    spacing: 0;
}
#configToggle::indicator {
    width: 36px;
    height: 20px;
    border-radius: 10px;
    background-color: @TEXT_PLACEHOLDER@;
    border: 1px solid @BG_BTN@;
}
#configToggle::indicator:checked {
    background-color: @PRIMARY@;
    border-color: @PRIMARY@;
}
#configToggle::indicator:unchecked:hover {
    background-color: @BG_BTN_PRESSED@;
}
#configToggle::indicator:checked:hover {
    background-color: @PRIMARY_HOVER2@;
}

#configEntry {
    background-color: @BG_SURFACE2@;
    color: @TEXT_PRIMARY@;
    border: 1px solid @BG_BTN@;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}
#configEntry:focus {
    border-color: @PRIMARY@;
}
#configEntry::placeholder {
    color: @TEXT_PLACEHOLDER@;
}

#configCombo {
    background-color: @BG_SURFACE2@;
    color: @TEXT_PRIMARY@;
    border: 1px solid @BG_BTN@;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
    min-width: 120px;
}
#configCombo:focus {
    border-color: @PRIMARY@;
}
#configCombo::drop-down {
    border: none;
    width: 24px;
}
#configCombo QAbstractItemView {
    background-color: @BG_SURFACE@;
    color: @TEXT_PRIMARY@;
    border: 1px solid @BG_BTN@;
    selection-background-color: @PRIMARY@;
    selection-color: @TEXT_WHITE@;
    outline: none;
}

#configSpin {
    background-color: @BG_SURFACE2@;
    color: @TEXT_PRIMARY@;
    border: 1px solid @BG_BTN@;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}
#configSpin:focus {
    border-color: @PRIMARY@;
}
#configSpin::up-button, #configSpin::down-button {
    border: none;
    background-color: transparent;
    width: 16px;
}
#configSpin::up-arrow {
    image: none;
}
#configSpin::down-arrow {
    image: none;
}

#configResetBtn {
    background-color: transparent;
    color: @TEXT_MUTED@;
    border: 1px solid @BG_BTN@;
    border-radius: 4px;
    padding: 6px 12px;
    font-size: 11px;
    margin-top: 12px;
}
#configResetBtn:hover {
    color: @DANGER@;
    border-color: @DANGER@;
}

#configScroll {
    background-color: transparent;
    border: none;
}

QScrollBar:vertical {
    width: 6px;
    background: transparent;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: @TEXT_PLACEHOLDER@;
    min-height: 30px;
    border-radius: 3px;
}
QScrollBar::handle:vertical:hover {
    background: @PRIMARY@;
}
QScrollBar::handle:vertical:pressed {
    background: @PRIMARY_PRESSED@;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
    background: none;
}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    height: 6px;
    background: transparent;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: @TEXT_PLACEHOLDER@;
    min-width: 30px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal:hover {
    background: @PRIMARY@;
}
QScrollBar::handle:horizontal:pressed {
    background: @PRIMARY_PRESSED@;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0;
    background: none;
}
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: none;
}
"""

# ── Génération du thème final ──────────────────────────────────────────────
DARK_THEME = _DARK_THEME_TEMPLATE
for _key, _value in COLORS.items():
    DARK_THEME = DARK_THEME.replace(f"@{_key}@", _value)
