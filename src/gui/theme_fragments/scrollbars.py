"""
CSS fragment — scrollbars.
Utilise les placeholders @KEY@ definis dans colors.py.
"""


CSS = """\
QScrollBar::handle:vertical {
    background: @BG_BTN_DISABLED@;
    min-height: 15px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: @PRIMARY@;
}

QScrollBar::handle:vertical:pressed {
    background: @PRIMARY_PRESSED@;
}

QScrollBar::sub-line:vertical {
    height: 0;
    background: none;
}

QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar::handle:horizontal {
    background: @BG_BTN_DISABLED@;
    min-width: 15px;
    border-radius: 3px;
}

QScrollBar::handle:horizontal:hover {
    background: @PRIMARY@;
}

QScrollBar::handle:horizontal:pressed {
    background: @PRIMARY_PRESSED@;
}

QScrollBar::sub-line:horizontal {
    width: 0;
    background: none;
}

QScrollBar::sub-page:horizontal {
    background: none;
}
"""
