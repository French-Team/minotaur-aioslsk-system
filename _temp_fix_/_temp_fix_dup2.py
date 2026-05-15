import pathlib, sys
f = pathlib.Path('src/gui/main_window.py')
raw = f.read_bytes()
text = raw.decode('utf-8-sig')
lines = text.replace('\r\n', '\n').split('\n')

# Remove lines 167-173 (1-indexed) = indices 166-172 (0-indexed)
# Verify: line 166 (0-indexed) should start with '# .. Menu Outils'
safe_check = ''.join(c if ord(c) < 128 else '?' for c in lines[166])
if 'Menu Outils' in safe_check:
    new_lines = lines[:166] + lines[173:]
    result = '\n'.join(new_lines)
    f.write_bytes(result.encode('utf-8'))
    sys.exit(0)
else:
    sys.exit(1)
