"""
Palette de couleurs centralisée.
Toutes les couleurs utilisées dans l'interface sont définies ici.
"""

def rgba(hex_color: str, alpha_hex: str) -> str:
    """Convertir une couleur hex + alpha hex en rgba() compatible Qt.

    Qt Style Sheets ne supporte pas le format #RRGGBBAA.
    Exemple : rgba('#6c5ce7', '44') -> 'rgba(108, 92, 231, 0.267)'
    """
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    a = round(int(alpha_hex, 16) / 255, 3)
    return f"rgba({r}, {g}, {b}, {a})"


COLORS = {
    "BG_MAIN":        "#0f0f13",
    "BG_DARK":        "#0a0a0f",
    "BG_CENTER":      "#111118",
    "BG_SIDE":        "#16161e",
    "BG_HEADER":      "#1c1c26",
    "BG_SURFACE":     "#1a1a22",
    "BG_SURFACE2":    "#14141e",
    "BG_HOVER":       "#24242e",
    "BG_PRESSED":     "#1e1e28",
    "BG_ROW_HOVER":   "#1a1a28",
    "BG_BTN":         "#2e2e3a",
    "BG_BTN_DISABLED":"#3a3a4a",
    "BG_BTN_PRESSED": "#4a4a5a",
    "PRIMARY":         "#7E5527",
    "PRIMARY_HOVER":   "#5F401C",
    "PRIMARY_HOVER2":  "#412A0F",
    "PRIMARY_PRESSED": "#44290B",
    "TEXT_PRIMARY":    "#e4e4ec",
    "TEXT_WHITE":      "#ffffff",
    "TEXT_SECONDARY":  "#8a8a9a",
    "TEXT_MUTED":       "#5a5a6a",
    "TEXT_MUTED_BG":    rgba("#5a5a6a", "4D"),
    "TEXT_MUTED_BORDER":rgba("#5a5a6a", "80"),
    "TEXT_TERTIARY":   "#b0b0c0",
    "TEXT_DISABLED":   "#6a6a7a",
    "TEXT_PLACEHOLDER":"#3a3a4a",
    "TEXT_DARK":       "#1a1a1a",
    "SUCCESS":          "#00e676",
    "SUCCESS_BG":       rgba("#00e676", "4D"),
    "SUCCESS_BORDER":   rgba("#00e676", "80"),
    "DANGER":           "#ff5252",
    "DANGER_HOVER":     "#ff7070",
    "DANGER_PRESSED":   "#cc3333",
    "DANGER_PRESSED2":  "#d32f2f",
    "DANGER_BG_HOVER":  "#2e1a1a",
    "DANGER_BG_PRESSED":"#1e1010",
    "WARNING":          "#ffab00",

    # Nuances BotBibliothèque (violet, grilles, inputs)
    "ACCENT":           "#362511",   # (boutons, highlights)
    "ACCENT_HOVER":     "#3A2308",   # survol
    "BG_INPUT":         "#1e1e2e",   # Fond inputs, tableaux
    "GRIDLINE":         "#2a2a3e",   # Lignes de grille/séparation
    "BG_TABLE_HEADER":  "#181825",   # Fond en-tête tableau
    "TEXT_INPUT":       "#cdd6f4",   # Texte sur inputs
    "TEXT_SURFACE":     "#a6adc8",   # Texte secondaire surfaces

    # Statistiques Bibliothèque
    "STAT_FILES":       "#00b894",   # Vert fichiers
    "STAT_FILES_HOVER": "#00a381",   # Vert fichiers survol
    "STAT_AUDIO":       "#fdcb6e",   # Jaune audio

    # Nuances danger spécifiques
    "DANGER_BTN":       "#e74c3c",   # Rouge bouton supprimer
    "DANGER_BTN_HOVER": "#c0392b",   # Rouge bouton supprimer survol

    "BORDER":          "#2e2e3a",
    "BORDER_LIGHT":    "#3a3a4a",
    "BORDER_HOVER":    "#4a4a5a",
    "BORDER_CONFIG":   "#3a3a5a",
}
