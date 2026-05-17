"""
CSS fragment — progression.
Utilise les placeholders @KEY@ definis dans colors.py.
"""


CSS = """\
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
    border: 1px solid @BORDER@;
    border-radius: 4px;
    min-height: 8px;
    max-height: 8px;
    text-align: center;
}

#progressionBar::chunk {
    background-color: @PRIMARY@;
    border-radius: 3px;
}
"""
