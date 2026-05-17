"""
CSS fragment — layout.
Utilise les placeholders @KEY@ definis dans colors.py.
"""

CSS = """\
#leftZone {
    border: 1px solid @BORDER_LIGHT@;
    background-color: @BG_SIDE@;
}

#centerZone {
    border: 1px solid @BORDER_LIGHT@;
    background-color: @BG_CENTER@;
}

#rightZone {
    border: 1px solid @BORDER_LIGHT@;
    background-color: @BG_SIDE@;
}

#footerZone {
    border: 1px solid @BORDER_LIGHT@;
    background-color: @BG_HEADER@;
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

#rightHandle:hover {
    background-color: @BG_HOVER@;
}

#rightHandle:hover #handleArrow {
    color: @PRIMARY@;
}

#leftHandle:hover {
    background-color: @BG_HOVER@;
}

#leftHandle:hover #handleArrow {
    color: @PRIMARY@;
}

#footerNavButton:hover {
    background-color: @BG_HOVER@;
    color: @TEXT_PRIMARY@;
    border-color: @BORDER_LIGHT@;
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
    border-radius: 4px;
    padding: 8px 12px;
    font-size: 12px;
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
"""
