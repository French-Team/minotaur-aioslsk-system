"""
CSS fragment — config.
Utilise les placeholders @KEY@ definis dans colors.py.
"""

CSS = """\
#configRow {
    background-color: @BG_SURFACE@;
    border: 1px solid @BORDER@;
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
    background-color: @BG_BTN_DISABLED@;
    border: 1px solid @BORDER@;
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
    border: 1px solid @BORDER@;
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
    border: 1px solid @BORDER@;
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
    border: 1px solid @BORDER@;
    selection-background-color: @PRIMARY@;
    selection-color: @TEXT_WHITE@;
    outline: none;
}

#configSpin {
    background-color: @BG_SURFACE2@;
    color: @TEXT_PRIMARY@;
    border: 1px solid @BORDER@;
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
    border: 1px solid @BORDER@;
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
"""
