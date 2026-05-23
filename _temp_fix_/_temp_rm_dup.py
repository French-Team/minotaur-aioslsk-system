import logging
import pathlib

logger = logging.getLogger("[TEMP-RM-DUP]")
f = pathlib.Path('src/gui/main_window.py')
lines = f.read_text(encoding='utf-8').splitlines()

# Find lines with duplicate menu - look for the second Outils menu
# Line 167 (index 166) is the duplicate comment line
# Line 173 (index 172) is tools_menu.addAction

# Print for verification
for i in range(155, min(180, len(lines))):
    print(f'{i+1}: |{lines[i]}|')

# Check if line 166 (index 165) contains "Menu Outils ? QSS Inspector"
# and line 173 (index 172) starts with "        help_menu"
if len(lines) > 173:
    # Remove lines 167-173 (index 166-172) if they're the duplicate
    # Check the context
    if 'Menu Outils' in lines[165] and 'help_menu' in lines[173]:
        print("\n--- Removing duplicate lines 167-173 ---")
        new_lines = lines[:166] + lines[173:]
        f.write_text('\n'.join(new_lines), encoding='utf-8')
        print("Duplicate removed!")
    else:
        print("\nPattern doesn't match, checking what's there...")
