"""
CSS fragment — Bibliothèque (exploration fichiers partagés).
Utilise les placeholders @KEY@ définis dans colors.py.
"""


CSS = """
/* ============================================================
   BotBibliotheque — Stat Cards
   ============================================================ */
#statCard {
    background: @BG_SURFACE@;
    border: 1px solid @BORDER@;
    border-radius: 8px;
    min-width: 120px;
}

#statCardValue {
    font-size: 24px;
    font-weight: 700;
    background: transparent;
    border: none;
}

#statCardLabel {
    color: @TEXT_DISABLED@;
    font-size: 11px;
    background: transparent;
    border: none;
}

/* ============================================================
   BotBibliotheque — Toolbar (search, progress, rescan)
   ============================================================ */
#bibliothequeToolbar {
    background: transparent;
    border: none;
}

#bibliothequeSearch {
    background: @BG_INPUT@;
    border: 1px solid @BORDER_LIGHT@;
    border-radius: 6px;
    color: @TEXT_INPUT@;
    font-size: 13px;
    padding: 6px 10px;
}

#bibliothequeSearch:focus {
    border-color: @ACCENT@;
}

#bibliothequeProgress {
    background: @BG_INPUT@;
    border: 1px solid @BORDER_LIGHT@;
    border-radius: 5px;
    text-align: center;
    min-height: 20px;
    max-height: 20px;
    font-size: 11px;
    color: @TEXT_PRIMARY@;
}

#bibliothequeProgress::chunk {
    background: @ACCENT@;
    border-radius: 5px;
}

#bibliothequeRescan {
    background: @ACCENT@;
    color: @TEXT_WHITE@;
    border: none;
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 600;
}

#bibliothequeRescan:hover {
    background: @ACCENT_HOVER@;
}

#bibliothequeRescan:disabled {
    background: @BG_BTN_DISABLED@;
    color: @TEXT_DISABLED@;
}

/* ============================================================
   BotBibliotheque — FileInfoPopup (dialog)
   ============================================================ */
#fileInfoPopup {
    background: @BG_INPUT@;
    border: 1px solid @BORDER_LIGHT@;
    border-radius: 8px;
}

#fileInfoTitle {
    color: @TEXT_INPUT@;
    font-size: 16px;
    font-weight: 700;
    background: transparent;
    border: none;
}

#fileInfoLabel {
    color: @TEXT_SURFACE@;
    font-size: 13px;
    font-weight: 600;
    background: transparent;
    border: none;
}

#fileInfoValue {
    color: @TEXT_INPUT@;
    font-size: 13px;
    background: transparent;
    border: none;
}

#fileInfoSep {
    color: @BORDER_LIGHT@;
    background: transparent;
    border: none;
}

#fileInfoSepAudio {
    color: @ACCENT@;
    background: transparent;
    border: none;
    font-weight: 600;
}

#fileInfoRow {
    background: transparent;
    border: none;
}

#infoLireBtn {
    background: @STAT_FILES@;
    color: @TEXT_WHITE@;
    border: none;
    border-radius: 5px;
    padding: 8px 20px;
    font-size: 12px;
    font-weight: 600;
}

#infoLireBtn:hover {
    background: @STAT_FILES_HOVER@;
}

#infoSupprBtn {
    background: @DANGER_BTN@;
    color: @TEXT_WHITE@;
    border: none;
    border-radius: 5px;
    padding: 8px 20px;
    font-size: 12px;
    font-weight: 600;
}

#infoSupprBtn:hover {
    background: @DANGER_BTN_HOVER@;
}

#infoFermerBtn {
    background: @BG_BTN_DISABLED@;
    color: @TEXT_INPUT@;
    border: none;
    border-radius: 5px;
    padding: 8px 20px;
    font-size: 12px;
    font-weight: 600;
}

#infoFermerBtn:hover {
    background: @BG_BTN_PRESSED@;
}

/* ============================================================
   BotBibliotheque — Header
   ============================================================ */
#bibliothequeHeader {
    color: @TEXT_INPUT@;
    font-size: 18px;
    font-weight: 700;
    background: transparent;
    border: none;
    padding: 0;
}

/* ============================================================
   BotBibliotheque — Status Bar
   ============================================================ */
#bibliothequeStatus {
    color: @TEXT_DISABLED@;
    font-size: 11px;
    padding: 4px 0;
    background: transparent;
    border: none;
}

/* ============================================================
   BotBibliotheque — Disconnected State
   ============================================================ */
#lockIcon {
    font-size: 48px;
    background: transparent;
    border: none;
}

#lockMessage {
    color: @TEXT_SURFACE@;
    font-size: 14px;
    background: transparent;
    border: none;
}

#connectSoulseekBtn {
    background: @ACCENT@;
    color: @TEXT_WHITE@;
    border: none;
    border-radius: 6px;
    padding: 10px 24px;
    font-size: 13px;
    font-weight: 600;
    min-width: 160px;
}

#connectSoulseekBtn:hover {
    background: @ACCENT_HOVER@;
}

/* ============================================================
   BotBibliotheque — Splitter
   ============================================================ */
#bibliothequeSplitter::handle {
    background: @BORDER_LIGHT@;
    width: 2px;
}

/* ============================================================
   BotBibliotheque — Tree Widget (dossiers)
   ============================================================ */
#folderTree {
    background: @BG_INPUT@;
    border: 1px solid @BORDER_LIGHT@;
    border-radius: 6px;
    color: @TEXT_INPUT@;
    font-size: 13px;
    outline: none;
}

#folderTree::item:selected {
    background: @GRIDLINE@;
    color: @TEXT_WHITE@;
}

#folderTree::item:hover {
    background: @BG_HOVER@;
}

#folderTree QHeaderView::section {
    background: @BG_TABLE_HEADER@;
    color: @TEXT_SURFACE@;
    border: none;
    border-bottom: 1px solid @BORDER_LIGHT@;
    padding: 6px 10px;
    font-size: 12px;
    font-weight: 600;
}

/* ============================================================
   BotBibliotheque — Table Widget (fichiers)
   ============================================================ */
#fileTable {
    background: @BG_INPUT@;
    border: 1px solid @BORDER_LIGHT@;
    border-radius: 6px;
    color: @TEXT_INPUT@;
    font-size: 13px;
    gridline-color: @GRIDLINE@;
    outline: none;
}

#fileTable::item:selected {
    background: @ACCENT@;
    color: @TEXT_WHITE@;
}

#fileTable::item:hover {
    background: @BG_HOVER@;
}

#fileTable QHeaderView::section {
    background: @BG_TABLE_HEADER@;
    color: @TEXT_SURFACE@;
    border: none;
    border-bottom: 1px solid @BORDER_LIGHT@;
    padding: 6px 10px;
    font-size: 12px;
    font-weight: 600;
}

/* Alternating row colors */
#fileTable::item:alternate {
    background: @BG_SURFACE2@;
}

/* ============================================================
   BotBibliotheque — Empty State
   ============================================================ */
#bibliothequeEmpty {
    color: @TEXT_MUTED@;
    font-size: 13px;
    background: transparent;
    border: none;
}

/* ============================================================
   BotBibliotheque — Context Menu
   ============================================================ */
#bibliothequeMenu {
    background: @BG_INPUT@;
    border: 1px solid @BORDER_LIGHT@;
    border-radius: 6px;
    padding: 4px 0;
}

#bibliothequeMenu::item {
    color: @TEXT_INPUT@;
    padding: 6px 16px;
    font-size: 12px;
}

#bibliothequeMenu::item:selected {
    background: @ACCENT@;
    color: @TEXT_WHITE@;
}

#bibliothequeMenu::separator {
    height: 1px;
    background: @BORDER_LIGHT@;
    margin: 4px 8px;
}

/* ============================================================
   BotBibliotheque — Message Box
   ============================================================ */
#bibliothequeMsgBox {
    background: @BG_INPUT@;
    color: @TEXT_INPUT@;
}

#bibliothequeMsgBox QLabel {
    color: @TEXT_INPUT@;
}

#bibliothequeMsgBox QPushButton {
    background: @BG_BTN_DISABLED@;
    color: @TEXT_INPUT@;
    border: none;
    border-radius: 5px;
    padding: 8px 24px;
    font-size: 12px;
    font-weight: 600;
    min-width: 80px;
}

#bibliothequeMsgBox QPushButton:hover {
    background: @BG_BTN_PRESSED@;
}
"""
