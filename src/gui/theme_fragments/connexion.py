"""
CSS fragment — connexion (header, avatar, username).
"""


CSS = """\
/* ---- En-tete de connexion ---- */
#connexionHeader {
    background-color: @BG_SURFACE@;
    border-radius: 6px;
    min-height: 44px;
}
#connexionHeader:hover {
    background-color: @BG_HOVER@;
}

/* ---- Avatar du header ---- */
#headerAvatar {
    background-color: @BG_BTN_DISABLED@;
    color: @TEXT_PRIMARY@;
    font-weight: 700;
    font-size: 15px;
    border-radius: 18px;
    border: 2px solid @BORDER@;
    min-width: 36px;
    min-height: 36px;
}

/* ---- Nom d'utilisateur ---- */
#headerUsername {
    color: @TEXT_PRIMARY@;
    font-size: 12px;
    font-weight: 700;
    background: transparent;
}
"""
