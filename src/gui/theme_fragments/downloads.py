"""
CSS fragment — downloads.
Utilise les placeholders @KEY@ definis dans colors.py.
"""


CSS = """\
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
    border: 1px solid @BORDER@;
    border-radius: 6px;
}

#downloadRow:hover {
    background-color: @BG_ROW_HOVER@;
    border: 1px solid @BORDER_HOVER@;
}

#downloadFileName {
    color: @TEXT_PRIMARY@;
    font-size: 13px;
    font-weight: 500;
}

#downloadProgress {
    background-color: @BG_SURFACE@;
    border: 1px solid @BORDER@;
    border-radius: 4px;
    min-height: 14px;
    max-height: 14px;
    text-align: center;
    font-size: 10px;
}

#downloadBtnCancel {
    background-color: @BG_BTN@;
    color: @DANGER@;
    border: 1px solid @BORDER_LIGHT@;
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
    border: 1px solid @BORDER_LIGHT@;
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
    border: 1px solid @BORDER@;
    border-radius: 6px;
    padding: 6px;
}

#toolbarBtn {
    background-color: @BG_BTN@;
    color: @TEXT_TERTIARY@;
    border: 1px solid @BORDER_LIGHT@;
    border-radius: 4px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
}

#toolbarBtn:hover {
    background-color: @BORDER_LIGHT@;
    color: @TEXT_PRIMARY@;
    border: 1px solid @PRIMARY@;
}

#toolbarBtn:pressed {
    background-color: @BG_BTN_PRESSED@;
}

#toolbarBtnDanger {
    background-color: @BG_BTN@;
    color: @DANGER@;
    border: 1px solid @BORDER_LIGHT@;
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
"""
