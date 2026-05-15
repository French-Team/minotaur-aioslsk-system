import pathlib, sys
f = pathlib.Path('src/gui/main_window.py')
raw = f.read_bytes()
text = raw.decode('utf-8-sig')
lines = text.replace('\r\n', '\n').split('\n')

# Find ALL lines mentioning Outils or QSS Inspector or tools_menu
for i, line in enumerate(lines):
    if 'Outils' in line or 'QSS' in line or 'tools_menu' in line or 'inspect_action' in line:
        safe = ''.join(c if ord(c) < 128 else '.' for c in line)
        print(f'{i+1}: {safe}')

print('---')
# Also find the help_menu line
for i, line in enumerate(lines):
    if 'help_menu' in line:
        print(f'{i+1}: {line}')
