"""
CSS fragment — clients.
Utilise les placeholders @KEY@ definis dans colors.py.
"""


CSS = """\
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
    border: 1px solid @BORDER@;
    border-radius: 6px;
}

#clientRow:hover {
    background-color: @BG_ROW_HOVER@;
    border: 1px solid @BORDER_HOVER@;
}

#clientsActionBtn {
    background-color: @BG_BTN@;
    color: @TEXT_TERTIARY@;
    border: 1px solid @BORDER_LIGHT@;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 500;
}

#clientsActionBtn:hover {
    background-color: @BORDER_LIGHT@;
    color: @TEXT_PRIMARY@;
    border: 1px solid @PRIMARY@;
}

#clientsActionBtn:pressed {
    background-color: @BG_BTN_PRESSED@;
}

#clientsActionBtnDanger {
    background-color: @BG_BTN@;
    color: @DANGER@;
    border: 1px solid @BORDER_LIGHT@;
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
"""
