import logging
import pathlib
import sys

logger = logging.getLogger("[TEMP-RM-DUP2]")
f = pathlib.Path('src/gui/main_window.py')
raw = f.read_bytes()
text = raw.decode('utf-8-sig')
lines = text.replace('\r\n', '\n').split('\n')

# Remove duplicate menu block (second occurrence of Outils menu)
# Lines 167-173 (1-indexed) = indices 166-172 (0-indexed)
# Check: line 173 (index 172) should contain 'help_menu'

if len(lines) > 172 and 'help_menu' in lines[172]:
    # Confirm this is the right place
    new_lines = lines[:166] + lines[172:]
    result = '\n'.join(new_lines)
    f.write_bytes(result.encode('utf-8'))
    print(f"OK: removed duplicate, file now {len(result.encode('utf-8').split(b'\\n'))} lines")
    sys.exit(0)
else:
    print(f"ERR: line 173 = {repr(lines[172])[:80] if len(lines) > 172 else 'N/A'}")
    sys.exit(1)
