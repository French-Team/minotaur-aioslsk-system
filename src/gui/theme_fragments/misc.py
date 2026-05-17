"""
CSS fragment — misc.
Utilise les placeholders @KEY@ definis dans colors.py.
"""


CSS = """\
#clockLabel {
    color: @SUCCESS@;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 18px;
    font-weight: 700;
    background-color: transparent;
    border: none;
    padding: 2px 8px;
}

#roomsTabs QTabBar::tab {
    background-color: @BG_SURFACE@;
    color: @TEXT_MUTED@;
    border: 1px solid @BORDER@;
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
"""
