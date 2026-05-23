import logging
import pathlib

logger = logging.getLogger("[TEMP-FIX-DUP]")
f = pathlib.Path('src/gui/main_window.py')
raw = f.read_bytes()
text = raw.decode('utf-8-sig')
lines = text.replace('\r\n', '\n').split('\n')

# Remove lines 167-173 (0-indexed: 166 to 172 inclusive)
# Line 173 (index 172) is tools_menu.addAction
# After removing, line 166 (0-indexed: 165) is the first menu's tools_menu.addAction
# and line 174 (0-indexed: 173) should be help_menu

print(f"Total lines: {len(lines)}")
print(f"Line 166: {lines[165]}")
print(f"Line 167: {lines[166]}")
print(f"Line 174: {lines[173]}")
print(f"Line 175: {lines[174]}")

# Remove lines 166-172 (0-indexed)
new_lines = lines[:166] + lines[173:]
result = '\n'.join(new_lines)
f.write_bytes(result.encode('utf-8'))
print(f"Done! New line count: {len(new_lines)}")
