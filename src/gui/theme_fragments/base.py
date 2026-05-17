"""
CSS fragment — base.
Utilise les placeholders @KEY@ definis dans colors.py.
"""


CSS = """\
QMainWindow {
    background-color: @BG_MAIN@;
}

QLabel {
    color: @TEXT_PRIMARY@;
    background-color: transparent;
}

QPushButton:hover {
    background-color: @PRIMARY_HOVER@;
}

QPushButton:pressed {
    background-color: @PRIMARY_PRESSED@;
}

QPushButton:disabled {
    background-color: @BG_BTN_DISABLED@;
    color: @TEXT_DISABLED@;
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

QMenuBar::item:selected {
    background-color: @BG_HOVER@;
    color: @TEXT_PRIMARY@;
}

QMenu {
    background-color: @BG_SURFACE@;
    border: 1px solid @BORDER@;
    color: @TEXT_PRIMARY@;
}

QMenu::item:selected {
    background-color: @PRIMARY@;
}

QStatusBar::item {
    border: none;
}
"""
